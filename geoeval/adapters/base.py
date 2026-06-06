"""LLM gateway interface.

The whole pipeline is offline-first: the ``replay`` adapter serves recorded
responses so judging/baselines run with no API key. Live adapters (``vertex``)
implement the same ``complete`` method. The optional ``key`` lets the replay
adapter look a response up by item id; live adapters ignore it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    name: str

    def complete(self, prompt: str, *, system: str | None = None, key: str | None = None) -> str:
        ...


class ReplayClient:
    """Serves recorded responses from a JSONL file keyed by ``key_field``."""

    name = "replay"

    def __init__(self, path: str | Path, key_field: str = "id", response_field: str = "replay_response"):
        self._responses: dict[str, str] = {}
        p = Path(path)
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if response_field in row:
                    self._responses[str(row[key_field])] = row[response_field]

    def complete(self, prompt: str, *, system: str | None = None, key: str | None = None) -> str:
        if key is None or key not in self._responses:
            raise KeyError(f"replay adapter has no recorded response for key={key!r}")
        return self._responses[key]
