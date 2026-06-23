"""Trace payload helpers for sequence-strip icon scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ...shared.icon_task_rendering import icon_render_style_trace


def sequence_render_spec(
    *,
    common_ids: Mapping[str, Any],
    panel_geometry: Mapping[str, Any],
    render_params: Mapping[str, Any],
    sampled_palette_rgb: Sequence[Sequence[int]],
    cell_box_width_px: int,
    cell_box_height_px: int,
    extra_style: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize shared render metadata for a horizontal sequence row."""

    style = {
        **icon_render_style_trace(
            render_params=render_params,
            sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
        ),
        "cell_padding_px": int(render_params["cell_padding_px"]),
        "cell_icon_padding_px": int(render_params["cell_icon_padding_px"]),
        "cell_corner_radius_px": int(render_params["cell_corner_radius_px"]),
        "cell_box_width_range_px": [
            int(render_params["cell_box_width_min_px"]),
            int(render_params["cell_box_width_max_px"]),
        ],
        "cell_box_height_range_px": [
            int(render_params["cell_box_height_min_px"]),
            int(render_params["cell_box_height_max_px"]),
        ],
        "sampled_cell_box_size_px": [
            int(cell_box_width_px),
            int(cell_box_height_px),
        ],
    }
    if extra_style:
        style.update({str(key): value for key, value in extra_style.items()})
    return {
        **dict(common_ids),
        "canvas_size": list(panel_geometry["canvas_size"]),
        "coord_space": "pixel",
        "panel_geometry": dict(panel_geometry),
        "style": style,
    }


def bbox_anchor_render_map(*, anchor_name: str, bbox_xyxy: Sequence[int]) -> dict[str, Any]:
    """Serialize a scalar bbox anchor for the rendered image."""

    return {
        "image_id": "img0",
        "anchors": {
            str(anchor_name): [int(value) for value in bbox_xyxy],
        },
    }


__all__ = ["bbox_anchor_render_map", "sequence_render_spec"]
