"""Count dots-and-boxes moves that would complete a box."""

from __future__ import annotations

from typing import Any, Dict, Sequence

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.assembly import build_dots_and_boxes_components
from .shared.mechanics import build_dots_and_boxes_count_board_state
from .shared.sampling import (
    resolve_dots_and_boxes_board_shape_axis,
    resolve_dots_and_boxes_candidate_edge_count_axis,
    resolve_dots_and_boxes_scene_axes,
    resolve_dots_and_boxes_target_axis,
)
from .shared.state import DEFAULTS, SCENE_ID


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


@register_task
class GamesDotsAndBoxesCaptureMoveCountTask:
    """Count missing-edge moves, or highlighted candidate moves, that complete boxes."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        scene_axes = resolve_dots_and_boxes_scene_axes(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
        board_shape = resolve_dots_and_boxes_board_shape_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
        candidate_edge_count_axis = resolve_dots_and_boxes_candidate_edge_count_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
        target_axis = resolve_dots_and_boxes_target_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=str(TARGET_SUPPORT_KEY_BY_QUERY_ID[str(query_id)]),
            fallback_support=_fallback_support(str(query_id)),
            namespace=f"{str(query_id)}.target_answer",
        )

        board_state = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.dots_and_boxes.{str(query_id)}.attempt.{int(attempt_index)}")
            try:
                board_state = build_dots_and_boxes_count_board_state(
                    rng=rng,
                    count_mode=str(query_id),
                    target_answer=int(target_axis.value),
                    box_rows=int(board_shape.box_rows),
                    box_cols=int(board_shape.box_cols),
                    candidate_edge_count=int(candidate_edge_count_axis.value),
                )
            except (RuntimeError, ValueError):
                continue
            break
        if board_state is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid dots-and-boxes scene after {max_attempts} attempts")

        query_params = {
            "target_answer": int(target_axis.value),
            "target_answer_support": [int(value) for value in target_axis.support],
            "target_answer_probabilities": dict(target_axis.probabilities),
        }
        components = build_dots_and_boxes_components(
            domain=self.domain,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
            scene_axes=scene_axes,
            board_shape=board_shape,
            board_state=board_state,
            answer_value=int(target_axis.value),
            annotation_kind="edge_point_pair",
            annotation_entity_ids=tuple(str(edge_id) for edge_id in board_state.counted_edge_ids),
            prompt_query_key=str(PROMPT_QUERY_KEY_BY_QUERY_ID[str(query_id)]),
            query_params=query_params,
            candidate_edge_count_axis=candidate_edge_count_axis,
        )
        return TaskOutput(
            prompt=str(components.prompt),
            prompt_variants=dict(components.prompt_variants),
            answer_gt=TypedValue(type=str(components.answer_type), value=components.answer_value),
            annotation_gt=TypedValue(type=str(components.annotation_type), value=components.annotation_value),
            image=components.image,
            image_id="img0",
            trace_payload=dict(components.trace_payload),
            task_versions=default_task_versions(),
            query_id=str(components.query_id),
            scene_id=SCENE_ID,
        )


__all__ = ["GamesDotsAndBoxesCaptureMoveCountTask"]
