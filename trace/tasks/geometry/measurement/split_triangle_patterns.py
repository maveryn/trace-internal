"""Geometry3K-style split-triangle measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font
from ..shared.complexity import build_geometry_measurement_complexity, normalize_linear
from ..shared.diagram_style import prepare_geometry_diagram_style_and_background
from ..shared.fixed_query_task import geometry_query_ids_for_task, geometry_selected_probability_map as _probability_map
from ..shared.measurement_rendering import bbox_from_points, bbox_to_list, draw_label_backplate, pad_bbox, readout_text_metadata
from ..shared.metadata_serialization import geometry_json_ready as _json_ready
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.scene_transform import LazySceneTransform
from ..shared.vector2d import (
    add_scaled as _add,
    mid as _mid,
    perp as _perp,
    point_to_list as _point_to_list,
    sub as _sub,
    unit as _unit,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_split_triangle_patterns_v0"
ANGLE_SCENE_ID = "split_triangle_angle_chase"
TRIG_SCENE_ID = "split_triangle_trig_chain"
TRIANGLE_RELATIONS_SCENE_ID = "triangle_relations"

ANGLE_TASK_ID = "task_geometry__split_triangle_angle_chase__target_angle_value"
BISECTOR_VARIABLE_TASK_ID = "task_geometry__triangle_relations__angle_bisector_variable_value"
TRIG_CHAIN_TASK_ID = "task_geometry__split_triangle_trig_chain__side_length_value"

ANGLE_QUERY_IDS: Tuple[str, ...] = (
    "single_cevian_triangle_angle_sum",
    "shared_vertex_split_angle_sum",
    "two_step_adjacent_triangle_angle_sum",
)
BISECTOR_QUERY_IDS: Tuple[str, ...] = (
    "split_segment_ratio_variable",
    "adjacent_side_ratio_variable",
)
TRIG_QUERY_IDS: Tuple[str, ...] = (
    "shared_altitude_two_angles_side",
    "shared_altitude_side_then_hypotenuse",
    "isosceles_altitude_trig_side",
)
DEGREE_SYMBOL = chr(176)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)


@dataclass(frozen=True)
class _Case:
    task_id: str
    scene_id: str
    query_id: str
    relation: str
    answer: float | int
    target_name: str
    answer_type: str
    labels: Mapping[str, str]
    values: Mapping[str, float | int | str]
    variable_name: str = "x"


@dataclass(frozen=True)
class _ResolvedProblem:
    task_id: str
    scene_id: str
    query_id: str
    case: _Case
    query_probabilities: Dict[str, float]
    case_index: int
    query_ids: Tuple[str, ...]


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
    label_backing_color: Color
    fill_color: Color
    alt_fill_color: Color
    muted_color: Color
    accent_color: Color
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


def _num(value: float | int) -> float | int:
    rounded = round(float(value), 1)
    if abs(rounded - round(rounded)) < 1e-9:
        return int(round(rounded))
    return float(rounded)


def _segment_label_offset(a: Point, b: Point, distance: float) -> Point:
    return _perp(_unit(_sub(b, a)))[0] * float(distance), _perp(_unit(_sub(b, a)))[1] * float(distance)


def _line_bbox(points: Sequence[Point], ctx: _RenderContext, *, pad: float = 5.0) -> BBox:
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=pad)


def _build_context(
    *,
    scene_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", group_default(rendering_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(rendering_defaults, "canvas_height", 580)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=str(scene_id),
        task_group=TASK_GROUP,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=False,
        require_grid=False,
    )
    image = image.convert("RGB")
    font_size = int(params.get("label_font_size", group_default(rendering_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(rendering_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(rendering_defaults, "line_width", 3)))
    label_stroke_width = int(params.get("label_stroke_width", group_default(rendering_defaults, "label_stroke_width", 1)))
    return _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        label_backing_color=tuple(int(value) for value in diagram_style.panel_fill_rgb),
        fill_color=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        alt_fill_color=tuple(int(value) for value in diagram_style.option_fill_rgb),
        muted_color=tuple(int(value) for value in diagram_style.guide_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, min(1, int(label_stroke_width))),
        font=load_font(max(12, int(font_size)), bold=False),
        small_font=load_font(max(10, int(small_font_size)), bold=False),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{scene_id}.scene_rotation"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True, required: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    draw_label_backplate(ctx, bbox)
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
        required=bool(required),
        extra_metadata=readout_text_metadata(ctx, ctx.label_color),
    )
    return pad_bbox(bbox, 4.0, width=ctx.width, height=ctx.height)


def _draw_polygon(ctx: _RenderContext, points: Sequence[Point], *, fill: Color | None = None) -> BBox:
    polygon = [(float(x), float(y)) for x, y in points]
    ctx.draw.polygon(polygon, fill=fill or ctx.fill_color)
    ctx.draw.line(polygon + [polygon[0]], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    return bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_segment(ctx: _RenderContext, a: Point, b: Point, *, color: Color | None = None) -> BBox:
    ctx.draw.line((a, b), fill=color or ctx.secondary_color, width=ctx.line_width)
    return _line_bbox((a, b), ctx, pad=ctx.line_width + 3)


def _draw_side_label(ctx: _RenderContext, a: Point, b: Point, text: str, *, offset: float) -> BBox:
    return _draw_text_centered(ctx, str(text), _add(_mid(a, b), _segment_label_offset(a, b, offset)), small=True)


def _draw_point_label(ctx: _RenderContext, label: str, point: Point, direction: Point, *, offset: float = 22.0) -> BBox:
    return _draw_text_centered(ctx, str(label), _add(point, _unit(direction), offset), small=True, required=False)


def _draw_tick(ctx: _RenderContext, a: Point, b: Point, *, count: int = 1) -> BBox:
    center = _mid(a, b)
    tangent = _unit(_sub(b, a))
    normal = _perp(tangent)
    tick_points: list[Point] = []
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * 9.0
        tick_center = _add(center, tangent, shift)
        p0 = _add(tick_center, normal, -9.0)
        p1 = _add(tick_center, normal, 9.0)
        ctx.draw.line((p0, p1), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        tick_points.extend([p0, p1])
    return _line_bbox(tick_points, ctx, pad=4.0)


def _draw_right_angle(ctx: _RenderContext, vertex: Point, ray_a: Point, ray_b: Point, *, size: float = 20.0) -> BBox:
    u = _unit(_sub(ray_a, vertex))
    v = _unit(_sub(ray_b, vertex))
    p1 = _add(vertex, u, size)
    p2 = _add(p1, v, size)
    p3 = _add(vertex, v, size)
    ctx.draw.line((p1, p2, p3), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    return _line_bbox((p1, p2, p3), ctx, pad=4.0)


def _draw_angle_arc(ctx: _RenderContext, vertex: Point, ray_a: Point, ray_b: Point, *, radius: float = 30.0) -> BBox:
    start = math.atan2(float(ray_a[1]) - float(vertex[1]), float(ray_a[0]) - float(vertex[0]))
    end = math.atan2(float(ray_b[1]) - float(vertex[1]), float(ray_b[0]) - float(vertex[0]))
    delta = (end - start + math.pi) % (2.0 * math.pi) - math.pi
    steps = 16
    points = [
        (
            float(vertex[0]) + math.cos(start + delta * (index / steps)) * float(radius),
            float(vertex[1]) + math.sin(start + delta * (index / steps)) * float(radius),
        )
        for index in range(steps + 1)
    ]
    ctx.draw.line(points, fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    return _line_bbox(points, ctx, pad=4.0)


def _angle_point(vertex: Point, ray_a: Point, ray_b: Point, radius: float = 42.0) -> Point:
    direction = _unit(_add(_unit(_sub(ray_a, vertex)), _unit(_sub(ray_b, vertex))))
    if math.hypot(direction[0], direction[1]) <= 1e-9:
        direction = _perp(_unit(_sub(ray_a, vertex)))
    return _add(vertex, direction, radius)


def _draw_angle_label(ctx: _RenderContext, text: str, vertex: Point, ray_a: Point, ray_b: Point, *, radius: float = 42.0) -> Tuple[BBox, Point]:
    point = _angle_point(vertex, ray_a, ray_b, radius=radius)
    bbox = _draw_text_centered(ctx, str(text), point, small=True)
    return bbox, point


def _split_triangle_points(ctx: _RenderContext, *, instance_seed: int) -> Dict[str, Point]:
    rng = spawn_rng(int(instance_seed), "split_triangle.points")
    top_y = ctx.height * 0.22 + rng.uniform(-12.0, 12.0)
    left_x = ctx.width * 0.18 + rng.uniform(-10.0, 16.0)
    right_x = ctx.width * 0.82 + rng.uniform(-16.0, 10.0)
    split_x = ctx.width * 0.50 + rng.uniform(-32.0, 32.0)
    apex = (ctx.width * 0.50 + rng.uniform(-18.0, 18.0), ctx.height * 0.78 + rng.uniform(-14.0, 12.0))
    points = {
        "A": (left_x, top_y),
        "B": (split_x, top_y + rng.uniform(-4.0, 4.0)),
        "C": (right_x, top_y),
        "D": apex,
    }
    return {
        key: value
        for key, value in zip(points.keys(), ctx.scene_transform.points(tuple(points.values())))
    }


def _right_triangle_points(ctx: _RenderContext, *, instance_seed: int) -> Dict[str, Point]:
    rng = spawn_rng(int(instance_seed), "split_triangle.right_points")
    base_y = ctx.height * 0.76 + rng.uniform(-12.0, 12.0)
    left = (ctx.width * 0.18 + rng.uniform(-10.0, 12.0), base_y)
    right = (ctx.width * 0.82 + rng.uniform(-12.0, 10.0), base_y + rng.uniform(-4.0, 4.0))
    foot = (ctx.width * 0.50 + rng.uniform(-20.0, 20.0), base_y)
    top = (foot[0] + rng.uniform(-8.0, 8.0), ctx.height * 0.20 + rng.uniform(-8.0, 12.0))
    points = {"A": top, "B": left, "C": right, "D": foot}
    return {
        key: value
        for key, value in zip(points.keys(), ctx.scene_transform.points(tuple(points.values())))
    }


def _angle_cases() -> Tuple[_Case, ...]:
    rows = [
        ("single_cevian_triangle_angle_sum", 42, 72, 66),
        ("single_cevian_triangle_angle_sum", 55, 47, 78),
        ("single_cevian_triangle_angle_sum", 38, 84, 58),
        ("single_cevian_triangle_angle_sum", 63, 46, 71),
        ("single_cevian_triangle_angle_sum", 48, 69, 63),
        ("single_cevian_triangle_angle_sum", 36, 92, 52),
        ("single_cevian_triangle_angle_sum", 44, 62, 74),
        ("single_cevian_triangle_angle_sum", 50, 46, 84),
        ("single_cevian_triangle_angle_sum", 67, 58, 55),
        ("single_cevian_triangle_angle_sum", 39, 72, 69),
        ("shared_vertex_split_angle_sum", 51, 57, 72),
        ("shared_vertex_split_angle_sum", 44, 68, 68),
        ("shared_vertex_split_angle_sum", 62, 41, 77),
        ("shared_vertex_split_angle_sum", 35, 83, 62),
        ("shared_vertex_split_angle_sum", 58, 52, 70),
        ("two_step_adjacent_triangle_angle_sum", 51, 49, 33),
        ("two_step_adjacent_triangle_angle_sum", 42, 66, 38),
        ("two_step_adjacent_triangle_angle_sum", 55, 35, 47),
        ("two_step_adjacent_triangle_angle_sum", 48, 54, 39),
        ("two_step_adjacent_triangle_angle_sum", 60, 42, 36),
        ("two_step_adjacent_triangle_angle_sum", 46, 58, 26),
        ("two_step_adjacent_triangle_angle_sum", 38, 63, 23),
        ("two_step_adjacent_triangle_angle_sum", 44, 51, 21),
        ("two_step_adjacent_triangle_angle_sum", 57, 48, 38),
        ("two_step_adjacent_triangle_angle_sum", 49, 57, 29),
    ]
    cases: list[_Case] = []
    for query_id, a, b, c in rows:
        if query_id == "two_step_adjacent_triangle_angle_sum":
            left_b = 180 - int(a) - int(b)
            right_b = 180 - int(left_b)
            answer = 180 - int(right_b) - int(c)
            labels = {
                "given_left_A": f"{int(a)}{DEGREE_SYMBOL}",
                "given_left_D": f"{int(b)}{DEGREE_SYMBOL}",
                "given_right_C": f"{int(c)}{DEGREE_SYMBOL}",
                "target": "?",
            }
        elif query_id == "shared_vertex_split_angle_sum":
            answer = int(c)
            labels = {
                "given_left_A": f"{int(a)}{DEGREE_SYMBOL}",
                "given_left_D": f"{int(b)}{DEGREE_SYMBOL}",
                "target": "?",
            }
        else:
            answer = int(c)
            labels = {
                "given_left_A": f"{int(a)}{DEGREE_SYMBOL}",
                "given_left_B": f"{int(b)}{DEGREE_SYMBOL}",
                "target": "?",
            }
        cases.append(
            _Case(
                task_id=ANGLE_TASK_ID,
                scene_id=ANGLE_SCENE_ID,
                query_id=str(query_id),
                relation="split_triangle_angle_sum",
                answer=int(answer),
                target_name="the marked angle",
                answer_type="integer",
                labels=labels,
                values={"angle_a": int(a), "angle_b": int(b), "angle_c": int(c), "answer": int(answer)},
            )
        )
    return tuple(cases)


def _bisector_cases() -> Tuple[_Case, ...]:
    rows = [
        ("split_segment_ratio_variable", 12, 18, 8, 4, 8),
        ("split_segment_ratio_variable", 10, 15, 6, 3, 6),
        ("split_segment_ratio_variable", 14, 21, 10, 5, 10),
        ("split_segment_ratio_variable", 9, 12, 8, 15, 12),
        ("split_segment_ratio_variable", 15, 20, 9, 3, 9),
        ("split_segment_ratio_variable", 10, 15, 5, 8, 7),
        ("split_segment_ratio_variable", 12, 16, 9, 15, 11),
        ("adjacent_side_ratio_variable", 5, 8, 3, 16, 7),
        ("adjacent_side_ratio_variable", 6, 9, 4, 18, 8),
        ("adjacent_side_ratio_variable", 4, 7, 2, 21, 10),
        ("adjacent_side_ratio_variable", 7, 10, 5, 20, 9),
        ("adjacent_side_ratio_variable", 8, 12, 6, 24, 10),
        ("adjacent_side_ratio_variable", 5, 10, 4, 20, 6),
        ("adjacent_side_ratio_variable", 6, 8, 4, 20, 11),
        ("adjacent_side_ratio_variable", 7, 14, 3, 30, 12),
    ]
    cases: list[_Case] = []
    for query_id, left_num, right_num, addend, known, answer in rows:
        if query_id == "split_segment_ratio_variable":
            labels = {"AB": str(left_num), "AC": str(right_num), "BD": str(known), "DC": f"x+{addend}"}
        else:
            labels = {"BD": str(left_num), "DC": str(right_num), "AB": f"x+{addend}", "AC": str(known)}
        cases.append(
            _Case(
                task_id=BISECTOR_VARIABLE_TASK_ID,
                scene_id=TRIANGLE_RELATIONS_SCENE_ID,
                query_id=str(query_id),
                relation="angle_bisector_theorem_variable",
                answer=int(answer),
                target_name="x",
                answer_type="integer",
                labels=labels,
                values={"answer": int(answer)},
            )
        )
    return tuple(cases)


def _trig_cases() -> Tuple[_Case, ...]:
    rows = [
        ("shared_altitude_two_angles_side", 12.0, 55.0, 47.0),
        ("shared_altitude_two_angles_side", 10.0, 50.0, 38.0),
        ("shared_altitude_two_angles_side", 14.0, 42.0, 52.0),
        ("shared_altitude_two_angles_side", 9.0, 63.0, 45.0),
        ("shared_altitude_two_angles_side", 16.0, 36.0, 58.0),
        ("shared_altitude_side_then_hypotenuse", 18.0, 48.0, 41.0),
        ("shared_altitude_side_then_hypotenuse", 20.0, 37.0, 54.0),
        ("shared_altitude_side_then_hypotenuse", 15.0, 62.0, 46.0),
        ("shared_altitude_side_then_hypotenuse", 22.0, 44.0, 39.0),
        ("shared_altitude_side_then_hypotenuse", 17.0, 55.0, 51.0),
        ("isosceles_altitude_trig_side", 8.0, 45.0, 45.0),
        ("isosceles_altitude_trig_side", 10.0, 52.0, 52.0),
        ("isosceles_altitude_trig_side", 7.0, 38.0, 38.0),
        ("isosceles_altitude_trig_side", 12.0, 57.0, 57.0),
        ("isosceles_altitude_trig_side", 9.0, 49.0, 49.0),
    ]
    cases: list[_Case] = []
    for query_id, value, left_angle, right_angle in rows:
        if query_id == "shared_altitude_two_angles_side":
            altitude = value * math.tan(math.radians(left_angle))
            answer = altitude / math.sin(math.radians(right_angle))
            labels = {"BD": f"{_num(value)}", "angle_B": f"{int(left_angle)}{DEGREE_SYMBOL}", "angle_C": f"{int(right_angle)}{DEGREE_SYMBOL}", "AC": "?"}
            target_name = "AC"
        elif query_id == "shared_altitude_side_then_hypotenuse":
            altitude = value * math.sin(math.radians(left_angle))
            answer = altitude / math.sin(math.radians(right_angle))
            labels = {"AB": f"{_num(value)}", "angle_B": f"{int(left_angle)}{DEGREE_SYMBOL}", "angle_C": f"{int(right_angle)}{DEGREE_SYMBOL}", "AC": "?"}
            target_name = "AC"
        else:
            answer = value / math.cos(math.radians(left_angle))
            labels = {"BD": f"{_num(value)}", "angle_B": f"{int(left_angle)}{DEGREE_SYMBOL}", "AB": "?"}
            target_name = "AB"
        cases.append(
            _Case(
                task_id=TRIG_CHAIN_TASK_ID,
                scene_id=TRIG_SCENE_ID,
                query_id=str(query_id),
                relation="split_triangle_trig_chain",
                answer=float(round(answer, 1)),
                target_name=str(target_name),
                answer_type="number",
                labels=labels,
                values={"known_value": float(value), "left_angle": float(left_angle), "right_angle": float(right_angle), "answer": float(round(answer, 1))},
            )
        )
    return tuple(cases)


def _cases_for_task(task_id: str) -> Tuple[_Case, ...]:
    if task_id == ANGLE_TASK_ID:
        return _angle_cases()
    if task_id == BISECTOR_VARIABLE_TASK_ID:
        return _bisector_cases()
    if task_id == TRIG_CHAIN_TASK_ID:
        return _trig_cases()
    raise ValueError(f"unknown split-triangle task_id={task_id!r}")


_QUERY_IDS_BY_TASK_ID: Dict[str, Tuple[str, ...]] = {
    ANGLE_TASK_ID: ANGLE_QUERY_IDS,
    BISECTOR_VARIABLE_TASK_ID: BISECTOR_QUERY_IDS,
    TRIG_CHAIN_TASK_ID: TRIG_QUERY_IDS,
}


def _select_problem(task_id: str, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    query_ids = geometry_query_ids_for_task(
        task_id,
        _QUERY_IDS_BY_TASK_ID,
        context="split-triangle",
    )
    forced_query = params.get("query_id")
    if forced_query is not None:
        query_id = str(forced_query)
        if query_id not in query_ids:
            raise ValueError(f"query_id={query_id!r} is not supported by {task_id}")
    else:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.query_id")
        query_id = query_ids[int(index) % len(query_ids)]
    query_probabilities = _probability_map(query_ids, selected=str(query_id) if forced_query is not None else None)
    cases = tuple(case for case in _cases_for_task(task_id) if case.query_id == query_id)
    case_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.{query_id}.case")
    case = cases[int(case_index) % len(cases)]
    return _ResolvedProblem(
        task_id=str(task_id),
        scene_id=str(case.scene_id),
        query_id=str(query_id),
        case=case,
        query_probabilities=dict(query_probabilities),
        case_index=int(case_index) % len(cases),
        query_ids=query_ids,
    )


def _render_angle_case(problem: _ResolvedProblem, ctx: _RenderContext, *, instance_seed: int) -> _RenderedScene:
    pts = _split_triangle_points(ctx, instance_seed=instance_seed)
    labels = dict(problem.case.labels)
    construction: Dict[str, BBox] = {
        "left_triangle": _draw_polygon(ctx, (pts["A"], pts["B"], pts["D"]), fill=ctx.fill_color),
        "right_triangle": _draw_polygon(ctx, (pts["B"], pts["C"], pts["D"]), fill=ctx.alt_fill_color),
        "split_segment": _draw_segment(ctx, pts["B"], pts["D"], color=ctx.secondary_color),
    }
    point_labels = {
        "A": bbox_to_list(_draw_point_label(ctx, "A", pts["A"], (-1.0, -1.0))),
        "B": bbox_to_list(_draw_point_label(ctx, "B", pts["B"], (0.0, -1.0))),
        "C": bbox_to_list(_draw_point_label(ctx, "C", pts["C"], (1.0, -1.0))),
        "D": bbox_to_list(_draw_point_label(ctx, "D", pts["D"], (0.0, 1.0))),
    }
    readouts: Dict[str, Any] = {}
    annotation: Dict[str, Point] = {}
    if problem.query_id == "single_cevian_triangle_angle_sum":
        _, p_a = _draw_angle_label(ctx, labels["given_left_A"], pts["A"], pts["B"], pts["D"], radius=50.0)
        _, p_b = _draw_angle_label(ctx, labels["given_left_B"], pts["B"], pts["A"], pts["D"], radius=50.0)
        _, p_t = _draw_angle_label(ctx, labels["target"], pts["D"], pts["A"], pts["B"], radius=58.0)
        annotation = {"target_angle": p_t, "given_angle_1": p_a, "given_angle_2": p_b}
    elif problem.query_id == "shared_vertex_split_angle_sum":
        _, p_a = _draw_angle_label(ctx, labels["given_left_A"], pts["A"], pts["B"], pts["D"], radius=50.0)
        _, p_d = _draw_angle_label(ctx, labels["given_left_D"], pts["D"], pts["A"], pts["B"], radius=58.0)
        _, p_t = _draw_angle_label(ctx, labels["target"], pts["B"], pts["A"], pts["D"], radius=50.0)
        annotation = {"target_angle": p_t, "given_angle_1": p_a, "given_angle_2": p_d}
    else:
        _, p_a = _draw_angle_label(ctx, labels["given_left_A"], pts["A"], pts["B"], pts["D"], radius=50.0)
        _, p_d = _draw_angle_label(ctx, labels["given_left_D"], pts["D"], pts["A"], pts["B"], radius=58.0)
        _, p_c = _draw_angle_label(ctx, labels["given_right_C"], pts["C"], pts["B"], pts["D"], radius=50.0)
        _, p_t = _draw_angle_label(ctx, labels["target"], pts["D"], pts["B"], pts["C"], radius=58.0)
        annotation = {"target_angle": p_t, "given_angle_1": p_a, "given_angle_2": p_d, "given_angle_3": p_c, "shared_straight_angle_vertex": pts["B"]}
    render_map = {
        "vertices": {key: _point_to_list(value) for key, value in pts.items()},
        "point_label_bboxes": point_labels,
        "construction_bboxes": _json_ready(construction),
        "readout_bboxes": _json_ready(readouts),
    }
    return _RenderedScene(ctx.image, annotation, render_map)


def _render_bisector_case(problem: _ResolvedProblem, ctx: _RenderContext, *, instance_seed: int) -> _RenderedScene:
    pts = _right_triangle_points(ctx, instance_seed=instance_seed)
    # Rename to a general triangle: A is vertex, B/C base, D split point.
    labels = dict(problem.case.labels)
    construction: Dict[str, BBox] = {
        "triangle": _draw_polygon(ctx, (pts["A"], pts["B"], pts["C"]), fill=ctx.fill_color),
        "angle_bisector": _draw_segment(ctx, pts["A"], pts["D"], color=ctx.secondary_color),
        "left_angle_mark": _draw_angle_arc(ctx, pts["A"], pts["B"], pts["D"], radius=34.0),
        "right_angle_mark": _draw_angle_arc(ctx, pts["A"], pts["D"], pts["C"], radius=34.0),
    }
    point_labels = {
        label: bbox_to_list(_draw_point_label(ctx, label, pts[label], direction))
        for label, direction in (("A", (0.0, -1.0)), ("B", (-1.0, 1.0)), ("C", (1.0, 1.0)), ("D", (0.0, 1.0)))
    }
    readouts = {
        "AB": _draw_side_label(ctx, pts["A"], pts["B"], labels["AB"], offset=-36.0),
        "AC": _draw_side_label(ctx, pts["A"], pts["C"], labels["AC"], offset=36.0),
        "BD": _draw_side_label(ctx, pts["B"], pts["D"], labels["BD"], offset=30.0),
        "DC": _draw_side_label(ctx, pts["D"], pts["C"], labels["DC"], offset=30.0),
    }
    annotation = {
        "angle_vertex": pts["A"],
        "split_point": pts["D"],
        "left_side_start": pts["A"],
        "left_side_end": pts["B"],
        "right_side_start": pts["A"],
        "right_side_end": pts["C"],
        "left_split_start": pts["B"],
        "left_split_end": pts["D"],
        "right_split_start": pts["D"],
        "right_split_end": pts["C"],
    }
    render_map = {
        "vertices": {key: _point_to_list(value) for key, value in pts.items()},
        "point_label_bboxes": point_labels,
        "construction_bboxes": _json_ready(construction),
        "readout_bboxes": _json_ready(readouts),
    }
    return _RenderedScene(ctx.image, annotation, render_map)


def _render_trig_case(problem: _ResolvedProblem, ctx: _RenderContext, *, instance_seed: int) -> _RenderedScene:
    pts = _right_triangle_points(ctx, instance_seed=instance_seed)
    labels = dict(problem.case.labels)
    construction: Dict[str, BBox] = {
        "left_triangle": _draw_polygon(ctx, (pts["A"], pts["B"], pts["D"]), fill=ctx.fill_color),
        "right_triangle": _draw_polygon(ctx, (pts["A"], pts["D"], pts["C"]), fill=ctx.alt_fill_color),
        "altitude": _draw_segment(ctx, pts["A"], pts["D"], color=ctx.secondary_color),
        "right_angle": _draw_right_angle(ctx, pts["D"], pts["A"], pts["C"], size=20.0),
    }
    if problem.query_id == "isosceles_altitude_trig_side":
        construction["left_side_tick"] = _draw_tick(ctx, pts["A"], pts["B"], count=1)
        construction["right_side_tick"] = _draw_tick(ctx, pts["A"], pts["C"], count=1)
        construction["left_base_tick"] = _draw_tick(ctx, pts["B"], pts["D"], count=2)
        construction["right_base_tick"] = _draw_tick(ctx, pts["D"], pts["C"], count=2)
    point_labels = {
        label: bbox_to_list(_draw_point_label(ctx, label, pts[label], direction))
        for label, direction in (("A", (0.0, -1.0)), ("B", (-1.0, 1.0)), ("C", (1.0, 1.0)), ("D", (0.0, 1.0)))
    }
    readouts: Dict[str, BBox] = {}
    annotation: Dict[str, Point]
    if "BD" in labels and labels["BD"] != "?":
        readouts["BD"] = _draw_side_label(ctx, pts["B"], pts["D"], labels["BD"], offset=32.0)
    if "AB" in labels and labels["AB"] != "?":
        readouts["AB"] = _draw_side_label(ctx, pts["A"], pts["B"], labels["AB"], offset=-36.0)
    if "AC" in labels and labels["AC"] != "?":
        readouts["AC"] = _draw_side_label(ctx, pts["A"], pts["C"], labels["AC"], offset=36.0)
    if "angle_B" in labels:
        _, p_b = _draw_angle_label(ctx, labels["angle_B"], pts["B"], pts["A"], pts["D"], radius=52.0)
    else:
        p_b = _angle_point(pts["B"], pts["A"], pts["D"], radius=52.0)
    if "angle_C" in labels:
        _, p_c = _draw_angle_label(ctx, labels["angle_C"], pts["C"], pts["D"], pts["A"], radius=52.0)
    else:
        p_c = _angle_point(pts["C"], pts["D"], pts["A"], radius=52.0)
    if problem.case.target_name == "AC":
        readouts["target_AC"] = _draw_side_label(ctx, pts["A"], pts["C"], "?", offset=36.0)
        annotation = {
            "target_segment_start": pts["A"],
            "target_segment_end": pts["C"],
            "altitude_start": pts["A"],
            "altitude_end": pts["D"],
            "known_angle_left": p_b,
            "known_angle_right": p_c,
            "known_segment_start": pts["B"] if "BD" in labels else pts["A"],
            "known_segment_end": pts["D"] if "BD" in labels else pts["B"],
        }
    else:
        readouts["target_AB"] = _draw_side_label(ctx, pts["A"], pts["B"], "?", offset=-36.0)
        annotation = {
            "target_segment_start": pts["A"],
            "target_segment_end": pts["B"],
            "altitude_start": pts["A"],
            "altitude_end": pts["D"],
            "known_angle": p_b,
            "known_segment_start": pts["B"],
            "known_segment_end": pts["D"],
        }
    render_map = {
        "vertices": {key: _point_to_list(value) for key, value in pts.items()},
        "point_label_bboxes": point_labels,
        "construction_bboxes": _json_ready(construction),
        "readout_bboxes": _json_ready(readouts),
    }
    return _RenderedScene(ctx.image, annotation, render_map)


def _render_problem(problem: _ResolvedProblem, ctx: _RenderContext, *, instance_seed: int) -> _RenderedScene:
    if problem.task_id == ANGLE_TASK_ID:
        return _render_angle_case(problem, ctx, instance_seed=instance_seed)
    if problem.task_id == BISECTOR_VARIABLE_TASK_ID:
        return _render_bisector_case(problem, ctx, instance_seed=instance_seed)
    if problem.task_id == TRIG_CHAIN_TASK_ID:
        return _render_trig_case(problem, ctx, instance_seed=instance_seed)
    raise ValueError(f"unknown split-triangle task_id={problem.task_id!r}")


def _make_prompt_examples(annotation_keys: Sequence[str], *, answer: float | int) -> tuple[str, str]:
    annotation = {str(key): [160 + index * 26, 220 + (index % 3) * 24] for index, key in enumerate(annotation_keys)}
    answer_value = _num(answer)
    return dump_prompt_json_examples(annotation=annotation, answer=answer_value)


class _SplitTrianglePatternBase:
    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True

    task_id: str
    scene_id: str
    public_scene_id: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                problem = _select_problem(self.task_id, int(instance_seed), params)
                ctx = _build_context(
                    scene_id=problem.scene_id,
                    instance_seed=int(instance_seed) + int(attempt),
                    params=params,
                    rendering_defaults=rendering_defaults,
                )
                rendered = _render_problem(problem, ctx, instance_seed=int(instance_seed) + int(attempt))
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
                "answer_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_keys = tuple(rendered.annotation_points.keys())
        annotation_key_text = ", ".join(f'"{key}"' for key in annotation_keys)
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys, answer=problem.case.answer)
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
                "target_name": str(problem.case.target_name),
                "variable_name": str(problem.case.variable_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_text),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_value = _num(problem.case.answer)
        annotation_value = {str(key): _point_to_list(point) for key, point in rendered.annotation_points.items()}
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": self.task_id,
                "scene_id": problem.scene_id,
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": "split_triangle_diagram",
                        "scene_id": str(problem.scene_id),
                        "render_map": dict(rendered.render_map),
                    },
                ],
                "relations": {"type": str(problem.case.relation), "query_id": str(problem.query_id)},
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
                "single_object_scene_rotation": ctx.scene_transform.metadata(),
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
                "relation": str(problem.case.relation),
                "target_name": str(problem.case.target_name),
                "variable_name": str(problem.case.variable_name),
                "labels": dict(problem.case.labels),
                "values": dict(problem.case.values),
                "answer": answer_value,
                "annotation_roles": list(annotation_keys),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": problem.scene_id,
                "query_id": str(problem.query_id),
                "relation": str(problem.case.relation),
                "answer": answer_value,
                "labels": dict(problem.case.labels),
                "values": dict(problem.case.values),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        complexity = build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            visual_scan=0.66,
            measurement_precision=0.62 if problem.case.answer_type == "integer" else 0.72,
            ambiguity=0.42,
            output_burden=normalize_linear(len(annotation_value), min_value=3, max_value=9),
        )
        typed_answer_type = "integer" if problem.case.answer_type == "integer" else "number"
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type=typed_answer_type, value=answer_value),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=problem.scene_id,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometrySplitTriangleAngleChaseTargetAngleValueTask(_SplitTrianglePatternBase):
    """Find a missing angle in a triangle split into adjacent smaller triangles."""

    task_id = ANGLE_TASK_ID
    scene_id = ANGLE_SCENE_ID
    public_scene_id = ANGLE_SCENE_ID


@register_task
class GeometryTriangleRelationsAngleBisectorVariableValueTask(_SplitTrianglePatternBase):
    """Solve a variable from an angle-bisector theorem split triangle."""

    task_id = BISECTOR_VARIABLE_TASK_ID
    scene_id = TRIANGLE_RELATIONS_SCENE_ID
    public_scene_id = TRIANGLE_RELATIONS_SCENE_ID


@register_task
class GeometrySplitTriangleTrigChainSideLengthValueTask(_SplitTrianglePatternBase):
    """Find a side length from a split-triangle trigonometric chain."""

    task_id = TRIG_CHAIN_TASK_ID
    scene_id = TRIG_SCENE_ID
    public_scene_id = TRIG_SCENE_ID


__all__ = [
    "ANGLE_QUERY_IDS",
    "ANGLE_SCENE_ID",
    "ANGLE_TASK_ID",
    "BISECTOR_QUERY_IDS",
    "BISECTOR_VARIABLE_TASK_ID",
    "GeometrySplitTriangleAngleChaseTargetAngleValueTask",
    "GeometrySplitTriangleTrigChainSideLengthValueTask",
    "GeometryTriangleRelationsAngleBisectorVariableValueTask",
    "TRIG_CHAIN_TASK_ID",
    "TRIG_QUERY_IDS",
    "TRIG_SCENE_ID",
]
