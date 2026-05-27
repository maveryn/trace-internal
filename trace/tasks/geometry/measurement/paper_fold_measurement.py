"""Paper-fold measurement tasks."""

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
    fmt_measure as _fmt_number,
    bbox_to_list as _bbox_to_list,
    clamp_bbox as _clamp_bbox,
    pad_bbox as _pad_bbox,
    bbox_from_points as _bbox_from_points,
    draw_label as _draw_label,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "paper_fold"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_paper_fold_measurement_v0"
DEGREE_SYMBOL = chr(176)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)

_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "paper_white": {"kind": "solid", "color": [255, 255, 252]},
        "cool_paper": {"kind": "solid", "color": [248, 252, 255]},
        "warm_paper": {"kind": "solid", "color": [255, 251, 246]},
        "notebook_pale": {"kind": "solid", "color": [248, 250, 246]},
    },
    "weights": {"paper_white": 1.0, "cool_paper": 1.0, "warm_paper": 1.0, "notebook_pale": 1.0},
}

_NOISE_DEFAULTS: Dict[str, Any] = {
    "apply_prob": 0.45,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.08, 0.24]},
        "downsample": {"scale": [0.95, 0.99]},
        "jpeg": {"quality": [88, 96]},
        "noise": {"alpha": [0.008, 0.02]},
    },
}

_ANGLE_QUERIES: Tuple[str, ...] = (
    "fold_angle_from_total_label",
)

_FOLD_CASES: Tuple[Tuple[int, int], ...] = (
    (10, 6),
    (12, 8),
    (14, 6),
    (15, 9),
    (16, 10),
    (18, 12),
    (20, 14),
    (12, 5),
    (14, 10),
    (16, 7),
    (18, 9),
    (20, 11),
)


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
    paper_fill_color: Color
    folded_fill_color: Color
    crease_color: Color
    dashed_color: Color
    line_width: int
    font: Any
    small_font: Any
    point_font: Any


@dataclass(frozen=True)
class _FoldGeometry:
    height_units: float
    folded_offset_units: float
    width_units: float
    upper_segment_units: float
    lower_segment_units: float
    half_angle_degrees: float
    total_angle_degrees: float


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    scene_variant: str
    answer: float
    geometry: _FoldGeometry
    params: Dict[str, Any]
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedPaperFoldScene:
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


def _fmt_angle(value: float) -> str:
    return f"{_fmt_number(value)}{DEGREE_SYMBOL}"


def _selected_probability_map(values: Sequence[float], selected: float) -> Dict[str, float]:
    selected_key = f"{float(selected):.1f}"
    return {f"{float(value):.1f}": (1.0 if f"{float(value):.1f}" == selected_key else 0.0) for value in values}


def _draw_point_label(ctx: _RenderContext, label: str, point: Point, offset: Point) -> BBox:
    center = (float(point[0]) + float(offset[0]), float(point[1]) + float(offset[1]))
    bbox = ctx.draw.textbbox((0, 0), str(label), font=ctx.point_font, stroke_width=2)
    text_w = float(bbox[2] - bbox[0])
    text_h = float(bbox[3] - bbox[1])
    left = float(center[0]) - (text_w / 2.0)
    top = float(center[1]) - (text_h / 2.0)
    ctx.draw.text(
        (left, top),
        str(label),
        font=ctx.point_font,
        fill=ctx.label_color,
        stroke_width=2,
        stroke_fill=ctx.label_stroke_color,
    )
    return _pad_bbox((left, top, left + text_w, top + text_h), 3.0, width=ctx.width, height=ctx.height)


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: Point,
    end: Point,
    *,
    fill: Color,
    width: int,
    dash: float = 12.0,
    gap: float = 8.0,
) -> None:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return
    ux = dx / length
    uy = dy / length
    cursor = 0.0
    while cursor < length:
        dash_end = min(length, cursor + float(dash))
        draw.line(
            [
                (float(start[0]) + ux * cursor, float(start[1]) + uy * cursor),
                (float(start[0]) + ux * dash_end, float(start[1]) + uy * dash_end),
            ],
            fill=fill,
            width=width,
        )
        cursor += float(dash) + float(gap)


