"""Mixed-infographic page field extremum module task."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    NATIVE_LAYOUT_MODES,
    PAGE_FIELD_EXTREMUM_QUERY_ID as QUERY_ID,
    MIXED_INFOGRAPHIC_PAGE_FIELD_EXTREMUM_TASK_ID as TASK_ID,
    PagesMixedInfographicPageFieldExtremumModuleLabelTask as _RuntimeTask,
    SCENE_VARIANTS,
)


@register_task
class PagesMixedInfographicPageFieldExtremumModuleLabelTask(_RuntimeTask):
    """Find the module with the highest or lowest value for a shared field."""


__all__ = [
    "NATIVE_LAYOUT_MODES",
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesMixedInfographicPageFieldExtremumModuleLabelTask",
]

