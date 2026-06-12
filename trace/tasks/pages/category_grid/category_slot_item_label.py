"""Category-grid lookup task for an ordinal item label."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from .shared.runtime import (
    CATEGORY_SLOT_ITEM_QUERY_ID,
    CATEGORY_SLOT_ITEM_TASK_ID,
    SCENE_VARIANTS,
    generate_category_grid_output,
)


TASK_ID = CATEGORY_SLOT_ITEM_TASK_ID
QUERY_ID = CATEGORY_SLOT_ITEM_QUERY_ID


@register_task
class PagesCategoryGridCategorySlotItemLabelTask:
    """Read an ordinal item label from a category/subcategory grid."""

    task_id = TASK_ID
    domain = "pages"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return generate_category_grid_output(
            public_task_id=self.task_id,
            fixed_query_id=QUERY_ID,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "QUERY_ID",
    "SCENE_VARIANTS",
    "TASK_ID",
    "PagesCategoryGridCategorySlotItemLabelTask",
]

