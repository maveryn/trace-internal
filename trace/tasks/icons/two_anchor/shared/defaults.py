"""Default parameter bundles for two-anchor icon scenes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, Tuple

from ...shared.defaults import ICON_SHARED_DEFAULTS


DOMAIN = "icons"
SCENE_ID = "two_anchor"


@dataclass(frozen=True)
class TwoAnchorDefaults:
    """Scene defaults for counting icons between two marked anchors."""

    object_count_min: int = 1
    object_count_max: int = 15
    target_count_min: int = 0
    target_count_max: int = 5
    distractor_count_min: int = 1
    distractor_count_max: int = 10
    distractor_margin_over_target: int = 0
    canvas_width: int = 960
    canvas_height: int = 544
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_min_px
    scene_icon_size_max_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_max_px
    scene_max_overlap_fraction: float = 0.08
    scene_placement_max_attempts: int = 120
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )
    anchor_highlight_padding_px: int = 10
    anchor_highlight_radius_px: int = 14
    anchor_outline_rgb: Tuple[int, int, int] = (74, 113, 188)
    anchor_label_color_rgb: Tuple[int, int, int] = (57, 87, 145)
    anchor_label_font_size_px: int = 20
    strip_boundary_margin_px: int = 14
    strip_span_ratio_min: float = 0.32
    strip_span_ratio_max: float = 0.60
    strip_outside_ratio_min: float = 0.12
    anchor_edge_padding_px: int = 10


__all__ = ["DOMAIN", "SCENE_ID", "TwoAnchorDefaults"]

