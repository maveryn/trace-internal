"""Count fixture elements with a target state."""

from __future__ import annotations

from ...registry import register_task
from .shared.common import STATE_TASK_ID
from .shared.task_base import BaseSurfaceFixtureCountTask


TASK_ID = STATE_TASK_ID
SUPPORTED_QUERY_IDS = ("element_state_count",)


@register_task
class ThreeDSurfaceFixtureStateElementCountTask(BaseSurfaceFixtureCountTask):
    """Count fixture elements with a target state."""

    task_id = TASK_ID


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSurfaceFixtureStateElementCountTask",
]

