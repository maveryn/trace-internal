"""Rendering primitives for tangent-packing diagrams."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.core.visual.background import make_background_canvas
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    draw_label,
    fmt_measure,
    pad_bbox,
)
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .defaults import BACKGROUND_DEFAULTS
from .measurements import case_trace_values
from .state import BBox, Color, Point, RenderContext, RenderedTangentPackingScene, TangentPackingProblem


def _union_bboxes(bboxes: Sequence[BBox], *, width: int, height: int, pad: float = 0.0) -> BBox:
    if not bboxes:
        return (0.0, 0.0, 1.0, 1.0)
    return pad_bbox(
        (
            min(bbox[0] for bbox in bboxes),
            min(bbox[1] for bbox in bboxes),
            max(bbox[2] for bbox in bboxes),
            max(bbox[3] for bbox in bboxes),
        ),
        pad,
        width=width,
        height=height,
    )


def _ellipse_bbox(center: Point, radius: float) -> BBox:
    return (
        float(center[0]) - float(radius),
        float(center[1]) - float(radius),
        float(center[0]) + float(radius),
        float(center[1]) + float(radius),
    )


def _rect_points(rect: BBox) -> tuple[Point, Point, Point, Point]:
    return (
        (float(rect[0]), float(rect[1])),
        (float(rect[2]), float(rect[1])),
        (float(rect[2]), float(rect[3])),
        (float(rect[0]), float(rect[3])),
    )


def _closed(points: Sequence[Point]) -> list[Point]:
    return list(points) + [points[0]] if points else []


def _transformed_radius(ctx: RenderContext, radius: float) -> float:
    return float(radius) * float(ctx.scene_transform.transform.scale)


def _draw_dimension(
    ctx: RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    label_offset: Point = (0.0, 0.0),
    color: Color | None = None,
) -> BBox:
    draw_color = color if color is not None else ctx.label_color
    ctx.draw.line([start, end], fill=draw_color, width=max(2, ctx.line_width - 1))
    tick = 8.0
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length > 1e-9:
        nx = -dy / length
        ny = dx / length
        for point in (start, end):
            ctx.draw.line(
                [
                    (point[0] - nx * tick, point[1] - ny * tick),
                    (point[0] + nx * tick, point[1] + ny * tick),
                ],
                fill=draw_color,
                width=max(2, ctx.line_width - 1),
            )
    label_bbox = draw_label(
        ctx,
        label,
        (
            (float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]),
            (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]),
        ),
        small=True,
    )
    line_bbox = bbox_from_points((start, end), width=ctx.width, height=ctx.height, pad=10.0)
    return _union_bboxes((line_bbox, label_bbox), width=ctx.width, height=ctx.height)


def create_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    namespace: str,
) -> tuple[RenderContext, dict[str, Any]]:
    """Create a styled PIL render context for one tangent-packing sample."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.render")
    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 780)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
    image, background_meta = make_background_canvas(
        canvas_width=int(width),
        canvas_height=int(height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=BACKGROUND_DEFAULTS,
        fallback_color=(255, 255, 252),
    )
    shape_style = sample_geometry_shape_style(
        rng,
        params=params,
        render_defaults=render_defaults,
        anchor_colors=extract_background_anchor_colors(background_meta),
    )
    palettes: tuple[tuple[Color, Color, Color, Color], ...] = (
        ((229, 240, 255), (247, 222, 186), (26, 123, 185), (126, 143, 156)),
        ((236, 247, 232), (255, 224, 210), (38, 143, 104), (150, 142, 132)),
        ((248, 238, 252), (226, 242, 255), (123, 95, 190), (143, 154, 172)),
        ((255, 244, 224), (226, 240, 255), (196, 102, 44), (132, 146, 160)),
    )
    palette_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.palette",
    )
    fill_color, shaded_color, accent_color, muted_color = palettes[int(palette_index) % len(palettes)]
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
    from trace.tasks.shared.text_rendering import load_font

    ctx = RenderContext(
        rng=rng,
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=shape_style.line_color,
        label_color=shape_style.label_color,
        label_stroke_color=shape_style.label_stroke_color,
        fill_color=fill_color,
        shaded_color=shaded_color,
        accent_color=accent_color,
        muted_color=muted_color,
        line_width=max(2, int(line_width)),
        font=load_font(max(12, int(font_size)), bold=True),
        small_font=load_font(max(10, int(small_font_size)), bold=True),
        scene_transform=LazySceneTransform(
            rng,
            params=params,
            render_defaults=render_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )
    return ctx, {
        "background_style": dict(background_meta),
        "shape_style": shape_style.to_trace_dict(),
        "line_width": int(ctx.line_width),
        "label_font_size": int(font_size),
        "small_label_font_size": int(small_font_size),
        "fill_color": list(fill_color),
        "shaded_color": list(shaded_color),
        "accent_color": list(accent_color),
        "muted_color": list(muted_color),
    }


def _build_rendered_scene(
    *,
    ctx: RenderContext,
    problem: TangentPackingProblem,
    target_bbox: BBox,
    scene_bbox: BBox,
    support_bbox: BBox,
    label_bboxes: Mapping[str, BBox],
    scene_entities: tuple[dict[str, Any], ...],
    render_map: Mapping[str, Any],
    witness: Mapping[str, Any],
) -> RenderedTangentPackingScene:
    annotation_bboxes = {
        "target_cue": target_bbox,
        "packing_region": scene_bbox,
        "support_measurement": support_bbox,
    }
    return RenderedTangentPackingScene(
        image=ctx.image,
        answer=float(problem.answer),
        annotation_bboxes=dict(annotation_bboxes),
        annotation_roles=("target_cue", "packing_region", "support_measurement"),
        label_bboxes=dict(label_bboxes),
        scene_entities=tuple(scene_entities),
        render_map={
            "coord_space": "pixel",
            "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
            **dict(render_map),
        },
        witness=dict(witness),
    )


def render_circle_in_square_scene(
    ctx: RenderContext,
    problem: TangentPackingProblem,
) -> RenderedTangentPackingScene:
    """Render a circle tangent inside a square container."""

    case = problem.case
    square = (185.0, 125.0, 485.0, 425.0)
    center_raw = (335.0, 275.0)
    radius_raw = 150.0
    circle_extents = (
        (center_raw[0] - radius_raw, center_raw[1]),
        (center_raw[0] + radius_raw, center_raw[1]),
        (center_raw[0], center_raw[1] - radius_raw),
        (center_raw[0], center_raw[1] + radius_raw),
    )
    ctx.scene_transform.resolve(
        _rect_points(square)
        + circle_extents
        + (
            (580.0, 104.0),
            (560.0, 274.0),
            (590.0, 104.0),
            (square[0], square[3] + 26.0),
            (square[2], square[3] + 26.0),
        )
    )
    square_points = ctx.scene_transform.points(_rect_points(square))
    center = ctx.scene_transform.point(center_raw)
    radius_px = _transformed_radius(ctx, radius_raw)
    circle_bbox = _ellipse_bbox(center, radius_px)
    label_bboxes: dict[str, BBox] = {}
    use_gap_shading = problem.target_kind == "shaded_area" or problem.support_kind == "shaded_area"
    if use_gap_shading:
        ctx.draw.polygon(square_points, fill=ctx.shaded_color)
        ctx.draw.ellipse(circle_bbox, fill=ctx.fill_color)
    else:
        ctx.draw.polygon(square_points, fill=ctx.fill_color)
        ctx.draw.ellipse(circle_bbox, outline=ctx.accent_color, width=ctx.line_width)
    ctx.draw.line(_closed(square_points), fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ctx.draw.ellipse(circle_bbox, outline=ctx.accent_color, width=ctx.line_width)
    supporting: list[BBox] = []
    if problem.support_kind == "shaded_area":
        label_bboxes["support"] = draw_label(ctx, problem.support_text, ctx.scene_transform.point((580.0, 104.0)), small=True)
    else:
        label_bboxes["support"] = _draw_dimension(
            ctx,
            ctx.scene_transform.point((square[0], square[3] + 26.0)),
            ctx.scene_transform.point((square[2], square[3] + 26.0)),
            problem.support_text,
        )
    supporting.append(label_bboxes["support"])
    if problem.target_kind == "radius":
        radius_endpoint = ctx.scene_transform.point((center_raw[0] + radius_raw, center_raw[1]))
        ctx.draw.line([center, radius_endpoint], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        label_bboxes["target"] = draw_label(ctx, problem.target_text, ctx.scene_transform.point((560.0, 274.0)), small=True)
    else:
        label_bboxes["target"] = draw_label(ctx, problem.target_text, ctx.scene_transform.point((590.0, 104.0)), small=True)
    scene_bbox = bbox_from_points(square_points, width=ctx.width, height=ctx.height, pad=10.0)
    support_bbox = _union_bboxes(supporting, width=ctx.width, height=ctx.height, pad=4.0)
    circle_padded = pad_bbox(circle_bbox, 4.0, width=ctx.width, height=ctx.height)
    witness = {
        "scene_variant": "circle_in_square",
        "formula": str(problem.formula_text),
        "answer_value": float(problem.answer),
        **case_trace_values(case),
    }
    return _build_rendered_scene(
        ctx=ctx,
        problem=problem,
        target_bbox=label_bboxes["target"],
        scene_bbox=scene_bbox,
        support_bbox=support_bbox,
        label_bboxes=label_bboxes,
        scene_entities=(
            {"entity_id": "square_container", "entity_type": "square", "bbox": bbox_to_list(scene_bbox)},
            {
                "entity_id": "inscribed_circle",
                "entity_type": "circle",
                "bbox": bbox_to_list(circle_padded),
                "center": [round(center[0], 3), round(center[1], 3)],
                "radius_px": round(radius_px, 3),
            },
        ),
        render_map={
            "scene_variant": "circle_in_square",
            "square_bbox": bbox_to_list(scene_bbox),
            "circle_bbox": bbox_to_list(circle_padded),
            "shaded_region_bbox": bbox_to_list(scene_bbox),
        },
        witness=witness,
    )


def render_square_in_circle_scene(
    ctx: RenderContext,
    problem: TangentPackingProblem,
) -> RenderedTangentPackingScene:
    """Render a square tangent inside a circle container."""

    case = problem.case
    center_raw = (350.0, 280.0)
    radius_raw = 170.0
    square_points_raw = ((350.0, 110.0), (520.0, 280.0), (350.0, 450.0), (180.0, 280.0))
    ctx.scene_transform.resolve(
        tuple(square_points_raw)
        + (
            (center_raw[0] - radius_raw, center_raw[1]),
            (center_raw[0] + radius_raw, center_raw[1]),
            (center_raw[0], center_raw[1] - radius_raw),
            (center_raw[0], center_raw[1] + radius_raw),
            (575.0, 104.0),
            (570.0, 454.0),
            (440.0, 252.0),
        )
    )
    center = ctx.scene_transform.point(center_raw)
    radius_px = _transformed_radius(ctx, radius_raw)
    square_points = ctx.scene_transform.points(square_points_raw)
    circle_bbox = _ellipse_bbox(center, radius_px)
    label_bboxes: dict[str, BBox] = {}
    use_gap_shading = problem.target_kind == "shaded_area" or problem.support_kind == "shaded_area"
    if use_gap_shading:
        ctx.draw.ellipse(circle_bbox, fill=ctx.shaded_color)
        ctx.draw.polygon(square_points, fill=ctx.fill_color)
    else:
        ctx.draw.ellipse(circle_bbox, fill=ctx.fill_color)
    ctx.draw.ellipse(circle_bbox, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.line(_closed(square_points), fill=ctx.accent_color, width=ctx.line_width, joint="curve")
    radius_endpoint = ctx.scene_transform.point((center_raw[0] + radius_raw, center_raw[1]))
    ctx.draw.line([center, radius_endpoint], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    if problem.support_kind == "shaded_area":
        label_bboxes["support"] = draw_label(ctx, problem.support_text, ctx.scene_transform.point((575.0, 104.0)), small=True)
    else:
        label_bboxes["support"] = draw_label(ctx, problem.support_text, ctx.scene_transform.point((440.0, 252.0)), small=True)
    if problem.target_kind == "square_side":
        label_bboxes["target"] = draw_label(ctx, problem.target_text, ctx.scene_transform.point((570.0, 454.0)), small=True)
    else:
        label_bboxes["target"] = draw_label(ctx, problem.target_text, ctx.scene_transform.point((575.0, 104.0)), small=True)
    scene_bbox = pad_bbox(circle_bbox, 10.0, width=ctx.width, height=ctx.height)
    square_bbox = bbox_from_points(square_points, width=ctx.width, height=ctx.height, pad=4.0)
    witness = {
        "scene_variant": "square_in_circle",
        "formula": str(problem.formula_text),
        "answer_value": float(problem.answer),
        **case_trace_values(case),
    }
    return _build_rendered_scene(
        ctx=ctx,
        problem=problem,
        target_bbox=label_bboxes["target"],
        scene_bbox=scene_bbox,
        support_bbox=pad_bbox(label_bboxes["support"], 4.0, width=ctx.width, height=ctx.height),
        label_bboxes=label_bboxes,
        scene_entities=(
            {
                "entity_id": "circle_container",
                "entity_type": "circle",
                "bbox": bbox_to_list(scene_bbox),
                "center": [round(center[0], 3), round(center[1], 3)],
                "radius_px": round(radius_px, 3),
            },
            {
                "entity_id": "inscribed_square",
                "entity_type": "square",
                "bbox": bbox_to_list(square_bbox),
                "points": [[round(x, 3), round(y, 3)] for x, y in square_points],
            },
        ),
        render_map={
            "scene_variant": "square_in_circle",
            "circle_bbox": bbox_to_list(scene_bbox),
            "square_points": [[round(x, 3), round(y, 3)] for x, y in square_points],
        },
        witness=witness,
    )


def render_two_circles_rectangle_scene(
    ctx: RenderContext,
    problem: TangentPackingProblem,
) -> RenderedTangentPackingScene:
    """Render two equal tangent circles inside a rectangle."""

    case = problem.case
    rect = (110.0, 160.0, 670.0, 440.0)
    c1_raw = (250.0, 300.0)
    c2_raw = (530.0, 300.0)
    radius_raw = 140.0
    ctx.scene_transform.resolve(
        _rect_points(rect)
        + (
            (c1_raw[0] - radius_raw, c1_raw[1]),
            (c1_raw[0] + radius_raw, c1_raw[1]),
            (c1_raw[0], c1_raw[1] - radius_raw),
            (c1_raw[0], c1_raw[1] + radius_raw),
            (c2_raw[0] - radius_raw, c2_raw[1]),
            (c2_raw[0] + radius_raw, c2_raw[1]),
            (c2_raw[0], c2_raw[1] - radius_raw),
            (c2_raw[0], c2_raw[1] + radius_raw),
            (570.0, 112.0),
            (250.0, 262.0),
            (rect[0], rect[3] + 26.0),
            (rect[2], rect[3] + 26.0),
        )
    )
    rect_points = ctx.scene_transform.points(_rect_points(rect))
    c1 = ctx.scene_transform.point(c1_raw)
    c2 = ctx.scene_transform.point(c2_raw)
    radius_px = _transformed_radius(ctx, radius_raw)
    circle1_bbox = _ellipse_bbox(c1, radius_px)
    circle2_bbox = _ellipse_bbox(c2, radius_px)
    label_bboxes: dict[str, BBox] = {}
    use_gap_shading = problem.target_kind == "shaded_area" or problem.support_kind == "shaded_area"
    if use_gap_shading:
        ctx.draw.polygon(rect_points, fill=ctx.shaded_color)
        ctx.draw.ellipse(circle1_bbox, fill=ctx.fill_color)
        ctx.draw.ellipse(circle2_bbox, fill=ctx.fill_color)
    else:
        ctx.draw.polygon(rect_points, fill=ctx.fill_color)
    ctx.draw.line(_closed(rect_points), fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ctx.draw.ellipse(circle1_bbox, outline=ctx.accent_color, width=ctx.line_width)
    ctx.draw.ellipse(circle2_bbox, outline=ctx.accent_color, width=ctx.line_width)
    ctx.draw.line([c1, ctx.scene_transform.point((c1_raw[0] + radius_raw, c1_raw[1]))], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    if problem.support_kind == "shaded_area":
        label_bboxes["support"] = draw_label(ctx, problem.support_text, ctx.scene_transform.point((570.0, 112.0)), small=True)
    else:
        label_bboxes["support"] = _draw_dimension(
            ctx,
            ctx.scene_transform.point((rect[0], rect[3] + 26.0)),
            ctx.scene_transform.point((rect[2], rect[3] + 26.0)),
            problem.support_text,
        )
    if problem.target_kind == "radius":
        label_bboxes["target"] = draw_label(ctx, problem.target_text, ctx.scene_transform.point((250.0, 262.0)), small=True)
    else:
        label_bboxes["target"] = draw_label(ctx, problem.target_text, ctx.scene_transform.point((570.0, 112.0)), small=True)
    scene_bbox = bbox_from_points(rect_points, width=ctx.width, height=ctx.height, pad=10.0)
    support_bbox = pad_bbox(label_bboxes["support"], 4.0, width=ctx.width, height=ctx.height)
    circle1_padded = pad_bbox(circle1_bbox, 4.0, width=ctx.width, height=ctx.height)
    circle2_padded = pad_bbox(circle2_bbox, 4.0, width=ctx.width, height=ctx.height)
    witness = {
        "scene_variant": "two_circles_in_rectangle",
        "formula": str(problem.formula_text),
        "answer_value": float(problem.answer),
        **case_trace_values(case),
    }
    return _build_rendered_scene(
        ctx=ctx,
        problem=problem,
        target_bbox=label_bboxes["target"],
        scene_bbox=scene_bbox,
        support_bbox=support_bbox,
        label_bboxes=label_bboxes,
        scene_entities=(
            {"entity_id": "rectangle_container", "entity_type": "rectangle", "bbox": bbox_to_list(scene_bbox)},
            {
                "entity_id": "left_circle",
                "entity_type": "circle",
                "bbox": bbox_to_list(circle1_padded),
                "center": [round(c1[0], 3), round(c1[1], 3)],
                "radius_px": round(radius_px, 3),
            },
            {
                "entity_id": "right_circle",
                "entity_type": "circle",
                "bbox": bbox_to_list(circle2_padded),
                "center": [round(c2[0], 3), round(c2[1], 3)],
                "radius_px": round(radius_px, 3),
            },
        ),
        render_map={
            "scene_variant": "two_circles_in_rectangle",
            "rectangle_bbox": bbox_to_list(scene_bbox),
            "circle_bboxes": [bbox_to_list(circle1_padded), bbox_to_list(circle2_padded)],
        },
        witness=witness,
    )


__all__ = [
    "create_render_context",
    "render_circle_in_square_scene",
    "render_square_in_circle_scene",
    "render_two_circles_rectangle_scene",
]
