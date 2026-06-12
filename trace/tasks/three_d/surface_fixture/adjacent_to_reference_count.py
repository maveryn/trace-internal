"""Count fixture elements sharing an edge with a reference element."""

from __future__ import annotations

from ...registry import register_task
from .shared.common import ADJACENT_TASK_ID
from .shared.task_base import BaseSurfaceFixtureCountTask


TASK_ID = ADJACENT_TASK_ID
SUPPORTED_QUERY_IDS = ("adjacent_to_reference_count",)


@register_task
class ThreeDSurfaceFixtureAdjacentToReferenceCountTask(BaseSurfaceFixtureCountTask):
    """Count fixture elements sharing an edge with a uniquely colored reference element."""

    task_id = TASK_ID


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSurfaceFixtureAdjacentToReferenceCountTask",
]

