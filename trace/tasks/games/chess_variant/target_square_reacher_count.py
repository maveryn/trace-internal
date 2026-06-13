"""Count pieces that can reach a marked target square under a visible rule."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.games.chess_variant._lifecycle import (
    prepare_chess_variant_count_objective,
    run_chess_variant_public_entry,
)
from trace.tasks.games.chess_variant.shared.sampling import (
    max_possible_target_reacher_answer,
    sample_target_reacher_scene,
)
from trace.tasks.games.chess_variant.shared.state import ChessVariantSceneAxes
from trace.tasks.games.shared.piece_board_rules import BLACK, WHITE
from trace.tasks.registry import register_task


TASK_ID = "task_games__chess_variant__target_square_reacher_count"
SUPPORTED_QUERY_IDS = (
    "white_piece_reaches_target_count",
    "black_piece_reaches_target_count",
)
REACHER_COUNT_SUPPORT = (0, 1, 2, 3, 4)

def _target_color_for_query(selected: str) -> str:
    if str(selected) == "black_piece_reaches_target_count":
        return BLACK
    return WHITE


def _prepare_target_square_reacher_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    axes: ChessVariantSceneAxes,
    query_id: str,
):
    """Prepare task-owned semantics for one target-square reacher query."""

    target_color = _target_color_for_query(str(query_id))
    possible_max = max_possible_target_reacher_answer(
        rule_family=str(axes.rule_family),
        range_k=int(axes.range_k),
    )
    return prepare_chess_variant_count_objective(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        task_params=task_params,
        query_id=str(query_id),
        support_key=f"{str(target_color)}_piece_reaches_target_count_support",
        fallback_support=REACHER_COUNT_SUPPORT,
        possible_max=int(possible_max),
        attempt_namespace="games.chess_variant.target_square_reacher_count",
        semantic_query_params={"target_color": str(target_color)},
        construct_sample=lambda rng, target_answer: sample_target_reacher_scene(
            rng=rng,
            axes=axes,
            target_color=str(target_color),
            target_answer=int(target_answer),
        ),
        outline_rgb=(35, 95, 220),
        target_color=str(target_color),
        example_answer=3,
    )


@register_task
class GamesChessVariantTargetSquareReacherCountTask:
    """Count same-side pieces that can legally move to one target square."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    prepare_objective = staticmethod(_prepare_target_square_reacher_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int) -> TaskOutput:
        """Generate a target-square reacher count from task-owned query semantics."""

        return run_chess_variant_public_entry(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GamesChessVariantTargetSquareReacherCountTask"]
