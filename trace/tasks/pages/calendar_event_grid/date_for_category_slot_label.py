"""Calendar-event-grid task for finding the date of a category in one slot."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    BaseCalendarEventGridTask,
    DATE_FOR_CATEGORY_SLOT_QUERY_ID,
    DATE_FOR_CATEGORY_SLOT_TASK_ID,
)


TASK_ID = DATE_FOR_CATEGORY_SLOT_TASK_ID
QUERY_ID = DATE_FOR_CATEGORY_SLOT_QUERY_ID


@register_task
class PagesCalendarEventGridDateForCategorySlotLabelTask(BaseCalendarEventGridTask):
    """Return the date number whose named slot contains one requested category."""

    task_id = TASK_ID
    fixed_query_id = QUERY_ID
    default_dataset_enabled = True


__all__ = ["QUERY_ID", "TASK_ID", "PagesCalendarEventGridDateForCategorySlotLabelTask"]
