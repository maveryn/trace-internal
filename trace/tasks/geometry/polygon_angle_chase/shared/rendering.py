"""Rendering primitives for polygon angle-chase diagrams."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from ...shared.diagram_style import prepare_geometry_diagram_style_and_background
from ...shared.measurement_rendering import bbox_from_points, pad_bbox
from ...shared.scene_transform import LazySceneTransform
from ...shared.vector2d import add_scaled as _add
from ...shared.vector2d import sub as _sub
from ...shared.vector2d import unit as _unit

from .defaults import SCENE_ID
from .measurements import angle_name, assert_non_overlapping, format_degrees
from .state import (
    BBox,
    Color,
    ParallelAnglePlan,
    Point,
    PolygonAnglePlan,
    RenderContext,
    RenderedParallelAngleScene,
    RenderedPolygonAngleScene,
    RenderedSymmetryAngleScene,
    SymmetryAnglePlan,
)


def make_render_context(
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> RenderContext:
    """Create one styled diagram canvas and transform state."""

    width = int(params.get("canvas_width", group_default(rendering_defaults, "canvas_width", 760)))
    height = int(params.get("canvas_height", group_default(rendering_defaults, "canvas_height", 560)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=False,
        require_grid=None,
    )
    draw = ImageDraw.Draw(image)
    font_size = int(params.get("label_font_size", group_default(rendering_defaults, "label_font_size", 22)))
    small_font_size = int(
        params.get("small_label_font_size", group_default(rendering_defaults, "small_label_font_size", 18))
    )
    line_width = int(params.get("line_width", group_default(rendering_defaults, "line_width", 3)))
    label_stroke_width = int(
        params.get(
            "label_stroke_width",
            group_default(rendering_defaults, "label_stroke_width", int(diagram_style.label_stroke_width_px)),
        )
    )
    return RenderContext(
        image=image,
        draw=draw,
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        fill_color=tuple(int(value) for value in diagram_style.muted_fill_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, int(label_stroke_width)),
        font=load_font(font_size),
        small_font=load_font(small_font_size),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_transform"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _draw_text_centered(ctx: RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    x, y = float(center[0]), float(center[1])
    draw_text_traced(
        ctx.draw,
        (x, y),
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
        (x, y),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    return pad_bbox(bbox, 2.0, width=ctx.width, height=ctx.height)


def _line_point(start: Point, end: Point, t: float) -> Point:
    return (
        float(start[0]) + ((float(end[0]) - float(start[0])) * float(t)),
        float(start[1]) + ((float(end[1]) - float(start[1])) * float(t)),
    )


def _draw_segment(ctx: RenderContext, start: Point, end: Point, *, secondary: bool = False) -> None:
    ctx.draw.line(
        [start, end],
        fill=ctx.secondary_color if bool(secondary) else ctx.line_color,
        width=int(ctx.line_width),
    )


def _draw_dashed_segment(
    ctx: RenderContext,
    start: Point,
    end: Point,
    *,
    color: Color | None = None,
    width: int | None = None,
    dash: float = 14.0,
    gap: float = 8.0,
) -> None:
    direction = _unit(_sub(end, start))
    length = math.hypot(float(end[0]) - float(start[0]), float(end[1]) - float(start[1]))
    cursor = 0.0
    while cursor < length:
        segment_end = min(length, cursor + float(dash))
        p0 = _add(start, direction, cursor)
        p1 = _add(start, direction, segment_end)
        ctx.draw.line(
            [p0, p1],
            fill=tuple(int(value) for value in (color or ctx.secondary_color)),
            width=max(1, int(width or max(2, ctx.line_width - 1))),
        )
        cursor += float(dash) + float(gap)


def _draw_angle_marker(
    ctx: RenderContext,
    *,
    vertex: Point,
    prev_point: Point,
    next_point: Point,
    label: str,
    radius: float,
) -> tuple[BBox, BBox, Point]:
    vector_prev = _unit(_sub(prev_point, vertex))
    vector_next = _unit(_sub(next_point, vertex))
    angle_prev = math.atan2(vector_prev[1], vector_prev[0])
    angle_next = math.atan2(vector_next[1], vector_next[0])
    delta = ((angle_next - angle_prev + math.pi) % (2.0 * math.pi)) - math.pi
    steps = max(8, int(abs(delta) / (math.pi / 18.0)))
    arc_points: list[Point] = []
    for step_index in range(steps + 1):
        theta = angle_prev + (delta * (float(step_index) / float(steps)))
        arc_points.append(
            (
                float(vertex[0]) + (float(radius) * math.cos(theta)),
                float(vertex[1]) + (float(radius) * math.sin(theta)),
            )
        )
    ctx.draw.line(arc_points, fill=ctx.accent_color, width=max(2, ctx.line_width - 1), joint="curve")
    arc_bbox = bbox_from_points(arc_points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)

    bisector = _unit((vector_prev[0] + vector_next[0], vector_prev[1] + vector_next[1]))
    if math.hypot(bisector[0], bisector[1]) <= 1e-6:
        bisector = _unit((-float(vertex[0]) + (ctx.width / 2.0), -float(vertex[1]) + (ctx.height / 2.0)))
    label_center = _add(vertex, bisector, float(radius) + 24.0)
    label_bbox = _draw_text_centered(ctx, label, label_center, small=True)
    annotation_point = _add(vertex, bisector, max(10.0, float(radius) * 0.35))
    return arc_bbox, label_bbox, annotation_point


def _sample_polygon_vertices(ctx: RenderContext, plan: PolygonAnglePlan, *, instance_seed: int) -> tuple[Point, ...]:
    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.render.polygon")
    side_count = int(plan.side_count)
    margin_x = 105.0
    margin_y = 86.0
    center = (
        (ctx.width / 2.0) + rng.uniform(-28.0, 28.0),
        (ctx.height / 2.0) + rng.uniform(-20.0, 24.0),
    )
    radius_x = rng.uniform(185.0, 235.0) * (0.92 if side_count == 5 else 1.0)
    radius_y = rng.uniform(145.0, 190.0)
    phase = rng.uniform(-math.pi, math.pi)
    raw_points: list[Point] = []
    for index in range(side_count):
        theta = phase + (2.0 * math.pi * float(index) / float(side_count)) + rng.uniform(-0.11, 0.11)
        local_radius_x = radius_x * rng.uniform(0.91, 1.08)
        local_radius_y = radius_y * rng.uniform(0.91, 1.08)
        raw_points.append(
            (
                center[0] + (local_radius_x * math.cos(theta)),
                center[1] + (local_radius_y * math.sin(theta)),
            )
        )
    min_x = min(point[0] for point in raw_points)
    max_x = max(point[0] for point in raw_points)
    min_y = min(point[1] for point in raw_points)
    max_y = max(point[1] for point in raw_points)
    shift_x = 0.0
    shift_y = 0.0
    if min_x < margin_x:
        shift_x = margin_x - min_x
    if max_x + shift_x > ctx.width - margin_x:
        shift_x = (ctx.width - margin_x) - max_x
    if min_y < margin_y:
        shift_y = margin_y - min_y
    if max_y + shift_y > ctx.height - margin_y:
        shift_y = (ctx.height - margin_y) - max_y
    return tuple((float(x) + shift_x, float(y) + shift_y) for x, y in raw_points)


def render_polygon_angle_scene(
    ctx: RenderContext,
    plan: PolygonAnglePlan,
    *,
    instance_seed: int,
) -> RenderedPolygonAngleScene:
    """Render a labeled polygon with visible algebraic angle labels."""

    vertices = _sample_polygon_vertices(ctx, plan, instance_seed=int(instance_seed))
    vertices = ctx.scene_transform.points(vertices)
    ctx.draw.polygon(vertices, fill=ctx.fill_color)
    ctx.draw.line(
        [*vertices, vertices[0]],
        fill=ctx.line_color,
        width=int(ctx.line_width),
        joint="curve",
    )

    centroid = (
        sum(float(point[0]) for point in vertices) / float(len(vertices)),
        sum(float(point[1]) for point in vertices) / float(len(vertices)),
    )
    point_label_bboxes: dict[str, BBox] = {}
    angle_arc_bboxes: dict[str, BBox] = {}
    angle_label_bboxes: dict[str, BBox] = {}
    annotation_points: dict[str, Point] = {}

    for index, vertex in enumerate(vertices):
        label = str(plan.labels[index])
        outward = _unit(_sub(vertex, centroid))
        point_label_center = _add(vertex, outward, 25.0)
        point_label_bboxes[label] = _draw_text_centered(ctx, label, point_label_center, small=True)
        annotation_points[label] = vertex

    label_bboxes = list(point_label_bboxes.values())
    for index, vertex in enumerate(vertices):
        prev_point = vertices[(index - 1) % len(vertices)]
        next_point = vertices[(index + 1) % len(vertices)]
        arc_bbox, label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=vertex,
            prev_point=prev_point,
            next_point=next_point,
            label=str(plan.display_angle_labels[index]),
            radius=45.0 if plan.side_count == 4 else 39.0,
        )
        name = angle_name(plan.labels, index)
        angle_arc_bboxes[name] = arc_bbox
        angle_label_bboxes[name] = label_bbox
        label_bboxes.append(label_bbox)
    assert_non_overlapping(label_bboxes)
    for bbox in label_bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 6 or y0 <= 6 or x1 >= ctx.width - 6 or y1 >= ctx.height - 6:
            raise ValueError("polygon angle label too close to canvas edge")

    return RenderedPolygonAngleScene(
        image=ctx.image,
        annotation_keyed_points=dict(annotation_points),
        annotation_roles=tuple(annotation_points.keys()),
        point_label_bboxes=dict(point_label_bboxes),
        angle_arc_bboxes=dict(angle_arc_bboxes),
        angle_label_bboxes=dict(angle_label_bboxes),
        vertices=tuple(vertices),
    )


def _draw_parallel_line_marks(ctx: RenderContext, segments: Sequence[tuple[Point, Point]], *, count: int = 1) -> BBox:
    mark_points: list[Point] = []
    for segment_index, (start, end) in enumerate(segments):
        direction = _unit(_sub(end, start))
        normal = (-direction[1], direction[0])
        base = _line_point(start, end, 0.38 + (0.08 * (segment_index % 2)))
        for mark_index in range(max(1, int(count))):
            center = _add(base, direction, (float(mark_index) - ((max(1, int(count)) - 1) / 2.0)) * 13.0)
            p0 = _add(center, normal, -8.0)
            p1 = _add(center, normal, 8.0)
            ctx.draw.line([p0, p1], fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
            mark_points.extend([p0, p1])
    return bbox_from_points(mark_points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _assert_parallel_line_layout(label_bboxes: Sequence[BBox], *, width: int, height: int) -> None:
    assert_non_overlapping(label_bboxes)
    for bbox in label_bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 8 or y0 <= 8 or x1 >= width - 8 or y1 >= height - 8:
            raise ValueError("parallel-line angle label too close to canvas edge")


def render_parallel_one_transversal_scene(
    ctx: RenderContext,
    plan: ParallelAnglePlan,
    *,
    instance_seed: int,
) -> RenderedParallelAngleScene:
    """Render three parallel lines cut by one transversal."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.render.parallel_one")
    support_angle = int(plan.support_angles[0])
    top_y = 140.0 + rng.uniform(-12.0, 10.0)
    mid_y = 280.0 + rng.uniform(-8.0, 8.0)
    bottom_y = 420.0 + rng.uniform(-10.0, 12.0)
    center_x = (ctx.width / 2.0) + rng.uniform(-28.0, 28.0)
    dy = bottom_y - top_y
    dx = dy / math.tan(math.radians(float(support_angle)))
    top_x = center_x - (dx / 2.0)
    bottom_x = center_x + (dx / 2.0)
    if top_x < 150.0:
        shift = 150.0 - top_x
        top_x += shift
        bottom_x += shift
    if bottom_x > ctx.width - 150.0:
        shift = (ctx.width - 150.0) - bottom_x
        top_x += shift
        bottom_x += shift

    line_x0 = 90.0 + rng.uniform(-8.0, 8.0)
    line_x1 = ctx.width - 90.0 + rng.uniform(-8.0, 8.0)
    top_line = ((line_x0, top_y), (line_x1, top_y))
    mid_line = ((line_x0, mid_y), (line_x1, mid_y))
    bottom_line = ((line_x0, bottom_y), (line_x1, bottom_y))
    for segment in (top_line, mid_line, bottom_line):
        _draw_segment(ctx, segment[0], segment[1])

    t_mid = (mid_y - top_y) / (bottom_y - top_y)
    support_vertex = (float(top_x), float(top_y))
    bridge_vertex = (float(top_x + ((bottom_x - top_x) * t_mid)), float(mid_y))
    target_vertex = (float(bottom_x), float(bottom_y))
    v_down = _unit(_sub(target_vertex, support_vertex))
    trans_start = _add(support_vertex, v_down, -70.0)
    trans_end = _add(target_vertex, v_down, 70.0)
    _draw_segment(ctx, trans_start, trans_end)
    parallel_marks_bbox = _draw_parallel_line_marks(ctx, (top_line, mid_line, bottom_line), count=1)

    east = (1.0, 0.0)
    west = (-1.0, 0.0)
    support_arc, support_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=support_vertex,
        prev_point=_add(support_vertex, east, 80.0),
        next_point=_add(support_vertex, v_down, 80.0),
        label=format_degrees(support_angle),
        radius=36.0,
    )
    target_prev = _add(target_vertex, east if plan.relation_id == "corresponding_same" else west, 80.0)
    target_arc, target_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=target_vertex,
        prev_point=target_prev,
        next_point=_add(target_vertex, v_down, 80.0),
        label=str(plan.target_angle_label),
        radius=36.0,
    )
    point_label_bboxes = [
        _draw_text_centered(ctx, "P", _add(support_vertex, (-1.0, -1.0), 24.0), small=True),
        _draw_text_centered(ctx, "Q", _add(bridge_vertex, (-1.0, 0.0), 25.0), small=True),
        _draw_text_centered(ctx, "R", _add(target_vertex, (1.0, 1.0), 24.0), small=True),
    ]
    _assert_parallel_line_layout(
        [*point_label_bboxes, support_label_bbox, target_label_bbox],
        width=ctx.width,
        height=ctx.height,
    )

    return RenderedParallelAngleScene(
        image=ctx.image,
        annotation_keyed_points={"P": support_vertex, "Q": bridge_vertex, "R": target_vertex},
        annotation_roles=("P", "Q", "R"),
        angle_arc_bboxes={
            "support_angle": support_arc,
            "target_angle": target_arc,
            "parallel_marks": parallel_marks_bbox,
        },
        angle_label_bboxes={
            "support_angle_label": support_label_bbox,
            "target_angle_label": target_label_bbox,
        },
        line_segments={
            "parallel_line_1": top_line,
            "parallel_line_2": mid_line,
            "parallel_line_3": bottom_line,
            "transversal": (trans_start, trans_end),
        },
        intersections={"P": support_vertex, "Q": bridge_vertex, "R": target_vertex},
    )


