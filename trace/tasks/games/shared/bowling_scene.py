"""Shared Bowling lane renderer for games-domain tasks."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_arrow, draw_dashed_line
from ...shared.text_rendering import fit_font_to_box
from .bowling_common import BowlingPathOption, BowlingPin
from .layout import apply_games_layout_jitter_to_bbox
from .scene_style import GamePanelSceneStyle, draw_panel_scene_chrome, game_panel_scene_style_metadata


@dataclass(frozen=True)
class BowlingRenderParams:
    """Resolved render controls for one bowling lane scene."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    lane_width_px: int
    lane_height_px: int
    lane_border_width_px: int
    pin_radius_px: int
    ball_radius_px: int
    path_width_px: int
    label_font_size_px: int
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class BowlingTheme:
    """Resolved Bowling visual theme."""

    lane_fill_rgb: Tuple[int, int, int]
    lane_outline_rgb: Tuple[int, int, int]
    board_line_rgb: Tuple[int, int, int]
    approach_fill_rgb: Tuple[int, int, int]
    pin_fill_rgb: Tuple[int, int, int]
    pin_band_rgb: Tuple[int, int, int]
    pin_outline_rgb: Tuple[int, int, int]
    pin_text_rgb: Tuple[int, int, int]
    fallen_pin_rgb: Tuple[int, int, int]
    ball_fill_rgb: Tuple[int, int, int]
    ball_outline_rgb: Tuple[int, int, int]
    path_palette_rgb: Tuple[Tuple[int, int, int], ...]
    path_label_fill_rgb: Tuple[int, int, int]
    path_label_text_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedBowlingScene:
    """Rendered Bowling image plus trace-friendly geometry."""

    image: Image.Image
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def build_games_bowling_theme(*, style_variant: str) -> BowlingTheme:
    """Return one Bowling visual theme."""

    style = str(style_variant)
    if style == "cosmic":
        return BowlingTheme(
            lane_fill_rgb=(31, 27, 63),
            lane_outline_rgb=(143, 104, 255),
            board_line_rgb=(79, 83, 142),
            approach_fill_rgb=(18, 16, 37),
            pin_fill_rgb=(247, 247, 255),
            pin_band_rgb=(255, 83, 168),
            pin_outline_rgb=(204, 217, 255),
            pin_text_rgb=(34, 26, 61),
            fallen_pin_rgb=(116, 111, 150),
            ball_fill_rgb=(76, 220, 244),
            ball_outline_rgb=(227, 250, 255),
            path_palette_rgb=((255, 214, 83), (92, 238, 168), (255, 111, 173), (117, 156, 255), (255, 145, 88), (199, 112, 255)),
            path_label_fill_rgb=(30, 27, 57),
            path_label_text_rgb=(245, 247, 255),
        )
    if style == "paper":
        return BowlingTheme(
            lane_fill_rgb=(237, 222, 181),
            lane_outline_rgb=(94, 74, 52),
            board_line_rgb=(203, 181, 132),
            approach_fill_rgb=(224, 211, 176),
            pin_fill_rgb=(252, 249, 236),
            pin_band_rgb=(188, 57, 47),
            pin_outline_rgb=(88, 72, 56),
            pin_text_rgb=(42, 32, 24),
            fallen_pin_rgb=(180, 167, 138),
            ball_fill_rgb=(64, 103, 151),
            ball_outline_rgb=(35, 55, 82),
            path_palette_rgb=((193, 83, 64), (71, 130, 88), (62, 104, 163), (184, 132, 53), (133, 88, 154), (82, 132, 137)),
            path_label_fill_rgb=(245, 238, 214),
            path_label_text_rgb=(46, 36, 27),
        )
    if style == "tournament":
        return BowlingTheme(
            lane_fill_rgb=(198, 146, 83),
            lane_outline_rgb=(82, 47, 26),
            board_line_rgb=(160, 111, 61),
            approach_fill_rgb=(126, 78, 46),
            pin_fill_rgb=(255, 255, 250),
            pin_band_rgb=(205, 38, 45),
            pin_outline_rgb=(71, 56, 46),
            pin_text_rgb=(28, 26, 24),
            fallen_pin_rgb=(161, 139, 112),
            ball_fill_rgb=(46, 59, 73),
            ball_outline_rgb=(225, 231, 236),
            path_palette_rgb=((35, 92, 167), (201, 73, 55), (48, 139, 86), (229, 171, 61), (131, 80, 164), (40, 137, 150)),
            path_label_fill_rgb=(252, 250, 240),
            path_label_text_rgb=(32, 32, 30),
        )
    if style == "retro":
        return BowlingTheme(
            lane_fill_rgb=(231, 182, 95),
            lane_outline_rgb=(82, 48, 60),
            board_line_rgb=(189, 133, 73),
            approach_fill_rgb=(58, 65, 95),
            pin_fill_rgb=(255, 250, 234),
            pin_band_rgb=(228, 83, 73),
            pin_outline_rgb=(74, 58, 62),
            pin_text_rgb=(48, 38, 42),
            fallen_pin_rgb=(183, 153, 126),
            ball_fill_rgb=(67, 178, 194),
            ball_outline_rgb=(35, 79, 92),
            path_palette_rgb=((221, 76, 87), (80, 173, 126), (76, 128, 207), (238, 183, 78), (171, 92, 180), (59, 151, 156)),
            path_label_fill_rgb=(247, 236, 196),
            path_label_text_rgb=(56, 40, 48),
        )
    return BowlingTheme(
        lane_fill_rgb=(215, 167, 96),
        lane_outline_rgb=(94, 59, 31),
        board_line_rgb=(176, 125, 66),
        approach_fill_rgb=(118, 78, 45),
        pin_fill_rgb=(255, 255, 246),
        pin_band_rgb=(206, 43, 54),
        pin_outline_rgb=(70, 58, 46),
        pin_text_rgb=(30, 27, 24),
        fallen_pin_rgb=(171, 145, 115),
        ball_fill_rgb=(51, 78, 116),
        ball_outline_rgb=(226, 232, 239),
        path_palette_rgb=((48, 105, 179), (204, 73, 63), (59, 147, 97), (218, 159, 58), (136, 91, 174), (58, 143, 153)),
        path_label_fill_rgb=(250, 247, 235),
        path_label_text_rgb=(32, 30, 28),
    )


