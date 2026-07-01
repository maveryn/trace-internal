"""Rendering primitives for coordinate-conversion diagrams."""

from __future__ import annotations

import math
from typing import Any, Mapping

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import (
    GEOMETRY_STYLE_PROFILE_COORDINATE_GRID,
    prepare_geometry_diagram_style_and_background,
)
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.text_rendering import draw_text_centered, load_font

from .sampling import format_number
from .state import CartesianPointCase, PolarPointCase, RenderedCoordinateScene

SCENE_ID = "coordinate_conversion"


def _resolve_canvas(rendering_defaults: Mapping[str, Any]) -> tuple[int, int]:
    width = int(group_default(rendering_defaults, "canvas_width", 768))
    height = int(group_default(rendering_defaults, "canvas_height", 768))
    return max(480, width), max(480, height)


def _plot_bbox(width: int, height: int) -> tuple[int, int, int, int]:
    margin = max(70, int(round(min(width, height) * 0.095)))
    size = min(int(width) - (2 * margin), int(height) - (2 * margin))
    left = (int(width) - size) // 2
    top = (int(height) - size) // 2
    return int(left), int(top), int(left + size), int(top + size)


def _project_graph_point(
    point: tuple[float, float],
    *,
    plot_bbox: tuple[int, int, int, int],
    graph_min: int,
    graph_max: int,
) -> tuple[float, float]:
    left, top, right, bottom = [float(value) for value in plot_bbox]
    span = float(int(graph_max) - int(graph_min))
    return (
        left + ((float(point[0]) - float(graph_min)) / span * (right - left)),
        top + ((float(graph_max) - float(point[1])) / span * (bottom - top)),
    )


