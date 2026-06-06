"""Grade a scalar answer (area, distance, count) against a golden value.

This is the verifier behind the CRS-trap task: a buffer area computed in degrees
returns a *number that executes cleanly* but is wrong by orders of magnitude, so
"did it run" is useless — only a tolerance check against the golden value catches it.
"""
from __future__ import annotations

from typing import Any

from ..models import Task, Verdict
from .base import as_number


def verify(task: Task, produced: Any, params: dict) -> Verdict:
    expected = as_number(task.golden)
    try:
        got = as_number(produced)
    except (ValueError, TypeError) as exc:
        return Verdict(False, 0.0, f"could not read a numeric value from candidate: {exc}",
                       expected, produced)

    diff = abs(got - expected)
    tol = params.get("tolerance")
    rel = params.get("rel_tolerance")

    if tol is not None:
        ok = diff <= tol
        basis = f"abs tol {tol}"
    elif rel is not None:
        ok = diff <= rel * abs(expected)
        basis = f"rel tol {rel} (= {rel * abs(expected):.6g})"
    else:
        ok = diff == 0
        basis = "exact"

    detail = f"|{got:.6g} - {expected:.6g}| = {diff:.6g} ({basis})"
    return Verdict(ok, 1.0 if ok else 0.0, detail, expected, got)
