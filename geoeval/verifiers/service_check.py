"""Grade a GeoServer OGC service response.

The runner produces a small summary dict from a WFS GetFeature / WMS GetMap call,
e.g. ``{"feature_count": 42}`` or ``{"non_blank": true}``; this verifier checks it
against the golden expectation. Offline, the summary is the recorded candidate output.
"""
from __future__ import annotations

from typing import Any

from ..models import Task, Verdict


def verify(task: Task, produced: Any, params: dict) -> Verdict:
    gold = task.golden or {}
    if not isinstance(produced, dict):
        return Verdict(False, 0.0, "service response summary missing", gold, produced)

    if "feature_count" in gold:
        tol = int(params.get("tolerance", 0))
        exp = int(gold["feature_count"])
        got = int(produced.get("feature_count", -1))
        ok = abs(got - exp) <= tol
        return Verdict(ok, 1.0 if ok else 0.0,
                       f"WFS feature_count={got} (expected {exp}±{tol})", exp, got)

    if gold.get("non_blank"):
        got = bool(produced.get("non_blank"))
        return Verdict(got, 1.0 if got else 0.0,
                       f"WMS tile non_blank={got}", True, got)

    return Verdict(False, 0.0, "no recognized expectation in golden answer", gold, produced)
