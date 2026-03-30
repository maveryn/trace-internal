"""Shared physics-domain visual-theme helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from ...shared.named_colors import available_named_colors, darken_color, named_color


Color = Tuple[int, int, int]
SUPPORTED_PHYSICS_COLOR_NAMES: Tuple[str, ...] = tuple(str(name) for name, _ in available_named_colors())


@dataclass(frozen=True)
class PhysicsLeverTheme:
    """Resolved per-instance lever-balance theme derived from one named accent color."""

    accent_color_name: str
    beam_fill_rgb: Color
    beam_outline_rgb: Color
    beam_tick_rgb: Color
    distance_text_rgb: Color
    weight_fill_rgb: Color
    weight_outline_rgb: Color
    weight_text_rgb: Color
    fulcrum_fill_rgb: Color
    fulcrum_outline_rgb: Color
    texture_rgb: Color


def _blend_with_white(color: Sequence[int], *, color_weight: float) -> Color:
    """Blend one RGB color toward white by the requested color weight."""

    weight = max(0.0, min(1.0, float(color_weight)))
    if len(color) < 3:
        raise ValueError("physics color blends require three RGB channels")
    return tuple(
        max(0, min(255, int(round((255.0 * (1.0 - weight)) + (float(int(channel)) * weight)))))
        for channel in color[:3]
    )


def build_physics_lever_theme(accent_color_name: str) -> PhysicsLeverTheme:
    """Resolve one readable lever-balance theme from a named accent color."""

    accent_rgb = tuple(int(channel) for channel in named_color(str(accent_color_name)))
    accent_dark_rgb = darken_color(accent_rgb, factor=0.60)
    accent_deep_rgb = darken_color(accent_rgb, factor=0.42)
    beam_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.34)
    weight_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.14)
    fulcrum_fill_rgb = _blend_with_white(accent_rgb, color_weight=0.78)
    texture_rgb = _blend_with_white(accent_dark_rgb, color_weight=0.42)
    neutral_text_rgb = (42, 46, 52)
    return PhysicsLeverTheme(
        accent_color_name=str(accent_color_name),
        beam_fill_rgb=tuple(int(channel) for channel in beam_fill_rgb),
        beam_outline_rgb=tuple(int(channel) for channel in accent_deep_rgb),
        beam_tick_rgb=tuple(int(channel) for channel in accent_dark_rgb),
        distance_text_rgb=tuple(int(channel) for channel in accent_deep_rgb),
        weight_fill_rgb=tuple(int(channel) for channel in weight_fill_rgb),
        weight_outline_rgb=tuple(int(channel) for channel in accent_dark_rgb),
        weight_text_rgb=tuple(int(channel) for channel in neutral_text_rgb),
        fulcrum_fill_rgb=tuple(int(channel) for channel in fulcrum_fill_rgb),
        fulcrum_outline_rgb=tuple(int(channel) for channel in accent_deep_rgb),
        texture_rgb=tuple(int(channel) for channel in texture_rgb),
    )


__all__ = [
    "PhysicsLeverTheme",
    "SUPPORTED_PHYSICS_COLOR_NAMES",
    "build_physics_lever_theme",
]
