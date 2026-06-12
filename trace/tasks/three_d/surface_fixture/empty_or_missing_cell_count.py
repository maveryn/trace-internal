"""Count missing cells in a visible fixture grid."""

from __future__ import annotations

from ...registry import register_task
from .shared.common import EMPTY_MISSING_TASK_ID
from .shared.task_base import BaseSurfaceFixtureCountTask


TASK_ID = EMPTY_MISSING_TASK_ID
SUPPORTED_QUERY_IDS = ("empty_or_missing_cell_count",)


@register_task
class ThreeDSurfaceFixtureEmptyOrMissingCellCountTask(BaseSurfaceFixtureCountTask):
    """Count missing cells in a visible fixture grid."""

    task_id = TASK_ID


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSurfaceFixtureEmptyOrMissingCellCountTask",
]

