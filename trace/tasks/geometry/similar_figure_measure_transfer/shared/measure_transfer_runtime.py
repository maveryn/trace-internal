"""Similar-figure measurement transfer tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import (
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)

SCENE_ID = "similar_figure_measure_transfer"
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.shared.fixed_query import geometry_query_ids_for_task, geometry_selected_probability_map as _probability_map
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, pad_bbox
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready as _json_ready
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.geometry.shared.vector2d import add_scaled as _add, mid as _mid, point_to_list as _point_to_list, sub as _sub, unit as _unit

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]
Side = Tuple[int, int]

PROMPT_BUNDLE_ID = "geometry_similar_figure_measure_transfer_v0"
CORRESPONDING_SIDE_OBJECTIVE = "corresponding_side_value"
SCALE_FACTOR_OBJECTIVE = "scale_factor_value"
AREA_SCALE_OBJECTIVE = "area_scale_side_length_value"

_SCENE_DEFAULTS = get_scene_defaults("geometry", "similar_figure_measure_transfer")

_CORRESPONDING_SIDE_QUERY_IDS: Tuple[str, ...] = (
    "direct_side_transfer",
    "two_pair_side_transfer",
    "nested_side_transfer",
)
_SCALE_FACTOR_QUERY_IDS: Tuple[str, ...] = (
    "scale_factor_from_side_pair",
    "scale_factor_from_perimeter_pair",
    "scale_factor_from_area_pair",
)
_AREA_SCALE_QUERY_IDS: Tuple[str, ...] = (
    "side_length_from_area_pair",
    "side_length_from_area_ratio",
    "side_length_from_area_and_known_side",
)



@dataclass(frozen=True)
class MeasureTransferArtifact:
    """Generated data needed by a public similar-figure transfer task."""

    prompt: str
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any
    image: Any
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, Any]
    query_id: str
    prompt_variants: Dict[str, Any]


@dataclass(frozen=True)
class _Case:
    query_id: str
    shape_kind: str
    layout_kind: str
    answer: int
    target_name: str
    relation: str
    scale_factor: int
    source_target_side_value: int | None = None
    target_target_side_value: int | None = None
    support_source_side_value: int | None = None
    support_target_side_value: int | None = None
    source_perimeter: int | None = None
    target_perimeter: int | None = None
    source_area: int | None = None
    target_area: int | None = None
    area_ratio_label: str | None = None
    target_side: Side = (0, 1)
    support_side: Side = (2, 3)


@dataclass(frozen=True)
class _ResolvedProblem:
    objective_key: str
    query_id: str
    case: _Case
    query_probabilities: Dict[str, float]
    case_index: int
    layout_seed: int


@dataclass
class _RenderContext:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    accent_color: Color
    source_fill: Color
    target_fill: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class _FigureGeometry:
    source_vertices: Tuple[Point, ...]
    target_vertices: Tuple[Point, ...]
    source_labels: Tuple[str, ...]
    target_labels: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    figure_geometry: _FigureGeometry
    annotation_points: Dict[str, Point]
    point_label_bboxes: Dict[str, BBox]
    readout_bboxes: Dict[str, BBox]
    construction_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]


def _default_support_side(shape_kind: str) -> Side:
    if str(shape_kind) == "triangle":
        return (1, 2)
    return (2, 3)


def _corresponding_case(
    query_id: str,
    shape_kind: str,
    layout_kind: str,
    *,
    scale_factor: int,
    source_side: int,
    support_source: int,
) -> _Case:
    return _Case(
        query_id=query_id,
        shape_kind=shape_kind,
        layout_kind=layout_kind,
        answer=int(scale_factor) * int(source_side),
        target_name="segment A'B'",
        relation="corresponding_sides_of_similar_figures",
        scale_factor=int(scale_factor),
        source_target_side_value=int(source_side),
        target_target_side_value=int(scale_factor) * int(source_side),
        support_source_side_value=int(support_source),
        support_target_side_value=int(scale_factor) * int(support_source),
        target_side=(0, 1),
        support_side=_default_support_side(shape_kind),
    )


def _scale_factor_side_case(query_id: str, shape_kind: str, layout_kind: str, *, scale_factor: int, source_side: int) -> _Case:
    return _Case(
        query_id=query_id,
        shape_kind=shape_kind,
        layout_kind=layout_kind,
        answer=int(scale_factor),
        target_name="the scale factor from the first figure to the second figure",
        relation="scale_factor_from_corresponding_side_lengths",
        scale_factor=int(scale_factor),
        support_source_side_value=int(source_side),
        support_target_side_value=int(scale_factor) * int(source_side),
        target_side=(0, 1),
        support_side=(0, 1),
    )


def _scale_factor_perimeter_case(
    query_id: str,
    shape_kind: str,
    layout_kind: str,
    *,
    scale_factor: int,
    source_perimeter: int,
) -> _Case:
    return _Case(
        query_id=query_id,
        shape_kind=shape_kind,
        layout_kind=layout_kind,
        answer=int(scale_factor),
        target_name="the scale factor from the first figure to the second figure",
        relation="scale_factor_from_perimeters",
        scale_factor=int(scale_factor),
        source_perimeter=int(source_perimeter),
        target_perimeter=int(scale_factor) * int(source_perimeter),
        target_side=(0, 1),
        support_side=(0, 1),
    )


def _scale_factor_area_case(query_id: str, shape_kind: str, layout_kind: str, *, scale_factor: int, source_area: int) -> _Case:
    return _Case(
        query_id=query_id,
        shape_kind=shape_kind,
        layout_kind=layout_kind,
        answer=int(scale_factor),
        target_name="the scale factor from the first figure to the second figure",
        relation="linear_scale_factor_from_area_scale",
        scale_factor=int(scale_factor),
        source_area=int(source_area),
        target_area=int(source_area) * int(scale_factor) * int(scale_factor),
        target_side=(0, 1),
        support_side=(0, 1),
    )


def _area_side_case(
    query_id: str,
    shape_kind: str,
    layout_kind: str,
    *,
    scale_factor: int,
    source_side: int,
    source_area: int | None = None,
) -> _Case:
    area = int(source_area if source_area is not None else max(4, source_side))
    return _Case(
        query_id=query_id,
        shape_kind=shape_kind,
        layout_kind=layout_kind,
        answer=int(scale_factor) * int(source_side),
        target_name="segment A'B'",
        relation="side_length_from_area_scale",
        scale_factor=int(scale_factor),
        source_target_side_value=int(source_side),
        target_target_side_value=int(scale_factor) * int(source_side),
        source_area=int(area),
        target_area=int(area) * int(scale_factor) * int(scale_factor),
        area_ratio_label=f"{int(scale_factor) * int(scale_factor)}:1",
        target_side=(0, 1),
        support_side=(0, 1),
    )


_CORRESPONDING_SIDE_CASES: Tuple[_Case, ...] = (
    _corresponding_case("direct_side_transfer", "quadrilateral", "side_by_side", scale_factor=2, source_side=6, support_source=5),
    _corresponding_case("direct_side_transfer", "triangle", "side_by_side", scale_factor=3, source_side=5, support_source=4),
    _corresponding_case("direct_side_transfer", "pentagon", "side_by_side", scale_factor=4, source_side=5, support_source=3),
    _corresponding_case("direct_side_transfer", "quadrilateral", "side_by_side", scale_factor=5, source_side=5, support_source=2),
    _corresponding_case("direct_side_transfer", "triangle", "side_by_side", scale_factor=6, source_side=4, support_source=3),
    _corresponding_case("two_pair_side_transfer", "pentagon", "rotated_pair", scale_factor=2, source_side=5, support_source=7),
    _corresponding_case("two_pair_side_transfer", "quadrilateral", "rotated_pair", scale_factor=3, source_side=6, support_source=5),
    _corresponding_case("two_pair_side_transfer", "triangle", "rotated_pair", scale_factor=4, source_side=7, support_source=4),
    _corresponding_case("two_pair_side_transfer", "pentagon", "rotated_pair", scale_factor=5, source_side=6, support_source=3),
    _corresponding_case("two_pair_side_transfer", "quadrilateral", "rotated_pair", scale_factor=6, source_side=6, support_source=2),
    _corresponding_case("nested_side_transfer", "triangle", "nested", scale_factor=2, source_side=8, support_source=5),
    _corresponding_case("nested_side_transfer", "quadrilateral", "nested", scale_factor=3, source_side=7, support_source=4),
    _corresponding_case("nested_side_transfer", "pentagon", "nested", scale_factor=4, source_side=6, support_source=3),
    _corresponding_case("nested_side_transfer", "triangle", "nested", scale_factor=5, source_side=5, support_source=4),
    _corresponding_case("nested_side_transfer", "quadrilateral", "nested", scale_factor=6, source_side=5, support_source=3),
)

_SCALE_FACTOR_CASES: Tuple[_Case, ...] = (
    _scale_factor_side_case("scale_factor_from_side_pair", "triangle", "side_by_side", scale_factor=2, source_side=6),
    _scale_factor_side_case("scale_factor_from_side_pair", "quadrilateral", "rotated_pair", scale_factor=3, source_side=5),
    _scale_factor_side_case("scale_factor_from_side_pair", "pentagon", "side_by_side", scale_factor=4, source_side=4),
    _scale_factor_side_case("scale_factor_from_side_pair", "triangle", "rotated_pair", scale_factor=5, source_side=3),
    _scale_factor_side_case("scale_factor_from_side_pair", "quadrilateral", "side_by_side", scale_factor=6, source_side=3),
    _scale_factor_perimeter_case("scale_factor_from_perimeter_pair", "quadrilateral", "side_by_side", scale_factor=2, source_perimeter=18),
    _scale_factor_perimeter_case("scale_factor_from_perimeter_pair", "pentagon", "rotated_pair", scale_factor=3, source_perimeter=16),
    _scale_factor_perimeter_case("scale_factor_from_perimeter_pair", "triangle", "side_by_side", scale_factor=4, source_perimeter=14),
    _scale_factor_perimeter_case("scale_factor_from_perimeter_pair", "quadrilateral", "rotated_pair", scale_factor=5, source_perimeter=12),
    _scale_factor_perimeter_case("scale_factor_from_perimeter_pair", "pentagon", "side_by_side", scale_factor=6, source_perimeter=10),
    _scale_factor_area_case("scale_factor_from_area_pair", "pentagon", "side_by_side", scale_factor=2, source_area=9),
    _scale_factor_area_case("scale_factor_from_area_pair", "triangle", "rotated_pair", scale_factor=3, source_area=4),
    _scale_factor_area_case("scale_factor_from_area_pair", "quadrilateral", "side_by_side", scale_factor=4, source_area=5),
    _scale_factor_area_case("scale_factor_from_area_pair", "pentagon", "rotated_pair", scale_factor=5, source_area=4),
    _scale_factor_area_case("scale_factor_from_area_pair", "triangle", "side_by_side", scale_factor=6, source_area=3),
)

_AREA_SCALE_CASES: Tuple[_Case, ...] = (
    _area_side_case("side_length_from_area_pair", "triangle", "side_by_side", scale_factor=2, source_side=6, source_area=9),
    _area_side_case("side_length_from_area_pair", "quadrilateral", "rotated_pair", scale_factor=3, source_side=5, source_area=4),
    _area_side_case("side_length_from_area_pair", "pentagon", "side_by_side", scale_factor=4, source_side=4, source_area=5),
    _area_side_case("side_length_from_area_pair", "triangle", "rotated_pair", scale_factor=5, source_side=5, source_area=4),
    _area_side_case("side_length_from_area_pair", "quadrilateral", "side_by_side", scale_factor=6, source_side=4, source_area=3),
    _area_side_case("side_length_from_area_ratio", "quadrilateral", "side_by_side", scale_factor=2, source_side=7, source_area=8),
    _area_side_case("side_length_from_area_ratio", "pentagon", "rotated_pair", scale_factor=3, source_side=6, source_area=6),
    _area_side_case("side_length_from_area_ratio", "triangle", "side_by_side", scale_factor=4, source_side=5, source_area=4),
    _area_side_case("side_length_from_area_ratio", "quadrilateral", "rotated_pair", scale_factor=5, source_side=5, source_area=5),
    _area_side_case("side_length_from_area_ratio", "pentagon", "side_by_side", scale_factor=6, source_side=5, source_area=3),
    _area_side_case("side_length_from_area_and_known_side", "pentagon", "nested", scale_factor=2, source_side=8, source_area=7),
    _area_side_case("side_length_from_area_and_known_side", "triangle", "nested", scale_factor=3, source_side=7, source_area=5),
    _area_side_case("side_length_from_area_and_known_side", "quadrilateral", "nested", scale_factor=4, source_side=6, source_area=4),
    _area_side_case("side_length_from_area_and_known_side", "pentagon", "nested", scale_factor=5, source_side=5, source_area=3),
    _area_side_case("side_length_from_area_and_known_side", "triangle", "nested", scale_factor=6, source_side=5, source_area=2),
)


_QUERY_IDS_BY_OBJECTIVE: Dict[str, Tuple[str, ...]] = {
    CORRESPONDING_SIDE_OBJECTIVE: _CORRESPONDING_SIDE_QUERY_IDS,
    SCALE_FACTOR_OBJECTIVE: _SCALE_FACTOR_QUERY_IDS,
    AREA_SCALE_OBJECTIVE: _AREA_SCALE_QUERY_IDS,
}


def _all_cases_for_objective(objective_key: str) -> Tuple[_Case, ...]:
    if objective_key == CORRESPONDING_SIDE_OBJECTIVE:
        return _CORRESPONDING_SIDE_CASES
    if objective_key == SCALE_FACTOR_OBJECTIVE:
        return _SCALE_FACTOR_CASES
    if objective_key == AREA_SCALE_OBJECTIVE:
        return _AREA_SCALE_CASES
    raise ValueError(f"unknown similar-figure objective: {objective_key}")


def _offset_from_segment(a: Point, b: Point, distance: float) -> Point:
    ux, uy = _unit(_sub(b, a))
    return (-uy * float(distance), ux * float(distance))


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    draw_text_traced(
        ctx.draw,
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=max(0, int(ctx.label_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    return pad_bbox(bbox, 3.0, width=ctx.width, height=ctx.height)


def _shape_template(shape_kind: str) -> Tuple[Point, ...]:
    if shape_kind == "triangle":
        return ((0.0, -1.0), (1.18, 0.78), (-1.05, 0.82))
    if shape_kind == "quadrilateral":
        return ((-1.15, -0.78), (0.82, -0.92), (1.18, 0.65), (-0.82, 0.92))
    if shape_kind == "pentagon":
        return ((0.0, -1.10), (1.05, -0.36), (0.76, 0.92), (-0.45, 1.08), (-1.16, 0.12))
    raise ValueError(f"unknown shape_kind={shape_kind!r}")


def _source_labels(shape_kind: str) -> Tuple[str, ...]:
    return tuple(chr(ord("A") + index) for index in range(len(_shape_template(shape_kind))))


def _target_labels(shape_kind: str) -> Tuple[str, ...]:
    return tuple(f"{label}'" for label in _source_labels(shape_kind))


def _transform_points(points: Sequence[Point], *, center: Point, scale: float, rotation_degrees: float) -> Tuple[Point, ...]:
    theta = math.radians(float(rotation_degrees))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    transformed: list[Point] = []
    for x, y in points:
        sx = float(x) * float(scale)
        sy = float(y) * float(scale)
        transformed.append(
            (
                float(center[0]) + (sx * cos_t) - (sy * sin_t),
                float(center[1]) + (sx * sin_t) + (sy * cos_t),
            )
        )
    return tuple(transformed)


def _figure_geometry(case: _Case, *, width: int, height: int, instance_seed: int) -> _FigureGeometry:
    rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{case.layout_kind}.{case.shape_kind}.layout")
    base = _shape_template(case.shape_kind)
    visual_scale_factor = min(1.95, 1.10 + (0.16 * float(case.scale_factor)))
    source_scale = rng.uniform(58.0, 70.0) if case.layout_kind != "nested" else rng.uniform(48.0, 58.0)
    target_scale = source_scale * visual_scale_factor
    if case.layout_kind == "nested":
        center = (float(width) / 2.0 + rng.uniform(-12.0, 12.0), float(height) / 2.0 + rng.uniform(-8.0, 12.0))
        source_center = center
        target_center = center
        source_rotation = rng.uniform(-6.0, 6.0)
        target_rotation = source_rotation
    else:
        source_center = (float(width) * 0.32 + rng.uniform(-16.0, 12.0), float(height) * 0.53 + rng.uniform(-18.0, 18.0))
        target_center = (float(width) * 0.69 + rng.uniform(-12.0, 16.0), float(height) * 0.52 + rng.uniform(-18.0, 18.0))
        source_rotation = rng.uniform(-8.0, 8.0)
        target_rotation = rng.uniform(14.0, 24.0) if case.layout_kind == "rotated_pair" else source_rotation + rng.uniform(-2.0, 2.0)
    return _FigureGeometry(
        source_vertices=_transform_points(base, center=source_center, scale=source_scale, rotation_degrees=source_rotation),
        target_vertices=_transform_points(base, center=target_center, scale=target_scale, rotation_degrees=target_rotation),
        source_labels=_source_labels(case.shape_kind),
        target_labels=_target_labels(case.shape_kind),
    )


def _draw_polygon(ctx: _RenderContext, points: Sequence[Point], *, fill: Color, outline: Color) -> BBox:
    polygon = [(float(x), float(y)) for x, y in points]
    ctx.draw.polygon(polygon, fill=fill)
    ctx.draw.line(polygon + [polygon[0]], fill=outline, width=ctx.line_width, joint="curve")
    return bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_vertex_labels(ctx: _RenderContext, points: Sequence[Point], labels: Sequence[str], *, offset: float) -> Dict[str, BBox]:
    center = (sum(point[0] for point in points) / float(len(points)), sum(point[1] for point in points) / float(len(points)))
    bboxes: Dict[str, BBox] = {}
    for label, point in zip(labels, points):
        direction = _unit(_sub(point, center))
        label_center = _add(point, direction, offset)
        bboxes[str(label)] = _draw_text_centered(ctx, str(label), label_center, small=True)
    return bboxes


def _draw_tick(ctx: _RenderContext, a: Point, b: Point, *, count: int = 1) -> BBox:
    center = _mid(a, b)
    tangent = _unit(_sub(b, a))
    normal = (-tangent[1], tangent[0])
    tick_points: list[Point] = []
    spacing = 9.0
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * spacing
        tick_center = _add(center, tangent, shift)
        p0 = _add(tick_center, normal, -9.0)
        p1 = _add(tick_center, normal, 9.0)
        ctx.draw.line((p0, p1), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        tick_points.extend([p0, p1])
    return bbox_from_points(tick_points, width=ctx.width, height=ctx.height, pad=3.0)


def _draw_side_label(ctx: _RenderContext, points: Sequence[Point], side: Side, text: str, *, offset: float) -> BBox:
    a = points[int(side[0])]
    b = points[int(side[1])]
    label_center = _add(_mid(a, b), _offset_from_segment(a, b, offset))
    return _draw_text_centered(ctx, str(text), label_center, small=True)


def _side_name(labels: Sequence[str], side: Side) -> str:
    return f"{labels[int(side[0])]}{labels[int(side[1])]}"


def _draw_caption(ctx: _RenderContext, text: str, center: Point) -> BBox:
    return _draw_text_centered(ctx, str(text), center, small=True)


def _render_problem(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    case = problem.case
    geometry = _figure_geometry(case, width=ctx.width, height=ctx.height, instance_seed=problem.layout_seed)
    construction_bboxes: Dict[str, BBox] = {}
    readout_bboxes: Dict[str, BBox] = {}
    point_label_bboxes: Dict[str, BBox] = {}

    if case.layout_kind == "nested":
        construction_bboxes["target_figure"] = _draw_polygon(ctx, geometry.target_vertices, fill=ctx.target_fill, outline=ctx.secondary_color)
        construction_bboxes["source_figure"] = _draw_polygon(ctx, geometry.source_vertices, fill=ctx.source_fill, outline=ctx.line_color)
    else:
        construction_bboxes["source_figure"] = _draw_polygon(ctx, geometry.source_vertices, fill=ctx.source_fill, outline=ctx.line_color)
        construction_bboxes["target_figure"] = _draw_polygon(ctx, geometry.target_vertices, fill=ctx.target_fill, outline=ctx.secondary_color)

    point_label_bboxes.update({f"source_{key}": value for key, value in _draw_vertex_labels(ctx, geometry.source_vertices, geometry.source_labels, offset=24.0).items()})
    point_label_bboxes.update({f"target_{key}": value for key, value in _draw_vertex_labels(ctx, geometry.target_vertices, geometry.target_labels, offset=28.0).items()})

    source_target_side = case.target_side
    target_target_side = case.target_side
    source_support_side = case.support_side
    target_support_side = case.support_side

    if case.source_target_side_value is not None:
        readout_bboxes["source_target_side_label"] = _draw_side_label(
            ctx,
            geometry.source_vertices,
            source_target_side,
            str(case.source_target_side_value),
            offset=-28.0,
        )
        readout_bboxes["target_target_side_label"] = _draw_side_label(
            ctx,
            geometry.target_vertices,
            target_target_side,
            "?" if problem.objective_key != SCALE_FACTOR_OBJECTIVE else str(case.target_target_side_value or ""),
            offset=32.0,
        )
        construction_bboxes["source_target_side_tick"] = _draw_tick(
            ctx,
            geometry.source_vertices[source_target_side[0]],
            geometry.source_vertices[source_target_side[1]],
            count=1,
        )
        construction_bboxes["target_target_side_tick"] = _draw_tick(
            ctx,
            geometry.target_vertices[target_target_side[0]],
            geometry.target_vertices[target_target_side[1]],
            count=1,
        )

    if case.support_source_side_value is not None and case.support_target_side_value is not None:
        readout_bboxes["support_source_side_label"] = _draw_side_label(
            ctx,
            geometry.source_vertices,
            source_support_side,
            str(case.support_source_side_value),
            offset=30.0,
        )
        readout_bboxes["support_target_side_label"] = _draw_side_label(
            ctx,
            geometry.target_vertices,
            target_support_side,
            str(case.support_target_side_value),
            offset=-34.0,
        )
        construction_bboxes["support_source_side_tick"] = _draw_tick(
            ctx,
            geometry.source_vertices[source_support_side[0]],
            geometry.source_vertices[source_support_side[1]],
            count=2,
        )
        construction_bboxes["support_target_side_tick"] = _draw_tick(
            ctx,
            geometry.target_vertices[target_support_side[0]],
            geometry.target_vertices[target_support_side[1]],
            count=2,
        )

    source_center = (
        sum(point[0] for point in geometry.source_vertices) / float(len(geometry.source_vertices)),
        sum(point[1] for point in geometry.source_vertices) / float(len(geometry.source_vertices)),
    )
    target_center = (
        sum(point[0] for point in geometry.target_vertices) / float(len(geometry.target_vertices)),
        sum(point[1] for point in geometry.target_vertices) / float(len(geometry.target_vertices)),
    )
    if case.source_perimeter is not None and case.target_perimeter is not None:
        readout_bboxes["source_perimeter_label"] = _draw_caption(ctx, f"perimeter = {case.source_perimeter}", _add(source_center, (0.0, 120.0)))
        readout_bboxes["target_perimeter_label"] = _draw_caption(ctx, f"perimeter = {case.target_perimeter}", _add(target_center, (0.0, 142.0)))
    if case.source_area is not None and case.target_area is not None:
        readout_bboxes["source_area_label"] = _draw_caption(ctx, f"area = {case.source_area}", _add(source_center, (0.0, 120.0)))
        if case.query_id == "side_length_from_area_ratio":
            readout_bboxes["area_ratio_label"] = _draw_caption(ctx, f"area ratio = {case.area_ratio_label}", (ctx.width / 2.0, 62.0))
        else:
            readout_bboxes["target_area_label"] = _draw_caption(ctx, f"area = {case.target_area}", _add(target_center, (0.0, 142.0)))

    annotation = {
        "target_side_start": geometry.target_vertices[target_target_side[0]],
        "target_side_end": geometry.target_vertices[target_target_side[1]],
        "source_corresponding_side_start": geometry.source_vertices[source_target_side[0]],
        "source_corresponding_side_end": geometry.source_vertices[source_target_side[1]],
    }
    if case.support_source_side_value is not None and case.support_target_side_value is not None:
        annotation.update(
            {
                "support_source_side_start": geometry.source_vertices[source_support_side[0]],
                "support_source_side_end": geometry.source_vertices[source_support_side[1]],
                "support_target_side_start": geometry.target_vertices[target_support_side[0]],
                "support_target_side_end": geometry.target_vertices[target_support_side[1]],
            }
        )
    if problem.objective_key == SCALE_FACTOR_OBJECTIVE and case.source_target_side_value is None:
        annotation = {
            "source_figure_anchor": source_center,
            "target_figure_anchor": target_center,
            "source_reference_side_start": geometry.source_vertices[source_support_side[0]],
            "source_reference_side_end": geometry.source_vertices[source_support_side[1]],
            "target_reference_side_start": geometry.target_vertices[target_support_side[0]],
            "target_reference_side_end": geometry.target_vertices[target_support_side[1]],
        }

    render_map = {
        "source_vertices": {label: _point_to_list(point) for label, point in zip(geometry.source_labels, geometry.source_vertices)},
        "target_vertices": {label: _point_to_list(point) for label, point in zip(geometry.target_labels, geometry.target_vertices)},
        "point_label_bboxes": _json_ready(point_label_bboxes),
        "readout_bboxes": _json_ready(readout_bboxes),
        "construction_bboxes": _json_ready(construction_bboxes),
    }
    return _RenderedScene(
        image=ctx.image,
        figure_geometry=geometry,
        annotation_points=annotation,
        point_label_bboxes=point_label_bboxes,
        readout_bboxes=readout_bboxes,
        construction_bboxes=construction_bboxes,
        render_map=render_map,
    )


def _select_problem(objective_key: str, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    query_ids = geometry_query_ids_for_task(
        objective_key,
        _QUERY_IDS_BY_OBJECTIVE,
        context="similar-figure",
    )
    forced_query = params.get("query_id")
    if forced_query is not None:
        query_id = str(forced_query)
        if query_id not in query_ids:
            raise ValueError(f"query_id={query_id!r} is not supported by {objective_key}")
    else:
        query_rng = spawn_rng(int(instance_seed), f"{objective_key}.query")
        query_id = query_ids[int(query_rng.randrange(len(query_ids)))]
    query_probabilities = _probability_map(query_ids, query_id if forced_query is not None else None)
    cases = tuple(case for case in _all_cases_for_objective(objective_key) if case.query_id == query_id)
    if not cases:
        raise ValueError(f"no cases for query_id={query_id!r}")
    case_rng = spawn_rng(int(instance_seed), f"{objective_key}.{query_id}.case")
    case_index = int(case_rng.randrange(len(cases)))
    return _ResolvedProblem(
        objective_key=str(objective_key),
        query_id=str(query_id),
        case=cases[case_index],
        query_probabilities=dict(query_probabilities),
        case_index=int(case_index),
        layout_seed=int(instance_seed),
    )


def _build_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", rendering_defaults.get("canvas_width", 820)))
    height = int(params.get("canvas_height", rendering_defaults.get("canvas_height", 580)))
    background, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        allow_dark=False,
        require_grid=False,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    readout_font_family = str(params.get("readout_font_family", rendering_defaults.get("readout_font_family", "roboto")))
    diagram_style_trace = dict(diagram_style_meta)
    diagram_style_trace["readout_font_family"] = readout_font_family
    return _RenderContext(
        image=image,
        draw=draw,
        width=width,
        height=height,
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        source_fill=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        target_fill=tuple(int(value) for value in diagram_style.option_fill_rgb),
        line_width=max(2, int(params.get("line_width", rendering_defaults.get("line_width", 3)))),
        label_stroke_width=max(0, min(1, int(diagram_style.label_stroke_width_px))),
        font=load_font(
            int(params.get("label_font_size", rendering_defaults.get("label_font_size", 22))),
            bold=False,
            font_family=readout_font_family,
        ),
        small_font=load_font(
            int(params.get("small_label_font_size", rendering_defaults.get("small_label_font_size", 18))),
            bold=False,
            font_family=readout_font_family,
        ),
        diagram_style_meta=diagram_style_trace,
        background_meta=dict(background_meta),
    )


def _make_prompt_examples(annotation_keys: Sequence[str], *, answer: int) -> tuple[str, str]:
    return build_keyed_point_prompt_json_examples(annotation_keys=annotation_keys, answer=int(answer))


def _answer_hint_for_objective(objective_key: str, prompt_defaults: Mapping[str, Any]) -> str:
    if objective_key == SCALE_FACTOR_OBJECTIVE:
        return str(prompt_defaults["answer_hint_integer_scale"])
    return str(prompt_defaults["answer_hint_integer_length"])


class MeasureTransferRuntime:
    """Generate artifacts for similar-figure measurement-transfer objectives."""

    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID

    def generate_artifact(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
        runtime_namespace: str,
        objective_key: str,
        query_id: str,
    ) -> MeasureTransferArtifact:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=objective_key,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                runtime_params = dict(params)
                runtime_params["query_id"] = str(query_id)
                problem = _select_problem(objective_key, int(instance_seed) + int(attempt), runtime_params)
                ctx = _build_context(
                    instance_seed=int(instance_seed) + int(attempt),
                    params=runtime_params,
                    rendering_defaults=rendering_defaults,
                )
                rendered = _render_problem(problem, ctx)
                break
            except Exception as exc:
                last_error = exc
                continue
        else:
            raise RuntimeError(f"failed to generate {runtime_namespace}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=runtime_params,
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
                "annotation_hint",
                "answer_hint_integer_length",
                "answer_hint_integer_scale",
            ),
            context=f"prompt defaults for {runtime_namespace}",
        )
        annotation_keys = tuple(rendered.annotation_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys, answer=int(problem.case.answer))
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
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
                "target_name": str(problem.case.target_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": _answer_hint_for_objective(objective_key, prompt_defaults),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {key: _point_to_list(point) for key, point in rendered.annotation_points.items()}
        source_vertices_payload = {
            label: _point_to_list(point)
            for label, point in zip(rendered.figure_geometry.source_labels, rendered.figure_geometry.source_vertices)
        }
        target_vertices_payload = {
            label: _point_to_list(point)
            for label, point in zip(rendered.figure_geometry.target_labels, rendered.figure_geometry.target_vertices)
        }
        measure_payload = {
            "scale_factor": int(problem.case.scale_factor),
            "source_target_side_value": problem.case.source_target_side_value,
            "target_target_side_value": problem.case.target_target_side_value,
            "support_source_side_value": problem.case.support_source_side_value,
            "support_target_side_value": problem.case.support_target_side_value,
            "source_perimeter": problem.case.source_perimeter,
            "target_perimeter": problem.case.target_perimeter,
            "source_area": problem.case.source_area,
            "target_area": problem.case.target_area,
            "area_ratio_label": problem.case.area_ratio_label,
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": str(self.scene_id or self.public_scene_id),
                "task_id": runtime_namespace,
                "objective_key": str(objective_key),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": "similar_figure_pair",
                        "shape_kind": str(problem.case.shape_kind),
                        "source_vertices": dict(source_vertices_payload),
                        "target_vertices": dict(target_vertices_payload),
                    },
                ],
                "relations": {
                    "type": str(problem.case.relation),
                    "query_id": str(problem.query_id),
                    "scale_factor": int(problem.case.scale_factor),
                },
            },
            "query_spec": {
                "task_id": runtime_namespace,
                "objective_key": str(objective_key),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "case_index": int(problem.case_index),
                },
            },
            "render_spec": {
                "task_id": runtime_namespace,
                "objective_key": str(objective_key),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                    "post_image_noise": dict(noise_meta),
                },
                "prompt": {
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                },
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "task_id": runtime_namespace,
                "objective_key": str(objective_key),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "shape_kind": str(problem.case.shape_kind),
                "layout_kind": str(problem.case.layout_kind),
                "target_name": str(problem.case.target_name),
                "relation": str(problem.case.relation),
                "answer": int(problem.case.answer),
                "annotation_roles": list(annotation_keys),
                **dict(measure_payload),
            },
            "witness_symbolic": {
                "task_id": runtime_namespace,
                "objective_key": str(objective_key),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_name": str(problem.case.target_name),
                "relation": str(problem.case.relation),
                "answer": int(problem.case.answer),
                **dict(measure_payload),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        return MeasureTransferArtifact(
            prompt=str(prompt_artifacts.prompt),
            answer_type="integer",
            answer_value=int(problem.case.answer),
            annotation_type="keyed_point_map",
            annotation_value=dict(annotation_value),
            image=image,
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

