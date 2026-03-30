"""Shared styling helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


SUPPORTED_GAMES_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
)


@dataclass(frozen=True)
class CardTheme:
    """Resolved face-up card palette for one style variant."""

    card_fill_rgb: Tuple[int, int, int]
    card_border_rgb: Tuple[int, int, int]
    card_border_width_px: int
    shadow_rgb: Tuple[int, int, int]
    shadow_alpha: int
    shadow_offset_px: Tuple[int, int]
    center_symbol_rgb_black: Tuple[int, int, int]
    center_symbol_rgb_red: Tuple[int, int, int]
    rank_rgb_black: Tuple[int, int, int]
    rank_rgb_red: Tuple[int, int, int]
    reference_fill_rgb: Tuple[int, int, int]
    reference_text_rgb: Tuple[int, int, int]
    continuation_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class DominoTheme:
    """Resolved domino-scene palette for one style variant."""

    tile_fill_rgb: Tuple[int, int, int]
    tile_border_rgb: Tuple[int, int, int]
    tile_border_width_px: int
    divider_rgb: Tuple[int, int, int]
    pip_rgb: Tuple[int, int, int]
    shadow_rgb: Tuple[int, int, int]
    shadow_alpha: int
    shadow_offset_px: Tuple[int, int]
    reference_outline_rgb: Tuple[int, int, int]
    reference_tag_fill_rgb: Tuple[int, int, int]
    reference_tag_text_rgb: Tuple[int, int, int]


def build_games_card_theme(*, style_variant: str) -> CardTheme:
    """Return one resolved card-scene theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return CardTheme(
            card_fill_rgb=(253, 251, 245),
            card_border_rgb=(92, 98, 106),
            card_border_width_px=3,
            shadow_rgb=(19, 28, 24),
            shadow_alpha=58,
            shadow_offset_px=(5, 6),
            center_symbol_rgb_black=(41, 45, 52),
            center_symbol_rgb_red=(174, 44, 57),
            rank_rgb_black=(36, 41, 47),
            rank_rgb_red=(170, 46, 59),
            reference_fill_rgb=(66, 112, 198),
            reference_text_rgb=(255, 255, 255),
            continuation_rgb=(66, 112, 198),
        )
    if variant == "outlined":
        return CardTheme(
            card_fill_rgb=(255, 255, 255),
            card_border_rgb=(56, 63, 72),
            card_border_width_px=4,
            shadow_rgb=(16, 20, 22),
            shadow_alpha=42,
            shadow_offset_px=(4, 5),
            center_symbol_rgb_black=(34, 38, 44),
            center_symbol_rgb_red=(178, 38, 57),
            rank_rgb_black=(28, 32, 38),
            rank_rgb_red=(176, 41, 60),
            reference_fill_rgb=(72, 125, 217),
            reference_text_rgb=(255, 255, 255),
            continuation_rgb=(72, 125, 217),
        )
    return CardTheme(
        card_fill_rgb=(255, 255, 255),
        card_border_rgb=(68, 74, 82),
        card_border_width_px=3,
        shadow_rgb=(18, 22, 24),
        shadow_alpha=52,
        shadow_offset_px=(4, 5),
        center_symbol_rgb_black=(28, 31, 36),
        center_symbol_rgb_red=(184, 34, 54),
        rank_rgb_black=(24, 28, 32),
        rank_rgb_red=(180, 37, 57),
        reference_fill_rgb=(56, 106, 202),
        reference_text_rgb=(255, 255, 255),
        continuation_rgb=(56, 106, 202),
    )


def build_games_domino_theme(*, style_variant: str) -> DominoTheme:
    """Return one resolved domino-scene theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return DominoTheme(
            tile_fill_rgb=(250, 247, 241),
            tile_border_rgb=(92, 98, 106),
            tile_border_width_px=3,
            divider_rgb=(104, 111, 119),
            pip_rgb=(38, 42, 48),
            shadow_rgb=(19, 28, 24),
            shadow_alpha=54,
            shadow_offset_px=(5, 5),
            reference_outline_rgb=(199, 63, 59),
            reference_tag_fill_rgb=(199, 63, 59),
            reference_tag_text_rgb=(255, 255, 255),
        )
    if variant == "outlined":
        return DominoTheme(
            tile_fill_rgb=(255, 255, 255),
            tile_border_rgb=(56, 63, 72),
            tile_border_width_px=4,
            divider_rgb=(68, 76, 86),
            pip_rgb=(31, 35, 41),
            shadow_rgb=(16, 20, 22),
            shadow_alpha=40,
            shadow_offset_px=(4, 5),
            reference_outline_rgb=(208, 60, 58),
            reference_tag_fill_rgb=(208, 60, 58),
            reference_tag_text_rgb=(255, 255, 255),
        )
    return DominoTheme(
        tile_fill_rgb=(255, 255, 255),
        tile_border_rgb=(68, 74, 82),
        tile_border_width_px=3,
        divider_rgb=(78, 86, 94),
        pip_rgb=(26, 30, 35),
        shadow_rgb=(18, 22, 24),
        shadow_alpha=48,
        shadow_offset_px=(4, 5),
        reference_outline_rgb=(203, 58, 57),
        reference_tag_fill_rgb=(203, 58, 57),
        reference_tag_text_rgb=(255, 255, 255),
    )


def suit_color(theme: CardTheme, *, suit_name: str) -> Tuple[int, int, int]:
    """Return the rendered suit/rank color for one suit under the active theme."""

    return (
        tuple(int(value) for value in theme.center_symbol_rgb_red)
        if str(suit_name) in {"hearts", "diamonds"}
        else tuple(int(value) for value in theme.center_symbol_rgb_black)
    )


def style_probability_map() -> Dict[str, float]:
    """Return one stable uniform style-probability map."""

    probability = 1.0 / float(len(SUPPORTED_GAMES_STYLE_VARIANTS))
    return {str(name): float(probability) for name in SUPPORTED_GAMES_STYLE_VARIANTS}


__all__ = [
    "CardTheme",
    "DominoTheme",
    "SUPPORTED_GAMES_STYLE_VARIANTS",
    "build_games_card_theme",
    "build_games_domino_theme",
    "style_probability_map",
    "suit_color",
]
