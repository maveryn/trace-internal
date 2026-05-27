"""Cone sector-net measurement tasks."""

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
from ..shared.complexity import (
    build_geometry_measurement_complexity,
    clamp_unit_interval,
    normalize_linear,
)
from ..shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
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

SCENE_ID = "cone_net"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_cone_sector_net_v0"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)

_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "paper_white": {"kind": "solid", "color": [255, 255, 252]},
        "cool_paper": {"kind": "solid", "color": [248, 252, 255]},
        "warm_paper": {"kind": "solid", "color": [255, 251, 246]},
    },
    "weights": {"paper_white": 1.0, "cool_paper": 1.0, "warm_paper": 1.0},
}

_NOISE_DEFAULTS: Dict[str, Any] = {
    "apply_prob": 0.45,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.08, 0.22]},
        "downsample": {"scale": [0.95, 0.99]},
        "jpeg": {"quality": [88, 96]},
        "noise": {"alpha": [0.008, 0.02]},
    },
}

_BASE_RADIUS_QUERIES: Tuple[str, ...] = ("base_radius_from_sector_angle",)
_HEIGHT_QUERIES: Tuple[str, ...] = ("height_from_sector_angle",)
_ALL_CONE_SECTOR_NET_QUERIES: Tuple[str, ...] = (
    *_BASE_RADIUS_QUERIES,
    *_HEIGHT_QUERIES,
)

_CONE_NET_CASES: Tuple[Tuple[int, int], ...] = (
    (9, 120),
    (10, 144),
    (12, 150),
    (14, 180),
    (15, 120),
    (16, 135),
    (18, 160),
    (20, 162),
    (21, 120),
    (24, 150),
    (24, 180),
    (30, 144),
)


@dataclass
class _RenderContext:
    rng: Any
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    label_color: Color
    label_stroke_color: Color
    fill_color: Color
    cone_fill_color: Color
    accent_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    answer: float
    slant_height: int
    theta_degrees: int
    base_radius: float
    cone_height: float
    arc_length: float
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedConeSectorNetScene:
    image: Image.Image
    answer: float
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _draw_dimension(
    ctx: _RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    label_offset: Point = (0.0, 0.0),
    color: Color | None = None,
    dashed: bool = False,
) -> BBox:
    draw_color = color if color is not None else ctx.label_color
    if dashed:
        _draw_dashed_line(ctx, start, end, fill=draw_color, width=max(2, ctx.line_width - 1))
    else:
        ctx.draw.line([start, end], fill=draw_color, width=max(2, ctx.line_width - 1))
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
                fill=draw_color,
                width=max(2, ctx.line_width - 1),
            )
    center = (
        (float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]),
        (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]),
    )
    return _draw_label(ctx, label, center, small=True)


