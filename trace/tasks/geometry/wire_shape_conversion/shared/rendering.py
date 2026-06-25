"""Rendering primitives for wire-shape-conversion diagrams."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_to_list,
    bbox_union_from_bboxes,
    pad_bbox,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from .construction import (
    SOURCE_CIRCLE,
    SOURCE_PARALLELOGRAM,
    SOURCE_TRAPEZOID,
    TARGET_CUBE_FRAME,
    TARGET_CUBOID_FRAME,
    TARGET_RECTANGLE,
)
from .defaults import SCENE_ID
from .state import BBox, Color, Point, RenderContext, RenderedScene, ResolvedProblem


def make_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    random_namespace: str,
) -> RenderContext:
    """Prepare a styled diagram canvas and reusable drawing context."""

    width = int(params.get("canvas_width", render_defaults.get("canvas_width", 860)))
    height = int(params.get("canvas_height", render_defaults.get("canvas_height", 620)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=False,
        require_grid=False,
    )
    palette = (
        ((225, 239, 255), (255, 238, 218), (28, 106, 176)),
        ((238, 234, 255), (231, 248, 244), (112, 82, 190)),
        ((229, 246, 236), (255, 235, 229), (42, 128, 90)),
    )
    color_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{random_namespace}.palette",
    ) % len(palette)
    source_fill, target_fill, accent = palette[int(color_index)]
    line_width = max(2, int(params.get("line_width", render_defaults.get("line_width", 3))))
    font_size = int(params.get("label_font_size", render_defaults.get("label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", render_defaults.get("small_label_font_size", 17)))
    return RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=width,
        height=height,
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        source_fill=source_fill,
        target_fill=target_fill,
        accent_color=accent,
        muted_color=tuple(int(value) for value in diagram_style.panel_border_rgb),
        line_width=line_width,
        label_stroke_width=max(1, int(diagram_style.label_stroke_width_px)),
        font=load_font(max(12, font_size), bold=True),
        small_font=load_font(max(10, small_font_size), bold=True),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
    )


def _line_bbox(p0: Point, p1: Point, *, width: int, height: int, pad: float = 5.0) -> BBox:
    return pad_bbox(
        (
            min(float(p0[0]), float(p1[0])),
            min(float(p0[1]), float(p1[1])),
            max(float(p0[0]), float(p1[0])),
            max(float(p0[1]), float(p1[1])),
        ),
        float(pad),
        width=int(width),
        height=int(height),
    )


def _draw_text(ctx: RenderContext, text: str, center: Point, *, small: bool = False) -> BBox:
    font = ctx.small_font if small else ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=ctx.label_stroke_width)
    width = float(bbox[2] - bbox[0])
    height = float(bbox[3] - bbox[1])
    x = float(center[0]) - width / 2.0
    y = float(center[1]) - height / 2.0
    draw_text_traced(
        ctx.draw,
        (x, y),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((x, y, x + width, y + height), 4.0, width=ctx.width, height=ctx.height)


def _draw_value_box(ctx: RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if small else ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=ctx.label_stroke_width)
    width = float(bbox[2] - bbox[0])
    height = float(bbox[3] - bbox[1])
    x0 = float(center[0]) - width / 2.0 - 9.0
    y0 = float(center[1]) - height / 2.0 - 6.0
    x1 = x0 + width + 18.0
    y1 = y0 + height + 12.0
    ctx.draw.rounded_rectangle((x0, y0, x1, y1), radius=6, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
    draw_text_traced(
        ctx.draw,
        (x0 + 9.0, y0 + 6.0),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((x0, y0, x1, y1), 3.0, width=ctx.width, height=ctx.height)


def _draw_arrow(ctx: RenderContext, start: Point, end: Point) -> BBox:
    ctx.draw.line([start, end], fill=ctx.accent_color, width=max(3, ctx.line_width + 1))
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = max(1e-6, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head = 16.0
    wing = 8.0
    p1 = (float(end[0]) - ux * head + px * wing, float(end[1]) - uy * head + py * wing)
    p2 = (float(end[0]) - ux * head - px * wing, float(end[1]) - uy * head - py * wing)
    ctx.draw.polygon([end, p1, p2], fill=ctx.accent_color)
    return bbox_union_from_bboxes(
        (
            (start[0], start[1], start[0], start[1]),
            (end[0], end[1], end[0], end[1]),
            (p1[0], p1[1], p1[0], p1[1]),
            (p2[0], p2[1], p2[0], p2[1]),
        ),
        width=ctx.width,
        height=ctx.height,
        pad=8.0,
    )


def _draw_trapezoid(ctx: RenderContext, bbox: BBox, *, fill: Color) -> tuple[Point, ...]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    inset = (x1 - x0) * 0.22
    points = ((x0 + inset, y0), (x1 - inset, y0), (x1, y1), (x0, y1))
    ctx.draw.polygon(points, fill=fill, outline=ctx.line_color)
    ctx.draw.line([*points, points[0]], fill=ctx.line_color, width=ctx.line_width)
    return points


def _draw_parallelogram(ctx: RenderContext, bbox: BBox, *, fill: Color) -> tuple[Point, ...]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    shift = (x1 - x0) * 0.18
    points = ((x0 + shift, y0), (x1, y0), (x1 - shift, y1), (x0, y1))
    ctx.draw.polygon(points, fill=fill, outline=ctx.line_color)
    ctx.draw.line([*points, points[0]], fill=ctx.line_color, width=ctx.line_width)
    return points


def _draw_circle(ctx: RenderContext, bbox: BBox, *, fill: Color) -> None:
    ctx.draw.ellipse(bbox, fill=fill, outline=ctx.line_color, width=ctx.line_width)


def _draw_rectangle_wire(ctx: RenderContext, bbox: BBox, *, fill: Color) -> tuple[Point, ...]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    points = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    ctx.draw.polygon(points, fill=fill, outline=ctx.line_color)
    ctx.draw.line([*points, points[0]], fill=ctx.line_color, width=ctx.line_width)
    return points


def _draw_cube_frame(ctx: RenderContext, bbox: BBox) -> tuple[BBox, BBox]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    depth = min(54.0, (x1 - x0) * 0.25)
    front = (x0, y0 + depth * 0.45, x1 - depth, y1)
    back = (front[0] + depth, front[1] - depth * 0.45, front[2] + depth, front[3] - depth * 0.45)
    edges = (
        ((front[0], front[1]), (front[2], front[1])),
        ((front[2], front[1]), (front[2], front[3])),
        ((front[2], front[3]), (front[0], front[3])),
        ((front[0], front[3]), (front[0], front[1])),
        ((back[0], back[1]), (back[2], back[1])),
        ((back[2], back[1]), (back[2], back[3])),
        ((back[2], back[3]), (back[0], back[3])),
        ((back[0], back[3]), (back[0], back[1])),
        ((front[0], front[1]), (back[0], back[1])),
        ((front[2], front[1]), (back[2], back[1])),
        ((front[2], front[3]), (back[2], back[3])),
        ((front[0], front[3]), (back[0], back[3])),
    )
    for edge in edges:
        ctx.draw.line(edge, fill=ctx.line_color, width=ctx.line_width)
    bottom_edge_bbox = _line_bbox((front[0], front[3]), (front[2], front[3]), width=ctx.width, height=ctx.height, pad=6.0)
    height_edge_bbox = _line_bbox((front[0], front[1]), (front[0], front[3]), width=ctx.width, height=ctx.height, pad=6.0)
    return bottom_edge_bbox, height_edge_bbox


def _draw_source_shape(ctx: RenderContext, problem: ResolvedProblem, bbox: BBox) -> tuple[BBox, tuple[BBox, ...]]:
    label_boxes: list[BBox] = []
    if problem.source_shape == SOURCE_TRAPEZOID:
        _draw_trapezoid(ctx, bbox, fill=ctx.source_fill)
        label_boxes.append(_draw_value_box(ctx, f"top={problem.source_values['top']}", ((bbox[0] + bbox[2]) / 2.0, bbox[1] - 18.0)))
        label_boxes.append(_draw_value_box(ctx, f"bottom={problem.source_values['bottom']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0)))
        label_boxes.append(_draw_value_box(ctx, f"side={problem.source_values['side']}", (bbox[2] + 50.0, (bbox[1] + bbox[3]) / 2.0)))
    elif problem.source_shape == SOURCE_PARALLELOGRAM:
        _draw_parallelogram(ctx, bbox, fill=ctx.source_fill)
        label_boxes.append(_draw_value_box(ctx, f"base={problem.source_values['base']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0)))
        label_boxes.append(_draw_value_box(ctx, f"side={problem.source_values['side']}", (bbox[0] - 48.0, (bbox[1] + bbox[3]) / 2.0)))
    elif problem.source_shape == SOURCE_CIRCLE:
        _draw_circle(ctx, bbox, fill=ctx.source_fill)
        if "area" in problem.source_values:
            label_boxes.append(_draw_value_box(ctx, f"area={problem.source_values['area']}", ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0), small=False))
        else:
            label_boxes.append(_draw_value_box(ctx, f"r={problem.source_values['radius']}", ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0), small=False))
        label_boxes.append(_draw_value_box(ctx, f"pi={problem.source_values['pi']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 30.0)))
    else:
        raise ValueError(f"unsupported source shape: {problem.source_shape}")
    return pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height), tuple(label_boxes)


def _draw_target_shape(ctx: RenderContext, problem: ResolvedProblem, bbox: BBox) -> tuple[BBox, tuple[BBox, ...], BBox]:
    label_boxes: list[BBox] = []
    if problem.target_shape == TARGET_CUBE_FRAME:
        target_bbox = pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height)
        edge_bbox, _height_edge_bbox = _draw_cube_frame(ctx, bbox)
        label_boxes.append(_draw_value_box(ctx, "12 equal edges", ((bbox[0] + bbox[2]) / 2.0, bbox[1] - 20.0)))
        unknown_label = _draw_value_box(ctx, "edge=?", ((edge_bbox[0] + edge_bbox[2]) / 2.0, edge_bbox[3] + 22.0))
        unknown_bbox = bbox_union_from_bboxes((edge_bbox, unknown_label), width=ctx.width, height=ctx.height, pad=4.0)
    elif problem.target_shape == TARGET_CUBOID_FRAME:
        target_bbox = pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height)
        _edge_bbox, height_edge_bbox = _draw_cube_frame(ctx, bbox)
        label_boxes.append(_draw_value_box(ctx, f"L={problem.target_values['length']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0)))
        label_boxes.append(_draw_value_box(ctx, f"W={problem.target_values['width']}", (bbox[2] + 48.0, bbox[1] + 45.0)))
        unknown_label = _draw_value_box(ctx, "H=?", (bbox[0] - 36.0, (bbox[1] + bbox[3]) / 2.0))
        unknown_bbox = bbox_union_from_bboxes((height_edge_bbox, unknown_label), width=ctx.width, height=ctx.height, pad=4.0)
    elif problem.target_shape == SOURCE_TRAPEZOID:
        points = _draw_trapezoid(ctx, bbox, fill=ctx.target_fill)
        target_bbox = pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height)
        label_boxes.append(_draw_value_box(ctx, f"top={problem.target_values['top']}", ((bbox[0] + bbox[2]) / 2.0, bbox[1] - 18.0)))
        label_boxes.append(_draw_value_box(ctx, f"bottom={problem.target_values['bottom']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0)))
        unknown_label = _draw_value_box(ctx, "side=?", (bbox[2] + 50.0, (bbox[1] + bbox[3]) / 2.0))
        unknown_edge = _line_bbox(points[1], points[2], width=ctx.width, height=ctx.height, pad=6.0)
        unknown_bbox = bbox_union_from_bboxes((unknown_edge, unknown_label), width=ctx.width, height=ctx.height, pad=4.0)
    elif problem.target_shape == TARGET_RECTANGLE:
        points = _draw_rectangle_wire(ctx, bbox, fill=ctx.target_fill)
        target_bbox = pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height)
        label_boxes.append(_draw_value_box(ctx, f"side={problem.target_values['known_side']}", (bbox[2] + 48.0, (bbox[1] + bbox[3]) / 2.0)))
        unknown_label = _draw_value_box(ctx, "side=?", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0))
        unknown_edge = _line_bbox(points[2], points[3], width=ctx.width, height=ctx.height, pad=6.0)
        unknown_bbox = bbox_union_from_bboxes((unknown_edge, unknown_label), width=ctx.width, height=ctx.height, pad=4.0)
    else:
        raise ValueError(f"unsupported target shape: {problem.target_shape}")
    return target_bbox, tuple(label_boxes), unknown_bbox


def render_wire_length_scene(ctx: RenderContext, problem: ResolvedProblem, *, instance_seed: int) -> RenderedScene:
    """Render the single-shape wire-length diagram and its role boxes."""

    rng = spawn_rng(int(instance_seed), "wire_length.render.scene")
    panel = (112.0, 92.0, 728.0, 505.0)
    ctx.draw.rounded_rectangle(panel, radius=10, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
    source_bbox = (300.0 + rng.uniform(-12, 12), 200.0, 540.0 + rng.uniform(-12, 12), 390.0)
    if problem.source_shape == SOURCE_CIRCLE:
        source_bbox = (300.0, 175.0, 520.0, 395.0)
    source_shape_bbox, source_label_boxes = _draw_source_shape(ctx, problem, source_bbox)
    question_bbox = _draw_value_box(ctx, "wire length ?", (ctx.width / 2.0, 118.0), small=False)
    annotation_bboxes = {
        "wire_shape_bbox": source_shape_bbox,
        "dimension_region_bbox": bbox_union_from_bboxes(source_label_boxes, width=ctx.width, height=ctx.height, pad=5.0),
    }
    return _rendered_result(
        ctx=ctx,
        problem=problem,
        annotation_bboxes=annotation_bboxes,
        label_bboxes={"question": question_bbox},
    )


def render_conversion_scene(ctx: RenderContext, problem: ResolvedProblem, *, instance_seed: int) -> RenderedScene:
    """Render the source-to-target wire conversion diagram and its role boxes."""

    rng = spawn_rng(int(instance_seed), "wire_conversion.render.scene")
    panel = (70.0, 92.0, 785.0, 525.0)
    ctx.draw.rounded_rectangle(panel, radius=10, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
    source_bbox = (130.0 + rng.uniform(-10, 10), 220.0, 345.0 + rng.uniform(-10, 10), 390.0)
    target_bbox = (555.0 + rng.uniform(-10, 10), 205.0, 725.0 + rng.uniform(-10, 10), 415.0)
    if problem.source_shape == SOURCE_CIRCLE:
        source_bbox = (150.0, 195.0, 330.0, 375.0)
    source_shape_bbox, source_label_boxes = _draw_source_shape(ctx, problem, source_bbox)
    target_shape_bbox, target_label_boxes, unknown_bbox = _draw_target_shape(ctx, problem, target_bbox)
    _draw_arrow(ctx, (source_bbox[2] + 38.0, 300.0), (target_bbox[0] - 38.0, 300.0))
    same_wire_bbox = _draw_text(ctx, "same wire", (ctx.width / 2.0, 260.0), small=True)

    target_key = "target_frame_bbox" if problem.target_shape in {TARGET_CUBE_FRAME, TARGET_CUBOID_FRAME} else "target_shape_bbox"
    unknown_key = "target_unknown_edge_bbox" if problem.target_shape in {TARGET_CUBE_FRAME, TARGET_CUBOID_FRAME} else "target_unknown_side_bbox"
    annotation_bboxes = {
        "source_wire_shape_bbox": source_shape_bbox,
        target_key: target_shape_bbox,
        "source_dimension_region_bbox": bbox_union_from_bboxes(source_label_boxes, width=ctx.width, height=ctx.height, pad=5.0),
        "target_known_dimension_region_bbox": bbox_union_from_bboxes(target_label_boxes, width=ctx.width, height=ctx.height, pad=5.0),
        unknown_key: unknown_bbox,
    }
    return _rendered_result(
        ctx=ctx,
        problem=problem,
        annotation_bboxes=annotation_bboxes,
        label_bboxes={"same_wire": same_wire_bbox},
    )


def _rendered_result(
    *,
    ctx: RenderContext,
    problem: ResolvedProblem,
    annotation_bboxes: dict[str, BBox],
    label_bboxes: dict[str, BBox],
) -> RenderedScene:
    entities = (
        {
            "entity_id": "source_wire_shape",
            "entity_type": str(problem.source_shape),
            "values": dict(problem.source_values),
            "wire_length_units": int(problem.source_values["wire_length"]),
        },
        {
            "entity_id": "target_shape",
            "entity_type": str(problem.target_shape),
            "values": dict(problem.target_values),
        },
    )
    return RenderedScene(
        image=ctx.image,
        annotation_bboxes=dict(annotation_bboxes),
        label_bboxes=dict(label_bboxes),
        scene_entities=entities,
        render_map={
            "coord_space": "pixel",
            "source_shape": str(problem.source_shape),
            "target_shape": str(problem.target_shape),
            "style": {
                "technical_diagram": dict(ctx.diagram_style_meta),
                "background": dict(ctx.background_meta),
            },
            "annotation_bboxes": {key: bbox_to_list(value) for key, value in annotation_bboxes.items()},
        },
    )


def render_wire_shape_with_retries(
    *,
    problem: ResolvedProblem,
    render_scene: Callable[..., RenderedScene],
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    max_attempts: int,
    random_namespace: str,
) -> RenderedScene:
    """Retry scene rendering with deterministic seed offsets until layout succeeds."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            render_seed = int(instance_seed) + int(attempt) * 9973
            ctx = make_render_context(
                instance_seed=render_seed,
                params=params,
                render_defaults=render_defaults,
                random_namespace=str(random_namespace),
            )
            return render_scene(ctx, problem, instance_seed=render_seed)
        except Exception as exc:
            last_error = exc
    raise RuntimeError("failed to render wire-shape-conversion scene") from last_error


__all__ = [
    "make_render_context",
    "render_conversion_scene",
    "render_wire_length_scene",
    "render_wire_shape_with_retries",
]
