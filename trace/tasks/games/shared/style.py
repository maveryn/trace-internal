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
class ReversiTheme:
    """Resolved Reversi-board palette for one style variant."""

    board_frame_rgb: Tuple[int, int, int]
    board_fill_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    badge_fill_rgb: Tuple[int, int, int]
    badge_outline_rgb: Tuple[int, int, int]
    badge_text_rgb: Tuple[int, int, int]
    black_disc_fill_rgb: Tuple[int, int, int]
    black_disc_outline_rgb: Tuple[int, int, int]
    black_disc_shine_rgb: Tuple[int, int, int]
    white_disc_fill_rgb: Tuple[int, int, int]
    white_disc_outline_rgb: Tuple[int, int, int]
    white_disc_shine_rgb: Tuple[int, int, int]
    disc_outline_width_px: int
    marked_square_outline_rgb: Tuple[int, int, int]
    marked_square_fill_rgba: Tuple[int, int, int, int]


@dataclass(frozen=True)
class ConnectFourTheme:
    """Resolved Connect Four board palette for one style variant."""

    board_frame_rgb: Tuple[int, int, int]
    board_fill_rgb: Tuple[int, int, int]
    cell_well_rgb: Tuple[int, int, int]
    cell_well_outline_rgb: Tuple[int, int, int]
    cell_well_outline_width_px: int
    badge_fill_rgb: Tuple[int, int, int]
    badge_outline_rgb: Tuple[int, int, int]
    badge_text_rgb: Tuple[int, int, int]
    red_disc_fill_rgb: Tuple[int, int, int]
    red_disc_outline_rgb: Tuple[int, int, int]
    red_disc_shine_rgb: Tuple[int, int, int]
    yellow_disc_fill_rgb: Tuple[int, int, int]
    yellow_disc_outline_rgb: Tuple[int, int, int]
    yellow_disc_shine_rgb: Tuple[int, int, int]
    disc_outline_width_px: int
    marked_square_outline_rgb: Tuple[int, int, int]
    marked_square_fill_rgba: Tuple[int, int, int, int]


@dataclass(frozen=True)
class CheckersTheme:
    """Resolved Checkers board palette for one style variant."""

    board_frame_rgb: Tuple[int, int, int]
    light_square_rgb: Tuple[int, int, int]
    dark_square_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    grid_line_width_px: int
    badge_fill_rgb: Tuple[int, int, int]
    badge_outline_rgb: Tuple[int, int, int]
    badge_text_rgb: Tuple[int, int, int]
    red_piece_fill_rgb: Tuple[int, int, int]
    red_piece_outline_rgb: Tuple[int, int, int]
    red_piece_shine_rgb: Tuple[int, int, int]
    black_piece_fill_rgb: Tuple[int, int, int]
    black_piece_outline_rgb: Tuple[int, int, int]
    black_piece_shine_rgb: Tuple[int, int, int]
    piece_outline_width_px: int


@dataclass(frozen=True)
class MancalaTheme:
    """Resolved Mancala board palette for one style variant."""

    board_frame_rgb: Tuple[int, int, int]
    board_fill_rgb: Tuple[int, int, int]
    pit_fill_rgb: Tuple[int, int, int]
    pit_outline_rgb: Tuple[int, int, int]
    pit_outline_width_px: int
    store_fill_rgb: Tuple[int, int, int]
    store_outline_rgb: Tuple[int, int, int]
    badge_fill_rgb: Tuple[int, int, int]
    badge_outline_rgb: Tuple[int, int, int]
    badge_text_rgb: Tuple[int, int, int]
    top_side_text_rgb: Tuple[int, int, int]
    bottom_side_text_rgb: Tuple[int, int, int]
    count_text_rgb: Tuple[int, int, int]


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


