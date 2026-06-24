"""Rendering primitives for split-triangle trigonometric side-length diagrams."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    draw_label_backplate,
    pad_bbox,
    readout_text_metadata,
)
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import (
    add_scaled,
    mid,
    perp,
    point_to_list,
    sub,
    unit,
)
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from .state import BBox, Point, RenderContext, RenderedSplitTriangleTrigScene, SCENE_ID, SplitTriangleTrigCase

RENDER_ALTITUDE_WITH_TWO_ANGLES = "altitude_with_two_angles"
RENDER_SIDE_TO_HYPOTENUSE = "side_to_hypotenuse"
RENDER_ISOSCELES_ALTITUDE = "isosceles_altitude"


def create_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> RenderContext:
    """Create one styled drawing context with scene-level rotation support."""

    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 580)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=False,
        require_grid=False,
    )
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 3)))
    label_stroke_width = int(params.get("label_stroke_width", group_default(render_defaults, "label_stroke_width", 1)))
    image = image.convert("RGB")
    return RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        label_backing_color=tuple(int(value) for value in diagram_style.panel_fill_rgb),
        fill_color=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        alt_fill_color=tuple(int(value) for value in diagram_style.option_fill_rgb),
        muted_color=tuple(int(value) for value in diagram_style.guide_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, min(1, int(label_stroke_width))),
        font=load_font(max(12, int(font_size)), bold=False),
        small_font=load_font(max(10, int(small_font_size)), bold=False),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_rotation"),
            params=params,
            render_defaults=render_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _segment_label_offset(a: Point, b: Point, distance: float) -> Point:
    normal = perp(unit(sub(b, a)))
    return normal[0] * float(distance), normal[1] * float(distance)


def _line_bbox(points: Sequence[Point], ctx: RenderContext, *, pad: float = 5.0) -> BBox:
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=pad)


def _draw_text_centered(
    ctx: RenderContext,
    text: str,
    center: Point,
    *,
    small: bool = True,
    required: bool = True,
) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    draw_label_backplate(ctx, bbox)
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
        required=bool(required),
        extra_metadata=readout_text_metadata(ctx, ctx.label_color),
    )
    return pad_bbox(bbox, 4.0, width=ctx.width, height=ctx.height)


def _draw_polygon(ctx: RenderContext, points: Sequence[Point], *, fill: tuple[int, int, int] | None = None) -> BBox:
    polygon = [(float(x), float(y)) for x, y in points]
    ctx.draw.polygon(polygon, fill=fill or ctx.fill_color)
    ctx.draw.line(polygon + [polygon[0]], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    return bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_segment(ctx: RenderContext, a: Point, b: Point, *, color: tuple[int, int, int] | None = None) -> BBox:
    ctx.draw.line((a, b), fill=color or ctx.secondary_color, width=ctx.line_width)
    return _line_bbox((a, b), ctx, pad=ctx.line_width + 3)


def _draw_side_label(ctx: RenderContext, a: Point, b: Point, text: str, *, offset: float) -> BBox:
    return _draw_text_centered(ctx, str(text), add_scaled(mid(a, b), _segment_label_offset(a, b, offset), 1.0), small=True)


def _draw_point_label(ctx: RenderContext, label: str, point: Point, direction: Point, *, offset: float = 22.0) -> BBox:
    return _draw_text_centered(ctx, str(label), add_scaled(point, unit(direction), offset), small=True, required=False)


def _draw_tick(ctx: RenderContext, a: Point, b: Point, *, count: int = 1) -> BBox:
    center = mid(a, b)
    tangent = unit(sub(b, a))
    normal = perp(tangent)
    tick_points: list[Point] = []
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * 9.0
        tick_center = add_scaled(center, tangent, shift)
        p0 = add_scaled(tick_center, normal, -9.0)
        p1 = add_scaled(tick_center, normal, 9.0)
        ctx.draw.line((p0, p1), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        tick_points.extend([p0, p1])
    return _line_bbox(tick_points, ctx, pad=4.0)


def _draw_right_angle(ctx: RenderContext, vertex: Point, ray_a: Point, ray_b: Point, *, size: float = 20.0) -> BBox:
    u = unit(sub(ray_a, vertex))
    v = unit(sub(ray_b, vertex))
    p1 = add_scaled(vertex, u, size)
    p2 = add_scaled(p1, v, size)
    p3 = add_scaled(vertex, v, size)
    ctx.draw.line((p1, p2, p3), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    return _line_bbox((p1, p2, p3), ctx, pad=4.0)


def _angle_label_point(vertex: Point, ray_a: Point, ray_b: Point, radius: float = 42.0) -> Point:
    direction = unit(add_scaled(unit(sub(ray_a, vertex)), unit(sub(ray_b, vertex)), 1.0))
    if math.hypot(direction[0], direction[1]) <= 1e-9:
        direction = perp(unit(sub(ray_a, vertex)))
    return add_scaled(vertex, direction, radius)


def _draw_angle_label(
    ctx: RenderContext,
    text: str,
    vertex: Point,
    ray_a: Point,
    ray_b: Point,
    *,
    radius: float = 42.0,
) -> tuple[BBox, Point]:
    point = _angle_label_point(vertex, ray_a, ray_b, radius=radius)
    bbox = _draw_text_centered(ctx, str(text), point, small=True)
    return bbox, point


def _right_triangle_points(ctx: RenderContext, *, instance_seed: int) -> dict[str, Point]:
    """Sample and transform the four labeled construction points."""

    rng = spawn_rng(int(instance_seed), "split_triangle.right_points")
    base_y = ctx.height * 0.76 + rng.uniform(-12.0, 12.0)
    left = (ctx.width * 0.18 + rng.uniform(-10.0, 12.0), base_y)
    right = (ctx.width * 0.82 + rng.uniform(-12.0, 10.0), base_y + rng.uniform(-4.0, 4.0))
    foot = (ctx.width * 0.50 + rng.uniform(-20.0, 20.0), base_y)
    top = (foot[0] + rng.uniform(-8.0, 8.0), ctx.height * 0.20 + rng.uniform(-8.0, 12.0))
    raw_points = {"A": top, "B": left, "C": right, "D": foot}
    transformed = ctx.scene_transform.points(tuple(raw_points.values()))
    return {key: value for key, value in zip(raw_points.keys(), transformed)}


def draw_split_triangle_trig_scene(
    *,
    case: SplitTriangleTrigCase,
    ctx: RenderContext,
    instance_seed: int,
) -> RenderedSplitTriangleTrigScene:
    """Render one selected trig case without knowing public task identity."""

    points = _right_triangle_points(ctx, instance_seed=int(instance_seed))
    labels = dict(case.labels)
    construction: dict[str, BBox] = {
        "left_triangle": _draw_polygon(ctx, (points["A"], points["B"], points["D"]), fill=ctx.fill_color),
        "right_triangle": _draw_polygon(ctx, (points["A"], points["D"], points["C"]), fill=ctx.alt_fill_color),
        "altitude": _draw_segment(ctx, points["A"], points["D"], color=ctx.secondary_color),
        "right_angle": _draw_right_angle(ctx, points["D"], points["A"], points["C"], size=20.0),
    }
    if case.render_kind == RENDER_ISOSCELES_ALTITUDE:
        construction["left_side_tick"] = _draw_tick(ctx, points["A"], points["B"], count=1)
        construction["right_side_tick"] = _draw_tick(ctx, points["A"], points["C"], count=1)
        construction["left_base_tick"] = _draw_tick(ctx, points["B"], points["D"], count=2)
        construction["right_base_tick"] = _draw_tick(ctx, points["D"], points["C"], count=2)

    point_label_bboxes = {
        label: bbox_to_list(_draw_point_label(ctx, label, points[label], direction))
        for label, direction in (("A", (0.0, -1.0)), ("B", (-1.0, 1.0)), ("C", (1.0, 1.0)), ("D", (0.0, 1.0)))
    }
    readout_bboxes: dict[str, BBox] = {}
    if "BD" in labels and labels["BD"] != "?":
        readout_bboxes["BD"] = _draw_side_label(ctx, points["B"], points["D"], labels["BD"], offset=32.0)
    if "AB" in labels and labels["AB"] != "?":
        readout_bboxes["AB"] = _draw_side_label(ctx, points["A"], points["B"], labels["AB"], offset=-36.0)
    if "AC" in labels and labels["AC"] != "?":
        readout_bboxes["AC"] = _draw_side_label(ctx, points["A"], points["C"], labels["AC"], offset=36.0)
    if "angle_B" in labels:
        _draw_angle_label(ctx, labels["angle_B"], points["B"], points["A"], points["D"], radius=52.0)
    if "angle_C" in labels:
        _draw_angle_label(ctx, labels["angle_C"], points["C"], points["D"], points["A"], radius=52.0)
    if case.target_name == "AC":
        readout_bboxes["target_AC"] = _draw_side_label(ctx, points["A"], points["C"], "?", offset=36.0)
    else:
        readout_bboxes["target_AB"] = _draw_side_label(ctx, points["A"], points["B"], "?", offset=-36.0)

    render_map = {
        "vertices": {key: point_to_list(value) for key, value in points.items()},
        "point_label_bboxes": dict(point_label_bboxes),
        "construction_bboxes": geometry_json_ready(construction),
        "readout_bboxes": geometry_json_ready(readout_bboxes),
        "single_object_scene_rotation": ctx.scene_transform.metadata(),
        "style": {
            "technical_diagram": dict(ctx.diagram_style_meta),
            "background": dict(ctx.background_meta),
        },
    }
    return RenderedSplitTriangleTrigScene(
        image=ctx.image,
        annotation_points=dict(points),
        render_map=dict(render_map),
    )


__all__ = [
    "RENDER_ALTITUDE_WITH_TWO_ANGLES",
    "RENDER_ISOSCELES_ALTITUDE",
    "RENDER_SIDE_TO_HYPOTENUSE",
    "create_render_context",
    "draw_split_triangle_trig_scene",
]