def _draw_dashed_line(
    ctx: _RenderContext,
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
    pos = 0.0
    while pos < length:
        segment_end = min(length, pos + dash)
        ctx.draw.line(
            [
                (float(start[0]) + ux * pos, float(start[1]) + uy * pos),
                (
                    float(start[0]) + ux * segment_end,
                    float(start[1]) + uy * segment_end,
                ),
            ],
            fill=fill,
            width=width,
        )
        pos += dash + gap


def _point_on_circle(center: Point, radius: float, degrees: float) -> Point:
    radians = math.radians(float(degrees))
    return (
        float(center[0]) + float(radius) * math.cos(radians),
        float(center[1]) + float(radius) * math.sin(radians),
    )


def _draw_arc_band(
    ctx: _RenderContext,
    box: BBox,
    *,
    start: float,
    end: float,
    color: Color,
    width_extra: int = 2,
) -> None:
    ctx.draw.arc(
        box,
        start=float(start),
        end=float(end),
        fill=color,
        width=max(5, int(ctx.line_width) + int(width_extra)),
    )


def _draw_arrow(ctx: _RenderContext, start: Point, end: Point) -> None:
    ctx.draw.line([start, end], fill=ctx.accent_color, width=max(3, ctx.line_width - 1))
    angle = math.atan2(float(end[1]) - float(start[1]), float(end[0]) - float(start[0]))
    head = 14.0
    spread = math.radians(28.0)
    left = (
        float(end[0]) - head * math.cos(angle - spread),
        float(end[1]) - head * math.sin(angle - spread),
    )
    right = (
        float(end[0]) - head * math.cos(angle + spread),
        float(end[1]) - head * math.sin(angle + spread),
    )
    ctx.draw.polygon((end, left, right), fill=ctx.accent_color)


def _selected_probability_map(
    values: Sequence[int | float], selected: int | float
) -> Dict[str, float]:
    return {
        _fmt_number(value): (1.0 if _round1(value) == _round1(selected) else 0.0)
        for value in values
    }


def _resolve_problem(
    *,
    task_id: str,
    supported_queries: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    explicit_query_raw = params.get("query_id", params.get("query_variant"))
    if explicit_query_raw is not None:
        query_id = str(explicit_query_raw)
        if query_id not in set(supported_queries):
            raise ValueError(f"unsupported query_id for {task_id}: {query_id}")
        query_probabilities = {query_id: 1.0}
    else:
        query_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.query_id",
        )
        query_id = str(
            tuple(supported_queries)[int(query_index) % len(tuple(supported_queries))]
        )
        query_probabilities = {
            str(value): 1.0 / float(len(tuple(supported_queries)))
            for value in tuple(supported_queries)
        }

    case_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.case",
    )
    slant_height, theta_degrees = _CONE_NET_CASES[int(case_index) % len(_CONE_NET_CASES)]
    slant_height = int(params.get("slant_height", slant_height))
    theta_degrees = int(params.get("theta_degrees", theta_degrees))
    if int(slant_height) <= 0:
        raise ValueError("cone net slant height must be positive")
    if not 0 < int(theta_degrees) < 360:
        raise ValueError("cone net central angle must be between 0 and 360 degrees")

    base_radius = float(slant_height) * float(theta_degrees) / 360.0
    cone_height = math.sqrt(max(0.0, float(slant_height) ** 2 - base_radius**2))
    arc_length = (float(theta_degrees) / 360.0) * 2.0 * math.pi * float(slant_height)
    if query_id == "base_radius_from_sector_angle":
        answer = base_radius
        support_values = tuple(case[0] * case[1] / 360.0 for case in _CONE_NET_CASES)
    elif query_id == "height_from_sector_angle":
        answer = cone_height
        support_values = tuple(
            math.sqrt(max(0.0, case[0] ** 2 - (case[0] * case[1] / 360.0) ** 2))
            for case in _CONE_NET_CASES
        )
    else:
        raise ValueError(f"unsupported cone-sector-net query_id: {query_id}")

    return _ResolvedProblem(
        query_id=str(query_id),
        answer=_round1(answer),
        slant_height=int(slant_height),
        theta_degrees=int(theta_degrees),
        base_radius=_round1(base_radius),
        cone_height=_round1(cone_height),
        arc_length=_round1(arc_length),
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(_round1(value) for value in support_values))), answer
        ),
    )


