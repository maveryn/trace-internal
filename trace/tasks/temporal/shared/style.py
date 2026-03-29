"""Shared temporal-domain visual-theme helpers for clocks, calendars, schedules, and timelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from ...shared.named_colors import available_named_colors, darken_color, named_color


Color = Tuple[int, int, int]
SUPPORTED_TEMPORAL_STYLE_VARIANTS: Tuple[str, ...] = (
    "studio",
    "accented",
    "marker",
)
SUPPORTED_TEMPORAL_COLOR_NAMES: Tuple[str, ...] = tuple(str(name) for name, _ in available_named_colors())
SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS: Tuple[str, ...] = SUPPORTED_TEMPORAL_STYLE_VARIANTS
SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES: Tuple[str, ...] = SUPPORTED_TEMPORAL_COLOR_NAMES


@dataclass(frozen=True)
class TemporalClockTheme:
    """Resolved per-instance analog-clock theme derived from one named accent color."""

    accent_color_name: str
    style_variant: str
    face_fill_rgb: Color
    face_outline_rgb: Color
    numeral_color_rgb: Color
    tick_color_rgb: Color
    hour_hand_color_rgb: Color
    minute_hand_color_rgb: Color
    center_dot_color_rgb: Color
    inner_ring_rgb: Color | None
    minor_tick_mode: str


@dataclass(frozen=True)
class TemporalCalendarTheme:
    """Resolved per-instance calendar theme derived from one named accent color."""

    accent_color_name: str
    style_variant: str
    panel_fill_rgb: Color
    panel_outline_rgb: Color
    title_text_rgb: Color
    weekday_fill_rgb: Color
    weekday_text_rgb: Color
    grid_line_rgb: Color
    date_text_rgb: Color
    inactive_date_text_rgb: Color
    marker_fill_rgb: Color
    marker_outline_rgb: Color
    marker_text_rgb: Color
    marker_kind: str


@dataclass(frozen=True)
class TemporalScheduleTheme:
    """Resolved per-instance day-planner theme derived from one named accent color."""

    accent_color_name: str
    style_variant: str
    panel_fill_rgb: Color
    panel_outline_rgb: Color
    header_fill_rgb: Color
    header_text_rgb: Color
    grid_line_rgb: Color
    minor_grid_line_rgb: Color
    time_text_rgb: Color
    event_fill_rgb: Color
    event_outline_rgb: Color
    event_text_rgb: Color
    reference_fill_rgb: Color
    reference_outline_rgb: Color
    reference_text_rgb: Color
    header_kind: str


@dataclass(frozen=True)
class TemporalTimelineTheme:
    """Resolved per-instance milestone-timeline theme derived from one named accent color."""

    accent_color_name: str
    style_variant: str
    panel_fill_rgb: Color
    panel_outline_rgb: Color
    title_text_rgb: Color
    subtitle_text_rgb: Color
    axis_line_rgb: Color
    tick_line_rgb: Color
    connector_line_rgb: Color
    marker_fill_rgb: Color
    marker_outline_rgb: Color
    event_fill_rgb: Color
    event_outline_rgb: Color
    event_text_rgb: Color
    event_subtext_rgb: Color
    primary_reference_fill_rgb: Color
    primary_reference_outline_rgb: Color
    primary_reference_text_rgb: Color
    secondary_reference_fill_rgb: Color
    secondary_reference_outline_rgb: Color
    secondary_reference_text_rgb: Color


def _blend_with_white(color: Sequence[int], *, color_weight: float) -> Color:
    """Blend one RGB color toward white by the requested color weight."""

    weight = max(0.0, min(1.0, float(color_weight)))
    if len(color) < 3:
        raise ValueError("temporal clock color blends require three RGB channels")
    return tuple(
        max(0, min(255, int(round((255.0 * (1.0 - weight)) + (float(int(channel)) * weight)))))
        for channel in color[:3]
    )


def _relative_luminance(color: Sequence[int]) -> float:
    """Return one simple perceived-luminance estimate in ``[0, 1]``."""

    if len(color) < 3:
        raise ValueError("temporal clock luminance requires three RGB channels")
    red, green, blue = [float(int(channel)) / 255.0 for channel in color[:3]]
    return float((0.2126 * red) + (0.7152 * green) + (0.0722 * blue))


def build_temporal_clock_theme(accent_color_name: str, style_variant: str) -> TemporalClockTheme:
    """Resolve one readable analog-clock theme from a named accent color and style."""

    accent_rgb = tuple(int(channel) for channel in named_color(str(accent_color_name)))
    accent_dark_rgb = darken_color(accent_rgb, factor=0.58)
    accent_deep_rgb = darken_color(accent_rgb, factor=0.42)
    neutral_dark_rgb = (42, 48, 58)
    subtle_outline_rgb = _blend_with_white(accent_deep_rgb, color_weight=0.42)
    face_fill_rgb = (255, 255, 255)
    numeral_color_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    tick_color_rgb = tuple(int(channel) for channel in accent_dark_rgb)
    hour_hand_color_rgb = tuple(int(channel) for channel in neutral_dark_rgb)
    minute_hand_color_rgb = tuple(int(channel) for channel in accent_rgb)
    center_dot_color_rgb = tuple(int(channel) for channel in accent_rgb)
    inner_ring_rgb: Color | None = None
    minor_tick_mode = "line"

    variant = str(style_variant)
    if variant == "accented":
        face_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.10)
        numeral_color_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        tick_color_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        hour_hand_color_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        minute_hand_color_rgb = tuple(int(channel) for channel in accent_rgb)
        center_dot_color_rgb = tuple(int(channel) for channel in accent_rgb)
        inner_ring_rgb = _blend_with_white(accent_rgb, color_weight=0.56)
        face_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
    elif variant == "marker":
        face_fill_rgb = (255, 255, 255)
        numeral_color_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        tick_color_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        hour_hand_color_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        minute_hand_color_rgb = tuple(int(channel) for channel in accent_rgb)
        center_dot_color_rgb = tuple(int(channel) for channel in accent_rgb)
        inner_ring_rgb = _blend_with_white(accent_rgb, color_weight=0.30)
        face_outline_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        minor_tick_mode = "dot"
    else:
        face_outline_rgb = tuple(int(channel) for channel in subtle_outline_rgb)
        inner_ring_rgb = _blend_with_white(accent_rgb, color_weight=0.18)

    if _relative_luminance(face_fill_rgb) <= 0.45:
        numeral_color_rgb = (255, 255, 255)

    return TemporalClockTheme(
        accent_color_name=str(accent_color_name),
        style_variant=variant,
        face_fill_rgb=tuple(int(channel) for channel in face_fill_rgb),
        face_outline_rgb=tuple(int(channel) for channel in face_outline_rgb),
        numeral_color_rgb=tuple(int(channel) for channel in numeral_color_rgb),
        tick_color_rgb=tuple(int(channel) for channel in tick_color_rgb),
        hour_hand_color_rgb=tuple(int(channel) for channel in hour_hand_color_rgb),
        minute_hand_color_rgb=tuple(int(channel) for channel in minute_hand_color_rgb),
        center_dot_color_rgb=tuple(int(channel) for channel in center_dot_color_rgb),
        inner_ring_rgb=(tuple(int(channel) for channel in inner_ring_rgb) if inner_ring_rgb is not None else None),
        minor_tick_mode=str(minor_tick_mode),
    )


def build_temporal_calendar_theme(accent_color_name: str, style_variant: str) -> TemporalCalendarTheme:
    """Resolve one readable month-calendar theme from a named accent color and style."""

    accent_rgb = tuple(int(channel) for channel in named_color(str(accent_color_name)))
    accent_dark_rgb = darken_color(accent_rgb, factor=0.58)
    accent_deep_rgb = darken_color(accent_rgb, factor=0.42)
    neutral_dark_rgb = (46, 52, 62)

    variant = str(style_variant)
    panel_fill_rgb = (255, 255, 255)
    panel_outline_rgb = _blend_with_white(accent_deep_rgb, color_weight=0.30)
    title_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    weekday_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.14)
    weekday_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    grid_line_rgb = _blend_with_white(accent_deep_rgb, color_weight=0.18)
    date_text_rgb = tuple(int(channel) for channel in neutral_dark_rgb)
    inactive_date_text_rgb = (170, 176, 186)
    marker_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.28)
    marker_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
    marker_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    marker_kind = "fill"

    if variant == "accented":
        panel_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.06)
        panel_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        weekday_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.22)
        weekday_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        grid_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.24)
        marker_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.44)
        marker_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        marker_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    elif variant == "marker":
        panel_fill_rgb = (255, 255, 255)
        panel_outline_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        title_text_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        weekday_fill_rgb = (255, 255, 255)
        weekday_text_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        grid_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.28)
        marker_fill_rgb = (255, 255, 255)
        marker_outline_rgb = tuple(int(channel) for channel in accent_rgb)
        marker_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        marker_kind = "ring"

    return TemporalCalendarTheme(
        accent_color_name=str(accent_color_name),
        style_variant=variant,
        panel_fill_rgb=tuple(int(channel) for channel in panel_fill_rgb),
        panel_outline_rgb=tuple(int(channel) for channel in panel_outline_rgb),
        title_text_rgb=tuple(int(channel) for channel in title_text_rgb),
        weekday_fill_rgb=tuple(int(channel) for channel in weekday_fill_rgb),
        weekday_text_rgb=tuple(int(channel) for channel in weekday_text_rgb),
        grid_line_rgb=tuple(int(channel) for channel in grid_line_rgb),
        date_text_rgb=tuple(int(channel) for channel in date_text_rgb),
        inactive_date_text_rgb=tuple(int(channel) for channel in inactive_date_text_rgb),
        marker_fill_rgb=tuple(int(channel) for channel in marker_fill_rgb),
        marker_outline_rgb=tuple(int(channel) for channel in marker_outline_rgb),
        marker_text_rgb=tuple(int(channel) for channel in marker_text_rgb),
        marker_kind=str(marker_kind),
    )


def build_temporal_schedule_theme(accent_color_name: str, style_variant: str) -> TemporalScheduleTheme:
    """Resolve one readable day-planner theme from a named accent color and style."""

    accent_rgb = tuple(int(channel) for channel in named_color(str(accent_color_name)))
    accent_dark_rgb = darken_color(accent_rgb, factor=0.58)
    accent_deep_rgb = darken_color(accent_rgb, factor=0.42)
    neutral_dark_rgb = (46, 52, 62)

    variant = str(style_variant)
    panel_fill_rgb = (255, 255, 255)
    panel_outline_rgb = _blend_with_white(accent_deep_rgb, color_weight=0.30)
    header_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.14)
    header_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    grid_line_rgb = _blend_with_white(accent_deep_rgb, color_weight=0.18)
    minor_grid_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.10)
    time_text_rgb = tuple(int(channel) for channel in neutral_dark_rgb)
    event_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.20)
    event_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
    event_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    reference_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.42)
    reference_outline_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    reference_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    header_kind = "fill"

    if variant == "accented":
        panel_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.06)
        panel_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        header_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.26)
        header_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        grid_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.22)
        minor_grid_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.14)
        event_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.30)
        event_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        event_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        reference_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.52)
        reference_outline_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        reference_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    elif variant == "marker":
        panel_fill_rgb = (255, 255, 255)
        panel_outline_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        header_fill_rgb = (255, 255, 255)
        header_text_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        grid_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.22)
        minor_grid_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.12)
        time_text_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        event_fill_rgb = (255, 255, 255)
        event_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        event_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        reference_fill_rgb = (255, 255, 255)
        reference_outline_rgb = tuple(int(channel) for channel in accent_rgb)
        reference_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        header_kind = "line"

    return TemporalScheduleTheme(
        accent_color_name=str(accent_color_name),
        style_variant=variant,
        panel_fill_rgb=tuple(int(channel) for channel in panel_fill_rgb),
        panel_outline_rgb=tuple(int(channel) for channel in panel_outline_rgb),
        header_fill_rgb=tuple(int(channel) for channel in header_fill_rgb),
        header_text_rgb=tuple(int(channel) for channel in header_text_rgb),
        grid_line_rgb=tuple(int(channel) for channel in grid_line_rgb),
        minor_grid_line_rgb=tuple(int(channel) for channel in minor_grid_line_rgb),
        time_text_rgb=tuple(int(channel) for channel in time_text_rgb),
        event_fill_rgb=tuple(int(channel) for channel in event_fill_rgb),
        event_outline_rgb=tuple(int(channel) for channel in event_outline_rgb),
        event_text_rgb=tuple(int(channel) for channel in event_text_rgb),
        reference_fill_rgb=tuple(int(channel) for channel in reference_fill_rgb),
        reference_outline_rgb=tuple(int(channel) for channel in reference_outline_rgb),
        reference_text_rgb=tuple(int(channel) for channel in reference_text_rgb),
        header_kind=str(header_kind),
    )


def build_temporal_timeline_theme(accent_color_name: str, style_variant: str) -> TemporalTimelineTheme:
    """Resolve one readable milestone-timeline theme from a named accent color and style."""

    accent_rgb = tuple(int(channel) for channel in named_color(str(accent_color_name)))
    accent_dark_rgb = darken_color(accent_rgb, factor=0.58)
    accent_deep_rgb = darken_color(accent_rgb, factor=0.42)
    neutral_dark_rgb = (46, 52, 62)
    soft_gray_rgb = (124, 132, 144)

    variant = str(style_variant)
    panel_fill_rgb = (255, 255, 255)
    panel_outline_rgb = _blend_with_white(accent_deep_rgb, color_weight=0.30)
    title_text_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    subtitle_text_rgb = tuple(int(channel) for channel in soft_gray_rgb)
    axis_line_rgb = _blend_with_white(accent_deep_rgb, color_weight=0.22)
    tick_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.18)
    connector_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.22)
    marker_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.28)
    marker_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
    event_fill_rgb = (255, 255, 255)
    event_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
    event_text_rgb = tuple(int(channel) for channel in neutral_dark_rgb)
    event_subtext_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    reference_fill_rgb = tuple(int(channel) for channel in accent_rgb)
    reference_outline_rgb = tuple(int(channel) for channel in accent_deep_rgb)
    reference_text_rgb: Color = (255, 255, 255) if _relative_luminance(reference_fill_rgb) < 0.60 else tuple(int(channel) for channel in neutral_dark_rgb)

    if variant == "accented":
        panel_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.07)
        panel_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        axis_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.30)
        tick_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.24)
        connector_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.26)
        marker_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.38)
        marker_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        event_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.18)
        event_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        event_subtext_rgb = tuple(int(channel) for channel in accent_dark_rgb)
    elif variant == "marker":
        panel_fill_rgb = (255, 255, 255)
        panel_outline_rgb = tuple(int(channel) for channel in accent_deep_rgb)
        title_text_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        axis_line_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        tick_line_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.18)
        connector_line_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        marker_fill_rgb = (255, 255, 255)
        marker_outline_rgb = tuple(int(channel) for channel in accent_rgb)
        event_fill_rgb = (255, 255, 255)
        event_outline_rgb = tuple(int(channel) for channel in accent_dark_rgb)
        event_subtext_rgb = tuple(int(channel) for channel in accent_dark_rgb)

    return TemporalTimelineTheme(
        accent_color_name=str(accent_color_name),
        style_variant=variant,
        panel_fill_rgb=tuple(int(channel) for channel in panel_fill_rgb),
        panel_outline_rgb=tuple(int(channel) for channel in panel_outline_rgb),
        title_text_rgb=tuple(int(channel) for channel in title_text_rgb),
        subtitle_text_rgb=tuple(int(channel) for channel in subtitle_text_rgb),
        axis_line_rgb=tuple(int(channel) for channel in axis_line_rgb),
        tick_line_rgb=tuple(int(channel) for channel in tick_line_rgb),
        connector_line_rgb=tuple(int(channel) for channel in connector_line_rgb),
        marker_fill_rgb=tuple(int(channel) for channel in marker_fill_rgb),
        marker_outline_rgb=tuple(int(channel) for channel in marker_outline_rgb),
        event_fill_rgb=tuple(int(channel) for channel in event_fill_rgb),
        event_outline_rgb=tuple(int(channel) for channel in event_outline_rgb),
        event_text_rgb=tuple(int(channel) for channel in event_text_rgb),
        event_subtext_rgb=tuple(int(channel) for channel in event_subtext_rgb),
        primary_reference_fill_rgb=tuple(int(channel) for channel in reference_fill_rgb),
        primary_reference_outline_rgb=tuple(int(channel) for channel in reference_outline_rgb),
        primary_reference_text_rgb=tuple(int(channel) for channel in reference_text_rgb),
        secondary_reference_fill_rgb=tuple(int(channel) for channel in reference_fill_rgb),
        secondary_reference_outline_rgb=tuple(int(channel) for channel in reference_outline_rgb),
        secondary_reference_text_rgb=tuple(int(channel) for channel in reference_text_rgb),
    )


__all__ = [
    "SUPPORTED_TEMPORAL_COLOR_NAMES",
    "SUPPORTED_TEMPORAL_STYLE_VARIANTS",
    "SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES",
    "SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS",
    "TemporalCalendarTheme",
    "TemporalClockTheme",
    "TemporalScheduleTheme",
    "TemporalTimelineTheme",
    "build_temporal_calendar_theme",
    "build_temporal_clock_theme",
    "build_temporal_schedule_theme",
    "build_temporal_timeline_theme",
]
