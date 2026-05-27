"""Solid-of-revolution measurement tasks."""

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

SCENE_ID = "solid_revolution"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_solid_revolution_v0"

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

_CYLINDER_QUERIES: Tuple[str, ...] = ("cylinder_volume_from_rectangle",)
_CONE_QUERIES: Tuple[str, ...] = ("cone_volume_from_right_triangle",)
_DOUBLE_CONE_QUERIES: Tuple[str, ...] = ("double_cone_volume_from_triangle",)
_FRUSTUM_QUERIES: Tuple[str, ...] = ("frustum_volume_from_trapezoid",)

_CYLINDER_CASES: Tuple[Tuple[str, int, int, int], ...] = (
    ("diagonal", 6, 8, 10),
    ("diagonal", 8, 15, 17),
    ("diagonal", 9, 12, 15),
    ("diagonal", 10, 24, 26),
    ("diagonal", 12, 16, 20),
    ("diagonal", 16, 30, 34),
    ("diagonal", 20, 21, 29),
    ("diameter", 8, 7, 8),
    ("diameter", 12, 7, 12),
    ("diameter", 14, 6, 14),
)

_CONE_CASES: Tuple[Tuple[int, int, int], ...] = (
    (5, 12, 13),
    (6, 8, 10),
    (7, 24, 25),
    (8, 15, 17),
    (9, 12, 15),
    (10, 24, 26),
    (12, 16, 20),
    (12, 35, 37),
    (15, 20, 25),
    (16, 30, 34),
)

_DOUBLE_CONE_CASES: Tuple[Tuple[int, int], ...] = (
    (3, 5),
    (4, 6),
    (5, 6),
    (5, 8),
    (6, 7),
    (6, 9),
    (7, 6),
    (7, 8),
    (8, 7),
    (9, 6),
)

