"""Rendering for incircle-tangent diagrams."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping

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
from .measurements import triangle_layout
from .state import Color, IncircleDiagramSpec, Point, RenderContext, RenderedIncircleScene


def _transform_layout(layout: Mapping[str, Point | float], ctx: RenderContext) -> Dict[str, Point | float]:
    points = [layout[key] for key in ("A", "B", "C")]
    xs = [float(point[0]) for point in points if isinstance(point, tuple)]
    ys = [float(point[1]) for point in points if isinstance(point, tuple)]
    margin_x = 112.0
    margin_top = 86.0
    margin_bottom = 98.0
    scale = min(
        (float(ctx.width) - 2.0 * margin_x) / max(1.0, max(xs) - min(xs)),
        (float(ctx.height) - margin_top - margin_bottom) / max(1.0, max(ys) - min(ys)),
    )
    left = (float(ctx.width) - (max(xs) - min(xs)) * scale) / 2.0
    bottom = float(ctx.height) - margin_bottom

    def tx(point: Point) -> Point:
        return (
            left + (float(point[0]) - min(xs)) * scale,
            bottom - (float(point[1]) - min(ys)) * scale,
        )

    transformed: Dict[str, Point | float] = {}
    for key, value in layout.items():
        transformed[key] = tx(value) if isinstance(value, tuple) else float(value) * scale
    return transformed


def _unit_vector(start: Point, end: Point) -> Point:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return (0.0, -1.0)
    return (dx / length, dy / length)


def _draw_tick(ctx: RenderContext, start: Point, end: Point, *, count: int, color: Color) -> None:
    ux, uy = _unit_vector(start, end)
    nx, ny = -uy, ux
    mid = ((float(start[0]) + float(end[0])) / 2.0, (float(start[1]) + float(end[1])) / 2.0)
    spacing = 5.0
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * spacing
        cx = mid[0] + ux * shift
        cy = mid[1] + uy * shift
        ctx.draw.line(
            [(cx - nx * 7.0, cy - ny * 7.0), (cx + nx * 7.0, cy + ny * 7.0)],
            fill=color,
            width=2,
        )


def _make_render_context(
    *,
    random_namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> tuple[RenderContext, Dict[str, Any]]:
    """Create canvas, style, font, and transform state for one diagram."""

    rng = spawn_rng(int(instance_seed), f"{random_namespace}.render")
    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 760)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
    image, background_meta = make_background_canvas(
        canvas_width=width,
        canvas_height=height,
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
    accents: tuple[Color, ...] = (
        (27, 113, 191),
        (189, 91, 37),
        (111, 92, 190),
        (30, 132, 92),
    )
    accent_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{random_namespace}.accent",
    )
    accent_color = accents[int(accent_index) % len(accents)]
    fill_color = (
        min(255, int(accent_color[0] * 0.18 + 255 * 0.82)),
        min(255, int(accent_color[1] * 0.18 + 255 * 0.82)),
        min(255, int(accent_color[2] * 0.18 + 255 * 0.82)),
    )
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(
        params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18))
    )
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
    ctx = RenderContext(
        rng=rng,
        image=image,
        draw=ImageDraw.Draw(image),
        width=width,
        height=height,
        line_color=shape_style.line_color,
        label_color=shape_style.label_color,
        label_stroke_color=shape_style.label_stroke_color,
        accent_color=accent_color,
        fill_color=fill_color,
        line_width=max(2, int(line_width)),
        font=load_font(max(12, int(font_size)), bold=False),
        small_font=load_font(max(10, int(small_font_size)), bold=False),
        scene_transform=LazySceneTransform(
            rng,
            params=params,
            render_defaults=render_defaults,
            canvas_width=width,
            canvas_height=height,
        ),
    )
    render_meta = {
        "background_style": dict(background_meta),
        "shape_style": shape_style.to_trace_dict(),
        "line_width": int(ctx.line_width),
        "label_font_size": int(font_size),
        "small_label_font_size": int(small_font_size),
        "accent_color": list(accent_color),
        "fill_color": list(fill_color),
    }
    return ctx, render_meta


def _render_incircle_scene(ctx: RenderContext, spec: IncircleDiagramSpec) -> RenderedIncircleScene:
    """Draw the triangle grammar and return labels projected after final transform."""

    raw_layout = triangle_layout(spec)
    layout = _transform_layout(raw_layout, ctx)
    point_layout = {key: value for key, value in layout.items() if isinstance(value, tuple)}
    ctx.scene_transform.resolve(tuple(point_layout.values()))
    point_layout = ctx.scene_transform.keyed_points(point_layout)
    for key, value in point_layout.items():
        layout[key] = value
    inradius_px = float(layout["inradius"]) * float(ctx.scene_transform.transform.scale)

    a = point_layout["A"]
    b = point_layout["B"]
    c = point_layout["C"]
    d = point_layout["D"]
    e = point_layout["E"]
    f = point_layout["F"]
    o = point_layout["O"]

    ctx.draw.polygon([a, b, c], fill=ctx.fill_color)
    ctx.draw.line([a, b, c, a], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ctx.draw.ellipse(
        (o[0] - inradius_px, o[1] - inradius_px, o[0] + inradius_px, o[1] + inradius_px),
        outline=ctx.accent_color,
        width=max(2, ctx.line_width - 1),
    )
    for point in (d, e, f):
        ctx.draw.ellipse((point[0] - 4.0, point[1] - 4.0, point[0] + 4.0, point[1] + 4.0), fill=ctx.accent_color)
    for label, point, offset in (
        ("A", a, (-20.0, 22.0)),
        ("B", b, (20.0, 22.0)),
        ("C", c, (0.0, -24.0)),
        ("O", o, (0.0, 23.0)),
    ):
        ctx.draw.ellipse((point[0] - 3.5, point[1] - 3.5, point[0] + 3.5, point[1] + 3.5), fill=ctx.line_color)
        draw_label(ctx, label, (point[0] + offset[0], point[1] + offset[1]), small=True)

    _draw_tick(ctx, a, d, count=1, color=ctx.accent_color)
    _draw_tick(ctx, a, f, count=1, color=ctx.accent_color)
    _draw_tick(ctx, b, d, count=2, color=ctx.accent_color)
    _draw_tick(ctx, b, e, count=2, color=ctx.accent_color)
    _draw_tick(ctx, c, e, count=3, color=ctx.accent_color)
    _draw_tick(ctx, c, f, count=3, color=ctx.accent_color)

    label_bboxes: Dict[str, tuple[float, float, float, float]] = {
        "AD_AF": draw_label(ctx, f"AD=AF={fmt_measure(spec.tangent_a)}", (a[0] - 4.0, a[1] + 54.0), small=True),
        "BD_BE": draw_label(ctx, f"BD=BE={fmt_measure(spec.tangent_b)}", (b[0] + 8.0, b[1] + 54.0), small=True),
        "CE_CF": draw_label(ctx, f"CE=CF={fmt_measure(spec.tangent_c)}", (c[0], c[1] - 52.0), small=True),
    }
    if spec.show_area_label:
        label_bboxes["area"] = draw_label(ctx, f"Area={fmt_measure(spec.displayed_area)}", (596.0, 96.0), small=True)
    if spec.show_radius_segment:
        ctx.draw.line([o, d], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    if spec.unknown_label:
        if spec.show_radius_segment:
            label_center = ((o[0] + d[0]) / 2.0 - 28.0, (o[1] + d[1]) / 2.0)
        else:
            label_center = (o[0], o[1] - 62.0)
        label_bboxes["unknown"] = draw_label(ctx, spec.unknown_label, label_center, small=True)

    triangle_bbox = bbox_from_points((a, b, c), width=ctx.width, height=ctx.height, pad=10.0)
    incircle_bbox = pad_bbox(
        (o[0] - inradius_px, o[1] - inradius_px, o[0] + inradius_px, o[1] + inradius_px),
        6.0,
        width=ctx.width,
        height=ctx.height,
    )
    scene_entities = (
        {
            "entity_id": "triangle_ABC",
            "entity_type": "triangle",
            "vertices": {
                "A": [round(a[0], 3), round(a[1], 3)],
                "B": [round(b[0], 3), round(b[1], 3)],
                "C": [round(c[0], 3), round(c[1], 3)],
            },
            "side_lengths": {
                "AB": round(float(spec.side_ab), 3),
                "BC": round(float(spec.side_bc), 3),
                "CA": round(float(spec.side_ca), 3),
            },
            "bbox": bbox_to_list(triangle_bbox),
        },
        {
            "entity_id": "incircle",
            "entity_type": "circle",
            "center": [round(o[0], 3), round(o[1], 3)],
            "radius_px": round(inradius_px, 3),
            "radius_units": round(float(spec.inradius), 3),
            "bbox": bbox_to_list(incircle_bbox),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "points": {
            key: [round(value[0], 3), round(value[1], 3)]
            for key, value in point_layout.items()
        },
        "incircle_radius_px": round(inradius_px, 3),
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
    }
    return RenderedIncircleScene(
        image=ctx.image,
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map=render_map,
        annotation_roles=tuple(spec.annotation_roles),
    )


def render_incircle_scene_with_retries(
    *,
    random_namespace: str,
    spec: IncircleDiagramSpec,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    max_attempts: int,
) -> tuple[RenderedIncircleScene, Dict[str, Any]]:
    """Render one incircle scene, retrying if a sampled layout fails."""

    last_error: Exception | None = None
    for _attempt in range(max(1, int(max_attempts))):
        try:
            ctx, render_meta = _make_render_context(
                random_namespace=str(random_namespace),
                instance_seed=int(instance_seed),
                params=params,
                render_defaults=render_defaults,
            )
            rendered = _render_incircle_scene(ctx, spec)
            render_meta = dict(render_meta)
            render_meta["single_object_scene_rotation"] = ctx.scene_transform.metadata()
            return rendered, render_meta
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"failed to render incircle_tangents scene for {random_namespace}") from last_error


__all__ = ["render_incircle_scene_with_retries"]
