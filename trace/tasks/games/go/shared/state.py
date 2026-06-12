"""Identity-free Go scene state for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .mechanics import SUPPORTED_GO_PLAYER_COLORS


SCENE_ID = "go"
GO_NAMESPACE = "games.go"
SUPPORTED_GO_SCENE_VARIANTS: Tuple[str, ...] = ("open_board", "crowded_board")


@dataclass(frozen=True)
class GoSceneDefaults:
    """Stable scene fallback defaults for visible Go boards."""

    liberty_count_support: Tuple[int, ...] = (1, 2, 3, 4, 6)
    adjacent_enemy_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    shared_liberty_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    stone_group_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
    board_size_support: Tuple[int, ...] = (6, 7, 8)
    canvas_width: int = 920
    canvas_height: int = 920
    panel_margin_px: int = 48
    max_board_size_px: int = 760
    board_padding_px: int = 78
    board_corner_radius_px: int = 24
    board_frame_width_px: int = 12
    line_width_px: int = 4
    point_radius_px: int = 4
    stone_radius_fraction: float = 0.34
    highlight_outline_width_px: int = 10
    liberty_bbox_fraction: float = 0.72
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 560
    canvas_min_height_px: int = 560
    canvas_side_padding_px: int = 110
    canvas_vertical_padding_px: int = 110


@dataclass(frozen=True)
class GoSceneAxes:
    """Resolved scene/style axes shared by Go tasks."""

    scene_variant: str
    style_variant: str
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class GoIntegerAxis:
    """Resolved integer sampling axis with trace metadata."""

    value: int
    support: Tuple[int, ...]
    probabilities: Dict[str, float]


@dataclass(frozen=True)
class GoPlayerColorAxis:
    """Resolved Go player color axis with trace metadata."""

    player_color: str
    probabilities: Dict[str, float]


@dataclass(frozen=True)
class GoGeneratedComponents:
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


DEFAULTS = GoSceneDefaults()


__all__ = [
    "DEFAULTS",
    "GO_NAMESPACE",
    "SCENE_ID",
    "SUPPORTED_GO_PLAYER_COLORS",
    "SUPPORTED_GO_SCENE_VARIANTS",
    "GoGeneratedComponents",
    "GoIntegerAxis",
    "GoPlayerColorAxis",
    "GoSceneAxes",
    "GoSceneDefaults",
]
