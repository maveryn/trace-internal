"""Games tasks for variable-size Tetris board mechanics."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import fit_font_to_box, load_font, resolve_text_stroke_fill
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
from ..shared.layout import apply_games_layout_jitter_to_bbox, resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import (
    draw_panel_grid_cell,
    draw_panel_option_card,
    make_panel_scene_background,
    resolve_game_panel_scene_style,
)
from ..shared.visual_defaults import load_games_noise_defaults


TASK_GROUP = "tetris"
SCENE_ID = "tetris"

QUERY_LINE_CLEAR_COUNT = "line_clear_count"
QUERY_DROP_RESULT_LABEL = "drop_result_label"

SUPPORTED_PUBLIC_QUERIES: Tuple[str, ...] = (
    QUERY_LINE_CLEAR_COUNT,
    QUERY_DROP_RESULT_LABEL,
)
LINE_CLEAR_BRANCHES: Tuple[str, ...] = (
    "max_clear_with_next_piece",
)
DROP_RESULT_BRANCHES: Tuple[str, ...] = (
    "no_clear_result",
    "single_clear_result",
    "multi_clear_result",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("low_stack", "notched_stack", "high_stack")
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = ("panel_scene",)
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E")

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
    option_count_support: Tuple[int, ...] = (5,)
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
    option_count: int
    board_rows: int
    board_cols: int
    target_label: str | None
    query_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
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
    evidence_entity_ids: Tuple[str, ...]
    evidence_kind: str
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
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="games_tetris_base",
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


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
    return _ResolvedAxes(
        public_query=str(public_query),
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_clear_count=None if target_clear_count is None else int(target_clear_count),
        option_count=int(option_count),
        board_rows=int(board_rows),
        board_cols=int(board_cols),
        target_label=target_label,
        query_probabilities=dict(query_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        answer_probabilities=dict(answer_probabilities),
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
        layout_jitter_meta=dict(layout_jitter),
    )


def _piece_color(piece: str, state_colors: Sequence[Sequence[int]]) -> Tuple[int, int, int]:
    fallback = {
        "I": (38, 180, 210),
        "O": (239, 193, 50),
        "T": (154, 90, 204),
        "S": (78, 174, 86),
        "Z": (220, 72, 82),
        "J": (65, 112, 210),
        "L": (230, 145, 52),
    }
    index = PIECE_ORDER.index(str(piece)) if str(piece) in PIECE_ORDER else 0
    if len(state_colors) >= len(PIECE_ORDER):
        return tuple(int(v) for v in state_colors[index % len(state_colors)])
    return fallback.get(str(piece), (110, 130, 155))


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


def _construct_board_with_target_clear(
    rng,
    *,
    target_clear_count: int,
    scene_variant: str,
    board_rows: int,
    board_cols: int,
) -> Tuple[Board, _Placement, _Outcome]:
    target = int(target_clear_count)
    for _attempt in range(900):
        piece, orientation_index = _random_piece_with_min_rows(rng, min_rows=max(1, target))
        shape = TETROMINOES[str(piece)][int(orientation_index)]
        height, width = _shape_size(shape)
        if int(width) > int(board_cols) or int(height) > int(board_rows):
            continue
        col = int(rng.randint(0, int(board_cols) - int(width)))
        top = int(board_rows - int(height))
        placement = _Placement(str(piece), int(orientation_index), int(col), int(top))
        piece_cells = set(_piece_cells(placement))
        piece_rows = sorted({row for row, _col in piece_cells})
        target_rows = set(rng.sample(piece_rows, int(target))) if target > 0 else set()
        rows = [[EMPTY for _ in range(int(board_cols))] for _ in range(int(board_rows))]
        fill_base = {"low_stack": 0.12, "notched_stack": 0.18, "high_stack": 0.24}.get(str(scene_variant), 0.16)
        for row in range(int(board_rows)):
            if row in target_rows:
                for col_index in range(int(board_cols)):
                    if (row, col_index) not in piece_cells:
                        rows[row][col_index] = str(rng.choice(PIECE_ORDER))
                continue
            if row >= top - 1:
                row_prob = min(0.70, fill_base + (0.10 * (row - max(0, top - 1))))
                for col_index in range(int(board_cols)):
                    if (row, col_index) not in piece_cells and rng.random() < row_prob:
                        rows[row][col_index] = str(rng.choice(PIECE_ORDER))
        for row, col_index in piece_cells:
            rows[int(row)][int(col_index)] = EMPTY
        _avoid_prefilled_full_rows(rows, protected_empty=piece_cells, rng=rng)
        board = _freeze(rows)
        dropped_top = _hard_drop_top(board, piece=str(piece), orientation_index=int(orientation_index), col=int(col))
        if dropped_top != int(top):
            continue
        outcome = _evaluate_outcome(board, placement)
        if int(outcome.clear_count) == int(target):
            return board, placement, outcome
    raise ValueError(f"failed to construct Tetris board for clear count {target}")


def _random_stack_board(rng, *, scene_variant: str, board_rows: int, board_cols: int) -> Board:
    rows = [[EMPTY for _ in range(int(board_cols))] for _ in range(int(board_rows))]
    height_low, height_high = {
        "low_stack": (1, 3),
        "notched_stack": (2, 5),
        "high_stack": (3, 6),
    }.get(str(scene_variant), (2, 5))
    capped_high = min(int(height_high), max(1, int(board_rows) - 2))
    capped_low = min(int(height_low), capped_high)
    heights = [int(rng.randint(capped_low, capped_high)) for _ in range(int(board_cols))]
    for col in range(int(board_cols)):
        for depth in range(heights[col]):
            row = int(board_rows) - 1 - int(depth)
            if rng.random() < 0.10 and depth > 0:
                continue
            rows[row][col] = str(rng.choice(PIECE_ORDER))
    _avoid_prefilled_full_rows(rows, protected_empty=set(), rng=rng)
    return _freeze(rows)


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
            evidence_entity_ids=("main", "next_piece"),
            evidence_kind="board_and_next_piece",
            metadata={
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
    rows = [list(row) for row in board]
    filled = [(r, c) for r in range(board_rows) for c in range(board_cols) if rows[r][c] != EMPTY]
    empties = [(r, c) for r in range(board_rows) for c in range(board_cols) if rows[r][c] == EMPTY]
    if filled and empties and int(rng.randrange(2)) == 0:
        source = tuple(rng.choice(filled))
        target = tuple(rng.choice(empties))
        rows[int(target[0])][int(target[1])] = rows[int(source[0])][int(source[1])]
        rows[int(source[0])][int(source[1])] = EMPTY
    elif empties:
        target = tuple(rng.choice(empties))
        rows[int(target[0])][int(target[1])] = str(rng.choice(PIECE_ORDER))
    elif filled:
        source = tuple(rng.choice(filled))
        rows[int(source[0])][int(source[1])] = EMPTY
    return _freeze(rows)


def _drop_result_distractor_boards(rng, board: Board, outcome: _Outcome) -> Tuple[Board, ...]:
    boards: List[Board] = []
    seen = {_board_key(outcome.result_board)}

    def add(candidate: Board) -> None:
        key = _board_key(candidate)
        if key not in seen:
            seen.add(key)
            boards.append(candidate)

    add(_uncleared_board_after_lock(outcome))
    add(_clear_without_gravity(outcome))
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
                add(_evaluate_outcome(board, alt).result_board)
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
                add(_evaluate_outcome(board, alt).result_board)
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
        evidence_entity_ids=(f"option_{answer_label.lower()}",),
        evidence_kind="option_panel",
        metadata={
            "target_clear_count": int(outcome.clear_count),
            "drop_result_branch": str(axes.query_id),
        },
    )


def _sample_scene(rng, axes: _ResolvedAxes) -> _Sample:
    if str(axes.public_query) == QUERY_LINE_CLEAR_COUNT:
        return _make_line_clear_sample(rng, axes)
    if str(axes.public_query) == QUERY_DROP_RESULT_LABEL:
        return _make_drop_result_sample(rng, axes)
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


def _label_text(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int], text: str, *, font_size: int, fill: Sequence[int]) -> None:
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(12, float(bbox[2] - bbox[0] - 8)),
        max_height=max(10, float(bbox[3] - bbox[1] - 4)),
        bold=True,
        min_size_px=8,
        max_size_px=int(font_size),
        fill_ratio=0.95,
    )
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    fill_rgb = tuple(int(v) for v in fill)
    draw.text(
        (
            bbox[0] + ((bbox[2] - bbox[0]) - (text_bbox[2] - text_bbox[0])) / 2.0,
            bbox[1] + ((bbox[3] - bbox[1]) - (text_bbox[3] - text_bbox[1])) / 2.0 - text_bbox[1],
        ),
        str(text),
        font=font,
        fill=fill_rgb,
        stroke_width=1,
        stroke_fill=tuple(resolve_text_stroke_fill(fill_rgb)),
    )


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
) -> Tuple[Dict[str, Any], Tuple[Dict[str, Any], ...]]:
    draw = ImageDraw.Draw(image, "RGBA")
    draw_panel_option_card(draw, bbox=panel_bbox, style=style, radius=12, border_width=2)
    label_bbox = (
        int(panel_bbox[0] + params.panel_pad_px),
        int(panel_bbox[1] + params.panel_pad_px),
        int(panel_bbox[2] - params.panel_pad_px),
        int(panel_bbox[1] + params.panel_pad_px + params.label_band_height_px),
    )
    _label_text(draw, label_bbox, str(label), font_size=int(params.label_font_size_px), fill=style.text_rgb)

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
            else:
                fill = _piece_color(str(cell_value), style.state_colors)
            draw_panel_grid_cell(
                draw,
                bbox=bbox,
                fill=fill,
                style=style,
                outline=style.grid_rgb,
                width=int(params.cell_outline_width_px),
            )
            if (row, col) in ghost_set:
                ghost_fill = _piece_color(str(ghost_piece or "I"), style.state_colors)
                draw.rounded_rectangle(
                    (bbox[0] + 3, bbox[1] + 3, bbox[2] - 3, bbox[3] - 3),
                    radius=5,
                    fill=tuple(ghost_fill) + (78,),
                    outline=tuple(style.mark_rgb) + (255,),
                    width=int(params.ghost_outline_width_px),
                )
            if (row, col) in falling_set:
                falling_fill = _piece_color(str(falling_piece or "I"), style.state_colors)
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
) -> Tuple[Dict[str, Any], Tuple[Dict[str, Any], ...]]:
    draw = ImageDraw.Draw(image, "RGBA")
    draw_panel_option_card(draw, bbox=panel_bbox, style=style, radius=12, border_width=2)
    label_bbox = (
        int(panel_bbox[0] + params.panel_pad_px),
        int(panel_bbox[1] + params.panel_pad_px),
        int(panel_bbox[2] - params.panel_pad_px),
        int(panel_bbox[1] + params.panel_pad_px + params.label_band_height_px),
    )
    _label_text(draw, label_bbox, str(label), font_size=int(params.label_font_size_px), fill=style.text_rgb)

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
        fill = _piece_color(str(piece), style.state_colors)
        draw_panel_grid_cell(
            draw,
            bbox=bbox,
            fill=fill,
            style=style,
            outline=style.grid_rgb,
            width=max(1, int(params.cell_outline_width_px)),
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


def _render_scene(
    *,
    sample: _Sample,
    axes: _ResolvedAxes,
    params: _RenderParams,
    instance_seed: int,
) -> _RenderedScene:
    style, style_meta = resolve_game_panel_scene_style(
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
    }

    if str(axes.public_query) == QUERY_LINE_CLEAR_COUNT:
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
        )
        entities.extend(panel_entities)
        render_map["panels"]["main"] = panel_map["panel_bbox_px"]
        render_map["option_bboxes_px"]["main"] = panel_map["panel_bbox_px"]
        render_map["cell_bboxes_px"].update(panel_map["cell_bboxes_px"])
        render_map["row_bboxes_px"].update(panel_map["row_bboxes_px"])
    else:
        bboxes = _grid_panel_bboxes(
            params,
            count=1 + len(sample.options),
            cols=3,
            rows=2,
            board_rows=board_rows,
            board_cols=board_cols,
        )
        start_map, start_entities = _draw_board_panel(
            image,
            panel_bbox=bboxes[0],
            label="START",
            board=sample.board,
            style=style,
            params=params,
            ghost_cells=(),
            ghost_piece=None,
            falling_cells=_piece_cells(sample.falling_placement) if sample.falling_placement is not None else (),
            falling_piece=sample.piece,
            selected_rows=(),
            entity_prefix="start",
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
                params=params,
                ghost_cells=(),
                ghost_piece=None,
                selected_rows=(),
                entity_prefix=f"option_{option.label.lower()}",
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
        style_meta=dict(style_meta),
        background_meta=dict(background_meta),
    )


def _evidence_bboxes(sample: _Sample, render_map: Mapping[str, Any]) -> List[List[float]]:
    bboxes: List[List[float]] = []
    if str(sample.evidence_kind) in {"option_panel", "board_and_next_piece"}:
        option_bboxes = render_map.get("option_bboxes_px", {})
        for entity_id in sample.evidence_entity_ids:
            bboxes.append([float(v) for v in option_bboxes[str(entity_id)]])
        return bboxes
    cell_bboxes = render_map.get("cell_bboxes_px", {})
    row_bboxes = render_map.get("row_bboxes_px", {})
    for entity_id in sample.evidence_entity_ids:
        if str(entity_id).startswith("cleared_row_"):
            bboxes.append([float(v) for v in row_bboxes[str(entity_id)]])
        else:
            bboxes.append([float(v) for v in cell_bboxes[str(entity_id)]])
    return bboxes


def _build_prompt_json_examples(public_query: str) -> Tuple[str, str]:
    if str(public_query) == QUERY_LINE_CLEAR_COUNT:
        answer: int | str = 2
    else:
        answer = "C"
    evidence = [[80, 120, 180, 240]]
    return (
        json.dumps({"evidence": evidence, "answer": answer}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer}, separators=(",", ":"), ensure_ascii=False),
    )


def _task_answer_hint_key(public_query: str) -> str:
    return f"answer_hint_{str(public_query)}"


def _task_evidence_hint_key(public_query: str) -> str:
    return f"evidence_hint_{str(public_query)}"


def _complexity_for_sample(task_id: str, axes: _ResolvedAxes, sample: _Sample) -> TaskComplexity:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=str(task_id))
    filled_count = sum(1 for row in sample.board for cell in row if cell != EMPTY)
    option_count = len(sample.options)
    clear_count = int(sample.outcome.clear_count) if sample.outcome is not None else int(sample.metadata.get("target_clear_count", 0))
    reasoning_base = {
        QUERY_LINE_CLEAR_COUNT: 0.66,
        QUERY_DROP_RESULT_LABEL: 0.64,
    }.get(str(axes.public_query), 0.50)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": min(1.0, 0.36 * normalize_linear(filled_count, min_value=8.0, max_value=46.0) + 0.24 * normalize_linear(option_count, min_value=0.0, max_value=5.0)),
            "state_reasoning": min(1.0, reasoning_base + 0.06 * normalize_linear(clear_count, min_value=0.0, max_value=4.0)),
            "ambiguity": min(1.0, 0.12 * normalize_linear(option_count, min_value=0.0, max_value=5.0) + 0.08 * normalize_linear(len(sample.evidence_entity_ids), min_value=1.0, max_value=8.0)),
            "output_burden": normalize_linear(len(sample.evidence_entity_ids), min_value=1.0, max_value=8.0),
        },
    )


class GamesTetrisBoardTask:
    """Generate one grounded Tetris mechanics query."""

    task_id = "games_tetris_base"
    domain = "games"
    task_group = TASK_GROUP
    public_query = QUERY_LINE_CLEAR_COUNT

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
        evidence_bboxes = _evidence_bboxes(sample, rendered.render_map)
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

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
                "line_clear_rule_text",
                "answer_hint_line_clear_count",
                "answer_hint_drop_result_label",
                "evidence_hint_line_clear_count",
                "evidence_hint_drop_result_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.public_query))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_tetris_board"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "answer_hint": str(prompt_defaults[_task_answer_hint_key(str(axes.public_query))]),
                "evidence_hint": str(prompt_defaults[_task_evidence_hint_key(str(axes.public_query))]),
                "tetris_rule_text": str(prompt_defaults["tetris_rule_text"]),
                "next_piece_rule_text": str(prompt_defaults["next_piece_rule_text"]),
                "fixed_drop_rule_text": str(prompt_defaults["fixed_drop_rule_text"]),
                "line_clear_rule_text": str(prompt_defaults["line_clear_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_gt = TypedValue(type=str(sample.answer_type), value=sample.answer)
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = _complexity_for_sample(str(self.task_id), axes, sample)

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
                    "evidence_entity_ids": [str(v) for v in sample.evidence_entity_ids],
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
                    "option_count": int(axes.option_count),
                    "target_label": axes.target_label,
                    "query_id_probabilities": dict(axes.query_probabilities),
                    "query_id_probabilities": {"default": 1.0},
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "answer_probabilities": dict(axes.answer_probabilities),
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
                "evidence_kind": str(sample.evidence_kind),
                "evidence_entity_ids": [str(v) for v in sample.evidence_entity_ids],
                **dict(sample.metadata),
            },
            "witness_symbolic": {"type": "object_set", "ids": [str(v) for v in sample.evidence_entity_ids]},
            "projected_evidence": {"bbox_set": [list(bbox) for bbox in evidence_bboxes]},
            "background": dict(rendered.background_meta),
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(axes.query_id),
        )


@register_task
class GamesTetrisLineClearCountTask(GamesTetrisBoardTask):
    """Count rows cleared by one shown Tetris drop."""

    task_id = "task_games__tetris__line_clear_count"
    public_query = QUERY_LINE_CLEAR_COUNT


@register_task
class GamesTetrisDropResultLabelTask(GamesTetrisBoardTask):
    """Choose the board state after one Tetris drop and line clear."""

    task_id = "task_games__tetris__drop_result_label"
    public_query = QUERY_DROP_RESULT_LABEL


__all__ = [
    "GamesTetrisBoardTask",
    "GamesTetrisDropResultLabelTask",
    "GamesTetrisLineClearCountTask",
]
