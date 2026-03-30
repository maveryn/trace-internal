"""Shared config, generation, and render helpers for logic puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from .common import resolve_puzzle_axis_variant
from .logic_scene import PuzzleLogicRenderParams, SUPPORTED_PUZZLE_LOGIC_SCENE_VARIANTS
from .symbol_rendering import PUZZLE_OBJECT_TYPES
from ....core.seed import spawn_rng


@dataclass(frozen=True)
class PuzzleLogicDefaults:
    """Stable fallback defaults shared by logic-grid puzzle tasks."""

    board_size_min: int = 3
    board_size_max: int = 5
    option_count: int = 6
    canvas_width: int = 1200
    canvas_height: int = 920
    scene_margin_left_px: int = 64
    scene_margin_right_px: int = 64
    scene_margin_top_px: int = 56
    scene_margin_bottom_px: int = 56
    cell_size_px: int = 96
    cell_gap_px: int = 18
    board_panel_padding_px: int = 26
    board_to_options_gap_px: int = 56
    option_panel_width_px: int = 144
    option_panel_height_px: int = 172
    option_gap_px: int = 20
    option_symbol_box_size_px: int = 92
    option_label_gap_px: int = 16
    slot_corner_radius_px: int = 18
    border_width_px: int = 3
    panel_corner_radius_px: int = 28
    value_font_size_px: int = 46
    option_label_font_size_px: int = 30
    balanced_task_variant_sampling: bool = True
    balanced_scene_variant_sampling: bool = True


def resolve_logic_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: PuzzleLogicDefaults,
) -> PuzzleLogicRenderParams:
    """Resolve one reusable logic-grid render-parameter record."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        raw = params.get(str(key), group_default(render_defaults, str(key), list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must be a length-3 RGB sequence")
        return tuple(int(value) for value in raw)

    return PuzzleLogicRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", int(defaults.canvas_width)))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", int(defaults.canvas_height)))),
        scene_margin_left_px=int(params.get("scene_margin_left_px", group_default(render_defaults, "scene_margin_left_px", int(defaults.scene_margin_left_px)))),
        scene_margin_right_px=int(params.get("scene_margin_right_px", group_default(render_defaults, "scene_margin_right_px", int(defaults.scene_margin_right_px)))),
        scene_margin_top_px=int(params.get("scene_margin_top_px", group_default(render_defaults, "scene_margin_top_px", int(defaults.scene_margin_top_px)))),
        scene_margin_bottom_px=int(params.get("scene_margin_bottom_px", group_default(render_defaults, "scene_margin_bottom_px", int(defaults.scene_margin_bottom_px)))),
        cell_size_px=int(params.get("cell_size_px", group_default(render_defaults, "cell_size_px", int(defaults.cell_size_px)))),
        cell_gap_px=int(params.get("cell_gap_px", group_default(render_defaults, "cell_gap_px", int(defaults.cell_gap_px)))),
        board_panel_padding_px=int(params.get("board_panel_padding_px", group_default(render_defaults, "board_panel_padding_px", int(defaults.board_panel_padding_px)))),
        board_to_options_gap_px=int(params.get("board_to_options_gap_px", group_default(render_defaults, "board_to_options_gap_px", int(defaults.board_to_options_gap_px)))),
        option_panel_width_px=int(params.get("option_panel_width_px", group_default(render_defaults, "option_panel_width_px", int(defaults.option_panel_width_px)))),
        option_panel_height_px=int(params.get("option_panel_height_px", group_default(render_defaults, "option_panel_height_px", int(defaults.option_panel_height_px)))),
        option_gap_px=int(params.get("option_gap_px", group_default(render_defaults, "option_gap_px", int(defaults.option_gap_px)))),
        option_symbol_box_size_px=int(params.get("option_symbol_box_size_px", group_default(render_defaults, "option_symbol_box_size_px", int(defaults.option_symbol_box_size_px)))),
        option_label_gap_px=int(params.get("option_label_gap_px", group_default(render_defaults, "option_label_gap_px", int(defaults.option_label_gap_px)))),
        slot_corner_radius_px=int(params.get("slot_corner_radius_px", group_default(render_defaults, "slot_corner_radius_px", int(defaults.slot_corner_radius_px)))),
        border_width_px=int(params.get("border_width_px", group_default(render_defaults, "border_width_px", int(defaults.border_width_px)))),
        panel_corner_radius_px=int(params.get("panel_corner_radius_px", group_default(render_defaults, "panel_corner_radius_px", int(defaults.panel_corner_radius_px)))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(render_defaults, "value_font_size_px", int(defaults.value_font_size_px)))),
        option_label_font_size_px=int(params.get("option_label_font_size_px", group_default(render_defaults, "option_label_font_size_px", int(defaults.option_label_font_size_px)))),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        cell_fill_rgb=_triple("cell_fill_rgb", (252, 252, 255)),
        unknown_cell_fill_rgb=_triple("unknown_cell_fill_rgb", (242, 246, 255)),
        option_panel_fill_rgb=_triple("option_panel_fill_rgb", (251, 251, 255)),
        option_symbol_fill_rgb=_triple("option_symbol_fill_rgb", (252, 252, 255)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        accent_color_rgb=_triple("accent_color_rgb", (54, 102, 180)),
    )


