"""Counterfactual-style canonical board grid counting task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_centered_text
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.complexity import build_puzzle_complexity, clamp_unit_interval, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles__counterfactual_board__board_grid_count"
SCENE_ID = "counterfactual_board"

CHESS_STYLE = "chess_checkers"
SUDOKU_STYLE = "sudoku"
XIANGQI_STYLE = "xiangqi"
SUPPORTED_BOARD_STYLES: Tuple[str, ...] = (CHESS_STYLE, SUDOKU_STYLE, XIANGQI_STYLE)

ROW_COUNT_QUERY = "row_count"
COLUMN_COUNT_QUERY = "column_count"
CELL_COUNT_QUERY = "cell_count"
HORIZONTAL_LINE_COUNT_QUERY = "horizontal_line_count"
VERTICAL_LINE_COUNT_QUERY = "vertical_line_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    ROW_COUNT_QUERY,
    COLUMN_COUNT_QUERY,
    HORIZONTAL_LINE_COUNT_QUERY,
    VERTICAL_LINE_COUNT_QUERY,
)

_STYLE_SPECS: Dict[str, Dict[str, Any]] = {
    CHESS_STYLE: {
        "canonical_rows": 8,
        "canonical_cols": 8,
        "row_support": tuple(range(6, 11)),
        "col_support": tuple(range(6, 11)),
        "valid_queries": (ROW_COUNT_QUERY, COLUMN_COUNT_QUERY),
        "grid_kind": "cell_board",
    },
    SUDOKU_STYLE: {
        "canonical_rows": 9,
        "canonical_cols": 9,
        "row_support": tuple(range(7, 12)),
        "col_support": tuple(range(7, 12)),
        "valid_queries": (ROW_COUNT_QUERY, COLUMN_COUNT_QUERY),
        "grid_kind": "cell_board",
    },
    XIANGQI_STYLE: {
        "canonical_rows": 10,
        "canonical_cols": 9,
        "row_support": tuple(range(8, 13)),
        "col_support": tuple(range(7, 12)),
        "valid_queries": (HORIZONTAL_LINE_COUNT_QUERY, VERTICAL_LINE_COUNT_QUERY),
        "grid_kind": "line_board",
    },
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "counterfactual")
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="counterfactual", apply_prob=0.0)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="counterfactual")


@dataclass(frozen=True)
class _GridElementSpec:
    element_id: str
    element_type: str
    bbox: List[float]


@dataclass(frozen=True)
class _DecorativeSpec:
    entity_id: str
    entity_type: str
    bbox: List[float]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedBoard:
    image: Image.Image
    entities: List[Dict[str, Any]]
    counted_elements: List[_GridElementSpec]
    board_bbox: List[float]
    render_map: Dict[str, Any]


def _scale_bbox(bbox: Sequence[float], scale: int) -> List[float]:
    return [float(value) * int(scale) for value in bbox]


def _scale_bbox_about_center(bbox: Sequence[float], unit_scale: float) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    width = (x1 - x0) * float(unit_scale)
    height = (y1 - y0) * float(unit_scale)
    return [
        float(cx - 0.5 * width),
        float(cy - 0.5 * height),
        float(cx + 0.5 * width),
        float(cy + 0.5 * height),
    ]


def _draw_centered_label(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font_size_px: float,
    scale: int,
    fill_rgb: Tuple[int, int, int],
    stroke_rgb: Tuple[int, int, int],
    stroke_width_px: int = 1,
) -> None:
    font = load_font(max(8, int(round(float(font_size_px) * int(scale)))), bold=True)
    draw_centered_text(
        draw,
        text=str(text),
        center=(float(center[0]) * int(scale), float(center[1]) * int(scale)),
        font=font,
        fill=fill_rgb + (255,),
        stroke_fill=stroke_rgb + (235,),
        stroke_width=max(0, int(stroke_width_px) * int(scale)),
    )


def _draw_piece_disc(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    scale: int,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    width_px: int,
) -> None:
    draw.ellipse(
        _scale_bbox(bbox, int(scale)),
        fill=fill_rgb + (255,),
        outline=outline_rgb + (245,),
        width=max(1, int(width_px) * int(scale)),
    )


def _background_rgb_from_meta(background_meta: Mapping[str, Any], fallback: Sequence[int]) -> Tuple[int, int, int]:
    style_spec = background_meta.get("style_spec", {})
    if isinstance(style_spec, Mapping):
        return _rgb(style_spec.get("background_rgb", style_spec.get("color")), fallback)
    return _rgb(None, fallback)


def _style_probability_map(gen_defaults: Mapping[str, Any], params: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get(
        "board_style_weights",
        group_default(gen_defaults, "board_style_weights", {style: 1.0 for style in SUPPORTED_BOARD_STYLES}),
    )
    if not isinstance(raw, Mapping):
        raise ValueError("board_style_weights must be a mapping")
    return normalize_positive_weights(
        {str(style): float(raw.get(str(style), 0.0)) for style in SUPPORTED_BOARD_STYLES},
        default_keys=SUPPORTED_BOARD_STYLES,
    )


def _query_probability_map(gen_defaults: Mapping[str, Any], params: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get(
        "query_id_weights",
        group_default(gen_defaults, "query_id_weights", {query_id: 1.0 for query_id in SUPPORTED_QUERY_IDS}),
    )
    if not isinstance(raw, Mapping):
        raise ValueError("query_id_weights must be a mapping")
    return normalize_positive_weights(
        {str(query_id): float(raw.get(str(query_id), 0.0)) for query_id in SUPPORTED_QUERY_IDS},
        default_keys=SUPPORTED_QUERY_IDS,
    )


def _valid_queries_for_style(style: str) -> Tuple[str, ...]:
    return tuple(str(value) for value in _STYLE_SPECS[str(style)]["valid_queries"])


def _compatible_styles_for_query(query_id: str) -> Tuple[str, ...]:
    return tuple(style for style in SUPPORTED_BOARD_STYLES if str(query_id) in _valid_queries_for_style(style))


def _resolve_style(gen_defaults: Mapping[str, Any], params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    probabilities = _style_probability_map(gen_defaults, params)
    explicit = params.get("board_style")
    if explicit is not None:
        style = str(explicit)
        if style not in SUPPORTED_BOARD_STYLES:
            raise ValueError(f"unsupported board_style: {style!r}")
        return style, dict(probabilities)
    explicit_query = params.get("query_id")
    candidate_styles = SUPPORTED_BOARD_STYLES
    if explicit_query is not None:
        candidate_styles = _compatible_styles_for_query(str(explicit_query))
        if not candidate_styles:
            raise ValueError(f"query_id is incompatible with all board styles: {explicit_query!r}")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:board_style")
    compatible_probabilities = normalize_positive_weights(
        {style: float(probabilities.get(style, 0.0)) for style in candidate_styles},
        default_keys=candidate_styles,
    )
    return str(weighted_choice(rng, compatible_probabilities, sort_keys=True)), dict(probabilities)


def _resolve_query(
    style: str,
    gen_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    *,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    probabilities = _query_probability_map(gen_defaults, params)
    valid_queries = _valid_queries_for_style(str(style))
    explicit = params.get("query_id")
    if explicit is not None:
        query_id = str(explicit)
        if query_id not in valid_queries:
            raise ValueError(f"query_id {query_id!r} is not compatible with board_style {style!r}")
        return query_id, dict(probabilities)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:query_id")
    compatible_probabilities = normalize_positive_weights(
        {query: float(probabilities.get(query, 0.0)) for query in valid_queries},
        default_keys=valid_queries,
    )
    return str(weighted_choice(rng, compatible_probabilities, sort_keys=True)), dict(probabilities)


def _select_from_support(
    *,
    support: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    sampling_index: int | None,
) -> int:
    values = tuple(int(value) for value in support)
    if not values:
        raise ValueError("empty support")
    if sampling_index is not None:
        return int(values[int(sampling_index) % len(values)])
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(values[int(index) % len(values)])


def _resolve_dimensions(
    *,
    style: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[int, int, Dict[str, float], Dict[str, float]]:
    spec = _STYLE_SPECS[str(style)]
    row_support = tuple(int(value) for value in spec["row_support"])
    col_support = tuple(int(value) for value in spec["col_support"])
    explicit_rows = params.get("visible_rows", params.get("row_count"))
    explicit_cols = params.get("visible_columns", params.get("column_count"))
    dimension_index = None
    if explicit_rows is None:
        rows = _select_from_support(
            support=row_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:{style}:rows",
            sampling_index=dimension_index,
        )
    else:
        rows = int(explicit_rows)
        if rows not in row_support:
            raise ValueError(f"visible_rows must be in {row_support} for {style!r}")
    if explicit_cols is None:
        col_index = None if dimension_index is None else int(dimension_index) // len(row_support)
        cols = _select_from_support(
            support=col_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:{style}:columns",
            sampling_index=col_index,
        )
    else:
        cols = int(explicit_cols)
        if cols not in col_support:
            raise ValueError(f"visible_columns must be in {col_support} for {style!r}")
    return (
        int(rows),
        int(cols),
        dict(uniform_probability_map(row_support, selected=int(rows) if explicit_rows is not None else None)),
        dict(uniform_probability_map(col_support, selected=int(cols) if explicit_cols is not None else None)),
    )


def _target_answer(query_id: str, rows: int, cols: int) -> int:
    if str(query_id) in (ROW_COUNT_QUERY, HORIZONTAL_LINE_COUNT_QUERY):
        return int(rows)
    if str(query_id) in (COLUMN_COUNT_QUERY, VERTICAL_LINE_COUNT_QUERY):
        return int(cols)
    if str(query_id) == CELL_COUNT_QUERY:
        return int(rows) * int(cols)
    raise ValueError(f"unsupported query_id: {query_id!r}")


def _canonical_answer(query_id: str, style: str) -> int:
    spec = _STYLE_SPECS[str(style)]
    return _target_answer(str(query_id), int(spec["canonical_rows"]), int(spec["canonical_cols"]))


def _element_type(query_id: str) -> str:
    if str(query_id) == ROW_COUNT_QUERY:
        return "board_row"
    if str(query_id) == COLUMN_COUNT_QUERY:
        return "board_column"
    if str(query_id) == CELL_COUNT_QUERY:
        return "board_cell"
    if str(query_id) == HORIZONTAL_LINE_COUNT_QUERY:
        return "horizontal_grid_line"
    if str(query_id) == VERTICAL_LINE_COUNT_QUERY:
        return "vertical_grid_line"
    raise ValueError(f"unsupported query_id: {query_id!r}")


def _build_counted_elements(
    *,
    query_id: str,
    rows: int,
    cols: int,
    board_bbox: Sequence[float],
    padding: float,
) -> List[_GridElementSpec]:
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    cell_w = (x1 - x0) / float(max(1, cols))
    cell_h = (y1 - y0) / float(max(1, rows))
    element_type = _element_type(str(query_id))
    elements: List[_GridElementSpec] = []
    if str(query_id) == ROW_COUNT_QUERY:
        for row in range(int(rows)):
            bbox = [x0 - padding, y0 + row * cell_h - padding, x1 + padding, y0 + (row + 1) * cell_h + padding]
            elements.append(_GridElementSpec(f"row_{row}", element_type, _round_bbox(bbox)))
    elif str(query_id) == COLUMN_COUNT_QUERY:
        for col in range(int(cols)):
            bbox = [x0 + col * cell_w - padding, y0 - padding, x0 + (col + 1) * cell_w + padding, y1 + padding]
            elements.append(_GridElementSpec(f"column_{col}", element_type, _round_bbox(bbox)))
    elif str(query_id) == CELL_COUNT_QUERY:
        for row in range(int(rows)):
            for col in range(int(cols)):
                bbox = [
                    x0 + col * cell_w - padding,
                    y0 + row * cell_h - padding,
                    x0 + (col + 1) * cell_w + padding,
                    y0 + (row + 1) * cell_h + padding,
                ]
                elements.append(_GridElementSpec(f"cell_{row}_{col}", element_type, _round_bbox(bbox)))
    elif str(query_id) == HORIZONTAL_LINE_COUNT_QUERY:
        line_gap = (y1 - y0) / float(max(1, rows - 1))
        for row in range(int(rows)):
            y = y0 + row * line_gap
            bbox = [x0 - padding, y - padding, x1 + padding, y + padding]
            elements.append(_GridElementSpec(f"horizontal_line_{row}", element_type, _round_bbox(bbox)))
    elif str(query_id) == VERTICAL_LINE_COUNT_QUERY:
        line_gap = (x1 - x0) / float(max(1, cols - 1))
        for col in range(int(cols)):
            x = x0 + col * line_gap
            bbox = [x - padding, y0 - padding, x + padding, y1 + padding]
            elements.append(_GridElementSpec(f"vertical_line_{col}", element_type, _round_bbox(bbox)))
    return elements


def _board_bbox_for_cells(width: int, height: int, rows: int, cols: int, margin: float) -> List[float]:
    max_w = float(width) - 2.0 * float(margin)
    max_h = float(height) - 2.0 * float(margin)
    cell = min(max_w / float(cols), max_h / float(rows))
    board_w = cell * float(cols)
    board_h = cell * float(rows)
    x0 = (float(width) - board_w) * 0.5
    y0 = (float(height) - board_h) * 0.5
    return [x0, y0, x0 + board_w, y0 + board_h]


def _board_bbox_for_lines(width: int, height: int, rows: int, cols: int, margin: float) -> List[float]:
    max_w = float(width) - 2.0 * float(margin)
    max_h = float(height) - 2.0 * float(margin)
    unit = min(max_w / float(max(1, cols - 1)), max_h / float(max(1, rows - 1)))
    board_w = unit * float(max(1, cols - 1))
    board_h = unit * float(max(1, rows - 1))
    x0 = (float(width) - board_w) * 0.5
    y0 = (float(height) - board_h) * 0.5
    return [x0, y0, x0 + board_w, y0 + board_h]


def _render_chess_checkers(
    draw: ImageDraw.ImageDraw,
    *,
    rows: int,
    cols: int,
    board_bbox: Sequence[float],
    scale: int,
    light_rgb: Tuple[int, int, int],
    dark_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    cell_w = (x1 - x0) / float(cols)
    cell_h = (y1 - y0) / float(rows)
    for row in range(int(rows)):
        for col in range(int(cols)):
            fill = light_rgb if (row + col) % 2 == 0 else dark_rgb
            bbox = [x0 + col * cell_w, y0 + row * cell_h, x0 + (col + 1) * cell_w, y0 + (row + 1) * cell_h]
            draw.rectangle(_scale_bbox(bbox, scale), fill=fill + (255,))
    draw.rectangle(_scale_bbox(board_bbox, scale), outline=outline_rgb + (245,), width=max(2, 3 * int(scale)))


def _render_sudoku(
    draw: ImageDraw.ImageDraw,
    *,
    rows: int,
    cols: int,
    board_bbox: Sequence[float],
    scale: int,
    fill_rgb: Tuple[int, int, int],
    line_rgb: Tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    draw.rectangle(_scale_bbox(board_bbox, scale), fill=fill_rgb + (255,))
    cell_w = (x1 - x0) / float(cols)
    cell_h = (y1 - y0) / float(rows)
    row_thick = max(1, int(round(float(rows) / 3.0)))
    col_thick = max(1, int(round(float(cols) / 3.0)))
    for row in range(int(rows) + 1):
        width = 3 if row in (0, int(rows)) or row % row_thick == 0 else 1
        y = y0 + row * cell_h
        draw.line(_scale_bbox([x0, y, x1, y], scale), fill=line_rgb + (245,), width=max(1, width * int(scale)))
    for col in range(int(cols) + 1):
        width = 3 if col in (0, int(cols)) or col % col_thick == 0 else 1
        x = x0 + col * cell_w
        draw.line(_scale_bbox([x, y0, x, y1], scale), fill=line_rgb + (245,), width=max(1, width * int(scale)))


def _render_xiangqi(
    draw: ImageDraw.ImageDraw,
    *,
    rows: int,
    cols: int,
    board_bbox: Sequence[float],
    scale: int,
    board_rgb: Tuple[int, int, int],
    line_rgb: Tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    pad = 34.0
    draw.rounded_rectangle(
        _scale_bbox([x0 - pad, y0 - pad, x1 + pad, y1 + pad], scale),
        radius=18 * int(scale),
        fill=board_rgb + (255,),
        outline=line_rgb + (225,),
        width=max(2, 2 * int(scale)),
    )
    dx = (x1 - x0) / float(max(1, cols - 1))
    dy = (y1 - y0) / float(max(1, rows - 1))
    river_after = max(2, int(rows) // 2 - 1)
    river_before = min(int(rows) - 2, river_after + 1)
    line_width = max(2, 2 * int(scale))
    for row in range(int(rows)):
        y = y0 + row * dy
        draw.line(_scale_bbox([x0, y, x1, y], scale), fill=line_rgb + (245,), width=line_width)
    for col in range(int(cols)):
        x = x0 + col * dx
        if col in (0, int(cols) - 1):
            draw.line(_scale_bbox([x, y0, x, y1], scale), fill=line_rgb + (245,), width=line_width)
        else:
            y_top_end = y0 + river_after * dy
            y_bottom_start = y0 + river_before * dy
            draw.line(_scale_bbox([x, y0, x, y_top_end], scale), fill=line_rgb + (245,), width=line_width)
            draw.line(_scale_bbox([x, y_bottom_start, x, y1], scale), fill=line_rgb + (245,), width=line_width)
    if int(cols) >= 5 and int(rows) >= 6:
        mid = int(cols) // 2
        left = max(0, mid - 1)
        right = min(int(cols) - 1, mid + 1)
        top_a, top_b = 0, min(2, int(rows) - 1)
        bot_a, bot_b = max(0, int(rows) - 3), int(rows) - 1
        palace_lines = (
            (left, top_a, right, top_b),
            (right, top_a, left, top_b),
            (left, bot_a, right, bot_b),
            (right, bot_a, left, bot_b),
        )
        for c0, r0, c1, r1 in palace_lines:
            draw.line(
                _scale_bbox([x0 + c0 * dx, y0 + r0 * dy, x0 + c1 * dx, y0 + r1 * dy], scale),
                fill=line_rgb + (245,),
                width=line_width,
            )


def _render_chess_checkers_fillers(
    draw: ImageDraw.ImageDraw,
    *,
    rows: int,
    cols: int,
    board_bbox: Sequence[float],
    scale: int,
) -> List[_DecorativeSpec]:
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    cell_w = (x1 - x0) / float(cols)
    cell_h = (y1 - y0) / float(rows)
    radius = 0.30 * min(cell_w, cell_h)
    candidates = (
        (0, 1, "dark", (32, 34, 40), (236, 238, 241)),
        (0, min(int(cols) - 1, 3), "dark", (32, 34, 40), (236, 238, 241)),
        (1, 0, "dark", (32, 34, 40), (236, 238, 241)),
        (1, min(int(cols) - 1, 4), "dark", (32, 34, 40), (236, 238, 241)),
        (int(rows) - 1, max(0, int(cols) - 2), "light", (246, 247, 245), (31, 35, 42)),
        (int(rows) - 1, max(0, int(cols) - 4), "light", (246, 247, 245), (31, 35, 42)),
        (int(rows) - 2, int(cols) - 1, "light", (246, 247, 245), (31, 35, 42)),
        (int(rows) - 2, max(0, int(cols) - 5), "light", (246, 247, 245), (31, 35, 42)),
    )
    used: set[Tuple[int, int]] = set()
    fillers: List[_DecorativeSpec] = []
    for row, col, color_role, fill_rgb, outline_rgb in candidates:
        if not (0 <= int(row) < int(rows) and 0 <= int(col) < int(cols)):
            continue
        key = (int(row), int(col))
        if key in used:
            continue
        used.add(key)
        cx = x0 + (float(col) + 0.5) * cell_w
        cy = y0 + (float(row) + 0.5) * cell_h
        bbox = _round_bbox([cx - radius, cy - radius, cx + radius, cy + radius])
        _draw_piece_disc(
            draw,
            bbox=bbox,
            scale=int(scale),
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
            width_px=2,
        )
        fillers.append(
            _DecorativeSpec(
                entity_id=f"decorative_piece_{len(fillers)}",
                entity_type="board_filler_checker_piece",
                bbox=list(bbox),
                metadata={"row": int(row), "column": int(col), "color_role": str(color_role)},
            )
        )
        if len(fillers) >= 6:
            break
    return fillers


def _render_sudoku_fillers(
    draw: ImageDraw.ImageDraw,
    *,
    rows: int,
    cols: int,
    board_bbox: Sequence[float],
    scale: int,
) -> List[_DecorativeSpec]:
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    cell_w = (x1 - x0) / float(cols)
    cell_h = (y1 - y0) / float(rows)
    raw_positions = (
        (0, 0),
        (0, max(0, int(cols) - 2)),
        (1, 2),
        (2, max(0, int(cols) - 1)),
        (int(rows) // 2, int(cols) // 2),
        (max(0, int(rows) - 3), 1),
        (max(0, int(rows) - 2), max(0, int(cols) - 3)),
        (int(rows) - 1, int(cols) - 1),
        (int(rows) // 2, max(0, int(cols) - 2)),
        (max(0, int(rows) - 4), int(cols) // 3),
    )
    used: set[Tuple[int, int]] = set()
    fillers: List[_DecorativeSpec] = []
    font_size = 0.44 * min(cell_w, cell_h)
    text_rgb = (31, 36, 44)
    stroke_rgb = (255, 255, 252)
    for row, col in raw_positions:
        if not (0 <= int(row) < int(rows) and 0 <= int(col) < int(cols)):
            continue
        key = (int(row), int(col))
        if key in used:
            continue
        used.add(key)
        value = 1 + ((int(row) * 3 + int(col) * 5 + len(fillers)) % 9)
        cx = x0 + (float(col) + 0.5) * cell_w
        cy = y0 + (float(row) + 0.5) * cell_h
        bbox = _round_bbox([x0 + col * cell_w, y0 + row * cell_h, x0 + (col + 1) * cell_w, y0 + (row + 1) * cell_h])
        _draw_centered_label(
            draw,
            text=str(value),
            center=(cx, cy),
            font_size_px=float(font_size),
            scale=int(scale),
            fill_rgb=text_rgb,
            stroke_rgb=stroke_rgb,
            stroke_width_px=1,
        )
        fillers.append(
            _DecorativeSpec(
                entity_id=f"decorative_digit_{len(fillers)}",
                entity_type="sudoku_given_digit",
                bbox=list(bbox),
                metadata={"row": int(row), "column": int(col), "digit": int(value)},
            )
        )
        if len(fillers) >= max(5, min(10, (int(rows) * int(cols)) // 9)):
            break
    return fillers


def _render_xiangqi_fillers(
    draw: ImageDraw.ImageDraw,
    *,
    rows: int,
    cols: int,
    board_bbox: Sequence[float],
    scale: int,
    board_rgb: Tuple[int, int, int],
) -> List[_DecorativeSpec]:
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    dx = (x1 - x0) / float(max(1, int(cols) - 1))
    dy = (y1 - y0) / float(max(1, int(rows) - 1))
    radius = 0.28 * min(dx, dy)
    mid = int(cols) // 2
    candidates = (
        (0, max(0, mid - 1), "R", "black", (36, 31, 26), (44, 32, 24)),
        (0, mid, "K", "black", (36, 31, 26), (44, 32, 24)),
        (0, min(int(cols) - 1, mid + 1), "R", "black", (36, 31, 26), (44, 32, 24)),
        (min(int(rows) - 1, 2), min(int(cols) - 1, 1), "C", "black", (36, 31, 26), (44, 32, 24)),
        (int(rows) - 1, max(0, mid - 1), "R", "red", (148, 33, 28), (132, 28, 24)),
        (int(rows) - 1, mid, "K", "red", (148, 33, 28), (132, 28, 24)),
        (int(rows) - 1, min(int(cols) - 1, mid + 1), "R", "red", (148, 33, 28), (132, 28, 24)),
        (max(0, int(rows) - 3), max(0, int(cols) - 2), "C", "red", (148, 33, 28), (132, 28, 24)),
    )
    used: set[Tuple[int, int]] = set()
    fillers: List[_DecorativeSpec] = []
    for row, col, label, side, text_rgb, outline_rgb in candidates:
        if not (0 <= int(row) < int(rows) and 0 <= int(col) < int(cols)):
            continue
        key = (int(row), int(col))
        if key in used:
            continue
        used.add(key)
        cx = x0 + float(col) * dx
        cy = y0 + float(row) * dy
        bbox = _round_bbox([cx - radius, cy - radius, cx + radius, cy + radius])
        _draw_piece_disc(
            draw,
            bbox=bbox,
            scale=int(scale),
            fill_rgb=(252, 231, 185),
            outline_rgb=outline_rgb,
            width_px=2,
        )
        _draw_centered_label(
            draw,
            text=str(label),
            center=(cx, cy),
            font_size_px=0.70 * radius,
            scale=int(scale),
            fill_rgb=text_rgb,
            stroke_rgb=board_rgb,
            stroke_width_px=1,
        )
        fillers.append(
            _DecorativeSpec(
                entity_id=f"decorative_xiangqi_piece_{len(fillers)}",
                entity_type="xiangqi_reference_piece",
                bbox=list(bbox),
                metadata={"row": int(row), "column": int(col), "label": str(label), "side": str(side)},
            )
        )
        if len(fillers) >= 8:
            break
    return fillers


def _render_scene(
    *,
    query_id: str,
    style: str,
    rows: int,
    cols: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_RenderedBoard, Dict[str, Any]]:
    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 920)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 720)))
    scale = int(params.get("scene_supersample_scale", group_default(render_defaults, "scene_supersample_scale", 2)))
    margin = float(params.get("board_margin_px", group_default(render_defaults, "board_margin_px", 92)))
    unit_size_scale, unit_size_jitter = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.unit_size",
    )
    evidence_padding = float(
        scale_puzzle_px(
            params.get("evidence_padding_px", group_default(render_defaults, "evidence_padding_px", 3)),
            unit_size_scale,
            min_px=1,
        )
    )
    background_rgb_fallback = _rgb(group_default(render_defaults, "background_rgb", [246, 248, 250]), [246, 248, 250])
    outline_rgb = _rgb(group_default(render_defaults, "outline_rgb", [33, 37, 45]), [33, 37, 45])
    scene_style, scene_style_meta = resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.counterfactual_board_background",
    )
    image, background_meta = make_puzzle_scene_background(
        canvas_width=int(width) * int(scale),
        canvas_height=int(height) * int(scale),
        style=scene_style,
    )
    background_rgb = _background_rgb_from_meta(background_meta, background_rgb_fallback)
    draw = ImageDraw.Draw(image, "RGBA")
    if str(style) == XIANGQI_STYLE:
        board_bbox = _board_bbox_for_lines(width, height, rows, cols, margin)
    else:
        board_bbox = _board_bbox_for_cells(width, height, rows, cols, margin)
    board_bbox = _scale_bbox_about_center(board_bbox, float(unit_size_scale))
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    if str(style) == CHESS_STYLE:
        _render_chess_checkers(
            draw,
            rows=int(rows),
            cols=int(cols),
            board_bbox=board_bbox,
            scale=int(scale),
            light_rgb=_rgb(group_default(render_defaults, "chess_light_rgb", [238, 229, 206]), [238, 229, 206]),
            dark_rgb=_rgb(group_default(render_defaults, "chess_dark_rgb", [92, 124, 80]), [92, 124, 80]),
            outline_rgb=outline_rgb,
        )
        decorative_items = _render_chess_checkers_fillers(
            draw,
            rows=int(rows),
            cols=int(cols),
            board_bbox=board_bbox,
            scale=int(scale),
        )
    elif str(style) == SUDOKU_STYLE:
        _render_sudoku(
            draw,
            rows=int(rows),
            cols=int(cols),
            board_bbox=board_bbox,
            scale=int(scale),
            fill_rgb=_rgb(group_default(render_defaults, "sudoku_fill_rgb", [255, 255, 252]), [255, 255, 252]),
            line_rgb=_rgb(group_default(render_defaults, "sudoku_line_rgb", [38, 42, 50]), [38, 42, 50]),
        )
        decorative_items = _render_sudoku_fillers(
            draw,
            rows=int(rows),
            cols=int(cols),
            board_bbox=board_bbox,
            scale=int(scale),
        )
    elif str(style) == XIANGQI_STYLE:
        xiangqi_board_rgb = _rgb(group_default(render_defaults, "xiangqi_board_rgb", [241, 205, 142]), [241, 205, 142])
        _render_xiangqi(
            draw,
            rows=int(rows),
            cols=int(cols),
            board_bbox=board_bbox,
            scale=int(scale),
            board_rgb=xiangqi_board_rgb,
            line_rgb=_rgb(group_default(render_defaults, "xiangqi_line_rgb", [72, 45, 24]), [72, 45, 24]),
        )
        decorative_items = _render_xiangqi_fillers(
            draw,
            rows=int(rows),
            cols=int(cols),
            board_bbox=board_bbox,
            scale=int(scale),
            board_rgb=xiangqi_board_rgb,
        )
    else:
        raise ValueError(f"unsupported board style: {style!r}")
    counted_elements = _build_counted_elements(
        query_id=str(query_id),
        rows=int(rows),
        cols=int(cols),
        board_bbox=board_bbox,
        padding=float(evidence_padding),
    )
    board_bbox_round = _round_bbox(board_bbox)
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "board_0",
            "entity_type": "counterfactual_board",
            "board_style": str(style),
            "visible_rows": int(rows),
            "visible_columns": int(cols),
            "bbox": list(board_bbox_round),
        }
    ]
    for index, element in enumerate(counted_elements):
        entities.append(
            {
                "entity_id": str(element.element_id),
                "entity_type": str(element.element_type),
                "reading_order_index": int(index),
                "bbox": list(element.bbox),
            }
        )
    for item in decorative_items:
        entities.append(
            {
                "entity_id": str(item.entity_id),
                "entity_type": str(item.entity_type),
                "bbox": list(item.bbox),
                **dict(item.metadata),
            }
        )
    small = image.resize((width, height), Image.Resampling.LANCZOS)
    return (
        _RenderedBoard(
            image=small,
            entities=entities,
            counted_elements=list(counted_elements),
            board_bbox=list(board_bbox_round),
            render_map={
                "board_bbox_px": list(board_bbox_round),
                "counted_element_bboxes_px": {str(element.element_id): list(element.bbox) for element in counted_elements},
                "counted_element_ids": [str(element.element_id) for element in counted_elements],
                "decorative_item_bboxes_px": {str(item.entity_id): list(item.bbox) for item in decorative_items},
                "decorative_item_ids": [str(item.entity_id) for item in decorative_items],
                "unit_size_jitter": dict(unit_size_jitter),
            },
        ),
        {
                "canvas_width": int(width),
                "canvas_height": int(height),
                "scene_supersample_scale": int(scale),
                "background_rgb": list(background_rgb),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "unit_size_jitter": dict(unit_size_jitter),
        },
    )


def _build_prompt(
    *,
    prompt_defaults: Mapping[str, Any],
    query_id: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    prompt_values = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "evidence_hint",
            "answer_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {TASK_ID}",
    )
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="counterfactual",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_values["object_description"]),
            "json_output_contract": str(prompt_values["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
            "evidence_hint": str(prompt_values["evidence_hint"]),
            "answer_hint": str(prompt_values["answer_hint"]),
            "json_example": str(prompt_values["json_example"]),
            "json_example_answer_only": str(prompt_values["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_values["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }


@register_task
class PuzzlesCounterfactualBoardGridCountTask:
    """Count rows, columns, cells, or board lines when a familiar board size changes."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "counterfactual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        group_defaults = get_task_group_defaults("puzzles", "counterfactual")
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(group_defaults, task_id=TASK_ID)
        style, style_probabilities = _resolve_style(gen_defaults, params, instance_seed=int(instance_seed))
        query_id, query_probabilities = _resolve_query(str(style), gen_defaults, params, instance_seed=int(instance_seed))
        rows, cols, row_probabilities, col_probabilities = _resolve_dimensions(
            style=str(style),
            params=params,
            instance_seed=int(instance_seed),
        )
        answer = _target_answer(str(query_id), int(rows), int(cols))
        canonical_answer = _canonical_answer(str(query_id), str(style))
        rendered, render_meta = _render_scene(
            query_id=str(query_id),
            style=str(style),
            rows=int(rows),
            cols=int(cols),
            params=params,
            render_defaults=render_defaults,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        evidence_bboxes = [list(rendered.board_bbox)]
        answer_gt = TypedValue(type="integer", value=int(answer))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        counterfactual_delta = int(answer) - int(canonical_answer)
        query_params = {
            "query_id": str(query_id),
            "query_id_probabilities": {str(key): float(value) for key, value in query_probabilities.items()},
            "scene_id": SCENE_ID,
            "board_style": str(style),
            "board_style_probabilities": {str(key): float(value) for key, value in style_probabilities.items()},
            "visible_rows": int(rows),
            "visible_columns": int(cols),
            "row_count_probabilities": {str(key): float(value) for key, value in row_probabilities.items()},
            "column_count_probabilities": {str(key): float(value) for key, value in col_probabilities.items()},
            "canonical_rows": int(_STYLE_SPECS[str(style)]["canonical_rows"]),
            "canonical_columns": int(_STYLE_SPECS[str(style)]["canonical_cols"]),
            "answer_value": int(answer),
            "canonical_bias_answer": int(canonical_answer),
            "counterfactual_delta": int(counterfactual_delta),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_id": SCENE_ID,
                    "board_style": str(style),
                    "visible_rows": int(rows),
                    "visible_columns": int(cols),
                    "target_answer": int(answer),
                    "canonical_bias_answer": int(canonical_answer),
                    "counterfactual_delta": int(counterfactual_delta),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                **dict(render_meta),
                "scene_id": SCENE_ID,
                "coord_space": "pixel",
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered.board_bbox),
            },
            "render_map": {
                "image_id": "img0",
                **with_puzzle_unit_size_jitter(rendered.render_map, rendered.render_map.get("unit_size_jitter", {})),
                "evidence_source": "board_bbox_px",
            },
            "execution_trace": {
                **dict(query_params),
                "question_format": str(query_id),
                "grid_kind": str(_STYLE_SPECS[str(style)]["grid_kind"]),
                "counted_element_type": str(_element_type(str(query_id))),
                "counted_element_ids": [str(element.element_id) for element in rendered.counted_elements],
                "counted_element_bboxes_px": [list(element.bbox) for element in rendered.counted_elements],
                "decorative_item_ids": list(rendered.render_map.get("decorative_item_ids", [])),
                "decorative_item_bboxes_px": dict(rendered.render_map.get("decorative_item_bboxes_px", {})),
                "supporting_item_ids": ["board_0"],
                "is_counterfactual": bool(counterfactual_delta != 0),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
                "counted_element_ids": [str(element.element_id) for element in rendered.counted_elements],
                "visible_element_count": int(answer),
                "canonical_bias_answer": int(canonical_answer),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "value": list(evidence_bboxes),
            },
        }
        answer_support = _answer_support()
        visual_scan = normalize_int_with_bounds(int(answer), [min(answer_support), max(answer_support)])
        conflict = clamp_unit_interval(abs(float(counterfactual_delta)) / max(1.0, float(canonical_answer) * 0.25))
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(0.22 + 0.28 * conflict),
                "scene_variant_load": float({CHESS_STYLE: 0.20, SUDOKU_STYLE: 0.24, XIANGQI_STYLE: 0.30}[str(style)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


def _answer_support() -> Tuple[int, ...]:
    answers: set[int] = set()
    for style, spec in _STYLE_SPECS.items():
        rows = tuple(int(value) for value in spec["row_support"])
        cols = tuple(int(value) for value in spec["col_support"])
        for query_id in _valid_queries_for_style(str(style)):
            if query_id in (ROW_COUNT_QUERY, HORIZONTAL_LINE_COUNT_QUERY):
                answers.update(rows)
            elif query_id in (COLUMN_COUNT_QUERY, VERTICAL_LINE_COUNT_QUERY):
                answers.update(cols)
            elif query_id == CELL_COUNT_QUERY:
                answers.update(int(row) * int(col) for row in rows for col in cols)
    return tuple(sorted(answers))


__all__ = [
    "CELL_COUNT_QUERY",
    "CHESS_STYLE",
    "COLUMN_COUNT_QUERY",
    "HORIZONTAL_LINE_COUNT_QUERY",
    "PuzzlesCounterfactualBoardGridCountTask",
    "ROW_COUNT_QUERY",
    "SCENE_ID",
    "SUDOKU_STYLE",
    "SUPPORTED_BOARD_STYLES",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "VERTICAL_LINE_COUNT_QUERY",
    "XIANGQI_STYLE",
]
