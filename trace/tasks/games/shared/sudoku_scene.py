"""Shared Sudoku-grid renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import fit_font_to_box
from ...shared.text_legibility import draw_text_traced
from .layout import apply_games_layout_jitter_to_bbox
from .scene_style import GamePanelSceneStyle, draw_panel_scene_chrome, game_panel_scene_style_metadata
from .style import SudokuTheme, build_games_sudoku_theme
from .sudoku_common import Board, Coord, SIZE, coord_to_cell_id, unit_coords


@dataclass(frozen=True)
class SudokuRenderParams:
    """Resolved render controls for one Sudoku scene."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    max_board_size_px: int
    board_border_width_px: int
    grid_line_width_px: int
    box_line_width_px: int
    cell_padding_px: int
    digit_font_size_px: int
    marked_cell_outline_width_px: int
    font_family: str = ""
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class SudokuCellSpec:
    """One rendered Sudoku cell."""

    cell_id: str
    row: int
    col: int
    value: int
    bbox_px: Tuple[float, float, float, float]


@dataclass(frozen=True)
class RenderedSudokuScene:
    """Rendered Sudoku image plus trace-friendly cell geometry."""

    image: Image.Image
    cell_specs: Tuple[SudokuCellSpec, ...]
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
    """Return the bbox for one Sudoku cell, with optional inset padding."""

    left = float(board_left + (int(col) * float(cell_size)) + float(padding_px))
    top = float(board_top + (int(row) * float(cell_size)) + float(padding_px))
    right = float(board_left + ((int(col) + 1) * float(cell_size)) - float(padding_px))
    bottom = float(board_top + ((int(row) + 1) * float(cell_size)) - float(padding_px))
    return (round(left, 3), round(top, 3), round(right, 3), round(bottom, 3))


def _draw_digit(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_px: Tuple[float, float, float, float],
    digit: int,
    theme: SudokuTheme,
    font_size_px: int,
    conflict: bool,
    font_family: str = "",
) -> None:
    """Draw one centered Sudoku digit."""

    left, top, right, bottom = bbox_px
    width = float(right - left)
    height = float(bottom - top)
    text = str(int(digit))
    font = fit_font_to_box(
        draw,
        text=text,
        max_width=float(width),
        max_height=float(height),
        bold=True,
        min_size_px=16,
        max_size_px=int(font_size_px),
        fill_ratio=0.72,
        font_family=str(font_family) or None,
    )
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    text_x = float(left + (0.5 * (width - text_w)) - float(text_bbox[0]))
    text_y = float(top + (0.5 * (height - text_h)) - float(text_bbox[1]))
    fill = theme.conflict_digit_rgb if bool(conflict) else theme.digit_rgb
    draw_text_traced(draw,(text_x, text_y), text, fill=tuple(int(v) for v in fill), font=font, role="readout", required=False)


