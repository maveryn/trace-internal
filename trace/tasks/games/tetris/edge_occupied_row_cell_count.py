"""Count filled or empty cells in the top or bottom occupied Tetris row."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import TetrisObjectivePlan, resolve_tetris_integer_target, run_tetris_lifecycle
from .shared.prompts import format_json_examples
from .shared.rendering import RENDER_MODE_STATIC_BOARD
from .shared.sampling import build_edge_occupied_row_cell_count_sample


TASK_ID = "task_games__tetris__edge_occupied_row_cell_count"
SUPPORTED_QUERY_IDS = (
    "top_occupied_row_filled_cell_count",
    "top_occupied_row_empty_cell_count",
    "bottom_occupied_row_filled_cell_count",
    "bottom_occupied_row_empty_cell_count",
)
JSON_EXAMPLE, JSON_EXAMPLE_ANSWER_ONLY = format_json_examples(
    annotation=[[120, 220, 150, 250], [154, 220, 184, 250]],
    answer=2,
)


def _edge_status_parts(selected_query: str) -> tuple[str, str]:
    """Parse the public query branch into row-edge and cell-status operands."""

    raw = str(selected_query)
    if raw.startswith("top_"):
        edge = "top"
    elif raw.startswith("bottom_"):
        edge = "bottom"
    else:
        raise ValueError(f"unsupported Tetris edge-row query: {selected_query}")
    if "_filled_" in raw:
        status = "filled"
    elif "_empty_" in raw:
        status = "empty"
    else:
        raise ValueError(f"unsupported Tetris edge-row query: {selected_query}")
    return str(edge), str(status)


def _valid_cell_count_support(*, board_cols: int, cell_status: str) -> tuple[int, ...]:
    """Return feasible counts for a nonempty occupied row on this board width."""

    if str(cell_status) == "filled":
        return tuple(range(1, int(board_cols) + 1))
    return tuple(range(0, int(board_cols)))


def _prepare_edge_row_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query: str,
    query_probabilities: Mapping[str, float],
    axes,
) -> TetrisObjectivePlan:
    """Resolve the selected edge/status pair and exact target cell count."""

    edge, cell_status = _edge_status_parts(str(selected_query))
    valid_support = _valid_cell_count_support(board_cols=int(axes.board_cols), cell_status=str(cell_status))
    target_cell_count, target_probabilities, target_support = resolve_tetris_integer_target(
        instance_seed=int(instance_seed),
        params=task_params,
        support_key="edge_occupied_row_valid_cell_count_support",
        explicit_key="target_cell_count",
        fallback_support=valid_support,
        namespace=f"{TASK_ID}.{edge}.{cell_status}.target_cell_count",
        gen_defaults={},
    )

    def construct_attempt(rng, resolved_axes):
        return build_edge_occupied_row_cell_count_sample(
            rng,
            scene_variant=str(resolved_axes.scene_variant),
            board_rows=int(resolved_axes.board_rows),
            board_cols=int(resolved_axes.board_cols),
            edge=str(edge),
            cell_status=str(cell_status),
            target_cell_count=int(target_cell_count),
        )

    return TetrisObjectivePlan(
        attempt_namespace=f"games.tetris.edge_row.{edge}.{cell_status}.{int(target_cell_count)}",
        prompt_query_key=str(selected_query),
        answer_hint_key="answer_hint_edge_occupied_row_cell_count",
        annotation_hint_key="annotation_hint_edge_occupied_row_cell_count",
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
        render_mode=RENDER_MODE_STATIC_BOARD,
        query_params={
            "edge_row_selector": str(edge),
            "counted_cell_status": str(cell_status),
            "target_cell_count": int(target_cell_count),
            "target_cell_count_support": [int(value) for value in target_support],
            "target_cell_count_probabilities": dict(target_probabilities),
            "edge_row_query_probabilities": dict(query_probabilities),
        },
        construct_attempt=construct_attempt,
    )


@register_task
class GamesTetrisEdgeOccupiedRowCellCountTask:
    """Count cells with the requested status in the selected occupied edge row."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_tetris_lifecycle(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_edge_row_objective,
        )


__all__ = ["GamesTetrisEdgeOccupiedRowCellCountTask"]
