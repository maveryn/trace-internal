"""Count dots-and-boxes moves that would complete a box."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import DotsAndBoxesObjectivePlan, make_count_objective_plan, run_dots_and_boxes_lifecycle
from .shared.defaults import DEFAULTS, SCENE_ID
from .shared.sampling import (
    resolve_dots_and_boxes_candidate_edge_count_axis,
    resolve_dots_and_boxes_target_axis,
)
from .shared.state import DotsAndBoxesBoardShapeAxis


TASK_ID = "task_games__dots_and_boxes__capture_move_count"
SUPPORTED_QUERY_IDS = ("capture_move_count", "highlighted_candidate_capture_count")
PROMPT_QUERY_KEY_BY_QUERY_ID = {
    "capture_move_count": "capture_move_count",
    "highlighted_candidate_capture_count": "highlighted_candidate_capture_count",
}
TARGET_SUPPORT_KEY_BY_QUERY_ID = {
    "capture_move_count": "capture_move_count_support",
    "highlighted_candidate_capture_count": "highlighted_candidate_capture_count_support",
}
FALLBACK_SUPPORT_BY_QUERY_ID = {
    "capture_move_count": DEFAULTS.capture_move_count_support,
    "highlighted_candidate_capture_count": DEFAULTS.highlighted_candidate_capture_count_support,
}
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _fallback_support(query_id: str) -> Sequence[int]:
    return FALLBACK_SUPPORT_BY_QUERY_ID[str(query_id)]


def _prepare_capture_move_objective(
    instance_seed: int,
    params: Mapping[str, Any],
    query_probabilities: Mapping[str, float],
    query_id: str,
    board_shape: DotsAndBoxesBoardShapeAxis,
) -> DotsAndBoxesObjectivePlan:
    """Bind the selected capture-count query to neutral edge-completion rules."""

    del query_probabilities
    selected_query = str(query_id)
    candidate_edge_count_axis = resolve_dots_and_boxes_candidate_edge_count_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
    )
    target_axis = resolve_dots_and_boxes_target_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(TARGET_SUPPORT_KEY_BY_QUERY_ID[selected_query]),
        fallback_support=_fallback_support(selected_query),
        namespace=f"{selected_query}.target_answer",
    )
    count_mode = "capture_move" if selected_query == "capture_move_count" else "highlighted_candidate_capture"
    return make_count_objective_plan(
        prompt_query_key=str(PROMPT_QUERY_KEY_BY_QUERY_ID[selected_query]),
        annotation_example_shape="point_pair_set",
        annotation_kind="edge_point_pair",
        annotation_entity_attr="counted_edge_ids",
        target_axis=target_axis,
        board_shape=board_shape,
        count_mode=count_mode,
        attempt_namespace=f"games.dots_and_boxes.{selected_query}",
        candidate_edge_count_axis=candidate_edge_count_axis,
    )


@register_task
class GamesDotsAndBoxesCaptureMoveCountTask:
    """Count missing-edge moves, or highlighted candidate moves, that complete boxes."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_dots_and_boxes_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_capture_move_objective,
        )


__all__ = ["GamesDotsAndBoxesCaptureMoveCountTask"]
