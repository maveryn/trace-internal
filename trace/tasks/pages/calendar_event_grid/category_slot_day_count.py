"""Calendar-event-grid task for counting dates with a category in one slot."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    BaseCalendarEventGridTask,
    CATEGORY_SLOT_DAY_COUNT_QUERY_ID,
    CATEGORY_SLOT_DAY_COUNT_TASK_ID,
)


TASK_ID = CATEGORY_SLOT_DAY_COUNT_TASK_ID
QUERY_ID = CATEGORY_SLOT_DAY_COUNT_QUERY_ID


@register_task
class PagesCalendarEventGridCategorySlotDayCountTask(BaseCalendarEventGridTask):
    """Count dates whose named slot contains one requested category."""

    task_id = TASK_ID
    fixed_query_id = QUERY_ID
    default_dataset_enabled = True


__all__ = ["QUERY_ID", "TASK_ID", "PagesCalendarEventGridCategorySlotDayCountTask"]
