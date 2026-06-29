"""Passive state, constants, and dataclasses for matchstick puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


DOMAIN = "puzzles"
SCENE_ID = "matchstick"
SCENE_VARIANTS: Tuple[str, ...] = (
    "wooden_matches",
    "colored_rods",
    "chalk_sticks",
    "neon_rods",
    "metal_rods",
)
OPTION_LABELS: Tuple[str, ...] = tuple("ABCDEF")

Color = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class RenderParams:
    """Resolved render dimensions for one matchstick scene."""

    canvas_width: int
    canvas_height: int
    margin_px: int
    source_panel_height_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    stick_width_px: int
    option_label_font_size_px: int
    caption_font_size_px: int
    source_caption_font_size_px: int


@dataclass(frozen=True)
class OptionSpec:
    """One labeled candidate panel."""

    label: str
    is_correct: bool
    value: Any
    metric_value: int | None = None


@dataclass(frozen=True)
class NumberDataset:
    """Concrete number-transform instance before rendering."""

    scene_variant: str
    source_number: int
    answer_number: int
    answer_label: str
    option_count: int
    option_specs: Tuple[OptionSpec, ...]
    changed_digit_index: int
    removed_segment_keys: Tuple[str, ...]
    added_segment_keys: Tuple[str, ...]


@dataclass(frozen=True)
class RenderedScene:
    """Rendered matchstick image plus item projections."""

    image: Any
    scene_bbox_px: BBox
    item_bbox_map: Dict[str, BBox]
    entities: Tuple[Dict[str, Any], ...]


__all__ = [
    "BBox",
    "Color",
    "DOMAIN",
    "NumberDataset",
    "OPTION_LABELS",
    "OptionSpec",
    "RenderParams",
    "RenderedScene",
    "SCENE_ID",
    "SCENE_VARIANTS",
]
