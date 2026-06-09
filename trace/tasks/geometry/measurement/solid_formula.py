"""Direct solid-formula measurement tasks."""

from __future__ import annotations

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
from ...shared.text_legibility import draw_text_traced
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
from ..shared.fixed_query_task import geometry_selected_probability_map as _selected_probability_map

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "solid_formula"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_solid_formula_v0"

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

_MISSING_DIMENSION_QUERIES: Tuple[str, ...] = (
    "cylinder_cone_radius_from_volume_heights",
    "cylinder_cone_height_from_volume_radius",
    "prism_pyramid_height_from_volume",
    "house_prism_length_from_volume",
)

_CYLINDER_CONE_RADIUS_CASES: Tuple[Tuple[float, float, float], ...] = (
    (3.0, 12.0, 6.0),
    (4.0, 9.0, 6.0),
    (4.5, 10.0, 9.0),
    (5.0, 8.0, 6.0),
    (5.5, 10.0, 6.0),
    (6.0, 9.0, 9.0),
    (7.0, 8.0, 12.0),
    (8.0, 7.0, 6.0),
)

_CYLINDER_CONE_HEIGHT_CASES: Tuple[Tuple[float, float, float], ...] = (
    (3.0, 9.0, 6.0),
    (4.0, 7.0, 9.0),
    (5.0, 8.0, 6.0),
    (6.0, 5.5, 9.0),
    (7.0, 6.0, 6.0),
    (8.0, 4.5, 9.0),
    (5.0, 10.0, 12.0),
    (6.0, 7.0, 12.0),
)

_PRISM_PYRAMID_CASES: Tuple[Tuple[float, float, float, float], ...] = (
    (6.0, 4.0, 7.0, 6.0),
    (8.0, 5.0, 6.0, 9.0),
    (7.0, 6.0, 5.0, 6.0),
    (9.0, 4.0, 8.0, 3.0),
    (10.0, 5.0, 4.5, 6.0),
    (8.0, 6.0, 5.5, 9.0),
    (9.0, 7.0, 4.0, 6.0),
    (12.0, 5.0, 6.5, 3.0),
)

_HOUSE_PRISM_CASES: Tuple[Tuple[float, float, float, float], ...] = (
    (6.0, 4.0, 4.0, 8.0),
    (8.0, 3.0, 6.0, 7.0),
    (10.0, 5.0, 4.0, 6.0),
    (12.0, 4.0, 6.0, 5.5),
    (9.0, 5.0, 8.0, 4.0),
    (7.0, 6.0, 4.0, 6.5),
    (11.0, 4.0, 6.0, 5.0),
    (10.0, 6.0, 6.0, 4.5),
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
    muted_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    solid_kind: str
    answer: float
    unknown_dimension: str
    radius: float | None
    height: float | None
    total_height: float | None
    cylinder_height: float | None
    cone_height: float | None
    volume: float | None
    volume_pi_multiple: float | None
    surface_area: float | None
    side_a: float | None
    side_b: float | None
    side_x: float | None
    prism_height: float | None
    pyramid_height: float | None
    triangle_base: float | None
    triangle_height: float | None
    prism_length: float | None
    wall_height: float | None
    roof_height: float | None
    formula: str
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedSolidFormulaScene:
    image: Image.Image
    answer: float
    annotation_bboxes: Tuple[BBox, ...]
    annotation_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _fmt_pi_multiple(value: float) -> str:
    pi_symbol = "\u03c0"
    coefficient = _fmt_number(value)
    if coefficient == "1":
        return pi_symbol
    return f"{coefficient}{pi_symbol}"


def _draw_value_box(ctx: _RenderContext, text: str, center: Point) -> BBox:
    font = ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    text_w = float(bbox[2] - bbox[0])
    text_h = float(bbox[3] - bbox[1])
    left = float(center[0]) - (text_w / 2.0) - 12.0
    top = float(center[1]) - (text_h / 2.0) - 8.0
    right = left + text_w + 24.0
    bottom = top + text_h + 16.0
    ctx.draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=6,
        fill=(255, 255, 255),
        outline=ctx.muted_color,
        width=2,
    )
    draw_text_traced(ctx.draw,
        (left + 12.0, top + 8.0),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=1,
        stroke_fill=ctx.label_stroke_color,
     role="readout", required=False,)
    return _pad_bbox((left, top, right, bottom), 2.0, width=ctx.width, height=ctx.height)


