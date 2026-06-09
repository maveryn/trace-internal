"""Coordinate-code letter grid puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from string import ascii_uppercase
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import required_group_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font
from ..shared.common import (
    get_int_range as _get_range,
    load_puzzle_task_defaults,
    projected_puzzle_keyed_bbox_annotation,
    resolve_puzzle_axis_variant,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds
from ..shared.drawing import draw_centered_text, draw_rounded_rect
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults
from .search_grid import _WORD_POOL, _scan_word


SCENE_ID = "code_grid"
DECODED_WORD_TASK_ID = "task_puzzles__code_grid__decoded_word_label"
DECODE_COORDINATE_SEQUENCE_QUERY_ID = "decode_coordinate_sequence"
DECODE_SPACED_COORDINATE_SEQUENCE_QUERY_ID = "decode_spaced_coordinate_sequence"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    DECODE_COORDINATE_SEQUENCE_QUERY_ID,
    DECODE_SPACED_COORDINATE_SEQUENCE_QUERY_ID,
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "code_grid_classic",
    "code_grid_notebook",
    "code_grid_card",
)
_SCENE_LOAD_BY_VARIANT = {
    "code_grid_classic": 0.16,
    "code_grid_notebook": 0.22,
    "code_grid_card": 0.20,
}
_CODE_GRID_EXTRA_WORDS: Tuple[str, ...] = (
    "BASIC",
    "BRIDGE",
    "CABLE",
    "CLOUD",
    "CODE",
    "FRAME",
    "LASER",
    "LEMON",
    "MARKET",
    "MATH",
    "PIXEL",
    "PLANE",
    "PUZZLE",
    "RIVER",
    "ROBOT",
    "SHAPE",
    "TRAIL",
    "VECTOR",
)
_CODE_GRID_WORD_POOL: Tuple[str, ...] = tuple(sorted(set(_WORD_POOL + _CODE_GRID_EXTRA_WORDS)))

Cell = Tuple[int, int]
BBox = List[float]

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "word")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="word", apply_prob=0.0)


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    cell_size_px: int
    header_size_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    grid_line_width_px: int
    letter_font_size_px: int
    index_font_size_px: int
    title_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    grid_fill_rgb: Tuple[int, int, int]
    header_fill_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    task_id: str
    query_id: str
    rows: int
    cols: int
    grid_size_range: Tuple[int, int]
    grid: Tuple[Tuple[str, ...], ...]
    target_word: str
    answer_value: str
    coordinate_tokens: Tuple[str, ...]
    coordinate_sequence: str
    target_cells: Tuple[Cell, ...]
    supporting_role_item_ids: Dict[str, str]
    scene_variant: str
    target_answer_support: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    scene_bbox_px: BBox
    item_bbox_map: Dict[str, BBox]
    cell_bbox_map: Dict[str, BBox]
    layout_jitter: Dict[str, Any]


def _cell_key(cell: Cell) -> str:
    return f"cell_{int(cell[0])}_{int(cell[1])}"


def _coordinate_token(cell: Cell) -> str:
    row, col = int(cell[0]), int(cell[1])
    return f"{ascii_uppercase[row]}{col + 1}"


def _load_defaults(task_id: str = DECODED_WORD_TASK_ID) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None and effective_params.get("query_variant") is not None:
        effective_params["query_id"] = str(effective_params["query_variant"])
    return resolve_puzzle_axis_variant(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_IDS,
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_grid_size(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, int, Tuple[int, int]]:
    size_min, size_max = _get_range(
        params,
        gen_defaults,
        min_key="grid_size_min",
        max_key="grid_size_max",
        fallback_min=4,
        fallback_max=5,
    )
    explicit_size = params.get("grid_size")
    if explicit_size is not None:
        size = int(explicit_size)
    else:
        selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{DECODED_WORD_TASK_ID}.grid_size"))
        size = int(size_min + (selection % (size_max - size_min + 1)))
    if not int(size_min) <= int(size) <= int(size_max):
        raise ValueError("grid_size outside configured range")
    return int(size), int(size), (int(size_min), int(size_max))


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> _RenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.code_grid.unit_size",
    )
    return _RenderParams(
        canvas_width=int(render_defaults.get("canvas_width", 900)),
        canvas_height=int(render_defaults.get("canvas_height", 700)),
        cell_size_px=scale_puzzle_px(render_defaults.get("cell_size_px", 64), unit_scale, min_px=42),
        header_size_px=scale_puzzle_px(render_defaults.get("header_size_px", 48), unit_scale, min_px=32),
        panel_padding_px=scale_puzzle_px(render_defaults.get("panel_padding_px", 28), unit_scale, min_px=18),
        panel_corner_radius_px=scale_puzzle_px(render_defaults.get("panel_corner_radius_px", 18), unit_scale, min_px=8),
        grid_line_width_px=scale_puzzle_px(render_defaults.get("grid_line_width_px", 2), unit_scale, min_px=1),
        letter_font_size_px=scale_puzzle_px(render_defaults.get("letter_font_size_px", 28), unit_scale, min_px=18),
        index_font_size_px=scale_puzzle_px(render_defaults.get("index_font_size_px", 19), unit_scale, min_px=13),
        title_font_size_px=scale_puzzle_px(render_defaults.get("title_font_size_px", 24), unit_scale, min_px=16),
        panel_fill_rgb=_rgb(render_defaults.get("panel_fill_rgb"), (250, 251, 253)),
        grid_fill_rgb=_rgb(render_defaults.get("grid_fill_rgb"), (255, 255, 255)),
        header_fill_rgb=_rgb(render_defaults.get("header_fill_rgb"), (239, 243, 248)),
        grid_line_rgb=_rgb(render_defaults.get("grid_line_rgb"), (93, 102, 116)),
        text_rgb=_rgb(render_defaults.get("text_rgb"), (26, 31, 39)),
        text_stroke_rgb=_rgb(render_defaults.get("text_stroke_rgb"), (255, 255, 255)),
        unit_size_jitter=dict(unit_meta),
    )


def _resize_canvas_to_content(
    render_params: _RenderParams,
    *,
    rows: int,
    cols: int,
    instance_seed: int,
) -> _RenderParams:
    cell = int(render_params.cell_size_px)
    header = int(render_params.header_size_px)
    padding = int(render_params.panel_padding_px)
    title_band_px = 48
    margin = 34
    grid_w = int(header + cols * cell)
    grid_h = int(header + rows * cell)
    panel_w = int(grid_w + 2 * padding)
    panel_h = int(grid_h + 2 * padding + title_band_px)
    rng = spawn_rng(int(instance_seed), f"{DECODED_WORD_TASK_ID}.canvas")
    slack_x = int(rng.randrange(28, 91))
    slack_y = int(rng.randrange(24, 81))
    return replace(
        render_params,
        canvas_width=min(int(render_params.canvas_width), max(420, int(panel_w + 2 * margin + slack_x))),
        canvas_height=min(int(render_params.canvas_height), max(380, int(panel_h + 2 * margin + slack_y))),
    )


def _choose_word(rng, *, min_len: int, max_len: int) -> str:
    pool = [word for word in _CODE_GRID_WORD_POOL if int(min_len) <= len(str(word)) <= int(max_len)]
    if not pool:
        raise RuntimeError("code-grid word pool is empty for configured length range")
    return str(pool[int(rng.randrange(len(pool)))])


def _is_simple_line(cells: Sequence[Cell]) -> bool:
    if len(cells) < 3:
        return False
    deltas = [
        (int(cells[index + 1][0]) - int(cells[index][0]), int(cells[index + 1][1]) - int(cells[index][1]))
        for index in range(len(cells) - 1)
    ]
    first = deltas[0]
    if first == (0, 0):
        return False
    return all(delta == first for delta in deltas) and all(abs(value) <= 1 for value in first)


def _sample_target_cells(*, rows: int, cols: int, length: int, rng) -> Tuple[Cell, ...]:
    all_cells = [(row, col) for row in range(int(rows)) for col in range(int(cols))]
    for _attempt in range(200):
        rng.shuffle(all_cells)
        cells = tuple((int(row), int(col)) for row, col in all_cells[: int(length)])
        if not _is_simple_line(cells):
            return cells
    return tuple((int(row), int(col)) for row, col in all_cells[: int(length)])


def _fill_grid(
    *,
    rows: int,
    cols: int,
    word: str,
    target_cells: Sequence[Cell],
    rng,
) -> Tuple[Tuple[str, ...], ...]:
    grid = [["" for _ in range(int(cols))] for _ in range(int(rows))]
    for char, (row, col) in zip(str(word), target_cells):
        grid[int(row)][int(col)] = str(char)
    for row in range(int(rows)):
        for col in range(int(cols)):
            if not grid[row][col]:
                grid[row][col] = str(ascii_uppercase[int(rng.randrange(len(ascii_uppercase)))])
    return tuple(tuple(str(value) for value in row) for row in grid)


def _build_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    query_id: str,
    scene_variant: str,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{DECODED_WORD_TASK_ID}.dataset")
    rows, cols, size_range = _resolve_grid_size(params, gen_defaults, instance_seed=int(instance_seed))
    word_min, word_max = _get_range(
        params,
        gen_defaults,
        min_key="target_word_length_min",
        max_key="target_word_length_max",
        fallback_min=3,
        fallback_max=6,
    )
    for _attempt in range(400):
        target_word = _choose_word(rng, min_len=int(word_min), max_len=int(word_max))
        target_cells = _sample_target_cells(rows=int(rows), cols=int(cols), length=len(target_word), rng=rng)
        grid = _fill_grid(rows=int(rows), cols=int(cols), word=str(target_word), target_cells=target_cells, rng=rng)
        if _scan_word(grid, str(target_word)):
            continue
        coordinate_tokens = tuple(_coordinate_token(cell) for cell in target_cells)
        coordinate_sequence = "".join(coordinate_tokens)
        if str(query_id) == DECODE_SPACED_COORDINATE_SEQUENCE_QUERY_ID:
            coordinate_sequence = " ".join(coordinate_tokens)
        supporting_role_item_ids = {
            f"cell_{index}": _cell_key(cell)
            for index, cell in enumerate(target_cells, start=1)
        }
        return _Dataset(
            task_id=DECODED_WORD_TASK_ID,
            query_id=str(query_id),
            rows=int(rows),
            cols=int(cols),
            grid_size_range=tuple(size_range),
            grid=grid,
            target_word=str(target_word),
            answer_value=str(target_word),
            coordinate_tokens=tuple(coordinate_tokens),
            coordinate_sequence=str(coordinate_sequence),
            target_cells=tuple(target_cells),
            supporting_role_item_ids=dict(supporting_role_item_ids),
            scene_variant=str(scene_variant),
            target_answer_support=tuple(_CODE_GRID_WORD_POOL),
        )
    raise RuntimeError("failed to build code-grid decoded-word dataset")


def _render_scene(
    image: Image.Image,
    *,
    dataset: _Dataset,
    render_params: _RenderParams,
    instance_seed: int,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    rows = int(dataset.rows)
    cols = int(dataset.cols)
    cell = int(render_params.cell_size_px)
    header = int(render_params.header_size_px)
    padding = int(render_params.panel_padding_px)
    title_band_px = 48
    grid_w = int(header + cols * cell)
    grid_h = int(header + rows * cell)
    panel_w = int(grid_w + 2 * padding)
    panel_h = int(grid_h + 2 * padding + title_band_px)
    canvas_margin = 34
    rng = spawn_rng(int(instance_seed), f"{DECODED_WORD_TASK_ID}.layout")
    max_panel_x0 = max(canvas_margin, int(render_params.canvas_width) - canvas_margin - panel_w)
    max_panel_y0 = max(canvas_margin, int(render_params.canvas_height) - canvas_margin - panel_h)
    panel_x0 = int(canvas_margin + rng.randrange(max(1, max_panel_x0 - canvas_margin + 1)))
    panel_y0 = int(canvas_margin + rng.randrange(max(1, max_panel_y0 - canvas_margin + 1)))
    panel_x1 = int(panel_x0 + panel_w)
    panel_y1 = int(panel_y0 + panel_h)
    grid_x0 = int(panel_x0 + padding)
    grid_y0 = int(panel_y0 + padding + title_band_px)
    layout_jitter = {
        "enabled": True,
        "panel_x0_px": int(panel_x0),
        "panel_y0_px": int(panel_y0),
        "grid_x0_px": int(grid_x0),
        "grid_y0_px": int(grid_y0),
        "available_x0_min_px": int(canvas_margin),
        "available_x0_max_px": int(max_panel_x0),
        "available_y0_min_px": int(canvas_margin),
        "available_y0_max_px": int(max_panel_y0),
    }

    draw_rounded_rect(
        draw,
        (panel_x0, panel_y0, panel_x1, panel_y1),
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.grid_line_rgb,
        width=max(1, int(render_params.grid_line_width_px)),
    )
    if dataset.scene_variant == "code_grid_notebook":
        for y in range(panel_y0 + 16, panel_y1 - 8, max(14, cell // 2)):
            draw.line((panel_x0 + 8, y, panel_x1 - 8, y), fill=render_params.grid_line_rgb, width=1)

    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    letter_font = load_font(int(render_params.letter_font_size_px), bold=True)
    index_font = load_font(int(render_params.index_font_size_px), bold=True)
    draw_text_traced(
        draw,
        (panel_x0 + 18, panel_y0 + 14),
        "Code Grid",
        fill=render_params.text_rgb,
        font=title_font,
        role="readout",
        required=False,
    )

    item_bbox_map: Dict[str, BBox] = {}
    cell_bbox_map: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "code_grid_panel",
            "entity_type": "puzzle_code_grid_panel",
            "bbox_px": _round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
            "scene_variant": str(dataset.scene_variant),
        }
    ]

    for row in range(rows + 1):
        for col in range(cols + 1):
            if row == 0 and col == 0:
                bbox = (grid_x0, grid_y0, grid_x0 + header, grid_y0 + header)
                fill = render_params.header_fill_rgb
            elif row == 0:
                bbox = (
                    grid_x0 + header + ((col - 1) * cell),
                    grid_y0,
                    grid_x0 + header + (col * cell),
                    grid_y0 + header,
                )
                fill = render_params.header_fill_rgb
            elif col == 0:
                bbox = (
                    grid_x0,
                    grid_y0 + header + ((row - 1) * cell),
                    grid_x0 + header,
                    grid_y0 + header + (row * cell),
                )
                fill = render_params.header_fill_rgb
            else:
                bbox = (
                    grid_x0 + header + ((col - 1) * cell),
                    grid_y0 + header + ((row - 1) * cell),
                    grid_x0 + header + (col * cell),
                    grid_y0 + header + (row * cell),
                )
                fill = render_params.grid_fill_rgb
            draw.rectangle(bbox, fill=fill, outline=render_params.grid_line_rgb, width=max(1, int(render_params.grid_line_width_px)))
            if row == 0 and col > 0:
                draw_centered_text(
                    draw,
                    text=str(col),
                    center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
                    font=index_font,
                    fill=render_params.text_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
            elif col == 0 and row > 0:
                draw_centered_text(
                    draw,
                    text=str(ascii_uppercase[row - 1]),
                    center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
                    font=index_font,
                    fill=render_params.text_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
            elif row > 0 and col > 0:
                letter = str(dataset.grid[row - 1][col - 1])
                cell_id = _cell_key((row - 1, col - 1))
                cell_bbox_map[cell_id] = _round_bbox(bbox)
                item_bbox_map[cell_id] = _round_bbox(bbox)
                draw_centered_text(
                    draw,
                    text=letter,
                    center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
                    font=letter_font,
                    fill=render_params.text_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
                entities.append(
                    {
                        "entity_id": cell_id,
                        "entity_type": "puzzle_code_grid_cell",
                        "bbox_px": _round_bbox(bbox),
                        "row": int(row - 1),
                        "col": int(col - 1),
                        "row_label": str(ascii_uppercase[row - 1]),
                        "col_label": str(col),
                        "coordinate": _coordinate_token((row - 1, col - 1)),
                        "letter": letter,
                    }
                )

    return _RenderedScene(
        image=image,
        entities=tuple(entities),
        scene_bbox_px=_round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
        item_bbox_map=item_bbox_map,
        cell_bbox_map=cell_bbox_map,
        layout_jitter=dict(layout_jitter),
    )


def _build_prompt(
    *,
    dataset: _Dataset,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    query_id = str(dataset.query_id)
    scene_variant = str(dataset.scene_variant)
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        f"answer_hint_{query_id}",
        f"annotation_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {DECODED_WORD_TASK_ID}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "coordinate_sequence": str(dataset.coordinate_sequence),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="word",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


@register_task
class PuzzlesCodeGridDecodedWordLabelTask:
    """Decode an ordered row/column coordinate sequence into a word."""

    domain = "puzzles"
    task_group = "word"
    task_id = DECODED_WORD_TASK_ID
    query_id = DECODE_COORDINATE_SEQUENCE_QUERY_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        query_id, query_id_probabilities = _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )

        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    params=params,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    gen_defaults=gen_defaults,
                    query_id=str(query_id),
                    scene_variant=str(scene_variant),
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate code-grid puzzle instance") from last_error

        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _resize_canvas_to_content(
            render_params,
            rows=int(dataset.rows),
            cols=int(dataset.cols),
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.code_grid_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            grid_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            header_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            grid_line_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_scene(
            background,
            dataset=dataset,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            dataset=dataset,
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
        )
        annotation_projection = projected_puzzle_keyed_bbox_annotation(
            rendered_scene.item_bbox_map,
            dataset.supporting_role_item_ids,
        )
        annotation_bboxes = {
            str(key): [round(float(value), 3) for value in bbox]
            for key, bbox in annotation_projection["keyed_bbox_map"].items()
        }
        answer_gt = TypedValue(type="string", value=str(dataset.answer_value))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bboxes))

        target_cell_records = [
            {
                "index": int(index),
                "row": int(cell[0]),
                "col": int(cell[1]),
                "coordinate": str(token),
                "letter": str(dataset.grid[int(cell[0])][int(cell[1])]),
            }
            for index, (cell, token) in enumerate(zip(dataset.target_cells, dataset.coordinate_tokens), start=1)
        ]
        query_params = {
            "query_id": str(dataset.query_id),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "grid_size_range": list(dataset.grid_size_range),
            "coordinate_sequence": str(dataset.coordinate_sequence),
            "coordinate_tokens": list(dataset.coordinate_tokens),
            "target_answer_support": list(dataset.target_answer_support),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "answer_value": str(dataset.answer_value),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "scene_style": dict(scene_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
                "layout_jitter": dict(rendered_scene.layout_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter(
                {
                    "image_id": "img0",
                    "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                    "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                    "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                    "keyed_item_bboxes_px": dict(annotation_bboxes),
                    "annotation_source": "keyed_item_bboxes_px",
                    "layout_jitter": dict(rendered_scene.layout_jitter),
                },
                render_params.unit_size_jitter,
            ),
            "execution_trace": {
                **dict(query_params),
                "grid": [list(row) for row in dataset.grid],
                "target_word": str(dataset.target_word),
                "target_cells": target_cell_records,
                "answer_value": str(dataset.answer_value),
                "supporting_role_item_ids": dict(dataset.supporting_role_item_ids),
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": {"type": "keyed_bbox_map", "value": dict(annotation_bboxes)},
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_bboxes),
                "pixel_keyed_bbox_map": dict(annotation_bboxes),
                "value": dict(annotation_bboxes),
            },
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        visual_scan = normalize_int_with_bounds(
            int(dataset.rows * dataset.cols),
            [int(dataset.grid_size_range[0]) ** 2, int(dataset.grid_size_range[1]) ** 2],
        )
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": 0.50,
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        trace_payload["complexity"] = complexity.to_dict()
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


__all__ = [
    "DECODE_COORDINATE_SEQUENCE_QUERY_ID",
    "DECODE_SPACED_COORDINATE_SEQUENCE_QUERY_ID",
    "DECODED_WORD_TASK_ID",
    "PuzzlesCodeGridDecodedWordLabelTask",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
]
