"""Shared month-calendar rendering helpers for temporal tasks."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import draw_text_centered, load_font
from .style import TemporalCalendarTheme
from .time_format import month_name, weekday_abbreviation


SUPPORTED_TEMPORAL_CALENDAR_SCENE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "minimal",
    "outline",
)


@dataclass(frozen=True)
class CalendarRenderParams:
    """Resolved rendering parameters for a month-view calendar scene."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    title_height_px: int
    title_bottom_gap_px: int
    weekday_header_height_px: int
    weekday_grid_gap_px: int
    cell_gap_px: int
    panel_corner_radius_px: int
    panel_outline_width_px: int
    cell_corner_radius_px: int
    cell_outline_width_px: int
    title_font_size_px: int
    weekday_font_size_px: int
    date_font_size_px: int
    marker_inset_px: int
    marker_outline_width_px: int


@dataclass(frozen=True)
class RenderedCalendarScene:
    """Rendered month-view calendar geometry and projected date-cell metadata."""

    year: int
    month: int
    row_count: int
    title_text: str
    panel_bbox_px: Tuple[float, float, float, float]
    scene_bbox_px: Tuple[float, float, float, float]
    date_cell_bboxes_by_day: Dict[int, Tuple[float, float, float, float]]
    entities: Tuple[Dict[str, Any], ...]


def _require_int(value: Any, *, name: str) -> int:
    """Convert one render parameter to `int` and fail loudly on missing values."""

    if value is None:
        raise ValueError(f"missing required calendar render parameter: {name}")
    return int(value)


def resolve_calendar_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    fallback_values: Mapping[str, Any],
) -> CalendarRenderParams:
    """Resolve the active month-calendar render parameters from task defaults."""

    resolved: Dict[str, int] = {}
    for key, fallback in fallback_values.items():
        if key not in {
            "canvas_width",
            "canvas_height",
            "outer_margin_px",
            "title_height_px",
            "title_bottom_gap_px",
            "weekday_header_height_px",
            "weekday_grid_gap_px",
            "cell_gap_px",
            "panel_corner_radius_px",
            "panel_outline_width_px",
            "cell_corner_radius_px",
            "cell_outline_width_px",
            "title_font_size_px",
            "weekday_font_size_px",
            "date_font_size_px",
            "marker_inset_px",
            "marker_outline_width_px",
        }:
            continue
        resolved[str(key)] = _require_int(params.get(str(key), render_defaults.get(str(key), fallback)), name=str(key))
    return CalendarRenderParams(**resolved)


def _rounded(draw: ImageDraw.ImageDraw, bbox: Sequence[float], *, radius: int, fill=None, outline=None, width: int = 1) -> None:
    """Draw one rounded rectangle with consistent coordinate coercion."""

    draw.rounded_rectangle([float(value) for value in bbox], radius=int(radius), fill=fill, outline=outline, width=int(width))


