"""Timeline task for computing the day gap between two milestone events."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from . import _lifecycle


TASK_ID = "task_pages__timeline__event_date_gap_value"
PROMPT_QUERY_KEY = "event_date_gap_value"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)


@register_task
class PagesTimelineEventDateGapValueTask:
    """Compute the calendar-day gap between two named milestone events."""

    task_id = TASK_ID
    domain = _lifecycle.DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Mapping[str, Any], max_attempts: int):
        del max_attempts
        selected_branch, branch_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
        )
        return _lifecycle.build_timeline_response(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_branch=str(selected_branch),
            branch_probabilities=branch_probabilities,
            program_mode=_lifecycle.DAY_DELTA_MODE,
            interval_relation="date_gap",
            prompt_query_key=PROMPT_QUERY_KEY,
            source_query_name=PROMPT_QUERY_KEY,
        )


__all__ = [
    "PROMPT_QUERY_KEY",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "PagesTimelineEventDateGapValueTask",
]
