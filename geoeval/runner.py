"""Grade candidates — either from recorded output (offline) or by executing the
solution against the live stack (live).

The offline path needs only the recorded ``candidate.produced`` and the pure
verifiers, so it runs anywhere with no DB/GDAL. The live path (PostGIS via
psycopg, GDAL via subprocess) is used by ``make run-live`` and the integration
tests; its heavy imports are deferred so importing this module never requires them.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .models import Candidate, Task, Verdict
from .verifiers import get_verifier


# --------------------------------------------------------------------------- #
# Grading (verifier composition)
# --------------------------------------------------------------------------- #
def grade_produced(task: Task, produced: Any) -> Verdict:
    """Run every verifier declared by the task and AND the results."""
    verdicts = []
    for spec in task.verifier_specs:
        fn = get_verifier(spec["name"])
        verdicts.append((spec["name"], fn(task, produced, spec.get("params", {}))))

    passed = all(v.passed for _, v in verdicts)
    score = sum(v.score for _, v in verdicts) / len(verdicts)
    detail = " ; ".join(f"[{name}] {v.detail}" for name, v in verdicts)
    return Verdict(passed, score, detail,
                   expected=[v.expected for _, v in verdicts],
                   got=[v.got for _, v in verdicts])


def run_offline(task: Task, candidate: Candidate) -> Verdict:
    if candidate.produced is None:
        return Verdict(False, 0.0,
                       f"candidate '{candidate.name}' has no recorded 'produced' output for offline grading",
                       None, None)
    return grade_produced(task, candidate.produced)


# --------------------------------------------------------------------------- #
# Live execution
# --------------------------------------------------------------------------- #
def db_dsn() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'postgis')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'geoeval')} "
        f"user={os.environ.get('POSTGRES_USER', 'geoeval')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'geoeval')}"
    )


def _shape_sql_output(task: Task, columns: list[str], rows: list[tuple]) -> Any:
    """Normalize a SQL result into the canonical form the task's verifier expects."""
    names = {s["name"] for s in task.verifier_specs}

    # numeric: a single 'value' cell
    if "numeric" in names and len(columns) == 1 and len(rows) == 1:
        return {"value": rows[0][0]}

    # vector: rows of (id, geojson[, attrs...]) -> FeatureCollection
    if names & {"vector_equiv", "crs_check"} and "geojson" in columns:
        gj_i = columns.index("geojson")
        id_i = columns.index("id") if "id" in columns else 0
        feats = []
        for r in rows:
            props = {c: r[i] for i, c in enumerate(columns) if c != "geojson"}
            feats.append({"type": "Feature", "properties": props,
                          "geometry": json.loads(r[gj_i])})
        epsg = (task.expected or {}).get("epsg") or (task.golden or {}).get("crs_epsg")
        return {"type": "FeatureCollection", "crs_epsg": epsg, "features": feats}

    # default: a result set
    return {"columns": columns, "rows": [list(r) for r in rows]}


def produce_live_sql(task: Task, solution_path: Path) -> Any:
    import psycopg  # deferred (live extra)

    setup = task.dir / "setup.sql"
    sql = solution_path.read_text()
    with psycopg.connect(db_dsn()) as conn, conn.cursor() as cur:
        if setup.exists():  # task-local tables (kept separate from the shared seed)
            cur.execute(setup.read_text())
        cur.execute(sql)
        columns = [d.name for d in cur.description] if cur.description else []
        rows = cur.fetchall() if cur.description else []
    return _shape_sql_output(task, columns, rows)


def produce_live_shell(task: Task, solution_path: Path) -> Any:
    """Run a GDAL shell solution that prints the path of a vector file it produced,
    then normalize that file to a canonical FeatureCollection via ogr2ogr."""
    proc = subprocess.run(["bash", str(solution_path)], cwd=str(task.dir),
                          capture_output=True, text=True, check=True)
    out_path = proc.stdout.strip().splitlines()[-1].strip()
    gj = subprocess.run(
        ["ogr2ogr", "-f", "GeoJSON", "/vsistdout/", out_path, "-lco", "RFC7946=NO"],
        capture_output=True, text=True, check=True,
    ).stdout
    fc = json.loads(gj)
    # derive EPSG from the source (ogr keeps native CRS with RFC7946=NO)
    epsg = (task.expected or {}).get("epsg") or (task.golden or {}).get("crs_epsg")
    fc["crs_epsg"] = epsg
    return fc


def run_live(task: Task, candidate: Candidate) -> Verdict:
    if not candidate.solution:
        # rejection/recorded-only candidates fall back to their recorded output
        return run_offline(task, candidate)
    sol = task.dir / "candidates" / candidate.solution
    try:
        if sol.suffix == ".sql":
            produced = produce_live_sql(task, sol)
        elif sol.suffix in (".sh", ".bash"):
            produced = produce_live_shell(task, sol)
        else:
            return run_offline(task, candidate)
    except Exception as exc:  # execution failure is itself a (failing) result
        return Verdict(False, 0.0, f"live execution error: {type(exc).__name__}: {exc}", None, None)
    return grade_produced(task, produced)


# --------------------------------------------------------------------------- #
# Live model baseline (run an LLM over the suite)
# --------------------------------------------------------------------------- #
GEO_SYSTEM = (
    "You are an expert GIS engineer. Solve the task precisely. Always use a "
    "projected/equal-area CRS for distance and area; respect topological "
    "predicate semantics; and REFUSE any task that cannot be answered correctly "
    "with the data provided rather than guessing."
)


def _output_spec(task: Task) -> str:
    names = {s["name"] for s in task.verifier_specs}
    if (not task.solvable) or "rejection" in names:
        return '{"action": "refuse" | "attempt", "reason": "<why>", "value": <optional answer>}'
    if "numeric" in names:
        unit = (task.golden or {}).get("unit", "") if isinstance(task.golden, dict) else ""
        return f'{{"value": <number in {unit or "the requested unit"}>}}'
    if names & {"vector_equiv", "crs_check"}:
        epsg = (task.expected or {}).get("epsg") or (isinstance(task.golden, dict) and task.golden.get("crs_epsg"))
        return ('{"type":"FeatureCollection","crs_epsg":%s,'
                '"features":[{"type":"Feature","properties":{"id":<id>},"geometry":{...}}]}' % epsg)
    if "sql_result" in names:
        return '{"columns":[...], "rows":[[...], ...]}'
    if "service_check" in names:
        return '{"feature_count": <int>}'
    return '{"value": <answer>}'


def _extract_json(text: str) -> Any:
    import re

    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    blob = m.group(1) if m else None
    if blob is None:
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j > i:
            blob = text[i:j + 1]
    if blob is None:
        raise ValueError("no JSON object found in model output")
    return json.loads(blob)


def produce_model(task: Task, client) -> Any:
    prompt = (
        f"{task.prompt}\n\n"
        f"Inputs available: {json.dumps(task.inputs)}\n\n"
        f"Respond with ONLY a fenced ```json block matching this schema:\n{_output_spec(task)}"
    )
    text = client.complete(prompt, system=GEO_SYSTEM, key=task.id)
    return _extract_json(text)


def run_model(task: Task, client) -> Verdict:
    try:
        produced = produce_model(task, client)
    except Exception as exc:
        return Verdict(False, 0.0, f"model output parse error: {type(exc).__name__}: {exc}", None, None)
    return grade_produced(task, produced)
