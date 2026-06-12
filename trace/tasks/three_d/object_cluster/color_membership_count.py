"""Count clustered objects matching one semantic color."""

from __future__ import annotations

from ...registry import register_task
from .shared.predicate_counts import (
    COLOR_MEMBERSHIP_COUNT_TASK_ID,
    COLOR_MEMBERSHIP_QUERY_IDS,
    ObjectClusterPredicateCountBase,
)


TASK_ID = COLOR_MEMBERSHIP_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = COLOR_MEMBERSHIP_QUERY_IDS


@register_task
class ThreeDObjectClusterColorMembershipCountTask(ObjectClusterPredicateCountBase):
    """Count clustered objects matching one semantic color."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDObjectClusterColorMembershipCountTask",
]