def _fit_text(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    text: str,
    fill: Tuple[int, int, int],
    max_size_px: int,
) -> None:
    """Draw centered text inside one bbox."""

    left, top, right, bottom = bbox
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(right - left)),
        max_height=max(1.0, float(bottom - top)),
        bold=True,
        min_size_px=7,
        max_size_px=int(max_size_px),
        fill_ratio=0.72,
    )
    text_bbox = draw.textbbox((0, 0), str(text), font=font)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    draw.text(
        (
            float(left + (0.5 * (float(right - left) - text_w)) - float(text_bbox[0])),
            float(top + (0.5 * (float(bottom - top) - text_h)) - float(text_bbox[1])),
        ),
        str(text),
        fill=tuple(int(v) for v in fill),
        font=font,
    )


def _pin_positions(
    lane_bbox: Tuple[float, float, float, float],
    *,
    pins: Tuple[BowlingPin, ...] = tuple(),
) -> Dict[int, Tuple[float, float]]:
    """Return canonical 10-pin rack centers in lane coordinates."""

    left, top, right, bottom = lane_bbox
    explicit: Dict[int, Tuple[float, float]] = {}
    for pin in pins:
        if pin.x_norm is None or pin.y_norm is None:
            continue
        explicit[int(pin.rack_index)] = (
            float(left + (float(pin.x_norm) * (right - left))),
            float(top + (float(pin.y_norm) * (bottom - top))),
        )
    if explicit:
        return explicit

    cx = float((left + right) / 2.0)
    rack_top = float(top + 94.0)
    spacing_x = float((right - left) * 0.062)
    spacing_y = float((bottom - top) * 0.058)
    positions: Dict[int, Tuple[float, float]] = {}
    index = 0
    for row, count in enumerate((4, 3, 2, 1)):
        y = float(rack_top + (row * spacing_y))
        start_x = float(cx - ((count - 1) * spacing_x / 2.0))
        for col in range(count):
            positions[index] = (float(start_x + (col * spacing_x)), float(y))
            index += 1
    return positions


