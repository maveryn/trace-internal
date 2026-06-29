"""Passive constants and dataclasses for polyomino missing-piece puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from PIL import Image


DOMAIN = "puzzles"
SCENE_ID = "polyomino_missing"
PROMPT_BUNDLE_ID = "puzzles_polyomino_missing_v1"
PROMPT_SCENE_KEY = "polyomino_missing"

SCENE_VARIANTS: Tuple[str, ...] = (
    "polyomino_strip",
    "polyomino_card",
    "polyomino_outline",
)

Cells = Tuple[Tuple[int, int], ...]
Cell = Tuple[int, int]


@dataclass(frozen=True)
class PolyominoMissingDefaults:
    """Stable code fallbacks for polyomino missing-piece sampling."""

    complement_option_count_min: int = 4
    complement_option_count_max: int = 6
    complement_target_width_min: int = 4
    complement_target_width_max: int = 6
    complement_target_height_min: int = 4
    complement_target_height_max: int = 6
    complement_cutout_cell_count_min: int = 3
    complement_cutout_cell_count_max: int = 7
    complement_transform_allowed_cutout_cell_count_min: int = 5
    complement_shape_bbox_max_dim: int = 6
    board_cell_size_px: int = 36
    board_cell_gap_px: int = 2
    target_cell_size_px: int = 38
    target_cell_gap_px: int = 4


@dataclass(frozen=True)
class PolyominoOptionRenderDefaults:
    """Stable fallback defaults for polyomino option-panel rendering."""

    canvas_width: int = 1200
    canvas_height: int = 980
    scene_margin_left_px: int = 64
    scene_margin_right_px: int = 64
    scene_margin_top_px: int = 56
    scene_margin_bottom_px: int = 56
    piece_to_options_gap_px: int = 56
    piece_panel_padding_px: int = 24
    option_panel_width_px: int = 176
    option_panel_height_px: int = 204
    option_gap_px: int = 22
    option_row_gap_px: int = 22
    option_shape_box_size_px: int = 126
    option_label_gap_px: int = 16
    shape_cell_size_px: int = 22
    shape_cell_gap_px: int = 4
    panel_corner_radius_px: int = 28
    cell_corner_radius_px: int = 8
    border_width_px: int = 3
    option_label_font_size_px: int = 30


@dataclass(frozen=True)
class PolyominoOptionRenderParams:
    """Resolved rendering knobs for polyomino target and option panels."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    piece_to_options_gap_px: int
    piece_panel_padding_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_row_gap_px: int
    option_shape_box_size_px: int
    option_label_gap_px: int
    shape_cell_size_px: int
    shape_cell_gap_px: int
    panel_corner_radius_px: int
    cell_corner_radius_px: int
    border_width_px: int
    option_label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    option_panel_fill_rgb: Tuple[int, int, int]
    option_shape_fill_rgb: Tuple[int, int, int]
    shape_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class CustomRenderParams:
    """Resolved custom rendering knobs for the target grid."""

    board_cell_size_px: int
    board_cell_gap_px: int
    target_cell_size_px: int
    target_cell_gap_px: int
    unit_size_jitter: Dict[str, Any]
    highlight_fill_rgb: Tuple[int, int, int]
    empty_cell_rgb: Tuple[int, int, int]
    board_grid_rgb: Tuple[int, int, int]
    marked_cell_rgb: Tuple[int, int, int]
    target_cell_rgb: Tuple[int, int, int]
    missing_cell_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedPolyominoMissingScene:
    """Rendered polyomino missing-piece scene with traced geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    bbox_map: Dict[str, List[float]]


DEFAULTS = PolyominoMissingDefaults()

__all__ = [
    "Cell",
    "Cells",
    "CustomRenderParams",
    "DEFAULTS",
    "DOMAIN",
    "PROMPT_BUNDLE_ID",
    "PROMPT_SCENE_KEY",
    "PolyominoOptionRenderDefaults",
    "PolyominoOptionRenderParams",
    "RenderedPolyominoMissingScene",
    "SCENE_ID",
    "SCENE_VARIANTS",
]
