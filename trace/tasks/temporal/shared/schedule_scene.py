"""Shared single-day schedule rendering helpers for temporal tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from .style import TemporalScheduleTheme
from .time_format import format_day_time_hhmm


SUPPORTED_TEMPORAL_SCHEDULE_SCENE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "minimal",
    "outline",
)


@dataclass(frozen=True)
class ScheduleRenderParams:
    """Resolved rendering parameters for a single-day planner scene."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    header_height_px: int
    panel_corner_radius_px: int
    panel_outline_width_px: int
    time_axis_width_px: int
    planner_top_gap_px: int
    planner_bottom_gap_px: int
    lane_gap_px: int
    grid_line_width_px: int
    minor_grid_line_width_px: int
    hour_label_font_size_px: int
    title_font_size_px: int
    event_label_font_size_px: int
    event_corner_radius_px: int
    event_text_padding_px: int


@dataclass(frozen=True)
class ScheduledEventSpec:
    """One rendered schedule event block."""

    event_id: str
    label: str
    start_total_minutes: int
    end_total_minutes: int
    lane_index: int
    is_reference: bool = False

    @property
    def duration_minutes(self) -> int:
        """Return the event duration in minutes."""

        return int(self.end_total_minutes) - int(self.start_total_minutes)


@dataclass(frozen=True)
class RenderedScheduleScene:
    """Rendered day-planner geometry and event-block projections."""

    title_text: str
    scene_bbox_px: Tuple[float, float, float, float]
    panel_bbox_px: Tuple[float, float, float, float]
    event_bboxes_by_id: Dict[str, Tuple[float, float, float, float]]
    entities: Tuple[Dict[str, Any], ...]


def _require_int(value: Any, *, name: str) -> int:
    """Convert one render parameter to ``int`` and fail loudly when missing."""

    if value is None:
        raise ValueError(f"missing required schedule render parameter: {name}")
    return int(value)


def resolve_schedule_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    fallback_values: Mapping[str, Any],
) -> ScheduleRenderParams:
    """Resolve active single-day planner render parameters."""

    resolved: Dict[str, int] = {}
    allowed_keys = {
        "canvas_width",
        "canvas_height",
        "outer_margin_px",
        "header_height_px",
        "panel_corner_radius_px",
        "panel_outline_width_px",
        "time_axis_width_px",
        "planner_top_gap_px",
        "planner_bottom_gap_px",
        "lane_gap_px",
        "grid_line_width_px",
        "minor_grid_line_width_px",
        "hour_label_font_size_px",
        "title_font_size_px",
        "event_label_font_size_px",
        "event_corner_radius_px",
        "event_text_padding_px",
    }
    for key, fallback in fallback_values.items():
        if key not in allowed_keys:
            continue
        resolved[str(key)] = _require_int(params.get(str(key), render_defaults.get(str(key), fallback)), name=str(key))
    return ScheduleRenderParams(**resolved)


def _rounded(draw: ImageDraw.ImageDraw, bbox: Sequence[float], *, radius: int, fill=None, outline=None, width: int = 1) -> None:
    """Draw one rounded rectangle with stable coordinate coercion."""

    draw.rounded_rectangle([float(value) for value in bbox], radius=int(radius), fill=fill, outline=outline, width=int(width))


