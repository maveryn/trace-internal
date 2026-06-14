"""Count adjacent Hex cells around a labeled reference cell by state."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import HexAttemptResult, HexObjectivePlan, run_hex_lifecycle
from .shared.sampling import (
    resolve_hex_integer_axis,
    sample_neighbor_count_scene,
)
from .shared.state import SCENE_ID


TASK_ID = "task_games__hex__candidate_neighbor_count"
SUPPORTED_QUERY_IDS = ("red_neighbor_count", "blue_neighbor_count", "empty_neighbor_count")
QUERY_TO_TARGET_STATE = {
    "red_neighbor_count": "red",
    "blue_neighbor_count": "blue",
    "empty_neighbor_count": "empty",
}
NEIGHBOR_COUNT_SUPPORT = (0, 1, 2, 3, 4, 5, 6)

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_neighbor_count_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query_id: str,
    _branch_probabilities: Mapping[str, float],
    scene_axes,
) -> HexObjectivePlan:
    """Bind the selected neighbor-state query to a labeled-cell count."""

    del scene_axes
    target_state = str(QUERY_TO_TARGET_STATE[str(selected_query_id)])
    target_axis = resolve_hex_integer_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="neighbor_count_support",
        explicit_key="target_answer",
        fallback_support=NEIGHBOR_COUNT_SUPPORT,
        namespace=f"{selected_query_id}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    def construct_attempt(rng, axes) -> HexAttemptResult:
        sample = sample_neighbor_count_scene(
            rng=rng,
            scene_axes=axes,
            target_answer=int(target_axis.value),
            target_state=target_state,
        )
        return HexAttemptResult(
            sample=sample,
            annotation_coords=tuple(sample.annotation_coords),
            execution_extra={"target_state": target_state},
        )

    return HexObjectivePlan(
        prompt_query_key=str(selected_query_id),
        answer_gt=TypedValue(type="integer", value=int(target_axis.value)),
        target_axis=target_axis,
        candidate_count_axis=None,
        extra_query_params={"neighbor_target_state": target_state},
        attempt_namespace=f"games.hex.{selected_query_id}",
        construct_attempt=construct_attempt,
    )


@register_task
class GamesHexCandidateNeighborCountTask:
    """Count red, blue, or empty neighbors touching one labeled Hex cell."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_hex_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_neighbor_count_objective,
        )


__all__ = ["GamesHexCandidateNeighborCountTask"]
