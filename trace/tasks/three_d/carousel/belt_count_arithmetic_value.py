"""Compute arithmetic over object counts on the inner and outer carousel belts."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import run_conveyor_count_arithmetic_lifecycle
from .shared.sampling import (
    ARITHMETIC_DIFFERENCE,
    ARITHMETIC_SUM,
    PREDICATE_COLOR_ARITHMETIC,
    PREDICATE_OBJECT_TYPE_ARITHMETIC,
)


TASK_ID = "task_three_d__carousel__belt_count_arithmetic_value"
COLOR_SUM_QUERY_ID = "color_count_sum"
COLOR_DIFFERENCE_QUERY_ID = "color_count_difference"
OBJECT_SUM_QUERY_ID = "object_count_sum"
OBJECT_DIFFERENCE_QUERY_ID = "object_count_difference"
SUPPORTED_QUERY_IDS = (
    COLOR_SUM_QUERY_ID,
    COLOR_DIFFERENCE_QUERY_ID,
    OBJECT_SUM_QUERY_ID,
    OBJECT_DIFFERENCE_QUERY_ID,
)
PROMPT_QUERY_KEY_BY_BRANCH = {
    COLOR_SUM_QUERY_ID: "color_count_sum",
    COLOR_DIFFERENCE_QUERY_ID: "color_count_difference",
    OBJECT_SUM_QUERY_ID: "object_count_sum",
    OBJECT_DIFFERENCE_QUERY_ID: "object_count_difference",
}
PREDICATE_KIND_BY_BRANCH = {
    COLOR_SUM_QUERY_ID: PREDICATE_COLOR_ARITHMETIC,
    COLOR_DIFFERENCE_QUERY_ID: PREDICATE_COLOR_ARITHMETIC,
    OBJECT_SUM_QUERY_ID: PREDICATE_OBJECT_TYPE_ARITHMETIC,
    OBJECT_DIFFERENCE_QUERY_ID: PREDICATE_OBJECT_TYPE_ARITHMETIC,
}
OPERATION_BY_BRANCH = {
    COLOR_SUM_QUERY_ID: ARITHMETIC_SUM,
    COLOR_DIFFERENCE_QUERY_ID: ARITHMETIC_DIFFERENCE,
    OBJECT_SUM_QUERY_ID: ARITHMETIC_SUM,
    OBJECT_DIFFERENCE_QUERY_ID: ARITHMETIC_DIFFERENCE,
}


@register_task
class ThreeDCarouselBeltCountArithmeticValueTask:
    """Compute sum or absolute difference of scoped belt object counts."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_conveyor_count_arithmetic_lifecycle(
            public_name=TASK_ID,
            domain_name=self.domain,
            prompt_query_key_by_branch=PROMPT_QUERY_KEY_BY_BRANCH,
            predicate_kind_by_branch=PREDICATE_KIND_BY_BRANCH,
            operation_by_branch=OPERATION_BY_BRANCH,
            supported_branches=SUPPORTED_QUERY_IDS,
            default_branch=COLOR_SUM_QUERY_ID,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "COLOR_DIFFERENCE_QUERY_ID",
    "COLOR_SUM_QUERY_ID",
    "OBJECT_DIFFERENCE_QUERY_ID",
    "OBJECT_SUM_QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDCarouselBeltCountArithmeticValueTask",
]
