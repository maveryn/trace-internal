"""Games tasks for variable-size Tetris board mechanics."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import fit_font_to_box, resolve_text_stroke_fill
from ..shared.text import draw_game_text_traced as draw_text_traced
from ..shared.layout import apply_games_layout_jitter_to_bbox, resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import (
    draw_panel_grid_cell,
    draw_panel_option_card,
    make_panel_scene_background,
    resolve_game_panel_scene_style,
)
from ..shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "tetris"
SCENE_ID = "tetris"

QUERY_LINE_CLEAR_COUNT = "line_clear_count"
QUERY_DROP_RESULT_LABEL = "drop_result_label"
QUERY_ROW_OCCUPANCY_STATUS_COUNT = "row_occupancy_status_count"
QUERY_DROP_COLLISION_TIME_VALUE = "drop_collision_time_value"
QUERY_EDGE_OCCUPIED_ROW_CELL_COUNT = "edge_occupied_row_cell_count"

SUPPORTED_PUBLIC_QUERIES: Tuple[str, ...] = (
    QUERY_LINE_CLEAR_COUNT,
    QUERY_DROP_RESULT_LABEL,
    QUERY_ROW_OCCUPANCY_STATUS_COUNT,
    QUERY_DROP_COLLISION_TIME_VALUE,
    QUERY_EDGE_OCCUPIED_ROW_CELL_COUNT,
)
LINE_CLEAR_BRANCHES: Tuple[str, ...] = (
    "max_clear_with_next_piece",
)
DROP_RESULT_BRANCHES: Tuple[str, ...] = (
    "no_clear_result",
    "single_clear_result",
    "multi_clear_result",
)
ROW_OCCUPANCY_BRANCHES: Tuple[str, ...] = (
    "full_row_count",
    "one_gap_row_count",
)
DROP_COLLISION_TIME_BRANCHES: Tuple[str, ...] = (
    "no_shift_collision_time",
    "left_shift_collision_time",
    "right_shift_collision_time",
)
EDGE_OCCUPIED_ROW_BRANCHES: Tuple[str, ...] = (
    "top_occupied_row_filled_cell_count",
    "top_occupied_row_empty_cell_count",
    "bottom_occupied_row_filled_cell_count",
    "bottom_occupied_row_empty_cell_count",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("low_stack", "notched_stack", "high_stack")
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic_blocks",
    "beveled_blocks",
    "paper_tiles",
    "glass_blocks",
    "neon_blocks",
)
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

EMPTY = "."
Coord = Tuple[int, int]
Board = Tuple[Tuple[str, ...], ...]


RAW_TETROMINOES: Dict[str, Tuple[Tuple[Coord, ...], ...]] = {
    "I": (
        ((0, 0), (0, 1), (0, 2), (0, 3)),
        ((0, 0), (1, 0), (2, 0), (3, 0)),
    ),
    "O": (
        ((0, 0), (0, 1), (1, 0), (1, 1)),
    ),
    "T": (
        ((0, 0), (0, 1), (0, 2), (1, 1)),
        ((0, 1), (1, 0), (1, 1), (2, 1)),
        ((0, 1), (1, 0), (1, 1), (1, 2)),
        ((0, 0), (1, 0), (1, 1), (2, 0)),
    ),
    "L": (
        ((0, 0), (1, 0), (2, 0), (2, 1)),
        ((0, 0), (0, 1), (0, 2), (1, 0)),
        ((0, 0), (0, 1), (1, 1), (2, 1)),
        ((0, 2), (1, 0), (1, 1), (1, 2)),
    ),
    "J": (
        ((0, 1), (1, 1), (2, 0), (2, 1)),
        ((0, 0), (1, 0), (1, 1), (1, 2)),
        ((0, 0), (0, 1), (1, 0), (2, 0)),
        ((0, 0), (0, 1), (0, 2), (1, 2)),
    ),
    "S": (
        ((0, 1), (0, 2), (1, 0), (1, 1)),
        ((0, 0), (1, 0), (1, 1), (2, 1)),
    ),
    "Z": (
        ((0, 0), (0, 1), (1, 1), (1, 2)),
        ((0, 1), (1, 0), (1, 1), (2, 0)),
    ),
}

PIECE_ORDER: Tuple[str, ...] = tuple(RAW_TETROMINOES)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Tetris tasks."""

    line_clear_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    drop_result_clear_count_support: Tuple[int, ...] = (0, 1, 2)
    row_occupancy_status_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    drop_collision_time_support: Tuple[int, ...] = tuple(range(0, 9))
    edge_occupied_row_cell_count_support: Tuple[int, ...] = tuple(range(0, 12))
    shift_magnitude_support: Tuple[int, ...] = (1, 2, 3)
    option_count_support: Tuple[int, ...] = (4, 6)
    board_row_count_support: Tuple[int, ...] = tuple(range(10, 16))
    board_col_count_support: Tuple[int, ...] = tuple(range(7, 12))
    canvas_width: int = 1100
    canvas_height: int = 990
    panel_margin_px: int = 42
    board_gap_px: int = 34
    cell_size_px: int = 24
    line_cell_size_px: int = 34
    cell_gap_px: int = 2
    panel_pad_px: int = 12
    label_band_height_px: int = 28
    cell_outline_width_px: int = 1
    ghost_outline_width_px: int = 4
    label_font_size_px: int = 20
    small_label_font_size_px: int = 15


@dataclass(frozen=True)
class _Placement:
    """One hard-dropped tetromino placement."""

    piece: str
    orientation_index: int
    col: int
    top: int

    @property
    def entity_id(self) -> str:
        return f"placement_{self.piece.lower()}_{self.orientation_index}_{self.col}_{self.top}"


@dataclass(frozen=True)
class _Outcome:
    """Result of locking one placement."""

    placement: _Placement
    clear_count: int
    locked_board: Board
    result_board: Board
    locked_cells: Tuple[Coord, ...]
    cleared_rows: Tuple[int, ...]
    holes_after: int
    max_height_after: int
    aggregate_height_after: int


@dataclass(frozen=True)
class _DropCollision:
    """Result of shifting a falling piece and dropping until collision."""

    start_placement: _Placement
    shifted_placement: _Placement
    final_placement: _Placement
    drop_steps: int
    blocker_cells: Tuple[Coord, ...]
    bottom_contact_cells: Tuple[Coord, ...]
    collision_kind: str


@dataclass(frozen=True)
class _Option:
    """One labeled Tetris option panel."""

    label: str
    board: Board
    placement: _Placement | None
    outcome: _Outcome | None
    is_answer: bool
    metric_value: int | None = None

    @property
    def entity_id(self) -> str:
        return f"option_{self.label.lower()}"


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic/rendering axes for one instance."""

    public_query: str
    query_id: str
    scene_variant: str
    style_variant: str
    target_clear_count: int | None
    target_row_count: int | None
    target_drop_steps: int | None
    target_cell_count: int | None
    shift_delta: int
    option_count: int
    board_rows: int
    board_cols: int
    target_label: str | None
    query_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    shift_delta_probabilities: Dict[str, float]
    option_count_probabilities: Dict[str, float]
    board_row_probabilities: Dict[str, float]
    board_col_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderParams:
    """Resolved Tetris rendering controls."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    board_gap_px: int
    cell_size_px: int
    line_cell_size_px: int
    cell_gap_px: int
    panel_pad_px: int
    label_band_height_px: int
    cell_outline_width_px: int
    ghost_outline_width_px: int
    label_font_size_px: int
    small_label_font_size_px: int
    font_family: str
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Sample:
    """One generated Tetris task sample."""

    answer: int | str
    answer_type: str
    board: Board
    piece: str
    preview_orientation_index: int
    placement: _Placement | None
    falling_placement: _Placement | None
    outcome: _Outcome | None
    options: Tuple[_Option, ...]
    annotation_entity_ids: Tuple[str, ...]
    annotation_kind: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered Tetris scene and trace maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id="games_tetris_base",
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _normalize_shape(cells: Iterable[Coord]) -> Tuple[Coord, ...]:
    rows = [int(r) for r, _c in cells]
    cols = [int(c) for _r, c in cells]
    min_row = min(rows)
    min_col = min(cols)
    return tuple(sorted((int(r) - min_row, int(c) - min_col) for r, c in cells))


TETROMINOES: Dict[str, Tuple[Tuple[Coord, ...], ...]] = {
    piece: tuple(dict.fromkeys(_normalize_shape(shape) for shape in orientations))
    for piece, orientations in RAW_TETROMINOES.items()
}


def _shape(placement: _Placement) -> Tuple[Coord, ...]:
    return TETROMINOES[str(placement.piece)][int(placement.orientation_index)]


def _shape_size(shape: Sequence[Coord]) -> Tuple[int, int]:
    return (max(int(r) for r, _c in shape) + 1, max(int(c) for _r, c in shape) + 1)


def _board_size(board: Board) -> Tuple[int, int]:
    rows = len(board)
    cols = len(board[0]) if rows else 0
    return int(rows), int(cols)


def _empty_board(*, rows: int, cols: int) -> Board:
    return tuple(tuple(EMPTY for _ in range(int(cols))) for _ in range(int(rows)))


def _freeze(rows: Sequence[Sequence[str]]) -> Board:
    return tuple(tuple(str(cell) for cell in row) for row in rows)


def _piece_cells(placement: _Placement) -> Tuple[Coord, ...]:
    return tuple(
        sorted((int(placement.top) + int(r), int(placement.col) + int(c)) for r, c in _shape(placement))
    )


def _valid_cells(board: Board, cells: Sequence[Coord]) -> bool:
    board_rows, board_cols = _board_size(board)
    return all(0 <= int(r) < board_rows and 0 <= int(c) < board_cols for r, c in cells)


def _can_place(board: Board, placement: _Placement) -> bool:
    cells = _piece_cells(placement)
    return _valid_cells(board, cells) and all(board[int(r)][int(c)] == EMPTY for r, c in cells)


def _hard_drop_top(board: Board, *, piece: str, orientation_index: int, col: int) -> int | None:
    board_rows, _board_cols = _board_size(board)
    shape = TETROMINOES[str(piece)][int(orientation_index)]
    height, _width = _shape_size(shape)
    top_min = -height + 1
    last_valid: int | None = None
    for top in range(top_min, board_rows):
        placement = _Placement(str(piece), int(orientation_index), int(col), int(top))
        cells = _piece_cells(placement)
        if not _valid_cells(board, cells):
            continue
        if all(board[int(r)][int(c)] == EMPTY for r, c in cells):
            last_valid = int(top)
            continue
        if last_valid is not None:
            break
    return last_valid


def _lock_piece(board: Board, placement: _Placement) -> Board:
    rows = [list(row) for row in board]
    for row, col in _piece_cells(placement):
        rows[int(row)][int(col)] = str(placement.piece)
    return _freeze(rows)


def _clear_full_rows(board: Board) -> Tuple[Board, Tuple[int, ...]]:
    _board_rows, board_cols = _board_size(board)
    full_rows = tuple(index for index, row in enumerate(board) if all(cell != EMPTY for cell in row))
    kept = [list(row) for index, row in enumerate(board) if index not in set(full_rows)]
    new_rows = [[EMPTY for _ in range(board_cols)] for _ in range(len(full_rows))] + kept
    return _freeze(new_rows), tuple(int(v) for v in full_rows)


def _column_heights(board: Board) -> Tuple[int, ...]:
    board_rows, board_cols = _board_size(board)
    heights: List[int] = []
    for col in range(board_cols):
        height = 0
        for row in range(board_rows):
            if board[row][col] != EMPTY:
                height = board_rows - row
                break
        heights.append(int(height))
    return tuple(heights)


def _hole_count(board: Board) -> int:
    board_rows, board_cols = _board_size(board)
    holes = 0
    for col in range(board_cols):
        seen_block = False
        for row in range(board_rows):
            if board[row][col] != EMPTY:
                seen_block = True
            elif seen_block:
                holes += 1
    return int(holes)


