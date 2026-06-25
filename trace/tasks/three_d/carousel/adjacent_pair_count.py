"""Count ordered adjacent object pairs on one carousel belt."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import run_conveyor_ordered_pair_count_lifecycle
from .shared.sampling import PREDICATE_ORDERED_COLOR_PAIR, PREDICATE_ORDERED_OBJECT_PAIR


TASK_ID = "task_three_d__carousel__adjacent_pair_count"
COLOR_ORDERED_PAIR_QUERY_ID = "color_ordered_pair_count"
OBJECT_ORDERED_PAIR_QUERY_ID = "object_ordered_pair_count"
SUPPORTED_QUERY_IDS = (
    COLOR_ORDERED_PAIR_QUERY_ID,
    OBJECT_ORDERED_PAIR_QUERY_ID,
)
PROMPT_QUERY_KEY_BY_BRANCH = {
    COLOR_ORDERED_PAIR_QUERY_ID: "color_ordered_pair_count",
    OBJECT_ORDERED_PAIR_QUERY_ID: "object_ordered_pair_count",
}
PREDICATE_KIND_BY_BRANCH = {
    COLOR_ORDERED_PAIR_QUERY_ID: PREDICATE_ORDERED_COLOR_PAIR,
    OBJECT_ORDERED_PAIR_QUERY_ID: PREDICATE_ORDERED_OBJECT_PAIR,
}


@register_task
class ThreeDCarouselAdjacentPairCountTask:
    """Count immediate ordered neighbor pairs along a selected carousel belt."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_conveyor_ordered_pair_count_lifecycle(
            public_name=TASK_ID,
            domain_name=self.domain,
            prompt_query_key_by_branch=PROMPT_QUERY_KEY_BY_BRANCH,
            predicate_kind_by_branch=PREDICATE_KIND_BY_BRANCH,
            supported_branches=SUPPORTED_QUERY_IDS,
            default_branch=COLOR_ORDERED_PAIR_QUERY_ID,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "COLOR_ORDERED_PAIR_QUERY_ID",
    "OBJECT_ORDERED_PAIR_QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDCarouselAdjacentPairCountTask",
]
