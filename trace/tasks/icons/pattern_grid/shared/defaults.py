"""Defaults for the pattern-grid icons scene."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, Tuple

from ...shared.defaults import ICON_SHARED_DEFAULTS


DOMAIN = "icons"
SCENE_ID = "pattern_grid"

DEFAULT_COLOR_NAMES: Tuple[str, ...] = (
    "red",
    "orange",
    "yellow",
    "green",
    "cyan",
    "blue",
    "purple",
    "magenta",
)
DEFAULT_COLOR_LADDER_RGB: Tuple[Tuple[int, int, int], ...] = (
    (210, 54, 64),
    (224, 120, 28),
    (198, 164, 28),
    (48, 156, 72),
    (22, 160, 178),
    (58, 104, 210),
    (132, 74, 200),
    (204, 70, 156),
)


@dataclass(frozen=True)
class PatternGridDefaults:
    """Stable fallback defaults for numbered icon pattern grids."""

    grid_rows: int = 3
    grid_cols: int = 3
    answer_index_min: int = 1
    answer_index_max: int = 9
    canvas_width: int = 672
    canvas_height: int = 672
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    scene_icon_size_min_px: int = 34
    scene_icon_size_max_px: int = 84
    color_icon_size_min_px: int = 66
    color_icon_size_max_px: int = 84
    size_icon_size_min_px: int = 34
    size_icon_size_max_px: int = 82
    cell_box_width_min_px: int = 116
    cell_box_width_max_px: int = 152
    cell_box_height_min_px: int = 116
    cell_box_height_max_px: int = 152
    scene_max_overlap_fraction: float = 0.20
    scene_placement_max_attempts: int = 80
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    pool_manifest: str = "all_icons.txt"
    color_level_names: Tuple[str, ...] = DEFAULT_COLOR_NAMES
    color_ladder_rgb: Tuple[Tuple[int, int, int], ...] = DEFAULT_COLOR_LADDER_RGB
    color_levels: Tuple[int, ...] = tuple(range(len(DEFAULT_COLOR_LADDER_RGB)))
    base_color_level_candidates: Tuple[int, ...] = tuple(range(len(DEFAULT_COLOR_LADDER_RGB)))
    row_step_color_candidates: Tuple[int, ...] = (-2, -1, 0, 1, 2)
    col_step_color_candidates: Tuple[int, ...] = (-2, -1, 0, 1, 2)
    size_levels: Tuple[int, ...] = (1, 2, 3, 4, 5)
    base_size_level_candidates: Tuple[int, ...] = (1, 2, 3, 4, 5)
    row_step_size_candidates: Tuple[int, ...] = (-1, 0, 1)
    col_step_size_candidates: Tuple[int, ...] = (-1, 0, 1)
    min_violation_level_delta: int = 2
    size_level_gap_px: int = 10
    shared_rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    palette_size_min: int = 1
    palette_size_max: int = 1
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    cell_padding_px: int = 10
    cell_icon_padding_px: int = 10
    cell_corner_radius_px: int = 12
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_font_size_px: int = 22
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    scene_content_side_padding_px: int = 10
    scene_content_bottom_padding_px: int = 10
    scene_content_top_offset_px: int = 40
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = (0, 0)
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )


__all__ = [
    "DEFAULT_COLOR_LADDER_RGB",
    "DEFAULT_COLOR_NAMES",
    "DOMAIN",
    "PatternGridDefaults",
    "SCENE_ID",
]
