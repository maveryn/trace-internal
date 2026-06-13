"""Count moving objects that intersect the marked crossing route."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.games.crossing._lifecycle import (
    CrossingCountObjectiveSpec,
    CrossingObjectivePlan,
    prepare_count_objective_from_spec,
    run_crossing_lifecycle,
)
from trace.tasks.games.crossing.shared.defaults import SCENE_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults


TASK_ID = "task_games__crossing__moving_object_count"
QUERY_ID = "moving_object_count"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
MOVING_OBJECT_COUNT_SUPPORT: Tuple[int, ...] = (1, 2, 3, 4, 5)
COUNT_OBJECTIVE_SPEC = CrossingCountObjectiveSpec(
    prompt_query_key=PROMPT_QUERY_KEY,
    count_mode="route_intersections",
    support_key="moving_object_count_support",
    fallback_support=MOVING_OBJECT_COUNT_SUPPORT,
    include_route_in_description=True,
    include_motion_rule_text=True,
    min_lane_count_answer_padding=2,
    min_row_count_from_answer=True,
)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_route_intersection_count_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query_id: str,
    _query_probabilities: Mapping[str, float],
) -> CrossingObjectivePlan:
    """Bind route-intersection count semantics and exact-answer construction."""

    return prepare_count_objective_from_spec(
        task_id=TASK_ID,
        spec=COUNT_OBJECTIVE_SPEC,
        instance_seed=int(instance_seed),
        task_params=task_params,
        selected_query_id=str(selected_query_id),
        gen_defaults=_GEN_DEFAULTS,
    )


@register_task
class GamesCrossingMovingObjectCountTask:
    """Count moving objects that collide with the marked route."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate an exact marked-route collision count."""

        return run_crossing_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_route_intersection_count_objective,
        )


__all__ = ["GamesCrossingMovingObjectCountTask"]
