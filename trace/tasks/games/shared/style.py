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


@dataclass(frozen=True)
class BingoTheme:
    """Resolved bingo-card palette for one style variant."""

    card_fill_rgb: Tuple[int, int, int]
    card_border_rgb: Tuple[int, int, int]
    card_border_width_px: int
    shadow_rgb: Tuple[int, int, int]
    shadow_alpha: int
    shadow_offset_px: Tuple[int, int]
    title_rgb: Tuple[int, int, int]
    header_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    cell_fill_rgb: Tuple[int, int, int]
    number_rgb: Tuple[int, int, int]
    mark_fill_rgba: Tuple[int, int, int, int]
    mark_outline_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class DotsAndBoxesTheme:
    """Resolved dots-and-boxes palette for one style variant."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    board_border_width_px: int
    shadow_rgb: Tuple[int, int, int]
    shadow_alpha: int
    shadow_offset_px: Tuple[int, int]
    title_rgb: Tuple[int, int, int]
    dot_rgb: Tuple[int, int, int]
    edge_rgb: Tuple[int, int, int]
    edge_width_px: int
    highlight_rgb: Tuple[int, int, int]
    highlight_width_px: int
    guide_rgb: Tuple[int, int, int]


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


def build_games_bingo_theme(*, style_variant: str) -> BingoTheme:
    """Return one resolved bingo-card theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return BingoTheme(
            card_fill_rgb=(251, 246, 236),
            card_border_rgb=(102, 112, 124),
            card_border_width_px=3,
            shadow_rgb=(18, 24, 20),
            shadow_alpha=56,
            shadow_offset_px=(5, 6),
            title_rgb=(40, 63, 121),
            header_rgb=(56, 84, 146),
            grid_line_rgb=(132, 142, 152),
            cell_fill_rgb=(255, 252, 247),
            number_rgb=(41, 46, 54),
            mark_fill_rgba=(214, 84, 76, 136),
            mark_outline_rgb=(184, 58, 54),
        )
    if variant == "outlined":
        return BingoTheme(
            card_fill_rgb=(255, 255, 255),
            card_border_rgb=(62, 70, 80),
            card_border_width_px=4,
            shadow_rgb=(14, 18, 20),
            shadow_alpha=40,
            shadow_offset_px=(4, 5),
            title_rgb=(44, 75, 168),
            header_rgb=(51, 88, 186),
            grid_line_rgb=(92, 100, 110),
            cell_fill_rgb=(255, 255, 255),
            number_rgb=(33, 38, 44),
            mark_fill_rgba=(218, 66, 60, 126),
            mark_outline_rgb=(196, 48, 44),
        )
    return BingoTheme(
        card_fill_rgb=(255, 253, 247),
        card_border_rgb=(74, 82, 92),
        card_border_width_px=3,
        shadow_rgb=(18, 22, 24),
        shadow_alpha=48,
        shadow_offset_px=(4, 5),
        title_rgb=(42, 72, 160),
        header_rgb=(48, 82, 180),
        grid_line_rgb=(108, 116, 126),
        cell_fill_rgb=(255, 255, 252),
        number_rgb=(29, 34, 40),
        mark_fill_rgba=(212, 62, 56, 132),
        mark_outline_rgb=(190, 46, 42),
    )


def build_games_dots_and_boxes_theme(*, style_variant: str) -> DotsAndBoxesTheme:
    """Return one resolved dots-and-boxes theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return DotsAndBoxesTheme(
            board_fill_rgb=(249, 244, 234),
            board_border_rgb=(102, 112, 124),
            board_border_width_px=3,
            shadow_rgb=(18, 24, 20),
            shadow_alpha=56,
            shadow_offset_px=(5, 6),
            title_rgb=(52, 76, 132),
            dot_rgb=(54, 60, 68),
            edge_rgb=(66, 74, 86),
            edge_width_px=8,
            highlight_rgb=(202, 74, 60),
            highlight_width_px=10,
            guide_rgb=(176, 184, 194),
        )
    if variant == "outlined":
        return DotsAndBoxesTheme(
            board_fill_rgb=(255, 255, 255),
            board_border_rgb=(62, 70, 80),
            board_border_width_px=4,
            shadow_rgb=(14, 18, 20),
            shadow_alpha=40,
            shadow_offset_px=(4, 5),
            title_rgb=(44, 75, 168),
            dot_rgb=(36, 40, 46),
            edge_rgb=(52, 58, 68),
            edge_width_px=8,
            highlight_rgb=(214, 60, 54),
            highlight_width_px=10,
            guide_rgb=(196, 202, 210),
        )
    return DotsAndBoxesTheme(
        board_fill_rgb=(255, 252, 244),
        board_border_rgb=(74, 82, 92),
        board_border_width_px=3,
        shadow_rgb=(18, 22, 24),
        shadow_alpha=48,
        shadow_offset_px=(4, 5),
        title_rgb=(45, 76, 160),
        dot_rgb=(30, 34, 40),
        edge_rgb=(46, 52, 60),
        edge_width_px=8,
        highlight_rgb=(210, 58, 52),
        highlight_width_px=10,
        guide_rgb=(184, 190, 198),
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
    "BingoTheme",
    "CardTheme",
    "DominoTheme",
    "DotsAndBoxesTheme",
    "SUPPORTED_GAMES_STYLE_VARIANTS",
    "build_games_bingo_theme",
    "build_games_card_theme",
    "build_games_domino_theme",
    "build_games_dots_and_boxes_theme",
    "style_probability_map",
    "suit_color",
]
