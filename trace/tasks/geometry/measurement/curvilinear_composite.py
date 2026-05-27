"""Curvilinear composite geometry formula tasks.

These tasks cover colored composite diagrams whose values come from combining
straight-edged formulas with semicircle, sector, and arc formulas.  They are
kept separate from ``composite_shape`` because the visual grammar
is formula-region based rather than theorem/constraint based.
"""

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
from ..shared.complexity import (
    build_geometry_measurement_complexity,
    clamp_unit_interval,
    normalize_linear,
)
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

SCENE_ID = "composite_shape"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_curvilinear_composite_v0"
PI_VALUE = math.pi

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)

_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "paper_white": {"kind": "solid", "color": [255, 255, 252]},
        "cool_paper": {"kind": "solid", "color": [249, 252, 255]},
        "warm_paper": {"kind": "solid", "color": [255, 252, 246]},
        "mint_paper": {"kind": "solid", "color": [249, 254, 251]},
    },
    "weights": {
        "paper_white": 1.0,
        "cool_paper": 1.0,
        "warm_paper": 1.0,
        "mint_paper": 1.0,
    },
}

_NOISE_DEFAULTS: Dict[str, Any] = {
    "apply_prob": 0.5,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.12, 0.32]},
        "downsample": {"scale": [0.93, 0.98]},
        "jpeg": {"quality": [84, 94]},
        "noise": {"alpha": [0.01, 0.03]},
    },
}

_WIDTH_SUPPORT: Tuple[int, ...] = tuple(range(8, 19))
_HEIGHT_SUPPORT: Tuple[int, ...] = (6, 8, 10, 12, 14, 16)
_RADIUS_SUPPORT: Tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10, 11, 12)
_THETA_SUPPORT: Tuple[int, ...] = (45, 60, 75, 90, 105, 120, 135, 150)

