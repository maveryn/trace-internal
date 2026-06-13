"""Pythagorean attached-square tree measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)

SCENE_ID = "pythagorean_tree"
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font
from ..shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.shared.fixed_query import (
    geometry_selected_probability_map as _probability_map,
    select_indexed_geometry_query_id,
)
from ..shared.measurement_rendering import bbox_from_points, bbox_to_list, pad_bbox
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.pythagorean import (
    IntegerRightTriangle,
    integer_right_triangles,
    validate_integer_right_triangle,
)
from ..shared.scene_transform import LazySceneTransform
from ..shared.vector2d import add as _add, dot as _dot, mul as _mul, sub as _sub, unit as _unit

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]
Polygon = Tuple[Point, ...]

PROMPT_BUNDLE_ID = "geometry_pythagorean_tree_v0"
TASK_ID = "task_geometry__pythagorean_tree__missing_square_area_value"

_SCENE_DEFAULTS = get_scene_defaults("geometry", "pythagorean_tree")
_QUERY_IDS: Tuple[str, ...] = ("hypotenuse_square_area", "leg_square_area")
_LEG_TARGET_ROLES: Tuple[str, ...] = ("leg_square_1", "leg_square_2")


def _default_tree_triples() -> Tuple[Tuple[int, int, int], ...]:
    """Return attached-square cases with distinct leg and hypotenuse answers."""

    triples: list[Tuple[int, int, int]] = []
    used_legs: set[int] = set()
    used_hypotenuses: set[int] = set()
    for triangle in integer_right_triangles(
        min_leg=3,
        max_leg=55,
        max_hypotenuse=65,
    ):
        leg_a = int(triangle.leg_a)
        leg_b = int(triangle.leg_b)
        hypotenuse = int(triangle.hypotenuse)
        if leg_a in used_legs or leg_b in used_legs:
            continue
        if hypotenuse in used_hypotenuses:
            continue
        triples.append((leg_a, leg_b, hypotenuse))
        used_legs.update((leg_a, leg_b))
        used_hypotenuses.add(hypotenuse)
    if len(triples) < 10:
        raise RuntimeError("pythagorean tree triple pool is unexpectedly small")
    return tuple(triples)


_TRIPLES: Tuple[Tuple[int, int, int], ...] = _default_tree_triples()


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    leg_a: int
    leg_b: int
    hypotenuse: int
    target_role: str
    answer: int
    known_area_labels: Dict[str, str]
    query_probabilities: Dict[str, float]
    target_role_probabilities: Dict[str, float]
    triple_probabilities: Dict[str, float]
    witness: Dict[str, Any]


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
    triangle_fill: Color
    leg_square_fill: Color
    other_leg_square_fill: Color
    hypotenuse_square_fill: Color
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
    annotation_keyed_bboxes: Dict[str, BBox]
    annotation_roles: Tuple[str, ...]
    square_polygons: Dict[str, Polygon]
    triangle_vertices: Dict[str, Point]
    label_bboxes: Dict[str, BBox]
    marker_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]



def _triple_key(triple: Tuple[int, int, int]) -> str:
    return f"{int(triple[0])}-{int(triple[1])}-{int(triple[2])}"


def _select_leg_target_role(*, params: Mapping[str, Any], instance_seed: int) -> tuple[str, Dict[str, float]]:
    explicit = params.get("target_role")
    if explicit is not None:
        role = str(explicit)
        if role not in _LEG_TARGET_ROLES:
            raise ValueError(f"unsupported target_role for {TASK_ID}: {role}")
        return role, _probability_map(_LEG_TARGET_ROLES, selected=role)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.leg_target_role",
    )
    role = str(_LEG_TARGET_ROLES[int(index) % len(_LEG_TARGET_ROLES)])
    return role, _probability_map(_LEG_TARGET_ROLES)


def _resolve_problem(*, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    query_id, query_probabilities = select_indexed_geometry_query_id(
        params,
        query_ids=_QUERY_IDS,
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
    )
    explicit_triple = params.get("triple")
    if explicit_triple is not None:
        if not isinstance(explicit_triple, Sequence) or len(explicit_triple) != 3:
            raise ValueError("triple must be a three-item sequence")
        leg_a, leg_b, hypotenuse = [int(value) for value in explicit_triple]
        validate_integer_right_triangle(
            IntegerRightTriangle(
                leg_a=int(leg_a),
                leg_b=int(leg_b),
                hypotenuse=int(hypotenuse),
            )
        )
        triple = (leg_a, leg_b, hypotenuse)
        triple_probabilities = {_triple_key(triple): 1.0}
    else:
        triple_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.triple",
        )
        triple = _TRIPLES[int(triple_index) % len(_TRIPLES)]
        triple_probabilities = {_triple_key(value): 1.0 / float(len(_TRIPLES)) for value in _TRIPLES}
    leg_a, leg_b, hypotenuse = [int(value) for value in triple]
    leg_area_1 = int(leg_a * leg_a)
    leg_area_2 = int(leg_b * leg_b)
    hyp_area = int(hypotenuse * hypotenuse)

    if str(query_id) == "hypotenuse_square_area":
        target_role = "hypotenuse_square"
        target_role_probabilities = {"hypotenuse_square": 1.0}
        answer = int(hyp_area)
        known_area_labels = {
            "leg_square_1": f"Area={leg_area_1}",
            "leg_square_2": f"Area={leg_area_2}",
            "hypotenuse_square": "Area=?",
        }
        equation = "hypotenuse_square_area = leg_square_1_area + leg_square_2_area"
    elif str(query_id) == "leg_square_area":
        target_role, target_role_probabilities = _select_leg_target_role(
            params=params,
            instance_seed=int(instance_seed),
        )
        if target_role == "leg_square_1":
            answer = int(leg_area_1)
            known_area_labels = {
                "leg_square_1": "Area=?",
                "leg_square_2": f"Area={leg_area_2}",
                "hypotenuse_square": f"Area={hyp_area}",
            }
            equation = "leg_square_1_area = hypotenuse_square_area - leg_square_2_area"
        else:
            answer = int(leg_area_2)
            known_area_labels = {
                "leg_square_1": f"Area={leg_area_1}",
                "leg_square_2": "Area=?",
                "hypotenuse_square": f"Area={hyp_area}",
            }
            equation = "leg_square_2_area = hypotenuse_square_area - leg_square_1_area"
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    witness = {
        "formula_family": "pythagorean_attached_square_area",
        "query_id": str(query_id),
        "target_role": str(target_role),
        "leg_a": int(leg_a),
        "leg_b": int(leg_b),
        "hypotenuse": int(hypotenuse),
        "leg_square_1_area": int(leg_area_1),
        "leg_square_2_area": int(leg_area_2),
        "hypotenuse_square_area": int(hyp_area),
        "equation": str(equation),
        "answer_value": int(answer),
    }
    return _ResolvedProblem(
        query_id=str(query_id),
        leg_a=int(leg_a),
        leg_b=int(leg_b),
        hypotenuse=int(hypotenuse),
        target_role=str(target_role),
        answer=int(answer),
        known_area_labels=dict(known_area_labels),
        query_probabilities=dict(query_probabilities),
        target_role_probabilities=dict(target_role_probabilities),
        triple_probabilities=dict(triple_probabilities),
        witness=dict(witness),
    )


def _make_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", group_default(rendering_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(rendering_defaults, "canvas_height", 600)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=False,
        require_grid=None,
    )
    fills: Tuple[Tuple[Color, Color, Color, Color], ...] = (
        ((246, 248, 252), (226, 239, 255), (231, 246, 235), (255, 239, 219)),
        ((248, 247, 255), (234, 232, 255), (224, 245, 247), (255, 235, 232)),
        ((250, 249, 242), (237, 246, 224), (232, 240, 255), (252, 235, 210)),
        ((246, 250, 250), (229, 243, 252), (241, 235, 255), (255, 244, 224)),
    )
    palette_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.fill_palette",
    )
    triangle_fill, leg_fill, other_leg_fill, hyp_fill = fills[int(palette_index) % len(fills)]
    font_size = int(params.get("label_font_size", group_default(rendering_defaults, "label_font_size", 22)))
    small_font_size = int(
        params.get("small_label_font_size", group_default(rendering_defaults, "small_label_font_size", 18))
    )
    line_width = int(params.get("line_width", group_default(rendering_defaults, "line_width", 3)))
    label_stroke_width = int(
        params.get(
            "label_stroke_width",
            group_default(rendering_defaults, "label_stroke_width", int(diagram_style.label_stroke_width_px)),
        )
    )
    return _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        triangle_fill=tuple(int(value) for value in triangle_fill),
        leg_square_fill=tuple(int(value) for value in leg_fill),
        other_leg_square_fill=tuple(int(value) for value in other_leg_fill),
        hypotenuse_square_fill=tuple(int(value) for value in hyp_fill),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, int(label_stroke_width)),
        font=load_font(max(12, int(font_size))),
        small_font=load_font(max(10, int(small_font_size))),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_transform"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _square_on_segment(start: Point, end: Point, *, away_from: Point) -> Polygon:
    vector = _sub(end, start)
    length = math.hypot(float(vector[0]), float(vector[1]))
    normal = _unit((-float(vector[1]), float(vector[0])))
    midpoint = ((float(start[0]) + float(end[0])) / 2.0, (float(start[1]) + float(end[1])) / 2.0)
    if _dot(_sub(away_from, midpoint), normal) > 0.0:
        normal = (-normal[0], -normal[1])
    offset = _mul(normal, length)
    return (start, end, _add(end, offset), _add(start, offset))


def _rotate(point: Point, angle_radians: float) -> Point:
    x, y = float(point[0]), float(point[1])
    cos_a = math.cos(float(angle_radians))
    sin_a = math.sin(float(angle_radians))
    return ((x * cos_a) - (y * sin_a), (x * sin_a) + (y * cos_a))


def _transform_points(
    points: Sequence[Point],
    *,
    angle_radians: float,
    scale: float,
    offset: Point,
) -> Tuple[Point, ...]:
    return tuple(_add(_mul(_rotate(point, angle_radians), float(scale)), offset) for point in points)


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    x, y = float(center[0]), float(center[1])
    draw_text_traced(
        ctx.draw,
        (x, y),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=max(0, int(ctx.label_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=True,
    )
    bbox = ctx.draw.textbbox(
        (x, y),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    return pad_bbox(bbox, 3.0, width=ctx.width, height=ctx.height)


def _polygon_center(points: Sequence[Point]) -> Point:
    return (
        sum(float(point[0]) for point in points) / float(len(points)),
        sum(float(point[1]) for point in points) / float(len(points)),
    )


def _bbox_dict(polygons: Mapping[str, Polygon], *, width: int, height: int) -> Dict[str, BBox]:
    return {
        str(key): bbox_from_points(points, width=int(width), height=int(height), pad=2.0)
        for key, points in polygons.items()
    }


def _annotation_for_problem(problem: _ResolvedProblem, square_bboxes: Mapping[str, BBox]) -> Dict[str, BBox]:
    """Build the public annotation map without duplicating one square under multiple keys."""

    if str(problem.query_id) == "hypotenuse_square_area":
        return {
            "unknown_hypotenuse_square": square_bboxes["hypotenuse_square"],
            "known_leg_square_1": square_bboxes["leg_square_1"],
            "known_leg_square_2": square_bboxes["leg_square_2"],
        }

    if str(problem.query_id) == "leg_square_area":
        known_leg_role = "leg_square_2" if str(problem.target_role) == "leg_square_1" else "leg_square_1"
        return {
            "unknown_leg_square": square_bboxes[str(problem.target_role)],
            "known_leg_square": square_bboxes[known_leg_role],
            "known_hypotenuse_square": square_bboxes["hypotenuse_square"],
        }

    raise ValueError(f"unsupported query_id: {problem.query_id}")


def _assert_bboxes_inside(bboxes: Sequence[BBox], *, width: int, height: int) -> None:
    for bbox in bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 4 or y0 <= 4 or x1 >= float(width) - 4 or y1 >= float(height) - 4:
            raise ValueError("pythagorean tree label or square too close to canvas edge")


def _draw_right_angle_marker(ctx: _RenderContext, *, vertex: Point, arm_a: Point, arm_b: Point) -> BBox:
    size = 18.0
    u = _unit(_sub(arm_a, vertex))
    v = _unit(_sub(arm_b, vertex))
    p1 = _add(vertex, _mul(u, size))
    p2 = _add(p1, _mul(v, size))
    p3 = _add(vertex, _mul(v, size))
    ctx.draw.line([p1, p2, p3], fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    return bbox_from_points((p1, p2, p3), width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _render_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render.scene")
    a = (0.0, 0.0)
    b = (float(problem.leg_b), 0.0)
    c = (0.0, -float(problem.leg_a))
    leg_square_1 = _square_on_segment(a, c, away_from=b)
    leg_square_2 = _square_on_segment(a, b, away_from=c)
    hypotenuse_square = _square_on_segment(b, c, away_from=a)
    all_local_points = (a, b, c, *leg_square_1, *leg_square_2, *hypotenuse_square)

    base_rotation = float(rng.choice((0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)))
    angle = base_rotation + math.radians(float(rng.uniform(-7.0, 7.0)))
    rotated = [_rotate(point, angle) for point in all_local_points]
    min_x = min(point[0] for point in rotated)
    max_x = max(point[0] for point in rotated)
    min_y = min(point[1] for point in rotated)
    max_y = max(point[1] for point in rotated)
    span_x = max(1e-6, max_x - min_x)
    span_y = max(1e-6, max_y - min_y)
    scale = min((ctx.width - 130.0) / span_x, (ctx.height - 120.0) / span_y)
    scale *= float(rng.uniform(0.91, 0.98))
    center_after_scale = ((min_x + max_x) * scale / 2.0, (min_y + max_y) * scale / 2.0)
    target_center = (
        (ctx.width / 2.0) + float(rng.uniform(-26.0, 26.0)),
        (ctx.height / 2.0) + float(rng.uniform(-18.0, 18.0)),
    )
    offset = (target_center[0] - center_after_scale[0], target_center[1] - center_after_scale[1])

    a_px, b_px, c_px = _transform_points((a, b, c), angle_radians=angle, scale=scale, offset=offset)
    square_polygons = {
        "leg_square_1": _transform_points(leg_square_1, angle_radians=angle, scale=scale, offset=offset),
        "leg_square_2": _transform_points(leg_square_2, angle_radians=angle, scale=scale, offset=offset),
        "hypotenuse_square": _transform_points(hypotenuse_square, angle_radians=angle, scale=scale, offset=offset),
    }
    transform_points = (a_px, b_px, c_px, *(point for polygon in square_polygons.values() for point in polygon))
    ctx.scene_transform.resolve(transform_points)
    a_px, b_px, c_px = ctx.scene_transform.points((a_px, b_px, c_px))
    square_polygons = {key: ctx.scene_transform.points(polygon) for key, polygon in square_polygons.items()}
    square_bboxes = _bbox_dict(square_polygons, width=ctx.width, height=ctx.height)
    _assert_bboxes_inside(square_bboxes.values(), width=ctx.width, height=ctx.height)

    for key, fill in (
        ("leg_square_1", ctx.leg_square_fill),
        ("leg_square_2", ctx.other_leg_square_fill),
        ("hypotenuse_square", ctx.hypotenuse_square_fill),
    ):
        polygon = square_polygons[key]
        ctx.draw.polygon(polygon, fill=fill)
        ctx.draw.line([*polygon, polygon[0]], fill=ctx.line_color, width=ctx.line_width, joint="curve")

    triangle = (a_px, b_px, c_px)
    ctx.draw.polygon(triangle, fill=ctx.triangle_fill)
    ctx.draw.line([a_px, b_px, c_px, a_px], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    right_angle_bbox = _draw_right_angle_marker(ctx, vertex=a_px, arm_a=b_px, arm_b=c_px)

    label_bboxes: Dict[str, BBox] = {}
    for role, text in problem.known_area_labels.items():
        label_bboxes[f"{role}_label"] = _draw_text_centered(
            ctx,
            str(text),
            _polygon_center(square_polygons[str(role)]),
            small=True,
        )
    _assert_bboxes_inside(label_bboxes.values(), width=ctx.width, height=ctx.height)

    annotation = _annotation_for_problem(problem, square_bboxes)
    render_map = {
        "coord_space": "pixel",
        "triangle_vertices": {
            "right_angle_vertex": [round(a_px[0], 3), round(a_px[1], 3)],
            "leg_square_2_endpoint": [round(b_px[0], 3), round(b_px[1], 3)],
            "leg_square_1_endpoint": [round(c_px[0], 3), round(c_px[1], 3)],
        },
        "square_vertices": {
            key: [[round(x, 3), round(y, 3)] for x, y in polygon]
            for key, polygon in square_polygons.items()
        },
        "square_bboxes": {key: bbox_to_list(value) for key, value in square_bboxes.items()},
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "marker_bboxes": {"right_angle": bbox_to_list(right_angle_bbox)},
        "rotation_degrees": round(math.degrees(angle), 3),
        "scale_px_per_unit": round(float(scale), 3),
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_keyed_bboxes={key: tuple(value) for key, value in annotation.items()},
        annotation_roles=tuple(annotation.keys()),
        square_polygons={key: tuple(value) for key, value in square_polygons.items()},
        triangle_vertices={"right_angle_vertex": a_px, "leg_square_2_endpoint": b_px, "leg_square_1_endpoint": c_px},
        label_bboxes=dict(label_bboxes),
        marker_bboxes={"right_angle": right_angle_bbox},
        render_map=dict(render_map),
    )


@register_task
class GeometryPythagoreanTreeMissingSquareAreaValueTask:
    """Compute a missing attached-square area from the Pythagorean relation."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = _QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=self.task_id,
        )
        problem = _resolve_problem(instance_seed=int(instance_seed), params=params)
        rendered: _RenderedScene | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_params = dict(params)
            attempt_params["_render_attempt"] = int(attempt)
            try:
                ctx = _make_render_context(
                    instance_seed=int(instance_seed) + int(attempt),
                    params=attempt_params,
                    rendering_defaults=rendering_defaults,
                )
                rendered = _render_scene(ctx, problem, instance_seed=int(instance_seed) + int(attempt))
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or ctx is None:
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
                "annotation_hint_hypotenuse_square_area",
                "annotation_hint_leg_square_area",
                "answer_hint_integer",
                "json_example_hypotenuse_square_area",
                "json_example_leg_square_area",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_hint = str(
            prompt_defaults.get(
                f"annotation_hint_{problem.query_id}",
                prompt_defaults["annotation_hint"],
            )
        )
        json_example = str(
            prompt_defaults.get(
                f"json_example_{problem.query_id}",
                prompt_defaults[f"json_example_{_QUERY_IDS[0]}"],
            )
        )
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
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {
            str(key): bbox_to_list(value)
            for key, value in rendered.annotation_keyed_bboxes.items()
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": str(self.scene_id or self.public_scene_id),
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": {
                    "triangle_vertices": dict(rendered.render_map["triangle_vertices"]),
                    "square_vertices": dict(rendered.render_map["square_vertices"]),
                },
                "relations": {
                    "type": "pythagorean_attached_square_area",
                    "query_id": str(problem.query_id),
                    "target_role": str(problem.target_role),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "target_role": str(problem.target_role),
                    "target_role_probabilities": dict(problem.target_role_probabilities),
                    "triple_probabilities": dict(problem.triple_probabilities),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
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
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_role": str(problem.target_role),
                "answer": int(problem.answer),
                "annotation_roles": list(rendered.annotation_roles),
                **dict(problem.witness),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                **dict(problem.witness),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_value),
                "pixel_keyed_bbox_map": dict(annotation_value),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryPythagoreanTreeMissingSquareAreaValueTask",
    "SCENE_ID",
    "TASK_ID",
]
