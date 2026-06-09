"""Geometry measurement tasks with visible tools placed on shapes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_geometry_measurement_complexity,
    clamp_unit_interval,
)
from ..shared.diagram_style import (
    geometry_diagram_style_metadata,
    prepare_geometry_diagram_style_and_background,
)
from ..shared.fixed_query_task import geometry_selected_probability_map as _selected_probability_map
from ..shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    pad_bbox,
    round1,
)
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.vector2d import add as _add, mul as _scale, point_to_list as _round_point, sub as _sub

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "measuring_tools"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_measuring_tools_v0"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)
_LENGTH_SUPPORT: Tuple[int, ...] = tuple(range(2, 9))
_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(30, 151, 5))


@dataclass(frozen=True)
class _ResolvedProblem:
    """Sampled measuring-tool problem parameters."""

    query_id: str
    answer: float
    answer_probabilities: Dict[str, float]
    target_length: int | None = None
    target_angle: int | None = None
    ruler_start_cm: int | None = None
    ruler_max_cm: int | None = None
    shape_kind: str = ""


@dataclass
class _RenderContext:
    """Rendering context shared by measuring-tool scene drawers."""

    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    guide_color: Color
    label_color: Color
    label_stroke_color: Color
    panel_fill: Color
    panel_alt_fill: Color
    panel_border: Color
    accent_color: Color
    secondary_accent_color: Color
    line_width: int
    font: Any
    small_font: Any
    tiny_font: Any


@dataclass(frozen=True)
class _RenderedToolScene:
    """Rendered measuring-tool scene plus verifier payload fragments."""

    image: Image.Image
    answer: float
    annotation_keyed_points: Dict[str, list[float]]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _resolve_supported_value(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    explicit_key: str,
    support: Sequence[int],
) -> tuple[int, Dict[str, float]]:
    """Resolve one target value with balanced deterministic support cycling."""

    supported_values = tuple(int(value) for value in support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(supported_values):
            raise ValueError(f"{explicit_key}={selected} is outside support for {task_id}")
        return selected, _selected_probability_map(
            supported_values,
            selected,
            key_fn=lambda value: str(int(value)),
            is_selected=lambda value, target: int(value) == int(target),
        )
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{explicit_key}",
    )
    selected = supported_values[int(index) % len(supported_values)]
    probability = 1.0 / float(len(supported_values))
    return selected, {str(value): float(probability) for value in supported_values}


def _resolve_query_id(
    *,
    task_id: str,
    query_ids: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> str:
    """Resolve the task-internal query branch."""

    explicit = params.get("query_id")
    supported = tuple(str(query_id) for query_id in query_ids)
    if explicit is not None:
        query_id = str(explicit)
        if query_id not in supported:
            raise ValueError(f"query_id={query_id!r} is outside support for {task_id}")
        return query_id
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_id",
    )
    return supported[int(index) % len(supported)]


def _resolve_problem(
    *,
    task_id: str,
    query_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _ResolvedProblem:
    """Resolve one measuring-tool problem."""

    if query_id in {"polygon_side_ruler_reading", "circle_radius_ruler_reading"}:
        length_min = int(params.get("length_min", group_default(gen_defaults, "length_min", 2)))
        length_max = int(params.get("length_max", group_default(gen_defaults, "length_max", 8)))
        support = tuple(range(length_min, length_max + 1))
        if not support:
            raise ValueError("length support is empty")
        target, probabilities = _resolve_supported_value(
            task_id=task_id,
            params=params,
            instance_seed=instance_seed,
            explicit_key="target_length",
            support=support,
        )
        ruler_max = int(params.get("ruler_max_cm", group_default(gen_defaults, "ruler_max_cm", 10)))
        if int(ruler_max) <= int(target):
            raise ValueError("ruler_max_cm must exceed target_length")
        max_start = int(ruler_max) - int(target)
        start_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.ruler_start_cm",
        )
        explicit_start = params.get("ruler_start_cm")
        start_cm = int(explicit_start) if explicit_start is not None else int(start_index) % (max_start + 1)
        if start_cm < 0 or start_cm + int(target) > int(ruler_max):
            raise ValueError("ruler_start_cm plus target_length exceeds ruler range")
        shape_options = ("triangle", "parallelogram", "trapezoid")
        shape_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.shape_kind",
        )
        return _ResolvedProblem(
            query_id=str(query_id),
            answer=float(target),
            target_length=int(target),
            ruler_start_cm=int(start_cm),
            ruler_max_cm=int(ruler_max),
            answer_probabilities=probabilities,
            shape_kind=shape_options[int(shape_index) % len(shape_options)]
            if query_id == "polygon_side_ruler_reading"
            else "circle",
        )
    if query_id in {"triangle_vertex_protractor_reading", "quadrilateral_vertex_protractor_reading"}:
        angle_min = int(params.get("angle_min", group_default(gen_defaults, "angle_min", 30)))
        angle_max = int(params.get("angle_max", group_default(gen_defaults, "angle_max", 150)))
        angle_step = int(params.get("angle_step", group_default(gen_defaults, "angle_step", 5)))
        support = tuple(value for value in range(angle_min, angle_max + 1, angle_step))
        if not support:
            raise ValueError("angle support is empty")
        target, probabilities = _resolve_supported_value(
            task_id=task_id,
            params=params,
            instance_seed=instance_seed,
            explicit_key="target_angle",
            support=support,
        )
        return _ResolvedProblem(
            query_id=str(query_id),
            answer=float(target),
            target_angle=int(target),
            answer_probabilities=probabilities,
            shape_kind="triangle" if query_id == "triangle_vertex_protractor_reading" else "quadrilateral",
        )
    raise ValueError(f"unsupported measuring-tools query_id: {query_id}")


def _make_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    task_id: str,
) -> tuple[_RenderContext, Dict[str, Any]]:
    """Create one styled rendering context."""

    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 760)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
    protected = ((205, 70, 52), (30, 126, 185), (38, 150, 95))
    image, background_meta, diagram_style, style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        task_group=TASK_GROUP,
        canvas_width=width,
        canvas_height=height,
        protected_colors=protected,
        allow_dark=False,
        require_grid=False,
    )
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(
        params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 17))
    )
    tiny_font_size = int(
        params.get("tiny_label_font_size", group_default(render_defaults, "tiny_label_font_size", 13))
    )
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
    ctx = _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=width,
        height=height,
        line_color=tuple(int(v) for v in diagram_style.stroke_rgb),
        secondary_color=tuple(int(v) for v in diagram_style.secondary_stroke_rgb),
        guide_color=tuple(int(v) for v in diagram_style.guide_rgb),
        label_color=tuple(int(v) for v in diagram_style.label_rgb),
        label_stroke_color=tuple(int(v) for v in diagram_style.label_stroke_rgb),
        panel_fill=tuple(int(v) for v in diagram_style.panel_fill_rgb),
        panel_alt_fill=tuple(int(v) for v in diagram_style.panel_alt_fill_rgb),
        panel_border=tuple(int(v) for v in diagram_style.panel_border_rgb),
        accent_color=tuple(int(v) for v in diagram_style.accent_rgb),
        secondary_accent_color=tuple(int(v) for v in diagram_style.secondary_accent_rgb),
        line_width=max(2, line_width),
        font=load_font(max(12, font_size), bold=True),
        small_font=load_font(max(10, small_font_size), bold=True),
        tiny_font=load_font(max(8, tiny_font_size), bold=True),
    )
    render_meta = {
        "background_style": dict(background_meta),
        "technical_diagram_style": geometry_diagram_style_metadata(diagram_style),
        "technical_diagram_style_resolution": dict(style_meta),
        "line_width": int(ctx.line_width),
        "label_font_size": int(font_size),
        "small_label_font_size": int(small_font_size),
        "tiny_label_font_size": int(tiny_font_size),
        "task_style_namespace": str(task_id),
    }
    return ctx, render_meta


def _unit_from_degrees(degrees: float) -> Point:
    theta = math.radians(float(degrees))
    return (math.cos(theta), math.sin(theta))


def _normal(axis: Point) -> Point:
    return (-float(axis[1]), float(axis[0]))


def _draw_text(
    ctx: _RenderContext,
    text: str,
    center: Point,
    *,
    font: Any | None = None,
    fill: Color | None = None,
    stroke_width: int = 1,
) -> BBox:
    """Draw centered text and return its padded bbox."""

    active_font = font or ctx.small_font
    active_fill = fill or ctx.label_color
    bbox = ctx.draw.textbbox((0, 0), str(text), font=active_font, stroke_width=stroke_width)
    text_w = float(bbox[2] - bbox[0])
    text_h = float(bbox[3] - bbox[1])
    left = float(center[0]) - (text_w / 2.0)
    top = float(center[1]) - (text_h / 2.0)
    draw_text_traced(
        ctx.draw,
        (left, top),
        str(text),
        font=active_font,
        fill=active_fill,
        stroke_width=int(stroke_width),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((left, top, left + text_w, top + text_h), 3.0, width=ctx.width, height=ctx.height)


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: Point,
    end: Point,
    *,
    fill: Color,
    width: int,
    dash: float = 8.0,
    gap: float = 6.0,
) -> None:
    """Draw a deterministic dashed line."""

    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return
    ux, uy = dx / length, dy / length
    pos = 0.0
    while pos < length:
        seg_end = min(length, pos + dash)
        draw.line(
            [(sx + ux * pos, sy + uy * pos), (sx + ux * seg_end, sy + uy * seg_end)],
            fill=fill,
            width=max(1, int(width)),
        )
        pos = seg_end + gap


def _draw_rotated_ruler(
    ctx: _RenderContext,
    *,
    zero_point: Point,
    axis: Point,
    normal: Point,
    unit_px: float,
    ruler_max_cm: int,
    highlight_start_cm: int,
    highlight_end_cm: int,
    half_width: float = 30.0,
) -> tuple[BBox, Point, Point]:
    """Draw a ruler aligned with a segment and return bbox plus highlighted ticks."""

    axis = _scale(axis, 1.0 / max(1e-9, math.hypot(float(axis[0]), float(axis[1]))))
    normal = _scale(normal, 1.0 / max(1e-9, math.hypot(float(normal[0]), float(normal[1]))))
    p0 = zero_point
    p1 = _add(zero_point, _scale(axis, float(ruler_max_cm) * float(unit_px)))
    corners = (
        _add(p0, _scale(normal, -half_width)),
        _add(p1, _scale(normal, -half_width)),
        _add(p1, _scale(normal, half_width)),
        _add(p0, _scale(normal, half_width)),
    )
    ctx.draw.polygon(corners, fill=ctx.panel_alt_fill, outline=ctx.panel_border)
    ctx.draw.line([corners[0], corners[1], corners[2], corners[3], corners[0]], fill=ctx.panel_border, width=2)
    for half_tick in range(0, (2 * int(ruler_max_cm)) + 1):
        cm_value = half_tick / 2.0
        tick_center = _add(zero_point, _scale(axis, cm_value * float(unit_px)))
        major = half_tick % 2 == 0
        tick_len = half_width * (1.35 if major else 0.78)
        p_start = _add(tick_center, _scale(normal, -half_width))
        p_end = _add(tick_center, _scale(normal, -half_width + tick_len))
        ctx.draw.line([p_start, p_end], fill=ctx.secondary_color, width=2 if major else 1)
        if major:
            label_center = _add(tick_center, _scale(normal, half_width + 13.0))
            _draw_text(ctx, str(int(cm_value)), label_center, font=ctx.tiny_font, stroke_width=1)
    unit_label = _add(_add(zero_point, _scale(axis, float(ruler_max_cm) * float(unit_px) - 18.0)), _scale(normal, 13.0))
    _draw_text(ctx, "cm", unit_label, font=ctx.tiny_font, stroke_width=1)
    highlight_start = _add(zero_point, _scale(axis, float(highlight_start_cm) * float(unit_px)))
    highlight_end = _add(zero_point, _scale(axis, float(highlight_end_cm) * float(unit_px)))
    ctx.draw.line(
        [_add(highlight_start, _scale(normal, -half_width)), _add(highlight_start, _scale(normal, half_width))],
        fill=ctx.secondary_accent_color,
        width=3,
    )
    ctx.draw.line(
        [_add(highlight_end, _scale(normal, -half_width)), _add(highlight_end, _scale(normal, half_width))],
        fill=ctx.secondary_accent_color,
        width=3,
    )
    return bbox_from_points(corners, width=ctx.width, height=ctx.height, pad=10.0), highlight_start, highlight_end


def _draw_polygon_shape(ctx: _RenderContext, problem: _ResolvedProblem, start: Point, end: Point, axis: Point) -> None:
    """Draw one simple polygon that contains the measured side."""

    normal = _normal(axis)
    length_px = math.hypot(float(end[0] - start[0]), float(end[1] - start[1]))
    height = max(96.0, min(145.0, length_px * 0.42))
    if problem.shape_kind == "triangle":
        apex = _add(_add(start, _scale(axis, length_px * 0.46)), _scale(normal, -height))
        vertices = (start, end, apex)
    elif problem.shape_kind == "trapezoid":
        skew = _scale(axis, length_px * 0.18)
        top_left = _add(_add(start, _scale(normal, -height)), skew)
        top_right = _add(_add(end, _scale(normal, -height)), _scale(axis, -length_px * 0.20))
        vertices = (start, end, top_right, top_left)
    else:
        offset = _add(_scale(normal, -height), _scale(axis, length_px * 0.18))
        vertices = (start, end, _add(end, offset), _add(start, offset))
    ctx.draw.polygon(vertices, fill=ctx.panel_fill, outline=ctx.line_color)
    ctx.draw.line(list(vertices) + [vertices[0]], fill=ctx.line_color, width=max(2, ctx.line_width))
    ctx.draw.line([start, end], fill=ctx.accent_color, width=ctx.line_width + 3)
    for point in (start, end):
        r = 5.5
        ctx.draw.ellipse((point[0] - r, point[1] - r, point[0] + r, point[1] + r), fill=ctx.accent_color)


def _render_shape_length_scene(
    ctx: _RenderContext,
    problem: _ResolvedProblem,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> _RenderedToolScene:
    """Render a ruler placed against a polygon side or circle radius."""

    if problem.target_length is None or problem.ruler_start_cm is None or problem.ruler_max_cm is None:
        raise ValueError("length scene requires target_length, ruler_start_cm, and ruler_max_cm")
    unit_px = float(params.get("ruler_unit_px", group_default(render_defaults, "ruler_unit_px", 42)))
    length_px = float(problem.target_length) * unit_px
    ruler_start_cm = int(problem.ruler_start_cm)
    ruler_end_cm = int(problem.ruler_start_cm + problem.target_length)
    orientation_options = (-22.0, -12.0, 0.0, 14.0, 25.0)
    angle_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_ID}.{problem.query_id}.orientation",
    )
    axis = _unit_from_degrees(orientation_options[int(angle_index) % len(orientation_options)])
    normal = _normal(axis)

    if problem.query_id == "circle_radius_ruler_reading":
        center = (float(ctx.width) * 0.45, float(ctx.height) * 0.44)
        end = _add(center, _scale(axis, length_px))
        radius = length_px
        ctx.draw.ellipse(
            (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
            fill=ctx.panel_fill,
            outline=ctx.line_color,
            width=max(2, ctx.line_width),
        )
        ctx.draw.line([center, end], fill=ctx.accent_color, width=ctx.line_width + 3)
        for point in (center, end):
            r = 5.5
            ctx.draw.ellipse((point[0] - r, point[1] - r, point[0] + r, point[1] + r), fill=ctx.accent_color)
        ruler_start_tick_target = _add(center, _scale(normal, 70.0))
        zero_point = _sub(ruler_start_tick_target, _scale(axis, float(ruler_start_cm) * unit_px))
        ruler_bbox, ruler_start_tick, ruler_end_tick = _draw_rotated_ruler(
            ctx,
            zero_point=zero_point,
            axis=axis,
            normal=normal,
            unit_px=unit_px,
            ruler_max_cm=int(problem.ruler_max_cm),
            highlight_start_cm=ruler_start_cm,
            highlight_end_cm=ruler_end_cm,
        )
        _draw_dashed_line(ctx.draw, center, ruler_start_tick, fill=ctx.guide_color, width=max(1, ctx.line_width - 2))
        _draw_dashed_line(ctx.draw, end, ruler_end_tick, fill=ctx.guide_color, width=max(1, ctx.line_width - 2))
        measure_start, measure_end = center, end
    else:
        center = (float(ctx.width) * 0.52, float(ctx.height) * 0.47)
        start = _sub(center, _scale(axis, length_px / 2.0))
        end = _add(center, _scale(axis, length_px / 2.0))
        _draw_polygon_shape(ctx, problem, start, end, axis)
        ruler_start_tick_target = _add(start, _scale(normal, 72.0))
        zero_point = _sub(ruler_start_tick_target, _scale(axis, float(ruler_start_cm) * unit_px))
        ruler_bbox, ruler_start_tick, ruler_end_tick = _draw_rotated_ruler(
            ctx,
            zero_point=zero_point,
            axis=axis,
            normal=normal,
            unit_px=unit_px,
            ruler_max_cm=int(problem.ruler_max_cm),
            highlight_start_cm=ruler_start_cm,
            highlight_end_cm=ruler_end_cm,
        )
        _draw_dashed_line(ctx.draw, start, ruler_start_tick, fill=ctx.guide_color, width=max(1, ctx.line_width - 2))
        _draw_dashed_line(ctx.draw, end, ruler_end_tick, fill=ctx.guide_color, width=max(1, ctx.line_width - 2))
        measure_start, measure_end = start, end

    label_center = _add(_add(measure_start, _scale(_sub(measure_end, measure_start), 0.5)), _scale(normal, -25.0))
    _draw_text(ctx, "?", label_center, font=ctx.font, fill=ctx.secondary_accent_color)
    annotation = {
        "measure_start": _round_point(measure_start),
        "measure_end": _round_point(measure_end),
        "ruler_start_tick": _round_point(ruler_start_tick),
        "ruler_end_tick": _round_point(ruler_end_tick),
    }
    scene_entities = (
        {
            "entity_id": "ruler",
            "entity_type": "measuring_tool",
            "tool_kind": "ruler",
            "unit": "centimeter",
            "max_cm": int(problem.ruler_max_cm),
            "bbox": bbox_to_list(ruler_bbox),
        },
        {
            "entity_id": "measured_feature",
            "entity_type": "radius" if problem.query_id == "circle_radius_ruler_reading" else "side",
            "shape_kind": str(problem.shape_kind),
            "length_cm": int(problem.target_length),
            "endpoints_px": [_round_point(measure_start), _round_point(measure_end)],
            "bbox": bbox_to_list(bbox_from_points((measure_start, measure_end), width=ctx.width, height=ctx.height, pad=18.0)),
        },
    )
    return _RenderedToolScene(
        image=ctx.image,
        answer=float(problem.answer),
        annotation_keyed_points=annotation,
        scene_entities=scene_entities,
        render_map={
            "coord_space": "pixel",
            "tool_kind": "ruler",
            "shape_kind": str(problem.shape_kind),
            "ruler_unit_px": round(unit_px, 3),
            "ruler_start_cm": int(ruler_start_cm),
            "ruler_end_cm": int(ruler_end_cm),
            "ruler_bbox": bbox_to_list(ruler_bbox),
            "measurement_points": dict(annotation),
        },
        witness={
            "tool_kind": "ruler",
            "shape_kind": str(problem.shape_kind),
            "unit": "centimeter",
            "target_length_cm": int(problem.target_length),
            "ruler_start_cm": int(ruler_start_cm),
            "ruler_end_cm": int(ruler_end_cm),
            "answer_value": float(problem.answer),
        },
    )


def _protractor_point(center: Point, radius: float, degree_value: float) -> Point:
    """Return a point on the protractor semicircle for a visible degree value."""

    theta = math.radians(float(degree_value))
    return (
        float(center[0]) + (float(radius) * math.cos(theta)),
        float(center[1]) - (float(radius) * math.sin(theta)),
    )


def _render_shape_angle_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedToolScene:
    """Render a protractor placed on a polygon vertex."""

    if problem.target_angle is None:
        raise ValueError("angle scene requires target_angle")
    cx = float(ctx.width) * 0.34
    cy = float(ctx.height) * 0.72
    center = (cx, cy)
    outer_radius = min(float(ctx.width) * 0.34, float(ctx.height) * 0.43)
    inner_radius = outer_radius - 76.0
    ray_radius = outer_radius - 22.0
    baseline_end = _protractor_point(center, ray_radius, 0)
    target_end = _protractor_point(center, ray_radius, float(problem.target_angle))

    if problem.shape_kind == "quadrilateral":
        top = (
            min(float(ctx.width) - 80.0, max(baseline_end[0], target_end[0]) + 35.0),
            min(baseline_end[1], target_end[1]) - 80.0,
        )
        shape_points = (center, baseline_end, top, target_end)
    else:
        shape_points = (center, baseline_end, target_end)
    ctx.draw.polygon(shape_points, fill=ctx.panel_fill, outline=ctx.line_color)
    ctx.draw.line(list(shape_points) + [shape_points[0]], fill=ctx.line_color, width=max(2, ctx.line_width))
    ctx.draw.line([center, baseline_end], fill=ctx.accent_color, width=ctx.line_width + 3)
    ctx.draw.line([center, target_end], fill=ctx.accent_color, width=ctx.line_width + 3)

    protractor_box = (
        cx - outer_radius,
        cy - outer_radius,
        cx + outer_radius,
        cy + outer_radius,
    )
    inner_box = (
        cx - inner_radius,
        cy - inner_radius,
        cx + inner_radius,
        cy + inner_radius,
    )
    ctx.draw.pieslice(protractor_box, start=180, end=360, fill=ctx.panel_alt_fill, outline=ctx.panel_border, width=3)
    ctx.draw.arc(protractor_box, start=180, end=360, fill=ctx.line_color, width=3)
    ctx.draw.arc(inner_box, start=180, end=360, fill=ctx.secondary_color, width=2)
    left = _protractor_point(center, outer_radius, 180)
    right = _protractor_point(center, outer_radius, 0)
    ctx.draw.line([left, right], fill=ctx.line_color, width=3)
    for degree in range(0, 181, 5):
        tick_len = 22.0 if degree % 10 == 0 else 12.0
        if degree % 30 == 0:
            tick_len = 28.0
        p0 = _protractor_point(center, outer_radius - 2.0, degree)
        p1 = _protractor_point(center, outer_radius - tick_len, degree)
        ctx.draw.line([p0, p1], fill=ctx.secondary_color, width=2 if degree % 10 == 0 else 1)
    for degree in range(0, 181, 30):
        label_center = _protractor_point(center, outer_radius - 48.0, degree)
        _draw_text(ctx, str(degree), label_center, font=ctx.tiny_font, stroke_width=1)
    dot_r = 6.0
    ctx.draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=ctx.accent_color)
    arc_box = (cx - 78.0, cy - 78.0, cx + 78.0, cy + 78.0)
    ctx.draw.arc(
        arc_box,
        start=360 - int(problem.target_angle),
        end=360,
        fill=ctx.secondary_accent_color,
        width=5,
    )
    mid_degree = float(problem.target_angle) / 2.0
    question_center = _protractor_point(center, 103.0, mid_degree)
    _draw_text(ctx, "?", question_center, font=ctx.font, fill=ctx.secondary_accent_color)
    reading_tick = _protractor_point(center, outer_radius - 10.0, float(problem.target_angle))
    annotation = {
        "angle_vertex": _round_point(center),
        "baseline_ray_point": _round_point(baseline_end),
        "target_ray_point": _round_point(target_end),
        "protractor_reading_tick": _round_point(reading_tick),
    }
    scale_bbox = bbox_to_list(pad_bbox((cx - outer_radius, cy - outer_radius, cx + outer_radius, cy), 10.0, width=ctx.width, height=ctx.height))
    angle_bbox = bbox_to_list(bbox_from_points((center, baseline_end, target_end), width=ctx.width, height=ctx.height, pad=18.0))
    scene_entities = (
        {
            "entity_id": "protractor",
            "entity_type": "measuring_tool",
            "tool_kind": "protractor",
            "center_px": _round_point(center),
            "outer_radius_px": round(outer_radius, 3),
            "bbox": scale_bbox,
        },
        {
            "entity_id": "target_angle",
            "entity_type": "angle",
            "shape_kind": str(problem.shape_kind),
            "degree_value": int(problem.target_angle),
            "vertex_px": _round_point(center),
            "ray_endpoints_px": [_round_point(baseline_end), _round_point(target_end)],
            "bbox": angle_bbox,
        },
    )
    return _RenderedToolScene(
        image=ctx.image,
        answer=float(problem.answer),
        annotation_keyed_points=annotation,
        scene_entities=scene_entities,
        render_map={
            "coord_space": "pixel",
            "tool_kind": "protractor",
            "shape_kind": str(problem.shape_kind),
            "center_px": _round_point(center),
            "outer_radius_px": round(outer_radius, 3),
            "target_angle_degrees": int(problem.target_angle),
            "measurement_points": dict(annotation),
        },
        witness={
            "tool_kind": "protractor",
            "shape_kind": str(problem.shape_kind),
            "target_angle_degrees": int(problem.target_angle),
            "answer_value": float(problem.answer),
        },
    )


class _MeasuringToolsBaseTask:
    """Shared public-task implementation for measuring-tool scenes."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    query_ids: Tuple[str, ...] = ()
    prompt_task_key = ""

    def _build_complexity(self, rendered: _RenderedToolScene) -> TaskComplexity:
        tool_kind = str(rendered.witness.get("tool_kind", ""))
        if tool_kind == "protractor":
            target = int(rendered.witness.get("target_angle_degrees", 90))
            non_major_tick = 1.0 if target % 10 != 0 else 0.0
            precision = clamp_unit_interval(0.52 + (0.20 * non_major_tick) + (0.10 * abs(target - 90) / 60.0))
            visual_scan = 0.64
            ambiguity = 0.48 + (0.10 * non_major_tick)
        else:
            length = int(rendered.witness.get("target_length_cm", 6))
            precision = clamp_unit_interval(0.42 + (0.16 * (length / 8.0)))
            visual_scan = 0.62
            ambiguity = 0.46
        output_burden = clamp_unit_interval(0.44 + (0.04 * len(rendered.annotation_keyed_points)))
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(precision),
            ambiguity=float(ambiguity),
            output_burden=float(output_burden),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
        )
        query_id = _resolve_query_id(
            task_id=str(self.task_id),
            query_ids=tuple(self.query_ids),
            instance_seed=int(instance_seed),
            params=params,
        )
        problem = _resolve_problem(
            task_id=str(self.task_id),
            query_id=str(query_id),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
        rendered: _RenderedToolScene | None = None
        render_meta: Dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = _make_context(
                    instance_seed=int(instance_seed) + int(attempt),
                    params=params,
                    render_defaults=render_defaults,
                    task_id=str(self.task_id),
                )
                if problem.query_id in {"polygon_side_ruler_reading", "circle_radius_ruler_reading"}:
                    rendered = _render_shape_length_scene(
                        ctx,
                        problem,
                        instance_seed=int(instance_seed) + int(attempt),
                        params=params,
                        render_defaults=render_defaults,
                    )
                elif problem.query_id in {"triangle_vertex_protractor_reading", "quadrilateral_vertex_protractor_reading"}:
                    rendered = _render_shape_angle_scene(ctx, problem)
                else:
                    raise ValueError(f"unsupported measuring-tools query_id: {problem.query_id}")
                render_meta = dict(render_meta_attempt)
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or render_meta is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_number",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=None,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        rounded_answer = float(round1(rendered.answer))
        answer_value: int | float = rounded_answer
        if abs(rounded_answer - round(rounded_answer)) <= 1e-9:
            answer_value = int(round(rounded_answer))
        answer_gt = TypedValue(type="number", value=answer_value)
        annotation_keyed_points = {str(key): list(value) for key, value in rendered.annotation_keyed_points.items()}
        annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_keyed_points))
        query_prob = {str(query): (1.0 / float(len(self.query_ids))) for query in self.query_ids}
        query_params = {
            "scene_id": SCENE_ID,
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(query_prob),
            "target_support_probabilities": dict(problem.answer_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_measuring_tools",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "answer_value": answer_value,
                    "annotation_keys": list(annotation_keyed_points.keys()),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": [int(image.size[0]), int(image.size[1])],
                "coord_space": "pixel",
                "post_image_noise": dict(noise_meta),
                **dict(render_meta),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "answer_type": "number",
                "answer_value": answer_value,
                "answer_rounding": "integer",
                "annotation_keys": list(annotation_keyed_points.keys()),
                "reasoning_steps": 1,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "measuring_tool_on_shape_readout",
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "source_witness_type": "keyed_point_map",
                "original_annotation_value": dict(annotation_keyed_points),
                "answer_value": answer_value,
                **dict(rendered.witness),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_keyed_points),
                "pixel_keyed_point_map": dict(annotation_keyed_points),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=self._build_complexity(rendered),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryMeasuringToolsShapeLengthValuePolygonSideRulerReadingTask(_MeasuringToolsBaseTask):
    """Read a polygon side length using a visible ruler."""

    task_id = "task_geometry__measuring_tools__shape_length_value_polygon_side_ruler_reading"
    query_ids = ("polygon_side_ruler_reading",)
    prompt_task_key = "shape_length_value_query"


@register_task
class GeometryMeasuringToolsShapeLengthValueCircleRadiusRulerReadingTask(_MeasuringToolsBaseTask):
    """Read a circle radius using a visible ruler."""

    task_id = "task_geometry__measuring_tools__shape_length_value_circle_radius_ruler_reading"
    query_ids = ("circle_radius_ruler_reading",)
    prompt_task_key = "shape_length_value_query"


@register_task
class GeometryMeasuringToolsShapeAngleValueTriangleVertexProtractorReadingTask(_MeasuringToolsBaseTask):
    """Read a triangle vertex angle using a visible protractor."""

    task_id = "task_geometry__measuring_tools__shape_angle_value_triangle_vertex_protractor_reading"
    query_ids = ("triangle_vertex_protractor_reading",)
    prompt_task_key = "shape_angle_value_query"


@register_task
class GeometryMeasuringToolsShapeAngleValueQuadrilateralVertexProtractorReadingTask(_MeasuringToolsBaseTask):
    """Read a quadrilateral vertex angle using a visible protractor."""

    task_id = "task_geometry__measuring_tools__shape_angle_value_quadrilateral_vertex_protractor_reading"
    query_ids = ("quadrilateral_vertex_protractor_reading",)
    prompt_task_key = "shape_angle_value_query"


__all__ = [
    "GeometryMeasuringToolsShapeAngleValueQuadrilateralVertexProtractorReadingTask",
    "GeometryMeasuringToolsShapeAngleValueTriangleVertexProtractorReadingTask",
    "GeometryMeasuringToolsShapeLengthValueCircleRadiusRulerReadingTask",
    "GeometryMeasuringToolsShapeLengthValuePolygonSideRulerReadingTask",
    "SCENE_ID",
]
