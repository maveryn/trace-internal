"""Reusable analog-clock rendering helpers for temporal tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import draw_text_centered, load_font
from .style import TemporalClockTheme
from .time_format import split_clock_total_minutes


SUPPORTED_TEMPORAL_CLOCK_SCENE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "minimal",
    "outline",
)


@dataclass(frozen=True)
class ClockRenderParams:
    """Concrete analog-clock render parameters resolved from config."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    face_radius_px: int
    bezel_width_px: int
    numeral_font_size_px: int
    major_tick_length_px: int
    minor_tick_length_px: int
    major_tick_width_px: int
    minor_tick_width_px: int
    minor_tick_dot_radius_px: int
    hour_hand_width_px: int
    minute_hand_width_px: int
    hand_bbox_padding_px: int
    center_dot_radius_px: int
    inner_ring_inset_px: int
    inner_ring_width_px: int


def resolve_clock_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    fallback_values: Mapping[str, Any],
) -> ClockRenderParams:
    """Resolve concrete clock render parameters from config + task-local fallbacks."""

    def _render_value(key: str, fallback: Any) -> Any:
        return params.get(key, render_defaults.get(key, fallback))

    return ClockRenderParams(
        canvas_width=int(_render_value("canvas_width", fallback_values["canvas_width"])),
        canvas_height=int(_render_value("canvas_height", fallback_values["canvas_height"])),
        outer_margin_px=int(_render_value("outer_margin_px", fallback_values["outer_margin_px"])),
        face_radius_px=int(_render_value("face_radius_px", fallback_values["face_radius_px"])),
        bezel_width_px=int(_render_value("bezel_width_px", fallback_values["bezel_width_px"])),
        numeral_font_size_px=int(_render_value("numeral_font_size_px", fallback_values["numeral_font_size_px"])),
        major_tick_length_px=int(_render_value("major_tick_length_px", fallback_values["major_tick_length_px"])),
        minor_tick_length_px=int(_render_value("minor_tick_length_px", fallback_values["minor_tick_length_px"])),
        major_tick_width_px=int(_render_value("major_tick_width_px", fallback_values["major_tick_width_px"])),
        minor_tick_width_px=int(_render_value("minor_tick_width_px", fallback_values["minor_tick_width_px"])),
        minor_tick_dot_radius_px=int(_render_value("minor_tick_dot_radius_px", fallback_values["minor_tick_dot_radius_px"])),
        hour_hand_width_px=int(_render_value("hour_hand_width_px", fallback_values["hour_hand_width_px"])),
        minute_hand_width_px=int(_render_value("minute_hand_width_px", fallback_values["minute_hand_width_px"])),
        hand_bbox_padding_px=int(_render_value("hand_bbox_padding_px", fallback_values["hand_bbox_padding_px"])),
        center_dot_radius_px=int(_render_value("center_dot_radius_px", fallback_values["center_dot_radius_px"])),
        inner_ring_inset_px=int(_render_value("inner_ring_inset_px", fallback_values["inner_ring_inset_px"])),
        inner_ring_width_px=int(_render_value("inner_ring_width_px", fallback_values["inner_ring_width_px"])),
    )


@dataclass(frozen=True)
class RenderedClockGeometry:
    """Rendered analog-clock geometry plus scene entities."""

    face_bbox_px: Tuple[float, float, float, float]
    center_px: Tuple[float, float]
    hour_hand_bbox_px: Tuple[float, float, float, float]
    minute_hand_bbox_px: Tuple[float, float, float, float]
    hour_hand_tip_px: Tuple[float, float]
    minute_hand_tip_px: Tuple[float, float]
    entities: List[Dict[str, Any]]


@dataclass(frozen=True)
class RenderedClockScene:
    """Rendered analog-clock image plus witness geometry."""

    image: Image.Image
    scene_bbox_px: Tuple[float, float, float, float]
    face_bbox_px: Tuple[float, float, float, float]
    center_px: Tuple[float, float]
    hour_hand_bbox_px: Tuple[float, float, float, float]
    minute_hand_bbox_px: Tuple[float, float, float, float]
    hour_hand_tip_px: Tuple[float, float]
    minute_hand_tip_px: Tuple[float, float]
    entities: List[Dict[str, Any]]


