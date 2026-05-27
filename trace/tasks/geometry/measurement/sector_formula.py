"""Circular sector formula measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.complexity import build_geometry_measurement_complexity, clamp_unit_interval, normalize_linear
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.measurement_rendering import (
    round1 as _round1,
    fmt_measure as _fmt_measure,
    bbox_to_list as _bbox_to_list,
    clamp_bbox as _clamp_bbox,
    pad_bbox as _pad_bbox,
    bbox_from_points as _bbox_from_points,
    draw_label as _draw_label,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "sector"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_sector_formula_v0"
PI_VALUE = math.pi

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)

_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "paper_white": {"kind": "solid", "color": [255, 255, 252]},
        "cool_paper": {"kind": "solid", "color": [249, 252, 255]},
        "warm_paper": {"kind": "solid", "color": [255, 252, 246]},
        "blueprint_pale": {"kind": "solid", "color": [246, 250, 255]},
    },
    "weights": {
        "paper_white": 1.0,
        "cool_paper": 1.0,
        "warm_paper": 1.0,
        "blueprint_pale": 1.0,
    },
}

_NOISE_DEFAULTS: Dict[str, Any] = {
    "apply_prob": 0.5,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.10, 0.28]},
        "downsample": {"scale": [0.94, 0.99]},
        "jpeg": {"quality": [86, 95]},
        "noise": {"alpha": [0.01, 0.025]},
    },
}

_MEASURE_QUERIES: Tuple[str, ...] = (
    "area_from_radius_and_complement_angle",
    "arc_length_from_radius_and_supplement_angle",
    "area_from_arc_length_and_radius",
    "arc_length_from_area_and_radius",
)
_ANGLE_RELATION_QUERIES: Tuple[str, ...] = (
    "angle_from_arc_length_and_radius",
    "angle_from_area_and_radius",
    "complement_angle_from_arc_length",
    "supplement_angle_from_area",
    "remaining_angle_from_sector_measure",
)

_RADIUS_SUPPORT: Tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10, 11, 12)
_DIRECT_THETA_SUPPORT: Tuple[int, ...] = (45, 60, 72, 75, 90, 105, 120, 135, 150)
_COMPLEMENT_THETA_SUPPORT: Tuple[int, ...] = (25, 30, 35, 40, 45, 50, 55, 60, 65)
_SUPPLEMENT_THETA_SUPPORT: Tuple[int, ...] = (40, 45, 60, 72, 75, 90, 105, 120, 135, 150)
_REMAINING_THETA_SUPPORT: Tuple[int, ...] = (45, 60, 72, 90, 108, 120, 135, 144, 150, 180)
_BETA_LABEL_QUERIES = {
    "area_from_radius_and_complement_angle",
    "arc_length_from_radius_and_supplement_angle",
    "complement_angle_from_arc_length",
    "supplement_angle_from_area",
    "remaining_angle_from_sector_measure",
}
_NO_ANGLE_LABEL_QUERIES = {
    "area_from_arc_length_and_radius",
    "arc_length_from_area_and_radius",
}


@dataclass
class _RenderContext:
    rng: Any
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    background_color: Color
    line_color: Color
    label_color: Color
    label_stroke_color: Color
    fill_color: Color
    secondary_fill_color: Color
    accent_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    scene_variant: str
    answer: float
    params: Dict[str, Any]
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedSectorScene:
    image: Image.Image
    answer: float
    query_id: str
    scene_variant: str
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]
    reasoning_steps: int


def _fmt_given(value: float) -> str:
    return f"{float(value):.1f}"


def _draw_dimension(
    ctx: _RenderContext,
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
    center = (
        (float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]),
        (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]),
    )
    return _draw_label(ctx, label, center, small=True)


def _point_on_circle(center: Point, radius: float, degrees: float) -> Point:
    radians = math.radians(float(degrees))
    return (float(center[0]) + float(radius) * math.cos(radians), float(center[1]) + float(radius) * math.sin(radians))


def _draw_arc_band(ctx: _RenderContext, box: BBox, *, start: float, end: float, color: Color, width_extra: int = 2) -> None:
    ctx.draw.arc(box, start=float(start), end=float(end), fill=color, width=max(5, int(ctx.line_width) + int(width_extra)))


def _selected_probability_map(values: Sequence[int], selected: int | float) -> Dict[str, float]:
    return {str(value): (1.0 if float(value) == float(selected) else 0.0) for value in values}


def _cycle_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    query_count: int,
    explicit_query: bool,
) -> int:
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(index)


def _resolve_problem(
    *,
    task_id: str,
    supported_queries: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    explicit_query_raw = params.get("query_id", params.get("query_variant"))
    explicit_query = explicit_query_raw is not None
    if explicit_query:
        query_id = str(explicit_query_raw)
        if query_id not in set(supported_queries):
            raise ValueError(f"unsupported query_id for {task_id}: {query_id}")
        query_probabilities = {query_id: 1.0}
    else:
        query_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.query_id")
        query_id = str(tuple(supported_queries)[int(query_index) % len(tuple(supported_queries))])
        query_probabilities = {str(value): 1.0 / float(len(tuple(supported_queries))) for value in tuple(supported_queries)}

    index = _cycle_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.values",
        query_count=len(tuple(supported_queries)),
        explicit_query=bool(explicit_query),
    )
    radius_units = int(params.get("radius_units", _RADIUS_SUPPORT[int(index) % len(_RADIUS_SUPPORT)]))
    if query_id in {"area_from_radius_and_complement_angle", "complement_angle_from_arc_length"}:
        theta_values = _COMPLEMENT_THETA_SUPPORT
    elif query_id == "remaining_angle_from_sector_measure":
        theta_values = _REMAINING_THETA_SUPPORT
    else:
        theta_values = _DIRECT_THETA_SUPPORT if "supplement" not in query_id else _SUPPLEMENT_THETA_SUPPORT
    theta = int(params.get("theta_degrees", theta_values[(int(index) // len(_RADIUS_SUPPORT)) % len(theta_values)]))
    arc_length = _round1((float(theta) / 360.0) * 2.0 * PI_VALUE * float(radius_units))
    sector_area = _round1((float(theta) / 360.0) * PI_VALUE * float(radius_units) ** 2)
    angle_from_arc = _round1((360.0 * float(arc_length)) / (2.0 * PI_VALUE * float(radius_units)))
    angle_from_area = _round1((360.0 * float(sector_area)) / (PI_VALUE * float(radius_units) ** 2))
    scene_variant = "single_sector"
    reasoning_steps = 1
    target_angle_total = None

    if query_id == "area_from_radius_and_complement_angle":
        answer = sector_area
        formula_family = "sector_area_from_complement_angle"
        target_angle_total = 90
        scene_variant = "measure_from_complement"
        reasoning_steps = 2
    elif query_id == "arc_length_from_radius_and_supplement_angle":
        answer = arc_length
        formula_family = "sector_arc_from_supplement_angle"
        target_angle_total = 180
        scene_variant = "measure_from_supplement"
        reasoning_steps = 2
    elif query_id == "area_from_arc_length_and_radius":
        answer = _round1(0.5 * float(radius_units) * float(arc_length))
        formula_family = "sector_area_from_arc"
        reasoning_steps = 2
    elif query_id == "arc_length_from_area_and_radius":
        answer = _round1((2.0 * float(sector_area)) / float(radius_units))
        formula_family = "sector_arc_from_area"
        reasoning_steps = 2
    elif query_id == "angle_from_arc_length_and_radius":
        answer = angle_from_arc
        formula_family = "sector_angle_from_arc"
    elif query_id == "angle_from_area_and_radius":
        answer = angle_from_area
        formula_family = "sector_angle_from_area"
    elif query_id == "complement_angle_from_arc_length":
        target_angle_total = 90
        answer = _round1(float(target_angle_total) - float(angle_from_arc))
        formula_family = "sector_angle_then_complement"
        scene_variant = "adjacent_complement"
        reasoning_steps = 2
    elif query_id == "supplement_angle_from_area":
        target_angle_total = 180
        answer = _round1(float(target_angle_total) - float(angle_from_area))
        formula_family = "sector_angle_then_supplement"
        scene_variant = "adjacent_supplement"
        reasoning_steps = 2
    elif query_id == "remaining_angle_from_sector_measure":
        target_angle_total = 360
        answer = _round1(float(target_angle_total) - float(angle_from_arc))
        formula_family = "sector_angle_then_remaining"
        scene_variant = "remaining_circle_angle"
        reasoning_steps = 2
    else:
        raise ValueError(f"unsupported sector query_id: {query_id}")

    support_values = theta_values if "angle" in formula_family else _RADIUS_SUPPORT
    return _ResolvedProblem(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        answer=float(answer),
        params={
            "pi_value": float(PI_VALUE),
            "radius_units": int(radius_units),
            "theta_degrees": int(theta),
            "adjacent_angle_degrees": None if target_angle_total is None else int(target_angle_total) - int(theta),
            "angle_from_arc_length": float(angle_from_arc),
            "angle_from_sector_area": float(angle_from_area),
            "arc_length": float(arc_length),
            "sector_area": float(sector_area),
            "target_angle_total": target_angle_total,
            "answer_value": float(answer),
            "formula_family": str(formula_family),
            "reasoning_steps": int(reasoning_steps),
        },
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(support_values, theta if "angle" in formula_family else radius_units),
    )


def _draw_sector_base(ctx: _RenderContext, problem: _ResolvedProblem) -> Dict[str, Any]:
    values = dict(problem.params)
    theta = int(values["theta_degrees"])
    radius_units = int(values["radius_units"])
    radius_px = 178.0
    center = (302.0, 306.0)
    start_deg = -142.0
    end_deg = start_deg + float(theta)
    arc_box = (center[0] - radius_px, center[1] - radius_px, center[0] + radius_px, center[1] + radius_px)
    ctx.draw.pieslice(arc_box, start=start_deg, end=end_deg, fill=ctx.fill_color, outline=ctx.line_color, width=ctx.line_width)
    p0 = _point_on_circle(center, radius_px, start_deg)
    p1 = _point_on_circle(center, radius_px, end_deg)
    ctx.draw.line([center, p0], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([center, p1], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse((center[0] - 4, center[1] - 4, center[0] + 4, center[1] + 4), fill=ctx.line_color)
    _draw_arc_band(ctx, arc_box, start=start_deg, end=end_deg, color=ctx.accent_color, width_extra=3)
    return {
        "center": center,
        "radius_px": radius_px,
        "radius_units": radius_units,
        "theta": theta,
        "start_deg": start_deg,
        "end_deg": end_deg,
        "arc_box": arc_box,
        "p0": p0,
        "p1": p1,
        "sector_bbox": _pad_bbox(arc_box, 8.0, width=ctx.width, height=ctx.height),
        "arc_bbox": _bbox_from_points((p0, p1), width=ctx.width, height=ctx.height, pad=28.0),
    }


def _render_sector_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedSectorScene:
    values = dict(problem.params)
    query_id = str(problem.query_id)
    base = _draw_sector_base(ctx, problem)
    center = base["center"]
    radius_px = float(base["radius_px"])
    start_deg = float(base["start_deg"])
    end_deg = float(base["end_deg"])
    mid_deg = (start_deg + end_deg) / 2.0
    target_bbox = base["sector_bbox"]
    target_role = "target_sector_region"

    radius_label = f"r={_fmt_measure(values['radius_units'])}"
    radius_bbox = _draw_dimension(ctx, center, base["p0"], radius_label, label_offset=(-18.0, 24.0))
    angle_bbox: BBox | None = None
    if query_id not in _NO_ANGLE_LABEL_QUERIES:
        angle_text = "beta" if query_id in _BETA_LABEL_QUERIES else f"{_fmt_measure(values['theta_degrees'])}"
        angle_bbox = _draw_label(
            ctx,
            angle_text if not query_id.startswith("angle_from_") else "?",
            (center[0] + 58.0 * math.cos(math.radians(mid_deg)), center[1] + 58.0 * math.sin(math.radians(mid_deg))),
            small=False,
        )
    support_bboxes = []
    support_roles = []
    if query_id in {"area_from_radius_and_complement_angle", "arc_length_from_radius_and_supplement_angle"}:
        total = int(values["target_angle_total"])
        adjacent_angle = int(values["adjacent_angle_degrees"])
        target_end = start_deg + float(total)
        p_target = _point_on_circle(center, radius_px, target_end)
        ctx.draw.line([center, p_target], fill=ctx.line_color, width=ctx.line_width)
        relation_bbox = _draw_label(ctx, f"beta+{adjacent_angle}={total}", (590.0, 232.0), small=True)
        support_bboxes.extend([radius_bbox, relation_bbox])
        support_roles.extend(["radius_label", "angle_relation_label"])
    elif query_id == "area_from_arc_length_and_radius":
        arc_bbox = _draw_label(ctx, f"arc={_fmt_given(values['arc_length'])}", (590.0, 214.0), small=True)
        support_bboxes.extend([radius_bbox, arc_bbox])
        support_roles.extend(["radius_label", "arc_length_label"])
    elif query_id == "arc_length_from_area_and_radius":
        area_bbox = _draw_label(ctx, f"Area={_fmt_given(values['sector_area'])}", (590.0, 214.0), small=True)
        support_bboxes.extend([radius_bbox, area_bbox])
        support_roles.extend(["radius_label", "sector_area_label"])
    else:
        if "arc_length" in query_id or query_id == "remaining_angle_from_sector_measure":
            measure_bbox = _draw_label(ctx, f"arc={_fmt_given(values['arc_length'])}", (590.0, 214.0), small=True)
            measure_role = "arc_length_label"
        else:
            measure_bbox = _draw_label(ctx, f"Area={_fmt_given(values['sector_area'])}", (590.0, 214.0), small=True)
            measure_role = "sector_area_label"
        support_bboxes.extend([radius_bbox, measure_bbox])
        support_roles.extend(["radius_label", measure_role])
        if query_id in {"angle_from_arc_length_and_radius", "angle_from_area_and_radius"}:
            if angle_bbox is None:
                raise ValueError(f"missing angle bbox for {query_id}")
            target_bbox = angle_bbox
            target_role = "target_angle_cue"
        else:
            total = int(values["target_angle_total"])
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
            target_bbox = _draw_label(
                ctx,
                "?",
                (
                    center[0] + target_radius * math.cos(math.radians(target_mid)),
                    center[1] + target_radius * math.sin(math.radians(target_mid)),
                ),
                small=False,
            )
            relation_bbox = _draw_label(ctx, f"?+beta={total}", (590.0, 252.0), small=True)
            support_bboxes.append(relation_bbox)
            support_roles.append("angle_relation_label")
            target_role = "target_related_angle_cue"

    if target_role in {"target_sector_region", "target_arc"}:
        evidence_bboxes = tuple(support_bboxes)
        evidence_roles = tuple(support_roles)
    else:
        evidence_bboxes = (target_bbox, *tuple(support_bboxes))
        evidence_roles = (target_role, *tuple(support_roles))
    scene_entities = (
        {
            "entity_id": "sector",
            "entity_type": "sector",
            "bbox": _bbox_to_list(base["sector_bbox"]),
            "radius": int(values["radius_units"]),
            "theta_degrees": int(values["theta_degrees"]),
            "arc_length": float(values["arc_length"]),
            "sector_area": float(values["sector_area"]),
        },
    )
    return _RenderedSectorScene(
        image=ctx.image,
        answer=float(problem.answer),
        query_id=str(problem.query_id),
        scene_variant=str(problem.scene_variant),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        scene_entities=scene_entities,
        render_map={
            "target_bbox": _bbox_to_list(target_bbox),
            "sector_bbox": _bbox_to_list(base["sector_bbox"]),
            "support_bboxes": [_bbox_to_list(bbox) for bbox in support_bboxes],
            "coord_space": "pixel",
        },
        witness={
            "formula_family": str(values["formula_family"]),
            **dict(values),
        },
        reasoning_steps=int(values["reasoning_steps"]),
    )


class _SectorFormulaBaseTask:
    """Shared implementation for sector formula tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "sector_formula"

    def _make_render_context(self, *, instance_seed: int, params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[_RenderContext, Dict[str, Any]]:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.render")
        width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 760)))
        height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
        image, background_meta = make_background_canvas(
            canvas_width=int(width),
            canvas_height=int(height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
            fallback_color=(255, 255, 252),
        )
        bg_color = tuple(int(value) for value in background_meta.get("color", [255, 255, 252])[:3])
        shape_style = sample_geometry_shape_style(
            rng,
            params=params,
            render_defaults=render_defaults,
            anchor_colors=extract_background_anchor_colors(background_meta),
        )
        fill_palette: Tuple[Tuple[Color, Color, Color], ...] = (
            ((92, 158, 236), (114, 204, 164), (25, 91, 168)),
            ((238, 148, 86), (117, 190, 219), (150, 72, 24)),
            ((144, 116, 220), (230, 108, 164), (96, 69, 160)),
            ((94, 188, 138), (238, 184, 82), (32, 119, 76)),
        )
        color_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.task_id}.fill") % len(fill_palette)
        fill_color, secondary_fill_color, accent_color = fill_palette[int(color_index)]
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
        line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
        ctx = _RenderContext(
            rng=rng,
            image=image,
            draw=ImageDraw.Draw(image),
            width=int(width),
            height=int(height),
            background_color=(int(bg_color[0]), int(bg_color[1]), int(bg_color[2])),
            line_color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
            fill_color=fill_color,
            secondary_fill_color=secondary_fill_color,
            accent_color=accent_color,
            line_width=max(2, int(line_width)),
            font=load_font(max(12, int(font_size)), bold=True),
            small_font=load_font(max(10, int(small_font_size)), bold=True),
        )
        render_meta = {
            "background_style": dict(background_meta),
            "shape_style": shape_style.to_trace_dict(),
            "line_width": int(ctx.line_width),
            "label_font_size": int(font_size),
            "small_label_font_size": int(small_font_size),
            "fill_color": list(fill_color),
            "secondary_fill_color": list(secondary_fill_color),
            "accent_color": list(accent_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedSectorScene) -> TaskComplexity:
        precision = 0.70 if self.reasoning_kind == "sector_measure" else 0.80
        if "radius_from" in rendered.query_id:
            precision += 0.06
        if "complement" in rendered.query_id or "supplement" in rendered.query_id or "remaining" in rendered.query_id:
            precision += 0.08
        visual_scan = clamp_unit_interval(0.42 + normalize_linear(len(rendered.evidence_bboxes), min_value=4, max_value=6) * 0.25)
        ambiguity = 0.44 + (0.10 if rendered.reasoning_steps > 1 else 0.0)
        output_burden = clamp_unit_interval(0.46 + normalize_linear(len(rendered.evidence_bboxes), min_value=4, max_value=6) * 0.18)
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(min(1.0, precision)),
            ambiguity=float(ambiguity),
            output_burden=float(output_burden),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no sector query support")
        _gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
        )
        problem = _resolve_problem(
            task_id=str(self.task_id),
            supported_queries=tuple(self.supported_queries),
            instance_seed=int(instance_seed),
            params=params,
        )
        last_error: Exception | None = None
        rendered: _RenderedSectorScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_sector_scene(ctx, problem)
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
            default_config=_NOISE_DEFAULTS,
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
            query_key=str(problem.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "arc_length": _fmt_given(float(problem.params.get("arc_length", 0.0))),
                "sector_area": _fmt_given(float(problem.params.get("sector_area", 0.0))),
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

        evidence_bboxes = [_bbox_to_list(bbox) for bbox in rendered.evidence_bboxes]
        evidence_points = [
            [
                round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
            ]
            for bbox in evidence_bboxes
        ]
        answer_gt = TypedValue(type="number", value=float(rendered.answer))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        query_params = {
            "scene_id": SCENE_ID,
            "scene_variant": str(problem.scene_variant),
            "query_variant": "default",
            "query_id": str(problem.query_id),
            "query_variant_probabilities": dict(problem.query_probabilities),
            "variant_probabilities": {"default": 1.0},
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(problem.params),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_sector_formula",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_variant": "default",
                    "query_id": str(problem.query_id),
                    "scene_variant": str(problem.scene_variant),
                    "answer_value": float(rendered.answer),
                    "evidence_roles": list(rendered.evidence_roles),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_variant": "default",
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
            "render_map": {
                "coord_space": "pixel",
                **dict(rendered.render_map),
            },
            "execution_trace": {
                "scene_id": SCENE_ID,
                "scene_variant": str(problem.scene_variant),
                "query_variant": "default",
                "query_id": str(problem.query_id),
                "query_variant_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "nearest_tenth",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": int(rendered.reasoning_steps),
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "sector_formula",
                "scene_id": SCENE_ID,
                "query_variant": "default",
                "query_id": str(problem.query_id),
                "answer_value": float(rendered.answer),
                "source_witness_type": "bbox_set",
                "original_evidence_value": list(rendered.evidence_roles),
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
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometrySectorMeasureValueTask(_SectorFormulaBaseTask):
    """Compute direct and inverse sector measures."""

    task_id = "task_geometry__sector__sector_measure_value"
    supported_queries = _MEASURE_QUERIES
    reasoning_kind = "sector_measure"


@register_task
class GeometrySectorAngleRelationValueTask(_SectorFormulaBaseTask):
    """Infer a sector angle or related adjacent angle."""

    task_id = "task_geometry__sector__sector_angle_relation_value"
    supported_queries = _ANGLE_RELATION_QUERIES
    reasoning_kind = "sector_angle_relation"


__all__ = [
    "GeometrySectorMeasureValueTask",
    "GeometrySectorAngleRelationValueTask",
]
