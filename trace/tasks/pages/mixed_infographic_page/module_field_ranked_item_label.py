"""Mixed-infographic module field ranked item task."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    FIELD_RANKED_QUERY_ID as QUERY_ID,
    MIXED_INFOGRAPHIC_FIELD_RANKED_TASK_ID as TASK_ID,
    NATIVE_LAYOUT_MODES,
    PagesMixedInfographicModuleFieldRankedItemLabelTask as _RuntimeTask,
    SCENE_VARIANTS,
)


@register_task
class PagesMixedInfographicModuleFieldRankedItemLabelTask(_RuntimeTask):
    """Find the item at a requested numeric rank in one module field."""


__all__ = [
    "NATIVE_LAYOUT_MODES",
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesMixedInfographicModuleFieldRankedItemLabelTask",
]

