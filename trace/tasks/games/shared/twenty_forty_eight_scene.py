"""Shared renderer for 2048 board scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.text_rendering import fit_font_to_box
from .layout import apply_games_layout_jitter_to_bbox
from .scene_style import GamePanelSceneStyle, draw_panel_scene_chrome, game_panel_scene_style_metadata
from .twenty_forty_eight_common import (
    Board,
    Coord,
    EMPTY,
    SIZE,
    SUPPORTED_2048_DIRECTIONS,
    coord_to_cell_id,
)


@dataclass(frozen=True)
class TwentyFortyEightRenderParams:
    """Resolved render controls for one 2048 board."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    board_size_px: int
    board_radius_px: int
    cell_gap_px: int
    cell_radius_px: int
    tile_font_size_px: int
    arrow_width_px: int
    label_font_size_px: int
    goal_outline_width_px: int
    font_family: str = ""
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class TwentyFortyEightTheme:
    """Resolved palette for one 2048 visual style."""

    board_fill_rgb: Tuple[int, int, int]
    board_outline_rgb: Tuple[int, int, int]
    empty_cell_rgb: Tuple[int, int, int]
    tile_text_rgb_dark: Tuple[int, int, int]
    tile_text_rgb_light: Tuple[int, int, int]
    arrow_rgb: Tuple[int, int, int]
    arrow_label_fill_rgb: Tuple[int, int, int]
    arrow_label_text_rgb: Tuple[int, int, int]
    goal_outline_rgb: Tuple[int, int, int]
    tile_palette: Mapping[int, Tuple[int, int, int]]


@dataclass(frozen=True)
class Rendered2048Scene:
    """Rendered 2048 image plus trace-friendly geometry."""

    image: Image.Image
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def build_2048_theme(*, style_variant: str) -> TwentyFortyEightTheme:
    """Return a 2048 palette for one style variant."""

    palettes: Dict[str, TwentyFortyEightTheme] = {
        "classic": TwentyFortyEightTheme(
            board_fill_rgb=(179, 165, 148),
            board_outline_rgb=(117, 103, 89),
            empty_cell_rgb=(205, 193, 180),
            tile_text_rgb_dark=(116, 102, 88),
            tile_text_rgb_light=(250, 246, 238),
            arrow_rgb=(63, 91, 125),
            arrow_label_fill_rgb=(246, 243, 232),
            arrow_label_text_rgb=(41, 48, 58),
            goal_outline_rgb=(34, 150, 214),
            tile_palette={
                2: (238, 228, 218),
                4: (237, 224, 200),
                8: (242, 177, 121),
                16: (245, 149, 99),
                32: (246, 124, 95),
                64: (246, 94, 59),
                128: (237, 207, 114),
                256: (237, 204, 97),
                512: (237, 200, 80),
            },
        ),
        "dark": TwentyFortyEightTheme(
            board_fill_rgb=(38, 45, 54),
            board_outline_rgb=(18, 22, 28),
            empty_cell_rgb=(61, 70, 82),
            tile_text_rgb_dark=(30, 35, 44),
            tile_text_rgb_light=(247, 250, 252),
            arrow_rgb=(96, 196, 181),
            arrow_label_fill_rgb=(21, 27, 36),
            arrow_label_text_rgb=(238, 246, 248),
            goal_outline_rgb=(255, 212, 95),
            tile_palette={
                2: (184, 205, 214),
                4: (149, 188, 202),
                8: (99, 168, 198),
                16: (72, 143, 194),
                32: (118, 122, 211),
                64: (147, 92, 198),
                128: (207, 93, 167),
                256: (225, 91, 117),
                512: (238, 137, 82),
            },
        ),
        "paper": TwentyFortyEightTheme(
            board_fill_rgb=(214, 204, 183),
            board_outline_rgb=(91, 84, 69),
            empty_cell_rgb=(239, 232, 214),
            tile_text_rgb_dark=(74, 67, 56),
            tile_text_rgb_light=(255, 252, 242),
            arrow_rgb=(106, 86, 63),
            arrow_label_fill_rgb=(255, 248, 228),
            arrow_label_text_rgb=(73, 58, 42),
            goal_outline_rgb=(196, 82, 72),
            tile_palette={
                2: (246, 236, 209),
                4: (232, 218, 178),
                8: (222, 185, 111),
                16: (209, 151, 84),
                32: (196, 114, 81),
                64: (170, 85, 78),
                128: (143, 116, 73),
                256: (111, 119, 91),
                512: (83, 114, 113),
            },
        ),
        "neon": TwentyFortyEightTheme(
            board_fill_rgb=(22, 24, 55),
            board_outline_rgb=(83, 95, 173),
            empty_cell_rgb=(40, 43, 88),
            tile_text_rgb_dark=(14, 20, 35),
            tile_text_rgb_light=(245, 248, 255),
            arrow_rgb=(255, 91, 155),
            arrow_label_fill_rgb=(30, 31, 68),
            arrow_label_text_rgb=(249, 250, 255),
            goal_outline_rgb=(67, 234, 179),
            tile_palette={
                2: (124, 231, 213),
                4: (80, 202, 237),
                8: (87, 148, 245),
                16: (130, 105, 244),
                32: (183, 89, 229),
                64: (237, 82, 177),
                128: (255, 109, 118),
                256: (255, 163, 86),
                512: (246, 222, 91),
            },
        ),
        "pastel": TwentyFortyEightTheme(
            board_fill_rgb=(174, 185, 198),
            board_outline_rgb=(91, 103, 121),
            empty_cell_rgb=(226, 231, 235),
            tile_text_rgb_dark=(61, 73, 88),
            tile_text_rgb_light=(255, 255, 255),
            arrow_rgb=(82, 112, 166),
            arrow_label_fill_rgb=(249, 252, 255),
            arrow_label_text_rgb=(48, 58, 77),
            goal_outline_rgb=(215, 100, 83),
            tile_palette={
                2: (232, 220, 239),
                4: (215, 229, 249),
                8: (198, 233, 226),
                16: (232, 235, 190),
                32: (244, 213, 178),
                64: (241, 188, 179),
                128: (208, 190, 232),
                256: (175, 206, 235),
                512: (154, 203, 191),
            },
        ),
    }
    return palettes.get(str(style_variant), palettes["classic"])


