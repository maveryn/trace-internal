"""Solid cross-section measurement tasks."""

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

SCENE_ID = "solid_cross_section"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_solid_cross_section_v0"

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
    "apply_prob": 0.40,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.06, 0.18]},
        "downsample": {"scale": [0.96, 0.99]},
        "jpeg": {"quality": [90, 97]},
        "noise": {"alpha": [0.006, 0.018]},
    },
}

_CROSS_SECTION_QUERIES: Tuple[str, ...] = (
    "cone_parallel_slice_area",
    "square_pyramid_parallel_slice_area",
)

_CONE_CASES: Tuple[Tuple[float, float, float], ...] = (
    (5.0, 10.0, 4.0),
    (6.0, 12.0, 5.0),
    (7.0, 14.0, 6.0),
    (8.0, 16.0, 7.0),
    (9.0, 18.0, 10.0),
    (10.0, 20.0, 9.0),
    (12.0, 18.0, 9.0),
    (12.0, 24.0, 11.0),
)

_PYRAMID_CASES: Tuple[Tuple[float, float, float], ...] = (
    (11.0, 22.0, 9.0),
    (13.0, 26.0, 11.0),
    (16.0, 24.0, 10.0),
    (18.0, 30.0, 11.0),
    (20.0, 25.0, 9.0),
    (15.0, 20.0, 7.0),
    (12.0, 16.0, 9.0),
    (10.0, 15.0, 8.0),
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
    secondary_fill_color: Color
    accent_color: Color
    slice_fill_color: Color
    muted_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    solid_kind: str
    answer: float
    base_radius: float | None
    base_side: float | None
    solid_height: float
    slice_distance_from_apex: float
    slice_radius: float | None
    slice_side: float | None
    formula: str
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedCrossSectionScene:
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
) -> BBox:
    ctx.draw.line([start, end], fill=ctx.label_color, width=max(2, ctx.line_width - 1))
    tick = 7.0
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = (dx**2 + dy**2) ** 0.5
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


def _draw_dashed_line(
    ctx: _RenderContext,
    start: Point,
    end: Point,
    *,
    fill: Color,
    width: int,
    dash: float = 10.0,
    gap: float = 7.0,
) -> None:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = (dx**2 + dy**2) ** 0.5
    if length <= 1e-9:
        return
    ux = dx / length
    uy = dy / length
    distance = 0.0
    while distance < length:
        seg_start = distance
        seg_end = min(length, distance + dash)
        ctx.draw.line(
            [
                (float(start[0]) + ux * seg_start, float(start[1]) + uy * seg_start),
                (float(start[0]) + ux * seg_end, float(start[1]) + uy * seg_end),
            ],
            fill=fill,
            width=width,
        )
        distance += dash + gap


def _selected_probability_map(values: Sequence[float], selected: float) -> Dict[str, float]:
    return {
        _fmt_number(value): (1.0 if abs(float(value) - float(selected)) <= 1e-9 else 0.0)
        for value in values
    }


def _case_pool_for_query(query_id: str) -> Tuple[Tuple[float, ...], ...]:
    if query_id == "cone_parallel_slice_area":
        return tuple(tuple(case) for case in _CONE_CASES)
    if query_id == "square_pyramid_parallel_slice_area":
        return tuple(tuple(case) for case in _PYRAMID_CASES)
    raise ValueError(f"unsupported solid-cross-section query_id: {query_id}")


def _answer_for_case(query_id: str, case: Sequence[float]) -> float:
    if query_id == "cone_parallel_slice_area":
        base_radius, solid_height, slice_distance = [float(value) for value in case]
        slice_radius = base_radius * slice_distance / solid_height
        return _round1(math.pi * slice_radius**2)
    if query_id == "square_pyramid_parallel_slice_area":
        base_side, solid_height, slice_distance = [float(value) for value in case]
        slice_side = base_side * slice_distance / solid_height
        return _round1(slice_side**2)
    raise ValueError(f"unsupported solid-cross-section query_id: {query_id}")