def _evaluate_outcome(board: Board, placement: _Placement) -> _Outcome:
    locked = _lock_piece(board, placement)
    result, cleared_rows = _clear_full_rows(locked)
    heights = _column_heights(result)
    return _Outcome(
        placement=placement,
        clear_count=len(cleared_rows),
        locked_board=locked,
        result_board=result,
        locked_cells=_piece_cells(placement),
        cleared_rows=tuple(int(v) for v in cleared_rows),
        holes_after=_hole_count(result),
        max_height_after=max(heights) if heights else 0,
        aggregate_height_after=sum(heights),
    )


def _shifted_placement(placement: _Placement, *, shift_delta: int) -> _Placement:
    return _Placement(
        str(placement.piece),
        int(placement.orientation_index),
        int(placement.col) + int(shift_delta),
        int(placement.top),
    )


def _drop_collision(board: Board, placement: _Placement, *, shift_delta: int) -> _DropCollision | None:
    shifted = _shifted_placement(placement, shift_delta=int(shift_delta))
    if not _can_place(board, shifted):
        return None
    current = shifted
    drop_steps = 0
    while True:
        candidate = _Placement(
            str(current.piece),
            int(current.orientation_index),
            int(current.col),
            int(current.top) + 1,
        )
        if _can_place(board, candidate):
            current = candidate
            drop_steps += 1
            continue
        board_rows, _board_cols = _board_size(board)
        current_cells = set(_piece_cells(current))
        blocker_cells: List[Coord] = []
        bottom_contact_cells: List[Coord] = []
        for row, col in current_cells:
            below = (int(row) + 1, int(col))
            if below in current_cells:
                continue
            if int(row) + 1 >= int(board_rows):
                bottom_contact_cells.append((int(row), int(col)))
            elif board[int(row) + 1][int(col)] != EMPTY:
                blocker_cells.append((int(row) + 1, int(col)))
        if blocker_cells:
            collision_kind = "locked_block"
        elif bottom_contact_cells:
            collision_kind = "bottom_boundary"
        else:
            return None
        return _DropCollision(
            start_placement=placement,
            shifted_placement=shifted,
            final_placement=current,
            drop_steps=int(drop_steps),
            blocker_cells=tuple(sorted(set(blocker_cells))),
            bottom_contact_cells=tuple(sorted(set(bottom_contact_cells))),
            collision_kind=str(collision_kind),
        )


def _all_placements(board: Board, *, piece: str) -> Tuple[_Placement, ...]:
    _board_rows, board_cols = _board_size(board)
    placements: List[_Placement] = []
    for orientation_index, shape in enumerate(TETROMINOES[str(piece)]):
        _height, width = _shape_size(shape)
        for col in range(0, board_cols - int(width) + 1):
            top = _hard_drop_top(board, piece=str(piece), orientation_index=int(orientation_index), col=int(col))
            if top is None:
                continue
            placement = _Placement(str(piece), int(orientation_index), int(col), int(top))
            if _can_place(board, placement):
                placements.append(placement)
    return tuple(placements)


def _sample_label(instance_seed: int, *, namespace: str, labels: Sequence[str] = OPTION_LABELS) -> Tuple[str, Dict[str, float]]:
    values = tuple(str(label) for label in labels)
    if not values:
        raise ValueError("labels must not be empty")
    rng = spawn_rng(int(instance_seed), str(namespace))
    offset = int(rng.randrange(len(values)))
    label = values[(int(instance_seed) + int(offset)) % len(values)]
    probability = 1.0 / float(len(values))
    return str(label), {str(value): float(probability) for value in values}


def _sample_named_axis(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(item) for item in supported),
    )


