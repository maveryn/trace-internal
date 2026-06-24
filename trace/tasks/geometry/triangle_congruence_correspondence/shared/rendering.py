"""Rendering primitives for triangle-congruence correspondence diagrams."""

from __future__ import annotations

import math
from typing import Any, Sequence

from PIL import ImageDraw

from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, pad_bbox
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready
from trace.tasks.geometry.shared.vector2d import add_scaled, mid, point_to_list, sub, unit
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from .construction import triangle_geometry
from .state import (
    MEASUREMENT_ALGEBRAIC_SIDE,
    MEASUREMENT_ANGLE,
    Point,
    RenderContext,
    RenderedTriangleCongruenceScene,
    Side,
    TriangleCongruenceProblem,
)


def create_render_context(
    *,
    instance_seed: int,
    params: dict[str, Any],
    render_defaults: dict[str, Any],
) -> RenderContext:
    """Create the styled canvas and fonts for one rendered sample."""

    width = int(params.get("canvas_width", render_defaults.get("canvas_width", 820)))
    height = int(params.get("canvas_height", render_defaults.get("canvas_height", 580)))
    background, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id="triangle_congruence_correspondence",
        canvas_width=width,
        canvas_height=height,
        allow_dark=False,
        require_grid=False,
    )
    readout_font_family = str(params.get("readout_font_family", render_defaults.get("readout_font_family", "roboto")))
    style_meta = dict(diagram_style_meta)
    style_meta["readout_font_family"] = readout_font_family
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
        source_fill=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        target_fill=tuple(int(value) for value in diagram_style.option_fill_rgb),
        line_width=max(2, int(params.get("line_width", render_defaults.get("line_width", 3)))),
        label_stroke_width=max(0, min(1, int(diagram_style.label_stroke_width_px))),
        font=load_font(int(params.get("label_font_size", render_defaults.get("label_font_size", 22))), bold=False, font_family=readout_font_family),
        small_font=load_font(int(params.get("small_label_font_size", render_defaults.get("small_label_font_size", 18))), bold=False, font_family=readout_font_family),
        diagram_style_meta=style_meta,
        background_meta=dict(background_meta),
    )


def _offset_from_segment(a: Point, b: Point, distance: float) -> Point:
    ux, uy = unit(sub(b, a))
    return (-uy * float(distance), ux * float(distance))


