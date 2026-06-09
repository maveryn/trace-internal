"""Shared Backgammon board renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from .text import draw_centered_game_text as draw_centered_text
from ...shared.text_rendering import fit_font_to_box, resolve_text_stroke_fill
from .backgammon_common import (
    PLAYER_BLACK,
    PLAYER_WHITE,
    POINT_IDS,
    BackgammonPoint,
    checker_entity_id,
    die_entity_id,
    point_entity_id,
    stack_at,
)
from .layout import apply_games_layout_jitter_to_bbox
from .scene_style import GamePanelSceneStyle, draw_panel_scene_chrome, game_panel_scene_style_metadata


@dataclass(frozen=True)
class BackgammonRenderParams:
    """Resolved render controls for one Backgammon scene."""

    canvas_width: int
    canvas_height: int
    board_width_px: int
    board_height_px: int
    board_margin_px: int
    board_border_width_px: int
    point_label_font_size_px: int
    header_font_size_px: int
    checker_radius_px: int
    die_size_px: int
    font_family: str = ""
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class BackgammonTheme:
    """Resolved Backgammon board palette."""

    board_fill_rgb: Tuple[int, int, int]
    board_outline_rgb: Tuple[int, int, int]
    bar_fill_rgb: Tuple[int, int, int]
    triangle_light_rgb: Tuple[int, int, int]
    triangle_dark_rgb: Tuple[int, int, int]
    label_rgb: Tuple[int, int, int]
    black_checker_rgb: Tuple[int, int, int]
    white_checker_rgb: Tuple[int, int, int]
    checker_outline_rgb: Tuple[int, int, int]
    die_fill_rgb: Tuple[int, int, int]
    die_pip_rgb: Tuple[int, int, int]
    header_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedBackgammonScene:
    """Rendered Backgammon image plus trace-friendly geometry."""

    image: Image.Image
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def build_games_backgammon_theme(*, style_variant: str) -> BackgammonTheme:
    """Return one Backgammon board visual theme."""

    style = str(style_variant)
    if style == "navy":
        return BackgammonTheme(
            board_fill_rgb=(24, 43, 70),
            board_outline_rgb=(171, 196, 222),
            bar_fill_rgb=(37, 61, 92),
            triangle_light_rgb=(222, 225, 220),
            triangle_dark_rgb=(75, 139, 186),
            label_rgb=(238, 242, 247),
            black_checker_rgb=(23, 24, 31),
            white_checker_rgb=(235, 238, 229),
            checker_outline_rgb=(251, 252, 246),
            die_fill_rgb=(235, 238, 229),
            die_pip_rgb=(20, 24, 32),
            header_rgb=(245, 248, 252),
        )
    if style == "parchment":
        return BackgammonTheme(
            board_fill_rgb=(235, 218, 174),
            board_outline_rgb=(92, 67, 42),
            bar_fill_rgb=(183, 143, 91),
            triangle_light_rgb=(248, 234, 190),
            triangle_dark_rgb=(153, 82, 58),
            label_rgb=(54, 41, 30),
            black_checker_rgb=(45, 38, 32),
            white_checker_rgb=(246, 238, 216),
            checker_outline_rgb=(76, 53, 36),
            die_fill_rgb=(249, 241, 219),
            die_pip_rgb=(59, 43, 31),
            header_rgb=(55, 40, 30),
        )
    if style == "slate":
        return BackgammonTheme(
            board_fill_rgb=(43, 50, 56),
            board_outline_rgb=(183, 193, 200),
            bar_fill_rgb=(64, 72, 78),
            triangle_light_rgb=(180, 188, 195),
            triangle_dark_rgb=(91, 111, 126),
            label_rgb=(239, 243, 246),
            black_checker_rgb=(18, 19, 22),
            white_checker_rgb=(224, 228, 230),
            checker_outline_rgb=(245, 248, 249),
            die_fill_rgb=(226, 231, 232),
            die_pip_rgb=(28, 31, 35),
            header_rgb=(239, 243, 246),
        )
    if style == "tournament":
        return BackgammonTheme(
            board_fill_rgb=(33, 101, 82),
            board_outline_rgb=(238, 207, 132),
            bar_fill_rgb=(47, 125, 101),
            triangle_light_rgb=(244, 223, 150),
            triangle_dark_rgb=(173, 52, 54),
            label_rgb=(245, 239, 208),
            black_checker_rgb=(26, 31, 33),
            white_checker_rgb=(244, 242, 230),
            checker_outline_rgb=(30, 31, 30),
            die_fill_rgb=(244, 242, 230),
            die_pip_rgb=(34, 37, 39),
            header_rgb=(244, 238, 205),
        )
    return BackgammonTheme(
        board_fill_rgb=(118, 72, 41),
        board_outline_rgb=(58, 39, 25),
        bar_fill_rgb=(92, 57, 34),
        triangle_light_rgb=(222, 169, 92),
        triangle_dark_rgb=(91, 49, 34),
        label_rgb=(250, 236, 207),
        black_checker_rgb=(28, 26, 24),
        white_checker_rgb=(238, 226, 201),
        checker_outline_rgb=(67, 42, 28),
        die_fill_rgb=(244, 232, 207),
        die_pip_rgb=(45, 33, 25),
        header_rgb=(250, 237, 211),
    )


def _point_order() -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Return visible top and bottom point labels."""

    return tuple(range(24, 12, -1)), tuple(range(1, 13))


