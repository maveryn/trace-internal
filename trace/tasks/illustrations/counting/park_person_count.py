"""Merged park/playground person counting task."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple, Type

from ....core.task_group_config import get_task_group_defaults
from ...base import Task, TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ..shared.merged_counting_task import rewrite_branch_output, select_query_id
from ._park_person_activity_branch import ParkPersonActivityBranch, QUERY_IDS as ACTIVITY_QUERY_IDS
from ._park_person_zone_branch import ParkPersonZoneBranch, QUERY_IDS as ZONE_QUERY_IDS
from ._park_person_equipment_use_branch import (
    ParkPersonEquipmentUseBranch,
    QUERY_IDS as EQUIPMENT_USAGE_QUERY_IDS,
)


TASK_ID = "task_illustrations__park_playground__person_count"
SCENE_ID = "park_playground"
QUERY_IDS: Tuple[str, ...] = (*ACTIVITY_QUERY_IDS, *ZONE_QUERY_IDS, *EQUIPMENT_USAGE_QUERY_IDS)

_BRANCH_BY_QUERY: Dict[str, Type[Task]] = {
    **{query_id: ParkPersonActivityBranch for query_id in ACTIVITY_QUERY_IDS},
    **{query_id: ParkPersonZoneBranch for query_id in ZONE_QUERY_IDS},
    **{query_id: ParkPersonEquipmentUseBranch for query_id in EQUIPMENT_USAGE_QUERY_IDS},
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class IllustrationsCountingParkPersonCountTask:
    """Count people by activity, park zone, or equipment use."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = select_query_id(
            task_id=TASK_ID,
            params=params,
            defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            fallback=QUERY_IDS,
        )
        branch_cls = _BRANCH_BY_QUERY[str(query_id)]
        branch_params = dict(params)
        branch_params["query_id"] = str(query_id)
        output = branch_cls().generate(int(instance_seed), params=branch_params, max_attempts=int(max_attempts))
        return rewrite_branch_output(
            output,
            public_task_id=TASK_ID,
            branch_id=str(branch_cls.branch_id),
            query_probabilities=query_probabilities,
        )


__all__ = ["IllustrationsCountingParkPersonCountTask", "TASK_ID", "SCENE_ID", "QUERY_IDS"]