def _draw_angle_arc(
    ctx: _RenderContext,
    origin: Point,
    *,
    start_degrees: float,
    end_degrees: float,
    radius: float,
    label: str,
    color: Color,
    label_radius: float | None = None,
) -> BBox:
    steps = max(12, int(abs(float(end_degrees) - float(start_degrees)) // 4) + 1)
    points: list[Point] = []
    for index in range(steps + 1):
        t = float(index) / float(steps)
        degrees = float(start_degrees) + (float(end_degrees) - float(start_degrees)) * t
        radians = math.radians(degrees)
        points.append(
            (
                float(origin[0]) + float(radius) * math.cos(radians),
                float(origin[1]) + float(radius) * math.sin(radians),
            )
        )
    if len(points) > 1:
        ctx.draw.line(points, fill=color, width=max(3, ctx.line_width - 1), joint="curve")
    mid_degrees = (float(start_degrees) + float(end_degrees)) / 2.0
    label_dist = float(label_radius if label_radius is not None else radius + 22.0)
    label_center = (
        float(origin[0]) + label_dist * math.cos(math.radians(mid_degrees)),
        float(origin[1]) + label_dist * math.sin(math.radians(mid_degrees)),
    )
    return _draw_label(ctx, label, label_center, small=True)


def _fold_geometry(height_units: float, folded_offset_units: float) -> _FoldGeometry:
    height = float(height_units)
    offset = float(folded_offset_units)
    upper = (height * height + offset * offset) / (2.0 * height)
    lower = height - upper
    crease_top_x = (height * height + offset * offset) / (2.0 * offset)
    width_units = max(18.0, crease_top_x + 4.0, offset + 7.0)
    half_angle = 90.0 - math.degrees(math.atan(offset / height))
    return _FoldGeometry(
        height_units=height,
        folded_offset_units=offset,
        width_units=width_units,
        upper_segment_units=upper,
        lower_segment_units=lower,
        half_angle_degrees=half_angle,
        total_angle_degrees=2.0 * half_angle,
    )


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
    explicit_query_raw = params.get("query_id")
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
        namespace=f"{task_id}.{query_id}.fold_case",
        query_count=len(tuple(supported_queries)),
        explicit_query=bool(explicit_query),
    )
    default_height, default_offset = _FOLD_CASES[int(index) % len(_FOLD_CASES)]
    height_units = float(params.get("height_units", default_height))
    folded_offset_units = float(params.get("folded_offset_units", default_offset))
    if not (2.0 < folded_offset_units < height_units):
        raise ValueError("paper fold requires 2 < folded_offset_units < height_units")

    geometry = _fold_geometry(height_units, folded_offset_units)

    if query_id == "fold_angle_from_total_label":
        answer = _round1(geometry.half_angle_degrees)
        known_angle = _round1(2.0 * answer)
        scene_variant = "corner_fold_angle_bisector"
        target_role = "half_angle_x"
        support_values = tuple(_round1(_fold_geometry(h, u).half_angle_degrees) for h, u in _FOLD_CASES)
        reasoning_steps = 1
        formula_family = "fold_crease_bisects_reflected_angle"
    else:
        raise ValueError(f"unsupported paper-fold query_id: {query_id}")

    return _ResolvedProblem(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        answer=float(answer),
        geometry=geometry,
        params={
            "height_units": float(height_units),
            "folded_offset_units": float(folded_offset_units),
            "upper_segment_units": float(_round1(geometry.upper_segment_units)),
            "lower_segment_units": float(_round1(geometry.lower_segment_units)),
            "half_angle_degrees": float(_round1(geometry.half_angle_degrees)),
            "total_angle_degrees": float(_round1(geometry.total_angle_degrees)),
            "known_angle_degrees": None if known_angle is None else float(known_angle),
            "target_role": str(target_role),
            "answer_value": float(answer),
            "formula_family": str(formula_family),
            "reasoning_steps": int(reasoning_steps),
        },
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(support_values, answer),
    )


def _render_paper_fold_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedPaperFoldScene:
    geometry = problem.geometry
    margin_x = 94.0
    margin_y = 72.0
    scale = min((float(ctx.width) - 2.0 * margin_x) / geometry.width_units, (float(ctx.height) - 170.0) / geometry.height_units)
    paper_w = geometry.width_units * scale
    paper_h = geometry.height_units * scale
    x0 = (float(ctx.width) - paper_w) / 2.0
    y0 = margin_y

    def pt(x_units: float, y_units: float) -> Point:
        return (x0 + float(x_units) * scale, y0 + float(y_units) * scale)

    height = geometry.height_units
    offset = geometry.folded_offset_units
    upper = geometry.upper_segment_units
    crease_top_x = (height * height + offset * offset) / (2.0 * offset)

    a = pt(0.0, 0.0)
    b = pt(geometry.width_units, 0.0)
    c = pt(geometry.width_units, height)
    d = pt(0.0, height)
    e = pt(0.0, upper)
    f = pt(crease_top_x, 0.0)
    p = pt(offset, height)

    paper_bbox = _bbox_from_points((a, b, c, d), width=ctx.width, height=ctx.height, pad=0.0)
    ctx.draw.rectangle(paper_bbox, fill=ctx.paper_fill_color, outline=ctx.line_color, width=ctx.line_width)

    overlay = Image.new("RGBA", ctx.image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    folded_fill = (*ctx.folded_fill_color[:3], 88)
    overlay_draw.polygon([e, f, p], fill=folded_fill)
    ctx.image.paste(Image.alpha_composite(ctx.image.convert("RGBA"), overlay).convert("RGB"))
    ctx.draw = ImageDraw.Draw(ctx.image)

    _draw_dashed_line(ctx.draw, a, e, fill=ctx.dashed_color, width=max(2, ctx.line_width - 1))
    _draw_dashed_line(ctx.draw, a, f, fill=ctx.dashed_color, width=max(2, ctx.line_width - 1))
    ctx.draw.line([e, p, f], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([e, f], fill=ctx.crease_color, width=ctx.line_width + 1)
    for point in (a, b, c, d, e, f, p):
        radius = 4.0
        ctx.draw.ellipse(
            (point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius),
            fill=ctx.label_color,
            outline=ctx.label_stroke_color,
            width=1,
        )

    _draw_point_label(ctx, "A", a, (-14.0, -16.0))
    _draw_point_label(ctx, "B", b, (14.0, -16.0))
    _draw_point_label(ctx, "C", c, (14.0, 16.0))
    _draw_point_label(ctx, "D", d, (-15.0, 17.0))
    _draw_point_label(ctx, "E", e, (-18.0, -2.0))
    _draw_point_label(ctx, "F", f, (0.0, -18.0))
    _draw_point_label(ctx, "P", p, (0.0, 20.0))

    label_bboxes: Dict[str, BBox] = {}
    evidence_roles: Tuple[str, ...]
    target_role = str(problem.params["target_role"])
    theta_original = -90.0
    theta_crease = -math.degrees(math.atan(offset / height))
    theta_folded = -90.0 + 2.0 * (90.0 - math.degrees(math.atan(offset / height)))
    label_bboxes["known_angle"] = _draw_angle_arc(
        ctx,
        e,
        start_degrees=theta_original,
        end_degrees=theta_folded,
        radius=78.0,
        label=_fmt_angle(float(problem.params["known_angle_degrees"])),
        color=ctx.crease_color,
        label_radius=106.0,
    )
    label_bboxes["target"] = _draw_angle_arc(
        ctx,
        e,
        start_degrees=theta_crease,
        end_degrees=theta_folded,
        radius=42.0,
        label="x",
        color=ctx.crease_color,
        label_radius=62.0,
    )
    evidence_roles = (target_role, "known_angle_label")
    evidence_bboxes = (label_bboxes["target"], label_bboxes["known_angle"])

    folded_bbox = _bbox_from_points((e, f, p), width=ctx.width, height=ctx.height, pad=8.0)
    original_fold_bbox = _bbox_from_points((a, e, f), width=ctx.width, height=ctx.height, pad=8.0)
    crease_bbox = _bbox_from_points((e, f), width=ctx.width, height=ctx.height, pad=8.0)
    scene_entities = (
        {
            "entity_id": "paper_rectangle",
            "entity_type": "paper_rectangle",
            "bbox": _bbox_to_list(paper_bbox),
            "height_units": float(height),
            "width_units": float(geometry.width_units),
        },
        {
            "entity_id": "original_corner",
            "entity_type": "dashed_original_fold_region",
            "bbox": _bbox_to_list(original_fold_bbox),
        },
        {
            "entity_id": "folded_corner",
            "entity_type": "folded_flap",
            "bbox": _bbox_to_list(folded_bbox),
        },
        {
            "entity_id": "fold_crease",
            "entity_type": "fold_crease",
            "bbox": _bbox_to_list(crease_bbox),
        },
    )
    point_map = {
        "A": _bbox_to_list(_pad_bbox((a[0], a[1], a[0], a[1]), 3.0, width=ctx.width, height=ctx.height)),
        "D": _bbox_to_list(_pad_bbox((d[0], d[1], d[0], d[1]), 3.0, width=ctx.width, height=ctx.height)),
        "E": _bbox_to_list(_pad_bbox((e[0], e[1], e[0], e[1]), 3.0, width=ctx.width, height=ctx.height)),
        "F": _bbox_to_list(_pad_bbox((f[0], f[1], f[0], f[1]), 3.0, width=ctx.width, height=ctx.height)),
        "P": _bbox_to_list(_pad_bbox((p[0], p[1], p[0], p[1]), 3.0, width=ctx.width, height=ctx.height)),
    }
    return _RenderedPaperFoldScene(
        image=ctx.image,
        answer=float(problem.answer),
        query_id=str(problem.query_id),
        scene_variant=str(problem.scene_variant),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        scene_entities=scene_entities,
        render_map={
            "target_bbox": _bbox_to_list(evidence_bboxes[0]),
            "support_bboxes": [_bbox_to_list(bbox) for bbox in evidence_bboxes[1:]],
            "paper_bbox": _bbox_to_list(paper_bbox),
            "folded_flap_bbox": _bbox_to_list(folded_bbox),
            "original_corner_bbox": _bbox_to_list(original_fold_bbox),
            "crease_bbox": _bbox_to_list(crease_bbox),
            "point_bboxes": point_map,
            "coord_space": "pixel",
        },
        witness={
            "formula_family": str(problem.params["formula_family"]),
            "height_units": float(height),
            "folded_offset_units": float(offset),
            "upper_segment_units": float(_round1(geometry.upper_segment_units)),
            "lower_segment_units": float(_round1(geometry.lower_segment_units)),
            "half_angle_degrees": float(_round1(geometry.half_angle_degrees)),
            "total_angle_degrees": float(_round1(geometry.total_angle_degrees)),
            "target_role": str(target_role),
        },
        reasoning_steps=int(problem.params["reasoning_steps"]),
    )


class _PaperFoldMeasurementBaseTask:
    """Shared implementation for folded-paper measurement tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "paper_fold_measurement"

    def _make_render_context(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> tuple[_RenderContext, Dict[str, Any]]:
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
        palette: Tuple[Tuple[Color, Color, Color, Color], ...] = (
            ((252, 249, 235), (96, 164, 214), (24, 107, 166), (122, 132, 142)),
            ((247, 250, 255), (226, 143, 106), (165, 74, 40), (118, 126, 136)),
            ((250, 247, 255), (126, 155, 226), (74, 86, 162), (121, 126, 140)),
            ((247, 253, 247), (96, 178, 132), (39, 124, 74), (120, 132, 122)),
        )
        color_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.task_id}.paper_palette") % len(palette)
        paper_fill, folded_fill, crease_color, dashed_color = palette[int(color_index)]
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
        point_font_size = int(params.get("point_label_font_size", group_default(render_defaults, "point_label_font_size", 17)))
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
            paper_fill_color=paper_fill,
            folded_fill_color=folded_fill,
            crease_color=crease_color,
            dashed_color=dashed_color,
            line_width=max(2, int(line_width)),
            font=load_font(max(12, int(font_size)), bold=True),
            small_font=load_font(max(10, int(small_font_size)), bold=True),
            point_font=load_font(max(10, int(point_font_size)), bold=True),
        )
        render_meta = {
            "background_style": dict(background_meta),
            "shape_style": shape_style.to_trace_dict(),
            "line_width": int(ctx.line_width),
            "label_font_size": int(font_size),
            "small_label_font_size": int(small_font_size),
            "point_label_font_size": int(point_font_size),
            "paper_fill_color": list(paper_fill),
            "folded_fill_color": list(folded_fill),
            "crease_color": list(crease_color),
            "dashed_color": list(dashed_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedPaperFoldScene) -> TaskComplexity:
        if self.reasoning_kind == "paper_fold_angle":
            precision = 0.62
            ambiguity = 0.46
        else:
            precision = 0.76
            ambiguity = 0.54
        visual_scan = clamp_unit_interval(0.42 + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=4) * 0.18)
        output_burden = clamp_unit_interval(0.44 + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=4) * 0.16)
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(precision),
            ambiguity=float(ambiguity),
            output_burden=float(output_burden),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no paper-fold query support")
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
        rendered: _RenderedPaperFoldScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_paper_fold_scene(ctx, problem)
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
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(problem.params),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_paper_fold_measurement",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": str(problem.scene_variant),
                    "answer_value": float(rendered.answer),
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
            "render_map": {
                "coord_space": "pixel",
                **dict(rendered.render_map),
            },
            "execution_trace": {
                "scene_id": SCENE_ID,
                "scene_variant": str(problem.scene_variant),
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "nearest_tenth",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": int(rendered.reasoning_steps),
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "paper_fold_measurement",
                "scene_id": SCENE_ID,
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
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryPaperFoldAngleValueTask(_PaperFoldMeasurementBaseTask):
    """Compute a marked angle in a folded-paper diagram."""

    task_id = "task_geometry__paper_fold__paper_fold_angle_value"
    supported_queries = _ANGLE_QUERIES
    reasoning_kind = "paper_fold_angle"


__all__ = [
    "GeometryPaperFoldAngleValueTask",
]