def render_parallel_two_transversal_scene(
    ctx: RenderContext,
    plan: ParallelAnglePlan,
    *,
    instance_seed: int,
) -> RenderedParallelAngleScene:
    """Render two transversals between two parallel lines."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.render.parallel_two")
    left_angle, right_angle = [int(value) for value in plan.support_angles]
    top_y = 142.0 + rng.uniform(-10.0, 10.0)
    target_y = 294.0 + rng.uniform(-12.0, 12.0)
    bottom_y = 430.0 + rng.uniform(-10.0, 10.0)
    target_x = (ctx.width / 2.0) + rng.uniform(-24.0, 24.0)
    left_dx = (target_y - top_y) / math.tan(math.radians(float(left_angle)))
    right_dx = (target_y - top_y) / math.tan(math.radians(float(right_angle)))
    support_vertex_1 = (float(target_x - left_dx), float(top_y))
    support_vertex_2 = (float(target_x + right_dx), float(top_y))
    target_vertex = (float(target_x), float(target_y))
    scale_to_bottom = (bottom_y - target_y) / (target_y - top_y)
    bottom_right = _add(target_vertex, _sub(target_vertex, support_vertex_1), scale_to_bottom)
    bottom_left = _add(target_vertex, _sub(target_vertex, support_vertex_2), scale_to_bottom)

    line_x0 = 88.0 + rng.uniform(-8.0, 8.0)
    line_x1 = ctx.width - 88.0 + rng.uniform(-8.0, 8.0)
    top_line = ((line_x0, top_y), (line_x1, top_y))
    bottom_line = ((line_x0, bottom_y), (line_x1, bottom_y))
    for segment in (top_line, bottom_line):
        _draw_segment(ctx, segment[0], segment[1])
    _draw_segment(ctx, support_vertex_1, bottom_right)
    _draw_segment(ctx, support_vertex_2, bottom_left)
    parallel_marks_bbox = _draw_parallel_line_marks(ctx, (top_line, bottom_line), count=1)

    east = (1.0, 0.0)
    west = (-1.0, 0.0)
    support_arc_1, support_label_bbox_1, _ = _draw_angle_marker(
        ctx,
        vertex=support_vertex_1,
        prev_point=_add(support_vertex_1, east, 80.0),
        next_point=target_vertex,
        label=format_degrees(left_angle),
        radius=35.0,
    )
    support_arc_2, support_label_bbox_2, _ = _draw_angle_marker(
        ctx,
        vertex=support_vertex_2,
        prev_point=target_vertex,
        next_point=_add(support_vertex_2, west, 80.0),
        label=format_degrees(right_angle),
        radius=35.0,
    )
    target_arc, target_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=target_vertex,
        prev_point=support_vertex_1,
        next_point=support_vertex_2,
        label=str(plan.target_angle_label),
        radius=42.0,
    )
    point_label_bboxes = [
        _draw_text_centered(ctx, "P", _add(support_vertex_1, (-1.0, -1.0), 24.0), small=True),
        _draw_text_centered(ctx, "Q", _add(target_vertex, (0.0, 1.0), 27.0), small=True),
        _draw_text_centered(ctx, "R", _add(support_vertex_2, (1.0, -1.0), 24.0), small=True),
    ]
    _assert_parallel_line_layout(
        [*point_label_bboxes, support_label_bbox_1, support_label_bbox_2, target_label_bbox],
        width=ctx.width,
        height=ctx.height,
    )

    return RenderedParallelAngleScene(
        image=ctx.image,
        annotation_keyed_points={"P": support_vertex_1, "Q": target_vertex, "R": support_vertex_2},
        annotation_roles=("P", "Q", "R"),
        angle_arc_bboxes={
            "support_angle_1": support_arc_1,
            "support_angle_2": support_arc_2,
            "target_angle": target_arc,
            "parallel_marks": parallel_marks_bbox,
        },
        angle_label_bboxes={
            "support_angle_1_label": support_label_bbox_1,
            "support_angle_2_label": support_label_bbox_2,
            "target_angle_label": target_label_bbox,
        },
        line_segments={
            "parallel_line_1": top_line,
            "parallel_line_2": bottom_line,
            "transversal_1": (support_vertex_1, bottom_right),
            "transversal_2": (support_vertex_2, bottom_left),
        },
        intersections={"P": support_vertex_1, "Q": target_vertex, "R": support_vertex_2},
    )


def _draw_right_angle_marker(
    ctx: RenderContext,
    *,
    vertex: Point,
    arm_a: Point,
    arm_b: Point,
    size: float = 22.0,
) -> BBox:
    u = _unit(_sub(arm_a, vertex))
    v = _unit(_sub(arm_b, vertex))
    p1 = _add(vertex, u, float(size))
    p2 = _add(p1, v, float(size))
    p3 = _add(vertex, v, float(size))
    ctx.draw.line([p1, p2, p3], fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    return bbox_from_points((p1, p2, p3), width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_equal_side_ticks(ctx: RenderContext, segments: Sequence[tuple[Point, Point]], *, count: int = 1) -> BBox:
    tick_points: list[Point] = []
    for start, end in segments:
        direction = _unit(_sub(end, start))
        normal = (-direction[1], direction[0])
        midpoint = _line_point(start, end, 0.5)
        for index in range(max(1, int(count))):
            shift = (float(index) - ((max(1, int(count)) - 1) / 2.0)) * 6.0
            center = _add(midpoint, direction, shift)
            p0 = _add(center, normal, -8.0)
            p1 = _add(center, normal, 8.0)
            ctx.draw.line([p0, p1], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
            tick_points.extend((p0, p1))
    return bbox_from_points(tick_points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _assert_symmetry_angle_layout(label_bboxes: Sequence[BBox], *, width: int, height: int) -> None:
    assert_non_overlapping(label_bboxes)
    for bbox in label_bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 8 or y0 <= 8 or x1 >= width - 8 or y1 >= height - 8:
            raise ValueError("symmetry angle label too close to canvas edge")


def render_rectangle_diagonal_scene(
    ctx: RenderContext,
    plan: SymmetryAnglePlan,
    *,
    instance_seed: int,
) -> RenderedSymmetryAngleScene:
    """Render a rectangle with a diagonal splitting one right angle."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.render.rectangle_diagonal")
    known_angle = int(plan.support_angle)
    ratio = math.tan(math.radians(float(known_angle)))
    max_w = 355.0
    max_h = 260.0
    if ratio <= max_h / max_w:
        rect_w = max_w
        rect_h = rect_w * ratio
    else:
        rect_h = max_h
        rect_w = rect_h / ratio
    scale = rng.uniform(0.94, 1.05)
    rect_w *= scale
    rect_h *= scale
    cx = (ctx.width / 2.0) + rng.uniform(-24.0, 28.0)
    cy = (ctx.height / 2.0) + rng.uniform(-18.0, 20.0)
    a = (cx - (rect_w / 2.0), cy - (rect_h / 2.0))
    b = (cx + (rect_w / 2.0), cy - (rect_h / 2.0))
    c = (cx + (rect_w / 2.0), cy + (rect_h / 2.0))
    d = (cx - (rect_w / 2.0), cy + (rect_h / 2.0))

    ctx.draw.polygon((a, b, c, d), fill=ctx.fill_color)
    ctx.draw.line([a, b, c, d, a], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    _draw_segment(ctx, a, c, secondary=True)
    right_angle_bbox = _draw_right_angle_marker(ctx, vertex=a, arm_a=b, arm_b=d)

    point_bboxes = [
        _draw_text_centered(ctx, "A", _add(a, (-1.0, -1.0), 22.0), small=True),
        _draw_text_centered(ctx, "B", _add(b, (1.0, -1.0), 22.0), small=True),
        _draw_text_centered(ctx, "C", _add(c, (1.0, 1.0), 22.0), small=True),
        _draw_text_centered(ctx, "D", _add(d, (-1.0, 1.0), 22.0), small=True),
    ]
    support_arc, support_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=a,
        prev_point=b,
        next_point=c,
        label=format_degrees(known_angle),
        radius=39.0,
    )
    target_arc, target_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=a,
        prev_point=c,
        next_point=d,
        label=str(plan.target_angle_label),
        radius=69.0,
    )
    _assert_symmetry_angle_layout([*point_bboxes, support_label_bbox, target_label_bbox], width=ctx.width, height=ctx.height)

    return RenderedSymmetryAngleScene(
        image=ctx.image,
        annotation_keyed_points={"A": a, "B": b, "C": c, "D": d},
        annotation_roles=("A", "B", "C", "D"),
        angle_arc_bboxes={
            "known_angle": support_arc,
            "target_angle": target_arc,
            "right_angle_marker": right_angle_bbox,
        },
        angle_label_bboxes={
            "known_angle_label": support_label_bbox,
            "target_angle_label": target_label_bbox,
        },
        construction_segments={
            "side_ab": (a, b),
            "side_bc": (b, c),
            "side_cd": (c, d),
            "side_da": (d, a),
            "diagonal_ac": (a, c),
        },
        construction_points={"A": a, "B": b, "C": c, "D": d},
    )


