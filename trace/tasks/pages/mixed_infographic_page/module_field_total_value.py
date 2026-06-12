"""Mixed-infographic module field total task."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    FIELD_TOTAL_QUERY_ID as QUERY_ID,
    MIXED_INFOGRAPHIC_FIELD_TOTAL_TASK_ID as TASK_ID,
    NATIVE_LAYOUT_MODES,
    PagesMixedInfographicModuleFieldTotalValueTask as _RuntimeTask,
    SCENE_VARIANTS,
)


@register_task
class PagesMixedInfographicModuleFieldTotalValueTask(_RuntimeTask):
    """Sum one additive numeric field across all items in one module."""


__all__ = [
    "NATIVE_LAYOUT_MODES",
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesMixedInfographicModuleFieldTotalValueTask",
]

