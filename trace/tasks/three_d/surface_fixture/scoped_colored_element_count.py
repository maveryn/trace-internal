"""Count colored fixture elements inside one row or column."""

from __future__ import annotations

from ...registry import register_task
from .shared.common import SCOPED_COLORED_TASK_ID
from .shared.task_base import BaseSurfaceFixtureCountTask


TASK_ID = SCOPED_COLORED_TASK_ID
SUPPORTED_QUERY_IDS = ("scoped_element_color_count",)


@register_task
class ThreeDSurfaceFixtureScopedColoredElementCountTask(BaseSurfaceFixtureCountTask):
    """Count colored fixture elements inside one row or column."""

    task_id = TASK_ID


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSurfaceFixtureScopedColoredElementCountTask",
]