def render_month_calendar_scene(
    image: Image.Image,
    *,
    year: int,
    month: int,
    marked_dates: Sequence[int],
    scene_variant: str,
    render_params: CalendarRenderParams,
    visual_theme: TemporalCalendarTheme,
) -> RenderedCalendarScene:
    """Render one month-view calendar and return projected valid-date geometry."""

    calendar_rows = calendar.Calendar(firstweekday=0).monthdayscalendar(int(year), int(month))
    row_count = len(calendar_rows)
    if int(row_count) not in {4, 5, 6}:
        raise ValueError("monthdayscalendar returned an unsupported row count")

    draw = ImageDraw.Draw(image)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    weekday_font = load_font(int(render_params.weekday_font_size_px), bold=True)
    date_font = load_font(int(render_params.date_font_size_px), bold=False)

    panel_bbox = (
        float(render_params.outer_margin_px),
        float(render_params.outer_margin_px),
        float(render_params.canvas_width - render_params.outer_margin_px),
        float(render_params.canvas_height - render_params.outer_margin_px),
    )
    panel_outline_width = 0 if str(scene_variant) == "minimal" else int(render_params.panel_outline_width_px)
    _rounded(
        draw,
        panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=tuple(int(channel) for channel in visual_theme.panel_fill_rgb),
        outline=(tuple(int(channel) for channel in visual_theme.panel_outline_rgb) if panel_outline_width > 0 else None),
        width=max(1, int(panel_outline_width)) if panel_outline_width > 0 else 1,
    )

    title_text = f"{month_name(int(month))} {int(year)}"
    title_center = (
        0.5 * float(panel_bbox[0] + panel_bbox[2]),
        float(panel_bbox[1]) + (0.5 * float(render_params.title_height_px)),
    )
    draw_text_centered(
        draw,
        text=str(title_text),
        center=title_center,
        font=title_font,
        fill=tuple(int(channel) for channel in visual_theme.title_text_rgb),
    )

    grid_left = float(panel_bbox[0]) + float(render_params.cell_gap_px)
    grid_right = float(panel_bbox[2]) - float(render_params.cell_gap_px)
    weekday_top = float(panel_bbox[1]) + float(render_params.title_height_px) + float(render_params.title_bottom_gap_px)
    available_grid_top = weekday_top + float(render_params.weekday_header_height_px) + float(render_params.weekday_grid_gap_px)
    grid_bottom = float(panel_bbox[3]) - float(render_params.cell_gap_px)
    cell_gap = float(render_params.cell_gap_px)
    available_grid_width = float(grid_right - grid_left)
    available_grid_height = float(grid_bottom - available_grid_top)
    cell_width = (float(available_grid_width) - (6.0 * cell_gap)) / 7.0
    cell_height = (float(available_grid_height) - (float(row_count - 1) * cell_gap)) / float(row_count)
    if float(cell_width) <= 0.0 or float(cell_height) <= 0.0:
        raise ValueError("calendar render area is too small for the requested month grid")

    entities: List[Dict[str, Any]] = []
    date_cell_bboxes_by_day: Dict[int, Tuple[float, float, float, float]] = {}
    marked_date_set = {int(day) for day in marked_dates}

    for weekday_index in range(7):
        header_x1 = float(grid_left + (weekday_index * (cell_width + cell_gap)))
        header_x2 = float(header_x1 + cell_width)
        header_bbox = (
            float(header_x1),
            float(weekday_top),
            float(header_x2),
            float(weekday_top + float(render_params.weekday_header_height_px)),
        )
        header_fill = None if str(scene_variant) == "minimal" else tuple(int(channel) for channel in visual_theme.weekday_fill_rgb)
        header_outline = (
            tuple(int(channel) for channel in visual_theme.panel_outline_rgb)
            if str(scene_variant) in {"classic", "outline"}
            else None
        )
        _rounded(
            draw,
            header_bbox,
            radius=max(4, int(render_params.cell_corner_radius_px) - 2),
            fill=header_fill,
            outline=header_outline,
            width=max(1, int(render_params.cell_outline_width_px) - 1) if header_outline is not None else 1,
        )
        draw_text_centered(
            draw,
            text=weekday_abbreviation(int(weekday_index)),
            center=(0.5 * float(header_bbox[0] + header_bbox[2]), 0.5 * float(header_bbox[1] + header_bbox[3])),
            font=weekday_font,
            fill=tuple(int(channel) for channel in visual_theme.weekday_text_rgb),
        )

    for row_index, week in enumerate(calendar_rows):
        row_y1 = float(available_grid_top + (row_index * (cell_height + cell_gap)))
        row_y2 = float(row_y1 + cell_height)
        for weekday_index, day_value in enumerate(week):
            cell_x1 = float(grid_left + (weekday_index * (cell_width + cell_gap)))
            cell_x2 = float(cell_x1 + cell_width)
            cell_bbox = (float(cell_x1), float(row_y1), float(cell_x2), float(row_y2))
            cell_outline = (
                tuple(int(channel) for channel in visual_theme.grid_line_rgb)
                if str(scene_variant) != "minimal"
                else tuple(int(channel) for channel in visual_theme.grid_line_rgb)
            )
            cell_fill = tuple(int(channel) for channel in visual_theme.panel_fill_rgb)
            _rounded(
                draw,
                cell_bbox,
                radius=int(render_params.cell_corner_radius_px),
                fill=cell_fill,
                outline=cell_outline,
                width=max(1, int(render_params.cell_outline_width_px)),
            )

            if int(day_value) <= 0:
                continue

            is_marked = int(day_value) in marked_date_set
            if is_marked:
                marker_bbox = (
                    float(cell_bbox[0] + float(render_params.marker_inset_px)),
                    float(cell_bbox[1] + float(render_params.marker_inset_px)),
                    float(cell_bbox[2] - float(render_params.marker_inset_px)),
                    float(cell_bbox[3] - float(render_params.marker_inset_px)),
                )
                marker_fill = (
                    tuple(int(channel) for channel in visual_theme.marker_fill_rgb)
                    if str(visual_theme.marker_kind) == "fill"
                    else None
                )
                _rounded(
                    draw,
                    marker_bbox,
                    radius=max(4, int(render_params.cell_corner_radius_px) - 2),
                    fill=marker_fill,
                    outline=tuple(int(channel) for channel in visual_theme.marker_outline_rgb),
                    width=max(1, int(render_params.marker_outline_width_px)),
                )

            draw_text_centered(
                draw,
                text=str(int(day_value)),
                center=(0.5 * float(cell_bbox[0] + cell_bbox[2]), 0.5 * float(cell_bbox[1] + cell_bbox[3])),
                font=date_font,
                fill=(
                    tuple(int(channel) for channel in visual_theme.marker_text_rgb)
                    if is_marked
                    else tuple(int(channel) for channel in visual_theme.date_text_rgb)
                ),
            )

            date_cell_bboxes_by_day[int(day_value)] = tuple(float(value) for value in cell_bbox)
            entities.append(
                {
                    "entity_id": f"date_{int(day_value)}",
                    "entity_type": "calendar_date_cell",
                    "bbox_px": [round(float(value), 3) for value in cell_bbox],
                    "attrs": {
                        "date_number": int(day_value),
                        "weekday_index": int(weekday_index),
                        "week_row_index": int(row_index),
                        "year": int(year),
                        "month": int(month),
                        "month_name": str(month_name(int(month))),
                        "is_marked": bool(is_marked),
                    },
                }
            )

    return RenderedCalendarScene(
        year=int(year),
        month=int(month),
        row_count=int(row_count),
        title_text=str(title_text),
        panel_bbox_px=tuple(float(value) for value in panel_bbox),
        scene_bbox_px=tuple(float(value) for value in panel_bbox),
        date_cell_bboxes_by_day={int(day): tuple(float(value) for value in bbox) for day, bbox in date_cell_bboxes_by_day.items()},
        entities=tuple(dict(entity) for entity in entities),
    )


__all__ = [
    "CalendarRenderParams",
    "RenderedCalendarScene",
    "SUPPORTED_TEMPORAL_CALENDAR_SCENE_VARIANTS",
    "render_month_calendar_scene",
    "resolve_calendar_render_params",
]
