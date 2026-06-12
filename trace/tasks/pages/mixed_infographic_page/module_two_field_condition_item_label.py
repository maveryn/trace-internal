"""Mixed-infographic two-field condition item task."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    MIXED_INFOGRAPHIC_TWO_FIELD_CONDITION_TASK_ID as TASK_ID,
    NATIVE_LAYOUT_MODES,
    PagesMixedInfographicModuleTwoFieldConditionItemLabelTask as _RuntimeTask,
    SCENE_VARIANTS,
    TWO_FIELD_CONDITION_QUERY_ID as QUERY_ID,
)


@register_task
class PagesMixedInfographicModuleTwoFieldConditionItemLabelTask(_RuntimeTask):
    """Find the item satisfying one numeric and one categorical condition."""


__all__ = [
    "NATIVE_LAYOUT_MODES",
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesMixedInfographicModuleTwoFieldConditionItemLabelTask",
]

