"""Rendering primitives for split-triangle angle-chase diagrams."""

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

from .state import BBox, Point, RenderContext, RenderedSplitTriangleScene, SCENE_ID, SplitTriangleAngleCase

RENDER_SINGLE_CEVIAN = "single_cevian"
RENDER_SHARED_VERTEX = "shared_vertex_split"
RENDER_TWO_STEP_ADJACENT = "two_step_adjacent"


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


def _draw_point_label(ctx: RenderContext, label: str, point: Point, direction: Point, *, offset: float = 22.0) -> BBox:
    return _draw_text_centered(ctx, str(label), add_scaled(point, unit(direction), offset), small=True, required=False)


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


def _split_triangle_points(ctx: RenderContext, *, instance_seed: int) -> dict[str, Point]:
    """Sample and transform the four visible vertices for the scene grammar."""

    rng = spawn_rng(int(instance_seed), "split_triangle.points")
    top_y = ctx.height * 0.22 + rng.uniform(-12.0, 12.0)
    left_x = ctx.width * 0.18 + rng.uniform(-10.0, 16.0)
    right_x = ctx.width * 0.82 + rng.uniform(-16.0, 10.0)
    split_x = ctx.width * 0.50 + rng.uniform(-32.0, 32.0)
    apex = (ctx.width * 0.50 + rng.uniform(-18.0, 18.0), ctx.height * 0.78 + rng.uniform(-14.0, 12.0))
    raw_points = {
        "A": (left_x, top_y),
        "B": (split_x, top_y + rng.uniform(-4.0, 4.0)),
        "C": (right_x, top_y),
        "D": apex,
    }
    transformed = ctx.scene_transform.points(tuple(raw_points.values()))
    return {key: value for key, value in zip(raw_points.keys(), transformed)}


def draw_split_triangle_scene(
    *,
    case: SplitTriangleAngleCase,
    ctx: RenderContext,
    instance_seed: int,
) -> RenderedSplitTriangleScene:
    """Render one selected theorem case without knowing public task identity."""

    points = _split_triangle_points(ctx, instance_seed=int(instance_seed))
    labels = dict(case.labels)
    construction_bboxes: dict[str, BBox] = {
        "left_triangle": _draw_polygon(ctx, (points["A"], points["B"], points["D"]), fill=ctx.fill_color),
        "right_triangle": _draw_polygon(ctx, (points["B"], points["C"], points["D"]), fill=ctx.alt_fill_color),
        "split_segment": _draw_segment(ctx, points["B"], points["D"], color=ctx.secondary_color),
    }
    point_label_bboxes = {
        "A": bbox_to_list(_draw_point_label(ctx, "A", points["A"], (-1.0, -1.0))),
        "B": bbox_to_list(_draw_point_label(ctx, "B", points["B"], (0.0, -1.0))),
        "C": bbox_to_list(_draw_point_label(ctx, "C", points["C"], (1.0, -1.0))),
        "D": bbox_to_list(_draw_point_label(ctx, "D", points["D"], (0.0, 1.0))),
    }
    readout_bboxes: dict[str, Any] = {}
    if case.render_kind == RENDER_SINGLE_CEVIAN:
        _draw_angle_label(ctx, labels["given_left_A"], points["A"], points["B"], points["D"], radius=50.0)
        _draw_angle_label(ctx, labels["given_left_B"], points["B"], points["A"], points["D"], radius=50.0)
        _draw_angle_label(ctx, labels["target"], points["D"], points["A"], points["B"], radius=58.0)
    elif case.render_kind == RENDER_SHARED_VERTEX:
        _draw_angle_label(ctx, labels["given_left_A"], points["A"], points["B"], points["D"], radius=50.0)
        _draw_angle_label(ctx, labels["given_left_D"], points["D"], points["A"], points["B"], radius=58.0)
        _draw_angle_label(ctx, labels["target"], points["B"], points["A"], points["D"], radius=50.0)
    elif case.render_kind == RENDER_TWO_STEP_ADJACENT:
        _draw_angle_label(ctx, labels["given_left_A"], points["A"], points["B"], points["D"], radius=50.0)
        _draw_angle_label(ctx, labels["given_left_D"], points["D"], points["A"], points["B"], radius=58.0)
        _draw_angle_label(ctx, labels["given_right_C"], points["C"], points["B"], points["D"], radius=50.0)
        _draw_angle_label(ctx, labels["target"], points["D"], points["B"], points["C"], radius=58.0)
    else:
        raise ValueError(f"unknown split-triangle render kind: {case.render_kind}")

    render_map = {
        "vertices": {key: point_to_list(value) for key, value in points.items()},
        "point_label_bboxes": dict(point_label_bboxes),
        "construction_bboxes": geometry_json_ready(construction_bboxes),
        "readout_bboxes": geometry_json_ready(readout_bboxes),
        "single_object_scene_rotation": ctx.scene_transform.metadata(),
        "style": {
            "technical_diagram": dict(ctx.diagram_style_meta),
            "background": dict(ctx.background_meta),
        },
    }
    return RenderedSplitTriangleScene(
        image=ctx.image,
        annotation_points=dict(points),
        render_map=dict(render_map),
    )


__all__ = [
    "RENDER_SHARED_VERTEX",
    "RENDER_SINGLE_CEVIAN",
    "RENDER_TWO_STEP_ADJACENT",
    "create_render_context",
    "draw_split_triangle_scene",
]
