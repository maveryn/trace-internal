"""Geometry measurement tasks over visible measuring tools."""

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
from ..shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    pad_bbox,
    round1,
)
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "measuring_tools"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_measuring_tools_v0"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)
_PROTRACTOR_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(30, 151, 5))
_RULER_LENGTH_SUPPORT: Tuple[int, ...] = tuple(range(2, 13))


@dataclass(frozen=True)
class _ResolvedProblem:
    """Sampled measuring-tool problem parameters."""

    query_id: str
    answer: float
    target_angle: int | None
    target_length: int | None
    ruler_start_cm: int | None
    ruler_max_cm: int | None
    answer_probabilities: Dict[str, float]


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
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _selected_probability_map(values: Sequence[int], selected: int | float) -> Dict[str, float]:
    """Return a one-hot probability map over a finite support."""

    return {str(int(value)): (1.0 if int(value) == int(selected) else 0.0) for value in values}


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
        return selected, _selected_probability_map(supported_values, selected)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{explicit_key}",
    )
    selected = supported_values[int(index) % len(supported_values)]
    probability = 1.0 / float(len(supported_values))
    return selected, {str(value): float(probability) for value in supported_values}


def _resolve_problem(
    *,
    task_id: str,
    query_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _ResolvedProblem:
    """Resolve one measuring-tool problem."""

    if query_id == "protractor_angle_value":
        angle_min = int(params.get("angle_min", group_default(gen_defaults, "angle_min", 30)))
        angle_max = int(params.get("angle_max", group_default(gen_defaults, "angle_max", 150)))
        angle_step = int(params.get("angle_step", group_default(gen_defaults, "angle_step", 5)))
        support = tuple(value for value in range(angle_min, angle_max + 1, angle_step))
        if not support:
            raise ValueError("protractor angle support is empty")
        target, probabilities = _resolve_supported_value(
            task_id=task_id,
            params=params,
            instance_seed=instance_seed,
            explicit_key="target_angle",
            support=support,
        )
        return _ResolvedProblem(
            query_id=query_id,
            answer=float(target),
            target_angle=int(target),
            target_length=None,
            ruler_start_cm=None,
            ruler_max_cm=None,
            answer_probabilities=probabilities,
        )
    if query_id == "ruler_length_value":
        length_min = int(params.get("length_min", group_default(gen_defaults, "length_min", 2)))
        length_max = int(params.get("length_max", group_default(gen_defaults, "length_max", 12)))
        support = tuple(range(length_min, length_max + 1))
        if not support:
            raise ValueError("ruler length support is empty")
        target, probabilities = _resolve_supported_value(
            task_id=task_id,
            params=params,
            instance_seed=instance_seed,
            explicit_key="target_length",
            support=support,
        )
        ruler_max = int(params.get("ruler_max_cm", group_default(gen_defaults, "ruler_max_cm", 14)))
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
        return _ResolvedProblem(
            query_id=query_id,
            answer=float(target),
            target_angle=None,
            target_length=int(target),
            ruler_start_cm=int(start_cm),
            ruler_max_cm=int(ruler_max),
            answer_probabilities=probabilities,
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


def _draw_text(
    ctx: _RenderContext,
    text: str,
    center: Point,
    *,
    font: Any | None = None,
    fill: Color | None = None,
    stroke_width: int = 2,
) -> BBox:
    """Draw centered text and return its padded bbox."""

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


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: Point,
    end: Point,
    *,
    fill: Color,
    width: int,
    dash: float = 9.0,
    gap: float = 7.0,
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


def _protractor_point(center: Point, radius: float, degree_value: float) -> Point:
    """Return a point on the protractor semicircle for a visible degree value."""

    theta = math.radians(float(degree_value))
    return (
        float(center[0]) + (float(radius) * math.cos(theta)),
        float(center[1]) - (float(radius) * math.sin(theta)),
    )


def _render_protractor_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedToolScene:
    """Render a protractor angle-reading scene."""

    if problem.target_angle is None:
        raise ValueError("protractor scene requires target_angle")
    cx = float(ctx.width) / 2.0
    cy = float(ctx.height) * 0.73
    center = (cx, cy)
    outer_radius = min(float(ctx.width) * 0.36, float(ctx.height) * 0.48)
    inner_radius = outer_radius - 78.0
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
    fill_color = ctx.panel_alt_fill
    ctx.draw.pieslice(protractor_box, start=180, end=360, fill=fill_color, outline=ctx.panel_border, width=3)
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

    ray_radius = outer_radius - 24.0
    baseline_end = _protractor_point(center, ray_radius, 0)
    target_end = _protractor_point(center, ray_radius, float(problem.target_angle))
    ctx.draw.line([center, baseline_end], fill=ctx.accent_color, width=ctx.line_width + 1)
    ctx.draw.line([center, target_end], fill=ctx.accent_color, width=ctx.line_width + 1)
    for degree in range(0, 181, 30):
        label_center = _protractor_point(center, outer_radius - 48.0, degree)
        _draw_text(ctx, str(degree), label_center, font=ctx.tiny_font, stroke_width=1)
    dot_r = 6.0
    ctx.draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=ctx.accent_color)
    arc_box = (cx - 82.0, cy - 82.0, cx + 82.0, cy + 82.0)
    ctx.draw.arc(
        arc_box,
        start=360 - int(problem.target_angle),
        end=360,
        fill=ctx.secondary_accent_color,
        width=5,
    )
    mid_degree = float(problem.target_angle) / 2.0
    question_center = _protractor_point(center, 110.0, mid_degree)
    cue_bbox = _draw_text(ctx, "? deg", question_center, font=ctx.small_font, fill=ctx.secondary_accent_color)

    angle_bbox = bbox_from_points(
        (center, baseline_end, target_end, question_center),
        width=ctx.width,
        height=ctx.height,
        pad=18.0,
    )
    angle_bbox = (
        min(angle_bbox[0], cue_bbox[0]),
        min(angle_bbox[1], cue_bbox[1]),
        max(angle_bbox[2], cue_bbox[2]),
        max(angle_bbox[3], cue_bbox[3]),
    )
    visible_protractor_bbox = (cx - outer_radius, cy - outer_radius, cx + outer_radius, cy)
    scale_bbox = pad_bbox(visible_protractor_bbox, 10.0, width=ctx.width, height=ctx.height)
    scene_entities = (
        {
            "entity_id": "protractor",
            "entity_type": "measuring_tool",
            "tool_kind": "protractor",
            "center_px": [round(cx, 3), round(cy, 3)],
            "outer_radius_px": round(outer_radius, 3),
            "bbox": bbox_to_list(scale_bbox),
        },
        {
            "entity_id": "target_angle",
            "entity_type": "angle",
            "degree_value": int(problem.target_angle),
            "vertex_px": [round(cx, 3), round(cy, 3)],
            "ray_endpoints_px": [
                [round(baseline_end[0], 3), round(baseline_end[1], 3)],
                [round(target_end[0], 3), round(target_end[1], 3)],
            ],
            "bbox": bbox_to_list(angle_bbox),
        },
    )
    return _RenderedToolScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=(angle_bbox, scale_bbox),
        evidence_roles=("target_angle_mark", "protractor_scale"),
        scene_entities=scene_entities,
        render_map={
            "coord_space": "pixel",
            "tool_kind": "protractor",
            "center_px": [round(cx, 3), round(cy, 3)],
            "outer_radius_px": round(outer_radius, 3),
            "target_angle_degrees": int(problem.target_angle),
            "target_ray_end_px": [round(target_end[0], 3), round(target_end[1], 3)],
        },
        witness={
            "tool_kind": "protractor",
            "target_angle_degrees": int(problem.target_angle),
            "answer_value": float(problem.answer),
        },
    )


