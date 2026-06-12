"""Public task module for object-scene exclusion counting."""

from __future__ import annotations

from ...registry import register_task
from .shared.logical_predicate_count import (
    MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_EXCLUSION_QUERY_IDS,
    _ThreeDSpatialLogicalPredicateCountBase,
)


TASK_ID = MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = MULTI_ATTRIBUTE_EXCLUSION_QUERY_IDS


@register_task
class ThreeDObjectSceneMultiAttributeExclusionCountTask(_ThreeDSpatialLogicalPredicateCountBase):
    """Count objects matching an attribute while excluding another attribute."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDObjectSceneMultiAttributeExclusionCountTask"]
