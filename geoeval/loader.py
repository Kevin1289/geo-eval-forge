"""Load and schema-validate tasks and their candidate solutions."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .models import Candidate, Task

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
SCHEMA_PATH = ROOT / "schema" / "task.schema.json"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def validate_task_dict(data: dict, validator: Draft202012Validator | None = None) -> None:
    validator = validator or Draft202012Validator(load_schema())
    validator.validate(data)


def task_dirs() -> list[Path]:
    if not TASKS_DIR.exists():
        return []
    return sorted(p for p in TASKS_DIR.iterdir() if (p / "task.json").exists())


def load_task(task_dir: Path, validator: Draft202012Validator | None = None) -> Task:
    data = json.loads((task_dir / "task.json").read_text())
    validate_task_dict(data, validator)
    task = Task(
        id=data["id"],
        title=data["title"],
        category=data["category"],
        difficulty=data["difficulty"],
        prompt=data["prompt"],
        solvable=data["solvable"],
        verifier=data["verifier"],
        expected=data.get("expected", {}),
        inputs=data.get("inputs", {}),
        rejection_reason=data.get("rejection_reason"),
        dir=task_dir,
    )
    golden_path = task_dir / "golden" / "answer.json"
    if golden_path.exists():
        task.golden = json.loads(golden_path.read_text())
    return task


def load_candidates(task: Task) -> list[Candidate]:
    manifest = task.dir / "candidates" / "manifest.json"
    if not manifest.exists():
        return []
    data = json.loads(manifest.read_text())
    return [
        Candidate(
            name=c["name"],
            label=c["label"],
            produced=c.get("produced"),
            solution=c.get("solution"),
            failure_class=c.get("failure_class"),
            description=c.get("description", ""),
        )
        for c in data.get("candidates", [])
    ]


def load_all() -> list[tuple[Task, list[Candidate]]]:
    validator = Draft202012Validator(load_schema())
    out = []
    for d in task_dirs():
        task = load_task(d, validator)
        out.append((task, load_candidates(task)))
    return out
