"""Parallel segment proportion scene construction and rendering helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

SCENE_ID = "parallel_segment_proportion"
from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.shared.fixed_query import geometry_selected_probability_map as _probability_map
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, bbox_to_list as _bbox_to_list, pad_bbox
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready as _json_ready
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import (
    add_scaled as _add,
    mid as _mid,
    point_to_list as _point_to_list,
    sub as _sub,
    unit as _unit,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]
Side = Tuple[int, int]
PROMPT_BUNDLE_ID = "geometry_geo3k_marked_equations_v0"
SIMILAR_SCENE_ID = "similar_figure_measure_transfer"
MARKED_POLYGON_SCENE_ID = "parallel_segment_proportion"
PARALLEL_SCENE_ID = "parallel_segment_proportion"

SIMILAR_VARIABLE_TASK_KEY = "similar_variable_value"
SIMILAR_SIDE_LENGTH_TASK_KEY = "similar_side_length_from_expression_value"
MARKED_SIDE_VARIABLE_TASK_KEY = "marked_side_variable_value"
MARKED_ANGLE_VARIABLE_TASK_KEY = "marked_angle_variable_value"
MARKED_SIDE_LENGTH_TASK_KEY = "marked_side_length_value"
MARKED_ANGLE_VALUE_TASK_KEY = "marked_angle_value"
PARALLEL_VARIABLE_TASK_KEY = "parallel_variable_value"
PARALLEL_SEGMENT_LENGTH_TASK_KEY = "parallel_segment_length_value"

DEGREE_SYMBOL = chr(176)
_SCENE_DEFAULTS = get_scene_defaults("geometry", "parallel_segment_proportion")

_QUERY_IDS_BY_TASK: Dict[str, Tuple[str, ...]] = {
    SIMILAR_VARIABLE_TASK_KEY: (
        "similar_triangles_side_ratio_variable",
        "similar_polygons_side_ratio_variable",
        "two_expression_side_ratio_variable",
    ),
    SIMILAR_SIDE_LENGTH_TASK_KEY: (
        "similar_triangles_target_side_from_expression",
        "similar_polygons_target_side_from_expression",
    ),
    MARKED_SIDE_VARIABLE_TASK_KEY: (
        "isosceles_triangle_equal_side_variable",
        "equilateral_triangle_equal_side_variable",
        "marked_polygon_equal_side_variable",
        "isosceles_altitude_base_split_variable",
    ),
    MARKED_ANGLE_VARIABLE_TASK_KEY: (
        "marked_equal_angles_variable",
        "isosceles_triangle_base_angle_variable",
        "equilateral_median_right_angle_variable",
    ),
    MARKED_SIDE_LENGTH_TASK_KEY: (
        "isosceles_triangle_side_from_expression",
        "equilateral_triangle_side_from_expression",
        "marked_polygon_side_from_expression",
        "equilateral_median_side_length_from_expression",
    ),
    MARKED_ANGLE_VALUE_TASK_KEY: (
        "marked_equal_angle_from_expression",
        "isosceles_triangle_angle_from_expression",
    ),
    PARALLEL_VARIABLE_TASK_KEY: (
        "triangle_side_splitter_variable",
        "parallel_transversal_segment_variable",
    ),
    PARALLEL_SEGMENT_LENGTH_TASK_KEY: (
        "triangle_side_splitter_segment_length",
        "parallel_transversal_segment_length",
    ),
}


@dataclass(frozen=True)
class _Case:
    scene_id: str
    task_id: str
    query_id: str
    draw_kind: str
    answer: float
    target_name: str
    variable_name: str = "x"
    shape_kind: str = ""
    relation: str = ""
    labels: Mapping[str, str] | None = None
    measures: Mapping[str, float] | None = None


@dataclass(frozen=True)
class _ResolvedProblem:
    task_id: str
    scene_id: str
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
    fill_color: Color
    alt_fill_color: Color
    muted_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_points: Dict[str, Point]
    render_map: Dict[str, Any]


def _num(value: float) -> float | int:
    rounded = round(float(value), 1)
    if abs(rounded - round(rounded)) < 1e-9:
        return int(round(rounded))
    return float(rounded)


def _offset_from_segment(a: Point, b: Point, distance: float) -> Point:
    ux, uy = _unit(_sub(b, a))
    return (-uy * float(distance), ux * float(distance))


def _line_bbox(points: Sequence[Point], ctx: _RenderContext, pad: float = 5.0) -> BBox:
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=pad)


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


def _draw_point_label(ctx: _RenderContext, label: str, point: Point, direction: Point, *, offset: float = 22.0) -> BBox:
    return _draw_text_centered(ctx, label, _add(point, _unit(direction), offset), small=True)


def _draw_side_label(ctx: _RenderContext, points: Sequence[Point], side: Side, text: str, *, offset: float) -> BBox:
    a = points[int(side[0])]
    b = points[int(side[1])]
    return _draw_text_centered(ctx, str(text), _add(_mid(a, b), _offset_from_segment(a, b, offset)), small=True)


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
    return _line_bbox(tick_points, ctx, pad=4.0)


def _draw_parallel_mark(ctx: _RenderContext, a: Point, b: Point, *, count: int = 1) -> BBox:
    center = _mid(a, b)
    tangent = _unit(_sub(b, a))
    normal = _offset_from_segment(a, b, 1.0)
    mark_points: list[Point] = []
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * 14.0
        mark_center = _add(center, tangent, shift)
        base = _add(mark_center, normal, -8.0)
        tip = _add(mark_center, normal, 8.0)
        left = _add(base, tangent, -5.0)
        right = _add(base, tangent, 5.0)
        ctx.draw.line((left, tip, right), fill=ctx.accent_color, width=max(2, ctx.line_width - 1), joint="curve")
        mark_points.extend([left, tip, right])
    return _line_bbox(mark_points, ctx, pad=4.0)


def _draw_angle_arc(ctx: _RenderContext, vertex: Point, ray_a: Point, ray_b: Point, *, radius: float = 34.0, count: int = 1) -> BBox:
    va = _unit(_sub(ray_a, vertex))
    vb = _unit(_sub(ray_b, vertex))
    angle_a = math.atan2(va[1], va[0])
    angle_b = math.atan2(vb[1], vb[0])
    delta = (angle_b - angle_a) % (2.0 * math.pi)
    if delta > math.pi:
        angle_a, angle_b = angle_b, angle_a
        delta = (angle_b - angle_a) % (2.0 * math.pi)
    points: list[Point] = []
    for arc_index in range(int(count)):
        r = float(radius) + arc_index * 8.0
        last: Point | None = None
        for step in range(17):
            t = float(step) / 16.0
            theta = angle_a + delta * t
            point = (vertex[0] + math.cos(theta) * r, vertex[1] + math.sin(theta) * r)
            if last is not None:
                ctx.draw.line((last, point), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
            last = point
            points.append(point)
    return _line_bbox(points, ctx, pad=5.0)


def _draw_right_angle_marker(ctx: _RenderContext, vertex: Point, ray_a: Point, ray_b: Point, *, size: float = 20.0) -> BBox:
    u = _unit(_sub(ray_a, vertex))
    v = _unit(_sub(ray_b, vertex))
    p1 = _add(vertex, u, size)
    p2 = _add(p1, v, size)
    p3 = _add(vertex, v, size)
    ctx.draw.line((p1, p2, p3), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    return _line_bbox((p1, p2, p3), ctx, pad=4.0)


def _draw_polygon(ctx: _RenderContext, points: Sequence[Point], *, fill: Color | None = None, outline: Color | None = None) -> BBox:
    polygon = [(float(x), float(y)) for x, y in points]
    ctx.draw.polygon(polygon, fill=fill or ctx.fill_color)
    ctx.draw.line(polygon + [polygon[0]], fill=outline or ctx.line_color, width=ctx.line_width, joint="curve")
    return bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _rotated_template(points: Sequence[Point], *, center: Point, scale: float, rotation_degrees: float) -> Tuple[Point, ...]:
    theta = math.radians(float(rotation_degrees))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    transformed: list[Point] = []
    for x, y in points:
        sx = float(x) * float(scale)
        sy = float(y) * float(scale)
        transformed.append((center[0] + sx * cos_t - sy * sin_t, center[1] + sx * sin_t + sy * cos_t))
    return tuple(transformed)


def _shape_template(shape_kind: str) -> Tuple[Point, ...]:
    if shape_kind == "triangle":
        return ((0.0, -1.05), (1.16, 0.82), (-1.08, 0.82))
    if shape_kind == "quadrilateral":
        return ((-1.1, -0.82), (0.86, -0.98), (1.18, 0.66), (-0.86, 0.96))
    if shape_kind == "pentagon":
        return ((0.0, -1.12), (1.08, -0.34), (0.76, 0.96), (-0.46, 1.08), (-1.14, 0.12))
    raise ValueError(f"unknown shape_kind={shape_kind!r}")


def _labels_for_shape(shape_kind: str, *, target: bool = False) -> Tuple[str, ...]:
    base = tuple(chr(ord("A") + index) for index in range(len(_shape_template(shape_kind))))
    if target:
        return tuple(f"{label}'" for label in base)
    return base


def _build_context(
    *,
    scene_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", rendering_defaults.get("canvas_width", 820)))
    height = int(params.get("canvas_height", rendering_defaults.get("canvas_height", 580)))
    background, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=str(scene_id),
        canvas_width=width,
        canvas_height=height,
        allow_dark=False,
        require_grid=False,
    )
    image = background.convert("RGB")
    readout_font_family = str(params.get("readout_font_family", rendering_defaults.get("readout_font_family", "roboto")))
    diagram_style_trace = dict(diagram_style_meta)
    diagram_style_trace["readout_font_family"] = readout_font_family
    return _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=width,
        height=height,
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        fill_color=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        alt_fill_color=tuple(int(value) for value in diagram_style.option_fill_rgb),
        muted_color=tuple(int(value) for value in diagram_style.guide_rgb),
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
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{scene_id}.scene_transform"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _similar_case(
    query_id: str,
    *,
    task_id: str,
    shape_kind: str,
    answer: float,
    target_name: str,
    source_target_label: str,
    target_target_label: str,
    support_source_label: str,
    support_target_label: str,
    scale_factor: float,
) -> _Case:
    return _Case(
        scene_id=SIMILAR_SCENE_ID,
        task_id=task_id,
        query_id=query_id,
        draw_kind="similar_pair",
        answer=float(answer),
        target_name=str(target_name),
        variable_name="x",
        shape_kind=str(shape_kind),
        relation="similar_figure_marked_side_equation",
        labels={
            "source_target_side": str(source_target_label),
            "target_target_side": str(target_target_label),
            "support_source_side": str(support_source_label),
            "support_target_side": str(support_target_label),
        },
        measures={"scale_factor": float(scale_factor)},
    )


_SIMILAR_CASES: Tuple[_Case, ...] = (
    _similar_case(
        "similar_triangles_side_ratio_variable",
        task_id=SIMILAR_VARIABLE_TASK_KEY,
        shape_kind="triangle",
        answer=4.5,
        target_name="x",
        source_target_label="2x+1",
        target_target_label="15",
        support_source_label="6",
        support_target_label="9",
        scale_factor=1.5,
    ),
    _similar_case(
        "similar_polygons_side_ratio_variable",
        task_id=SIMILAR_VARIABLE_TASK_KEY,
        shape_kind="quadrilateral",
        answer=5,
        target_name="x",
        source_target_label="x+3",
        target_target_label="20",
        support_source_label="4",
        support_target_label="10",
        scale_factor=2.5,
    ),
    _similar_case(
        "two_expression_side_ratio_variable",
        task_id=SIMILAR_VARIABLE_TASK_KEY,
        shape_kind="pentagon",
        answer=4,
        target_name="x",
        source_target_label="x+2",
        target_target_label="2x+1",
        support_source_label="8",
        support_target_label="12",
        scale_factor=1.5,
    ),
    _similar_case(
        "similar_triangles_target_side_from_expression",
        task_id=SIMILAR_SIDE_LENGTH_TASK_KEY,
        shape_kind="triangle",
        answer=10,
        target_name="AB",
        source_target_label="3x-2",
        target_target_label="20",
        support_source_label="5",
        support_target_label="10",
        scale_factor=2.0,
    ),
    _similar_case(
        "similar_polygons_target_side_from_expression",
        task_id=SIMILAR_SIDE_LENGTH_TASK_KEY,
        shape_kind="quadrilateral",
        answer=11,
        target_name="AB",
        source_target_label="2x+5",
        target_target_label="33",
        support_source_label="4",
        support_target_label="12",
        scale_factor=3.0,
    ),
)


def _marked_case(
    query_id: str,
    *,
    task_id: str,
    draw_kind: str,
    answer: float,
    target_name: str,
    shape_kind: str,
    labels: Mapping[str, str],
    relation: str,
    variable_name: str = "x",
) -> _Case:
    return _Case(
        scene_id=MARKED_POLYGON_SCENE_ID,
        task_id=task_id,
        query_id=query_id,
        draw_kind=draw_kind,
        answer=float(answer),
        target_name=str(target_name),
        variable_name=str(variable_name),
        shape_kind=str(shape_kind),
        relation=str(relation),
        labels=dict(labels),
    )


_MARKED_CASES: Tuple[_Case, ...] = (
    _marked_case(
        "isosceles_triangle_equal_side_variable",
        task_id=MARKED_SIDE_VARIABLE_TASK_KEY,
        draw_kind="triangle_equal_sides",
        answer=7,
        target_name="x",
        shape_kind="triangle",
        relation="isosceles_equal_sides_expression",
        labels={"left_side": "2x+4", "right_side": "18"},
    ),
    _marked_case(
        "equilateral_triangle_equal_side_variable",
        task_id=MARKED_SIDE_VARIABLE_TASK_KEY,
        draw_kind="equilateral_sides",
        answer=6,
        target_name="x",
        shape_kind="triangle",
        relation="equilateral_equal_sides_expression",
        labels={"left_side": "3x+2", "right_side": "20", "base_side": "20"},
    ),
    _marked_case(
        "marked_polygon_equal_side_variable",
        task_id=MARKED_SIDE_VARIABLE_TASK_KEY,
        draw_kind="polygon_equal_sides",
        answer=7,
        target_name="x",
        shape_kind="quadrilateral",
        relation="marked_polygon_equal_sides_expression",
        labels={"left_side": "2x+3", "right_side": "x+10"},
    ),
    _marked_case(
        "marked_equal_angles_variable",
        task_id=MARKED_ANGLE_VARIABLE_TASK_KEY,
        draw_kind="polygon_equal_angles",
        answer=20,
        target_name="x",
        shape_kind="quadrilateral",
        relation="marked_equal_angles_expression",
        labels={"angle_a": f"(3x+5){DEGREE_SYMBOL}", "angle_b": f"(2x+25){DEGREE_SYMBOL}"},
    ),
    _marked_case(
        "isosceles_triangle_base_angle_variable",
        task_id=MARKED_ANGLE_VARIABLE_TASK_KEY,
        draw_kind="isosceles_base_angles",
        answer=15,
        target_name="x",
        shape_kind="triangle",
        relation="isosceles_base_angles_expression",
        labels={"angle_a": f"(2x+10){DEGREE_SYMBOL}", "angle_b": f"(4x-20){DEGREE_SYMBOL}"},
    ),
    _marked_case(
        "isosceles_triangle_side_from_expression",
        task_id=MARKED_SIDE_LENGTH_TASK_KEY,
        draw_kind="triangle_equal_sides",
        answer=17,
        target_name="AB",
        shape_kind="triangle",
        relation="isosceles_side_length_from_expression",
        labels={"left_side": "2x+3", "right_side": "17"},
    ),
    _marked_case(
        "equilateral_triangle_side_from_expression",
        task_id=MARKED_SIDE_LENGTH_TASK_KEY,
        draw_kind="equilateral_sides",
        answer=20,
        target_name="AB",
        shape_kind="triangle",
        relation="equilateral_side_length_from_expression",
        labels={"left_side": "3x-1", "right_side": "20", "base_side": "20"},
    ),
    _marked_case(
        "marked_polygon_side_from_expression",
        task_id=MARKED_SIDE_LENGTH_TASK_KEY,
        draw_kind="polygon_equal_sides",
        answer=22,
        target_name="AB",
        shape_kind="quadrilateral",
        relation="marked_polygon_side_length_from_expression",
        labels={"left_side": "4x+2", "right_side": "2x+12"},
    ),
    _marked_case(
        "marked_equal_angle_from_expression",
        task_id=MARKED_ANGLE_VALUE_TASK_KEY,
        draw_kind="polygon_equal_angles",
        answer=70,
        target_name="angle A",
        shape_kind="quadrilateral",
        relation="marked_equal_angle_measure_from_expression",
        labels={"angle_a": f"(3x+10){DEGREE_SYMBOL}", "angle_b": f"(x+50){DEGREE_SYMBOL}"},
    ),
    _marked_case(
        "isosceles_triangle_angle_from_expression",
        task_id=MARKED_ANGLE_VALUE_TASK_KEY,
        draw_kind="isosceles_base_angles",
        answer=55,
        target_name="angle B",
        shape_kind="triangle",
        relation="isosceles_angle_measure_from_expression",
        labels={"angle_a": f"(2x+15){DEGREE_SYMBOL}", "angle_b": f"(4x-25){DEGREE_SYMBOL}"},
    ),
)


def _parallel_case(
    query_id: str,
    *,
    task_id: str,
    draw_kind: str,
    answer: float,
    target_name: str,
    labels: Mapping[str, str],
    relation: str,
) -> _Case:
    return _Case(
        scene_id=PARALLEL_SCENE_ID,
        task_id=task_id,
        query_id=query_id,
        draw_kind=draw_kind,
        answer=float(answer),
        target_name=str(target_name),
        variable_name="x",
        shape_kind=str(draw_kind),
        relation=str(relation),
        labels=dict(labels),
    )


_PARALLEL_CASES: Tuple[_Case, ...] = (
    _parallel_case(
        "triangle_side_splitter_variable",
        task_id=PARALLEL_VARIABLE_TASK_KEY,
        draw_kind="triangle_side_splitter",
        answer=6,
        target_name="x",
        relation="triangle_side_splitter_proportion_expression",
        labels={"left_top": "6", "left_bottom": "x+2", "right_top": "9", "right_bottom": "12"},
    ),
    _parallel_case(
        "parallel_transversal_segment_variable",
        task_id=PARALLEL_VARIABLE_TASK_KEY,
        draw_kind="parallel_transversals",
        answer=11,
        target_name="x",
        relation="parallel_transversal_segment_proportion_expression",
        labels={"left_top": "8", "left_bottom": "12", "right_top": "x+1", "right_bottom": "18"},
    ),
    _parallel_case(
        "triangle_side_splitter_segment_length",
        task_id=PARALLEL_SEGMENT_LENGTH_TASK_KEY,
        draw_kind="triangle_side_splitter",
        answer=9,
        target_name="AE",
        relation="triangle_side_splitter_segment_length_expression",
        labels={"left_top": "5", "left_bottom": "10", "right_top": "2x+1", "right_bottom": "3x+6"},
    ),
    _parallel_case(
        "parallel_transversal_segment_length",
        task_id=PARALLEL_SEGMENT_LENGTH_TASK_KEY,
        draw_kind="parallel_transversals",
        answer=10,
        target_name="UV",
        relation="parallel_transversal_segment_length_expression",
        labels={"left_top": "4", "left_bottom": "6", "right_top": "x+2", "right_bottom": "15"},
    ),
)


def _cases_for_task(task_id: str) -> Tuple[_Case, ...]:
    if task_id in (SIMILAR_VARIABLE_TASK_KEY, SIMILAR_SIDE_LENGTH_TASK_KEY):
        return tuple(case for case in _SIMILAR_CASES if case.task_id == task_id)
    if task_id in (MARKED_SIDE_VARIABLE_TASK_KEY, MARKED_ANGLE_VARIABLE_TASK_KEY, MARKED_SIDE_LENGTH_TASK_KEY, MARKED_ANGLE_VALUE_TASK_KEY):
        return tuple(case for case in _MARKED_CASES if case.task_id == task_id)
    if task_id in (PARALLEL_VARIABLE_TASK_KEY, PARALLEL_SEGMENT_LENGTH_TASK_KEY):
        return tuple(case for case in _PARALLEL_CASES if case.task_id == task_id)
    raise ValueError(f"unknown Geo3K marked-equation task: {task_id}")


def _case_for_query(task_id: str, query_id: str, variant_index: int) -> _Case:
    v = int(variant_index) % 5
    if query_id == "similar_triangles_side_ratio_variable":
        answer = 3 + v
        b = v + 1
        source_value = (2 * answer) + b
        scale = 2
        return _similar_case(
            query_id,
            task_id=task_id,
            shape_kind="triangle",
            answer=answer,
            target_name="x",
            source_target_label=f"2x+{b}",
            target_target_label=str(source_value * scale),
            support_source_label=str(5 + v),
            support_target_label=str((5 + v) * scale),
            scale_factor=float(scale),
        )
    if query_id == "similar_polygons_side_ratio_variable":
        answer = 4 + v
        b = v + 2
        source_value = answer + b
        scale = 3
        return _similar_case(
            query_id,
            task_id=task_id,
            shape_kind="quadrilateral",
            answer=answer,
            target_name="x",
            source_target_label=f"x+{b}",
            target_target_label=str(source_value * scale),
            support_source_label=str(3 + v),
            support_target_label=str((3 + v) * scale),
            scale_factor=float(scale),
        )
    if query_id == "two_expression_side_ratio_variable":
        answer = 3 + v
        b = answer + 3
        c = answer + 6
        scale = 2
        return _similar_case(
            query_id,
            task_id=task_id,
            shape_kind="pentagon",
            answer=answer,
            target_name="x",
            source_target_label=f"x+{b}",
            target_target_label=f"3x+{c}",
            support_source_label=str(4 + v),
            support_target_label=str((4 + v) * scale),
            scale_factor=float(scale),
        )
    if query_id == "similar_triangles_target_side_from_expression":
        answer = 8 + (2 * v)
        scale = 2
        return _similar_case(
            query_id,
            task_id=task_id,
            shape_kind="triangle",
            answer=answer,
            target_name="AB",
            source_target_label="2x+2",
            target_target_label=str(answer * scale),
            support_source_label=str(4 + v),
            support_target_label=str((4 + v) * scale),
            scale_factor=float(scale),
        )
    if query_id == "similar_polygons_target_side_from_expression":
        answer = 9 + (2 * v)
        scale = 3
        b = v + 2
        return _similar_case(
            query_id,
            task_id=task_id,
            shape_kind="quadrilateral",
            answer=answer,
            target_name="AB",
            source_target_label=f"x+{b}",
            target_target_label=str(answer * scale),
            support_source_label=str(3 + v),
            support_target_label=str((3 + v) * scale),
            scale_factor=float(scale),
        )
    if query_id == "isosceles_triangle_equal_side_variable":
        answer = 4 + v
        b = v + 1
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="triangle_equal_sides",
            answer=answer,
            target_name="x",
            shape_kind="triangle",
            relation="isosceles_equal_sides_expression",
            labels={"left_side": f"2x+{b}", "right_side": str((2 * answer) + b)},
        )
    if query_id == "equilateral_triangle_equal_side_variable":
        answer = 3 + v
        b = v + 2
        value = (3 * answer) + b
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="equilateral_sides",
            answer=answer,
            target_name="x",
            shape_kind="triangle",
            relation="equilateral_equal_sides_expression",
            labels={"left_side": f"3x+{b}", "right_side": str(value), "base_side": str(value)},
        )
    if query_id == "marked_polygon_equal_side_variable":
        answer = 5 + v
        b = v + 3
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="polygon_equal_sides",
            answer=answer,
            target_name="x",
            shape_kind="quadrilateral",
            relation="marked_polygon_equal_sides_expression",
            labels={"left_side": f"2x+{b}", "right_side": f"x+{answer + b}"},
        )
    if query_id == "isosceles_altitude_base_split_variable":
        answer = 4 + v
        b = v + 2
        value = (2 * answer) + b
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="isosceles_altitude_base_split",
            answer=answer,
            target_name="x",
            shape_kind="triangle",
            relation="isosceles_altitude_base_split_expression",
            labels={"left_base": f"2x+{b}", "right_base": str(value)},
        )
    if query_id == "marked_equal_angles_variable":
        answer = 10 + (5 * v)
        b = 20 + v
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="polygon_equal_angles",
            answer=answer,
            target_name="x",
            shape_kind="quadrilateral",
            relation="marked_equal_angles_expression",
            labels={"angle_a": f"(2x+{b}){DEGREE_SYMBOL}", "angle_b": f"(x+{answer + b}){DEGREE_SYMBOL}"},
        )
    if query_id == "isosceles_triangle_base_angle_variable":
        answer = 8 + (4 * v)
        b = 15
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="isosceles_base_angles",
            answer=answer,
            target_name="x",
            shape_kind="triangle",
            relation="isosceles_base_angles_expression",
            labels={"angle_a": f"(2x+{b}){DEGREE_SYMBOL}", "angle_b": f"(x+{answer + b}){DEGREE_SYMBOL}"},
        )
    if query_id == "equilateral_median_right_angle_variable":
        coefficients = (3, 5, 6, 9, 10)
        coeff = coefficients[v]
        answer = int(90 / coeff)
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="equilateral_median_right_angle",
            answer=answer,
            target_name="y",
            variable_name="y",
            shape_kind="triangle",
            relation="equilateral_median_perpendicular_expression",
            labels={"right_angle_expression": f"{coeff}y{DEGREE_SYMBOL}"},
        )
    if query_id == "isosceles_triangle_side_from_expression":
        answer = 12 + (2 * v)
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="triangle_equal_sides",
            answer=answer,
            target_name="AB",
            shape_kind="triangle",
            relation="isosceles_side_length_from_expression",
            labels={"left_side": "2x+2", "right_side": str(answer)},
        )
    if query_id == "equilateral_triangle_side_from_expression":
        answer = 15 + (2 * v)
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="equilateral_sides",
            answer=answer,
            target_name="AB",
            shape_kind="triangle",
            relation="equilateral_side_length_from_expression",
            labels={"left_side": "3x+3", "right_side": str(answer), "base_side": str(answer)},
        )
    if query_id == "marked_polygon_side_from_expression":
        answer = 18 + (2 * v)
        b = v + 2
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="polygon_equal_sides",
            answer=answer,
            target_name="AB",
            shape_kind="quadrilateral",
            relation="marked_polygon_side_length_from_expression",
            labels={"left_side": f"2x+{b}", "right_side": str(answer)},
        )
    if query_id == "equilateral_median_side_length_from_expression":
        x_value = 3 + v
        answer = (3 * x_value) + 1
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="equilateral_median_sides",
            answer=answer,
            target_name="each side",
            shape_kind="triangle",
            relation="equilateral_median_side_length_from_expression",
            labels={"left_side": f"3x+1", "right_side": f"4x-2", "base_side": "?"},
        )
    if query_id == "marked_equal_angle_from_expression":
        answer = 50 + (10 * v)
        x_value = int((answer - 20) / 2)
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="polygon_equal_angles",
            answer=answer,
            target_name="angle A",
            shape_kind="quadrilateral",
            relation="marked_equal_angle_measure_from_expression",
            labels={"angle_a": f"(2x+20){DEGREE_SYMBOL}", "angle_b": f"(x+{answer - x_value}){DEGREE_SYMBOL}"},
        )
    if query_id == "isosceles_triangle_angle_from_expression":
        answer = 45 + (10 * v)
        x_value = int((answer - 15) / 2)
        return _marked_case(
            query_id,
            task_id=task_id,
            draw_kind="isosceles_base_angles",
            answer=answer,
            target_name="angle B",
            shape_kind="triangle",
            relation="isosceles_angle_measure_from_expression",
            labels={"angle_a": f"(2x+15){DEGREE_SYMBOL}", "angle_b": f"(x+{answer - x_value}){DEGREE_SYMBOL}"},
        )
    if query_id == "triangle_side_splitter_variable":
        answer = 3 + v
        c = 2
        left_top = 4 + v
        return _parallel_case(
            query_id,
            task_id=task_id,
            draw_kind="triangle_side_splitter",
            answer=answer,
            target_name="x",
            relation="triangle_side_splitter_proportion_expression",
            labels={
                "left_top": str(left_top),
                "left_bottom": f"x+{c}",
                "right_top": str(2 * left_top),
                "right_bottom": str(2 * (answer + c)),
            },
        )
    if query_id == "parallel_transversal_segment_variable":
        answer = 6 + v
        c = 1
        left_top = 5 + v
        return _parallel_case(
            query_id,
            task_id=task_id,
            draw_kind="parallel_transversals",
            answer=answer,
            target_name="x",
            relation="parallel_transversal_segment_proportion_expression",
            labels={
                "left_top": str(left_top),
                "left_bottom": str(2 * left_top),
                "right_top": f"x+{c}",
                "right_bottom": str(2 * (answer + c)),
            },
        )
    if query_id == "triangle_side_splitter_segment_length":
        answer = 8 + v
        left_top = 4 + v
        return _parallel_case(
            query_id,
            task_id=task_id,
            draw_kind="triangle_side_splitter",
            answer=answer,
            target_name="AE",
            relation="triangle_side_splitter_segment_length_expression",
            labels={
                "left_top": str(left_top),
                "left_bottom": str(2 * left_top),
                "right_top": "x+2",
                "right_bottom": str(2 * answer),
            },
        )
    if query_id == "parallel_transversal_segment_length":
        answer = 10 + v
        left_top = 5 + v
        return _parallel_case(
            query_id,
            task_id=task_id,
            draw_kind="parallel_transversals",
            answer=answer,
            target_name="UV",
            relation="parallel_transversal_segment_length_expression",
            labels={
                "left_top": str(left_top),
                "left_bottom": str(2 * left_top),
                "right_top": "x+1",
                "right_bottom": str(2 * answer),
            },
        )
    raise ValueError(f"unknown query_id={query_id!r}")


def _select_problem(task_id: str, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    query_ids = _QUERY_IDS_BY_TASK[str(task_id)]
    forced_query = params.get("query_id")
    if forced_query is not None:
        query_id = str(forced_query)
        if query_id not in query_ids:
            raise ValueError(f"query_id={query_id!r} is not supported by {task_id}")
    else:
        query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_id")
        query_id = query_ids[int(query_rng.randrange(len(query_ids)))]
    query_probabilities = _probability_map(query_ids, query_id if forced_query is not None else None)
    case_rng = spawn_rng(int(instance_seed), f"{task_id}.{query_id}.case")
    case_index = int(case_rng.randrange(5))
    case = _case_for_query(str(task_id), str(query_id), case_index)
    return _ResolvedProblem(
        task_id=str(task_id),
        scene_id=str(case.scene_id),
        query_id=str(query_id),
        case=case,
        query_probabilities=dict(query_probabilities),
        case_index=int(case_index),
        layout_seed=int(instance_seed),
    )


def _draw_vertex_labels(ctx: _RenderContext, points: Sequence[Point], labels: Sequence[str]) -> Dict[str, BBox]:
    center = (sum(point[0] for point in points) / float(len(points)), sum(point[1] for point in points) / float(len(points)))
    bboxes: Dict[str, BBox] = {}
    for label, point in zip(labels, points):
        bboxes[str(label)] = _draw_point_label(ctx, str(label), point, _sub(point, center), offset=24.0)
    return bboxes


def _render_similar_pair(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    case = problem.case
    labels = dict(case.labels or {})
    rng = spawn_rng(problem.layout_seed, f"{case.task_id}.{case.query_id}.similar_layout")
    shape_kind = str(case.shape_kind or "triangle")
    source_template = _shape_template(shape_kind)
    source_scale = rng.uniform(54.0, 68.0)
    visual_scale = rng.uniform(1.35, 1.62)
    source_center = (ctx.width * 0.31 + rng.uniform(-12.0, 10.0), ctx.height * 0.53 + rng.uniform(-16.0, 14.0))
    target_center = (ctx.width * 0.69 + rng.uniform(-10.0, 14.0), ctx.height * 0.52 + rng.uniform(-16.0, 14.0))
    source_points = _rotated_template(source_template, center=source_center, scale=source_scale, rotation_degrees=rng.uniform(-7.0, 7.0))
    target_points = _rotated_template(
        source_template,
        center=target_center,
        scale=source_scale * visual_scale,
        rotation_degrees=rng.uniform(10.0, 20.0),
    )
    source_labels = _labels_for_shape(shape_kind)
    target_labels = _labels_for_shape(shape_kind, target=True)
    construction: Dict[str, BBox] = {
        "source_figure": _draw_polygon(ctx, source_points, fill=ctx.fill_color, outline=ctx.line_color),
        "target_figure": _draw_polygon(ctx, target_points, fill=ctx.alt_fill_color, outline=ctx.secondary_color),
    }
    point_labels = {f"source_{key}": _bbox_to_list(value) for key, value in _draw_vertex_labels(ctx, source_points, source_labels).items()}
    point_labels.update({f"target_{key}": _bbox_to_list(value) for key, value in _draw_vertex_labels(ctx, target_points, target_labels).items()})
    target_side = (0, 1)
    support_side = (1, 2) if shape_kind == "triangle" else (2, 3)
    readouts = {
        "source_target_side_label": _draw_side_label(ctx, source_points, target_side, labels["source_target_side"], offset=-31.0),
        "target_target_side_label": _draw_side_label(ctx, target_points, target_side, labels["target_target_side"], offset=34.0),
        "support_source_side_label": _draw_side_label(ctx, source_points, support_side, labels["support_source_side"], offset=33.0),
        "support_target_side_label": _draw_side_label(ctx, target_points, support_side, labels["support_target_side"], offset=-36.0),
    }
    construction["source_target_side_tick"] = _draw_tick(ctx, source_points[target_side[0]], source_points[target_side[1]], count=1)
    construction["target_target_side_tick"] = _draw_tick(ctx, target_points[target_side[0]], target_points[target_side[1]], count=1)
    construction["support_source_side_tick"] = _draw_tick(ctx, source_points[support_side[0]], source_points[support_side[1]], count=2)
    construction["support_target_side_tick"] = _draw_tick(ctx, target_points[support_side[0]], target_points[support_side[1]], count=2)
    annotation = {
        "target_side_start": source_points[target_side[0]],
        "target_side_end": source_points[target_side[1]],
        "corresponding_side_start": target_points[target_side[0]],
        "corresponding_side_end": target_points[target_side[1]],
        "support_source_side_start": source_points[support_side[0]],
        "support_source_side_end": source_points[support_side[1]],
        "support_target_side_start": target_points[support_side[0]],
        "support_target_side_end": target_points[support_side[1]],
    }
    render_map = {
        "source_vertices": {label: _point_to_list(point) for label, point in zip(source_labels, source_points)},
        "target_vertices": {label: _point_to_list(point) for label, point in zip(target_labels, target_points)},
        "point_label_bboxes": point_labels,
        "readout_bboxes": _json_ready(readouts),
        "construction_bboxes": _json_ready(construction),
    }
    return _RenderedScene(ctx.image, annotation, render_map)


def _triangle_points(ctx: _RenderContext, rng: Any) -> Tuple[Point, Point, Point]:
    cx = ctx.width / 2.0 + rng.uniform(-12.0, 12.0)
    cy = ctx.height / 2.0 + rng.uniform(-10.0, 16.0)
    w = rng.uniform(360.0, 420.0)
    h = rng.uniform(265.0, 305.0)
    return ((cx, cy - h / 2.0), (cx - w / 2.0, cy + h / 2.0), (cx + w / 2.0, cy + h / 2.0))


def _split_triangle_points(ctx: _RenderContext, rng: Any) -> Tuple[Point, Point, Point, Point]:
    apex, left_base, right_base = _triangle_points(ctx, rng)
    split = _mid(left_base, right_base)
    return apex, left_base, right_base, split


def _quad_points(ctx: _RenderContext, rng: Any) -> Tuple[Point, Point, Point, Point]:
    cx = ctx.width / 2.0 + rng.uniform(-10.0, 12.0)
    cy = ctx.height / 2.0 + rng.uniform(-8.0, 16.0)
    return (
        (cx - rng.uniform(190.0, 220.0), cy - rng.uniform(130.0, 155.0)),
        (cx + rng.uniform(120.0, 160.0), cy - rng.uniform(150.0, 172.0)),
        (cx + rng.uniform(205.0, 235.0), cy + rng.uniform(110.0, 145.0)),
        (cx - rng.uniform(145.0, 180.0), cy + rng.uniform(145.0, 170.0)),
    )


def _render_marked_polygon(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    case = problem.case
    labels = dict(case.labels or {})
    rng = spawn_rng(problem.layout_seed, f"{case.task_id}.{case.query_id}.marked_polygon_layout")
    construction: Dict[str, BBox] = {}
    readouts: Dict[str, BBox] = {}
    point_label_bboxes: Dict[str, BBox] = {}
    annotation: Dict[str, Point] = {}
    vertex_payload: Dict[str, Point] = {}
    if case.draw_kind in {"equilateral_median_sides", "equilateral_median_right_angle", "isosceles_altitude_base_split"}:
        apex, left_base, right_base, split = _split_triangle_points(ctx, rng)
        apex, left_base, right_base, split = ctx.scene_transform.points((apex, left_base, right_base, split))
        points = (apex, left_base, right_base)
        vertex_payload = {"A": apex, "B": left_base, "C": right_base, "D": split}
        names = ("A", "B", "C")
        construction["polygon"] = _draw_polygon(ctx, points, fill=ctx.fill_color, outline=ctx.line_color)
        ctx.draw.line((apex, split), fill=ctx.secondary_color, width=ctx.line_width)
        construction["split_segment"] = _line_bbox((apex, split), ctx, pad=ctx.line_width + 3)
        construction["right_angle"] = _draw_right_angle_marker(ctx, split, apex, right_base)
        point_label_bboxes = {key: _bbox_to_list(value) for key, value in _draw_vertex_labels(ctx, points, names).items()}
        point_label_bboxes["D"] = _bbox_to_list(_draw_point_label(ctx, "D", split, (0.0, 1.0)))
        left_side = (apex, left_base)
        right_side = (apex, right_base)
        base_left = (left_base, split)
        base_right = (split, right_base)
        if case.draw_kind in {"equilateral_median_sides", "equilateral_median_right_angle"}:
            construction["left_side_tick"] = _draw_tick(ctx, *left_side, count=1)
            construction["right_side_tick"] = _draw_tick(ctx, *right_side, count=1)
            construction["base_tick"] = _draw_tick(ctx, left_base, right_base, count=1)
        if case.draw_kind == "isosceles_altitude_base_split":
            construction["left_side_tick"] = _draw_tick(ctx, *left_side, count=1)
            construction["right_side_tick"] = _draw_tick(ctx, *right_side, count=1)
            construction["left_base_split_tick"] = _draw_tick(ctx, *base_left, count=2)
            construction["right_base_split_tick"] = _draw_tick(ctx, *base_right, count=2)
            readouts["left_base_label"] = _draw_side_label(ctx, (left_base, split), (0, 1), labels["left_base"], offset=31.0)
            readouts["right_base_label"] = _draw_side_label(ctx, (split, right_base), (0, 1), labels["right_base"], offset=31.0)
            annotation = {
                "target_split_start": left_base,
                "target_split_end": split,
                "equal_split_start": split,
                "equal_split_end": right_base,
                "altitude_start": apex,
                "altitude_end": split,
            }
        elif case.draw_kind == "equilateral_median_right_angle":
            readouts["right_angle_expression"] = _draw_text_centered(ctx, labels["right_angle_expression"], _add(split, (44.0, -34.0)), small=True)
            annotation = {
                "target_angle_vertex": split,
                "target_angle_ray_1": apex,
                "target_angle_ray_2": right_base,
                "median_start": apex,
                "median_end": split,
            }
        else:
            readouts["left_side_label"] = _draw_side_label(ctx, (apex, left_base), (0, 1), labels["left_side"], offset=-32.0)
            readouts["right_side_label"] = _draw_side_label(ctx, (apex, right_base), (0, 1), labels["right_side"], offset=32.0)
            readouts["base_side_label"] = _draw_side_label(ctx, (left_base, right_base), (0, 1), labels["base_side"], offset=31.0)
            annotation = {
                "target_side_start": apex,
                "target_side_end": left_base,
                "equal_side_start": apex,
                "equal_side_end": right_base,
                "median_start": apex,
                "median_end": split,
            }
    elif case.draw_kind in {"triangle_equal_sides", "equilateral_sides", "isosceles_base_angles"}:
        points = _triangle_points(ctx, rng)
        points = ctx.scene_transform.points(points)
        vertex_payload = {"A": points[0], "B": points[1], "C": points[2]}
        names = ("A", "B", "C")
        construction["polygon"] = _draw_polygon(ctx, points, fill=ctx.fill_color, outline=ctx.line_color)
        point_label_bboxes = {key: _bbox_to_list(value) for key, value in _draw_vertex_labels(ctx, points, names).items()}
        left_side = (0, 1)
        right_side = (0, 2)
        base_side = (1, 2)
        if case.draw_kind in {"triangle_equal_sides", "equilateral_sides"}:
            readouts["left_side_label"] = _draw_side_label(ctx, points, left_side, labels["left_side"], offset=-31.0)
            readouts["right_side_label"] = _draw_side_label(ctx, points, right_side, labels["right_side"], offset=31.0)
            construction["left_equal_tick"] = _draw_tick(ctx, points[left_side[0]], points[left_side[1]], count=1)
            construction["right_equal_tick"] = _draw_tick(ctx, points[right_side[0]], points[right_side[1]], count=1)
            if case.draw_kind == "equilateral_sides":
                readouts["base_side_label"] = _draw_side_label(ctx, points, base_side, labels["base_side"], offset=30.0)
                construction["base_equal_tick"] = _draw_tick(ctx, points[base_side[0]], points[base_side[1]], count=1)
            annotation = {
                "target_side_start": points[left_side[0]],
                "target_side_end": points[left_side[1]],
                "equal_side_start": points[right_side[0]],
                "equal_side_end": points[right_side[1]],
            }
        else:
            construction["left_equal_tick"] = _draw_tick(ctx, points[left_side[0]], points[left_side[1]], count=1)
            construction["right_equal_tick"] = _draw_tick(ctx, points[right_side[0]], points[right_side[1]], count=1)
            construction["left_base_angle_mark"] = _draw_angle_arc(ctx, points[1], points[0], points[2], count=1)
            construction["right_base_angle_mark"] = _draw_angle_arc(ctx, points[2], points[0], points[1], count=1)
            readouts["left_angle_label"] = _draw_text_centered(ctx, labels["angle_a"], _add(points[1], (65.0, -32.0)), small=True)
            readouts["right_angle_label"] = _draw_text_centered(ctx, labels["angle_b"], _add(points[2], (-68.0, -32.0)), small=True)
            annotation = {
                "target_angle_vertex": points[1],
                "target_angle_ray_1": points[0],
                "target_angle_ray_2": points[2],
                "equal_angle_vertex": points[2],
                "equal_angle_ray_1": points[0],
                "equal_angle_ray_2": points[1],
            }
    else:
        points = _quad_points(ctx, rng)
        points = ctx.scene_transform.points(points)
        vertex_payload = {"A": points[0], "B": points[1], "C": points[2], "D": points[3]}
        names = ("A", "B", "C", "D")
        construction["polygon"] = _draw_polygon(ctx, points, fill=ctx.fill_color, outline=ctx.line_color)
        point_label_bboxes = {key: _bbox_to_list(value) for key, value in _draw_vertex_labels(ctx, points, names).items()}
        if case.draw_kind == "polygon_equal_sides":
            side_a = (0, 1)
            side_b = (2, 3)
            readouts["first_side_label"] = _draw_side_label(ctx, points, side_a, labels["left_side"], offset=-32.0)
            readouts["second_side_label"] = _draw_side_label(ctx, points, side_b, labels["right_side"], offset=33.0)
            construction["first_equal_tick"] = _draw_tick(ctx, points[side_a[0]], points[side_a[1]], count=2)
            construction["second_equal_tick"] = _draw_tick(ctx, points[side_b[0]], points[side_b[1]], count=2)
            annotation = {
                "target_side_start": points[side_a[0]],
                "target_side_end": points[side_a[1]],
                "equal_side_start": points[side_b[0]],
                "equal_side_end": points[side_b[1]],
            }
        else:
            construction["first_equal_angle_mark"] = _draw_angle_arc(ctx, points[0], points[1], points[3], count=2)
            construction["second_equal_angle_mark"] = _draw_angle_arc(ctx, points[2], points[1], points[3], count=2)
            readouts["first_angle_label"] = _draw_text_centered(ctx, labels["angle_a"], _add(points[0], (58.0, 42.0)), small=True)
            readouts["second_angle_label"] = _draw_text_centered(ctx, labels["angle_b"], _add(points[2], (-64.0, -38.0)), small=True)
            annotation = {
                "target_angle_vertex": points[0],
                "target_angle_ray_1": points[1],
                "target_angle_ray_2": points[3],
                "equal_angle_vertex": points[2],
                "equal_angle_ray_1": points[1],
                "equal_angle_ray_2": points[3],
            }
    render_map = {
        "vertices": {label: _point_to_list(point) for label, point in vertex_payload.items()},
        "point_label_bboxes": point_label_bboxes,
        "readout_bboxes": _json_ready(readouts),
        "construction_bboxes": _json_ready(construction),
    }
    return _RenderedScene(ctx.image, annotation, render_map)


def _render_parallel(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    case = problem.case
    labels = dict(case.labels or {})
    rng = spawn_rng(problem.layout_seed, f"{case.task_id}.{case.query_id}.parallel_layout")
    construction: Dict[str, BBox] = {}
    readouts: Dict[str, BBox] = {}
    point_label_bboxes: Dict[str, BBox] = {}
    annotation: Dict[str, Point] = {}
    if case.draw_kind == "triangle_side_splitter":
        apex = (ctx.width * 0.50 + rng.uniform(-8.0, 8.0), ctx.height * 0.19 + rng.uniform(-8.0, 8.0))
        left_base = (ctx.width * 0.22 + rng.uniform(-10.0, 8.0), ctx.height * 0.78 + rng.uniform(-8.0, 8.0))
        right_base = (ctx.width * 0.78 + rng.uniform(-8.0, 10.0), ctx.height * 0.78 + rng.uniform(-8.0, 8.0))
        t = rng.uniform(0.44, 0.52)
        d = _add(apex, _sub(left_base, apex), t)
        e = _add(apex, _sub(right_base, apex), t)
        apex, left_base, right_base, d, e = ctx.scene_transform.points((apex, left_base, right_base, d, e))
        points = (apex, left_base, right_base)
        construction["triangle"] = _draw_polygon(ctx, points, fill=ctx.fill_color, outline=ctx.line_color)
        ctx.draw.line((d, e), fill=ctx.secondary_color, width=ctx.line_width)
        construction["parallel_segment"] = _line_bbox((d, e), ctx, pad=ctx.line_width + 3)
        construction["base_parallel_mark"] = _draw_parallel_mark(ctx, left_base, right_base, count=1)
        construction["splitter_parallel_mark"] = _draw_parallel_mark(ctx, d, e, count=1)
        for label, point, direction in (
            ("A", apex, (0.0, -1.0)),
            ("B", left_base, (-1.0, 1.0)),
            ("C", right_base, (1.0, 1.0)),
            ("D", d, (-1.0, 0.0)),
            ("E", e, (1.0, 0.0)),
        ):
            point_label_bboxes[label] = _bbox_to_list(_draw_point_label(ctx, label, point, direction))
        readouts["left_top_label"] = _draw_text_centered(ctx, labels["left_top"], _add(_mid(apex, d), (-30.0, -7.0)), small=True)
        readouts["left_bottom_label"] = _draw_text_centered(ctx, labels["left_bottom"], _add(_mid(d, left_base), (-36.0, 8.0)), small=True)
        readouts["right_top_label"] = _draw_text_centered(ctx, labels["right_top"], _add(_mid(apex, e), (31.0, -7.0)), small=True)
        readouts["right_bottom_label"] = _draw_text_centered(ctx, labels["right_bottom"], _add(_mid(e, right_base), (40.0, 8.0)), small=True)
        annotation = {
            "left_top_segment_start": apex,
            "left_top_segment_end": d,
            "left_bottom_segment_start": d,
            "left_bottom_segment_end": left_base,
            "right_top_segment_start": apex,
            "right_top_segment_end": e,
            "right_bottom_segment_start": e,
            "right_bottom_segment_end": right_base,
        }
        vertex_payload = {"A": apex, "B": left_base, "C": right_base, "D": d, "E": e}
    else:
        x0 = ctx.width * 0.25 + rng.uniform(-8.0, 8.0)
        x1 = ctx.width * 0.75 + rng.uniform(-8.0, 8.0)
        ys = (ctx.height * 0.25 + rng.uniform(-6.0, 6.0), ctx.height * 0.50 + rng.uniform(-6.0, 6.0), ctx.height * 0.75 + rng.uniform(-6.0, 6.0))
        left = ((x0 - 62.0, ys[0]), (x0, ys[1]), (x0 + 62.0, ys[2]))
        right = ((x1 - 45.0, ys[0]), (x1, ys[1]), (x1 + 45.0, ys[2]))
        raw_parallel_lines = tuple(((ctx.width * 0.14, y), (ctx.width * 0.86, y)) for y in ys)
        ctx.scene_transform.resolve((*left, *right, *(point for segment in raw_parallel_lines for point in segment)))
        left = ctx.scene_transform.points(left)
        right = ctx.scene_transform.points(right)
        parallel_lines = tuple(tuple(ctx.scene_transform.points(segment)) for segment in raw_parallel_lines)
        for row, (p0, p1) in enumerate(parallel_lines):
            ctx.draw.line((p0, p1), fill=ctx.muted_color, width=max(2, ctx.line_width - 1))
            construction[f"parallel_line_{row}"] = _line_bbox((p0, p1), ctx, pad=ctx.line_width + 2)
            construction[f"parallel_mark_{row}"] = _draw_parallel_mark(ctx, p0, p1, count=1)
        ctx.draw.line(left, fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line(right, fill=ctx.secondary_color, width=ctx.line_width)
        construction["left_transversal"] = _line_bbox(left, ctx, pad=ctx.line_width + 3)
        construction["right_transversal"] = _line_bbox(right, ctx, pad=ctx.line_width + 3)
        for label, point, direction in (
            ("A", left[0], (-1.0, -1.0)),
            ("B", left[1], (-1.0, 0.0)),
            ("C", left[2], (-1.0, 1.0)),
            ("U", right[0], (1.0, -1.0)),
            ("V", right[1], (1.0, 0.0)),
            ("W", right[2], (1.0, 1.0)),
        ):
            point_label_bboxes[label] = _bbox_to_list(_draw_point_label(ctx, label, point, direction))
        readouts["left_top_label"] = _draw_text_centered(ctx, labels["left_top"], _add(_mid(left[0], left[1]), (-42.0, -2.0)), small=True)
        readouts["left_bottom_label"] = _draw_text_centered(ctx, labels["left_bottom"], _add(_mid(left[1], left[2]), (-45.0, 3.0)), small=True)
        readouts["right_top_label"] = _draw_text_centered(ctx, labels["right_top"], _add(_mid(right[0], right[1]), (44.0, -2.0)), small=True)
        readouts["right_bottom_label"] = _draw_text_centered(ctx, labels["right_bottom"], _add(_mid(right[1], right[2]), (45.0, 3.0)), small=True)
        annotation = {
            "left_top_segment_start": left[0],
            "left_top_segment_end": left[1],
            "left_bottom_segment_start": left[1],
            "left_bottom_segment_end": left[2],
            "right_top_segment_start": right[0],
            "right_top_segment_end": right[1],
            "right_bottom_segment_start": right[1],
            "right_bottom_segment_end": right[2],
        }
        vertex_payload = {"A": left[0], "B": left[1], "C": left[2], "U": right[0], "V": right[1], "W": right[2]}
    render_map = {
        "vertices": {label: _point_to_list(point) for label, point in vertex_payload.items()},
        "point_label_bboxes": point_label_bboxes,
        "readout_bboxes": _json_ready(readouts),
        "construction_bboxes": _json_ready(construction),
    }
    return _RenderedScene(ctx.image, annotation, render_map)


def _render_problem(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    if problem.case.draw_kind in {"triangle_side_splitter", "parallel_transversals"}:
        return _render_parallel(problem, ctx)
    if problem.scene_id == SIMILAR_SCENE_ID:
        return _render_similar_pair(problem, ctx)
    if problem.scene_id == MARKED_POLYGON_SCENE_ID:
        return _render_marked_polygon(problem, ctx)
    raise ValueError(f"unknown scene_id={problem.scene_id!r}")


def _make_prompt_examples(annotation_keys: Sequence[str], *, answer: float) -> tuple[str, str]:
    answer_value = _num(answer)
    return build_keyed_point_prompt_json_examples(annotation_keys=annotation_keys, answer=answer_value)


@dataclass(frozen=True)
class ParallelSegmentProportionArtifact:
    prompt: str
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Image.Image
    image_id: str
    trace_payload: Dict[str, Any]
    task_versions: Mapping[str, str]
    scene_id: str
    query_id: str
    prompt_variants: Dict[str, Any]


class ParallelSegmentProportionRuntime:
    domain = "geometry"
    default_dataset_enabled = True

    task_id: str
    scene_id: str
    public_scene_id: str
    case_family: str

    def __init__(self, *, runtime_namespace: str, case_family: str, scene_id: str) -> None:
        self.task_id = str(runtime_namespace)
        self.case_family = str(case_family)
        self.scene_id = str(scene_id)
        self.public_scene_id = str(scene_id)

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> ParallelSegmentProportionArtifact:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                problem = _select_problem(self.case_family, int(instance_seed) + int(attempt), params)
                ctx = _build_context(
                    scene_id=problem.scene_id,
                    instance_seed=int(instance_seed) + int(attempt),
                    params=params,
                    rendering_defaults=rendering_defaults,
                )
                rendered = _render_problem(problem, ctx)
                break
            except Exception as exc:
                last_error = exc
                continue
        else:
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
                "annotation_hint",
                "answer_hint_number",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_keys = tuple(rendered.annotation_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys, answer=float(problem.case.answer))
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=str(getattr(self, "scene_id", "") or getattr(self, "public_scene_id", "") or globals().get("SCENE_ID", "")),
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_name": str(problem.case.target_name),
                "variable_name": str(problem.case.variable_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_value = _num(problem.case.answer)
        annotation_value = {key: _point_to_list(point) for key, point in rendered.annotation_points.items()}
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": str(self.scene_id or self.public_scene_id),
                "task_id": self.task_id,
                "scene_id": problem.scene_id,
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": "marked_geometry_diagram",
                        "scene_id": str(problem.scene_id),
                        "shape_kind": str(problem.case.shape_kind),
                        "render_map": dict(rendered.render_map),
                    },
                ],
                "relations": {
                    "type": str(problem.case.relation),
                    "query_id": str(problem.query_id),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": problem.scene_id,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "case_index": int(problem.case_index),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
                "scene_id": problem.scene_id,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
                **(
                    {"single_object_scene_rotation": ctx.scene_transform.metadata()}
                    if problem.scene_id in {MARKED_POLYGON_SCENE_ID, PARALLEL_SCENE_ID}
                    else {}
                ),
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
                "task_id": self.task_id,
                "scene_id": problem.scene_id,
                "query_id": str(problem.query_id),
                "target_name": str(problem.case.target_name),
                "variable_name": str(problem.case.variable_name),
                "relation": str(problem.case.relation),
                "answer": answer_value,
                "labels": dict(problem.case.labels or {}),
                "measures": dict(problem.case.measures or {}),
                "annotation_roles": list(annotation_keys),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": problem.scene_id,
                "query_id": str(problem.query_id),
                "target_name": str(problem.case.target_name),
                "answer": answer_value,
                "labels": dict(problem.case.labels or {}),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        return ParallelSegmentProportionArtifact(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="number", value=answer_value),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=problem.scene_id,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )








__all__ = [
    "MARKED_ANGLE_VALUE_TASK_KEY",
    "MARKED_ANGLE_VARIABLE_TASK_KEY",
    "MARKED_POLYGON_SCENE_ID",
    "MARKED_SIDE_LENGTH_TASK_KEY",
    "MARKED_SIDE_VARIABLE_TASK_KEY",
    "ParallelSegmentProportionArtifact",
    "ParallelSegmentProportionRuntime",
]