def _clock_angles(total_minutes: int) -> Tuple[float, float]:
    """Return `(hour_angle_deg, minute_angle_deg)` in image coordinates."""

    hour_12, minute = split_clock_total_minutes(int(total_minutes))
    hour_progress = (float(hour_12 % 12) + (float(minute) / 60.0)) / 12.0
    minute_progress = float(minute) / 60.0
    hour_angle = (360.0 * hour_progress) - 90.0
    minute_angle = (360.0 * minute_progress) - 90.0
    return float(hour_angle), float(minute_angle)


def _endpoint(center: Tuple[float, float], radius: float, angle_deg: float) -> Tuple[float, float]:
    """Return one endpoint on the analog-clock circle."""

    rad = math.radians(float(angle_deg))
    return (
        float(center[0] + (float(radius) * math.cos(rad))),
        float(center[1] + (float(radius) * math.sin(rad))),
    )


def _segment_bbox(
    start: Tuple[float, float],
    end: Tuple[float, float],
    *,
    width_px: float,
    padding_px: float,
) -> Tuple[float, float, float, float]:
    """Return a padded axis-aligned bbox for one rendered hand segment."""

    pad = float(max(0.0, float(padding_px)) + (0.5 * float(width_px)))
    return (
        float(min(start[0], end[0]) - pad),
        float(min(start[1], end[1]) - pad),
        float(max(start[0], end[0]) + pad),
        float(max(start[1], end[1]) + pad),
    )


def _variant_style(scene_variant: str, params: ClockRenderParams, theme: TemporalClockTheme) -> Dict[str, Any]:
    """Return visual toggles for one clock scene variant."""

    if str(scene_variant) == "minimal":
        return {
            "show_minor_ticks": False,
            "face_fill_rgb": tuple(int(v) for v in theme.face_fill_rgb),
            "face_outline_rgb": tuple(int(v) for v in theme.face_outline_rgb),
            "tick_color_rgb": tuple(int(v) for v in theme.tick_color_rgb),
            "numeral_color_rgb": tuple(int(v) for v in theme.numeral_color_rgb),
            "inner_ring_rgb": None,
            "minor_tick_mode": str(theme.minor_tick_mode),
            "bezel_width_px": max(2, int(round(0.7 * float(params.bezel_width_px)))),
        }
    if str(scene_variant) == "outline":
        return {
            "show_minor_ticks": False,
            "face_fill_rgb": None,
            "face_outline_rgb": tuple(int(v) for v in theme.face_outline_rgb),
            "tick_color_rgb": tuple(int(v) for v in theme.tick_color_rgb),
            "numeral_color_rgb": tuple(int(v) for v in theme.numeral_color_rgb),
            "inner_ring_rgb": tuple(int(v) for v in theme.inner_ring_rgb) if theme.inner_ring_rgb is not None else None,
            "minor_tick_mode": str(theme.minor_tick_mode),
            "bezel_width_px": max(3, int(round(0.85 * float(params.bezel_width_px)))),
        }
    return {
        "show_minor_ticks": True,
        "face_fill_rgb": tuple(int(v) for v in theme.face_fill_rgb),
        "face_outline_rgb": tuple(int(v) for v in theme.face_outline_rgb),
        "tick_color_rgb": tuple(int(v) for v in theme.tick_color_rgb),
        "numeral_color_rgb": tuple(int(v) for v in theme.numeral_color_rgb),
        "inner_ring_rgb": tuple(int(v) for v in theme.inner_ring_rgb) if theme.inner_ring_rgb is not None else None,
        "minor_tick_mode": str(theme.minor_tick_mode),
        "bezel_width_px": int(params.bezel_width_px),
    }