def _render_ruler_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedToolScene:
    """Render a ruler length-reading scene."""

    if problem.target_length is None or problem.ruler_start_cm is None or problem.ruler_max_cm is None:
        raise ValueError("ruler scene requires target_length, ruler_start_cm, and ruler_max_cm")
    ruler_max = int(problem.ruler_max_cm)
    left = 78.0
    right = float(ctx.width) - 78.0
    top = float(ctx.height) * 0.60
    bottom = top + 78.0
    unit = (right - left) / float(ruler_max)
    start_cm = int(problem.ruler_start_cm)
    end_cm = int(start_cm + int(problem.target_length))
    start_x = left + (float(start_cm) * unit)
    end_x = left + (float(end_cm) * unit)
    segment_y = float(ctx.height) * 0.40

    ruler_bbox = (left - 10.0, top - 10.0, right + 10.0, bottom + 10.0)
    ctx.draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=8,
        fill=ctx.panel_alt_fill,
        outline=ctx.panel_border,
        width=3,
    )
    for half_tick in range(0, (2 * ruler_max) + 1):
        cm_value = half_tick / 2.0
        x = left + (cm_value * unit)
        major = half_tick % 2 == 0
        tick_bottom = bottom if major else top + 46.0
        ctx.draw.line([(x, top), (x, tick_bottom)], fill=ctx.secondary_color, width=2 if major else 1)
        if major:
            _draw_text(ctx, str(int(cm_value)), (x, bottom - 18.0), font=ctx.tiny_font, stroke_width=1)
    _draw_text(ctx, "cm", (right - 24.0, top + 18.0), font=ctx.tiny_font, stroke_width=1)

    guide_width = max(1, ctx.line_width - 2)
    _draw_dashed_line(ctx.draw, (start_x, segment_y + 12.0), (start_x, top), fill=ctx.guide_color, width=guide_width)
    _draw_dashed_line(ctx.draw, (end_x, segment_y + 12.0), (end_x, top), fill=ctx.guide_color, width=guide_width)
    ctx.draw.line([(start_x, segment_y), (end_x, segment_y)], fill=ctx.accent_color, width=ctx.line_width + 2)
    for x in (start_x, end_x):
        ctx.draw.ellipse((x - 7.0, segment_y - 7.0, x + 7.0, segment_y + 7.0), fill=ctx.accent_color)
    cue_bbox = _draw_text(
        ctx,
        "?",
        ((start_x + end_x) / 2.0, segment_y - 28.0),
        font=ctx.font,
        fill=ctx.secondary_accent_color,
    )
    segment_bbox = bbox_from_points(
        ((start_x, segment_y), (end_x, segment_y), ((start_x + end_x) / 2.0, segment_y - 28.0)),
        width=ctx.width,
        height=ctx.height,
        pad=18.0,
    )
    segment_bbox = (
        min(segment_bbox[0], cue_bbox[0]),
        min(segment_bbox[1], cue_bbox[1]),
        max(segment_bbox[2], cue_bbox[2]),
        max(segment_bbox[3], cue_bbox[3]),
    )
    interval_bbox = pad_bbox((start_x, top, end_x, bottom), 14.0, width=ctx.width, height=ctx.height)
    tool_bbox = pad_bbox(ruler_bbox, 4.0, width=ctx.width, height=ctx.height)
    scene_entities = (
        {
            "entity_id": "ruler",
            "entity_type": "measuring_tool",
            "tool_kind": "ruler",
            "unit": "centimeter",
            "max_cm": int(ruler_max),
            "bbox": bbox_to_list(tool_bbox),
        },
        {
            "entity_id": "target_segment",
            "entity_type": "segment",
            "start_cm": int(start_cm),
            "end_cm": int(end_cm),
            "length_cm": int(problem.target_length),
            "endpoints_px": [[round(start_x, 3), round(segment_y, 3)], [round(end_x, 3), round(segment_y, 3)]],
            "bbox": bbox_to_list(segment_bbox),
        },
    )
    return _RenderedToolScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=(segment_bbox, interval_bbox),
        evidence_roles=("target_segment", "ruler_interval"),
        scene_entities=scene_entities,
        render_map={
            "coord_space": "pixel",
            "tool_kind": "ruler",
            "ruler_bbox": bbox_to_list(tool_bbox),
            "ruler_unit_px": round(unit, 3),
            "ruler_start_cm": int(start_cm),
            "ruler_end_cm": int(end_cm),
            "target_segment_endpoints_px": [
                [round(start_x, 3), round(segment_y, 3)],
                [round(end_x, 3), round(segment_y, 3)],
            ],
        },
        witness={
            "tool_kind": "ruler",
            "unit": "centimeter",
            "ruler_start_cm": int(start_cm),
            "ruler_end_cm": int(end_cm),
            "target_length_cm": int(problem.target_length),
            "answer_value": float(problem.answer),
        },
    )


