"""Calendar-event-grid task for reading a category label from one date slot."""

from __future__ import annotations

from ...registry import register_task
from .shared.runtime import (
    BaseCalendarEventGridTask,
    DATE_SLOT_CATEGORY_QUERY_ID,
    DATE_SLOT_CATEGORY_TASK_ID,
)


TASK_ID = DATE_SLOT_CATEGORY_TASK_ID
QUERY_ID = DATE_SLOT_CATEGORY_QUERY_ID


@register_task
class PagesCalendarEventGridDateSlotCategoryLabelTask(BaseCalendarEventGridTask):
    """Return the category shown in a named slot on a named calendar date."""

    task_id = TASK_ID
    fixed_query_id = QUERY_ID
    default_dataset_enabled = True


__all__ = ["QUERY_ID", "TASK_ID", "PagesCalendarEventGridDateSlotCategoryLabelTask"]
