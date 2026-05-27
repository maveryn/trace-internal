"""Shared Minesweeper-grid renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import fit_font_to_box
from .layout import apply_games_layout_jitter_to_bbox
from .minesweeper_common import Coord, all_coords, clue_number, coord_to_cell_id
from .style import MinesweeperTheme, build_games_minesweeper_theme


@dataclass(frozen=True)
class MinesweeperRenderParams:
    """Resolved render controls for one Minesweeper scene."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    max_board_size_px: int
    board_border_width_px: int
    grid_line_width_px: int
    cell_padding_px: int
    number_font_size_px: int
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class MinesweeperCellSpec:
    """One rendered Minesweeper cell."""

    cell_id: str
    row: int
    col: int
    state: str
    has_mine: bool
    adjacent_mine_count: int
    bbox_px: Tuple[float, float, float, float]


@dataclass(frozen=True)
class RenderedMinesweeperScene:
    """Rendered Minesweeper image plus trace-friendly cell geometry."""

    image: Image.Image
    cell_specs: Tuple[MinesweeperCellSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _cell_bbox(
    *,
    board_left: float,
    board_top: float,
    cell_size: float,
    row: int,
    col: int,
    padding_px: float = 0.0,
) -> Tuple[float, float, float, float]:
    """Return the bbox for one Minesweeper cell, with optional inset padding."""

    left = float(board_left + (int(col) * float(cell_size)) + float(padding_px))
    top = float(board_top + (int(row) * float(cell_size)) + float(padding_px))
    right = float(board_left + ((int(col) + 1) * float(cell_size)) - float(padding_px))
    bottom = float(board_top + ((int(row) + 1) * float(cell_size)) - float(padding_px))
    return (round(left, 3), round(top, 3), round(right, 3), round(bottom, 3))


def _draw_number(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_px: Tuple[float, float, float, float],
    value: int,
    theme: MinesweeperTheme,
    font_size_px: int,
) -> None:
    """Draw one centered Minesweeper clue number."""

    number = int(value)
    if number <= 0:
        return
    left, top, right, bottom = bbox_px
    width = float(right - left)
    height = float(bottom - top)
    text = str(number)
    font = fit_font_to_box(
        draw,
        text=text,
        max_width=float(width),
        max_height=float(height),
        bold=True,
        min_size_px=14,
        max_size_px=int(font_size_px),
        fill_ratio=0.72,
    )
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    text_x = float(left + (0.5 * (width - text_w)) - float(text_bbox[0]))
    text_y = float(top + (0.5 * (height - text_h)) - float(text_bbox[1]))
    colors = tuple(theme.number_rgb_by_value)
    fill = colors[min(max(int(number), 0), len(colors) - 1)]
    draw.text((text_x, text_y), text, fill=tuple(int(v) for v in fill), font=font)


def _draw_flag(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_px: Tuple[float, float, float, float],
    theme: MinesweeperTheme,
) -> None:
    """Draw a compact flag marker inside one hidden cell."""

    left, top, right, bottom = bbox_px
    width = float(right - left)
    height = float(bottom - top)
    pole_x = float(left + 0.45 * width)
    pole_top = float(top + 0.24 * height)
    pole_bottom = float(top + 0.74 * height)
    draw.line(
        [(pole_x, pole_top), (pole_x, pole_bottom)],
        fill=tuple(int(v) for v in theme.flag_pole_rgb),
        width=max(2, int(round(0.05 * width))),
    )
    flag = [
        (pole_x, pole_top),
        (float(left + 0.74 * width), float(top + 0.34 * height)),
        (pole_x, float(top + 0.46 * height)),
    ]
    draw.polygon(flag, fill=tuple(int(v) for v in theme.flag_rgb))
    base_y = float(top + 0.77 * height)
    draw.line(
        [(float(left + 0.30 * width), base_y), (float(left + 0.62 * width), base_y)],
        fill=tuple(int(v) for v in theme.flag_pole_rgb),
        width=max(2, int(round(0.05 * width))),
    )


def render_minesweeper_grid_scene(
    *,
    size: int,
    mine_coords: Sequence[Coord],
    revealed_coords: Sequence[Coord],
    flagged_coords: Sequence[Coord],
    hidden_coords: Sequence[Coord],
    background: Image.Image,
    style_variant: str,
    params: MinesweeperRenderParams,
    highlighted_clue_coords: Sequence[Coord] | None = None,
) -> RenderedMinesweeperScene:
    """Render one Minesweeper grid with hidden, flagged, and revealed cells."""

    board_size = int(size)
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme = build_games_minesweeper_theme(style_variant=str(style_variant))

    max_board_size = min(
        int(params.max_board_size_px),
        int(params.canvas_width) - (2 * int(params.panel_margin_px)),
        int(params.canvas_height) - (2 * int(params.panel_margin_px)),
    )
    board_left = int(0.5 * (int(params.canvas_width) - int(max_board_size)))
    board_top = int(0.5 * (int(params.canvas_height) - int(max_board_size)))
    board_bbox = (
        round(float(board_left), 3),
        round(float(board_top), 3),
        round(float(board_left + max_board_size), 3),
        round(float(board_top + max_board_size), 3),
    )
    board_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    board_left = float(board_bbox[0])
    board_top = float(board_bbox[1])
    cell_size = float((float(board_bbox[2]) - float(board_bbox[0])) / float(board_size))

    draw.rectangle(board_bbox, fill=tuple(int(v) for v in theme.board_fill_rgb))

    mines = {(int(row), int(col)) for row, col in mine_coords}
    revealed = {(int(row), int(col)) for row, col in revealed_coords}
    flagged = {(int(row), int(col)) for row, col in flagged_coords}
    hidden = {(int(row), int(col)) for row, col in hidden_coords}
    highlighted_clues = {(int(row), int(col)) for row, col in (highlighted_clue_coords or ())}

    cell_bboxes_px: Dict[str, List[float]] = {}
    full_cell_bboxes_px: Dict[str, List[float]] = {}
    scene_entities: List[Dict[str, Any]] = []
    cell_specs: List[MinesweeperCellSpec] = []
    for row, col in all_coords(size=int(board_size)):
        coord = (int(row), int(col))
        cell_id = coord_to_cell_id(coord)
        full_bbox = _cell_bbox(
            board_left=board_left,
            board_top=board_top,
            cell_size=cell_size,
            row=int(row),
            col=int(col),
        )
        bbox_px = _cell_bbox(
            board_left=board_left,
            board_top=board_top,
            cell_size=cell_size,
            row=int(row),
            col=int(col),
            padding_px=float(params.cell_padding_px),
        )
        cell_bboxes_px[cell_id] = list(bbox_px)
        full_cell_bboxes_px[cell_id] = list(full_bbox)
        if coord in revealed:
            fill = theme.revealed_cell_alt_fill_rgb if (int(row) + int(col)) % 2 else theme.revealed_cell_fill_rgb
            draw.rectangle(full_bbox, fill=tuple(int(v) for v in fill))
        else:
            draw.rectangle(full_bbox, fill=tuple(int(v) for v in theme.hidden_cell_fill_rgb))
            inset = max(1.0, 0.08 * float(cell_size))
            draw.rectangle(
                (
                    full_bbox[0] + inset,
                    full_bbox[1] + inset,
                    full_bbox[2] - inset,
                    full_bbox[3] - inset,
                ),
                outline=tuple(int(v) for v in theme.hidden_cell_border_rgb),
                width=max(1, int(round(0.04 * float(cell_size)))),
            )
        if coord in flagged:
            _draw_flag(draw, bbox_px=bbox_px, theme=theme)
        elif coord in revealed:
            _draw_number(
                draw,
                bbox_px=bbox_px,
                value=clue_number(coord, mine_coords=mines, size=int(board_size)),
                theme=theme,
                font_size_px=int(params.number_font_size_px),
            )
        if coord in revealed:
            state = "revealed"
        elif coord in flagged:
            state = "flagged"
        else:
            state = "hidden"
        adjacent = clue_number(coord, mine_coords=mines, size=int(board_size))
        scene_entities.append(
            {
                "entity_id": str(cell_id),
                "entity_type": "minesweeper_cell",
                "row": int(row),
                "col": int(col),
                "state": str(state),
                "has_mine": bool(coord in mines),
                "adjacent_mine_count": int(adjacent),
                "is_highlighted_clue": bool(coord in highlighted_clues),
                "bbox_px": list(bbox_px),
            }
        )
        cell_specs.append(
            MinesweeperCellSpec(
                cell_id=str(cell_id),
                row=int(row),
                col=int(col),
                state=str(state),
                has_mine=bool(coord in mines),
                adjacent_mine_count=int(adjacent),
                bbox_px=bbox_px,
            )
        )

    for index in range(board_size + 1):
        x = float(board_left + (index * cell_size))
        y = float(board_top + (index * cell_size))
        draw.line(
            [(x, board_top), (x, float(board_bbox[3]))],
            fill=tuple(int(v) for v in theme.grid_line_rgb),
            width=int(params.grid_line_width_px),
        )
        draw.line(
            [(board_left, y), (float(board_bbox[2]), y)],
            fill=tuple(int(v) for v in theme.grid_line_rgb),
            width=int(params.grid_line_width_px),
        )
    for coord in sorted(highlighted_clues):
        cell_id = coord_to_cell_id(coord)
        if cell_id not in full_cell_bboxes_px:
            continue
        left, top, right, bottom = [float(value) for value in full_cell_bboxes_px[cell_id]]
        inset = max(2.0, 0.055 * float(cell_size))
        highlight_bbox = (left + inset, top + inset, right - inset, bottom - inset)
        width = max(4, int(round(0.075 * float(cell_size))))
        draw.rectangle(highlight_bbox, outline=(20, 20, 20, 220), width=width + 2)
        draw.rectangle(highlight_bbox, outline=(255, 212, 74, 255), width=width)
    draw.rectangle(
        board_bbox,
        outline=tuple(int(v) for v in theme.board_border_rgb),
        width=int(params.board_border_width_px),
    )

    render_map = {
        "board_bbox_px": list(board_bbox),
        "cell_bboxes_px": dict(cell_bboxes_px),
        "revealed_cell_ids": [coord_to_cell_id(coord) for coord in sorted(revealed)],
        "flagged_cell_ids": [coord_to_cell_id(coord) for coord in sorted(flagged)],
        "hidden_cell_ids": [coord_to_cell_id(coord) for coord in sorted(hidden)],
        "highlighted_clue_cell_ids": [coord_to_cell_id(coord) for coord in sorted(highlighted_clues)],
        "layout_jitter": dict(layout_jitter),
    }
    return RenderedMinesweeperScene(
        image=image,
        cell_specs=tuple(cell_specs),
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "MinesweeperCellSpec",
    "MinesweeperRenderParams",
    "RenderedMinesweeperScene",
    "render_minesweeper_grid_scene",
]
