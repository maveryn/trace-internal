"""Count clustered objects matching one attribute while excluding another."""

from __future__ import annotations

from ...registry import register_task
from .shared.predicate_counts import (
    MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_EXCLUSION_QUERY_IDS,
    ObjectClusterPredicateCountBase,
)


TASK_ID = MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = MULTI_ATTRIBUTE_EXCLUSION_QUERY_IDS


@register_task
class ThreeDObjectClusterMultiAttributeExclusionCountTask(ObjectClusterPredicateCountBase):
    """Count clustered objects matching one attribute while excluding another."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterMultiAttributeExclusionCountTask",
]

