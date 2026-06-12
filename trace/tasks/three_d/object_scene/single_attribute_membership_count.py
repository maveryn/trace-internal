"""Public task module for object-scene single-attribute counting."""

from __future__ import annotations

from ...registry import register_task
from .shared.logical_predicate_count import (
    SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID,
    SINGLE_ATTRIBUTE_QUERY_IDS,
    _ThreeDSpatialLogicalPredicateCountBase,
)


TASK_ID = SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = SINGLE_ATTRIBUTE_QUERY_IDS


@register_task
class ThreeDObjectSceneSingleAttributeMembershipCountTask(_ThreeDSpatialLogicalPredicateCountBase):
    """Count objects matching one object/color attribute membership predicate."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDObjectSceneSingleAttributeMembershipCountTask"]
