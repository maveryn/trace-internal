"""Backward-compatible shim for value-query helpers."""

from ..geometry.shared.value_queries import QueryOutcome, run_value_query, supported_value_query_types

__all__ = ["QueryOutcome", "run_value_query", "supported_value_query_types"]