def _draw_pin(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius_px: float,
    label: str,
    standing: bool,
    theme: BowlingTheme,
    label_font_size_px: int,
) -> Tuple[float, float, float, float]:
    """Draw one standing or fallen pin and return its bbox."""

    cx, cy = float(center[0]), float(center[1])
    r = float(radius_px)
    bbox = (round(cx - r, 3), round(cy - (1.35 * r), 3), round(cx + r, 3), round(cy + (1.35 * r), 3))
    if bool(standing):
        h = float(bbox[3] - bbox[1])
        body = [
            (cx - (0.34 * r), bbox[1] + (0.08 * h)),
            (cx + (0.34 * r), bbox[1] + (0.08 * h)),
            (cx + (0.48 * r), bbox[1] + (0.25 * h)),
            (cx + (0.80 * r), bbox[1] + (0.48 * h)),
            (cx + (0.92 * r), bbox[1] + (0.77 * h)),
            (cx + (0.60 * r), bbox[3] - (0.02 * h)),
            (cx - (0.60 * r), bbox[3] - (0.02 * h)),
            (cx - (0.92 * r), bbox[1] + (0.77 * h)),
            (cx - (0.80 * r), bbox[1] + (0.48 * h)),
            (cx - (0.48 * r), bbox[1] + (0.25 * h)),
        ]
        draw.polygon(body, fill=tuple(int(v) for v in theme.pin_fill_rgb), outline=tuple(int(v) for v in theme.pin_outline_rgb))
        draw.line(body + [body[0]], fill=tuple(int(v) for v in theme.pin_outline_rgb), width=2, joint="curve")
        neck = (cx - (0.42 * r), bbox[1] + (0.02 * h), cx + (0.42 * r), bbox[1] + (0.32 * h))
        draw.ellipse(neck, fill=tuple(int(v) for v in theme.pin_fill_rgb), outline=tuple(int(v) for v in theme.pin_outline_rgb), width=2)
        base_shadow = (cx - (0.62 * r), bbox[3] - (0.16 * h), cx + (0.62 * r), bbox[3] + (0.01 * h))
        draw.arc(base_shadow, start=0, end=180, fill=tuple(int(v) for v in theme.pin_outline_rgb), width=2)
        band_y = bbox[1] + (0.30 * h)
        band = (cx - (0.58 * r), band_y, cx + (0.58 * r), band_y + (0.23 * r))
        draw.rounded_rectangle(band, radius=max(2, int(r * 0.14)), fill=tuple(int(v) for v in theme.pin_band_rgb))
        text_box = (bbox[0] + (0.28 * r), cy + (0.02 * r), bbox[2] - (0.28 * r), cy + (0.82 * r))
        _fit_text(draw, bbox=text_box, text=str(label), fill=theme.pin_text_rgb, max_size_px=int(label_font_size_px))
    else:
        fallen = (bbox[0], cy - (0.42 * r), bbox[2], cy + (0.42 * r))
        draw.rounded_rectangle(
            fallen,
            radius=max(4, int(r * 0.30)),
            fill=tuple(int(v) for v in theme.fallen_pin_rgb) + (170,),
            outline=tuple(int(v) for v in theme.pin_outline_rgb) + (160,),
            width=1,
        )
    return bbox


