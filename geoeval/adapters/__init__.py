"""Adapter registry."""
from __future__ import annotations

from .base import LLMClient, ReplayClient


def get_adapter(name: str, **kwargs) -> LLMClient:
    if name == "replay":
        return ReplayClient(**kwargs)
    if name == "vertex":
        from .vertex import VertexClient
        return VertexClient(**kwargs)
    raise KeyError(f"unknown adapter '{name}'. Known: replay, vertex")
