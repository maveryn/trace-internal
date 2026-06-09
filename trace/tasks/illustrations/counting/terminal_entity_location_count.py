"""Merged transit-terminal entity/location counting task."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple, Type

from ....core.task_group_config import get_task_group_defaults
from ...base import Task, TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ..shared.merged_counting_task import rewrite_branch_output, select_query_id
from ._terminal_boarding_area_luggage_branch import (
    TerminalBoardingAreaLuggageBranch,
    QUERY_IDS as LUGGAGE_QUERY_IDS,
)
from ._terminal_boarding_area_person_branch import (
    TerminalBoardingAreaPersonBranch,
    QUERY_IDS as BOARDING_AREA_QUERY_IDS,
)
from ._terminal_queue_person_branch import TerminalQueuePersonBranch, QUERY_IDS as QUEUE_QUERY_IDS


SCENE_ID = "transit_terminal"
PERSON_BOARDING_AREA_TASK_ID = "task_illustrations__transit_terminal__person_in_boarding_area_count"
LUGGAGE_BOARDING_AREA_TASK_ID = "task_illustrations__transit_terminal__luggage_in_boarding_area_count"
PERSON_QUEUE_TASK_ID = "task_illustrations__transit_terminal__person_in_queue_count"
QUERY_IDS: Tuple[str, ...] = (*BOARDING_AREA_QUERY_IDS, *LUGGAGE_QUERY_IDS, *QUEUE_QUERY_IDS)

_BRANCH_BY_QUERY: Dict[str, Type[Task]] = {
    **{query_id: TerminalBoardingAreaPersonBranch for query_id in BOARDING_AREA_QUERY_IDS},
    **{query_id: TerminalBoardingAreaLuggageBranch for query_id in LUGGAGE_QUERY_IDS},
    **{query_id: TerminalQueuePersonBranch for query_id in QUEUE_QUERY_IDS},
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
def _public_generation_defaults(public_task_id: str) -> Mapping[str, Any]:
    gen_defaults, _render_defaults, _prompt_defaults = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(public_task_id),
    )
    return gen_defaults


def _generate_public_terminal_count(
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
class IllustrationsCountingTransitPersonInBoardingAreaCountTask:
    """Count people in one labeled boarding area of a transit terminal."""

    task_id = PERSON_BOARDING_AREA_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _generate_public_terminal_count(
            public_task_id=self.task_id,
            branch_cls=TerminalBoardingAreaPersonBranch,
            query_ids=BOARDING_AREA_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


@register_task
class IllustrationsCountingTransitLuggageInBoardingAreaCountTask:
    """Count luggage of one type in one labeled boarding area."""

    task_id = LUGGAGE_BOARDING_AREA_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _generate_public_terminal_count(
            public_task_id=self.task_id,
            branch_cls=TerminalBoardingAreaLuggageBranch,
            query_ids=LUGGAGE_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


@register_task
class IllustrationsCountingTransitPersonInQueueCountTask:
    """Count people in one queue at a transit terminal service point."""

    task_id = PERSON_QUEUE_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _generate_public_terminal_count(
            public_task_id=self.task_id,
            branch_cls=TerminalQueuePersonBranch,
            query_ids=QUEUE_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = [
    "IllustrationsCountingTransitPersonInBoardingAreaCountTask",
    "IllustrationsCountingTransitLuggageInBoardingAreaCountTask",
    "IllustrationsCountingTransitPersonInQueueCountTask",
    "SCENE_ID",
    "QUERY_IDS",
]