def _draw_ball(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius_px: float,
    theme: BowlingTheme,
) -> Tuple[float, float, float, float]:
    """Draw the bowling ball and return its bbox."""

    cx, cy = float(center[0]), float(center[1])
    r = float(radius_px)
    bbox = (round(cx - r, 3), round(cy - r, 3), round(cx + r, 3), round(cy + r, 3))
    draw.ellipse(bbox, fill=tuple(int(v) for v in theme.ball_fill_rgb), outline=tuple(int(v) for v in theme.ball_outline_rgb), width=3)
    for dx, dy, scale in ((-0.30, -0.34, 0.13), (0.05, -0.18, 0.11), (-0.04, 0.14, 0.10)):
        hole = (cx + (dx * r), cy + (dy * r))
        hr = float(r * scale)
        draw.ellipse((hole[0] - hr, hole[1] - hr, hole[0] + hr, hole[1] + hr), fill=(15, 18, 24, 180))
    return bbox


def _lane_point(lane_bbox: Tuple[float, float, float, float], *, x_norm: float, y_norm: float) -> Tuple[float, float]:
    """Map normalized lane coordinates to pixels."""

    left, top, right, bottom = lane_bbox
    return (
        float(left + (float(x_norm) * (right - left))),
        float(top + (float(y_norm) * (bottom - top))),
    )


def _bbox_for_path(
    *,
    start: Tuple[float, float],
    end: Tuple[float, float],
    pad: float,
) -> Tuple[float, float, float, float]:
    """Return a coarse bbox around a rendered path."""

    return (
        round(min(float(start[0]), float(end[0])) - float(pad), 3),
        round(min(float(start[1]), float(end[1])) - float(pad), 3),
        round(max(float(start[0]), float(end[0])) + float(pad), 3),
        round(max(float(start[1]), float(end[1])) + float(pad), 3),
    )


