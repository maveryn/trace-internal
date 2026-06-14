"""Count clustered objects selected by object-type frequency."""

from __future__ import annotations

from ...registry import register_task
from ._predicate_counts_impl import (
    ObjectClusterPredicateCountBase,
    TYPE_FREQUENCY_COUNT_TASK_ID,
    TYPE_FREQUENCY_QUERY_IDS,
)


TASK_ID = TYPE_FREQUENCY_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = TYPE_FREQUENCY_QUERY_IDS


@register_task
class ThreeDObjectClusterTypeFrequencyCountTask(ObjectClusterPredicateCountBase):
    """Count clustered objects selected by object-type frequency."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterTypeFrequencyCountTask",
]
