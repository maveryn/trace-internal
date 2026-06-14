"""Count connected Go stone groups for one color."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import make_go_stone_group_objective, run_go_lifecycle
from .shared.rules import GO_RULE_BLACK_GROUPS, GO_RULE_WHITE_GROUPS
from .shared.sampling import (
    resolve_go_target_axis,
)
from .shared.state import DEFAULTS, GoIntegerAxis, GoPlayerColorAxis, GoSceneAxes, SCENE_ID


TASK_ID = "task_games__go__stone_group_count"
SUPPORTED_QUERY_IDS = ("black_stone_group_count", "white_stone_group_count")
PLAYER_COLOR_BY_QUERY_ID = {
    "black_stone_group_count": "black",
    "white_stone_group_count": "white",
}
RULE_MODE_BY_QUERY_ID = {
    "black_stone_group_count": GO_RULE_BLACK_GROUPS,
    "white_stone_group_count": GO_RULE_WHITE_GROUPS,
}
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_stone_group_objective(
    instance_seed,
    task_params,
    query_id,
    _query_probabilities,
    scene_axes,
    board_size_axis,
):
    """Bind the selected stone-color query to a whole-board group count."""

    selected_query = str(query_id)
    player_color = str(PLAYER_COLOR_BY_QUERY_ID[selected_query])
    player_color_axis = GoPlayerColorAxis(
        player_color=player_color,
        probabilities={color: (1.0 if color == player_color else 0.0) for color in ("black", "white")},
    )
    target_axis = resolve_go_target_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="stone_group_count_support",
        fallback_support=DEFAULTS.stone_group_count_support,
        namespace=f"{selected_query}.target_answer",
    )

    return make_go_stone_group_objective(
        prompt_query_key=selected_query,
        rule_mode=str(RULE_MODE_BY_QUERY_ID[selected_query]),
        target_axis=target_axis,
        player_color_axis=player_color_axis,
        board_size_axis=board_size_axis,
        scene_axes=scene_axes,
        attempt_namespace=f"games.go.{selected_query}",
    )


@register_task
class GamesGoStoneGroupCountTask:
    """Count separate connected black or white stone groups."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_go_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_stone_group_objective,
        )


__all__ = ["GamesGoStoneGroupCountTask"]
