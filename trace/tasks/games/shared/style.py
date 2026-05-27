"""Shared styling helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


SUPPORTED_GAMES_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
)
SUPPORTED_CHESS_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "wood_token",
    "blue_glyph",
    "monochrome_glyph",
)
SUPPORTED_CHECKERS_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "wood_token",
    "blue_table",
    "charcoal",
)
SUPPORTED_CONNECT_FOUR_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "arcade_blue",
    "teal_frame",
    "charcoal",
)
SUPPORTED_DOMINO_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "ivory",
    "charcoal_tile",
    "wood_tile",
)
SUPPORTED_DOTS_AND_BOXES_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "notebook",
    "slate",
    "wood_panel",
)
SUPPORTED_BINGO_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "mint",
    "lavender",
    "amber",
    "slate",
)
SUPPORTED_GO_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "wood_board",
    "slate_board",
    "paper_board",
)
SUPPORTED_MINESWEEPER_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "notebook",
    "dark",
    "retro",
)
SUPPORTED_BATTLESHIP_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "navy",
    "radar",
    "paper",
)
SUPPORTED_HEX_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "slate",
    "paper",
)
SUPPORTED_POOL_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "tournament_blue",
    "burgundy",
    "charcoal",
    "light_rail",
)
SUPPORTED_REVERSI_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "wood_board",
    "slate_board",
    "blue_board",
)
SUPPORTED_SUDOKU_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "notebook",
    "slate",
    "warm_paper",
)
SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "soft",
    "outlined",
    "wood_panel",
    "slate",
    "parchment",
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
    tile_inner_fill_rgb: Tuple[int, int, int] | None = None
    tile_rendering: str = "flat"
    pip_rendering: str = "flat"
    divider_rendering: str = "line"


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
    board_shadow_rgb: Tuple[int, int, int] = (12, 16, 24)
    board_shadow_alpha: int = 0
    board_shadow_offset_px: Tuple[int, int] = (0, 0)
    board_rendering: str = "flat"
    cell_well_rendering: str = "flat"
    disc_rendering: str = "glossy"


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
    piece_shadow_rgb: Tuple[int, int, int] = (12, 14, 16)
    piece_shadow_alpha: int = 0
    piece_rendering: str = "ring"
    square_rendering: str = "flat"


@dataclass(frozen=True)
class ChessTheme:
    """Resolved Chess board palette for one style variant."""

    board_frame_rgb: Tuple[int, int, int]
    light_square_rgb: Tuple[int, int, int]
    dark_square_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    grid_line_width_px: int
    badge_fill_rgb: Tuple[int, int, int]
    badge_outline_rgb: Tuple[int, int, int]
    badge_text_rgb: Tuple[int, int, int]
    white_piece_fill_rgb: Tuple[int, int, int]
    white_piece_outline_rgb: Tuple[int, int, int]
    black_piece_fill_rgb: Tuple[int, int, int]
    black_piece_outline_rgb: Tuple[int, int, int]
    marked_square_outline_rgb: Tuple[int, int, int]
    marked_square_fill_rgba: Tuple[int, int, int, int]
    piece_shadow_rgb: Tuple[int, int, int]
    piece_shadow_alpha: int
    piece_rendering: str = "token"
    square_rendering: str = "flat"


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
    cell_alt_fill_rgb: Tuple[int, int, int]
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
    board_inner_fill_rgb: Tuple[int, int, int] | None = None
    board_pattern_rgb: Tuple[int, int, int] | None = None
    board_pattern_alpha: int = 0
    board_rendering: str = "flat"
    dot_outline_rgb: Tuple[int, int, int] | None = None
    dot_rendering: str = "flat"


@dataclass(frozen=True)
class NineMensMorrisTheme:
    """Resolved nine-men's-morris palette for one style variant."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    board_border_width_px: int
    shadow_rgb: Tuple[int, int, int]
    shadow_alpha: int
    shadow_offset_px: Tuple[int, int]
    title_rgb: Tuple[int, int, int]
    line_rgb: Tuple[int, int, int]
    line_width_px: int
    node_rgb: Tuple[int, int, int]
    white_piece_fill_rgb: Tuple[int, int, int]
    white_piece_outline_rgb: Tuple[int, int, int]
    black_piece_fill_rgb: Tuple[int, int, int]
    black_piece_outline_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class GoTheme:
    """Resolved Go-board palette for one style variant."""

    board_frame_rgb: Tuple[int, int, int]
    board_fill_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    point_rgb: Tuple[int, int, int]
    black_stone_fill_rgb: Tuple[int, int, int]
    black_stone_outline_rgb: Tuple[int, int, int]
    black_stone_shine_rgb: Tuple[int, int, int]
    white_stone_fill_rgb: Tuple[int, int, int]
    white_stone_outline_rgb: Tuple[int, int, int]
    white_stone_shine_rgb: Tuple[int, int, int]
    stone_outline_width_px: int
    highlight_outline_rgb: Tuple[int, int, int]
    highlight_fill_rgba: Tuple[int, int, int, int]


