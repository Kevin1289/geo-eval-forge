"""Check that a vector output declares the expected CRS (EPSG code).

Pairs with ``vector_equiv``: ``crs_check`` catches a candidate that targeted the
*wrong* CRS, while ``vector_equiv`` catches one that wrote the *right* CRS label
but never actually transformed the coordinates.
"""
from __future__ import annotations

from typing import Any

from ..models import Task, Verdict


def verify(task: Task, produced: Any, params: dict) -> Verdict:
    expected = (
        params.get("epsg")
        or (task.expected or {}).get("epsg")
        or (task.golden or {}).get("crs_epsg")
    )
    got = produced.get("crs_epsg") if isinstance(produced, dict) else None
    ok = got is not None and int(got) == int(expected)
    detail = f"output CRS EPSG:{got} (expected EPSG:{expected})"
    return Verdict(ok, 1.0 if ok else 0.0, detail, f"EPSG:{expected}", f"EPSG:{got}")
