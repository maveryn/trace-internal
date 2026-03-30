"""Shared Reversi board renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from .reversi_common import BLACK, WHITE, Coord, coord_to_cell_id, player_name
from .style import ReversiTheme, build_games_reversi_theme


@dataclass(frozen=True)
class ReversiRenderParams:
    """Resolved render controls for one Reversi board scene."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    player_badge_height_px: int
    player_badge_width_px: int
    header_gap_px: int
    max_board_size_px: int
    board_corner_radius_px: int
    board_frame_width_px: int
    cell_line_width_px: int
    marked_square_outline_width_px: int
    disc_inset_fraction: float
    player_badge_font_size_px: int


@dataclass(frozen=True)
class ReversiCellSpec:
    """One board cell after layout/render assignment."""

    cell_id: str
    row: int
    col: int
    occupant: str
    bbox_px: Tuple[float, float, float, float]
    disc_bbox_px: Tuple[float, float, float, float] | None


@dataclass(frozen=True)
class RenderedReversiScene:
    """Rendered Reversi scene plus trace-friendly metadata."""

    image: Image.Image
    cell_specs: Tuple[ReversiCellSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _disc_bbox(cell_bbox: Tuple[float, float, float, float], *, inset_fraction: float) -> Tuple[float, float, float, float]:
    """Return one inscribed disc bbox inside a board cell."""

    left, top, right, bottom = cell_bbox
    inset = float(max(5.0, inset_fraction * min(right - left, bottom - top)))
    return (
        round(float(left + inset), 3),
        round(float(top + inset), 3),
        round(float(right - inset), 3),
        round(float(bottom - inset), 3),
    )


def _draw_disc(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_px: Tuple[float, float, float, float],
    theme: ReversiTheme,
    player: int,
) -> None:
    """Draw one Reversi disc with simple highlight chrome."""

    if int(player) == int(BLACK):
        fill_rgb = theme.black_disc_fill_rgb
        outline_rgb = theme.black_disc_outline_rgb
        shine_rgb = theme.black_disc_shine_rgb
    else:
        fill_rgb = theme.white_disc_fill_rgb
        outline_rgb = theme.white_disc_outline_rgb
        shine_rgb = theme.white_disc_shine_rgb
    draw.ellipse(
        bbox_px,
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=int(theme.disc_outline_width_px),
    )
    left, top, right, bottom = bbox_px
    shine_w = 0.34 * (right - left)
    shine_h = 0.24 * (bottom - top)
    draw.ellipse(
        [
            left + 0.18 * (right - left),
            top + 0.16 * (bottom - top),
            left + 0.18 * (right - left) + shine_w,
            top + 0.16 * (bottom - top) + shine_h,
        ],
        fill=tuple(int(value) for value in shine_rgb),
    )


def render_reversi_board_scene(
    *,
    board: Sequence[Sequence[int]],
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    current_player: int,
    params: ReversiRenderParams,
    marked_move: Coord | None,
) -> RenderedReversiScene:
    """Render one visible Reversi board with an optional marked legal move."""

    board_size = int(len(board))
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    theme = build_games_reversi_theme(style_variant=str(style_variant))

    cell_size = min(
        int(params.max_board_size_px) // int(board_size),
        (int(params.canvas_width) - (2 * int(params.panel_margin_px))) // int(board_size),
        (
            int(params.canvas_height)
            - (2 * int(params.panel_margin_px))
            - int(params.player_badge_height_px)
            - int(params.header_gap_px)
        )
        // int(board_size),
    )
    board_width = int(cell_size) * int(board_size)
    board_height = int(cell_size) * int(board_size)
    board_left = int(0.5 * (int(params.canvas_width) - int(board_width)))
    available_height = (
        int(params.canvas_height)
        - (2 * int(params.panel_margin_px))
        - int(params.player_badge_height_px)
        - int(params.header_gap_px)
    )
    board_top = int(
        params.panel_margin_px
        + params.player_badge_height_px
        + params.header_gap_px
        + max(0, 0.5 * (available_height - int(board_height)))
    )
    board_bbox = (
        round(float(board_left), 3),
        round(float(board_top), 3),
        round(float(board_left + board_width), 3),
        round(float(board_top + board_height), 3),
    )
    draw.rounded_rectangle(
        board_bbox,
        radius=int(params.board_corner_radius_px),
        fill=tuple(int(value) for value in theme.board_frame_rgb),
    )
    inner_inset = float(params.board_frame_width_px)
    inner_bbox = (
        round(float(board_bbox[0] + inner_inset), 3),
        round(float(board_bbox[1] + inner_inset), 3),
        round(float(board_bbox[2] - inner_inset), 3),
        round(float(board_bbox[3] - inner_inset), 3),
    )
    draw.rounded_rectangle(
        inner_bbox,
        radius=max(8, int(params.board_corner_radius_px) - int(params.board_frame_width_px)),
        fill=tuple(int(value) for value in theme.board_fill_rgb),
    )

    badge_font = load_font(int(params.player_badge_font_size_px), bold=True)
    badge_text = f"{player_name(int(current_player))} to move"
    badge_text_bbox = draw.textbbox((0, 0), badge_text, font=badge_font, stroke_width=1)
    badge_width = max(
        int(params.player_badge_width_px),
        int((badge_text_bbox[2] - badge_text_bbox[0]) + params.player_badge_height_px + 34),
    )
    badge_left = int(0.5 * (int(params.canvas_width) - int(badge_width)))
    badge_top = int(params.panel_margin_px)
    badge_bbox = (
        round(float(badge_left), 3),
        round(float(badge_top), 3),
        round(float(badge_left + badge_width), 3),
        round(float(badge_top + params.player_badge_height_px), 3),
    )
    draw.rounded_rectangle(
        badge_bbox,
        radius=int(0.5 * int(params.player_badge_height_px)),
        fill=tuple(int(value) for value in theme.badge_fill_rgb),
        outline=tuple(int(value) for value in theme.badge_outline_rgb),
        width=2,
    )
    disc_d = int(params.player_badge_height_px) - 16
    disc_left = int(badge_left + 12)
    disc_top = int(badge_top + 8)
    _draw_disc(
        draw,
        bbox_px=(float(disc_left), float(disc_top), float(disc_left + disc_d), float(disc_top + disc_d)),
        theme=theme,
        player=int(current_player),
    )
    badge_text_rgb = tuple(int(value) for value in theme.badge_text_rgb)
    draw.text(
        (
            float(disc_left + disc_d + 12),
            float(badge_top + 0.5 * (int(params.player_badge_height_px) - (badge_text_bbox[3] - badge_text_bbox[1]))),
        ),
        badge_text,
        font=badge_font,
        fill=badge_text_rgb,
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(badge_text_rgb)),
    )

    cell_specs: List[ReversiCellSpec] = []
    scene_entities: List[Dict[str, Any]] = []
    cell_bboxes_px: Dict[str, Tuple[float, float, float, float]] = {}
    disc_bboxes_px: Dict[str, Tuple[float, float, float, float]] = {}

    for index in range(1, board_size):
        x = float(board_left + (index * cell_size))
        y = float(board_top + (index * cell_size))
        draw.line(
            [(x, float(board_top)), (x, float(board_top + board_height))],
            fill=tuple(int(value) for value in theme.grid_line_rgb),
            width=int(params.cell_line_width_px),
        )
        draw.line(
            [(float(board_left), y), (float(board_left + board_width), y)],
            fill=tuple(int(value) for value in theme.grid_line_rgb),
            width=int(params.cell_line_width_px),
        )

    marked_square_bbox_px: Tuple[float, float, float, float] | None = None
    for row in range(board_size):
        for col in range(board_size):
            cell_id = coord_to_cell_id((int(row), int(col)))
            cell_bbox = (
                round(float(board_left + (col * cell_size)), 3),
                round(float(board_top + (row * cell_size)), 3),
                round(float(board_left + ((col + 1) * cell_size)), 3),
                round(float(board_top + ((row + 1) * cell_size)), 3),
            )
            if marked_move is not None and (int(row), int(col)) == (int(marked_move[0]), int(marked_move[1])):
                marked_square_bbox_px = cell_bbox
                inset = 6.0
                draw.rounded_rectangle(
                    [
                        cell_bbox[0] + inset,
                        cell_bbox[1] + inset,
                        cell_bbox[2] - inset,
                        cell_bbox[3] - inset,
                    ],
                    radius=max(8, int(0.18 * cell_size)),
                    outline=tuple(int(value) for value in theme.marked_square_outline_rgb),
                    width=int(params.marked_square_outline_width_px),
                    fill=tuple(int(value) for value in theme.marked_square_fill_rgba),
                )
            occupant_value = int(board[row][col])
            occupant_name = "empty" if int(occupant_value) == 0 else "black" if int(occupant_value) == int(BLACK) else "white"
            disc_bbox_px = None
            if int(occupant_value) in {int(BLACK), int(WHITE)}:
                disc_bbox_px = _disc_bbox(cell_bbox, inset_fraction=float(params.disc_inset_fraction))
                disc_bboxes_px[str(cell_id)] = disc_bbox_px
                _draw_disc(draw, bbox_px=disc_bbox_px, theme=theme, player=int(occupant_value))
            cell_specs.append(
                ReversiCellSpec(
                    cell_id=str(cell_id),
                    row=int(row),
                    col=int(col),
                    occupant=str(occupant_name),
                    bbox_px=cell_bbox,
                    disc_bbox_px=disc_bbox_px,
                )
            )
            cell_bboxes_px[str(cell_id)] = cell_bbox
            entity: Dict[str, Any] = {
                "entity_id": str(cell_id),
                "entity_type": "board_cell",
                "row": int(row),
                "col": int(col),
                "occupant": str(occupant_name),
                "bbox": list(cell_bbox),
            }
            if disc_bbox_px is not None:
                entity["disc_bbox"] = list(disc_bbox_px)
            scene_entities.append(entity)

    return RenderedReversiScene(
        image=image,
        cell_specs=tuple(cell_specs),
        scene_entities=tuple(scene_entities),
        render_map={
            "board_bbox_px": list(board_bbox),
            "cell_bboxes_px": {str(key): list(value) for key, value in cell_bboxes_px.items()},
            "disc_bboxes_px": {str(key): list(value) for key, value in disc_bboxes_px.items()},
            "player_badge_bbox_px": list(badge_bbox),
            "marked_square_bbox_px": None if marked_square_bbox_px is None else list(marked_square_bbox_px),
            "board_size": int(board_size),
            "scene_variant": str(scene_variant),
            "style_variant": str(style_variant),
        },
    )


__all__ = [
    "RenderedReversiScene",
    "ReversiCellSpec",
    "ReversiRenderParams",
    "render_reversi_board_scene",
]