def _cell_bbox(
    *,
    board_left: float,
    board_top: float,
    cell_size: float,
    gap_px: float,
    row: int,
    col: int,
) -> Tuple[float, float, float, float]:
    """Return the bbox for one 2048 cell."""

    left = float(board_left + gap_px + (int(col) * (cell_size + gap_px)))
    top = float(board_top + gap_px + (int(row) * (cell_size + gap_px)))
    return (
        round(left, 3),
        round(top, 3),
        round(float(left + cell_size), 3),
        round(float(top + cell_size), 3),
    )


def _tile_fill(value: int, theme: TwentyFortyEightTheme) -> Tuple[int, int, int]:
    """Return a deterministic tile fill for one value."""

    if int(value) == EMPTY:
        return tuple(int(v) for v in theme.empty_cell_rgb)
    palette = dict(theme.tile_palette)
    if int(value) in palette:
        return tuple(int(v) for v in palette[int(value)])
    return tuple(int(v) for v in palette[max(palette)])


def _draw_tile_text(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    value: int,
    theme: TwentyFortyEightTheme,
    max_font_size_px: int,
    font_family: str,
) -> None:
    """Draw one centered 2048 tile value."""

    if int(value) == EMPTY:
        return
    left, top, right, bottom = [float(v) for v in bbox]
    text = str(int(value))
    font = fit_font_to_box(
        draw,
        text=text,
        max_width=float(right - left),
        max_height=float(bottom - top),
        bold=True,
        min_size_px=18,
        max_size_px=int(max_font_size_px),
        fill_ratio=0.72,
        font_family=str(font_family) or None,
    )
    fill = theme.tile_text_rgb_dark if int(value) <= 4 else theme.tile_text_rgb_light
    draw_centered_text(
        draw,
        text=text,
        center=(float((left + right) / 2.0), float((top + bottom) / 2.0)),
        font=font,
        fill=fill,
        stroke_fill=fill,
        stroke_width=0,
    )


