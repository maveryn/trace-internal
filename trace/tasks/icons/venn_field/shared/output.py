"""Trace output helpers for Venn-field icon scenes."""

from __future__ import annotations

from typing import Any, Mapping

from .styles import venn_style_trace


def venn_field_render_spec(
    *,
    render_params: Mapping[str, Any],
    panel_geometry: Mapping[str, Any],
    sampled_palette_rgb,
) -> dict[str, Any]:
    """Return shared render metadata for one Venn-field scene."""

    return {
        "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
        "coord_space": "pixel",
        "panel_geometry": dict(panel_geometry),
        "style": venn_style_trace(
            render_params=render_params,
            sampled_palette_rgb=sampled_palette_rgb,
        ),
    }


__all__ = ["venn_field_render_spec"]