@dataclass(frozen=True)
class SudokuTheme:
    """Resolved Sudoku-grid palette for one style variant."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    box_line_rgb: Tuple[int, int, int]
    cell_fill_rgb: Tuple[int, int, int]
    highlighted_cell_fill_rgba: Tuple[int, int, int, int]
    marked_cell_fill_rgba: Tuple[int, int, int, int]
    marked_cell_outline_rgb: Tuple[int, int, int]
    digit_rgb: Tuple[int, int, int]
    conflict_digit_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class MinesweeperTheme:
    """Resolved Minesweeper-grid palette for one style variant."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    hidden_cell_fill_rgb: Tuple[int, int, int]
    hidden_cell_border_rgb: Tuple[int, int, int]
    revealed_cell_fill_rgb: Tuple[int, int, int]
    revealed_cell_alt_fill_rgb: Tuple[int, int, int]
    number_rgb_by_value: Tuple[Tuple[int, int, int], ...]
    flag_rgb: Tuple[int, int, int]
    flag_pole_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class BattleshipTheme:
    """Resolved Battleship tracking-grid palette for one style variant."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    cell_fill_rgb: Tuple[int, int, int]
    cell_alt_fill_rgb: Tuple[int, int, int]
    hit_fill_rgb: Tuple[int, int, int]
    hit_outline_rgb: Tuple[int, int, int]
    miss_rgb: Tuple[int, int, int]
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    panel_text_rgb: Tuple[int, int, int]
    ship_icon_fill_rgb: Tuple[int, int, int]
    ship_icon_outline_rgb: Tuple[int, int, int]
    hit_marker_style: str = "disc"
    miss_marker_style: str = "ring"


@dataclass(frozen=True)
class HexTheme:
    """Resolved Hex-board palette for one style variant."""

    cell_fill_rgb: Tuple[int, int, int]
    cell_alt_fill_rgb: Tuple[int, int, int]
    cell_outline_rgb: Tuple[int, int, int]
    board_outline_rgb: Tuple[int, int, int]
    red_goal_rgb: Tuple[int, int, int]
    blue_goal_rgb: Tuple[int, int, int]
    red_stone_fill_rgb: Tuple[int, int, int]
    red_stone_outline_rgb: Tuple[int, int, int]
    red_stone_shine_rgb: Tuple[int, int, int]
    blue_stone_fill_rgb: Tuple[int, int, int]
    blue_stone_outline_rgb: Tuple[int, int, int]
    blue_stone_shine_rgb: Tuple[int, int, int]
    candidate_badge_fill_rgb: Tuple[int, int, int]
    candidate_badge_outline_rgb: Tuple[int, int, int]
    candidate_badge_text_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class PoolTheme:
    """Resolved Pool-table palette for one style variant."""

    rail_rgb: Tuple[int, int, int]
    rail_outline_rgb: Tuple[int, int, int]
    cloth_rgb: Tuple[int, int, int]
    cloth_line_rgb: Tuple[int, int, int]
    pocket_rgb: Tuple[int, int, int]
    pocket_outline_rgb: Tuple[int, int, int]
    ball_outline_rgb: Tuple[int, int, int]
    ball_shadow_rgb: Tuple[int, int, int]
    marker_rgb: Tuple[int, int, int]
    marker_fill_rgba: Tuple[int, int, int, int]
    badge_fill_rgb: Tuple[int, int, int]
    badge_outline_rgb: Tuple[int, int, int]
    badge_text_rgb: Tuple[int, int, int]
    shot_line_rgb: Tuple[int, int, int]
    ball_rendering: str = "glossy"


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
    if variant == "ivory":
        return DominoTheme(
            tile_fill_rgb=(252, 246, 226),
            tile_border_rgb=(111, 89, 62),
            tile_border_width_px=3,
            divider_rgb=(136, 112, 77),
            pip_rgb=(43, 36, 28),
            shadow_rgb=(28, 20, 14),
            shadow_alpha=56,
            shadow_offset_px=(5, 6),
            reference_outline_rgb=(181, 68, 54),
            reference_tag_fill_rgb=(181, 68, 54),
            reference_tag_text_rgb=(255, 255, 255),
            tile_inner_fill_rgb=(255, 250, 235),
            tile_rendering="inset",
            pip_rendering="ring",
            divider_rendering="line",
        )
    if variant == "charcoal_tile":
        return DominoTheme(
            tile_fill_rgb=(48, 52, 60),
            tile_border_rgb=(210, 215, 222),
            tile_border_width_px=3,
            divider_rgb=(214, 219, 226),
            pip_rgb=(245, 247, 250),
            shadow_rgb=(5, 7, 10),
            shadow_alpha=62,
            shadow_offset_px=(5, 6),
            reference_outline_rgb=(104, 186, 255),
            reference_tag_fill_rgb=(58, 118, 190),
            reference_tag_text_rgb=(255, 255, 255),
            tile_inner_fill_rgb=(57, 62, 72),
            tile_rendering="inset",
            pip_rendering="flat",
            divider_rendering="notch",
        )
    if variant == "wood_tile":
        return DominoTheme(
            tile_fill_rgb=(178, 121, 66),
            tile_border_rgb=(101, 61, 32),
            tile_border_width_px=3,
            divider_rgb=(92, 54, 30),
            pip_rgb=(42, 25, 16),
            shadow_rgb=(21, 13, 8),
            shadow_alpha=58,
            shadow_offset_px=(6, 6),
            reference_outline_rgb=(48, 111, 193),
            reference_tag_fill_rgb=(48, 111, 193),
            reference_tag_text_rgb=(255, 255, 255),
            tile_inner_fill_rgb=(194, 138, 78),
            tile_rendering="inset",
            pip_rendering="engraved",
            divider_rendering="notch",
        )
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
    if variant == "wood_board":
        return ReversiTheme(
            board_frame_rgb=(92, 58, 32),
            board_fill_rgb=(82, 132, 78),
            grid_line_rgb=(52, 92, 54),
            badge_fill_rgb=(252, 247, 238),
            badge_outline_rgb=(118, 86, 54),
            badge_text_rgb=(42, 34, 28),
            black_disc_fill_rgb=(34, 29, 25),
            black_disc_outline_rgb=(14, 12, 10),
            black_disc_shine_rgb=(94, 82, 70),
            white_disc_fill_rgb=(251, 246, 234),
            white_disc_outline_rgb=(128, 116, 98),
            white_disc_shine_rgb=(255, 255, 255),
            disc_outline_width_px=3,
            marked_square_outline_rgb=(203, 66, 54),
            marked_square_fill_rgba=(203, 66, 54, 36),
        )
    if variant == "slate_board":
        return ReversiTheme(
            board_frame_rgb=(35, 43, 52),
            board_fill_rgb=(62, 92, 84),
            grid_line_rgb=(28, 48, 46),
            badge_fill_rgb=(238, 242, 245),
            badge_outline_rgb=(84, 96, 108),
            badge_text_rgb=(24, 30, 36),
            black_disc_fill_rgb=(18, 23, 30),
            black_disc_outline_rgb=(8, 10, 13),
            black_disc_shine_rgb=(78, 88, 98),
            white_disc_fill_rgb=(240, 244, 246),
            white_disc_outline_rgb=(118, 128, 138),
            white_disc_shine_rgb=(255, 255, 255),
            disc_outline_width_px=3,
            marked_square_outline_rgb=(226, 74, 66),
            marked_square_fill_rgba=(226, 74, 66, 38),
        )
    if variant == "blue_board":
        return ReversiTheme(
            board_frame_rgb=(32, 55, 104),
            board_fill_rgb=(74, 128, 156),
            grid_line_rgb=(30, 74, 98),
            badge_fill_rgb=(242, 247, 252),
            badge_outline_rgb=(72, 92, 130),
            badge_text_rgb=(22, 38, 62),
            black_disc_fill_rgb=(26, 30, 38),
            black_disc_outline_rgb=(10, 12, 18),
            black_disc_shine_rgb=(82, 92, 112),
            white_disc_fill_rgb=(250, 253, 255),
            white_disc_outline_rgb=(116, 130, 146),
            white_disc_shine_rgb=(255, 255, 255),
            disc_outline_width_px=3,
            marked_square_outline_rgb=(215, 64, 76),
            marked_square_fill_rgba=(215, 64, 76, 36),
        )
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
    if variant == "arcade_blue":
        return ConnectFourTheme(
            board_frame_rgb=(18, 33, 92),
            board_fill_rgb=(34, 78, 190),
            cell_well_rgb=(224, 234, 252),
            cell_well_outline_rgb=(13, 42, 132),
            cell_well_outline_width_px=4,
            badge_fill_rgb=(245, 249, 255),
            badge_outline_rgb=(35, 54, 112),
            badge_text_rgb=(20, 31, 62),
            red_disc_fill_rgb=(221, 48, 51),
            red_disc_outline_rgb=(132, 24, 28),
            red_disc_shine_rgb=(252, 150, 145),
            yellow_disc_fill_rgb=(252, 208, 45),
            yellow_disc_outline_rgb=(174, 126, 12),
            yellow_disc_shine_rgb=(255, 238, 142),
            disc_outline_width_px=4,
            marked_square_outline_rgb=(255, 255, 255),
            marked_square_fill_rgba=(255, 255, 255, 34),
            board_shadow_rgb=(8, 12, 28),
            board_shadow_alpha=58,
            board_shadow_offset_px=(8, 10),
            board_rendering="inset",
            cell_well_rendering="inset",
            disc_rendering="glossy",
        )
    if variant == "teal_frame":
        return ConnectFourTheme(
            board_frame_rgb=(18, 93, 104),
            board_fill_rgb=(34, 139, 151),
            cell_well_rgb=(235, 249, 250),
            cell_well_outline_rgb=(102, 188, 194),
            cell_well_outline_width_px=2,
            badge_fill_rgb=(245, 251, 250),
            badge_outline_rgb=(55, 127, 134),
            badge_text_rgb=(17, 52, 56),
            red_disc_fill_rgb=(205, 67, 68),
            red_disc_outline_rgb=(132, 42, 42),
            red_disc_shine_rgb=(234, 132, 130),
            yellow_disc_fill_rgb=(238, 197, 70),
            yellow_disc_outline_rgb=(164, 127, 37),
            yellow_disc_shine_rgb=(255, 226, 139),
            disc_outline_width_px=3,
            marked_square_outline_rgb=(255, 248, 180),
            marked_square_fill_rgba=(255, 248, 180, 32),
            board_shadow_rgb=(10, 34, 38),
            board_shadow_alpha=46,
            board_shadow_offset_px=(7, 8),
            board_rendering="inset",
            cell_well_rendering="ring",
            disc_rendering="flat",
        )
    if variant == "charcoal":
        return ConnectFourTheme(
            board_frame_rgb=(28, 31, 38),
            board_fill_rgb=(58, 64, 78),
            cell_well_rgb=(236, 238, 242),
            cell_well_outline_rgb=(33, 37, 46),
            cell_well_outline_width_px=3,
            badge_fill_rgb=(247, 248, 250),
            badge_outline_rgb=(71, 78, 92),
            badge_text_rgb=(24, 28, 35),
            red_disc_fill_rgb=(219, 54, 61),
            red_disc_outline_rgb=(118, 25, 33),
            red_disc_shine_rgb=(246, 139, 145),
            yellow_disc_fill_rgb=(244, 204, 64),
            yellow_disc_outline_rgb=(157, 116, 26),
            yellow_disc_shine_rgb=(255, 232, 135),
            disc_outline_width_px=4,
            marked_square_outline_rgb=(89, 170, 255),
            marked_square_fill_rgba=(89, 170, 255, 34),
            board_shadow_rgb=(4, 5, 8),
            board_shadow_alpha=56,
            board_shadow_offset_px=(7, 9),
            board_rendering="flat",
            cell_well_rendering="inset",
            disc_rendering="token",
        )
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
    if variant == "wood_token":
        return CheckersTheme(
            board_frame_rgb=(91, 54, 28),
            light_square_rgb=(238, 202, 154),
            dark_square_rgb=(139, 83, 42),
            grid_line_rgb=(101, 59, 30),
            grid_line_width_px=2,
            badge_fill_rgb=(250, 245, 238),
            badge_outline_rgb=(111, 75, 46),
            badge_text_rgb=(40, 27, 18),
            red_piece_fill_rgb=(206, 57, 51),
            red_piece_outline_rgb=(126, 32, 28),
            red_piece_shine_rgb=(244, 158, 150),
            black_piece_fill_rgb=(37, 29, 26),
            black_piece_outline_rgb=(14, 11, 10),
            black_piece_shine_rgb=(108, 92, 82),
            piece_outline_width_px=4,
            piece_shadow_rgb=(16, 10, 6),
            piece_shadow_alpha=46,
            piece_rendering="double_ring",
            square_rendering="inset",
        )
    if variant == "blue_table":
        return CheckersTheme(
            board_frame_rgb=(42, 62, 92),
            light_square_rgb=(240, 247, 253),
            dark_square_rgb=(94, 128, 172),
            grid_line_rgb=(60, 80, 112),
            grid_line_width_px=2,
            badge_fill_rgb=(246, 249, 253),
            badge_outline_rgb=(74, 91, 116),
            badge_text_rgb=(20, 29, 42),
            red_piece_fill_rgb=(218, 70, 64),
            red_piece_outline_rgb=(137, 38, 34),
            red_piece_shine_rgb=(246, 170, 160),
            black_piece_fill_rgb=(23, 29, 40),
            black_piece_outline_rgb=(8, 12, 18),
            black_piece_shine_rgb=(86, 102, 124),
            piece_outline_width_px=3,
            piece_shadow_rgb=(8, 13, 20),
            piece_shadow_alpha=34,
            piece_rendering="flat",
            square_rendering="flat",
        )
    if variant == "charcoal":
        return CheckersTheme(
            board_frame_rgb=(52, 54, 58),
            light_square_rgb=(236, 236, 230),
            dark_square_rgb=(126, 128, 132),
            grid_line_rgb=(66, 68, 72),
            grid_line_width_px=3,
            badge_fill_rgb=(248, 248, 246),
            badge_outline_rgb=(84, 86, 90),
            badge_text_rgb=(24, 25, 27),
            red_piece_fill_rgb=(196, 50, 54),
            red_piece_outline_rgb=(122, 27, 31),
            red_piece_shine_rgb=(235, 144, 146),
            black_piece_fill_rgb=(22, 23, 25),
            black_piece_outline_rgb=(6, 7, 8),
            black_piece_shine_rgb=(92, 96, 102),
            piece_outline_width_px=4,
            piece_shadow_rgb=(6, 7, 8),
            piece_shadow_alpha=28,
            piece_rendering="ring",
            square_rendering="inset",
        )
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
            piece_shadow_rgb=(14, 16, 18),
            piece_shadow_alpha=24,
            piece_rendering="ring",
            square_rendering="flat",
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
            piece_shadow_rgb=(10, 12, 14),
            piece_shadow_alpha=20,
            piece_rendering="double_ring",
            square_rendering="inset",
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
        piece_shadow_rgb=(12, 14, 16),
        piece_shadow_alpha=26,
        piece_rendering="ring",
        square_rendering="flat",
    )


def build_games_chess_theme(*, style_variant: str) -> ChessTheme:
    """Return one resolved Chess-board theme for the active style variant."""

    variant = str(style_variant)
    if variant == "wood_token":
        return ChessTheme(
            board_frame_rgb=(91, 54, 28),
            light_square_rgb=(236, 202, 154),
            dark_square_rgb=(139, 83, 42),
            grid_line_rgb=(99, 58, 30),
            grid_line_width_px=2,
            badge_fill_rgb=(250, 245, 238),
            badge_outline_rgb=(111, 75, 46),
            badge_text_rgb=(40, 27, 18),
            white_piece_fill_rgb=(255, 249, 235),
            white_piece_outline_rgb=(71, 55, 44),
            black_piece_fill_rgb=(37, 29, 26),
            black_piece_outline_rgb=(238, 224, 204),
            marked_square_outline_rgb=(32, 96, 196),
            marked_square_fill_rgba=(32, 96, 196, 36),
            piece_shadow_rgb=(18, 12, 8),
            piece_shadow_alpha=52,
            piece_rendering="token",
            square_rendering="inset",
        )
    if variant == "blue_glyph":
        return ChessTheme(
            board_frame_rgb=(41, 61, 91),
            light_square_rgb=(242, 247, 253),
            dark_square_rgb=(94, 129, 173),
            grid_line_rgb=(58, 80, 112),
            grid_line_width_px=2,
            badge_fill_rgb=(246, 249, 253),
            badge_outline_rgb=(74, 91, 116),
            badge_text_rgb=(20, 29, 42),
            white_piece_fill_rgb=(255, 255, 252),
            white_piece_outline_rgb=(22, 33, 51),
            black_piece_fill_rgb=(20, 27, 38),
            black_piece_outline_rgb=(245, 249, 255),
            marked_square_outline_rgb=(217, 96, 36),
            marked_square_fill_rgba=(217, 96, 36, 38),
            piece_shadow_rgb=(8, 13, 20),
            piece_shadow_alpha=26,
            piece_rendering="glyph",
            square_rendering="flat",
        )
    if variant == "monochrome_glyph":
        return ChessTheme(
            board_frame_rgb=(54, 56, 60),
            light_square_rgb=(238, 238, 232),
            dark_square_rgb=(126, 128, 132),
            grid_line_rgb=(66, 68, 72),
            grid_line_width_px=3,
            badge_fill_rgb=(248, 248, 246),
            badge_outline_rgb=(84, 86, 90),
            badge_text_rgb=(24, 25, 27),
            white_piece_fill_rgb=(255, 255, 252),
            white_piece_outline_rgb=(18, 19, 21),
            black_piece_fill_rgb=(20, 21, 23),
            black_piece_outline_rgb=(245, 245, 242),
            marked_square_outline_rgb=(41, 116, 201),
            marked_square_fill_rgba=(41, 116, 201, 32),
            piece_shadow_rgb=(6, 7, 8),
            piece_shadow_alpha=20,
            piece_rendering="glyph",
            square_rendering="inset",
        )
    if variant == "soft":
        return ChessTheme(
            board_frame_rgb=(88, 67, 48),
            light_square_rgb=(232, 221, 202),
            dark_square_rgb=(112, 142, 108),
            grid_line_rgb=(86, 96, 82),
            grid_line_width_px=2,
            badge_fill_rgb=(241, 244, 247),
            badge_outline_rgb=(102, 112, 122),
            badge_text_rgb=(32, 38, 44),
            white_piece_fill_rgb=(250, 250, 244),
            white_piece_outline_rgb=(58, 64, 72),
            black_piece_fill_rgb=(34, 38, 44),
            black_piece_outline_rgb=(238, 240, 244),
            marked_square_outline_rgb=(49, 112, 214),
            marked_square_fill_rgba=(49, 112, 214, 38),
            piece_shadow_rgb=(15, 20, 18),
            piece_shadow_alpha=46,
            piece_rendering="token",
            square_rendering="flat",
        )
    if variant == "outlined":
        return ChessTheme(
            board_frame_rgb=(62, 70, 80),
            light_square_rgb=(255, 255, 255),
            dark_square_rgb=(116, 154, 122),
            grid_line_rgb=(78, 90, 98),
            grid_line_width_px=3,
            badge_fill_rgb=(255, 255, 255),
            badge_outline_rgb=(72, 82, 92),
            badge_text_rgb=(26, 30, 36),
            white_piece_fill_rgb=(255, 255, 255),
            white_piece_outline_rgb=(42, 48, 56),
            black_piece_fill_rgb=(28, 32, 38),
            black_piece_outline_rgb=(255, 255, 255),
            marked_square_outline_rgb=(45, 104, 210),
            marked_square_fill_rgba=(45, 104, 210, 30),
            piece_shadow_rgb=(12, 16, 18),
            piece_shadow_alpha=34,
            piece_rendering="token",
            square_rendering="inset",
        )
    return ChessTheme(
        board_frame_rgb=(76, 59, 42),
        light_square_rgb=(242, 232, 212),
        dark_square_rgb=(104, 137, 98),
        grid_line_rgb=(76, 86, 72),
        grid_line_width_px=2,
        badge_fill_rgb=(248, 249, 251),
        badge_outline_rgb=(94, 102, 110),
        badge_text_rgb=(27, 32, 38),
        white_piece_fill_rgb=(255, 254, 248),
        white_piece_outline_rgb=(52, 58, 66),
        black_piece_fill_rgb=(31, 35, 41),
        black_piece_outline_rgb=(242, 244, 248),
        marked_square_outline_rgb=(43, 101, 204),
        marked_square_fill_rgba=(43, 101, 204, 34),
        piece_shadow_rgb=(14, 18, 20),
        piece_shadow_alpha=42,
        piece_rendering="token",
        square_rendering="flat",
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
            cell_alt_fill_rgb=(248, 241, 231),
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
            cell_alt_fill_rgb=(242, 246, 255),
            number_rgb=(33, 38, 44),
            mark_fill_rgba=(218, 66, 60, 126),
            mark_outline_rgb=(196, 48, 44),
        )
    if variant == "mint":
        return BingoTheme(
            card_fill_rgb=(239, 250, 242),
            card_border_rgb=(63, 118, 95),
            card_border_width_px=3,
            shadow_rgb=(12, 30, 23),
            shadow_alpha=46,
            shadow_offset_px=(5, 6),
            title_rgb=(29, 94, 76),
            header_rgb=(35, 104, 86),
            grid_line_rgb=(103, 151, 132),
            cell_fill_rgb=(252, 255, 250),
            cell_alt_fill_rgb=(229, 246, 238),
            number_rgb=(28, 47, 43),
            mark_fill_rgba=(56, 122, 210, 130),
            mark_outline_rgb=(42, 91, 170),
        )
    if variant == "lavender":
        return BingoTheme(
            card_fill_rgb=(246, 243, 255),
            card_border_rgb=(102, 91, 151),
            card_border_width_px=3,
            shadow_rgb=(24, 21, 42),
            shadow_alpha=44,
            shadow_offset_px=(5, 5),
            title_rgb=(91, 69, 153),
            header_rgb=(105, 75, 166),
            grid_line_rgb=(145, 134, 182),
            cell_fill_rgb=(255, 253, 255),
            cell_alt_fill_rgb=(238, 235, 252),
            number_rgb=(38, 35, 50),
            mark_fill_rgba=(218, 141, 45, 138),
            mark_outline_rgb=(180, 112, 28),
        )
    if variant == "amber":
        return BingoTheme(
            card_fill_rgb=(255, 248, 231),
            card_border_rgb=(129, 91, 41),
            card_border_width_px=3,
            shadow_rgb=(36, 25, 13),
            shadow_alpha=48,
            shadow_offset_px=(5, 6),
            title_rgb=(127, 78, 25),
            header_rgb=(145, 85, 28),
            grid_line_rgb=(173, 135, 82),
            cell_fill_rgb=(255, 254, 248),
            cell_alt_fill_rgb=(250, 238, 212),
            number_rgb=(44, 36, 26),
            mark_fill_rgba=(48, 128, 116, 132),
            mark_outline_rgb=(28, 101, 93),
        )
    if variant == "slate":
        return BingoTheme(
            card_fill_rgb=(241, 245, 249),
            card_border_rgb=(67, 78, 93),
            card_border_width_px=4,
            shadow_rgb=(8, 12, 18),
            shadow_alpha=50,
            shadow_offset_px=(4, 6),
            title_rgb=(31, 71, 118),
            header_rgb=(39, 82, 129),
            grid_line_rgb=(111, 123, 138),
            cell_fill_rgb=(255, 255, 255),
            cell_alt_fill_rgb=(231, 238, 246),
            number_rgb=(24, 31, 40),
            mark_fill_rgba=(196, 64, 102, 132),
            mark_outline_rgb=(166, 43, 78),
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
        cell_alt_fill_rgb=(242, 247, 255),
        number_rgb=(29, 34, 40),
        mark_fill_rgba=(212, 62, 56, 132),
        mark_outline_rgb=(190, 46, 42),
    )


def build_games_dots_and_boxes_theme(*, style_variant: str) -> DotsAndBoxesTheme:
    """Return one resolved dots-and-boxes theme for the active style variant."""

    variant = str(style_variant)
    if variant == "notebook":
        return DotsAndBoxesTheme(
            board_fill_rgb=(255, 253, 246),
            board_border_rgb=(94, 112, 145),
            board_border_width_px=3,
            shadow_rgb=(15, 23, 42),
            shadow_alpha=44,
            shadow_offset_px=(5, 6),
            title_rgb=(42, 85, 176),
            dot_rgb=(25, 31, 42),
            edge_rgb=(38, 48, 66),
            edge_width_px=7,
            highlight_rgb=(214, 62, 58),
            highlight_width_px=10,
            guide_rgb=(184, 199, 224),
            board_inner_fill_rgb=(255, 255, 252),
            board_pattern_rgb=(159, 191, 226),
            board_pattern_alpha=46,
            board_rendering="notebook",
            dot_outline_rgb=(255, 255, 255),
            dot_rendering="outlined",
        )
    if variant == "slate":
        return DotsAndBoxesTheme(
            board_fill_rgb=(53, 61, 73),
            board_border_rgb=(194, 204, 216),
            board_border_width_px=4,
            shadow_rgb=(3, 6, 12),
            shadow_alpha=62,
            shadow_offset_px=(5, 7),
            title_rgb=(240, 244, 248),
            dot_rgb=(236, 240, 245),
            edge_rgb=(224, 231, 238),
            edge_width_px=8,
            highlight_rgb=(90, 203, 255),
            highlight_width_px=10,
            guide_rgb=(120, 132, 150),
            board_inner_fill_rgb=(62, 71, 84),
            board_pattern_rgb=(148, 163, 184),
            board_pattern_alpha=28,
            board_rendering="inset",
            dot_outline_rgb=(23, 29, 38),
            dot_rendering="outlined",
        )
    if variant == "wood_panel":
        return DotsAndBoxesTheme(
            board_fill_rgb=(172, 118, 72),
            board_border_rgb=(91, 55, 30),
            board_border_width_px=4,
            shadow_rgb=(18, 10, 6),
            shadow_alpha=58,
            shadow_offset_px=(6, 7),
            title_rgb=(56, 34, 20),
            dot_rgb=(42, 25, 15),
            edge_rgb=(55, 33, 20),
            edge_width_px=8,
            highlight_rgb=(33, 104, 196),
            highlight_width_px=10,
            guide_rgb=(136, 89, 52),
            board_inner_fill_rgb=(205, 154, 101),
            board_pattern_rgb=(121, 75, 39),
            board_pattern_alpha=34,
            board_rendering="wood",
            dot_outline_rgb=(232, 190, 137),
            dot_rendering="outlined",
        )
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


def build_games_nine_mens_morris_theme(*, style_variant: str) -> NineMensMorrisTheme:
    """Return one resolved nine-men's-morris theme for the active style variant."""

    variant = str(style_variant)
    if variant == "wood_panel":
        return NineMensMorrisTheme(
            board_fill_rgb=(222, 184, 128),
            board_border_rgb=(100, 66, 38),
            board_border_width_px=4,
            shadow_rgb=(18, 16, 12),
            shadow_alpha=58,
            shadow_offset_px=(6, 7),
            title_rgb=(78, 48, 28),
            line_rgb=(86, 56, 34),
            line_width_px=7,
            node_rgb=(70, 44, 28),
            white_piece_fill_rgb=(252, 246, 232),
            white_piece_outline_rgb=(118, 94, 70),
            black_piece_fill_rgb=(48, 36, 30),
            black_piece_outline_rgb=(18, 14, 12),
        )
    if variant == "slate":
        return NineMensMorrisTheme(
            board_fill_rgb=(54, 66, 78),
            board_border_rgb=(24, 30, 38),
            board_border_width_px=4,
            shadow_rgb=(8, 10, 14),
            shadow_alpha=72,
            shadow_offset_px=(5, 6),
            title_rgb=(226, 232, 238),
            line_rgb=(198, 206, 214),
            line_width_px=6,
            node_rgb=(222, 228, 234),
            white_piece_fill_rgb=(246, 248, 250),
            white_piece_outline_rgb=(132, 144, 156),
            black_piece_fill_rgb=(22, 28, 36),
            black_piece_outline_rgb=(6, 8, 12),
        )
    if variant == "parchment":
        return NineMensMorrisTheme(
            board_fill_rgb=(248, 236, 204),
            board_border_rgb=(124, 88, 52),
            board_border_width_px=4,
            shadow_rgb=(38, 28, 18),
            shadow_alpha=44,
            shadow_offset_px=(4, 5),
            title_rgb=(98, 66, 38),
            line_rgb=(110, 78, 48),
            line_width_px=6,
            node_rgb=(92, 62, 40),
            white_piece_fill_rgb=(255, 252, 242),
            white_piece_outline_rgb=(128, 112, 90),
            black_piece_fill_rgb=(54, 48, 42),
            black_piece_outline_rgb=(22, 18, 16),
        )
    if variant == "soft":
        return NineMensMorrisTheme(
            board_fill_rgb=(248, 242, 230),
            board_border_rgb=(102, 112, 124),
            board_border_width_px=3,
            shadow_rgb=(18, 24, 20),
            shadow_alpha=56,
            shadow_offset_px=(5, 6),
            title_rgb=(48, 76, 134),
            line_rgb=(86, 94, 106),
            line_width_px=6,
            node_rgb=(72, 80, 92),
            white_piece_fill_rgb=(252, 250, 244),
            white_piece_outline_rgb=(112, 118, 126),
            black_piece_fill_rgb=(58, 64, 72),
            black_piece_outline_rgb=(24, 28, 34),
        )
    if variant == "outlined":
        return NineMensMorrisTheme(
            board_fill_rgb=(255, 255, 255),
            board_border_rgb=(62, 70, 80),
            board_border_width_px=4,
            shadow_rgb=(14, 18, 20),
            shadow_alpha=40,
            shadow_offset_px=(4, 5),
            title_rgb=(44, 75, 168),
            line_rgb=(58, 64, 72),
            line_width_px=6,
            node_rgb=(46, 52, 60),
            white_piece_fill_rgb=(255, 255, 255),
            white_piece_outline_rgb=(112, 118, 126),
            black_piece_fill_rgb=(42, 48, 56),
            black_piece_outline_rgb=(18, 22, 28),
        )
    return NineMensMorrisTheme(
        board_fill_rgb=(255, 252, 244),
        board_border_rgb=(74, 82, 92),
        board_border_width_px=3,
        shadow_rgb=(18, 22, 24),
        shadow_alpha=48,
        shadow_offset_px=(4, 5),
        title_rgb=(45, 76, 160),
        line_rgb=(66, 72, 82),
        line_width_px=6,
        node_rgb=(44, 50, 58),
        white_piece_fill_rgb=(254, 252, 248),
        white_piece_outline_rgb=(106, 112, 120),
        black_piece_fill_rgb=(36, 42, 50),
        black_piece_outline_rgb=(18, 22, 28),
    )