def _render_cone_sector_net_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedConeSectorNetScene:
    sector_center = (245.0, 310.0)
    sector_radius_px = 172.0
    start_deg = -136.0
    end_deg = start_deg + float(problem.theta_degrees)
    mid_deg = (start_deg + end_deg) / 2.0
    arc_box = (
        sector_center[0] - sector_radius_px,
        sector_center[1] - sector_radius_px,
        sector_center[0] + sector_radius_px,
        sector_center[1] + sector_radius_px,
    )
    p0 = _point_on_circle(sector_center, sector_radius_px, start_deg)
    p1 = _point_on_circle(sector_center, sector_radius_px, end_deg)
    ctx.draw.pieslice(
        arc_box,
        start=start_deg,
        end=end_deg,
        fill=ctx.fill_color,
        outline=ctx.line_color,
        width=ctx.line_width,
    )
    ctx.draw.line([sector_center, p0], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([sector_center, p1], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(
        (
            sector_center[0] - 4.0,
            sector_center[1] - 4.0,
            sector_center[0] + 4.0,
            sector_center[1] + 4.0,
        ),
        fill=ctx.line_color,
    )
    _draw_arc_band(
        ctx, arc_box, start=start_deg, end=end_deg, color=ctx.accent_color, width_extra=4
    )

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["slant_height"] = _draw_dimension(
        ctx,
        sector_center,
        p0,
        f"l={_fmt_number(problem.slant_height)}",
        label_offset=(-18.0, 28.0),
    )
    small_angle_radius = 58.0
    small_angle_box = (
        sector_center[0] - small_angle_radius,
        sector_center[1] - small_angle_radius,
        sector_center[0] + small_angle_radius,
        sector_center[1] + small_angle_radius,
    )
    ctx.draw.arc(
        small_angle_box,
        start=start_deg,
        end=end_deg,
        fill=ctx.accent_color,
        width=max(3, ctx.line_width - 1),
    )
    angle_center = (
        sector_center[0] + 82.0 * math.cos(math.radians(mid_deg)),
        sector_center[1] + 82.0 * math.sin(math.radians(mid_deg)),
    )
    label_bboxes["sector_angle"] = _draw_label(
        ctx, f"theta={problem.theta_degrees}°", angle_center, small=True
    )

    cone_apex = (584.0, 122.0)
    cone_base_center = (584.0, 414.0)
    cone_base_left = (486.0, 414.0)
    cone_base_right = (682.0, 414.0)
    cone_base_box = (
        cone_base_left[0],
        cone_base_center[1] - 22.0,
        cone_base_right[0],
        cone_base_center[1] + 22.0,
    )
    ctx.draw.polygon(
        (cone_apex, cone_base_left, cone_base_right),
        fill=ctx.cone_fill_color,
        outline=ctx.line_color,
    )
    ctx.draw.line([cone_apex, cone_base_left], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([cone_apex, cone_base_right], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(cone_base_box, outline=ctx.accent_color, width=ctx.line_width)
    ctx.draw.arc(
        cone_base_box,
        start=0,
        end=180,
        fill=ctx.accent_color,
        width=ctx.line_width + 1,
    )
    _draw_dashed_line(
        ctx,
        cone_apex,
        cone_base_center,
        fill=ctx.line_color,
        width=max(2, ctx.line_width - 1),
    )
    ctx.draw.line(
        [cone_base_center, cone_base_right],
        fill=ctx.accent_color,
        width=max(2, ctx.line_width - 1),
    )
    marker = 16.0
    ctx.draw.line(
        [
            (cone_base_center[0], cone_base_center[1] - marker),
            (cone_base_center[0] + marker, cone_base_center[1] - marker),
            (cone_base_center[0] + marker, cone_base_center[1]),
        ],
        fill=ctx.line_color,
        width=2,
    )
    _draw_label(
        ctx,
        "l",
        (
            (cone_apex[0] + cone_base_right[0]) / 2.0 + 20.0,
            (cone_apex[1] + cone_base_right[1]) / 2.0,
        ),
        small=True,
    )
    _draw_arrow(ctx, (405.0, 252.0), (492.0, 342.0))

    if problem.query_id == "base_radius_from_sector_angle":
        label_bboxes["target"] = _draw_label(
            ctx,
            "r=?",
            (
                (cone_base_center[0] + cone_base_right[0]) / 2.0,
                cone_base_center[1] + 34.0,
            ),
            small=True,
        )
        target_role = "target_base_radius_cue"
    elif problem.query_id == "height_from_sector_angle":
        label_bboxes["target"] = _draw_label(
            ctx,
            "h=?",
            (cone_base_center[0] - 34.0, (cone_apex[1] + cone_base_center[1]) / 2.0),
            small=True,
        )
        target_role = "target_height_cue"
    else:
        raise ValueError(f"unsupported cone-sector-net query_id: {problem.query_id}")

    evidence_roles = (target_role, "slant_height_label", "sector_angle_label")
    evidence_bboxes = (
        label_bboxes["target"],
        label_bboxes["slant_height"],
        label_bboxes["sector_angle"],
    )

    sector_bbox = _pad_bbox(arc_box, 8.0, width=ctx.width, height=ctx.height)
    cone_bbox = _bbox_from_points(
        (cone_apex, cone_base_left, cone_base_right),
        width=ctx.width,
        height=ctx.height,
        pad=24.0,
    )
    scene_entities = (
        {
            "entity_id": "sector_net",
            "entity_type": "sector",
            "bbox": _bbox_to_list(sector_bbox),
            "radius_units": int(problem.slant_height),
            "theta_degrees": int(problem.theta_degrees),
            "arc_length_units": float(problem.arc_length),
        },
        {
            "entity_id": "folded_cone",
            "entity_type": "cone",
            "bbox": _bbox_to_list(cone_bbox),
            "slant_height_units": int(problem.slant_height),
            "base_radius_units": float(problem.base_radius),
            "height_units": float(problem.cone_height),
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "slant_height": int(problem.slant_height),
        "theta_degrees": int(problem.theta_degrees),
        "arc_length": float(problem.arc_length),
        "base_radius": float(problem.base_radius),
        "cone_height": float(problem.cone_height),
        "net_relation": "sector arc length equals folded cone base circumference",
        "base_radius_relation": "r = theta * l / 360",
        "height_relation": "h^2 + r^2 = l^2",
        "answer_value": float(problem.answer),
    }
    return _RenderedConeSectorNetScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "sector": {
                "center": [round(sector_center[0], 3), round(sector_center[1], 3)],
                "radius_px": round(sector_radius_px, 3),
                "start_degrees": round(start_deg, 3),
                "end_degrees": round(end_deg, 3),
                "endpoints": [
                    [round(p0[0], 3), round(p0[1], 3)],
                    [round(p1[0], 3), round(p1[1], 3)],
                ],
            },
            "cone": {
                "apex": [round(cone_apex[0], 3), round(cone_apex[1], 3)],
                "base_center": [
                    round(cone_base_center[0], 3),
                    round(cone_base_center[1], 3),
                ],
                "base_left": [round(cone_base_left[0], 3), round(cone_base_left[1], 3)],
                "base_right": [
                    round(cone_base_right[0], 3),
                    round(cone_base_right[1], 3),
                ],
            },
            "label_bboxes": {
                key: _bbox_to_list(value) for key, value in label_bboxes.items()
            },
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _ConeSectorNetBaseTask:
    """Shared implementation for cone sector-net tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "cone_sector_net"

    def _make_render_context(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> tuple[_RenderContext, Dict[str, Any]]:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.render")
        width = int(
            params.get(
                "canvas_width", group_default(render_defaults, "canvas_width", 760)
            )
        )
        height = int(
            params.get(
                "canvas_height", group_default(render_defaults, "canvas_height", 560)
            )
        )
        image, background_meta = make_background_canvas(
            canvas_width=int(width),
            canvas_height=int(height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
            fallback_color=(255, 255, 252),
        )
        shape_style = sample_geometry_shape_style(
            rng,
            params=params,
            render_defaults=render_defaults,
            anchor_colors=extract_background_anchor_colors(background_meta),
        )
        palettes: Tuple[Tuple[Color, Color, Color], ...] = (
            ((225, 239, 255), (233, 244, 232), (27, 113, 191)),
            ((255, 237, 222), (236, 240, 255), (189, 91, 37)),
            ((237, 232, 255), (235, 248, 246), (111, 92, 190)),
            ((230, 247, 235), (255, 239, 219), (30, 132, 92)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.palette",
        )
        fill_color, cone_fill_color, accent_color = palettes[
            int(palette_index) % len(palettes)
        ]
        font_size = int(
            params.get(
                "label_font_size", group_default(render_defaults, "label_font_size", 22)
            )
        )
        small_font_size = int(
            params.get(
                "small_label_font_size",
                group_default(render_defaults, "small_label_font_size", 18),
            )
        )
        line_width = int(
            params.get("line_width", group_default(render_defaults, "line_width", 4))
        )
        ctx = _RenderContext(
            rng=rng,
            image=image,
            draw=ImageDraw.Draw(image),
            width=int(width),
            height=int(height),
            line_color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
            fill_color=fill_color,
            cone_fill_color=cone_fill_color,
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
            "cone_fill_color": list(cone_fill_color),
            "accent_color": list(accent_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedConeSectorNetScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.44
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=5)
            * 0.18
        )
        formula_family = str(rendered.witness.get("formula_family", ""))
        is_base_radius = formula_family == "base_radius_from_sector_angle"
        precision = 0.76 if is_base_radius else 0.88
        ambiguity = 0.48 if is_base_radius else 0.56
        output_burden = clamp_unit_interval(
            0.44
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=5)
            * 0.12
        )
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
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no cone-sector-net query support")
        _gen_defaults, render_defaults, prompt_defaults = (
            split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS,
                task_id=str(self.task_id),
            )
        )
        problem = _resolve_problem(
            task_id=str(self.task_id),
            supported_queries=tuple(self.supported_queries),
            instance_seed=int(instance_seed),
            params=params,
        )
        last_error: Exception | None = None
        rendered: _RenderedConeSectorNetScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_cone_sector_net_scene(ctx, problem)
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
                "json_output_contract_answer_only": str(
                    prompt_defaults["json_output_contract_answer_only"]
                ),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(
                    prompt_defaults["json_example_answer_only"]
                ),
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
            "scene_variant": "sector_net_to_cone",
            "query_variant": "default",
            "query_id": str(problem.query_id),
            "query_variant_probabilities": dict(problem.query_probabilities),
            "variant_probabilities": {"default": 1.0},
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_cone_sector_net",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_variant": "default",
                    "query_id": str(problem.query_id),
                    "scene_variant": "sector_net_to_cone",
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
                "prompt_variant_active_key": str(
                    prompt_artifacts.prompt_variant_active_key
                ),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": [int(image.size[0]), int(image.size[1])],
                "coord_space": "pixel",
                "post_image_noise": dict(noise_meta),
                **dict(render_meta),
            },
            "render_map": {"coord_space": "pixel", **dict(rendered.render_map)},
            "execution_trace": {
                "scene_id": SCENE_ID,
                "scene_variant": "sector_net_to_cone",
                "query_variant": "default",
                "query_id": str(problem.query_id),
                "query_variant_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "nearest_tenth",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 1
                if problem.query_id == "base_radius_from_sector_angle"
                else 2,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "cone_sector_net_formula",
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
class GeometryConeSectorNetValueTask(_ConeSectorNetBaseTask):
    """Compute a base-radius or height value from a cone sector net."""

    task_id = "task_geometry__cone_net__cone_sector_net_value"
    supported_queries = _ALL_CONE_SECTOR_NET_QUERIES
    reasoning_kind = "cone_sector_net"


__all__ = [
    "GeometryConeSectorNetValueTask",
    "SCENE_ID",
]
