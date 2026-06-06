"""Core dataclasses shared across the harness."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Verdict:
    """The outcome of grading one produced output against a task's golden answer."""

    passed: bool
    score: float
    detail: str
    expected: Any = None
    got: Any = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Candidate:
    """A candidate solution to a task.

    ``produced`` is the recorded canonical output used for *offline* grading.
    ``solution`` is a path (relative to the task dir) to executable solution code
    (``.sql`` / ``.sh`` / ``.py``) used for *live* grading and for human display.
    """

    name: str
    label: str  # "correct" | "wrong"
    produced: Any = None
    solution: str | None = None
    failure_class: str | None = None
    description: str = ""


@dataclass
class Task:
    id: str
    title: str
    category: str
    difficulty: str
    prompt: str
    solvable: bool
    verifier: Any  # dict or list[dict] of {name, params}
    expected: dict = field(default_factory=dict)
    inputs: dict = field(default_factory=dict)
    rejection_reason: str | None = None
    dir: Path | None = None
    golden: Any = None  # loaded from golden/answer.json if present

    @property
    def verifier_specs(self) -> list[dict]:
        return self.verifier if isinstance(self.verifier, list) else [self.verifier]


@dataclass
class Result:
    task_id: str
    category: str
    candidate: str
    label: str
    failure_class: str | None
    verdict: Verdict

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict.to_dict()
        return d
