"""Rendering primitives for parallel-segment proportion diagrams."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, bbox_to_list, pad_bbox
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import add_scaled, mid, point_to_list, sub, unit
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from .defaults import SCENE_ID
from .state import BBox, Color, ParallelProportionPlan, Point, RenderContext, RenderedParallelProportionScene, Segment


def _segment_to_list(segment: Segment) -> list[list[float]]:
    return [point_to_list(segment[0]), point_to_list(segment[1])]


def _offset_from_segment(a: Point, b: Point, distance: float) -> Point:
    ux, uy = unit(sub(b, a))
    return (-uy * float(distance), ux * float(distance))


def _line_bbox(points: Sequence[Point], ctx: RenderContext, pad: float = 5.0) -> BBox:
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=pad)


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
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=stroke_width,
    )
    return pad_bbox(bbox, 3.0, width=ctx.width, height=ctx.height)


def _draw_point_label(ctx: RenderContext, label: str, point: Point, direction: Point, *, offset: float = 22.0) -> BBox:
    return _draw_text_centered(ctx, label, add_scaled(point, unit(direction), offset), small=True)


def _draw_parallel_mark(ctx: RenderContext, a: Point, b: Point, *, count: int = 1) -> BBox:
    center = mid(a, b)
    tangent = unit(sub(b, a))
    normal = _offset_from_segment(a, b, 1.0)
    mark_points: list[Point] = []
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * 14.0
        mark_center = add_scaled(center, tangent, shift)
        base = add_scaled(mark_center, normal, -8.0)
        tip = add_scaled(mark_center, normal, 8.0)
        left = add_scaled(base, tangent, -5.0)
        right = add_scaled(base, tangent, 5.0)
        ctx.draw.line(
            (left, tip, right),
            fill=ctx.accent_color,
            width=max(2, ctx.line_width - 1),
            joint="curve",
        )
        mark_points.extend([left, tip, right])
    return _line_bbox(mark_points, ctx, pad=4.0)


def _draw_polygon(
    ctx: RenderContext,
    points: Sequence[Point],
    *,
    fill: Color | None = None,
    outline: Color | None = None,
) -> BBox:
    polygon = [(float(x), float(y)) for x, y in points]
    ctx.draw.polygon(polygon, fill=fill or ctx.fill_color)
    ctx.draw.line(
        polygon + [polygon[0]],
        fill=outline or ctx.line_color,
        width=ctx.line_width,
        joint="curve",
    )
    return bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def make_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> tuple[RenderContext, dict[str, Any]]:
    """Create one styled render context for the scene."""

    width = int(params.get("canvas_width", group_default(rendering_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(rendering_defaults, "canvas_height", 580)))
    background, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        allow_dark=False,
        require_grid=False,
    )
    image = background.convert("RGB")
    readout_font_family = str(
        params.get("readout_font_family", group_default(rendering_defaults, "readout_font_family", "roboto"))
    )
    diagram_style_trace = dict(diagram_style_meta)
    diagram_style_trace["readout_font_family"] = readout_font_family
    ctx = RenderContext(
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
        muted_color=tuple(int(value) for value in diagram_style.guide_rgb),
        line_width=max(2, int(params.get("line_width", group_default(rendering_defaults, "line_width", 3)))),
        label_stroke_width=max(0, min(1, int(diagram_style.label_stroke_width_px))),
        font=load_font(
            int(params.get("label_font_size", group_default(rendering_defaults, "label_font_size", 22))),
            bold=False,
            font_family=readout_font_family,
        ),
        small_font=load_font(
            int(params.get("small_label_font_size", group_default(rendering_defaults, "small_label_font_size", 18))),
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
    return ctx, {
        "canvas": {"width": int(width), "height": int(height)},
        "style": {
            "technical_diagram": dict(diagram_style_trace),
            "background": dict(background_meta),
        },
    }


def _render_triangle_side_splitter(
    ctx: RenderContext,
    plan: ParallelProportionPlan,
    *,
    instance_seed: int,
) -> RenderedParallelProportionScene:
    """Draw one triangle splitter diagram and return transformed segment witnesses."""

    rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.triangle_side_splitter.layout")
    labels = dict(plan.labels)
    apex = (ctx.width * 0.50 + rng.uniform(-8.0, 8.0), ctx.height * 0.19 + rng.uniform(-8.0, 8.0))
    left_base = (ctx.width * 0.22 + rng.uniform(-10.0, 8.0), ctx.height * 0.78 + rng.uniform(-8.0, 8.0))
    right_base = (ctx.width * 0.78 + rng.uniform(-8.0, 10.0), ctx.height * 0.78 + rng.uniform(-8.0, 8.0))
    split_t = rng.uniform(0.44, 0.52)
    left_split = add_scaled(apex, sub(left_base, apex), split_t)
    right_split = add_scaled(apex, sub(right_base, apex), split_t)
    apex, left_base, right_base, left_split, right_split = ctx.scene_transform.points(
        (apex, left_base, right_base, left_split, right_split)
    )

    construction: dict[str, BBox] = {}
    readouts: dict[str, BBox] = {}
    point_label_bboxes: dict[str, list[float]] = {}
    construction["triangle"] = _draw_polygon(ctx, (apex, left_base, right_base), fill=ctx.fill_color)
    ctx.draw.line((left_split, right_split), fill=ctx.secondary_color, width=ctx.line_width)
    construction["parallel_segment"] = _line_bbox((left_split, right_split), ctx, pad=ctx.line_width + 3)
    construction["base_parallel_mark"] = _draw_parallel_mark(ctx, left_base, right_base, count=1)
    construction["splitter_parallel_mark"] = _draw_parallel_mark(ctx, left_split, right_split, count=1)

    for label, point, direction in (
        ("A", apex, (0.0, -1.0)),
        ("B", left_base, (-1.0, 1.0)),
        ("C", right_base, (1.0, 1.0)),
        ("D", left_split, (-1.0, 0.0)),
        ("E", right_split, (1.0, 0.0)),
    ):
        point_label_bboxes[label] = bbox_to_list(_draw_point_label(ctx, label, point, direction))

    left_top = (apex, left_split)
    left_bottom = (left_split, left_base)
    right_top = (apex, right_split)
    right_bottom = (right_split, right_base)
    readouts["left_top_label"] = _draw_text_centered(
        ctx,
        labels["left_top"],
        add_scaled(mid(*left_top), (-30.0, -7.0)),
        small=True,
    )
    readouts["left_bottom_label"] = _draw_text_centered(
        ctx,
        labels["left_bottom"],
        add_scaled(mid(*left_bottom), (-36.0, 8.0)),
        small=True,
    )
    readouts["right_top_label"] = _draw_text_centered(
        ctx,
        labels["right_top"],
        add_scaled(mid(*right_top), (31.0, -7.0)),
        small=True,
    )
    readouts["right_bottom_label"] = _draw_text_centered(
        ctx,
        labels["right_bottom"],
        add_scaled(mid(*right_bottom), (40.0, 8.0)),
        small=True,
    )

    segments: tuple[Segment, ...] = (left_top, left_bottom, right_top, right_bottom)
    vertex_payload = {
        "A": apex,
        "B": left_base,
        "C": right_base,
        "D": left_split,
        "E": right_split,
    }
    annotation_points = (apex, left_base, right_base, left_split, right_split)
    render_map = {
        "vertices": {label: point_to_list(point) for label, point in vertex_payload.items()},
        "annotation_points": [point_to_list(point) for point in annotation_points],
        "proportional_segments": [_segment_to_list(segment) for segment in segments],
        "point_label_bboxes": dict(point_label_bboxes),
        "readout_bboxes": geometry_json_ready(readouts),
        "construction_bboxes": geometry_json_ready(construction),
    }
    return RenderedParallelProportionScene(
        image=ctx.image,
        annotation_points=annotation_points,
        scene_entities=(
            {
                "type": "triangle_side_splitter",
                "vertices": {label: point_to_list(point) for label, point in vertex_payload.items()},
            },
        ),
        render_map=render_map,
        witness={
            "construction_family": plan.construction_family,
            "segment_roles": ["left_top", "left_bottom", "right_top", "right_bottom"],
        },
    )


def render_parallel_proportion_scene(
    ctx: RenderContext,
    plan: ParallelProportionPlan,
    *,
    instance_seed: int,
) -> RenderedParallelProportionScene:
    """Render one proportional-segment diagram."""

    if plan.construction_family == "triangle_side_splitter":
        return _render_triangle_side_splitter(ctx, plan, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported construction_family={plan.construction_family!r}")


__all__ = ["make_render_context", "render_parallel_proportion_scene"]