def _direction_arrow_points(
    *,
    direction: str,
    board_bbox: Tuple[float, float, float, float],
    canvas_width: int,
    canvas_height: int,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return start/end points for one prominent move arrow."""

    left, top, right, bottom = [float(v) for v in board_bbox]
    cx = float((left + right) / 2.0)
    cy = float((top + bottom) / 2.0)
    span = min(float(canvas_width), float(canvas_height)) * 0.085
    if str(direction) == "up":
        return (cx, float(top - span * 0.15)), (cx, float(top - span * 0.95))
    if str(direction) == "down":
        return (cx, float(bottom + span * 0.15)), (cx, float(bottom + span * 0.95))
    if str(direction) == "left":
        return (float(left - span * 0.15), cy), (float(left - span * 0.95), cy)
    if str(direction) == "right":
        return (float(right + span * 0.15), cy), (float(right + span * 0.95), cy)
    raise ValueError(f"unsupported direction: {direction!r}")


def _draw_arrow_label(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    center: Tuple[float, float],
    params: TwentyFortyEightRenderParams,
    theme: TwentyFortyEightTheme,
) -> Tuple[float, float, float, float]:
    """Draw a compact label badge near one arrow."""

    radius = max(18.0, float(params.label_font_size_px) * 0.86)
    cx, cy = float(center[0]), float(center[1])
    bbox = (
        round(cx - radius, 3),
        round(cy - radius, 3),
        round(cx + radius, 3),
        round(cy + radius, 3),
    )
    draw.ellipse(
        bbox,
        fill=tuple(int(v) for v in theme.arrow_label_fill_rgb),
        outline=tuple(int(v) for v in theme.arrow_rgb),
        width=3,
    )
    font = fit_font_to_box(
        draw,
        text=str(label),
        max_width=float(2.0 * radius),
        max_height=float(2.0 * radius),
        bold=True,
        min_size_px=12,
        max_size_px=int(params.label_font_size_px),
        fill_ratio=0.70,
        font_family=str(params.font_family) or None,
    )
    draw_centered_text(
        draw,
        text=str(label),
        center=(cx, cy),
        font=font,
        fill=theme.arrow_label_text_rgb,
        stroke_fill=theme.arrow_label_text_rgb,
        stroke_width=0,
    )
    return bbox


def render_2048_board_scene(
    *,
    board: Board,
    background: Image.Image,
    style_variant: str,
    params: TwentyFortyEightRenderParams,
    panel_style: GamePanelSceneStyle | None = None,
    move_direction: str | None = None,
    move_label_by_direction: Mapping[str, str] | None = None,
    goal_cell: Coord | None = None,
) -> Rendered2048Scene:
    """Render one 2048 board with either one move arrow or labeled candidate arrows."""

    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme = build_2048_theme(style_variant=str(style_variant))

    board_size = min(
        int(params.board_size_px),
        int(params.canvas_width) - (2 * int(params.panel_margin_px)),
        int(params.canvas_height) - (2 * int(params.panel_margin_px)),
    )
    board_left = float((int(params.canvas_width) - int(board_size)) / 2.0)
    board_top = float((int(params.canvas_height) - int(board_size)) / 2.0)
    board_bbox = (
        round(board_left, 3),
        round(board_top, 3),
        round(float(board_left + board_size), 3),
        round(float(board_top + board_size), 3),
    )
    board_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    board_left, board_top, board_right, board_bottom = [float(v) for v in board_bbox]

    panel_bbox: Tuple[int, int, int, int] | None = None
    if panel_style is not None:
        panel_pad = max(14, int(round(float(params.cell_gap_px) * 1.5)))
        panel_bbox = (
            max(4, int(round(board_left)) - panel_pad),
            max(4, int(round(board_top)) - panel_pad),
            min(int(params.canvas_width) - 4, int(round(board_right)) + panel_pad),
            min(int(params.canvas_height) - 4, int(round(board_bottom)) + panel_pad),
        )
        draw_panel_scene_chrome(
            draw,
            bbox=panel_bbox,
            style=panel_style,
            radius=max(14, int(params.board_radius_px) + 10),
            border_width=max(2, int(round(float(params.cell_gap_px) * 0.18))),
        )

    draw_rounded_rect(
        draw,
        board_bbox,
        radius=int(params.board_radius_px),
        fill=theme.board_fill_rgb,
        outline=theme.board_outline_rgb,
        width=4,
    )

    gap = float(params.cell_gap_px)
    cell_size = float((board_right - board_left - ((SIZE + 1) * gap)) / float(SIZE))
    entity_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    scene_entities: list[Dict[str, Any]] = []
    for row in range(SIZE):
        for col in range(SIZE):
            value = int(board[row][col])
            cell_id = coord_to_cell_id((row, col))
            bbox = _cell_bbox(
                board_left=board_left,
                board_top=board_top,
                cell_size=cell_size,
                gap_px=gap,
                row=row,
                col=col,
            )
            entity_bboxes[cell_id] = bbox
            fill = _tile_fill(value, theme)
            draw_rounded_rect(
                draw,
                bbox,
                radius=int(params.cell_radius_px),
                fill=fill,
                outline=theme.board_outline_rgb if value == EMPTY else fill,
                width=2,
            )
            if goal_cell is not None and int(goal_cell[0]) == row and int(goal_cell[1]) == col:
                inset = max(3.0, float(params.goal_outline_width_px) * 0.35)
                draw.rounded_rectangle(
                    (
                        float(bbox[0] + inset),
                        float(bbox[1] + inset),
                        float(bbox[2] - inset),
                        float(bbox[3] - inset),
                    ),
                    radius=max(4, int(params.cell_radius_px) - 2),
                    outline=tuple(int(v) for v in theme.goal_outline_rgb),
                    width=int(params.goal_outline_width_px),
                )
            _draw_tile_text(
                draw,
                bbox=bbox,
                value=value,
                theme=theme,
                max_font_size_px=int(params.tile_font_size_px),
                font_family=str(params.font_family),
            )
            scene_entities.append(
                {
                    "id": cell_id,
                    "type": "2048_cell",
                    "row": int(row),
                    "col": int(col),
                    "value": int(value),
                    "bbox": list(bbox),
                }
            )

    arrow_entities: list[Dict[str, Any]] = []
    if move_label_by_direction:
        for direction in SUPPORTED_2048_DIRECTIONS:
            if str(direction) not in move_label_by_direction:
                continue
            start, end = _direction_arrow_points(
                direction=str(direction),
                board_bbox=board_bbox,
                canvas_width=int(params.canvas_width),
                canvas_height=int(params.canvas_height),
            )
            draw_arrow(
                draw,
                start=start,
                end=end,
                fill=theme.arrow_rgb,
                width=int(params.arrow_width_px),
                head_length_px=24,
                head_width_px=28,
            )
            label_center = (
                float(end[0] + ((end[0] - start[0]) * 0.22)),
                float(end[1] + ((end[1] - start[1]) * 0.22)),
            )
            label_bbox = _draw_arrow_label(
                draw,
                label=str(move_label_by_direction[str(direction)]),
                center=label_center,
                params=params,
                theme=theme,
            )
            arrow_entities.append(
                {
                    "id": f"move_{direction}",
                    "type": "2048_candidate_move",
                    "direction": str(direction),
                    "label": str(move_label_by_direction[str(direction)]),
                    "bbox": list(label_bbox),
                }
            )
    elif move_direction is not None:
        start, end = _direction_arrow_points(
            direction=str(move_direction),
            board_bbox=board_bbox,
            canvas_width=int(params.canvas_width),
            canvas_height=int(params.canvas_height),
        )
        draw_arrow(
            draw,
            start=start,
            end=end,
            fill=theme.arrow_rgb,
            width=int(params.arrow_width_px),
            head_length_px=26,
            head_width_px=31,
        )
        arrow_entities.append(
            {
                "id": "shown_move",
                "type": "2048_move_arrow",
                "direction": str(move_direction),
                "bbox": [
                    round(min(start[0], end[0]) - 20.0, 3),
                    round(min(start[1], end[1]) - 20.0, 3),
                    round(max(start[0], end[0]) + 20.0, 3),
                    round(max(start[1], end[1]) + 20.0, 3),
                ],
            }
        )

    scene_entities.extend(arrow_entities)
    render_map: Dict[str, Any] = {
        "entity_bboxes_px": {key: list(value) for key, value in entity_bboxes.items()},
        "board_bbox_px": list(board_bbox),
        "panel_bbox_px": None if panel_bbox is None else [int(value) for value in panel_bbox],
        "layout_jitter": dict(layout_jitter),
        "style_variant": str(style_variant),
        "panel_scene_style": None if panel_style is None else game_panel_scene_style_metadata(panel_style),
        "effective_cell_size_px": round(float(cell_size), 3),
        "font_family": str(params.font_family),
        "goal_cell": None if goal_cell is None else [int(goal_cell[0]), int(goal_cell[1])],
    }
    return Rendered2048Scene(
        image=image,
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "TwentyFortyEightRenderParams",
    "Rendered2048Scene",
    "build_2048_theme",
    "render_2048_board_scene",
]
