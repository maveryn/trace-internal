"""Identity-free dots-and-boxes scene state for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .mechanics import SUPPORTED_DOTS_AND_BOXES_SCENE_VARIANTS


SCENE_ID = "dots_and_boxes"
DOTS_AND_BOXES_NAMESPACE = "games.dots_and_boxes"


@dataclass(frozen=True)
class DotsAndBoxesSceneDefaults:
    """Stable scene fallback defaults for visible dots-and-boxes boards."""

    three_sided_box_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    capture_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    highlighted_candidate_capture_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    owned_box_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8)
    candidate_edge_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    box_rows_support: Tuple[int, ...] = (3, 4)
    box_cols_support: Tuple[int, ...] = (3, 4)
    canvas_width: int = 1180
    canvas_height: int = 820
    board_width_px: int = 880
    board_height_px: int = 640
    board_corner_radius_px: int = 24
    panel_margin_px: int = 56
    title_font_size_px: int = 34
    title_band_height_px: int = 62
    board_padding_px: int = 62
    dot_radius_px: int = 7
    dash_length_px: int = 30
    dash_gap_px: int = 18
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 620
    canvas_min_height_px: int = 520
    canvas_side_padding_px: int = 150
    canvas_vertical_padding_px: int = 110


@dataclass(frozen=True)
class DotsAndBoxesSceneAxes:
    """Resolved scene/style axes shared by dots-and-boxes tasks."""

    scene_variant: str
    style_variant: str
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class DotsAndBoxesIntegerAxis:
    """Resolved integer sampling axis with trace metadata."""

    value: int
    support: Tuple[int, ...]
    probabilities: Dict[str, float]


@dataclass(frozen=True)
class DotsAndBoxesBoardShapeAxis:
    """Resolved board shape with trace metadata."""

    box_rows: int
    box_cols: int
    probabilities: Dict[str, float]


@dataclass(frozen=True)
class DotsAndBoxesGeneratedComponents:
    """Generated scene components for public task files to wrap in TaskOutput."""

    prompt: str
    prompt_variants: Dict[str, Any]
    answer_type: str
    answer_value: int | str
    annotation_type: str
    annotation_value: Any
    image: Any
    trace_payload: Dict[str, Any]
    query_id: str


DEFAULTS = DotsAndBoxesSceneDefaults()


__all__ = [
    "DEFAULTS",
    "DOTS_AND_BOXES_NAMESPACE",
    "SCENE_ID",
    "SUPPORTED_DOTS_AND_BOXES_SCENE_VARIANTS",
    "DotsAndBoxesBoardShapeAxis",
    "DotsAndBoxesGeneratedComponents",
    "DotsAndBoxesIntegerAxis",
    "DotsAndBoxesSceneAxes",
    "DotsAndBoxesSceneDefaults",
]
