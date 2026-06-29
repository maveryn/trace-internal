"""Sampling primitives for logic-grid puzzle tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from trace.core.sampling import support_probability_map
from trace.core.seed import spawn_rng
from trace.tasks.shared.mcq import option_label_for_index

from .defaults import resolve_option_count, sample_board_size
from .rules import (
    build_column_uniqueness_board,
    build_row_and_column_uniqueness_board,
    build_row_uniqueness_board,
    fill_board_with_king_non_touch,
    king_neighbor_coords,
    king_neighbor_symbol_set,
)
from .state import (
    COLUMN_AXIS,
    DEFAULTS,
    LOGIC_GRID_OBJECT_TYPES,
    ROW_AND_COLUMN_AXIS,
    ROW_AXIS,
    LogicGridDataset,
)


def _sample_symbol_pool(board_size: int, *, rng) -> List[str]:
    """Sample distinct symbols for one generated board."""

    all_symbols = list(LOGIC_GRID_OBJECT_TYPES)
    if int(board_size) > int(len(all_symbols)):
        raise ValueError("logic-grid board size exceeds supported symbol count")
    rng.shuffle(all_symbols)
    return [str(value) for value in all_symbols[: int(board_size)]]


def _grid_rows_for_display(
    board_values: Sequence[Sequence[str]],
    *,
    marked_row_index: int,
    marked_col_index: int,
) -> List[List[Dict[str, Any]]]:
    """Convert a solved board into renderable cells with one hidden slot."""

    grid_rows: List[List[Dict[str, Any]]] = []
    for row_index, row_values in enumerate(board_values):
        row_cells: List[Dict[str, Any]] = []
        for col_index, object_type in enumerate(row_values):
            is_marked = bool(row_index == marked_row_index and col_index == marked_col_index)
            row_cells.append(
                {
                    "cell_id": f"cell_{row_index}_{col_index}",
                    "row_index": int(row_index),
                    "col_index": int(col_index),
                    "is_unknown": bool(is_marked),
                    "object_type": None if is_marked else str(object_type),
                }
            )
        grid_rows.append(row_cells)
    return grid_rows


def _sample_correct_option_index(
    params: Mapping[str, Any],
    *,
    option_count: int,
    rng,
) -> tuple[int, Dict[str, float]]:
    """Sample the correct visual-option index from explicit option support."""

    support = tuple(range(int(option_count)))
    explicit = params.get("correct_option_index")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError("correct_option_index must fall inside the option-count range")
        return selected, support_probability_map(support, selected=selected, sort_keys=True)
    selected = int(rng.randrange(int(option_count)))
    return selected, support_probability_map(support, sort_keys=True)


def _option_specs(
    *,
    answer_object_type: str,
    distractor_types: Sequence[str],
    correct_option_index: int,
) -> tuple[List[Dict[str, Any]], List[str]]:
    """Build six labeled option specs with one inserted correct option."""

    option_object_types = [str(value) for value in distractor_types]
    option_object_types.insert(int(correct_option_index), str(answer_object_type))
    option_specs: List[Dict[str, Any]] = []
    option_labels: List[str] = []
    for option_index, option_object_type in enumerate(option_object_types):
        option_label = str(option_label_for_index(int(option_index)))
        option_labels.append(option_label)
        option_specs.append(
            {
                "option_panel_id": f"option_{option_label}",
                "option_index": int(option_index),
                "option_label": str(option_label),
                "object_type": str(option_object_type),
                "is_correct": bool(option_index == correct_option_index),
            }
        )
    return option_specs, option_labels


def sample_uniqueness_dataset(
    *,
    axis_kind: str,
    params: Mapping[str, Any],
    instance_seed: int,
    generation_defaults: Mapping[str, Any],
    namespace_base: str,
) -> LogicGridDataset:
    """Sample a row, column, or row-and-column uniqueness completion puzzle."""

    selected_axis = str(axis_kind)
    if selected_axis not in {ROW_AXIS, COLUMN_AXIS, ROW_AND_COLUMN_AXIS}:
        raise ValueError(f"unsupported uniqueness axis kind: {selected_axis}")
    rng = spawn_rng(int(instance_seed), f"{namespace_base}.dataset")
    board_size, board_size_probabilities = sample_board_size(
        params=params,
        generation_defaults=generation_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace_base}.board_size",
    )
    option_count = resolve_option_count(
        params,
        generation_defaults=generation_defaults,
        defaults=DEFAULTS,
    )
    symbol_pool = _sample_symbol_pool(int(board_size), rng=rng)
    if selected_axis == ROW_AXIS:
        board_values = build_row_uniqueness_board(symbol_pool, rng=rng)
        rule_name = "row_uniqueness"
    elif selected_axis == COLUMN_AXIS:
        board_values = build_column_uniqueness_board(symbol_pool, rng=rng)
        rule_name = "column_uniqueness"
    else:
        board_values = build_row_and_column_uniqueness_board(symbol_pool, rng=rng)
        rule_name = "row_column_uniqueness_rule"

    marked_row_index = int(rng.randrange(int(board_size)))
    marked_col_index = int(rng.randrange(int(board_size)))
    answer_object_type = str(board_values[marked_row_index][marked_col_index])
    distractor_pool = [
        str(value)
        for value in LOGIC_GRID_OBJECT_TYPES
        if str(value) != str(answer_object_type)
    ]
    rng.shuffle(distractor_pool)
    correct_index, correct_index_probabilities = _sample_correct_option_index(
        params,
        option_count=int(option_count),
        rng=rng,
    )
    option_specs, option_labels = _option_specs(
        answer_object_type=str(answer_object_type),
        distractor_types=distractor_pool[: int(option_count) - 1],
        correct_option_index=int(correct_index),
    )

    visible_row_values = [
        str(value)
        for col_index, value in enumerate(board_values[marked_row_index])
        if int(col_index) != int(marked_col_index)
    ]
    row_missing_symbol = next(symbol for symbol in symbol_pool if symbol not in visible_row_values)
    column_values = [
        str(board_values[row_index][marked_col_index])
        for row_index in range(int(board_size))
    ]
    visible_column_values = [
        str(value)
        for row_index, value in enumerate(column_values)
        if int(row_index) != int(marked_row_index)
    ]
    column_missing_symbol = next(symbol for symbol in symbol_pool if symbol not in visible_column_values)
    if selected_axis in {ROW_AXIS, ROW_AND_COLUMN_AXIS} and str(row_missing_symbol) != str(answer_object_type):
        raise ValueError("row uniqueness witness failed to recover the hidden symbol")
    if selected_axis in {COLUMN_AXIS, ROW_AND_COLUMN_AXIS} and str(column_missing_symbol) != str(answer_object_type):
        raise ValueError("column uniqueness witness failed to recover the hidden symbol")

    return LogicGridDataset(
        grid_rows=_grid_rows_for_display(
            board_values,
            marked_row_index=int(marked_row_index),
            marked_col_index=int(marked_col_index),
        ),
        board_values=[[str(value) for value in row] for row in board_values],
        symbol_pool=[str(value) for value in symbol_pool],
        marked_cell_id=f"cell_{marked_row_index}_{marked_col_index}",
        marked_row_index=int(marked_row_index),
        marked_col_index=int(marked_col_index),
        answer_object_type=str(answer_object_type),
        answer_option_label=str(option_label_for_index(int(correct_index))),
        correct_option_index=int(correct_index),
        correct_option_panel_id=str(option_specs[int(correct_index)]["option_panel_id"]),
        option_specs=option_specs,
        option_labels=option_labels,
        option_count=int(option_count),
        board_size=int(board_size),
        board_size_range=[
            int(min(board_size_probabilities, key=int)),
            int(max(board_size_probabilities, key=int)),
        ],
        cell_count=int(board_size * board_size),
        cell_count_range=[
            int(min(board_size_probabilities, key=int)) ** 2,
            int(max(board_size_probabilities, key=int)) ** 2,
        ],
        solver_trace={
            "rule_type": str(rule_name),
            "symbol_pool": [str(value) for value in symbol_pool],
            "row_missing_symbol": str(row_missing_symbol),
            "column_missing_symbol": str(column_missing_symbol),
            "correct_option_index": int(correct_index),
            "correct_option_label": str(option_label_for_index(int(correct_index))),
            "option_object_types": [str(spec["object_type"]) for spec in option_specs],
        },
        extra_trace={
            "axis_kind": str(selected_axis),
            "board_size_probabilities": dict(board_size_probabilities),
            "answer_option_index_probabilities": dict(correct_index_probabilities),
        },
    )


def sample_king_non_touch_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    generation_defaults: Mapping[str, Any],
    namespace_base: str,
) -> LogicGridDataset:
    """Sample a completion puzzle under the identical-symbol non-touch rule."""

    rng = spawn_rng(int(instance_seed), f"{namespace_base}.dataset")
    board_size, board_size_probabilities = sample_board_size(
        params=params,
        generation_defaults=generation_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace_base}.board_size",
    )
    option_count = resolve_option_count(
        params,
        generation_defaults=generation_defaults,
        defaults=DEFAULTS,
    )
    symbol_pool = list(LOGIC_GRID_OBJECT_TYPES[: int(option_count)])
    rng.shuffle(symbol_pool)
    candidates = [
        (int(row_index), int(col_index))
        for row_index in range(int(board_size))
        for col_index in range(int(board_size))
        if len(king_neighbor_coords(int(board_size), int(row_index), int(col_index))) >= 5
    ]
    if not candidates:
        raise ValueError("king non-touch puzzle requires at least one cell with five neighbors")

    marked_row_index, marked_col_index = rng.choice(candidates)
    answer_object_type = str(symbol_pool[0])
    forced_neighbor_symbols = [str(symbol) for symbol in symbol_pool[1:6]]
    neighbor_coords = list(king_neighbor_coords(int(board_size), int(marked_row_index), int(marked_col_index)))
    rng.shuffle(neighbor_coords)
    forced_neighbor_coords = list(neighbor_coords[:5])
    board_values: List[List[str | None]] = [
        [None for _ in range(int(board_size))]
        for _ in range(int(board_size))
    ]
    board_values[int(marked_row_index)][int(marked_col_index)] = str(answer_object_type)
    for (nbr_row, nbr_col), symbol in zip(forced_neighbor_coords, forced_neighbor_symbols, strict=True):
        board_values[int(nbr_row)][int(nbr_col)] = str(symbol)
    if not fill_board_with_king_non_touch(board_values, symbol_pool=symbol_pool, rng=rng):
        raise RuntimeError("failed to construct a valid king-non-touch board")

    filled_board = [[str(value) for value in row] for row in board_values]
    neighbor_symbol_set = king_neighbor_symbol_set(
        filled_board,
        row_index=int(marked_row_index),
        col_index=int(marked_col_index),
    )
    valid_symbols = [str(symbol) for symbol in symbol_pool if str(symbol) not in neighbor_symbol_set]
    if valid_symbols != [str(answer_object_type)]:
        raise ValueError("king non-touch witness failed to make the answer unique")

    correct_index, correct_index_probabilities = _sample_correct_option_index(
        params,
        option_count=int(option_count),
        rng=rng,
    )
    distractor_pool = [
        str(symbol)
        for symbol in symbol_pool
        if str(symbol) != str(answer_object_type)
    ]
    option_specs, option_labels = _option_specs(
        answer_object_type=str(answer_object_type),
        distractor_types=distractor_pool,
        correct_option_index=int(correct_index),
    )

    return LogicGridDataset(
        grid_rows=_grid_rows_for_display(
            filled_board,
            marked_row_index=int(marked_row_index),
            marked_col_index=int(marked_col_index),
        ),
        board_values=[[str(value) for value in row] for row in filled_board],
        symbol_pool=[str(value) for value in symbol_pool],
        marked_cell_id=f"cell_{marked_row_index}_{marked_col_index}",
        marked_row_index=int(marked_row_index),
        marked_col_index=int(marked_col_index),
        answer_object_type=str(answer_object_type),
        answer_option_label=str(option_label_for_index(int(correct_index))),
        correct_option_index=int(correct_index),
        correct_option_panel_id=str(option_specs[int(correct_index)]["option_panel_id"]),
        option_specs=option_specs,
        option_labels=option_labels,
        option_count=int(option_count),
        board_size=int(board_size),
        board_size_range=[
            int(min(board_size_probabilities, key=int)),
            int(max(board_size_probabilities, key=int)),
        ],
        cell_count=int(board_size * board_size),
        cell_count_range=[
            int(min(board_size_probabilities, key=int)) ** 2,
            int(max(board_size_probabilities, key=int)) ** 2,
        ],
        solver_trace={
            "rule_type": "king_non_touch",
            "touch_rule": "no_identical_symbols_touch_orthogonally_or_diagonally",
            "symbol_pool": [str(value) for value in symbol_pool],
            "neighbor_object_types": [str(value) for value in sorted(neighbor_symbol_set)],
            "valid_option_object_types": [str(value) for value in valid_symbols],
            "forced_neighbor_coords": [
                [int(row), int(col)]
                for row, col in sorted(forced_neighbor_coords)
            ],
            "correct_option_index": int(correct_index),
            "correct_option_label": str(option_label_for_index(int(correct_index))),
            "option_object_types": [str(spec["object_type"]) for spec in option_specs],
        },
        extra_trace={
            "board_size_probabilities": dict(board_size_probabilities),
            "answer_option_index_probabilities": dict(correct_index_probabilities),
            "neighbor_coords": [[int(row), int(col)] for row, col in sorted(neighbor_coords)],
            "forced_neighbor_coords": [
                [int(row), int(col)]
                for row, col in sorted(forced_neighbor_coords)
            ],
            "forced_neighbor_types": [str(value) for value in forced_neighbor_symbols],
            "query_neighbor_object_types": [str(value) for value in sorted(neighbor_symbol_set)],
            "valid_option_object_types": [str(value) for value in valid_symbols],
        },
    )
