"""Count visible Checkers pieces by color and board-edge state."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import (
    CheckersObjectivePlan,
    checkers_target_trace_params,
    resolve_checkers_task_target,
    run_checkers_lifecycle,
)
from .shared.rules import BLACK, RED
from .shared.sampling import sample_piece_state_scene, scene_object_description
from .shared.state import SCENE_ID, SampledCheckersScene


TASK_ID = "task_games__checkers__piece_state_count"
SUPPORTED_QUERY_IDS = (
    "red_piece_count",
    "black_piece_count",
    "red_edge_piece_count",
    "black_edge_piece_count",
)
QUERY_SETTINGS: Mapping[str, Mapping[str, Any]] = {
    "red_piece_count": {"player": RED, "edge_only": False},
    "black_piece_count": {"player": BLACK, "edge_only": False},
    "red_edge_piece_count": {"player": RED, "edge_only": True},
    "black_edge_piece_count": {"player": BLACK, "edge_only": True},
}
PIECE_STATE_COUNT_SUPPORT = (0, 1, 2, 3, 4, 5, 6)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_piece_state_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    query_id: str,
    _query_probabilities: Mapping[str, float],
) -> CheckersObjectivePlan:
    """Bind the selected color/perimeter piece-state query to exact-count sampling."""

    settings = QUERY_SETTINGS[str(query_id)]
    player = int(settings["player"])
    edge_only = bool(settings["edge_only"])
    target = resolve_checkers_task_target(
        instance_seed=int(instance_seed),
        task_params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="piece_state_count_support",
        fallback_support=PIECE_STATE_COUNT_SUPPORT,
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
    )

    def construct_attempt(rng, axes):
        return sample_piece_state_scene(
            rng=rng,
            axes=axes,
            params=task_params,
            target_answer=int(target.target_answer),
            player=int(player),
            edge_only=bool(edge_only),
        )

    def prompt_slots(sample: SampledCheckersScene) -> dict[str, str]:
        return {"object_description": scene_object_description(str(sample.scene_variant))}

    target_player = "red" if int(player) == int(RED) else "black"
    return CheckersObjectivePlan(
        attempt_namespace=f"games.checkers.piece_state_count.{str(query_id)}",
        prompt_query_key=str(query_id),
        target=target,
        query_params={
            **checkers_target_trace_params(target),
            "target_player": str(target_player),
            "edge_only": bool(edge_only),
        },
        execution_extra={
            "target_player": str(target_player),
            "edge_only": bool(edge_only),
        },
        construct_attempt=construct_attempt,
        build_prompt_dynamic_slots=prompt_slots,
    )


@register_task
class GamesCheckersPieceStateCountTask:
    """Count visible Checkers pieces by color and board-edge state."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        """Generate a color/perimeter piece count with point annotations."""

        return run_checkers_lifecycle(
            task_id=self.task_id,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_piece_state_objective,
        )


__all__ = ["GamesCheckersPieceStateCountTask"]