def draw_clock_geometry(
    image: Image.Image,
    *,
    center_px: Tuple[float, float],
    face_radius_px: float,
    scene_variant: str,
    shown_total_minutes: int,
    render_params: ClockRenderParams,
    visual_theme: TemporalClockTheme,
    entity_prefix: str = "",
    extra_face_attrs: Dict[str, Any] | None = None,
) -> RenderedClockGeometry:
    """Draw one analog clock into an existing image and return its geometry."""

    draw = ImageDraw.Draw(image)

    center = (float(center_px[0]), float(center_px[1]))
    face_radius = float(face_radius_px)
    face_bbox = (
        float(center[0] - face_radius),
        float(center[1] - face_radius),
        float(center[0] + face_radius),
        float(center[1] + face_radius),
    )
    style = _variant_style(str(scene_variant), render_params, visual_theme)

    if style["face_fill_rgb"] is not None:
        draw.ellipse(
            face_bbox,
            fill=tuple(int(v) for v in style["face_fill_rgb"]),
            outline=tuple(int(v) for v in style["face_outline_rgb"]),
            width=int(style["bezel_width_px"]),
        )
    else:
        draw.ellipse(
            face_bbox,
            outline=tuple(int(v) for v in style["face_outline_rgb"]),
            width=int(style["bezel_width_px"]),
        )
    if style["inner_ring_rgb"] is not None:
        inner_inset = float(max(6, int(render_params.inner_ring_inset_px)))
        inner_bbox = (
            float(face_bbox[0] + inner_inset),
            float(face_bbox[1] + inner_inset),
            float(face_bbox[2] - inner_inset),
            float(face_bbox[3] - inner_inset),
        )
        draw.ellipse(
            inner_bbox,
            outline=tuple(int(v) for v in style["inner_ring_rgb"]),
            width=int(render_params.inner_ring_width_px),
        )

    major_tick_inner = float(face_radius - render_params.major_tick_length_px)
    minor_tick_inner = float(face_radius - render_params.minor_tick_length_px)
    numeral_radius = float(face_radius - max(36, int(round(0.18 * float(face_radius)))))
    numeral_font = load_font(int(render_params.numeral_font_size_px), bold=True)

    for tick_index in range(60):
        angle_deg = (6.0 * float(tick_index)) - 90.0
        outer = _endpoint(center, face_radius - 4.0, angle_deg)
        is_major = (tick_index % 5) == 0
        if (not is_major) and (not bool(style["show_minor_ticks"])):
            continue
        if (not is_major) and str(style["minor_tick_mode"]) == "dot":
            dot_center = _endpoint(center, face_radius - 8.0, angle_deg)
            dot_radius = float(max(1, int(render_params.minor_tick_dot_radius_px)))
            draw.ellipse(
                (
                    float(dot_center[0] - dot_radius),
                    float(dot_center[1] - dot_radius),
                    float(dot_center[0] + dot_radius),
                    float(dot_center[1] + dot_radius),
                ),
                fill=tuple(int(v) for v in style["tick_color_rgb"]),
            )
            continue
        inner_radius = major_tick_inner if is_major else minor_tick_inner
        inner = _endpoint(center, inner_radius, angle_deg)
        draw.line(
            [inner, outer],
            fill=tuple(int(v) for v in style["tick_color_rgb"]),
            width=int(render_params.major_tick_width_px if is_major else render_params.minor_tick_width_px),
        )

    for numeral in range(1, 13):
        angle_deg = (30.0 * float(numeral)) - 90.0
        numeral_center = _endpoint(center, numeral_radius, angle_deg)
        draw_text_centered(
            draw,
            text=str(int(numeral)),
            center=numeral_center,
            font=numeral_font,
            fill=tuple(int(v) for v in style["numeral_color_rgb"]),
        )

    hour_angle, minute_angle = _clock_angles(int(shown_total_minutes))
    hour_tip = _endpoint(center, 0.55 * face_radius, hour_angle)
    minute_tip = _endpoint(center, 0.82 * face_radius, minute_angle)

    draw.line(
        [center, hour_tip],
        fill=tuple(int(v) for v in visual_theme.hour_hand_color_rgb),
        width=int(render_params.hour_hand_width_px),
    )
    draw.line(
        [center, minute_tip],
        fill=tuple(int(v) for v in visual_theme.minute_hand_color_rgb),
        width=int(render_params.minute_hand_width_px),
    )
    draw.ellipse(
        (
            float(center[0] - render_params.center_dot_radius_px),
            float(center[1] - render_params.center_dot_radius_px),
            float(center[0] + render_params.center_dot_radius_px),
            float(center[1] + render_params.center_dot_radius_px),
        ),
        fill=tuple(int(v) for v in visual_theme.center_dot_color_rgb),
    )

    hour_hand_bbox = _segment_bbox(
        center,
        hour_tip,
        width_px=float(render_params.hour_hand_width_px),
        padding_px=float(render_params.hand_bbox_padding_px),
    )
    minute_hand_bbox = _segment_bbox(
        center,
        minute_tip,
        width_px=float(render_params.minute_hand_width_px),
        padding_px=float(render_params.hand_bbox_padding_px),
    )

    prefix = str(entity_prefix).strip()
    if prefix:
        prefix = f"{prefix}_"
    face_attrs: Dict[str, Any] = {
        "scene_variant": str(scene_variant),
        "shown_total_minutes": int(shown_total_minutes),
        "accent_color_name": str(visual_theme.accent_color_name),
        "style_variant": str(visual_theme.style_variant),
    }
    if extra_face_attrs:
        face_attrs.update({str(key): value for key, value in extra_face_attrs.items()})

    entities: List[Dict[str, Any]] = [
        {
            "entity_id": f"{prefix}clock_face",
            "entity_kind": "clock_face",
            "bbox_px": [float(value) for value in face_bbox],
            "attrs": dict(face_attrs),
        },
        {
            "entity_id": f"{prefix}hour_hand",
            "entity_kind": "clock_hand",
            "bbox_px": [float(value) for value in hour_hand_bbox],
            "attrs": {
                "hand_kind": "hour",
                "tip_px": [float(hour_tip[0]), float(hour_tip[1])],
                "center_px": [float(center[0]), float(center[1])],
                "angle_deg": float(hour_angle),
            },
        },
        {
            "entity_id": f"{prefix}minute_hand",
            "entity_kind": "clock_hand",
            "bbox_px": [float(value) for value in minute_hand_bbox],
            "attrs": {
                "hand_kind": "minute",
                "tip_px": [float(minute_tip[0]), float(minute_tip[1])],
                "center_px": [float(center[0]), float(center[1])],
                "angle_deg": float(minute_angle),
            },
        },
    ]

    return RenderedClockGeometry(
        face_bbox_px=face_bbox,
        center_px=(float(center[0]), float(center[1])),
        hour_hand_bbox_px=hour_hand_bbox,
        minute_hand_bbox_px=minute_hand_bbox,
        hour_hand_tip_px=(float(hour_tip[0]), float(hour_tip[1])),
        minute_hand_tip_px=(float(minute_tip[0]), float(minute_tip[1])),
        entities=entities,
    )


