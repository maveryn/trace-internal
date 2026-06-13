"""Count pieces between a marked slider and a target chess square."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import (
    ChessObjectivePlan,
    prepare_chess_bbox_count_objective,
    run_chess_public_entry,
)
from .shared.sampling import sample_line_blocker_scene
from .shared.state import SCENE_ID


TASK_ID = "task_games__chess__marked_piece_blocker_count"
SUPPORTED_QUERY_IDS = ("rook_line_blocker_count", "bishop_diagonal_blocker_count", "queen_line_blocker_count")
BLOCKER_SUPPORT = (0, 1, 2, 3, 4)
_GEN_DEFAULTS = load_scene_generation_rendering_prompt_defaults("games", SCENE_ID, task_id=TASK_ID)[0]


def _slider_kind(selected: str) -> str:
    """Return the sliding piece kind used by the selected blocker query."""

    if str(selected).startswith("bishop"):
        return "bishop"
    if str(selected).startswith("queen"):
        return "queen"
    return "rook"


def _prepare_marked_piece_blocker_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    query_id: str,
    _query_probabilities: Mapping[str, float],
) -> ChessObjectivePlan:
    """Bind slider-line blocker-count semantics for one selected query."""

    slider_kind = _slider_kind(str(query_id))
    def construct_sample(rng, axes, target_answer):
        return sample_line_blocker_scene(
            rng=rng,
            axes=axes,
            slider_kind=str(slider_kind),
            target_answer=int(target_answer),
        )

    return prepare_chess_bbox_count_objective(
        instance_seed=int(instance_seed),
        task_params=task_params,
        task_id=TASK_ID,
        query_id=str(query_id),
        gen_defaults=_GEN_DEFAULTS,
        support_key="marked_piece_blocker_count_support",
        fallback_support=BLOCKER_SUPPORT,
        attempt_namespace="games.chess.marked_piece_blocker_count",
        construct_sample=construct_sample,
        badge_text=f"Marked {slider_kind}",
        witness_type="piece_set",
        query_params={"slider_kind": str(slider_kind)},
        execution_extra={"slider_kind": str(slider_kind)},
    )


@register_task
class GamesChessMarkedPieceBlockerCountTask:
    """Count intervening pieces between a marked sliding piece and a target square."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    prepare_objective = staticmethod(_prepare_marked_piece_blocker_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        """Generate a slider-line blocker count."""

        return run_chess_public_entry(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GamesChessMarkedPieceBlockerCountTask"]
