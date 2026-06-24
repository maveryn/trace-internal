"""Rendering primitives for trapezoid-extension diagrams."""

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
from trace.tasks.shared.text_rendering import load_font

from .defaults import BACKGROUND_DEFAULTS
from .measurements import case_trace_values
from .state import (
    BBox,
    Color,
    Point,
    RenderContext,
    RenderedTrapezoidExtensionScene,
    TrapezoidExtensionProblem,
)


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


def _draw_dashed_line(
    ctx: RenderContext,
    start: Point,
    end: Point,
    *,
    fill: Color | None = None,
    width: int | None = None,
    dash: float = 14.0,
    gap: float = 8.0,
) -> None:
    color = fill if fill is not None else ctx.muted_color
    line_width = int(width if width is not None else ctx.line_width)
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return
    ux = dx / length
    uy = dy / length
    distance = 0.0
    while distance < length:
        next_distance = min(length, distance + dash)
        p0 = (float(start[0]) + ux * distance, float(start[1]) + uy * distance)
        p1 = (float(start[0]) + ux * next_distance, float(start[1]) + uy * next_distance)
        ctx.draw.line([p0, p1], fill=color, width=line_width)
        distance += dash + gap


def _draw_height_marker(ctx: RenderContext, top: Point, bottom: Point, label: str, label_center: Point) -> BBox:
    tick = 11.0 * float(ctx.scene_transform.transform.scale)
    dx = float(bottom[0]) - float(top[0])
    dy = float(bottom[1]) - float(top[1])
    length = max(1e-9, math.hypot(dx, dy))
    nx = -dy / length
    ny = dx / length
    ctx.draw.line([top, bottom], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    ctx.draw.line(
        [(top[0] - nx * tick, top[1] - ny * tick), (top[0] + nx * tick, top[1] + ny * tick)],
        fill=ctx.accent_color,
        width=max(2, ctx.line_width - 1),
    )
    ctx.draw.line(
        [
            (bottom[0] - nx * tick, bottom[1] - ny * tick),
            (bottom[0] + nx * tick, bottom[1] + ny * tick),
        ],
        fill=ctx.accent_color,
        width=max(2, ctx.line_width - 1),
    )
    label_bbox = draw_label(ctx, label, label_center, small=True)
    marker_bbox = bbox_from_points(
        (
            (top[0] - nx * tick, top[1] - ny * tick),
            (top[0] + nx * tick, top[1] + ny * tick),
            (bottom[0] - nx * tick, bottom[1] - ny * tick),
            (bottom[0] + nx * tick, bottom[1] + ny * tick),
        ),
        width=ctx.width,
        height=ctx.height,
        pad=5.0,
    )
    return _union_bboxes((marker_bbox, label_bbox), width=ctx.width, height=ctx.height)


def create_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    namespace: str,
) -> tuple[RenderContext, dict[str, Any]]:
    """Create a styled PIL render context for one trapezoid-extension sample."""

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
        ((229, 240, 255), (255, 226, 199), (26, 123, 185), (126, 143, 156)),
        ((236, 247, 232), (255, 224, 210), (38, 143, 104), (150, 142, 132)),
        ((248, 238, 252), (226, 242, 255), (123, 95, 190), (143, 154, 172)),
        ((255, 244, 224), (226, 240, 255), (196, 102, 44), (132, 146, 160)),
    )
    palette_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.palette",
    )
    fill_color, extension_fill_color, accent_color, muted_color = palettes[int(palette_index) % len(palettes)]
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
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
        extension_fill_color=extension_fill_color,
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
        "extension_fill_color": list(extension_fill_color),
        "accent_color": list(accent_color),
        "muted_color": list(muted_color),
    }


