"""Count clustered objects whose type is one of two requested types."""

from __future__ import annotations

from ...registry import register_task
from .shared.predicate_counts import (
    ObjectClusterPredicateCountBase,
    TYPE_UNION_COUNT_TASK_ID,
    TYPE_UNION_QUERY_IDS,
)


TASK_ID = TYPE_UNION_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = TYPE_UNION_QUERY_IDS


@register_task
class ThreeDObjectClusterTypeUnionCountTask(ObjectClusterPredicateCountBase):
    """Count clustered objects whose type is one of two requested types."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterTypeUnionCountTask",
]

