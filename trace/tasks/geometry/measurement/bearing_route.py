"""Compass-bearing route geometry measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
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
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.labeling import LABEL_POOL_SAFE_UPPER, assign_random_shuffled_labels
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import build_geometry_measurement_complexity, clamp_unit_interval
from ..shared.diagram_style import (
    geometry_diagram_style_metadata,
    prepare_geometry_diagram_style_and_background,
)
from ..shared.measurement_rendering import bbox_from_points, bbox_to_list, pad_bbox, round1
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "bearing_route"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_bearing_route_v0"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)
_ROUTE_CASES: Tuple[Tuple[int, int, int], ...] = (
    (3, 4, 5),
    (6, 8, 10),
    (5, 12, 13),
    (9, 12, 15),
    (8, 15, 17),
    (12, 16, 20),
    (7, 24, 25),
    (10, 24, 26),
    (20, 21, 29),
    (18, 24, 30),
    (16, 30, 34),
    (12, 35, 37),
)
_CARDINAL_BEARINGS: Tuple[int, ...] = (0, 90, 180, 270)
_ROUTE_STYLE_IDS: Tuple[str, ...] = ("survey_sheet", "navigation_plot", "field_notebook", "compass_card")
_MARKER_STYLES: Tuple[str, ...] = ("ring", "target", "square", "pin")


@dataclass(frozen=True)
class _RouteCase:
    leg_a: int
    leg_b: int
    displacement: int
    bearing_a: int
    bearing_b: int
    turn_direction: str
    option_count: int
    target_index: int | None
    option_labels: Tuple[str, ...]


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    answer: int | str
    answer_type: str
    route_case: _RouteCase
    answer_probabilities: Dict[str, float]


@dataclass
class _RenderContext:
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
    font_family: str
    route_style_id: str
    marker_style: str


@dataclass(frozen=True)
class _RenderedBearingScene:
    image: Image.Image
    answer: int | str
    answer_type: str
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    evidence_points: Tuple[Point, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _probability_map(values: Sequence[int | str], selected: int | str | None = None) -> Dict[str, float]:
    if selected is None:
        probability = 1.0 / float(max(1, len(values)))
        return {str(value): float(probability) for value in values}
    return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in values}


def _bearing_to_unit_vector(bearing_degrees: int) -> Point:
    theta = math.radians(float(bearing_degrees))
    return (math.sin(theta), -math.cos(theta))


def _resolve_route_case(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
    include_labels: bool,
) -> tuple[_RouteCase, Dict[str, float]]:
    explicit = params.get("target_displacement")
    if explicit is not None:
        target_displacement = int(explicit)
        matching = [case for case in _ROUTE_CASES if int(case[2]) == target_displacement]
        if not matching:
            raise ValueError(f"target_displacement={target_displacement} is not supported by {task_id}")
        case_index = _ROUTE_CASES.index(matching[0])
        answer_probabilities = _probability_map([case[2] for case in _ROUTE_CASES], target_displacement)
    else:
        case_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.route_case",
            )
        ) % len(_ROUTE_CASES)
        answer_probabilities = _probability_map([case[2] for case in _ROUTE_CASES])
    leg_a, leg_b, displacement = _ROUTE_CASES[case_index]

    orientation_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.orientation",
        )
    )
    bearing_a = _CARDINAL_BEARINGS[orientation_index % len(_CARDINAL_BEARINGS)]
    turn_left = ((orientation_index // len(_CARDINAL_BEARINGS)) % 2) == 0
    bearing_b = (int(bearing_a) - 90) % 360 if turn_left else (int(bearing_a) + 90) % 360
    turn_direction = "left" if turn_left else "right"

    explicit_index = params.get("target_index")
    target_index: int | None = None
    labels: Tuple[str, ...] = ()
    if include_labels:
        if int(option_count) < 5:
            raise ValueError("bearing endpoint task requires at least five candidate positions")
        if int(option_count) > len(LABEL_POOL_SAFE_UPPER):
            raise ValueError("option_count exceeds safe label pool")
        if explicit_index is None:
            target_index = int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.target_index",
                )
            ) % int(option_count)
        else:
            target_index = int(explicit_index)
            if target_index < 0 or target_index >= int(option_count):
                raise ValueError("target_index is outside option count")
        label_rng = spawn_rng(int(instance_seed), f"{task_id}.labels")
        labels = assign_random_shuffled_labels(label_rng, object_count=int(option_count))
        answer_probabilities = _probability_map(tuple(range(int(option_count))))

    return (
        _RouteCase(
            leg_a=int(leg_a),
            leg_b=int(leg_b),
            displacement=int(displacement),
            bearing_a=int(bearing_a),
            bearing_b=int(bearing_b),
            turn_direction=str(turn_direction),
            option_count=int(option_count),
            target_index=target_index,
            option_labels=tuple(labels),
        ),
        answer_probabilities,
    )


def _resolve_problem(
    *,
    task_id: str,
    query_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _ResolvedProblem:
    option_count = int(params.get("option_count", group_default(gen_defaults, "option_count", 6)))
    if query_id == "final_displacement_value":
        route_case, probabilities = _resolve_route_case(
            task_id=task_id,
            params=params,
            instance_seed=int(instance_seed),
            option_count=option_count,
            include_labels=False,
        )
        return _ResolvedProblem(
            query_id=query_id,
            answer=int(route_case.displacement),
            answer_type="number",
            route_case=route_case,
            answer_probabilities=probabilities,
        )
    if query_id == "endpoint_position_label":
        route_case, probabilities = _resolve_route_case(
            task_id=task_id,
            params=params,
            instance_seed=int(instance_seed),
            option_count=option_count,
            include_labels=True,
        )
        if route_case.target_index is None:
            raise ValueError("endpoint label task requires target_index")
        return _ResolvedProblem(
            query_id=query_id,
            answer=str(route_case.option_labels[int(route_case.target_index)]),
            answer_type="option_letter",
            route_case=route_case,
            answer_probabilities=probabilities,
        )
    raise ValueError(f"unsupported bearing-route query_id: {query_id}")


def _make_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    task_id: str,
) -> tuple[_RenderContext, Dict[str, Any]]:
    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 580)))
    protected = ((205, 70, 52), (30, 126, 185), (38, 150, 95), (238, 182, 47))
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
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"geometry.{TASK_GROUP}.{SCENE_ID}.font_family",
        params=params,
    )
    font_record = get_font_family_record(str(font_family))
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
    tiny_font_size = int(params.get("tiny_label_font_size", group_default(render_defaults, "tiny_label_font_size", 14)))
    route_style_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.route_style_id",
    )
    marker_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.marker_style",
    )
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
    ctx = _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
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
        line_width=max(2, int(line_width)),
        font=load_font(max(12, font_size), bold=True, font_family=font_family),
        small_font=load_font(max(10, small_font_size), bold=True, font_family=font_family),
        tiny_font=load_font(max(8, tiny_font_size), bold=True, font_family=font_family),
        font_family=str(font_family),
        route_style_id=str(_ROUTE_STYLE_IDS[int(route_style_index) % len(_ROUTE_STYLE_IDS)]),
        marker_style=str(_MARKER_STYLES[int(marker_index) % len(_MARKER_STYLES)]),
    )
    render_meta = {
        "background_style": dict(background_meta),
        "technical_diagram_style": geometry_diagram_style_metadata(diagram_style),
        "technical_diagram_style_resolution": dict(style_meta),
        "font_asset_version": font_asset_version(),
        "font_family": font_record.to_trace(),
        "route_style_id": str(ctx.route_style_id),
        "marker_style": str(ctx.marker_style),
        "line_width": int(ctx.line_width),
        "label_font_size": int(font_size),
        "small_label_font_size": int(small_font_size),
        "tiny_label_font_size": int(tiny_font_size),
        "task_style_namespace": str(task_id),
    }
    return ctx, render_meta


def _draw_text(
    ctx: _RenderContext,
    text: str,
    center: Point,
    *,
    font: Any | None = None,
    fill: Color | None = None,
    stroke_width: int = 2,
) -> BBox:
    active_font = font or ctx.small_font
    active_fill = fill or ctx.label_color
    bbox = ctx.draw.textbbox((0, 0), str(text), font=active_font, stroke_width=stroke_width)
    text_w = float(bbox[2] - bbox[0])
    text_h = float(bbox[3] - bbox[1])
    left = float(center[0]) - (text_w / 2.0)
    top = float(center[1]) - (text_h / 2.0)
    draw_text_traced(ctx.draw,
        (left, top),
        str(text),
        font=active_font,
        fill=active_fill,
        stroke_width=int(stroke_width),
        stroke_fill=ctx.label_stroke_color,
     role="readout", required=False,)
    return pad_bbox((left, top, left + text_w, top + text_h), 3.0, width=ctx.width, height=ctx.height)


def _draw_panel(ctx: _RenderContext, bbox: BBox, *, fill: Color | None = None, radius: int = 8) -> BBox:
    ctx.draw.rounded_rectangle(
        tuple(float(v) for v in bbox),
        radius=int(radius),
        fill=fill or ctx.panel_fill,
        outline=ctx.panel_border,
        width=3,
    )
    return pad_bbox(bbox, 2.0, width=ctx.width, height=ctx.height)


def _draw_arrow_line(
    draw: ImageDraw.ImageDraw,
    start: Point,
    end: Point,
    *,
    fill: Color,
    width: int,
    arrow_size: float = 12.0,
) -> None:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    draw.line([(sx, sy), (ex, ey)], fill=fill, width=max(1, int(width)))
    angle = math.atan2(ey - sy, ex - sx)
    for sign in (-1.0, 1.0):
        head_angle = angle + (sign * math.radians(150.0))
        hx = ex + (float(arrow_size) * math.cos(head_angle))
        hy = ey + (float(arrow_size) * math.sin(head_angle))
        draw.line([(ex, ey), (hx, hy)], fill=fill, width=max(1, int(width)))


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


def _draw_marker(ctx: _RenderContext, center: Point, *, radius: float, color: Color, fill: Color | None = None) -> BBox:
    x, y = float(center[0]), float(center[1])
    r = float(radius)
    marker_fill = fill or ctx.panel_alt_fill
    if ctx.marker_style == "square":
        ctx.draw.rectangle((x - r, y - r, x + r, y + r), fill=marker_fill, outline=color, width=max(2, ctx.line_width))
    elif ctx.marker_style == "pin":
        ctx.draw.ellipse((x - r, y - r, x + r, y + r), fill=marker_fill, outline=color, width=max(2, ctx.line_width))
        ctx.draw.polygon([(x, y + r + 8), (x - r * 0.55, y + r * 0.1), (x + r * 0.55, y + r * 0.1)], fill=color)
    else:
        ctx.draw.ellipse((x - r, y - r, x + r, y + r), fill=marker_fill, outline=color, width=max(2, ctx.line_width))
        if ctx.marker_style == "target":
            ctx.draw.ellipse((x - (r * 0.45), y - (r * 0.45), x + (r * 0.45), y + (r * 0.45)), outline=color, width=2)
    ctx.draw.line([(x - r * 0.55, y), (x + r * 0.55, y)], fill=color, width=2)
    ctx.draw.line([(x, y - r * 0.55), (x, y + r * 0.55)], fill=color, width=2)
    return pad_bbox((x - r, y - r, x + r, y + r + (8.0 if ctx.marker_style == "pin" else 0.0)), 4.0, width=ctx.width, height=ctx.height)


def _draw_compass_rose(ctx: _RenderContext, center: Point, *, radius: float) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    r = float(radius)
    ctx.draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ctx.secondary_color, width=2)
    _draw_arrow_line(ctx.draw, (cx, cy + r * 0.65), (cx, cy - r * 0.78), fill=ctx.secondary_color, width=2, arrow_size=8)
    ctx.draw.line([(cx - r * 0.65, cy), (cx + r * 0.65, cy)], fill=ctx.guide_color, width=2)
    _draw_text(ctx, "N", (cx, cy - r - 15), font=ctx.tiny_font, stroke_width=1)
    _draw_text(ctx, "E", (cx + r + 15, cy), font=ctx.tiny_font, stroke_width=1)
    _draw_text(ctx, "S", (cx, cy + r + 16), font=ctx.tiny_font, stroke_width=1)
    _draw_text(ctx, "W", (cx - r - 15, cy), font=ctx.tiny_font, stroke_width=1)
    return pad_bbox((cx - r - 24, cy - r - 26, cx + r + 26, cy + r + 28), 2.0, width=ctx.width, height=ctx.height)


def _route_unit_points(route_case: _RouteCase) -> tuple[Point, Point, Point]:
    u1 = _bearing_to_unit_vector(int(route_case.bearing_a))
    u2 = _bearing_to_unit_vector(int(route_case.bearing_b))
    p0 = (0.0, 0.0)
    p1 = (u1[0] * float(route_case.leg_a), u1[1] * float(route_case.leg_a))
    p2 = (p1[0] + (u2[0] * float(route_case.leg_b)), p1[1] + (u2[1] * float(route_case.leg_b)))
    return p0, p1, p2


def _fit_points_to_box(points: Sequence[Point], bbox: BBox, *, min_scale: float = 6.0) -> tuple[float, Point]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width_units = max(1.0, max_x - min_x)
    height_units = max(1.0, max_y - min_y)
    left, top, right, bottom = (float(v) for v in bbox)
    box_w = max(1.0, right - left)
    box_h = max(1.0, bottom - top)
    scale = max(float(min_scale), min(box_w / width_units, box_h / height_units) * 0.72)
    route_w = width_units * scale
    route_h = height_units * scale
    origin_x = left + ((box_w - route_w) / 2.0) - (min_x * scale)
    origin_y = top + ((box_h - route_h) / 2.0) - (min_y * scale)
    return float(scale), (origin_x, origin_y)


def _project(point: Point, *, scale: float, origin: Point) -> Point:
    return (float(origin[0]) + (float(point[0]) * float(scale)), float(origin[1]) + (float(point[1]) * float(scale)))


def _leg_label(distance: int, bearing: int) -> str:
    return f"{int(bearing):03d} deg / {int(distance)}"


def _offset_label_point(start: Point, end: Point, amount: float) -> Point:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    dx, dy = ex - sx, ey - sy
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    return ((sx + ex) / 2.0 + nx * float(amount), (sy + ey) / 2.0 + ny * float(amount))


def _render_final_displacement_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedBearingScene:
    route_case = problem.route_case
    p0, p1, p2 = _route_unit_points(route_case)
    panel_bbox = (60.0, 78.0, 628.0, 504.0)
    route_panel_bbox = _draw_panel(ctx, panel_bbox, fill=ctx.panel_alt_fill)
    scale, origin = _fit_points_to_box((p0, p1, p2), (110.0, 135.0, 560.0, 448.0), min_scale=8.0)
    start = _project(p0, scale=scale, origin=origin)
    mid = _project(p1, scale=scale, origin=origin)
    end = _project(p2, scale=scale, origin=origin)

    _draw_arrow_line(ctx.draw, start, mid, fill=ctx.accent_color, width=ctx.line_width + 1, arrow_size=14)
    _draw_arrow_line(ctx.draw, mid, end, fill=ctx.accent_color, width=ctx.line_width + 1, arrow_size=14)
    _draw_dashed_line(ctx.draw, start, end, fill=ctx.secondary_accent_color, width=max(2, ctx.line_width - 1), dash=10, gap=7)
    start_bbox = _draw_marker(ctx, start, radius=10, color=ctx.secondary_color)
    end_bbox = _draw_marker(ctx, end, radius=10, color=ctx.secondary_accent_color)
    start_label_bbox = _draw_text(ctx, "S", (start[0] - 20.0, start[1] + 20.0), font=ctx.small_font, stroke_width=2)
    end_label_bbox = _draw_text(ctx, "F", (end[0] + 20.0, end[1] - 20.0), font=ctx.small_font, stroke_width=2)
    label1_bbox = _draw_text(ctx, _leg_label(route_case.leg_a, route_case.bearing_a), _offset_label_point(start, mid, 28.0), font=ctx.small_font)
    label2_bbox = _draw_text(ctx, _leg_label(route_case.leg_b, route_case.bearing_b), _offset_label_point(mid, end, 28.0), font=ctx.small_font)
    first_leg_bbox = _bbox_union(bbox_from_points((start, mid), width=ctx.width, height=ctx.height, pad=16.0), label1_bbox)
    second_leg_bbox = _bbox_union(bbox_from_points((mid, end), width=ctx.width, height=ctx.height, pad=16.0), label2_bbox)
    cue_bbox = _draw_text(
        ctx,
        "?",
        _offset_label_point(start, end, -30.0),
        font=ctx.font,
        fill=ctx.secondary_accent_color,
    )
    direct_bbox = bbox_from_points((start, end), width=ctx.width, height=ctx.height, pad=22.0)
    direct_bbox = (
        min(direct_bbox[0], cue_bbox[0], start_bbox[0], end_bbox[0], start_label_bbox[0], end_label_bbox[0]),
        min(direct_bbox[1], cue_bbox[1], start_bbox[1], end_bbox[1], start_label_bbox[1], end_label_bbox[1]),
        max(direct_bbox[2], cue_bbox[2], start_bbox[2], end_bbox[2], start_label_bbox[2], end_label_bbox[2]),
        max(direct_bbox[3], cue_bbox[3], start_bbox[3], end_bbox[3], start_label_bbox[3], end_label_bbox[3]),
    )
    compass_bbox = _draw_compass_rose(ctx, (720.0, 148.0), radius=42.0)
    note_bbox = _draw_panel(ctx, (650.0, 248.0, 780.0, 402.0), fill=ctx.panel_fill)
    _draw_text(ctx, "bearing", (715.0, 288.0), font=ctx.tiny_font, stroke_width=1)
    _draw_text(ctx, "clockwise", (715.0, 322.0), font=ctx.tiny_font, stroke_width=1)
    _draw_text(ctx, "from N", (715.0, 356.0), font=ctx.tiny_font, stroke_width=1)
    turn_bbox = pad_bbox(
        (mid[0] - 6.0, mid[1] - 6.0, mid[0] + 6.0, mid[1] + 6.0),
        4.0,
        width=ctx.width,
        height=ctx.height,
    )
    scene_entities = (
        {
            "entity_id": "route_path",
            "entity_type": "bearing_route",
            "points_px": [[round(start[0], 3), round(start[1], 3)], [round(mid[0], 3), round(mid[1], 3)], [round(end[0], 3), round(end[1], 3)]],
            "bbox": bbox_to_list(route_panel_bbox),
        },
        {
            "entity_id": "direct_displacement",
            "entity_type": "segment",
            "length": int(route_case.displacement),
            "bbox": bbox_to_list(direct_bbox),
        },
        {
            "entity_id": "compass_rose",
            "entity_type": "compass",
            "bbox": bbox_to_list(compass_bbox),
        },
    )
    return _RenderedBearingScene(
        image=ctx.image,
        answer=int(route_case.displacement),
        answer_type="number",
        evidence_bboxes=(start_bbox, turn_bbox, end_bbox),
        evidence_roles=("start_point", "turn_point", "finish_point"),
        evidence_points=(start, mid, end),
        scene_entities=scene_entities,
        render_map={
            "coord_space": "pixel",
            "route_panel_bbox": bbox_to_list(route_panel_bbox),
            "route_points_px": [[round(start[0], 3), round(start[1], 3)], [round(mid[0], 3), round(mid[1], 3)], [round(end[0], 3), round(end[1], 3)]],
            "compass_bbox": bbox_to_list(compass_bbox),
            "bearing_note_bbox": bbox_to_list(note_bbox),
            "route_leg_annotation_bboxes": {
                "first_route_leg": bbox_to_list(label1_bbox),
                "second_route_leg": bbox_to_list(label2_bbox),
            },
        },
        witness={
            "geometry_kind": "bearing_route_displacement",
            "leg_a": int(route_case.leg_a),
            "leg_b": int(route_case.leg_b),
            "bearing_a": int(route_case.bearing_a),
            "bearing_b": int(route_case.bearing_b),
            "turn_direction": str(route_case.turn_direction),
            "displacement": int(route_case.displacement),
            "answer_value": int(route_case.displacement),
        },
    )


def _candidate_unit_points(route_case: _RouteCase) -> list[tuple[str, Point]]:
    p0, p1, p2 = _route_unit_points(route_case)
    u1 = _bearing_to_unit_vector(int(route_case.bearing_a))
    u2 = _bearing_to_unit_vector(int(route_case.bearing_b))
    opposite_first = (-u1[0] * float(route_case.leg_a), -u1[1] * float(route_case.leg_a))
    swapped = (u1[0] * float(route_case.leg_b) + u2[0] * float(route_case.leg_a), u1[1] * float(route_case.leg_b) + u2[1] * float(route_case.leg_a))
    wrong_turn = (u1[0] * float(route_case.leg_a) - u2[0] * float(route_case.leg_b), u1[1] * float(route_case.leg_a) - u2[1] * float(route_case.leg_b))
    second_only = (u2[0] * float(route_case.leg_b), u2[1] * float(route_case.leg_b))
    candidates = [
        ("correct_endpoint", p2),
        ("first_leg_only", p1),
        ("second_leg_only", second_only),
        ("swapped_distances", swapped),
        ("opposite_second_turn", wrong_turn),
        ("opposite_first_leg", opposite_first),
    ]
    unique: list[tuple[str, Point]] = []
    seen: set[tuple[int, int]] = set()
    for name, point in candidates:
        key = (int(round(point[0] * 1000)), int(round(point[1] * 1000)))
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, point))
    while len(unique) < int(route_case.option_count):
        offset = float(len(unique) + 2)
        unique.append((f"distractor_{len(unique)}", (p2[0] + offset, p2[1] - offset)))
    return unique[: int(route_case.option_count)]


def _render_endpoint_label_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedBearingScene:
    route_case = problem.route_case
    if route_case.target_index is None:
        raise ValueError("endpoint label scene requires target_index")
    base_candidates = _candidate_unit_points(route_case)
    correct = base_candidates[0]
    distractors = base_candidates[1:]
    target_index = int(route_case.target_index)
    ordered_candidates = list(distractors)
    ordered_candidates.insert(target_index, correct)
    ordered_candidates = ordered_candidates[: int(route_case.option_count)]
    all_points = [(0.0, 0.0)] + [point for _, point in ordered_candidates]
    plot_panel = (60.0, 84.0, 552.0, 510.0)
    plot_panel_bbox = _draw_panel(ctx, plot_panel, fill=ctx.panel_alt_fill)
    scale, origin = _fit_points_to_box(all_points, (118.0, 145.0, 494.0, 445.0), min_scale=7.0)
    start = _project((0.0, 0.0), scale=scale, origin=origin)
    start_bbox = _draw_marker(ctx, start, radius=10.0, color=ctx.secondary_color)
    _draw_text(ctx, "S", (start[0] - 20.0, start[1] + 20.0), font=ctx.small_font)

    option_entities: list[Dict[str, Any]] = []
    selected_bbox: BBox | None = None
    selected_label_bbox: BBox | None = None
    selected_center: Point | None = None
    for idx, (candidate_kind, unit_point) in enumerate(ordered_candidates):
        label = str(route_case.option_labels[idx])
        point = _project(unit_point, scale=scale, origin=origin)
        point_bbox = _draw_marker(ctx, point, radius=11.0, color=ctx.secondary_accent_color)
        label_dx = 20.0 if point[0] >= start[0] else -20.0
        label_dy = -20.0 if point[1] <= start[1] else 20.0
        label_bbox = _draw_text(ctx, label, (point[0] + label_dx, point[1] + label_dy), font=ctx.small_font)
        combined_bbox = (
            min(point_bbox[0], label_bbox[0]),
            min(point_bbox[1], label_bbox[1]),
            max(point_bbox[2], label_bbox[2]),
            max(point_bbox[3], label_bbox[3]),
        )
        option_entities.append(
            {
                "entity_id": f"candidate_{idx}",
                "entity_type": "route_endpoint_candidate",
                "candidate_kind": str(candidate_kind),
                "candidate_index": int(idx),
                "label": str(label),
                "center_px": [round(point[0], 3), round(point[1], 3)],
                "marker_bbox": bbox_to_list(point_bbox),
                "label_bbox": bbox_to_list(label_bbox),
                "bbox": bbox_to_list(combined_bbox),
            }
        )
        if idx == target_index:
            selected_bbox = point_bbox
            selected_label_bbox = label_bbox
            selected_center = point
    if selected_bbox is None or selected_label_bbox is None or selected_center is None:
        raise ValueError("selected endpoint candidate was not rendered")

    instruction_panel = (586.0, 92.0, 782.0, 350.0)
    instruction_bbox = _draw_panel(ctx, instruction_panel, fill=ctx.panel_fill)
    _draw_text(ctx, "route", (684.0, 126.0), font=ctx.small_font)
    instr1 = _draw_text(ctx, f"1: {_leg_label(route_case.leg_a, route_case.bearing_a)}", (684.0, 178.0), font=ctx.tiny_font, stroke_width=1)
    instr2 = _draw_text(ctx, f"2: {_leg_label(route_case.leg_b, route_case.bearing_b)}", (684.0, 222.0), font=ctx.tiny_font, stroke_width=1)
    _draw_compass_rose(ctx, (684.0, 296.0), radius=31.0)
    instruction_evidence_bbox = (
        min(instruction_bbox[0], instr1[0], instr2[0]),
        min(instruction_bbox[1], instr1[1], instr2[1]),
        max(instruction_bbox[2], instr1[2], instr2[2]),
        max(instruction_bbox[3], instr1[3], instr2[3]),
    )
    scene_entities = (
        {
            "entity_id": "route_start",
            "entity_type": "route_start_point",
            "center_px": [round(start[0], 3), round(start[1], 3)],
            "bbox": bbox_to_list(start_bbox),
        },
        {
            "entity_id": "instruction_panel",
            "entity_type": "route_instruction_panel",
            "bbox": bbox_to_list(instruction_evidence_bbox),
        },
        {
            "entity_id": "candidate_panel",
            "entity_type": "endpoint_candidate_panel",
            "bbox": bbox_to_list(plot_panel_bbox),
        },
        *tuple(option_entities),
    )
    return _RenderedBearingScene(
        image=ctx.image,
        answer=str(problem.answer),
        answer_type="option_letter",
        evidence_bboxes=(start_bbox, selected_bbox),
        evidence_roles=("start_point", "reached_endpoint"),
        evidence_points=(start, selected_center),
        scene_entities=scene_entities,
        render_map={
            "coord_space": "pixel",
            "candidate_panel_bbox": bbox_to_list(plot_panel_bbox),
            "instruction_panel_bbox": bbox_to_list(instruction_evidence_bbox),
            "start_center_px": [round(start[0], 3), round(start[1], 3)],
            "selected_candidate_center_px": [round(selected_center[0], 3), round(selected_center[1], 3)],
            "selected_candidate_label_bbox": bbox_to_list(selected_label_bbox),
        },
        witness={
            "geometry_kind": "bearing_route_endpoint",
            "leg_a": int(route_case.leg_a),
            "leg_b": int(route_case.leg_b),
            "bearing_a": int(route_case.bearing_a),
            "bearing_b": int(route_case.bearing_b),
            "turn_direction": str(route_case.turn_direction),
            "displacement": int(route_case.displacement),
            "option_count": int(route_case.option_count),
            "target_index": int(route_case.target_index),
            "option_labels": list(route_case.option_labels),
            "answer_value": str(problem.answer),
        },
    )


def _bbox_centers(bboxes: Sequence[Sequence[float]]) -> list[list[float]]:
    return [
        [
            round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
            round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
        ]
        for bbox in bboxes
    ]


def _bbox_union(*bboxes: BBox) -> BBox:
    return (
        min(float(bbox[0]) for bbox in bboxes),
        min(float(bbox[1]) for bbox in bboxes),
        max(float(bbox[2]) for bbox in bboxes),
        max(float(bbox[3]) for bbox in bboxes),
    )


class _BearingRouteBaseTask:
    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    query_id = ""
    scene_variant = ""

    def _build_complexity(self, rendered: _RenderedBearingScene) -> TaskComplexity:
        if rendered.answer_type == "option_letter":
            visual_scan = 0.62
            precision = 0.54
            ambiguity = 0.48
        else:
            displacement = float(rendered.witness.get("displacement", 10))
            visual_scan = 0.58
            precision = clamp_unit_interval(0.42 + (0.20 * displacement / 37.0))
            ambiguity = 0.50
        output_burden = clamp_unit_interval(0.40 + (0.05 * len(rendered.evidence_bboxes)))
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
        problem = _resolve_problem(
            task_id=str(self.task_id),
            query_id=str(self.query_id),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
        rendered: _RenderedBearingScene | None = None
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
                if problem.query_id == "final_displacement_value":
                    rendered = _render_final_displacement_scene(ctx, problem)
                elif problem.query_id == "endpoint_position_label":
                    rendered = _render_endpoint_label_scene(ctx, problem)
                else:
                    raise ValueError(f"unsupported bearing-route query_id: {problem.query_id}")
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
                "evidence_hint",
                "answer_hint",
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
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        evidence_bboxes = [bbox_to_list(bbox) for bbox in rendered.evidence_bboxes]
        evidence_points = (
            [[round(float(point[0]), 3), round(float(point[1]), 3)] for point in rendered.evidence_points]
            if rendered.evidence_points
            else _bbox_centers(evidence_bboxes)
        )
        evidence_keyed_bboxes = {
            str(role): bbox_to_list(bbox)
            for role, bbox in zip(rendered.evidence_roles, rendered.evidence_bboxes, strict=True)
        }
        evidence_keyed_points = {
            str(role): point
            for role, point in zip(rendered.evidence_roles, evidence_points, strict=True)
        }
        if rendered.answer_type == "number":
            rounded_answer = float(round1(float(rendered.answer)))
            answer_value: int | float | str = rounded_answer
            if abs(rounded_answer - round(rounded_answer)) <= 1e-9:
                answer_value = int(round(rounded_answer))
            answer_gt = TypedValue(type="number", value=answer_value)
        else:
            answer_value = str(rendered.answer)
            answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        evidence_type = "keyed_point_map"
        evidence_value = dict(evidence_keyed_points)
        evidence_gt = TypedValue(type=str(evidence_type), value=evidence_value)
        query_params = {
            "scene_id": SCENE_ID,
            "scene_variant": str(self.scene_variant),
            "query_id": str(problem.query_id),
            "query_id_probabilities": {str(problem.query_id): 1.0},
            **dict(rendered.witness),
        }
        if str(problem.query_id) == "endpoint_position_label":
            query_params["target_index_probabilities"] = dict(problem.answer_probabilities)
        else:
            query_params["target_support_probabilities"] = dict(problem.answer_probabilities)
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_bearing_route",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "scene_variant": str(self.scene_variant),
                    "query_id": str(problem.query_id),
                    "answer_value": answer_value,
                    "evidence_roles": list(rendered.evidence_roles),
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
                "scene_variant": str(self.scene_variant),
                "query_id": str(problem.query_id),
                "answer_type": str(rendered.answer_type),
                "answer_value": answer_value,
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 2,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "bearing_route_measurement",
                "scene_id": SCENE_ID,
                "scene_variant": str(self.scene_variant),
                "query_id": str(problem.query_id),
                "source_witness_type": str(evidence_type),
                "original_evidence_value": list(rendered.evidence_roles),
                "answer_value": answer_value,
                **dict(rendered.witness),
            },
            "projected_evidence": {
                "type": str(evidence_type),
                "keyed_bbox_map": dict(evidence_keyed_bboxes),
                "pixel_keyed_bbox_map": dict(evidence_keyed_bboxes),
                "keyed_point_map": dict(evidence_keyed_points),
                "pixel_keyed_point_map": dict(evidence_keyed_points),
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
                "point_set": list(evidence_points),
                "pixel_point_set": list(evidence_points),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
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
class GeometryBearingRouteFinalDisplacementValueTask(_BearingRouteBaseTask):
    """Compute final direct displacement after following two compass-bearing legs."""

    task_id = "task_geometry__bearing_route__final_displacement_value"
    query_id = "final_displacement_value"
    scene_variant = "drawn_route_displacement"


@register_task
class GeometryBearingRouteEndpointPositionLabelTask(_BearingRouteBaseTask):
    """Select the labeled endpoint reached by route instructions."""

    task_id = "task_geometry__bearing_route__endpoint_position_label"
    query_id = "endpoint_position_label"
    scene_variant = "instruction_endpoint_candidates"


__all__ = [
    "GeometryBearingRouteEndpointPositionLabelTask",
    "GeometryBearingRouteFinalDisplacementValueTask",
    "SCENE_ID",
]