def _sample_integer_axis(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[int, Dict[str, float]]:
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=tuple(int(item) for item in fallback_support),
        namespace=f"{str(task_id)}.{str(namespace)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return int(value), {str(key): float(val) for key, val in probabilities.items()}


def _branches_for_public_query(public_query: str) -> Tuple[str, ...]:
    if str(public_query) == QUERY_LINE_CLEAR_COUNT:
        return LINE_CLEAR_BRANCHES
    if str(public_query) == QUERY_DROP_RESULT_LABEL:
        return DROP_RESULT_BRANCHES
    if str(public_query) == QUERY_ROW_OCCUPANCY_STATUS_COUNT:
        return ROW_OCCUPANCY_BRANCHES
    if str(public_query) == QUERY_DROP_COLLISION_TIME_VALUE:
        return DROP_COLLISION_TIME_BRANCHES
    if str(public_query) == QUERY_EDGE_OCCUPIED_ROW_CELL_COUNT:
        return EDGE_OCCUPIED_ROW_BRANCHES
    raise ValueError(f"unsupported public query: {public_query}")


def _resolve_axes(
    *,
    task_id: str,
    public_query: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedAxes:
    query_id, query_probabilities = _sample_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{public_query}.query",
        explicit_key="query_id",
        weights_key=f"{public_query}_query_weights",
        balance_flag_key="balanced_query_sampling",
        supported=_branches_for_public_query(str(public_query)),
    )
    scene_variant, scene_variant_probabilities = _sample_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _sample_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_STYLE_VARIANTS,
    )
    option_count, option_count_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=_DEFAULTS.option_count_support,
        namespace=f"{public_query}.option_count",
        balanced_flag_key="balanced_option_count_sampling",
    )
    board_rows, board_row_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="board_row_count_support",
        explicit_key="board_rows",
        fallback_support=_DEFAULTS.board_row_count_support,
        namespace=f"{public_query}.board_rows",
        balanced_flag_key="balanced_board_size_sampling",
    )
    board_cols, board_col_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="board_col_count_support",
        explicit_key="board_cols",
        fallback_support=_DEFAULTS.board_col_count_support,
        namespace=f"{public_query}.board_cols",
        balanced_flag_key="balanced_board_size_sampling",
    )
    target_clear_count: int | None = None
    target_row_count: int | None = None
    target_drop_steps: int | None = None
    target_cell_count: int | None = None
    shift_delta = 0
    shift_delta_probabilities: Dict[str, float] = {"0": 1.0}
    answer_probabilities: Dict[str, float]
    target_label: str | None = None
    if str(public_query) == QUERY_LINE_CLEAR_COUNT:
        target_clear_count, answer_probabilities = _sample_integer_axis(
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            support_key="line_clear_count_support",
            explicit_key="target_clear_count",
            fallback_support=_DEFAULTS.line_clear_count_support,
            namespace=f"{public_query}.target_clear_count.{query_id}",
            balanced_flag_key="balanced_target_answer_sampling",
        )
    elif str(public_query) == QUERY_DROP_RESULT_LABEL:
        support = _DEFAULTS.drop_result_clear_count_support
        if str(query_id) == "no_clear_result":
            support = (0,)
        elif str(query_id) == "single_clear_result":
            support = (1,)
        elif str(query_id) == "multi_clear_result":
            support = (2,)
        target_clear_count, _clear_prob = _sample_integer_axis(
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params={**dict(params), "drop_result_clear_count_support": list(support)},
            support_key="drop_result_clear_count_support",
            explicit_key="target_clear_count",
            fallback_support=support,
            namespace=f"{public_query}.target_clear_count.{query_id}",
            balanced_flag_key="balanced_target_clear_count_sampling",
        )
        target_label, answer_probabilities = _sample_label(
            int(instance_seed),
            namespace=f"{task_id}.{public_query}.target_label",
            labels=OPTION_LABELS[: int(option_count)],
        )
    elif str(public_query) == QUERY_ROW_OCCUPANCY_STATUS_COUNT:
        target_row_count, answer_probabilities = _sample_integer_axis(
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            support_key="row_occupancy_status_count_support",
            explicit_key="target_row_count",
            fallback_support=_DEFAULTS.row_occupancy_status_count_support,
            namespace=f"{public_query}.target_row_count.{query_id}",
            balanced_flag_key="balanced_target_answer_sampling",
        )
    elif str(public_query) == QUERY_DROP_COLLISION_TIME_VALUE:
        target_drop_steps, answer_probabilities = _sample_integer_axis(
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            support_key="drop_collision_time_support",
            explicit_key="target_drop_steps",
            fallback_support=_DEFAULTS.drop_collision_time_support,
            namespace=f"{public_query}.target_drop_steps.{query_id}",
            balanced_flag_key="balanced_target_answer_sampling",
        )
        if str(query_id) == "left_shift_collision_time":
            magnitude, magnitude_probabilities = _sample_integer_axis(
                task_id=str(task_id),
                instance_seed=int(instance_seed),
                params=params,
                support_key="shift_magnitude_support",
                explicit_key="shift_magnitude",
                fallback_support=_DEFAULTS.shift_magnitude_support,
                namespace=f"{public_query}.shift_magnitude.{query_id}",
                balanced_flag_key="balanced_shift_magnitude_sampling",
            )
            shift_delta = -int(magnitude)
            shift_delta_probabilities = {str(-int(key)): float(value) for key, value in magnitude_probabilities.items()}
        elif str(query_id) == "right_shift_collision_time":
            magnitude, magnitude_probabilities = _sample_integer_axis(
                task_id=str(task_id),
                instance_seed=int(instance_seed),
                params=params,
                support_key="shift_magnitude_support",
                explicit_key="shift_magnitude",
                fallback_support=_DEFAULTS.shift_magnitude_support,
                namespace=f"{public_query}.shift_magnitude.{query_id}",
                balanced_flag_key="balanced_shift_magnitude_sampling",
            )
            shift_delta = int(magnitude)
            shift_delta_probabilities = {str(int(key)): float(value) for key, value in magnitude_probabilities.items()}
    elif str(public_query) == QUERY_EDGE_OCCUPIED_ROW_CELL_COUNT:
        if "filled_cell_count" in str(query_id):
            support = tuple(range(1, int(board_cols) + 1))
        else:
            support = tuple(range(0, int(board_cols)))
        configured_support = tuple(
            int(value)
            for value in group_default(
                _GEN_DEFAULTS,
                "edge_occupied_row_cell_count_support",
                _DEFAULTS.edge_occupied_row_cell_count_support,
            )
        )
        feasible_support = tuple(value for value in configured_support if value in set(support))
        if not feasible_support:
            feasible_support = support
        target_cell_count, answer_probabilities = _sample_integer_axis(
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params={**dict(params), "edge_occupied_row_cell_count_support": list(feasible_support)},
            support_key="edge_occupied_row_cell_count_support",
            explicit_key="target_cell_count",
            fallback_support=feasible_support,
            namespace=f"{public_query}.target_cell_count.{query_id}",
            balanced_flag_key="balanced_target_answer_sampling",
        )
    return _ResolvedAxes(
        public_query=str(public_query),
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_clear_count=None if target_clear_count is None else int(target_clear_count),
        target_row_count=None if target_row_count is None else int(target_row_count),
        target_drop_steps=None if target_drop_steps is None else int(target_drop_steps),
        target_cell_count=None if target_cell_count is None else int(target_cell_count),
        shift_delta=int(shift_delta),
        option_count=int(option_count),
        board_rows=int(board_rows),
        board_cols=int(board_cols),
        target_label=target_label,
        query_probabilities=dict(query_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        answer_probabilities=dict(answer_probabilities),
        shift_delta_probabilities=dict(shift_delta_probabilities),
        option_count_probabilities=dict(option_count_probabilities),
        board_row_probabilities=dict(board_row_probabilities),
        board_col_probabilities=dict(board_col_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    layout_jitter = resolve_games_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.tetris.layout",
    )
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.tetris.font_family",
        params=params,
    )
    return _RenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        board_gap_px=int(params.get("board_gap_px", group_default(_RENDER_DEFAULTS, "board_gap_px", _DEFAULTS.board_gap_px))),
        cell_size_px=int(params.get("cell_size_px", group_default(_RENDER_DEFAULTS, "cell_size_px", _DEFAULTS.cell_size_px))),
        line_cell_size_px=int(params.get("line_cell_size_px", group_default(_RENDER_DEFAULTS, "line_cell_size_px", _DEFAULTS.line_cell_size_px))),
        cell_gap_px=int(params.get("cell_gap_px", group_default(_RENDER_DEFAULTS, "cell_gap_px", _DEFAULTS.cell_gap_px))),
        panel_pad_px=int(params.get("panel_pad_px", group_default(_RENDER_DEFAULTS, "panel_pad_px", _DEFAULTS.panel_pad_px))),
        label_band_height_px=int(params.get("label_band_height_px", group_default(_RENDER_DEFAULTS, "label_band_height_px", _DEFAULTS.label_band_height_px))),
        cell_outline_width_px=int(params.get("cell_outline_width_px", group_default(_RENDER_DEFAULTS, "cell_outline_width_px", _DEFAULTS.cell_outline_width_px))),
        ghost_outline_width_px=int(params.get("ghost_outline_width_px", group_default(_RENDER_DEFAULTS, "ghost_outline_width_px", _DEFAULTS.ghost_outline_width_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        small_label_font_size_px=int(params.get("small_label_font_size_px", group_default(_RENDER_DEFAULTS, "small_label_font_size_px", _DEFAULTS.small_label_font_size_px))),
        font_family=str(font_family),
        layout_jitter_meta=dict(layout_jitter),
    )


def _piece_color(piece: str, *, style_variant: str, state_colors: Sequence[Sequence[int]]) -> Tuple[int, int, int]:
    palettes: Dict[str, Dict[str, Tuple[int, int, int]]] = {
        "classic_blocks": {
            "I": (38, 180, 210),
            "O": (239, 193, 50),
            "T": (154, 90, 204),
            "S": (78, 174, 86),
            "Z": (220, 72, 82),
            "J": (65, 112, 210),
            "L": (230, 145, 52),
        },
        "beveled_blocks": {
            "I": (33, 166, 196),
            "O": (226, 177, 42),
            "T": (142, 82, 190),
            "S": (64, 156, 78),
            "Z": (207, 63, 78),
            "J": (54, 103, 194),
            "L": (218, 126, 42),
        },
        "paper_tiles": {
            "I": (88, 166, 184),
            "O": (214, 178, 86),
            "T": (151, 113, 174),
            "S": (105, 166, 112),
            "Z": (195, 102, 107),
            "J": (95, 128, 188),
            "L": (206, 142, 82),
        },
        "glass_blocks": {
            "I": (76, 200, 224),
            "O": (248, 208, 74),
            "T": (182, 112, 228),
            "S": (96, 204, 112),
            "Z": (244, 96, 112),
            "J": (88, 138, 232),
            "L": (248, 166, 72),
        },
        "neon_blocks": {
            "I": (42, 230, 244),
            "O": (255, 228, 78),
            "T": (210, 96, 255),
            "S": (86, 242, 126),
            "Z": (255, 86, 116),
            "J": (92, 164, 255),
            "L": (255, 172, 70),
        },
    }
    fallback = palettes["classic_blocks"]
    palette = palettes.get(str(style_variant), fallback)
    if str(style_variant) == "panel_state_colors":
        index = PIECE_ORDER.index(str(piece)) if str(piece) in PIECE_ORDER else 0
        if len(state_colors) >= len(PIECE_ORDER):
            return tuple(int(v) for v in state_colors[index % len(state_colors)])
    return palette.get(str(piece), (110, 130, 155))


def _draw_tetris_block(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    fill: Sequence[int],
    style,
    params: _RenderParams,
    style_variant: str,
    outline: Sequence[int] | None = None,
) -> None:
    """Draw one locked Tetris block with scene-local nonsemantic styling."""

    fill_rgb = tuple(int(v) for v in fill)
    draw_panel_grid_cell(
        draw,
        bbox=bbox,
        fill=fill_rgb,
        style=style,
        outline=outline or style.grid_rgb,
        width=int(params.cell_outline_width_px),
    )
    x0, y0, x1, y1 = [int(v) for v in bbox]
    inset = max(2, int(round(min(x1 - x0, y1 - y0) * 0.14)))
    variant = str(style_variant)
    if variant == "beveled_blocks":
        highlight = tuple(min(255, int(v) + 54) for v in fill_rgb)
        shadow = tuple(max(0, int(v) - 64) for v in fill_rgb)
        draw.line((x0 + inset, y0 + inset, x1 - inset, y0 + inset), fill=highlight, width=2)
        draw.line((x0 + inset, y0 + inset, x0 + inset, y1 - inset), fill=highlight, width=2)
        draw.line((x0 + inset, y1 - inset, x1 - inset, y1 - inset), fill=shadow, width=2)
        draw.line((x1 - inset, y0 + inset, x1 - inset, y1 - inset), fill=shadow, width=2)
    elif variant == "paper_tiles":
        accent = tuple(max(0, int(v) - 42) for v in fill_rgb)
        draw.line((x0 + inset, y1 - inset, x1 - inset, y0 + inset), fill=accent, width=1)
    elif variant == "glass_blocks":
        draw.rounded_rectangle(
            (x0 + inset, y0 + inset, x1 - inset, y0 + max(inset + 2, (y1 - y0) // 2)),
            radius=max(2, inset),
            fill=(255, 255, 255, 72),
            outline=None,
        )
    elif variant == "neon_blocks":
        glow = tuple(min(255, int(v) + 40) for v in fill_rgb)
        draw.rounded_rectangle(
            (x0 + 2, y0 + 2, x1 - 2, y1 - 2),
            radius=max(3, inset),
            outline=glow + (230,),
            width=max(2, int(params.cell_outline_width_px) + 1),
        )


def _random_piece_with_min_rows(rng, *, min_rows: int) -> Tuple[str, int]:
    candidates: List[Tuple[str, int]] = []
    for piece, orientations in TETROMINOES.items():
        for orientation_index, shape in enumerate(orientations):
            distinct_rows = len({int(r) for r, _c in shape})
            if distinct_rows >= int(min_rows):
                candidates.append((str(piece), int(orientation_index)))
    if not candidates:
        raise ValueError("no tetromino can cover requested row count")
    return tuple(rng.choice(candidates))  # type: ignore[return-value]


def _avoid_prefilled_full_rows(rows: List[List[str]], *, protected_empty: set[Coord], rng) -> None:
    board_rows = len(rows)
    board_cols = len(rows[0]) if board_rows else 0
    for row_index in range(board_rows):
        if all(cell != EMPTY for cell in rows[row_index]):
            candidates = [col for col in range(board_cols) if (row_index, col) not in protected_empty]
            if candidates:
                rows[row_index][int(rng.choice(candidates))] = EMPTY


def _supported_stack_generation_meta(*, strategy: str) -> Dict[str, Any]:
    """Return trace metadata for the visually-supported Tetris stack policy."""

    return {
        "board_generation": {
            "mode": "natural_supported_stack",
            "strategy": str(strategy),
            "cell_support_policy": "every locked cell is supported by the bottom or a locked cell below",
        }
    }


def _is_supported_stack_board(board: Board) -> bool:
    """Return whether every occupied board cell has vertical support."""

    board_rows, board_cols = _board_size(board)
    for row in range(board_rows - 1):
        for col in range(board_cols):
            if board[row][col] != EMPTY and board[row + 1][col] == EMPTY:
                return False
    return True


def _fill_supported_column(
    rows: List[List[str]],
    *,
    col: int,
    top_row: int,
    rng,
    protected_empty: set[Coord] | None = None,
) -> None:
    """Fill one column from bottom up to ``top_row`` without crossing protected gaps."""

    protected = set(protected_empty or set())
    board_rows = len(rows)
    if board_rows <= 0:
        return
    top = max(0, min(int(top_row), board_rows - 1))
    for row in range(board_rows - 1, top - 1, -1):
        coord = (int(row), int(col))
        if coord in protected:
            break
        if rows[int(row)][int(col)] == EMPTY:
            rows[int(row)][int(col)] = str(rng.choice(PIECE_ORDER))


def _supported_stack_from_heights(
    rng,
    *,
    board_rows: int,
    board_cols: int,
    heights: Sequence[int],
    protected_empty: set[Coord] | None = None,
) -> Board:
    """Build a board from contiguous per-column heights."""

    rows = [[EMPTY for _ in range(int(board_cols))] for _ in range(int(board_rows))]
    protected = set(protected_empty or set())
    for col in range(int(board_cols)):
        height = max(0, min(int(heights[int(col)]), int(board_rows)))
        if height <= 0:
            continue
        top = int(board_rows) - int(height)
        _fill_supported_column(rows, col=int(col), top_row=int(top), rng=rng, protected_empty=protected)
    board = _freeze(rows)
    if not _is_supported_stack_board(board):
        raise ValueError("constructed unsupported Tetris stack")
    return board


def _random_supported_heights(
    rng,
    *,
    scene_variant: str,
    board_rows: int,
    board_cols: int,
    force_gap_column: bool = True,
) -> List[int]:
    """Sample contiguous column heights for a natural-looking static stack."""

    height_low, height_high = {
        "low_stack": (1, 3),
        "notched_stack": (2, 5),
        "high_stack": (3, 6),
    }.get(str(scene_variant), (2, 5))
    capped_high = min(int(height_high), max(1, int(board_rows) - 2))
    capped_low = min(int(height_low), capped_high)
    heights = [int(rng.randint(capped_low, capped_high)) for _ in range(int(board_cols))]
    if force_gap_column and heights:
        gap_col = int(rng.randrange(int(board_cols)))
        heights[gap_col] = 0
    return heights


def _construct_board_with_target_clear(
    rng,
    *,
    target_clear_count: int,
    scene_variant: str,
    board_rows: int,
    board_cols: int,
) -> Tuple[Board, _Placement, _Outcome]:
    target = int(target_clear_count)
    if target > 0:
        # Use the canonical vertical-I well for exact 1..4-line clear
        # construction. This preserves a coherent supported stack while keeping
        # the answer balanced across the configured clear-count support.
        piece = "I"
        orientation_index = 1
        shape = TETROMINOES[piece][orientation_index]
        height, width = _shape_size(shape)
        if int(height) > int(board_rows) or int(width) > int(board_cols):
            raise ValueError("board is too small for Tetris clear-count construction")
        gap_col = int(rng.randint(0, int(board_cols) - int(width)))
        top = int(board_rows) - int(height)
        placement = _Placement(piece, int(orientation_index), int(gap_col), int(top))
        piece_cells = set(_piece_cells(placement))
        notch_candidates = [col for col in range(int(board_cols)) if int(col) != int(gap_col)]
        if not notch_candidates:
            raise ValueError("board is too narrow for Tetris clear-count construction")
        notch_col = int(rng.choice(notch_candidates))
        heights: List[int] = []
        for col in range(int(board_cols)):
            if int(col) == int(gap_col):
                heights.append(0)
                continue
            min_height = int(target)
            max_extra = {
                "low_stack": 1,
                "notched_stack": 2,
                "high_stack": 3,
            }.get(str(scene_variant), 2)
            max_height = min(int(height), int(target) + int(max_extra))
            if int(col) == int(notch_col):
                heights.append(int(target))
            else:
                heights.append(int(rng.randint(min_height, max_height)))
        board = _supported_stack_from_heights(
            rng,
            board_rows=int(board_rows),
            board_cols=int(board_cols),
            heights=heights,
            protected_empty=piece_cells,
        )
        dropped_top = _hard_drop_top(board, piece=piece, orientation_index=int(orientation_index), col=int(gap_col))
        if dropped_top != int(top):
            raise ValueError("guided Tetris well did not produce expected hard-drop top")
        outcome = _evaluate_outcome(board, placement)
        if int(outcome.clear_count) != int(target):
            raise ValueError(f"guided Tetris well produced {outcome.clear_count} clears instead of {target}")
        return board, placement, outcome

    for _attempt in range(900):
        piece, orientation_index = _random_piece_with_min_rows(rng, min_rows=1)
        shape = TETROMINOES[str(piece)][int(orientation_index)]
        height, width = _shape_size(shape)
        if int(width) > int(board_cols) or int(height) > int(board_rows):
            continue
        col = int(rng.randint(0, int(board_cols) - int(width)))
        board = _random_stack_board(
            rng,
            scene_variant=str(scene_variant),
            board_rows=int(board_rows),
            board_cols=int(board_cols),
        )
        dropped_top = _hard_drop_top(board, piece=str(piece), orientation_index=int(orientation_index), col=int(col))
        if dropped_top is None:
            continue
        placement = _Placement(str(piece), int(orientation_index), int(col), int(dropped_top))
        outcome = _evaluate_outcome(board, placement)
        if int(outcome.clear_count) == int(target):
            return board, placement, outcome
    raise ValueError(f"failed to construct Tetris board for clear count {target}")


def _random_stack_board(rng, *, scene_variant: str, board_rows: int, board_cols: int) -> Board:
    heights = _random_supported_heights(
        rng,
        scene_variant=str(scene_variant),
        board_rows=int(board_rows),
        board_cols=int(board_cols),
        force_gap_column=True,
    )
    return _supported_stack_from_heights(
        rng,
        board_rows=int(board_rows),
        board_cols=int(board_cols),
        heights=heights,
    )


def _board_key(board: Board) -> Tuple[Tuple[str, ...], ...]:
    return tuple(tuple(row) for row in board)


def _best_clear_outcomes(board: Board, *, piece: str) -> Tuple[int, Tuple[_Outcome, ...]]:
    outcomes = tuple(_evaluate_outcome(board, placement) for placement in _all_placements(board, piece=str(piece)))
    if not outcomes:
        return 0, ()
    best = max(int(outcome.clear_count) for outcome in outcomes)
    return int(best), tuple(outcome for outcome in outcomes if int(outcome.clear_count) == int(best))


def _make_line_clear_sample(rng, axes: _ResolvedAxes) -> _Sample:
    target = int(axes.target_clear_count or 0)
    for _attempt in range(1200):
        board, base_placement, _base_outcome = _construct_board_with_target_clear(
            rng,
            target_clear_count=target,
            scene_variant=str(axes.scene_variant),
            board_rows=int(axes.board_rows),
            board_cols=int(axes.board_cols),
        )
        piece = str(base_placement.piece)
        best_clear, best_outcomes = _best_clear_outcomes(board, piece=piece)
        if int(best_clear) != int(target) or not best_outcomes:
            continue
        best_outcome = sorted(
            best_outcomes,
            key=lambda outcome: (int(outcome.holes_after), int(outcome.max_height_after), int(outcome.placement.col)),
        )[0]
        return _Sample(
            answer=int(best_clear),
            answer_type="integer",
            board=board,
            piece=piece,
            preview_orientation_index=0,
            placement=best_outcome.placement,
            falling_placement=None,
            outcome=best_outcome,
            options=(),
            annotation_entity_ids=("main", "next_piece"),
            annotation_kind="board_and_next_piece",
            metadata={
                **_supported_stack_generation_meta(strategy="line_clear_guided_well" if target > 0 else "line_clear_supported_stack"),
                "drop_instruction": str(axes.query_id),
                "target_clear_count": int(best_clear),
                "best_clear_count": int(best_clear),
                "max_clear_placement_count": len(best_outcomes),
            },
        )
    raise ValueError("failed to construct Tetris max-clear sample")


def _uncleared_board_after_lock(outcome: _Outcome) -> Board:
    return outcome.locked_board


def _clear_without_gravity(outcome: _Outcome) -> Board:
    rows = [list(row) for row in outcome.locked_board]
    for row in outcome.cleared_rows:
        rows[int(row)] = [EMPTY for _ in range(len(rows[int(row)]))]
    return _freeze(rows)


def _mutated_result_board(rng, board: Board) -> Board:
    board_rows, board_cols = _board_size(board)
    return _random_stack_board(
        rng,
        scene_variant=str(rng.choice(SUPPORTED_SCENE_VARIANTS)),
        board_rows=int(board_rows),
        board_cols=int(board_cols),
    )


def _drop_result_distractor_boards(rng, board: Board, outcome: _Outcome) -> Tuple[Board, ...]:
    boards: List[Board] = []
    seen = {_board_key(outcome.result_board)}

    def add(candidate: Board) -> None:
        key = _board_key(candidate)
        if key not in seen:
            seen.add(key)
            boards.append(candidate)

    add(_uncleared_board_after_lock(outcome))
    for delta in (-1, 1, -2, 2):
        alt_top = _hard_drop_top(
            board,
            piece=str(outcome.placement.piece),
            orientation_index=int(outcome.placement.orientation_index),
            col=int(outcome.placement.col + delta),
        )
        if alt_top is not None:
            alt = _Placement(
                str(outcome.placement.piece),
                int(outcome.placement.orientation_index),
                int(outcome.placement.col + delta),
                int(alt_top),
            )
            if _can_place(board, alt):
                alt_board = _evaluate_outcome(board, alt).result_board
                if _is_supported_stack_board(alt_board):
                    add(alt_board)
    orientations = TETROMINOES[str(outcome.placement.piece)]
    for orientation_index in range(len(orientations)):
        if int(orientation_index) == int(outcome.placement.orientation_index):
            continue
        alt_top = _hard_drop_top(
            board,
            piece=str(outcome.placement.piece),
            orientation_index=int(orientation_index),
            col=int(outcome.placement.col),
        )
        if alt_top is not None:
            alt = _Placement(str(outcome.placement.piece), int(orientation_index), int(outcome.placement.col), int(alt_top))
            if _can_place(board, alt):
                alt_board = _evaluate_outcome(board, alt).result_board
                if _is_supported_stack_board(alt_board):
                    add(alt_board)
    while len(boards) < 8:
        add(_mutated_result_board(rng, boards[-1] if boards else outcome.locked_board))
    return tuple(boards)


def _make_drop_result_sample(rng, axes: _ResolvedAxes) -> _Sample:
    labels = OPTION_LABELS[: int(axes.option_count)]
    answer_label = str(axes.target_label or labels[0])
    board: Board | None = None
    placement: _Placement | None = None
    outcome: _Outcome | None = None
    falling_placement: _Placement | None = None
    for _attempt in range(900):
        board_candidate, placement_candidate, outcome_candidate = _construct_board_with_target_clear(
            rng,
            target_clear_count=int(axes.target_clear_count or 0),
            scene_variant=str(axes.scene_variant),
            board_rows=int(axes.board_rows),
            board_cols=int(axes.board_cols),
        )
        candidate_falling = _Placement(
            str(placement_candidate.piece),
            int(placement_candidate.orientation_index),
            int(placement_candidate.col),
            0,
        )
        if not _can_place(board_candidate, candidate_falling):
            continue
        board = board_candidate
        placement = placement_candidate
        outcome = outcome_candidate
        falling_placement = candidate_falling
        break
    if board is None or placement is None or outcome is None or falling_placement is None:
        raise ValueError("failed to construct Tetris fixed-drop sample")
    distractors = list(_drop_result_distractor_boards(rng, board, outcome))
    rng.shuffle(distractors)
    options: List[_Option] = []
    distractor_cursor = 0
    for label in labels:
        if str(label) == answer_label:
            options.append(_Option(str(label), outcome.result_board, None, outcome, True))
        else:
            options.append(_Option(str(label), distractors[distractor_cursor], None, None, False))
            distractor_cursor += 1
    return _Sample(
        answer=str(answer_label),
        answer_type="string",
        board=board,
        piece=str(placement.piece),
        preview_orientation_index=int(placement.orientation_index),
        placement=placement,
        falling_placement=falling_placement,
        outcome=outcome,
        options=tuple(options),
        annotation_entity_ids=(f"option_{answer_label.lower()}",),
        annotation_kind="option_panel",
        metadata={
            **_supported_stack_generation_meta(strategy="drop_result_guided_well" if int(outcome.clear_count) > 0 else "drop_result_supported_stack"),
            "target_clear_count": int(outcome.clear_count),
            "drop_result_branch": str(axes.query_id),
        },
    )


def _row_empty_count(row: Sequence[str]) -> int:
    """Return the number of empty cells in one Tetris row."""

    return sum(1 for cell in row if str(cell) == EMPTY)


def _row_qualifies_for_query(row: Sequence[str], *, query_id: str) -> bool:
    """Return whether one row satisfies the row-occupancy query."""

    empty_count = _row_empty_count(row)
    if str(query_id) == "full_row_count":
        return int(empty_count) == 0
    if str(query_id) == "one_gap_row_count":
        return int(empty_count) == 1
    raise ValueError(f"unsupported Tetris row-occupancy query: {query_id}")


def _qualifying_row_indices(board: Board, *, query_id: str) -> Tuple[int, ...]:
    """Return row indices satisfying the row-occupancy query."""

    return tuple(
        int(row_index)
        for row_index, row in enumerate(board)
        if _row_qualifies_for_query(row, query_id=str(query_id))
    )


def _make_row_with_empty_count(rng, *, board_cols: int, empty_count: int) -> Tuple[str, ...]:
    """Build one row with exactly `empty_count` empty cells."""

    empty_count = max(0, min(int(empty_count), int(board_cols)))
    row = [str(rng.choice(PIECE_ORDER)) for _ in range(int(board_cols))]
    for col in rng.sample(range(int(board_cols)), int(empty_count)):
        row[int(col)] = EMPTY
    return tuple(str(cell) for cell in row)


def _nonqualifying_empty_count(rng, *, query_id: str, board_cols: int, row_index: int, active_start: int) -> int:
    """Sample a row empty count that does not satisfy the active query."""

    board_cols = int(board_cols)
    top_band = int(row_index) < int(active_start)
    if str(query_id) == "full_row_count":
        if top_band:
            return int(rng.randint(max(1, board_cols - 2), board_cols))
        return int(rng.randint(1, min(board_cols, max(2, board_cols // 2 + 1))))
    if str(query_id) == "one_gap_row_count":
        if top_band:
            return int(rng.randint(min(2, board_cols), board_cols))
        choices = [0] + list(range(2, min(board_cols, max(3, board_cols // 2 + 1)) + 1))
        return int(rng.choice(choices))
    raise ValueError(f"unsupported Tetris row-occupancy query: {query_id}")


def _active_row_depth(scene_variant: str, *, board_rows: int) -> int:
    """Return the lower-board band used for denser static row-count patterns."""

    base_depth = {
        "low_stack": 6,
        "notched_stack": 8,
        "high_stack": 10,
    }.get(str(scene_variant), 8)
    return min(int(board_rows), max(5, int(base_depth)))


def _make_row_occupancy_sample(rng, axes: _ResolvedAxes) -> _Sample:
    """Construct one static Tetris board with an exact row-occupancy answer."""

    target = int(axes.target_row_count or 0)
    board_rows = int(axes.board_rows)
    board_cols = int(axes.board_cols)
    max_extra = {
        "low_stack": 2,
        "notched_stack": 4,
        "high_stack": 6,
    }.get(str(axes.scene_variant), 4)
    max_height = min(int(board_rows) - 2, int(target) + int(max_extra))
    if str(axes.query_id) == "full_row_count":
        if target <= 0:
            heights = _random_supported_heights(
                rng,
                scene_variant=str(axes.scene_variant),
                board_rows=int(board_rows),
                board_cols=int(board_cols),
                force_gap_column=True,
            )
            heights[int(rng.randrange(board_cols))] = 0
        else:
            heights = [
                int(rng.randint(int(target), max(int(target), int(max_height))))
                for _ in range(int(board_cols))
            ]
            heights[int(rng.randrange(board_cols))] = int(target)
        board = _supported_stack_from_heights(
            rng,
            board_rows=int(board_rows),
            board_cols=int(board_cols),
            heights=heights,
        )
    elif str(axes.query_id) == "one_gap_row_count":
        if target <= 0:
            first_gap = int(rng.randrange(board_cols))
            second_gap = int((first_gap + 1 + rng.randrange(max(1, board_cols - 1))) % board_cols)
            heights = [
                int(rng.randint(1, max(1, int(max_height))))
                for _ in range(int(board_cols))
            ]
            heights[first_gap] = 0
            heights[second_gap] = 0
        else:
            gap_col = int(rng.randrange(board_cols))
            stopper_candidates = [col for col in range(int(board_cols)) if int(col) != int(gap_col)]
            stopper_col = int(rng.choice(stopper_candidates))
            heights = [
                int(rng.randint(int(target), max(int(target), int(max_height))))
                for _ in range(int(board_cols))
            ]
            heights[gap_col] = 0
            heights[stopper_col] = int(target)
        board = _supported_stack_from_heights(
            rng,
            board_rows=int(board_rows),
            board_cols=int(board_cols),
            heights=heights,
        )
    else:
        raise ValueError(f"unsupported Tetris row-occupancy query: {axes.query_id}")
    qualifying_rows = _qualifying_row_indices(board, query_id=str(axes.query_id))
    if len(qualifying_rows) != int(target):
        raise ValueError("constructed Tetris row-occupancy board has wrong answer")
    return _Sample(
        answer=int(target),
        answer_type="integer",
        board=board,
        piece="",
        preview_orientation_index=0,
        placement=None,
        falling_placement=None,
        outcome=None,
        options=(),
        annotation_entity_ids=tuple(f"main_row_{int(row)}" for row in qualifying_rows),
        annotation_kind="row_set",
        metadata={
            **_supported_stack_generation_meta(strategy="row_occupancy_column_heights"),
            "target_row_count": int(target),
            "row_occupancy_query": str(axes.query_id),
            "qualifying_rows": [int(row) for row in qualifying_rows],
            "row_empty_counts": [int(_row_empty_count(row)) for row in board],
        },
    )


def _edge_occupied_row_index(board: Board, *, edge: str) -> int:
    """Return the topmost or bottommost occupied row index."""

    rows = range(len(board)) if str(edge) == "top" else range(len(board) - 1, -1, -1)
    for row in rows:
        if any(str(cell) != EMPTY for cell in board[int(row)]):
            return int(row)
    raise ValueError("Tetris board has no occupied row")


def _edge_row_query_parts(query_id: str) -> Tuple[str, str]:
    """Parse edge-row query id into row edge and counted cell status."""

    raw = str(query_id)
    if raw.startswith("top_occupied_row_"):
        edge = "top"
    elif raw.startswith("bottom_occupied_row_"):
        edge = "bottom"
    else:
        raise ValueError(f"unsupported Tetris edge-row query: {query_id}")
    if raw.endswith("_filled_cell_count"):
        status = "filled"
    elif raw.endswith("_empty_cell_count"):
        status = "empty"
    else:
        raise ValueError(f"unsupported Tetris edge-row query: {query_id}")
    return str(edge), str(status)


def _cell_ids_in_row_matching_status(board: Board, *, row_index: int, status: str, entity_prefix: str) -> Tuple[str, ...]:
    """Return rendered cell ids in one row matching filled or empty status."""

    ids: List[str] = []
    for col, cell in enumerate(board[int(row_index)]):
        is_filled = str(cell) != EMPTY
        if (str(status) == "filled" and is_filled) or (str(status) == "empty" and not is_filled):
            ids.append(f"{entity_prefix}_cell_{int(row_index)}_{int(col)}")
    return tuple(ids)


def _make_edge_occupied_row_cell_count_sample(rng, axes: _ResolvedAxes) -> _Sample:
    """Construct a board where an edge occupied row has an exact cell count."""

    board_rows = int(axes.board_rows)
    board_cols = int(axes.board_cols)
    target = int(axes.target_cell_count if axes.target_cell_count is not None else 0)
    edge, status = _edge_row_query_parts(str(axes.query_id))
    filled_in_selected_row = int(target) if str(status) == "filled" else int(board_cols) - int(target)
    if filled_in_selected_row < 1 or filled_in_selected_row > int(board_cols):
        raise ValueError("edge occupied row target is infeasible")

    height_cap = {
        "low_stack": 3,
        "notched_stack": 5,
        "high_stack": 7,
    }.get(str(axes.scene_variant), 5)
    height_cap = max(1, min(int(height_cap), int(board_rows) - 2))
    active_cols = set(int(col) for col in rng.sample(range(int(board_cols)), int(filled_in_selected_row)))

    if str(edge) == "top":
        peak_height = int(rng.randint(1 if height_cap == 1 else 2, int(height_cap)))
        heights = [
            int(peak_height) if int(col) in active_cols else int(rng.randint(0, max(0, int(peak_height) - 1)))
            for col in range(int(board_cols))
        ]
    else:
        heights = [
            int(rng.randint(1, int(height_cap))) if int(col) in active_cols else 0
            for col in range(int(board_cols))
        ]

    board = _supported_stack_from_heights(
        rng,
        board_rows=int(board_rows),
        board_cols=int(board_cols),
        heights=heights,
    )
    selected_row_index = _edge_occupied_row_index(board, edge=str(edge))
    annotation_entity_ids = _cell_ids_in_row_matching_status(
        board,
        row_index=int(selected_row_index),
        status=str(status),
        entity_prefix="main",
    )
    if len(annotation_entity_ids) != int(target):
        raise ValueError("constructed Tetris edge-row board has wrong answer")
    selected_row = board[int(selected_row_index)]
    return _Sample(
        answer=int(target),
        answer_type="integer",
        board=board,
        piece="",
        preview_orientation_index=0,
        placement=None,
        falling_placement=None,
        outcome=None,
        options=(),
        annotation_entity_ids=tuple(annotation_entity_ids),
        annotation_kind="cell_set",
        metadata={
            **_supported_stack_generation_meta(strategy="edge_occupied_row_column_heights"),
            "target_cell_count": int(target),
            "edge_row_selector": str(edge),
            "counted_cell_status": str(status),
            "selected_row_index": int(selected_row_index),
            "selected_row_filled_count": int(sum(1 for cell in selected_row if str(cell) != EMPTY)),
            "selected_row_empty_count": int(sum(1 for cell in selected_row if str(cell) == EMPTY)),
            "selected_cell_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            "column_heights": [int(value) for value in _column_heights(board)],
        },
    )


def _shift_instruction_text(shift_delta: int) -> str:
    if int(shift_delta) == 0:
        return "do not move it sideways"
    direction = "left" if int(shift_delta) < 0 else "right"
    magnitude = abs(int(shift_delta))
    unit = "column" if int(magnitude) == 1 else "columns"
    return f"move it {int(magnitude)} {unit} {direction}"


def _horizontal_sweep_cells(placement: _Placement, *, shift_delta: int) -> Tuple[Coord, ...]:
    if int(shift_delta) == 0:
        return _piece_cells(placement)
    step = 1 if int(shift_delta) > 0 else -1
    cells: List[Coord] = []
    for delta in range(0, int(shift_delta) + step, step):
        cells.extend(_piece_cells(_shifted_placement(placement, shift_delta=int(delta))))
    return tuple(sorted(set(cells)))


def _bottom_edge_below_cells(placement: _Placement) -> Tuple[Coord, ...]:
    cells = set(_piece_cells(placement))
    below_cells: List[Coord] = []
    for row, col in cells:
        below = (int(row) + 1, int(col))
        if below not in cells:
            below_cells.append(below)
    return tuple(sorted(set(below_cells)))


def _placement_trace(placement: _Placement) -> Dict[str, Any]:
    return {
        "piece": str(placement.piece),
        "orientation_index": int(placement.orientation_index),
        "col": int(placement.col),
        "top": int(placement.top),
        "cells": [[int(r), int(c)] for r, c in _piece_cells(placement)],
    }


def _make_drop_collision_time_sample(rng, axes: _ResolvedAxes) -> _Sample:
    target = int(axes.target_drop_steps or 0)
    board_rows = int(axes.board_rows)
    board_cols = int(axes.board_cols)
    shift_delta = int(axes.shift_delta)
    for _attempt in range(1600):
        piece = str(rng.choice(PIECE_ORDER))
        orientation_index = int(rng.randrange(len(TETROMINOES[piece])))
        shape = TETROMINOES[piece][orientation_index]
        height, width = _shape_size(shape)
        if int(width) > int(board_cols):
            continue
        final_top = int(target)
        # Keep a visible locked-block stop below the final piece instead of
        # relying on an image boundary as the stopping witness.
        if final_top < 0 or final_top >= int(board_rows) - int(height):
            continue
        shifted_col_candidates = []
        for shifted_col in range(0, int(board_cols) - int(width) + 1):
            start_col = int(shifted_col) - int(shift_delta)
            if 0 <= int(start_col) <= int(board_cols) - int(width):
                shifted_col_candidates.append((int(start_col), int(shifted_col)))
        if not shifted_col_candidates:
            continue
        start_col, shifted_col = tuple(rng.choice(shifted_col_candidates))
        start_placement = _Placement(piece, int(orientation_index), int(start_col), 0)
        final_placement = _Placement(piece, int(orientation_index), int(shifted_col), int(final_top))

        path_cells: set[Coord] = set()
        for top in range(0, int(final_top) + 1):
            path_cells.update(_piece_cells(_Placement(piece, int(orientation_index), int(shifted_col), int(top))))
        sweep_cells = set(_horizontal_sweep_cells(start_placement, shift_delta=int(shift_delta)))
        blocker_cells = set(_bottom_edge_below_cells(final_placement))
        blocker_cells = {(int(row), int(col)) for row, col in blocker_cells if 0 <= int(row) < int(board_rows)}
        if not blocker_cells:
            continue

        rows = [[EMPTY for _ in range(int(board_cols))] for _ in range(int(board_rows))]
        for row, col in blocker_cells:
            _fill_supported_column(rows, col=int(col), top_row=int(row), rng=rng)

        protected = set(path_cells) | set(sweep_cells) | set(blocker_cells)
        height_cap = {
            "low_stack": 3,
            "notched_stack": 5,
            "high_stack": 7,
        }.get(str(axes.scene_variant), 5)
        blocker_cols = {int(col) for _row, col in blocker_cells}
        for col in range(int(board_cols)):
            if int(col) in blocker_cols:
                continue
            protected_rows = [int(row) for row, protected_col in protected if int(protected_col) == int(col)]
            top_limit = max(protected_rows) + 1 if protected_rows else 0
            max_height = max(0, int(board_rows) - int(top_limit))
            if max_height <= 0:
                continue
            if rng.random() > 0.70:
                continue
            height = int(rng.randint(1, min(int(height_cap), int(max_height))))
            top_row = int(board_rows) - int(height)
            if int(top_row) < int(top_limit):
                top_row = int(top_limit)
            _fill_supported_column(rows, col=int(col), top_row=int(top_row), rng=rng, protected_empty=set(path_cells) | set(sweep_cells))
        board = _freeze(rows)
        if not _is_supported_stack_board(board):
            continue
        collision = _drop_collision(board, start_placement, shift_delta=int(shift_delta))
        if collision is None:
            continue
        if int(collision.drop_steps) != int(target):
            continue
        if str(collision.collision_kind) != "locked_block" or not collision.blocker_cells:
            continue

        start_ids = tuple(f"start_cell_{int(row)}_{int(col)}" for row, col in _piece_cells(start_placement))
        stop_ids = tuple(f"start_cell_{int(row)}_{int(col)}" for row, col in collision.blocker_cells)
        return _Sample(
            answer=int(collision.drop_steps),
            answer_type="integer",
            board=board,
            piece=str(piece),
            preview_orientation_index=int(orientation_index),
            placement=collision.final_placement,
            falling_placement=start_placement,
            outcome=None,
            options=(),
            annotation_entity_ids=tuple(start_ids + stop_ids),
            annotation_kind="collision_keyed_cell_sets",
            metadata={
                **_supported_stack_generation_meta(strategy="drop_collision_supported_blockers"),
                "target_drop_steps": int(target),
                "drop_steps": int(collision.drop_steps),
                "shift_delta": int(shift_delta),
                "shift_magnitude": abs(int(shift_delta)),
                "shift_instruction": _shift_instruction_text(int(shift_delta)),
                "collision_kind": str(collision.collision_kind),
                "start_placement": _placement_trace(collision.start_placement),
                "shifted_placement": _placement_trace(collision.shifted_placement),
                "final_placement": _placement_trace(collision.final_placement),
                "collision_blocker_cells": [[int(r), int(c)] for r, c in collision.blocker_cells],
                "bottom_contact_cells": [[int(r), int(c)] for r, c in collision.bottom_contact_cells],
                "annotation_entity_id_map": {
                    "start_piece": [str(entity_id) for entity_id in start_ids],
                    "stop_witness": [str(entity_id) for entity_id in stop_ids],
                },
            },
        )
    raise ValueError("failed to construct Tetris drop-collision-time sample")


def _sample_scene(rng, axes: _ResolvedAxes) -> _Sample:
    if str(axes.public_query) == QUERY_LINE_CLEAR_COUNT:
        return _make_line_clear_sample(rng, axes)
    if str(axes.public_query) == QUERY_DROP_RESULT_LABEL:
        return _make_drop_result_sample(rng, axes)
    if str(axes.public_query) == QUERY_ROW_OCCUPANCY_STATUS_COUNT:
        return _make_row_occupancy_sample(rng, axes)
    if str(axes.public_query) == QUERY_DROP_COLLISION_TIME_VALUE:
        return _make_drop_collision_time_sample(rng, axes)
    if str(axes.public_query) == QUERY_EDGE_OCCUPIED_ROW_CELL_COUNT:
        return _make_edge_occupied_row_cell_count_sample(rng, axes)
    raise ValueError(f"unsupported public query: {axes.public_query}")


def _board_panel_size(params: _RenderParams, *, board_rows: int, board_cols: int) -> Tuple[int, int]:
    cell = int(params.cell_size_px)
    gap = int(params.cell_gap_px)
    board_w = (int(board_cols) * cell) + ((int(board_cols) - 1) * gap)
    board_h = (int(board_rows) * cell) + ((int(board_rows) - 1) * gap)
    panel_w = board_w + (2 * int(params.panel_pad_px))
    panel_h = board_h + (2 * int(params.panel_pad_px)) + int(params.label_band_height_px)
    return int(panel_w), int(panel_h)


def _piece_preview_panel_size(params: _RenderParams) -> Tuple[int, int]:
    cell = int(params.cell_size_px)
    gap = int(params.cell_gap_px)
    preview_w = (4 * cell) + (3 * gap)
    preview_h = (4 * cell) + (3 * gap)
    return (
        int(preview_w + (2 * int(params.panel_pad_px))),
        int(preview_h + (2 * int(params.panel_pad_px)) + int(params.label_band_height_px)),
    )


def _label_text(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[int, int, int, int],
    text: str,
    *,
    font_size: int,
    fill: Sequence[int],
    font_family: str = "",
) -> None:
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(12, float(bbox[2] - bbox[0] - 8)),
        max_height=max(10, float(bbox[3] - bbox[1] - 4)),
        bold=True,
        min_size_px=8,
        max_size_px=int(font_size),
        fill_ratio=0.95,
        font_family=str(font_family) or None,
    )
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    fill_rgb = tuple(int(v) for v in fill)
    draw_text_traced(draw,
        (
            bbox[0] + ((bbox[2] - bbox[0]) - (text_bbox[2] - text_bbox[0])) / 2.0,
            bbox[1] + ((bbox[3] - bbox[1]) - (text_bbox[3] - text_bbox[1])) / 2.0 - text_bbox[1],
        ),
        str(text),
        font=font,
        fill=fill_rgb,
        stroke_width=1,
        stroke_fill=tuple(resolve_text_stroke_fill(fill_rgb)),
     role="readout", required=False,)


def _draw_board_panel(
    image: Image.Image,
    *,
    panel_bbox: Tuple[int, int, int, int],
    label: str,
    board: Board,
    style,
    params: _RenderParams,
    ghost_cells: Sequence[Coord] = (),
    ghost_piece: str | None = None,
    falling_cells: Sequence[Coord] = (),
    falling_piece: str | None = None,
    selected_rows: Sequence[int] = (),
    entity_prefix: str,
    tetris_style_variant: str,
) -> Tuple[Dict[str, Any], Tuple[Dict[str, Any], ...]]:
    draw = ImageDraw.Draw(image, "RGBA")
    draw_panel_option_card(draw, bbox=panel_bbox, style=style, radius=12, border_width=2)
    label_bbox = (
        int(panel_bbox[0] + params.panel_pad_px),
        int(panel_bbox[1] + params.panel_pad_px),
        int(panel_bbox[2] - params.panel_pad_px),
        int(panel_bbox[1] + params.panel_pad_px + params.label_band_height_px),
    )
    _label_text(
        draw,
        label_bbox,
        str(label),
        font_size=int(params.label_font_size_px),
        fill=style.text_rgb,
        font_family=str(params.font_family),
    )

    board_left = int(panel_bbox[0] + params.panel_pad_px)
    board_top = int(panel_bbox[1] + params.panel_pad_px + params.label_band_height_px)
    cell = int(params.cell_size_px)
    gap = int(params.cell_gap_px)
    cell_bboxes: Dict[str, List[float]] = {}
    row_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = [
        {
            "id": str(entity_prefix),
            "type": "tetris_board_panel",
            "label": str(label),
            "bbox_px": [float(v) for v in panel_bbox],
        }
    ]
    ghost_set = {tuple(coord) for coord in ghost_cells}
    falling_set = {tuple(coord) for coord in falling_cells}
    selected_row_set = {int(row) for row in selected_rows}
    board_rows, board_cols = _board_size(board)
    for row in range(board_rows):
        row_left = board_left
        row_top = board_top + row * (cell + gap)
        row_right = board_left + board_cols * cell + (board_cols - 1) * gap
        row_bottom = row_top + cell
        row_id = f"{entity_prefix}_row_{row}"
        row_bboxes[row_id] = [float(row_left), float(row_top), float(row_right), float(row_bottom)]
        if row in selected_row_set:
            draw.rectangle((row_left - 2, row_top - 2, row_right + 2, row_bottom + 2), outline=style.mark_rgb, width=3)
        for col in range(board_cols):
            left = board_left + col * (cell + gap)
            top = board_top + row * (cell + gap)
            bbox = (int(left), int(top), int(left + cell), int(top + cell))
            cell_value = board[row][col]
            if cell_value == EMPTY:
                fill = tuple(style.panel_fill_rgb)
                draw_panel_grid_cell(
                    draw,
                    bbox=bbox,
                    fill=fill,
                    style=style,
                    outline=style.grid_rgb,
                    width=int(params.cell_outline_width_px),
                )
            else:
                fill = _piece_color(
                    str(cell_value),
                    style_variant=str(tetris_style_variant),
                    state_colors=style.state_colors,
                )
                _draw_tetris_block(
                    draw,
                    bbox=bbox,
                    fill=fill,
                    style=style,
                    params=params,
                    style_variant=str(tetris_style_variant),
                    outline=style.grid_rgb,
                )
            if (row, col) in ghost_set:
                ghost_fill = _piece_color(
                    str(ghost_piece or "I"),
                    style_variant=str(tetris_style_variant),
                    state_colors=style.state_colors,
                )
                draw.rounded_rectangle(
                    (bbox[0] + 3, bbox[1] + 3, bbox[2] - 3, bbox[3] - 3),
                    radius=5,
                    fill=tuple(ghost_fill) + (78,),
                    outline=tuple(style.mark_rgb) + (255,),
                    width=int(params.ghost_outline_width_px),
                )
            if (row, col) in falling_set:
                falling_fill = _piece_color(
                    str(falling_piece or "I"),
                    style_variant=str(tetris_style_variant),
                    state_colors=style.state_colors,
                )
                draw.rounded_rectangle(
                    (bbox[0] + 3, bbox[1] + 3, bbox[2] - 3, bbox[3] - 3),
                    radius=5,
                    fill=tuple(falling_fill) + (210,),
                    outline=tuple(style.mark_rgb) + (255,),
                    width=max(2, int(params.ghost_outline_width_px)),
                )
            cell_id = f"{entity_prefix}_cell_{row}_{col}"
            cell_bboxes[cell_id] = [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]
            entities.append(
                {
                    "id": cell_id,
                    "type": "tetris_cell",
                    "row": int(row),
                    "col": int(col),
                    "value": str(cell_value),
                    "ghost": bool((row, col) in ghost_set),
                    "falling": bool((row, col) in falling_set),
                    "bbox_px": list(cell_bboxes[cell_id]),
                }
            )
    return {
        "panel_bbox_px": [float(v) for v in panel_bbox],
        "cell_bboxes_px": dict(cell_bboxes),
        "row_bboxes_px": dict(row_bboxes),
    }, tuple(entities)


def _draw_piece_preview_panel(
    image: Image.Image,
    *,
    panel_bbox: Tuple[int, int, int, int],
    label: str,
    piece: str,
    orientation_index: int,
    style,
    params: _RenderParams,
    entity_id: str,
    tetris_style_variant: str,
) -> Tuple[Dict[str, Any], Tuple[Dict[str, Any], ...]]:
    draw = ImageDraw.Draw(image, "RGBA")
    draw_panel_option_card(draw, bbox=panel_bbox, style=style, radius=12, border_width=2)
    label_bbox = (
        int(panel_bbox[0] + params.panel_pad_px),
        int(panel_bbox[1] + params.panel_pad_px),
        int(panel_bbox[2] - params.panel_pad_px),
        int(panel_bbox[1] + params.panel_pad_px + params.label_band_height_px),
    )
    _label_text(
        draw,
        label_bbox,
        str(label),
        font_size=int(params.label_font_size_px),
        fill=style.text_rgb,
        font_family=str(params.font_family),
    )

    cell = int(params.cell_size_px)
    gap = int(params.cell_gap_px)
    grid_left = int(panel_bbox[0] + params.panel_pad_px)
    grid_top = int(panel_bbox[1] + params.panel_pad_px + params.label_band_height_px)
    grid_w = (4 * cell) + (3 * gap)
    grid_h = (4 * cell) + (3 * gap)
    shape = TETROMINOES[str(piece)][int(orientation_index)]
    shape_h, shape_w = _shape_size(shape)
    offset_col = (4 - int(shape_w)) // 2
    offset_row = (4 - int(shape_h)) // 2
    entities: List[Dict[str, Any]] = [
        {
            "id": str(entity_id),
            "type": "tetris_next_piece_panel",
            "piece": str(piece),
            "orientation_index": int(orientation_index),
            "bbox_px": [float(v) for v in panel_bbox],
        }
    ]
    cell_bboxes: Dict[str, List[float]] = {}
    for row in range(4):
        for col in range(4):
            left = grid_left + col * (cell + gap)
            top = grid_top + row * (cell + gap)
            bbox = (int(left), int(top), int(left + cell), int(top + cell))
            draw_panel_grid_cell(
                draw,
                bbox=bbox,
                fill=tuple(style.panel_fill_rgb),
                style=style,
                outline=style.grid_rgb,
                width=int(params.cell_outline_width_px),
            )
    for index, (row, col) in enumerate(shape):
        r = int(row) + offset_row
        c = int(col) + offset_col
        left = grid_left + c * (cell + gap)
        top = grid_top + r * (cell + gap)
        bbox = (int(left), int(top), int(left + cell), int(top + cell))
        fill = _piece_color(
            str(piece),
            style_variant=str(tetris_style_variant),
            state_colors=style.state_colors,
        )
        _draw_tetris_block(
            draw,
            bbox=bbox,
            fill=fill,
            style=style,
            params=params,
            style_variant=str(tetris_style_variant),
            outline=style.grid_rgb,
        )
        cell_id = f"{entity_id}_cell_{index}"
        cell_bboxes[cell_id] = [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]
        entities.append(
            {
                "id": cell_id,
                "type": "tetris_next_piece_cell",
                "piece": str(piece),
                "bbox_px": list(cell_bboxes[cell_id]),
            }
        )
    return {
        "panel_bbox_px": [float(v) for v in panel_bbox],
        "cell_bboxes_px": dict(cell_bboxes),
        "grid_bbox_px": [float(grid_left), float(grid_top), float(grid_left + grid_w), float(grid_top + grid_h)],
    }, tuple(entities)


def _grid_panel_bboxes(
    params: _RenderParams,
    *,
    count: int,
    cols: int,
    rows: int,
    board_rows: int,
    board_cols: int,
) -> Tuple[Tuple[int, int, int, int], ...]:
    panel_w, panel_h = _board_panel_size(params, board_rows=int(board_rows), board_cols=int(board_cols))
    total_w = (int(cols) * panel_w) + ((int(cols) - 1) * int(params.board_gap_px))
    total_h = (int(rows) * panel_h) + ((int(rows) - 1) * int(params.board_gap_px))
    left = int((int(params.canvas_width) - total_w) / 2.0)
    top = int((int(params.canvas_height) - total_h) / 2.0)
    group_bbox = (float(left), float(top), float(left + total_w), float(top + total_h))
    _shifted, dx, dy, _resolved = apply_games_layout_jitter_to_bbox(
        bbox_px=group_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    bboxes: List[Tuple[int, int, int, int]] = []
    for index in range(int(count)):
        grid_row = index // int(cols)
        grid_col = index % int(cols)
        x0 = left + grid_col * (panel_w + int(params.board_gap_px)) + int(round(dx))
        y0 = top + grid_row * (panel_h + int(params.board_gap_px)) + int(round(dy))
        bboxes.append((int(x0), int(y0), int(x0 + panel_w), int(y0 + panel_h)))
    return tuple(bboxes)


def _result_option_grid_params(
    params: _RenderParams,
    *,
    panel_count: int,
    board_rows: int,
    board_cols: int,
) -> Tuple[_RenderParams, int, int]:
    """Return a fitted panel grid for START plus result-board options."""

    cols = 4 if int(panel_count) > 6 else 3
    rows = max(1, (int(panel_count) + int(cols) - 1) // int(cols))
    cell_gap = int(params.cell_gap_px)
    panel_pad = int(params.panel_pad_px)
    label_band = int(params.label_band_height_px)
    board_gap = int(params.board_gap_px)
    max_cell_w = (
        int(params.canvas_width)
        - ((int(cols) - 1) * board_gap)
        - (int(cols) * 2 * panel_pad)
        - (int(cols) * (int(board_cols) - 1) * cell_gap)
    ) // max(1, int(cols) * int(board_cols))
    max_cell_h = (
        int(params.canvas_height)
        - ((int(rows) - 1) * board_gap)
        - (int(rows) * ((2 * panel_pad) + label_band))
        - (int(rows) * (int(board_rows) - 1) * cell_gap)
    ) // max(1, int(rows) * int(board_rows))
    fitted_cell = max(10, min(int(params.cell_size_px), int(max_cell_w), int(max_cell_h)))
    return replace(params, cell_size_px=int(fitted_cell)), int(cols), int(rows)


def _render_scene(
    *,
    sample: _Sample,
    axes: _ResolvedAxes,
    params: _RenderParams,
    instance_seed: int,
) -> _RenderedScene:
    style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace="games.tetris.panel_style",
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        style=style,
    )
    image = background.convert("RGBA")
    entities: List[Dict[str, Any]] = []
    board_rows, board_cols = _board_size(sample.board)
    render_map: Dict[str, Any] = {
        "board_rows": int(board_rows),
        "board_cols": int(board_cols),
        "panels": {},
        "cell_bboxes_px": {},
        "row_bboxes_px": {},
        "option_bboxes_px": {},
        "layout_jitter": dict(params.layout_jitter_meta),
        "font_family": str(params.font_family),
        "text_style": {"font_family": str(params.font_family)},
        "panel_scene_style": dict(panel_style_meta),
        "tetris_board_style": {
            "style_variant": str(axes.style_variant),
            "available_styles": list(SUPPORTED_STYLE_VARIANTS),
            "piece_palette_policy": "scene_local_tetromino_piece_palette",
        },
    }

    if str(axes.public_query) in {
        QUERY_ROW_OCCUPANCY_STATUS_COUNT,
        QUERY_DROP_COLLISION_TIME_VALUE,
        QUERY_EDGE_OCCUPIED_ROW_CELL_COUNT,
    }:
        row_params = replace(params, cell_size_px=int(params.line_cell_size_px))
        board_w, board_h = _board_panel_size(row_params, board_rows=board_rows, board_cols=board_cols)
        left = int((int(row_params.canvas_width) - board_w) / 2.0)
        top = int((int(row_params.canvas_height) - board_h) / 2.0)
        group_bbox = (float(left), float(top), float(left + board_w), float(top + board_h))
        _shifted, dx, dy, _resolved = apply_games_layout_jitter_to_bbox(
            bbox_px=group_bbox,
            canvas_width=int(row_params.canvas_width),
            canvas_height=int(row_params.canvas_height),
            jitter=row_params.layout_jitter_meta,
        )
        panel_bbox = (
            int(left + round(dx)),
            int(top + round(dy)),
            int(left + round(dx) + board_w),
            int(top + round(dy) + board_h),
        )
        panel_map, panel_entities = _draw_board_panel(
            image,
            panel_bbox=panel_bbox,
            label="START" if str(axes.public_query) == QUERY_DROP_COLLISION_TIME_VALUE else "BOARD",
            board=sample.board,
            style=style,
            params=row_params,
            ghost_cells=(),
            ghost_piece=None,
            falling_cells=_piece_cells(sample.falling_placement) if sample.falling_placement is not None else (),
            falling_piece=sample.piece,
            selected_rows=(),
            entity_prefix="start" if str(axes.public_query) == QUERY_DROP_COLLISION_TIME_VALUE else "main",
            tetris_style_variant=str(axes.style_variant),
        )
        entities.extend(panel_entities)
        panel_key = "start" if str(axes.public_query) == QUERY_DROP_COLLISION_TIME_VALUE else "main"
        render_map["panels"][panel_key] = panel_map["panel_bbox_px"]
        render_map["option_bboxes_px"][panel_key] = panel_map["panel_bbox_px"]
        render_map["cell_bboxes_px"].update(panel_map["cell_bboxes_px"])
        render_map["row_bboxes_px"].update(panel_map["row_bboxes_px"])
    elif str(axes.public_query) == QUERY_LINE_CLEAR_COUNT:
        line_params = replace(params, cell_size_px=int(params.line_cell_size_px))
        board_w, board_h = _board_panel_size(line_params, board_rows=board_rows, board_cols=board_cols)
        preview_w, preview_h = _piece_preview_panel_size(line_params)
        total_h = preview_h + int(line_params.board_gap_px) + board_h
        left = int((int(line_params.canvas_width) - board_w) / 2.0)
        top = int((int(line_params.canvas_height) - total_h) / 2.0)
        group_bbox = (float(left), float(top), float(left + board_w), float(top + total_h))
        _shifted, dx, dy, _resolved = apply_games_layout_jitter_to_bbox(
            bbox_px=group_bbox,
            canvas_width=int(line_params.canvas_width),
            canvas_height=int(line_params.canvas_height),
            jitter=line_params.layout_jitter_meta,
        )
        left = int(left + round(dx))
        top = int(top + round(dy))
        preview_bbox = (
            int(left + (board_w - preview_w) / 2.0),
            int(top),
            int(left + (board_w - preview_w) / 2.0 + preview_w),
            int(top + preview_h),
        )
        panel_bbox = (
            int(left),
            int(top + preview_h + int(line_params.board_gap_px)),
            int(left + board_w),
            int(top + preview_h + int(line_params.board_gap_px) + board_h),
        )
        preview_map, preview_entities = _draw_piece_preview_panel(
            image,
            panel_bbox=preview_bbox,
            label="NEXT",
            piece=sample.piece,
            orientation_index=int(sample.preview_orientation_index),
            style=style,
            params=line_params,
            entity_id="next_piece",
            tetris_style_variant=str(axes.style_variant),
        )
        entities.extend(preview_entities)
        render_map["panels"]["next_piece"] = preview_map["panel_bbox_px"]
        render_map["option_bboxes_px"]["next_piece"] = preview_map["panel_bbox_px"]
        render_map["cell_bboxes_px"].update(preview_map["cell_bboxes_px"])
        panel_map, panel_entities = _draw_board_panel(
            image,
            panel_bbox=panel_bbox,
            label="BOARD",
            board=sample.board,
            style=style,
            params=line_params,
            ghost_cells=(),
            ghost_piece=None,
            selected_rows=(),
            entity_prefix="main",
            tetris_style_variant=str(axes.style_variant),
        )
        entities.extend(panel_entities)
        render_map["panels"]["main"] = panel_map["panel_bbox_px"]
        render_map["option_bboxes_px"]["main"] = panel_map["panel_bbox_px"]
        render_map["cell_bboxes_px"].update(panel_map["cell_bboxes_px"])
        render_map["row_bboxes_px"].update(panel_map["row_bboxes_px"])
    else:
        grid_params, grid_cols, grid_rows = _result_option_grid_params(
            params,
            panel_count=1 + len(sample.options),
            board_rows=board_rows,
            board_cols=board_cols,
        )
        bboxes = _grid_panel_bboxes(
            grid_params,
            count=1 + len(sample.options),
            cols=int(grid_cols),
            rows=int(grid_rows),
            board_rows=board_rows,
            board_cols=board_cols,
        )
        start_map, start_entities = _draw_board_panel(
            image,
            panel_bbox=bboxes[0],
            label="START",
            board=sample.board,
            style=style,
            params=grid_params,
            ghost_cells=(),
            ghost_piece=None,
            falling_cells=_piece_cells(sample.falling_placement) if sample.falling_placement is not None else (),
            falling_piece=sample.piece,
            selected_rows=(),
            entity_prefix="start",
            tetris_style_variant=str(axes.style_variant),
        )
        entities.extend(start_entities)
        render_map["panels"]["start"] = list(start_map["panel_bbox_px"])
        render_map["cell_bboxes_px"].update(start_map["cell_bboxes_px"])
        render_map["row_bboxes_px"].update(start_map["row_bboxes_px"])
        for option, panel_bbox in zip(sample.options, bboxes[1:]):
            panel_map, panel_entities = _draw_board_panel(
                image,
                panel_bbox=panel_bbox,
                label=str(option.label),
                board=option.board,
                style=style,
                params=grid_params,
                ghost_cells=(),
                ghost_piece=None,
                selected_rows=(),
                entity_prefix=f"option_{option.label.lower()}",
                tetris_style_variant=str(axes.style_variant),
            )
            entities.extend(panel_entities)
            render_map["option_bboxes_px"][option.entity_id] = list(panel_map["panel_bbox_px"])
            render_map["panels"][option.entity_id] = list(panel_map["panel_bbox_px"])
            render_map["cell_bboxes_px"].update(panel_map["cell_bboxes_px"])
            render_map["row_bboxes_px"].update(panel_map["row_bboxes_px"])
    return _RenderedScene(
        image=image,
        entities=tuple(entities),
        render_map=render_map,
        style_meta={
            "panel_scene_style": dict(panel_style_meta),
            "tetris_board_style": dict(render_map["tetris_board_style"]),
        },
        background_meta=dict(background_meta),
    )


def _annotation_bboxes(sample: _Sample, render_map: Mapping[str, Any]) -> List[List[float]]:
    bboxes: List[List[float]] = []
    if str(sample.annotation_kind) in {"option_panel", "board_and_next_piece"}:
        option_bboxes = render_map.get("option_bboxes_px", {})
        for entity_id in sample.annotation_entity_ids:
            bboxes.append([float(v) for v in option_bboxes[str(entity_id)]])
        return bboxes
    cell_bboxes = render_map.get("cell_bboxes_px", {})
    row_bboxes = render_map.get("row_bboxes_px", {})
    for entity_id in sample.annotation_entity_ids:
        if str(sample.annotation_kind) == "row_set" or str(entity_id).startswith("cleared_row_"):
            bboxes.append([float(v) for v in row_bboxes[str(entity_id)]])
        else:
            bboxes.append([float(v) for v in cell_bboxes[str(entity_id)]])
    return bboxes


def _keyed_annotation_bbox_sets(sample: _Sample, render_map: Mapping[str, Any]) -> Dict[str, List[List[float]]]:
    cell_bboxes = render_map.get("cell_bboxes_px", {})
    raw_map = sample.metadata.get("annotation_entity_id_map", {})
    if not isinstance(raw_map, Mapping):
        raise ValueError("keyed annotation sample is missing annotation_entity_id_map")
    result: Dict[str, List[List[float]]] = {}
    for key, entity_ids in raw_map.items():
        result[str(key)] = [
            [float(v) for v in cell_bboxes[str(entity_id)]]
            for entity_id in entity_ids
        ]
    return result


def _build_prompt_json_examples(public_query: str) -> Tuple[str, str]:
    if str(public_query) == QUERY_LINE_CLEAR_COUNT:
        answer: int | str = 2
        annotation: Any = {"board": [80, 170, 300, 620], "next_piece": [140, 60, 240, 155]}
    elif str(public_query) == QUERY_ROW_OCCUPANCY_STATUS_COUNT:
        answer = 3
        annotation = [[120, 310, 460, 344], [120, 380, 460, 414], [120, 450, 460, 484]]
    elif str(public_query) == QUERY_EDGE_OCCUPIED_ROW_CELL_COUNT:
        answer = 4
        annotation = [[120, 310, 154, 344], [156, 310, 190, 344], [192, 310, 226, 344], [228, 310, 262, 344]]
    elif str(public_query) == QUERY_DROP_COLLISION_TIME_VALUE:
        answer = 4
        annotation = {
            "start_piece": [[120, 90, 148, 118], [150, 90, 178, 118]],
            "stop_witness": [[120, 238, 148, 266], [150, 238, 178, 266]],
        }
    else:
        answer = "C"
        annotation = [[80, 120, 180, 240]]
    return (
        json.dumps({"annotation": annotation, "answer": answer}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer}, separators=(",", ":"), ensure_ascii=False),
    )


def _task_answer_hint_key(public_query: str) -> str:
    return f"answer_hint_{str(public_query)}"


def _task_annotation_hint_key(public_query: str) -> str:
    return f"annotation_hint_{str(public_query)}"




class GamesTetrisBoardTask:
    """Generate one grounded Tetris mechanics query."""

    task_id = "games_tetris_base"
    domain = "games"
    scene_id = SCENE_ID
    public_query = QUERY_LINE_CLEAR_COUNT
    supported_query_ids = LINE_CLEAR_BRANCHES

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(
            task_id=str(self.task_id),
            public_query=str(self.public_query),
            instance_seed=int(instance_seed),
            params=params,
        )
        render_params = _render_params(params, instance_seed=int(instance_seed))
        sample: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{self.task_id}.{axes.public_query}.attempt.{attempt_index}")
            try:
                sample = _sample_scene(rng, axes)
            except ValueError:
                continue
            break
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Tetris sample")

        rendered = _render_scene(
            sample=sample,
            axes=axes,
            params=render_params,
            instance_seed=int(instance_seed),
        )
        if str(sample.annotation_kind) == "board_and_next_piece":
            option_bboxes = rendered.render_map.get("option_bboxes_px", {})
            annotation_value: Any = {
                "board": [float(v) for v in option_bboxes["main"]],
                "next_piece": [float(v) for v in option_bboxes["next_piece"]],
            }
            annotation_type = "keyed_bbox_map"
            projected_annotation = {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_value),
                "pixel_keyed_bbox_map": dict(annotation_value),
            }
            witness_symbolic = {
                "type": "object_map",
                "ids": {"board": "main", "next_piece": "next_piece"},
            }
        elif str(sample.annotation_kind) == "collision_keyed_cell_sets":
            annotation_value = _keyed_annotation_bbox_sets(sample, rendered.render_map)
            annotation_type = "keyed_bbox_set_map"
            projected_annotation = {
                "type": "keyed_bbox_set_map",
                "keyed_bbox_set_map": dict(annotation_value),
                "pixel_keyed_bbox_set_map": dict(annotation_value),
            }
            witness_symbolic = {
                "type": "object_set_map",
                "ids": {
                    str(key): [str(entity_id) for entity_id in entity_ids]
                    for key, entity_ids in sample.metadata.get("annotation_entity_id_map", {}).items()
                },
            }
        else:
            annotation_bboxes = _annotation_bboxes(sample, rendered.render_map)
            annotation_value = [list(bbox) for bbox in annotation_bboxes]
            annotation_type = "bbox_set"
            projected_annotation = {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_value],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_value],
            }
            witness_symbolic = {"type": "object_set", "ids": [str(v) for v in sample.annotation_entity_ids]}
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_tetris_board",
                "tetris_rule_text",
                "next_piece_rule_text",
                "fixed_drop_rule_text",
                "collision_time_rule_text",
                "line_clear_rule_text",
                "answer_hint_line_clear_count",
                "answer_hint_drop_result_label",
                "answer_hint_row_occupancy_status_count",
                "answer_hint_drop_collision_time_value",
                "answer_hint_edge_occupied_row_cell_count",
                "annotation_hint_line_clear_count",
                "annotation_hint_drop_result_label",
                "annotation_hint_row_occupancy_status_count",
                "annotation_hint_drop_collision_time_value",
                "annotation_hint_edge_occupied_row_cell_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.public_query))
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults["object_description_tetris_board"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "answer_hint": str(prompt_defaults[_task_answer_hint_key(str(axes.public_query))]),
                "annotation_hint": str(prompt_defaults[_task_annotation_hint_key(str(axes.public_query))]),
                "tetris_rule_text": str(prompt_defaults["tetris_rule_text"]),
                "next_piece_rule_text": str(prompt_defaults["next_piece_rule_text"]),
                "fixed_drop_rule_text": str(prompt_defaults["fixed_drop_rule_text"]),
                "collision_time_rule_text": str(prompt_defaults["collision_time_rule_text"]),
                "line_clear_rule_text": str(prompt_defaults["line_clear_rule_text"]),
                "shift_instruction": str(sample.metadata.get("shift_instruction", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_gt = TypedValue(type=str(sample.answer_type), value=sample.answer)
        annotation_gt = TypedValue(type=str(annotation_type), value=annotation_value)

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_tetris_board_{axes.scene_variant}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "public_query": str(axes.public_query),
                    "piece": str(sample.piece),
                    "answer": sample.answer,
                    "annotation_entity_ids": [str(v) for v in sample.annotation_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(axes.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(axes.query_id),
                    "public_query": str(axes.public_query),
                    "scene_variant": str(axes.scene_variant),
                    "style_variant": str(axes.style_variant),
                    "board_rows": int(axes.board_rows),
                    "board_cols": int(axes.board_cols),
                    "target_clear_count": axes.target_clear_count,
                    "target_row_count": axes.target_row_count,
                    "target_drop_steps": axes.target_drop_steps,
                    "target_cell_count": axes.target_cell_count,
                    "shift_delta": int(axes.shift_delta),
                    "option_count": int(axes.option_count),
                    "target_label": axes.target_label,
                    "query_id_probabilities": dict(axes.query_probabilities),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "answer_probabilities": dict(axes.answer_probabilities),
                    "shift_delta_probabilities": dict(axes.shift_delta_probabilities),
                    "option_count_probabilities": dict(axes.option_count_probabilities),
                    "board_row_probabilities": dict(axes.board_row_probabilities),
                    "board_col_probabilities": dict(axes.board_col_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
                "style": dict(rendered.style_meta),
                "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
                "tetris_board_style": dict(rendered.style_meta.get("tetris_board_style", {})),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": str(axes.query_id),
                "public_query": str(axes.public_query),
                "scene_variant": str(axes.scene_variant),
                "board_row_count": int(axes.board_rows),
                "board_col_count": int(axes.board_cols),
                "board_rows": [list(row) for row in sample.board],
                "piece": str(sample.piece),
                "preview_orientation_index": int(sample.preview_orientation_index),
                "placement": None if sample.placement is None else {
                    "piece": sample.placement.piece,
                    "orientation_index": int(sample.placement.orientation_index),
                    "col": int(sample.placement.col),
                    "top": int(sample.placement.top),
                    "cells": [[int(r), int(c)] for r, c in _piece_cells(sample.placement)],
                },
                "falling_placement": None if sample.falling_placement is None else {
                    "piece": sample.falling_placement.piece,
                    "orientation_index": int(sample.falling_placement.orientation_index),
                    "col": int(sample.falling_placement.col),
                    "top": int(sample.falling_placement.top),
                    "cells": [[int(r), int(c)] for r, c in _piece_cells(sample.falling_placement)],
                },
                "locked_cells": [] if sample.outcome is None else [[int(r), int(c)] for r, c in sample.outcome.locked_cells],
                "cleared_rows": [] if sample.outcome is None else [int(v) for v in sample.outcome.cleared_rows],
                "result_board_rows": None if sample.outcome is None else [list(row) for row in sample.outcome.result_board],
                "options": [
                    {
                        "label": option.label,
                        "is_answer": bool(option.is_answer),
                        "board_rows": [list(row) for row in option.board],
                        "placement": None if option.placement is None else {
                            "piece": option.placement.piece,
                            "orientation_index": int(option.placement.orientation_index),
                            "col": int(option.placement.col),
                            "top": int(option.placement.top),
                            "cells": [[int(r), int(c)] for r, c in _piece_cells(option.placement)],
                        },
                        "metric_value": option.metric_value,
                    }
                    for option in sample.options
                ],
                "answer": sample.answer,
                "annotation_kind": str(sample.annotation_kind),
                "annotation_entity_ids": [str(v) for v in sample.annotation_entity_ids],
                **dict(sample.metadata),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_annotation": dict(projected_annotation),
            "background": dict(rendered.background_meta),
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(axes.query_id),
        )


class GamesTetrisLineClearCountTask(GamesTetrisBoardTask):
    """Count rows cleared by one shown Tetris drop."""

    task_id = "task_games__tetris__line_clear_count"
    public_query = QUERY_LINE_CLEAR_COUNT
    supported_query_ids = LINE_CLEAR_BRANCHES


class GamesTetrisDropResultLabelTask(GamesTetrisBoardTask):
    """Choose the board state after one Tetris drop and line clear."""

    task_id = "task_games__tetris__drop_result_label"
    public_query = QUERY_DROP_RESULT_LABEL
    supported_query_ids = DROP_RESULT_BRANCHES


class GamesTetrisRowOccupancyStatusCountTask(GamesTetrisBoardTask):
    """Count rows matching a static occupancy status on a Tetris board."""

    task_id = "task_games__tetris__row_occupancy_status_count"
    public_query = QUERY_ROW_OCCUPANCY_STATUS_COUNT
    supported_query_ids = ROW_OCCUPANCY_BRANCHES


@register_task
class GamesTetrisDropCollisionTimeValueTask(GamesTetrisBoardTask):
    """Count downward timesteps after a fixed Tetris horizontal shift."""

    task_id = "task_games__tetris__drop_collision_time_value"
    public_query = QUERY_DROP_COLLISION_TIME_VALUE
    supported_query_ids = DROP_COLLISION_TIME_BRANCHES


class GamesTetrisEdgeOccupiedRowCellCountTask(GamesTetrisBoardTask):
    """Count cells in the topmost or bottommost occupied Tetris row."""

    task_id = "task_games__tetris__edge_occupied_row_cell_count"
    public_query = QUERY_EDGE_OCCUPIED_ROW_CELL_COUNT
    supported_query_ids = EDGE_OCCUPIED_ROW_BRANCHES


__all__ = [
    "GamesTetrisBoardTask",
    "GamesTetrisDropCollisionTimeValueTask",
    "GamesTetrisDropResultLabelTask",
    "GamesTetrisEdgeOccupiedRowCellCountTask",
    "GamesTetrisLineClearCountTask",
    "GamesTetrisRowOccupancyStatusCountTask",
]