def render_day_schedule_scene(
    image: Image.Image,
    *,
    title_text: str,
    day_label_text: str,
    start_total_minutes: int,
    end_total_minutes: int,
    slot_minutes: int,
    lane_count: int,
    events: Sequence[ScheduledEventSpec],
    scene_variant: str,
    render_params: ScheduleRenderParams,
    visual_theme: TemporalScheduleTheme,
) -> RenderedScheduleScene:
    """Render one single-day planner and return projected event-block geometry."""

    if int(end_total_minutes) <= int(start_total_minutes):
        raise ValueError("day planner end_total_minutes must be greater than start_total_minutes")
    if int(slot_minutes) <= 0:
        raise ValueError("slot_minutes must be positive for schedule rendering")
    if int(lane_count) <= 0:
        raise ValueError("lane_count must be positive for schedule rendering")

    draw = ImageDraw.Draw(image)
    canvas_width = int(render_params.canvas_width)
    canvas_height = int(render_params.canvas_height)
    outer_margin = int(render_params.outer_margin_px)
    header_height = int(render_params.header_height_px)
    panel_bbox = (
        float(outer_margin),
        float(outer_margin),
        float(canvas_width - outer_margin),
        float(canvas_height - outer_margin),
    )
    scene_bbox = panel_bbox
    content_top = float(panel_bbox[1] + header_height)
    planner_top = float(content_top + int(render_params.planner_top_gap_px))
    planner_bottom = float(panel_bbox[3] - int(render_params.planner_bottom_gap_px))
    time_axis_width = int(render_params.time_axis_width_px)
    planner_left = float(panel_bbox[0] + time_axis_width)
    planner_right = float(panel_bbox[2] - outer_margin)

    if str(scene_variant) == "outline":
        panel_fill = (255, 255, 255)
    else:
        panel_fill = visual_theme.panel_fill_rgb
    _rounded(
        draw,
        panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=panel_fill,
        outline=visual_theme.panel_outline_rgb,
        width=int(render_params.panel_outline_width_px),
    )

    header_bbox = (panel_bbox[0], panel_bbox[1], panel_bbox[2], content_top)
    if str(scene_variant) != "minimal":
        if str(visual_theme.header_kind) == "line":
            draw.line(
                [(header_bbox[0], header_bbox[3]), (header_bbox[2], header_bbox[3])],
                fill=visual_theme.header_text_rgb,
                width=int(render_params.grid_line_width_px),
            )
        else:
            _rounded(
                draw,
                header_bbox,
                radius=int(render_params.panel_corner_radius_px),
                fill=visual_theme.header_fill_rgb,
                outline=None,
                width=1,
            )
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    draw_text_centered(
        draw,
        text=str(title_text),
        center=((header_bbox[0] + header_bbox[2]) * 0.5, float(header_bbox[1] + (0.42 * header_height))),
        font=title_font,
        fill=visual_theme.header_text_rgb,
    )
    day_font = load_font(max(12, int(render_params.title_font_size_px * 0.55)), bold=False)
    draw_text_centered(
        draw,
        text=str(day_label_text),
        center=((header_bbox[0] + header_bbox[2]) * 0.5, float(header_bbox[1] + (0.75 * header_height))),
        font=day_font,
        fill=visual_theme.header_text_rgb,
    )

    total_minutes = float(int(end_total_minutes) - int(start_total_minutes))
    minute_to_y = float(planner_bottom - planner_top) / float(total_minutes)
    lane_gap = float(render_params.lane_gap_px)
    lane_width = float(planner_right - planner_left - (lane_gap * float(max(0, int(lane_count) - 1)))) / float(int(lane_count))

    # Vertical lane separators are kept subtle so they add variety without becoming semantic.
    if str(scene_variant) == "classic":
        for lane_index in range(1, int(lane_count)):
            x = float(planner_left + (lane_width * float(lane_index)) + (lane_gap * float(lane_index - 0.5)))
            draw.line(
                [(x, planner_top), (x, planner_bottom)],
                fill=visual_theme.minor_grid_line_rgb,
                width=1,
            )

    hour_label_font = load_font(int(render_params.hour_label_font_size_px), bold=False)
    major_width = int(render_params.grid_line_width_px)
    minor_width = int(render_params.minor_grid_line_width_px)
    for minute_value in range(int(start_total_minutes), int(end_total_minutes) + 1, int(slot_minutes)):
        y = float(planner_top + ((float(minute_value) - float(start_total_minutes)) * minute_to_y))
        is_hour = (int(minute_value) % 60) == 0
        is_boundary = minute_value in {int(start_total_minutes), int(end_total_minutes)}
        line_color = visual_theme.grid_line_rgb if (is_hour or is_boundary) else visual_theme.minor_grid_line_rgb
        line_width = major_width if (is_hour or is_boundary) else minor_width
        if str(scene_variant) == "minimal" and not (is_hour or is_boundary):
            continue
        draw.line([(planner_left, y), (planner_right, y)], fill=line_color, width=int(line_width))
        if minute_value < int(end_total_minutes) and is_hour:
            time_text = format_day_time_hhmm(int(minute_value))
            draw.text(
                (float(panel_bbox[0] + 8), float(y - (0.5 * render_params.hour_label_font_size_px))),
                str(time_text),
                font=hour_label_font,
                fill=visual_theme.time_text_rgb,
            )

    event_bboxes_by_id: Dict[str, Tuple[float, float, float, float]] = {}
    entities: List[Dict[str, Any]] = []
    for event in events:
        block_left = float(planner_left + (float(event.lane_index) * (lane_width + lane_gap)))
        block_right = float(block_left + lane_width)
        block_top = float(planner_top + (float(event.start_total_minutes - int(start_total_minutes)) * minute_to_y))
        block_bottom = float(planner_top + (float(event.end_total_minutes - int(start_total_minutes)) * minute_to_y))
        bbox = (block_left, block_top, block_right, block_bottom)
        event_bboxes_by_id[str(event.event_id)] = bbox

        fill_rgb = visual_theme.reference_fill_rgb if bool(event.is_reference) else visual_theme.event_fill_rgb
        outline_rgb = visual_theme.reference_outline_rgb if bool(event.is_reference) else visual_theme.event_outline_rgb
        text_rgb = visual_theme.reference_text_rgb if bool(event.is_reference) else visual_theme.event_text_rgb
        _rounded(
            draw,
            bbox,
            radius=int(render_params.event_corner_radius_px),
            fill=fill_rgb,
            outline=outline_rgb,
            width=max(2, int(render_params.panel_outline_width_px) - 1),
        )
        label_font = fit_font_to_box(
            draw,
            text=str(event.label),
            max_width=float(max(24.0, (block_right - block_left) - (2 * float(render_params.event_text_padding_px)))),
            max_height=float(max(18.0, min(30.0, (block_bottom - block_top) - (2 * float(render_params.event_text_padding_px))))),
            bold=True,
            min_size_px=max(10, int(render_params.event_label_font_size_px * 0.7)),
            max_size_px=int(render_params.event_label_font_size_px),
            fill_ratio=0.88,
        )
        draw_text_centered(
            draw,
            text=str(event.label),
            center=((block_left + block_right) * 0.5, min(block_bottom - 12.0, block_top + 18.0)),
            font=label_font,
            fill=text_rgb,
        )

        entities.append(
            {
                "type": "scheduled_event_block",
                "event_id": str(event.event_id),
                "label": str(event.label),
                "start_total_minutes": int(event.start_total_minutes),
                "end_total_minutes": int(event.end_total_minutes),
                "duration_minutes": int(event.duration_minutes),
                "lane_index": int(event.lane_index),
                "is_reference": bool(event.is_reference),
                "bbox_xyxy_px": [round(float(value), 3) for value in bbox],
            }
        )

    return RenderedScheduleScene(
        title_text=str(title_text),
        scene_bbox_px=tuple(float(value) for value in scene_bbox),
        panel_bbox_px=tuple(float(value) for value in panel_bbox),
        event_bboxes_by_id=dict(event_bboxes_by_id),
        entities=tuple(dict(entity) for entity in entities),
    )


__all__ = [
    "RenderedScheduleScene",
    "SUPPORTED_TEMPORAL_SCHEDULE_SCENE_VARIANTS",
    "ScheduledEventSpec",
    "ScheduleRenderParams",
    "render_day_schedule_scene",
    "resolve_schedule_render_params",
]