def build_games_go_theme(*, style_variant: str) -> GoTheme:
    """Return one resolved Go-board theme for the active style variant."""

    variant = str(style_variant)
    if variant == "wood_board":
        return GoTheme(
            board_frame_rgb=(126, 78, 38),
            board_fill_rgb=(222, 172, 94),
            grid_line_rgb=(92, 54, 24),
            point_rgb=(86, 50, 22),
            black_stone_fill_rgb=(34, 32, 30),
            black_stone_outline_rgb=(12, 12, 12),
            black_stone_shine_rgb=(88, 82, 74),
            white_stone_fill_rgb=(252, 246, 232),
            white_stone_outline_rgb=(124, 112, 96),
            white_stone_shine_rgb=(255, 255, 255),
            stone_outline_width_px=2,
            highlight_outline_rgb=(42, 116, 218),
            highlight_fill_rgba=(82, 142, 236, 52),
        )
    if variant == "slate_board":
        return GoTheme(
            board_frame_rgb=(42, 50, 60),
            board_fill_rgb=(96, 114, 126),
            grid_line_rgb=(34, 42, 52),
            point_rgb=(30, 38, 48),
            black_stone_fill_rgb=(18, 22, 28),
            black_stone_outline_rgb=(6, 8, 12),
            black_stone_shine_rgb=(78, 88, 98),
            white_stone_fill_rgb=(240, 244, 246),
            white_stone_outline_rgb=(118, 128, 138),
            white_stone_shine_rgb=(255, 255, 255),
            stone_outline_width_px=2,
            highlight_outline_rgb=(78, 158, 244),
            highlight_fill_rgba=(86, 158, 244, 58),
        )
    if variant == "paper_board":
        return GoTheme(
            board_frame_rgb=(102, 110, 118),
            board_fill_rgb=(251, 247, 236),
            grid_line_rgb=(76, 82, 88),
            point_rgb=(68, 74, 82),
            black_stone_fill_rgb=(42, 46, 54),
            black_stone_outline_rgb=(16, 20, 26),
            black_stone_shine_rgb=(108, 116, 126),
            white_stone_fill_rgb=(255, 255, 255),
            white_stone_outline_rgb=(126, 134, 142),
            white_stone_shine_rgb=(255, 255, 255),
            stone_outline_width_px=3,
            highlight_outline_rgb=(52, 116, 222),
            highlight_fill_rgba=(86, 145, 235, 46),
        )
    if variant == "soft":
        return GoTheme(
            board_frame_rgb=(120, 89, 56),
            board_fill_rgb=(214, 181, 126),
            grid_line_rgb=(88, 64, 38),
            point_rgb=(80, 58, 34),
            black_stone_fill_rgb=(50, 56, 64),
            black_stone_outline_rgb=(20, 24, 30),
            black_stone_shine_rgb=(107, 114, 122),
            white_stone_fill_rgb=(247, 245, 238),
            white_stone_outline_rgb=(128, 132, 140),
            white_stone_shine_rgb=(255, 255, 255),
            stone_outline_width_px=2,
            highlight_outline_rgb=(67, 132, 223),
            highlight_fill_rgba=(93, 156, 240, 52),
        )
    if variant == "outlined":
        return GoTheme(
            board_frame_rgb=(82, 88, 98),
            board_fill_rgb=(255, 250, 241),
            grid_line_rgb=(78, 82, 90),
            point_rgb=(72, 78, 88),
            black_stone_fill_rgb=(48, 54, 62),
            black_stone_outline_rgb=(18, 22, 28),
            black_stone_shine_rgb=(110, 116, 126),
            white_stone_fill_rgb=(255, 255, 255),
            white_stone_outline_rgb=(130, 136, 144),
            white_stone_shine_rgb=(255, 255, 255),
            stone_outline_width_px=3,
            highlight_outline_rgb=(52, 116, 222),
            highlight_fill_rgba=(86, 145, 235, 44),
        )
    return GoTheme(
        board_frame_rgb=(118, 86, 48),
        board_fill_rgb=(225, 190, 128),
        grid_line_rgb=(86, 58, 30),
        point_rgb=(80, 54, 28),
        black_stone_fill_rgb=(42, 48, 56),
        black_stone_outline_rgb=(18, 22, 28),
        black_stone_shine_rgb=(102, 108, 118),
        white_stone_fill_rgb=(252, 250, 244),
        white_stone_outline_rgb=(124, 128, 136),
        white_stone_shine_rgb=(255, 255, 255),
        stone_outline_width_px=2,
        highlight_outline_rgb=(46, 113, 228),
        highlight_fill_rgba=(82, 142, 236, 46),
    )


