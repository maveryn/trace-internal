"""Shared Minesweeper-grid renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import fit_font_to_box
from .text import draw_game_text_traced as draw_text_traced
from .layout import apply_games_layout_jitter_to_bbox
from .marking import draw_semantic_bbox_marker, resolve_semantic_marker_style
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
    font_family: str = ""
    layout_jitter_meta: Dict[str, Any] | None = None
    instance_seed: int = 0


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


def _relative_luminance(rgb: Sequence[int]) -> float:
    """Return approximate sRGB luminance for contrast decisions."""

    r, g, b = (float(value) / 255.0 for value in tuple(rgb)[:3])
    return (0.2126 * r) + (0.7152 * g) + (0.0722 * b)


def _draw_number(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_px: Tuple[float, float, float, float],
    value: int,
    theme: MinesweeperTheme,
    font_size_px: int,
    font_family: str = "",
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
        font_family=str(font_family) or None,
    )
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    text_x = float(left + (0.5 * (width - text_w)) - float(text_bbox[0]))
    text_y = float(top + (0.5 * (height - text_h)) - float(text_bbox[1]))
    colors = tuple(theme.number_rgb_by_value)
    fill = colors[min(max(int(number), 0), len(colors) - 1)]
    draw_text_traced(draw,(text_x, text_y), text, fill=tuple(int(v) for v in fill), font=font, role="readout", required=False)


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


def _draw_reveal_outcome_options(
    draw: ImageDraw.ImageDraw,
    *,
    canvas_width: int,
    canvas_height: int,
    option_panel_top: float,
    options: Sequence[Tuple[str, str]],
    theme: MinesweeperTheme,
    font_family: str = "",
) -> Dict[str, List[float]]:
    """Draw six reveal-outcome option cards and return bboxes keyed by label."""

    option_bboxes: Dict[str, List[float]] = {}
    if not options:
        return option_bboxes
    panel_margin = max(28.0, 0.055 * float(canvas_width))
    gap_x = max(12.0, 0.018 * float(canvas_width))
    gap_y = max(10.0, 0.015 * float(canvas_height))
    panel_bottom = float(canvas_height) - max(22.0, 0.03 * float(canvas_height))
    available_w = float(canvas_width) - (2.0 * panel_margin)
    available_h = max(92.0, panel_bottom - float(option_panel_top))
    card_w = (available_w - (2.0 * gap_x)) / 3.0
    card_h = (available_h - gap_y) / 2.0
    card_fill = tuple(int(v) for v in theme.revealed_cell_fill_rgb) + (238,)
    dark_text = (34, 40, 48)
    light_text = (246, 248, 252)
    text_fill = light_text if _relative_luminance(theme.revealed_cell_fill_rgb) < 0.45 else dark_text
    label_fill = text_fill
    card_outline = tuple(int(v) for v in theme.board_border_rgb)
    for index, (label, outcome) in enumerate(options):
        row = int(index) // 3
        col = int(index) % 3
        left = float(panel_margin + (col * (card_w + gap_x)))
        top = float(option_panel_top + (row * (card_h + gap_y)))
        right = float(left + card_w)
        bottom = float(top + card_h)
        bbox = [round(left, 3), round(top, 3), round(right, 3), round(bottom, 3)]
        option_bboxes[str(label)] = bbox
        radius = max(5, int(round(0.04 * min(card_w, card_h))))
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=radius,
            fill=card_fill,
            outline=card_outline,
            width=max(2, int(round(0.012 * float(canvas_width)))),
        )
        label_text = f"{label})"
        label_font = fit_font_to_box(
            draw,
            text=label_text,
            max_width=0.27 * float(card_w),
            max_height=0.62 * float(card_h),
            bold=True,
            min_size_px=14,
            max_size_px=max(18, int(round(0.34 * float(card_h)))),
            fill_ratio=0.86,
            font_family=str(font_family) or None,
        )
        outcome_text = str(outcome)
        outcome_font = fit_font_to_box(
            draw,
            text=outcome_text,
            max_width=0.58 * float(card_w),
            max_height=0.62 * float(card_h),
            bold=True,
            min_size_px=14,
            max_size_px=max(18, int(round(0.36 * float(card_h)))),
            fill_ratio=0.86,
            font_family=str(font_family) or None,
        )
        label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
        outcome_bbox = draw.textbbox((0, 0), outcome_text, font=outcome_font)
        label_x = float(left + 0.12 * float(card_w) - float(label_bbox[0]))
        label_y = float(top + 0.5 * (float(card_h) - (label_bbox[3] - label_bbox[1])) - float(label_bbox[1]))
        outcome_x = float(left + 0.44 * float(card_w) - float(outcome_bbox[0]))
        outcome_y = float(top + 0.5 * (float(card_h) - (outcome_bbox[3] - outcome_bbox[1])) - float(outcome_bbox[1]))
        draw_text_traced(draw, (label_x, label_y), label_text, fill=label_fill, font=label_font, role="option_label", required=False)
        draw_text_traced(draw, (outcome_x, outcome_y), outcome_text, fill=text_fill, font=outcome_font, role="option_text", required=False)
    return option_bboxes


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
    highlighted_target_coords: Sequence[Coord] | None = None,
    reveal_outcome_options: Sequence[Tuple[str, str]] | None = None,
) -> RenderedMinesweeperScene:
    """Render one Minesweeper grid with hidden, flagged, and revealed cells."""

    board_size = int(size)
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme = build_games_minesweeper_theme(style_variant=str(style_variant))
    options = tuple((str(label), str(outcome)) for label, outcome in (reveal_outcome_options or ()))
    option_panel_height = max(0, int(round(0.24 * int(params.canvas_height)))) if options else 0
    board_canvas_height = int(params.canvas_height) - int(option_panel_height)
    board_canvas_height = max(int(params.panel_margin_px) * 2 + 120, int(board_canvas_height))

    max_board_size = min(
        int(params.max_board_size_px),
        int(params.canvas_width) - (2 * int(params.panel_margin_px)),
        int(board_canvas_height) - (2 * int(params.panel_margin_px)),
    )
    board_left = int(0.5 * (int(params.canvas_width) - int(max_board_size)))
    board_top = int(0.5 * (int(board_canvas_height) - int(max_board_size)))
    board_bbox = (
        round(float(board_left), 3),
        round(float(board_top), 3),
        round(float(board_left + max_board_size), 3),
        round(float(board_top + max_board_size), 3),
    )
    board_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(board_canvas_height),
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
    highlighted_targets = {(int(row), int(col)) for row, col in (highlighted_target_coords or ())}

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
                font_family=str(params.font_family),
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
                "is_highlighted_target": bool(coord in highlighted_targets),
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
        coord_surface_rgb = (
            theme.revealed_cell_alt_fill_rgb
            if (int(coord[0]) + int(coord[1])) % 2
            else theme.revealed_cell_fill_rgb
        )
        marker_style = resolve_semantic_marker_style(
            instance_seed=int(params.instance_seed),
            namespace=f"games.minesweeper.highlighted_clue.{cell_id}",
            role="minesweeper_highlighted_clue",
            surface_rgbs=(tuple(int(v) for v in coord_surface_rgb),),
            preferred_rgbs=((255, 212, 74),),
        )
        draw_semantic_bbox_marker(
            draw,
            highlight_bbox,
            style=marker_style,
            width=width,
            marker_kind="minesweeper_highlighted_clue_outline",
            extra_metadata={"cell_id": str(cell_id)},
            )
    draw.rectangle(
        board_bbox,
        outline=tuple(int(v) for v in theme.board_border_rgb),
        width=int(params.board_border_width_px),
    )
    for coord in sorted(highlighted_targets):
        cell_id = coord_to_cell_id(coord)
        if cell_id not in full_cell_bboxes_px:
            continue
        left, top, right, bottom = [float(value) for value in full_cell_bboxes_px[cell_id]]
        inset = max(2.0, 0.075 * float(cell_size))
        target_bbox = (left + inset, top + inset, right - inset, bottom - inset)
        marker_style = resolve_semantic_marker_style(
            instance_seed=int(params.instance_seed),
            namespace=f"games.minesweeper.reveal_target.{cell_id}",
            role="minesweeper_reveal_target",
            surface_rgbs=(tuple(int(v) for v in theme.hidden_cell_fill_rgb),),
            preferred_rgbs=((220, 32, 32),),
        )
        draw_semantic_bbox_marker(
            draw,
            target_bbox,
            style=marker_style,
            width=max(4, int(round(0.085 * float(cell_size)))),
            marker_kind="minesweeper_reveal_target_outline",
            extra_metadata={"cell_id": str(cell_id)},
        )

    option_panel_top = float(board_canvas_height) + max(6.0, 0.012 * float(params.canvas_height))
    option_bboxes = _draw_reveal_outcome_options(
        draw,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        option_panel_top=float(option_panel_top),
        options=options,
        theme=theme,
        font_family=str(params.font_family),
    )

    render_map = {
        "board_bbox_px": list(board_bbox),
        "cell_bboxes_px": dict(cell_bboxes_px),
        "revealed_cell_ids": [coord_to_cell_id(coord) for coord in sorted(revealed)],
        "flagged_cell_ids": [coord_to_cell_id(coord) for coord in sorted(flagged)],
        "hidden_cell_ids": [coord_to_cell_id(coord) for coord in sorted(hidden)],
        "highlighted_clue_cell_ids": [coord_to_cell_id(coord) for coord in sorted(highlighted_clues)],
        "highlighted_target_cell_ids": [coord_to_cell_id(coord) for coord in sorted(highlighted_targets)],
        "reveal_outcome_options": [
            {"label": str(label), "outcome": str(outcome), "display": str(outcome)}
            for label, outcome in options
        ],
        "reveal_outcome_option_bboxes_px": dict(option_bboxes),
        "style_variant": str(style_variant),
        "text_style": {"font_family": str(params.font_family)},
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
