"""Count objects between two marked anchors on one straight conveyor lane."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import run_conveyor_between_marked_items_count_lifecycle
from .shared.sampling import PREDICATE_BETWEEN_COLOR_ANCHORS, PREDICATE_BETWEEN_OBJECT_ANCHORS


TASK_ID = "task_three_d__conveyor__between_marked_items_count"
BETWEEN_COLOR_ANCHORS_QUERY_ID = "between_color_anchors_count"
BETWEEN_OBJECT_ANCHORS_QUERY_ID = "between_object_anchors_count"
SUPPORTED_QUERY_IDS = (
    BETWEEN_COLOR_ANCHORS_QUERY_ID,
    BETWEEN_OBJECT_ANCHORS_QUERY_ID,
)
PROMPT_QUERY_KEY_BY_BRANCH = {
    BETWEEN_COLOR_ANCHORS_QUERY_ID: "between_color_anchors_count",
    BETWEEN_OBJECT_ANCHORS_QUERY_ID: "between_object_anchors_count",
}
PREDICATE_KIND_BY_BRANCH = {
    BETWEEN_COLOR_ANCHORS_QUERY_ID: PREDICATE_BETWEEN_COLOR_ANCHORS,
    BETWEEN_OBJECT_ANCHORS_QUERY_ID: PREDICATE_BETWEEN_OBJECT_ANCHORS,
}


@register_task
class ThreeDConveyorBetweenMarkedItemsCountTask:
    """Count objects strictly between marked A/B anchors on one lane."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_conveyor_between_marked_items_count_lifecycle(
            public_name=TASK_ID,
            domain_name=self.domain,
            prompt_query_key_by_branch=PROMPT_QUERY_KEY_BY_BRANCH,
            predicate_kind_by_branch=PREDICATE_KIND_BY_BRANCH,
            supported_branches=SUPPORTED_QUERY_IDS,
            default_branch=BETWEEN_COLOR_ANCHORS_QUERY_ID,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "BETWEEN_COLOR_ANCHORS_QUERY_ID",
    "BETWEEN_OBJECT_ANCHORS_QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDConveyorBetweenMarkedItemsCountTask",
]
