"""Mixed-infographic module condition count task."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    CONDITION_COUNT_QUERY_ID as QUERY_ID,
    MIXED_INFOGRAPHIC_CONDITION_COUNT_TASK_ID as TASK_ID,
    NATIVE_LAYOUT_MODES,
    PagesMixedInfographicModuleConditionItemCountTask as _RuntimeTask,
    SCENE_VARIANTS,
)


@register_task
class PagesMixedInfographicModuleConditionItemCountTask(_RuntimeTask):
    """Count items in one module whose field value satisfies a condition."""


__all__ = [
    "NATIVE_LAYOUT_MODES",
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesMixedInfographicModuleConditionItemCountTask",
]

