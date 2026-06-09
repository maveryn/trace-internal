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


SCENE_ID = "park_playground"
ACTIVITY_TASK_ID = "task_illustrations__park_playground__activity_person_count"
AREA_TASK_ID = "task_illustrations__park_playground__area_person_count"
EQUIPMENT_USE_TASK_ID = "task_illustrations__park_playground__equipment_use_person_count"
QUERY_IDS: Tuple[str, ...] = (*ACTIVITY_QUERY_IDS, *ZONE_QUERY_IDS, *EQUIPMENT_USAGE_QUERY_IDS)

_BRANCH_BY_QUERY: Dict[str, Type[Task]] = {
    **{query_id: ParkPersonActivityBranch for query_id in ACTIVITY_QUERY_IDS},
    **{query_id: ParkPersonZoneBranch for query_id in ZONE_QUERY_IDS},
    **{query_id: ParkPersonEquipmentUseBranch for query_id in EQUIPMENT_USAGE_QUERY_IDS},
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
def _public_generation_defaults(public_task_id: str) -> Mapping[str, Any]:
    gen_defaults, _render_defaults, _prompt_defaults = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(public_task_id),
    )
    return gen_defaults


def _generate_public_person_count(
    *,
    public_task_id: str,
    branch_cls: Type[Task],
    query_ids: Tuple[str, ...],
    instance_seed: int,
    params: Dict[str, Any],
    max_attempts: int,
) -> TaskOutput:
    query_id, query_probabilities = select_query_id(
        task_id=str(public_task_id),
        params=params,
        defaults=_public_generation_defaults(str(public_task_id)),
        instance_seed=int(instance_seed),
        fallback=query_ids,
    )
    branch_params = dict(params)
    branch_params["query_id"] = str(query_id)
    branch_params["query_id_support"] = [str(value) for value in query_ids]
    output = branch_cls().generate(int(instance_seed), params=branch_params, max_attempts=int(max_attempts))
    return rewrite_branch_output(
        output,
        public_task_id=str(public_task_id),
        branch_id=str(branch_cls.branch_id),
        query_probabilities=query_probabilities,
    )

@register_task
class IllustrationsCountingParkActivityPersonCountTask:
    """Count people performing one activity in a park/playground scene."""

    task_id = ACTIVITY_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _generate_public_person_count(
            public_task_id=self.task_id,
            branch_cls=ParkPersonActivityBranch,
            query_ids=ACTIVITY_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


@register_task
class IllustrationsCountingParkAreaPersonCountTask:
    """Count people in one park/playground area."""

    task_id = AREA_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _generate_public_person_count(
            public_task_id=self.task_id,
            branch_cls=ParkPersonZoneBranch,
            query_ids=ZONE_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


@register_task
class IllustrationsCountingParkEquipmentUsePersonCountTask:
    """Count people using one playground equipment type."""

    task_id = EQUIPMENT_USE_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _generate_public_person_count(
            public_task_id=self.task_id,
            branch_cls=ParkPersonEquipmentUseBranch,
            query_ids=EQUIPMENT_USAGE_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = [
    "IllustrationsCountingParkActivityPersonCountTask",
    "IllustrationsCountingParkAreaPersonCountTask",
    "IllustrationsCountingParkEquipmentUsePersonCountTask",
    "SCENE_ID",
    "QUERY_IDS",
]
