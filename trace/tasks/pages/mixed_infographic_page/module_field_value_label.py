"""Mixed-infographic module field value lookup task."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    MODULE_FIELD_VALUE_QUERY_ID as QUERY_ID,
    MIXED_INFOGRAPHIC_MODULE_FIELD_VALUE_TASK_ID as TASK_ID,
    NATIVE_LAYOUT_MODES,
    PagesMixedInfographicModuleFieldValueLabelTask as _RuntimeTask,
    SCENE_VARIANTS,
)


@register_task
class PagesMixedInfographicModuleFieldValueLabelTask(_RuntimeTask):
    """Read a visible value from one module on a dense mixed infographic page."""


__all__ = [
    "NATIVE_LAYOUT_MODES",
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesMixedInfographicModuleFieldValueLabelTask",
]

