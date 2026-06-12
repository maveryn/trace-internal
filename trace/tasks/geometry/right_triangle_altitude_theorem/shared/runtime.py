"""Right-triangle altitude-to-hypotenuse theorem tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, pad_bbox
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready as _json_ready
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import add_scaled as _add, mid as _mid, point_to_list as _point_to_list, sub as _sub, unit as _unit


SCENE_ID = "right_triangle_altitude_theorem"
Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

PROMPT_BUNDLE_ID = "geometry_right_triangle_altitude_theorem_v0"
ALTITUDE_OBJECTIVE_KEY = "altitude_to_hypotenuse"
LEG_PROJECTION_OBJECTIVE_KEY = "leg_projection_length"

_SCENE_DEFAULTS = get_scene_defaults("geometry", "right_triangle_altitude_theorem")

_ALTITUDE_QUERY_IDS: Tuple[str, ...] = (
    "altitude_from_split_hypotenuse",
    "missing_projection_from_altitude",
)
_LEG_PROJECTION_QUERY_IDS: Tuple[str, ...] = (
    "leg_from_hypotenuse_projection",
    "projection_from_leg_and_hypotenuse",
)


@dataclass(frozen=True)
class _TheoremValues:
    left_projection: int
    right_projection: int
    altitude: int
    left_leg: int | None = None
    right_leg: int | None = None

    @property
    def hypotenuse(self) -> int:
        return int(self.left_projection) + int(self.right_projection)


@dataclass(frozen=True)
class _Case:
    query_id: str
    answer: int
    target_name: str
    target_role: str
    relation: str
    values: _TheoremValues
    visible_labels: Mapping[str, str]


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
    fill_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class _SceneGeometry:
    points: Dict[str, Point]
    labels: Dict[str, str]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    geometry: _SceneGeometry
    annotation_points: Dict[str, Point]
    point_label_bboxes: Dict[str, BBox]
    readout_bboxes: Dict[str, BBox]
    construction_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]


def _values(left_projection: int, right_projection: int, altitude: int, left_leg: int | None = None, right_leg: int | None = None) -> _TheoremValues:
    return _TheoremValues(
        left_projection=int(left_projection),
        right_projection=int(right_projection),
        altitude=int(altitude),
        left_leg=None if left_leg is None else int(left_leg),
        right_leg=None if right_leg is None else int(right_leg),
    )


_ALTITUDE_VALUE_ROWS: Tuple[_TheoremValues, ...] = (
    _values(4, 9, 6),
    _values(9, 16, 12, 15, 20),
    _values(16, 25, 20),
    _values(25, 36, 30),
    _values(18, 32, 24, 30, 40),
    _values(12, 27, 18),
    _values(36, 64, 48, 60, 80),
    _values(8, 18, 12),
)
_LEG_VALUE_ROWS: Tuple[_TheoremValues, ...] = (
    _values(9, 16, 12, 15, 20),
    _values(16, 9, 12, 20, 15),
    _values(18, 32, 24, 30, 40),
    _values(32, 18, 24, 40, 30),
    _values(27, 48, 36, 45, 60),
    _values(48, 27, 36, 60, 45),
    _values(36, 64, 48, 60, 80),
)


def _altitude_cases() -> Tuple[_Case, ...]:
    cases: list[_Case] = []
    for values in _ALTITUDE_VALUE_ROWS:
        cases.append(
            _Case(
                query_id="altitude_from_split_hypotenuse",
                answer=int(values.altitude),
                target_name="segment AD",
                target_role="altitude",
                relation="altitude_geometric_mean_from_split_hypotenuse",
                values=values,
                visible_labels={
                    "left_projection": str(values.left_projection),
                    "right_projection": str(values.right_projection),
                    "altitude": "?",
                },
            )
        )
        cases.append(
            _Case(
                query_id="missing_projection_from_altitude",
                answer=int(values.right_projection),
                target_name="segment DC",
                target_role="right_projection",
                relation="projection_from_altitude_and_other_projection",
                values=values,
                visible_labels={
                    "left_projection": str(values.left_projection),
                    "right_projection": "?",
                    "altitude": str(values.altitude),
                },
            )
        )
        cases.append(
            _Case(
                query_id="missing_projection_from_altitude",
                answer=int(values.left_projection),
                target_name="segment BD",
                target_role="left_projection",
                relation="projection_from_altitude_and_other_projection",
                values=values,
                visible_labels={
                    "left_projection": "?",
                    "right_projection": str(values.right_projection),
                    "altitude": str(values.altitude),
                },
            )
        )
    return tuple(cases)


def _leg_projection_cases() -> Tuple[_Case, ...]:
    cases: list[_Case] = []
    for values in _LEG_VALUE_ROWS:
        if values.left_leg is None or values.right_leg is None:
            continue
        cases.append(
            _Case(
                query_id="leg_from_hypotenuse_projection",
                answer=int(values.left_leg),
                target_name="segment AB",
                target_role="left_leg",
                relation="leg_geometric_mean_from_hypotenuse_projection",
                values=values,
                visible_labels={
                    "hypotenuse": str(values.hypotenuse),
                    "left_projection": str(values.left_projection),
                    "left_leg": "?",
                },
            )
        )
        cases.append(
            _Case(
                query_id="leg_from_hypotenuse_projection",
                answer=int(values.right_leg),
                target_name="segment AC",
                target_role="right_leg",
                relation="leg_geometric_mean_from_hypotenuse_projection",
                values=values,
                visible_labels={
                    "hypotenuse": str(values.hypotenuse),
                    "right_projection": str(values.right_projection),
                    "right_leg": "?",
                },
            )
        )
        cases.append(
            _Case(
                query_id="projection_from_leg_and_hypotenuse",
                answer=int(values.left_projection),
                target_name="segment BD",
                target_role="left_projection",
                relation="projection_from_leg_and_hypotenuse",
                values=values,
                visible_labels={
                    "hypotenuse": str(values.hypotenuse),
                    "left_leg": str(values.left_leg),
                    "left_projection": "?",
                },
            )
        )
        cases.append(
            _Case(
                query_id="projection_from_leg_and_hypotenuse",
                answer=int(values.right_projection),
                target_name="segment DC",
                target_role="right_projection",
                relation="projection_from_leg_and_hypotenuse",
                values=values,
                visible_labels={
                    "hypotenuse": str(values.hypotenuse),
                    "right_leg": str(values.right_leg),
                    "right_projection": "?",
                },
            )
        )
    return tuple(cases)


_ALTITUDE_CASES = _altitude_cases()
_LEG_PROJECTION_CASES = _leg_projection_cases()


def _cases_for_objective(objective_key: str) -> Tuple[_Case, ...]:
    if objective_key == ALTITUDE_OBJECTIVE_KEY:
        return _ALTITUDE_CASES
    if objective_key == LEG_PROJECTION_OBJECTIVE_KEY:
        return _LEG_PROJECTION_CASES
    raise ValueError(f"unknown right-triangle altitude theorem objective: {objective_key}")


def _normal_away_from(a: Point, b: Point, ref: Point, distance: float) -> Point:
    ux, uy = _unit(_sub(b, a))
    normal = (-uy, ux)
    midpoint = _mid(a, b)
    candidate = _add(midpoint, normal, distance)
    if math.hypot(candidate[0] - ref[0], candidate[1] - ref[1]) < math.hypot(midpoint[0] - ref[0], midpoint[1] - ref[1]):
        normal = (-normal[0], -normal[1])
    return (normal[0] * float(distance), normal[1] * float(distance))


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


def _draw_segment_label(ctx: _RenderContext, start: Point, end: Point, text: str, *, reference: Point, distance: float, toward_reference: bool = False) -> BBox:
    offset = _normal_away_from(start, end, reference, abs(float(distance)))
    if bool(toward_reference):
        offset = (-offset[0], -offset[1])
    return _draw_text_centered(ctx, str(text), _add(_mid(start, end), offset), small=True)


def _draw_dimension_line(ctx: _RenderContext, start: Point, end: Point, label: str, *, reference: Point, distance: float) -> BBox:
    offset = _normal_away_from(start, end, reference, abs(float(distance)))
    p0 = _add(start, offset)
    p1 = _add(end, offset)
    ctx.draw.line((p0, p1), fill=ctx.label_color, width=max(1, ctx.line_width - 1))
    ux, uy = _unit(_sub(end, start))
    normal = (-uy, ux)
    tick = 7.0
    for point in (p0, p1):
        ctx.draw.line(
            (_add(point, normal, -tick), _add(point, normal, tick)),
            fill=ctx.label_color,
            width=max(1, ctx.line_width - 1),
        )
    label_offset = (offset[0] * 0.22, offset[1] * 0.22)
    label_bbox = _draw_text_centered(ctx, str(label), _add(_mid(p0, p1), label_offset), small=True)
    return bbox_from_points((p0, p1), width=ctx.width, height=ctx.height, pad=10.0 + max(label_bbox[2] - label_bbox[0], label_bbox[3] - label_bbox[1]) * 0.05)


def _draw_right_angle_marker(ctx: _RenderContext, vertex: Point, arm_a: Point, arm_b: Point, *, size: float) -> BBox:
    u1 = _unit(_sub(arm_a, vertex))
    u2 = _unit(_sub(arm_b, vertex))
    p1 = _add(vertex, u1, size)
    p2 = _add(p1, u2, size)
    p3 = _add(vertex, u2, size)
    ctx.draw.line((p1, p2, p3), fill=ctx.accent_color, width=max(2, ctx.line_width - 1), joint="curve")
    return bbox_from_points((p1, p2, p3), width=ctx.width, height=ctx.height, pad=3.0)


def _scene_geometry(values: _TheoremValues, *, width: int, height: int, instance_seed: int) -> _SceneGeometry:
    rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.layout")
    c = float(values.hypotenuse)
    p = float(values.left_projection)
    h = float(values.altitude)
    local = {
        "B": (0.0, 0.0),
        "D": (p, 0.0),
        "C": (c, 0.0),
        "A": (p, -h),
    }
    min_x = min(point[0] for point in local.values())
    max_x = max(point[0] for point in local.values())
    min_y = min(point[1] for point in local.values())
    max_y = max(point[1] for point in local.values())
    scale = min((float(width) * 0.62) / max(1.0, max_x - min_x), (float(height) * 0.46) / max(1.0, max_y - min_y))
    angle = rng.uniform(-0.055, 0.055)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    center_local = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    center_canvas = (
        float(width) / 2.0 + rng.uniform(-18.0, 18.0),
        float(height) * 0.58 + rng.uniform(-12.0, 10.0),
    )
    points: Dict[str, Point] = {}
    for label, point in local.items():
        x = (float(point[0]) - center_local[0]) * scale
        y = (float(point[1]) - center_local[1]) * scale
        points[label] = (
            center_canvas[0] + (x * cos_a - y * sin_a),
            center_canvas[1] + (x * sin_a + y * cos_a),
        )
    return _SceneGeometry(points=points, labels={"A": "A", "B": "B", "C": "C", "D": "D"})


def _draw_vertex_labels(ctx: _RenderContext, points: Mapping[str, Point]) -> Dict[str, BBox]:
    centroid = (
        sum(point[0] for point in points.values()) / float(len(points)),
        sum(point[1] for point in points.values()) / float(len(points)),
    )
    bboxes: Dict[str, BBox] = {}
    for label, point in points.items():
        direction = _unit(_sub(point, centroid))
        bboxes[str(label)] = _draw_text_centered(ctx, str(label), _add(point, direction, 24.0), small=True)
    return bboxes


def _draw_measurement_labels(ctx: _RenderContext, case: _Case, points: Mapping[str, Point]) -> Dict[str, BBox]:
    bboxes: Dict[str, BBox] = {}
    a, b, c, d = points["A"], points["B"], points["C"], points["D"]
    labels = dict(case.visible_labels)
    if "left_projection" in labels:
        bboxes["left_projection_label"] = _draw_segment_label(ctx, b, d, labels["left_projection"], reference=a, distance=27.0, toward_reference=True)
    if "right_projection" in labels:
        bboxes["right_projection_label"] = _draw_segment_label(ctx, d, c, labels["right_projection"], reference=a, distance=27.0, toward_reference=True)
    if "hypotenuse" in labels:
        bboxes["hypotenuse_label"] = _draw_dimension_line(ctx, b, c, labels["hypotenuse"], reference=a, distance=46.0)
    if "altitude" in labels:
        bboxes["altitude_label"] = _draw_segment_label(ctx, a, d, labels["altitude"], reference=b, distance=32.0)
    if "left_leg" in labels:
        bboxes["left_leg_label"] = _draw_segment_label(ctx, a, b, labels["left_leg"], reference=d, distance=31.0)
    if "right_leg" in labels:
        bboxes["right_leg_label"] = _draw_segment_label(ctx, a, c, labels["right_leg"], reference=d, distance=31.0)
    return bboxes


def _render_problem(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    geometry = _scene_geometry(problem.case.values, width=ctx.width, height=ctx.height, instance_seed=problem.layout_seed)
    points = {
        key: value
        for key, value in zip(
            geometry.points.keys(),
            ctx.scene_transform.points(tuple(geometry.points.values())),
        )
    }
    geometry = _SceneGeometry(points=points, labels=dict(geometry.labels))
    a, b, c, d = points["A"], points["B"], points["C"], points["D"]

    construction_bboxes: Dict[str, BBox] = {}
    readout_bboxes: Dict[str, BBox] = {}
    point_label_bboxes: Dict[str, BBox] = {}

    triangle_points = (a, b, c)
    ctx.draw.polygon(triangle_points, fill=ctx.fill_color)
    ctx.draw.line((a, b, c, a), fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ctx.draw.line((a, d), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    construction_bboxes["right_triangle"] = bbox_from_points(triangle_points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 3)
    construction_bboxes["altitude"] = bbox_from_points((a, d), width=ctx.width, height=ctx.height, pad=ctx.line_width + 3)
    construction_bboxes["right_angle_marker"] = _draw_right_angle_marker(ctx, a, b, c, size=18.0)
    construction_bboxes["altitude_foot_marker"] = _draw_right_angle_marker(ctx, d, a, c, size=16.0)
    point_label_bboxes.update(_draw_vertex_labels(ctx, points))
    readout_bboxes.update(_draw_measurement_labels(ctx, problem.case, points))

    if problem.objective_key == ALTITUDE_OBJECTIVE_KEY:
        annotation = {
            "right_angle_vertex": a,
            "altitude_foot": d,
            "hypotenuse_left_endpoint": b,
            "hypotenuse_right_endpoint": c,
        }
    else:
        if problem.case.target_role in {"left_leg", "left_projection"}:
            leg_endpoint, other_endpoint = b, c
        else:
            leg_endpoint, other_endpoint = c, b
        annotation = {
            "right_angle_vertex": a,
            "leg_hypotenuse_endpoint": leg_endpoint,
            "altitude_foot": d,
            "other_hypotenuse_endpoint": other_endpoint,
        }

    render_map = {
        "points": {key: _point_to_list(point) for key, point in points.items()},
        "point_label_bboxes": _json_ready(point_label_bboxes),
        "readout_bboxes": _json_ready(readout_bboxes),
        "construction_bboxes": _json_ready(construction_bboxes),
    }
    return _RenderedScene(
        image=ctx.image,
        geometry=geometry,
        annotation_points=annotation,
        point_label_bboxes=point_label_bboxes,
        readout_bboxes=readout_bboxes,
        construction_bboxes=construction_bboxes,
        render_map=render_map,
    )


def _select_problem(
    *,
    objective_key: str,
    query_id: str,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    query_probability_map = {str(key): float(value) for key, value in dict(query_probabilities).items()}
    cases = tuple(case for case in _cases_for_objective(str(objective_key)) if case.query_id == str(query_id))
    if not cases:
        raise ValueError(f"no cases for query_id={query_id!r}")
    case_rng = spawn_rng(int(instance_seed), f"{objective_key}.{query_id}.case")
    case_index = int(case_rng.randrange(len(cases)))
    return _ResolvedProblem(
        objective_key=str(objective_key),
        query_id=str(query_id),
        case=cases[case_index],
        query_probabilities=dict(query_probability_map),
        case_index=int(case_index),
        layout_seed=int(instance_seed),
    )


def _build_context(*, instance_seed: int, params: Mapping[str, Any], rendering_defaults: Mapping[str, Any]) -> _RenderContext:
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
    readout_font_family = str(params.get("readout_font_family", rendering_defaults.get("readout_font_family", "roboto")))
    diagram_style_trace = dict(diagram_style_meta)
    diagram_style_trace["readout_font_family"] = readout_font_family
    image = background.convert("RGB")
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
        line_width=max(2, int(params.get("line_width", rendering_defaults.get("line_width", 3)))),
        label_stroke_width=max(0, min(1, int(diagram_style.label_stroke_width_px))),
        font=load_font(int(params.get("label_font_size", rendering_defaults.get("label_font_size", 22))), bold=False, font_family=readout_font_family),
        small_font=load_font(int(params.get("small_label_font_size", rendering_defaults.get("small_label_font_size", 18))), bold=False, font_family=readout_font_family),
        diagram_style_meta=diagram_style_trace,
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_rotation"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=width,
            canvas_height=height,
        ),
    )


def _make_prompt_examples(annotation_keys: Sequence[str], *, answer: int) -> tuple[str, str]:
    return build_keyed_point_prompt_json_examples(annotation_keys=annotation_keys, answer=int(answer))




@dataclass(frozen=True)
class RightTriangleAltitudeArtifact:
    prompt: str
    answer: int
    annotation_value: Dict[str, Any]
    image: Image.Image
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, Any]
    query_id: str
    prompt_variants: Dict[str, Any]


class RightTriangleAltitudeRuntime:
    """Scene-local runtime shared by right-triangle altitude theorem tasks."""

    def generate_artifact(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
        runtime_namespace: str,
        query_id: str,
        query_probabilities: Mapping[str, float],
        objective_key: str,
    ) -> RightTriangleAltitudeArtifact:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=str(runtime_namespace),
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                problem = _select_problem(
                    objective_key=str(objective_key),
                    query_id=str(query_id),
                    query_probabilities=query_probabilities,
                    instance_seed=int(instance_seed) + int(attempt),
                    params=params,
                )
                ctx = _build_context(instance_seed=int(instance_seed) + int(attempt), params=params, rendering_defaults=rendering_defaults)
                rendered = _render_problem(problem, ctx)
                break
            except Exception as exc:
                last_error = exc
                continue
        else:
            raise RuntimeError(f"failed to generate {str(runtime_namespace)}") from last_error

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
                "answer_hint_integer_length",
            ),
            context=f"prompt defaults for {str(runtime_namespace)}",
        )
        annotation_keys = tuple(rendered.annotation_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys, answer=int(problem.case.answer))
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        prompt_selection = render_scene_prompt_variants(
            domain="geometry",
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
                "answer_hint": str(prompt_defaults["answer_hint_integer_length"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {key: _point_to_list(point) for key, point in rendered.annotation_points.items()}
        values = problem.case.values
        measurement_payload = {
            "left_projection": int(values.left_projection),
            "right_projection": int(values.right_projection),
            "hypotenuse": int(values.hypotenuse),
            "altitude": int(values.altitude),
            "left_leg": values.left_leg,
            "right_leg": values.right_leg,
            "target_role": str(problem.case.target_role),
            "visible_labels": dict(problem.case.visible_labels),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": "geometry",
                "scene_id": SCENE_ID,
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": "right_triangle_with_altitude_to_hypotenuse",
                        "points": {key: _point_to_list(point) for key, point in rendered.geometry.points.items()},
                        "segments": {
                            "left_projection": "BD",
                            "right_projection": "DC",
                            "hypotenuse": "BC",
                            "altitude": "AD",
                            "left_leg": "AB",
                            "right_leg": "AC",
                        },
                    },
                ],
                "relations": {
                    "type": str(problem.case.relation),
                    "query_id": str(problem.query_id),
                },
            },
            "query_spec": {
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "case_index": int(problem.case_index),
                },
            },
            "render_spec": {
                "task_id": str(runtime_namespace),
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
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_name": str(problem.case.target_name),
                "relation": str(problem.case.relation),
                "answer": int(problem.case.answer),
                "annotation_roles": list(annotation_keys),
                **dict(measurement_payload),
            },
            "witness_symbolic": {
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_name": str(problem.case.target_name),
                "relation": str(problem.case.relation),
                "answer": int(problem.case.answer),
                **dict(measurement_payload),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        return RightTriangleAltitudeArtifact(
            prompt=str(prompt_artifacts.prompt),
            answer=int(problem.case.answer),
            annotation_value=dict(annotation_value),
            image=image,
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "ALTITUDE_OBJECTIVE_KEY",
    "LEG_PROJECTION_OBJECTIVE_KEY",
    "RightTriangleAltitudeArtifact",
    "RightTriangleAltitudeRuntime",
    "SCENE_ID",
]