def build_games_sudoku_theme(*, style_variant: str) -> SudokuTheme:
    """Return one resolved Sudoku-grid theme for the active style variant."""

    variant = str(style_variant)
    if variant == "notebook":
        return SudokuTheme(
            board_fill_rgb=(248, 251, 255),
            board_border_rgb=(56, 82, 122),
            grid_line_rgb=(180, 204, 226),
            box_line_rgb=(62, 98, 150),
            cell_fill_rgb=(253, 255, 255),
            highlighted_cell_fill_rgba=(80, 148, 220, 54),
            marked_cell_fill_rgba=(218, 70, 82, 46),
            marked_cell_outline_rgb=(190, 48, 62),
            digit_rgb=(34, 56, 86),
            conflict_digit_rgb=(174, 42, 58),
        )
    if variant == "slate":
        return SudokuTheme(
            board_fill_rgb=(48, 58, 70),
            board_border_rgb=(20, 26, 34),
            grid_line_rgb=(106, 120, 134),
            box_line_rgb=(226, 232, 238),
            cell_fill_rgb=(58, 70, 84),
            highlighted_cell_fill_rgba=(86, 160, 236, 64),
            marked_cell_fill_rgba=(228, 78, 86, 56),
            marked_cell_outline_rgb=(245, 100, 106),
            digit_rgb=(238, 242, 246),
            conflict_digit_rgb=(255, 138, 126),
        )
    if variant == "warm_paper":
        return SudokuTheme(
            board_fill_rgb=(250, 240, 218),
            board_border_rgb=(104, 76, 48),
            grid_line_rgb=(188, 164, 132),
            box_line_rgb=(92, 66, 42),
            cell_fill_rgb=(255, 248, 232),
            highlighted_cell_fill_rgba=(74, 134, 208, 54),
            marked_cell_fill_rgba=(210, 76, 62, 46),
            marked_cell_outline_rgb=(178, 54, 44),
            digit_rgb=(54, 42, 32),
            conflict_digit_rgb=(162, 48, 42),
        )
    if variant == "soft":
        return SudokuTheme(
            board_fill_rgb=(250, 248, 241),
            board_border_rgb=(95, 100, 110),
            grid_line_rgb=(169, 174, 181),
            box_line_rgb=(72, 78, 88),
            cell_fill_rgb=(255, 253, 247),
            highlighted_cell_fill_rgba=(88, 150, 232, 56),
            marked_cell_fill_rgba=(229, 75, 75, 46),
            marked_cell_outline_rgb=(196, 46, 54),
            digit_rgb=(38, 44, 54),
            conflict_digit_rgb=(174, 44, 57),
        )
    if variant == "outlined":
        return SudokuTheme(
            board_fill_rgb=(255, 255, 255),
            board_border_rgb=(50, 58, 70),
            grid_line_rgb=(138, 145, 154),
            box_line_rgb=(42, 50, 62),
            cell_fill_rgb=(252, 253, 255),
            highlighted_cell_fill_rgba=(58, 123, 220, 62),
            marked_cell_fill_rgba=(215, 54, 64, 50),
            marked_cell_outline_rgb=(174, 34, 48),
            digit_rgb=(28, 34, 44),
            conflict_digit_rgb=(160, 34, 50),
        )
    return SudokuTheme(
        board_fill_rgb=(246, 244, 236),
        board_border_rgb=(66, 72, 82),
        grid_line_rgb=(156, 160, 166),
        box_line_rgb=(48, 54, 64),
        cell_fill_rgb=(255, 254, 249),
        highlighted_cell_fill_rgba=(70, 136, 226, 58),
        marked_cell_fill_rgba=(216, 56, 66, 48),
        marked_cell_outline_rgb=(184, 38, 50),
        digit_rgb=(34, 40, 50),
        conflict_digit_rgb=(168, 36, 50),
    )


