"""Rendering primitives for right-triangle altitude theorem diagrams."""

from __future__ import annotations

import math
from typing import Any, Mapping

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, pad_bbox
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import add_scaled, mid, point_to_list, sub, unit
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from .defaults import SCENE_ID
from .state import BBox, Point, RenderContext, RenderedRightTriangleAltitudeScene, RightTriangleAltitudeProblem, SceneGeometry, TheoremValues


def create_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> RenderContext:
    """Create a styled non-grid geometry canvas for this scene."""

    width = int(params.get("canvas_width", rendering_defaults.get("canvas_width", 820)))
    height = int(params.get("canvas_height", rendering_defaults.get("canvas_height", 580)))
    background, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        allow_dark=False,
        require_grid=False,
    )
    readout_font_family = str(params.get("readout_font_family", rendering_defaults.get("readout_font_family", "roboto")))
    diagram_style_trace = dict(diagram_style_meta)
    diagram_style_trace["readout_font_family"] = readout_font_family
    image = background.convert("RGB")
    return RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=width,
        height=height,
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        fill_color=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        line_width=max(2, int(params.get("line_width", rendering_defaults.get("line_width", 3)))),
        label_stroke_width=max(0, min(1, int(diagram_style.label_stroke_width_px))),
        font=load_font(
            int(params.get("label_font_size", rendering_defaults.get("label_font_size", 22))),
            bold=False,
            font_family=readout_font_family,
        ),
        small_font=load_font(
            int(params.get("small_label_font_size", rendering_defaults.get("small_label_font_size", 18))),
            bold=False,
            font_family=readout_font_family,
        ),
        diagram_style_meta=diagram_style_trace,
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_transform"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _normal_away_from(start: Point, end: Point, reference: Point, distance: float) -> Point:
    direction = unit(sub(end, start))
    normal = (-direction[1], direction[0])
    midpoint = mid(start, end)
    candidate = add_scaled(midpoint, normal, distance)
    if math.hypot(candidate[0] - reference[0], candidate[1] - reference[1]) < math.hypot(
        midpoint[0] - reference[0],
        midpoint[1] - reference[1],
    ):
        normal = (-normal[0], -normal[1])
    return (normal[0] * float(distance), normal[1] * float(distance))


