"""Unit tests for each verifier, plus the offline invariant over the real task
library: every `correct` candidate passes and every `wrong` candidate fails.
"""
from __future__ import annotations

import pytest

from geoeval import loader, runner
from geoeval.models import Task
from geoeval.verifiers import crs_check, numeric, rejection, sql_result, vector_equiv


def _task(**kw) -> Task:
    base = dict(id="t", title="t", category="crs", difficulty="easy", prompt="p",
                solvable=True, verifier={"name": "numeric"})
    base.update(kw)
    return Task(**base)


# ----------------------------- numeric ----------------------------- #
def test_numeric_within_rel_tolerance():
    t = _task(golden={"value": 9_424_778, "unit": "m2"})
    assert numeric.verify(t, {"value": 9_390_000}, {"rel_tolerance": 0.02}).passed
    assert not numeric.verify(t, {"value": 0.00076}, {"rel_tolerance": 0.02}).passed


def test_numeric_abs_tolerance():
    t = _task(golden=100.0)
    assert numeric.verify(t, 101.0, {"tolerance": 2}).passed
    assert not numeric.verify(t, 105.0, {"tolerance": 2}).passed


# --------------------------- vector_equiv -------------------------- #
def _fc(epsg, feats):
    return {"type": "FeatureCollection", "crs_epsg": epsg, "features": feats}


def _pt(i, xy, **props):
    return {"type": "Feature", "properties": {"id": i, **props},
            "geometry": {"type": "Point", "coordinates": list(xy)}}


def test_vector_equiv_detects_unreprojected_coords():
    golden = _fc(32737, [_pt(1, (256309.5, 9857311.11))])
    t = _task(category="crs", golden=golden, verifier={"name": "vector_equiv"})
    # same CRS label but coords still in degrees -> fail (the relabel trap)
    relabeled = _fc(32737, [_pt(1, (36.81, -1.29))])
    assert not vector_equiv.verify(t, relabeled, {"tolerance": 1.0}).passed
    # identical -> pass
    assert vector_equiv.verify(t, golden, {"tolerance": 1.0}).passed


def test_vector_equiv_checks_attributes():
    golden = _fc(4326, [_pt(1, (1, 1), zone_id=1), _pt(2, (2, 2), zone_id=0)])
    t = _task(category="topology", golden=golden, verifier={"name": "vector_equiv"})
    wrong = _fc(4326, [_pt(1, (1, 1), zone_id=1), _pt(2, (2, 2), zone_id=2)])
    assert not vector_equiv.verify(t, wrong, {"check_attrs": ["zone_id"]}).passed


# ----------------------------- crs_check --------------------------- #
def test_crs_check():
    t = _task(golden=_fc(32737, []), expected={"epsg": 32737})
    assert crs_check.verify(t, {"crs_epsg": 32737}, {}).passed
    assert not crs_check.verify(t, {"crs_epsg": 32736}, {}).passed


# ---------------------------- sql_result --------------------------- #
def test_sql_result_unordered_setequality():
    t = _task(category="performance", golden={"columns": ["id"], "rows": [[1], [3]]},
              verifier={"name": "sql_result"})
    assert sql_result.verify(t, {"columns": ["id"], "rows": [[3], [1]]}, {}).passed
    assert not sql_result.verify(t, {"columns": ["id"], "rows": [[1], [2], [3], [4]]}, {}).passed


# ----------------------------- rejection --------------------------- #
def test_rejection_unsolvable():
    t = _task(category="rejection", solvable=False, rejection_reason="partial",
              verifier={"name": "rejection"})
    assert rejection.verify(t, {"action": "refuse"}, {}).passed
    assert not rejection.verify(t, {"action": "attempt", "value": 12.7}, {}).passed


def test_rejection_solvable_false_refusal():
    t = _task(category="rejection", solvable=True, verifier={"name": "rejection"})
    assert rejection.verify(t, {"action": "attempt", "value": 1}, {}).passed
    assert not rejection.verify(t, {"action": "refuse"}, {}).passed


# --------------- the real invariant over the task library ---------- #
@pytest.mark.parametrize("task,cand",
                         [(t, c) for t, cands in loader.load_all() for c in cands],
                         ids=lambda x: getattr(x, "id", getattr(x, "name", "")))
def test_offline_invariant(task, cand):
    verdict = runner.run_offline(task, cand)
    if cand.label == "correct":
        assert verdict.passed, f"{task.id}/{cand.name} should PASS: {verdict.detail}"
    elif cand.label == "wrong":
        assert not verdict.passed, f"{task.id}/{cand.name} should FAIL but passed: {verdict.detail}"
