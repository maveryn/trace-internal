"""Count fixture elements with a target semantic color."""

from __future__ import annotations

from ...registry import register_task
from .shared.common import COLORED_TASK_ID
from .shared.task_base import BaseSurfaceFixtureCountTask


TASK_ID = COLORED_TASK_ID
SUPPORTED_QUERY_IDS = ("element_color_count",)


@register_task
class ThreeDSurfaceFixtureColoredElementCountTask(BaseSurfaceFixtureCountTask):
    """Count fixture elements with a target semantic color."""

    task_id = TASK_ID


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSurfaceFixtureColoredElementCountTask",
]

