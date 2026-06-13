"""Count destinations or captures for one marked chess-variant piece."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.games.chess_variant._lifecycle import (
    prepare_chess_variant_count_objective,
    run_chess_variant_public_entry,
)
from trace.tasks.games.chess_variant.shared.sampling import (
    max_possible_marked_destination_answer,
    sample_marked_destination_scene,
)
from trace.tasks.games.chess_variant.shared.state import ChessVariantSceneAxes
from trace.tasks.games.shared.piece_board_rules import piece_name
from trace.tasks.registry import register_task


TASK_ID = "task_games__chess_variant__marked_piece_destination_count"
SUPPORTED_QUERY_IDS = ("marked_piece_move_count", "marked_piece_capture_count")
MOVE_COUNT_SUPPORT = (0, 1, 2, 3, 4)
CAPTURE_COUNT_SUPPORT = (0, 1, 2, 3, 4)

def _query_semantics(selected: str):
    if str(selected) == "marked_piece_capture_count":
        return "capture", "marked_piece_capture_count_support", CAPTURE_COUNT_SUPPORT
    return "move", "marked_piece_move_count_support", MOVE_COUNT_SUPPORT


def _prepare_marked_piece_destination_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    axes: ChessVariantSceneAxes,
    query_id: str,
):
    """Prepare task-owned semantics for one marked-piece destination query."""

    destination_mode, support_key, fallback_support = _query_semantics(str(query_id))
    possible_max = max_possible_marked_destination_answer(
        destination_mode=str(destination_mode),
        rule_family=str(axes.rule_family),
        range_k=int(axes.range_k),
    )
    def execution_extra(sample):
        marked_piece = sample.evaluation.marked_piece
        return {
            "marked_piece_name": "" if marked_piece is None else piece_name(marked_piece),
        }

    return prepare_chess_variant_count_objective(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        task_params=task_params,
        query_id=str(query_id),
        support_key=str(support_key),
        fallback_support=fallback_support,
        possible_max=int(possible_max),
        attempt_namespace="games.chess_variant.marked_piece_destination_count",
        semantic_query_params={"destination_mode": str(destination_mode)},
        construct_sample=lambda rng, target_answer: sample_marked_destination_scene(
            rng=rng,
            axes=axes,
            destination_mode=str(destination_mode),
            target_answer=int(target_answer),
        ),
        outline_rgb=(220, 38, 38),
        example_answer=4 if str(destination_mode) == "move" else 2,
        execution_extra={"destination_mode": str(destination_mode)},
        build_execution_extra=execution_extra,
    )


@register_task
class GamesChessVariantMarkedPieceDestinationCountTask:
    """Count legal destinations or capture destinations for the marked piece."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    prepare_objective = staticmethod(_prepare_marked_piece_destination_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int) -> TaskOutput:
        """Generate a marked-piece destination count from task-owned query semantics."""

        return run_chess_variant_public_entry(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GamesChessVariantMarkedPieceDestinationCountTask"]
