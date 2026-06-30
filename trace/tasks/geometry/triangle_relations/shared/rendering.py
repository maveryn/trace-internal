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
    pad_bbox,
)
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import add_scaled, mid, perp, point_to_list, sub, unit
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

BBox = tuple[float, float, float, float]


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


def _coerce_bbox(bbox: Sequence[float]) -> BBox:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _bbox_overlap_area(a: Sequence[float], b: Sequence[float]) -> float:
    ax0, ay0, ax1, ay1 = _coerce_bbox(a)
    bx0, by0, bx1, by1 = _coerce_bbox(b)
    overlap_w = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    overlap_h = max(0.0, min(ay1, by1) - max(ay0, by0))
    return overlap_w * overlap_h


def _expand_bbox(bbox: Sequence[float], pad: float) -> BBox:
    x0, y0, x1, y1 = _coerce_bbox(bbox)
    return (x0 - float(pad), y0 - float(pad), x1 + float(pad), y1 + float(pad))


def _readout_bbox(ctx: RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return (x0 - 4.0, y0 - 4.0, x1 + 4.0, y1 + 4.0)


def _placement_penalty(
    ctx: RenderContext,
    bbox: Sequence[float],
    *,
    avoid_bboxes: Sequence[Sequence[float]],
    anchor: Point,
    center: Point,
) -> float:
    x0, y0, x1, y1 = _coerce_bbox(bbox)
    margin = 16.0
    edge_penalty = 0.0
    if x0 < margin:
        edge_penalty += 1_000_000.0 + (margin - x0) * 120.0
    if y0 < margin:
        edge_penalty += 1_000_000.0 + (margin - y0) * 120.0
    if x1 > float(ctx.width) - margin:
        edge_penalty += 1_000_000.0 + (x1 - (float(ctx.width) - margin)) * 120.0
    if y1 > float(ctx.height) - margin:
        edge_penalty += 1_000_000.0 + (y1 - (float(ctx.height) - margin)) * 120.0
    overlap_penalty = 0.0
    for avoid_bbox in avoid_bboxes:
        overlap_area = _bbox_overlap_area(bbox, avoid_bbox)
        if overlap_area > 0.0:
            overlap_penalty += 1_000_000.0 + overlap_area * 100.0
    distance_penalty = math.hypot(float(center[0]) - float(anchor[0]), float(center[1]) - float(anchor[1])) * 0.08
    return edge_penalty + overlap_penalty + distance_penalty


def _choose_segment_label_center(
    ctx: RenderContext,
    a: Point,
    b: Point,
    text: str,
    offset: float,
    *,
    avoid_bboxes: Sequence[Sequence[float]],
) -> Point:
    tangent = unit(sub(b, a))
    normal = perp(tangent)
    midpoint = mid(a, b)
    base_offset = max(30.0, abs(float(offset)))
    preferred_sign = 1.0 if float(offset) >= 0.0 else -1.0
    segment_length = math.hypot(float(b[0]) - float(a[0]), float(b[1]) - float(a[1]))
    is_target_label = "?" in str(text)
    offset_scales = (1.0, 1.4, 1.9, 2.5, 3.2)
    shift_scales = (0.0, -0.18, 0.18, -0.34, 0.34, -0.52, 0.52)
    if is_target_label:
        shift_scales = (0.0, -0.18, 0.18, -0.34, 0.34, -0.52, 0.52, -0.68, 0.68)
    candidates: list[Point] = []
    for sign in (preferred_sign, -preferred_sign):
        for offset_scale in offset_scales:
            for shift_scale in shift_scales:
                center = add_scaled(add_scaled(midpoint, normal, sign * base_offset * offset_scale), tangent, segment_length * shift_scale)
                candidates.append(center)
    return min(
        candidates,
        key=lambda center: _placement_penalty(
            ctx,
            _readout_bbox(ctx, text, center, small=True),
            avoid_bboxes=avoid_bboxes,
            anchor=midpoint,
            center=center,
        ),
    )


def _draw_segment_label(
    ctx: RenderContext,
    points: Mapping[str, Point],
    label: SegmentLabel,
    *,
    avoid_bboxes: Sequence[Sequence[float]] = (),
) -> BBox:
    a = points[str(label.segment[0])]
    b = points[str(label.segment[1])]
    center = _choose_segment_label_center(ctx, a, b, str(label.text), float(label.offset), avoid_bboxes=avoid_bboxes)
    return draw_readout_centered(ctx, str(label.text), center, small=True, backed=False)


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


def _choose_point_label_center(
    ctx: RenderContext,
    label: str,
    point: Point,
    *,
    avoid_bboxes: Sequence[Sequence[float]],
) -> Point:
    """Choose a readable point-label position without changing projected geometry."""

    x, y = float(point[0]), float(point[1])
    outward_x = -1.0 if x < float(ctx.width) / 2.0 else 1.0
    outward_y = -1.0 if y < float(ctx.height) / 2.0 else 1.0
    offsets = (
        (0.0, -28.0),
        (28.0, 0.0),
        (0.0, 28.0),
        (-28.0, 0.0),
        (24.0 * outward_x, 24.0 * outward_y),
        (24.0 * outward_x, -24.0 * outward_y),
        (-24.0 * outward_x, 24.0 * outward_y),
        (-24.0 * outward_x, -24.0 * outward_y),
        (0.0, -38.0),
        (38.0, 0.0),
        (0.0, 38.0),
        (-38.0, 0.0),
        (0.0, -52.0),
        (52.0, 0.0),
        (0.0, 52.0),
        (-52.0, 0.0),
        (38.0 * outward_x, 38.0 * outward_y),
        (38.0 * outward_x, -38.0 * outward_y),
        (-38.0 * outward_x, 38.0 * outward_y),
        (-38.0 * outward_x, -38.0 * outward_y),
        (0.0, -66.0),
        (66.0, 0.0),
        (0.0, 66.0),
        (-66.0, 0.0),
    )
    candidates = [(x + dx, y + dy) for dx, dy in offsets]
    return min(
        candidates,
        key=lambda center: _placement_penalty(
            ctx,
            _readout_bbox(ctx, label, center, small=True),
            avoid_bboxes=avoid_bboxes,
            anchor=point,
            center=center,
        ),
    )


def _draw_point_labels(
    ctx: RenderContext,
    points: Mapping[str, Point],
    *,
    avoid_bboxes: Sequence[Sequence[float]] = (),
) -> dict[str, list[float]]:
    bboxes: dict[str, list[float]] = {}
    placed_avoid_bboxes: list[BBox] = []
    for label, point in points.items():
        center = _choose_point_label_center(ctx, str(label), point, avoid_bboxes=tuple(avoid_bboxes) + tuple(placed_avoid_bboxes))
        bbox = draw_readout_centered(ctx, str(label), center, small=True, backed=False, required=False)
        bboxes[str(label)] = bbox_to_list(bbox)
        placed_avoid_bboxes.append(_expand_bbox(bbox, 10.0))
    return bboxes


def _vertex_guard_bboxes(ctx: RenderContext, points: Mapping[str, Point], *, radius: float = 18.0) -> dict[str, BBox]:
    return {
        key: pad_bbox((float(point[0]), float(point[1]), float(point[0]), float(point[1])), float(radius), width=int(ctx.width), height=int(ctx.height))
        for key, point in points.items()
    }


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
    edge_bboxes: dict[str, list[float]] = {}
    edge_bbox_by_segment: dict[frozenset[str], BBox] = {}
    for a, b in case.edges:
        bbox = _draw_line(ctx, (points[a], points[b]), color=ctx.line_color)
        edge_bboxes[f"{a}{b}"] = bbox_to_list(bbox)
        edge_bbox_by_segment[frozenset((a, b))] = _coerce_bbox(bbox)
    angle_bboxes: dict[str, list[float]] = {}
    angle_bbox_values: list[BBox] = []
    for angle in case.angle_labels:
        bbox = _draw_angle(ctx, points, angle)
        angle_bboxes[angle.role or f"{angle.arm_a}{angle.vertex}{angle.arm_b}"] = bbox_to_list(bbox)
        angle_bbox_values.append(_coerce_bbox(bbox))
    right_angle_bboxes: dict[str, list[float]] = {}
    right_angle_bbox_values: list[BBox] = []
    for mark in case.right_angles:
        bbox = _draw_right_angle(ctx, points, mark)
        right_angle_bboxes[mark.vertex] = bbox_to_list(bbox)
        right_angle_bbox_values.append(_coerce_bbox(bbox))
    tick_bboxes: dict[str, list[float]] = {}
    tick_bbox_values: list[BBox] = []
    for idx, group in enumerate(case.tick_groups):
        bbox = _draw_tick_group(ctx, points, group)
        tick_bboxes[f"{group.kind}_{idx}"] = bbox_to_list(bbox)
        tick_bbox_values.append(_coerce_bbox(bbox))
    vertex_guards = _vertex_guard_bboxes(ctx, points)
    construction_bboxes = tuple(angle_bbox_values + right_angle_bbox_values + tick_bbox_values)
    label_bboxes: dict[str, list[float]] = {}
    label_bbox_values: list[BBox] = []
    label_avoid_bboxes: list[BBox] = []
    for label in case.segment_labels:
        owned_segment = frozenset(str(value) for value in label.segment)
        avoid_bboxes = (
            tuple(vertex_guards.values())
            + tuple(bbox for segment, bbox in edge_bbox_by_segment.items() if segment != owned_segment)
            + construction_bboxes
            + tuple(label_avoid_bboxes)
        )
        bbox = _draw_segment_label(ctx, points, label, avoid_bboxes=avoid_bboxes)
        label_bboxes[label.role or "".join(label.segment)] = bbox_to_list(bbox)
        raw_bbox = _coerce_bbox(bbox)
        label_bbox_values.append(raw_bbox)
        label_avoid_bboxes.append(_expand_bbox(raw_bbox, 14.0))
    point_label_bboxes = _draw_point_labels(
        ctx,
        points,
        avoid_bboxes=construction_bboxes + tuple(label_avoid_bboxes),
    )
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
