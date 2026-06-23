"""Layer piece-count task for 3D Tic-Tac-Toe boards."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import TicTacToe3DObjectivePlan, run_tic_tac_toe_3d_lifecycle
from .shared.prompts import format_json_examples
from .shared.sampling import sample_layer_piece_count_scene


TASK_ID = "task_games__tic_tac_toe_3d__layer_piece_count"
QUERY_X_LAYER_COUNT = "x_piece_count_in_layer"
QUERY_O_LAYER_COUNT = "o_piece_count_in_layer"
SUPPORTED_QUERY_IDS = (QUERY_X_LAYER_COUNT, QUERY_O_LAYER_COUNT)
TARGET_PLAYER_BY_QUERY = {
    QUERY_X_LAYER_COUNT: "X",
    QUERY_O_LAYER_COUNT: "O",
}
JSON_EXAMPLE, JSON_EXAMPLE_ANSWER_ONLY = format_json_examples(
    annotation=[[212, 318], [285, 391], [358, 318]],
    answer=3,
)


def _prepare_layer_piece_count_objective(
    _instance_seed: int,
    _params: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
) -> TicTacToe3DObjectivePlan:
    """Bind the target mark and layer count for the public count task."""

    if str(selected_branch) not in TARGET_PLAYER_BY_QUERY:
        raise ValueError(f"unsupported 3D Tic-Tac-Toe layer-count branch: {selected_branch}")
    target_player = str(TARGET_PLAYER_BY_QUERY[str(selected_branch)])

    def construct_attempt(rng, axes):
        return sample_layer_piece_count_scene(
            rng=rng,
            target_player=target_player,
            target_layer=str(axes.target_layer),
            target_answer=int(axes.target_answer),
        )

    return TicTacToe3DObjectivePlan(
        attempt_namespace=f"games.tic_tac_toe_3d.layer_count.{target_player}",
        prompt_query_key=str(selected_branch),
        answer_hint_key=f"answer_hint_{selected_branch}",
        annotation_hint_key=f"annotation_hint_{selected_branch}",
        annotation_kind="cell_point_set",
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
        construct_attempt=construct_attempt,
        trace_params={
            "target_player": target_player,
            "layer_count_branch_probabilities": dict(branch_probabilities),
        },
    )


@register_task
class GamesTicTacToe3DLayerPieceCountTask:
    """Count target-player pieces in one named 3D Tic-Tac-Toe layer."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        return run_tic_tac_toe_3d_lifecycle(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_X_LAYER_COUNT,
            instance_seed=int(instance_seed),
            params=dict(params or {}),
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_layer_piece_count_objective,
        )


__all__ = ["GamesTicTacToe3DLayerPieceCountTask", "TASK_ID"]
