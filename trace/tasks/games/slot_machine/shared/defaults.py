"""Scene-level defaults for slot-machine games tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "slot_machine"
SCENE_NAMESPACE = "games.slot_machine"
REEL_COUNT = 5
ROW_COUNT = 3
PAYLINE_ROW_IDS: Tuple[int, ...] = (0, 1, 2)
SYMBOL_KEYS: Tuple[str, ...] = ("seven", "bar", "gem", "star", "bell", "coin")
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("front_cabinet",)
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic_red",
    "chrome_blue",
    "neon_night",
    "candy_arcade",
    "paper_ticket",
)
WINNING_PAYLINE_COUNT_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3)


@dataclass(frozen=True)
class SlotMachineDefaults:
    """Stable fallback defaults for slot-machine scenes."""

    canvas_width: int = 900
    canvas_height: int = 720
    cabinet_width_px: int = 660
    cabinet_height_px: int = 560
    reel_cell_width_px: int = 104
    reel_cell_height_px: int = 106
    reel_gap_px: int = 10
    row_gap_px: int = 10
    cabinet_pad_px: int = 34
    payline_width_px: int = 6
    label_font_size_px: int = 24
    symbol_font_size_px: int = 28


DEFAULTS = SlotMachineDefaults()
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.45)


__all__ = [
    "DEFAULTS",
    "PAYLINE_ROW_IDS",
    "POST_IMAGE_NOISE_DEFAULTS",
    "REEL_COUNT",
    "ROW_COUNT",
    "SCENE_ID",
    "SCENE_NAMESPACE",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_STYLE_VARIANTS",
    "SYMBOL_KEYS",
    "SlotMachineDefaults",
    "WINNING_PAYLINE_COUNT_SUPPORT",
]