def _draw_text_centered(ctx: RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    stroke_width = max(0, int(ctx.label_stroke_width))
    draw_text_traced(
        ctx.draw,
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    bbox = ctx.draw.textbbox((float(center[0]), float(center[1])), str(text), anchor="mm", font=font, stroke_width=stroke_width)
    return pad_bbox(bbox, 3.0, width=ctx.width, height=ctx.height)


def _draw_segment_label(
    ctx: RenderContext,
    start: Point,
    end: Point,
    text: str,
    *,
    reference: Point,
    distance: float,
    toward_reference: bool = False,
) -> BBox:
    offset = _normal_away_from(start, end, reference, abs(float(distance)))
    if bool(toward_reference):
        offset = (-offset[0], -offset[1])
    return _draw_text_centered(ctx, str(text), add_scaled(mid(start, end), offset), small=True)


def _draw_dimension_line(
    ctx: RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    reference: Point,
    distance: float,
) -> BBox:
    offset = _normal_away_from(start, end, reference, abs(float(distance)))
    p0 = add_scaled(start, offset)
    p1 = add_scaled(end, offset)
    stroke = max(1, ctx.line_width - 1)
    ctx.draw.line((p0, p1), fill=ctx.label_color, width=stroke)
    direction = unit(sub(end, start))
    normal = (-direction[1], direction[0])
    for point in (p0, p1):
        ctx.draw.line((add_scaled(point, normal, -7.0), add_scaled(point, normal, 7.0)), fill=ctx.label_color, width=stroke)
    label_bbox = _draw_text_centered(ctx, str(label), add_scaled(mid(p0, p1), (offset[0] * 0.22, offset[1] * 0.22)), small=True)
    return bbox_from_points(
        (p0, p1, (label_bbox[0], label_bbox[1]), (label_bbox[2], label_bbox[3])),
        width=ctx.width,
        height=ctx.height,
        pad=8.0,
    )


def _draw_right_angle_marker(ctx: RenderContext, vertex: Point, arm_a: Point, arm_b: Point, *, size: float) -> BBox:
    unit_a = unit(sub(arm_a, vertex))
    unit_b = unit(sub(arm_b, vertex))
    p1 = add_scaled(vertex, unit_a, size)
    p2 = add_scaled(p1, unit_b, size)
    p3 = add_scaled(vertex, unit_b, size)
    ctx.draw.line((p1, p2, p3), fill=ctx.accent_color, width=max(2, ctx.line_width - 1), joint="curve")
    return bbox_from_points((p1, p2, p3), width=ctx.width, height=ctx.height, pad=3.0)


def _base_scene_geometry(values: TheoremValues, *, width: int, height: int, instance_seed: int) -> SceneGeometry:
    rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.layout")
    hypotenuse = float(values.hypotenuse)
    left_projection = float(values.left_projection)
    altitude = float(values.altitude)
    local = {
        "B": (0.0, 0.0),
        "D": (left_projection, 0.0),
        "C": (hypotenuse, 0.0),
        "A": (left_projection, -altitude),
    }
    min_x = min(point[0] for point in local.values())
    max_x = max(point[0] for point in local.values())
    min_y = min(point[1] for point in local.values())
    max_y = max(point[1] for point in local.values())
    scale = min((float(width) * 0.62) / max(1.0, max_x - min_x), (float(height) * 0.46) / max(1.0, max_y - min_y))
    angle = rng.uniform(-0.055, 0.055)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    center_local = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    center_canvas = (
        float(width) / 2.0 + rng.uniform(-18.0, 18.0),
        float(height) * 0.58 + rng.uniform(-12.0, 10.0),
    )
    points: dict[str, Point] = {}
    for label, point in local.items():
        x = (float(point[0]) - center_local[0]) * scale
        y = (float(point[1]) - center_local[1]) * scale
        points[str(label)] = (
            center_canvas[0] + (x * cos_a - y * sin_a),
            center_canvas[1] + (x * sin_a + y * cos_a),
        )
    return SceneGeometry(points=points, labels={"A": "A", "B": "B", "C": "C", "D": "D"})


def _draw_vertex_labels(ctx: RenderContext, points: Mapping[str, Point]) -> dict[str, BBox]:
    centroid = (
        sum(point[0] for point in points.values()) / float(len(points)),
        sum(point[1] for point in points.values()) / float(len(points)),
    )
    bboxes: dict[str, BBox] = {}
    for label, point in points.items():
        direction = unit(sub(point, centroid))
        bboxes[str(label)] = _draw_text_centered(ctx, str(label), add_scaled(point, direction, 24.0), small=True)
    return bboxes


def _draw_measurement_labels(ctx: RenderContext, problem: RightTriangleAltitudeProblem, points: Mapping[str, Point]) -> dict[str, BBox]:
    bboxes: dict[str, BBox] = {}
    a, b, c, d = points["A"], points["B"], points["C"], points["D"]
    labels = dict(problem.visible_labels)
    if "left_projection" in labels:
        bboxes["left_projection_label"] = _draw_segment_label(ctx, b, d, labels["left_projection"], reference=a, distance=27.0, toward_reference=True)
    if "right_projection" in labels:
        bboxes["right_projection_label"] = _draw_segment_label(ctx, d, c, labels["right_projection"], reference=a, distance=27.0, toward_reference=True)
    if "hypotenuse" in labels:
        bboxes["hypotenuse_label"] = _draw_dimension_line(ctx, b, c, labels["hypotenuse"], reference=a, distance=46.0)
    if "altitude" in labels:
        bboxes["altitude_label"] = _draw_segment_label(ctx, a, d, labels["altitude"], reference=b, distance=32.0)
    if "left_leg" in labels:
        bboxes["left_leg_label"] = _draw_segment_label(ctx, a, b, labels["left_leg"], reference=d, distance=31.0)
    if "right_leg" in labels:
        bboxes["right_leg_label"] = _draw_segment_label(ctx, a, c, labels["right_leg"], reference=d, distance=31.0)
    return bboxes


def render_right_triangle_altitude_scene(
    ctx: RenderContext,
    problem: RightTriangleAltitudeProblem,
) -> RenderedRightTriangleAltitudeScene:
    """Render a right triangle with altitude-to-hypotenuse construction."""

    base_geometry = _base_scene_geometry(problem.values, width=ctx.width, height=ctx.height, instance_seed=problem.layout_seed)
    transform = ctx.scene_transform.resolve(tuple(base_geometry.points.values()))
    points = {key: transform.point(point) for key, point in base_geometry.points.items()}
    geometry = SceneGeometry(points=points, labels=dict(base_geometry.labels))
    a, b, c, d = points["A"], points["B"], points["C"], points["D"]

    construction_bboxes: dict[str, BBox] = {}
    triangle_points = (a, b, c)
    ctx.draw.polygon(triangle_points, fill=ctx.fill_color)
    ctx.draw.line((a, b, c, a), fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ctx.draw.line((a, d), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    construction_bboxes["right_triangle"] = bbox_from_points(triangle_points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 3)
    construction_bboxes["altitude"] = bbox_from_points((a, d), width=ctx.width, height=ctx.height, pad=ctx.line_width + 3)
    construction_bboxes["right_angle_marker"] = _draw_right_angle_marker(ctx, a, b, c, size=18.0)
    construction_bboxes["altitude_foot_marker"] = _draw_right_angle_marker(ctx, d, a, c, size=16.0)
    point_label_bboxes = _draw_vertex_labels(ctx, points)
    readout_bboxes = _draw_measurement_labels(ctx, problem, points)
    render_map = {
        "points": {key: point_to_list(point) for key, point in points.items()},
        "point_label_bboxes": geometry_json_ready(point_label_bboxes),
        "readout_bboxes": geometry_json_ready(readout_bboxes),
        "construction_bboxes": geometry_json_ready(construction_bboxes),
    }
    return RenderedRightTriangleAltitudeScene(
        image=ctx.image,
        geometry=geometry,
        annotation_points=dict(points),
        point_label_bboxes=point_label_bboxes,
        readout_bboxes=readout_bboxes,
        construction_bboxes=construction_bboxes,
        render_map=render_map,
    )


__all__ = ["create_render_context", "render_right_triangle_altitude_scene"]