def build_games_minesweeper_theme(*, style_variant: str) -> MinesweeperTheme:
    """Return one resolved Minesweeper-grid theme for the active style variant."""

    number_colors: Tuple[Tuple[int, int, int], ...] = (
        (92, 96, 104),
        (42, 96, 196),
        (38, 132, 72),
        (195, 54, 62),
        (100, 74, 170),
        (178, 92, 36),
        (38, 136, 152),
        (72, 78, 88),
        (36, 40, 46),
    )
    dark_number_colors: Tuple[Tuple[int, int, int], ...] = (
        (176, 184, 194),
        (92, 156, 255),
        (118, 210, 142),
        (255, 120, 126),
        (190, 150, 255),
        (244, 174, 96),
        (92, 210, 224),
        (210, 218, 228),
        (246, 248, 250),
    )
    variant = str(style_variant)
    if variant == "notebook":
        return MinesweeperTheme(
            board_fill_rgb=(246, 250, 255),
            board_border_rgb=(54, 82, 118),
            grid_line_rgb=(174, 198, 222),
            hidden_cell_fill_rgb=(210, 226, 242),
            hidden_cell_border_rgb=(92, 126, 162),
            revealed_cell_fill_rgb=(252, 254, 255),
            revealed_cell_alt_fill_rgb=(244, 249, 255),
            number_rgb_by_value=number_colors,
            flag_rgb=(204, 50, 64),
            flag_pole_rgb=(42, 64, 92),
        )
    if variant == "dark":
        return MinesweeperTheme(
            board_fill_rgb=(36, 44, 54),
            board_border_rgb=(14, 18, 24),
            grid_line_rgb=(82, 94, 108),
            hidden_cell_fill_rgb=(72, 86, 102),
            hidden_cell_border_rgb=(142, 154, 168),
            revealed_cell_fill_rgb=(48, 58, 70),
            revealed_cell_alt_fill_rgb=(54, 66, 78),
            number_rgb_by_value=dark_number_colors,
            flag_rgb=(244, 82, 92),
            flag_pole_rgb=(226, 232, 238),
        )
    if variant == "retro":
        return MinesweeperTheme(
            board_fill_rgb=(184, 188, 192),
            board_border_rgb=(70, 74, 78),
            grid_line_rgb=(122, 126, 130),
            hidden_cell_fill_rgb=(198, 202, 206),
            hidden_cell_border_rgb=(86, 90, 94),
            revealed_cell_fill_rgb=(230, 230, 226),
            revealed_cell_alt_fill_rgb=(222, 222, 218),
            number_rgb_by_value=number_colors,
            flag_rgb=(206, 30, 42),
            flag_pole_rgb=(34, 36, 38),
        )
    if variant == "soft":
        return MinesweeperTheme(
            board_fill_rgb=(240, 237, 228),
            board_border_rgb=(104, 110, 120),
            grid_line_rgb=(178, 182, 190),
            hidden_cell_fill_rgb=(202, 210, 216),
            hidden_cell_border_rgb=(128, 136, 146),
            revealed_cell_fill_rgb=(248, 246, 239),
            revealed_cell_alt_fill_rgb=(241, 239, 232),
            number_rgb_by_value=number_colors,
            flag_rgb=(210, 54, 64),
            flag_pole_rgb=(66, 72, 82),
        )
    if variant == "outlined":
        return MinesweeperTheme(
            board_fill_rgb=(252, 253, 255),
            board_border_rgb=(54, 62, 74),
            grid_line_rgb=(142, 150, 160),
            hidden_cell_fill_rgb=(212, 218, 225),
            hidden_cell_border_rgb=(82, 92, 106),
            revealed_cell_fill_rgb=(255, 255, 255),
            revealed_cell_alt_fill_rgb=(248, 250, 252),
            number_rgb_by_value=number_colors,
            flag_rgb=(202, 42, 58),
            flag_pole_rgb=(42, 50, 60),
        )
    return MinesweeperTheme(
        board_fill_rgb=(235, 232, 224),
        board_border_rgb=(72, 78, 88),
        grid_line_rgb=(152, 158, 166),
        hidden_cell_fill_rgb=(190, 198, 206),
        hidden_cell_border_rgb=(96, 104, 114),
        revealed_cell_fill_rgb=(246, 244, 238),
        revealed_cell_alt_fill_rgb=(238, 236, 230),
        number_rgb_by_value=number_colors,
        flag_rgb=(204, 48, 58),
        flag_pole_rgb=(54, 60, 70),
    )


