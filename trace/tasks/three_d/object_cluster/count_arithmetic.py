"""Compute totals or absolute differences over two clustered object groups."""

from __future__ import annotations

from ...registry import register_task
from ._predicate_counts_impl import (
    COUNT_ARITHMETIC_QUERY_IDS,
    COUNT_ARITHMETIC_TASK_ID,
    ObjectClusterPredicateCountBase,
)


TASK_ID = COUNT_ARITHMETIC_TASK_ID
SUPPORTED_QUERY_IDS = COUNT_ARITHMETIC_QUERY_IDS


@register_task
class ThreeDObjectClusterCountArithmeticTask(ObjectClusterPredicateCountBase):
    """Compute totals or absolute differences over two clustered object groups."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    keyed_annotation = True


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterCountArithmeticTask",
]
