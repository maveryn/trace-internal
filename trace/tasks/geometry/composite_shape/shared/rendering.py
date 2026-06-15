"""Rendering primitives for composite-shape geometry scenes."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import (
    GEOMETRY_STYLE_PROFILE_ANALYTICAL_DIAGRAM,
    prepare_geometry_diagram_style_and_background,
)
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    draw_right_angle_marker,
    draw_label,
    fmt_measure,
    pad_bbox,
)
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from .defaults import SCENE_ID
from .state import BBox, Color, CompositeRenderContext, CompositeShapeProblem, Point, RenderedCompositeShape
from .styles import resolve_composite_shape_style


def create_composite_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    render_namespace: str,
) -> tuple[CompositeRenderContext, Dict[str, Any]]:
    """Resolve canvas, background, palette, and readout font choices."""

    rng = spawn_rng(int(instance_seed), f"{render_namespace}.render")
    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 760)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(width),
        canvas_height=int(height),
        require_grid=False,
        style_profile=GEOMETRY_STYLE_PROFILE_ANALYTICAL_DIAGRAM,
    )
    composite_style = resolve_composite_shape_style(
        instance_seed=int(instance_seed),
        params=params,
        render_namespace=str(render_namespace),
        diagram_style=diagram_style,
        background_meta=background_meta,
    )
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
    label_stroke_width = int(params.get("label_stroke_width", group_default(render_defaults, "label_stroke_width", 1)))
    ctx = CompositeRenderContext(
        rng=rng,
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        background_color=tuple(int(value) for value in diagram_style.canvas_rgb),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        label_color=tuple(int(value) for value in composite_style.label_color),
        label_stroke_color=tuple(int(value) for value in composite_style.label_stroke_color),
        accent_color=tuple(int(value) for value in composite_style.accent_color),
        fill_color=tuple(int(value) for value in composite_style.fill_color),
        secondary_fill_color=tuple(int(value) for value in composite_style.secondary_fill_color),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, int(label_stroke_width)),
        font=load_font(max(12, int(font_size))),
        small_font=load_font(max(10, int(small_font_size))),
        scene_transform=LazySceneTransform(
            rng,
            params=params,
            render_defaults=render_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )
    render_meta = {
        "background_style": dict(background_meta),
        "diagram_style": dict(diagram_style_meta),
        "line_width": int(ctx.line_width),
        "label_font_size": int(font_size),
        "small_label_font_size": int(small_font_size),
        "label_stroke_width": int(ctx.label_stroke_width),
        "fill_color": list(ctx.fill_color),
        "secondary_fill_color": list(ctx.secondary_fill_color),
        "accent_color": list(ctx.accent_color),
        "composite_fill_style": dict(composite_style.metadata),
    }
    return ctx, render_meta


def _place_points(ctx: CompositeRenderContext, points: Sequence[Point]) -> tuple[Point, ...]:
    """Apply the optional scene-level rigid transform before drawing/annotation."""

    resolved = tuple((float(point[0]), float(point[1])) for point in points)
    if ctx.scene_transform is None:
        return resolved
    return ctx.scene_transform.points(resolved)


def _place_point(ctx: CompositeRenderContext, point: Point) -> Point:
    if ctx.scene_transform is None:
        return (float(point[0]), float(point[1]))
    return ctx.scene_transform.point((float(point[0]), float(point[1])))


def _draw_text(
    ctx: CompositeRenderContext,
    text: str,
    center: Point,
    *,
    font: Any | None = None,
    fill: Color | None = None,
    stroke_width: int | None = None,
) -> BBox:
    active_font = font if font is not None else ctx.font
    active_fill = fill if fill is not None else ctx.label_color
    active_stroke_width = int(ctx.label_stroke_width if stroke_width is None else stroke_width)
    x, y = float(center[0]), float(center[1])
    draw_text_traced(
        ctx.draw,
        (x, y),
        str(text),
        anchor="mm",
        font=active_font,
        fill=active_fill,
        stroke_width=max(0, int(active_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    bbox = ctx.draw.textbbox(
        (x, y),
        str(text),
        anchor="mm",
        font=active_font,
        stroke_width=max(0, int(active_stroke_width)),
    )
    return pad_bbox(bbox, 2.0, width=ctx.width, height=ctx.height)


def _draw_segment_label(ctx: CompositeRenderContext, text: str, a: Point, b: Point, *, offset: float = 24.0) -> BBox:
    dx = float(b[0]) - float(a[0])
    dy = float(b[1]) - float(a[1])
    length = max(1.0, math.hypot(dx, dy))
    nx = -dy / length
    ny = dx / length
    center = (
        (float(a[0]) + float(b[0])) / 2.0 + nx * float(offset),
        (float(a[1]) + float(b[1])) / 2.0 + ny * float(offset),
    )
    return _draw_text(ctx, str(text), center)


def _draw_point_label_outward(
    ctx: CompositeRenderContext,
    label: str,
    point: Point,
    *,
    center: Point,
    distance: float = 24.0,
) -> BBox:
    dx = float(point[0]) - float(center[0])
    dy = float(point[1]) - float(center[1])
    length = max(1.0, math.hypot(dx, dy))
    label_center = (
        float(point[0]) + (dx / length) * float(distance),
        float(point[1]) + (dy / length) * float(distance),
    )
    return _draw_text(ctx, str(label), label_center, font=ctx.small_font)


def _draw_labeled_points(
    ctx: CompositeRenderContext,
    points: Mapping[str, Point],
    *,
    center: Point | None = None,
    distance: float = 24.0,
) -> tuple[dict[str, Point], dict[str, BBox]]:
    """Draw visible point labels and return the same final points for annotation."""

    point_items = [(str(label), (float(point[0]), float(point[1]))) for label, point in points.items()]
    if center is None:
        center = (
            sum(point[0] for _label, point in point_items) / max(1, len(point_items)),
            sum(point[1] for _label, point in point_items) / max(1, len(point_items)),
        )
    label_bboxes: dict[str, BBox] = {}
    keyed_points: dict[str, Point] = {}
    for label, point in point_items:
        keyed_points[label] = point
        label_bboxes[label] = _draw_point_label_outward(ctx, label, point, center=center, distance=distance)
    return keyed_points, label_bboxes


def _draw_point_marker(ctx: CompositeRenderContext, point: Point, *, radius: float = 4.0) -> BBox:
    x, y = float(point[0]), float(point[1])
    bbox = (x - float(radius), y - float(radius), x + float(radius), y + float(radius))
    ctx.draw.ellipse(bbox, fill=ctx.line_color)
    return pad_bbox(bbox, 2.0, width=ctx.width, height=ctx.height)


def _draw_polygon(
    ctx: CompositeRenderContext,
    points: Sequence[Point],
    *,
    fill: Color | None = None,
    outline: Color | None = None,
    width: int | None = None,
) -> BBox:
    if fill is not None:
        ctx.draw.polygon([(float(x), float(y)) for x, y in points], fill=fill)
    line_fill = outline if outline is not None else ctx.line_color
    line_width = int(width if width is not None else ctx.line_width)
    closed = list(points) + [points[0]]
    ctx.draw.line([(float(x), float(y)) for x, y in closed], fill=line_fill, width=line_width, joint="curve")
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=line_width + 2)


def _draw_dimension(
    ctx: CompositeRenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    label_offset: Point = (0.0, 0.0),
) -> BBox:
    ctx.draw.line([start, end], fill=ctx.label_color, width=max(2, ctx.line_width - 1))
    tick = 7.0
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length > 1e-9:
        nx = -dy / length
        ny = dx / length
        for point in (start, end):
            ctx.draw.line(
                [
                    (float(point[0]) - tick * nx, float(point[1]) - tick * ny),
                    (float(point[0]) + tick * nx, float(point[1]) + tick * ny),
                ],
                fill=ctx.label_color,
                width=max(2, ctx.line_width - 1),
            )
    center = (
        (float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]),
        (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]),
    )
    return draw_label(ctx, label, center, small=True)


def _vector_from(vertex: Point, endpoint: Point) -> Point:
    return (float(endpoint[0]) - float(vertex[0]), float(endpoint[1]) - float(vertex[1]))


def _draw_right_angle_notation(
    ctx: CompositeRenderContext,
    vertex: Point,
    arm_a: Point,
    arm_b: Point,
    *,
    side_px: float | None = None,
) -> BBox:
    return draw_right_angle_marker(
        ctx,
        vertex,
        arm_a=_vector_from(vertex, arm_a),
        arm_b=_vector_from(vertex, arm_b),
        side_px=float(side_px) if side_px is not None else max(12.0, float(ctx.line_width) * 3.5),
        color=ctx.line_color,
        width=max(1, int(ctx.line_width) - 2),
    )


def _draw_polygon_right_angle_notation(
    ctx: CompositeRenderContext,
    points: Sequence[Point],
    *,
    key_prefix: str,
) -> dict[str, BBox]:
    bboxes: dict[str, BBox] = {}
    point_list = list(points)
    for index, vertex in enumerate(point_list):
        bboxes[f"{key_prefix}_{index}_right_angle"] = _draw_right_angle_notation(
            ctx,
            vertex,
            point_list[index - 1],
            point_list[(index + 1) % len(point_list)],
        )
    return bboxes


def _draw_equal_side_ticks(
    ctx: CompositeRenderContext,
    a: Point,
    b: Point,
    *,
    count: int,
) -> BBox:
    dx = float(b[0]) - float(a[0])
    dy = float(b[1]) - float(a[1])
    length = max(1.0, math.hypot(dx, dy))
    ux = dx / length
    uy = dy / length
    nx = -uy
    ny = ux
    center_x = (float(a[0]) + float(b[0])) / 2.0
    center_y = (float(a[1]) + float(b[1])) / 2.0
    tick_len = max(12.0, float(ctx.line_width) * 3.5)
    spacing = max(5.0, float(ctx.line_width) * 1.6)
    drawn_points: list[Point] = []
    for index in range(max(1, int(count))):
        along = (float(index) - (float(count) - 1.0) / 2.0) * spacing
        cx = center_x + ux * along
        cy = center_y + uy * along
        start = (cx - nx * tick_len / 2.0, cy - ny * tick_len / 2.0)
        end = (cx + nx * tick_len / 2.0, cy + ny * tick_len / 2.0)
        ctx.draw.line([start, end], fill=ctx.line_color, width=max(2, int(ctx.line_width) - 1))
        drawn_points.extend([start, end])
    return bbox_from_points(drawn_points, width=ctx.width, height=ctx.height, pad=4.0)


def _render_rect_cut(ctx: CompositeRenderContext, problem: CompositeShapeProblem) -> RenderedCompositeShape:
    """Draw a rectangle with a visible triangular cutout for area subtraction."""

    values = dict(problem.dimensions)
    width_value = int(values["width"])
    height_value = int(values["height"])
    cut_base = int(values["cut_base"])
    cut_height = int(values["cut_height"])
    left, top = 150.0, 135.0
    w_px = 390.0
    h_px = 270.0
    raw_rect = [(left, top), (left + w_px, top), (left + w_px, top + h_px), (left, top + h_px)]
    raw_tri = [
        (left + w_px, top + h_px),
        (left + w_px - (w_px * cut_base / width_value), top + h_px),
        (left + w_px, top + h_px - (h_px * cut_height / height_value)),
    ]
    placed = _place_points(ctx, [*raw_rect, *raw_tri])
    rect = list(placed[:4])
    tri = list(placed[4:7])
    _draw_polygon(ctx, rect, fill=ctx.fill_color)
    ctx.draw.polygon([(float(x), float(y)) for x, y in tri], fill=ctx.background_color)
    _draw_polygon(ctx, rect)
    _draw_polygon(ctx, tri, outline=ctx.accent_color, width=max(2, ctx.line_width - 1))
    notation_bboxes = {
        **_draw_polygon_right_angle_notation(ctx, rect, key_prefix="outer_corner"),
        "cutout_right_angle": _draw_right_angle_notation(ctx, tri[0], tri[1], tri[2]),
    }
    region_bbox = bbox_from_points(rect, width=ctx.width, height=ctx.height, pad=2.0)
    cutout_bbox = bbox_from_points(tri, width=ctx.width, height=ctx.height, pad=4.0)
    label_bboxes = {
        "outer_width": _draw_segment_label(ctx, str(width_value), rect[3], rect[2], offset=-30.0),
        "outer_height": _draw_segment_label(ctx, str(height_value), rect[0], rect[3], offset=-26.0),
        "cutout_base": _draw_segment_label(ctx, str(cut_base), tri[1], tri[0], offset=24.0),
        "cutout_height": _draw_segment_label(ctx, str(cut_height), tri[0], tri[2], offset=25.0),
    }
    annotation_points, point_label_bboxes = _draw_labeled_points(
        ctx,
        {
            "A": rect[0],
            "B": rect[1],
            "C": rect[2],
            "D": rect[3],
            "E": tri[1],
            "F": tri[2],
        },
        center=((rect[0][0] + rect[2][0]) / 2.0, (rect[0][1] + rect[2][1]) / 2.0),
    )
    return RenderedCompositeShape(
        image=ctx.image,
        answer_value=problem.answer_value,
        annotation_roles=tuple(annotation_points),
        annotation_keyed_points=annotation_points,
        scene_entities=(
            {
                "type": "rectangle_with_triangular_cutout",
                "outer": rect,
                "cutout": tri,
                "points": dict(annotation_points),
            },
        ),
        render_map={
            "outer_region_bbox": bbox_to_list(region_bbox),
            "cutout_region_bbox": bbox_to_list(cutout_bbox),
            "measurement_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in label_bboxes.items()},
            "point_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in point_label_bboxes.items()},
            "visual_notation_bboxes": {key: bbox_to_list(bbox) for key, bbox in notation_bboxes.items()},
            "coord_space": "pixel",
        },
        witness={
            "outer_width": width_value,
            "outer_height": height_value,
            "cutout_base": cut_base,
            "cutout_height": cut_height,
            "answer_area": int(problem.answer_value),
        },
    )


def _render_l_profile(ctx: CompositeRenderContext, problem: CompositeShapeProblem) -> RenderedCompositeShape:
    """Draw an L-shaped region with a missing-corner witness bbox."""

    values = dict(problem.dimensions)
    width_value = int(values["width"])
    height_value = int(values["height"])
    cut_width = int(values["cut_width"])
    cut_height = int(values["cut_height"])
    left, top = 145.0, 125.0
    w_px, h_px = 420.0, 300.0
    cut_w_px = w_px * cut_width / width_value
    cut_h_px = h_px * cut_height / height_value
    raw_pts = [
        (left, top),
        (left + w_px, top),
        (left + w_px, top + h_px - cut_h_px),
        (left + w_px - cut_w_px, top + h_px - cut_h_px),
        (left + w_px - cut_w_px, top + h_px),
        (left, top + h_px),
    ]
    raw_cutout_corner = (raw_pts[2][0], raw_pts[4][1])
    placed = _place_points(ctx, [*raw_pts, raw_cutout_corner])
    pts = list(placed[:6])
    cutout_corner = placed[6]
    _draw_polygon(ctx, pts, fill=ctx.fill_color)
    _draw_polygon(ctx, pts)
    notation_bboxes = _draw_polygon_right_angle_notation(ctx, pts, key_prefix="corner")
    cutout_rect = [pts[3], pts[2], cutout_corner, pts[4]]
    region_bbox = bbox_from_points(pts, width=ctx.width, height=ctx.height, pad=2.0)
    cutout_bbox = bbox_from_points(cutout_rect, width=ctx.width, height=ctx.height, pad=4.0)
    label_bboxes = {
        "outer_width": _draw_segment_label(ctx, str(width_value), pts[0], pts[1], offset=-30.0),
        "outer_height": _draw_segment_label(ctx, str(height_value), pts[0], pts[5], offset=-26.0),
        "missing_width": _draw_segment_label(ctx, str(cut_width), pts[3], pts[2], offset=-24.0),
        "missing_height": _draw_segment_label(ctx, str(cut_height), pts[3], pts[4], offset=25.0),
    }
    annotation_points, point_label_bboxes = _draw_labeled_points(
        ctx,
        {label: point for label, point in zip(("A", "B", "C", "D", "E", "F"), pts)},
    )
    return RenderedCompositeShape(
        image=ctx.image,
        answer_value=problem.answer_value,
        annotation_roles=tuple(annotation_points),
        annotation_keyed_points=annotation_points,
        scene_entities=({"type": "rectilinear_corner_cutout", "outline": pts, "points": dict(annotation_points)},),
        render_map={
            "outer_region_bbox": bbox_to_list(region_bbox),
            "missing_corner_bbox": bbox_to_list(cutout_bbox),
            "measurement_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in label_bboxes.items()},
            "point_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in point_label_bboxes.items()},
            "visual_notation_bboxes": {key: bbox_to_list(bbox) for key, bbox in notation_bboxes.items()},
            "coord_space": "pixel",
        },
        witness={
            "outer_width": width_value,
            "outer_height": height_value,
            "missing_width": cut_width,
            "missing_height": cut_height,
            "answer_area": int(problem.answer_value),
        },
    )


def _render_house(ctx: CompositeRenderContext, problem: CompositeShapeProblem) -> RenderedCompositeShape:
    """Draw a pentagonal house outline for boundary-perimeter reasoning."""

    values = dict(problem.dimensions)
    width_value = int(values["width"])
    wall_height = int(values["wall_height"])
    roof_side = int(values["roof_side"])
    roof_height_units = math.sqrt(max(1.0, float(roof_side) ** 2 - (float(width_value) / 2.0) ** 2))
    scale = min(
        26.0,
        (float(ctx.width) - 220.0) / max(1.0, float(width_value)),
        (float(ctx.height) - 170.0) / max(1.0, float(wall_height) + roof_height_units),
    )
    scale = max(8.0, float(scale))
    w_px = float(width_value) * scale
    half_w = w_px / 2.0
    roof_h = math.sqrt(max(1.0, (float(roof_side) * scale) ** 2 - (half_w**2)))
    left = (float(ctx.width) - w_px) / 2.0
    base_y = 78.0 + (float(wall_height) * scale) + roof_h
    raw_a = (left, base_y)
    raw_b = (left + w_px, base_y)
    raw_c = (left + w_px, base_y - (float(wall_height) * scale))
    raw_d = (left + w_px / 2.0, raw_c[1] - roof_h)
    raw_e = (left, raw_c[1])
    a, b, c, d, e = _place_points(ctx, (raw_a, raw_b, raw_c, raw_d, raw_e))
    pts = [a, b, c, d, e]
    _draw_polygon(ctx, pts, fill=ctx.fill_color)
    _draw_polygon(ctx, pts)
    notation_bboxes = {
        "left_base_wall_right_angle": _draw_right_angle_notation(ctx, a, b, e),
        "right_base_wall_right_angle": _draw_right_angle_notation(ctx, b, a, c),
        "left_wall_equal_tick": _draw_equal_side_ticks(ctx, a, e, count=1),
        "right_wall_equal_tick": _draw_equal_side_ticks(ctx, b, c, count=1),
        "left_roof_equal_tick": _draw_equal_side_ticks(ctx, e, d, count=2),
        "right_roof_equal_tick": _draw_equal_side_ticks(ctx, c, d, count=2),
    }
    target_bbox = bbox_from_points(pts, width=ctx.width, height=ctx.height, pad=4.0)
    label_bboxes = {
        "base_length_AB": _draw_segment_label(ctx, str(width_value), a, b, offset=25.0),
        "wall_height_AE": _draw_segment_label(ctx, str(wall_height), a, e, offset=-25.0),
        "roof_side_CD": _draw_segment_label(ctx, str(roof_side), d, c, offset=28.0),
    }
    annotation_points, point_label_bboxes = _draw_labeled_points(
        ctx,
        {"A": a, "B": b, "C": c, "D": d, "E": e},
    )
    return RenderedCompositeShape(
        image=ctx.image,
        answer_value=problem.answer_value,
        annotation_roles=tuple(annotation_points),
        annotation_keyed_points=annotation_points,
        scene_entities=({"type": "pentagonal_house_outline", "points": dict(annotation_points)},),
        render_map={
            "target_boundary_bbox": bbox_to_list(target_bbox),
            "measurement_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in label_bboxes.items()},
            "point_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in point_label_bboxes.items()},
            "visual_notation_bboxes": {key: bbox_to_list(bbox) for key, bbox in notation_bboxes.items()},
            "coord_space": "pixel",
        },
        witness={
            "AB": width_value,
            "AE": wall_height,
            "CD_equals_DE": roof_side,
            "BC_equals_AE": True,
            "answer_perimeter": int(problem.answer_value),
        },
    )


def _render_tabbed(ctx: CompositeRenderContext, problem: CompositeShapeProblem) -> RenderedCompositeShape:
    """Draw a rectilinear tabbed outline for perimeter reasoning."""

    values = dict(problem.dimensions)
    width_value = int(values["width"])
    height_value = int(values["height"])
    tab_height = int(values["tab_height"])
    scale = min(
        25.0,
        (float(ctx.width) - 220.0) / max(1.0, float(width_value)),
        (float(ctx.height) - 170.0) / max(1.0, float(height_value + tab_height)),
    )
    scale = max(8.0, float(scale))
    w_px, h_px, tab_h_px = float(width_value) * scale, float(height_value) * scale, float(tab_height) * scale
    tab_w_px = w_px * 0.42
    left = (float(ctx.width) - w_px) / 2.0
    bottom = 78.0 + h_px + tab_h_px
    x0 = left + (w_px - tab_w_px) / 2.0
    x1 = x0 + tab_w_px
    raw_pts = [
        (left, bottom),
        (left + w_px, bottom),
        (left + w_px, bottom - h_px),
        (x1, bottom - h_px),
        (x1, bottom - h_px - tab_h_px),
        (x0, bottom - h_px - tab_h_px),
        (x0, bottom - h_px),
        (left, bottom - h_px),
    ]
    pts = list(_place_points(ctx, raw_pts))
    _draw_polygon(ctx, pts, fill=ctx.fill_color)
    _draw_polygon(ctx, pts)
    notation_bboxes = _draw_polygon_right_angle_notation(ctx, pts, key_prefix="corner")
    target_bbox = bbox_from_points(pts, width=ctx.width, height=ctx.height, pad=4.0)
    label_bboxes = {
        "overall_width": _draw_segment_label(ctx, str(width_value), pts[0], pts[1], offset=25.0),
        "main_height": _draw_segment_label(ctx, str(height_value), pts[0], pts[7], offset=-25.0),
        "tab_height": _draw_segment_label(ctx, str(tab_height), pts[3], pts[4], offset=26.0),
    }
    annotation_points, point_label_bboxes = _draw_labeled_points(
        ctx,
        {label: point for label, point in zip(("A", "B", "C", "D", "E", "F", "G", "H"), pts)},
        distance=22.0,
    )
    return RenderedCompositeShape(
        image=ctx.image,
        answer_value=problem.answer_value,
        annotation_roles=tuple(annotation_points),
        annotation_keyed_points=annotation_points,
        scene_entities=({"type": "tabbed_rectilinear_polygon", "outline": pts, "points": dict(annotation_points)},),
        render_map={
            "target_boundary_bbox": bbox_to_list(target_bbox),
            "measurement_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in label_bboxes.items()},
            "point_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in point_label_bboxes.items()},
            "visual_notation_bboxes": {key: bbox_to_list(bbox) for key, bbox in notation_bboxes.items()},
            "coord_space": "pixel",
        },
        witness={
            "overall_width": width_value,
            "main_height": height_value,
            "tab_height": tab_height,
            "answer_perimeter": int(problem.answer_value),
        },
    )


def _boundary_width(ctx: CompositeRenderContext) -> int:
    return max(int(ctx.line_width) + 2, 6)


def _render_semicircle(ctx: CompositeRenderContext, problem: CompositeShapeProblem, *, cutout: bool) -> RenderedCompositeShape:
    """Draw a rectangle combined with one semicircular add/remove component."""

    values = dict(problem.dimensions)
    width_units = int(values["width_units"])
    height_units = int(values["height_units"])
    radius_units = int(values["radius_units"])
    total_width_units = float(width_units + radius_units)
    total_height_units = max(float(height_units), float(2 * radius_units))
    scale = min(
        22.0,
        (float(ctx.width) - 210.0) / max(1.0, total_width_units),
        (float(ctx.height) - 180.0) / max(1.0, total_height_units),
    )
    scale = max(7.0, float(scale))
    rect_w = float(width_units) * scale
    rect_h = float(height_units) * scale
    radius_px = float(radius_units) * scale
    left = (float(ctx.width) - (total_width_units * scale)) / 2.0
    top = max(112.0, (float(ctx.height) - rect_h) / 2.0)
    right = left + rect_w
    bottom = top + rect_h
    mid_y = (top + bottom) / 2.0
    cap_start_y = mid_y - radius_px
    cap_end_y = mid_y + radius_px
    arc_box = (right - radius_px, mid_y - radius_px, right + radius_px, mid_y + radius_px)
    target_right = right if cutout else right + radius_px
    target_bbox = pad_bbox((left, top, target_right, bottom), 8.0, width=ctx.width, height=ctx.height)
    ctx.draw.rectangle((left, top, right, bottom), fill=ctx.fill_color)
    if cutout:
        ctx.draw.pieslice(arc_box, start=90, end=270, fill=ctx.background_color)
        arc_start, arc_end = 90, 270
    else:
        ctx.draw.pieslice(arc_box, start=-90, end=90, fill=ctx.fill_color)
        arc_start, arc_end = -90, 90
    ctx.draw.line([(left, top), (right, top)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(left, top), (left, bottom)], fill=ctx.line_color, width=ctx.line_width)
    if cap_start_y > top + 1.0:
        ctx.draw.line([(right, top), (right, cap_start_y)], fill=ctx.line_color, width=ctx.line_width)
    if cap_end_y < bottom - 1.0:
        ctx.draw.line([(right, cap_end_y), (right, bottom)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc(arc_box, start=arc_start, end=arc_end, fill=ctx.line_color, width=ctx.line_width)
    top_right_reference = (right, cap_start_y) if cap_start_y > top + 1.0 else (right, bottom)
    bottom_right_reference = (right, cap_end_y) if cap_end_y < bottom - 1.0 else (right, top)
    notation_bboxes = {
        "top_left_right_angle": _draw_right_angle_notation(ctx, (left, top), (right, top), (left, bottom)),
        "bottom_left_right_angle": _draw_right_angle_notation(ctx, (left, bottom), (left, top), (right, bottom)),
        "top_right_right_angle": _draw_right_angle_notation(ctx, (right, top), (left, top), top_right_reference),
        "bottom_right_right_angle": _draw_right_angle_notation(ctx, (right, bottom), bottom_right_reference, (left, bottom)),
    }
    if problem.metric_kind == "perimeter":
        highlight_width = _boundary_width(ctx)
        ctx.draw.line([(left, top), (right, top)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.line([(left, top), (left, bottom)], fill=ctx.accent_color, width=highlight_width)
        if cap_start_y > top + 1.0:
            ctx.draw.line([(right, top), (right, cap_start_y)], fill=ctx.accent_color, width=highlight_width)
        if cap_end_y < bottom - 1.0:
            ctx.draw.line([(right, cap_end_y), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.arc(arc_box, start=arc_start, end=arc_end, fill=ctx.accent_color, width=highlight_width)
    width_dim_y = min(bottom + 34.0, float(ctx.height) - 46.0)
    width_label_offset_y = -22.0 if width_dim_y >= float(ctx.height) - 54.0 else 20.0
    width_label = "?" if problem.metric_kind == "missing_width" else fmt_measure(width_units)
    width_bbox = _draw_dimension(ctx, (left, width_dim_y), (right, width_dim_y), width_label, label_offset=(0.0, width_label_offset_y))
    height_bbox = _draw_dimension(ctx, (left - 34.0, top), (left - 34.0, bottom), fmt_measure(height_units), label_offset=(-26.0, 0.0))
    radius_bbox = _draw_dimension(ctx, (right, mid_y), (right, mid_y - radius_px), f"r={fmt_measure(radius_units)}", label_offset=(44.0 if cutout else 54.0, 0.0))
    support_roles = ["width_label", "height_label", "radius_label"]
    support_bboxes = [width_bbox, height_bbox, radius_bbox]
    center_marker_bbox = _draw_point_marker(ctx, (right, mid_y))
    annotation_points, point_label_bboxes = _draw_labeled_points(
        ctx,
        {
            "A": (left, top),
            "B": (right, top),
            "C": (right, bottom),
            "D": (left, bottom),
            "O": (right, mid_y),
        },
        center=((left + right) / 2.0, (top + bottom) / 2.0),
        distance=24.0,
    )
    curved_component_bbox = pad_bbox(
        (right - radius_px, mid_y - radius_px, right, mid_y + radius_px)
        if cutout
        else (right, mid_y - radius_px, right + radius_px, mid_y + radius_px),
        6.0,
        width=ctx.width,
        height=ctx.height,
    )
    annotation_roles = tuple(annotation_points)
    if problem.metric_kind == "perimeter":
        annotation_roles = tuple(annotation_points)
    elif problem.metric_kind == "missing_width":
        total_bbox = draw_label(ctx, f"Area={float(values['total_area']):.1f}", ((left + target_right) / 2.0, top - 42.0), small=True)
        support_bboxes.append(total_bbox)
        support_roles.append("total_area_label")
    return RenderedCompositeShape(
        image=ctx.image,
        answer_value=problem.answer_value,
        annotation_roles=tuple(annotation_roles),
        annotation_keyed_points=annotation_points,
        scene_entities=(
            {
                "entity_id": "target_shape",
                "entity_type": "curvilinear_composite",
                "bbox": bbox_to_list(target_bbox),
                "points": dict(annotation_points),
                "components": [
                    {"kind": "rectangle", "width": width_units, "height": height_units},
                    {"kind": "semicircle", "radius": radius_units, "operation": "subtract" if cutout else "add"},
                ],
            },
        ),
        render_map={
            "target_bbox": bbox_to_list(target_bbox),
            "curved_component_bbox": bbox_to_list(curved_component_bbox),
            "support_bboxes": [bbox_to_list(bbox) for bbox in support_bboxes],
            "support_roles": list(support_roles),
            "center_marker_bbox": bbox_to_list(center_marker_bbox),
            "point_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in point_label_bboxes.items()},
            "visual_notation_bboxes": {key: bbox_to_list(bbox) for key, bbox in notation_bboxes.items()},
            "coord_space": "pixel",
        },
        witness={
            "formula_family": problem.formula_family,
            "operation": "subtract" if cutout else "add",
            **dict(values),
        },
    )


def _render_quarter_sector(ctx: CompositeRenderContext, problem: CompositeShapeProblem) -> RenderedCompositeShape:
    """Draw a rectangle whose top-right corner has a quarter-sector cutout."""

    values = dict(problem.dimensions)
    width_units = int(values["width_units"])
    height_units = int(values["height_units"])
    radius_units = int(values["radius_units"])
    scale = min(
        23.0,
        (float(ctx.width) - 210.0) / max(1.0, float(width_units)),
        (float(ctx.height) - 180.0) / max(1.0, float(height_units)),
    )
    scale = max(8.0, float(scale))
    rect_w = float(width_units) * scale
    rect_h = float(height_units) * scale
    radius_px = float(radius_units) * scale
    left = (float(ctx.width) - rect_w) / 2.0
    top = max(112.0, (float(ctx.height) - rect_h) / 2.0)
    right = left + rect_w
    bottom = top + rect_h
    center = (right, top)
    arc_box = (right - radius_px, top - radius_px, right + radius_px, top + radius_px)
    target_bbox = pad_bbox((left, top, right, bottom), 8.0, width=ctx.width, height=ctx.height)
    ctx.draw.rectangle((left, top, right, bottom), fill=ctx.secondary_fill_color)
    ctx.draw.pieslice(arc_box, start=90, end=180, fill=ctx.background_color)
    ctx.draw.line([(left, top), (left, bottom)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(right, top + radius_px), (right, bottom)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(right - radius_px, top), (left, top)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc(arc_box, start=90, end=180, fill=ctx.line_color, width=ctx.line_width)
    if problem.metric_kind == "perimeter":
        highlight_width = _boundary_width(ctx)
        ctx.draw.line([(left, top), (right - radius_px, top)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.line([(left, top), (left, bottom)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.line([(right, top + radius_px), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.arc(arc_box, start=90, end=180, fill=ctx.accent_color, width=highlight_width)
    notation_bboxes = {
        "top_left_right_angle": _draw_right_angle_notation(ctx, (left, top), (right - radius_px, top), (left, bottom)),
        "bottom_left_right_angle": _draw_right_angle_notation(ctx, (left, bottom), (left, top), (right, bottom)),
        "bottom_right_right_angle": _draw_right_angle_notation(ctx, (right, bottom), (right, top + radius_px), (left, bottom)),
        "quarter_sector_right_angle": _draw_right_angle_notation(
            ctx,
            center,
            (right - radius_px, top),
            (right, top + radius_px),
        ),
    }
    width_dim_y = min(bottom + 34.0, float(ctx.height) - 46.0)
    width_bbox = _draw_dimension(ctx, (left, width_dim_y), (right, width_dim_y), fmt_measure(width_units), label_offset=(0.0, 20.0))
    height_bbox = _draw_dimension(ctx, (left - 34.0, top), (left - 34.0, bottom), fmt_measure(height_units), label_offset=(-26.0, 0.0))
    radius_bbox = _draw_dimension(ctx, center, (right - radius_px, top), f"r={fmt_measure(radius_units)}", label_offset=(0.0, -26.0))
    center_marker_bbox = _draw_point_marker(ctx, center)
    annotation_points, point_label_bboxes = _draw_labeled_points(
        ctx,
        {
            "A": (left, top),
            "B": center,
            "C": (right, bottom),
            "D": (left, bottom),
            "E": (right - radius_px, top),
            "F": (right, top + radius_px),
        },
        center=((left + right) / 2.0, (top + bottom) / 2.0),
        distance=24.0,
    )
    curved_component_bbox = pad_bbox((right - radius_px, top, right, top + radius_px), 6.0, width=ctx.width, height=ctx.height)
    return RenderedCompositeShape(
        image=ctx.image,
        answer_value=problem.answer_value,
        annotation_roles=tuple(annotation_points),
        annotation_keyed_points=annotation_points,
        scene_entities=(
            {
                "entity_id": "target_shape",
                "entity_type": "curvilinear_composite",
                "bbox": bbox_to_list(target_bbox),
                "points": dict(annotation_points),
                "components": [
                    {"kind": "rectangle", "width": width_units, "height": height_units},
                    {"kind": "sector", "radius": radius_units, "theta_degrees": 90, "operation": "subtract"},
                ],
            },
        ),
        render_map={
            "target_bbox": bbox_to_list(target_bbox),
            "curved_component_bbox": bbox_to_list(curved_component_bbox),
            "support_bboxes": [bbox_to_list(width_bbox), bbox_to_list(height_bbox), bbox_to_list(radius_bbox)],
            "support_roles": ["width_label", "height_label", "radius_label"],
            "center_marker_bbox": bbox_to_list(center_marker_bbox),
            "point_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in point_label_bboxes.items()},
            "visual_notation_bboxes": {key: bbox_to_list(bbox) for key, bbox in notation_bboxes.items()},
            "coord_space": "pixel",
        },
        witness={"formula_family": problem.formula_family, **dict(values)},
    )


def _render_sector(ctx: CompositeRenderContext, problem: CompositeShapeProblem) -> RenderedCompositeShape:
    """Draw a circular sector with a missing central angle value."""

    values = dict(problem.dimensions)
    theta = int(values["theta_degrees"])
    radius_units = int(values["radius_units"])
    radius_px = 180.0
    center = (310.0, 310.0)
    start_deg = -135.0
    end_deg = start_deg + float(theta)
    arc_box = (center[0] - radius_px, center[1] - radius_px, center[0] + radius_px, center[1] + radius_px)
    ctx.draw.pieslice(arc_box, start=start_deg, end=end_deg, fill=ctx.fill_color, outline=ctx.line_color, width=ctx.line_width)
    start_rad = math.radians(start_deg)
    end_rad = math.radians(end_deg)
    p0 = (center[0] + radius_px * math.cos(start_rad), center[1] + radius_px * math.sin(start_rad))
    p1 = (center[0] + radius_px * math.cos(end_rad), center[1] + radius_px * math.sin(end_rad))
    ctx.draw.line([center, p0], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([center, p1], fill=ctx.line_color, width=ctx.line_width)
    center_marker_bbox = _draw_point_marker(ctx, center)
    mid_rad = math.radians((start_deg + end_deg) / 2.0)
    target_bbox = draw_label(ctx, "?", (center[0] + 54.0 * math.cos(mid_rad), center[1] + 54.0 * math.sin(mid_rad)), small=False)
    radius_bbox = _draw_dimension(ctx, center, p0, f"r={fmt_measure(radius_units)}", label_offset=(-18.0, 22.0))
    if problem.metric_kind == "sector_from_arc":
        measure_text = f"arc={float(values['arc_length']):.1f}"
        measure_role = "arc_length_label"
    else:
        measure_text = f"Area={float(values['sector_area']):.1f}"
        measure_role = "sector_area_label"
    measure_bbox = draw_label(ctx, measure_text, (560.0, 210.0), small=True)
    sector_bbox = pad_bbox(arc_box, 8.0, width=ctx.width, height=ctx.height)
    annotation_points, point_label_bboxes = _draw_labeled_points(
        ctx,
        {"O": center, "A": p0, "B": p1},
        center=((center[0] + p0[0] + p1[0]) / 3.0, (center[1] + p0[1] + p1[1]) / 3.0),
        distance=24.0,
    )
    return RenderedCompositeShape(
        image=ctx.image,
        answer_value=problem.answer_value,
        annotation_roles=tuple(annotation_points),
        annotation_keyed_points=annotation_points,
        scene_entities=(
            {
                "entity_id": "target_sector",
                "entity_type": "sector",
                "bbox": bbox_to_list(sector_bbox),
                "points": dict(annotation_points),
                "radius": radius_units,
                "theta_degrees": theta,
                "arc_length": float(values["arc_length"]),
                "sector_area": float(values["sector_area"]),
            },
        ),
        render_map={
            "target_bbox": bbox_to_list(target_bbox),
            "sector_bbox": bbox_to_list(sector_bbox),
            "support_bboxes": [bbox_to_list(radius_bbox), bbox_to_list(measure_bbox)],
            "support_roles": ["radius_label", measure_role],
            "center_marker_bbox": bbox_to_list(center_marker_bbox),
            "point_label_bboxes": {key: bbox_to_list(bbox) for key, bbox in point_label_bboxes.items()},
            "coord_space": "pixel",
        },
        witness={"formula_family": problem.formula_family, **dict(values)},
    )


def render_composite_shape(ctx: CompositeRenderContext, problem: CompositeShapeProblem) -> RenderedCompositeShape:
    """Dispatch from semantic shape family to the corresponding renderer primitive."""

    family = str(problem.shape_family)
    if family == "rect_cut":
        return _render_rect_cut(ctx, problem)
    if family == "l_profile":
        return _render_l_profile(ctx, problem)
    if family == "house":
        return _render_house(ctx, problem)
    if family == "tabbed":
        return _render_tabbed(ctx, problem)
    if family == "semi_cap":
        return _render_semicircle(ctx, problem, cutout=False)
    if family == "semi_cut":
        return _render_semicircle(ctx, problem, cutout=True)
    if family == "quarter_cut":
        return _render_quarter_sector(ctx, problem)
    if family == "sector":
        return _render_sector(ctx, problem)
    raise ValueError(f"unsupported composite shape family: {family}")
