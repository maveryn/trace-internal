"""Count clustered objects matching one semantic color."""

from __future__ import annotations

from ...registry import register_task
from ._predicate_counts_impl import (
    COLOR_MEMBERSHIP_COUNT_TASK_ID,
    ObjectClusterPredicateCountBase,
)


TASK_ID = COLOR_MEMBERSHIP_COUNT_TASK_ID
QUERY_ID = "single"
PROMPT_QUERY_KEY = "color_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


@register_task
class ThreeDObjectClusterColorMembershipCountTask(ObjectClusterPredicateCountBase):
    """Count clustered objects matching one semantic color."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    prompt_query_key = PROMPT_QUERY_KEY


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterColorMembershipCountTask",
]
