"""Geometry3K-style split-triangle measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, bbox_to_list, draw_label_backplate, pad_bbox, readout_text_metadata
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready as _json_ready
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import (
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
PROMPT_BUNDLE_ID = "geometry_split_triangle_patterns_v0"
SCENE_ID = "split_triangle_trig_chain"
TASK_ID = "task_geometry__split_triangle_trig_chain__side_length_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "shared_altitude_two_angles_side",
    "shared_altitude_side_then_hypotenuse",
    "isosceles_altitude_trig_side",
)
DEGREE_SYMBOL = chr(176)

_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)


@dataclass(frozen=True)
class _Case:
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



def _select_problem(
    *,
    query_id: str,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    cases = tuple(case for case in _trig_cases() if case.query_id == str(query_id))
    if not cases:
        raise ValueError(f"no split-triangle trig cases for query_id={query_id!r}")
    case_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_id}.case",
    )
    case = cases[int(case_index) % len(cases)]
    return _ResolvedProblem(
        query_id=str(query_id),
        case=case,
        query_probabilities={str(key): float(value) for key, value in query_probabilities.items()},
        case_index=int(case_index) % len(cases),
        query_ids=SUPPORTED_QUERY_IDS,
    )

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
    if "BD" in labels and labels["BD"] != "?":
        readouts["BD"] = _draw_side_label(ctx, pts["B"], pts["D"], labels["BD"], offset=32.0)
    if "AB" in labels and labels["AB"] != "?":
        readouts["AB"] = _draw_side_label(ctx, pts["A"], pts["B"], labels["AB"], offset=-36.0)
    if "AC" in labels and labels["AC"] != "?":
        readouts["AC"] = _draw_side_label(ctx, pts["A"], pts["C"], labels["AC"], offset=36.0)
    if "angle_B" in labels:
        _draw_angle_label(ctx, labels["angle_B"], pts["B"], pts["A"], pts["D"], radius=52.0)
    if "angle_C" in labels:
        _draw_angle_label(ctx, labels["angle_C"], pts["C"], pts["D"], pts["A"], radius=52.0)
    if problem.case.target_name == "AC":
        readouts["target_AC"] = _draw_side_label(ctx, pts["A"], pts["C"], "?", offset=36.0)
    else:
        readouts["target_AB"] = _draw_side_label(ctx, pts["A"], pts["B"], "?", offset=-36.0)
    render_map = {
        "vertices": {key: _point_to_list(value) for key, value in pts.items()},
        "point_label_bboxes": point_labels,
        "construction_bboxes": _json_ready(construction),
        "readout_bboxes": _json_ready(readouts),
    }
    return _RenderedScene(ctx.image, dict(pts), render_map)


def _make_prompt_examples(annotation_keys: Sequence[str], *, answer: float | int) -> tuple[str, str]:
    annotation = {str(key): [160 + index * 26, 220 + (index % 3) * 24] for index, key in enumerate(annotation_keys)}
    answer_value = _num(answer)
    return dump_prompt_json_examples(annotation=annotation, answer=answer_value)



@register_task
class GeometrySplitTriangleTrigChainSideLengthValueTask:
    """Find a side length from a split-triangle trigonometric chain."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=TASK_ID,
        )
        query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                attempt_seed = int(instance_seed) + int(attempt)
                problem = _select_problem(
                    query_id=str(query_id),
                    query_probabilities=query_probabilities,
                    instance_seed=attempt_seed,
                    params=task_params,
                )
                ctx = _build_context(
                    scene_id=SCENE_ID,
                    instance_seed=attempt_seed,
                    params=task_params,
                    rendering_defaults=rendering_defaults,
                )
                rendered = _render_trig_case(problem, ctx, instance_seed=attempt_seed)
                break
            except Exception as exc:
                last_error = exc
                continue
        else:
            raise RuntimeError(f"failed to generate {TASK_ID}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=task_params,
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
            context=f"prompt defaults for {TASK_ID}",
        )
        annotation_keys = tuple(rendered.annotation_points.keys())
        annotation_key_text = ", ".join(f'"{key}"' for key in annotation_keys)
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys, answer=problem.case.answer)
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
                "scene_id": SCENE_ID,
                "task_id": TASK_ID,
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": "split_triangle_trig_diagram",
                        "scene_id": SCENE_ID,
                        "render_map": dict(rendered.render_map),
                    },
                ],
                "relations": {"type": str(problem.case.relation), "query_id": str(problem.query_id)},
            },
            "query_spec": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "case_index": int(problem.case_index),
                },
            },
            "render_spec": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
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
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "relation": str(problem.case.relation),
                "target_name": str(problem.case.target_name),
                "labels": dict(problem.case.labels),
                "values": dict(problem.case.values),
                "answer": answer_value,
                "annotation_roles": list(annotation_keys),
            },
            "witness_symbolic": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
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
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="number", value=answer_value),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometrySplitTriangleTrigChainSideLengthValueTask",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
