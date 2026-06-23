"""Trace payload helpers for the pattern-grid icons scene."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ...shared.icon_task_rendering import icon_render_style_trace

from .state import PatternGridSpec, RenderedPatternGridScene


def scene_kind_for_axis(attribute_axis: str, *, color_group_axis: str = "") -> str:
    """Return the public trace scene-kind id for one pattern attribute."""

    if str(attribute_axis) == "color":
        return "icons_pattern_grid_color_violation"
    if str(attribute_axis) == "size":
        return "icons_pattern_grid_size_violation"
    raise ValueError(f"unsupported attribute_axis: {attribute_axis}")


def question_format_for_axis(attribute_axis: str, *, color_group_axis: str = "") -> str:
    """Return the execution-trace question-format id for one pattern attribute."""

    if str(attribute_axis) == "color":
        return "identify_grid_color_violation"
    if str(attribute_axis) == "size":
        return "identify_grid_size_violation"
    raise ValueError(f"unsupported attribute_axis: {attribute_axis}")


def pattern_rule_for_axis(attribute_axis: str, *, color_group_axis: str = "") -> str:
    """Return the symbolic pattern-rule id for one pattern attribute."""

    if str(attribute_axis) == "color":
        if str(color_group_axis) == "row":
            return "row_uniform_color"
        if str(color_group_axis) == "column":
            return "column_uniform_color"
        raise ValueError("color_group_axis must be 'row' or 'column' for color pattern grids")
    if str(attribute_axis) == "size":
        return "row_col_size_level_offsets"
    raise ValueError(f"unsupported attribute_axis: {attribute_axis}")


def pattern_grid_render_style(
    *,
    render_params: Mapping[str, Any],
    rendered_scene: RenderedPatternGridScene,
    spec: PatternGridSpec,
) -> Dict[str, Any]:
    """Return render style metadata for one pattern-grid instance."""

    style = icon_render_style_trace(
        render_params=render_params,
        sampled_palette_rgb=rendered_scene.sampled_palette_rgb,
    )
    style.update(
        {
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
                int(rendered_scene.cell_box_width_px),
                int(rendered_scene.cell_box_height_px),
            ],
            "cell_label_font_size_px": int(render_params["cell_label_font_size_px"]),
            "cell_label_color_rgb": list(render_params["cell_label_color_rgb"]),
            "scene_content_side_padding_px": int(render_params["scene_content_side_padding_px"]),
            "scene_content_bottom_padding_px": int(render_params["scene_content_bottom_padding_px"]),
            "scene_content_top_offset_px": int(render_params["scene_content_top_offset_px"]),
        }
    )
    if str(spec.attribute_axis) == "color":
        style["color_level_names"] = [str(value) for value in spec.level_names]
        style["color_ladder_rgb"] = [list(color) for color in spec.color_ladder_rgb]
        style["nominal_size_px"] = int(rendered_scene.nominal_size_px or 0)
    else:
        style["size_level_gap_px"] = int(render_params["size_level_gap_px"])
        style["size_level_nominal_sizes_px"] = {
            str(level): int(size_px)
            for level, size_px in dict(rendered_scene.size_level_nominal_sizes_px or {}).items()
        }
    return style


__all__ = [
    "pattern_grid_render_style",
    "pattern_rule_for_axis",
    "question_format_for_axis",
    "scene_kind_for_axis",
]
