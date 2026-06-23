"""Trace output helpers for two-anchor icon scenes."""

from __future__ import annotations

from typing import Any, Mapping

from .styles import two_anchor_style_trace


def two_anchor_render_spec(
    *,
    render_params: Mapping[str, Any],
    panel_geometry: Mapping[str, Any],
    sampled_palette_rgb,
) -> dict[str, Any]:
    """Return shared render metadata for a two-anchor scene."""

    return {
        "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
        "coord_space": "pixel",
        "panel_geometry": dict(panel_geometry),
        "style": two_anchor_style_trace(
            render_params=render_params,
            sampled_palette_rgb=sampled_palette_rgb,
        ),
    }


__all__ = ["two_anchor_render_spec"]

