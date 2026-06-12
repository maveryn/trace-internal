"""Circle/square tangent-packing measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)

SCENE_ID = "tangent_packing"
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from trace.tasks.geometry.shared.measurement_rendering import (
    round1 as _round1,
    fmt_measure as _fmt_number,
    bbox_to_list as _bbox_to_list,
    clamp_bbox as _clamp_bbox,
    pad_bbox as _pad_bbox,
    bbox_from_points as _bbox_from_points,
    draw_label as _draw_label,
)
from trace.tasks.shared.fixed_query import geometry_selected_probability_map as _selected_probability_map
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

PROMPT_BUNDLE_ID = "geometry_circle_square_tangent_packing_v0"

_SCENE_DEFAULTS = get_scene_defaults("geometry", "tangent_packing")

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

_LENGTH_QUERIES: Tuple[str, ...] = (
    "circle_in_square_radius_from_gap_area",
    "square_in_circle_side_from_gap_area",
    "two_circles_in_rectangle_radius_from_gap_area",
)
_AREA_QUERIES: Tuple[str, ...] = (
    "circle_in_square_gap_area",
    "square_in_circle_gap_area",
    "two_circles_in_rectangle_gap_area",
)


@dataclass(frozen=True)
class _Case:
    query_id: str
    radius: int

    @property
    def square_side(self) -> int:
        return 2 * int(self.radius)

    @property
    def packed_rectangle_width(self) -> int:
        return 4 * int(self.radius)

    @property
    def packed_rectangle_height(self) -> int:
        return 2 * int(self.radius)

    @property
    def inscribed_square_side(self) -> float:
        return _round1(float(self.radius) * math.sqrt(2.0))

    @property
    def circle_in_square_gap_area(self) -> float:
        r = float(self.radius)
        return _round1((2.0 * r) ** 2 - (math.pi * r * r))

    @property
    def square_in_circle_gap_area(self) -> float:
        r = float(self.radius)
        return _round1((math.pi * r * r) - (2.0 * r * r))

    @property
    def two_circles_rectangle_gap_area(self) -> float:
        r = float(self.radius)
        return _round1((4.0 * r) * (2.0 * r) - (2.0 * math.pi * r * r))


_RADII: Tuple[int, ...] = (3, 4, 5, 6, 7, 8, 9, 10, 11, 12)

_LENGTH_CASES: Tuple[_Case, ...] = tuple(
    _Case(query_id, radius)
    for query_id in _LENGTH_QUERIES
    for radius in _RADII
)

_AREA_CASES: Tuple[_Case, ...] = tuple(
    _Case(query_id, radius)
    for query_id in _AREA_QUERIES
    for radius in _RADII
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
    shaded_color: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    font: Any
    small_font: Any
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    answer: float
    case: _Case
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedTangentPackingScene:
    image: Image.Image
    answer: float
    annotation_bboxes: Tuple[BBox, ...]
    annotation_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


@dataclass(frozen=True)
class TangentPackingArtifact:
    prompt: str
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any
    image: Image.Image
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, str]
    query_id: str
    prompt_variants: Dict[str, Any]


def _union_bboxes(
    bboxes: Sequence[BBox], *, width: int, height: int, pad: float = 0.0
) -> BBox:
    if not bboxes:
        return (0.0, 0.0, 1.0, 1.0)
    return _pad_bbox(
        (
            min(bbox[0] for bbox in bboxes),
            min(bbox[1] for bbox in bboxes),
            max(bbox[2] for bbox in bboxes),
            max(bbox[3] for bbox in bboxes),
        ),
        pad,
        width=width,
        height=height,
    )


def _ellipse_bbox(center: Point, radius: float) -> BBox:
    return (
        float(center[0]) - float(radius),
        float(center[1]) - float(radius),
        float(center[0]) + float(radius),
        float(center[1]) + float(radius),
    )


def _rect_points(rect: BBox) -> Tuple[Point, Point, Point, Point]:
    return (
        (float(rect[0]), float(rect[1])),
        (float(rect[2]), float(rect[1])),
        (float(rect[2]), float(rect[3])),
        (float(rect[0]), float(rect[3])),
    )


def _closed(points: Sequence[Point]) -> list[Point]:
    if not points:
        return []
    return list(points) + [points[0]]


def _transformed_radius(ctx: _RenderContext, radius: float) -> float:
    return float(radius) * float(ctx.scene_transform.transform.scale)


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
    tick = 8.0
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length > 1e-9:
        nx = -dy / length
        ny = dx / length
        for point in (start, end):
            ctx.draw.line(
                [
                    (point[0] - nx * tick, point[1] - ny * tick),
                    (point[0] + nx * tick, point[1] + ny * tick),
                ],
                fill=draw_color,
                width=max(2, ctx.line_width - 1),
            )
    label_bbox = _draw_label(
        ctx,
        label,
        (
            (float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]),
            (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]),
        ),
        small=True,
    )
    line_bbox = _bbox_from_points((start, end), width=ctx.width, height=ctx.height, pad=10.0)
    return _union_bboxes((line_bbox, label_bbox), width=ctx.width, height=ctx.height)


def _answer_for_case(case: _Case, *, answer_kind: str) -> float:
    if case.query_id == "circle_in_square_radius_from_side":
        return float(case.radius)
    if case.query_id == "circle_in_square_radius_from_gap_area":
        return float(case.radius)
    if case.query_id == "square_in_circle_side_from_radius":
        return float(case.inscribed_square_side)
    if case.query_id == "square_in_circle_side_from_gap_area":
        return float(case.inscribed_square_side)
    if case.query_id == "two_circles_in_rectangle_radius_from_width":
        return float(case.radius)
    if case.query_id == "two_circles_in_rectangle_radius_from_gap_area":
        return float(case.radius)
    if case.query_id == "circle_in_square_gap_area":
        return float(case.circle_in_square_gap_area)
    if case.query_id == "square_in_circle_gap_area":
        return float(case.square_in_circle_gap_area)
    if case.query_id == "two_circles_in_rectangle_gap_area":
        return float(case.two_circles_rectangle_gap_area)
    raise ValueError(f"unsupported tangent-packing query_id: {case.query_id}")


def _resolve_problem(
    *,
    runtime_namespace: str,
    supported_queries: Sequence[str],
    cases: Sequence[_Case],
    instance_seed: int,
    params: Mapping[str, Any],
    answer_kind: str,
) -> _ResolvedProblem:
    if not cases:
        raise ValueError(f"{runtime_namespace} defines no tangent-packing cases")
    explicit_query_raw = params.get("query_id")
    if explicit_query_raw is not None:
        query_id = str(explicit_query_raw)
        if query_id not in set(supported_queries):
            raise ValueError(f"unsupported query_id for {runtime_namespace}: {query_id}")
        query_probabilities = {query_id: 1.0}
    else:
        query_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{runtime_namespace}.query_id",
        )
        query_id = str(tuple(supported_queries)[int(query_index) % len(tuple(supported_queries))])
        query_probabilities = {
            str(value): 1.0 / float(len(tuple(supported_queries)))
            for value in tuple(supported_queries)
        }

    query_cases = tuple(case for case in cases if case.query_id == query_id)
    if not query_cases:
        raise ValueError(f"{runtime_namespace} has no cases for query_id {query_id}")
    case_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime_namespace}.{query_id}.case",
    )
    case = query_cases[int(case_index) % len(query_cases)]
    if int(case.radius) <= 0:
        raise ValueError("circle/square tangent-packing radius must be positive")

    answer = _answer_for_case(case, answer_kind=str(answer_kind))
    support_values = tuple(_answer_for_case(candidate, answer_kind=str(answer_kind)) for candidate in cases)
    return _ResolvedProblem(
        query_id=str(query_id),
        answer=float(answer),
        case=case,
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(float(value) for value in support_values))),
            float(answer),
            key_fn=_fmt_number,
            is_selected=lambda value, selected: abs(float(value) - float(selected)) <= 1e-9,
        ),
    )


def _circle_in_square_geometry() -> tuple[BBox, Point, float]:
    square = (185.0, 125.0, 485.0, 425.0)
    center = (335.0, 275.0)
    radius = 150.0
    return square, center, radius


def _square_in_circle_geometry() -> tuple[Point, float, Tuple[Point, ...]]:
    center = (350.0, 280.0)
    radius = 170.0
    square = (
        (350.0, 110.0),
        (520.0, 280.0),
        (350.0, 450.0),
        (180.0, 280.0),
    )
    return center, radius, square


def _two_circles_geometry() -> tuple[BBox, Point, Point, float]:
    rect = (110.0, 160.0, 670.0, 440.0)
    radius = 140.0
    return rect, (250.0, 300.0), (530.0, 300.0), radius


def _render_circle_in_square(
    ctx: _RenderContext, problem: _ResolvedProblem, *, answer_kind: str
) -> _RenderedTangentPackingScene:
    case = problem.case
    square, center_raw, radius_raw = _circle_in_square_geometry()
    circle_extents = (
        (center_raw[0] - radius_raw, center_raw[1]),
        (center_raw[0] + radius_raw, center_raw[1]),
        (center_raw[0], center_raw[1] - radius_raw),
        (center_raw[0], center_raw[1] + radius_raw),
    )
    label_anchors = (
        (580.0, 104.0),
        (560.0, 274.0),
        (590.0, 104.0),
        (square[0], square[3] + 26.0),
        (square[2], square[3] + 26.0),
    )
    ctx.scene_transform.resolve(_rect_points(square) + circle_extents + label_anchors)
    square_points = ctx.scene_transform.points(_rect_points(square))
    center = ctx.scene_transform.point(center_raw)
    radius_px = _transformed_radius(ctx, radius_raw)
    circle_bbox = _ellipse_bbox(center, radius_px)
    label_bboxes: Dict[str, BBox] = {}
    uses_gap_area = problem.query_id in {
        "circle_in_square_gap_area",
        "circle_in_square_radius_from_gap_area",
    }
    if uses_gap_area:
        ctx.draw.polygon(square_points, fill=ctx.shaded_color)
        ctx.draw.ellipse(circle_bbox, fill=ctx.fill_color)
    else:
        ctx.draw.polygon(square_points, fill=ctx.fill_color)
        ctx.draw.ellipse(circle_bbox, outline=ctx.accent_color, width=ctx.line_width)
    ctx.draw.line(_closed(square_points), fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ctx.draw.ellipse(circle_bbox, outline=ctx.accent_color, width=ctx.line_width)
    supporting: list[BBox] = []
    if problem.query_id == "circle_in_square_radius_from_gap_area":
        label_bboxes["shaded_area"] = _draw_label(
            ctx,
            f"shaded area={_fmt_number(case.circle_in_square_gap_area)}",
            ctx.scene_transform.point((580.0, 104.0)),
            small=True,
        )
        supporting.append(label_bboxes["shaded_area"])
        radius_endpoint = ctx.scene_transform.point((center_raw[0] + radius_raw, center_raw[1]))
        ctx.draw.line([center, radius_endpoint], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        label_bboxes["target"] = _draw_label(ctx, "r=?", ctx.scene_transform.point((560.0, 274.0)), small=True)
        target_role = "target_radius_cue"
        formula = "radius = sqrt(shaded area / (4 - pi))"
    elif answer_kind == "length":
        label_bboxes["square_side"] = _draw_dimension(
            ctx,
            ctx.scene_transform.point((square[0], square[3] + 26.0)),
            ctx.scene_transform.point((square[2], square[3] + 26.0)),
            f"side={case.square_side}",
            label_offset=(0.0, 0.0),
        )
        supporting.append(label_bboxes["square_side"])
        radius_endpoint = ctx.scene_transform.point((center_raw[0] + radius_raw, center_raw[1]))
        ctx.draw.line([center, radius_endpoint], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        label_bboxes["target"] = _draw_label(ctx, "r=?", ctx.scene_transform.point((560.0, 274.0)), small=True)
        target_role = "target_radius_cue"
        formula = "radius = square side / 2"
    else:
        label_bboxes["square_side"] = _draw_dimension(
            ctx,
            ctx.scene_transform.point((square[0], square[3] + 26.0)),
            ctx.scene_transform.point((square[2], square[3] + 26.0)),
            f"side={case.square_side}",
            label_offset=(0.0, 0.0),
        )
        supporting.append(label_bboxes["square_side"])
        label_bboxes["target"] = _draw_label(ctx, "shaded area=?", ctx.scene_transform.point((590.0, 104.0)), small=True)
        target_role = "target_shaded_area_cue"
        formula = "shaded area = square area - circle area"
    scene_bbox = _bbox_from_points(
        square_points,
        width=ctx.width,
        height=ctx.height,
        pad=10.0,
    )
    shaded_bbox = scene_bbox
    support_bbox = _union_bboxes(supporting, width=ctx.width, height=ctx.height, pad=4.0)
    witness = {
        "formula_family": str(problem.query_id),
        "scene_variant": "circle_in_square",
        "radius": int(case.radius),
        "square_side": int(case.square_side),
        "container_width": int(case.square_side),
        "container_height": int(case.square_side),
        "inscribed_square_side": float(case.inscribed_square_side),
        "formula": formula,
        "answer_value": float(problem.answer),
    }
    return _build_rendered_scene(
        ctx=ctx,
        rendered_image=ctx.image,
        answer=float(problem.answer),
        target_bbox=label_bboxes["target"],
        scene_bbox=scene_bbox,
        support_bbox=support_bbox,
        target_role=target_role,
        scene_role="circle_tangent_inside_square",
        support_role="supporting_visible_labels",
        label_bboxes=label_bboxes,
        scene_entities=(
            {
                "entity_id": "square_container",
                "entity_type": "square",
                "bbox": _bbox_to_list(scene_bbox),
            },
            {
                "entity_id": "inscribed_circle",
                "entity_type": "circle",
                "bbox": _bbox_to_list(_pad_bbox(circle_bbox, 4.0, width=ctx.width, height=ctx.height)),
                "center": [round(center[0], 3), round(center[1], 3)],
                "radius_px": round(radius_px, 3),
            },
        ),
        render_map={
            "scene_variant": "circle_in_square",
            "square_bbox": _bbox_to_list(scene_bbox),
            "circle_bbox": _bbox_to_list(_pad_bbox(circle_bbox, 4.0, width=ctx.width, height=ctx.height)),
            "shaded_region_bbox": _bbox_to_list(shaded_bbox),
        },
        witness=witness,
    )


def _render_square_in_circle(
    ctx: _RenderContext, problem: _ResolvedProblem, *, answer_kind: str
) -> _RenderedTangentPackingScene:
    case = problem.case
    center_raw, radius_raw, square_points_raw = _square_in_circle_geometry()
    ctx.scene_transform.resolve(
        tuple(square_points_raw)
        + (
            (center_raw[0] - radius_raw, center_raw[1]),
            (center_raw[0] + radius_raw, center_raw[1]),
            (center_raw[0], center_raw[1] - radius_raw),
            (center_raw[0], center_raw[1] + radius_raw),
            (575.0, 104.0),
            (570.0, 454.0),
            (440.0, 252.0),
        )
    )
    center = ctx.scene_transform.point(center_raw)
    radius_px = _transformed_radius(ctx, radius_raw)
    square_points = ctx.scene_transform.points(square_points_raw)
    circle_bbox = _ellipse_bbox(center, radius_px)
    label_bboxes: Dict[str, BBox] = {}
    uses_gap_area = problem.query_id in {
        "square_in_circle_gap_area",
        "square_in_circle_side_from_gap_area",
    }
    if uses_gap_area:
        ctx.draw.ellipse(circle_bbox, fill=ctx.shaded_color)
        ctx.draw.polygon(square_points, fill=ctx.fill_color)
    else:
        ctx.draw.ellipse(circle_bbox, fill=ctx.fill_color)
    ctx.draw.ellipse(circle_bbox, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.line(_closed(square_points), fill=ctx.accent_color, width=ctx.line_width, joint="curve")
    radius_endpoint = ctx.scene_transform.point((center_raw[0] + radius_raw, center_raw[1]))
    ctx.draw.line([center, radius_endpoint], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    supporting: list[BBox] = []
    if problem.query_id == "square_in_circle_side_from_gap_area":
        label_bboxes["shaded_area"] = _draw_label(
            ctx,
            f"shaded area={_fmt_number(case.square_in_circle_gap_area)}",
            ctx.scene_transform.point((575.0, 104.0)),
            small=True,
        )
        supporting.append(label_bboxes["shaded_area"])
        label_bboxes["target"] = _draw_label(ctx, "square side=?", ctx.scene_transform.point((570.0, 454.0)), small=True)
        target_role = "target_square_side_cue"
        formula = "inscribed square side = sqrt(2 * shaded area / (pi - 2))"
    elif answer_kind == "length":
        label_bboxes["radius"] = _draw_label(ctx, f"r={case.radius}", ctx.scene_transform.point((440.0, 252.0)), small=True)
        supporting.append(label_bboxes["radius"])
        label_bboxes["target"] = _draw_label(ctx, "square side=?", ctx.scene_transform.point((570.0, 454.0)), small=True)
        target_role = "target_square_side_cue"
        formula = "inscribed square side = radius * sqrt(2)"
    else:
        label_bboxes["radius"] = _draw_label(ctx, f"r={case.radius}", ctx.scene_transform.point((440.0, 252.0)), small=True)
        supporting.append(label_bboxes["radius"])
        label_bboxes["target"] = _draw_label(ctx, "shaded area=?", ctx.scene_transform.point((575.0, 104.0)), small=True)
        target_role = "target_shaded_area_cue"
        formula = "shaded area = circle area - inscribed square area"
    scene_bbox = _pad_bbox(circle_bbox, 10.0, width=ctx.width, height=ctx.height)
    support_bbox = _union_bboxes(supporting, width=ctx.width, height=ctx.height, pad=4.0)
    witness = {
        "formula_family": str(problem.query_id),
        "scene_variant": "square_in_circle",
        "radius": int(case.radius),
        "square_side": int(case.square_side),
        "container_width": int(case.square_side),
        "container_height": int(case.square_side),
        "inscribed_square_side": float(case.inscribed_square_side),
        "formula": formula,
        "answer_value": float(problem.answer),
    }
    return _build_rendered_scene(
        ctx=ctx,
        rendered_image=ctx.image,
        answer=float(problem.answer),
        target_bbox=label_bboxes["target"],
        scene_bbox=scene_bbox,
        support_bbox=support_bbox,
        target_role=target_role,
        scene_role="square_tangent_inside_circle",
        support_role="supporting_visible_labels",
        label_bboxes=label_bboxes,
        scene_entities=(
            {
                "entity_id": "circle_container",
                "entity_type": "circle",
                "bbox": _bbox_to_list(scene_bbox),
                "center": [round(center[0], 3), round(center[1], 3)],
                "radius_px": round(radius_px, 3),
            },
            {
                "entity_id": "inscribed_square",
                "entity_type": "square",
                "bbox": _bbox_to_list(_bbox_from_points(square_points, width=ctx.width, height=ctx.height, pad=4.0)),
                "points": [[round(x, 3), round(y, 3)] for x, y in square_points],
            },
        ),
        render_map={
            "scene_variant": "square_in_circle",
            "circle_bbox": _bbox_to_list(scene_bbox),
            "square_points": [[round(x, 3), round(y, 3)] for x, y in square_points],
        },
        witness=witness,
    )


def _render_two_circles_rectangle(
    ctx: _RenderContext, problem: _ResolvedProblem, *, answer_kind: str
) -> _RenderedTangentPackingScene:
    case = problem.case
    rect, c1_raw, c2_raw, radius_raw = _two_circles_geometry()
    ctx.scene_transform.resolve(
        _rect_points(rect)
        + (
            (c1_raw[0] - radius_raw, c1_raw[1]),
            (c1_raw[0] + radius_raw, c1_raw[1]),
            (c1_raw[0], c1_raw[1] - radius_raw),
            (c1_raw[0], c1_raw[1] + radius_raw),
            (c2_raw[0] - radius_raw, c2_raw[1]),
            (c2_raw[0] + radius_raw, c2_raw[1]),
            (c2_raw[0], c2_raw[1] - radius_raw),
            (c2_raw[0], c2_raw[1] + radius_raw),
            (570.0, 112.0),
            (250.0, 262.0),
            (rect[0], rect[3] + 26.0),
            (rect[2], rect[3] + 26.0),
        )
    )
    rect_points = ctx.scene_transform.points(_rect_points(rect))
    c1 = ctx.scene_transform.point(c1_raw)
    c2 = ctx.scene_transform.point(c2_raw)
    radius_px = _transformed_radius(ctx, radius_raw)
    circle1_bbox = _ellipse_bbox(c1, radius_px)
    circle2_bbox = _ellipse_bbox(c2, radius_px)
    label_bboxes: Dict[str, BBox] = {}
    uses_gap_area = problem.query_id in {
        "two_circles_in_rectangle_gap_area",
        "two_circles_in_rectangle_radius_from_gap_area",
    }
    if uses_gap_area:
        ctx.draw.polygon(rect_points, fill=ctx.shaded_color)
        ctx.draw.ellipse(circle1_bbox, fill=ctx.fill_color)
        ctx.draw.ellipse(circle2_bbox, fill=ctx.fill_color)
    else:
        ctx.draw.polygon(rect_points, fill=ctx.fill_color)
    ctx.draw.line(_closed(rect_points), fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ctx.draw.ellipse(circle1_bbox, outline=ctx.accent_color, width=ctx.line_width)
    ctx.draw.ellipse(circle2_bbox, outline=ctx.accent_color, width=ctx.line_width)
    ctx.draw.line([c1, ctx.scene_transform.point((c1_raw[0] + radius_raw, c1_raw[1]))], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    supporting: list[BBox] = []
    if problem.query_id == "two_circles_in_rectangle_radius_from_gap_area":
        label_bboxes["shaded_area"] = _draw_label(
            ctx,
            f"shaded area={_fmt_number(case.two_circles_rectangle_gap_area)}",
            ctx.scene_transform.point((570.0, 112.0)),
            small=True,
        )
        supporting.append(label_bboxes["shaded_area"])
        label_bboxes["target"] = _draw_label(ctx, "r=?", ctx.scene_transform.point((250.0, 262.0)), small=True)
        target_role = "target_radius_cue"
        formula = "radius = sqrt(shaded area / (8 - 2*pi))"
    elif answer_kind == "length":
        label_bboxes["width"] = _draw_dimension(
            ctx,
            ctx.scene_transform.point((rect[0], rect[3] + 26.0)),
            ctx.scene_transform.point((rect[2], rect[3] + 26.0)),
            f"width={case.packed_rectangle_width}",
            label_offset=(0.0, 0.0),
        )
        supporting.append(label_bboxes["width"])
        label_bboxes["target"] = _draw_label(ctx, "r=?", ctx.scene_transform.point((250.0, 262.0)), small=True)
        target_role = "target_radius_cue"
        formula = "radius = rectangle width / 4"
    else:
        label_bboxes["width"] = _draw_dimension(
            ctx,
            ctx.scene_transform.point((rect[0], rect[3] + 26.0)),
            ctx.scene_transform.point((rect[2], rect[3] + 26.0)),
            f"width={case.packed_rectangle_width}",
            label_offset=(0.0, 0.0),
        )
        supporting.append(label_bboxes["width"])
        label_bboxes["target"] = _draw_label(ctx, "shaded area=?", ctx.scene_transform.point((570.0, 112.0)), small=True)
        target_role = "target_shaded_area_cue"
        formula = "shaded area = rectangle area - areas of two equal circles"
    scene_bbox = _bbox_from_points(
        rect_points,
        width=ctx.width,
        height=ctx.height,
        pad=10.0,
    )
    support_bbox = _union_bboxes(supporting, width=ctx.width, height=ctx.height, pad=4.0)
    witness = {
        "formula_family": str(problem.query_id),
        "scene_variant": "two_circles_in_rectangle",
        "radius": int(case.radius),
        "square_side": int(case.square_side),
        "container_width": int(case.packed_rectangle_width),
        "container_height": int(case.packed_rectangle_height),
        "inscribed_square_side": float(case.inscribed_square_side),
        "formula": formula,
        "answer_value": float(problem.answer),
    }
    return _build_rendered_scene(
        ctx=ctx,
        rendered_image=ctx.image,
        answer=float(problem.answer),
        target_bbox=label_bboxes["target"],
        scene_bbox=scene_bbox,
        support_bbox=support_bbox,
        target_role=target_role,
        scene_role="two_equal_circles_tangent_inside_rectangle",
        support_role="supporting_visible_labels",
        label_bboxes=label_bboxes,
        scene_entities=(
            {
                "entity_id": "rectangle_container",
                "entity_type": "rectangle",
                "bbox": _bbox_to_list(scene_bbox),
            },
            {
                "entity_id": "left_circle",
                "entity_type": "circle",
                "bbox": _bbox_to_list(_pad_bbox(circle1_bbox, 4.0, width=ctx.width, height=ctx.height)),
                "center": [round(c1[0], 3), round(c1[1], 3)],
                "radius_px": round(radius_px, 3),
            },
            {
                "entity_id": "right_circle",
                "entity_type": "circle",
                "bbox": _bbox_to_list(_pad_bbox(circle2_bbox, 4.0, width=ctx.width, height=ctx.height)),
                "center": [round(c2[0], 3), round(c2[1], 3)],
                "radius_px": round(radius_px, 3),
            },
        ),
        render_map={
            "scene_variant": "two_circles_in_rectangle",
            "rectangle_bbox": _bbox_to_list(scene_bbox),
            "circle_bboxes": [
                _bbox_to_list(_pad_bbox(circle1_bbox, 4.0, width=ctx.width, height=ctx.height)),
                _bbox_to_list(_pad_bbox(circle2_bbox, 4.0, width=ctx.width, height=ctx.height)),
            ],
        },
        witness=witness,
    )


def _build_rendered_scene(
    *,
    ctx: _RenderContext,
    rendered_image: Image.Image,
    answer: float,
    target_bbox: BBox,
    scene_bbox: BBox,
    support_bbox: BBox,
    target_role: str,
    scene_role: str,
    support_role: str,
    label_bboxes: Dict[str, BBox],
    scene_entities: Tuple[Dict[str, Any], ...],
    render_map: Dict[str, Any],
    witness: Dict[str, Any],
) -> _RenderedTangentPackingScene:
    annotation_roles = (target_role, scene_role, support_role)
    annotation_bboxes = (target_bbox, scene_bbox, support_bbox)
    return _RenderedTangentPackingScene(
        image=rendered_image,
        answer=float(answer),
        annotation_bboxes=tuple(annotation_bboxes),
        annotation_roles=tuple(annotation_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=tuple(scene_entities),
        render_map={
            "coord_space": "pixel",
            "label_bboxes": {key: _bbox_to_list(value) for key, value in label_bboxes.items()},
            **dict(render_map),
        },
        witness=dict(witness),
    )


def _render_tangent_packing_scene(
    ctx: _RenderContext, problem: _ResolvedProblem, *, answer_kind: str
) -> _RenderedTangentPackingScene:
    if problem.query_id in {
        "circle_in_square_radius_from_side",
        "circle_in_square_radius_from_gap_area",
        "circle_in_square_gap_area",
    }:
        return _render_circle_in_square(ctx, problem, answer_kind=answer_kind)
    if problem.query_id in {
        "square_in_circle_side_from_radius",
        "square_in_circle_side_from_gap_area",
        "square_in_circle_gap_area",
    }:
        return _render_square_in_circle(ctx, problem, answer_kind=answer_kind)
    if problem.query_id in {
        "two_circles_in_rectangle_radius_from_width",
        "two_circles_in_rectangle_radius_from_gap_area",
        "two_circles_in_rectangle_gap_area",
    }:
        return _render_two_circles_rectangle(ctx, problem, answer_kind=answer_kind)
    raise ValueError(f"unsupported tangent-packing query_id: {problem.query_id}")


class TangentPackingRuntime:
    """Scene-local runtime for tangent-packing diagrams."""

    domain = "geometry"

    def _make_render_context(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
        runtime_namespace: str,
    ) -> tuple[_RenderContext, Dict[str, Any]]:
        rng = spawn_rng(int(instance_seed), f"{runtime_namespace}.render")
        width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 780)))
        height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
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
            ((229, 240, 255), (247, 222, 186), (26, 123, 185), (126, 143, 156)),
            ((236, 247, 232), (255, 224, 210), (38, 143, 104), (150, 142, 132)),
            ((248, 238, 252), (226, 242, 255), (123, 95, 190), (143, 154, 172)),
            ((255, 244, 224), (226, 240, 255), (196, 102, 44), (132, 146, 160)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{runtime_namespace}.palette",
        )
        fill_color, shaded_color, accent_color, muted_color = palettes[int(palette_index) % len(palettes)]
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
        line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
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
            shaded_color=shaded_color,
            accent_color=accent_color,
            muted_color=muted_color,
            line_width=max(2, int(line_width)),
            font=load_font(max(12, int(font_size)), bold=True),
            small_font=load_font(max(10, int(small_font_size)), bold=True),
            scene_transform=LazySceneTransform(
                rng,
                params=params,
                render_defaults=render_defaults,
                canvas_width=int(width),
                canvas_height=int(height),
            ),
        )
        return ctx, {
            "background_style": dict(background_meta),
            "shape_style": shape_style.to_trace_dict(),
            "line_width": int(ctx.line_width),
            "label_font_size": int(font_size),
            "small_label_font_size": int(small_font_size),
            "fill_color": list(fill_color),
            "shaded_color": list(shaded_color),
            "accent_color": list(accent_color),
            "muted_color": list(muted_color),
        }


    def generate_artifact(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
        runtime_namespace: str,
        supported_queries: Sequence[str],
        cases: Sequence[_Case],
        answer_kind: str,
    ) -> TangentPackingArtifact:
        if not supported_queries:
            raise ValueError(f"{runtime_namespace} defines no tangent-packing query support")
        _gen_defaults, render_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=str(runtime_namespace),
        )
        problem = _resolve_problem(
            runtime_namespace=str(runtime_namespace),
            supported_queries=tuple(supported_queries),
            cases=tuple(cases),
            instance_seed=int(instance_seed),
            params=params,
            answer_kind=str(answer_kind),
        )
        last_error: Exception | None = None
        rendered: _RenderedTangentPackingScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                    runtime_namespace=str(runtime_namespace),
                )
                rendered = _render_tangent_packing_scene(ctx, problem, answer_kind=str(answer_kind))
                render_meta = dict(render_meta_attempt)
                render_meta["single_object_scene_rotation"] = ctx.scene_transform.metadata()
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or render_meta is None:
            raise RuntimeError(f"failed to generate {runtime_namespace}") from last_error

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
            context=f"prompt defaults for {runtime_namespace}",
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
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

        annotation_bboxes = [_bbox_to_list(bbox) for bbox in rendered.annotation_bboxes]
        annotation_points = [
            [
                round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
            ]
            for bbox in annotation_bboxes
        ]
        query_params = {
            "scene_id": SCENE_ID,
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_circle_square_tangent_packing",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "answer_value": float(rendered.answer),
                    "annotation_roles": list(rendered.annotation_roles),
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
            "render_map": {"coord_space": "pixel", **dict(rendered.render_map)},
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "one_decimal",
                "annotation_roles": list(rendered.annotation_roles),
                "reasoning_steps": 2 if str(answer_kind) == "area" else 1,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "circle_square_tangent_packing_formula",
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
        return TangentPackingArtifact(
            prompt=str(prompt_artifacts.prompt),
            answer_type="number",
            answer_value=float(rendered.answer),
            annotation_type="bbox_set",
            annotation_value=list(annotation_bboxes),
            image=image,
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "_AREA_CASES",
    "_LENGTH_CASES",
    "SCENE_ID",
    "TangentPackingArtifact",
    "TangentPackingRuntime",
]