def _resolve_problem(
    *,
    task_id: str,
    supported_queries: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    explicit_query_raw = params.get("query_id")
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

    case_pool = _case_pool_for_query(query_id)
    case_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.case",
    )
    selected_case = case_pool[int(case_index) % len(case_pool)]

    base_radius: float | None = None
    base_side: float | None = None
    slice_radius: float | None = None
    slice_side: float | None = None

    if query_id == "cone_parallel_slice_area":
        base_radius = float(params.get("base_radius", selected_case[0]))
        solid_height = float(params.get("solid_height", selected_case[1]))
        slice_distance = float(params.get("slice_distance_from_apex", selected_case[2]))
        if base_radius <= 0 or solid_height <= 0 or not 0 < slice_distance < solid_height:
            raise ValueError("cone slice dimensions must be positive and inside the solid")
        slice_radius = base_radius * slice_distance / solid_height
        answer = math.pi * slice_radius**2
        solid_kind = "cone"
        formula = "parallel cone slice: r_slice/R = d/H, area = pi r_slice^2"
    elif query_id == "square_pyramid_parallel_slice_area":
        base_side = float(params.get("base_side", selected_case[0]))
        solid_height = float(params.get("solid_height", selected_case[1]))
        slice_distance = float(params.get("slice_distance_from_apex", selected_case[2]))
        if base_side <= 0 or solid_height <= 0 or not 0 < slice_distance < solid_height:
            raise ValueError("pyramid slice dimensions must be positive and inside the solid")
        slice_side = base_side * slice_distance / solid_height
        answer = slice_side**2
        solid_kind = "square_pyramid"
        formula = "parallel square-pyramid slice: s_slice/s = d/H, area = s_slice^2"
    else:
        raise ValueError(f"unsupported solid-cross-section query_id: {query_id}")

    support_values = tuple(_answer_for_case(query_id, case) for case in case_pool)
    return _ResolvedProblem(
        query_id=str(query_id),
        solid_kind=str(solid_kind),
        answer=_round1(answer),
        base_radius=base_radius,
        base_side=base_side,
        solid_height=_round1(solid_height),
        slice_distance_from_apex=_round1(slice_distance),
        slice_radius=None if slice_radius is None else _round1(slice_radius),
        slice_side=None if slice_side is None else _round1(slice_side),
        formula=str(formula),
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(float(value) for value in support_values))),
            _round1(answer),
        ),
    )


def _slice_y(apex_y: float, base_y: float, solid_height: float, slice_distance: float) -> float:
    return apex_y + (base_y - apex_y) * (slice_distance / solid_height)


