"""Board-size resolution helpers for tile tasks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trace.tasks.shared.config_defaults import group_default, resolve_required_int_bounds
from trace.tasks.shared.deterministic_sampling import resolve_selection_index


def resolve_square_board_dimensions(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    fallback_rows: int,
    fallback_cols: int,
    fallback_board_size_min: int,
    fallback_board_size_max: int,
) -> tuple[int, int, dict[str, Any]]:
    """Resolve fixed rows/cols overrides or sample one square board size."""
    uses_fixed_rows_cols = (
        "rows" in params
        or "cols" in params
        or "rows" in generation_defaults
        or "cols" in generation_defaults
    )
    if uses_fixed_rows_cols:
        rows = int(params.get("rows", group_default(generation_defaults, "rows", int(fallback_rows))))
        cols = int(params.get("cols", group_default(generation_defaults, "cols", int(fallback_cols))))
        if int(rows) <= 0 or int(cols) <= 0:
            raise ValueError("rows and cols must be positive")
        board_metadata: dict[str, Any] = {
            "board_size_range": [min(int(rows), int(cols)), max(int(rows), int(cols))]
        }
        if int(rows) == int(cols):
            board_metadata["board_size"] = int(rows)
        return int(rows), int(cols), board_metadata

    board_size_min, board_size_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="board_size_min",
        max_key="board_size_max",
        fallback_min=int(fallback_board_size_min),
        fallback_max=int(fallback_board_size_max),
        context=f"generation defaults for {task_id}",
    )
    if int(board_size_min) <= 0:
        raise ValueError("board_size_min must be positive")
    board_axis_size = int(board_size_max) - int(board_size_min) + 1
    board_selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:board_size",
    )
    board_size = int(board_size_min) + (int(board_selection_index) % int(board_axis_size))
    return int(board_size), int(board_size), {
        "board_size": int(board_size),
        "board_size_range": [int(board_size_min), int(board_size_max)],
    }
