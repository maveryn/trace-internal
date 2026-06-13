"""Darts scene defaults and prompt wiring constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SCENE_ID = "darts"
DARTS_NAMESPACE = "games.darts"
PROMPT_WIRING_KEYS: Tuple[str, ...] = ("bundle_id", "scene_key", "task_key")
SUPPORTED_DARTS_SCENE_VARIANTS: Tuple[str, ...] = ("single_board",)
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


DEFAULTS = DartsSceneDefaults()


__all__ = [
    "DARTS_NAMESPACE",
    "DEFAULTS",
    "PROMPT_WIRING_KEYS",
    "SCENE_ID",
    "SUPPORTED_DARTS_SCENE_VARIANTS",
    "SUPPORTED_DARTS_TARGET_RINGS",
    "SUPPORTED_DARTS_THRESHOLDS",
    "DartsSceneDefaults",
]
