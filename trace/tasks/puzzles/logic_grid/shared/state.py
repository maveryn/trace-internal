"""Passive state records for the logic-grid puzzle scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from PIL import Image

from trace.tasks.puzzles.shared.symbol_rendering import PUZZLE_OBJECT_TYPES


DOMAIN = "puzzles"
SCENE_ID = "logic_grid"
SCENE_VARIANTS: Tuple[str, ...] = ("logic_strip", "logic_card", "logic_outline")
LOGIC_GRID_OBJECT_TYPES: Tuple[str, ...] = (*PUZZLE_OBJECT_TYPES, "pentagon")

ROW_AXIS = "row"
COLUMN_AXIS = "column"
ROW_AND_COLUMN_AXIS = "row_and_column"
SUPPORTED_UNIQUENESS_AXES: Tuple[str, ...] = (ROW_AXIS, COLUMN_AXIS)


@dataclass(frozen=True)
class LogicGridDefaults:
    """Stable code fallbacks for logic-grid scene generation and rendering."""

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


@dataclass(frozen=True)
class LogicGridRenderParams:
    """Resolved render parameters for one option-based logic puzzle."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    cell_size_px: int
    cell_gap_px: int
    board_panel_padding_px: int
    board_to_options_gap_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_symbol_box_size_px: int
    option_label_gap_px: int
    slot_corner_radius_px: int
    border_width_px: int
    panel_corner_radius_px: int
    value_font_size_px: int
    option_label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    cell_fill_rgb: Tuple[int, int, int]
    unknown_cell_fill_rgb: Tuple[int, int, int]
    option_panel_fill_rgb: Tuple[int, int, int]
    option_symbol_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    accent_color_rgb: Tuple[int, int, int]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class LogicGridDataset:
    """Generated symbolic grid plus answer-option records."""

    grid_rows: List[List[Dict[str, Any]]]
    board_values: List[List[str]]
    symbol_pool: List[str]
    marked_cell_id: str
    marked_row_index: int
    marked_col_index: int
    answer_object_type: str
    answer_option_label: str
    correct_option_index: int
    correct_option_panel_id: str
    option_specs: List[Dict[str, Any]]
    option_labels: List[str]
    option_count: int
    board_size: int
    board_size_range: List[int]
    cell_count: int
    cell_count_range: List[int]
    solver_trace: Dict[str, Any]
    extra_trace: Dict[str, Any]


@dataclass(frozen=True)
class RenderedLogicGridScene:
    """Rendered logic-grid image plus traced board/option geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    board_bbox_px: List[float]
    cell_bbox_map: Dict[str, List[float]]
    option_panel_bbox_map: Dict[str, List[float]]


DEFAULTS = LogicGridDefaults()
