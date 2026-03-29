"""Shared temporal-domain visual-theme helpers for analog clocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from ...shared.named_colors import available_named_colors, darken_color, named_color


Color = Tuple[int, int, int]
SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS: Tuple[str, ...] = (
    "studio",
    "accented",
    "marker",
)
SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES: Tuple[str, ...] = tuple(str(name) for name, _ in available_named_colors())


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


__all__ = [
    "SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES",
    "SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS",
    "TemporalClockTheme",
    "build_temporal_clock_theme",
]