def render_sudoku_grid_scene(
    *,
    board: Board,
    background: Image.Image,
    style_variant: str,
    params: SudokuRenderParams,
    highlighted_unit_type: str | None = None,
    highlighted_unit_index: int | None = None,
    marked_cell: Coord | None = None,
    conflict_coords: Sequence[Coord] = (),
    panel_style: GamePanelSceneStyle | None = None,
) -> RenderedSudokuScene:
    """Render one visible Sudoku grid with optional highlighted unit and marked cell."""

    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme = build_games_sudoku_theme(style_variant=str(style_variant))

    board_size_px = min(
        int(params.max_board_size_px),
        int(params.canvas_width) - (2 * int(params.panel_margin_px)),
        int(params.canvas_height) - (2 * int(params.panel_margin_px)),
    )
    board_left = int(0.5 * (int(params.canvas_width) - int(board_size_px)))
    board_top = int(0.5 * (int(params.canvas_height) - int(board_size_px)))
    board_bbox = (
        round(float(board_left), 3),
        round(float(board_top), 3),
        round(float(board_left + board_size_px), 3),
        round(float(board_top + board_size_px), 3),
    )
    board_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    board_left = float(board_bbox[0])
    board_top = float(board_bbox[1])
    cell_size = float((float(board_bbox[2]) - float(board_bbox[0])) / float(SIZE))

    if panel_style is not None:
        panel_pad = max(18.0, float(params.board_border_width_px) * 2.5)
        panel_bbox = (
            int(round(max(6.0, float(board_bbox[0]) - panel_pad))),
            int(round(max(6.0, float(board_bbox[1]) - panel_pad))),
            int(round(min(float(params.canvas_width) - 6.0, float(board_bbox[2]) + panel_pad))),
            int(round(min(float(params.canvas_height) - 6.0, float(board_bbox[3]) + panel_pad))),
        )
        draw_panel_scene_chrome(
            draw,
            bbox=panel_bbox,
            style=panel_style,
            radius=20,
            border_width=2,
        )

    draw.rectangle(board_bbox, fill=tuple(int(v) for v in theme.board_fill_rgb))
    inner_board_bbox = (
        round(float(board_bbox[0] + int(params.board_border_width_px)), 3),
        round(float(board_bbox[1] + int(params.board_border_width_px)), 3),
        round(float(board_bbox[2] - int(params.board_border_width_px)), 3),
        round(float(board_bbox[3] - int(params.board_border_width_px)), 3),
    )
    draw.rectangle(inner_board_bbox, fill=tuple(int(v) for v in theme.cell_fill_rgb))

    highlighted_coords: set[Coord] = set()
    if highlighted_unit_type is not None and highlighted_unit_index is not None:
        highlighted_coords = set(unit_coords(str(highlighted_unit_type), int(highlighted_unit_index)))
    for row, col in sorted(highlighted_coords):
        draw.rectangle(
            _cell_bbox(board_left=board_left, board_top=board_top, cell_size=cell_size, row=row, col=col),
            fill=tuple(int(v) for v in theme.highlighted_cell_fill_rgba),
        )
    if marked_cell is not None:
        mark_row, mark_col = int(marked_cell[0]), int(marked_cell[1])
        draw.rectangle(
            _cell_bbox(board_left=board_left, board_top=board_top, cell_size=cell_size, row=mark_row, col=mark_col),
            fill=tuple(int(v) for v in theme.marked_cell_fill_rgba),
        )

    cell_bboxes_px: Dict[str, List[float]] = {}
    scene_entities: List[Dict[str, Any]] = []
    cell_specs: List[SudokuCellSpec] = []
    conflict_set = {(int(row), int(col)) for row, col in conflict_coords}
    for row in range(SIZE):
        for col in range(SIZE):
            cell_id = coord_to_cell_id((row, col))
            bbox_px = _cell_bbox(
                board_left=board_left,
                board_top=board_top,
                cell_size=cell_size,
                row=row,
                col=col,
                padding_px=float(params.cell_padding_px),
            )
            cell_bboxes_px[cell_id] = list(bbox_px)
            value = int(board[row][col])
            if value != 0:
                _draw_digit(
                    draw,
                    bbox_px=bbox_px,
                    digit=int(value),
                    theme=theme,
                    font_size_px=int(params.digit_font_size_px),
                    conflict=(row, col) in conflict_set,
                    font_family=str(params.font_family),
                )
            scene_entities.append(
                {
                    "entity_id": str(cell_id),
                    "entity_type": "sudoku_cell",
                    "row": int(row),
                    "col": int(col),
                    "value": int(value),
                    "filled": bool(value != 0),
                    "highlighted": bool((row, col) in highlighted_coords),
                    "marked": bool(marked_cell is not None and (row, col) == (int(marked_cell[0]), int(marked_cell[1]))),
                    "conflict": bool((row, col) in conflict_set),
                    "bbox_px": list(bbox_px),
                }
            )
            cell_specs.append(
                SudokuCellSpec(
                    cell_id=str(cell_id),
                    row=int(row),
                    col=int(col),
                    value=int(value),
                    bbox_px=bbox_px,
                )
            )

    # Draw grid lines after cell fills and digits so the 3 by 3 structure remains clear.
    for index in range(SIZE + 1):
        x = float(board_left + (index * cell_size))
        y = float(board_top + (index * cell_size))
        is_box_line = int(index) % 3 == 0
        line_rgb = theme.box_line_rgb if bool(is_box_line) else theme.grid_line_rgb
        line_width = int(params.box_line_width_px if bool(is_box_line) else params.grid_line_width_px)
        draw.line(
            [(x, board_top), (x, float(board_bbox[3]))],
            fill=tuple(int(v) for v in line_rgb),
            width=int(line_width),
        )
        draw.line(
            [(board_left, y), (float(board_bbox[2]), y)],
            fill=tuple(int(v) for v in line_rgb),
            width=int(line_width),
        )
    draw.rectangle(
        board_bbox,
        outline=tuple(int(v) for v in theme.board_border_rgb),
        width=int(params.board_border_width_px),
    )

    if marked_cell is not None:
        mark_row, mark_col = int(marked_cell[0]), int(marked_cell[1])
        draw.rectangle(
            _cell_bbox(
                board_left=board_left,
                board_top=board_top,
                cell_size=cell_size,
                row=mark_row,
                col=mark_col,
                padding_px=0.5 * float(params.marked_cell_outline_width_px),
            ),
            outline=tuple(int(v) for v in theme.marked_cell_outline_rgb),
            width=int(params.marked_cell_outline_width_px),
        )

    render_map = {
        "board_bbox_px": list(board_bbox),
        "cell_bboxes_px": dict(cell_bboxes_px),
        "highlighted_cell_ids": [
            coord_to_cell_id(coord) for coord in sorted(highlighted_coords)
        ],
        "marked_cell_id": coord_to_cell_id(marked_cell) if marked_cell is not None else None,
        "conflict_cell_ids": [coord_to_cell_id(coord) for coord in sorted(conflict_set)],
        "style_variant": str(style_variant),
        "text_style": {"font_family": str(params.font_family)},
        "font_family": str(params.font_family),
        "panel_scene_style": None if panel_style is None else game_panel_scene_style_metadata(panel_style),
        "layout_jitter": dict(layout_jitter),
    }
    return RenderedSudokuScene(
        image=image.convert("RGB"),
        cell_specs=tuple(cell_specs),
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "RenderedSudokuScene",
    "SudokuCellSpec",
    "SudokuRenderParams",
    "render_sudoku_grid_scene",
]
