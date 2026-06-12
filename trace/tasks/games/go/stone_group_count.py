"""Count connected Go stone groups for one color."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.assembly import build_go_components
from .shared.mechanics import build_go_stone_group_count_state, color_name, coord_to_point_id
from .shared.sampling import (
    resolve_go_board_size_axis,
    resolve_go_scene_axes,
    resolve_go_target_axis,
)
from .shared.state import DEFAULTS, GoPlayerColorAxis, SCENE_ID


TASK_ID = "task_games__go__stone_group_count"
SUPPORTED_QUERY_IDS = ("black_stone_group_count", "white_stone_group_count")
PLAYER_COLOR_BY_QUERY_ID = {
    "black_stone_group_count": "black",
    "white_stone_group_count": "white",
}
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesGoStoneGroupCountTask:
    """Count separate connected black or white stone groups."""

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
            support_key="stone_group_count_support",
            fallback_support=DEFAULTS.stone_group_count_support,
            namespace=f"{str(query_id)}.target_answer",
        )
        player_color = str(PLAYER_COLOR_BY_QUERY_ID[str(query_id)])
        player_color_axis = GoPlayerColorAxis(
            player_color=player_color,
            probabilities={color: (1.0 if color == player_color else 0.0) for color in ("black", "white")},
        )

        board_state = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.go.{str(query_id)}.attempt.{int(attempt_index)}")
            try:
                board_state = build_go_stone_group_count_state(
                    rng=rng,
                    count_mode=str(query_id),
                    scene_variant=str(scene_axes.scene_variant),
                    target_answer=int(target_axis.value),
                    board_size=int(board_size_axis.value),
                )
            except (RuntimeError, ValueError):
                continue
            break
        if board_state is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid Go board after {max_attempts} attempts")

        annotation_ids = tuple(coord_to_point_id(coord) for coord in board_state.representative_coords)
        query_params = {
            "player_color": player_color,
            "target_answer": int(target_axis.value),
            "target_answer_support": [int(value) for value in target_axis.support],
            "target_answer_probabilities": dict(target_axis.probabilities),
        }
        execution_extra = {
            "target_group_color": str(color_name(board_state.target_color).lower()),
            "target_group_coords": [
                [[int(row), int(col)] for row, col in group]
                for group in board_state.target_group_coords
            ],
            "representative_coords": [[int(row), int(col)] for row, col in board_state.representative_coords],
            "representative_point_ids": [str(value) for value in annotation_ids],
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
            marked_group_coords=(),
            liberty_coords=(),
            annotation_point_ids=annotation_ids,
            prompt_query_key=str(query_id),
            stone_group_query=True,
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


__all__ = ["GamesGoStoneGroupCountTask"]
