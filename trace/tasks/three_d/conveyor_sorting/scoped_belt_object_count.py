"""Count objects matching one attribute on an inner or outer carousel belt."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import run_conveyor_sorting_lifecycle
from .shared.sampling import PREDICATE_COLOR, PREDICATE_OBJECT_TYPE


TASK_ID = "task_three_d__conveyor_sorting__scoped_belt_object_count"
OBJECT_TYPE_QUERY_ID = "object_type_belt_count"
COLOR_QUERY_ID = "color_belt_count"
SUPPORTED_QUERY_IDS = (OBJECT_TYPE_QUERY_ID, COLOR_QUERY_ID)
PROMPT_QUERY_KEY_BY_BRANCH = {
    OBJECT_TYPE_QUERY_ID: "object_type_belt_count",
    COLOR_QUERY_ID: "color_belt_count",
}
PREDICATE_KIND_BY_BRANCH = {
    OBJECT_TYPE_QUERY_ID: PREDICATE_OBJECT_TYPE,
    COLOR_QUERY_ID: PREDICATE_COLOR,
}


@register_task
class ThreeDConveyorSortingScopedBeltObjectCountTask:
    """Count objects matching one target attribute on a labeled carousel belt."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        clean_params = dict(params)
        output = run_conveyor_sorting_lifecycle(
            public_name=TASK_ID,
            domain_name=self.domain,
            prompt_query_key_by_branch=PROMPT_QUERY_KEY_BY_BRANCH,
            predicate_kind_by_branch=PREDICATE_KIND_BY_BRANCH,
            supported_branches=SUPPORTED_QUERY_IDS,
            default_branch=OBJECT_TYPE_QUERY_ID,
            instance_seed=int(instance_seed),
            params=clean_params,
            max_attempts=int(max_attempts),
        )
        return output


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDConveyorSortingScopedBeltObjectCountTask"]