_AREA_QUERIES: Tuple[str, ...] = (
    "rectangle_semicircle_cap_area",
    "rectangle_semicircle_cutout_area",
    "rectangle_quarter_sector_cutout_area",
)
_PERIMETER_QUERIES: Tuple[str, ...] = (
    "rectangle_semicircle_cap_perimeter",
    "rectangle_semicircle_cutout_perimeter",
    "rectangle_quarter_sector_cutout_perimeter",
)
_MISSING_SIDE_QUERIES: Tuple[str, ...] = (
    "missing_width_from_semicircle_cap_area",
    "missing_width_from_semicircle_cutout_area",
)
_SECTOR_ANGLE_QUERIES: Tuple[str, ...] = (
    "sector_angle_from_arc_length",
    "sector_angle_from_area",
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
class _RenderedCurvilinearScene:
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


def _boundary_width(ctx: _RenderContext) -> int:
    return max(int(ctx.line_width) + 2, 6)


def _probability_map(values: Sequence[str]) -> Dict[str, float]:
    unique = tuple(sorted(set(str(value) for value in values)))
    if not unique:
        return {}
    p = 1.0 / float(len(unique))
    return {value: float(p) for value in unique}


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


def _dimension_values(index: int) -> tuple[int, int, int]:
    width_units = _WIDTH_SUPPORT[int(index) % len(_WIDTH_SUPPORT)]
    height_units = _HEIGHT_SUPPORT[(int(index) // len(_WIDTH_SUPPORT)) % len(_HEIGHT_SUPPORT)]
    radius_units = max(3, int(height_units // 2))
    return int(width_units), int(height_units), int(radius_units)


def _sector_values(index: int) -> tuple[int, int]:
    theta = _THETA_SUPPORT[int(index) % len(_THETA_SUPPORT)]
    radius = _RADIUS_SUPPORT[(int(index) // len(_THETA_SUPPORT)) % len(_RADIUS_SUPPORT)]
    return int(theta), int(radius)


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
        query_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.query_id",
        )
        query_id = str(tuple(supported_queries)[int(query_index) % len(tuple(supported_queries))])
        query_probabilities = _probability_map(supported_queries)

    index = _cycle_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.values",
        query_count=len(tuple(supported_queries)),
        explicit_query=bool(explicit_query),
    )

    scene_variant = str(query_id)
    resolved: Dict[str, Any] = {"pi_value": float(PI_VALUE)}
    support_probabilities: Dict[str, float] = {}
    if query_id in {
        "rectangle_semicircle_cap_area",
        "rectangle_semicircle_cutout_area",
        "rectangle_semicircle_cap_perimeter",
        "rectangle_semicircle_cutout_perimeter",
        "missing_width_from_semicircle_cap_area",
        "missing_width_from_semicircle_cutout_area",
    }:
        width_units, height_units, radius_units = _dimension_values(index)
        width_units = int(params.get("width_units", width_units))
        height_units = int(params.get("height_units", height_units))
        radius_units = int(params.get("radius_units", max(3, int(height_units // 2))))
        semicircle_area = 0.5 * PI_VALUE * float(radius_units) ** 2
        semicircle_arc_length = PI_VALUE * float(radius_units)
        if query_id.endswith("_area") and query_id.startswith("rectangle_semicircle_cap"):
            answer = float(width_units * height_units) + float(semicircle_area)
        elif query_id.endswith("_area") and query_id.startswith("rectangle_semicircle_cutout"):
            answer = float(width_units * height_units) - float(semicircle_area)
        elif query_id.endswith("_perimeter"):
            answer = (2.0 * float(width_units)) + float(height_units) + float(semicircle_arc_length)
        elif query_id == "missing_width_from_semicircle_cap_area":
            total_area = float(width_units * height_units) + float(semicircle_area)
            answer = float(width_units)
            resolved["total_area"] = _round1(total_area)
        elif query_id == "missing_width_from_semicircle_cutout_area":
            total_area = float(width_units * height_units) - float(semicircle_area)
            answer = float(width_units)
            resolved["total_area"] = _round1(total_area)
        else:
            raise ValueError(f"unsupported curvilinear query_id: {query_id}")
        resolved.update(
            {
                "width_units": int(width_units),
                "height_units": int(height_units),
                "radius_units": int(radius_units),
                "semicircle_area": _round1(semicircle_area),
                "arc_length": _round1(semicircle_arc_length),
                "straight_boundary_length": _round1((2.0 * float(width_units)) + float(height_units)),
            }
        )
        support_probabilities = _selected_probability_map(_WIDTH_SUPPORT, width_units)
    elif query_id in {"rectangle_quarter_sector_cutout_area", "rectangle_quarter_sector_cutout_perimeter"}:
        width_units, height_units, _ = _dimension_values(index)
        radius_units = _RADIUS_SUPPORT[int(index) % len(_RADIUS_SUPPORT)]
        width_units = max(int(radius_units) + 4, int(params.get("width_units", width_units)))
        height_units = max(int(radius_units) + 3, int(params.get("height_units", height_units)))
        radius_units = int(params.get("radius_units", radius_units))
        theta = 90
        sector_area = (float(theta) / 360.0) * PI_VALUE * float(radius_units) ** 2
        arc_length = (float(theta) / 360.0) * 2.0 * PI_VALUE * float(radius_units)
        if query_id.endswith("_area"):
            answer = float(width_units * height_units) - float(sector_area)
        else:
            straight_boundary_length = (2.0 * float(width_units)) + (2.0 * float(height_units)) - (2.0 * float(radius_units))
            answer = float(straight_boundary_length) + float(arc_length)
        resolved.update(
            {
                "width_units": int(width_units),
                "height_units": int(height_units),
                "radius_units": int(radius_units),
                "theta_degrees": int(theta),
                "sector_area": _round1(sector_area),
                "arc_length": _round1(arc_length),
                "straight_boundary_length": _round1((2.0 * float(width_units)) + (2.0 * float(height_units)) - (2.0 * float(radius_units))),
            }
        )
        support_probabilities = _selected_probability_map(_RADIUS_SUPPORT, radius_units)
    elif query_id in _SECTOR_ANGLE_QUERIES:
        theta, radius_units = _sector_values(index)
        theta = int(params.get("theta_degrees", theta))
        radius_units = int(params.get("radius_units", radius_units))
        arc_length = _round1((float(theta) / 360.0) * 2.0 * PI_VALUE * float(radius_units))
        sector_area = _round1((float(theta) / 360.0) * PI_VALUE * float(radius_units) ** 2)
        if query_id == "sector_angle_from_arc_length":
            answer = _round1((360.0 * float(arc_length)) / (2.0 * PI_VALUE * float(radius_units)))
        else:
            answer = _round1((360.0 * float(sector_area)) / (PI_VALUE * float(radius_units) ** 2))
        resolved.update(
            {
                "theta_degrees": int(theta),
                "radius_units": int(radius_units),
                "arc_length": float(arc_length),
                "sector_area": float(sector_area),
            }
        )
        support_probabilities = _selected_probability_map(_THETA_SUPPORT, theta)
    else:
        raise ValueError(f"unsupported curvilinear query_id: {query_id}")

    resolved["answer_value"] = _round1(float(answer))
    return _ResolvedProblem(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        answer=_round1(float(answer)),
        params=resolved,
        query_probabilities=dict(query_probabilities),
        support_probabilities=dict(support_probabilities),
    )


def _render_semicircle_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, cutout: bool) -> _RenderedCurvilinearScene:
    values = dict(problem.params)
    width_units = int(values["width_units"])
    height_units = int(values["height_units"])
    radius_units = int(values["radius_units"])
    scale = 22.0
    rect_w = float(width_units) * scale
    rect_h = float(height_units) * scale
    radius_px = float(radius_units) * scale
    left = 130.0
    top = 150.0
    right = left + rect_w
    bottom = top + rect_h
    mid_y = (top + bottom) / 2.0
    arc_box = (right - radius_px, mid_y - radius_px, right + radius_px, mid_y + radius_px)
    target_right = right if bool(cutout) else right + radius_px
    target_bbox = _pad_bbox((left, top, target_right, bottom), 8.0, width=ctx.width, height=ctx.height)

    ctx.draw.rectangle((left, top, right, bottom), fill=ctx.fill_color)
    if cutout:
        ctx.draw.pieslice(arc_box, start=90, end=270, fill=ctx.background_color)
        ctx.draw.line([(left, top), (right, top)], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([(left, top), (left, bottom)], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([(right, top), (right, mid_y - radius_px)], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([(right, mid_y + radius_px), (right, bottom)], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.arc(arc_box, start=90, end=270, fill=ctx.line_color, width=ctx.line_width)
    else:
        ctx.draw.rectangle((left, top, right, bottom), outline=ctx.line_color, width=ctx.line_width)
        ctx.draw.pieslice(arc_box, start=-90, end=90, fill=ctx.fill_color, outline=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([(right, top + 2), (right, bottom - 2)], fill=ctx.fill_color, width=ctx.line_width + 2)

    if problem.query_id.endswith("_perimeter"):
        highlight_width = _boundary_width(ctx)
        if cutout:
            ctx.draw.line([(left, top), (right, top)], fill=ctx.accent_color, width=highlight_width)
            ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
            ctx.draw.line([(left, top), (left, bottom)], fill=ctx.accent_color, width=highlight_width)
            ctx.draw.line([(right, top), (right, mid_y - radius_px)], fill=ctx.accent_color, width=highlight_width)
            ctx.draw.line([(right, mid_y + radius_px), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
            ctx.draw.arc(arc_box, start=90, end=270, fill=ctx.accent_color, width=highlight_width)
        else:
            ctx.draw.line([(left, top), (right, top)], fill=ctx.accent_color, width=highlight_width)
            ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
            ctx.draw.line([(left, top), (left, bottom)], fill=ctx.accent_color, width=highlight_width)
            ctx.draw.arc(arc_box, start=-90, end=90, fill=ctx.accent_color, width=highlight_width)

    width_dim_y = min(bottom + 34.0, float(ctx.height) - 46.0)
    width_label_offset_y = -22.0 if width_dim_y >= float(ctx.height) - 54.0 else 20.0
    width_label = "?" if problem.query_id.startswith("missing_width") else _fmt_measure(width_units)
    width_bbox = _draw_dimension(
        ctx,
        (left, width_dim_y),
        (right, width_dim_y),
        width_label,
        label_offset=(0.0, width_label_offset_y),
    )
    height_bbox = _draw_dimension(
        ctx,
        (left - 34.0, top),
        (left - 34.0, bottom),
        _fmt_measure(height_units),
        label_offset=(-26.0, 0.0),
    )
    radius_bbox = _draw_dimension(
        ctx,
        (right, mid_y),
        (right, mid_y - radius_px),
        f"r={_fmt_measure(radius_units)}",
        label_offset=(44.0 if cutout else 54.0, 0.0),
    )
    support_bboxes = [width_bbox, height_bbox, radius_bbox]
    support_roles = ["width_label", "height_label", "radius_label"]
    evidence_bboxes: list[BBox] = list(support_bboxes)
    evidence_roles: list[str] = list(support_roles)
    if problem.query_id.endswith("_perimeter"):
        arc_label_x = right + (0.62 * radius_px if not cutout else -0.58 * radius_px)
        arc_label_y = mid_y + (0.48 * radius_px)
        arc_bbox = _draw_label(
            ctx,
            f"arc={_fmt_given(float(values['arc_length']))}",
            (arc_label_x, arc_label_y),
            small=True,
        )
        straight_bbox = _draw_label(
            ctx,
            f"straight={_fmt_given(float(values['straight_boundary_length']))}",
            ((left + target_right) / 2.0, top - 42.0),
            small=True,
        )
        support_bboxes.extend([arc_bbox, straight_bbox])
        support_roles.extend(["arc_length_label", "straight_boundary_length_label"])
        evidence_bboxes = [arc_bbox, straight_bbox]
        evidence_roles = ["arc_length_label", "straight_boundary_length_label"]
    if "total_area" in values:
        total_bbox = _draw_label(
            ctx,
            f"Area={_fmt_given(float(values['total_area']))}",
            ((left + target_right) / 2.0, top - 42.0),
            small=True,
        )
        support_bboxes.append(total_bbox)
        support_roles.append("total_area_label")
        evidence_bboxes = [width_bbox, height_bbox, radius_bbox, total_bbox]
        evidence_roles = ["unknown_width_cue", "height_label", "radius_label", "total_area_label"]

    scene_entities = (
        {
            "entity_id": "target_shape",
            "entity_type": "curvilinear_composite",
            "scene_variant": problem.scene_variant,
            "bbox": _bbox_to_list(target_bbox),
            "components": [
                {"kind": "rectangle", "width": width_units, "height": height_units},
                {"kind": "semicircle", "radius": radius_units, "operation": "subtract" if cutout else "add"},
            ],
        },
    )
    return _RenderedCurvilinearScene(
        image=ctx.image,
        answer=float(problem.answer),
        query_id=str(problem.query_id),
        scene_variant=str(problem.scene_variant),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        scene_entities=scene_entities,
        render_map={
            "target_bbox": _bbox_to_list(target_bbox),
            "support_bboxes": [_bbox_to_list(bbox) for bbox in support_bboxes],
            "coord_space": "pixel",
        },
        witness={
            "formula_family": "rectangle_semicircle",
            "operation": "subtract" if cutout else "add",
            **dict(values),
        },
        reasoning_steps=2 if "missing_width" not in problem.query_id else 3,
    )


def _render_quarter_sector_cutout(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedCurvilinearScene:
    values = dict(problem.params)
    width_units = int(values["width_units"])
    height_units = int(values["height_units"])
    radius_units = int(values["radius_units"])
    scale = 23.0
    rect_w = float(width_units) * scale
    rect_h = float(height_units) * scale
    radius_px = float(radius_units) * scale
    left = 130.0
    top = 120.0
    right = left + rect_w
    bottom = top + rect_h
    center = (right, top)
    arc_box = (right - radius_px, top - radius_px, right + radius_px, top + radius_px)
    target_bbox = _pad_bbox((left, top, right, bottom), 8.0, width=ctx.width, height=ctx.height)

    ctx.draw.rectangle((left, top, right, bottom), fill=ctx.secondary_fill_color)
    ctx.draw.pieslice(arc_box, start=90, end=180, fill=ctx.background_color)
    ctx.draw.line([(left, top), (right, top)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(left, top), (left, bottom)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(right, top + radius_px), (right, bottom)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(right - radius_px, top), (left, top)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc(arc_box, start=90, end=180, fill=ctx.line_color, width=ctx.line_width)
    if problem.query_id.endswith("_perimeter"):
        highlight_width = _boundary_width(ctx)
        ctx.draw.line([(left, top), (right - radius_px, top)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.line([(left, top), (left, bottom)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.line([(left, bottom), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.line([(right, top + radius_px), (right, bottom)], fill=ctx.accent_color, width=highlight_width)
        ctx.draw.arc(arc_box, start=90, end=180, fill=ctx.accent_color, width=highlight_width)

    width_dim_y = min(bottom + 34.0, float(ctx.height) - 46.0)
    width_label_offset_y = -22.0 if width_dim_y >= float(ctx.height) - 54.0 else 20.0
    width_bbox = _draw_dimension(
        ctx,
        (left, width_dim_y),
        (right, width_dim_y),
        _fmt_measure(width_units),
        label_offset=(0.0, width_label_offset_y),
    )
    height_bbox = _draw_dimension(ctx, (left - 34.0, top), (left - 34.0, bottom), _fmt_measure(height_units), label_offset=(-26.0, 0.0))
    radius_bbox = _draw_dimension(ctx, center, (right - radius_px, top), f"r={_fmt_measure(radius_units)}", label_offset=(0.0, -26.0))
    angle_bbox = _draw_label(ctx, "90 deg", (right - 48.0, top + 42.0), small=True)
    support_bboxes = [width_bbox, height_bbox, radius_bbox, angle_bbox]
    support_roles = ["width_label", "height_label", "radius_label", "angle_label"]
    evidence_bboxes: list[BBox] = list(support_bboxes)
    evidence_roles: list[str] = list(support_roles)
    if problem.query_id.endswith("_perimeter"):
        arc_bbox = _draw_label(ctx, f"arc={_fmt_given(float(values['arc_length']))}", (right - (0.45 * radius_px), top + (0.82 * radius_px)), small=True)
        straight_bbox = _draw_label(
            ctx,
            f"straight={_fmt_given(float(values['straight_boundary_length']))}",
            (left + 70.0, top - 30.0),
            small=True,
        )
        support_bboxes.extend([arc_bbox, straight_bbox])
        support_roles.extend(["arc_length_label", "straight_boundary_length_label"])
        evidence_bboxes = [arc_bbox, straight_bbox]
        evidence_roles = ["arc_length_label", "straight_boundary_length_label"]
    scene_entities = (
        {
            "entity_id": "target_shape",
            "entity_type": "curvilinear_composite",
            "scene_variant": problem.scene_variant,
            "bbox": _bbox_to_list(target_bbox),
            "components": [
                {"kind": "rectangle", "width": width_units, "height": height_units},
                {"kind": "sector", "radius": radius_units, "theta_degrees": 90, "operation": "subtract"},
            ],
        },
    )
    return _RenderedCurvilinearScene(
        image=ctx.image,
        answer=float(problem.answer),
        query_id=str(problem.query_id),
        scene_variant=str(problem.scene_variant),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        scene_entities=scene_entities,
        render_map={
            "target_bbox": _bbox_to_list(target_bbox),
            "support_bboxes": [_bbox_to_list(bbox) for bbox in support_bboxes],
            "coord_space": "pixel",
        },
        witness={
            "formula_family": "rectangle_quarter_sector_cutout",
            **dict(values),
        },
        reasoning_steps=3,
    )


def _render_sector_angle_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedCurvilinearScene:
    values = dict(problem.params)
    theta = int(values["theta_degrees"])
    radius_units = int(values["radius_units"])
    radius_px = 180.0
    center = (310.0, 310.0)
    start_deg = -135.0
    end_deg = start_deg + float(theta)
    arc_box = (center[0] - radius_px, center[1] - radius_px, center[0] + radius_px, center[1] + radius_px)
    ctx.draw.pieslice(arc_box, start=start_deg, end=end_deg, fill=ctx.fill_color, outline=ctx.line_color, width=ctx.line_width)
    start_rad = math.radians(start_deg)
    end_rad = math.radians(end_deg)
    p0 = (center[0] + radius_px * math.cos(start_rad), center[1] + radius_px * math.sin(start_rad))
    p1 = (center[0] + radius_px * math.cos(end_rad), center[1] + radius_px * math.sin(end_rad))
    ctx.draw.line([center, p0], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([center, p1], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse((center[0] - 4, center[1] - 4, center[0] + 4, center[1] + 4), fill=ctx.line_color)

    mid_rad = math.radians((start_deg + end_deg) / 2.0)
    target_bbox = _draw_label(ctx, "?", (center[0] + 54.0 * math.cos(mid_rad), center[1] + 54.0 * math.sin(mid_rad)), small=False)
    radius_bbox = _draw_dimension(
        ctx,
        center,
        p0,
        f"r={_fmt_measure(radius_units)}",
        label_offset=(-18.0, 22.0),
    )
    if problem.query_id == "sector_angle_from_arc_length":
        measure_text = f"arc={_fmt_given(float(values['arc_length']))}"
        measure_role = "arc_length_label"
    else:
        measure_text = f"Area={_fmt_given(float(values['sector_area']))}"
        measure_role = "sector_area_label"
    measure_bbox = _draw_label(ctx, measure_text, (560.0, 210.0), small=True)
    support_bboxes = (radius_bbox, measure_bbox)
    sector_bbox = _pad_bbox(arc_box, 8.0, width=ctx.width, height=ctx.height)
    scene_entities = (
        {
            "entity_id": "target_sector",
            "entity_type": "sector",
            "bbox": _bbox_to_list(sector_bbox),
            "radius": radius_units,
            "theta_degrees": theta,
            "arc_length": float(values["arc_length"]),
            "sector_area": float(values["sector_area"]),
        },
    )
    return _RenderedCurvilinearScene(
        image=ctx.image,
        answer=float(problem.answer),
        query_id=str(problem.query_id),
        scene_variant=str(problem.scene_variant),
        evidence_bboxes=(target_bbox, *support_bboxes),
        evidence_roles=("target_angle_cue", "radius_label", measure_role),
        scene_entities=scene_entities,
        render_map={
            "target_bbox": _bbox_to_list(target_bbox),
            "sector_bbox": _bbox_to_list(sector_bbox),
            "support_bboxes": [_bbox_to_list(bbox) for bbox in support_bboxes],
            "coord_space": "pixel",
        },
        witness={
            "formula_family": "sector_angle",
            **dict(values),
        },
        reasoning_steps=2,
    )


def _render_problem(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedCurvilinearScene:
    if "semicircle_cap" in problem.query_id or "from_semicircle_cap" in problem.query_id:
        return _render_semicircle_scene(ctx, problem, cutout=False)
    if "semicircle_cutout" in problem.query_id or "from_semicircle_cutout" in problem.query_id:
        return _render_semicircle_scene(ctx, problem, cutout=True)
    if "quarter_sector_cutout" in problem.query_id:
        return _render_quarter_sector_cutout(ctx, problem)
    if problem.query_id in _SECTOR_ANGLE_QUERIES:
        return _render_sector_angle_scene(ctx, problem)
    raise ValueError(f"unsupported curvilinear query_id: {problem.query_id}")


class _CurvilinearCompositeBaseTask:
    """Shared implementation for formula-based curvilinear composite tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "curvilinear_formula"

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
            ((109, 164, 255), (118, 221, 151), (31, 91, 168)),
            ((246, 156, 86), (237, 101, 131), (154, 74, 28)),
            ((146, 116, 218), (96, 204, 210), (96, 69, 160)),
            ((229, 108, 164), (206, 235, 85), (144, 72, 120)),
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

    def _build_complexity(self, rendered: _RenderedCurvilinearScene) -> TaskComplexity:
        query_id = str(rendered.query_id)
        precision = {
            "area": 0.70,
            "perimeter": 0.74,
            "missing_side": 0.82,
            "sector_angle": 0.78,
        }.get(str(self.reasoning_kind), 0.70)
        if "quarter_sector" in query_id or "sector_angle" in query_id:
            precision = min(1.0, precision + 0.06)
        visual_scan = clamp_unit_interval(0.45 + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=6) * 0.25)
        ambiguity = 0.48
        if "cutout" in query_id:
            ambiguity += 0.08
        if "missing" in query_id:
            ambiguity += 0.10
        output_burden = clamp_unit_interval(0.48 + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=6) * 0.20)
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
            raise ValueError(f"{self.task_id} defines no curvilinear query support")
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
        rendered: _RenderedCurvilinearScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_problem(ctx, problem)
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
                "total_area": _fmt_given(float(problem.params.get("total_area", 0.0))),
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
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(problem.params),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_curvilinear_composite_shape",
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
                "type": "curvilinear_composite_formula",
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
class GeometryCurvilinearCompositeAreaValueTask(_CurvilinearCompositeBaseTask):
    """Compute the area of a curvilinear composite region."""

    task_id = "task_geometry__composite_shape__curvilinear_composite_area_value"
    supported_queries = _AREA_QUERIES
    reasoning_kind = "area"


@register_task
class GeometryCurvilinearCompositePerimeterValueTask(_CurvilinearCompositeBaseTask):
    """Compute the perimeter of a curvilinear composite boundary."""

    task_id = "task_geometry__composite_shape__curvilinear_composite_perimeter_value"
    supported_queries = _PERIMETER_QUERIES
    reasoning_kind = "perimeter"


@register_task
class GeometryCurvilinearMissingSideFromAreaValueTask(_CurvilinearCompositeBaseTask):
    """Infer a missing rectangle width from the total curvilinear area."""

    task_id = "task_geometry__composite_shape__curvilinear_missing_side_from_area_value"
    supported_queries = _MISSING_SIDE_QUERIES
    reasoning_kind = "missing_side"


@register_task
class GeometryCurvilinearSectorAngleValueTask(_CurvilinearCompositeBaseTask):
    """Infer a sector angle from arc length or sector area."""

    task_id = "task_geometry__composite_shape__curvilinear_sector_angle_value"
    supported_queries = _SECTOR_ANGLE_QUERIES
    reasoning_kind = "sector_angle"


__all__ = [
    "GeometryCurvilinearCompositeAreaValueTask",
    "GeometryCurvilinearCompositePerimeterValueTask",
    "GeometryCurvilinearMissingSideFromAreaValueTask",
    "GeometryCurvilinearSectorAngleValueTask",
]