def render_bowling_scene(
    *,
    pins: Tuple[BowlingPin, ...],
    path_options: Tuple[BowlingPathOption, ...],
    query_id: str,
    ball_x_norm: float,
    target_pin_id: str | None,
    target_path_id: str | None,
    path_visible_fraction: float | None = None,
    background: Image.Image,
    style_variant: str,
    params: BowlingRenderParams,
    panel_style: GamePanelSceneStyle | None = None,
) -> RenderedBowlingScene:
    """Render one bowling lane scene."""

    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme = build_games_bowling_theme(style_variant=str(style_variant))

    lane_left = float((int(params.canvas_width) - int(params.lane_width_px)) / 2.0)
    lane_top = float((int(params.canvas_height) - int(params.lane_height_px)) / 2.0)
    lane_bbox = (
        lane_left,
        lane_top,
        lane_left + float(params.lane_width_px),
        lane_top + float(params.lane_height_px),
    )
    if isinstance(params.layout_jitter_meta, Mapping):
        lane_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
            bbox_px=lane_bbox,
            canvas_width=int(params.canvas_width),
            canvas_height=int(params.canvas_height),
            jitter=params.layout_jitter_meta,
        )
    else:
        layout_jitter = {}

    left, top, right, bottom = lane_bbox
    panel_bbox: Tuple[int, int, int, int] | None = None
    if panel_style is not None:
        panel_pad_x = max(18, int(round(float(params.panel_margin_px) * 0.60)))
        panel_pad_y = max(18, int(round(float(params.panel_margin_px) * 0.48)))
        panel_bbox = (
            max(4, int(round(left)) - panel_pad_x),
            max(4, int(round(top)) - panel_pad_y),
            min(int(params.canvas_width) - 4, int(round(right)) + panel_pad_x),
            min(int(params.canvas_height) - 4, int(round(bottom)) + panel_pad_y),
        )
        draw_panel_scene_chrome(
            draw,
            bbox=panel_bbox,
            style=panel_style,
            radius=34,
            border_width=max(2, int(round(float(params.lane_border_width_px) * 0.45))),
        )

    draw.rounded_rectangle(
        lane_bbox,
        radius=28,
        fill=tuple(int(v) for v in theme.lane_fill_rgb) + (244,),
        outline=tuple(int(v) for v in theme.lane_outline_rgb) + (255,),
        width=int(params.lane_border_width_px),
    )
    approach = (left + 34.0, bottom - 112.0, right - 34.0, bottom - 28.0)
    draw.rounded_rectangle(approach, radius=20, fill=tuple(int(v) for v in theme.approach_fill_rgb) + (116,))
    for index in range(1, 9):
        x = float(left + (index * (right - left) / 9.0))
        draw.line((x, top + 26.0, x, bottom - 24.0), fill=tuple(int(v) for v in theme.board_line_rgb) + (90,), width=1)

    pin_centers = _pin_positions(lane_bbox, pins=pins)
    entity_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    pin_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    path_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    scene_entities: list[Dict[str, Any]] = []
    ball_center = _lane_point(lane_bbox, x_norm=float(ball_x_norm), y_norm=0.875)

    if str(query_id) == "first_pin_hit_label":
        if target_pin_id is None:
            raise ValueError("first_pin_hit_label render requires target_pin_id")
        target_pin = next(pin for pin in pins if str(pin.pin_id) == str(target_pin_id))
        target_center = pin_centers[int(target_pin.rack_index)]
        visible_end = (
            float(ball_center[0] + (0.62 * (target_center[0] - ball_center[0]))),
            float(ball_center[1] + (0.62 * (target_center[1] - ball_center[1]))),
        )
        draw_dashed_line(
            draw,
            start=ball_center,
            end=visible_end,
            fill=tuple(int(v) for v in theme.path_palette_rgb[0]),
            width=int(params.path_width_px),
            dash_px=18,
            gap_px=10,
        )
        draw_arrow(
            draw,
            start=(ball_center[0] + (0.42 * (visible_end[0] - ball_center[0])), ball_center[1] + (0.42 * (visible_end[1] - ball_center[1]))),
            end=visible_end,
            fill=tuple(int(v) for v in theme.path_palette_rgb[0]),
            width=int(params.path_width_px),
            head_length_px=22,
            head_width_px=18,
        )
        rendered_paths = {
            "shown_path": {
                "start": [round(float(ball_center[0]), 3), round(float(ball_center[1]), 3)],
                "end": [round(float(target_center[0]), 3), round(float(target_center[1]), 3)],
                "visible_end": [round(float(visible_end[0]), 3), round(float(visible_end[1]), 3)],
            }
        }
    else:
        rendered_paths = {}
        for option in path_options:
            color = theme.path_palette_rgb[int(option.color_index) % len(theme.path_palette_rgb)]
            aim_end = _lane_point(lane_bbox, x_norm=float(option.aim_x_norm), y_norm=0.09)
            visible_fraction = max(0.34, min(0.68, float(path_visible_fraction if path_visible_fraction is not None else 0.50)))
            visible_end = (
                float(ball_center[0] + (visible_fraction * (aim_end[0] - ball_center[0]))),
                float(ball_center[1] + (visible_fraction * (aim_end[1] - ball_center[1]))),
            )
            line_width = int(params.path_width_px) + (2 if str(option.path_id) == str(target_path_id) else 0)
            draw_dashed_line(draw, start=ball_center, end=visible_end, fill=tuple(int(v) for v in color), width=line_width, dash_px=16, gap_px=9)
            label_center = _lane_point(lane_bbox, x_norm=float(option.aim_x_norm), y_norm=0.945)
            label_r = 18.0
            label_bbox = (
                round(label_center[0] - label_r, 3),
                round(label_center[1] - label_r, 3),
                round(label_center[0] + label_r, 3),
                round(label_center[1] + label_r, 3),
            )
            draw.ellipse(label_bbox, fill=tuple(int(v) for v in theme.path_label_fill_rgb), outline=tuple(int(v) for v in color), width=3)
            _fit_text(draw, bbox=label_bbox, text=str(option.label), fill=theme.path_label_text_rgb, max_size_px=int(params.label_font_size_px))
            path_bbox = _bbox_for_path(start=ball_center, end=aim_end, pad=20.0)
            path_bboxes[str(option.path_id)] = path_bbox
            entity_bboxes[str(option.path_id)] = label_bbox
            scene_entities.append(
                {
                    "entity_id": str(option.path_id),
                    "entity_type": "bowling_path_option",
                    "label": str(option.label),
                    "aim_x_norm": float(option.aim_x_norm),
                    "bbox_px": list(label_bbox),
                    "path_bbox_px": list(path_bbox),
                }
            )
            rendered_paths[str(option.path_id)] = {
                "start": [round(float(ball_center[0]), 3), round(float(ball_center[1]), 3)],
                "end": [round(float(aim_end[0]), 3), round(float(aim_end[1]), 3)],
                "visible_end": [round(float(visible_end[0]), 3), round(float(visible_end[1]), 3)],
                "visible_fraction": round(float(visible_fraction), 3),
            }

    for pin in pins:
        center = pin_centers[int(pin.rack_index)]
        bbox = _draw_pin(
            draw,
            center=center,
            radius_px=float(params.pin_radius_px),
            label=str(pin.label),
            standing=bool(pin.standing),
            theme=theme,
            label_font_size_px=int(params.label_font_size_px),
        )
        pin_bboxes[str(pin.pin_id)] = bbox
        entity_bboxes[str(pin.pin_id)] = bbox
        scene_entities.append(
            {
                "entity_id": str(pin.pin_id),
                "entity_type": "bowling_pin",
                "label": str(pin.label),
                "rack_index": int(pin.rack_index),
                "row": int(pin.row),
                "col": int(pin.col),
                "standing": bool(pin.standing),
                "bbox_px": list(bbox),
            }
        )

    ball_bbox = _draw_ball(draw, center=ball_center, radius_px=float(params.ball_radius_px), theme=theme)
    entity_bboxes["ball"] = ball_bbox
    scene_entities.append({"entity_id": "ball", "entity_type": "bowling_ball", "bbox_px": list(ball_bbox)})

    render_map = {
        "lane_bbox_px": [round(float(v), 3) for v in lane_bbox],
        "panel_bbox_px": None if panel_bbox is None else [int(value) for value in panel_bbox],
        "pin_centers_px": {
            str(pin.pin_id): [
                round(float(pin_centers[int(pin.rack_index)][0]), 3),
                round(float(pin_centers[int(pin.rack_index)][1]), 3),
            ]
            for pin in pins
        },
        "pin_bboxes_px": {str(key): list(value) for key, value in pin_bboxes.items()},
        "path_bboxes_px": {str(key): list(value) for key, value in path_bboxes.items()},
        "entity_bboxes_px": {str(key): list(value) for key, value in entity_bboxes.items()},
        "ball_bbox_px": list(ball_bbox),
        "ball_center_px": [round(float(ball_center[0]), 3), round(float(ball_center[1]), 3)],
        "motion_paths_px": rendered_paths,
        "layout_jitter": dict(layout_jitter),
        "path_visible_fraction": None if path_visible_fraction is None else round(float(path_visible_fraction), 3),
        "style_variant": str(style_variant),
        "panel_scene_style": None if panel_style is None else game_panel_scene_style_metadata(panel_style),
    }
    return RenderedBowlingScene(
        image=image.convert("RGB"),
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "BowlingRenderParams",
    "RenderedBowlingScene",
    "build_games_bowling_theme",
    "render_bowling_scene",
]
