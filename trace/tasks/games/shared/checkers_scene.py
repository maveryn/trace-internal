"""Shared Checkers board renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from .checkers_common import BLACK, BOARD_SIZE, RED, Coord, coord_to_cell_id, piece_to_entity_id, player_name
from .style import CheckersTheme, build_games_checkers_theme


@dataclass(frozen=True)
class CheckersRenderParams:
    """Resolved render controls for one Checkers scene."""

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
    player_badge_font_size_px: int


@dataclass(frozen=True)
class CheckersCellSpec:
    """One board cell after layout/render assignment."""

    cell_id: str
    row: int
    col: int
    playable: bool
    occupant: str
    bbox_px: Tuple[float, float, float, float]
    piece_bbox_px: Tuple[float, float, float, float] | None


@dataclass(frozen=True)
class RenderedCheckersScene:
    """Rendered Checkers scene plus trace-friendly metadata."""

    image: Image.Image
    cell_specs: Tuple[CheckersCellSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _piece_bbox(
    cell_bbox: Tuple[float, float, float, float],
    *,
    inset_fraction: float,
) -> Tuple[float, float, float, float]:
    """Return one inscribed checker-piece bbox inside one board cell."""

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
    theme: CheckersTheme,
    player: int,
) -> None:
    """Draw one ordinary checker piece with simple inner-ring chrome."""

    if int(player) == int(RED):
        fill_rgb = theme.red_piece_fill_rgb
        outline_rgb = theme.red_piece_outline_rgb
        shine_rgb = theme.red_piece_shine_rgb
    else:
        fill_rgb = theme.black_piece_fill_rgb
        outline_rgb = theme.black_piece_outline_rgb
        shine_rgb = theme.black_piece_shine_rgb
    draw.ellipse(
        bbox_px,
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=int(theme.piece_outline_width_px),
    )
    left, top, right, bottom = bbox_px
    inner_inset_x = 0.16 * (right - left)
    inner_inset_y = 0.16 * (bottom - top)
    draw.ellipse(
        [
            left + inner_inset_x,
            top + inner_inset_y,
            right - inner_inset_x,
            bottom - inner_inset_y,
        ],
        outline=tuple(int(value) for value in shine_rgb),
        width=max(2, int(0.08 * (right - left))),
    )


def render_checkers_board_scene(
    *,
    board: Sequence[Sequence[int]],
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    current_player: int,
    params: CheckersRenderParams,
) -> RenderedCheckersScene:
    """Render one visible Checkers board state."""

    del scene_variant
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    theme = build_games_checkers_theme(style_variant=str(style_variant))

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
    draw.rounded_rectangle(
        board_bbox,
        radius=int(params.board_corner_radius_px),
        fill=tuple(int(value) for value in theme.board_frame_rgb),
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
    sample_piece_d = int(params.player_badge_height_px) - 16
    sample_piece_left = int(badge_left + 12)
    sample_piece_top = int(badge_top + 8)
    _draw_piece(
        draw,
        bbox_px=(
            float(sample_piece_left),
            float(sample_piece_top),
            float(sample_piece_left + sample_piece_d),
            float(sample_piece_top + sample_piece_d),
        ),
        theme=theme,
        player=int(current_player),
    )
    badge_text_rgb = tuple(int(value) for value in theme.badge_text_rgb)
    draw.text(
        (
            float(sample_piece_left + sample_piece_d + 12),
            float(badge_top + 0.5 * (int(params.player_badge_height_px) - (badge_text_bbox[3] - badge_text_bbox[1]))),
        ),
        badge_text,
        font=badge_font,
        fill=badge_text_rgb,
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(badge_text_rgb)),
    )

    cell_specs: List[CheckersCellSpec] = []
    scene_entities: List[Dict[str, Any]] = []
    cell_bboxes_px: Dict[str, Tuple[float, float, float, float]] = {}
    piece_bboxes_px: Dict[str, Tuple[float, float, float, float]] = {}

    inner_inset = float(params.board_frame_width_px)
    playable_square_count = 0
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            left = float(board_left + (col * cell_size) + inner_inset)
            top = float(board_top + (row * cell_size) + inner_inset)
            right = float(board_left + ((col + 1) * cell_size) - inner_inset)
            bottom = float(board_top + ((row + 1) * cell_size) - inner_inset)
            cell_bbox = (round(left, 3), round(top, 3), round(right, 3), round(bottom, 3))
            playable = (row + col) % 2 == 1
            draw.rectangle(
                cell_bbox,
                fill=tuple(int(value) for value in (theme.dark_square_rgb if playable else theme.light_square_rgb)),
                outline=tuple(int(value) for value in theme.grid_line_rgb),
                width=int(theme.grid_line_width_px),
            )
            cell_id = coord_to_cell_id((int(row), int(col)))
            occupant_value = int(board[row][col])
            occupant = "red" if occupant_value == int(RED) else "black" if occupant_value == int(BLACK) else "empty"
            piece_bbox_px: Tuple[float, float, float, float] | None = None
            if occupant_value != 0:
                piece_bbox_px = _piece_bbox(cell_bbox, inset_fraction=float(params.piece_inset_fraction))
                _draw_piece(draw, bbox_px=piece_bbox_px, theme=theme, player=occupant_value)
                piece_entity_id = piece_to_entity_id((int(row), int(col)), player=occupant_value)
                piece_bboxes_px[str(piece_entity_id)] = piece_bbox_px
                scene_entities.append(
                    {
                        "id": str(piece_entity_id),
                        "kind": "checker_piece",
                        "player": str(occupant),
                        "cell_id": str(cell_id),
                        "bbox_px": list(piece_bbox_px),
                    }
                )
            cell_bboxes_px[str(cell_id)] = cell_bbox
            scene_entities.append(
                {
                    "id": str(cell_id),
                    "kind": "board_cell",
                    "row": int(row),
                    "col": int(col),
                    "playable": bool(playable),
                    "occupant": str(occupant),
                    "bbox_px": list(cell_bbox),
                }
            )
            cell_specs.append(
                CheckersCellSpec(
                    cell_id=str(cell_id),
                    row=int(row),
                    col=int(col),
                    playable=bool(playable),
                    occupant=str(occupant),
                    bbox_px=cell_bbox,
                    piece_bbox_px=piece_bbox_px,
                )
            )
            if playable:
                playable_square_count += 1

    render_map = {
        "board_bbox_px": list(board_bbox),
        "cell_bboxes_px": {str(key): list(value) for key, value in cell_bboxes_px.items()},
        "piece_bboxes_px": {str(key): list(value) for key, value in piece_bboxes_px.items()},
        "player_badge_bbox_px": list(badge_bbox),
        "playable_square_count": int(playable_square_count),
    }
    return RenderedCheckersScene(
        image=image,
        cell_specs=tuple(cell_specs),
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "CheckersCellSpec",
    "CheckersRenderParams",
    "RenderedCheckersScene",
    "render_checkers_board_scene",
]
