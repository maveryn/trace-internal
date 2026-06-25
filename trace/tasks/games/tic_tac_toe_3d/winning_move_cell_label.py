"""Winning-move option label task for 3D Tic-Tac-Toe boards."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import TicTacToe3DObjectivePlan, run_tic_tac_toe_3d_lifecycle
from .shared.prompts import format_json_examples
from .shared.sampling import sample_winning_move_scene
from .shared.state import OPTION_LABELS


TASK_ID = "task_games__tic_tac_toe_3d__winning_move_cell_label"
QUERY_X_WIN_MOVE = "x_winning_move_label"
QUERY_O_WIN_MOVE = "o_winning_move_label"
SUPPORTED_QUERY_IDS = (QUERY_X_WIN_MOVE, QUERY_O_WIN_MOVE)
TARGET_PLAYER_BY_QUERY = {
    QUERY_X_WIN_MOVE: "X",
    QUERY_O_WIN_MOVE: "O",
}
JSON_EXAMPLE, JSON_EXAMPLE_ANSWER_ONLY = format_json_examples(
    annotation=[[320, 190, 380, 250], [250, 190, 310, 250], [390, 190, 450, 250]],
    answer="B",
)


def _prepare_winning_move_objective(
    _instance_seed: int,
    _params: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
) -> TicTacToe3DObjectivePlan:
    """Bind the target player and answer option for the winning-move task."""

    if str(selected_branch) not in TARGET_PLAYER_BY_QUERY:
        raise ValueError(f"unsupported 3D Tic-Tac-Toe winning-move branch: {selected_branch}")
    target_player = str(TARGET_PLAYER_BY_QUERY[str(selected_branch)])

    def construct_attempt(rng, axes):
        return sample_winning_move_scene(
            rng=rng,
            target_player=target_player,
            option_count=int(axes.option_count),
            answer_option_index=int(axes.answer_option_index),
        )

    return TicTacToe3DObjectivePlan(
        attempt_namespace=f"games.tic_tac_toe_3d.winning_move.{target_player}",
        prompt_query_key=str(selected_branch),
        answer_hint_key=f"answer_hint_{selected_branch}",
        annotation_hint_key=f"annotation_hint_{selected_branch}",
        annotation_kind="cell_bbox_set",
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
        construct_attempt=construct_attempt,
        trace_params={
            "target_player": target_player,
            "winning_move_branch": str(selected_branch),
            "winning_move_branch_probabilities": dict(branch_probabilities),
            "available_option_labels": list(OPTION_LABELS),
        },
    )


@register_task
class GamesTicTacToe3DWinningMoveCellLabelTask:
    """Choose the labeled cell that completes a 3D Tic-Tac-Toe line."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        return run_tic_tac_toe_3d_lifecycle(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_X_WIN_MOVE,
            instance_seed=int(instance_seed),
            params=dict(params or {}),
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_winning_move_objective,
        )


__all__ = ["GamesTicTacToe3DWinningMoveCellLabelTask", "TASK_ID"]
