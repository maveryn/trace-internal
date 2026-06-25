"""Compute destination lane count after a counterfactual object transfer."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import run_conveyor_transfer_count_lifecycle
from .shared.sampling import PREDICATE_COLOR_TRANSFER, PREDICATE_OBJECT_TYPE_TRANSFER


TASK_ID = "task_three_d__conveyor__scope_count_after_transfer_value"
COLOR_TRANSFER_QUERY_ID = "color_transfer_total_count"
OBJECT_TRANSFER_QUERY_ID = "object_transfer_total_count"
SUPPORTED_QUERY_IDS = (
    COLOR_TRANSFER_QUERY_ID,
    OBJECT_TRANSFER_QUERY_ID,
)
PROMPT_QUERY_KEY_BY_BRANCH = {
    COLOR_TRANSFER_QUERY_ID: "color_transfer_total_count",
    OBJECT_TRANSFER_QUERY_ID: "object_transfer_total_count",
}
PREDICATE_KIND_BY_BRANCH = {
    COLOR_TRANSFER_QUERY_ID: PREDICATE_COLOR_TRANSFER,
    OBJECT_TRANSFER_QUERY_ID: PREDICATE_OBJECT_TYPE_TRANSFER,
}


@register_task
class ThreeDConveyorScopeCountAfterTransferValueTask:
    """Compute destination lane total after moving matching source-lane objects."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_conveyor_transfer_count_lifecycle(
            public_name=TASK_ID,
            domain_name=self.domain,
            prompt_query_key_by_branch=PROMPT_QUERY_KEY_BY_BRANCH,
            predicate_kind_by_branch=PREDICATE_KIND_BY_BRANCH,
            supported_branches=SUPPORTED_QUERY_IDS,
            default_branch=COLOR_TRANSFER_QUERY_ID,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "COLOR_TRANSFER_QUERY_ID",
    "OBJECT_TRANSFER_QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDConveyorScopeCountAfterTransferValueTask",
]
