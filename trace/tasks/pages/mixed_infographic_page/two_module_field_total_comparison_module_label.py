"""Mixed-infographic two-module total comparison task."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    MIXED_INFOGRAPHIC_TWO_MODULE_TOTAL_COMPARISON_TASK_ID as TASK_ID,
    NATIVE_LAYOUT_MODES,
    PagesMixedInfographicTwoModuleFieldTotalComparisonModuleLabelTask as _RuntimeTask,
    SCENE_VARIANTS,
    TWO_MODULE_TOTAL_COMPARISON_QUERY_ID as QUERY_ID,
)


@register_task
class PagesMixedInfographicTwoModuleFieldTotalComparisonModuleLabelTask(_RuntimeTask):
    """Compare totals for one additive field across two modules."""


__all__ = [
    "NATIVE_LAYOUT_MODES",
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesMixedInfographicTwoModuleFieldTotalComparisonModuleLabelTask",
]

