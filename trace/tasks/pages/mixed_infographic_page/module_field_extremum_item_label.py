"""Mixed-infographic module field extremum item task."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    FIELD_EXTREMUM_QUERY_ID as QUERY_ID,
    MIXED_INFOGRAPHIC_FIELD_EXTREMUM_TASK_ID as TASK_ID,
    NATIVE_LAYOUT_MODES,
    PagesMixedInfographicModuleFieldExtremumItemLabelTask as _RuntimeTask,
    SCENE_VARIANTS,
)


@register_task
class PagesMixedInfographicModuleFieldExtremumItemLabelTask(_RuntimeTask):
    """Find the item with the highest or lowest visible value in one module."""


__all__ = [
    "NATIVE_LAYOUT_MODES",
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesMixedInfographicModuleFieldExtremumItemLabelTask",
]