def resolve_logic_board_size_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleLogicDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive board-size bounds for logic-grid tasks."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="board_size_min",
        max_key="board_size_max",
        fallback_min=int(defaults.board_size_min),
        fallback_max=int(defaults.board_size_max),
        context=f"{task_id} board-size bounds",
    )


def resolve_logic_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one visual logic-grid scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_LOGIC_SCENE_VARIANTS,
        task_id=task_id,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _sample_symbol_pool(board_size: int, *, rng) -> List[str]:
    """Sample one distinct visible symbol pool for the logic board."""

    all_symbols = list(PUZZLE_OBJECT_TYPES)
    rng.shuffle(all_symbols)
    return [str(value) for value in all_symbols[: int(board_size)]]


def _build_row_uniqueness_board(symbol_pool: Sequence[str], *, rng) -> List[List[str]]:
    """Build a board where each row is a permutation of the visible symbol pool."""

    symbols = [str(value) for value in symbol_pool]
    rows: List[List[str]] = []
    for _ in range(len(symbols)):
        row = list(symbols)
        rng.shuffle(row)
        rows.append([str(value) for value in row])
    return rows


def _build_column_uniqueness_board(symbol_pool: Sequence[str], *, rng) -> List[List[str]]:
    """Build a board where each column is a permutation of the visible symbol pool."""

    symbols = [str(value) for value in symbol_pool]
    columns: List[List[str]] = []
    for _ in range(len(symbols)):
        column = list(symbols)
        rng.shuffle(column)
        columns.append([str(value) for value in column])
    board_size = len(symbols)
    return [
        [str(columns[col_index][row_index]) for col_index in range(board_size)]
        for row_index in range(board_size)
    ]


def _build_row_and_column_uniqueness_board(symbol_pool: Sequence[str], *, rng) -> List[List[str]]:
    """Build a Latin-style board where both rows and columns contain each symbol once."""

    symbols = [str(value) for value in symbol_pool]
    board_size = len(symbols)
    row_shift_order = list(range(board_size))
    col_permutation = list(range(board_size))
    symbol_permutation = list(symbols)
    rng.shuffle(row_shift_order)
    rng.shuffle(col_permutation)
    rng.shuffle(symbol_permutation)
    return [
        [
            str(symbol_permutation[(row_shift_order[row_index] + col_permutation[col_index]) % board_size])
            for col_index in range(board_size)
        ]
        for row_index in range(board_size)
    ]


def _resolve_board_size(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str,
    board_size_range: Sequence[int],
) -> int:
    """Pick one deterministic board size from the inclusive feasible support."""

    lower = int(board_size_range[0])
    upper = int(board_size_range[1])
    if upper < lower:
        raise ValueError(f"{task_id} received empty board-size support")
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:board_size",
        )
    )
    return int(lower + (selection % (upper - lower + 1)))


def _resolve_correct_option_index(
    params: Mapping[str, Any],
    *,
    query_row_index: int,
    query_col_index: int,
    board_size: int,
    answer_object_type: str,
    option_count: int,
) -> int:
    """Pick one deterministic correct-option index with broad letter coverage."""

    explicit = params.get("correct_option_index")
    if explicit is not None:
        index = int(explicit)
        if not 0 <= index < int(option_count):
            raise ValueError("correct_option_index must fall inside the option-count range")
        return int(index)
    flat_index = int(query_row_index) * int(board_size) + int(query_col_index)
    symbol_offset = int(list(PUZZLE_OBJECT_TYPES).index(str(answer_object_type)))
    return int((flat_index + symbol_offset) % int(option_count))


