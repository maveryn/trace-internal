"""Shared graph-domain style helpers for named-color visual themes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from ...shared.named_colors import available_named_colors, darken_color, named_color


Color = Tuple[int, int, int]
SUPPORTED_NODE_COLOR_NAMES: Tuple[str, ...] = tuple(str(name) for name, _ in available_named_colors())


@dataclass(frozen=True)
class GraphNamedColorTheme:
    """Resolved per-instance graph color theme derived from one named node color."""

    node_color_name: str
    background_color_rgb: Color
    panel_fill_rgb: Color
    panel_border_rgb: Color
    title_color_rgb: Color
    edge_color_rgb: Color
    node_fill_rgb: Color
    node_border_rgb: Color
    label_text_rgb: Color
    label_stroke_rgb: Color


def _blend_with_white(color: Sequence[int], *, color_weight: float) -> Color:
    """Blend one RGB color toward white by the requested color weight."""

    weight = max(0.0, min(1.0, float(color_weight)))
    if len(color) < 3:
        raise ValueError("graph color blends require three RGB channels")
    return tuple(
        max(0, min(255, int(round((255.0 * (1.0 - weight)) + (float(int(channel)) * weight)))))
        for channel in color[:3]
    )


def _relative_luminance(color: Sequence[int]) -> float:
    """Return one simple perceived-luminance estimate in ``[0, 1]``."""

    if len(color) < 3:
        raise ValueError("graph luminance requires three RGB channels")
    red, green, blue = [float(int(channel)) / 255.0 for channel in color[:3]]
    return float((0.2126 * red) + (0.7152 * green) + (0.0722 * blue))


def build_graph_named_color_theme(node_color_name: str) -> GraphNamedColorTheme:
    """Resolve one readable graph theme from a canonical named node color."""

    node_fill_rgb = tuple(int(channel) for channel in named_color(str(node_color_name)))
    node_border_rgb = darken_color(node_fill_rgb, factor=0.58)
    edge_color_rgb = darken_color(node_fill_rgb, factor=0.72)
    title_color_rgb = darken_color(node_fill_rgb, factor=0.46)
    panel_border_rgb = _blend_with_white(node_fill_rgb, color_weight=0.28)
    panel_fill_rgb = _blend_with_white(node_fill_rgb, color_weight=0.06)
    background_color_rgb = _blend_with_white(node_fill_rgb, color_weight=0.03)

    if _relative_luminance(node_fill_rgb) >= 0.55:
        label_text_rgb = tuple(int(channel) for channel in darken_color(node_fill_rgb, factor=0.23))
        label_stroke_rgb = (255, 255, 255)
    else:
        label_text_rgb = (255, 255, 255)
        label_stroke_rgb = tuple(int(channel) for channel in node_border_rgb)

    return GraphNamedColorTheme(
        node_color_name=str(node_color_name),
        background_color_rgb=tuple(int(channel) for channel in background_color_rgb),
        panel_fill_rgb=tuple(int(channel) for channel in panel_fill_rgb),
        panel_border_rgb=tuple(int(channel) for channel in panel_border_rgb),
        title_color_rgb=tuple(int(channel) for channel in title_color_rgb),
        edge_color_rgb=tuple(int(channel) for channel in edge_color_rgb),
        node_fill_rgb=tuple(int(channel) for channel in node_fill_rgb),
        node_border_rgb=tuple(int(channel) for channel in node_border_rgb),
        label_text_rgb=tuple(int(channel) for channel in label_text_rgb),
        label_stroke_rgb=tuple(int(channel) for channel in label_stroke_rgb),
    )


__all__ = [
    "GraphNamedColorTheme",
    "SUPPORTED_NODE_COLOR_NAMES",
    "build_graph_named_color_theme",
]
