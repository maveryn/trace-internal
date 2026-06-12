"""Public task module for object-scene conjunction counting."""

from __future__ import annotations

from ...registry import register_task
from .shared.logical_predicate_count import (
    MULTI_ATTRIBUTE_AND_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_AND_QUERY_IDS,
    _ThreeDSpatialLogicalPredicateCountBase,
)


TASK_ID = MULTI_ATTRIBUTE_AND_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = MULTI_ATTRIBUTE_AND_QUERY_IDS


@register_task
class ThreeDObjectSceneMultiAttributeAndCountTask(_ThreeDSpatialLogicalPredicateCountBase):
    """Count objects matching a color and object-type conjunction."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDObjectSceneMultiAttributeAndCountTask"]
