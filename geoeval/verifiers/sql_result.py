"""Grade a tabular query result against a golden result set.

Canonical form::

    { "columns": ["id", "name"], "rows": [[1, "a"], [2, "b"]] }

Rows are compared as a multiset unless ``params.ordered`` is true. Floats are
rounded to ``params.round`` (default 6) decimals so that engine-level numeric
noise doesn't cause spurious failures.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from ..models import Task, Verdict


def _norm_row(row, ndigits: int) -> tuple:
    out = []
    for v in row:
        if isinstance(v, float):
            out.append(round(v, ndigits))
        else:
            out.append(v)
    return tuple(out)


def verify(task: Task, produced: Any, params: dict) -> Verdict:
    gold = task.golden or {}
    if not isinstance(produced, dict) or "rows" not in produced:
        return Verdict(False, 0.0, "candidate output has no 'rows'", gold.get("rows"), produced)

    ndigits = int(params.get("round", 6))
    ordered = bool(params.get("ordered", False))
    g_rows = [_norm_row(r, ndigits) for r in gold.get("rows", [])]
    p_rows = [_norm_row(r, ndigits) for r in produced.get("rows", [])]

    if ordered:
        ok = g_rows == p_rows
    else:
        ok = Counter(g_rows) == Counter(p_rows)

    if ok:
        return Verdict(True, 1.0, f"result set matches ({len(g_rows)} rows)", len(g_rows), len(p_rows))

    g_set, p_set = Counter(g_rows), Counter(p_rows)
    missing = list((g_set - p_set).elements())
    extra = list((p_set - g_set).elements())
    return Verdict(False, 0.0,
                   f"result set differs: {len(missing)} missing e.g. {missing[:3]}, "
                   f"{len(extra)} extra e.g. {extra[:3]}",
                   len(g_rows), len(p_rows))