def _draw_cone_slice(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> Tuple[BBox, BBox, Dict[str, BBox], Tuple[str, ...]]:
    apex = (410.0, 92.0)
    base_left = (226.0, 438.0)
    base_right = (594.0, 438.0)
    base_center = (410.0, 438.0)
    base_ellipse_h = 74.0
    slice_y = _slice_y(
        apex[1],
        base_center[1],
        problem.solid_height,
        problem.slice_distance_from_apex,
    )
    scale = problem.slice_distance_from_apex / problem.solid_height
    slice_half_w = (base_right[0] - base_left[0]) * scale / 2.0
    slice_ellipse_h = base_ellipse_h * scale

    ctx.draw.polygon((apex, base_left, base_right), fill=ctx.fill_color)
    ctx.draw.line([apex, base_left], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([apex, base_right], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(
        (base_left[0], base_left[1] - base_ellipse_h / 2.0, base_right[0], base_right[1] + base_ellipse_h / 2.0),
        fill=ctx.secondary_fill_color,
        outline=ctx.line_color,
        width=ctx.line_width,
    )
    _draw_dashed_line(ctx, apex, base_center, fill=ctx.accent_color, width=3)
    slice_bbox = (
        base_center[0] - slice_half_w,
        slice_y - slice_ellipse_h / 2.0,
        base_center[0] + slice_half_w,
        slice_y + slice_ellipse_h / 2.0,
    )
    ctx.draw.ellipse(
        slice_bbox,
        fill=ctx.slice_fill_color,
        outline=ctx.accent_color,
        width=max(3, ctx.line_width),
    )
    ctx.draw.line(
        [(slice_bbox[0], slice_y), (slice_bbox[2], slice_y)],
        fill=ctx.accent_color,
        width=2,
    )

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["target"] = _draw_label(
        ctx, "A=?", (base_center[0], slice_y - slice_ellipse_h / 2.0 - 28.0), small=True
    )
    label_bboxes["base_radius"] = _draw_dimension(
        ctx,
        base_center,
        base_right,
        f"R={_fmt_number(problem.base_radius or 0)}",
        label_offset=(0.0, 36.0),
    )
    label_bboxes["height"] = _draw_dimension(
        ctx,
        (base_right[0] + 48.0, apex[1]),
        (base_right[0] + 48.0, base_center[1]),
        f"H={_fmt_number(problem.solid_height)}",
        label_offset=(38.0, 0.0),
    )
    label_bboxes["slice_distance"] = _draw_dimension(
        ctx,
        (base_center[0] - 42.0, apex[1]),
        (base_center[0] - 42.0, slice_y),
        f"d={_fmt_number(problem.slice_distance_from_apex)}",
        label_offset=(-36.0, 0.0),
    )
    solid_bbox = _bbox_from_points(
        (apex, base_left, base_right),
        width=ctx.width,
        height=ctx.height,
        pad=58.0,
    )
    slice_region_bbox = _pad_bbox(slice_bbox, 6.0, width=ctx.width, height=ctx.height)
    return solid_bbox, slice_region_bbox, label_bboxes, (
        "target_area_label",
        "slice_region",
        "base_radius_label",
        "height_label",
        "slice_distance_label",
    )


def _draw_pyramid_slice(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> Tuple[BBox, BBox, Dict[str, BBox], Tuple[str, ...]]:
    apex = (410.0, 84.0)
    front_left = (246.0, 438.0)
    front_right = (538.0, 438.0)
    back_right = (610.0, 382.0)
    back_left = (318.0, 382.0)
    base_center = (
        (front_left[0] + front_right[0] + back_right[0] + back_left[0]) / 4.0,
        (front_left[1] + front_right[1] + back_right[1] + back_left[1]) / 4.0,
    )
    base_points = (front_left, front_right, back_right, back_left)
    slice_scale = problem.slice_distance_from_apex / problem.solid_height
    slice_points = tuple(
        (
            apex[0] + (point[0] - apex[0]) * slice_scale,
            apex[1] + (point[1] - apex[1]) * slice_scale,
        )
        for point in base_points
    )
    slice_y = _slice_y(
        apex[1],
        base_center[1],
        problem.solid_height,
        problem.slice_distance_from_apex,
    )

    ctx.draw.polygon(base_points, fill=ctx.secondary_fill_color)
    for start, end in zip(base_points, base_points[1:] + base_points[:1]):
        ctx.draw.line([start, end], fill=ctx.line_color, width=ctx.line_width)
    for point in base_points:
        ctx.draw.line([apex, point], fill=ctx.line_color, width=ctx.line_width)
    _draw_dashed_line(ctx, apex, base_center, fill=ctx.accent_color, width=3)
    ctx.draw.polygon(slice_points, fill=ctx.slice_fill_color)
    for start, end in zip(slice_points, slice_points[1:] + slice_points[:1]):
        ctx.draw.line([start, end], fill=ctx.accent_color, width=max(3, ctx.line_width))

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["target"] = _draw_label(
        ctx, "A=?", (base_center[0], slice_y - 32.0), small=True
    )
    label_bboxes["base_side"] = _draw_dimension(
        ctx,
        (front_left[0], front_left[1] + 34.0),
        (front_right[0], front_right[1] + 34.0),
        f"s={_fmt_number(problem.base_side or 0)}",
        label_offset=(0.0, 28.0),
    )
    label_bboxes["height"] = _draw_dimension(
        ctx,
        (back_right[0] + 42.0, apex[1]),
        (back_right[0] + 42.0, base_center[1]),
        f"H={_fmt_number(problem.solid_height)}",
        label_offset=(38.0, 0.0),
    )
    label_bboxes["slice_distance"] = _draw_dimension(
        ctx,
        (base_center[0] - 44.0, apex[1]),
        (base_center[0] - 44.0, slice_y),
        f"d={_fmt_number(problem.slice_distance_from_apex)}",
        label_offset=(-36.0, 0.0),
    )
    solid_bbox = _bbox_from_points(
        (apex,) + base_points,
        width=ctx.width,
        height=ctx.height,
        pad=58.0,
    )
    slice_region_bbox = _bbox_from_points(
        slice_points,
        width=ctx.width,
        height=ctx.height,
        pad=6.0,
    )
    return solid_bbox, slice_region_bbox, label_bboxes, (
        "target_area_label",
        "slice_region",
        "base_side_label",
        "height_label",
        "slice_distance_label",
    )


def _render_cross_section_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedCrossSectionScene:
    if problem.query_id == "cone_parallel_slice_area":
        solid_bbox, slice_bbox, label_bboxes, evidence_roles = _draw_cone_slice(
            ctx, problem
        )
    elif problem.query_id == "square_pyramid_parallel_slice_area":
        solid_bbox, slice_bbox, label_bboxes, evidence_roles = _draw_pyramid_slice(
            ctx, problem
        )
    else:
        raise ValueError(f"unsupported solid-cross-section query_id: {problem.query_id}")

    evidence_lookup = {
        "target_area_label": label_bboxes.get("target"),
        "slice_region": slice_bbox,
        "base_radius_label": label_bboxes.get("base_radius"),
        "base_side_label": label_bboxes.get("base_side"),
        "height_label": label_bboxes.get("height"),
        "slice_distance_label": label_bboxes.get("slice_distance"),
    }
    evidence_bboxes = tuple(
        bbox
        for role in evidence_roles
        for bbox in (evidence_lookup.get(role),)
        if bbox is not None
    )
    scene_entities = (
        {
            "entity_id": "solid",
            "entity_type": str(problem.solid_kind),
            "bbox": _bbox_to_list(solid_bbox),
        },
        {
            "entity_id": "cross_section",
            "entity_type": "parallel_slice",
            "bbox": _bbox_to_list(slice_bbox),
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "solid_kind": str(problem.solid_kind),
        "base_radius": None if problem.base_radius is None else float(problem.base_radius),
        "base_side": None if problem.base_side is None else float(problem.base_side),
        "solid_height": float(problem.solid_height),
        "slice_distance_from_apex": float(problem.slice_distance_from_apex),
        "similarity_scale": float(problem.slice_distance_from_apex / problem.solid_height),
        "slice_radius": None if problem.slice_radius is None else float(problem.slice_radius),
        "slice_side": None if problem.slice_side is None else float(problem.slice_side),
        "formula": str(problem.formula),
        "answer_value": float(problem.answer),
    }
    return _RenderedCrossSectionScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "solid": {
                "kind": str(problem.solid_kind),
                "bbox": _bbox_to_list(solid_bbox),
            },
            "cross_section": {"bbox": _bbox_to_list(slice_bbox)},
            "label_bboxes": {
                key: _bbox_to_list(value) for key, value in label_bboxes.items()
            },
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _SolidCrossSectionBaseTask:
    """Shared implementation for solid cross-section measurement tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "solid_cross_section"

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
                "canvas_width", group_default(render_defaults, "canvas_width", 820)
            )
        )
        height = int(
            params.get(
                "canvas_height", group_default(render_defaults, "canvas_height", 580)
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
        palettes: Tuple[Tuple[Color, Color, Color, Color, Color], ...] = (
            ((225, 239, 255), (238, 246, 236), (27, 113, 191), (115, 184, 148), (160, 176, 190)),
            ((255, 237, 222), (236, 240, 255), (189, 91, 37), (232, 160, 98), (164, 150, 136)),
            ((237, 232, 255), (235, 248, 246), (111, 92, 190), (170, 143, 225), (158, 152, 178)),
            ((230, 247, 235), (255, 239, 219), (30, 132, 92), (101, 190, 143), (144, 168, 150)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.palette",
        )
        fill_color, secondary_fill_color, accent_color, slice_fill_color, muted_color = palettes[
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
            secondary_fill_color=secondary_fill_color,
            accent_color=accent_color,
            slice_fill_color=slice_fill_color,
            muted_color=muted_color,
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
            "slice_fill_color": list(slice_fill_color),
            "muted_color": list(muted_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedCrossSectionScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.48
            + normalize_linear(len(rendered.evidence_bboxes), min_value=4, max_value=5)
            * 0.16
        )
        precision_by_kind = {
            "cone": 0.78,
            "square_pyramid": 0.72,
        }
        ambiguity_by_kind = {
            "cone": 0.62,
            "square_pyramid": 0.58,
        }
        solid_kind = str(rendered.witness.get("solid_kind", "cone"))
        output_burden = clamp_unit_interval(
            0.46
            + normalize_linear(len(rendered.evidence_bboxes), min_value=4, max_value=5)
            * 0.12
        )
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(precision_by_kind.get(solid_kind, 0.74)),
            ambiguity=float(ambiguity_by_kind.get(solid_kind, 0.60)),
            output_burden=float(output_burden),
        )

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no solid-cross-section query support")
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
        rendered: _RenderedCrossSectionScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_cross_section_scene(ctx, problem)
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
            "scene_variant": str(problem.solid_kind),
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "variant_probabilities": {"default": 1.0},
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_solid_cross_section",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": str(problem.solid_kind),
                    "answer_value": float(rendered.answer),
                    "evidence_roles": list(rendered.evidence_roles),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
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
                "scene_variant": str(problem.solid_kind),
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "one_decimal",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 2,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "solid_cross_section_area",
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
class GeometrySolidCrossSectionAreaValueTask(_SolidCrossSectionBaseTask):
    """Compute the area of a marked solid cross-section."""

    task_id = "task_geometry__solid_cross_section__solid_cross_section_area_value"
    supported_queries = _CROSS_SECTION_QUERIES
    reasoning_kind = "cross_section_area"


__all__ = [
    "GeometrySolidCrossSectionAreaValueTask",
    "SCENE_ID",
]