def _bbox_centers(bboxes: Sequence[Sequence[float]]) -> list[list[float]]:
    """Return bbox centers for projected evidence diagnostics."""

    return [
        [
            round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
            round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
        ]
        for bbox in bboxes
    ]


class _MeasuringToolsBaseTask:
    """Shared public-task implementation for measuring-tool scenes."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    query_id = ""
    prompt_task_key = ""
    scene_variant = ""

    def _build_complexity(self, rendered: _RenderedToolScene) -> TaskComplexity:
        tool_kind = str(rendered.witness.get("tool_kind", ""))
        if tool_kind == "protractor":
            target = int(rendered.witness.get("target_angle_degrees", 90))
            non_major_tick = 1.0 if target % 10 != 0 else 0.0
            precision = clamp_unit_interval(0.46 + (0.22 * non_major_tick) + (0.12 * abs(target - 90) / 60.0))
            visual_scan = 0.58
            ambiguity = 0.42 + (0.10 * non_major_tick)
        else:
            length = int(rendered.witness.get("target_length_cm", 6))
            precision = clamp_unit_interval(0.36 + (0.18 * (length / 12.0)))
            visual_scan = 0.48
            ambiguity = 0.34
        output_burden = clamp_unit_interval(0.42 + (0.06 * len(rendered.evidence_bboxes)))
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(precision),
            ambiguity=float(ambiguity),
            output_burden=float(output_burden),
        )

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
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
                if problem.query_id == "protractor_angle_value":
                    rendered = _render_protractor_scene(ctx, problem)
                elif problem.query_id == "ruler_length_value":
                    rendered = _render_ruler_scene(ctx, problem)
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
                "evidence_hint",
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
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        evidence_bboxes = [bbox_to_list(bbox) for bbox in rendered.evidence_bboxes]
        evidence_points = _bbox_centers(evidence_bboxes)
        rounded_answer = float(round1(rendered.answer))
        answer_value: int | float = rounded_answer
        if abs(rounded_answer - round(rounded_answer)) <= 1e-9:
            answer_value = int(round(rounded_answer))
        answer_gt = TypedValue(type="number", value=answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        query_params = {
            "scene_id": SCENE_ID,
            "scene_variant": str(self.scene_variant),
            "query_id": str(problem.query_id),
            "query_id_probabilities": {str(problem.query_id): 1.0},
            "target_support_probabilities": dict(problem.answer_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_measuring_tools",
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
                "answer_type": "number",
                "answer_value": answer_value,
                "answer_rounding": "integer",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 1,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "measuring_tool_readout",
                "scene_id": SCENE_ID,
                "scene_variant": str(self.scene_variant),
                "query_id": str(problem.query_id),
                "source_witness_type": "bbox_set",
                "original_evidence_value": list(rendered.evidence_roles),
                "answer_value": answer_value,
                **dict(rendered.witness),
            },
            "projected_evidence": {
                "type": "bbox_set",
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
class GeometryMeasuringToolsProtractorAngleValueTask(_MeasuringToolsBaseTask):
    """Read an angle from a protractor diagram."""

    task_id = "task_geometry__measuring_tools__protractor_angle_value"
    query_id = "protractor_angle_value"
    prompt_task_key = "protractor_angle_value_query"
    scene_variant = "protractor"


@register_task
class GeometryMeasuringToolsRulerLengthValueTask(_MeasuringToolsBaseTask):
    """Read a segment length from a ruler diagram."""

    task_id = "task_geometry__measuring_tools__ruler_length_value"
    query_id = "ruler_length_value"
    prompt_task_key = "ruler_length_value_query"
    scene_variant = "ruler"


__all__ = [
    "GeometryMeasuringToolsProtractorAngleValueTask",
    "GeometryMeasuringToolsRulerLengthValueTask",
    "SCENE_ID",
]
