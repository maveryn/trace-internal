"""Shared Chess board renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import fit_font_to_box, load_font, resolve_text_stroke_fill
from .chess_common import (
    BLACK,
    BOARD_SIZE,
    WHITE,
    ChessPiece,
    Coord,
    color_name,
    coord_to_cell_id,
    piece_to_entity_id,
)
from .layout import apply_games_layout_jitter_to_bbox, offset_bbox
from .style import ChessTheme, build_games_chess_theme


@dataclass(frozen=True)
class ChessRenderParams:
    """Resolved render controls for one Chess scene."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    player_badge_height_px: int
    player_badge_width_px: int
    header_gap_px: int
    max_board_size_px: int
    board_corner_radius_px: int
    board_frame_width_px: int
    piece_inset_fraction: float
    piece_font_size_px: int
    marked_square_outline_width_px: int
    player_badge_font_size_px: int
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class ChessCellSpec:
    """One board cell after layout/render assignment."""

    cell_id: str
    row: int
    col: int
    occupant: str
    bbox_px: Tuple[float, float, float, float]
    piece_bbox_px: Tuple[float, float, float, float] | None


@dataclass(frozen=True)
class RenderedChessScene:
    """Rendered Chess scene plus trace-friendly metadata."""

    image: Image.Image
    cell_specs: Tuple[ChessCellSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


_PIECE_CODEPOINTS: Dict[Tuple[str, str], int] = {
    (WHITE, "king"): 0x2654,
    (WHITE, "queen"): 0x2655,
    (WHITE, "rook"): 0x2656,
    (WHITE, "bishop"): 0x2657,
    (WHITE, "knight"): 0x2658,
    (WHITE, "pawn"): 0x2659,
    (BLACK, "king"): 0x265A,
    (BLACK, "queen"): 0x265B,
    (BLACK, "rook"): 0x265C,
    (BLACK, "bishop"): 0x265D,
    (BLACK, "knight"): 0x265E,
    (BLACK, "pawn"): 0x265F,
}


def _adjust_rgb(rgb: Sequence[int], delta: int) -> Tuple[int, int, int]:
    """Return an RGB color lightened/darkened by a small channel delta."""

    return tuple(max(0, min(255, int(value) + int(delta))) for value in rgb[:3])


def _inset_square_rgb(rgb: Sequence[int]) -> Tuple[int, int, int]:
    """Return a subtle inner-square shade for inset board styles."""

    brightness = sum(int(value) for value in rgb[:3]) / 3.0
    return _adjust_rgb(rgb, 10 if brightness < 158.0 else -7)


def _piece_bbox(cell_bbox: Tuple[float, float, float, float], *, inset_fraction: float) -> Tuple[float, float, float, float]:
    """Return an inscribed piece bbox inside one board cell."""

    left, top, right, bottom = cell_bbox
    inset = float(max(4.0, inset_fraction * min(right - left, bottom - top)))
    return (
        round(float(left + inset), 3),
        round(float(top + inset), 3),
        round(float(right - inset), 3),
        round(float(bottom - inset), 3),
    )


def _draw_piece(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_px: Tuple[float, float, float, float],
    piece: ChessPiece,
    theme: ChessTheme,
    font_size_px: int,
) -> None:
    """Draw one chess piece glyph centered in its cell."""

    left, top, right, bottom = bbox_px
    width = float(right - left)
    height = float(bottom - top)
    shadow_offset = max(1, int(round(0.045 * min(width, height))))
    draw.ellipse(
        [left + shadow_offset, top + shadow_offset, right + shadow_offset, bottom + shadow_offset],
        fill=tuple(int(value) for value in theme.piece_shadow_rgb) + (int(theme.piece_shadow_alpha),),
    )
    if str(piece.color) == WHITE:
        fill_rgb = tuple(int(value) for value in theme.white_piece_fill_rgb)
        outline_rgb = tuple(int(value) for value in theme.white_piece_outline_rgb)
        glyph_fill = fill_rgb
        glyph_stroke = outline_rgb
    else:
        fill_rgb = tuple(int(value) for value in theme.black_piece_fill_rgb)
        outline_rgb = tuple(int(value) for value in theme.black_piece_outline_rgb)
        glyph_fill = fill_rgb
        glyph_stroke = outline_rgb
    glyph = chr(_PIECE_CODEPOINTS[(str(piece.color), str(piece.kind))])
    if str(theme.piece_rendering) == "glyph":
        font = fit_font_to_box(
            draw,
            text=glyph,
            max_width=width,
            max_height=height,
            bold=False,
            min_size_px=18,
            max_size_px=int(font_size_px),
            fill_ratio=0.98,
        )
        stroke_width = max(1, int(round(0.035 * min(width, height))))
        text_bbox = draw.textbbox((0, 0), glyph, font=font, stroke_width=stroke_width)
        text_width = float(text_bbox[2] - text_bbox[0])
        text_height = float(text_bbox[3] - text_bbox[1])
        x = float(left + (0.5 * (width - text_width)) - text_bbox[0])
        y = float(top + (0.5 * (height - text_height)) - text_bbox[1] - (0.02 * height))
        draw.text(
            (x, y),
            glyph,
            font=font,
            fill=glyph_fill,
            stroke_width=stroke_width,
            stroke_fill=glyph_stroke,
        )
        return
    draw.ellipse(
        bbox_px,
        fill=fill_rgb,
        outline=outline_rgb,
        width=max(2, int(round(0.045 * min(width, height)))),
    )
    font = fit_font_to_box(
        draw,
        text=glyph,
        max_width=width,
        max_height=height,
        bold=False,
        min_size_px=16,
        max_size_px=int(font_size_px),
        fill_ratio=0.96,
    )
    text_bbox = draw.textbbox((0, 0), glyph, font=font, stroke_width=1)
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    x = float(left + (0.5 * (width - text_width)) - text_bbox[0])
    y = float(top + (0.5 * (height - text_height)) - text_bbox[1] - (0.02 * height))
    draw.text(
        (x, y),
        glyph,
        font=font,
        fill=glyph_fill,
        stroke_width=1,
        stroke_fill=glyph_stroke,
    )


def render_chess_board_scene(
    *,
    board: Sequence[Sequence[ChessPiece | None]],
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    badge_text: str,
    marked_coord: Coord | None,
    params: ChessRenderParams,
) -> RenderedChessScene:
    """Render one visible Chess board state."""

    del scene_variant
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    theme = build_games_chess_theme(style_variant=str(style_variant))

    cell_size = min(
        int(params.max_board_size_px) // BOARD_SIZE,
        (int(params.canvas_width) - (2 * int(params.panel_margin_px))) // BOARD_SIZE,
        (
            int(params.canvas_height)
            - (2 * int(params.panel_margin_px))
            - int(params.player_badge_height_px)
            - int(params.header_gap_px)
        )
        // BOARD_SIZE,
    )
    board_size_px = int(cell_size) * BOARD_SIZE
    board_left = int(0.5 * (int(params.canvas_width) - int(board_size_px)))
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
        + max(0, 0.5 * (available_height - int(board_size_px)))
    )
    board_bbox = (
        round(float(board_left), 3),
        round(float(board_top), 3),
        round(float(board_left + board_size_px), 3),
        round(float(board_top + board_size_px), 3),
    )

    badge_font = load_font(int(params.player_badge_font_size_px), bold=True)
    badge_text_bbox = draw.textbbox((0, 0), str(badge_text), font=badge_font, stroke_width=1)
    badge_width = max(
        int(params.player_badge_width_px),
        int((badge_text_bbox[2] - badge_text_bbox[0]) + 44),
    )
    badge_left = int(0.5 * (int(params.canvas_width) - int(badge_width)))
    badge_top = int(params.panel_margin_px)
    badge_bbox = (
        round(float(badge_left), 3),
        round(float(badge_top), 3),
        round(float(badge_left + badge_width), 3),
        round(float(badge_top + params.player_badge_height_px), 3),
    )
    group_bbox = (
        min(float(board_bbox[0]), float(badge_bbox[0])),
        min(float(board_bbox[1]), float(badge_bbox[1])),
        max(float(board_bbox[2]), float(badge_bbox[2])),
        max(float(board_bbox[3]), float(badge_bbox[3])),
    )
    _group_bbox, dx, dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=group_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    board_left = float(board_left + dx)
    board_top = float(board_top + dy)
    badge_left = float(badge_left + dx)
    badge_top = float(badge_top + dy)
    board_bbox = offset_bbox(board_bbox, dx=dx, dy=dy)
    badge_bbox = offset_bbox(badge_bbox, dx=dx, dy=dy)

    draw.rounded_rectangle(
        board_bbox,
        radius=int(params.board_corner_radius_px),
        fill=tuple(int(value) for value in theme.board_frame_rgb),
    )
    draw.rounded_rectangle(
        badge_bbox,
        radius=int(0.5 * int(params.player_badge_height_px)),
        fill=tuple(int(value) for value in theme.badge_fill_rgb),
        outline=tuple(int(value) for value in theme.badge_outline_rgb),
        width=2,
    )
    badge_text_rgb = tuple(int(value) for value in theme.badge_text_rgb)
    draw.text(
        (
            float(badge_left + 22),
            float(badge_top + 0.5 * (int(params.player_badge_height_px) - (badge_text_bbox[3] - badge_text_bbox[1]))),
        ),
        str(badge_text),
        font=badge_font,
        fill=badge_text_rgb,
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(badge_text_rgb)),
    )

    cell_specs: List[ChessCellSpec] = []
    scene_entities: List[Dict[str, Any]] = []
    cell_bboxes_px: Dict[str, Tuple[float, float, float, float]] = {}
    piece_bboxes_px: Dict[str, Tuple[float, float, float, float]] = {}
    inner_inset = float(params.board_frame_width_px)
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            left = float(board_left + (col * cell_size) + inner_inset)
            top = float(board_top + (row * cell_size) + inner_inset)
            right = float(board_left + ((col + 1) * cell_size) - inner_inset)
            bottom = float(board_top + ((row + 1) * cell_size) - inner_inset)
            cell_bbox = (round(left, 3), round(top, 3), round(right, 3), round(bottom, 3))
            is_light = (row + col) % 2 == 0
            square_rgb = tuple(int(value) for value in (theme.light_square_rgb if is_light else theme.dark_square_rgb))
            draw.rectangle(
                cell_bbox,
                fill=square_rgb,
                outline=tuple(int(value) for value in theme.grid_line_rgb),
                width=int(theme.grid_line_width_px),
            )
            if str(theme.square_rendering) == "inset":
                inset = max(2.0, 0.045 * min(cell_bbox[2] - cell_bbox[0], cell_bbox[3] - cell_bbox[1]))
                draw.rectangle(
                    [
                        cell_bbox[0] + inset,
                        cell_bbox[1] + inset,
                        cell_bbox[2] - inset,
                        cell_bbox[3] - inset,
                    ],
                    fill=_inset_square_rgb(square_rgb),
                )
            cell_id = coord_to_cell_id((int(row), int(col)))
            if marked_coord is not None and (int(row), int(col)) == (int(marked_coord[0]), int(marked_coord[1])):
                mark_inset = max(3.0, 0.06 * min(cell_bbox[2] - cell_bbox[0], cell_bbox[3] - cell_bbox[1]))
                draw.rectangle(
                    [
                        cell_bbox[0] + mark_inset,
                        cell_bbox[1] + mark_inset,
                        cell_bbox[2] - mark_inset,
                        cell_bbox[3] - mark_inset,
                    ],
                    fill=tuple(int(value) for value in theme.marked_square_fill_rgba),
                )
            occupant_piece = board[row][col]
            occupant = "empty" if occupant_piece is None else f"{occupant_piece.color}_{occupant_piece.kind}"
            piece_bbox_px: Tuple[float, float, float, float] | None = None
            if occupant_piece is not None:
                piece_bbox_px = _piece_bbox(cell_bbox, inset_fraction=float(params.piece_inset_fraction))
                _draw_piece(
                    draw,
                    bbox_px=piece_bbox_px,
                    piece=occupant_piece,
                    theme=theme,
                    font_size_px=int(params.piece_font_size_px),
                )
                piece_id = piece_to_entity_id((int(row), int(col)), occupant_piece)
                piece_bboxes_px[piece_id] = piece_bbox_px
                scene_entities.append(
                    {
                        "id": str(piece_id),
                        "type": "chess_piece",
                        "color": str(occupant_piece.color),
                        "kind": str(occupant_piece.kind),
                        "row": int(row),
                        "col": int(col),
                        "bbox_px": list(piece_bbox_px),
                    }
                )
            cell_bboxes_px[cell_id] = cell_bbox
            cell_specs.append(
                ChessCellSpec(
                    cell_id=str(cell_id),
                    row=int(row),
                    col=int(col),
                    occupant=str(occupant),
                    bbox_px=cell_bbox,
                    piece_bbox_px=piece_bbox_px,
                )
            )
            scene_entities.append(
                {
                    "id": str(cell_id),
                    "type": "chess_board_cell",
                    "row": int(row),
                    "col": int(col),
                    "occupant": str(occupant),
                    "bbox_px": list(cell_bbox),
                }
            )

    if marked_coord is not None:
        marked_id = coord_to_cell_id(marked_coord)
        marked_bbox = cell_bboxes_px[str(marked_id)]
        inset = max(3.0, 0.06 * min(marked_bbox[2] - marked_bbox[0], marked_bbox[3] - marked_bbox[1]))
        draw.rectangle(
            [
                marked_bbox[0] + inset,
                marked_bbox[1] + inset,
                marked_bbox[2] - inset,
                marked_bbox[3] - inset,
            ],
            outline=tuple(int(value) for value in theme.marked_square_outline_rgb),
            width=int(params.marked_square_outline_width_px),
        )

    render_map: Dict[str, Any] = {
        "board_bbox_px": list(board_bbox),
        "badge_bbox_px": list(badge_bbox),
        "cell_bboxes_px": {str(key): list(value) for key, value in cell_bboxes_px.items()},
        "piece_bboxes_px": {str(key): list(value) for key, value in piece_bboxes_px.items()},
        "marked_cell_id": None if marked_coord is None else coord_to_cell_id(marked_coord),
        "layout_jitter": dict(layout_jitter),
        "board_size": int(BOARD_SIZE),
    }
    return RenderedChessScene(
        image=image,
        cell_specs=tuple(cell_specs),
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "ChessCellSpec",
    "ChessRenderParams",
    "RenderedChessScene",
    "render_chess_board_scene",
]
