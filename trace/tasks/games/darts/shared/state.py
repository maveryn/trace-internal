"""Identity-free darts scene state for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .rendering import DartInstance, DartScoreOption


SCENE_ID = "darts"
DARTS_NAMESPACE = "games.darts"
SUPPORTED_DARTS_SCENE_VARIANTS: Tuple[str, ...] = ("single_board",)
SUPPORTED_DARTS_QUERY_IDS: Tuple[str, ...] = (
    "total_score",
    "ring_count",
    "threshold_score_count",
)
SUPPORTED_DARTS_TARGET_RINGS: Tuple[str, ...] = ("single", "double", "triple", "bull")
SUPPORTED_DARTS_THRESHOLDS: Tuple[int, ...] = (20, 25, 30, 40, 50)


@dataclass(frozen=True)
class DartsSceneDefaults:
    """Stable scene fallback defaults for visible dartboard tasks."""

    count_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    total_score_dart_count_support: Tuple[int, ...] = (1,)
    count_query_dart_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    score_option_count_support: Tuple[int, ...] = (4, 6)
    canvas_width: int = 1040
    canvas_height: int = 980
    board_center_x_px: int = 520
    board_center_y_px: int = 464
    board_radius_px: int = 330
    marker_radius_px: int = 17
    number_font_size_px: int = 36
    title_font_size_px: int = 30


@dataclass(frozen=True)
class DartsSceneAxes:
    """Resolved scene and visual axes shared by darts tasks."""

    scene_variant: str
    style_variant: str
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class DartsIntegerAxis:
    """Resolved integer sampling axis with trace metadata."""

    value: int
    support: Tuple[int, ...]
    probabilities: Dict[str, float]


@dataclass(frozen=True)
class DartsScoreSlot:
    """One scoring area on the board."""

    sector_value: int | None
    ring: str
    score: int


@dataclass(frozen=True)
class DartsSampledScene:
    """One sampled darts scene with query-specific witness metadata."""

    darts: Tuple[DartInstance, ...]
    annotation_dart_ids: Tuple[str, ...]
    total_score: int
    score_options: Tuple[DartScoreOption, ...] = ()
    answer_label: str | None = None


@dataclass(frozen=True)
class DartsGeneratedComponents:
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


DEFAULTS = DartsSceneDefaults()


__all__ = [
    "DARTS_NAMESPACE",
    "DEFAULTS",
    "SCENE_ID",
    "SUPPORTED_DARTS_QUERY_IDS",
    "SUPPORTED_DARTS_SCENE_VARIANTS",
    "SUPPORTED_DARTS_TARGET_RINGS",
    "SUPPORTED_DARTS_THRESHOLDS",
    "DartsGeneratedComponents",
    "DartsIntegerAxis",
    "DartsSceneAxes",
    "DartsSampledScene",
    "DartsSceneDefaults",
    "DartsScoreSlot",
]