def build_games_reversi_theme(*, style_variant: str) -> ReversiTheme:
    """Return one resolved Reversi-board theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return ReversiTheme(
            board_frame_rgb=(76, 56, 38),
            board_fill_rgb=(66, 126, 86),
            grid_line_rgb=(29, 74, 46),
            badge_fill_rgb=(241, 244, 247),
            badge_outline_rgb=(102, 112, 122),
            badge_text_rgb=(32, 38, 44),
            black_disc_fill_rgb=(35, 39, 46),
            black_disc_outline_rgb=(18, 22, 28),
            black_disc_shine_rgb=(92, 100, 110),
            white_disc_fill_rgb=(245, 247, 250),
            white_disc_outline_rgb=(124, 132, 142),
            white_disc_shine_rgb=(255, 255, 255),
            disc_outline_width_px=3,
            marked_square_outline_rgb=(199, 63, 59),
            marked_square_fill_rgba=(199, 63, 59, 34),
        )
    if variant == "outlined":
        return ReversiTheme(
            board_frame_rgb=(58, 43, 31),
            board_fill_rgb=(72, 135, 88),
            grid_line_rgb=(24, 68, 41),
            badge_fill_rgb=(255, 255, 255),
            badge_outline_rgb=(72, 82, 92),
            badge_text_rgb=(26, 30, 36),
            black_disc_fill_rgb=(28, 31, 36),
            black_disc_outline_rgb=(10, 12, 15),
            black_disc_shine_rgb=(86, 94, 104),
            white_disc_fill_rgb=(255, 255, 255),
            white_disc_outline_rgb=(122, 130, 140),
            white_disc_shine_rgb=(255, 255, 255),
            disc_outline_width_px=4,
            marked_square_outline_rgb=(208, 60, 58),
            marked_square_fill_rgba=(208, 60, 58, 28),
        )
    return ReversiTheme(
        board_frame_rgb=(70, 50, 34),
        board_fill_rgb=(60, 121, 79),
        grid_line_rgb=(26, 72, 43),
        badge_fill_rgb=(248, 249, 251),
        badge_outline_rgb=(94, 102, 110),
        badge_text_rgb=(27, 32, 38),
        black_disc_fill_rgb=(31, 34, 39),
        black_disc_outline_rgb=(13, 15, 19),
        black_disc_shine_rgb=(84, 92, 102),
        white_disc_fill_rgb=(250, 251, 253),
        white_disc_outline_rgb=(128, 136, 145),
        white_disc_shine_rgb=(255, 255, 255),
        disc_outline_width_px=3,
        marked_square_outline_rgb=(203, 58, 57),
        marked_square_fill_rgba=(203, 58, 57, 32),
    )


def build_games_connect_four_theme(*, style_variant: str) -> ConnectFourTheme:
    """Return one resolved Connect Four theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return ConnectFourTheme(
            board_frame_rgb=(39, 61, 138),
            board_fill_rgb=(66, 99, 208),
            cell_well_rgb=(235, 241, 255),
            cell_well_outline_rgb=(184, 198, 236),
            cell_well_outline_width_px=2,
            badge_fill_rgb=(241, 244, 247),
            badge_outline_rgb=(102, 112, 122),
            badge_text_rgb=(32, 38, 44),
            red_disc_fill_rgb=(212, 72, 68),
            red_disc_outline_rgb=(150, 45, 42),
            red_disc_shine_rgb=(241, 160, 154),
            yellow_disc_fill_rgb=(245, 201, 72),
            yellow_disc_outline_rgb=(186, 142, 34),
            yellow_disc_shine_rgb=(255, 232, 150),
            disc_outline_width_px=3,
            marked_square_outline_rgb=(199, 63, 59),
            marked_square_fill_rgba=(199, 63, 59, 30),
        )
    if variant == "outlined":
        return ConnectFourTheme(
            board_frame_rgb=(32, 48, 118),
            board_fill_rgb=(54, 86, 196),
            cell_well_rgb=(255, 255, 255),
            cell_well_outline_rgb=(193, 206, 242),
            cell_well_outline_width_px=3,
            badge_fill_rgb=(255, 255, 255),
            badge_outline_rgb=(72, 82, 92),
            badge_text_rgb=(26, 30, 36),
            red_disc_fill_rgb=(220, 60, 58),
            red_disc_outline_rgb=(150, 34, 32),
            red_disc_shine_rgb=(247, 160, 156),
            yellow_disc_fill_rgb=(250, 206, 54),
            yellow_disc_outline_rgb=(182, 136, 18),
            yellow_disc_shine_rgb=(255, 237, 150),
            disc_outline_width_px=4,
            marked_square_outline_rgb=(208, 60, 58),
            marked_square_fill_rgba=(208, 60, 58, 24),
        )
    return ConnectFourTheme(
        board_frame_rgb=(35, 55, 126),
        board_fill_rgb=(58, 91, 204),
        cell_well_rgb=(238, 244, 255),
        cell_well_outline_rgb=(187, 201, 238),
        cell_well_outline_width_px=2,
        badge_fill_rgb=(248, 249, 251),
        badge_outline_rgb=(94, 102, 110),
        badge_text_rgb=(27, 32, 38),
        red_disc_fill_rgb=(216, 66, 62),
        red_disc_outline_rgb=(146, 40, 36),
        red_disc_shine_rgb=(244, 158, 152),
        yellow_disc_fill_rgb=(246, 203, 60),
        yellow_disc_outline_rgb=(185, 139, 24),
        yellow_disc_shine_rgb=(255, 233, 148),
        disc_outline_width_px=3,
        marked_square_outline_rgb=(203, 58, 57),
        marked_square_fill_rgba=(203, 58, 57, 28),
    )


