"""Every task validates against the schema and is internally consistent."""
from __future__ import annotations

import json

import pytest

from geoeval import loader

TASK_DIRS = loader.task_dirs()


def test_there_are_tasks():
    assert TASK_DIRS, "no tasks found under tasks/"


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_task_validates(task_dir):
    data = json.loads((task_dir / "task.json").read_text())
    loader.validate_task_dict(data)  # raises on failure
    assert data["id"] == task_dir.name, "task id must match its directory name"


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_unsolvable_tasks_have_reason(task_dir):
    data = json.loads((task_dir / "task.json").read_text())
    if not data["solvable"]:
        assert data.get("rejection_reason"), "unsolvable tasks must declare a rejection_reason"


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_each_task_has_a_correct_and_wrong_candidate(task_dir):
    task = loader.load_task(task_dir)
    cands = loader.load_candidates(task)
    labels = {c.label for c in cands}
    assert "correct" in labels, f"{task.id}: needs a correct candidate"
    assert "wrong" in labels, f"{task.id}: needs at least one wrong candidate"
