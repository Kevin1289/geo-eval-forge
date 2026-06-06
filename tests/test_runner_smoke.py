"""Integration smoke tests for the LIVE path (requires the Docker stack).

Skipped by default (pyproject sets `-m 'not integration'`). Run inside the worker
with PostGIS up::

    docker compose up -d postgis
    docker compose run --rm worker pytest -m integration
"""
from __future__ import annotations

import pytest

from geoeval import loader, runner

# tasks whose correct candidate is an executable SQL solution
_LIVE_SQL = [
    (t, c)
    for t, cands in loader.load_all()
    for c in cands
    if c.label == "correct" and (c.solution or "").endswith(".sql")
]


@pytest.mark.integration
@pytest.mark.parametrize("task,cand", _LIVE_SQL, ids=lambda x: getattr(x, "id", getattr(x, "name", "")))
def test_live_correct_candidate_passes(task, cand):
    verdict = runner.run_live(task, cand)
    assert verdict.passed, f"{task.id}/{cand.name} failed live: {verdict.detail}"


@pytest.mark.integration
@pytest.mark.parametrize("task,cand",
                         [(t, c) for t, cands in loader.load_all() for c in cands
                          if c.label == "wrong" and (c.solution or "").endswith(".sql")],
                         ids=lambda x: getattr(x, "id", getattr(x, "name", "")))
def test_live_wrong_candidate_fails(task, cand):
    verdict = runner.run_live(task, cand)
    assert not verdict.passed, f"{task.id}/{cand.name} unexpectedly passed live: {verdict.detail}"
