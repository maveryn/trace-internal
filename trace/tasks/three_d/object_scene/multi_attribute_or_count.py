"""Public task module for object-scene inclusive-or counting."""

from __future__ import annotations

from ...registry import register_task
from .shared.logical_predicate_count import (
    MULTI_ATTRIBUTE_OR_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_OR_QUERY_IDS,
    _ThreeDSpatialLogicalPredicateCountBase,
)


TASK_ID = MULTI_ATTRIBUTE_OR_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = MULTI_ATTRIBUTE_OR_QUERY_IDS


@register_task
class ThreeDObjectSceneMultiAttributeOrCountTask(_ThreeDSpatialLogicalPredicateCountBase):
    """Count objects matching a color or object-type inclusive OR."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDObjectSceneMultiAttributeOrCountTask"]
