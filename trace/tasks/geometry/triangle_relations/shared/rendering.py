"""Rendering primitives for triangle-relations analytical diagrams."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import (
    geometry_diagram_style_metadata,
    prepare_geometry_diagram_style_and_background,
)
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    draw_readout_centered,
)
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import add_scaled, mid, mul, perp, point_to_list, sub, unit
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from trace.tasks.shared.text_rendering import load_font

from .state import (
    DOMAIN,
    SCENE_ID,
    AngleLabel,
    Point,
    RenderContext,
    RenderedTriangleRelationsScene,
    RightAngleMark,
    SegmentLabel,
    TickGroup,
    TriangleRelationsProblem,
)


def create_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> RenderContext:
    """Create a styled analytical-diagram render context for this scene."""

    rng = spawn_rng(int(instance_seed), f"{DOMAIN}.{SCENE_ID}.render")
    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 580)))
    image, background_meta, diagram_style, diagram_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=True,
        require_grid=False,
        style_profile="analytical_diagram",
    )
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"geometry.{SCENE_ID}.font_family",
        params=params,
    )
    font_record = get_font_family_record(str(font_family))
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 3)))
    label_stroke_width = int(params.get("label_stroke_width", group_default(render_defaults, "label_stroke_width", 1)))
    diagram_meta = {
        **geometry_diagram_style_metadata(diagram_style),
        **dict(diagram_meta),
        "font_family": font_record.to_trace(),
        "font_asset_version": font_asset_version(),
    }
    rgb_image = image.convert("RGB")
    return RenderContext(
        rng=rng,
        image=rgb_image,
        draw=ImageDraw.Draw(rgb_image),
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        fill_color=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        alt_fill_color=tuple(int(value) for value in diagram_style.option_fill_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, min(1, int(label_stroke_width))),
        font=load_font(max(12, int(font_size)), bold=False, font_family=str(font_family)),
        small_font=load_font(max(10, int(small_font_size)), bold=False, font_family=str(font_family)),
        diagram_style_meta=diagram_meta,
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            rng,
            params=params,
            render_defaults=render_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _draw_line(ctx: RenderContext, points: Sequence[Point], *, color: tuple[int, int, int] | None = None, width: int | None = None) -> tuple[float, float, float, float]:
    ctx.draw.line(list(points), fill=color or ctx.line_color, width=int(width or ctx.line_width), joint="curve")
    return bbox_from_points(tuple(points), width=ctx.width, height=ctx.height, pad=float(width or ctx.line_width) + 3.0)


def _draw_polygon(ctx: RenderContext, points: Sequence[Point], *, fill: tuple[int, int, int] | None = None) -> tuple[float, float, float, float]:
    if fill is not None:
        ctx.draw.polygon(list(points), fill=fill)
    return _draw_line(ctx, tuple(points) + (tuple(points)[0],))


def _label_offset_center(a: Point, b: Point, offset: float) -> Point:
    direction = unit(sub(b, a))
    return add_scaled(mid(a, b), perp(direction), float(offset))


def _draw_segment_label(ctx: RenderContext, points: Mapping[str, Point], label: SegmentLabel) -> tuple[float, float, float, float]:
    a = points[str(label.segment[0])]
    b = points[str(label.segment[1])]
    return draw_readout_centered(ctx, str(label.text), _label_offset_center(a, b, label.offset), small=True, backed=False)


def _angle_points(vertex: Point, arm_a: Point, arm_b: Point, radius: float) -> tuple[Point, ...]:
    start = math.atan2(float(arm_a[1]) - float(vertex[1]), float(arm_a[0]) - float(vertex[0]))
    end = math.atan2(float(arm_b[1]) - float(vertex[1]), float(arm_b[0]) - float(vertex[0]))
    delta = (end - start + math.pi) % (2.0 * math.pi) - math.pi
    steps = max(10, int(abs(delta) / math.radians(8.0)))
    return tuple(
        (
            float(vertex[0]) + math.cos(start + delta * (idx / steps)) * float(radius),
            float(vertex[1]) + math.sin(start + delta * (idx / steps)) * float(radius),
        )
        for idx in range(steps + 1)
    )


def _draw_angle(ctx: RenderContext, points: Mapping[str, Point], angle: AngleLabel) -> tuple[float, float, float, float]:
    vertex = points[str(angle.vertex)]
    arm_a = points[str(angle.arm_a)]
    arm_b = points[str(angle.arm_b)]
    arc = _angle_points(vertex, arm_a, arm_b, max(24.0, float(angle.radius)))
    arc_bbox = _draw_line(ctx, arc, color=ctx.accent_color, width=max(2, ctx.line_width - 1))
    if not str(angle.text):
        return arc_bbox
    direction = unit(add_scaled(unit(sub(arm_a, vertex)), unit(sub(arm_b, vertex)), 1.0))
    if math.hypot(direction[0], direction[1]) <= 1e-6:
        direction = perp(unit(sub(arm_a, vertex)))
    text_bbox = draw_readout_centered(ctx, str(angle.text), add_scaled(vertex, direction, float(angle.radius) + 24.0), small=True, backed=False)
    return bbox_from_points(((arc_bbox[0], arc_bbox[1]), (arc_bbox[2], arc_bbox[3]), (text_bbox[0], text_bbox[1]), (text_bbox[2], text_bbox[3])), width=ctx.width, height=ctx.height, pad=2.0)


def _draw_right_angle(ctx: RenderContext, points: Mapping[str, Point], mark: RightAngleMark) -> tuple[float, float, float, float]:
    vertex = points[str(mark.vertex)]
    u = unit(sub(points[str(mark.arm_a)], vertex))
    v = unit(sub(points[str(mark.arm_b)], vertex))
    size = 22.0
    p1 = add_scaled(vertex, u, size)
    p2 = add_scaled(p1, v, size)
    p3 = add_scaled(vertex, v, size)
    return _draw_line(ctx, (p1, p2, p3), color=ctx.accent_color, width=max(2, ctx.line_width - 1))


def _draw_tick_group(ctx: RenderContext, points: Mapping[str, Point], group: TickGroup) -> tuple[float, float, float, float]:
    """Draw equal/parallel marks; angle-bisector groups are already shown by arcs."""

    if str(group.kind) == "angle_bisector" or int(group.count) <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    tick_points: list[Point] = []
    for a_label, b_label in group.segments:
        a = points[str(a_label)]
        b = points[str(b_label)]
        tangent = unit(sub(b, a))
        normal = perp(tangent)
        center = mid(a, b)
        for idx in range(int(group.count)):
            shift = (idx - (int(group.count) - 1) / 2.0) * 11.0
            tick_center = add_scaled(center, tangent, shift)
            p0 = add_scaled(tick_center, normal, -9.0)
            p1 = add_scaled(tick_center, normal, 9.0)
            _draw_line(ctx, (p0, p1), color=ctx.accent_color, width=max(2, ctx.line_width - 1))
            tick_points.extend((p0, p1))
    return bbox_from_points(tuple(tick_points), width=ctx.width, height=ctx.height, pad=5.0) if tick_points else (0.0, 0.0, 0.0, 0.0)


def _draw_point_labels(ctx: RenderContext, points: Mapping[str, Point]) -> dict[str, list[float]]:
    bboxes: dict[str, list[float]] = {}
    for label, point in points.items():
        x, y = float(point[0]), float(point[1])
        if y > ctx.height * 0.68:
            offset = (0.0, 22.0)
        elif y < ctx.height * 0.24:
            offset = (0.0, -22.0)
        elif x < ctx.width * 0.35:
            offset = (-22.0, 0.0)
        else:
            offset = (22.0, 0.0)
        bbox = draw_readout_centered(ctx, str(label), (x + offset[0], y + offset[1]), small=True, backed=False, required=False)
        bboxes[str(label)] = bbox_to_list(bbox)
    return bboxes


def render_triangle_relations_scene(
    ctx: RenderContext,
    problem: TriangleRelationsProblem,
) -> RenderedTriangleRelationsScene:
    """Render one resolved construction and project witnesses after transform."""

    case = problem.case
    source_points = tuple(case.vertices.values())
    ctx.scene_transform.resolve(source_points)
    points = ctx.scene_transform.keyed_points(case.vertices)
    polygon_bboxes: dict[str, Any] = {}
    for polygon in case.filled_polygons:
        polygon_bboxes["filled_" + "_".join(polygon)] = bbox_to_list(_draw_polygon(ctx, [points[label] for label in polygon], fill=ctx.fill_color))
    for polygon in case.polygons:
        polygon_bboxes["_".join(polygon)] = bbox_to_list(_draw_polygon(ctx, [points[label] for label in polygon]))
    edge_bboxes = {
        f"{a}{b}": bbox_to_list(_draw_line(ctx, (points[a], points[b]), color=ctx.line_color))
        for a, b in case.edges
    }
    label_bboxes = {label.role or "".join(label.segment): bbox_to_list(_draw_segment_label(ctx, points, label)) for label in case.segment_labels}
    angle_bboxes = {
        angle.role or f"{angle.arm_a}{angle.vertex}{angle.arm_b}": bbox_to_list(_draw_angle(ctx, points, angle))
        for angle in case.angle_labels
    }
    right_angle_bboxes = {mark.vertex: bbox_to_list(_draw_right_angle(ctx, points, mark)) for mark in case.right_angles}
    tick_bboxes = {
        f"{group.kind}_{idx}": bbox_to_list(_draw_tick_group(ctx, points, group))
        for idx, group in enumerate(case.tick_groups)
    }
    point_label_bboxes = _draw_point_labels(ctx, points)
    annotation_segment = None
    annotation_point = None
    annotation_points: dict[str, Point] = {}
    roles: tuple[str, ...] = ()
    if problem.annotation_mode == "segment" and case.target_segment is not None:
        annotation_segment = (points[case.target_segment[0]], points[case.target_segment[1]])
        roles = ("target_segment",)
    elif problem.annotation_mode == "point" and case.target_point is not None:
        annotation_point = points[case.target_point]
        roles = ("target_point",)
    elif problem.annotation_mode == "point_map":
        annotation_points = {label: points[label] for label in case.point_annotation_labels}
        roles = tuple(annotation_points)
    return RenderedTriangleRelationsScene(
        image=ctx.image,
        answer=case.answer,
        annotation_mode=str(problem.annotation_mode),
        annotation_segment=annotation_segment,
        annotation_point=annotation_point,
        annotation_points=annotation_points,
        annotation_roles=roles,
        scene_entities=(
            {
                "type": "triangle_relations_diagram",
                "points": {key: point_to_list(value) for key, value in points.items()},
                "case_kind": str(case.case_kind),
            },
        ),
        render_map={
            "coord_space": "pixel",
            "vertices": {key: point_to_list(value) for key, value in points.items()},
            "point_label_bboxes": point_label_bboxes,
            "edge_bboxes": edge_bboxes,
            "polygon_bboxes": polygon_bboxes,
            "measurement_label_bboxes": label_bboxes,
            "angle_bboxes": angle_bboxes,
            "right_angle_bboxes": right_angle_bboxes,
            "tick_bboxes": tick_bboxes,
            "single_object_scene_rotation": ctx.scene_transform.metadata(),
        },
        witness=geometry_json_ready(case.trace_values),
        reasoning_steps=int(case.reasoning_steps),
    )


__all__ = ["create_render_context", "render_triangle_relations_scene"]
