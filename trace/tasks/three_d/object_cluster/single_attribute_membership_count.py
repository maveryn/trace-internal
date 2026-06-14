"""Count objects of one type in a dense synthetic 3D object cluster."""

from __future__ import annotations

from ...registry import register_task
from ._instance_count_impl import ObjectClusterSingleAttributeMembershipCountBase, TASK_ID


QUERY_ID = "single"
PROMPT_QUERY_KEY = "type_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


@register_task
class ThreeDObjectClusterSingleAttributeMembershipCountTask(ObjectClusterSingleAttributeMembershipCountBase):
    """Count visible instances of one object type in a dense object cluster."""

    supported_query_ids = SUPPORTED_QUERY_IDS
    prompt_query_key = PROMPT_QUERY_KEY


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterSingleAttributeMembershipCountTask",
]
