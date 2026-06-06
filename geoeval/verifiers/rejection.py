"""Grade whether a candidate correctly *refused* an unsolvable task.

The hardest GIS-AI gap (per GeoBenchX/GeoAnalystBench) is knowing when a task
cannot be answered — models tend to compute a plausible number for an
under-specified or impossible request instead of flagging it. The candidate's
decision is recorded as ``{"action": "refuse" | "attempt", "reason": ...}``.

- unsolvable task (``task.solvable == False``): refusing is correct.
- solvable task: attempting is correct (so we also penalize *false* refusals).
"""
from __future__ import annotations

from typing import Any

from ..models import Task, Verdict


def verify(task: Task, produced: Any, params: dict) -> Verdict:
    action = produced.get("action") if isinstance(produced, dict) else None
    if action not in ("refuse", "attempt"):
        return Verdict(False, 0.0, f"candidate gave no clear refuse/attempt decision (got {action!r})",
                       "refuse" if not task.solvable else "attempt", action)

    should_refuse = not task.solvable
    refused = action == "refuse"
    ok = refused == should_refuse

    if ok and should_refuse:
        detail = f"correctly refused unsolvable task ({task.rejection_reason})"
    elif ok:
        detail = "correctly attempted a solvable task"
    elif should_refuse:
        detail = f"ATTEMPTED an unsolvable task (should refuse: {task.rejection_reason})"
    else:
        detail = "refused a solvable task (false refusal)"

    return Verdict(ok, 1.0 if ok else 0.0, detail,
                   "refuse" if should_refuse else "attempt", action)
