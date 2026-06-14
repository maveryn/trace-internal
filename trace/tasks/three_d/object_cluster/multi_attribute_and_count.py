"""Count semantic color/object conjunctions in a dense 3D object cluster."""

from __future__ import annotations

from ...registry import register_task
from ._attribute_count_impl import ObjectClusterMultiAttributeAndCountBase, TASK_ID


QUERY_ID = "single"
PROMPT_QUERY_KEY = "type_and_color_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


@register_task
class ThreeDObjectClusterMultiAttributeAndCountTask(ObjectClusterMultiAttributeAndCountBase):
    """Count clustered objects matching both object type and semantic color."""

    supported_query_ids = SUPPORTED_QUERY_IDS
    prompt_query_key = PROMPT_QUERY_KEY


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterMultiAttributeAndCountTask",
]
