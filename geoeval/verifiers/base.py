"""Verifier contract.

A verifier is a pure function::

    verify(task: Task, produced: Any, params: dict) -> Verdict

It compares a candidate's ``produced`` output against the task's golden answer
(``task.golden``) and/or its declared expectations (``task.expected``,
``task.solvable``). Verifiers must be deterministic and must not touch the
network or the database — the *runner* is responsible for producing ``produced``
(by reading a recorded artifact offline, or executing a solution live). This
separation keeps verifiers unit-testable without the Docker stack.
"""
from __future__ import annotations

from typing import Any, Callable

from ..models import Task, Verdict

Verifier = Callable[[Task, Any, dict], Verdict]


def as_number(value: Any) -> float:
    """Coerce a numeric answer that may be a bare number or ``{"value": n}``."""
    if isinstance(value, dict):
        value = value.get("value")
    if value is None:
        raise ValueError("expected a numeric value, got None")
    return float(value)
