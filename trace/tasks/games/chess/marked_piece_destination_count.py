"""Count destinations or captures for one marked chess piece."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.games.shared.piece_board_rules import piece_name
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import (
    ChessObjectivePlan,
    prepare_chess_bbox_count_objective,
    run_chess_public_entry,
)
from .shared.sampling import sample_marked_piece_destination_scene
from .shared.state import SCENE_ID


TASK_ID = "task_games__chess__marked_piece_destination_count"
SUPPORTED_QUERY_IDS = ("marked_piece_move_count", "marked_piece_capture_count")
MARKED_MOVE_SUPPORT = (1, 2, 3, 4, 5, 6, 7, 8)
MARKED_CAPTURE_SUPPORT = (0, 1, 2, 3, 4)
_GEN_DEFAULTS = load_scene_generation_rendering_prompt_defaults("games", SCENE_ID, task_id=TASK_ID)[0]


def _destination_query(selected: str) -> tuple[str, tuple[int, ...], str]:
    """Map the selected local query to destination semantics and support."""

    if str(selected) == "marked_piece_capture_count":
        return "capture", MARKED_CAPTURE_SUPPORT, "marked_piece_capture_count_support"
    return "move", MARKED_MOVE_SUPPORT, "marked_piece_move_count_support"


def _prepare_marked_piece_destination_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    query_id: str,
    _query_probabilities: Mapping[str, float],
) -> ChessObjectivePlan:
    """Bind marked-piece destination/capture semantics for one selected query."""

    destination_mode, fallback_support, support_key = _destination_query(str(query_id))
    def construct_sample(rng, axes, target_answer):
        return sample_marked_piece_destination_scene(
            rng=rng,
            axes=axes,
            destination_mode=str(destination_mode),
            target_answer=int(target_answer),
        )

    return prepare_chess_bbox_count_objective(
        instance_seed=int(instance_seed),
        task_params=task_params,
        task_id=TASK_ID,
        query_id=str(query_id),
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        fallback_support=fallback_support,
        attempt_namespace="games.chess.marked_piece_destination_count",
        construct_sample=construct_sample,
        badge_builder=lambda sample: "Marked piece"
        if sample.marked_piece is None
        else f"Marked {piece_name(sample.marked_piece)}",
        witness_type="cell_set",
        query_params={"destination_mode": str(destination_mode)},
    )


@register_task
class GamesChessMarkedPieceDestinationCountTask:
    """Count legal destinations or captures for the marked chess piece."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    prepare_objective = staticmethod(_prepare_marked_piece_destination_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        """Generate a marked-piece destination count."""

        return run_chess_public_entry(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GamesChessMarkedPieceDestinationCountTask", "sample_marked_piece_destination_scene"]
