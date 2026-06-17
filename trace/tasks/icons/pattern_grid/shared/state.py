"""Passive state records for the pattern-grid icons scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from PIL import Image


BBox = Tuple[int, int, int, int]
RGB = Tuple[int, int, int]
ATTRIBUTE_AXES: Tuple[str, str] = ("color", "size")


@dataclass(frozen=True)
class PatternGridSpec:
    """Resolved symbolic pattern with one violating numbered cell."""

    attribute_axis: str
    grid_rows: int
    grid_cols: int
    answer_index: int
    violation_cell_index: int
    expected_levels: Tuple[int, ...]
    observed_levels: Tuple[int, ...]
    base_level: int
    row_step_levels: int
    col_step_levels: int
    violation_level: int
    shared_rotation_degrees: int
    level_support: Tuple[int, ...]
    plausible_rule_count: int
    total_rule_support: int
    answer_index_probabilities: Dict[str, float]
    level_names: Tuple[str, ...] = ()
    color_ladder_rgb: Tuple[RGB, ...] = ()
    size_level_nominal_sizes_px: Dict[int, int] | None = None


@dataclass(frozen=True)
class RenderedPatternGridScene:
    """Rendered image plus trace-ready scene payloads."""

    image: Image.Image
    pattern_icon_id: str
    sampled_palette_rgb: Tuple[RGB, ...]
    panel_geometry: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]
    scene_icon_instances: Tuple[Dict[str, Any], ...]
    violating_cell_bbox: BBox
    cell_box_width_px: int
    cell_box_height_px: int
    nominal_size_px: int | None = None
    size_level_nominal_sizes_px: Dict[int, int] | None = None


__all__ = [
    "ATTRIBUTE_AXES",
    "BBox",
    "PatternGridSpec",
    "RGB",
    "RenderedPatternGridScene",
]
