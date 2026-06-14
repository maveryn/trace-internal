"""Count clustered objects whose type is one of two requested types."""

from __future__ import annotations

from ...registry import register_task
from ._predicate_counts_impl import (
    ObjectClusterPredicateCountBase,
    TYPE_UNION_COUNT_TASK_ID,
)


TASK_ID = TYPE_UNION_COUNT_TASK_ID
QUERY_ID = "single"
PROMPT_QUERY_KEY = "two_type_union_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


@register_task
class ThreeDObjectClusterTypeUnionCountTask(ObjectClusterPredicateCountBase):
    """Count clustered objects whose type is one of two requested types."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    prompt_query_key = PROMPT_QUERY_KEY


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterTypeUnionCountTask",
]
