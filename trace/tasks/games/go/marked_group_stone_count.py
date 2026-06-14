"""Count stones in the connected group containing one marked Go stone."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import make_go_marked_group_objective, run_go_lifecycle
from .shared.rules import GO_RULE_MARKED_GROUP_STONES
from .shared.sampling import (
    resolve_go_player_color_axis,
    resolve_go_target_axis,
)
from .shared.state import DEFAULTS, GoIntegerAxis, GoSceneAxes, SCENE_ID


TASK_ID = "task_games__go__marked_group_stone_count"
QUERY_ID = "single"
PROMPT_QUERY_KEY = "marked_group_stone_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_stone_group_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    query_id: str,
    _query_probabilities: Mapping[str, float],
    scene_axes: GoSceneAxes,
    board_size_axis: GoIntegerAxis,
):
    """Bind marked-stone group-size counting to a Go board construction."""

    del query_id, _query_probabilities
    player_color_axis = resolve_go_player_color_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
    )
    target_axis = resolve_go_target_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="marked_group_stone_count_support",
        fallback_support=DEFAULTS.marked_group_stone_count_support,
        namespace=f"{PROMPT_QUERY_KEY}.target_answer",
    )

    return make_go_marked_group_objective(
        prompt_query_key=PROMPT_QUERY_KEY,
        rule_mode=GO_RULE_MARKED_GROUP_STONES,
        target_axis=target_axis,
        player_color_axis=player_color_axis,
        board_size_axis=board_size_axis,
        scene_axes=scene_axes,
        annotation_coord_attr="marked_group_coords",
        attempt_namespace=f"games.go.{PROMPT_QUERY_KEY}",
        mark_reference_stone_only=True,
        prompt_example_annotation_points=((280, 220), (353, 220), (353, 293), (426, 293)),
        prompt_example_answer=4,
    )


@register_task
class GamesGoMarkedGroupStoneCountTask:
    """Count stones in the same-color group containing the marked stone."""

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
            default_query_id=QUERY_ID,
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_stone_group_objective,
        )


__all__ = ["GamesGoMarkedGroupStoneCountTask"]