def _draw_dimension(
    ctx: _RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    label_offset: Point = (0.0, 0.0),
    target: bool = False,
) -> BBox:
    color = ctx.accent_color if bool(target) else ctx.label_color
    width = max(2, ctx.line_width - 1)
    ctx.draw.line([start, end], fill=color, width=width)
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
                fill=color,
                width=width,
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


def _case_pool_for_query(query_id: str) -> Tuple[Tuple[float, ...], ...]:
    if query_id == "cylinder_cone_radius_from_volume_heights":
        return tuple(tuple(case) for case in _CYLINDER_CONE_RADIUS_CASES)
    if query_id == "cylinder_cone_height_from_volume_radius":
        return tuple(tuple(case) for case in _CYLINDER_CONE_HEIGHT_CASES)
    if query_id == "prism_pyramid_height_from_volume":
        return tuple(tuple(case) for case in _PRISM_PYRAMID_CASES)
    if query_id == "house_prism_length_from_volume":
        return tuple(tuple(case) for case in _HOUSE_PRISM_CASES)
    raise ValueError(f"unsupported solid-formula query_id: {query_id}")


def _answer_for_case(query_id: str, case: Sequence[float]) -> float:
    if query_id == "cylinder_cone_radius_from_volume_heights":
        return _round1(float(case[0]))
    if query_id == "cylinder_cone_height_from_volume_radius":
        return _round1(float(case[1]))
    if query_id == "prism_pyramid_height_from_volume":
        return _round1(float(case[2]))
    if query_id == "house_prism_length_from_volume":
        return _round1(float(case[3]))
    raise ValueError(f"unsupported solid-formula query_id: {query_id}")


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
    height: float | None = None
    total_height: float | None = None
    cylinder_height: float | None = None
    cone_height: float | None = None
    volume: float | None = None
    volume_pi_multiple: float | None = None
    surface_area: float | None = None
    side_a: float | None = None
    side_b: float | None = None
    side_x: float | None = None
    prism_height: float | None = None
    pyramid_height: float | None = None
    triangle_base: float | None = None
    triangle_height: float | None = None
    prism_length: float | None = None
    wall_height: float | None = None
    roof_height: float | None = None

    if query_id == "cylinder_cone_radius_from_volume_heights":
        radius = float(params.get("radius", selected_case[0]))
        cylinder_height = float(params.get("cylinder_height", selected_case[1]))
        cone_height = float(params.get("cone_height", selected_case[2]))
        if radius <= 0 or cylinder_height <= 0 or cone_height <= 0:
            raise ValueError("cylinder-cone dimensions must be positive")
        total_height = cylinder_height + cone_height
        volume_pi_multiple = radius**2 * (cylinder_height + (cone_height / 3.0))
        answer = radius
        solid_kind = "cylinder_cone"
        unknown_dimension = "radius"
        formula = "V = pi r^2 h_cyl + (1/3) pi r^2 h_cone, solve r from total height and cone height"
    elif query_id == "cylinder_cone_height_from_volume_radius":
        radius = float(params.get("radius", selected_case[0]))
        cylinder_height = float(params.get("cylinder_height", selected_case[1]))
        cone_height = float(params.get("cone_height", selected_case[2]))
        if radius <= 0 or cylinder_height <= 0 or cone_height <= 0:
            raise ValueError("cylinder-cone dimensions must be positive")
        volume_pi_multiple = radius**2 * (cylinder_height + (cone_height / 3.0))
        answer = cylinder_height
        solid_kind = "cylinder_cone"
        unknown_dimension = "cylinder_height"
        formula = "V = pi r^2 x + (1/3) pi r^2 h_cone, solve x from V, r, and cone height"
    elif query_id == "prism_pyramid_height_from_volume":
        side_a = float(params.get("side_a", selected_case[0]))
        side_b = float(params.get("side_b", selected_case[1]))
        prism_height = float(params.get("prism_height", selected_case[2]))
        pyramid_height = float(params.get("pyramid_height", selected_case[3]))
        if side_a <= 0 or side_b <= 0 or prism_height <= 0 or pyramid_height <= 0:
            raise ValueError("prism-pyramid dimensions must be positive")
        base_area = side_a * side_b
        volume = base_area * (prism_height + (pyramid_height / 3.0))
        answer = prism_height
        solid_kind = "prism_pyramid"
        unknown_dimension = "prism_height"
        formula = "V = lwx + (1/3)lwp, solve x from V, l, w, and pyramid height"
    elif query_id == "house_prism_length_from_volume":
        triangle_base = float(params.get("triangle_base", selected_case[0]))
        wall_height = float(params.get("wall_height", selected_case[1]))
        roof_height = float(params.get("roof_height", selected_case[2]))
        prism_length = float(params.get("prism_length", selected_case[3]))
        if triangle_base <= 0 or wall_height <= 0 or roof_height <= 0 or prism_length <= 0:
            raise ValueError("house-prism dimensions must be positive")
        cross_section_area = (triangle_base * wall_height) + (
            0.5 * triangle_base * roof_height
        )
        volume = cross_section_area * prism_length
        answer = prism_length
        solid_kind = "house_prism"
        unknown_dimension = "length"
        formula = "V = (bw + (1/2)bt)L, solve L from rectangular wall and triangular roof cross-section"
    else:
        raise ValueError(f"unsupported solid-formula query_id: {query_id}")

    support_values = tuple(_answer_for_case(query_id, case) for case in case_pool)
    return _ResolvedProblem(
        query_id=str(query_id),
        solid_kind=str(solid_kind),
        answer=_round1(answer),
        unknown_dimension=str(unknown_dimension),
        radius=radius,
        height=height,
        total_height=None if total_height is None else _round1(total_height),
        cylinder_height=None if cylinder_height is None else _round1(cylinder_height),
        cone_height=None if cone_height is None else _round1(cone_height),
        volume=None if volume is None else _round1(volume),
        volume_pi_multiple=None
        if volume_pi_multiple is None
        else _round1(volume_pi_multiple),
        surface_area=None if surface_area is None else _round1(surface_area),
        side_a=side_a,
        side_b=side_b,
        side_x=side_x,
        prism_height=None if prism_height is None else _round1(prism_height),
        pyramid_height=None if pyramid_height is None else _round1(pyramid_height),
        triangle_base=triangle_base,
        triangle_height=triangle_height,
        prism_length=prism_length,
        wall_height=None if wall_height is None else _round1(wall_height),
        roof_height=None if roof_height is None else _round1(roof_height),
        formula=str(formula),
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(float(value) for value in support_values))),
            _round1(answer),
            key_fn=_fmt_number,
            is_selected=lambda value, selected: abs(float(value) - float(selected)) <= 1e-9,
        ),
    )


