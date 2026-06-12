"""Count clustered objects matching a type/color inclusive OR."""

from __future__ import annotations

from ...registry import register_task
from .shared.predicate_counts import (
    MULTI_ATTRIBUTE_OR_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_OR_QUERY_IDS,
    ObjectClusterPredicateCountBase,
)


TASK_ID = MULTI_ATTRIBUTE_OR_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = MULTI_ATTRIBUTE_OR_QUERY_IDS


@register_task
class ThreeDObjectClusterMultiAttributeOrCountTask(ObjectClusterPredicateCountBase):
    """Count clustered objects matching a type/color inclusive OR."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterMultiAttributeOrCountTask",
]

