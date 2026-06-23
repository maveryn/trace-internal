"""Rendering for marked polygon equation diagrams."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    pad_bbox,
)
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import add_scaled, mid, point_to_list, sub, unit
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from .defaults import SCENE_ID
from .state import BBox, MarkedEquationCase, Point, RenderContext, RenderedMarkedEquationScene, Side


def _offset_from_segment(a: Point, b: Point, distance: float) -> Point:
    ux, uy = unit(sub(b, a))
    return (-uy * float(distance), ux * float(distance))


def _line_bbox(points: Sequence[Point], ctx: RenderContext, pad: float = 5.0) -> BBox:
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=pad)


def _draw_text_centered(ctx: RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
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


def _draw_point_label(ctx: RenderContext, label: str, point: Point, direction: Point, *, offset: float = 22.0) -> BBox:
    return _draw_text_centered(ctx, label, add_scaled(point, unit(direction), offset), small=True)


def _draw_side_label(ctx: RenderContext, points: Sequence[Point], side: Side, text: str, *, offset: float) -> BBox:
    a = points[int(side[0])]
    b = points[int(side[1])]
    return _draw_text_centered(ctx, str(text), add_scaled(mid(a, b), _offset_from_segment(a, b, offset)), small=True)


def _draw_tick(ctx: RenderContext, a: Point, b: Point, *, count: int = 1) -> BBox:
    center = mid(a, b)
    tangent = unit(sub(b, a))
    normal = (-tangent[1], tangent[0])
    tick_points: list[Point] = []
    spacing = 9.0
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * spacing
        tick_center = add_scaled(center, tangent, shift)
        p0 = add_scaled(tick_center, normal, -9.0)
        p1 = add_scaled(tick_center, normal, 9.0)
        ctx.draw.line((p0, p1), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        tick_points.extend([p0, p1])
    return _line_bbox(tick_points, ctx, pad=4.0)


def _draw_angle_arc(
    ctx: RenderContext,
    vertex: Point,
    ray_a: Point,
    ray_b: Point,
    *,
    radius: float = 34.0,
    count: int = 1,
) -> BBox:
    va = unit(sub(ray_a, vertex))
    vb = unit(sub(ray_b, vertex))
    angle_a = math.atan2(va[1], va[0])
    angle_b = math.atan2(vb[1], vb[0])
    delta = (angle_b - angle_a) % (2.0 * math.pi)
    if delta > math.pi:
        angle_a, angle_b = angle_b, angle_a
        delta = (angle_b - angle_a) % (2.0 * math.pi)
    points: list[Point] = []
    for arc_index in range(int(count)):
        radius_px = float(radius) + arc_index * 8.0
        last: Point | None = None
        for step in range(17):
            t = float(step) / 16.0
            theta = angle_a + delta * t
            point = (vertex[0] + math.cos(theta) * radius_px, vertex[1] + math.sin(theta) * radius_px)
            if last is not None:
                ctx.draw.line((last, point), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
            last = point
            points.append(point)
    return _line_bbox(points, ctx, pad=5.0)


def _draw_right_angle_marker(ctx: RenderContext, vertex: Point, ray_a: Point, ray_b: Point, *, size: float = 20.0) -> BBox:
    u = unit(sub(ray_a, vertex))
    v = unit(sub(ray_b, vertex))
    p1 = add_scaled(vertex, u, size)
    p2 = add_scaled(p1, v, size)
    p3 = add_scaled(vertex, v, size)
    ctx.draw.line((p1, p2, p3), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    return _line_bbox((p1, p2, p3), ctx, pad=4.0)


def _draw_polygon(ctx: RenderContext, points: Sequence[Point]) -> BBox:
    polygon = [(float(x), float(y)) for x, y in points]
    ctx.draw.polygon(polygon, fill=ctx.fill_color)
    ctx.draw.line(polygon + [polygon[0]], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    return bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_vertex_labels(ctx: RenderContext, points: Sequence[Point], labels: Sequence[str]) -> Dict[str, BBox]:
    center = (sum(point[0] for point in points) / float(len(points)), sum(point[1] for point in points) / float(len(points)))
    bboxes: Dict[str, BBox] = {}
    for label, point in zip(labels, points):
        bboxes[str(label)] = _draw_point_label(ctx, str(label), point, sub(point, center), offset=24.0)
    return bboxes


def _make_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> RenderContext:
    """Create canvas, style, font, and transform state for one diagram."""

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
        diagram_style_meta=style_meta,
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_transform"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _triangle_points(ctx: RenderContext, rng: Any) -> Tuple[Point, Point, Point]:
    cx = ctx.width / 2.0 + rng.uniform(-12.0, 12.0)
    cy = ctx.height / 2.0 + rng.uniform(-10.0, 16.0)
    w = rng.uniform(360.0, 420.0)
    h = rng.uniform(265.0, 305.0)
    return ((cx, cy - h / 2.0), (cx - w / 2.0, cy + h / 2.0), (cx + w / 2.0, cy + h / 2.0))


def _split_triangle_points(ctx: RenderContext, rng: Any) -> Tuple[Point, Point, Point, Point]:
    apex, left_base, right_base = _triangle_points(ctx, rng)
    split = mid(left_base, right_base)
    return apex, left_base, right_base, split


def _quad_points(ctx: RenderContext, rng: Any) -> Tuple[Point, Point, Point, Point]:
    cx = ctx.width / 2.0 + rng.uniform(-10.0, 12.0)
    cy = ctx.height / 2.0 + rng.uniform(-8.0, 16.0)
    return (
        (cx - rng.uniform(190.0, 220.0), cy - rng.uniform(130.0, 155.0)),
        (cx + rng.uniform(120.0, 160.0), cy - rng.uniform(150.0, 172.0)),
        (cx + rng.uniform(205.0, 235.0), cy + rng.uniform(110.0, 145.0)),
        (cx - rng.uniform(145.0, 180.0), cy + rng.uniform(145.0, 170.0)),
    )


def _render_split_triangle(case: MarkedEquationCase, ctx: RenderContext, rng: Any) -> tuple[dict[str, Point], dict[str, BBox], dict[str, BBox], dict[str, BBox]]:
    """Draw triangle-with-median constructions and return projected render maps."""

    labels = dict(case.labels)
    apex, left_base, right_base, split = ctx.scene_transform.points(_split_triangle_points(ctx, rng))
    points = (apex, left_base, right_base)
    vertices = {"A": apex, "B": left_base, "C": right_base, "D": split}
    construction = {
        "polygon": _draw_polygon(ctx, points),
        "split_segment": _line_bbox((apex, split), ctx, pad=ctx.line_width + 3),
        "right_angle": _draw_right_angle_marker(ctx, split, apex, right_base),
    }
    ctx.draw.line((apex, split), fill=ctx.secondary_color, width=ctx.line_width)
    point_labels = {key: bbox_to_list(value) for key, value in _draw_vertex_labels(ctx, points, ("A", "B", "C")).items()}
    point_labels["D"] = bbox_to_list(_draw_point_label(ctx, "D", split, (0.0, 1.0)))
    readouts: dict[str, BBox] = {}
    left_side = (apex, left_base)
    right_side = (apex, right_base)
    if case.draw_kind in {"equilateral_median_sides", "equilateral_median_right_angle"}:
        construction["left_side_tick"] = _draw_tick(ctx, *left_side, count=1)
        construction["right_side_tick"] = _draw_tick(ctx, *right_side, count=1)
        construction["base_tick"] = _draw_tick(ctx, left_base, right_base, count=1)
    if case.draw_kind == "isosceles_altitude_base_split":
        construction["left_side_tick"] = _draw_tick(ctx, *left_side, count=1)
        construction["right_side_tick"] = _draw_tick(ctx, *right_side, count=1)
        construction["left_base_split_tick"] = _draw_tick(ctx, left_base, split, count=2)
        construction["right_base_split_tick"] = _draw_tick(ctx, split, right_base, count=2)
        readouts["left_base_label"] = _draw_side_label(ctx, (left_base, split), (0, 1), labels["left_base"], offset=31.0)
        readouts["right_base_label"] = _draw_side_label(ctx, (split, right_base), (0, 1), labels["right_base"], offset=31.0)
    elif case.draw_kind == "equilateral_median_right_angle":
        readouts["right_angle_expression"] = _draw_text_centered(ctx, labels["right_angle_expression"], add_scaled(split, (44.0, -34.0)), small=True)
    else:
        readouts["left_side_label"] = _draw_side_label(ctx, (apex, left_base), (0, 1), labels["left_side"], offset=-32.0)
        readouts["right_side_label"] = _draw_side_label(ctx, (apex, right_base), (0, 1), labels["right_side"], offset=32.0)
        readouts["base_side_label"] = _draw_side_label(ctx, (left_base, right_base), (0, 1), labels["base_side"], offset=31.0)
    return vertices, point_labels, readouts, construction


def _render_basic_triangle(case: MarkedEquationCase, ctx: RenderContext, rng: Any) -> tuple[dict[str, Point], dict[str, BBox], dict[str, BBox], dict[str, BBox]]:
    """Draw triangle equal-side or base-angle constructions."""

    labels = dict(case.labels)
    points = tuple(ctx.scene_transform.points(_triangle_points(ctx, rng)))
    vertices = {"A": points[0], "B": points[1], "C": points[2]}
    construction = {"polygon": _draw_polygon(ctx, points)}
    point_labels = {key: bbox_to_list(value) for key, value in _draw_vertex_labels(ctx, points, ("A", "B", "C")).items()}
    readouts: dict[str, BBox] = {}
    left_side = (0, 1)
    right_side = (0, 2)
    base_side = (1, 2)
    if case.draw_kind in {"triangle_equal_sides", "equilateral_sides"}:
        readouts["left_side_label"] = _draw_side_label(ctx, points, left_side, labels["left_side"], offset=-31.0)
        readouts["right_side_label"] = _draw_side_label(ctx, points, right_side, labels["right_side"], offset=31.0)
        construction["left_equal_tick"] = _draw_tick(ctx, points[left_side[0]], points[left_side[1]], count=1)
        construction["right_equal_tick"] = _draw_tick(ctx, points[right_side[0]], points[right_side[1]], count=1)
        if case.draw_kind == "equilateral_sides":
            readouts["base_side_label"] = _draw_side_label(ctx, points, base_side, labels["base_side"], offset=30.0)
            construction["base_equal_tick"] = _draw_tick(ctx, points[base_side[0]], points[base_side[1]], count=1)
    else:
        construction["left_equal_tick"] = _draw_tick(ctx, points[left_side[0]], points[left_side[1]], count=1)
        construction["right_equal_tick"] = _draw_tick(ctx, points[right_side[0]], points[right_side[1]], count=1)
        construction["left_base_angle_mark"] = _draw_angle_arc(ctx, points[1], points[0], points[2], count=1)
        construction["right_base_angle_mark"] = _draw_angle_arc(ctx, points[2], points[0], points[1], count=1)
        readouts["left_angle_label"] = _draw_text_centered(ctx, labels["angle_a"], add_scaled(points[1], (65.0, -32.0)), small=True)
        readouts["right_angle_label"] = _draw_text_centered(ctx, labels["angle_b"], add_scaled(points[2], (-68.0, -32.0)), small=True)
    return vertices, point_labels, readouts, construction


def _render_quad(case: MarkedEquationCase, ctx: RenderContext, rng: Any) -> tuple[dict[str, Point], dict[str, BBox], dict[str, BBox], dict[str, BBox]]:
    """Draw quadrilateral equal-side or equal-angle constructions."""

    labels = dict(case.labels)
    points = tuple(ctx.scene_transform.points(_quad_points(ctx, rng)))
    vertices = {"A": points[0], "B": points[1], "C": points[2], "D": points[3]}
    construction = {"polygon": _draw_polygon(ctx, points)}
    point_labels = {key: bbox_to_list(value) for key, value in _draw_vertex_labels(ctx, points, ("A", "B", "C", "D")).items()}
    readouts: dict[str, BBox] = {}
    if case.draw_kind == "polygon_equal_sides":
        side_a = (0, 1)
        side_b = (2, 3)
        readouts["first_side_label"] = _draw_side_label(ctx, points, side_a, labels["left_side"], offset=-32.0)
        readouts["second_side_label"] = _draw_side_label(ctx, points, side_b, labels["right_side"], offset=33.0)
        construction["first_equal_tick"] = _draw_tick(ctx, points[side_a[0]], points[side_a[1]], count=2)
        construction["second_equal_tick"] = _draw_tick(ctx, points[side_b[0]], points[side_b[1]], count=2)
    else:
        construction["first_equal_angle_mark"] = _draw_angle_arc(ctx, points[0], points[1], points[3], count=2)
        construction["second_equal_angle_mark"] = _draw_angle_arc(ctx, points[2], points[1], points[3], count=2)
        readouts["first_angle_label"] = _draw_text_centered(ctx, labels["angle_a"], add_scaled(points[0], (58.0, 42.0)), small=True)
        readouts["second_angle_label"] = _draw_text_centered(ctx, labels["angle_b"], add_scaled(points[2], (-64.0, -38.0)), small=True)
    return vertices, point_labels, readouts, construction


def _render_marked_equation(case: MarkedEquationCase, ctx: RenderContext, *, instance_seed: int) -> RenderedMarkedEquationScene:
    """Draw one case after final layout jitter and return vertex-point annotation."""

    rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{case.construction_family}.layout")
    if case.draw_kind in {"equilateral_median_sides", "equilateral_median_right_angle", "isosceles_altitude_base_split"}:
        vertices, point_labels, readouts, construction = _render_split_triangle(case, ctx, rng)
    elif case.draw_kind in {"triangle_equal_sides", "equilateral_sides", "isosceles_base_angles"}:
        vertices, point_labels, readouts, construction = _render_basic_triangle(case, ctx, rng)
    else:
        vertices, point_labels, readouts, construction = _render_quad(case, ctx, rng)

    render_map = {
        "vertices": {label: point_to_list(point) for label, point in vertices.items()},
        "point_label_bboxes": dict(point_labels),
        "readout_bboxes": geometry_json_ready(readouts),
        "construction_bboxes": geometry_json_ready(construction),
    }
    scene_entities = (
        {
            "type": "marked_geometry_diagram",
            "shape_kind": str(case.shape_kind),
            "construction_family": str(case.construction_family),
            "render_map": dict(render_map),
        },
    )
    return RenderedMarkedEquationScene(
        image=ctx.image,
        annotation_points=dict(vertices),
        render_map=dict(render_map),
        scene_entities=scene_entities,
    )


def render_marked_equation_with_retries(
    *,
    case: MarkedEquationCase,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    max_attempts: int,
) -> tuple[RenderedMarkedEquationScene, dict[str, Any]]:
    """Render one case and retry only for layout/style failures."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            seed = int(instance_seed) + int(attempt)
            ctx = _make_render_context(
                instance_seed=seed,
                params=params,
                rendering_defaults=rendering_defaults,
            )
            rendered = _render_marked_equation(case, ctx, instance_seed=seed)
            render_meta = {
                "canvas_size": [int(ctx.width), int(ctx.height)],
                "coord_space": "pixel",
                "single_object_scene_rotation": ctx.scene_transform.metadata(),
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                },
            }
            return rendered, render_meta
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("failed to render marked polygon equation scene") from last_error


__all__ = ["render_marked_equation_with_retries"]