def _king_neighbor_coords(board_size: int, row_index: int, col_index: int) -> List[Tuple[int, int]]:
    """Return all in-bounds king-move neighbors for one board cell."""

    neighbors: List[Tuple[int, int]] = []
    for delta_row in (-1, 0, 1):
        for delta_col in (-1, 0, 1):
            if int(delta_row) == 0 and int(delta_col) == 0:
                continue
            nbr_row = int(row_index + delta_row)
            nbr_col = int(col_index + delta_col)
            if 0 <= nbr_row < int(board_size) and 0 <= nbr_col < int(board_size):
                neighbors.append((int(nbr_row), int(nbr_col)))
    return neighbors


def _king_neighbor_symbol_set(
    board_values: Sequence[Sequence[str | None]],
    *,
    row_index: int,
    col_index: int,
) -> set[str]:
    """Return the set of already assigned neighboring symbols around one cell."""

    board_size = int(len(board_values))
    seen: set[str] = set()
    for nbr_row, nbr_col in _king_neighbor_coords(int(board_size), int(row_index), int(col_index)):
        value = board_values[int(nbr_row)][int(nbr_col)]
        if value is not None:
            seen.add(str(value))
    return seen


def _allowed_king_symbols(
    board_values: Sequence[Sequence[str | None]],
    *,
    row_index: int,
    col_index: int,
    symbol_pool: Sequence[str],
) -> List[str]:
    """Return symbols that preserve the king-adjacency non-touch rule at one cell."""

    blocked = _king_neighbor_symbol_set(board_values, row_index=int(row_index), col_index=int(col_index))
    return [str(symbol) for symbol in symbol_pool if str(symbol) not in blocked]


def _fill_board_with_king_non_touch(
    board_values: List[List[str | None]],
    *,
    symbol_pool: Sequence[str],
    rng,
) -> bool:
    """Backtrack-fill the remaining board cells under the king-adjacency non-touch rule."""

    pending: List[Tuple[int, int, List[str]]] = []
    for row_index, row in enumerate(board_values):
        for col_index, value in enumerate(row):
            if value is not None:
                continue
            allowed = _allowed_king_symbols(
                board_values,
                row_index=int(row_index),
                col_index=int(col_index),
                symbol_pool=symbol_pool,
            )
            if not allowed:
                return False
            pending.append((int(row_index), int(col_index), list(allowed)))
    if not pending:
        return True

    row_index, col_index, allowed = min(pending, key=lambda item: (len(item[2]), item[0], item[1]))
    rng.shuffle(allowed)
    for symbol in allowed:
        board_values[int(row_index)][int(col_index)] = str(symbol)
        if _fill_board_with_king_non_touch(board_values, symbol_pool=symbol_pool, rng=rng):
            return True
        board_values[int(row_index)][int(col_index)] = None
    return False


