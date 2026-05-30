"""Cellular automaton puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.color_distance import color_distance
from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import contrast_ratio
from ...shared.text_rendering import load_font, temporary_default_font_family
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_puzzle_task_defaults,
    projected_puzzle_bbox_evidence,
    projected_puzzle_keyed_bbox_evidence,
    resolve_puzzle_axis_variant,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds
from ..shared.scene_style import (
    DEFAULT_PUZZLE_SCENE_STYLE,
    PUZZLE_SCENE_TREATMENTS,
    PuzzleSceneStyle,
    draw_puzzle_chrome_by_mode,
    draw_puzzle_grid_cell,
    draw_puzzle_option_card,
    make_puzzle_scene_background,
    resolve_panel_chrome_mode,
    resolve_puzzle_scene_style,
)
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


AGENT_FINAL_TASK_ID = "task_puzzles__agent_automaton__agent_final_pose_label"
AGENT_FLIP_TASK_ID = "task_puzzles__agent_automaton__agent_cell_flip_count"
LIFE_GRID_TASK_ID = "task_puzzles__life_automaton__life_future_grid_label"
LIFE_POP_TASK_ID = "task_puzzles__life_automaton__life_population_count"
TURING_SYMBOL_COUNT_TASK_ID = "task_puzzles__turing_tape__turing_written_symbol_count"

AGENT_SCENE_ID = "agent_automaton"
LIFE_SCENE_ID = "life_automaton"
TURING_SCENE_ID = "turing_tape"

AGENT_FINAL_QUERY_IDS: Tuple[str, ...] = ("binary_rule_final_pose", "three_state_rule_final_pose")
AGENT_FLIP_QUERY_IDS: Tuple[str, ...] = ("marked_region_flip_count",)
LIFE_GRID_QUERY_IDS: Tuple[str, ...] = ("one_step_future_grid", "two_step_future_grid")
LIFE_POP_QUERY_IDS: Tuple[str, ...] = ("marked_line_live_count",)
TURING_QUERY_IDS: Tuple[str, ...] = ("written_symbol_count",)

_SCENE_VARIANTS: Tuple[str, ...] = ("clean_grid", "lab_panel", "notebook_grid")
_DIRECTIONS: Tuple[str, ...] = ("up", "right", "down", "left")
_DIR_VEC: Tuple[Tuple[int, int], ...] = ((-1, 0), (0, 1), (1, 0), (0, -1))
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_TURING_SYMBOLS: Tuple[str, ...] = ("0", "1", "2")
_TURING_MOVES: Tuple[str, str] = ("L", "R")


_AGENT_STATE_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (246, 248, 252),
    (84, 134, 207),
    (82, 169, 116),
)
_LIFE_DEAD_RGB = (247, 248, 250)
_LIFE_ALIVE_RGB = (35, 42, 54)
_GRID_RGB = (87, 96, 111)
_PANEL_RGB = (251, 252, 254)
_PANEL_BORDER_RGB = (87, 96, 111)
_TEXT_RGB = (28, 33, 42)
_TEXT_STROKE_RGB = (255, 255, 255)
_MARK_RGB = (235, 91, 66)
_AGENT_RGB = (218, 58, 74)
_OPTION_FILL_RGB = (250, 251, 254)
_OPTION_SELECTED_RGB = (239, 246, 255)

_AGENT_STYLE_TREATMENTS: Tuple[str, ...] = tuple(PUZZLE_SCENE_TREATMENTS)
_AGENT_BOARD_STYLES: Tuple[str, ...] = (
    "classic_grid",
    "rounded_tiles",
    "inset_cells",
    "lab_matrix",
    "notebook_cells",
)
_LIFE_BOARD_STYLES: Tuple[str, ...] = (
    "classic_grid",
    "rounded_tiles",
    "inset_tiles",
    "lab_matrix",
    "notebook_cells",
    "terminal_cells",
)
_LIFE_CELL_PALETTES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "mono_ink": {
        "dead": (247, 248, 250),
        "alive": (35, 42, 54),
        "grid": (90, 101, 116),
        "edge": (68, 79, 94),
        "mark": (230, 73, 82),
        "accent": (188, 201, 218),
    },
    "blueprint_cells": {
        "dead": (239, 247, 254),
        "alive": (19, 55, 96),
        "grid": (73, 111, 150),
        "edge": (36, 82, 126),
        "mark": (230, 94, 55),
        "accent": (171, 203, 232),
    },
    "forest_cells": {
        "dead": (240, 249, 243),
        "alive": (20, 76, 58),
        "grid": (82, 129, 105),
        "edge": (44, 97, 77),
        "mark": (205, 69, 88),
        "accent": (180, 216, 194),
    },
    "plum_cells": {
        "dead": (250, 244, 251),
        "alive": (72, 35, 88),
        "grid": (126, 94, 141),
        "edge": (94, 63, 110),
        "mark": (35, 135, 168),
        "accent": (218, 193, 226),
    },
    "sepia_cells": {
        "dead": (252, 247, 236),
        "alive": (78, 51, 34),
        "grid": (142, 114, 82),
        "edge": (105, 82, 58),
        "mark": (202, 70, 61),
        "accent": (224, 204, 170),
    },
    "teal_cells": {
        "dead": (238, 250, 248),
        "alive": (16, 78, 85),
        "grid": (72, 132, 136),
        "edge": (36, 100, 106),
        "mark": (211, 70, 92),
        "accent": (172, 219, 218),
    },
    "burgundy_cells": {
        "dead": (252, 243, 245),
        "alive": (96, 30, 48),
        "grid": (145, 85, 100),
        "edge": (113, 55, 71),
        "mark": (0, 128, 158),
        "accent": (228, 192, 201),
    },
    "carbon_cells": {
        "dead": (246, 246, 242),
        "alive": (19, 22, 26),
        "grid": (92, 96, 101),
        "edge": (61, 66, 73),
        "mark": (226, 78, 66),
        "accent": (199, 202, 202),
    },
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "automaton")
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="automaton")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="automaton", apply_prob=0.5)


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    cell_size_px: int
    grid_gap_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    grid_line_width_px: int
    option_card_width_px: int
    option_card_height_px: int
    option_gap_px: int
    option_grid_cell_px: int
    label_font_size_px: int
    small_font_size_px: int
    arrow_width_px: int
    unit_size_jitter: Dict[str, Any]
    layout_seed: int
    font_family: str


@dataclass(frozen=True)
class _AgentTrace:
    step: int
    row: int
    col: int
    direction: int
    state_before: int
    state_after: int


@dataclass(frozen=True)
class _AgentDataset:
    rows: int
    cols: int
    state_count: int
    rule_variant: str
    query_id: str
    steps: int
    initial_grid: Tuple[Tuple[int, ...], ...]
    start_row: int
    start_col: int
    start_direction: int
    final_grid: Tuple[Tuple[int, ...], ...]
    final_row: int
    final_col: int
    final_direction: int
    traces: Tuple[_AgentTrace, ...]
    option_specs: Tuple[Dict[str, Any], ...]
    answer_label: str
    target_cells: Tuple[Tuple[int, int], ...]
    target_state: int | None
    flip_count: int


@dataclass(frozen=True)
class _LifeDataset:
    rows: int
    cols: int
    query_id: str
    steps: int
    initial_grid: Tuple[Tuple[int, ...], ...]
    future_grid: Tuple[Tuple[int, ...], ...]
    option_specs: Tuple[Dict[str, Any], ...]
    answer_label: str
    target_cells: Tuple[Tuple[int, int], ...]
    live_count: int


@dataclass(frozen=True)
class _LifeBoardVisual:
    board_style: str
    cell_palette_id: str
    dead_rgb: Tuple[int, int, int]
    alive_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    edge_rgb: Tuple[int, int, int]
    mark_rgb: Tuple[int, int, int]
    accent_rgb: Tuple[int, int, int]
    board_style_probabilities: Dict[str, float]
    cell_palette_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _TuringTransition:
    state: str
    read_symbol: str
    write_symbol: str
    move: str
    next_state: str


@dataclass(frozen=True)
class _TuringTrace:
    step: int
    state: str
    head_position: int
    read_symbol: str
    write_symbol: str
    move: str
    next_state: str


@dataclass(frozen=True)
class _TuringDataset:
    tape_length: int
    symbol_count: int
    symbols: Tuple[str, ...]
    query_id: str
    query_symbol: str
    steps: int
    states: Tuple[str, ...]
    start_state: str
    start_head: int
    initial_tape: Tuple[str, ...]
    final_tape: Tuple[str, ...]
    transitions: Tuple[_TuringTransition, ...]
    traces: Tuple[_TuringTrace, ...]
    answer_count: int


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    scene_bbox_px: Tuple[int, int, int, int]
    item_bboxes: Dict[str, Tuple[int, int, int, int]]
    entities: Tuple[Dict[str, Any], ...]
    layout_jitter: Dict[str, Any]
    style_metadata: Dict[str, Any]


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


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
        namespace="puzzles.automaton.unit_size",
    )
    font_params = {**dict(render_defaults), **dict(params)}
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="puzzles.automaton.font",
        params=font_params,
    )
    return _RenderParams(
        canvas_width=int(group_default(render_defaults, "canvas_width", 1040)),
        canvas_height=int(group_default(render_defaults, "canvas_height", 880)),
        cell_size_px=scale_puzzle_px(group_default(render_defaults, "cell_size_px", 54), unit_scale, min_px=28),
        grid_gap_px=scale_puzzle_px(group_default(render_defaults, "grid_gap_px", 2), unit_scale, min_px=1),
        panel_padding_px=scale_puzzle_px(group_default(render_defaults, "panel_padding_px", 28), unit_scale, min_px=12),
        panel_corner_radius_px=scale_puzzle_px(group_default(render_defaults, "panel_corner_radius_px", 22), unit_scale, min_px=8),
        panel_border_width_px=scale_puzzle_px(group_default(render_defaults, "panel_border_width_px", 3), unit_scale, min_px=1),
        grid_line_width_px=scale_puzzle_px(group_default(render_defaults, "grid_line_width_px", 2), unit_scale, min_px=1),
        option_card_width_px=scale_puzzle_px(group_default(render_defaults, "option_card_width_px", 150), unit_scale, min_px=80),
        option_card_height_px=scale_puzzle_px(group_default(render_defaults, "option_card_height_px", 116), unit_scale, min_px=70),
        option_gap_px=scale_puzzle_px(group_default(render_defaults, "option_gap_px", 18), unit_scale, min_px=8),
        option_grid_cell_px=scale_puzzle_px(group_default(render_defaults, "option_grid_cell_px", 24), unit_scale, min_px=9),
        label_font_size_px=scale_puzzle_px(group_default(render_defaults, "label_font_size_px", 22), unit_scale, min_px=12),
        small_font_size_px=scale_puzzle_px(group_default(render_defaults, "small_font_size_px", 16), unit_scale, min_px=10),
        arrow_width_px=scale_puzzle_px(group_default(render_defaults, "arrow_width_px", 6), unit_scale, min_px=2),
        unit_size_jitter=dict(unit_meta),
        layout_seed=int(hash64(int(instance_seed), "puzzles.automaton.layout", 0)),
        font_family=str(font_family),
    )


def _style_meta_with_font(style_meta: Mapping[str, Any], render_params: _RenderParams) -> Dict[str, Any]:
    """Attach the sampled readout font metadata used by rendered scene text."""

    return {
        **dict(style_meta),
        "font_family": str(render_params.font_family),
        "font": {
            "source": "global_font_pool",
            "font_family": str(render_params.font_family),
            "font_asset_version": font_asset_version(),
            "scope": "single_automaton_panel",
        },
    }


def _resolve_life_board_visual(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> _LifeBoardVisual:
    board_style, board_probs = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        supported_variants=_LIFE_BOARD_STYLES,
        explicit_key="life_board_style",
        weights_key="life_board_style_weights",
        balance_flag_key="balanced_life_board_style_sampling",
        axis_namespace="life_board_style",
    )
    palette_id, palette_probs = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        supported_variants=tuple(_LIFE_CELL_PALETTES),
        explicit_key="life_cell_palette",
        weights_key="life_cell_palette_weights",
        balance_flag_key="balanced_life_cell_palette_sampling",
        axis_namespace="life_cell_palette",
    )
    palette = _LIFE_CELL_PALETTES[str(palette_id)]
    return _LifeBoardVisual(
        board_style=str(board_style),
        cell_palette_id=str(palette_id),
        dead_rgb=tuple(int(value) for value in palette["dead"]),
        alive_rgb=tuple(int(value) for value in palette["alive"]),
        grid_rgb=tuple(int(value) for value in palette["grid"]),
        edge_rgb=tuple(int(value) for value in palette["edge"]),
        mark_rgb=tuple(int(value) for value in palette["mark"]),
        accent_rgb=tuple(int(value) for value in palette["accent"]),
        board_style_probabilities={str(key): float(value) for key, value in board_probs.items()},
        cell_palette_probabilities={str(key): float(value) for key, value in palette_probs.items()},
    )


def _resolve_agent_board_style(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        supported_variants=_AGENT_BOARD_STYLES,
        explicit_key="agent_board_style",
        weights_key="agent_board_style_weights",
        balance_flag_key="balanced_agent_board_style_sampling",
        axis_namespace="agent_board_style",
    )


def _style_meta_with_agent_board(
    style_meta: Mapping[str, Any],
    *,
    board_style: str,
    board_style_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    return {
        **dict(style_meta),
        "agent_board": {
            "board_style": str(board_style),
            "board_style_probabilities": {str(key): float(value) for key, value in board_style_probabilities.items()},
            "semantic_color_policy": {
                "state_colors_preserved_from_scene_style": True,
                "same_board_style_for_source_and_options": True,
            },
        },
    }


def _life_board_visual_metadata(life_visual: _LifeBoardVisual) -> Dict[str, Any]:
    alive_dead_lab = float(color_distance(life_visual.alive_rgb, life_visual.dead_rgb, distance_space="lab"))
    alive_dead_contrast = float(contrast_ratio(life_visual.alive_rgb, life_visual.dead_rgb))
    mark_contrast = min(
        float(contrast_ratio(life_visual.mark_rgb, life_visual.dead_rgb)),
        float(contrast_ratio(life_visual.mark_rgb, life_visual.alive_rgb)),
    )
    mark_lab = min(
        float(color_distance(life_visual.mark_rgb, life_visual.dead_rgb, distance_space="lab")),
        float(color_distance(life_visual.mark_rgb, life_visual.alive_rgb, distance_space="lab")),
    )
    return {
        "board_style": str(life_visual.board_style),
        "board_style_probabilities": dict(life_visual.board_style_probabilities),
        "cell_palette_id": str(life_visual.cell_palette_id),
        "cell_palette_probabilities": dict(life_visual.cell_palette_probabilities),
        "resolved_rgb": {
            "dead": list(life_visual.dead_rgb),
            "alive": list(life_visual.alive_rgb),
            "grid": list(life_visual.grid_rgb),
            "edge": list(life_visual.edge_rgb),
            "mark": list(life_visual.mark_rgb),
            "accent": list(life_visual.accent_rgb),
        },
        "semantic_color_policy": {
            "alive_cells_remain_dark": True,
            "empty_cells_remain_light": True,
            "same_style_and_palette_for_source_and_options": True,
        },
        "contrast_checks": {
            "alive_dead_contrast_ratio": round(alive_dead_contrast, 3),
            "alive_dead_lab_distance": round(alive_dead_lab, 3),
            "alive_dead_pass": bool(alive_dead_contrast >= 4.5 and alive_dead_lab >= 45.0),
            "mark_min_cell_contrast_ratio": round(mark_contrast, 3),
            "mark_min_cell_lab_distance": round(mark_lab, 3),
            "mark_pass": bool(mark_contrast >= 2.0 and mark_lab >= 30.0),
        },
    }


def _style_meta_with_life_board(
    style_meta: Mapping[str, Any],
    *,
    life_visual: _LifeBoardVisual,
) -> Dict[str, Any]:
    return {
        **dict(style_meta),
        "life_board": _life_board_visual_metadata(life_visual),
    }


def _agent_option_vertical_gap(render_params: _RenderParams) -> int:
    unit_scale = float(render_params.unit_size_jitter.get("scale", 1.0))
    return scale_puzzle_px(58, unit_scale, min_px=34)


def _agent_content_metrics(
    *,
    dataset: _AgentDataset,
    render_params: _RenderParams,
) -> Dict[str, int]:
    rows, cols = int(dataset.rows), int(dataset.cols)
    cell = int(render_params.cell_size_px)
    gap = int(render_params.grid_gap_px)
    grid_bbox = _grid_bbox(left=0, top=0, rows=rows, cols=cols, cell_size=cell, gap=gap)
    grid_w = int(grid_bbox[2] - grid_bbox[0])
    grid_h = int(grid_bbox[3] - grid_bbox[1])
    panel_w = int(grid_w + 2 * int(render_params.panel_padding_px))
    panel_h = int(grid_h + 2 * int(render_params.panel_padding_px))
    option_w = 0
    option_h = 0
    option_gap_y = 0
    if dataset.option_specs:
        card_w = int(render_params.option_card_width_px)
        card_h = int(render_params.option_card_height_px)
        gap_x = int(render_params.option_gap_px)
        option_w = int(len(dataset.option_specs) * card_w + max(0, len(dataset.option_specs) - 1) * gap_x)
        option_h = int(card_h)
        option_gap_y = int(_agent_option_vertical_gap(render_params))
    content_w = int(max(panel_w, option_w))
    content_h = int(panel_h + (option_gap_y + option_h if option_h else 0))
    return {
        "grid_width_px": grid_w,
        "grid_height_px": grid_h,
        "panel_width_px": panel_w,
        "panel_height_px": panel_h,
        "option_width_px": option_w,
        "option_height_px": option_h,
        "option_vertical_gap_px": option_gap_y,
        "content_width_px": content_w,
        "content_height_px": content_h,
    }


def _life_option_vertical_gap(render_params: _RenderParams) -> int:
    unit_scale = float(render_params.unit_size_jitter.get("scale", 1.0))
    return scale_puzzle_px(50, unit_scale, min_px=28)


def _life_option_grid_gap(render_params: _RenderParams) -> int:
    return max(1, int(render_params.grid_gap_px))


def _life_option_card_size(
    *,
    rows: int,
    cols: int,
    render_params: _RenderParams,
) -> Tuple[int, int]:
    cell = int(render_params.option_grid_cell_px)
    gap = _life_option_grid_gap(render_params)
    grid_w = int(cols * cell + max(0, cols - 1) * gap)
    grid_h = int(rows * cell + max(0, rows - 1) * gap)
    pad_x = max(10, int(round(render_params.panel_padding_px * 0.45)))
    header_h = max(30, int(round(render_params.label_font_size_px * 1.45)))
    pad_bottom = max(10, int(round(render_params.panel_padding_px * 0.40)))
    return (
        max(int(render_params.option_card_width_px), int(grid_w + 2 * pad_x)),
        max(int(render_params.option_card_height_px) + 38, int(header_h + grid_h + pad_bottom)),
    )


def _life_content_metrics(
    *,
    dataset: _LifeDataset,
    render_params: _RenderParams,
) -> Dict[str, int]:
    rows, cols = int(dataset.rows), int(dataset.cols)
    cell = int(render_params.cell_size_px)
    gap = int(render_params.grid_gap_px)
    grid_bbox = _grid_bbox(left=0, top=0, rows=rows, cols=cols, cell_size=cell, gap=gap)
    grid_w = int(grid_bbox[2] - grid_bbox[0])
    grid_h = int(grid_bbox[3] - grid_bbox[1])
    panel_w = int(grid_w + 2 * int(render_params.panel_padding_px))
    panel_h = int(grid_h + 2 * int(render_params.panel_padding_px))
    option_w = 0
    option_h = 0
    option_gap_y = 0
    if dataset.option_specs:
        card_w, card_h = _life_option_card_size(rows=rows, cols=cols, render_params=render_params)
        gap_x = int(render_params.option_gap_px)
        option_w = int(len(dataset.option_specs) * card_w + max(0, len(dataset.option_specs) - 1) * gap_x)
        option_h = int(card_h)
        option_gap_y = int(_life_option_vertical_gap(render_params))
    content_w = int(max(panel_w, option_w))
    content_h = int(panel_h + (option_gap_y + option_h if option_h else 0))
    return {
        "grid_width_px": grid_w,
        "grid_height_px": grid_h,
        "panel_width_px": panel_w,
        "panel_height_px": panel_h,
        "option_width_px": option_w,
        "option_height_px": option_h,
        "option_vertical_gap_px": option_gap_y,
        "content_width_px": content_w,
        "content_height_px": content_h,
    }


def _fit_agent_render_params(
    *,
    dataset: _AgentDataset,
    render_params: _RenderParams,
) -> _RenderParams:
    metrics = _agent_content_metrics(dataset=dataset, render_params=render_params)
    rng = spawn_rng(instance_seed=int(render_params.layout_seed), namespace="agent_automaton_canvas")
    min_margin = max(28, int(round(render_params.panel_padding_px * 1.15)))
    max_margin = max(min_margin, int(round(render_params.panel_padding_px * 2.45)))
    left_margin = rng.randint(min_margin, max_margin)
    right_margin = rng.randint(min_margin, max_margin)
    top_margin = rng.randint(min_margin, max_margin)
    bottom_margin = rng.randint(min_margin, max_margin)
    min_canvas_w = 520 if dataset.option_specs else 420
    min_canvas_h = 420 if dataset.option_specs else 360
    target_w = int(metrics["content_width_px"] + left_margin + right_margin)
    target_h = int(metrics["content_height_px"] + top_margin + bottom_margin)
    canvas_w = min(int(render_params.canvas_width), max(int(min_canvas_w), target_w))
    canvas_h = min(int(render_params.canvas_height), max(int(min_canvas_h), target_h))
    return replace(render_params, canvas_width=int(canvas_w), canvas_height=int(canvas_h))


def _fit_life_render_params(
    *,
    dataset: _LifeDataset,
    render_params: _RenderParams,
) -> _RenderParams:
    if dataset.option_specs:
        safe_margin = max(18, int(round(render_params.panel_padding_px * 0.85)))
        min_cell = max(18, min(int(render_params.cell_size_px), 22))
        for cell in range(int(render_params.cell_size_px), min_cell - 1, -1):
            candidate = replace(render_params, cell_size_px=int(cell), option_grid_cell_px=int(cell))
            candidate_metrics = _life_content_metrics(dataset=dataset, render_params=candidate)
            if (
                int(candidate_metrics["content_width_px"]) <= int(render_params.canvas_width - 2 * safe_margin)
                and int(candidate_metrics["content_height_px"]) <= int(render_params.canvas_height - 2 * safe_margin)
            ):
                render_params = candidate
                break
        else:
            render_params = replace(render_params, cell_size_px=int(min_cell), option_grid_cell_px=int(min_cell))
    metrics = _life_content_metrics(dataset=dataset, render_params=render_params)
    rng = spawn_rng(instance_seed=int(render_params.layout_seed), namespace="life_automaton_canvas")
    min_margin = max(24, int(round(render_params.panel_padding_px * 1.05)))
    max_margin = max(min_margin, int(round(render_params.panel_padding_px * 2.25)))
    left_margin = rng.randint(min_margin, max_margin)
    right_margin = rng.randint(min_margin, max_margin)
    top_margin = rng.randint(min_margin, max_margin)
    bottom_margin = rng.randint(min_margin, max_margin)
    min_canvas_w = 520 if dataset.option_specs else 420
    min_canvas_h = 420 if dataset.option_specs else 360
    target_w = int(metrics["content_width_px"] + left_margin + right_margin)
    target_h = int(metrics["content_height_px"] + top_margin + bottom_margin)
    canvas_w = min(int(render_params.canvas_width), max(int(min_canvas_w), target_w))
    canvas_h = min(int(render_params.canvas_height), max(int(min_canvas_h), target_h))
    return replace(render_params, canvas_width=int(canvas_w), canvas_height=int(canvas_h))


def _resolve_agent_style(
    *,
    scene_variant: str,
    render_params: _RenderParams,
) -> Tuple[PuzzleSceneStyle, Dict[str, Any]]:
    """Resolve one non-semantic scene-level style pack for the agent board."""

    style, metadata = resolve_puzzle_scene_style(
        instance_seed=int(render_params.layout_seed),
        namespace=f"agent_automaton.{scene_variant}",
        treatments=_AGENT_STYLE_TREATMENTS,
    )
    chrome_mode, chrome_metadata = resolve_panel_chrome_mode(
        instance_seed=int(render_params.layout_seed),
        namespace=f"agent_automaton.{scene_variant}",
    )
    return style, {
        **dict(metadata),
        "scene_variant": str(scene_variant),
        "panel_chrome": dict(chrome_metadata),
        "panel_chrome_mode": str(chrome_mode),
    }


def _resolve_turing_style(
    *,
    scene_variant: str,
    render_params: _RenderParams,
) -> Tuple[PuzzleSceneStyle, Dict[str, Any]]:
    """Resolve one non-semantic scene-level style pack for the tape machine."""

    style, metadata = resolve_puzzle_scene_style(
        instance_seed=int(render_params.layout_seed),
        namespace=f"turing_tape.{scene_variant}",
        treatments=_AGENT_STYLE_TREATMENTS,
    )
    chrome_mode, chrome_metadata = resolve_panel_chrome_mode(
        instance_seed=int(render_params.layout_seed),
        namespace=f"turing_tape.{scene_variant}",
    )
    return style, {
        **dict(metadata),
        "scene_variant": str(scene_variant),
        "panel_chrome": dict(chrome_metadata),
        "panel_chrome_mode": str(chrome_mode),
    }


def _resolve_axis(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_variants: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(item) for item in supported_variants],
        task_id=str(task_id),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        axis_namespace=str(axis_namespace),
    )


def _resolve_query(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_queries: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None and effective_params.get("query_id") is not None:
        effective_params["query_id"] = str(effective_params["query_id"])
    return _resolve_axis(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        supported_variants=supported_queries,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _decorrelated_selection_index(*, params: Mapping[str, Any], instance_seed: int, namespace: str) -> int:
    return resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))


def _turn_offsets(rule_variant: str) -> Tuple[int, ...]:
    if str(rule_variant) == "three_state_rule":
        return (1, 0, -1)
    return (1, -1)


def _rule_variant_from_query(query_id: str) -> str:
    return "three_state_rule" if "three_state" in str(query_id) else "binary_rule"


def _simulate_agent(
    grid: Sequence[Sequence[int]],
    *,
    start_row: int,
    start_col: int,
    start_direction: int,
    steps: int,
    turn_offsets: Sequence[int],
) -> Tuple[Tuple[Tuple[int, ...], ...], int, int, int, Tuple[_AgentTrace, ...]]:
    state_count = len(turn_offsets)
    rows = len(grid)
    cols = len(grid[0])
    current = [list(row) for row in grid]
    row = int(start_row)
    col = int(start_col)
    direction = int(start_direction)
    traces: List[_AgentTrace] = []
    for step in range(1, int(steps) + 1):
        state_before = int(current[row][col])
        direction = int((direction + int(turn_offsets[state_before])) % 4)
        state_after = int((state_before + 1) % state_count)
        current[row][col] = state_after
        traces.append(
            _AgentTrace(
                step=int(step),
                row=int(row),
                col=int(col),
                direction=int(direction),
                state_before=int(state_before),
                state_after=int(state_after),
            )
        )
        dr, dc = _DIR_VEC[direction]
        row = int((row + dr) % rows)
        col = int((col + dc) % cols)
    return tuple(tuple(int(value) for value in row_values) for row_values in current), row, col, direction, tuple(traces)


def _simulate_life(grid: Sequence[Sequence[int]], *, steps: int) -> Tuple[Tuple[int, ...], ...]:
    current = tuple(tuple(int(value) for value in row) for row in grid)
    rows = len(current)
    cols = len(current[0])
    for _ in range(int(steps)):
        next_rows: List[Tuple[int, ...]] = []
        for row in range(rows):
            values: List[int] = []
            for col in range(cols):
                neighbors = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = row + dr
                        cc = col + dc
                        if 0 <= rr < rows and 0 <= cc < cols:
                            neighbors += int(current[rr][cc])
                alive = int(current[row][col])
                values.append(1 if (neighbors == 3 or (alive and neighbors == 2)) else 0)
            next_rows.append(tuple(values))
        current = tuple(next_rows)
    return current


def _sample_grid(rng, *, rows: int, cols: int, state_count: int, live_prob: float = 0.34) -> Tuple[Tuple[int, ...], ...]:
    values: List[Tuple[int, ...]] = []
    for _row in range(int(rows)):
        row_values: List[int] = []
        for _col in range(int(cols)):
            if int(state_count) == 2:
                row_values.append(1 if float(rng.random()) < float(live_prob) else 0)
            else:
                row_values.append(int(rng.randrange(int(state_count))))
        values.append(tuple(row_values))
    return tuple(values)


def _option_pose_text(row: int, col: int, direction: int) -> str:
    return f"r{int(row) + 1}, c{int(col) + 1}, {_DIRECTIONS[int(direction)]}"


def _state_label(*, state: int, state_count: int) -> str:
    if int(state_count) == 2:
        return "light" if int(state) == 0 else "colored state"
    return f"state {int(state)}"


def _build_pose_options(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    rows: int,
    cols: int,
    final_row: int,
    final_col: int,
    final_direction: int,
    option_count: int,
    rng,
) -> Tuple[Tuple[Dict[str, Any], ...], str]:
    correct = (int(final_row), int(final_col), int(final_direction))
    options = {correct}
    while len(options) < int(option_count):
        kind = int(rng.randrange(4))
        if kind == 0:
            candidate = (int((final_row + rng.choice([-2, -1, 1, 2])) % rows), int(final_col), int(final_direction))
        elif kind == 1:
            candidate = (int(final_row), int((final_col + rng.choice([-2, -1, 1, 2])) % cols), int(final_direction))
        elif kind == 2:
            candidate = (int(final_row), int(final_col), int((final_direction + rng.choice([1, 2, 3])) % 4))
        else:
            candidate = (int(rng.randrange(rows)), int(rng.randrange(cols)), int(rng.randrange(4)))
        options.add(candidate)
    distractors = [option for option in options if option != correct]
    rng.shuffle(distractors)
    correct_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))) % int(option_count)
    ordered: List[Tuple[int, int, int]] = []
    for index in range(int(option_count)):
        if index == correct_index:
            ordered.append(correct)
        else:
            ordered.append(distractors.pop())
    specs: List[Dict[str, Any]] = []
    answer_label = "A"
    for index, (row, col, direction) in enumerate(ordered):
        label = option_label_for_index(index)
        if (row, col, direction) == correct:
            answer_label = str(label)
        specs.append(
            {
                "option_id": f"option_{label}",
                "label": str(label),
                "row": int(row),
                "col": int(col),
                "direction": int(direction),
                "pose_text": _option_pose_text(row, col, direction),
                "is_correct": bool((row, col, direction) == correct),
            }
        )
    return tuple(specs), str(answer_label)


def _grid_live_count(grid: Sequence[Sequence[int]], cells: Sequence[Tuple[int, int]] | None = None) -> int:
    if cells is None:
        return int(sum(int(value) for row in grid for value in row))
    return int(sum(int(grid[int(row)][int(col)]) for row, col in cells))


def _rect_cells(row0: int, col0: int, height: int, width: int) -> Tuple[Tuple[int, int], ...]:
    return tuple((int(row), int(col)) for row in range(row0, row0 + height) for col in range(col0, col0 + width))


def _agent_visit_counts(traces: Sequence[_AgentTrace]) -> Dict[Tuple[int, int], int]:
    counts: Dict[Tuple[int, int], int] = {}
    for trace in traces:
        key = (int(trace.row), int(trace.col))
        counts[key] = int(counts.get(key, 0)) + 1
    return counts


def _build_agent_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
    rule_variant: str | None = None,
) -> _AgentDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.agent")
    rows_min, rows_max = _get_range(params, gen_defaults, min_key="agent_rows_min", max_key="agent_rows_max", fallback_min=6, fallback_max=9)
    cols_min, cols_max = _get_range(params, gen_defaults, min_key="agent_cols_min", max_key="agent_cols_max", fallback_min=6, fallback_max=9)
    steps_min, steps_max = _get_range(params, gen_defaults, min_key="agent_steps_min", max_key="agent_steps_max", fallback_min=5, fallback_max=14)
    rows = int(rng.randint(rows_min, rows_max))
    cols = int(rng.randint(cols_min, cols_max))
    steps = int(params.get("steps", rng.randint(steps_min, steps_max)))
    resolved_rule_variant = str(rule_variant or _rule_variant_from_query(str(query_id)))
    state_count = 3 if resolved_rule_variant == "three_state_rule" else 2
    grid = _sample_grid(rng, rows=rows, cols=cols, state_count=state_count, live_prob=0.38)
    start_row = int(rng.randrange(rows))
    start_col = int(rng.randrange(cols))
    start_direction = int(rng.randrange(4))
    final_grid, final_row, final_col, final_direction, traces = _simulate_agent(
        grid,
        start_row=start_row,
        start_col=start_col,
        start_direction=start_direction,
        steps=steps,
        turn_offsets=_turn_offsets(resolved_rule_variant),
    )
    option_specs: Tuple[Dict[str, Any], ...] = tuple()
    answer_label = ""
    target_cells: Tuple[Tuple[int, int], ...] = tuple()
    target_state: int | None = None
    flip_count = 0
    if str(task_id) == AGENT_FINAL_TASK_ID:
        option_count = _get_int(params, gen_defaults, "pose_option_count", 5)
        option_specs, answer_label = _build_pose_options(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query_id}.answer_option",
            rows=rows,
            cols=cols,
            final_row=final_row,
            final_col=final_col,
            final_direction=final_direction,
            option_count=option_count,
            rng=rng,
        )
    else:
        visit_counts = _agent_visit_counts(traces)
        if str(query_id) == "marked_line_flip_count":
            line_kind = "row" if int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.{query_id}.line_kind")) % 2 == 0 else "column"
            candidates_by_score: Dict[int, List[Tuple[Tuple[int, int], ...]]] = {}
            if line_kind == "row":
                for row in range(rows):
                    cells = tuple((row, col) for col in range(cols))
                    score = int(sum(visit_counts.get((int(r), int(c)), 0) for r, c in cells))
                    if score > 0:
                        candidates_by_score.setdefault(score, []).append(cells)
            else:
                for col in range(cols):
                    cells = tuple((row, col) for row in range(rows))
                    score = int(sum(visit_counts.get((int(r), int(c)), 0) for r, c in cells))
                    if score > 0:
                        candidates_by_score.setdefault(score, []).append(cells)
            if candidates_by_score:
                scores = sorted(candidates_by_score)
                score_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.{query_id}.answer_count")) % len(scores)
                selected_score = int(scores[score_index])
                target_cells = rng.choice(candidates_by_score[selected_score])
            else:
                target_cells = ((int(start_row), int(start_col)),)
            target_set = set(target_cells)
            flip_count = int(sum(1 for trace in traces if (int(trace.row), int(trace.col)) in target_set))
        elif str(query_id) == "marked_region_flip_count":
            candidates_by_score: Dict[int, List[Tuple[Tuple[int, int], ...]]] = {}
            for height, width in ((2, 2), (2, 3), (3, 2), (3, 3)):
                if height > rows or width > cols:
                    continue
                for row0 in range(rows - height + 1):
                    for col0 in range(cols - width + 1):
                        cells = _rect_cells(row0, col0, height, width)
                        score = int(sum(visit_counts.get((int(row), int(col)), 0) for row, col in cells))
                        if score > 0:
                            candidates_by_score.setdefault(score, []).append(cells)
            if candidates_by_score:
                scores = sorted(candidates_by_score)
                desired_max = max(1, min(int(steps), int(params.get("flip_answer_max", group_default(gen_defaults, "flip_answer_max", 8)))))
                desired = 1 + (
                    int(
                        _decorrelated_selection_index(
                            params=params,
                            instance_seed=int(instance_seed),
                            namespace=f"{task_id}.{query_id}.desired_answer_count",
                        )
                    )
                    % desired_max
                )
                selected_score = min(scores, key=lambda score: (abs(int(score) - int(desired)), int(score)))
                target_cells = rng.choice(candidates_by_score[selected_score])
            else:
                target_cells = ((int(start_row), int(start_col)),)
            target_set = set(target_cells)
            flip_count = int(sum(1 for trace in traces if (int(trace.row), int(trace.col)) in target_set))
        else:
            counts_by_state = {
                state: int(sum(1 for trace in traces if int(trace.state_before) == int(state)))
                for state in range(int(state_count))
            }
            states_by_count: Dict[int, List[int]] = {}
            for state, count in counts_by_state.items():
                if int(count) > 0:
                    states_by_count.setdefault(int(count), []).append(int(state))
            feasible_counts = sorted(states_by_count)
            count_index = int(
                _decorrelated_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.{query_id}.answer_count",
                )
            ) % len(feasible_counts)
            selected_count = int(feasible_counts[count_index])
            target_state = int(rng.choice(states_by_count[selected_count]))
            flip_count = int(sum(1 for trace in traces if int(trace.state_before) == int(target_state)))
    return _AgentDataset(
        rows=int(rows),
        cols=int(cols),
        state_count=int(state_count),
        rule_variant=str(resolved_rule_variant),
        query_id=str(query_id),
        steps=int(steps),
        initial_grid=grid,
        start_row=int(start_row),
        start_col=int(start_col),
        start_direction=int(start_direction),
        final_grid=final_grid,
        final_row=int(final_row),
        final_col=int(final_col),
        final_direction=int(final_direction),
        traces=traces,
        option_specs=option_specs,
        answer_label=str(answer_label),
        target_cells=target_cells,
        target_state=target_state,
        flip_count=int(flip_count),
    )


def _build_life_options(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    future_grid: Sequence[Sequence[int]],
    option_count: int,
    rng,
) -> Tuple[Tuple[Dict[str, Any], ...], str]:
    rows = len(future_grid)
    cols = len(future_grid[0])
    correct = tuple(tuple(int(value) for value in row) for row in future_grid)
    options = {correct}
    while len(options) < int(option_count):
        candidate = [list(row) for row in correct]
        flips = int(rng.randint(1, 4))
        for _ in range(flips):
            row = int(rng.randrange(rows))
            col = int(rng.randrange(cols))
            candidate[row][col] = 1 - int(candidate[row][col])
        options.add(tuple(tuple(int(value) for value in row) for row in candidate))
    distractors = [option for option in options if option != correct]
    rng.shuffle(distractors)
    correct_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))) % int(option_count)
    ordered = []
    for index in range(int(option_count)):
        if index == correct_index:
            ordered.append(correct)
        else:
            ordered.append(distractors.pop())
    specs: List[Dict[str, Any]] = []
    answer_label = "A"
    for index, option_grid in enumerate(ordered):
        label = option_label_for_index(index)
        if option_grid == correct:
            answer_label = str(label)
        specs.append(
            {
                "option_id": f"option_{label}",
                "label": str(label),
                "grid": [list(row) for row in option_grid],
                "is_correct": bool(option_grid == correct),
            }
        )
    return tuple(specs), str(answer_label)


def _build_life_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
) -> _LifeDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.life")
    rows_min, rows_max = _get_range(params, gen_defaults, min_key="life_rows_min", max_key="life_rows_max", fallback_min=5, fallback_max=8)
    cols_min, cols_max = _get_range(params, gen_defaults, min_key="life_cols_min", max_key="life_cols_max", fallback_min=5, fallback_max=8)
    rows = int(rng.randint(rows_min, rows_max))
    cols = int(rng.randint(cols_min, cols_max))
    density = float(params.get("live_density", group_default(gen_defaults, "live_density", 0.36)))
    grid = _sample_grid(rng, rows=rows, cols=cols, state_count=2, live_prob=density)
    if str(query_id) == "two_step_future_grid":
        steps = 2
    elif str(query_id) == "one_step_future_grid":
        steps = 1
    else:
        steps_min, steps_max = _get_range(params, gen_defaults, min_key="life_steps_min", max_key="life_steps_max", fallback_min=1, fallback_max=3)
        steps = int(params.get("steps", rng.randint(steps_min, steps_max)))
    future_grid = _simulate_life(grid, steps=steps)
    option_specs: Tuple[Dict[str, Any], ...] = tuple()
    answer_label = ""
    target_cells: Tuple[Tuple[int, int], ...] = tuple((row, col) for row in range(rows) for col in range(cols))
    if str(task_id) == LIFE_GRID_TASK_ID:
        option_count = _get_int(params, gen_defaults, "grid_option_count", 5)
        option_specs, answer_label = _build_life_options(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query_id}.answer_option",
            future_grid=future_grid,
            option_count=option_count,
            rng=rng,
        )
    elif str(query_id) == "marked_line_live_count":
        candidates_by_count: Dict[int, List[Tuple[Tuple[int, int], ...]]] = {}
        for row in range(rows):
            cells = tuple((row, col) for col in range(cols))
            count = _grid_live_count(future_grid, cells)
            candidates_by_count.setdefault(int(count), []).append(cells)
        for col in range(cols):
            cells = tuple((row, col) for row in range(rows))
            count = _grid_live_count(future_grid, cells)
            candidates_by_count.setdefault(int(count), []).append(cells)
        counts = sorted(candidates_by_count)
        desired = int(
            _decorrelated_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.{query_id}.desired_answer_count",
            )
        ) % (min(rows, cols) + 1)
        selected_count = int(min(counts, key=lambda count: (abs(int(count) - int(desired)), int(count))))
        target_cells = rng.choice(candidates_by_count[selected_count])
    elif str(query_id) == "marked_region_live_count":
        candidates_by_count: Dict[int, List[Tuple[Tuple[int, int], ...]]] = {}
        for height, width in ((2, 2), (2, 3), (3, 2), (3, 3)):
            if height > rows or width > cols:
                continue
            for row0 in range(rows - height + 1):
                for col0 in range(cols - width + 1):
                    cells = _rect_cells(row0, col0, height, width)
                    count = _grid_live_count(future_grid, cells)
                    candidates_by_count.setdefault(int(count), []).append(cells)
        counts = sorted(candidates_by_count)
        count_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.{query_id}.answer_count",
            )
        ) % len(counts)
        selected_count = int(counts[count_index])
        target_cells = rng.choice(candidates_by_count[selected_count])
    live_count = _grid_live_count(future_grid, target_cells if str(query_id) in {"marked_line_live_count", "marked_region_live_count"} else None)
    return _LifeDataset(
        rows=int(rows),
        cols=int(cols),
        query_id=str(query_id),
        steps=int(steps),
        initial_grid=grid,
        future_grid=future_grid,
        option_specs=option_specs,
        answer_label=str(answer_label),
        target_cells=target_cells,
        live_count=int(live_count),
    )


def _move_delta(move: str) -> int:
    return -1 if str(move) == "L" else 1


def _sample_turing_head_path(
    rng,
    *,
    tape_length: int,
    steps: int,
) -> Tuple[int, Tuple[str, ...], Tuple[int, ...]]:
    for _attempt in range(200):
        head = int(rng.randrange(1, max(2, int(tape_length) - 1)))
        positions: List[int] = []
        moves: List[str] = []
        for _step in range(int(steps)):
            allowed: List[str] = []
            if head > 0:
                allowed.append("L")
            if head < int(tape_length) - 1:
                allowed.append("R")
            move = str(rng.choice(allowed or list(_TURING_MOVES)))
            positions.append(int(head))
            moves.append(move)
            head += _move_delta(move)
        if len(set(positions)) >= min(3, int(steps)):
            return int(positions[0]), tuple(moves), tuple(positions)
    start = int(max(1, min(int(tape_length) - 2, int(tape_length) // 2)))
    positions = []
    moves = []
    head = start
    direction = 1
    for _step in range(int(steps)):
        positions.append(int(head))
        if head >= int(tape_length) - 2:
            direction = -1
        elif head <= 1:
            direction = 1
        move = "R" if direction > 0 else "L"
        moves.append(move)
        head += _move_delta(move)
    return int(start), tuple(moves), tuple(positions)


def _transition_key(transition: _TuringTransition) -> Tuple[str, str]:
    return (str(transition.state), str(transition.read_symbol))


def _simulate_turing(
    *,
    initial_tape: Sequence[str],
    start_state: str,
    start_head: int,
    transitions: Sequence[_TuringTransition],
    steps: int,
) -> Tuple[Tuple[str, ...], Tuple[_TuringTrace, ...]]:
    table = {_transition_key(transition): transition for transition in transitions}
    tape = [str(symbol) for symbol in initial_tape]
    state = str(start_state)
    head = int(start_head)
    traces: List[_TuringTrace] = []
    for step in range(1, int(steps) + 1):
        read_symbol = str(tape[head])
        transition = table[(state, read_symbol)]
        tape[head] = str(transition.write_symbol)
        traces.append(
            _TuringTrace(
                step=int(step),
                state=str(state),
                head_position=int(head),
                read_symbol=str(read_symbol),
                write_symbol=str(transition.write_symbol),
                move=str(transition.move),
                next_state=str(transition.next_state),
            )
        )
        head = max(0, min(len(tape) - 1, int(head + _move_delta(str(transition.move)))))
        state = str(transition.next_state)
    return tuple(tape), tuple(traces)


def _build_turing_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
) -> _TuringDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.turing")
    tape_min, tape_max = _get_range(params, gen_defaults, min_key="turing_tape_length_min", max_key="turing_tape_length_max", fallback_min=8, fallback_max=11)
    steps_min, steps_max = _get_range(params, gen_defaults, min_key="turing_steps_min", max_key="turing_steps_max", fallback_min=3, fallback_max=6)
    symbol_min, symbol_max = _get_range(params, gen_defaults, min_key="turing_symbol_count_min", max_key="turing_symbol_count_max", fallback_min=2, fallback_max=2)
    answer_min, answer_max = _get_range(params, gen_defaults, min_key="turing_answer_min", max_key="turing_answer_max", fallback_min=1, fallback_max=7)
    symbol_count = int(max(2, min(len(_TURING_SYMBOLS), rng.randint(symbol_min, symbol_max))))
    symbols = tuple(_TURING_SYMBOLS[:symbol_count])
    tape_length = int(rng.randint(tape_min, tape_max))
    max_answer = int(min(answer_max, tape_length - 1))
    answer_support = list(range(int(answer_min), int(max_answer) + 1))
    if not answer_support:
        answer_support = [max(0, min(tape_length, int(answer_min)))]
    desired_answer = int(
        answer_support[
            int(
                _decorrelated_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.{query_id}.desired_answer_count",
                )
            )
            % len(answer_support)
        ]
    )
    query_symbol = str(symbols[int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.query_symbol")) % len(symbols)])
    steps = int(rng.randint(steps_min, steps_max))
    states = tuple(f"S{index}" for index in range(int(steps)))
    start_state = states[0]
    start_head, planned_moves, planned_positions = _sample_turing_head_path(rng, tape_length=tape_length, steps=steps)

    final_tape: List[str] = [str(rng.choice([symbol for symbol in symbols if symbol != query_symbol])) for _ in range(tape_length)]
    query_positions = list(range(tape_length))
    rng.shuffle(query_positions)
    for pos in query_positions[:desired_answer]:
        final_tape[int(pos)] = str(query_symbol)

    initial_tape = list(final_tape)
    first_visit_positions = []
    seen_positions: set[int] = set()
    for pos in planned_positions:
        if int(pos) not in seen_positions:
            first_visit_positions.append(int(pos))
            seen_positions.add(int(pos))
    for pos in first_visit_positions:
        if rng.random() < 0.65:
            alternatives = [symbol for symbol in symbols if str(symbol) != str(final_tape[pos])]
            initial_tape[pos] = str(rng.choice(alternatives))
    if first_visit_positions and all(str(initial_tape[pos]) == str(final_tape[pos]) for pos in first_visit_positions):
        pos = int(first_visit_positions[0])
        alternatives = [symbol for symbol in symbols if str(symbol) != str(final_tape[pos])]
        initial_tape[pos] = str(alternatives[0])

    transitions_by_key: Dict[Tuple[str, str], _TuringTransition] = {}
    tape = list(initial_tape)
    for step_index, (position, move) in enumerate(zip(planned_positions, planned_moves)):
        state = str(states[step_index])
        read_symbol = str(tape[int(position)])
        write_symbol = str(final_tape[int(position)])
        next_state = str(states[step_index + 1]) if step_index + 1 < len(states) else str(states[0])
        transition = _TuringTransition(
            state=state,
            read_symbol=read_symbol,
            write_symbol=write_symbol,
            move=str(move),
            next_state=next_state,
        )
        transitions_by_key[(state, read_symbol)] = transition
        tape[int(position)] = write_symbol

    for state in states:
        for symbol in symbols:
            key = (str(state), str(symbol))
            if key in transitions_by_key:
                continue
            transitions_by_key[key] = _TuringTransition(
                state=str(state),
                read_symbol=str(symbol),
                write_symbol=str(rng.choice(symbols)),
                move=str(rng.choice(_TURING_MOVES)),
                next_state=str(rng.choice(states)),
            )

    transitions = tuple(
        transitions_by_key[(str(state), str(symbol))]
        for state in states
        for symbol in symbols
    )
    simulated_final_tape, traces = _simulate_turing(
        initial_tape=initial_tape,
        start_state=start_state,
        start_head=start_head,
        transitions=transitions,
        steps=steps,
    )
    answer_count = int(sum(1 for symbol in simulated_final_tape if str(symbol) == str(query_symbol)))
    if answer_count != desired_answer:
        raise RuntimeError(f"constructed Turing tape answer mismatch: {answer_count} != {desired_answer}")
    return _TuringDataset(
        tape_length=int(tape_length),
        symbol_count=int(symbol_count),
        symbols=tuple(symbols),
        query_id=str(query_id),
        query_symbol=str(query_symbol),
        steps=int(steps),
        states=tuple(states),
        start_state=str(start_state),
        start_head=int(start_head),
        initial_tape=tuple(str(symbol) for symbol in initial_tape),
        final_tape=tuple(str(symbol) for symbol in simulated_final_tape),
        transitions=transitions,
        traces=traces,
        answer_count=int(answer_count),
    )


def _grid_bbox(
    *,
    left: int,
    top: int,
    rows: int,
    cols: int,
    cell_size: int,
    gap: int,
) -> Tuple[int, int, int, int]:
    width = int(cols * cell_size + max(0, cols - 1) * gap)
    height = int(rows * cell_size + max(0, rows - 1) * gap)
    return (int(left), int(top), int(left + width), int(top + height))


def _cell_bbox(
    *,
    left: int,
    top: int,
    row: int,
    col: int,
    cell_size: int,
    gap: int,
) -> Tuple[int, int, int, int]:
    x0 = int(left + col * (cell_size + gap))
    y0 = int(top + row * (cell_size + gap))
    return (x0, y0, int(x0 + cell_size), int(y0 + cell_size))


def _inset_bbox(bbox: Sequence[int], inset: int) -> Tuple[int, int, int, int]:
    x0, y0, x1, y1 = [int(value) for value in bbox]
    inset_px = max(0, int(inset))
    return (
        min(x1, x0 + inset_px),
        min(y1, y0 + inset_px),
        max(x0, x1 - inset_px),
        max(y0, y1 - inset_px),
    )


def _blend_rgb(color_a: Sequence[int], color_b: Sequence[int], alpha_b: float) -> Tuple[int, int, int]:
    alpha = max(0.0, min(1.0, float(alpha_b)))
    return tuple(
        int(round((float(color_a[index]) * (1.0 - alpha)) + (float(color_b[index]) * alpha)))
        for index in range(3)
    )


def _draw_cell_grid(
    draw: ImageDraw.ImageDraw,
    *,
    grid: Sequence[Sequence[int]],
    left: int,
    top: int,
    cell_size: int,
    gap: int,
    state_colors: Sequence[Sequence[int]],
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    item_prefix: str,
    target_cells: Sequence[Tuple[int, int]] = tuple(),
    draw_labels: bool = False,
    style: PuzzleSceneStyle = DEFAULT_PUZZLE_SCENE_STYLE,
    cell_render_style: str = "classic_grid",
) -> None:
    target_set = {(int(row), int(col)) for row, col in target_cells}
    rows = len(grid)
    cols = len(grid[0])
    font = load_font(max(10, int(cell_size * 0.28)), bold=True)
    for row in range(rows):
        for col in range(cols):
            bbox = _cell_bbox(left=left, top=top, row=row, col=col, cell_size=cell_size, gap=gap)
            state = int(grid[row][col])
            fill = tuple(int(value) for value in state_colors[state % len(state_colors)])
            cell_id = f"{item_prefix}_cell_{row}_{col}"
            item_bboxes[cell_id] = bbox
            selected = (row, col) in target_set
            render_style = str(cell_render_style)
            if render_style == "rounded_tiles":
                draw_rounded_rect(
                    draw,
                    bbox=bbox,
                    radius=max(3, int(round(cell_size * 0.10))),
                    fill=fill,
                    outline=style.grid_rgb,
                    width=max(1, int(round(cell_size * 0.035))),
                )
            elif render_style == "inset_cells":
                draw.rectangle(bbox, fill=style.grid_rgb)
                inner = _inset_bbox(bbox, max(1, int(round(cell_size * 0.08))))
                draw_rounded_rect(
                    draw,
                    bbox=inner,
                    radius=max(3, int(round(cell_size * 0.10))),
                    fill=fill,
                    outline=style.panel_border_rgb,
                    width=1,
                )
            elif render_style == "lab_matrix":
                draw.rectangle(bbox, fill=fill, outline=style.panel_border_rgb, width=max(1, int(round(cell_size * 0.04))))
                highlight = _blend_rgb(fill, (255, 255, 255), 0.32)
                draw.line((bbox[0] + 2, bbox[1] + 2, bbox[2] - 3, bbox[1] + 2), fill=highlight, width=1)
                draw.line((bbox[0] + 2, bbox[1] + 2, bbox[0] + 2, bbox[3] - 3), fill=highlight, width=1)
            elif render_style == "notebook_cells":
                draw.rectangle(bbox, fill=fill, outline=style.grid_rgb, width=1)
                draw.line(
                    (bbox[0] + 4, bbox[1] + max(4, int(cell_size * 0.28)), bbox[2] - 4, bbox[1] + max(4, int(cell_size * 0.28))),
                    fill=style.notebook_line_rgb,
                    width=1,
                )
            else:
                draw_puzzle_grid_cell(
                    draw,
                    bbox=bbox,
                    fill=fill,
                    style=style,
                    outline=style.grid_rgb,
                    width=1,
                    selected=False,
                )
            if selected:
                draw.rectangle(
                    bbox,
                    outline=style.mark_rgb,
                    width=max(3, int(cell_size * 0.10)),
                )
            if draw_labels:
                draw_centered_text(
                    draw,
                    text=str(state),
                    center=((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0),
                    font=font,
                    fill=style.text_rgb if state == 0 else style.text_stroke_rgb,
                    stroke_fill=style.text_stroke_rgb if state == 0 else style.text_rgb,
                    stroke_width=1,
                )


def _draw_life_cell_grid(
    draw: ImageDraw.ImageDraw,
    *,
    grid: Sequence[Sequence[int]],
    left: int,
    top: int,
    cell_size: int,
    gap: int,
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    item_prefix: str,
    target_cells: Sequence[Tuple[int, int]] = tuple(),
    style: PuzzleSceneStyle = DEFAULT_PUZZLE_SCENE_STYLE,
    life_visual: _LifeBoardVisual,
) -> None:
    target_set = {(int(row), int(col)) for row, col in target_cells}
    rows = len(grid)
    cols = len(grid[0])
    board_bbox = _grid_bbox(left=left, top=top, rows=rows, cols=cols, cell_size=cell_size, gap=gap)
    board_style = str(life_visual.board_style)
    if board_style in {"inset_tiles", "terminal_cells"}:
        draw_rounded_rect(
            draw,
            bbox=board_bbox,
            radius=max(4, int(cell_size * 0.14)),
            fill=life_visual.grid_rgb,
            outline=life_visual.edge_rgb,
            width=max(1, int(round(cell_size * 0.04))),
        )
    for row in range(rows):
        for col in range(cols):
            bbox = _cell_bbox(left=left, top=top, row=row, col=col, cell_size=cell_size, gap=gap)
            state = int(grid[row][col])
            fill = life_visual.alive_rgb if state else life_visual.dead_rgb
            cell_id = f"{item_prefix}_cell_{row}_{col}"
            item_bboxes[cell_id] = bbox
            if board_style == "classic_grid":
                draw.rectangle(
                    bbox,
                    fill=fill,
                    outline=life_visual.grid_rgb,
                    width=max(1, int(round(cell_size * 0.035))),
                )
            elif board_style == "rounded_tiles":
                draw_rounded_rect(
                    draw,
                    bbox=bbox,
                    radius=max(3, int(cell_size * 0.10)),
                    fill=fill,
                    outline=life_visual.grid_rgb,
                    width=max(1, int(round(cell_size * 0.035))),
                )
            elif board_style == "inset_tiles":
                inner = _inset_bbox(bbox, max(1, int(round(cell_size * 0.08))))
                draw_rounded_rect(
                    draw,
                    bbox=inner,
                    radius=max(3, int(cell_size * 0.12)),
                    fill=fill,
                    outline=life_visual.edge_rgb,
                    width=1,
                )
            elif board_style == "lab_matrix":
                draw.rectangle(
                    bbox,
                    fill=fill,
                    outline=life_visual.edge_rgb,
                    width=max(1, int(round(cell_size * 0.04))),
                )
                highlight = _blend_rgb(fill, (255, 255, 255), 0.24 if state else 0.42)
                draw.line((bbox[0] + 2, bbox[1] + 2, bbox[2] - 3, bbox[1] + 2), fill=highlight, width=1)
                draw.line((bbox[0] + 2, bbox[1] + 2, bbox[0] + 2, bbox[3] - 3), fill=highlight, width=1)
            elif board_style == "notebook_cells":
                draw.rectangle(bbox, fill=fill, outline=life_visual.grid_rgb, width=1)
                if not state:
                    line_y = int(round((bbox[1] + bbox[3]) / 2.0))
                    draw.line((bbox[0] + 4, line_y, bbox[2] - 4, line_y), fill=life_visual.accent_rgb, width=1)
                else:
                    draw.line((bbox[0] + 3, bbox[1] + 3, bbox[2] - 4, bbox[1] + 3), fill=life_visual.accent_rgb, width=1)
            elif board_style == "terminal_cells":
                draw.rectangle(bbox, fill=life_visual.grid_rgb)
                inner = _inset_bbox(bbox, max(1, int(round(cell_size * 0.06))))
                draw.rectangle(inner, fill=fill, outline=life_visual.edge_rgb, width=1)
                if state:
                    glow = _blend_rgb(fill, life_visual.accent_rgb, 0.20)
                    draw.rectangle(_inset_bbox(inner, max(2, int(round(cell_size * 0.22)))), fill=glow)
            else:
                draw_puzzle_grid_cell(
                    draw,
                    bbox=bbox,
                    fill=fill,
                    style=style,
                    outline=life_visual.grid_rgb,
                    width=1,
                    selected=False,
                )
            if (row, col) in target_set:
                draw.rectangle(
                    bbox,
                    outline=life_visual.mark_rgb,
                    width=max(3, int(cell_size * 0.10)),
                )


def _draw_agent_marker(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[int],
    direction: int,
    color: Sequence[int] = _AGENT_RGB,
    inner_fill: Sequence[int] = (255, 246, 236),
    width: int = 6,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    radius = 0.34 * min(x1 - x0, y1 - y0)
    dr, dc = _DIR_VEC[int(direction)]
    end = (float(cx + dc * radius), float(cy + dr * radius))
    start = (float(cx - dc * radius * 0.55), float(cy - dr * radius * 0.55))
    draw.ellipse(
        (cx - radius * 0.55, cy - radius * 0.55, cx + radius * 0.55, cy + radius * 0.55),
        fill=tuple(int(value) for value in inner_fill),
        outline=color,
        width=3,
    )
    draw_arrow(draw, start=start, end=end, fill=color, width=int(width), head_length_px=14, head_width_px=18)


def _draw_option_card(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    label: str,
    fill: Sequence[int] = _OPTION_FILL_RGB,
    style: PuzzleSceneStyle = DEFAULT_PUZZLE_SCENE_STYLE,
) -> None:
    draw_puzzle_option_card(
        draw,
        bbox=bbox,
        style=style,
        fill=fill,
        radius=14,
        border_width=2,
    )
    font = load_font(20, bold=True)
    draw_centered_text(
        draw,
        text=str(label),
        center=(bbox[0] + 20, bbox[1] + 20),
        font=font,
        fill=style.text_rgb,
        stroke_fill=style.text_stroke_rgb,
        stroke_width=1,
    )


def _draw_agent_pose_options(
    draw: ImageDraw.ImageDraw,
    *,
    option_specs: Sequence[Mapping[str, Any]],
    render_params: _RenderParams,
    top: int,
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    style: PuzzleSceneStyle = DEFAULT_PUZZLE_SCENE_STYLE,
    cell_render_style: str = "classic_grid",
) -> Tuple[int, int, int, int]:
    card_w = int(render_params.option_card_width_px)
    card_h = int(render_params.option_card_height_px)
    gap = int(render_params.option_gap_px)
    count = len(option_specs)
    total_w = count * card_w + max(0, count - 1) * gap
    left = int((render_params.canvas_width - total_w) // 2)
    text_font = load_font(int(render_params.small_font_size_px), bold=False)
    for index, option in enumerate(option_specs):
        x0 = int(left + index * (card_w + gap))
        bbox = (x0, int(top), int(x0 + card_w), int(top + card_h))
        _draw_option_card(draw, bbox=bbox, label=str(option["label"]), fill=style.option_fill_rgb, style=style)
        item_bboxes[str(option["option_id"])] = bbox
        marker_side = max(24, min(int(card_w * 0.46), int(card_h * 0.42)))
        marker_left = int(x0 + (card_w - marker_side) / 2)
        marker_top = int(top + max(22, int(card_h * 0.22)))
        marker_bbox = (
            marker_left,
            marker_top,
            int(marker_left + marker_side),
            int(marker_top + marker_side),
        )
        _draw_cell_grid(
            draw,
            grid=((0,),),
            left=int(marker_bbox[0]),
            top=int(marker_bbox[1]),
            cell_size=int(marker_side),
            gap=1,
            state_colors=(style.option_marker_fill_rgb,),
            item_bboxes={},
            item_prefix="agent_option_marker",
            style=style,
            cell_render_style=str(cell_render_style),
        )
        _draw_agent_marker(
            draw,
            bbox=marker_bbox,
            direction=int(option["direction"]),
            color=style.agent_rgb,
            inner_fill=style.agent_inner_rgb,
            width=max(3, int(render_params.arrow_width_px) - 2),
        )
        draw_centered_text(
            draw,
            text=f"r{int(option['row']) + 1}, c{int(option['col']) + 1}",
            center=(x0 + card_w / 2, int(top) + card_h - max(14, int(card_h * 0.17))),
            font=text_font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
    return (left, int(top), int(left + total_w), int(top + card_h))


def _draw_life_option_grid(
    draw: ImageDraw.ImageDraw,
    *,
    option_grid: Sequence[Sequence[int]],
    bbox: Tuple[int, int, int, int],
    label: str,
    render_params: _RenderParams,
    style: PuzzleSceneStyle = DEFAULT_PUZZLE_SCENE_STYLE,
    life_visual: _LifeBoardVisual,
) -> None:
    _draw_option_card(draw, bbox=bbox, label=label, fill=style.option_fill_rgb, style=style)
    rows = len(option_grid)
    cols = len(option_grid[0])
    cell = int(render_params.option_grid_cell_px)
    gap = _life_option_grid_gap(render_params)
    grid_w = cols * cell + max(0, cols - 1) * gap
    grid_h = rows * cell + max(0, rows - 1) * gap
    header_h = max(30, int(round(render_params.label_font_size_px * 1.45)))
    left = int(bbox[0] + (bbox[2] - bbox[0] - grid_w) / 2)
    top = int(bbox[1] + header_h + max(0, (bbox[3] - bbox[1] - header_h - grid_h) / 2))
    dummy: Dict[str, Tuple[int, int, int, int]] = {}
    _draw_life_cell_grid(
        draw,
        grid=option_grid,
        left=left,
        top=top,
        cell_size=cell,
        gap=gap,
        item_bboxes=dummy,
        item_prefix="option_preview",
        style=style,
        life_visual=life_visual,
    )


def _draw_life_options(
    draw: ImageDraw.ImageDraw,
    *,
    option_specs: Sequence[Mapping[str, Any]],
    render_params: _RenderParams,
    top: int,
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    style: PuzzleSceneStyle = DEFAULT_PUZZLE_SCENE_STYLE,
    life_visual: _LifeBoardVisual,
    left: int | None = None,
) -> Tuple[int, int, int, int]:
    rows = len(option_specs[0]["grid"]) if option_specs else 0
    cols = len(option_specs[0]["grid"][0]) if option_specs else 0
    card_w, card_h = _life_option_card_size(rows=rows, cols=cols, render_params=render_params)
    gap = int(render_params.option_gap_px)
    count = len(option_specs)
    total_w = count * card_w + max(0, count - 1) * gap
    if left is None:
        left = int((render_params.canvas_width - total_w) // 2)
    else:
        left = int(left)
    for index, option in enumerate(option_specs):
        x0 = int(left + index * (card_w + gap))
        bbox = (x0, int(top), int(x0 + card_w), int(top + card_h))
        _draw_life_option_grid(
            draw,
            option_grid=option["grid"],
            bbox=bbox,
            label=str(option["label"]),
            render_params=render_params,
            style=style,
            life_visual=life_visual,
        )
        item_bboxes[str(option["option_id"])] = bbox
    return (left, int(top), int(left + total_w), int(top + card_h))


def _mark_region_bbox(
    *,
    cells: Sequence[Tuple[int, int]],
    grid_left: int,
    grid_top: int,
    cell_size: int,
    gap: int,
) -> Tuple[int, int, int, int]:
    boxes = [
        _cell_bbox(left=grid_left, top=grid_top, row=int(row), col=int(col), cell_size=cell_size, gap=gap)
        for row, col in cells
    ]
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _decorate_panel(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    scene_variant: str,
    radius: int = 22,
    border_width: int = 3,
    style: PuzzleSceneStyle = DEFAULT_PUZZLE_SCENE_STYLE,
    chrome_mode: str = "accent_frame",
) -> None:
    draw_puzzle_chrome_by_mode(
        draw,
        bbox=bbox,
        style=style,
        radius=int(radius),
        border_width=int(border_width),
        mode=str(chrome_mode),
    )


def _render_agent_scene(
    *,
    background: Image.Image,
    dataset: _AgentDataset,
    scene_variant: str,
    render_params: _RenderParams,
    style: PuzzleSceneStyle | None = None,
    style_meta: Mapping[str, Any] | None = None,
    board_style: str = "classic_grid",
) -> _RenderedScene:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    item_bboxes: Dict[str, Tuple[int, int, int, int]] = {}
    if style is None or style_meta is None:
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
    rows, cols = int(dataset.rows), int(dataset.cols)
    cell = int(render_params.cell_size_px)
    gap = int(render_params.grid_gap_px)
    grid_bbox = _grid_bbox(left=0, top=0, rows=rows, cols=cols, cell_size=cell, gap=gap)
    grid_w = grid_bbox[2] - grid_bbox[0]
    grid_h = grid_bbox[3] - grid_bbox[1]
    metrics = _agent_content_metrics(dataset=dataset, render_params=render_params)
    layout_rng = spawn_rng(instance_seed=int(render_params.layout_seed), namespace="agent_automaton_panel_origin")
    safe_margin = max(18, int(round(render_params.panel_padding_px * 0.85)))
    panel_w = int(metrics["panel_width_px"])
    panel_h = int(metrics["panel_height_px"])
    content_h = int(metrics["content_height_px"])
    min_panel_left = int(safe_margin)
    max_panel_left = int(render_params.canvas_width - panel_w - safe_margin)
    if max_panel_left >= min_panel_left:
        available_x = int(max_panel_left - min_panel_left)
        offset_x = layout_rng.randint(0, available_x) if available_x > 0 else 0
        panel_left = int(min_panel_left + offset_x)
    else:
        available_x = 0
        offset_x = 0
        panel_left = max(0, int((render_params.canvas_width - panel_w) // 2))
    min_panel_top = int(safe_margin)
    max_panel_top = int(render_params.canvas_height - content_h - safe_margin)
    if max_panel_top >= min_panel_top:
        available_y = int(max_panel_top - min_panel_top)
        offset_y = layout_rng.randint(0, available_y) if available_y > 0 else 0
        panel_top = int(min_panel_top + offset_y)
    else:
        available_y = 0
        offset_y = 0
        panel_top = max(0, int((render_params.canvas_height - content_h) // 2))
    grid_left = int(panel_left + int(render_params.panel_padding_px))
    grid_top = int(panel_top + int(render_params.panel_padding_px))
    panel_bbox = (
        grid_left - int(render_params.panel_padding_px),
        grid_top - int(render_params.panel_padding_px),
        grid_left + grid_w + int(render_params.panel_padding_px),
        grid_top + grid_h + int(render_params.panel_padding_px),
    )
    _decorate_panel(
        draw,
        bbox=panel_bbox,
        scene_variant=str(scene_variant),
        radius=int(render_params.panel_corner_radius_px),
        border_width=int(render_params.panel_border_width_px),
        style=style,
        chrome_mode=str(style_meta.get("panel_chrome_mode", "accent_frame")),
    )
    _draw_cell_grid(
        draw,
        grid=dataset.initial_grid,
        left=grid_left,
        top=grid_top,
        cell_size=cell,
        gap=gap,
        state_colors=style.state_colors[: dataset.state_count],
        item_bboxes=item_bboxes,
        item_prefix="source",
        target_cells=dataset.target_cells,
        draw_labels=bool(dataset.state_count == 3),
        style=style,
        cell_render_style=str(board_style),
    )
    item_bboxes["source_grid"] = _grid_bbox(left=grid_left, top=grid_top, rows=rows, cols=cols, cell_size=cell, gap=gap)
    start_bbox = _cell_bbox(left=grid_left, top=grid_top, row=dataset.start_row, col=dataset.start_col, cell_size=cell, gap=gap)
    item_bboxes["initial_agent"] = start_bbox
    if not dataset.option_specs:
        step_font = load_font(max(10, int(cell * 0.24)), bold=True)
        for trace in dataset.traces:
            bbox = _cell_bbox(left=grid_left, top=grid_top, row=trace.row, col=trace.col, cell_size=cell, gap=gap)
            cx = int((bbox[0] + bbox[2]) / 2)
            cy = int((bbox[1] + bbox[3]) / 2)
            radius = max(8, int(cell * 0.19))
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                fill=style.step_fill_rgb,
                outline=style.agent_rgb,
                width=2,
            )
            draw_centered_text(
                draw,
                text=str(int(trace.step)),
                center=(cx, cy),
                font=step_font,
                fill=style.text_rgb,
                stroke_fill=style.text_stroke_rgb,
                stroke_width=1,
            )
    _draw_agent_marker(
        draw,
        bbox=start_bbox,
        direction=dataset.start_direction,
        color=style.agent_rgb,
        inner_fill=style.agent_inner_rgb,
        width=int(render_params.arrow_width_px),
    )
    if dataset.target_cells:
        item_bboxes["marked_region"] = _mark_region_bbox(
            cells=dataset.target_cells,
            grid_left=grid_left,
            grid_top=grid_top,
            cell_size=cell,
            gap=gap,
        )
    option_bbox = (0, 0, 0, 0)
    if dataset.option_specs:
        option_bbox = _draw_agent_pose_options(
            draw,
            option_specs=dataset.option_specs,
            render_params=render_params,
            top=int(panel_bbox[3] + _agent_option_vertical_gap(render_params)),
            item_bboxes=item_bboxes,
            style=style,
            cell_render_style=str(board_style),
        )
    scene_bbox = (
        min(panel_bbox[0], option_bbox[0]) if option_bbox[2] else panel_bbox[0],
        panel_bbox[1],
        max(panel_bbox[2], option_bbox[2]) if option_bbox[2] else panel_bbox[2],
        max(panel_bbox[3], option_bbox[3]) if option_bbox[2] else panel_bbox[3],
    )
    entities = tuple(
        {
            "entity_id": key,
            "bbox_px": list(value),
            "entity_type": "automaton_item",
        }
        for key, value in sorted(item_bboxes.items())
    )
    layout_jitter = {
        "enabled": True,
        "layout_seed": int(render_params.layout_seed),
        "canvas_size_px": [int(render_params.canvas_width), int(render_params.canvas_height)],
        "content_size_px": [int(metrics["content_width_px"]), int(metrics["content_height_px"])],
        "panel_size_px": [int(panel_w), int(panel_h)],
        "panel_origin_px": [int(panel_bbox[0]), int(panel_bbox[1])],
        "grid_bbox_px": [int(value) for value in item_bboxes["source_grid"]],
        "option_bbox_px": [int(value) for value in option_bbox] if option_bbox[2] else [],
        "available_offset_px": [int(available_x), int(available_y)],
        "sampled_offset_px": [int(offset_x), int(offset_y)],
        "safe_margin_px": int(safe_margin),
        "option_vertical_gap_px": int(_agent_option_vertical_gap(render_params)),
    }
    return _RenderedScene(
        image=image,
        scene_bbox_px=scene_bbox,
        item_bboxes=item_bboxes,
        entities=entities,
        layout_jitter=layout_jitter,
        style_metadata=style_meta,
    )


def _render_life_scene(
    *,
    background: Image.Image,
    dataset: _LifeDataset,
    scene_variant: str,
    render_params: _RenderParams,
    style: PuzzleSceneStyle | None = None,
    style_meta: Mapping[str, Any] | None = None,
    life_visual: _LifeBoardVisual | None = None,
) -> _RenderedScene:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    item_bboxes: Dict[str, Tuple[int, int, int, int]] = {}
    if style is None or style_meta is None:
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
    if life_visual is None:
        life_visual = _LifeBoardVisual(
            board_style="classic_grid",
            cell_palette_id="mono_ink",
            dead_rgb=_LIFE_DEAD_RGB,
            alive_rgb=_LIFE_ALIVE_RGB,
            grid_rgb=style.grid_rgb,
            edge_rgb=style.grid_rgb,
            mark_rgb=style.mark_rgb,
            accent_rgb=style.panel_accent_rgb,
            board_style_probabilities={"classic_grid": 1.0},
            cell_palette_probabilities={"mono_ink": 1.0},
        )
    rows, cols = int(dataset.rows), int(dataset.cols)
    cell = int(render_params.cell_size_px)
    gap = int(render_params.grid_gap_px)
    grid_bbox = _grid_bbox(left=0, top=0, rows=rows, cols=cols, cell_size=cell, gap=gap)
    grid_w = grid_bbox[2] - grid_bbox[0]
    grid_h = grid_bbox[3] - grid_bbox[1]
    is_population_count = not bool(dataset.option_specs)
    metrics = _life_content_metrics(dataset=dataset, render_params=render_params)
    layout_rng = spawn_rng(instance_seed=int(render_params.layout_seed), namespace="life_automaton_panel_origin")
    safe_margin = max(18, int(round(render_params.panel_padding_px * 0.85)))
    content_w = int(metrics["content_width_px"])
    content_h = int(metrics["content_height_px"])
    panel_w = int(metrics["panel_width_px"])
    panel_h = int(metrics["panel_height_px"])
    min_content_left = int(safe_margin)
    max_content_left = int(render_params.canvas_width - content_w - safe_margin)
    if max_content_left >= min_content_left:
        available_x = int(max_content_left - min_content_left)
        offset_x = layout_rng.randint(0, available_x) if available_x > 0 else 0
        content_left = int(min_content_left + offset_x)
    else:
        available_x = 0
        offset_x = 0
        content_left = max(0, int((render_params.canvas_width - content_w) // 2))
    min_content_top = int(safe_margin)
    max_content_top = int(render_params.canvas_height - content_h - safe_margin)
    if max_content_top >= min_content_top:
        available_y = int(max_content_top - min_content_top)
        offset_y = layout_rng.randint(0, available_y) if available_y > 0 else 0
        content_top = int(min_content_top + offset_y)
    else:
        available_y = 0
        offset_y = 0
        content_top = max(0, int((render_params.canvas_height - content_h) // 2))
    panel_left = int(content_left + max(0, content_w - panel_w) // 2)
    panel_top = int(content_top)
    grid_left = int(panel_left + int(render_params.panel_padding_px))
    future_left = grid_left
    grid_top = int(panel_top + int(render_params.panel_padding_px))
    panel_bbox = (
        grid_left - int(render_params.panel_padding_px),
        grid_top - int(render_params.panel_padding_px),
        grid_left + grid_w + int(render_params.panel_padding_px),
        grid_top + grid_h + int(render_params.panel_padding_px),
    )
    _decorate_panel(
        draw,
        bbox=panel_bbox,
        scene_variant=str(scene_variant),
        style=style,
        chrome_mode=str(style_meta.get("panel_chrome_mode", "accent_frame")),
    )
    target_cells = dataset.target_cells if str(dataset.query_id) in {"marked_line_live_count", "marked_region_live_count"} else tuple()
    if is_population_count:
        _draw_life_cell_grid(
            draw,
            grid=dataset.future_grid,
            left=future_left,
            top=grid_top,
            cell_size=cell,
            gap=gap,
            item_bboxes=item_bboxes,
            item_prefix="future",
            target_cells=target_cells,
            style=style,
            life_visual=life_visual,
        )
        item_bboxes["future_grid"] = _grid_bbox(left=future_left, top=grid_top, rows=rows, cols=cols, cell_size=cell, gap=gap)
    else:
        _draw_life_cell_grid(
            draw,
            grid=dataset.initial_grid,
            left=grid_left,
            top=grid_top,
            cell_size=cell,
            gap=gap,
            item_bboxes=item_bboxes,
            item_prefix="source",
            target_cells=tuple(),
            style=style,
            life_visual=life_visual,
        )
        item_bboxes["source_grid"] = _grid_bbox(left=grid_left, top=grid_top, rows=rows, cols=cols, cell_size=cell, gap=gap)
    if target_cells:
        item_bboxes["marked_region"] = _mark_region_bbox(
            cells=target_cells,
            grid_left=future_left if is_population_count else grid_left,
            grid_top=grid_top,
            cell_size=cell,
            gap=gap,
        )
    option_bbox = (0, 0, 0, 0)
    if dataset.option_specs:
        option_left = int(content_left + max(0, content_w - int(metrics["option_width_px"])) // 2)
        option_bbox = _draw_life_options(
            draw,
            option_specs=dataset.option_specs,
            render_params=render_params,
            top=int(panel_bbox[3] + int(metrics["option_vertical_gap_px"])),
            item_bboxes=item_bboxes,
            style=style,
            life_visual=life_visual,
            left=option_left,
        )
    scene_bbox = (
        min(panel_bbox[0], option_bbox[0]) if option_bbox[2] else panel_bbox[0],
        panel_bbox[1],
        max(panel_bbox[2], option_bbox[2]) if option_bbox[2] else panel_bbox[2],
        max(panel_bbox[3], option_bbox[3]) if option_bbox[2] else panel_bbox[3],
    )
    entities = tuple(
        {
            "entity_id": key,
            "bbox_px": list(value),
            "entity_type": "automaton_item",
        }
        for key, value in sorted(item_bboxes.items())
    )
    return _RenderedScene(
        image=image,
        scene_bbox_px=scene_bbox,
        item_bboxes=item_bboxes,
        entities=entities,
        layout_jitter={
            "enabled": True,
            "mode": "safe_margin_free_area",
            "canvas_size_px": [int(render_params.canvas_width), int(render_params.canvas_height)],
            "content_size_px": [int(content_w), int(content_h)],
            "panel_size_px": [int(panel_w), int(panel_h)],
            "panel_origin_px": [int(panel_bbox[0]), int(panel_bbox[1])],
            "grid_bbox_px": [int(value) for value in (item_bboxes["future_grid"] if is_population_count else item_bboxes["source_grid"])],
            "option_bbox_px": [int(value) for value in option_bbox] if option_bbox[2] else [],
            "free_space_px": [
                int(render_params.canvas_width - content_w),
                int(render_params.canvas_height - content_h),
            ],
            "available_offset_px": [int(available_x), int(available_y)],
            "sampled_offset_px": [int(offset_x), int(offset_y)],
            "sampled_fraction": [
                round(float(offset_x) / float(available_x), 6) if available_x > 0 else 0.5,
                round(float(offset_y) / float(available_y), 6) if available_y > 0 else 0.5,
            ],
            "content_origin_px": [int(content_left), int(content_top)],
            "centered_content_origin_px": [
                int((render_params.canvas_width - content_w) // 2),
                int((render_params.canvas_height - content_h) // 2),
            ],
            "dx_dy_from_center_px": [
                int(content_left - int((render_params.canvas_width - content_w) // 2)),
                int(content_top - int((render_params.canvas_height - content_h) // 2)),
            ],
            "safe_margin_px": int(safe_margin),
            "option_vertical_gap_px": int(metrics["option_vertical_gap_px"]),
        },
        style_metadata=dict(style_meta),
    )


def _draw_turing_tape(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _TuringDataset,
    left: int,
    top: int,
    cell_size: int,
    gap: int,
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    style: PuzzleSceneStyle,
) -> Tuple[int, int, int, int]:
    font = load_font(max(16, int(cell_size * 0.42)), bold=True)
    small_font = load_font(max(11, int(cell_size * 0.22)), bold=True)
    symbol_to_color = {
        symbol: tuple(style.state_colors[index % len(style.state_colors)])
        for index, symbol in enumerate(dataset.symbols)
    }
    for index, symbol in enumerate(dataset.initial_tape):
        bbox = (
            int(left + index * (cell_size + gap)),
            int(top),
            int(left + index * (cell_size + gap) + cell_size),
            int(top + cell_size),
        )
        item_bboxes[f"tape_cell_{index}"] = bbox
        draw_puzzle_grid_cell(
            draw,
            bbox=bbox,
            fill=symbol_to_color[str(symbol)],
            style=style,
            outline=style.grid_rgb,
            width=2,
            selected=int(index) == int(dataset.start_head),
            selected_width=max(3, int(cell_size * 0.09)),
        )
        draw_centered_text(
            draw,
            text=str(symbol),
            center=((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0),
            font=font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
        draw_centered_text(
            draw,
            text=str(index + 1),
            center=((bbox[0] + bbox[2]) / 2.0, bbox[3] + max(11, int(cell_size * 0.18))),
            font=small_font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
    tape_bbox = _grid_bbox(left=left, top=top, rows=1, cols=int(dataset.tape_length), cell_size=cell_size, gap=gap)
    item_bboxes["source_tape"] = (int(tape_bbox[0]), int(tape_bbox[1]), int(tape_bbox[2]), int(tape_bbox[3] + max(18, int(cell_size * 0.30))))
    head_cell = _cell_bbox(left=left, top=top, row=0, col=int(dataset.start_head), cell_size=cell_size, gap=gap)
    head_cx = int((head_cell[0] + head_cell[2]) / 2)
    arrow_top = int(head_cell[1] - max(32, int(cell_size * 0.48)))
    arrow_end = int(head_cell[1] - 5)
    draw_arrow(
        draw,
        start=(head_cx, arrow_top),
        end=(head_cx, arrow_end),
        fill=style.agent_rgb,
        width=max(3, int(cell_size * 0.08)),
        head_length_px=max(12, int(cell_size * 0.22)),
        head_width_px=max(14, int(cell_size * 0.24)),
    )
    head_label_bbox = (
        int(head_cx - cell_size * 0.65),
        int(arrow_top - max(22, int(cell_size * 0.30))),
        int(head_cx + cell_size * 0.65),
        int(arrow_top - 2),
    )
    draw_rounded_rect(draw, head_label_bbox, radius=8, fill=style.panel_accent_rgb, outline=style.panel_border_rgb, width=1)
    draw_centered_text(
        draw,
        text=f"HEAD {dataset.start_state}",
        center=((head_label_bbox[0] + head_label_bbox[2]) / 2.0, (head_label_bbox[1] + head_label_bbox[3]) / 2.0),
        font=small_font,
        fill=style.text_rgb,
        stroke_fill=style.text_stroke_rgb,
        stroke_width=1,
    )
    item_bboxes["start_head"] = (
        int(min(head_label_bbox[0], head_cell[0])),
        int(head_label_bbox[1]),
        int(max(head_label_bbox[2], head_cell[2])),
        int(head_cell[1]),
    )
    return item_bboxes["source_tape"]


def _draw_turing_transition_table(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _TuringDataset,
    left: int,
    top: int,
    row_height: int,
    style: PuzzleSceneStyle,
) -> Tuple[int, int, int, int]:
    col_widths = (76, 70, 72, 70, 84)
    headers = ("State", "Read", "Write", "Move", "Next")
    table_width = int(sum(col_widths))
    header_font = load_font(max(12, int(row_height * 0.42)), bold=True)
    cell_font = load_font(max(12, int(row_height * 0.42)), bold=False)
    x = int(left)
    y = int(top)
    header_bbox = (x, y, x + table_width, y + row_height)
    draw_rounded_rect(draw, header_bbox, radius=10, fill=style.panel_accent_rgb, outline=style.panel_border_rgb, width=2)
    cursor = x
    for width, header in zip(col_widths, headers):
        draw_centered_text(
            draw,
            text=header,
            center=(cursor + width / 2, y + row_height / 2),
            font=header_font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
        cursor += int(width)
    used_keys = {(trace.state, trace.read_symbol) for trace in dataset.traces}
    for row_index, transition in enumerate(dataset.transitions, 1):
        y0 = int(top + row_index * row_height)
        row_bbox = (x, y0, x + table_width, y0 + row_height)
        row_fill = style.option_marker_fill_rgb if (transition.state, transition.read_symbol) in used_keys else style.option_fill_rgb
        draw.rectangle(row_bbox, fill=row_fill, outline=style.grid_rgb, width=1)
        values = (
            transition.state,
            transition.read_symbol,
            transition.write_symbol,
            transition.move,
            transition.next_state,
        )
        cursor = x
        for width, value in zip(col_widths, values):
            draw_centered_text(
                draw,
                text=str(value),
                center=(cursor + width / 2, y0 + row_height / 2),
                font=cell_font,
                fill=style.text_rgb,
                stroke_fill=style.text_stroke_rgb,
                stroke_width=1,
            )
            cursor += int(width)
    return (x, y, x + table_width, int(top + (len(dataset.transitions) + 1) * row_height))


def _render_turing_scene(
    *,
    background: Image.Image,
    dataset: _TuringDataset,
    scene_variant: str,
    render_params: _RenderParams,
    style: PuzzleSceneStyle | None = None,
    style_meta: Mapping[str, Any] | None = None,
) -> _RenderedScene:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    item_bboxes: Dict[str, Tuple[int, int, int, int]] = {}
    if style is None or style_meta is None:
        style, style_meta = _resolve_turing_style(scene_variant=str(scene_variant), render_params=render_params)
    cell = max(38, min(60, int(render_params.cell_size_px)))
    gap = max(2, int(render_params.grid_gap_px))
    tape_width = int(dataset.tape_length * cell + max(0, dataset.tape_length - 1) * gap)
    tape_left = int((render_params.canvas_width - tape_width) // 2)
    tape_top = max(96, int(render_params.panel_padding_px) + 72)
    machine_panel = (
        int(tape_left - render_params.panel_padding_px),
        int(tape_top - render_params.panel_padding_px - 62),
        int(tape_left + tape_width + render_params.panel_padding_px),
        int(tape_top + cell + render_params.panel_padding_px + 46),
    )
    _decorate_panel(
        draw,
        bbox=machine_panel,
        scene_variant=str(scene_variant),
        radius=int(render_params.panel_corner_radius_px),
        border_width=int(render_params.panel_border_width_px),
        style=style,
        chrome_mode=str(style_meta.get("panel_chrome_mode", "accent_frame")),
    )
    _draw_turing_tape(
        draw,
        dataset=dataset,
        left=tape_left,
        top=tape_top,
        cell_size=cell,
        gap=gap,
        item_bboxes=item_bboxes,
        style=style,
    )
    chip_font = load_font(max(13, int(render_params.small_font_size_px)), bold=True)
    chip_y = int(machine_panel[3] - render_params.panel_padding_px - 22)
    chips = (
        f"steps {dataset.steps}",
        f"count {dataset.query_symbol}",
    )
    chip_x = int(machine_panel[0] + render_params.panel_padding_px)
    query_chip_bbox = (0, 0, 0, 0)
    for chip in chips:
        chip_w = max(82, 16 + len(chip) * max(8, int(render_params.small_font_size_px * 0.52)))
        bbox = (chip_x, chip_y, int(chip_x + chip_w), int(chip_y + 28))
        draw_rounded_rect(draw, bbox, radius=10, fill=style.step_fill_rgb, outline=style.panel_border_rgb, width=1)
        draw_centered_text(
            draw,
            text=chip,
            center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
            font=chip_font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
        if chip.startswith("count "):
            query_chip_bbox = bbox
        chip_x += int(chip_w + 12)
    item_bboxes["machine_panel"] = machine_panel
    item_bboxes["query_symbol"] = query_chip_bbox

    row_height = max(28, min(36, int(render_params.cell_size_px * 0.58)))
    table_width = 372
    table_left = int((render_params.canvas_width - table_width) // 2)
    table_top = int(machine_panel[3] + 34)
    table_bbox_raw = _draw_turing_transition_table(
        draw,
        dataset=dataset,
        left=table_left,
        top=table_top,
        row_height=row_height,
        style=style,
    )
    table_panel = (
        int(table_bbox_raw[0] - 18),
        int(table_bbox_raw[1] - 18),
        int(table_bbox_raw[2] + 18),
        int(table_bbox_raw[3] + 18),
    )
    table_crop = image.crop(table_bbox_raw)
    _decorate_panel(
        draw,
        bbox=table_panel,
        scene_variant=str(scene_variant),
        radius=int(render_params.panel_corner_radius_px),
        border_width=2,
        style=style,
        chrome_mode="plain_panel",
    )
    image.paste(table_crop, table_bbox_raw)
    item_bboxes["transition_table"] = table_panel
    scene_bbox = (
        int(min(machine_panel[0], table_panel[0])),
        int(min(machine_panel[1], table_panel[1])),
        int(max(machine_panel[2], table_panel[2])),
        int(max(machine_panel[3], table_panel[3])),
    )
    entities = tuple(
        {
            "entity_id": key,
            "bbox_px": list(value),
            "entity_type": "turing_machine_item",
        }
        for key, value in sorted(item_bboxes.items())
    )
    return _RenderedScene(
        image=image,
        scene_bbox_px=scene_bbox,
        item_bboxes=item_bboxes,
        entities=entities,
        layout_jitter={
            "enabled": False,
            "reason": "single_tape_and_table_layout",
            "canvas_size_px": [int(render_params.canvas_width), int(render_params.canvas_height)],
            "tape_cell_size_px": int(cell),
            "transition_row_height_px": int(row_height),
        },
        style_metadata=dict(style_meta),
    )


def _build_prompt(
    *,
    prompt_defaults: Mapping[str, Any],
    scene_variant: str,
    query_id: str,
    steps: int,
    instance_seed: int,
    task_id: str,
    task_group: str = "automaton",
    rule_variant: str | None = None,
    extra_slots: Mapping[str, Any] | None = None,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        f"object_description_{scene_variant}",
        f"query_instruction_{query_id}",
        "json_output_contract",
        "json_output_contract_answer_only",
        "evidence_hint",
        "answer_hint",
        "json_example",
        "json_example_answer_only",
    )
    if rule_variant is not None:
        required_keys = (*required_keys, f"rule_instruction_{rule_variant}")
    values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {task_id}")
    slots = {
        "object_description": str(values[f"object_description_{scene_variant}"]),
        "query_instruction": str(values[f"query_instruction_{query_id}"]),
        "steps": int(steps),
        "json_output_contract": str(values["json_output_contract"]),
        "json_output_contract_answer_only": str(values["json_output_contract_answer_only"]),
        "evidence_hint": str(values["evidence_hint"]),
        "answer_hint": str(values["answer_hint"]),
        "json_example": str(values["json_example"]),
        "json_example_answer_only": str(values["json_example_answer_only"]),
    }
    if rule_variant is not None:
        slots["rule_instruction"] = str(values[f"rule_instruction_{rule_variant}"])
    if isinstance(extra_slots, Mapping):
        slots.update({str(key): value for key, value in extra_slots.items()})
    selection = render_task_prompt_variants(
        domain="puzzles",
        task_group=str(task_group),
        bundle_id=str(values["bundle_id"]),
        scene_key=str(values["scene_key"]),
        task_key=str(values["task_key"]),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    artifacts = build_prompt_trace_artifacts(selection)
    return str(artifacts.prompt), dict(artifacts.prompt_variants), {
        "prompt_variant": dict(artifacts.prompt_variant),
        "prompt_variant_active_key": str(artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(artifacts.prompt_variants_for_trace),
        "bundle_id": str(values["bundle_id"]),
    }


def _common_trace(
    *,
    scene_id: str,
    task_id: str,
    query_id: str,
    query_probabilities: Mapping[str, float],
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    prompt_meta: Mapping[str, Any],
    render_params: _RenderParams,
    rendered_scene: _RenderedScene,
    background_meta: Mapping[str, Any],
    post_noise_meta: Mapping[str, Any],
    evidence_type: str,
    evidence_value: Any,
    answer_value: Any,
    execution_trace: Mapping[str, Any],
) -> Dict[str, Any]:
    query_params = {
        "query_id": str(query_id),
        "query_id_probabilities": {str(key): float(value) for key, value in query_probabilities.items()},
        "scene_id": str(scene_id),
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": {str(key): float(value) for key, value in scene_variant_probabilities.items()},
    }
    witness_symbolic, projected_evidence = _evidence_trace_payload(
        evidence_type=str(evidence_type),
        evidence_value=evidence_value,
    )
    return {
        "scene_ir": {
            "scene_kind": str(scene_id),
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": dict(query_params),
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
            "scene_id": str(scene_id),
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "coord_space": "pixel",
            "scene_variant": str(scene_variant),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "scene_bbox_px": [int(value) for value in rendered_scene.scene_bbox_px],
            "render_params": {
                "cell_size_px": int(render_params.cell_size_px),
                "grid_gap_px": int(render_params.grid_gap_px),
                "option_card_width_px": int(render_params.option_card_width_px),
                "option_card_height_px": int(render_params.option_card_height_px),
                "option_grid_cell_px": int(render_params.option_grid_cell_px),
            },
            "unit_size_jitter": dict(render_params.unit_size_jitter),
            "layout_jitter": dict(rendered_scene.layout_jitter),
            "scene_style": dict(rendered_scene.style_metadata),
        },
        "render_map": with_puzzle_unit_size_jitter({
            "image_id": "img0",
            "scene_bbox_px": [int(value) for value in rendered_scene.scene_bbox_px],
            "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bboxes.items()},
            "evidence_source": "item_bboxes_px",
            "layout_jitter": dict(rendered_scene.layout_jitter),
            "scene_style": dict(rendered_scene.style_metadata),
        }, render_params.unit_size_jitter),
        "execution_trace": {
            **dict(query_params),
            "question_format": str(query_id),
            "task_id": str(task_id),
            "answer_value": answer_value,
            **dict(execution_trace),
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_evidence": dict(projected_evidence),
    }


def _round_bboxes(evidence_projection: Mapping[str, Any]) -> List[List[float]]:
    return [[round(float(value), 3) for value in bbox] for bbox in evidence_projection.get("bbox_set", [])]


def _round_keyed_bboxes(evidence_projection: Mapping[str, Any]) -> Dict[str, List[float]]:
    return {
        str(key): [round(float(value), 3) for value in bbox]
        for key, bbox in dict(evidence_projection.get("keyed_bbox_map", {})).items()
    }


def _evidence_trace_payload(*, evidence_type: str, evidence_value: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if str(evidence_type) == "keyed_bbox_map":
        keyed = {
            str(key): [round(float(value), 3) for value in bbox]
            for key, bbox in dict(evidence_value).items()
        }
        return (
            {"type": "keyed_bbox_map", "value": dict(keyed)},
            {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(keyed),
                "pixel_keyed_bbox_map": dict(keyed),
                "value": dict(keyed),
            },
        )
    bbox_set = [[round(float(value), 3) for value in bbox] for bbox in list(evidence_value)]
    return (
        {"type": "bbox_set", "value": [list(bbox) for bbox in bbox_set]},
        {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in bbox_set],
            "pixel_bbox_set": [list(bbox) for bbox in bbox_set],
            "value": [list(bbox) for bbox in bbox_set],
        },
    )


class _BaseAutomatonTask:
    domain = "puzzles"
    task_group = "automaton"
    default_dataset_enabled = True

    def _scene_variant(
        self,
        *,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
    ) -> Tuple[str, Dict[str, float]]:
        return _resolve_axis(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_variants=_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )


@register_task
class PuzzlesAutomatonAgentFinalPoseLabelTask(_BaseAutomatonTask):
    """Choose the final agent pose after simulating a turning automaton."""

    task_id = AGENT_FINAL_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(self.task_id)
        query_id, query_probabilities = _resolve_query(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_queries=AGENT_FINAL_QUERY_IDS,
        )
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        dataset = _build_agent_dataset(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, query_id=query_id)
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _fit_agent_render_params(dataset=dataset, render_params=render_params)
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
        agent_board_style, agent_board_probs = _resolve_agent_board_style(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id)
        style_meta = _style_meta_with_font(style_meta, render_params)
        style_meta = _style_meta_with_agent_board(style_meta, board_style=agent_board_style, board_style_probabilities=agent_board_probs)
        background, background_meta = make_puzzle_scene_background(
            canvas_width=render_params.canvas_width,
            canvas_height=render_params.canvas_height,
            style=style,
        )
        with temporary_default_font_family(render_params.font_family):
            rendered = _render_agent_scene(
                background=background,
                dataset=dataset,
                scene_variant=scene_variant,
                render_params=render_params,
                style=style,
                style_meta=style_meta,
                board_style=agent_board_style,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            scene_variant=scene_variant,
            query_id=query_id,
            steps=dataset.steps,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        correct_option = next(option for option in dataset.option_specs if bool(option["is_correct"]))
        evidence_role_item_ids = {
            "start_marker": "initial_agent",
            "selected_option": str(correct_option["option_id"]),
        }
        evidence_keyed_bboxes = _round_keyed_bboxes(
            projected_puzzle_keyed_bbox_evidence(rendered.item_bboxes, evidence_role_item_ids)
        )
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        evidence_gt = TypedValue(type="keyed_bbox_map", value=dict(evidence_keyed_bboxes))
        execution_trace = {
            "rule_variant": str(dataset.rule_variant),
            "state_count": int(dataset.state_count),
            "steps": int(dataset.steps),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "initial_grid": [list(row) for row in dataset.initial_grid],
            "final_grid": [list(row) for row in dataset.final_grid],
            "start_pose": {"row": int(dataset.start_row), "col": int(dataset.start_col), "direction": _DIRECTIONS[dataset.start_direction]},
            "final_pose": {"row": int(dataset.final_row), "col": int(dataset.final_col), "direction": _DIRECTIONS[dataset.final_direction]},
            "option_specs": [dict(option) for option in dataset.option_specs],
            "supporting_item_ids": list(evidence_role_item_ids.values()),
            "supporting_item_ids_by_role": dict(evidence_role_item_ids),
        }
        trace_payload = _common_trace(
            scene_id=AGENT_SCENE_ID,
            task_id=self.task_id,
            query_id=query_id,
            query_probabilities=query_probabilities,
            scene_variant=scene_variant,
            scene_variant_probabilities=scene_probs,
            prompt_meta=prompt_meta,
            render_params=render_params,
            rendered_scene=rendered,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            evidence_type="keyed_bbox_map",
            evidence_value=evidence_keyed_bboxes,
            answer_value=str(dataset.answer_label),
            execution_trace=execution_trace,
        )
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": normalize_int_with_bounds(dataset.rows * dataset.cols, [36, 81]),
                "reasoning_load": normalize_int_with_bounds(dataset.steps, [5, 14]),
                "scene_variant_load": 0.20 if scene_variant == "clean_grid" else 0.30,
            },
        )
        return TaskOutput(
            prompt=prompt,
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=AGENT_SCENE_ID,
            query_id=query_id,
            prompt_variants=prompt_variants,
        )


@register_task
class PuzzlesAutomatonAgentCellFlipCountTask(_BaseAutomatonTask):
    """Count how often a marked cell or region changes state under agent motion."""

    task_id = AGENT_FLIP_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(self.task_id)
        query_id, query_probabilities = _resolve_query(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_queries=AGENT_FLIP_QUERY_IDS,
        )
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        rule_variant, rule_probs = _resolve_axis(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_variants=("binary_rule", "three_state_rule"),
            explicit_key="rule_variant",
            weights_key="rule_variant_weights",
            balance_flag_key="balanced_rule_variant_sampling",
            axis_namespace="rule_variant",
        )
        dataset = _build_agent_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            query_id=query_id,
            rule_variant=rule_variant,
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _fit_agent_render_params(dataset=dataset, render_params=render_params)
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
        agent_board_style, agent_board_probs = _resolve_agent_board_style(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id)
        style_meta = _style_meta_with_font(style_meta, render_params)
        style_meta = _style_meta_with_agent_board(style_meta, board_style=agent_board_style, board_style_probabilities=agent_board_probs)
        background, background_meta = make_puzzle_scene_background(
            canvas_width=render_params.canvas_width,
            canvas_height=render_params.canvas_height,
            style=style,
        )
        with temporary_default_font_family(render_params.font_family):
            rendered = _render_agent_scene(
                background=background,
                dataset=dataset,
                scene_variant=scene_variant,
                render_params=render_params,
                style=style,
                style_meta=style_meta,
                board_style=agent_board_style,
            )
        image, post_noise_meta = apply_post_image_noise(rendered.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            scene_variant=scene_variant,
            query_id=query_id,
            steps=dataset.steps,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            rule_variant=rule_variant,
            extra_slots={
                "target_state_label": _state_label(state=int(dataset.target_state or 0), state_count=int(dataset.state_count)),
            }
            if query_id == "target_state_flip_count"
            else None,
        )
        evidence_ids = ["marked_region"]
        evidence_bboxes = _round_bboxes(projected_puzzle_bbox_evidence(rendered.item_bboxes, evidence_ids))
        answer_gt = TypedValue(type="integer", value=int(dataset.flip_count))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        execution_trace = {
            "rule_variant": str(rule_variant),
            "rule_variant_probabilities": dict(rule_probs),
            "state_count": int(dataset.state_count),
            "steps": int(dataset.steps),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "initial_grid": [list(row) for row in dataset.initial_grid],
            "target_cells": [[int(row), int(col)] for row, col in dataset.target_cells],
            "target_state": (int(dataset.target_state) if dataset.target_state is not None else None),
            "target_state_label": (
                _state_label(state=int(dataset.target_state), state_count=int(dataset.state_count))
                if dataset.target_state is not None
                else ""
            ),
            "flip_count": int(dataset.flip_count),
            "path_trace": [
                {"step": trace.step, "row": trace.row, "col": trace.col, "state_before": trace.state_before, "state_after": trace.state_after}
                for trace in dataset.traces
            ],
            "supporting_item_ids": list(evidence_ids),
        }
        trace_payload = _common_trace(
            scene_id=AGENT_SCENE_ID,
            task_id=self.task_id,
            query_id=query_id,
            query_probabilities=query_probabilities,
            scene_variant=scene_variant,
            scene_variant_probabilities=scene_probs,
            prompt_meta=prompt_meta,
            render_params=render_params,
            rendered_scene=rendered,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            evidence_type="bbox_set",
            evidence_value=evidence_bboxes,
            answer_value=int(dataset.flip_count),
            execution_trace=execution_trace,
        )
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": normalize_int_with_bounds(dataset.rows * dataset.cols, [36, 81]),
                "reasoning_load": normalize_int_with_bounds(dataset.steps + len(dataset.target_cells), [6, 24]),
                "scene_variant_load": 0.20 if scene_variant == "clean_grid" else 0.30,
            },
        )
        return TaskOutput(
            prompt=prompt,
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=AGENT_SCENE_ID,
            query_id=query_id,
            prompt_variants=prompt_variants,
        )


@register_task
class PuzzlesAutomatonLifeFutureGridLabelTask(_BaseAutomatonTask):
    """Choose the future grid after one or two Life updates."""

    task_id = LIFE_GRID_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(self.task_id)
        query_id, query_probabilities = _resolve_query(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, supported_queries=LIFE_GRID_QUERY_IDS)
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        dataset = _build_life_dataset(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, query_id=query_id)
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _fit_life_render_params(dataset=dataset, render_params=render_params)
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
        life_visual = _resolve_life_board_visual(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id)
        style_meta = _style_meta_with_font(style_meta, render_params)
        style_meta = _style_meta_with_life_board(style_meta, life_visual=life_visual)
        background, background_meta = make_puzzle_scene_background(canvas_width=render_params.canvas_width, canvas_height=render_params.canvas_height, style=style)
        with temporary_default_font_family(render_params.font_family):
            rendered = _render_life_scene(background=background, dataset=dataset, scene_variant=scene_variant, render_params=render_params, style=style, style_meta=style_meta, life_visual=life_visual)
        image, post_noise_meta = apply_post_image_noise(rendered.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(prompt_defaults=prompt_defaults, scene_variant=scene_variant, query_id=query_id, steps=dataset.steps, instance_seed=int(instance_seed), task_id=self.task_id)
        correct_option = next(option for option in dataset.option_specs if bool(option["is_correct"]))
        evidence_role_item_ids = {
            "source_grid": "source_grid",
            "selected_option": str(correct_option["option_id"]),
        }
        evidence_keyed_bboxes = _round_keyed_bboxes(
            projected_puzzle_keyed_bbox_evidence(rendered.item_bboxes, evidence_role_item_ids)
        )
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        evidence_gt = TypedValue(type="keyed_bbox_map", value=dict(evidence_keyed_bboxes))
        execution_trace = {
            "steps": int(dataset.steps),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "initial_grid": [list(row) for row in dataset.initial_grid],
            "future_grid": [list(row) for row in dataset.future_grid],
            "option_specs": [dict(option) for option in dataset.option_specs],
            "supporting_item_ids": list(evidence_role_item_ids.values()),
            "supporting_item_ids_by_role": dict(evidence_role_item_ids),
        }
        trace_payload = _common_trace(scene_id=LIFE_SCENE_ID, task_id=self.task_id, query_id=query_id, query_probabilities=query_probabilities, scene_variant=scene_variant, scene_variant_probabilities=scene_probs, prompt_meta=prompt_meta, render_params=render_params, rendered_scene=rendered, background_meta=background_meta, post_noise_meta=post_noise_meta, evidence_type="keyed_bbox_map", evidence_value=evidence_keyed_bboxes, answer_value=str(dataset.answer_label), execution_trace=execution_trace)
        complexity = build_puzzle_complexity(weights=complexity_weights, components={"visual_scan": normalize_int_with_bounds(dataset.rows * dataset.cols, [25, 64]), "reasoning_load": normalize_int_with_bounds(dataset.steps, [1, 3]), "scene_variant_load": 0.20 if scene_variant == "clean_grid" else 0.30})
        return TaskOutput(prompt=prompt, answer_gt=answer_gt, evidence_gt=evidence_gt, image=image, image_id="img0", trace_payload=trace_payload, complexity=complexity, task_versions=default_task_versions(), scene_id=LIFE_SCENE_ID, query_id=query_id, prompt_variants=prompt_variants)


@register_task
class PuzzlesAutomatonLifePopulationCountTask(_BaseAutomatonTask):
    """Count live cells after Life updates."""

    task_id = LIFE_POP_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(self.task_id)
        query_id, query_probabilities = _resolve_query(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, supported_queries=LIFE_POP_QUERY_IDS)
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        dataset = _build_life_dataset(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, query_id=query_id)
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _fit_life_render_params(dataset=dataset, render_params=render_params)
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
        life_visual = _resolve_life_board_visual(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id)
        style_meta = _style_meta_with_font(style_meta, render_params)
        style_meta = _style_meta_with_life_board(style_meta, life_visual=life_visual)
        background, background_meta = make_puzzle_scene_background(canvas_width=render_params.canvas_width, canvas_height=render_params.canvas_height, style=style)
        with temporary_default_font_family(render_params.font_family):
            rendered = _render_life_scene(background=background, dataset=dataset, scene_variant=scene_variant, render_params=render_params, style=style, style_meta=style_meta, life_visual=life_visual)
        image, post_noise_meta = apply_post_image_noise(rendered.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(prompt_defaults=prompt_defaults, scene_variant=scene_variant, query_id=query_id, steps=dataset.steps, instance_seed=int(instance_seed), task_id=self.task_id)
        evidence_ids = ["marked_region"] if query_id in {"marked_line_live_count", "marked_region_live_count"} else ["source_grid"]
        evidence_bboxes = _round_bboxes(projected_puzzle_bbox_evidence(rendered.item_bboxes, evidence_ids))
        answer_gt = TypedValue(type="integer", value=int(dataset.live_count))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        execution_trace = {
            "steps": int(dataset.steps),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "initial_grid": [list(row) for row in dataset.initial_grid],
            "future_grid": [list(row) for row in dataset.future_grid],
            "target_cells": [[int(row), int(col)] for row, col in dataset.target_cells],
            "live_count": int(dataset.live_count),
            "supporting_item_ids": list(evidence_ids),
        }
        trace_payload = _common_trace(scene_id=LIFE_SCENE_ID, task_id=self.task_id, query_id=query_id, query_probabilities=query_probabilities, scene_variant=scene_variant, scene_variant_probabilities=scene_probs, prompt_meta=prompt_meta, render_params=render_params, rendered_scene=rendered, background_meta=background_meta, post_noise_meta=post_noise_meta, evidence_type="bbox_set", evidence_value=evidence_bboxes, answer_value=int(dataset.live_count), execution_trace=execution_trace)
        complexity = build_puzzle_complexity(weights=complexity_weights, components={"visual_scan": normalize_int_with_bounds(dataset.rows * dataset.cols, [25, 64]), "reasoning_load": normalize_int_with_bounds(dataset.steps + len(dataset.target_cells), [2, 20]), "scene_variant_load": 0.20 if scene_variant == "clean_grid" else 0.30})
        return TaskOutput(prompt=prompt, answer_gt=answer_gt, evidence_gt=evidence_gt, image=image, image_id="img0", trace_payload=trace_payload, complexity=complexity, task_versions=default_task_versions(), scene_id=LIFE_SCENE_ID, query_id=query_id, prompt_variants=prompt_variants)


@register_task
class PuzzlesAutomatonTuringWrittenSymbolCountTask(_BaseAutomatonTask):
    """Count a queried tape symbol after fixed-step Turing-style transitions."""

    task_id = TURING_SYMBOL_COUNT_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(self.task_id)
        query_id, query_probabilities = _resolve_query(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_queries=TURING_QUERY_IDS,
        )
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        dataset = _build_turing_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            query_id=query_id,
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        style, style_meta = _resolve_turing_style(scene_variant=str(scene_variant), render_params=render_params)
        background, background_meta = make_puzzle_scene_background(
            canvas_width=render_params.canvas_width,
            canvas_height=render_params.canvas_height,
            style=style,
        )
        rendered = _render_turing_scene(
            background=background,
            dataset=dataset,
            scene_variant=scene_variant,
            render_params=render_params,
            style=style,
            style_meta=style_meta,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            scene_variant=scene_variant,
            query_id=query_id,
            steps=dataset.steps,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            extra_slots={
                "query_symbol": str(dataset.query_symbol),
                "start_state": str(dataset.start_state),
            },
        )
        evidence_ids = ["machine_panel", "transition_table"]
        evidence_bboxes = _round_bboxes(projected_puzzle_bbox_evidence(rendered.item_bboxes, evidence_ids))
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_count))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        execution_trace = {
            "steps": int(dataset.steps),
            "tape_length": int(dataset.tape_length),
            "symbol_count": int(dataset.symbol_count),
            "symbols": list(dataset.symbols),
            "query_symbol": str(dataset.query_symbol),
            "start_state": str(dataset.start_state),
            "start_head": int(dataset.start_head),
            "initial_tape": list(dataset.initial_tape),
            "final_tape": list(dataset.final_tape),
            "transitions": [
                {
                    "state": transition.state,
                    "read_symbol": transition.read_symbol,
                    "write_symbol": transition.write_symbol,
                    "move": transition.move,
                    "next_state": transition.next_state,
                }
                for transition in dataset.transitions
            ],
            "step_trace": [
                {
                    "step": trace.step,
                    "state": trace.state,
                    "head_position": trace.head_position,
                    "read_symbol": trace.read_symbol,
                    "write_symbol": trace.write_symbol,
                    "move": trace.move,
                    "next_state": trace.next_state,
                }
                for trace in dataset.traces
            ],
            "answer_count": int(dataset.answer_count),
            "supporting_item_ids": list(evidence_ids),
        }
        trace_payload = _common_trace(
            scene_id=TURING_SCENE_ID,
            task_id=self.task_id,
            query_id=query_id,
            query_probabilities=query_probabilities,
            scene_variant=scene_variant,
            scene_variant_probabilities=scene_probs,
            prompt_meta=prompt_meta,
            render_params=render_params,
            rendered_scene=rendered,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            evidence_type="bbox_set",
            evidence_value=evidence_bboxes,
            answer_value=int(dataset.answer_count),
            execution_trace=execution_trace,
        )
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": normalize_int_with_bounds(dataset.tape_length + len(dataset.transitions), [14, 24]),
                "reasoning_load": normalize_int_with_bounds(dataset.steps + dataset.symbol_count, [5, 9]),
                "scene_variant_load": 0.20 if scene_variant == "clean_grid" else 0.30,
            },
        )
        return TaskOutput(
            prompt=prompt,
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=TURING_SCENE_ID,
            query_id=query_id,
            prompt_variants=prompt_variants,
        )


__all__ = [
    "PuzzlesAutomatonAgentCellFlipCountTask",
    "PuzzlesAutomatonAgentFinalPoseLabelTask",
    "PuzzlesAutomatonLifeFutureGridLabelTask",
    "PuzzlesAutomatonLifePopulationCountTask",
    "PuzzlesAutomatonTuringWrittenSymbolCountTask",
]