def render_reflection_axis_scene(
    ctx: RenderContext,
    plan: SymmetryAnglePlan,
    *,
    instance_seed: int,
) -> RenderedSymmetryAngleScene:
    """Render two rays mirrored about a vertical axis."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.render.reflection_axis")
    support_angle = int(plan.support_angle)
    vertex = ((ctx.width / 2.0) + rng.uniform(-24.0, 24.0), 235.0 + rng.uniform(-14.0, 16.0))
    axis_top = (vertex[0], 82.0 + rng.uniform(-8.0, 8.0))
    axis_bottom = (vertex[0], 454.0 + rng.uniform(-8.0, 8.0))
    ray_length = 205.0 + rng.uniform(-8.0, 12.0)
    sin_a = math.sin(math.radians(float(support_angle)))
    cos_a = math.cos(math.radians(float(support_angle)))
    left_endpoint = _add(vertex, (-sin_a, cos_a), ray_length)
    right_endpoint = _add(vertex, (sin_a, cos_a), ray_length)

    _draw_dashed_segment(ctx, axis_top, axis_bottom, color=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    _draw_segment(ctx, vertex, left_endpoint)
    _draw_segment(ctx, vertex, right_endpoint)
    axis_mark_bbox = _draw_equal_side_ticks(ctx, ((axis_top, vertex), (vertex, axis_bottom)), count=1)

    support_arc, support_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=vertex,
        prev_point=axis_bottom,
        next_point=right_endpoint,
        label=format_degrees(support_angle),
        radius=38.0,
    )
    target_arc, target_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=vertex,
        prev_point=left_endpoint,
        next_point=right_endpoint,
        label=str(plan.target_angle_label),
        radius=72.0,
    )
    point_bboxes = [
        _draw_text_centered(ctx, "P", _add(vertex, (0.0, -1.0), 26.0), small=True),
        _draw_text_centered(ctx, "Q", _add(axis_top, (0.0, -1.0), 22.0), small=True),
        _draw_text_centered(ctx, "R", _add(axis_bottom, (0.0, 1.0), 22.0), small=True),
    ]
    _assert_symmetry_angle_layout([*point_bboxes, support_label_bbox, target_label_bbox], width=ctx.width, height=ctx.height)

    return RenderedSymmetryAngleScene(
        image=ctx.image,
        annotation_keyed_points={"P": vertex, "Q": axis_top, "R": axis_bottom},
        annotation_roles=("P", "Q", "R"),
        angle_arc_bboxes={
            "known_angle": support_arc,
            "target_angle": target_arc,
            "symmetry_axis_marks": axis_mark_bbox,
        },
        angle_label_bboxes={
            "known_angle_label": support_label_bbox,
            "target_angle_label": target_label_bbox,
        },
        construction_segments={
            "symmetry_axis": (axis_top, axis_bottom),
            "ray_left": (vertex, left_endpoint),
            "ray_right": (vertex, right_endpoint),
        },
        construction_points={
            "P": vertex,
            "Q": axis_top,
            "R": axis_bottom,
            "left_ray_endpoint": left_endpoint,
            "right_ray_endpoint": right_endpoint,
        },
    )


def render_isosceles_angle_scene(
    ctx: RenderContext,
    plan: SymmetryAnglePlan,
    *,
    instance_seed: int,
) -> RenderedSymmetryAngleScene:
    """Render an isosceles triangle with one target angle."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.render.isosceles")
    if plan.target_role == "base_angle":
        apex_angle = int(plan.support_angle)
        support_label = format_degrees(apex_angle)
    else:
        apex_angle = int(plan.answer)
        support_label = format_degrees(int(plan.support_angle))
    half_apex = max(16.0, float(apex_angle) / 2.0)
    max_half_base = 178.0
    max_height = 278.0
    height = max_half_base / math.tan(math.radians(half_apex))
    if height > max_height:
        height = max_height
        half_base = height * math.tan(math.radians(half_apex))
    else:
        half_base = max_half_base
    scale = rng.uniform(0.94, 1.05)
    half_base *= scale
    height *= scale
    cx = (ctx.width / 2.0) + rng.uniform(-24.0, 24.0)
    cy = (ctx.height / 2.0) + rng.uniform(-14.0, 18.0)
    apex = (cx, cy - (height / 2.0))
    base_left = (cx - half_base, cy + (height / 2.0))
    base_right = (cx + half_base, cy + (height / 2.0))

    ctx.draw.polygon((apex, base_left, base_right), fill=ctx.fill_color)
    ctx.draw.line([apex, base_left, base_right, apex], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ticks_bbox = _draw_equal_side_ticks(ctx, ((apex, base_left), (apex, base_right)), count=1)
    point_bboxes = [
        _draw_text_centered(ctx, "A", _add(apex, (0.0, -1.0), 25.0), small=True),
        _draw_text_centered(ctx, "B", _add(base_left, (-1.0, 1.0), 24.0), small=True),
        _draw_text_centered(ctx, "C", _add(base_right, (1.0, 1.0), 24.0), small=True),
    ]

    if plan.target_role == "base_angle":
        target_arc, target_label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=base_left,
            prev_point=base_right,
            next_point=apex,
            label=str(plan.target_angle_label),
            radius=43.0,
        )
        support_arc, support_label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=apex,
            prev_point=base_left,
            next_point=base_right,
            label=support_label,
            radius=47.0,
        )
    else:
        target_arc, target_label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=apex,
            prev_point=base_left,
            next_point=base_right,
            label=str(plan.target_angle_label),
            radius=47.0,
        )
        support_arc, support_label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=base_left,
            prev_point=base_right,
            next_point=apex,
            label=support_label,
            radius=43.0,
        )

    _assert_symmetry_angle_layout([*point_bboxes, support_label_bbox, target_label_bbox], width=ctx.width, height=ctx.height)

    return RenderedSymmetryAngleScene(
        image=ctx.image,
        annotation_keyed_points={"A": apex, "B": base_left, "C": base_right},
        annotation_roles=("A", "B", "C"),
        angle_arc_bboxes={
            "known_angle": support_arc,
            "target_angle": target_arc,
            "equal_side_ticks": ticks_bbox,
        },
        angle_label_bboxes={
            "known_angle_label": support_label_bbox,
            "target_angle_label": target_label_bbox,
        },
        construction_segments={
            "side_ab": (apex, base_left),
            "side_ac": (apex, base_right),
            "base_bc": (base_left, base_right),
        },
        construction_points={"A": apex, "B": base_left, "C": base_right},
    )


__all__ = [
    "make_render_context",
    "render_isosceles_angle_scene",
    "render_parallel_one_transversal_scene",
    "render_parallel_two_transversal_scene",
    "render_polygon_angle_scene",
    "render_rectangle_diagonal_scene",
    "render_reflection_axis_scene",
]