def render_clock_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    shown_total_minutes: int,
    render_params: ClockRenderParams,
    visual_theme: TemporalClockTheme,
) -> RenderedClockScene:
    """Render one analog clock and return witness geometry for both hands."""

    image = background.copy().convert("RGB")
    geometry = draw_clock_geometry(
        image,
        center_px=(0.5 * float(render_params.canvas_width), 0.5 * float(render_params.canvas_height)),
        face_radius_px=float(render_params.face_radius_px),
        scene_variant=str(scene_variant),
        shown_total_minutes=int(shown_total_minutes),
        render_params=render_params,
        visual_theme=visual_theme,
    )
    return RenderedClockScene(
        image=image,
        scene_bbox_px=tuple(float(value) for value in geometry.face_bbox_px),
        face_bbox_px=tuple(float(value) for value in geometry.face_bbox_px),
        center_px=tuple(float(value) for value in geometry.center_px),
        hour_hand_bbox_px=tuple(float(value) for value in geometry.hour_hand_bbox_px),
        minute_hand_bbox_px=tuple(float(value) for value in geometry.minute_hand_bbox_px),
        hour_hand_tip_px=tuple(float(value) for value in geometry.hour_hand_tip_px),
        minute_hand_tip_px=tuple(float(value) for value in geometry.minute_hand_tip_px),
        entities=[dict(entity) for entity in geometry.entities],
    )


__all__ = [
    "ClockRenderParams",
    "RenderedClockGeometry",
    "RenderedClockScene",
    "SUPPORTED_TEMPORAL_CLOCK_SCENE_VARIANTS",
    "draw_clock_geometry",
    "render_clock_scene",
    "resolve_clock_render_params",
]
