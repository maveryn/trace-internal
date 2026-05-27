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


TASK_ID = "task_illustrations__transit_terminal__entity_location_count"
SCENE_ID = "transit_terminal"
QUERY_IDS: Tuple[str, ...] = (*BOARDING_AREA_QUERY_IDS, *LUGGAGE_QUERY_IDS, *QUEUE_QUERY_IDS)

_BRANCH_BY_QUERY: Dict[str, Type[Task]] = {
    **{query_id: TerminalBoardingAreaPersonBranch for query_id in BOARDING_AREA_QUERY_IDS},
    **{query_id: TerminalBoardingAreaLuggageBranch for query_id in LUGGAGE_QUERY_IDS},
    **{query_id: TerminalQueuePersonBranch for query_id in QUEUE_QUERY_IDS},
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class IllustrationsCountingTerminalEntityLocationCountTask:
    """Count people, luggage, or queue members in a transit terminal."""

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


__all__ = ["IllustrationsCountingTerminalEntityLocationCountTask", "TASK_ID", "SCENE_ID", "QUERY_IDS"]