def _draw_cylinder_cone_body(ctx: _RenderContext) -> tuple[BBox, Dict[str, Point]]:
    x0, x1 = 250.0, 570.0
    cyl_top_y, bottom_y = 252.0, 438.0
    apex = (410.0, 84.0)
    ellipse_h = 66.0
    cx = (x0 + x1) / 2.0

    ctx.draw.rectangle((x0, cyl_top_y, x1, bottom_y), fill=ctx.fill_color)
    ctx.draw.line([(x0, cyl_top_y), (x0, bottom_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([(x1, cyl_top_y), (x1, bottom_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc(
        (x0, bottom_y - ellipse_h / 2.0, x1, bottom_y + ellipse_h / 2.0),
        0,
        180,
        fill=ctx.line_color,
        width=ctx.line_width,
    )
    ctx.draw.arc(
        (x0, bottom_y - ellipse_h / 2.0, x1, bottom_y + ellipse_h / 2.0),
        180,
        360,
        fill=ctx.muted_color,
        width=max(2, ctx.line_width - 1),
    )
    ctx.draw.polygon((apex, (x0, cyl_top_y), (x1, cyl_top_y)), fill=ctx.secondary_fill_color)
    ctx.draw.line([apex, (x0, cyl_top_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([apex, (x1, cyl_top_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(
        (x0, cyl_top_y - ellipse_h / 2.0, x1, cyl_top_y + ellipse_h / 2.0),
        fill=None,
        outline=ctx.line_color,
        width=ctx.line_width,
    )
    _draw_dashed_line(ctx, apex, (cx, cyl_top_y), fill=ctx.accent_color, width=3)
    bbox = _pad_bbox(
        (x0, apex[1], x1, bottom_y + ellipse_h / 2.0),
        42.0,
        width=ctx.width,
        height=ctx.height,
    )
    return bbox, {
        "apex": apex,
        "base_left": (x0, cyl_top_y),
        "base_right": (x1, cyl_top_y),
        "base_center": (cx, cyl_top_y),
        "bottom_center": (cx, bottom_y),
        "bottom_right": (x1, bottom_y),
        "bottom_left": (x0, bottom_y),
        "cyl_top_right": (x1, cyl_top_y),
    }


def _draw_cylinder_cone_radius(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> Tuple[BBox, Dict[str, BBox], Tuple[str, ...]]:
    bbox, points = _draw_cylinder_cone_body(ctx)
    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["volume"] = _draw_value_box(
        ctx, f"V={_fmt_pi_multiple(problem.volume_pi_multiple or 0)}", (166.0, 92.0)
    )
    label_bboxes["total_height"] = _draw_dimension(
        ctx,
        (points["bottom_left"][0] - 50.0, points["apex"][1]),
        (points["bottom_left"][0] - 50.0, points["bottom_left"][1]),
        f"H={_fmt_number(problem.total_height or 0)}",
        label_offset=(-42.0, 0.0),
    )
    label_bboxes["cone_height"] = _draw_dimension(
        ctx,
        (points["cyl_top_right"][0] + 38.0, points["apex"][1]),
        (points["cyl_top_right"][0] + 38.0, points["cyl_top_right"][1]),
        f"c={_fmt_number(problem.cone_height or 0)}",
        label_offset=(36.0, 0.0),
    )
    label_bboxes["target"] = _draw_dimension(
        ctx,
        points["base_center"],
        points["base_right"],
        "r=?",
        label_offset=(0.0, -34.0),
        target=True,
    )
    return bbox, label_bboxes, (
        "target_radius_label",
        "volume_label",
        "total_height_label",
        "cone_height_label",
    )


def _draw_cylinder_cone_height(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> Tuple[BBox, Dict[str, BBox], Tuple[str, ...]]:
    bbox, points = _draw_cylinder_cone_body(ctx)
    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["volume"] = _draw_value_box(
        ctx, f"V={_fmt_pi_multiple(problem.volume_pi_multiple or 0)}", (164.0, 92.0)
    )
    label_bboxes["radius"] = _draw_dimension(
        ctx,
        points["base_center"],
        points["base_right"],
        f"r={_fmt_number(problem.radius or 0)}",
        label_offset=(0.0, -34.0),
    )
    label_bboxes["cone_height"] = _draw_dimension(
        ctx,
        (points["cyl_top_right"][0] + 38.0, points["apex"][1]),
        (points["cyl_top_right"][0] + 38.0, points["cyl_top_right"][1]),
        f"c={_fmt_number(problem.cone_height or 0)}",
        label_offset=(36.0, 0.0),
    )
    label_bboxes["target"] = _draw_dimension(
        ctx,
        (points["bottom_right"][0] + 42.0, points["cyl_top_right"][1]),
        (points["bottom_right"][0] + 42.0, points["bottom_right"][1]),
        "x=?",
        label_offset=(38.0, 0.0),
        target=True,
    )
    return bbox, label_bboxes, (
        "target_cylinder_height_label",
        "volume_label",
        "radius_label",
        "cone_height_label",
    )


def _draw_prism_pyramid(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> Tuple[BBox, Dict[str, BBox], Tuple[str, ...]]:
    front = ((236.0, 232.0), (516.0, 232.0), (516.0, 424.0), (236.0, 424.0))
    offset = (96.0, -62.0)
    back = tuple((x + offset[0], y + offset[1]) for x, y in front)
    front_tl, front_tr, front_br, front_bl = front
    back_tl, back_tr, back_br, back_bl = back
    roof_apex = (
        (front_tl[0] + front_tr[0] + back_tl[0] + back_tr[0]) / 4.0,
        90.0,
    )
    roof_center = (
        (front_tl[0] + front_tr[0] + back_tl[0] + back_tr[0]) / 4.0,
        (front_tl[1] + front_tr[1] + back_tl[1] + back_tr[1]) / 4.0,
    )

    ctx.draw.polygon((front_tl, front_tr, back_tr, back_tl), fill=ctx.secondary_fill_color)
    ctx.draw.polygon((front_tr, front_br, back_br, back_tr), fill=ctx.fill_color)
    ctx.draw.polygon((front_bl, front_br, back_br, back_bl), fill=ctx.secondary_fill_color)
    ctx.draw.polygon(front, fill=ctx.fill_color)
    for start, end in (
        (front_tl, front_tr),
        (front_tr, front_br),
        (front_br, front_bl),
        (front_bl, front_tl),
        (back_tl, back_tr),
        (back_tr, back_br),
        (back_br, back_bl),
        (back_bl, back_tl),
        (front_tl, back_tl),
        (front_tr, back_tr),
        (front_br, back_br),
        (front_bl, back_bl),
    ):
        ctx.draw.line([start, end], fill=ctx.line_color, width=ctx.line_width)
    roof_faces = (
        (front_tl, front_tr, roof_apex),
        (front_tr, back_tr, roof_apex),
        (back_tr, back_tl, roof_apex),
        (back_tl, front_tl, roof_apex),
    )
    for face in roof_faces:
        ctx.draw.polygon(face, fill=ctx.secondary_fill_color)
    for point in (front_tl, front_tr, back_tr, back_tl):
        ctx.draw.line([roof_apex, point], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([front_tl, front_tr], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([front_tr, back_tr], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([back_tr, back_tl], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([back_tl, front_tl], fill=ctx.line_color, width=ctx.line_width)
    _draw_dashed_line(ctx, roof_apex, roof_center, fill=ctx.accent_color, width=3)

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["volume"] = _draw_value_box(
        ctx, f"V={_fmt_number(problem.volume or 0)}", (154.0, 94.0)
    )
    label_bboxes["side_a"] = _draw_dimension(
        ctx,
        (front_bl[0], front_bl[1] + 36.0),
        (front_br[0], front_br[1] + 36.0),
        f"l={_fmt_number(problem.side_a or 0)}",
        label_offset=(0.0, 28.0),
    )
    label_bboxes["side_b"] = _draw_dimension(
        ctx,
        (front_br[0] + 18.0, front_br[1] + 18.0),
        (back_br[0] + 18.0, back_br[1] + 18.0),
        f"w={_fmt_number(problem.side_b or 0)}",
        label_offset=(30.0, 20.0),
    )
    label_bboxes["pyramid_height"] = _draw_dimension(
        ctx,
        (roof_center[0] + 32.0, roof_apex[1]),
        (roof_center[0] + 32.0, roof_center[1]),
        f"p={_fmt_number(problem.pyramid_height or 0)}",
        label_offset=(36.0, 0.0),
    )
    label_bboxes["target"] = _draw_dimension(
        ctx,
        (front_tl[0] - 34.0, front_tl[1]),
        (front_bl[0] - 34.0, front_bl[1]),
        "x=?",
        label_offset=(-34.0, 0.0),
        target=True,
    )
    bbox = _bbox_from_points(tuple(front) + tuple(back) + (roof_apex,), width=ctx.width, height=ctx.height, pad=54.0)
    return bbox, label_bboxes, (
        "target_prism_height_label",
        "volume_label",
        "known_length_label",
        "known_width_label",
        "pyramid_height_label",
    )


def _draw_house_prism(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> Tuple[BBox, Dict[str, BBox], Tuple[str, ...]]:
    front_a = (260.0, 420.0)
    front_b = (520.0, 420.0)
    front_c = (520.0, 262.0)
    front_d = (390.0, 148.0)
    front_e = (260.0, 262.0)
    offset = (116.0, -76.0)
    back_a = (front_a[0] + offset[0], front_a[1] + offset[1])
    back_b = (front_b[0] + offset[0], front_b[1] + offset[1])
    back_c = (front_c[0] + offset[0], front_c[1] + offset[1])
    back_d = (front_d[0] + offset[0], front_d[1] + offset[1])
    back_e = (front_e[0] + offset[0], front_e[1] + offset[1])

    front_poly = (front_a, front_b, front_c, front_d, front_e)
    back_poly = (back_a, back_b, back_c, back_d, back_e)
    ctx.draw.polygon((front_a, front_b, back_b, back_a), fill=ctx.secondary_fill_color)
    ctx.draw.polygon((front_b, front_c, back_c, back_b), fill=ctx.fill_color)
    ctx.draw.polygon((front_c, front_d, back_d, back_c), fill=ctx.secondary_fill_color)
    ctx.draw.polygon(front_poly, fill=ctx.fill_color)
    for start, end in (
        (front_a, front_b),
        (front_b, front_c),
        (front_c, front_d),
        (front_d, front_e),
        (front_e, front_a),
        (back_a, back_b),
        (back_b, back_c),
        (back_c, back_d),
        (back_d, back_e),
        (back_e, back_a),
        (front_a, back_a),
        (front_b, back_b),
        (front_c, back_c),
        (front_d, back_d),
        (front_e, back_e),
    ):
        ctx.draw.line([start, end], fill=ctx.line_color, width=ctx.line_width)
    roof_foot = (front_d[0], front_c[1])
    _draw_dashed_line(ctx, front_d, roof_foot, fill=ctx.accent_color, width=3)

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["volume"] = _draw_value_box(
        ctx, f"V={_fmt_number(problem.volume or 0)}", (154.0, 94.0)
    )
    label_bboxes["triangle_base"] = _draw_dimension(
        ctx,
        (front_a[0], front_a[1] + 34.0),
        (front_b[0], front_b[1] + 34.0),
        f"b={_fmt_number(problem.triangle_base or 0)}",
        label_offset=(0.0, 28.0),
    )
    label_bboxes["wall_height"] = _draw_dimension(
        ctx,
        (front_a[0] - 34.0, front_e[1]),
        (front_a[0] - 34.0, front_a[1]),
        f"h={_fmt_number(problem.wall_height or 0)}",
        label_offset=(-36.0, 0.0),
    )
    label_bboxes["roof_height"] = _draw_dimension(
        ctx,
        (roof_foot[0] + 34.0, front_d[1]),
        (roof_foot[0] + 34.0, roof_foot[1]),
        f"t={_fmt_number(problem.roof_height or 0)}",
        label_offset=(34.0, 0.0),
    )
    label_bboxes["target"] = _draw_dimension(
        ctx,
        (front_b[0] + 20.0, front_b[1] + 16.0),
        (back_b[0] + 20.0, back_b[1] + 16.0),
        "L=?",
        label_offset=(34.0, 20.0),
        target=True,
    )
    bbox = _bbox_from_points(
        front_poly + back_poly,
        width=ctx.width,
        height=ctx.height,
        pad=54.0,
    )
    return bbox, label_bboxes, (
        "target_length_label",
        "volume_label",
        "triangle_base_label",
        "wall_height_label",
        "roof_height_label",
    )


def _render_solid_formula_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedSolidFormulaScene:
    if problem.query_id == "cylinder_cone_radius_from_volume_heights":
        solid_bbox, label_bboxes, annotation_roles = _draw_cylinder_cone_radius(
            ctx, problem
        )
    elif problem.query_id == "cylinder_cone_height_from_volume_radius":
        solid_bbox, label_bboxes, annotation_roles = _draw_cylinder_cone_height(
            ctx, problem
        )
    elif problem.query_id == "prism_pyramid_height_from_volume":
        solid_bbox, label_bboxes, annotation_roles = _draw_prism_pyramid(ctx, problem)
    elif problem.query_id == "house_prism_length_from_volume":
        solid_bbox, label_bboxes, annotation_roles = _draw_house_prism(ctx, problem)
    else:
        raise ValueError(f"unsupported solid-formula query_id: {problem.query_id}")

    annotation_lookup = {
        "target_radius_label": label_bboxes.get("target"),
        "target_cylinder_height_label": label_bboxes.get("target"),
        "target_prism_height_label": label_bboxes.get("target"),
        "target_length_label": label_bboxes.get("target"),
        "volume_label": label_bboxes.get("volume"),
        "height_label": label_bboxes.get("height"),
        "total_height_label": label_bboxes.get("total_height"),
        "cone_height_label": label_bboxes.get("cone_height"),
        "radius_label": label_bboxes.get("radius"),
        "surface_area_label": label_bboxes.get("surface_area"),
        "known_length_label": label_bboxes.get("side_a"),
        "known_width_label": label_bboxes.get("side_b"),
        "pyramid_height_label": label_bboxes.get("pyramid_height"),
        "triangle_base_label": label_bboxes.get("triangle_base"),
        "triangle_height_label": label_bboxes.get("triangle_height"),
        "wall_height_label": label_bboxes.get("wall_height"),
        "roof_height_label": label_bboxes.get("roof_height"),
    }
    annotation_bboxes = tuple(
        bbox
        for role in annotation_roles
        for bbox in (annotation_lookup.get(role),)
        if bbox is not None
    )
    scene_entities = (
        {
            "entity_id": "solid",
            "entity_type": str(problem.solid_kind),
            "bbox": _bbox_to_list(solid_bbox),
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "solid_kind": str(problem.solid_kind),
        "unknown_dimension": str(problem.unknown_dimension),
        "radius": None if problem.radius is None else float(problem.radius),
        "height": None if problem.height is None else float(problem.height),
        "total_height": None if problem.total_height is None else float(problem.total_height),
        "cylinder_height": None if problem.cylinder_height is None else float(problem.cylinder_height),
        "cone_height": None if problem.cone_height is None else float(problem.cone_height),
        "volume": None if problem.volume is None else float(problem.volume),
        "volume_pi_multiple": None
        if problem.volume_pi_multiple is None
        else float(problem.volume_pi_multiple),
        "surface_area": None if problem.surface_area is None else float(problem.surface_area),
        "side_a": None if problem.side_a is None else float(problem.side_a),
        "side_b": None if problem.side_b is None else float(problem.side_b),
        "side_x": None if problem.side_x is None else float(problem.side_x),
        "prism_height": None if problem.prism_height is None else float(problem.prism_height),
        "pyramid_height": None if problem.pyramid_height is None else float(problem.pyramid_height),
        "triangle_base": None
        if problem.triangle_base is None
        else float(problem.triangle_base),
        "triangle_height": None
        if problem.triangle_height is None
        else float(problem.triangle_height),
        "prism_length": None
        if problem.prism_length is None
        else float(problem.prism_length),
        "wall_height": None if problem.wall_height is None else float(problem.wall_height),
        "roof_height": None if problem.roof_height is None else float(problem.roof_height),
        "formula": str(problem.formula),
        "answer_value": float(problem.answer),
    }
    return _RenderedSolidFormulaScene(
        image=ctx.image,
        answer=float(problem.answer),
        annotation_bboxes=tuple(annotation_bboxes),
        annotation_roles=tuple(annotation_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
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


class _SolidFormulaBaseTask:
    """Shared implementation for direct solid-formula missing-dimension tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "solid_formula"

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
            ((225, 239, 255), (238, 246, 236), (27, 113, 191), (160, 176, 190)),
            ((255, 237, 222), (236, 240, 255), (189, 91, 37), (164, 150, 136)),
            ((237, 232, 255), (235, 248, 246), (111, 92, 190), (158, 152, 178)),
            ((230, 247, 235), (255, 239, 219), (30, 132, 92), (144, 168, 150)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.palette",
        )
        fill_color, secondary_fill_color, accent_color, muted_color = palettes[
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
            "muted_color": list(muted_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedSolidFormulaScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.44
            + normalize_linear(len(rendered.annotation_bboxes), min_value=4, max_value=5)
            * 0.18
        )
        precision_by_kind = {
            "cylinder_cone": 0.72,
            "prism_pyramid": 0.78,
            "house_prism": 0.80,
        }
        ambiguity_by_kind = {
            "cylinder_cone": 0.62,
            "prism_pyramid": 0.66,
            "house_prism": 0.68,
        }
        solid_kind = str(rendered.witness.get("solid_kind", "cylinder_cone"))
        output_burden = clamp_unit_interval(
            0.44
            + normalize_linear(len(rendered.annotation_bboxes), min_value=4, max_value=5)
            * 0.12
        )
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(precision_by_kind.get(solid_kind, 0.66)),
            ambiguity=float(ambiguity_by_kind.get(solid_kind, 0.54)),
            output_burden=float(output_burden),
        )

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no solid-formula query support")
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
        rendered: _RenderedSolidFormulaScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_solid_formula_scene(ctx, problem)
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
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(
                    prompt_defaults["json_output_contract_answer_only"]
                ),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(
                    prompt_defaults["json_example_answer_only"]
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_bboxes = [_bbox_to_list(bbox) for bbox in rendered.annotation_bboxes]
        annotation_points = [
            [
                round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
            ]
            for bbox in annotation_bboxes
        ]
        answer_gt = TypedValue(type="number", value=float(rendered.answer))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        query_params = {
            "scene_id": SCENE_ID,
            "scene_variant": str(problem.solid_kind),
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_solid_formula",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": str(problem.solid_kind),
                    "answer_value": float(rendered.answer),
                    "annotation_roles": list(rendered.annotation_roles),
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
                "annotation_roles": list(rendered.annotation_roles),
                "reasoning_steps": 2,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "solid_formula_missing_dimension",
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "answer_value": float(rendered.answer),
                "source_witness_type": "bbox_set",
                "original_annotation_value": list(rendered.annotation_roles),
                **dict(rendered.witness),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": list(annotation_bboxes),
                "pixel_bbox_set": list(annotation_bboxes),
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
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
class GeometrySolidFormulaCylinderConeHeightFromVolumeRadiusTask(_SolidFormulaBaseTask):
    """Compute cylinder-cone height from volume and radius."""

    task_id = "task_geometry__solid_formula__cylinder_cone_height_from_volume_radius"
    supported_queries = ("cylinder_cone_height_from_volume_radius",)
    reasoning_kind = "missing_dimension"


@register_task
class GeometrySolidFormulaCylinderConeRadiusFromVolumeHeightsTask(_SolidFormulaBaseTask):
    """Compute cylinder-cone radius from volume and heights."""

    task_id = "task_geometry__solid_formula__cylinder_cone_radius_from_volume_heights"
    supported_queries = ("cylinder_cone_radius_from_volume_heights",)
    reasoning_kind = "missing_dimension"


@register_task
class GeometrySolidFormulaHousePrismLengthFromVolumeTask(_SolidFormulaBaseTask):
    """Compute house-prism length from volume."""

    task_id = "task_geometry__solid_formula__house_prism_length_from_volume"
    supported_queries = ("house_prism_length_from_volume",)
    reasoning_kind = "missing_dimension"


@register_task
class GeometrySolidFormulaPrismPyramidHeightFromVolumeTask(_SolidFormulaBaseTask):
    """Compute prism-pyramid height from volume."""

    task_id = "task_geometry__solid_formula__prism_pyramid_height_from_volume"
    supported_queries = ("prism_pyramid_height_from_volume",)
    reasoning_kind = "missing_dimension"


__all__ = [
    "GeometrySolidFormulaCylinderConeHeightFromVolumeRadiusTask",
    "GeometrySolidFormulaCylinderConeRadiusFromVolumeHeightsTask",
    "GeometrySolidFormulaHousePrismLengthFromVolumeTask",
    "GeometrySolidFormulaPrismPyramidHeightFromVolumeTask",
    "SCENE_ID",
]
