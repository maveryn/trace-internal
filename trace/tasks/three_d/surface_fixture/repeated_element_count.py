"""Count all repeated elements on a projected fixture surface."""

from __future__ import annotations

from ...registry import register_task
from .shared.common import REPEATED_TASK_ID
from .shared.task_base import BaseSurfaceFixtureCountTask


TASK_ID = REPEATED_TASK_ID
SUPPORTED_QUERY_IDS = ("element_type_count",)


@register_task
class ThreeDSurfaceFixtureRepeatedElementCountTask(BaseSurfaceFixtureCountTask):
    """Count all repeated elements on a projected fixture surface."""

    task_id = TASK_ID


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSurfaceFixtureRepeatedElementCountTask",
]