def render_trapezoid_extension_scene(
    ctx: RenderContext,
    problem: TrapezoidExtensionProblem,
) -> RenderedTrapezoidExtensionScene:
    """Draw one resolved trapezoid-completion construction and projected witnesses."""

    case = problem.case
    a = (135.0, 170.0)
    b = (355.0, 170.0)
    e = (685.0, 170.0)
    d = (95.0, 420.0)
    c = (645.0, 420.0)
    raw_label_points = {
        "top_base": (245.0, 132.0),
        "height_top": (56.0, 170.0),
        "height_bottom": (56.0, 420.0),
        "height_label": (98.0, 295.0),
        "parallelogram_area": (520.0, 84.0),
        "parallelogram_perimeter": (520.0, 84.0),
        "side": (94.0, 288.0),
        "extension": (520.0, 132.0),
        "bottom_base": (370.0, 458.0),
        "target_extension": (520.0, 202.0),
        "target_area": (520.0, 505.0),
    }
    ctx.scene_transform.resolve((a, b, e, d, c, *raw_label_points.values()))
    a, b, e, d, c = ctx.scene_transform.points((a, b, e, d, c))
    label_points = ctx.scene_transform.keyed_points(raw_label_points)

    trapezoid_points = (a, b, c, d)
    extension_points = (b, e, c)
    parallelogram_points = (a, e, c, d)
    ctx.draw.polygon(trapezoid_points, fill=ctx.fill_color)
    ctx.draw.polygon(extension_points, fill=ctx.extension_fill_color)
    ctx.draw.line([a, b, c, d, a], fill=ctx.line_color, width=ctx.line_width)
    _draw_dashed_line(ctx, b, e, fill=ctx.muted_color, width=ctx.line_width)
    _draw_dashed_line(ctx, e, c, fill=ctx.muted_color, width=ctx.line_width)
    ctx.draw.line([d, c], fill=ctx.line_color, width=ctx.line_width)

    label_bboxes: dict[str, BBox] = {}
    label_bboxes["top_base"] = draw_label(ctx, f"AB={case.top_base}", label_points["top_base"], small=True)
    label_bboxes["height"] = _draw_height_marker(
        ctx,
        label_points["height_top"],
        label_points["height_bottom"],
        f"h={case.height}",
        label_points["height_label"],
    )
    for label in problem.support_labels:
        label_bboxes[str(label.role)] = draw_label(
            ctx,
            str(label.text),
            label_points[str(label.position_key)],
            small=True,
        )
    label_bboxes["target"] = draw_label(
        ctx,
        str(problem.target_text),
        label_points[str(problem.target_position_key)],
        small=True,
    )

    support_bboxes = [label_bboxes["top_base"]]
    if bool(problem.include_height_in_support):
        support_bboxes.append(label_bboxes["height"])
    support_bboxes.extend(label_bboxes[str(label.role)] for label in problem.support_labels)
    original_bbox = bbox_from_points(trapezoid_points, width=ctx.width, height=ctx.height, pad=10.0)
    dashed_completion_bbox = bbox_from_points(extension_points, width=ctx.width, height=ctx.height, pad=10.0)
    completed_bbox = bbox_from_points(parallelogram_points, width=ctx.width, height=ctx.height, pad=10.0)
    supporting_bbox = _union_bboxes(tuple(support_bboxes), width=ctx.width, height=ctx.height, pad=4.0)

    annotation_bboxes = {
        "target_cue": label_bboxes["target"],
        "original_trapezoid": original_bbox,
        "dashed_parallelogram_completion": dashed_completion_bbox,
        "supporting_visible_labels": supporting_bbox,
    }
    scene_entities = (
        {
            "entity_id": "original_trapezoid",
            "entity_type": "trapezoid",
            "bbox": bbox_to_list(original_bbox),
            "points": [[round(x, 3), round(y, 3)] for x, y in trapezoid_points],
        },
        {
            "entity_id": "completion_triangle",
            "entity_type": "dashed_extension_region",
            "bbox": bbox_to_list(dashed_completion_bbox),
            "points": [[round(x, 3), round(y, 3)] for x, y in extension_points],
        },
        {
            "entity_id": "completed_parallelogram",
            "entity_type": "parallelogram",
            "bbox": bbox_to_list(completed_bbox),
            "points": [[round(x, 3), round(y, 3)] for x, y in parallelogram_points],
        },
    )
    witness = {
        "formula_family": str(problem.formula_family),
        "formula": str(problem.formula_text),
        "answer_value": float(problem.answer),
        "target_support_probabilities": dict(problem.target_support_probabilities),
        **case_trace_values(case),
    }
    return RenderedTrapezoidExtensionScene(
        image=ctx.image,
        answer=float(problem.answer),
        annotation_bboxes=dict(annotation_bboxes),
        annotation_roles=tuple(annotation_bboxes.keys()),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "coord_space": "pixel",
            "original_trapezoid": {
                "points": [[round(x, 3), round(y, 3)] for x, y in trapezoid_points],
                "bbox": bbox_to_list(original_bbox),
            },
            "completion_triangle": {
                "points": [[round(x, 3), round(y, 3)] for x, y in extension_points],
                "bbox": bbox_to_list(dashed_completion_bbox),
            },
            "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        },
        witness=witness,
    )


__all__ = ["create_render_context", "fmt_measure", "render_trapezoid_extension_scene"]