def _draw_text_centered(ctx: RenderContext, text: str, center: Point, *, small: bool = True) -> tuple[float, float, float, float]:
    font = ctx.small_font if bool(small) else ctx.font
    draw_text_traced(
        ctx.draw,
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=max(0, int(ctx.label_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    return pad_bbox(bbox, 3.0, width=ctx.width, height=ctx.height)


def _draw_polygon(ctx: RenderContext, points: Sequence[Point], *, fill: tuple[int, int, int], outline: tuple[int, int, int]) -> tuple[float, float, float, float]:
    polygon = [(float(x), float(y)) for x, y in points]
    ctx.draw.polygon(polygon, fill=fill)
    ctx.draw.line(polygon + [polygon[0]], fill=outline, width=ctx.line_width, joint="curve")
    return bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_vertex_labels(ctx: RenderContext, points: Sequence[Point], labels: Sequence[str], *, offset: float) -> dict[str, tuple[float, float, float, float]]:
    center = (sum(point[0] for point in points) / float(len(points)), sum(point[1] for point in points) / float(len(points)))
    bboxes: dict[str, tuple[float, float, float, float]] = {}
    for label, point in zip(labels, points, strict=True):
        direction = unit(sub(point, center))
        bboxes[str(label)] = _draw_text_centered(ctx, str(label), add_scaled(point, direction, offset), small=True)
    return bboxes


def _draw_tick(ctx: RenderContext, a: Point, b: Point, *, count: int = 1) -> tuple[float, float, float, float]:
    center = mid(a, b)
    tangent = unit(sub(b, a))
    normal = (-tangent[1], tangent[0])
    points: list[Point] = []
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * 9.0
        tick_center = add_scaled(center, tangent, shift)
        p0 = add_scaled(tick_center, normal, -9.0)
        p1 = add_scaled(tick_center, normal, 9.0)
        ctx.draw.line((p0, p1), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        points.extend([p0, p1])
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=3.0)


def _draw_side_label(ctx: RenderContext, points: Sequence[Point], side: Side, text: str, *, offset: float) -> tuple[float, float, float, float]:
    a = points[int(side[0])]
    b = points[int(side[1])]
    center = add_scaled(mid(a, b), _offset_from_segment(a, b, offset), 1.0)
    return _draw_text_centered(ctx, str(text), center, small=True)


def _angle_arc_points(vertex: Point, arm_a: Point, arm_b: Point, *, radius: float) -> tuple[Point, ...]:
    start = math.atan2(float(arm_a[1]) - float(vertex[1]), float(arm_a[0]) - float(vertex[0]))
    end = math.atan2(float(arm_b[1]) - float(vertex[1]), float(arm_b[0]) - float(vertex[0]))
    delta = (end - start) % (2.0 * math.pi)
    if delta > math.pi:
        delta -= 2.0 * math.pi
    steps = 18
    return tuple(
        (
            float(vertex[0]) + (math.cos(start + (delta * index / steps)) * float(radius)),
            float(vertex[1]) + (math.sin(start + (delta * index / steps)) * float(radius)),
        )
        for index in range(steps + 1)
    )


def _draw_angle_arc(
    ctx: RenderContext,
    points: Sequence[Point],
    *,
    index: int,
    label: str,
    radius: float = 34.0,
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    vertex = points[int(index)]
    arm_a = points[(int(index) - 1) % 3]
    arm_b = points[(int(index) + 1) % 3]
    arc_points = _angle_arc_points(vertex, arm_a, arm_b, radius=radius)
    ctx.draw.line(arc_points, fill=ctx.accent_color, width=max(2, ctx.line_width - 1), joint="curve")
    middle = arc_points[len(arc_points) // 2]
    direction = unit(sub(middle, vertex))
    label_bbox = _draw_text_centered(ctx, str(label), add_scaled(vertex, direction, radius + 24.0), small=True)
    return bbox_from_points(arc_points, width=ctx.width, height=ctx.height, pad=3.0), label_bbox


def render_triangle_congruence_scene(ctx: RenderContext, problem: TriangleCongruenceProblem) -> RenderedTriangleCongruenceScene:
    """Render triangles after a public task has selected a concrete case."""

    case = problem.case
    geometry = triangle_geometry(case, width=ctx.width, height=ctx.height, instance_seed=problem.layout_seed)
    construction_bboxes: dict[str, tuple[float, float, float, float]] = {}
    readout_bboxes: dict[str, tuple[float, float, float, float]] = {}
    point_label_bboxes: dict[str, tuple[float, float, float, float]] = {}

    if case.layout_kind == "overlap":
        construction_bboxes["target_triangle"] = _draw_polygon(ctx, geometry.target_vertices, fill=ctx.target_fill, outline=ctx.secondary_color)
        construction_bboxes["source_triangle"] = _draw_polygon(ctx, geometry.source_vertices, fill=ctx.source_fill, outline=ctx.line_color)
    else:
        construction_bboxes["source_triangle"] = _draw_polygon(ctx, geometry.source_vertices, fill=ctx.source_fill, outline=ctx.line_color)
        construction_bboxes["target_triangle"] = _draw_polygon(ctx, geometry.target_vertices, fill=ctx.target_fill, outline=ctx.secondary_color)

    point_label_bboxes.update(_draw_vertex_labels(ctx, geometry.source_vertices, geometry.source_labels, offset=24.0))
    point_label_bboxes.update(_draw_vertex_labels(ctx, geometry.target_vertices, geometry.target_labels, offset=27.0))
    if case.show_statement:
        readout_bboxes["congruence_statement"] = _draw_text_centered(ctx, geometry.statement, (ctx.width / 2.0, 56.0), small=True)

    if case.measurement_family == MEASUREMENT_ANGLE:
        source_arc, source_label = _draw_angle_arc(ctx, geometry.source_vertices, index=case.source_angle_index, label=f"{case.source_angle_value}\N{DEGREE SIGN}")
        target_arc, target_label = _draw_angle_arc(ctx, geometry.target_vertices, index=case.target_angle_index, label="?")
        construction_bboxes["source_angle_arc"] = source_arc
        construction_bboxes["target_angle_arc"] = target_arc
        readout_bboxes["source_angle_label"] = source_label
        readout_bboxes["target_angle_label"] = target_label
    else:
        source_text = str(case.source_target_expression if case.source_target_expression is not None else case.source_target_side_value)
        readout_bboxes["source_target_side_label"] = _draw_side_label(ctx, geometry.source_vertices, case.source_side, source_text, offset=-28.0)
        readout_bboxes["target_target_side_label"] = _draw_side_label(ctx, geometry.target_vertices, case.target_side, "?", offset=32.0)
        construction_bboxes["source_target_side_tick"] = _draw_tick(ctx, geometry.source_vertices[case.source_side[0]], geometry.source_vertices[case.source_side[1]], count=1)
        construction_bboxes["target_target_side_tick"] = _draw_tick(ctx, geometry.target_vertices[case.target_side[0]], geometry.target_vertices[case.target_side[1]], count=1)
        if case.measurement_family == MEASUREMENT_ALGEBRAIC_SIDE:
            readout_bboxes["source_support_side_label"] = _draw_side_label(ctx, geometry.source_vertices, case.support_side, str(case.source_support_expression), offset=30.0)
            readout_bboxes["target_support_side_label"] = _draw_side_label(ctx, geometry.target_vertices, case.support_side, str(case.target_support_expression), offset=-34.0)
            construction_bboxes["source_support_side_tick"] = _draw_tick(ctx, geometry.source_vertices[case.support_side[0]], geometry.source_vertices[case.support_side[1]], count=2)
            construction_bboxes["target_support_side_tick"] = _draw_tick(ctx, geometry.target_vertices[case.support_side[0]], geometry.target_vertices[case.support_side[1]], count=2)
        elif case.show_statement:
            construction_bboxes["source_support_side_tick"] = _draw_tick(ctx, geometry.source_vertices[case.support_side[0]], geometry.source_vertices[case.support_side[1]], count=2)
            construction_bboxes["target_support_side_tick"] = _draw_tick(ctx, geometry.target_vertices[case.support_side[0]], geometry.target_vertices[case.support_side[1]], count=2)

    annotation_points = {
        **{label: point for label, point in zip(geometry.source_labels, geometry.source_vertices, strict=True)},
        **{label: point for label, point in zip(geometry.target_labels, geometry.target_vertices, strict=True)},
    }
    render_map = {
        "source_vertices": {label: point_to_list(point) for label, point in zip(geometry.source_labels, geometry.source_vertices, strict=True)},
        "target_vertices": {label: point_to_list(point) for label, point in zip(geometry.target_labels, geometry.target_vertices, strict=True)},
        "point_label_bboxes": geometry_json_ready(point_label_bboxes),
        "readout_bboxes": geometry_json_ready(readout_bboxes),
        "construction_bboxes": geometry_json_ready(construction_bboxes),
    }
    return RenderedTriangleCongruenceScene(
        image=ctx.image,
        geometry=geometry,
        annotation_keyed_points=annotation_points,
        point_label_bboxes=point_label_bboxes,
        readout_bboxes=readout_bboxes,
        construction_bboxes=construction_bboxes,
        render_map=render_map,
    )


__all__ = ["create_render_context", "render_triangle_congruence_scene"]
