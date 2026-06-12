"""Rendering helpers for circle-pair external tangent diagrams."""

from __future__ import annotations

from typing import Any, Mapping

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import (
    assert_bboxes_inside,
    bbox_from_points,
    bbox_to_list,
    draw_dimension_line,
    draw_readout_centered,
    draw_right_angle_marker,
)
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import (
    add,
    mul,
    perp,
    point_to_list,
    sub,
    unit,
)

from .state import (
    BBox,
    Color,
    PairTangentDiagramSpec,
    PairTangentRenderContext,
    Point,
    RenderedPairTangentScene,
    SCENE_ID,
)


def create_pair_tangent_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> PairTangentRenderContext:
    """Create a styled PIL render context for one pair-tangent diagram."""

    width = int(params.get("canvas_width", group_default(rendering_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(rendering_defaults, "canvas_height", 600)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=False,
        require_grid=None,
    )
    fill_palettes: tuple[tuple[Color, Color], ...] = (
        ((238, 246, 255), (255, 247, 231)),
        ((241, 248, 239), (246, 242, 255)),
        ((255, 242, 235), (232, 246, 250)),
        ((248, 247, 240), (234, 242, 255)),
    )
    fill_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_ID}.fill_palette",
    )
    circle_fill_o1, circle_fill_o2 = fill_palettes[int(fill_index) % len(fill_palettes)]
    font_size = int(params.get("label_font_size", group_default(rendering_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(rendering_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(rendering_defaults, "line_width", 3)))
    label_stroke_width = int(
        params.get(
            "label_stroke_width",
            group_default(rendering_defaults, "label_stroke_width", int(diagram_style.label_stroke_width_px)),
        )
    )
    return PairTangentRenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        label_backing_color=tuple(int(value) for value in diagram_style.panel_fill_rgb),
        circle_fill_o1=tuple(int(value) for value in circle_fill_o1),
        circle_fill_o2=tuple(int(value) for value in circle_fill_o2),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, int(label_stroke_width)),
        font=load_font(max(12, int(font_size))),
        small_font=load_font(max(10, int(small_font_size))),
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


def _ellipse_bbox(center: Point, radius: float) -> BBox:
    return (
        float(center[0]) - float(radius),
        float(center[1]) - float(radius),
        float(center[0]) + float(radius),
        float(center[1]) + float(radius),
    )


def render_pair_tangent_scene(
    ctx: PairTangentRenderContext,
    spec: PairTangentDiagramSpec,
    *,
    instance_seed: int,
    render_namespace: str,
) -> RenderedPairTangentScene:
    """Draw two separated circles and their external common tangent."""

    rng = spawn_rng(int(instance_seed), str(render_namespace))
    radius_o1 = float(spec.radius_o1)
    radius_o2 = float(spec.radius_o2)
    center_distance = float(spec.center_distance)
    tangent_length = float(spec.tangent_length)
    delta = radius_o2 - radius_o1
    side_sign = 1.0 if str(spec.tangent_side) == "above" else -1.0

    u_unit = (tangent_length / center_distance, side_sign * delta / center_distance)
    n_unit = (delta / center_distance, -side_sign * tangent_length / center_distance)

    o1_local = (0.0, 0.0)
    o2_local = (center_distance, 0.0)
    t1_local = add(o1_local, mul(n_unit, radius_o1))
    t2_local = add(o2_local, mul(n_unit, radius_o2))

    local_points = (
        add(o1_local, (-radius_o1, -radius_o1)),
        add(o1_local, (radius_o1, radius_o1)),
        add(o2_local, (-radius_o2, -radius_o2)),
        add(o2_local, (radius_o2, radius_o2)),
        t1_local,
        t2_local,
    )
    min_x = min(point[0] for point in local_points)
    max_x = max(point[0] for point in local_points)
    min_y = min(point[1] for point in local_points)
    max_y = max(point[1] for point in local_points)
    span_x = max(1e-6, float(max_x - min_x))
    span_y = max(1e-6, float(max_y - min_y))
    scale = min((ctx.width - 190.0) / span_x, (ctx.height - 160.0) / span_y)
    scale *= float(rng.uniform(0.86, 0.95))
    local_center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    target_center = (
        (ctx.width / 2.0) + float(rng.uniform(-28.0, 28.0)),
        (ctx.height / 2.0) + float(rng.uniform(-22.0, 22.0)),
    )

    def transform(point: Point) -> Point:
        return (
            (float(point[0]) - float(local_center[0])) * float(scale) + float(target_center[0]),
            (float(point[1]) - float(local_center[1])) * float(scale) + float(target_center[1]),
        )

    o1 = transform(o1_local)
    o2 = transform(o2_local)
    t1 = transform(t1_local)
    t2 = transform(t2_local)
    radius_o1_px = radius_o1 * scale
    radius_o2_px = radius_o2 * scale
    ctx.scene_transform.resolve((o1, o2, t1, t2))
    o1, o2, t1, t2 = ctx.scene_transform.points((o1, o2, t1, t2))
    radius_o1_px *= float(ctx.scene_transform.transform.scale)
    radius_o2_px *= float(ctx.scene_transform.transform.scale)
    u_px = sub(t2, t1)
    n_px = sub(t1, o1)

    o1_bbox = _ellipse_bbox(o1, radius_o1_px)
    o2_bbox = _ellipse_bbox(o2, radius_o2_px)
    assert_bboxes_inside(
        (o1_bbox, o2_bbox),
        width=ctx.width,
        height=ctx.height,
        error_message="circle-pair tangent label too close to canvas edge",
    )

    ctx.draw.ellipse(o1_bbox, fill=ctx.circle_fill_o1, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(o2_bbox, fill=ctx.circle_fill_o2, outline=ctx.line_color, width=ctx.line_width)

    center_label_offset = (0.0, 26.0 if str(spec.tangent_side) == "above" else -26.0)
    tangent_label_offset = (0.0, -28.0 if str(spec.tangent_side) == "above" else 28.0)
    radius_label_shift = mul(perp(n_px), 0.18)

    label_bboxes: dict[str, BBox] = {}
    label_bboxes["center_distance"] = draw_dimension_line(
        ctx,
        o1,
        o2,
        str(spec.center_segment_label),
        label_offset=center_label_offset,
        color=ctx.secondary_color,
        tick_px=7.0,
        backed=False,
    )
    label_bboxes["radius_o1"] = draw_dimension_line(
        ctx,
        o1,
        t1,
        f"r1={int(spec.radius_o1)}",
        label_offset=radius_label_shift,
        color=ctx.secondary_color,
        tick_px=7.0,
        backed=False,
    )
    label_bboxes["radius_o2"] = draw_dimension_line(
        ctx,
        o2,
        t2,
        f"r2={int(spec.radius_o2)}",
        label_offset=mul(radius_label_shift, -1.0),
        color=ctx.secondary_color,
        tick_px=7.0,
        backed=False,
    )

    extension = max(18.0, ctx.line_width * 7.0)
    tangent_start = add(t1, mul(unit(u_px), -extension))
    tangent_end = add(t2, mul(unit(u_px), extension))
    ctx.draw.line([tangent_start, tangent_end], fill=ctx.accent_color, width=ctx.line_width + 1)
    label_bboxes["tangent_length"] = draw_dimension_line(
        ctx,
        t1,
        t2,
        str(spec.tangent_segment_label),
        label_offset=tangent_label_offset,
        color=ctx.accent_color,
        tick_px=7.0,
        backed=False,
    )

    label_bboxes["right_angle_t1"] = draw_right_angle_marker(ctx, t1, arm_a=mul(n_px, -1.0), arm_b=u_px)
    label_bboxes["right_angle_t2"] = draw_right_angle_marker(ctx, t2, arm_a=mul(n_px, -1.0), arm_b=u_px)

    dot_radius = max(3, int(ctx.line_width + 1))
    point_label_offsets = {
        "O1": (-18.0, 18.0),
        "O2": (18.0, 18.0),
        "T1": (-22.0, -20.0 if str(spec.tangent_side) == "above" else 20.0),
        "T2": (22.0, -20.0 if str(spec.tangent_side) == "above" else 20.0),
    }
    for label, point in (("O1", o1), ("O2", o2), ("T1", t1), ("T2", t2)):
        ctx.draw.ellipse(
            (point[0] - dot_radius, point[1] - dot_radius, point[0] + dot_radius, point[1] + dot_radius),
            fill=ctx.line_color if label.startswith("O") else ctx.accent_color,
            outline=ctx.line_color,
            width=1,
        )
        label_bboxes[f"{label}_label"] = draw_readout_centered(
            ctx,
            label,
            add(point, point_label_offsets[label]),
            small=True,
            backed=False,
        )
    assert_bboxes_inside(
        label_bboxes.values(),
        width=ctx.width,
        height=ctx.height,
        error_message="circle-pair tangent label too close to canvas edge",
    )

    annotation = {"O1": o1, "O2": o2, "T1": t1, "T2": t2}
    scene_entities = (
        {
            "entity_id": "circle_o1",
            "entity_type": "circle",
            "center": point_to_list(o1),
            "radius_units": int(spec.radius_o1),
            "radius_px": round(float(radius_o1_px), 3),
            "bbox": bbox_to_list(o1_bbox),
        },
        {
            "entity_id": "circle_o2",
            "entity_type": "circle",
            "center": point_to_list(o2),
            "radius_units": int(spec.radius_o2),
            "radius_px": round(float(radius_o2_px), 3),
            "bbox": bbox_to_list(o2_bbox),
        },
        {
            "entity_id": "common_tangent_segment",
            "entity_type": "segment",
            "endpoints": [point_to_list(t1), point_to_list(t2)],
            "length_units": int(spec.tangent_length),
            "bbox": bbox_to_list(bbox_from_points((t1, t2), width=ctx.width, height=ctx.height, pad=16.0)),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "centers": {"O1": point_to_list(o1), "O2": point_to_list(o2)},
        "tangent_points": {"T1": point_to_list(t1), "T2": point_to_list(t2)},
        "circle_bboxes": {"O1": bbox_to_list(o1_bbox), "O2": bbox_to_list(o2_bbox)},
        "tangent_segment": [point_to_list(t1), point_to_list(t2)],
        "center_segment": [point_to_list(o1), point_to_list(o2)],
        "radii_segments": {"O1T1": [point_to_list(o1), point_to_list(t1)], "O2T2": [point_to_list(o2), point_to_list(t2)]},
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "scale_px_per_unit": round(float(scale), 3),
        "tangent_side": str(spec.tangent_side),
        "larger_circle_side": str(spec.larger_circle_side),
    }
    return RenderedPairTangentScene(
        image=ctx.image,
        annotation_keyed_points={key: tuple(value) for key, value in annotation.items()},
        annotation_roles=tuple(spec.annotation_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map=render_map,
    )


__all__ = [
    "create_pair_tangent_render_context",
    "render_pair_tangent_scene",
]
