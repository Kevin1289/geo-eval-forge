"""Verifier registry."""
from __future__ import annotations

from . import crs_check, numeric, rejection, service_check, sql_result, vector_equiv
from .base import Verifier

REGISTRY: dict[str, Verifier] = {
    "numeric": numeric.verify,
    "vector_equiv": vector_equiv.verify,
    "sql_result": sql_result.verify,
    "crs_check": crs_check.verify,
    "service_check": service_check.verify,
    "rejection": rejection.verify,
}


def get_verifier(name: str) -> Verifier:
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown verifier '{name}'. Known: {sorted(REGISTRY)}") from None
