"""3D Tic-Tac-Toe layer-count and winning-move tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ...shared.text_rendering import load_font
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
from ..shared.layout import (
    apply_games_layout_jitter_to_bbox,
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import draw_panel_scene_chrome, make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.text import draw_centered_game_text
from ..shared.visual_defaults import load_games_noise_defaults


TASK_GROUP = "tic_tac_toe_3d"
SCENE_ID = "tic_tac_toe_3d"
BOARD_SIZE = 3
QUERY_X_WIN_MOVE = "x_winning_move_label"
QUERY_O_WIN_MOVE = "o_winning_move_label"
QUERY_X_LAYER_COUNT = "x_piece_count_in_layer"
QUERY_O_LAYER_COUNT = "o_piece_count_in_layer"
WINNING_MOVE_QUERIES: Tuple[str, ...] = (QUERY_X_WIN_MOVE, QUERY_O_WIN_MOVE)
LAYER_COUNT_QUERIES: Tuple[str, ...] = (QUERY_X_LAYER_COUNT, QUERY_O_LAYER_COUNT)
ALL_QUERIES: Tuple[str, ...] = WINNING_MOVE_QUERIES + LAYER_COUNT_QUERIES
LAYERS: Tuple[Tuple[str, str], ...] = (("top", "top"), ("middle", "middle"), ("bottom", "bottom"))
LAYOUT_VARIANTS: Tuple[str, ...] = ("vertical_perspective_stack",)
STYLE_VARIANTS: Tuple[str, ...] = ("classic_grid", "paper_board", "arcade_blue", "mint_table", "charcoal_lines")
OPTION_LABELS: Tuple[str, ...] = tuple("ABCDEF")
Coord = Tuple[int, int, int]
Line = Tuple[Coord, Coord, Coord]
Board = Tuple[Tuple[Tuple[str, ...], ...], ...]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for 3D Tic-Tac-Toe scenes."""

    layer_piece_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    option_count_support: Tuple[int, ...] = (4, 6)
    canvas_width: int = 760
    canvas_height: int = 900
    canvas_min_width_px: int = 580
    canvas_min_height_px: int = 720
    canvas_side_padding_px: int = 72
    panel_margin_px: int = 38
    panel_inner_padding_px: int = 36
    cell_size_px: int = 104
    cell_gap_px: int = 0
    layer_gap_px: int = 52
    skew_x_px: int = 40
    skew_y_px: int = 20
    mark_size_px: int = 66
    option_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one instance."""

    query_id: str
    layout_variant: str
    style_variant: str
    option_count: int
    answer_option_index: int
    target_layer: str
    target_answer: int
    query_id_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    option_count_probabilities: Dict[str, float]
    answer_option_probabilities: Dict[str, float]
    target_layer_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Sample:
    """Constructed 3D Tic-Tac-Toe scene and query witness."""

    query_id: str
    board: Board
    answer: int | str
    answer_type: str
    target_player: str
    target_layer: str
    option_cells: Tuple[Coord, ...]
    answer_cell: Coord | None
    support_cells: Tuple[Coord, ...]
    annotation_coords: Tuple[Coord, ...]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered scene and pixel projection maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class _BoardVisualStyle:
    """Resolved nonsemantic board styling."""

    layer_fill_rgb: Tuple[int, int, int]
    cell_fill_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    border_rgb: Tuple[int, int, int]
    x_rgb: Tuple[int, int, int]
    o_rgb: Tuple[int, int, int]
    option_fill_rgb: Tuple[int, int, int]
    option_outline_rgb: Tuple[int, int, int]
    option_text_rgb: Tuple[int, int, int]
    label_rgb: Tuple[int, int, int]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="games_tic_tac_toe_3d_base",
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def _layer_index(layer: str) -> int:
    mapping = {"top": 0, "middle": 1, "bottom": 2}
    if str(layer) not in mapping:
        raise ValueError(f"unsupported 3D Tic-Tac-Toe layer: {layer}")
    return int(mapping[str(layer)])


def _coord_id(coord: Coord) -> str:
    z, row, col = coord
    return f"cell_z{int(z)}_r{int(row) + 1}_c{int(col) + 1}"


def _layer_id(layer_index: int) -> str:
    return f"layer_{LAYERS[int(layer_index)][0]}"


def _all_coords() -> Tuple[Coord, ...]:
    return tuple((z, row, col) for z in range(BOARD_SIZE) for row in range(BOARD_SIZE) for col in range(BOARD_SIZE))


def _build_winning_lines() -> Tuple[Line, ...]:
    directions: list[Coord] = []
    for dz, dr, dc in product((-1, 0, 1), repeat=3):
        if (dz, dr, dc) == (0, 0, 0):
            continue
        first_nonzero = next(value for value in (dz, dr, dc) if value != 0)
        if first_nonzero > 0:
            directions.append((int(dz), int(dr), int(dc)))
    lines: list[Line] = []
    for start in _all_coords():
        z, row, col = start
        for dz, dr, dc in directions:
            prev = (z - dz, row - dr, col - dc)
            if all(0 <= int(value) < BOARD_SIZE for value in prev):
                continue
            coords: list[Coord] = []
            for step in range(BOARD_SIZE):
                coord = (z + step * dz, row + step * dr, col + step * dc)
                if not all(0 <= int(value) < BOARD_SIZE for value in coord):
                    break
                coords.append(coord)
            if len(coords) == BOARD_SIZE:
                lines.append(tuple(coords))  # type: ignore[arg-type]
    return tuple(lines)


WINNING_LINES: Tuple[Line, ...] = _build_winning_lines()


def _empty_board() -> list[list[list[str]]]:
    return [[["" for _col in range(BOARD_SIZE)] for _row in range(BOARD_SIZE)] for _z in range(BOARD_SIZE)]


def _freeze_board(board: Sequence[Sequence[Sequence[str]]]) -> Board:
    return tuple(tuple(tuple(str(value) for value in row) for row in layer) for layer in board)


def _board_get(board: Board | Sequence[Sequence[Sequence[str]]], coord: Coord) -> str:
    z, row, col = coord
    return str(board[int(z)][int(row)][int(col)])


def _board_set(board: list[list[list[str]]], coord: Coord, value: str) -> None:
    z, row, col = coord
    board[int(z)][int(row)][int(col)] = str(value)


def _completed_lines(board: Board | Sequence[Sequence[Sequence[str]]], player: str) -> Tuple[Line, ...]:
    completed: list[Line] = []
    for line in WINNING_LINES:
        if all(_board_get(board, coord) == str(player) for coord in line):
            completed.append(line)
    return tuple(completed)


def _immediate_winning_cells(board: Board | Sequence[Sequence[Sequence[str]]], player: str) -> Tuple[Coord, ...]:
    cells: set[Coord] = set()
    for line in WINNING_LINES:
        values = [_board_get(board, coord) for coord in line]
        if values.count(str(player)) == BOARD_SIZE - 1 and values.count("") == 1:
            cells.add(line[values.index("")])
    return tuple(sorted(cells))


def _target_player(query_id: str) -> str:
    return "X" if str(query_id).startswith("x_") else "O"


def _opponent(player: str) -> str:
    return "O" if str(player) == "X" else "X"


def _resolve_named_axis(
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
        supported_variants=tuple(str(value) for value in supported),
    )


def _resolve_query_id(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_queries: Sequence[str],
    weights_key: str,
) -> Tuple[str, Dict[str, float]]:
    local_params = dict(params)
    if str(weights_key) != "query_id_weights":
        configured = local_params.get(str(weights_key), group_default(_GEN_DEFAULTS, str(weights_key), None))
        if configured is not None and "query_id_weights" not in local_params:
            local_params["query_id_weights"] = configured
    return resolve_games_query_id(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=local_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=tuple(str(value) for value in supported_queries),
    )


def _resolve_integer_axis(
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
        fallback_support=tuple(int(value) for value in fallback_support),
        namespace=f"{str(task_id)}.{str(namespace)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return int(value), dict(probabilities)


def _resolve_answer_option_index(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    option_count: int,
) -> Tuple[int, Dict[str, float]]:
    return _resolve_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="answer_option_index_support",
        explicit_key="answer_option_index",
        fallback_support=tuple(range(int(option_count))),
        namespace=f"answer_option_index.{int(option_count)}",
        balanced_flag_key="balanced_answer_option_sampling",
    )


def _resolve_axes(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_queries: Sequence[str],
    query_weights_key: str,
) -> _ResolvedAxes:
    query_id, query_probs = _resolve_query_id(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        supported_queries=tuple(str(value) for value in supported_queries),
        weights_key=str(query_weights_key),
    )
    layout_variant, layout_probs = _resolve_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace="layout_variant",
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=LAYOUT_VARIANTS,
    )
    style_variant, style_probs = _resolve_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=STYLE_VARIANTS,
    )
    option_count, option_probs = _resolve_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=_DEFAULTS.option_count_support,
        namespace="option_count",
        balanced_flag_key="balanced_option_count_sampling",
    )
    answer_option_index, answer_option_probs = _resolve_answer_option_index(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        option_count=int(option_count),
    )
    target_layer, target_layer_probs = _resolve_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace="target_layer",
        explicit_key="target_layer",
        weights_key="target_layer_weights",
        balance_flag_key="balanced_target_layer_sampling",
        supported=tuple(layer for layer, _label in LAYERS),
    )
    target_answer, target_answer_probs = _resolve_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="layer_piece_count_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.layer_piece_count_support,
        namespace="layer_piece_count.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        layout_variant=str(layout_variant),
        style_variant=str(style_variant),
        option_count=int(option_count),
        answer_option_index=int(answer_option_index),
        target_layer=str(target_layer),
        target_answer=int(target_answer),
        query_id_probabilities=dict(query_probs),
        layout_variant_probabilities=dict(layout_probs),
        style_variant_probabilities=dict(style_probs),
        option_count_probabilities=dict(option_probs),
        answer_option_probabilities=dict(answer_option_probs),
        target_layer_probabilities=dict(target_layer_probs),
        target_answer_probabilities=dict(target_answer_probs),
    )


def _random_empty_coords(board: Sequence[Sequence[Sequence[str]]], *, exclude: set[Coord] | None = None) -> list[Coord]:
    excluded = set(exclude or set())
    return [coord for coord in _all_coords() if coord not in excluded and _board_get(board, coord) == ""]


def _sample_winning_move_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target_player = _target_player(str(axes.query_id))
    other_player = _opponent(target_player)
    line = tuple(rng.choice(WINNING_LINES))
    answer_cell = tuple(rng.choice(line))
    support_cells = tuple(coord for coord in line if coord != answer_cell)
    board = _empty_board()
    for coord in support_cells:
        _board_set(board, coord, target_player)

    filler_target = int(rng.randint(6, 13))
    candidate_coords = _random_empty_coords(board, exclude={answer_cell})
    rng.shuffle(candidate_coords)
    for coord in candidate_coords:
        if sum(1 for placed in _all_coords() if _board_get(board, placed) != "") >= filler_target + len(support_cells):
            break
        mark = target_player if rng.random() < 0.45 else other_player
        _board_set(board, coord, mark)
        if _completed_lines(board, "X") or _completed_lines(board, "O"):
            _board_set(board, coord, "")

    frozen = _freeze_board(board)
    winning_cells = set(_immediate_winning_cells(frozen, target_player))
    if answer_cell not in winning_cells:
        raise ValueError("constructed winning move no longer completes a line")
    distractors = [coord for coord in _random_empty_coords(frozen, exclude={answer_cell}) if coord not in winning_cells]
    if len(distractors) < int(axes.option_count) - 1:
        raise ValueError("not enough non-winning distractor cells")
    rng.shuffle(distractors)
    option_cells = list(distractors[: int(axes.option_count) - 1])
    insert_at = min(max(0, int(axes.answer_option_index)), int(axes.option_count) - 1)
    option_cells.insert(int(insert_at), answer_cell)
    label = OPTION_LABELS[int(insert_at)]
    correct_options = [
        OPTION_LABELS[index]
        for index, coord in enumerate(option_cells)
        if coord in winning_cells
    ]
    if tuple(correct_options) != (label,):
        raise ValueError("winning-move options are not unique")
    return _Sample(
        query_id=str(axes.query_id),
        board=frozen,
        answer=str(label),
        answer_type="string",
        target_player=str(target_player),
        target_layer="",
        option_cells=tuple(option_cells),
        answer_cell=answer_cell,
        support_cells=tuple(support_cells),
        annotation_coords=(answer_cell, *support_cells),
        metadata={
            "winning_line": [[int(c[0]), int(c[1]), int(c[2])] for c in line],
            "winning_cells": [[int(c[0]), int(c[1]), int(c[2])] for c in sorted(winning_cells)],
            "correct_option_labels": list(correct_options),
        },
    )


def _sample_layer_count_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target_player = _target_player(str(axes.query_id))
    other_player = _opponent(target_player)
    target_layer_index = _layer_index(str(axes.target_layer))
    board = _empty_board()
    layer_coords = [(target_layer_index, row, col) for row in range(BOARD_SIZE) for col in range(BOARD_SIZE)]
    rng.shuffle(layer_coords)
    target_cells = tuple(layer_coords[: int(axes.target_answer)])
    for coord in target_cells:
        _board_set(board, coord, target_player)

    remaining_layer = [coord for coord in layer_coords if coord not in set(target_cells)]
    rng.shuffle(remaining_layer)
    opponent_in_layer = int(rng.randint(0, min(3, len(remaining_layer))))
    for coord in remaining_layer[:opponent_in_layer]:
        _board_set(board, coord, other_player)

    outside_coords = [coord for coord in _all_coords() if int(coord[0]) != int(target_layer_index)]
    rng.shuffle(outside_coords)
    outside_piece_count = int(rng.randint(5, min(14, len(outside_coords))))
    for coord in outside_coords[:outside_piece_count]:
        _board_set(board, coord, target_player if rng.random() < 0.5 else other_player)

    frozen = _freeze_board(board)
    annotation_coords = tuple(
        coord
        for coord in layer_coords
        if _board_get(frozen, coord) == target_player
    )
    if len(annotation_coords) != int(axes.target_answer):
        raise ValueError("layer piece-count construction mismatch")
    return _Sample(
        query_id=str(axes.query_id),
        board=frozen,
        answer=int(axes.target_answer),
        answer_type="integer",
        target_player=str(target_player),
        target_layer=str(axes.target_layer),
        option_cells=(),
        answer_cell=None,
        support_cells=(),
        annotation_coords=tuple(annotation_coords),
        metadata={
            "target_layer_index": int(target_layer_index),
            "target_layer_name": str(axes.target_layer),
        },
    )


def _sample_scene(*, task_id: str, instance_seed: int, axes: _ResolvedAxes, max_attempts: int) -> _Sample:
    attempts = max(1, int(max_attempts))
    last_error: Exception | None = None
    for attempt in range(attempts):
        rng = spawn_rng(int(instance_seed), f"{str(task_id)}.sample.{int(attempt)}")
        try:
            if str(axes.query_id) in WINNING_MOVE_QUERIES:
                return _sample_winning_move_scene(rng=rng, axes=axes)
            return _sample_layer_count_scene(rng=rng, axes=axes)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"failed to sample {task_id} after {attempts} attempts: {last_error}") from last_error


def _resolve_board_visual_style(style_variant: str) -> Tuple[_BoardVisualStyle, Dict[str, Any]]:
    styles = {
        "classic_grid": _BoardVisualStyle(
            layer_fill_rgb=(235, 241, 250),
            cell_fill_rgb=(249, 252, 255),
            grid_rgb=(75, 94, 126),
            border_rgb=(35, 58, 92),
            x_rgb=(7, 39, 104),
            o_rgb=(126, 19, 36),
            option_fill_rgb=(255, 224, 79),
            option_outline_rgb=(53, 62, 83),
            option_text_rgb=(27, 31, 43),
            label_rgb=(30, 48, 74),
        ),
        "paper_board": _BoardVisualStyle(
            layer_fill_rgb=(241, 234, 213),
            cell_fill_rgb=(252, 248, 232),
            grid_rgb=(129, 105, 76),
            border_rgb=(92, 70, 51),
            x_rgb=(18, 52, 96),
            o_rgb=(125, 39, 27),
            option_fill_rgb=(242, 211, 98),
            option_outline_rgb=(84, 67, 45),
            option_text_rgb=(35, 30, 24),
            label_rgb=(64, 48, 34),
        ),
        "arcade_blue": _BoardVisualStyle(
            layer_fill_rgb=(23, 43, 76),
            cell_fill_rgb=(32, 61, 104),
            grid_rgb=(98, 210, 234),
            border_rgb=(73, 232, 237),
            x_rgb=(226, 252, 255),
            o_rgb=(255, 219, 93),
            option_fill_rgb=(255, 231, 67),
            option_outline_rgb=(255, 255, 255),
            option_text_rgb=(28, 31, 39),
            label_rgb=(225, 247, 255),
        ),
        "mint_table": _BoardVisualStyle(
            layer_fill_rgb=(212, 235, 225),
            cell_fill_rgb=(238, 249, 241),
            grid_rgb=(72, 135, 113),
            border_rgb=(32, 93, 76),
            x_rgb=(5, 70, 132),
            o_rgb=(128, 24, 51),
            option_fill_rgb=(255, 227, 111),
            option_outline_rgb=(36, 92, 67),
            option_text_rgb=(28, 44, 35),
            label_rgb=(27, 74, 61),
        ),
        "charcoal_lines": _BoardVisualStyle(
            layer_fill_rgb=(54, 58, 65),
            cell_fill_rgb=(72, 77, 86),
            grid_rgb=(171, 183, 197),
            border_rgb=(226, 232, 240),
            x_rgb=(235, 250, 255),
            o_rgb=(255, 216, 118),
            option_fill_rgb=(255, 218, 78),
            option_outline_rgb=(250, 250, 245),
            option_text_rgb=(24, 27, 32),
            label_rgb=(239, 244, 250),
        ),
    }
    resolved = str(style_variant) if str(style_variant) in styles else "classic_grid"
    return styles[resolved], {
        "style_variant": str(resolved),
        "available_styles": list(STYLE_VARIANTS),
        "board_style_policy": "scene_local_tic_tac_toe_3d_palette",
    }


def _int_default(params: Mapping[str, Any], key: str, fallback: int) -> int:
    if str(key) in params:
        return int(params[str(key)])
    return int(group_default(_RENDER_DEFAULTS, str(key), int(fallback)))


def _center_of_bbox(bbox: Sequence[float]) -> Tuple[float, float]:
    return ((float(bbox[0]) + float(bbox[2])) / 2.0, (float(bbox[1]) + float(bbox[3])) / 2.0)


def _polygon_bbox(points: Sequence[Sequence[float]]) -> BBox:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _polygon_center(points: Sequence[Sequence[float]]) -> Tuple[float, float]:
    if not points:
        raise ValueError("points must be non-empty")
    return (
        sum(float(point[0]) for point in points) / float(len(points)),
        sum(float(point[1]) for point in points) / float(len(points)),
    )


def _grid_point(
    *,
    origin_x: float,
    origin_y: float,
    row: int,
    col: int,
    col_step: float,
    row_step: float,
    skew_x: float,
    skew_y: float,
) -> Tuple[float, float]:
    return (
        float(origin_x + (int(col) * float(col_step)) + (int(row) * float(skew_x))),
        float(origin_y + (int(row) * float(row_step)) + (int(col) * float(skew_y))),
    )


def _cell_polygon(
    *,
    origin_x: float,
    origin_y: float,
    row: int,
    col: int,
    col_step: float,
    row_step: float,
    skew_x: float,
    skew_y: float,
) -> Tuple[Tuple[float, float], ...]:
    return (
        _grid_point(origin_x=origin_x, origin_y=origin_y, row=row, col=col, col_step=col_step, row_step=row_step, skew_x=skew_x, skew_y=skew_y),
        _grid_point(origin_x=origin_x, origin_y=origin_y, row=row, col=col + 1, col_step=col_step, row_step=row_step, skew_x=skew_x, skew_y=skew_y),
        _grid_point(origin_x=origin_x, origin_y=origin_y, row=row + 1, col=col + 1, col_step=col_step, row_step=row_step, skew_x=skew_x, skew_y=skew_y),
        _grid_point(origin_x=origin_x, origin_y=origin_y, row=row + 1, col=col, col_step=col_step, row_step=row_step, skew_x=skew_x, skew_y=skew_y),
    )


def _contrast_halo_rgb(mark_rgb: Sequence[int]) -> Tuple[int, int, int]:
    """Return an opposite-luminance halo for hand-drawn X/O board marks."""

    return (10, 14, 22) if sum(int(channel) for channel in mark_rgb[:3]) >= 470 else (250, 252, 255)


def _draw_tic_tac_toe_mark(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    mark: str,
    mark_rgb: Sequence[int],
    mark_size_px: int,
) -> None:
    """Draw a high-contrast X/O mark without depending on font glyph shape."""

    cx, cy = float(center[0]), float(center[1])
    size = max(24.0, float(mark_size_px))
    half_x = float(size) * 0.34
    half_y = float(size) * 0.23
    stroke_width = max(4, int(round(float(size) * 0.11)))
    halo_width = int(stroke_width + max(3, int(round(float(size) * 0.055))))
    fill = tuple(int(channel) for channel in mark_rgb[:3])
    halo = _contrast_halo_rgb(fill)
    if str(mark) == "X":
        segments = (
            ((cx - half_x, cy - half_y), (cx + half_x, cy + half_y)),
            ((cx - half_x, cy + half_y), (cx + half_x, cy - half_y)),
        )
        for p0, p1 in segments:
            draw.line((p0, p1), fill=halo, width=halo_width)
        for p0, p1 in segments:
            draw.line((p0, p1), fill=fill, width=stroke_width)
        return
    bbox = (cx - half_x, cy - half_y, cx + half_x, cy + half_y)
    draw.ellipse(bbox, outline=halo, width=halo_width)
    draw.ellipse(bbox, outline=fill, width=stroke_width)


def _render_scene(
    *,
    sample: _Sample,
    axes: _ResolvedAxes,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _RenderedScene:
    base_canvas_width = _int_default(params, "canvas_width", _DEFAULTS.canvas_width)
    base_canvas_height = _int_default(params, "canvas_height", _DEFAULTS.canvas_height)
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.tic_tac_toe_3d.panel_style",
        treatment_weights=group_default(_GEN_DEFAULTS, "panel_treatment_weights", {}),
        palette_weights=group_default(_GEN_DEFAULTS, "panel_palette_weights", {}),
    )
    layout_jitter = resolve_games_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.tic_tac_toe_3d.layout",
    )
    unit_scale, unit_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.tic_tac_toe_3d.unit_size",
    )
    cell = scale_games_px(_int_default(params, "cell_size_px", _DEFAULTS.cell_size_px), unit_scale, min_px=30)
    _gap = scale_games_px(_int_default(params, "cell_gap_px", _DEFAULTS.cell_gap_px), unit_scale, min_px=0)
    layer_gap = scale_games_px(_int_default(params, "layer_gap_px", _DEFAULTS.layer_gap_px), unit_scale, min_px=18)
    skew_x = scale_games_px(_int_default(params, "skew_x_px", _DEFAULTS.skew_x_px), unit_scale, min_px=14)
    skew_y = scale_games_px(_int_default(params, "skew_y_px", _DEFAULTS.skew_y_px), unit_scale, min_px=7)
    inner = scale_games_px(_int_default(params, "panel_inner_padding_px", _DEFAULTS.panel_inner_padding_px), unit_scale, min_px=26)
    col_step = float(cell)
    row_step = float(cell) * 0.48
    layer_width = int(round((BOARD_SIZE * col_step) + (BOARD_SIZE * skew_x)))
    layer_height = int(round((BOARD_SIZE * row_step) + (BOARD_SIZE * skew_y)))
    content_width = int(layer_width)
    content_height = int((BOARD_SIZE * layer_height) + ((BOARD_SIZE - 1) * layer_gap))
    raw_panel_width = int(content_width + 2 * inner)
    raw_panel_height = int(content_height + 2 * inner)
    dynamic_canvas_enabled = bool(params.get("dynamic_canvas_size_enabled", group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", True)))
    canvas_width = int(base_canvas_width)
    canvas_height = int(base_canvas_height)
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        side_padding = _int_default(params, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px)
        canvas_width = min(
            int(base_canvas_width),
            max(_int_default(params, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px), int(raw_panel_width + side_padding)),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        side_padding = _int_default(params, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px)
        canvas_height = min(
            int(base_canvas_height),
            max(_int_default(params, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px), int(raw_panel_height + side_padding)),
        )
    margin = _int_default(params, "panel_margin_px", _DEFAULTS.panel_margin_px)
    panel_width = min(int(raw_panel_width), int(canvas_width - 2 * margin))
    panel_height = min(int(raw_panel_height), int(canvas_height - 2 * margin))
    image, background_meta = make_panel_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=panel_style,
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    base_panel = (
        float((canvas_width - panel_width) / 2.0),
        float((canvas_height - panel_height) / 2.0),
        float((canvas_width + panel_width) / 2.0),
        float((canvas_height + panel_height) / 2.0),
    )
    panel_bbox, _dx, _dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=base_panel,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    draw_panel_scene_chrome(
        draw,
        bbox=tuple(int(round(value)) for value in panel_bbox),
        style=panel_style,
        radius=18,
        border_width=3,
    )
    board_style, board_style_meta = _resolve_board_visual_style(str(axes.style_variant))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.tic_tac_toe_3d.font_family",
        params=params,
    )
    mark_size = scale_games_px(_int_default(params, "mark_size_px", _DEFAULTS.mark_size_px), unit_scale, min_px=30)
    option_font = load_font(
        scale_games_px(_int_default(params, "option_font_size_px", _DEFAULTS.option_font_size_px), unit_scale, min_px=13),
        bold=True,
        font_family=str(font_family),
    )
    content_left = float(panel_bbox[0] + inner)
    content_top = float(panel_bbox[1] + inner)
    layer_origins: dict[int, Tuple[float, float]] = {}
    for z in range(BOARD_SIZE):
        x0 = content_left
        y0 = content_top + float(z * (layer_height + layer_gap))
        layer_origins[int(z)] = (float(x0), float(y0))

    option_label_by_coord = {
        coord: OPTION_LABELS[index]
        for index, coord in enumerate(sample.option_cells)
    }
    entities: List[Dict[str, Any]] = []
    entity_bboxes: Dict[str, List[float]] = {}
    entity_points: Dict[str, List[float]] = {}
    layer_bboxes: Dict[str, List[float]] = {}
    cell_bboxes: Dict[str, List[float]] = {}
    cell_centers: Dict[str, List[float]] = {}

    for z in range(BOARD_SIZE):
        origin_x, origin_y = layer_origins[int(z)]
        layer_poly = (
            _grid_point(
                origin_x=origin_x,
                origin_y=origin_y,
                row=0,
                col=0,
                col_step=col_step,
                row_step=row_step,
                skew_x=float(skew_x),
                skew_y=float(skew_y),
            ),
            _grid_point(
                origin_x=origin_x,
                origin_y=origin_y,
                row=0,
                col=BOARD_SIZE,
                col_step=col_step,
                row_step=row_step,
                skew_x=float(skew_x),
                skew_y=float(skew_y),
            ),
            _grid_point(
                origin_x=origin_x,
                origin_y=origin_y,
                row=BOARD_SIZE,
                col=BOARD_SIZE,
                col_step=col_step,
                row_step=row_step,
                skew_x=float(skew_x),
                skew_y=float(skew_y),
            ),
            _grid_point(
                origin_x=origin_x,
                origin_y=origin_y,
                row=BOARD_SIZE,
                col=0,
                col_step=col_step,
                row_step=row_step,
                skew_x=float(skew_x),
                skew_y=float(skew_y),
            ),
        )
        layer_bbox = _polygon_bbox(layer_poly)
        layer_key = _layer_id(int(z))
        rounded_layer_bbox = [round(float(value), 3) for value in layer_bbox]
        layer_bboxes[layer_key] = list(rounded_layer_bbox)
        entity_bboxes[layer_key] = list(rounded_layer_bbox)
        entities.append(
            {
                "entity_id": str(layer_key),
                "entity_type": "tic_tac_toe_3d_layer",
                "layer_name": str(LAYERS[int(z)][0]),
                "bbox_px": list(rounded_layer_bbox),
            }
        )
        draw.polygon(layer_poly, fill=tuple(board_style.layer_fill_rgb), outline=tuple(board_style.border_rgb))
        draw.line((*layer_poly, layer_poly[0]), fill=tuple(board_style.border_rgb), width=3)
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                coord = (int(z), int(row), int(col))
                cell_poly = _cell_polygon(
                    origin_x=origin_x,
                    origin_y=origin_y,
                    row=int(row),
                    col=int(col),
                    col_step=col_step,
                    row_step=row_step,
                    skew_x=float(skew_x),
                    skew_y=float(skew_y),
                )
                bbox = _polygon_bbox(cell_poly)
                draw.polygon(cell_poly, fill=tuple(board_style.cell_fill_rgb), outline=tuple(board_style.grid_rgb))
                draw.line((*cell_poly, cell_poly[0]), fill=tuple(board_style.grid_rgb), width=2)
                cell_id = _coord_id(coord)
                bbox_list = [round(float(value), 3) for value in bbox]
                center = _polygon_center(cell_poly)
                center_list = [round(float(center[0]), 3), round(float(center[1]), 3)]
                entity_bboxes[cell_id] = list(bbox_list)
                cell_bboxes[cell_id] = list(bbox_list)
                entity_points[cell_id] = list(center_list)
                cell_centers[cell_id] = list(center_list)
                value = _board_get(sample.board, coord)
                entities.append(
                    {
                        "entity_id": str(cell_id),
                        "entity_type": "tic_tac_toe_3d_cell",
                        "layer_name": str(LAYERS[int(z)][0]),
                        "layer_index": int(z),
                        "row": int(row + 1),
                        "col": int(col + 1),
                        "mark": str(value),
                        "option_label": str(option_label_by_coord.get(coord, "")),
                        "bbox_px": list(bbox_list),
                        "center_px": list(center_list),
                    }
                )
                if value:
                    mark_fill = board_style.x_rgb if str(value) == "X" else board_style.o_rgb
                    _draw_tic_tac_toe_mark(
                        draw,
                        center=center,
                        mark=str(value),
                        mark_rgb=mark_fill,
                        mark_size_px=int(mark_size),
                    )
                if coord in option_label_by_coord:
                    label = option_label_by_coord[coord]
                    radius = max(8.0, float(cell) * 0.18)
                    label_bbox = (
                        float(center[0] - radius),
                        float(center[1] - radius),
                        float(center[0] + radius),
                        float(center[1] + radius),
                    )
                    draw.ellipse(
                        label_bbox,
                        fill=tuple(board_style.option_fill_rgb),
                        outline=tuple(board_style.option_outline_rgb),
                        width=2,
                    )
                    draw_centered_game_text(
                        draw,
                        text=str(label),
                        center=_center_of_bbox(label_bbox),
                        font=option_font,
                        fill=board_style.option_text_rgb,
                        stroke_fill=board_style.option_fill_rgb,
                        stroke_width=0,
                        role="board_mark",
                        required=True,
                        surface_rgbs=[board_style.option_fill_rgb],
                        preferred_rgbs=[board_style.option_text_rgb],
                        candidate_rgbs=[board_style.option_text_rgb],
                        instance_seed=int(instance_seed),
                        namespace=f"{str(task_id)}.tic_tac_toe_3d.option.{label}",
                    )

    render_map = {
        "entity_bboxes_px": dict(entity_bboxes),
        "entity_points_px": dict(entity_points),
        "layer_bboxes_px": dict(layer_bboxes),
        "cell_bboxes_px": dict(cell_bboxes),
        "cell_centers_px": dict(cell_centers),
        "panel_bbox_px": [round(float(value), 3) for value in panel_bbox],
        "layout_variant": str(axes.layout_variant),
        "panel_scene_style": dict(panel_style_meta),
        "tic_tac_toe_3d_board_style": dict(board_style_meta),
        "font_family": str(font_family),
        "text_style": {"font_family": str(font_family), "board_marks": "drawn_x_o_strokes_v1"},
        "layout_jitter": attach_games_unit_size_jitter(resolved_jitter, unit_meta),
        "effective_cell_size_px": int(cell),
        "effective_cell_gap_px": int(_gap),
        "effective_mark_size_px": int(mark_size),
        "effective_projection": {
            "col_step_px": round(float(col_step), 3),
            "row_step_px": round(float(row_step), 3),
            "skew_x_px": int(skew_x),
            "skew_y_px": int(skew_y),
            "layer_width_px": int(layer_width),
            "layer_height_px": int(layer_height),
        },
        "dynamic_canvas": {
            "enabled": bool(dynamic_canvas_enabled),
            "base_canvas_width": int(base_canvas_width),
            "base_canvas_height": int(base_canvas_height),
            "raw_panel_width_px": int(raw_panel_width),
            "raw_panel_height_px": int(raw_panel_height),
            "resolved_canvas_width": int(canvas_width),
            "resolved_canvas_height": int(canvas_height),
        },
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=dict(render_map),
        style_meta={
            "panel_scene_style": dict(panel_style_meta),
            "tic_tac_toe_3d_board_style": dict(board_style_meta),
            "text_style": {
                "font_family": str(font_family),
                "font_asset": get_font_family_record(str(font_family)).to_trace(),
            },
        },
        background_meta=dict(background_meta),
    )


def _json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) in WINNING_MOVE_QUERIES:
        answer_and_annotation = {
            "annotation": [[320, 190, 380, 250], [250, 190, 310, 250], [390, 190, 450, 250]],
            "answer": "B",
        }
        answer_only = {"answer": "B"}
    else:
        answer_and_annotation = {"annotation": [[212, 318], [285, 391], [358, 318]], "answer": 3}
        answer_only = {"answer": 3}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _build_prompt(sample: _Sample, *, instance_seed: int) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_tic_tac_toe_3d",
            f"answer_hint_{str(sample.query_id)}",
            f"annotation_hint_{str(sample.query_id)}",
            "tic_tac_toe_3d_winning_rule_text",
        ),
        context=f"prompt defaults for {str(sample.query_id)}",
    )
    json_example, json_example_answer_only = _json_examples(str(sample.query_id))
    target_layer_label = str(sample.target_layer)
    slots = {
        "object_description": str(prompt_defaults["object_description_tic_tac_toe_3d"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[f"answer_hint_{str(sample.query_id)}"]),
        "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(sample.query_id)}"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "winning_rule_text": str(prompt_defaults["tic_tac_toe_3d_winning_rule_text"]),
        "target_layer_label": str(target_layer_label),
    }
    prompt_selection = render_task_prompt_variants(
        domain="games",
        task_group=TASK_GROUP,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(sample.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }


def _build_complexity(*, task_id: str, sample: _Sample, annotation_count: int) -> Any:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=str(task_id))
    mark_count = sum(1 for coord in _all_coords() if _board_get(sample.board, coord))
    visual_scan = normalize_linear(float(mark_count), min_value=4.0, max_value=18.0)
    game_reasoning = 0.72 if str(sample.query_id) in WINNING_MOVE_QUERIES else 0.36
    ambiguity = normalize_linear(float(len(sample.option_cells) or annotation_count), min_value=0.0, max_value=6.0)
    output_burden = normalize_linear(float(annotation_count), min_value=0.0, max_value=6.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "game_reasoning": float(game_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def _board_trace(board: Board) -> List[List[List[str]]]:
    return [
        [[str(board[z][row][col]) for col in range(BOARD_SIZE)] for row in range(BOARD_SIZE)]
        for z in range(BOARD_SIZE)
    ]


class _TicTacToe3DTask:
    """Base generator for 3D Tic-Tac-Toe public tasks."""

    domain = "games"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    supported_queries: Tuple[str, ...] = ALL_QUERIES
    query_weights_key = "query_id_weights"

    def generate(self, instance_seed: int, *, params: Dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        params = dict(params or {})
        axes = _resolve_axes(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
            supported_queries=tuple(self.supported_queries),
            query_weights_key=str(self.query_weights_key),
        )
        sample = _sample_scene(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            axes=axes,
            max_attempts=int(max_attempts),
        )
        rendered = _render_scene(
            sample=sample,
            axes=axes,
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
        )
        entity_bboxes = rendered.render_map["entity_bboxes_px"]
        entity_points = rendered.render_map["entity_points_px"]
        annotation_entity_ids = [_coord_id(coord) for coord in sample.annotation_coords]
        if str(sample.query_id) in WINNING_MOVE_QUERIES:
            annotation_value = [list(entity_bboxes[str(entity_id)]) for entity_id in annotation_entity_ids]
            annotation_type = "bbox_set"
        else:
            annotation_value = [list(entity_points[str(entity_id)]) for entity_id in annotation_entity_ids]
            annotation_type = "point_set"

        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(sample, instance_seed=int(instance_seed))
        answer_gt = TypedValue(type=str(sample.answer_type), value=sample.answer)
        annotation_gt = TypedValue(type=str(annotation_type), value=list(annotation_value))
        complexity = _build_complexity(
            task_id=str(self.task_id),
            sample=sample,
            annotation_count=len(annotation_entity_ids),
        )
        answer_option_support = tuple(range(int(axes.option_count)))
        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_tic_tac_toe_3d_board",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_id": SCENE_ID,
                    "query_id": str(sample.query_id),
                    "layout_variant": str(axes.layout_variant),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(BOARD_SIZE),
                    "target_player": str(sample.target_player),
                    "target_layer": str(sample.target_layer),
                    "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": {
                    "query_id": str(sample.query_id),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "layout_variant": str(axes.layout_variant),
                    "layout_variant_probabilities": dict(axes.layout_variant_probabilities),
                    "style_variant": str(axes.style_variant),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "option_count": int(axes.option_count),
                    "option_count_support": list(resolve_integer_support(params, gen_defaults=_GEN_DEFAULTS, key="option_count_support", fallback=_DEFAULTS.option_count_support)),
                    "option_count_probabilities": dict(axes.option_count_probabilities),
                    "answer_option_index": int(axes.answer_option_index),
                    "answer_option_index_support": [int(value) for value in answer_option_support],
                    "answer_option_probabilities": dict(axes.answer_option_probabilities),
                    "target_layer": str(axes.target_layer),
                    "target_layer_probabilities": dict(axes.target_layer_probabilities),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": list(resolve_integer_support(params, gen_defaults=_GEN_DEFAULTS, key="layer_piece_count_support", fallback=_DEFAULTS.layer_piece_count_support)),
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.layout_variant),
                "layout_variant": str(axes.layout_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
                "tic_tac_toe_3d_board_style": dict(rendered.style_meta.get("tic_tac_toe_3d_board_style", {})),
                "text_style": dict(rendered.style_meta.get("text_style", {})),
                "effective_cell_size_px": int(rendered.render_map["effective_cell_size_px"]),
                "effective_mark_size_px": int(rendered.render_map["effective_mark_size_px"]),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": str(sample.query_id),
                "board_size": int(BOARD_SIZE),
                "winning_line_count": int(len(WINNING_LINES)),
                "board_layers": _board_trace(sample.board),
                "layer_names": [str(label) for _key, label in LAYERS],
                "target_player": str(sample.target_player),
                "target_layer": str(sample.target_layer),
                "answer": sample.answer,
                "answer_cell": None if sample.answer_cell is None else [int(v) for v in sample.answer_cell],
                "support_cells": [[int(v) for v in coord] for coord in sample.support_cells],
                "option_cells": [[int(v) for v in coord] for coord in sample.option_cells],
                "option_labels": list(OPTION_LABELS[: len(sample.option_cells)]),
                "annotation_coords": [[int(v) for v in coord] for coord in sample.annotation_coords],
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
                **dict(sample.metadata),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in annotation_entity_ids],
            },
            "projected_annotation": (
                {
                    "type": "bbox_set",
                    "bbox_set": [list(value) for value in annotation_value],
                    "pixel_bbox_set": [list(value) for value in annotation_value],
                }
                if str(annotation_type) == "bbox_set"
                else {
                    "type": "point_set",
                    "point_set": [list(value) for value in annotation_value],
                    "pixel_point_set": [list(value) for value in annotation_value],
                }
            ),
            "background": dict(rendered.background_meta),
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt),
            prompt_variants=dict(prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


@register_task
class GamesTicTacToe3DWinningMoveCellLabelTask(_TicTacToe3DTask):
    """Choose the labeled empty cell that completes a 3D Tic-Tac-Toe line."""

    task_id = "task_games__tic_tac_toe_3d__winning_move_cell_label"
    supported_queries = WINNING_MOVE_QUERIES
    query_weights_key = "winning_move_query_id_weights"


@register_task
class GamesTicTacToe3DLayerPieceCountTask(_TicTacToe3DTask):
    """Count X or O pieces in a named 3D Tic-Tac-Toe layer."""

    task_id = "task_games__tic_tac_toe_3d__layer_piece_count"
    supported_queries = LAYER_COUNT_QUERIES
    query_weights_key = "layer_piece_count_query_id_weights"


__all__ = [
    "WINNING_LINES",
    "_immediate_winning_cells",
    "GamesTicTacToe3DLayerPieceCountTask",
    "GamesTicTacToe3DWinningMoveCellLabelTask",
]