_FRUSTUM_CASES: Tuple[Tuple[int, int, int], ...] = (
    (1, 2, 6),
    (1, 3, 6),
    (2, 3, 6),
    (2, 4, 6),
    (2, 5, 6),
    (3, 4, 6),
    (3, 5, 6),
    (4, 5, 6),
    (4, 6, 6),
    (5, 7, 6),
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
    solid_fill_color: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    solid_kind: str
    generating_shape: str
    answer: float
    diameter: float | None
    radius: float | None
    height: float | None
    slant_height: float | None
    diagonal: float | None
    half_height: float | None
    top_radius: float | None
    bottom_radius: float | None
    total_height: float | None
    formula: str
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedSolidRevolutionScene:
    image: Image.Image
    answer: float
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


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


def _draw_dimension(
    ctx: _RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    label_offset: Point = (0.0, 0.0),
    color: Color | None = None,
) -> BBox:
    draw_color = color if color is not None else ctx.label_color
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


def _draw_arrowhead(ctx: _RenderContext, end: Point, angle: float) -> None:
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


def _draw_arrow(ctx: _RenderContext, start: Point, end: Point) -> None:
    ctx.draw.line([start, end], fill=ctx.accent_color, width=max(3, ctx.line_width - 1))
    angle = math.atan2(float(end[1]) - float(start[1]), float(end[0]) - float(start[0]))
    _draw_arrowhead(ctx, end, angle)


def _draw_rotation_cue(ctx: _RenderContext, center: Point) -> None:
    box = (
        float(center[0]) - 60.0,
        float(center[1]) - 28.0,
        float(center[0]) + 60.0,
        float(center[1]) + 28.0,
    )
    ctx.draw.arc(box, start=205, end=515, fill=ctx.accent_color, width=3)
    end_angle = math.radians(155.0)
    end = (
        float(center[0]) + 60.0 * math.cos(end_angle),
        float(center[1]) + 28.0 * math.sin(end_angle),
    )
    _draw_arrowhead(ctx, end, end_angle + math.pi / 2.0)
    _draw_label(ctx, "360°", (float(center[0]) + 6.0, float(center[1]) - 36.0), small=True)


def _draw_right_angle(ctx: _RenderContext, corner: Point, *, size: float = 18.0) -> None:
    x, y = float(corner[0]), float(corner[1])
    ctx.draw.line(
        [(x, y - size), (x + size, y - size), (x + size, y)],
        fill=ctx.line_color,
        width=2,
    )


def _draw_cylinder_preview(ctx: _RenderContext, center: Point) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    top_y = cy - 120.0
    bottom_y = cy + 120.0
    left_x = cx - 86.0
    right_x = cx + 86.0
    ellipse_h = 42.0
    ctx.draw.rectangle((left_x, top_y, right_x, bottom_y), fill=ctx.solid_fill_color)
    ctx.draw.line([(left_x, top_y), (left_x, bottom_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(right_x, top_y), (right_x, bottom_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(
        (left_x, top_y - ellipse_h / 2.0, right_x, top_y + ellipse_h / 2.0),
        fill=ctx.solid_fill_color,
        outline=ctx.line_color,
        width=ctx.line_width,
    )
    ctx.draw.arc(
        (left_x, bottom_y - ellipse_h / 2.0, right_x, bottom_y + ellipse_h / 2.0),
        start=0,
        end=180,
        fill=ctx.line_color,
        width=ctx.line_width,
    )
    ctx.draw.arc(
        (left_x, bottom_y - ellipse_h / 2.0, right_x, bottom_y + ellipse_h / 2.0),
        start=180,
        end=360,
        fill=ctx.muted_color,
        width=max(2, ctx.line_width - 1),
    )
    return _pad_bbox(
        (left_x, top_y - ellipse_h / 2.0, right_x, bottom_y + ellipse_h / 2.0),
        12.0,
        width=ctx.width,
        height=ctx.height,
    )


def _draw_cone_preview(ctx: _RenderContext, center: Point) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    apex = (cx, cy - 135.0)
    left = (cx - 94.0, cy + 118.0)
    right = (cx + 94.0, cy + 118.0)
    ctx.draw.polygon((apex, left, right), fill=ctx.solid_fill_color)
    ctx.draw.line([apex, left], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([apex, right], fill=ctx.line_color, width=ctx.line_width)
    base_box = (left[0], left[1] - 22.0, right[0], right[1] + 22.0)
    ctx.draw.arc(base_box, start=0, end=180, fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc(base_box, start=180, end=360, fill=ctx.muted_color, width=max(2, ctx.line_width - 1))
    return _bbox_from_points((apex, left, right), width=ctx.width, height=ctx.height, pad=24.0)


def _draw_double_cone_preview(ctx: _RenderContext, center: Point) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    top = (cx, cy - 142.0)
    mid_left = (cx - 92.0, cy)
    mid_right = (cx + 92.0, cy)
    bottom = (cx, cy + 142.0)
    ctx.draw.polygon((top, mid_left, mid_right), fill=ctx.solid_fill_color)
    ctx.draw.polygon((bottom, mid_left, mid_right), fill=ctx.solid_fill_color)
    for segment in ((top, mid_left), (top, mid_right), (bottom, mid_left), (bottom, mid_right)):
        ctx.draw.line(segment, fill=ctx.line_color, width=ctx.line_width)
    mid_box = (mid_left[0], cy - 22.0, mid_right[0], cy + 22.0)
    ctx.draw.arc(mid_box, start=0, end=180, fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc(mid_box, start=180, end=360, fill=ctx.muted_color, width=max(2, ctx.line_width - 1))
    return _bbox_from_points((top, mid_left, mid_right, bottom), width=ctx.width, height=ctx.height, pad=22.0)


def _draw_frustum_preview(ctx: _RenderContext, center: Point) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    top_y = cy - 120.0
    bottom_y = cy + 120.0
    top_left = cx - 54.0
    top_right = cx + 54.0
    bottom_left = cx - 104.0
    bottom_right = cx + 104.0
    ellipse_h = 36.0
    ctx.draw.polygon(
        ((top_left, top_y), (top_right, top_y), (bottom_right, bottom_y), (bottom_left, bottom_y)),
        fill=ctx.solid_fill_color,
    )
    ctx.draw.line([(top_left, top_y), (bottom_left, bottom_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(top_right, top_y), (bottom_right, bottom_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(
        (top_left, top_y - ellipse_h / 2.0, top_right, top_y + ellipse_h / 2.0),
        fill=ctx.solid_fill_color,
        outline=ctx.line_color,
        width=ctx.line_width,
    )
    ctx.draw.arc(
        (bottom_left, bottom_y - ellipse_h / 2.0, bottom_right, bottom_y + ellipse_h / 2.0),
        start=0,
        end=180,
        fill=ctx.line_color,
        width=ctx.line_width,
    )
    ctx.draw.arc(
        (bottom_left, bottom_y - ellipse_h / 2.0, bottom_right, bottom_y + ellipse_h / 2.0),
        start=180,
        end=360,
        fill=ctx.muted_color,
        width=max(2, ctx.line_width - 1),
    )
    return _pad_bbox(
        (bottom_left, top_y - ellipse_h / 2.0, bottom_right, bottom_y + ellipse_h / 2.0),
        12.0,
        width=ctx.width,
        height=ctx.height,
    )


def _selected_probability_map(values: Sequence[float], selected: float) -> Dict[str, float]:
    return {
        _fmt_number(value): (1.0 if _round1(value) == _round1(selected) else 0.0)
        for value in values
    }


def _volume_for_case(query_id: str, case: Sequence[Any]) -> float:
    if query_id == "cylinder_volume_from_rectangle":
        if isinstance(case[0], str):
            _mode, diameter, height, _support = case
        else:
            diameter, height, _support = case
        diameter = float(diameter)
        height = float(height)
        radius = diameter / 2.0
        return math.pi * radius**2 * height
    if query_id == "cone_volume_from_right_triangle":
        radius, height, _slant_height = [float(value) for value in case]
        return (math.pi * radius**2 * height) / 3.0
    if query_id == "double_cone_volume_from_triangle":
        radius, half_height = [float(value) for value in case]
        return (2.0 * math.pi * radius**2 * half_height) / 3.0
    if query_id == "frustum_volume_from_trapezoid":
        top_radius, bottom_radius, height = [float(value) for value in case]
        return (math.pi * height * (bottom_radius**2 + bottom_radius * top_radius + top_radius**2)) / 3.0
    raise ValueError(f"unsupported solid-revolution query_id: {query_id}")


def _case_pool_for_query(query_id: str) -> Tuple[Tuple[Any, ...], ...]:
    if query_id == "cylinder_volume_from_rectangle":
        return tuple(tuple(value for value in case) for case in _CYLINDER_CASES)
    if query_id == "cone_volume_from_right_triangle":
        return tuple(tuple(value for value in case) for case in _CONE_CASES)
    if query_id == "double_cone_volume_from_triangle":
        return tuple(tuple(value for value in case) for case in _DOUBLE_CONE_CASES)
    if query_id == "frustum_volume_from_trapezoid":
        return tuple(tuple(value for value in case) for case in _FRUSTUM_CASES)
    raise ValueError(f"unsupported solid-revolution query_id: {query_id}")


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

    radius: float | None = None
    diameter: float | None = None
    height: float | None = None
    slant_height: float | None = None
    diagonal: float | None = None
    half_height: float | None = None
    top_radius: float | None = None
    bottom_radius: float | None = None
    total_height: float | None = None
    generating_shape: str
    solid_kind: str
    formula: str

    if query_id == "cylinder_volume_from_rectangle":
        if isinstance(selected_case[0], str):
            selected_mode = str(selected_case[0])
            selected_diameter = selected_case[1]
            selected_height = selected_case[2]
            selected_support = selected_case[3]
        else:
            selected_mode = "diagonal"
            selected_diameter = selected_case[0]
            selected_height = selected_case[1]
            selected_support = selected_case[2]
        dimension_mode = str(params.get("dimension_mode", selected_mode))
        diameter = float(params.get("diameter", selected_diameter))
        height = float(params.get("height", selected_height))
        if diameter <= 0 or height <= 0:
            raise ValueError("cylinder diameter and height must be positive")
        if dimension_mode == "diagonal":
            diagonal = float(params.get("diagonal", selected_support))
            if diagonal <= 0:
                raise ValueError("cylinder diagonal must be positive")
            if abs((diameter**2 + height**2) - diagonal**2) > 1e-6:
                raise ValueError("rectangle diagonal must match diameter and height")
            formula = "d^2 = q^2 - h^2, then V = pi (d/2)^2 h"
            selected_support_case = ("diagonal", int(diameter), int(height), int(diagonal))
        elif dimension_mode == "diameter":
            diagonal = None
            formula = "V = pi (d/2)^2 h"
            selected_support_case = ("diameter", int(diameter), int(height), int(diameter))
        else:
            raise ValueError(f"unsupported cylinder dimension_mode: {dimension_mode}")
        radius = diameter / 2.0
        answer = math.pi * radius**2 * height
        generating_shape = "centered_rectangle"
        solid_kind = "cylinder"
    elif query_id == "cone_volume_from_right_triangle":
        radius = float(params.get("radius", selected_case[0]))
        height = float(params.get("height", selected_case[1]))
        slant_height = float(params.get("slant_height", selected_case[2]))
        if radius <= 0 or height <= 0 or slant_height <= 0:
            raise ValueError("cone radius, height, and slant height must be positive")
        if abs((radius**2 + height**2) - slant_height**2) > 1e-6:
            raise ValueError("cone slant height must match radius and height")
        answer = (math.pi * radius**2 * height) / 3.0
        generating_shape = "right_triangle"
        solid_kind = "cone"
        formula = "r^2 = l^2 - h^2, then V = (1/3) pi r^2 h"
        selected_support_case = (int(radius), int(height), int(slant_height))
    elif query_id == "double_cone_volume_from_triangle":
        radius = float(params.get("radius", selected_case[0]))
        half_height = float(params.get("half_height", selected_case[1]))
        if radius <= 0 or half_height <= 0:
            raise ValueError("double-cone radius and half height must be positive")
        total_height = 2.0 * half_height
        answer = (2.0 * math.pi * radius**2 * half_height) / 3.0
        generating_shape = "isosceles_triangle"
        solid_kind = "double_cone"
        formula = "V = 2 * (1/3) pi r^2 h"
        selected_support_case = (int(radius), int(half_height))
    elif query_id == "frustum_volume_from_trapezoid":
        top_radius = float(params.get("top_radius", selected_case[0]))
        bottom_radius = float(params.get("bottom_radius", selected_case[1]))
        height = float(params.get("height", selected_case[2]))
        if top_radius <= 0 or bottom_radius <= 0 or height <= 0:
            raise ValueError("frustum radii and height must be positive")
        if top_radius >= bottom_radius:
            raise ValueError("frustum top radius must be smaller than bottom radius")
        answer = (
            math.pi
            * height
            * (bottom_radius**2 + bottom_radius * top_radius + top_radius**2)
        ) / 3.0
        generating_shape = "right_trapezoid"
        solid_kind = "frustum"
        formula = "V = (1/3) pi h (R^2 + Rr + r^2)"
        selected_support_case = (int(top_radius), int(bottom_radius), int(height))
    else:
        raise ValueError(f"unsupported solid-revolution query_id: {query_id}")

    support_values = tuple(_round1(_volume_for_case(query_id, case)) for case in case_pool)
    return _ResolvedProblem(
        query_id=str(query_id),
        solid_kind=str(solid_kind),
        generating_shape=str(generating_shape),
        answer=_round1(answer),
        diameter=diameter,
        radius=radius,
        height=height,
        slant_height=slant_height,
        diagonal=diagonal,
        half_height=half_height,
        top_radius=top_radius,
        bottom_radius=bottom_radius,
        total_height=total_height,
        formula=str(formula),
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(float(value) for value in support_values))),
            _volume_for_case(query_id, selected_support_case),
        ),
    )


def _render_solid_revolution_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedSolidRevolutionScene:
    left_x = 200.0
    top_y = 142.0
    bottom_y = 424.0
    right_x = 340.0
    mid_y = (top_y + bottom_y) / 2.0
    preview_center = (638.0, 288.0)
    label_bboxes: Dict[str, BBox] = {}
    evidence_roles: Tuple[str, ...]
    figure_points: Tuple[Point, ...]

    if problem.query_id == "cylinder_volume_from_rectangle":
        axis_x = 236.0
        rect_left_x = 132.0
        rect_right_x = 340.0
        figure_points = (
            (rect_left_x, top_y),
            (rect_right_x, top_y),
            (rect_right_x, bottom_y),
            (rect_left_x, bottom_y),
        )
        ctx.draw.polygon(figure_points, fill=ctx.fill_color)
        for start, end in zip(figure_points, figure_points[1:] + figure_points[:1]):
            ctx.draw.line([start, end], fill=ctx.line_color, width=ctx.line_width)
        _draw_dashed_line(ctx, (axis_x, top_y - 34.0), (axis_x, bottom_y + 34.0), fill=ctx.accent_color, width=3)
        label_bboxes["height"] = _draw_dimension(
            ctx,
            (rect_left_x - 36.0, top_y),
            (rect_left_x - 36.0, bottom_y),
            f"h={_fmt_number(problem.height or 0)}",
            label_offset=(-28.0, 0.0),
        )
        if problem.diagonal is not None:
            label_bboxes["diagonal"] = _draw_dimension(
                ctx,
                (rect_left_x, top_y),
                (rect_right_x, bottom_y),
                f"q={_fmt_number(problem.diagonal)}",
                label_offset=(34.0, -16.0),
            )
            evidence_roles = ("target_volume_cue", "diagonal_label", "height_label")
        else:
            label_bboxes["diameter"] = _draw_dimension(
                ctx,
                (rect_left_x, bottom_y + 34.0),
                (rect_right_x, bottom_y + 34.0),
                f"d={_fmt_number(problem.diameter or 0)}",
                label_offset=(0.0, 26.0),
            )
            evidence_roles = ("target_volume_cue", "diameter_label", "height_label")
        solid_bbox = _draw_cylinder_preview(ctx, preview_center)
    elif problem.query_id == "cone_volume_from_right_triangle":
        figure_points = ((left_x, top_y), (left_x, bottom_y), (right_x, bottom_y))
        ctx.draw.polygon(figure_points, fill=ctx.fill_color)
        for start, end in zip(figure_points, figure_points[1:] + figure_points[:1]):
            ctx.draw.line([start, end], fill=ctx.line_color, width=ctx.line_width)
        _draw_right_angle(ctx, (left_x, bottom_y))
        _draw_dashed_line(ctx, (left_x, top_y - 34.0), (left_x, bottom_y + 34.0), fill=ctx.accent_color, width=3)
        label_bboxes["height"] = _draw_dimension(
            ctx,
            (left_x - 36.0, top_y),
            (left_x - 36.0, bottom_y),
            f"h={_fmt_number(problem.height or 0)}",
            label_offset=(-28.0, 0.0),
        )
        label_bboxes["slant_height"] = _draw_dimension(
            ctx,
            (left_x, top_y),
            (right_x, bottom_y),
            f"l={_fmt_number(problem.slant_height or 0)}",
            label_offset=(30.0, -16.0),
        )
        solid_bbox = _draw_cone_preview(ctx, preview_center)
        evidence_roles = ("target_volume_cue", "slant_height_label", "height_label")
    elif problem.query_id == "double_cone_volume_from_triangle":
        figure_points = ((left_x, top_y), (left_x, bottom_y), (right_x, mid_y))
        ctx.draw.polygon(figure_points, fill=ctx.fill_color)
        for start, end in zip(figure_points, figure_points[1:] + figure_points[:1]):
            ctx.draw.line([start, end], fill=ctx.line_color, width=ctx.line_width)
        _draw_dashed_line(ctx, (left_x, top_y - 34.0), (left_x, bottom_y + 34.0), fill=ctx.accent_color, width=3)
        label_bboxes["half_height"] = _draw_dimension(
            ctx,
            (left_x - 36.0, top_y),
            (left_x - 36.0, mid_y),
            f"h={_fmt_number(problem.half_height or 0)}",
            label_offset=(-28.0, 0.0),
        )
        label_bboxes["radius"] = _draw_dimension(
            ctx,
            (left_x, mid_y + 34.0),
            (right_x, mid_y + 34.0),
            f"r={_fmt_number(problem.radius or 0)}",
            label_offset=(0.0, 26.0),
        )
        solid_bbox = _draw_double_cone_preview(ctx, preview_center)
        evidence_roles = ("target_volume_cue", "radius_label", "half_height_label")
    elif problem.query_id == "frustum_volume_from_trapezoid":
        top_right = left_x + 86.0
        bottom_right = right_x
        figure_points = ((left_x, top_y), (top_right, top_y), (bottom_right, bottom_y), (left_x, bottom_y))
        ctx.draw.polygon(figure_points, fill=ctx.fill_color)
        for start, end in zip(figure_points, figure_points[1:] + figure_points[:1]):
            ctx.draw.line([start, end], fill=ctx.line_color, width=ctx.line_width)
        _draw_right_angle(ctx, (left_x, bottom_y))
        _draw_dashed_line(ctx, (left_x, top_y - 34.0), (left_x, bottom_y + 34.0), fill=ctx.accent_color, width=3)
        label_bboxes["height"] = _draw_dimension(
            ctx,
            (left_x - 36.0, top_y),
            (left_x - 36.0, bottom_y),
            f"h={_fmt_number(problem.height or 0)}",
            label_offset=(-28.0, 0.0),
        )
        label_bboxes["top_radius"] = _draw_dimension(
            ctx,
            (left_x, top_y - 34.0),
            (top_right, top_y - 34.0),
            f"r={_fmt_number(problem.top_radius or 0)}",
            label_offset=(0.0, -24.0),
        )
        label_bboxes["bottom_radius"] = _draw_dimension(
            ctx,
            (left_x, bottom_y + 34.0),
            (bottom_right, bottom_y + 34.0),
            f"R={_fmt_number(problem.bottom_radius or 0)}",
            label_offset=(0.0, 26.0),
        )
        solid_bbox = _draw_frustum_preview(ctx, preview_center)
        evidence_roles = (
            "target_volume_cue",
            "top_radius_label",
            "bottom_radius_label",
            "height_label",
        )
    else:
        raise ValueError(f"unsupported solid-revolution query_id: {problem.query_id}")

    _draw_label(ctx, "axis", (left_x - 4.0, top_y - 58.0), small=True)
    _draw_rotation_cue(ctx, (left_x + 78.0, top_y - 62.0))
    _draw_arrow(ctx, (395.0, 288.0), (494.0, 288.0))
    label_bboxes["target"] = _draw_label(ctx, "V=?", (preview_center[0], preview_center[1] - 168.0), small=True)

    evidence_lookup = {
        "target_volume_cue": label_bboxes["target"],
        "diameter_label": label_bboxes.get("diameter"),
        "diagonal_label": label_bboxes.get("diagonal"),
        "radius_label": label_bboxes.get("radius"),
        "slant_height_label": label_bboxes.get("slant_height"),
        "height_label": label_bboxes.get("height"),
        "half_height_label": label_bboxes.get("half_height"),
        "total_height_label": label_bboxes.get("total_height"),
        "top_radius_label": label_bboxes.get("top_radius"),
        "bottom_radius_label": label_bboxes.get("bottom_radius"),
    }
    evidence_bboxes = tuple(
        bbox for role in evidence_roles for bbox in (evidence_lookup.get(role),) if bbox is not None
    )
    figure_bbox = _bbox_from_points(figure_points, width=ctx.width, height=ctx.height, pad=48.0)
    scene_entities = (
        {
            "entity_id": "generating_shape",
            "entity_type": str(problem.generating_shape),
            "bbox": _bbox_to_list(figure_bbox),
            "rotation_axis": "marked_left_side",
        },
        {
            "entity_id": "revolved_solid",
            "entity_type": str(problem.solid_kind),
            "bbox": _bbox_to_list(solid_bbox),
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "generating_shape": str(problem.generating_shape),
        "solid_kind": str(problem.solid_kind),
        "diameter": None if problem.diameter is None else float(problem.diameter),
        "radius": None if problem.radius is None else float(problem.radius),
        "height": None if problem.height is None else float(problem.height),
        "slant_height": None if problem.slant_height is None else float(problem.slant_height),
        "diagonal": None if problem.diagonal is None else float(problem.diagonal),
        "half_height": None if problem.half_height is None else float(problem.half_height),
        "top_radius": None if problem.top_radius is None else float(problem.top_radius),
        "bottom_radius": None if problem.bottom_radius is None else float(problem.bottom_radius),
        "total_height": None if problem.total_height is None else float(problem.total_height),
        "rotation_degrees": 360,
        "volume_formula": str(problem.formula),
        "answer_value": float(problem.answer),
    }
    return _RenderedSolidRevolutionScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "generating_shape": {
                "points": [[round(x, 3), round(y, 3)] for x, y in figure_points],
                "bbox": _bbox_to_list(figure_bbox),
            },
            "solid": {
                "kind": str(problem.solid_kind),
                "bbox": _bbox_to_list(solid_bbox),
            },
            "label_bboxes": {
                key: _bbox_to_list(value) for key, value in label_bboxes.items()
            },
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _SolidRevolutionBaseTask:
    """Shared implementation for solid-of-revolution tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "solid_revolution"

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
        palettes: Tuple[Tuple[Color, Color, Color, Color], ...] = (
            ((225, 239, 255), (235, 245, 236), (27, 113, 191), (120, 145, 168)),
            ((255, 237, 222), (236, 240, 255), (189, 91, 37), (150, 132, 116)),
            ((237, 232, 255), (235, 248, 246), (111, 92, 190), (132, 126, 158)),
            ((230, 247, 235), (255, 239, 219), (30, 132, 92), (112, 150, 128)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.palette",
        )
        fill_color, solid_fill_color, accent_color, muted_color = palettes[
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
            solid_fill_color=solid_fill_color,
            accent_color=accent_color,
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
            "solid_fill_color": list(solid_fill_color),
            "accent_color": list(accent_color),
            "muted_color": list(muted_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedSolidRevolutionScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.46
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=4)
            * 0.20
        )
        precision_by_kind = {
            "cylinder": 0.58,
            "cone": 0.66,
            "double_cone": 0.74,
            "frustum": 0.88,
        }
        ambiguity_by_kind = {
            "cylinder": 0.44,
            "cone": 0.50,
            "double_cone": 0.62,
            "frustum": 0.72,
        }
        solid_kind = str(rendered.witness.get("solid_kind", "cylinder"))
        output_burden = clamp_unit_interval(
            0.42
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=4)
            * 0.16
        )
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(precision_by_kind.get(solid_kind, 0.66)),
            ambiguity=float(ambiguity_by_kind.get(solid_kind, 0.56)),
            output_burden=float(output_burden),
        )

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no solid-revolution query support")
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
        rendered: _RenderedSolidRevolutionScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_solid_revolution_scene(ctx, problem)
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
                "scene_kind": "geometry_solid_revolution",
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
                "answer_rounding": "nearest_tenth",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 1 if problem.solid_kind in {"cylinder", "cone"} else 2,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "solid_revolution_formula",
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
class GeometrySolidRevolutionCylinderVolumeValueTask(_SolidRevolutionBaseTask):
    """Compute cylinder volume from a rectangle rotated around a side."""

    task_id = "task_geometry__solid_revolution__revolution_cylinder_volume_value"
    supported_queries = _CYLINDER_QUERIES
    reasoning_kind = "cylinder_volume"


@register_task
class GeometrySolidRevolutionConeVolumeValueTask(_SolidRevolutionBaseTask):
    """Compute cone volume from a right triangle rotated around a leg."""

    task_id = "task_geometry__solid_revolution__revolution_cone_volume_value"
    supported_queries = _CONE_QUERIES
    reasoning_kind = "cone_volume"


@register_task
class GeometrySolidRevolutionDoubleConeVolumeValueTask(_SolidRevolutionBaseTask):
    """Compute double-cone volume from a triangle rotated around its side."""

    task_id = "task_geometry__solid_revolution__revolution_double_cone_volume_value"
    supported_queries = _DOUBLE_CONE_QUERIES
    reasoning_kind = "double_cone_volume"


@register_task
class GeometrySolidRevolutionFrustumVolumeValueTask(_SolidRevolutionBaseTask):
    """Compute frustum volume from a trapezoid rotated around a side."""

    task_id = "task_geometry__solid_revolution__revolution_frustum_volume_value"
    supported_queries = _FRUSTUM_QUERIES
    reasoning_kind = "frustum_volume"


__all__ = [
    "GeometrySolidRevolutionConeVolumeValueTask",
    "GeometrySolidRevolutionCylinderVolumeValueTask",
    "GeometrySolidRevolutionDoubleConeVolumeValueTask",
    "GeometrySolidRevolutionFrustumVolumeValueTask",
    "SCENE_ID",
]