def _point_geometry(
    *,
    board_bbox: Tuple[float, float, float, float],
    point_height: float,
) -> Dict[int, Dict[str, Any]]:
    """Return triangle polygons, point bboxes, and stack centers for all points."""

    left, top, right, bottom = [float(v) for v in board_bbox]
    bar_width = float((right - left) * 0.058)
    section_width = float(((right - left) - bar_width) / 2.0)
    point_width = float(section_width / 6.0)
    bar_left = float(left + section_width)
    right_section_left = float(bar_left + bar_width)
    geometry: Dict[int, Dict[str, Any]] = {}

    top_points, bottom_points = _point_order()
    for row_name, points in (("top", top_points), ("bottom", bottom_points)):
        for index, point in enumerate(points):
            section_index = int(index // 6)
            col_index = int(index % 6)
            section_left = left if section_index == 0 else right_section_left
            x0 = float(section_left + (col_index * point_width))
            x1 = float(x0 + point_width)
            cx = float((x0 + x1) / 2.0)
            if row_name == "top":
                polygon = ((x0, top), (x1, top), (cx, top + point_height))
                bbox = (x0, top, x1, top + point_height)
                stack_start = (cx, top + 26.0)
                stack_direction = 1.0
                label_center = (cx, top + point_height + 19.0)
            else:
                polygon = ((x0, bottom), (x1, bottom), (cx, bottom - point_height))
                bbox = (x0, bottom - point_height, x1, bottom)
                stack_start = (cx, bottom - 26.0)
                stack_direction = -1.0
                label_center = (cx, bottom - point_height - 19.0)
            geometry[int(point)] = {
                "polygon": tuple((round(float(px), 3), round(float(py), 3)) for px, py in polygon),
                "bbox": tuple(round(float(v), 3) for v in bbox),
                "center": (round(cx, 3), round(float((bbox[1] + bbox[3]) / 2.0), 3)),
                "stack_start": (round(float(stack_start[0]), 3), round(float(stack_start[1]), 3)),
                "stack_direction": float(stack_direction),
                "label_center": (round(float(label_center[0]), 3), round(float(label_center[1]), 3)),
            }
    return geometry


def _checker_bbox(center: Tuple[float, float], radius: float) -> Tuple[float, float, float, float]:
    """Return one checker bbox."""

    cx, cy = float(center[0]), float(center[1])
    return (
        round(cx - float(radius), 3),
        round(cy - float(radius), 3),
        round(cx + float(radius), 3),
        round(cy + float(radius), 3),
    )


def _draw_die(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    value: int,
    size: int,
    theme: BackgammonTheme,
) -> Tuple[float, float, float, float]:
    """Draw one die and return its bbox."""

    cx, cy = float(center[0]), float(center[1])
    half = float(size) / 2.0
    bbox = (round(cx - half, 3), round(cy - half, 3), round(cx + half, 3), round(cy + half, 3))
    draw.rounded_rectangle(
        bbox,
        radius=max(4, int(size * 0.18)),
        fill=tuple(int(v) for v in theme.die_fill_rgb) + (255,),
        outline=tuple(int(v) for v in theme.board_outline_rgb) + (255,),
        width=max(2, int(size * 0.06)),
    )
    pip_offsets = {
        1: ((0, 0),),
        2: ((-1, -1), (1, 1)),
        3: ((-1, -1), (0, 0), (1, 1)),
        4: ((-1, -1), (1, -1), (-1, 1), (1, 1)),
        5: ((-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)),
        6: ((-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)),
    }
    pip_radius = max(2.0, float(size) * 0.055)
    step = float(size) * 0.25
    for ox, oy in pip_offsets[int(value)]:
        pcx = float(cx + (float(ox) * step))
        pcy = float(cy + (float(oy) * step))
        draw.ellipse(
            (pcx - pip_radius, pcy - pip_radius, pcx + pip_radius, pcy + pip_radius),
            fill=tuple(int(v) for v in theme.die_pip_rgb) + (255,),
        )
    return bbox


def render_backgammon_scene(
    *,
    points: Mapping[int, BackgammonPoint],
    dice: Tuple[int, int],
    background: Image.Image,
    style_variant: str,
    active_player: str,
    params: BackgammonRenderParams,
    panel_style: GamePanelSceneStyle | None = None,
) -> RenderedBackgammonScene:
    """Render one visible Backgammon board with numbered points and dice."""

    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme = build_games_backgammon_theme(style_variant=str(style_variant))
    left = float((int(params.canvas_width) - int(params.board_width_px)) / 2.0)
    top = float((int(params.canvas_height) - int(params.board_height_px)) / 2.0)
    board_bbox = (
        left,
        top,
        left + float(params.board_width_px),
        top + float(params.board_height_px),
    )
    if isinstance(params.layout_jitter_meta, Mapping):
        board_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
            bbox_px=board_bbox,
            canvas_width=int(params.canvas_width),
            canvas_height=int(params.canvas_height),
            jitter=params.layout_jitter_meta,
        )
    else:
        layout_jitter = {}

    panel_bbox: Tuple[int, int, int, int] | None = None
    if panel_style is not None:
        panel_pad_x = max(22, int(round(float(params.board_margin_px) * 0.42)))
        panel_pad_top = max(52, int(round(float(params.header_font_size_px) * 2.0)) + 22)
        panel_pad_bottom = max(22, int(round(float(params.board_margin_px) * 0.36)))
        panel_bbox = (
            max(4, int(round(board_bbox[0])) - panel_pad_x),
            max(4, int(round(board_bbox[1])) - panel_pad_top),
            min(int(params.canvas_width) - 4, int(round(board_bbox[2])) + panel_pad_x),
            min(int(params.canvas_height) - 4, int(round(board_bbox[3])) + panel_pad_bottom),
        )
        draw_panel_scene_chrome(
            draw,
            bbox=panel_bbox,
            style=panel_style,
            radius=28,
            border_width=max(2, int(round(float(params.board_border_width_px) * 0.55))),
        )

    draw.rounded_rectangle(
        board_bbox,
        radius=24,
        fill=tuple(int(v) for v in theme.board_fill_rgb) + (246,),
        outline=tuple(int(v) for v in theme.board_outline_rgb) + (255,),
        width=max(2, int(params.board_border_width_px)),
    )
    left_b, top_b, right_b, bottom_b = [float(v) for v in board_bbox]
    bar_width = float((right_b - left_b) * 0.058)
    section_width = float(((right_b - left_b) - bar_width) / 2.0)
    bar_bbox = (
        round(left_b + section_width, 3),
        round(top_b + 8.0, 3),
        round(left_b + section_width + bar_width, 3),
        round(bottom_b - 8.0, 3),
    )
    draw.rectangle(
        bar_bbox,
        fill=tuple(int(v) for v in theme.bar_fill_rgb) + (245,),
        outline=tuple(int(v) for v in theme.board_outline_rgb) + (220,),
        width=2,
    )

    point_height = float((bottom_b - top_b) * 0.38)
    point_geometry = _point_geometry(board_bbox=board_bbox, point_height=point_height)
    point_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    checker_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    entity_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    scene_entities: list[Dict[str, Any]] = []

    min_point_width = min(float(value["bbox"][2] - value["bbox"][0]) for value in point_geometry.values())
    label_font = fit_font_to_box(
        draw,
        text="24",
        max_width=max(12.0, float(min_point_width) * 0.72),
        max_height=max(10.0, float(params.point_label_font_size_px) * 1.45),
        bold=True,
        min_size_px=8,
        max_size_px=max(8, int(params.point_label_font_size_px)),
        fill_ratio=0.96,
        font_family=str(params.font_family) or None,
    )
    for point in POINT_IDS:
        geom = point_geometry[int(point)]
        fill = theme.triangle_dark_rgb if int(point) % 2 else theme.triangle_light_rgb
        draw.polygon(
            geom["polygon"],
            fill=tuple(int(v) for v in fill) + (245,),
            outline=tuple(int(v) for v in theme.board_outline_rgb) + (150,),
        )
        point_bbox = tuple(float(v) for v in geom["bbox"])
        point_bboxes[point_entity_id(point)] = point_bbox
        entity_bboxes[point_entity_id(point)] = point_bbox
        scene_entities.append(
            {
                "entity_id": point_entity_id(point),
                "entity_type": "backgammon_point",
                "point_id": int(point),
                "bbox_px": list(point_bbox),
            }
        )
        draw_centered_text(
            draw,
            text=str(point),
            center=geom["label_center"],
            font=label_font,
            fill=tuple(int(v) for v in theme.label_rgb),
            stroke_fill=tuple(int(v) for v in theme.board_fill_rgb),
            stroke_width=2,
        )

    radius = float(params.checker_radius_px)
    stack_step = float(radius * 1.34)
    checker_font = fit_font_to_box(
        draw,
        text="4",
        max_width=max(8.0, float(radius) * 1.12),
        max_height=max(8.0, float(radius) * 1.12),
        bold=True,
        min_size_px=7,
        max_size_px=max(8, int(radius * 0.72)),
        fill_ratio=0.92,
        font_family=str(params.font_family) or None,
    )
    for point in POINT_IDS:
        stack = stack_at(points, int(point))
        if stack.owner is None or int(stack.count) <= 0:
            continue
        geom = point_geometry[int(point)]
        sx, sy = geom["stack_start"]
        direction = float(geom["stack_direction"])
        fill = theme.black_checker_rgb if str(stack.owner) == PLAYER_BLACK else theme.white_checker_rgb
        for index in range(int(stack.count)):
            cy = float(sy + (direction * stack_step * float(index)))
            center = (float(sx), float(cy))
            bbox = _checker_bbox(center, radius)
            draw.ellipse(
                bbox,
                fill=tuple(int(v) for v in fill) + (255,),
                outline=tuple(int(v) for v in theme.checker_outline_rgb) + (255,),
                width=3,
            )
            if int(stack.count) >= 4 and index == int(stack.count) - 1:
                draw_centered_text(
                    draw,
                    text=str(stack.count),
                    center=center,
                    font=checker_font,
                    fill=tuple(int(v) for v in theme.label_rgb),
                    stroke_fill=tuple(int(v) for v in fill),
                    stroke_width=2,
                )
            entity_id = checker_entity_id(point, index)
            checker_bboxes[str(entity_id)] = bbox
            entity_bboxes[str(entity_id)] = bbox
            scene_entities.append(
                {
                    "entity_id": str(entity_id),
                    "entity_type": "backgammon_checker",
                    "point_id": int(point),
                    "stack_index": int(index),
                    "owner": str(stack.owner),
                    "bbox_px": list(bbox),
                }
            )

    die_size = int(params.die_size_px)
    die_y = float((top_b + bottom_b) / 2.0)
    die_x0 = float((left_b + right_b) / 2.0) - float(die_size * 0.68)
    die_x1 = float((left_b + right_b) / 2.0) + float(die_size * 0.68)
    for index, (x, value) in enumerate(((die_x0, dice[0]), (die_x1, dice[1]))):
        die_bbox = _draw_die(draw, center=(x, die_y), value=int(value), size=die_size, theme=theme)
        entity_id = die_entity_id(index)
        entity_bboxes[str(entity_id)] = die_bbox
        scene_entities.append(
            {
                "entity_id": str(entity_id),
                "entity_type": "backgammon_die",
                "die_index": int(index),
                "value": int(value),
                "bbox_px": list(die_bbox),
            }
        )

    player_text = "White" if str(active_player) == PLAYER_WHITE else "Black"
    direction_text = "1 to 24" if str(active_player) == PLAYER_WHITE else "24 to 1"
    header_text = f"{player_text.upper()} moves {direction_text} | use either die"
    header_height = max(28.0, float(params.header_font_size_px) * 1.85)
    header_y1 = round(float(top_b - 8.0), 3)
    header_y0 = round(max(4.0, float(header_y1 - header_height)), 3)
    header_pad_x = max(18.0, float(right_b - left_b) * 0.09)
    header_bbox = (
        round(float(left_b + header_pad_x), 3),
        header_y0,
        round(float(right_b - header_pad_x), 3),
        header_y1,
    )
    draw.rounded_rectangle(
        header_bbox,
        radius=max(8, int(round(float(header_height) * 0.32))),
        fill=tuple(int(v) for v in theme.board_fill_rgb) + (232,),
        outline=tuple(int(v) for v in theme.board_outline_rgb) + (245,),
        width=max(2, int(round(float(params.board_border_width_px) * 0.62))),
    )
    header_font = fit_font_to_box(
        draw,
        text=header_text,
        max_width=max(80.0, float(header_bbox[2] - header_bbox[0]) * 0.94),
        max_height=max(12.0, float(header_bbox[3] - header_bbox[1]) * 0.74),
        bold=True,
        min_size_px=10,
        max_size_px=max(9, int(params.header_font_size_px)),
        fill_ratio=0.98,
        font_family=str(params.font_family) or None,
    )
    header_fill = tuple(int(v) for v in theme.header_rgb)
    draw_centered_text(
        draw,
        text=header_text,
        center=(float((header_bbox[0] + header_bbox[2]) / 2.0), float((header_bbox[1] + header_bbox[3]) / 2.0)),
        font=header_font,
        fill=header_fill,
        stroke_fill=resolve_text_stroke_fill(header_fill),
        stroke_width=1,
    )

    render_map = {
        "board_bbox_px": [round(float(v), 3) for v in board_bbox],
        "panel_bbox_px": None if panel_bbox is None else [int(value) for value in panel_bbox],
        "bar_bbox_px": list(bar_bbox),
        "header_bbox_px": [round(float(v), 3) for v in header_bbox],
        "point_bboxes_px": {str(key): list(value) for key, value in point_bboxes.items()},
        "checker_bboxes_px": {str(key): list(value) for key, value in checker_bboxes.items()},
        "entity_bboxes_px": {str(key): list(value) for key, value in entity_bboxes.items()},
        "layout_jitter": dict(layout_jitter),
        "style_variant": str(style_variant),
        "active_player": str(active_player),
        "movement_direction_text": str(direction_text),
        "panel_scene_style": None if panel_style is None else game_panel_scene_style_metadata(panel_style),
        "effective_point_width_px": round(float(min_point_width), 3),
        "font_family": str(params.font_family),
    }
    return RenderedBackgammonScene(
        image=image.convert("RGB"),
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "BackgammonRenderParams",
    "BackgammonTheme",
    "RenderedBackgammonScene",
    "build_games_backgammon_theme",
    "render_backgammon_scene",
]