def build_logic_adjacency_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleLogicDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic explicit-rule adjacency logic puzzle dataset."""

    selected_variant = str(task_variant)
    supported = {"king_non_touch"}
    if selected_variant not in supported:
        raise ValueError(f"unsupported logic adjacency variant: {task_variant}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    board_size_range = resolve_logic_board_size_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    board_size = _resolve_board_size(
        params,
        instance_seed=int(instance_seed),
        task_id=task_id,
        board_size_range=board_size_range,
    )
    option_count = int(params.get("option_count", group_default(gen_defaults, "option_count", int(defaults.option_count))))
    if int(option_count) != 6:
        raise ValueError(f"{task_id} currently requires exactly 6 options for stable option-letter coverage")

    symbol_pool = list(PUZZLE_OBJECT_TYPES)
    if int(len(symbol_pool)) != int(option_count):
        raise ValueError(f"{task_id} expects the global puzzle symbol pool to match option_count")
    rng.shuffle(symbol_pool)
    query_candidates = [
        (int(row_index), int(col_index))
        for row_index in range(int(board_size))
        for col_index in range(int(board_size))
        if len(_king_neighbor_coords(int(board_size), int(row_index), int(col_index))) >= 5
    ]
    if not query_candidates:
        raise ValueError(f"{task_id} requires at least one cell with five neighbors")

    query_selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:query_cell",
        )
    )
    query_row_index, query_col_index = query_candidates[int(query_selection % len(query_candidates))]
    answer_object_type = str(symbol_pool[0])
    forced_neighbor_symbols = [str(symbol) for symbol in symbol_pool[1:6]]
    neighbor_coords = list(_king_neighbor_coords(int(board_size), int(query_row_index), int(query_col_index)))
    rng.shuffle(neighbor_coords)
    forced_neighbor_coords = list(neighbor_coords[:5])

    board_values: List[List[str | None]] = [
        [None for _ in range(int(board_size))]
        for _ in range(int(board_size))
    ]
    board_values[int(query_row_index)][int(query_col_index)] = str(answer_object_type)
    for (nbr_row, nbr_col), symbol in zip(forced_neighbor_coords, forced_neighbor_symbols, strict=True):
        board_values[int(nbr_row)][int(nbr_col)] = str(symbol)
    if not _fill_board_with_king_non_touch(board_values, symbol_pool=symbol_pool, rng=rng):
        raise RuntimeError("failed to construct a valid king-non-touch logic board")

    filled_board = [[str(value) for value in row] for row in board_values]
    neighbor_symbol_set = _king_neighbor_symbol_set(
        filled_board,
        row_index=int(query_row_index),
        col_index=int(query_col_index),
    )
    valid_symbols = [str(symbol) for symbol in symbol_pool if str(symbol) not in neighbor_symbol_set]
    if valid_symbols != [str(answer_object_type)]:
        raise ValueError("logic adjacency witness failed to make the answer unique")

    query_cell_id = f"cell_{query_row_index}_{query_col_index}"
    grid_rows: List[List[Dict[str, Any]]] = []
    for row_index, row_values in enumerate(filled_board):
        row_cells: List[Dict[str, Any]] = []
        for col_index, object_type in enumerate(row_values):
            cell_id = f"cell_{row_index}_{col_index}"
            row_cells.append(
                {
                    "cell_id": str(cell_id),
                    "row_index": int(row_index),
                    "col_index": int(col_index),
                    "is_unknown": bool(row_index == query_row_index and col_index == query_col_index),
                    "object_type": None if row_index == query_row_index and col_index == query_col_index else str(object_type),
                }
            )
        grid_rows.append(row_cells)

    distractor_pool = [str(symbol) for symbol in symbol_pool if str(symbol) != str(answer_object_type)]
    correct_option_index = _resolve_correct_option_index(
        params,
        query_row_index=int(query_row_index),
        query_col_index=int(query_col_index),
        board_size=int(board_size),
        answer_object_type=str(answer_object_type),
        option_count=int(option_count),
    )
    option_object_types = list(distractor_pool)
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

    return {
        "grid_rows": grid_rows,
        "board_values": [[str(value) for value in row] for row in filled_board],
        "symbol_pool": [str(value) for value in symbol_pool],
        "query_cell_id": str(query_cell_id),
        "query_row_index": int(query_row_index),
        "query_col_index": int(query_col_index),
        "answer_object_type": str(answer_object_type),
        "answer_option_label": str(option_label_for_index(correct_option_index)),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(option_specs[correct_option_index]["option_panel_id"]),
        "option_specs": option_specs,
        "option_labels": option_labels,
        "option_count": int(option_count),
        "board_size": int(board_size),
        "board_size_range": [int(board_size_range[0]), int(board_size_range[1])],
        "cell_count": int(board_size * board_size),
        "cell_count_range": [int(board_size_range[0] ** 2), int(board_size_range[1] ** 2)],
        "neighbor_coords": [[int(row), int(col)] for row, col in sorted(neighbor_coords)],
        "forced_neighbor_coords": [[int(row), int(col)] for row, col in sorted(forced_neighbor_coords)],
        "forced_neighbor_types": [str(value) for value in forced_neighbor_symbols],
        "query_neighbor_object_types": [str(value) for value in sorted(neighbor_symbol_set)],
        "valid_option_object_types": [str(value) for value in valid_symbols],
        "solver_trace": {
            "rule_type": str(selected_variant),
            "touch_rule": "no_identical_symbols_touch_orthogonally_or_diagonally",
            "symbol_pool": [str(value) for value in symbol_pool],
            "query_neighbor_object_types": [str(value) for value in sorted(neighbor_symbol_set)],
            "valid_option_object_types": [str(value) for value in valid_symbols],
            "forced_neighbor_coords": [[int(row), int(col)] for row, col in sorted(forced_neighbor_coords)],
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
            "option_object_types": [str(value) for value in option_object_types],
        },
    }


def build_logic_grid_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleLogicDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic logic-grid puzzle dataset."""

    selected_variant = str(task_variant)
    supported = {
        "row_uniqueness",
        "column_uniqueness",
        "row_and_column_uniqueness",
    }
    if selected_variant not in supported:
        raise ValueError(f"unsupported logic-grid variant: {task_variant}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    board_size_range = resolve_logic_board_size_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    board_size = _resolve_board_size(
        params,
        instance_seed=int(instance_seed),
        task_id=task_id,
        board_size_range=board_size_range,
    )
    option_count = int(params.get("option_count", group_default(gen_defaults, "option_count", int(defaults.option_count))))
    if int(option_count) != 6:
        raise ValueError(f"{task_id} currently requires exactly 6 options for stable option-letter coverage")

    symbol_pool = _sample_symbol_pool(int(board_size), rng=rng)
    if selected_variant == "row_uniqueness":
        board_values = _build_row_uniqueness_board(symbol_pool, rng=rng)
    elif selected_variant == "column_uniqueness":
        board_values = _build_column_uniqueness_board(symbol_pool, rng=rng)
    else:
        board_values = _build_row_and_column_uniqueness_board(symbol_pool, rng=rng)

    query_row_index = int(rng.randrange(int(board_size)))
    query_col_index = int(rng.randrange(int(board_size)))
    answer_object_type = str(board_values[query_row_index][query_col_index])
    query_cell_id = f"cell_{query_row_index}_{query_col_index}"

    grid_rows: List[List[Dict[str, Any]]] = []
    for row_index, row_values in enumerate(board_values):
        row_cells: List[Dict[str, Any]] = []
        for col_index, object_type in enumerate(row_values):
            cell_id = f"cell_{row_index}_{col_index}"
            row_cells.append(
                {
                    "cell_id": str(cell_id),
                    "row_index": int(row_index),
                    "col_index": int(col_index),
                    "is_unknown": bool(row_index == query_row_index and col_index == query_col_index),
                    "object_type": None if row_index == query_row_index and col_index == query_col_index else str(object_type),
                }
            )
        grid_rows.append(row_cells)

    distractor_pool = [str(value) for value in PUZZLE_OBJECT_TYPES if str(value) != str(answer_object_type)]
    rng.shuffle(distractor_pool)
    distractor_types = [str(value) for value in distractor_pool[: int(option_count) - 1]]
    correct_option_index = _resolve_correct_option_index(
        params,
        query_row_index=int(query_row_index),
        query_col_index=int(query_col_index),
        board_size=int(board_size),
        answer_object_type=str(answer_object_type),
        option_count=int(option_count),
    )
    option_object_types = list(distractor_types)
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

    visible_row_values = [
        str(value)
        for col_index, value in enumerate(board_values[query_row_index])
        if int(col_index) != int(query_col_index)
    ]
    row_missing_symbol = next(
        symbol
        for symbol in symbol_pool
        if symbol not in visible_row_values
    )
    column_values = [str(board_values[row_index][query_col_index]) for row_index in range(int(board_size))]
    visible_column_values = [
        str(value)
        for row_index, value in enumerate(column_values)
        if int(row_index) != int(query_row_index)
    ]
    column_missing_symbol = next(
        symbol
        for symbol in symbol_pool
        if symbol not in visible_column_values
    )
    if selected_variant in {"row_uniqueness", "row_and_column_uniqueness"} and str(row_missing_symbol) != str(answer_object_type):
        raise ValueError("logic row witness failed to recover the hidden symbol")
    if selected_variant in {"column_uniqueness", "row_and_column_uniqueness"} and str(column_missing_symbol) != str(answer_object_type):
        raise ValueError("logic column witness failed to recover the hidden symbol")

    return {
        "grid_rows": grid_rows,
        "board_values": [[str(value) for value in row] for row in board_values],
        "symbol_pool": [str(value) for value in symbol_pool],
        "query_cell_id": str(query_cell_id),
        "query_row_index": int(query_row_index),
        "query_col_index": int(query_col_index),
        "answer_object_type": str(answer_object_type),
        "answer_option_label": str(option_label_for_index(correct_option_index)),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(option_specs[correct_option_index]["option_panel_id"]),
        "option_specs": option_specs,
        "option_labels": option_labels,
        "option_count": int(option_count),
        "board_size": int(board_size),
        "board_size_range": [int(board_size_range[0]), int(board_size_range[1])],
        "cell_count": int(board_size * board_size),
        "cell_count_range": [int(board_size_range[0] ** 2), int(board_size_range[1] ** 2)],
        "solver_trace": {
            "rule_type": str(selected_variant),
            "symbol_pool": [str(value) for value in symbol_pool],
            "row_missing_symbol": str(row_missing_symbol),
            "column_missing_symbol": str(column_missing_symbol),
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
            "option_object_types": [str(value) for value in option_object_types],
        },
    }


__all__ = [
    "PuzzleLogicDefaults",
    "PuzzleLogicRenderParams",
    "SUPPORTED_PUZZLE_LOGIC_SCENE_VARIANTS",
    "build_logic_adjacency_dataset_for_variant",
    "build_logic_grid_dataset_for_variant",
    "resolve_logic_board_size_bounds",
    "resolve_logic_render_params",
    "resolve_logic_scene_variant",
]