def build_games_battleship_theme(*, style_variant: str) -> BattleshipTheme:
    """Return one resolved Battleship tracking-grid theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return BattleshipTheme(
            board_fill_rgb=(226, 238, 244),
            board_border_rgb=(68, 92, 108),
            grid_line_rgb=(150, 174, 190),
            cell_fill_rgb=(238, 248, 252),
            cell_alt_fill_rgb=(230, 242, 248),
            hit_fill_rgb=(218, 62, 66),
            hit_outline_rgb=(128, 32, 38),
            miss_rgb=(78, 122, 148),
            panel_fill_rgb=(248, 250, 246),
            panel_border_rgb=(108, 122, 132),
            panel_text_rgb=(34, 44, 54),
            ship_icon_fill_rgb=(104, 122, 136),
            ship_icon_outline_rgb=(42, 52, 64),
            hit_marker_style="disc",
            miss_marker_style="ring",
        )
    if variant == "outlined":
        return BattleshipTheme(
            board_fill_rgb=(255, 255, 255),
            board_border_rgb=(42, 52, 64),
            grid_line_rgb=(120, 132, 146),
            cell_fill_rgb=(253, 254, 255),
            cell_alt_fill_rgb=(246, 248, 251),
            hit_fill_rgb=(210, 44, 58),
            hit_outline_rgb=(96, 22, 32),
            miss_rgb=(54, 94, 126),
            panel_fill_rgb=(255, 255, 255),
            panel_border_rgb=(52, 62, 76),
            panel_text_rgb=(24, 30, 38),
            ship_icon_fill_rgb=(96, 104, 116),
            ship_icon_outline_rgb=(28, 34, 44),
            hit_marker_style="cross",
            miss_marker_style="cross",
        )
    if variant == "navy":
        return BattleshipTheme(
            board_fill_rgb=(20, 42, 66),
            board_border_rgb=(8, 16, 28),
            grid_line_rgb=(70, 108, 140),
            cell_fill_rgb=(31, 62, 92),
            cell_alt_fill_rgb=(26, 54, 82),
            hit_fill_rgb=(246, 78, 78),
            hit_outline_rgb=(255, 198, 198),
            miss_rgb=(160, 210, 232),
            panel_fill_rgb=(24, 38, 54),
            panel_border_rgb=(118, 154, 178),
            panel_text_rgb=(230, 238, 244),
            ship_icon_fill_rgb=(150, 166, 178),
            ship_icon_outline_rgb=(230, 238, 244),
            hit_marker_style="disc",
            miss_marker_style="ring",
        )
    if variant == "radar":
        return BattleshipTheme(
            board_fill_rgb=(24, 58, 46),
            board_border_rgb=(10, 30, 24),
            grid_line_rgb=(80, 150, 112),
            cell_fill_rgb=(34, 76, 58),
            cell_alt_fill_rgb=(30, 68, 52),
            hit_fill_rgb=(238, 74, 58),
            hit_outline_rgb=(122, 26, 24),
            miss_rgb=(176, 224, 190),
            panel_fill_rgb=(232, 244, 232),
            panel_border_rgb=(62, 104, 78),
            panel_text_rgb=(24, 52, 38),
            ship_icon_fill_rgb=(86, 120, 92),
            ship_icon_outline_rgb=(24, 52, 38),
            hit_marker_style="square",
            miss_marker_style="ring",
        )
    if variant == "paper":
        return BattleshipTheme(
            board_fill_rgb=(244, 239, 224),
            board_border_rgb=(90, 78, 62),
            grid_line_rgb=(176, 158, 132),
            cell_fill_rgb=(255, 252, 240),
            cell_alt_fill_rgb=(248, 243, 228),
            hit_fill_rgb=(198, 52, 50),
            hit_outline_rgb=(116, 34, 30),
            miss_rgb=(78, 106, 138),
            panel_fill_rgb=(252, 248, 236),
            panel_border_rgb=(112, 96, 74),
            panel_text_rgb=(48, 42, 34),
            ship_icon_fill_rgb=(122, 112, 98),
            ship_icon_outline_rgb=(58, 50, 42),
            hit_marker_style="cross",
            miss_marker_style="dot",
        )
    return BattleshipTheme(
        board_fill_rgb=(212, 230, 238),
        board_border_rgb=(42, 72, 94),
        grid_line_rgb=(126, 160, 182),
        cell_fill_rgb=(232, 246, 252),
        cell_alt_fill_rgb=(222, 238, 246),
        hit_fill_rgb=(222, 58, 64),
        hit_outline_rgb=(110, 26, 34),
        miss_rgb=(58, 108, 142),
        panel_fill_rgb=(246, 248, 244),
        panel_border_rgb=(86, 104, 116),
        panel_text_rgb=(30, 38, 48),
        ship_icon_fill_rgb=(98, 116, 130),
        ship_icon_outline_rgb=(36, 46, 58),
        hit_marker_style="disc",
        miss_marker_style="ring",
    )


def build_games_pool_theme(*, style_variant: str) -> PoolTheme:
    """Return one resolved Pool-table theme for the active style variant."""

    variant = str(style_variant)
    if variant == "tournament_blue":
        return PoolTheme(
            rail_rgb=(34, 42, 54),
            rail_outline_rgb=(10, 16, 24),
            cloth_rgb=(38, 94, 132),
            cloth_line_rgb=(96, 156, 190),
            pocket_rgb=(5, 8, 12),
            pocket_outline_rgb=(194, 214, 226),
            ball_outline_rgb=(26, 30, 38),
            ball_shadow_rgb=(6, 10, 14),
            marker_rgb=(255, 214, 92),
            marker_fill_rgba=(255, 214, 92, 50),
            badge_fill_rgb=(238, 246, 250),
            badge_outline_rgb=(50, 78, 102),
            badge_text_rgb=(20, 32, 44),
            shot_line_rgb=(255, 224, 92),
        )
    if variant == "burgundy":
        return PoolTheme(
            rail_rgb=(78, 42, 36),
            rail_outline_rgb=(32, 18, 16),
            cloth_rgb=(92, 36, 52),
            cloth_line_rgb=(154, 94, 108),
            pocket_rgb=(12, 8, 10),
            pocket_outline_rgb=(218, 186, 160),
            ball_outline_rgb=(34, 24, 24),
            ball_shadow_rgb=(16, 6, 10),
            marker_rgb=(250, 206, 94),
            marker_fill_rgba=(250, 206, 94, 52),
            badge_fill_rgb=(252, 242, 232),
            badge_outline_rgb=(116, 72, 62),
            badge_text_rgb=(48, 28, 24),
            shot_line_rgb=(255, 220, 104),
        )
    if variant == "charcoal":
        return PoolTheme(
            rail_rgb=(32, 36, 42),
            rail_outline_rgb=(8, 10, 12),
            cloth_rgb=(48, 74, 68),
            cloth_line_rgb=(116, 144, 136),
            pocket_rgb=(4, 5, 6),
            pocket_outline_rgb=(176, 188, 184),
            ball_outline_rgb=(18, 20, 22),
            ball_shadow_rgb=(4, 5, 6),
            marker_rgb=(248, 214, 76),
            marker_fill_rgba=(248, 214, 76, 52),
            badge_fill_rgb=(236, 240, 238),
            badge_outline_rgb=(72, 84, 82),
            badge_text_rgb=(28, 34, 34),
            shot_line_rgb=(250, 216, 78),
        )
    if variant == "light_rail":
        return PoolTheme(
            rail_rgb=(156, 128, 88),
            rail_outline_rgb=(78, 58, 36),
            cloth_rgb=(54, 126, 94),
            cloth_line_rgb=(128, 190, 154),
            pocket_rgb=(10, 8, 6),
            pocket_outline_rgb=(80, 58, 34),
            ball_outline_rgb=(40, 34, 26),
            ball_shadow_rgb=(28, 18, 10),
            marker_rgb=(34, 54, 76),
            marker_fill_rgba=(34, 54, 76, 40),
            badge_fill_rgb=(255, 250, 238),
            badge_outline_rgb=(108, 82, 48),
            badge_text_rgb=(42, 32, 22),
            shot_line_rgb=(34, 54, 76),
        )
    return PoolTheme(
        rail_rgb=(66, 54, 38),
        rail_outline_rgb=(26, 18, 12),
        cloth_rgb=(40, 112, 76),
        cloth_line_rgb=(104, 174, 132),
        pocket_rgb=(6, 8, 8),
        pocket_outline_rgb=(210, 186, 124),
        ball_outline_rgb=(22, 24, 24),
        ball_shadow_rgb=(6, 10, 8),
        marker_rgb=(246, 206, 60),
        marker_fill_rgba=(246, 206, 60, 55),
        badge_fill_rgb=(248, 246, 236),
        badge_outline_rgb=(82, 70, 46),
        badge_text_rgb=(28, 34, 28),
        shot_line_rgb=(248, 214, 76),
    )


def build_games_hex_theme(*, style_variant: str) -> HexTheme:
    """Return one resolved Hex-board theme for the active style variant."""

    variant = str(style_variant)
    if variant == "soft":
        return HexTheme(
            cell_fill_rgb=(238, 232, 212),
            cell_alt_fill_rgb=(229, 222, 202),
            cell_outline_rgb=(119, 104, 82),
            board_outline_rgb=(81, 66, 46),
            red_goal_rgb=(204, 72, 65),
            blue_goal_rgb=(58, 112, 204),
            red_stone_fill_rgb=(208, 66, 62),
            red_stone_outline_rgb=(108, 35, 35),
            red_stone_shine_rgb=(244, 150, 140),
            blue_stone_fill_rgb=(53, 110, 200),
            blue_stone_outline_rgb=(28, 58, 112),
            blue_stone_shine_rgb=(142, 190, 244),
            candidate_badge_fill_rgb=(255, 250, 236),
            candidate_badge_outline_rgb=(89, 78, 62),
            candidate_badge_text_rgb=(38, 34, 28),
        )
    if variant == "outlined":
        return HexTheme(
            cell_fill_rgb=(250, 250, 248),
            cell_alt_fill_rgb=(241, 242, 238),
            cell_outline_rgb=(64, 70, 78),
            board_outline_rgb=(34, 38, 46),
            red_goal_rgb=(190, 52, 56),
            blue_goal_rgb=(43, 94, 178),
            red_stone_fill_rgb=(224, 62, 64),
            red_stone_outline_rgb=(74, 26, 28),
            red_stone_shine_rgb=(255, 154, 150),
            blue_stone_fill_rgb=(48, 104, 200),
            blue_stone_outline_rgb=(20, 42, 86),
            blue_stone_shine_rgb=(144, 190, 250),
            candidate_badge_fill_rgb=(255, 255, 255),
            candidate_badge_outline_rgb=(40, 46, 54),
            candidate_badge_text_rgb=(18, 24, 30),
        )
    if variant == "slate":
        return HexTheme(
            cell_fill_rgb=(74, 88, 92),
            cell_alt_fill_rgb=(66, 78, 84),
            cell_outline_rgb=(174, 188, 190),
            board_outline_rgb=(226, 232, 230),
            red_goal_rgb=(236, 92, 82),
            blue_goal_rgb=(94, 164, 236),
            red_stone_fill_rgb=(214, 68, 62),
            red_stone_outline_rgb=(80, 24, 22),
            red_stone_shine_rgb=(252, 148, 140),
            blue_stone_fill_rgb=(58, 126, 218),
            blue_stone_outline_rgb=(18, 48, 94),
            blue_stone_shine_rgb=(142, 204, 255),
            candidate_badge_fill_rgb=(244, 248, 246),
            candidate_badge_outline_rgb=(28, 36, 40),
            candidate_badge_text_rgb=(16, 20, 22),
        )
    if variant == "paper":
        return HexTheme(
            cell_fill_rgb=(250, 241, 216),
            cell_alt_fill_rgb=(242, 230, 200),
            cell_outline_rgb=(136, 104, 68),
            board_outline_rgb=(82, 58, 34),
            red_goal_rgb=(184, 66, 54),
            blue_goal_rgb=(52, 104, 166),
            red_stone_fill_rgb=(202, 76, 62),
            red_stone_outline_rgb=(92, 40, 32),
            red_stone_shine_rgb=(242, 154, 132),
            blue_stone_fill_rgb=(56, 112, 184),
            blue_stone_outline_rgb=(30, 60, 96),
            blue_stone_shine_rgb=(142, 194, 238),
            candidate_badge_fill_rgb=(255, 249, 226),
            candidate_badge_outline_rgb=(112, 82, 46),
            candidate_badge_text_rgb=(44, 30, 18),
        )
    return HexTheme(
        cell_fill_rgb=(232, 210, 164),
        cell_alt_fill_rgb=(220, 198, 150),
        cell_outline_rgb=(104, 78, 46),
        board_outline_rgb=(66, 48, 28),
        red_goal_rgb=(194, 50, 54),
        blue_goal_rgb=(44, 92, 178),
        red_stone_fill_rgb=(214, 54, 58),
        red_stone_outline_rgb=(82, 24, 28),
        red_stone_shine_rgb=(248, 138, 136),
        blue_stone_fill_rgb=(48, 100, 196),
        blue_stone_outline_rgb=(22, 44, 92),
        blue_stone_shine_rgb=(136, 184, 248),
        candidate_badge_fill_rgb=(255, 248, 224),
        candidate_badge_outline_rgb=(78, 58, 34),
        candidate_badge_text_rgb=(30, 24, 18),
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
    "BattleshipTheme",
    "BingoTheme",
    "CardTheme",
    "CheckersTheme",
    "ChessTheme",
    "ConnectFourTheme",
    "DominoTheme",
    "DotsAndBoxesTheme",
    "GoTheme",
    "HexTheme",
    "MinesweeperTheme",
    "NineMensMorrisTheme",
    "PoolTheme",
    "ReversiTheme",
    "SudokuTheme",
    "SUPPORTED_CHECKERS_STYLE_VARIANTS",
    "SUPPORTED_CHESS_STYLE_VARIANTS",
    "SUPPORTED_CONNECT_FOUR_STYLE_VARIANTS",
    "SUPPORTED_DOMINO_STYLE_VARIANTS",
    "SUPPORTED_DOTS_AND_BOXES_STYLE_VARIANTS",
    "SUPPORTED_GAMES_STYLE_VARIANTS",
    "SUPPORTED_BINGO_STYLE_VARIANTS",
    "SUPPORTED_BATTLESHIP_STYLE_VARIANTS",
    "SUPPORTED_GO_STYLE_VARIANTS",
    "SUPPORTED_HEX_STYLE_VARIANTS",
    "SUPPORTED_MINESWEEPER_STYLE_VARIANTS",
    "SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS",
    "SUPPORTED_POOL_STYLE_VARIANTS",
    "SUPPORTED_REVERSI_STYLE_VARIANTS",
    "SUPPORTED_SUDOKU_STYLE_VARIANTS",
    "build_games_battleship_theme",
    "build_games_bingo_theme",
    "build_games_card_theme",
    "build_games_checkers_theme",
    "build_games_chess_theme",
    "build_games_connect_four_theme",
    "build_games_domino_theme",
    "build_games_dots_and_boxes_theme",
    "build_games_go_theme",
    "build_games_hex_theme",
    "build_games_minesweeper_theme",
    "build_games_nine_mens_morris_theme",
    "build_games_pool_theme",
    "build_games_reversi_theme",
    "build_games_sudoku_theme",
    "style_probability_map",
    "suit_color",
]
