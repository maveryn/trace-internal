from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import ObjectiveRhythmPlan, run_rhythm_lifecycle
from .shared.sampling import resolve_rhythm_count_target_axis, resolve_selected_lane, sample_lane_hit_count_scene
from .shared.state import SCENE_ID, SCENE_NAMESPACE


TASK_ID = "task_games__rhythm__lane_hit_count"
PROMPT_QUERY_KEY = "lane_hit_count"

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_lane_hit_objective(
    instance_seed: int,
    params: Mapping[str, Any],
    _query_probabilities: Mapping[str, float],
    query_id: str,
) -> ObjectiveRhythmPlan:
    if str(query_id) != DEFAULT_QUERY_ID:
        raise ValueError(f"unsupported Rhythm lane-hit query: {query_id}")
    target_axis = resolve_rhythm_count_target_axis(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=f"{SCENE_NAMESPACE}.lane_hit.target_count",
    )
    return ObjectiveRhythmPlan(
        attempt_namespace=f"{SCENE_NAMESPACE}.lane_hit",
        prompt_query_key=PROMPT_QUERY_KEY,
        annotation_kind="note_bbox_set",
        query_params={"target_hit_count": int(target_axis.target_hit_count)},
        construct_attempt=lambda rng, axes: sample_lane_hit_count_scene(
            rng=rng,
            axes=axes,
            selected_lane=resolve_selected_lane(rng, lane_count=int(axes.lane_count), params=params),
            target_count=int(target_axis.target_hit_count),
        ),
    )


@register_task
class GamesRhythmLaneHitCountTask:
    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = (DEFAULT_QUERY_ID,)

    def generate(self, instance_seed: int, *, params: dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        return run_rhythm_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=self.supported_query_ids,
            default_query_id=DEFAULT_QUERY_ID,
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=dict(params or {}),
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_lane_hit_objective,
        )


__all__ = ["GamesRhythmLaneHitCountTask", "TASK_ID"]
