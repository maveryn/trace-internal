"""Rendering primitives for circular-sector formula diagrams."""

from __future__ import annotations

import math
from typing import Any, Mapping

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    draw_label,
    fmt_measure,
    pad_bbox,
)
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.text_rendering import load_font

from .defaults import SCENE_ID
from .state import BBox, Color, Point, RenderContext, RenderedSectorScene, SectorProblem


def create_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> RenderContext:
    """Create a styled analytical geometry canvas for one sector diagram."""

    width = int(params.get("canvas_width", rendering_defaults.get("canvas_width", 760)))
    height = int(params.get("canvas_height", rendering_defaults.get("canvas_height", 560)))
    background, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        allow_dark=True,
        require_grid=False,
    )
    fill_palette: tuple[tuple[Color, Color, Color], ...] = (
        ((92, 158, 236), (114, 204, 164), (25, 91, 168)),
        ((238, 148, 86), (117, 190, 219), (150, 72, 24)),
        ((144, 116, 220), (230, 108, 164), (96, 69, 160)),
        ((94, 188, 138), (238, 184, 82), (32, 119, 76)),
    )
    fill_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_ID}.fill_palette",
    ) % len(fill_palette)
    fill_color, secondary_fill_color, accent_color = fill_palette[int(fill_index)]
    readout_font_family = str(params.get("readout_font_family", rendering_defaults.get("readout_font_family", "roboto")))
    diagram_style_trace = dict(diagram_style_meta)
    diagram_style_trace["readout_font_family"] = readout_font_family
    image = background.convert("RGB")
    return RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=width,
        height=height,
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        fill_color=fill_color,
        secondary_fill_color=secondary_fill_color,
        accent_color=accent_color,
        line_width=max(2, int(params.get("line_width", rendering_defaults.get("line_width", 4)))),
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
        diagram_style_meta=diagram_style_trace,
        background_meta=dict(background_meta),
        fill_style_meta={
            "fill_palette_index": int(fill_index),
            "fill_color": list(fill_color),
            "secondary_fill_color": list(secondary_fill_color),
            "accent_color": list(accent_color),
        },
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_transform"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _point_on_circle(center: Point, radius: float, degrees: float) -> Point:
    radians = math.radians(float(degrees))
    return (
        float(center[0]) + float(radius) * math.cos(radians),
        float(center[1]) + float(radius) * math.sin(radians),
    )


def _draw_arc_band(ctx: RenderContext, box: BBox, *, start: float, end: float, color: Color, width_extra: int = 2) -> None:
    ctx.draw.arc(
        box,
        start=float(start),
        end=float(end),
        fill=color,
        width=max(5, int(ctx.line_width) + int(width_extra)),
    )


def _draw_dimension(
    ctx: RenderContext,
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
    label_center = (
        (float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]),
        (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]),
    )
    return draw_label(ctx, label, label_center, small=True)


