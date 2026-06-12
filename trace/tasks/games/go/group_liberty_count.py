"""Count liberties or shared liberties of a marked Go group."""

from __future__ import annotations

from typing import Any, Dict, Sequence

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.assembly import build_go_components
from .shared.mechanics import build_go_board_state, color_name, coord_to_point_id, liberty_point_ids
from .shared.sampling import (
    resolve_go_board_size_axis,
    resolve_go_player_color_axis,
    resolve_go_scene_axes,
    resolve_go_target_axis,
)
from .shared.state import DEFAULTS, SCENE_ID


TASK_ID = "task_games__go__group_liberty_count"
SUPPORTED_QUERY_IDS = ("marked_group_liberty_count", "marked_group_shared_liberty_count")
PROMPT_QUERY_KEY_BY_QUERY_ID = {
    "marked_group_liberty_count": "marked_group_liberty_count",
    "marked_group_shared_liberty_count": "marked_group_shared_liberty_count",
}
TARGET_SUPPORT_KEY_BY_QUERY_ID = {
    "marked_group_liberty_count": "liberty_count_support",
    "marked_group_shared_liberty_count": "shared_liberty_count_support",
}
FALLBACK_SUPPORT_BY_QUERY_ID = {
    "marked_group_liberty_count": DEFAULTS.liberty_count_support,
    "marked_group_shared_liberty_count": DEFAULTS.shared_liberty_count_support,
}
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _fallback_support(query_id: str) -> Sequence[int]:
    return FALLBACK_SUPPORT_BY_QUERY_ID[str(query_id)]


@register_task
class GamesGoGroupLibertyCountTask:
    """Count marked-group liberties or liberties shared with opponent stones."""

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
        player_color_axis = resolve_go_player_color_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
        scene_axes = resolve_go_scene_axes(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
        board_size_axis = resolve_go_board_size_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
        target_axis = resolve_go_target_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=str(TARGET_SUPPORT_KEY_BY_QUERY_ID[str(query_id)]),
            fallback_support=_fallback_support(str(query_id)),
            namespace=f"{str(query_id)}.target_answer",
        )

        board_state = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.go.{str(query_id)}.attempt.{int(attempt_index)}")
            try:
                board_state = build_go_board_state(
                    rng=rng,
                    count_mode=str(query_id),
                    player_color=str(player_color_axis.player_color),
                    scene_variant=str(scene_axes.scene_variant),
                    target_answer=int(target_axis.value),
                    board_size=int(board_size_axis.value),
                )
            except (RuntimeError, ValueError):
                continue
            break
        if board_state is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid Go board after {max_attempts} attempts")

        if str(query_id) == "marked_group_liberty_count":
            annotation_ids = liberty_point_ids(board_state.liberty_coords)
        else:
            annotation_ids = liberty_point_ids(board_state.shared_liberty_coords)
        query_params = {
            "target_answer": int(target_axis.value),
            "target_answer_support": [int(value) for value in target_axis.support],
            "target_answer_probabilities": dict(target_axis.probabilities),
        }
        execution_extra = {
            "marked_group_color": str(color_name(board_state.marked_group_color).lower()),
            "marked_group_point_ids": [coord_to_point_id(coord) for coord in board_state.marked_group_coords],
            "adjacent_enemy_coords": [[int(row), int(col)] for row, col in board_state.adjacent_enemy_coords],
            "shared_liberty_coords": [[int(row), int(col)] for row, col in board_state.shared_liberty_coords],
        }
        components = build_go_components(
            domain=self.domain,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
            scene_axes=scene_axes,
            player_color_axis=player_color_axis,
            board_size_axis=board_size_axis,
            target_axis=target_axis,
            board=board_state.board,
            stone_specs=board_state.stone_specs,
            marked_group_coords=board_state.marked_group_coords,
            liberty_coords=board_state.liberty_coords,
            annotation_point_ids=annotation_ids,
            prompt_query_key=str(PROMPT_QUERY_KEY_BY_QUERY_ID[str(query_id)]),
            stone_group_query=False,
            query_params=query_params,
            execution_extra=execution_extra,
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


__all__ = ["GamesGoGroupLibertyCountTask"]