def build_games_checkers_theme(*, style_variant: str) -> CheckersTheme:
    """Return one resolved Checkers theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return CheckersTheme(
            board_frame_rgb=(103, 70, 44),
            light_square_rgb=(235, 223, 198),
            dark_square_rgb=(110, 76, 48),
            grid_line_rgb=(88, 63, 42),
            grid_line_width_px=2,
            badge_fill_rgb=(241, 244, 247),
            badge_outline_rgb=(102, 112, 122),
            badge_text_rgb=(32, 38, 44),
            red_piece_fill_rgb=(205, 74, 69),
            red_piece_outline_rgb=(144, 45, 40),
            red_piece_shine_rgb=(238, 166, 158),
            black_piece_fill_rgb=(47, 50, 56),
            black_piece_outline_rgb=(21, 24, 29),
            black_piece_shine_rgb=(112, 118, 128),
            piece_outline_width_px=3,
        )
    if variant == "outlined":
        return CheckersTheme(
            board_frame_rgb=(94, 62, 37),
            light_square_rgb=(246, 239, 220),
            dark_square_rgb=(117, 80, 46),
            grid_line_rgb=(82, 59, 40),
            grid_line_width_px=3,
            badge_fill_rgb=(255, 255, 255),
            badge_outline_rgb=(72, 82, 92),
            badge_text_rgb=(26, 30, 36),
            red_piece_fill_rgb=(215, 61, 58),
            red_piece_outline_rgb=(147, 34, 31),
            red_piece_shine_rgb=(244, 165, 160),
            black_piece_fill_rgb=(36, 39, 44),
            black_piece_outline_rgb=(9, 12, 15),
            black_piece_shine_rgb=(104, 112, 122),
            piece_outline_width_px=4,
        )
    return CheckersTheme(
        board_frame_rgb=(98, 66, 41),
        light_square_rgb=(241, 232, 210),
        dark_square_rgb=(103, 70, 42),
        grid_line_rgb=(84, 60, 39),
        grid_line_width_px=2,
        badge_fill_rgb=(248, 249, 251),
        badge_outline_rgb=(94, 102, 110),
        badge_text_rgb=(27, 32, 38),
        red_piece_fill_rgb=(210, 67, 63),
        red_piece_outline_rgb=(143, 41, 37),
        red_piece_shine_rgb=(241, 162, 156),
        black_piece_fill_rgb=(41, 44, 50),
        black_piece_outline_rgb=(15, 18, 22),
        black_piece_shine_rgb=(106, 114, 124),
        piece_outline_width_px=3,
    )


def build_games_mancala_theme(*, style_variant: str) -> MancalaTheme:
    """Return one resolved Mancala board theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return MancalaTheme(
            board_frame_rgb=(124, 88, 58),
            board_fill_rgb=(201, 160, 112),
            pit_fill_rgb=(231, 205, 166),
            pit_outline_rgb=(152, 115, 77),
            pit_outline_width_px=3,
            store_fill_rgb=(224, 194, 152),
            store_outline_rgb=(148, 108, 72),
            badge_fill_rgb=(241, 244, 247),
            badge_outline_rgb=(102, 112, 122),
            badge_text_rgb=(32, 38, 44),
            top_side_text_rgb=(213, 120, 63),
            bottom_side_text_rgb=(72, 116, 196),
            count_text_rgb=(53, 41, 31),
        )
    if variant == "outlined":
        return MancalaTheme(
            board_frame_rgb=(112, 78, 46),
            board_fill_rgb=(214, 176, 127),
            pit_fill_rgb=(247, 233, 209),
            pit_outline_rgb=(128, 92, 57),
            pit_outline_width_px=4,
            store_fill_rgb=(239, 220, 190),
            store_outline_rgb=(124, 87, 54),
            badge_fill_rgb=(255, 255, 255),
            badge_outline_rgb=(72, 82, 92),
            badge_text_rgb=(26, 30, 36),
            top_side_text_rgb=(220, 112, 50),
            bottom_side_text_rgb=(54, 108, 204),
            count_text_rgb=(48, 37, 27),
        )
    return MancalaTheme(
        board_frame_rgb=(118, 82, 50),
        board_fill_rgb=(206, 167, 117),
        pit_fill_rgb=(237, 214, 178),
        pit_outline_rgb=(145, 105, 68),
        pit_outline_width_px=3,
        store_fill_rgb=(229, 204, 165),
        store_outline_rgb=(140, 101, 66),
        badge_fill_rgb=(248, 249, 251),
        badge_outline_rgb=(94, 102, 110),
        badge_text_rgb=(27, 32, 38),
        top_side_text_rgb=(216, 116, 56),
        bottom_side_text_rgb=(61, 112, 201),
        count_text_rgb=(50, 39, 29),
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
    "CheckersTheme",
    "ConnectFourTheme",
    "DominoTheme",
    "MancalaTheme",
    "ReversiTheme",
    "SUPPORTED_GAMES_STYLE_VARIANTS",
    "build_games_card_theme",
    "build_games_checkers_theme",
    "build_games_connect_four_theme",
    "build_games_domino_theme",
    "build_games_mancala_theme",
    "build_games_reversi_theme",
    "style_probability_map",
    "suit_color",
]
