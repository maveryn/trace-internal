"""Passive state objects for the Tangram puzzle scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from PIL import Image

DOMAIN = "puzzles"
SCENE_ID = "tangram"

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "tangram_square",
    "tangram_diamond",
    "tangram_tilted",
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class PieceSpec:
    """One tangram assembly piece in normalized local coordinates."""

    piece_id: str
    shape_id: str
    shape_name: str
    points: Tuple[Point, ...]


@dataclass(frozen=True)
class OptionSpec:
    """One labeled visual option for the missing-piece task."""

    option_id: str
    option_label: str
    shape_id: str
    is_correct: bool
    display_rotation_degrees: int
    shape_points: Tuple[Point, ...]


@dataclass(frozen=True)
class TangramSample:
    """Task-owned symbolic Tangram instance before rendering."""

    piece_specs: Tuple[PieceSpec, ...]
    target_piece_ids: Tuple[str, ...]
    target_piece_id: str
    target_shape_id: str
    target_shape_name: str
    contact_piece_ids: Tuple[str, ...]
    contact_count: int
    contact_count_support: Tuple[int, ...]
    option_specs: Tuple[OptionSpec, ...]
    option_count: int
    option_count_range: Tuple[int, int]
    correct_option_index: int | None
    answer_option_label: str
    correct_option_panel_id: str
    construction_mode: str


@dataclass(frozen=True)
class TangramRenderParams:
    """Resolved visual parameters for one Tangram scene."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    assembly_panel_width_px: int
    assembly_panel_height_px: int
    assembly_panel_padding_px: int
    assembly_to_options_gap_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_row_gap_px: int
    option_shape_box_size_px: int
    option_label_gap_px: int
    panel_corner_radius_px: int
    content_corner_radius_px: int
    border_width_px: int
    seam_width_px: int
    highlight_width_px: int
    option_label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    assembly_panel_fill_rgb: Tuple[int, int, int]
    option_panel_fill_rgb: Tuple[int, int, int]
    option_shape_fill_rgb: Tuple[int, int, int]
    missing_fill_rgb: Tuple[int, int, int]
    marked_outline_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    seam_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    instance_seed: int = 0


@dataclass(frozen=True)
class RenderedTangramScene:
    """Rendered Tangram scene with traceable pixel geometry."""

    image: Image.Image
    entities: Tuple[dict, ...]
    scene_bbox_px: list[float]
    assembly_panel_bbox_px: list[float]
    assembly_bbox_px: list[float]
    piece_bbox_map: dict[str, list[float]]
    option_panel_bbox_map: dict[str, list[float]]


__all__ = [
    "BBox",
    "DOMAIN",
    "OptionSpec",
    "PieceSpec",
    "Point",
    "RenderedTangramScene",
    "SCENE_ID",
    "SUPPORTED_SCENE_VARIANTS",
    "TangramRenderParams",
    "TangramSample",
]