def _draw_sector_base(ctx: RenderContext, problem: SectorProblem) -> dict[str, Any]:
    """Draw the common sector body and return projected geometry after rotation."""

    values = problem.values
    radius_px = 178.0
    center = (302.0, 306.0)
    start_deg = -142.0
    end_deg = start_deg + float(values.theta_degrees)
    ctx.scene_transform.resolve(
        (
            center,
            (center[0] - radius_px, center[1]),
            (center[0] + radius_px, center[1]),
            (center[0], center[1] - radius_px),
            (center[0], center[1] + radius_px),
        )
    )
    center = ctx.scene_transform.point(center)
    radius_px *= float(ctx.scene_transform.transform.scale)
    start_deg += float(ctx.scene_transform.transform.angle_degrees)
    end_deg += float(ctx.scene_transform.transform.angle_degrees)
    arc_box = (
        center[0] - radius_px,
        center[1] - radius_px,
        center[0] + radius_px,
        center[1] + radius_px,
    )
    ctx.draw.pieslice(
        arc_box,
        start=start_deg,
        end=end_deg,
        fill=ctx.fill_color,
        outline=ctx.line_color,
        width=ctx.line_width,
    )
    p0 = _point_on_circle(center, radius_px, start_deg)
    p1 = _point_on_circle(center, radius_px, end_deg)
    ctx.draw.line([center, p0], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([center, p1], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse((center[0] - 4, center[1] - 4, center[0] + 4, center[1] + 4), fill=ctx.line_color)
    _draw_arc_band(ctx, arc_box, start=start_deg, end=end_deg, color=ctx.accent_color, width_extra=3)
    return {
        "center": center,
        "radius_px": radius_px,
        "start_deg": start_deg,
        "end_deg": end_deg,
        "arc_box": arc_box,
        "p0": p0,
        "p1": p1,
        "sector_bbox": pad_bbox(arc_box, 8.0, width=ctx.width, height=ctx.height),
        "arc_bbox": bbox_from_points((p0, p1), width=ctx.width, height=ctx.height, pad=28.0),
    }


def _fmt_given(value: float) -> str:
    return f"{float(value):.1f}"


def _draw_visible_measure(ctx: RenderContext, problem: SectorProblem, radius_bbox: BBox) -> dict[str, BBox]:
    values = problem.values
    bboxes: dict[str, BBox] = {"radius_label": radius_bbox}
    if problem.visible_measure_kind == "arc_length":
        bboxes["arc_length_label"] = draw_label(ctx, f"arc={_fmt_given(values.arc_length)}", (590.0, 214.0), small=True)
    elif problem.visible_measure_kind == "sector_area":
        bboxes["sector_area_label"] = draw_label(ctx, f"Area={_fmt_given(values.sector_area)}", (590.0, 214.0), small=True)
    return bboxes


def render_sector_scene(
    ctx: RenderContext,
    problem: SectorProblem,
) -> RenderedSectorScene:
    """Render a sector diagram without public task/query routing in shared code."""

    values = problem.values
    base = _draw_sector_base(ctx, problem)
    center = base["center"]
    radius_px = float(base["radius_px"])
    start_deg = float(base["start_deg"])
    end_deg = float(base["end_deg"])
    mid_deg = (start_deg + end_deg) / 2.0
    radius_bbox = _draw_dimension(
        ctx,
        center,
        base["p0"],
        f"r={fmt_measure(values.radius_units)}",
        label_offset=(-18.0, 24.0),
    )

    annotation_bboxes: dict[str, BBox] = {
        "target_sector_region": base["sector_bbox"],
        "target_arc": base["arc_bbox"],
        **_draw_visible_measure(ctx, problem, radius_bbox),
    }
    if problem.visible_measure_kind in {"complement_relation", "supplement_relation"}:
        total = int(values.target_angle_total or 0)
        adjacent = int(values.adjacent_angle_degrees or 0)
        target_end = start_deg + float(total)
        p_target = _point_on_circle(center, radius_px, target_end)
        ctx.draw.line([center, p_target], fill=ctx.line_color, width=ctx.line_width)
        annotation_bboxes["angle_relation_label"] = draw_label(ctx, f"beta+{adjacent}={total}", (590.0, 232.0), small=True)

    if problem.target_kind in {"sector_angle", "related_angle"} or problem.visible_measure_kind in {
        "complement_relation",
        "supplement_relation",
    }:
        angle_text = "?" if problem.target_kind == "sector_angle" else "beta"
        annotation_bboxes["target_angle_cue"] = draw_label(
            ctx,
            angle_text,
            (
                center[0] + 58.0 * math.cos(math.radians(mid_deg)),
                center[1] + 58.0 * math.sin(math.radians(mid_deg)),
            ),
            small=False,
        )

    if problem.target_kind == "related_angle":
        total = int(values.target_angle_total or 0)
        target_start = end_deg
        target_end = start_deg + float(total)
        target_mid = (target_start + target_end) / 2.0
        target_radius = 86.0 if total < 360 else 124.0
        if total == 360:
            _draw_arc_band(ctx, base["arc_box"], start=end_deg, end=start_deg + 360.0, color=ctx.secondary_fill_color, width_extra=0)
        else:
            p_target = _point_on_circle(center, radius_px, target_end)
            ctx.draw.line([center, p_target], fill=ctx.line_color, width=ctx.line_width)
            small_box = (
                center[0] - target_radius,
                center[1] - target_radius,
                center[0] + target_radius,
                center[1] + target_radius,
            )
            _draw_arc_band(ctx, small_box, start=target_start, end=target_end, color=ctx.secondary_fill_color, width_extra=0)
        annotation_bboxes["target_related_angle_cue"] = draw_label(
            ctx,
            "?",
            (
                center[0] + target_radius * math.cos(math.radians(target_mid)),
                center[1] + target_radius * math.sin(math.radians(target_mid)),
            ),
            small=False,
        )
        annotation_bboxes["angle_relation_label"] = draw_label(ctx, f"?+beta={total}", (590.0, 252.0), small=True)

    scene_entities = (
        {
            "entity_id": "sector",
            "entity_type": "sector",
            "bbox": bbox_to_list(base["sector_bbox"]),
            "radius": int(values.radius_units),
            "theta_degrees": int(values.theta_degrees),
            "arc_length": float(values.arc_length),
            "sector_area": float(values.sector_area),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "target_bboxes": geometry_json_ready(annotation_bboxes),
        "sector_bbox": bbox_to_list(base["sector_bbox"]),
        "arc_bbox": bbox_to_list(base["arc_bbox"]),
        "scene_transform": dict(ctx.scene_transform.metadata()),
    }
    witness = {
        "formula_family": str(problem.formula_family),
        "pi_value": float(math.pi),
        "radius_units": int(values.radius_units),
        "theta_degrees": int(values.theta_degrees),
        "adjacent_angle_degrees": values.adjacent_angle_degrees,
        "angle_from_arc_length": float(values.angle_from_arc_length),
        "angle_from_sector_area": float(values.angle_from_sector_area),
        "arc_length": float(values.arc_length),
        "sector_area": float(values.sector_area),
        "target_angle_total": values.target_angle_total,
        "answer_value": float(problem.answer),
    }
    return RenderedSectorScene(
        image=ctx.image,
        annotation_bboxes=dict(annotation_bboxes),
        scene_entities=scene_entities,
        render_map=render_map,
        witness=witness,
        reasoning_steps=int(problem.reasoning_steps),
    )


__all__ = ["create_render_context", "render_sector_scene"]
