"""Export the benchmark as ready-to-use AI-training data.

Two artifacts, both JSONL:

- ``records.jsonl``          one row per candidate — an SFT/eval item carrying the
                            prompt, the candidate's solution/output, whether it
                            passed the deterministic verifier, and *why*.
- ``preference_pairs.jsonl``  one row per (correct, wrong) pair per task — a
                            DPO/RLHF-style chosen-vs-rejected example, tagged with
                            the failure class and the reason the rejected one is wrong.

This is the actual contract deliverable in miniature: hard, verifiable, contrastive
data with a machine-checkable label, not human-asserted.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import loader, runner

ROOT = Path(__file__).resolve().parent.parent


def _modality(cand) -> str:
    if cand.solution and cand.solution.endswith(".sql"):
        return "sql"
    if isinstance(cand.produced, dict) and cand.produced.get("action") in ("refuse", "attempt"):
        return "rejection"
    return "artifact"


def _solution_code(task, cand) -> str | None:
    if not cand.solution:
        return None
    p = task.dir / "candidates" / cand.solution
    return p.read_text() if p.exists() else None


def build() -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    pairs: list[dict] = []

    for task, cands in loader.load_all():
        for c in cands:
            verdict = runner.run_offline(task, c)
            records.append({
                "task_id": task.id, "category": task.category, "difficulty": task.difficulty,
                "prompt": task.prompt, "solvable": task.solvable,
                "candidate": c.name, "label": c.label, "failure_class": c.failure_class,
                "rationale": c.description, "modality": _modality(c),
                "solution_code": _solution_code(task, c), "produced": c.produced,
                "passed": verdict.passed, "verifier_detail": verdict.detail,
            })

        correct = next((c for c in cands if c.label == "correct"), None)
        if correct:
            chosen = {"solution_code": _solution_code(task, correct), "produced": correct.produced}
            for c in cands:
                if c.label != "wrong":
                    continue
                pairs.append({
                    "task_id": task.id, "category": task.category, "prompt": task.prompt,
                    "chosen": chosen,
                    "rejected": {"solution_code": _solution_code(task, c), "produced": c.produced},
                    "failure_class": c.failure_class, "why_rejected": c.description,
                })

    return records, pairs


def write(out_dir: Path) -> tuple[int, int]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records, pairs = build()
    (out_dir / "records.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")
    (out_dir / "preference_pairs.jsonl").write_text("\n".join(json.dumps(p) for p in pairs) + "\n")
    return len(records), len(pairs)
