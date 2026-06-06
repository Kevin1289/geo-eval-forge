"""Aggregate graded candidates into ``results.json`` and per-task map GeoJSON.

Offline, the suite grades every recorded candidate (correct + wrong). To populate
a leaderboard without live model runs, we synthesize two illustrative pseudo-models
from the candidate library:

- ``expert``    — always picks the ``correct`` candidate (≈100%).
- ``naive-llm`` — picks the first ``wrong`` candidate where a documented trap exists,
  otherwise the correct one — i.e. it falls into exactly the traps the suite encodes.

When real models are run live (``geoeval run --adapter vertex``), their rows are
appended alongside these. The leaderboard math is identical either way.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .models import Candidate, Task, Verdict

ROOT = Path(__file__).resolve().parent.parent


def _solution_code(task: Task, candidate: Candidate) -> str | None:
    if not candidate.solution:
        return None
    p = task.dir / "candidates" / candidate.solution
    return p.read_text() if p.exists() else None


def _golden_summary(task: Task) -> str:
    g = task.golden
    if isinstance(g, dict):
        if "value" in g:
            return f"{g['value']} {g.get('unit', '')}".strip()
        if g.get("type") == "FeatureCollection":
            return f"{len(g.get('features', []))} features @ EPSG:{g.get('crs_epsg')}"
        if "rows" in g:
            return f"{len(g['rows'])} rows"
        if "feature_count" in g:
            return f"WFS feature_count={g['feature_count']}"
    if not task.solvable:
        return "unsolvable (must refuse)"
    return "—"


def build_results(graded: list[tuple[Task, Candidate, Verdict]], mode: str) -> dict:
    by_task: dict[str, dict] = {}
    tasks_order: list[str] = []
    task_obj: dict[str, Task] = {}

    for task, cand, verdict in graded:
        if task.id not in by_task:
            tasks_order.append(task.id)
            task_obj[task.id] = task
            by_task[task.id] = {
                "id": task.id, "title": task.title, "category": task.category,
                "difficulty": task.difficulty, "prompt": task.prompt,
                "solvable": task.solvable, "rejection_reason": task.rejection_reason,
                "golden_summary": _golden_summary(task),
                "map": None, "candidates": [],
            }
        by_task[task.id]["candidates"].append({
            "name": cand.name, "label": cand.label,
            "failure_class": cand.failure_class, "description": cand.description,
            "passed": verdict.passed, "score": round(verdict.score, 4),
            "detail": verdict.detail, "solution_code": _solution_code(task, cand),
        })

    tasks = [by_task[tid] for tid in tasks_order]
    categories = sorted({t["category"] for t in tasks})

    # ----- leaderboard -----
    def selector(name: str):
        """Return a function picking one candidate per task for a given 'model'."""
        if name == "expert":
            return lambda cands: next((c for c in cands if c["label"] == "correct"),
                                      cands[0] if cands else None)
        if name == "naive-llm":
            return lambda cands: next((c for c in cands if c["label"] == "wrong"),
                                      next((c for c in cands if c["label"] == "correct"), None))
        # real model run live: pick the candidate whose name matches the model
        return lambda cands: next((c for c in cands if c["name"] == name), None)

    def score_model(name: str) -> dict:
        per_cat_pass: dict[str, list[int]] = defaultdict(list)
        rej_pass: list[int] = []
        chosen, sel = [], selector(name)
        for te in tasks:
            c = sel(te["candidates"])
            if not c:
                continue
            ok = 1 if c["passed"] else 0
            per_cat_pass[te["category"]].append(ok)
            if te["category"] == "rejection":
                rej_pass.append(ok)
            chosen.append((te["id"], c["name"], ok))
        total = sum(len(v) for v in per_cat_pass.values())
        solved = sum(sum(v) for v in per_cat_pass.values())
        return {
            "model": name,
            "overall": round(solved / total, 4) if total else None,
            "solved": solved, "total": total,
            "by_category": {k: round(sum(v) / len(v), 4) for k, v in per_cat_pass.items()},
            "rejection_accuracy": round(sum(rej_pass) / len(rej_pass), 4) if rej_pass else None,
            "picks": chosen,
        }

    # real model rows first (live baselines), then the illustrative pseudo-models
    model_names: list[str] = []
    for te in tasks:
        for c in te["candidates"]:
            if c["label"] == "model" and c["name"] not in model_names:
                model_names.append(c["name"])

    leaderboard = [score_model(m) for m in model_names] + [
        score_model("expert"), score_model("naive-llm"),
    ]

    # ----- failure taxonomy (wrong candidates that did fail, by class) -----
    tax: Counter = Counter()
    example: dict[str, str] = {}
    for te in tasks:
        for c in te["candidates"]:
            if c["label"] == "wrong" and not c["passed"] and c["failure_class"]:
                tax[c["failure_class"]] += 1
                example.setdefault(c["failure_class"], te["id"])
    failure_taxonomy = [
        {"failure_class": k, "count": v, "example_task": example[k]}
        for k, v in tax.most_common()
    ]

    return {
        "suite": "geo-eval-forge",
        "mode": mode,
        "categories": categories,
        "tasks": tasks,
        "leaderboard": leaderboard,
        "failure_taxonomy": failure_taxonomy,
        "judge": {"calibrated": False, "human_agreement": None, "n_labels": 0},
    }


def emit_map_geojson(graded: list[tuple[Task, Candidate, Verdict]], out_dir: Path) -> dict[str, str]:
    """For tasks whose answers are FeatureCollections in EPSG:4326, write a combined
    GeoJSON (golden + each candidate, tagged by role) the MapExplorer can overlay."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_task: dict[str, Task] = {}
    cands_by_task: dict[str, list[Candidate]] = defaultdict(list)
    for task, cand, _ in graded:
        by_task[task.id] = task
        cands_by_task[task.id].append(cand)

    written: dict[str, str] = {}
    for tid, task in by_task.items():
        # 1) explicit hand-authored map for tasks whose answer isn't a 4326 FC
        explicit = task.dir / "map.geojson" if task.dir else None
        if explicit and explicit.exists():
            (out_dir / f"{tid}.json").write_text(explicit.read_text())
            written[tid] = f"geojson/{tid}.json"
            continue

        g = task.golden
        if not (isinstance(g, dict) and g.get("type") == "FeatureCollection" and g.get("crs_epsg") == 4326):
            continue
        feats = []
        for f in g.get("features", []):
            feats.append({**f, "properties": {**f.get("properties", {}), "_role": "golden"}})
        for cand in cands_by_task[tid]:
            p = cand.produced
            if isinstance(p, dict) and p.get("type") == "FeatureCollection" and p.get("crs_epsg") == 4326:
                for f in p.get("features", []):
                    feats.append({**f, "properties": {
                        **f.get("properties", {}), "_role": cand.name, "_label": cand.label}})
        fc = {"type": "FeatureCollection", "display_crs": 4326, "features": feats}
        (out_dir / f"{tid}.json").write_text(json.dumps(fc))
        written[tid] = f"geojson/{tid}.json"
    return written


def write_results(results: dict, out_path: Path, map_index: dict[str, str]) -> None:
    for t in results["tasks"]:
        if t["id"] in map_index:
            t["map"] = map_index[t["id"]]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
