"""Rendering primitives for graph-paper geometry scenes."""

from __future__ import annotations

from math import atan2, cos, degrees, radians, sin
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.tasks.shared.text_rendering import load_font

from .defaults import int_default
from .state import BBox, Color, GraphObject, GraphPaperContext, Point

LIGHT_THEMES: tuple[tuple[Color, Color, Color, Color, Color], ...] = (
    ((250, 252, 255), (216, 226, 238), (118, 132, 150), (30, 52, 76), (19, 29, 43)),
    ((252, 251, 246), (224, 218, 204), (142, 127, 104), (52, 57, 66), (25, 28, 34)),
    ((247, 252, 249), (209, 229, 218), (105, 143, 125), (35, 69, 66), (20, 37, 35)),
)


def make_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    theme_index: int = 0,
) -> GraphPaperContext:
    """Create a graph-paper canvas with one bounded coordinate frame."""

    canvas_size = int_default(params, defaults, "canvas_size", 768)
    graph_min = int_default(params, defaults, "graph_cells_min", 14)
    graph_max = int_default(params, defaults, "graph_cells_max", 20)
    graph_cells = max(
        8,
        min(
            24,
            graph_min + (abs(int(instance_seed)) % max(1, graph_max - graph_min + 1)),
        ),
    )
    margin = int_default(params, defaults, "margin_px", 56)
    panel_box = (
        float(margin),
        float(margin),
        float(canvas_size - margin),
        float(canvas_size - margin),
    )
    content_pad = int_default(params, defaults, "content_pad_px", 18)
    content_box = (
        panel_box[0] + content_pad,
        panel_box[1] + content_pad,
        panel_box[2] - content_pad,
        panel_box[3] - content_pad,
    )
    spacing = min(
        (content_box[2] - content_box[0]) / float(graph_cells),
        (content_box[3] - content_box[1]) / float(graph_cells),
    )
    half_range = int(graph_cells // 2)
    origin = (
        (content_box[0] + content_box[2]) / 2.0,
        (content_box[1] + content_box[3]) / 2.0,
    )
    background, grid, axis, ink, label = LIGHT_THEMES[
        int(theme_index) % len(LIGHT_THEMES)
    ]
    image = Image.new("RGB", (canvas_size, canvas_size), background)
    draw = ImageDraw.Draw(image)
    for index in range(-half_range, half_range + 1):
        x = origin[0] + index * spacing
        y = origin[1] - index * spacing
        draw.line([(x, content_box[1]), (x, content_box[3])], fill=grid, width=1)
        draw.line([(content_box[0], y), (content_box[2], y)], fill=grid, width=1)
    draw.rectangle(panel_box, outline=axis, width=2)
    draw.line(
        [(content_box[0], origin[1]), (content_box[2], origin[1])], fill=axis, width=2
    )
    draw.line(
        [(origin[0], content_box[1]), (origin[0], content_box[3])], fill=axis, width=2
    )
    tick_font = load_font(14, bold=False)
    for value in range(-half_range, half_range + 1, 2):
        x = origin[0] + value * spacing
        y = origin[1] - value * spacing
        draw.text((x - 4, origin[1] + 5), str(value), fill=label, font=tick_font)
        if value != 0:
            draw.text((origin[0] + 5, y - 7), str(value), fill=label, font=tick_font)
    return GraphPaperContext(
        image=image,
        draw=draw,
        canvas_size=int(canvas_size),
        graph_cells=int(graph_cells),
        panel_box=panel_box,
        content_box=content_box,
        origin_px=origin,
        spacing_px=float(spacing),
        graph_half_range=int(half_range),
        ink_color=ink,
        accent_color=(194, 57, 52),
        grid_color=grid,
        axis_color=axis,
        label_color=label,
        background_meta={
            "selected_style": "graph_paper_panel",
            "theme_index": int(theme_index) % len(LIGHT_THEMES),
            "kind": "bounded_graph_paper",
        },
        post_noise_meta={"enabled": False},
    )


def project(ctx: GraphPaperContext, point: Point) -> Point:
    """Project graph-unit coordinates into final image pixels."""

    return (
        float(ctx.origin_px[0]) + float(point[0]) * float(ctx.spacing_px),
        float(ctx.origin_px[1]) - float(point[1]) * float(ctx.spacing_px),
    )


def graph_bbox(
    ctx: GraphPaperContext, points: Sequence[Point], *, pad_px: float = 8.0
) -> BBox:
    """Return a padded pixel bbox around graph-unit points."""

    projected = [project(ctx, point) for point in points]
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    return (min(xs) - pad_px, min(ys) - pad_px, max(xs) + pad_px, max(ys) + pad_px)


def pixel_bbox(points: Sequence[Point], *, pad_px: float = 8.0) -> BBox:
    """Return a padded pixel bbox around already projected points."""

    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (min(xs) - pad_px, min(ys) - pad_px, max(xs) + pad_px, max(ys) + pad_px)


def draw_label(
    ctx: GraphPaperContext, text: str, point: Point, *, anchor: str = "mm"
) -> None:
    """Draw one compact object label near a rendered object."""

    font = load_font(22, bold=True)
    x, y = float(point[0]), float(point[1])
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    if anchor == "mm":
        loc = (x - width / 2.0, y - height / 2.0)
    elif anchor == "above":
        loc = (x - width / 2.0, y - height - 8)
    else:
        loc = (x + 6, y - height / 2.0)
    ctx.draw.text(loc, str(text), fill=ctx.label_color, font=font)


def draw_point_marker(
    ctx: GraphPaperContext, label: str, point: Point, *, color: Color | None = None
) -> Point:
    """Draw one labeled graph point and return its projected pixel point."""

    px = project(ctx, point)
    stroke = color or ctx.accent_color
    radius = 5
    ctx.draw.ellipse(
        (px[0] - radius, px[1] - radius, px[0] + radius, px[1] + radius), fill=stroke
    )
    draw_label(ctx, label, (px[0] + 14, px[1] - 12), anchor="left")
    return px


def draw_segment(
    ctx: GraphPaperContext,
    label: str,
    start: Point,
    end: Point,
    *,
    color: Color | None = None,
) -> GraphObject:
    """Draw a labeled line segment and return its rendered object record."""

    start_px = project(ctx, start)
    end_px = project(ctx, end)
    stroke = color or ctx.ink_color
    ctx.draw.line([start_px, end_px], fill=stroke, width=4)
    mid = ((start_px[0] + end_px[0]) / 2.0, (start_px[1] + end_px[1]) / 2.0)
    if str(label):
        draw_label(ctx, label, (mid[0], mid[1] - 18), anchor="mm")
    return GraphObject(
        label=str(label),
        kind="segment",
        points_px=(start_px, end_px),
        bbox_px=pixel_bbox((start_px, end_px), pad_px=10),
        metric_value=0.0,
        class_name="segment",
        graph_points=(start, end),
    )


def angle_points(
    center: Point, degrees: float, *, radius: float = 2.8
) -> tuple[Point, Point, Point]:
    """Return endpoint-center-endpoint graph points for one angle."""

    left = radians(180.0)
    right = radians(180.0 - float(degrees))
    first = (
        float(center[0]) + radius * cos(left),
        float(center[1]) + radius * sin(left),
    )
    second = (
        float(center[0]) + radius * cos(right),
        float(center[1]) + radius * sin(right),
    )
    return first, center, second


def draw_angle(
    ctx: GraphPaperContext,
    label: str,
    points: Sequence[Point],
    *,
    color: Color | None = None,
) -> GraphObject:
    """Draw one labeled angle from graph points ordered endpoint, vertex, endpoint."""

    endpoint_a, vertex, endpoint_b = tuple(points)
    px_a, px_v, px_b = (
        project(ctx, endpoint_a),
        project(ctx, vertex),
        project(ctx, endpoint_b),
    )
    stroke = color or ctx.ink_color
    ctx.draw.line([px_v, px_a], fill=stroke, width=4)
    ctx.draw.line([px_v, px_b], fill=stroke, width=4)
    angle_a = degrees(atan2(px_a[1] - px_v[1], px_a[0] - px_v[0]))
    angle_b = degrees(atan2(px_b[1] - px_v[1], px_b[0] - px_v[0]))
    while angle_b < angle_a:
        angle_b += 360.0
    if angle_b - angle_a > 180.0:
        angle_a, angle_b = angle_b, angle_a + 360.0
    ctx.draw.arc(
        (px_v[0] - 28, px_v[1] - 28, px_v[0] + 28, px_v[1] + 28),
        start=float(angle_a),
        end=float(angle_b),
        fill=stroke,
        width=3,
    )
    if str(label):
        draw_label(ctx, label, (px_v[0], px_v[1] - 34), anchor="mm")
    return GraphObject(
        label=str(label),
        kind="angle",
        points_px=(px_a, px_v, px_b),
        bbox_px=pixel_bbox((px_a, px_v, px_b), pad_px=14),
        metric_value=0.0,
        class_name="angle",
        graph_points=(endpoint_a, vertex, endpoint_b),
    )


def draw_polygon(
    ctx: GraphPaperContext,
    label: str,
    points: Sequence[Point],
    *,
    class_name: str = "polygon",
    color: Color | None = None,
    fill: Color | None = None,
) -> GraphObject:
    """Draw one labeled polygon."""

    pts = tuple(project(ctx, point) for point in points)
    ctx.draw.polygon(pts, fill=fill or (235, 241, 248), outline=color or ctx.ink_color)
    ctx.draw.line([*pts, pts[0]], fill=color or ctx.ink_color, width=4)
    bbox = pixel_bbox(pts, pad_px=8)
    if str(label):
        draw_label(ctx, label, ((bbox[0] + bbox[2]) / 2.0, bbox[1] - 16), anchor="mm")
    return GraphObject(
        label=str(label),
        kind="polygon",
        points_px=pts,
        bbox_px=bbox,
        metric_value=0.0,
        class_name=str(class_name),
        graph_points=tuple(points),
    )


def draw_ellipse_or_circle(
    ctx: GraphPaperContext,
    label: str,
    center: Point,
    radius_x: float,
    radius_y: float,
    *,
    class_name: str,
    color: Color | None = None,
) -> GraphObject:
    """Draw one labeled circle or ellipse with graph-unit radii."""

    center_px = project(ctx, center)
    rx = float(radius_x) * float(ctx.spacing_px)
    ry = float(radius_y) * float(ctx.spacing_px)
    bbox = (center_px[0] - rx, center_px[1] - ry, center_px[0] + rx, center_px[1] + ry)
    ctx.draw.ellipse(
        bbox, outline=color or ctx.ink_color, width=4, fill=(236, 244, 249)
    )
    if str(label):
        draw_label(ctx, label, (center_px[0], bbox[1] - 16), anchor="mm")
    return GraphObject(
        label=str(label),
        kind=str(class_name),
        points_px=(center_px,),
        bbox_px=bbox,
        metric_value=0.0,
        class_name=str(class_name),
        graph_points=(center,),
        extra={"radius_x": float(radius_x), "radius_y": float(radius_y)},
    )


def slot_centers(ctx: GraphPaperContext, count: int) -> list[Point]:
    """Return graph-unit slot centers for multi-object scenes."""

    cols = 3 if int(count) > 4 else 2
    rows = (int(count) + cols - 1) // cols
    x_values = [-(cols - 1) * 3.2 / 2.0 + index * 3.2 for index in range(cols)]
    y_values = [(rows - 1) * 3.0 / 2.0 - index * 3.0 for index in range(rows)]
    centers: list[Point] = []
    for y in y_values:
        for x in x_values:
            centers.append((float(x), float(y)))
            if len(centers) == int(count):
                return centers
    return centers


def render_metadata(ctx: GraphPaperContext) -> dict[str, Any]:
    """Build graph-paper render metadata for trace payloads."""

    return {
        "canvas_size": [int(ctx.canvas_size), int(ctx.canvas_size)],
        "coord_space": "pixel",
        "scene_bbox_px": [round(float(v), 3) for v in ctx.panel_box],
        "layout_placement": {
            "mode": "fractional_free_area",
            "origin_fraction_x": 0.5,
            "origin_fraction_y": 0.5,
        },
        "background_style": dict(ctx.background_meta),
        "post_image_noise": dict(ctx.post_noise_meta),
        "text_style": {"draw_object_labels": True},
        "graph_cells": int(ctx.graph_cells),
        "graph_panel_bbox_px": [round(float(v), 3) for v in ctx.panel_box],
        "graph_content_bbox_px": [round(float(v), 3) for v in ctx.content_box],
        "graph_origin_px": [round(float(v), 3) for v in ctx.origin_px],
        "graph_coordinate_frame": {
            "origin_pixel": [round(float(v), 3) for v in ctx.origin_px],
            "spacing_px": round(float(ctx.spacing_px), 3),
            "x_positive": "right",
            "y_positive": "up",
        },
        "graph_paper_grid": {
            "spacing_px": round(float(ctx.spacing_px), 3),
            "cells_per_side": int(ctx.graph_cells),
        },
    }