def _draw_coordinate_grid(
    draw: ImageDraw.ImageDraw,
    *,
    plot_bbox: tuple[int, int, int, int],
    graph_min: int,
    graph_max: int,
    style: Any,
) -> None:
    """Draw grid, axes, and labels without changing graph-to-pixel mapping."""

    draw.rectangle(
        plot_bbox,
        fill=tuple(int(value) for value in style.panel_alt_fill_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=2,
    )
    tick_font = load_font(16, bold=False)
    for value in range(int(graph_min), int(graph_max) + 1):
        x_px, _ = _project_graph_point((value, graph_min), plot_bbox=plot_bbox, graph_min=graph_min, graph_max=graph_max)
        _, y_px = _project_graph_point((graph_min, value), plot_bbox=plot_bbox, graph_min=graph_min, graph_max=graph_max)
        is_axis = value == 0
        is_major = value % 4 == 0
        color = style.axis_rgb if is_axis else (style.grid_major_rgb if is_major else style.grid_minor_rgb)
        line_width = style.axis_stroke_width_px if is_axis else (style.grid_major_width_px if is_major else style.grid_minor_width_px)
        draw.line([(x_px, plot_bbox[1]), (x_px, plot_bbox[3])], fill=tuple(color), width=max(1, int(line_width)))
        draw.line([(plot_bbox[0], y_px), (plot_bbox[2], y_px)], fill=tuple(color), width=max(1, int(line_width)))
        if value % 4 == 0:
            draw_text_centered(
                draw,
                text=str(value),
                center=(float(x_px), float(plot_bbox[3] + 22)),
                font=tick_font,
                fill=tuple(style.label_rgb),
                stroke_fill=tuple(style.label_stroke_rgb),
                stroke_width=0,
            )
            draw_text_centered(
                draw,
                text=str(value),
                center=(float(plot_bbox[0] - 26), float(y_px)),
                font=tick_font,
                fill=tuple(style.label_rgb),
                stroke_fill=tuple(style.label_stroke_rgb),
                stroke_width=0,
            )
    label_font = load_font(18, bold=True)
    draw_text_centered(
        draw,
        text="x",
        center=(float(plot_bbox[2] + 26), float(_project_graph_point((0, 0), plot_bbox=plot_bbox, graph_min=graph_min, graph_max=graph_max)[1])),
        font=label_font,
        fill=tuple(style.label_rgb),
        stroke_fill=tuple(style.label_stroke_rgb),
        stroke_width=0,
    )
    draw_text_centered(
        draw,
        text="y",
        center=(float(_project_graph_point((0, 0), plot_bbox=plot_bbox, graph_min=graph_min, graph_max=graph_max)[0]), float(plot_bbox[1] - 25)),
        font=label_font,
        fill=tuple(style.label_rgb),
        stroke_fill=tuple(style.label_stroke_rgb),
        stroke_width=0,
    )


def _point_bbox(point_px: tuple[float, float], radius: int) -> list[float]:
    x_px, y_px = float(point_px[0]), float(point_px[1])
    return [x_px - int(radius), y_px - int(radius), x_px + int(radius), y_px + int(radius)]


def render_cartesian_point_scene(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    case: CartesianPointCase,
) -> RenderedCoordinateScene:
    """Render a Cartesian point on a coordinate grid without an origin ray."""

    width, height = _resolve_canvas(rendering_defaults)
    graph_min = int(group_default(rendering_defaults, "graph_grid_min", -12))
    graph_max = int(group_default(rendering_defaults, "graph_grid_max", 12))
    background, background_meta, style, style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        style_profile=GEOMETRY_STYLE_PROFILE_COORDINATE_GRID,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_bbox = _plot_bbox(width, height)
    _draw_coordinate_grid(draw, plot_bbox=plot_bbox, graph_min=graph_min, graph_max=graph_max, style=style)
    point_px = _project_graph_point((case.x, case.y), plot_bbox=plot_bbox, graph_min=graph_min, graph_max=graph_max)
    marker_radius = int(group_default(rendering_defaults, "marker_radius_px", 9))
    marker_color = tuple(int(value) for value in style.accent_rgb)
    draw.ellipse(tuple(_point_bbox(point_px, marker_radius)), fill=marker_color, outline=tuple(style.label_rgb), width=2)
    label_offset_x = -22 if case.x > 0 else 22
    label_offset_y = -22 if case.y <= 0 else 22
    draw_text_centered(
        draw,
        text="P",
        center=(float(point_px[0] + label_offset_x), float(point_px[1] + label_offset_y)),
        font=load_font(int(group_default(rendering_defaults, "label_font_size", 28)), bold=True),
        fill=tuple(style.label_rgb),
        stroke_fill=tuple(style.label_stroke_rgb),
        stroke_width=0,
    )
    point_value = [round(float(point_px[0]), 3), round(float(point_px[1]), 3)]
    return RenderedCoordinateScene(
        image=image,
        render_map={
            "coord_space": "pixel",
            "plot_bbox": list(plot_bbox),
            "point_p_px": point_value,
            "point_p_bbox": [round(float(value), 3) for value in _point_bbox(point_px, marker_radius)],
            "point_p_graph": [int(case.x), int(case.y)],
        },
        render_spec={
            "canvas_width": int(width),
            "canvas_height": int(height),
            "graph_min": int(graph_min),
            "graph_max": int(graph_max),
            "ray_op_visible": False,
        },
        scene_entities=[
            {
                "entity_id": "P",
                "kind": "cartesian_point",
                "graph_point": [int(case.x), int(case.y)],
                "pixel_point": point_value,
            }
        ],
        background_meta=dict(background_meta),
        style_meta=dict(style_meta),
    )


def render_polar_point_scene(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    case: PolarPointCase,
) -> RenderedCoordinateScene:
    """Render a polar point with axes, angle arc, and segment OP."""

    width, height = _resolve_canvas(rendering_defaults)
    background, background_meta, style, style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        style_profile=GEOMETRY_STYLE_PROFILE_COORDINATE_GRID,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    rng = spawn_rng(int(instance_seed), "geometry.coordinate_conversion.polar.layout")
    center = (float(width) * (0.5 + rng.uniform(-0.035, 0.035)), float(height) * (0.5 + rng.uniform(-0.035, 0.035)))
    axis_length = min(width, height) * 0.38
    axis_color = tuple(int(value) for value in style.axis_rgb)
    draw.line([(center[0] - axis_length, center[1]), (center[0] + axis_length, center[1])], fill=axis_color, width=3)
    draw.line([(center[0], center[1] + axis_length), (center[0], center[1] - axis_length)], fill=axis_color, width=3)
    radius_min = float(group_default(rendering_defaults, "polar_display_radius_min_px", 80))
    radius_max = float(group_default(rendering_defaults, "polar_display_radius_max_px", 255))
    radius_fraction = (float(case.radius) - 12.0) / max(1.0, 80.0 - 12.0)
    display_radius = radius_min + max(0.0, min(1.0, radius_fraction)) * (radius_max - radius_min)
    theta_rad = math.radians(float(case.theta_degrees))
    point_px = (
        center[0] + (display_radius * math.cos(theta_rad)),
        center[1] - (display_radius * math.sin(theta_rad)),
    )
    ray_color = tuple(int(value) for value in style.accent_rgb)
    draw.line([center, point_px], fill=ray_color, width=5)
    marker_radius = int(group_default(rendering_defaults, "marker_radius_px", 9))
    draw.ellipse(tuple(_point_bbox(point_px, marker_radius)), fill=ray_color, outline=tuple(style.label_rgb), width=2)
    label_font = load_font(int(group_default(rendering_defaults, "label_font_size", 28)), bold=True)
    draw_text_centered(
        draw,
        text="O",
        center=(center[0] - 20, center[1] + 24),
        font=label_font,
        fill=tuple(style.label_rgb),
        stroke_fill=tuple(style.label_stroke_rgb),
        stroke_width=0,
    )
    point_label_offset = (22 if math.cos(theta_rad) >= 0 else -22, -22 if math.sin(theta_rad) >= 0 else 22)
    draw_text_centered(
        draw,
        text="P",
        center=(point_px[0] + point_label_offset[0], point_px[1] + point_label_offset[1]),
        font=label_font,
        fill=tuple(style.label_rgb),
        stroke_fill=tuple(style.label_stroke_rgb),
        stroke_width=0,
    )
    readout_font = load_font(int(group_default(rendering_defaults, "readout_font_size", 24)), bold=False)
    readout_fill = tuple(int(value) for value in style.label_rgb)
    mid = ((center[0] + point_px[0]) / 2.0, (center[1] + point_px[1]) / 2.0)
    draw_text_centered(
        draw,
        text=f"r={format_number(case.radius)}",
        center=(mid[0], mid[1] - 24),
        font=readout_font,
        fill=readout_fill,
        stroke_fill=tuple(style.label_stroke_rgb),
        stroke_width=0,
    )
    arc_radius = min(70.0, max(44.0, display_radius * 0.32))
    arc_box = (center[0] - arc_radius, center[1] - arc_radius, center[0] + arc_radius, center[1] + arc_radius)
    draw.arc(arc_box, start=-float(case.theta_degrees), end=0.0, fill=ray_color, width=4)
    angle_label_theta = math.radians(float(case.theta_degrees) / 2.0)
    angle_label_radius = arc_radius + 36.0
    angle_label = (
        center[0] + angle_label_radius * math.cos(angle_label_theta),
        center[1] - angle_label_radius * math.sin(angle_label_theta),
    )
    draw_text_centered(
        draw,
        text=f"theta={format_number(case.theta_degrees)}°",
        center=angle_label,
        font=readout_font,
        fill=readout_fill,
        stroke_fill=tuple(style.label_stroke_rgb),
        stroke_width=0,
    )
    point_value = [round(float(point_px[0]), 3), round(float(point_px[1]), 3)]
    origin_value = [round(float(center[0]), 3), round(float(center[1]), 3)]
    segment_value = [origin_value, point_value]
    return RenderedCoordinateScene(
        image=image,
        render_map={
            "coord_space": "pixel",
            "origin_o_px": origin_value,
            "point_p_px": point_value,
            "point_p_bbox": [round(float(value), 3) for value in _point_bbox(point_px, marker_radius)],
            "ray_op_px": segment_value,
        },
        render_spec={
            "canvas_width": int(width),
            "canvas_height": int(height),
            "ray_op_visible": True,
            "display_radius_px": round(float(display_radius), 3),
        },
        scene_entities=[
            {
                "entity_id": "P",
                "kind": "polar_point",
                "radius": int(case.radius),
                "theta_degrees": int(case.theta_degrees),
                "pixel_point": point_value,
                "ray_op_px": segment_value,
            }
        ],
        background_meta=dict(background_meta),
        style_meta=dict(style_meta),
    )


__all__ = [
    "render_cartesian_point_scene",
    "render_polar_point_scene",
]
