"""Scene-local construction and rendering helpers for circle-polygon composites."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.shared.fixed_query import geometry_selected_probability_map as _probability_map
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    draw_label_backplate,
    pad_bbox,
    readout_text_metadata,
)
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import (
    add as _add,
    mul as _mul,
    point_to_list as _point_to_list,
    sub as _sub,
    unit as _unit,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "circle_polygon_composite"
PROMPT_BUNDLE_ID = "geometry_circle_polygon_composite_v0"
TARGET_PAIRS: Tuple[str, ...] = ("AB_CD", "BC_DA")
CONSTRUCTION_KINDS: Tuple[str, ...] = ("incircle", "semicircle")
TANGENTIAL_ANNOTATION_KEYS: Tuple[str, ...] = (
    "vertex_A",
    "vertex_B",
    "vertex_C",
    "vertex_D",
    "tangent_AB",
    "tangent_BC",
    "tangent_CD",
    "tangent_DA",
    "incircle_center",
)
TANGENT_CASES: Tuple[Tuple[int, int, int, int], ...] = (
    (3, 4, 5, 6),
    (4, 5, 6, 7),
    (5, 6, 7, 8),
    (4, 6, 8, 10),
    (6, 7, 9, 10),
    (5, 8, 9, 12),
    (7, 9, 10, 12),
    (8, 10, 11, 13),
    (6, 8, 12, 14),
    (9, 10, 12, 15),
    (7, 11, 13, 16),
    (10, 12, 14, 18),
)
ANGLE_SUPPORT: Tuple[int, ...] = (25, 30, 35, 40, 45, 50, 55, 60, 65)
SIDE_SIGN_SUPPORT: Tuple[int, int] = (-1, 1)
ANGLE_ANNOTATION_KEYS: Tuple[str, ...] = (
    "shape_corner_A",
    "shape_corner_B",
    "shape_corner_C",
    "shape_corner_D",
    "circle_center",
    "tangent_point",
    "known_angle_vertex",
    "known_angle_reference_point",
    "target_angle_vertex",
    "target_reference_point",
)


@dataclass(frozen=True)
class ResolvedTangentialProblem:
    target_pair: str
    target_pair_label: str
    known_pair: str
    known_pair_label: str
    vertex_tangents: Dict[str, int]
    side_lengths: Dict[str, int]
    answer: int
    target_pair_probabilities: Dict[str, float]
    tangent_case_probabilities: Dict[str, float]


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
    polygon_fill: Color
    circle_fill: Color
    accent_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class RenderedTangentialScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    vertices: Dict[str, Point]
    tangency_points: Dict[str, Point]
    label_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]


@dataclass(frozen=True)
class ResolvedAngleProblem:
    construction_kind: str
    answer: int
    side_sign: int
    angle_probabilities: Dict[str, float]
    side_probabilities: Dict[str, float]


@dataclass(frozen=True)
class RenderedAngleScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]


def _case_key(case: Sequence[int]) -> str:
    return "-".join(str(int(value)) for value in case)


def select_target_pair(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("target_pair")
    if explicit is not None:
        target_pair = str(explicit)
        if target_pair not in TARGET_PAIRS:
            raise ValueError(f"unsupported target_pair: {target_pair}")
        return target_pair, _probability_map(TARGET_PAIRS, selected=target_pair)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    target_pair = str(TARGET_PAIRS[int(index) % len(TARGET_PAIRS)])
    return target_pair, _probability_map(TARGET_PAIRS)


def resolve_tangential_problem(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    target_pair_namespace: str,
    tangent_case_namespace: str,
) -> ResolvedTangentialProblem:
    target_pair, target_pair_probabilities = select_target_pair(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(target_pair_namespace),
    )

    explicit_tangents = params.get("tangent_lengths")
    if explicit_tangents is not None:
        if not isinstance(explicit_tangents, Sequence) or len(explicit_tangents) != 4:
            raise ValueError("tangent_lengths must be a four-item sequence")
        case = tuple(int(value) for value in explicit_tangents)
        if any(value <= 0 for value in case):
            raise ValueError("tangent_lengths values must be positive")
        tangent_case_probabilities = {_case_key(case): 1.0}
    else:
        case_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(tangent_case_namespace),
        )
        case = TANGENT_CASES[int(case_index) % len(TANGENT_CASES)]
        tangent_case_probabilities = {
            _case_key(value): 1.0 / float(len(TANGENT_CASES)) for value in TANGENT_CASES
        }

    t_a, t_b, t_c, t_d = [int(value) for value in case]
    side_lengths = {
        "AB": int(t_a + t_b),
        "BC": int(t_b + t_c),
        "CD": int(t_c + t_d),
        "DA": int(t_d + t_a),
    }
    if target_pair == "AB_CD":
        target_pair_label = "AB + CD"
        known_pair = "BC_DA"
        known_pair_label = "BC and DA"
        answer = int(side_lengths["AB"] + side_lengths["CD"])
    else:
        target_pair_label = "BC + DA"
        known_pair = "AB_CD"
        known_pair_label = "AB and CD"
        answer = int(side_lengths["BC"] + side_lengths["DA"])

    return ResolvedTangentialProblem(
        target_pair=str(target_pair),
        target_pair_label=str(target_pair_label),
        known_pair=str(known_pair),
        known_pair_label=str(known_pair_label),
        vertex_tangents={"A": int(t_a), "B": int(t_b), "C": int(t_c), "D": int(t_d)},
        side_lengths=dict(side_lengths),
        answer=int(answer),
        target_pair_probabilities=dict(target_pair_probabilities),
        tangent_case_probabilities=dict(tangent_case_probabilities),
    )


def make_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    fill_namespace: str,
    transform_namespace: str = f"{SCENE_ID}.scene_transform",
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
    fill_palettes: Tuple[Tuple[Color, Color], ...] = (
        ((238, 246, 255), (255, 252, 232)),
        ((241, 248, 239), (247, 243, 255)),
        ((255, 243, 234), (235, 246, 250)),
        ((248, 247, 240), (232, 242, 255)),
    )
    fill_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(fill_namespace),
    )
    polygon_fill, circle_fill = fill_palettes[int(fill_index) % len(fill_palettes)]
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
        label_backing_color=tuple(int(value) for value in diagram_style.panel_fill_rgb),
        polygon_fill=tuple(int(value) for value in polygon_fill),
        circle_fill=tuple(int(value) for value in circle_fill),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, int(label_stroke_width)),
        font=load_font(max(12, int(font_size))),
        small_font=load_font(max(10, int(small_font_size))),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), str(transform_namespace)),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _solve_inradius(tangents: Sequence[int]) -> float:
    lengths = [float(value) for value in tangents]

    def total_gap(radius: float) -> float:
        return sum(2.0 * math.atan(float(radius) / length) for length in lengths)

    low = 1e-6
    high = max(lengths)
    while total_gap(high) <= 2.0 * math.pi:
        high *= 2.0
    for _ in range(90):
        mid = (low + high) / 2.0
        if total_gap(mid) < 2.0 * math.pi:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def _normal(angle: float) -> Point:
    return (math.cos(float(angle)), math.sin(float(angle)))


def _line_intersection(normal_a: Point, normal_b: Point, radius: float) -> Point:
    ax, ay = float(normal_a[0]), float(normal_a[1])
    bx, by = float(normal_b[0]), float(normal_b[1])
    det = (ax * by) - (ay * bx)
    if abs(det) <= 1e-9:
        raise ValueError("near-parallel tangent lines")
    return (float(radius) * (by - ay) / det, float(radius) * (ax - bx) / det)


def _rotate(point: Point, angle_radians: float) -> Point:
    x, y = float(point[0]), float(point[1])
    cos_a = math.cos(float(angle_radians))
    sin_a = math.sin(float(angle_radians))
    return ((x * cos_a) - (y * sin_a), (x * sin_a) + (y * cos_a))


def _transform(point: Point, *, angle_radians: float, scale: float, offset: Point) -> Point:
    rotated = _rotate(point, angle_radians)
    return ((rotated[0] * float(scale)) + float(offset[0]), (rotated[1] * float(scale)) + float(offset[1]))


def _centroid(points: Sequence[Point]) -> Point:
    return (
        sum(float(point[0]) for point in points) / float(len(points)),
        sum(float(point[1]) for point in points) / float(len(points)),
    )


def _local_geometry(problem: ResolvedTangentialProblem) -> tuple[Dict[str, Point], Dict[str, Point], float]:
    t_a = int(problem.vertex_tangents["A"])
    t_b = int(problem.vertex_tangents["B"])
    t_c = int(problem.vertex_tangents["C"])
    t_d = int(problem.vertex_tangents["D"])
    radius = _solve_inradius((t_a, t_b, t_c, t_d))
    gap_b = 2.0 * math.atan(float(radius) / float(t_b))
    gap_c = 2.0 * math.atan(float(radius) / float(t_c))
    gap_d = 2.0 * math.atan(float(radius) / float(t_d))
    phi_ab = 0.0
    phi_bc = phi_ab + gap_b
    phi_cd = phi_bc + gap_c
    phi_da = phi_cd + gap_d
    normals = {
        "AB": _normal(phi_ab),
        "BC": _normal(phi_bc),
        "CD": _normal(phi_cd),
        "DA": _normal(phi_da),
    }
    vertices = {
        "A": _line_intersection(normals["DA"], normals["AB"], radius),
        "B": _line_intersection(normals["AB"], normals["BC"], radius),
        "C": _line_intersection(normals["BC"], normals["CD"], radius),
        "D": _line_intersection(normals["CD"], normals["DA"], radius),
    }
    tangency_points = {side: _mul(normal, radius) for side, normal in normals.items()}
    return vertices, tangency_points, float(radius)


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
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
        required=True,
        extra_metadata=readout_text_metadata(ctx, ctx.label_color),
    )
    return pad_bbox(bbox, 4.0, width=ctx.width, height=ctx.height)


def _outside_label_point(start: Point, end: Point, centroid: Point, *, offset: float) -> Point:
    midpoint = ((float(start[0]) + float(end[0])) / 2.0, (float(start[1]) + float(end[1])) / 2.0)
    vector = _sub(end, start)
    normal = _unit((-vector[1], vector[0]))
    if ((midpoint[0] - centroid[0]) * normal[0]) + ((midpoint[1] - centroid[1]) * normal[1]) < 0.0:
        normal = (-normal[0], -normal[1])
    return _add(midpoint, _mul(normal, float(offset)))


def _assert_bboxes_inside(bboxes: Sequence[BBox], *, width: int, height: int) -> None:
    for bbox in bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 4.0 or y0 <= 4.0 or x1 >= float(width) - 4.0 or y1 >= float(height) - 4.0:
            raise ValueError("circle-polygon label too close to canvas edge")


def resolve_angle_problem(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    construction_kind: str,
    angle_namespace: str,
    side_namespace: str,
) -> ResolvedAngleProblem:
    kind = str(construction_kind)
    if kind not in CONSTRUCTION_KINDS:
        raise ValueError(f"unsupported construction_kind: {kind}")
    explicit_answer = params.get("target_angle")
    if explicit_answer is not None:
        answer = int(explicit_answer)
        if answer not in ANGLE_SUPPORT:
            raise ValueError(f"target_angle must be one of {ANGLE_SUPPORT}")
        angle_probabilities = {str(value): (1.0 if int(value) == int(answer) else 0.0) for value in ANGLE_SUPPORT}
    else:
        angle_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(angle_namespace),
        )
        answer = int(ANGLE_SUPPORT[int(angle_index) % len(ANGLE_SUPPORT)])
        angle_probabilities = {str(value): 1.0 / float(len(ANGLE_SUPPORT)) for value in ANGLE_SUPPORT}

    explicit_side = params.get("side_sign")
    if explicit_side is not None:
        side_sign = int(explicit_side)
        if side_sign not in SIDE_SIGN_SUPPORT:
            raise ValueError("side_sign must be -1 or 1")
        side_probabilities = {"-1": 1.0 if side_sign == -1 else 0.0, "1": 1.0 if side_sign == 1 else 0.0}
    else:
        side_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(side_namespace),
        )
        side_sign = -1 if int(side_index) % 2 == 0 else 1
        side_probabilities = {"-1": 0.5, "1": 0.5}

    return ResolvedAngleProblem(
        construction_kind=str(kind),
        answer=int(answer),
        side_sign=int(side_sign),
        angle_probabilities=dict(angle_probabilities),
        side_probabilities=dict(side_probabilities),
    )


def _transform_local(point: Point, *, scale: float, offset: Point) -> Point:
    return ((float(point[0]) * float(scale)) + float(offset[0]), float(offset[1]) - (float(point[1]) * float(scale)))


def _line_rectangle_intersections(point: Point, direction: Point, bounds: tuple[float, float, float, float]) -> Tuple[Point, ...]:
    xmin, ymin, xmax, ymax = [float(value) for value in bounds]
    px, py = float(point[0]), float(point[1])
    dx, dy = float(direction[0]), float(direction[1])
    candidates: list[tuple[float, Point]] = []
    if abs(dx) > 1e-9:
        for x in (xmin, xmax):
            t = (x - px) / dx
            y = py + (t * dy)
            if ymin - 1e-7 <= y <= ymax + 1e-7:
                candidates.append((float(t), (float(x), float(y))))
    if abs(dy) > 1e-9:
        for y in (ymin, ymax):
            t = (y - py) / dy
            x = px + (t * dx)
            if xmin - 1e-7 <= x <= xmax + 1e-7:
                candidates.append((float(t), (float(x), float(y))))
    unique: list[tuple[float, Point]] = []
    for t, candidate in candidates:
        if not any(math.hypot(candidate[0] - other[1][0], candidate[1] - other[1][1]) <= 1e-6 for other in unique):
            unique.append((t, candidate))
    unique.sort(key=lambda item: item[0])
    if len(unique) < 2:
        raise ValueError("tangent line did not cross shape bounds clearly")
    return (unique[0][1], unique[-1][1])


def _draw_local_polyline(ctx: _RenderContext, points: Sequence[Point], *, scale: float, offset: Point, fill: Color, width: int) -> Tuple[Point, ...]:
    transformed = tuple(_transform_local(point, scale=scale, offset=offset) for point in points)
    ctx.draw.line(transformed, fill=fill, width=max(1, int(width)), joint="curve")
    return transformed


def _arc_points(*, center: Point, radius: float, start_degrees: float, end_degrees: float, steps: int = 18) -> Tuple[Point, ...]:
    return tuple(
        (
            float(center[0]) + (float(radius) * math.cos(math.radians(start_degrees + ((end_degrees - start_degrees) * i / max(1, steps))))),
            float(center[1]) + (float(radius) * math.sin(math.radians(start_degrees + ((end_degrees - start_degrees) * i / max(1, steps))))),
        )
        for i in range(int(steps) + 1)
    )


def _angle_between_degrees(vector: Point) -> float:
    return math.degrees(math.atan2(float(vector[1]), float(vector[0])))


def _draw_angle_arc_at_vertex(
    ctx: _RenderContext,
    *,
    vertex: Point,
    arm_a: Point,
    arm_b: Point,
    radius: float,
    scale: float,
    offset: Point,
) -> Tuple[Point, ...]:
    angle_a = _angle_between_degrees(_sub(arm_a, vertex))
    angle_b = _angle_between_degrees(_sub(arm_b, vertex))
    while angle_b - angle_a > 180.0:
        angle_b -= 360.0
    while angle_b - angle_a < -180.0:
        angle_b += 360.0
    if abs(angle_b - angle_a) > 120.0:
        angle_b = angle_a + (360.0 - abs(angle_b - angle_a)) * (1.0 if angle_b < angle_a else -1.0)
    points = _arc_points(center=vertex, radius=float(radius), start_degrees=angle_a, end_degrees=angle_b, steps=16)
    return _draw_local_polyline(
        ctx,
        points,
        scale=scale,
        offset=offset,
        fill=ctx.accent_color,
        width=max(2, ctx.line_width - 1),
    )


def _draw_semicircle(
    ctx: _RenderContext,
    *,
    center: Point,
    radius: float,
    scale: float,
    offset: Point,
) -> Tuple[Point, ...]:
    points = _arc_points(center=center, radius=float(radius), start_degrees=0.0, end_degrees=180.0, steps=48)
    return _draw_local_polyline(
        ctx,
        points,
        scale=scale,
        offset=offset,
        fill=ctx.secondary_color,
        width=max(2, ctx.line_width - 1),
    )


def render_angle_scene(
    ctx: _RenderContext,
    problem: ResolvedAngleProblem,
    *,
    instance_seed: int,
    render_namespace: str,
) -> RenderedAngleScene:
    rng = spawn_rng(int(instance_seed), str(render_namespace))
    theta = math.radians(float(problem.answer))
    sign = int(problem.side_sign)
    is_semicircle = str(problem.construction_kind) == "semicircle"
    if is_semicircle:
        bounds = (-1.25, 0.0, 1.25, 1.25)
        corners = {
            "A": (-1.25, 1.25),
            "B": (1.25, 1.25),
            "C": (1.25, 0.0),
            "D": (-1.25, 0.0),
        }
        all_local_points = tuple(corners.values())
        scale = min((ctx.width - 180.0) / 2.5, (ctx.height - 150.0) / 1.35) * float(rng.uniform(0.88, 0.96))
        offset = (
            (ctx.width / 2.0) + float(rng.uniform(-30.0, 30.0)),
            (ctx.height * 0.70) + float(rng.uniform(-18.0, 18.0)),
        )
    else:
        bounds = (-1.0, -1.0, 1.0, 1.0)
        corners = {
            "A": (-1.0, 1.0),
            "B": (1.0, 1.0),
            "C": (1.0, -1.0),
            "D": (-1.0, -1.0),
        }
        all_local_points = tuple(corners.values())
        scale = min((ctx.width - 180.0) / 2.05, (ctx.height - 150.0) / 2.05) * float(rng.uniform(0.86, 0.94))
        offset = (
            (ctx.width / 2.0) + float(rng.uniform(-28.0, 28.0)),
            (ctx.height / 2.0) + float(rng.uniform(-20.0, 20.0)),
        )

    _assert_bboxes_inside(
        (bbox_from_points(tuple(_transform_local(point, scale=scale, offset=offset) for point in all_local_points), width=ctx.width, height=ctx.height, pad=4.0),),
        width=ctx.width,
        height=ctx.height,
    )

    tangent_point = (float(sign) * math.sin(theta), math.cos(theta))
    tangent_direction = (-float(sign) * math.cos(theta), math.sin(theta))
    tangent_endpoints = _line_rectangle_intersections(tangent_point, tangent_direction, bounds)
    known_angle_vertex = max(tangent_endpoints, key=lambda point: point[1])
    known_angle_reference_point = (
        known_angle_vertex[0] - (float(sign) * 0.36),
        known_angle_vertex[1],
    )
    target_angle_vertex = (0.0, 0.0)
    target_reference_point = (0.0, 1.0)
    circle_center = (0.0, 0.0)

    corner_px = {key: _transform_local(value, scale=scale, offset=offset) for key, value in corners.items()}
    tangent_point_px = _transform_local(tangent_point, scale=scale, offset=offset)
    circle_center_px = _transform_local(circle_center, scale=scale, offset=offset)
    known_angle_vertex_px = _transform_local(known_angle_vertex, scale=scale, offset=offset)
    known_angle_reference_px = _transform_local(known_angle_reference_point, scale=scale, offset=offset)
    target_reference_px = _transform_local(target_reference_point, scale=scale, offset=offset)

    polygon = (corner_px["A"], corner_px["B"], corner_px["C"], corner_px["D"])
    ctx.draw.polygon(polygon, fill=ctx.polygon_fill)
    ctx.draw.line([*polygon, polygon[0]], fill=ctx.line_color, width=ctx.line_width, joint="curve")

    if is_semicircle:
        _draw_semicircle(ctx, center=(0.0, 0.0), radius=1.0, scale=scale, offset=offset)
        diameter = (_transform_local((-1.0, 0.0), scale=scale, offset=offset), _transform_local((1.0, 0.0), scale=scale, offset=offset))
        ctx.draw.line(diameter, fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    else:
        circle_bbox = (
            circle_center_px[0] - scale,
            circle_center_px[1] - scale,
            circle_center_px[0] + scale,
            circle_center_px[1] + scale,
        )
        ctx.draw.ellipse(circle_bbox, fill=ctx.circle_fill, outline=ctx.secondary_color, width=max(2, ctx.line_width - 1))

    _draw_local_polyline(ctx, tangent_endpoints, scale=scale, offset=offset, fill=ctx.line_color, width=ctx.line_width)
    _draw_local_polyline(ctx, (circle_center, tangent_point), scale=scale, offset=offset, fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    _draw_local_polyline(ctx, (circle_center, target_reference_point), scale=scale, offset=offset, fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    target_arc = _draw_angle_arc_at_vertex(
        ctx,
        vertex=target_angle_vertex,
        arm_a=target_reference_point,
        arm_b=tangent_point,
        radius=0.28,
        scale=scale,
        offset=offset,
    )
    known_arc = _draw_angle_arc_at_vertex(
        ctx,
        vertex=known_angle_vertex,
        arm_a=known_angle_reference_point,
        arm_b=tangent_point,
        radius=0.20,
        scale=scale,
        offset=offset,
    )

    dot_radius = max(3, int(ctx.line_width + 1))
    for point in (circle_center_px, tangent_point_px):
        ctx.draw.ellipse(
            (point[0] - dot_radius, point[1] - dot_radius, point[0] + dot_radius, point[1] + dot_radius),
            fill=ctx.accent_color,
            outline=ctx.line_color,
            width=1,
        )

    label_bboxes: Dict[str, BBox] = {}
    for key, point in corner_px.items():
        local_point = corners[str(key)]
        direction = _unit(local_point)
        label_local = _add(local_point, _mul(direction, 0.13))
        label_bboxes[f"corner_{key}_label"] = _draw_text_centered(
            ctx,
            str(key),
            _transform_local(label_local, scale=scale, offset=offset),
            small=True,
        )
    label_bboxes["center_label"] = _draw_text_centered(
        ctx,
        "O",
        _add(circle_center_px, (16.0, 15.0)),
        small=True,
    )
    label_bboxes["tangent_label"] = _draw_text_centered(
        ctx,
        "T",
        _add(tangent_point_px, (float(sign) * 18.0, -16.0)),
        small=True,
    )
    known_label_local = (known_angle_vertex[0] - (float(sign) * 0.05), known_angle_vertex[1] + 0.26)
    target_label_local = _add(
        target_angle_vertex,
        _mul(_unit(_add(_sub(target_reference_point, target_angle_vertex), _sub(tangent_point, target_angle_vertex))), 0.43),
    )
    degree = "\N{DEGREE SIGN}"
    label_bboxes["known_angle_label"] = _draw_text_centered(
        ctx,
        f"{int(problem.answer)}{degree}",
        _transform_local(known_label_local, scale=scale, offset=offset),
        small=True,
    )
    label_bboxes["target_angle_label"] = _draw_text_centered(
        ctx,
        "?",
        _transform_local(target_label_local, scale=scale, offset=offset),
        small=True,
    )
    _assert_bboxes_inside(label_bboxes.values(), width=ctx.width, height=ctx.height)

    annotation = {
        "shape_corner_A": corner_px["A"],
        "shape_corner_B": corner_px["B"],
        "shape_corner_C": corner_px["C"],
        "shape_corner_D": corner_px["D"],
        "circle_center": circle_center_px,
        "tangent_point": tangent_point_px,
        "known_angle_vertex": known_angle_vertex_px,
        "known_angle_reference_point": known_angle_reference_px,
        "target_angle_vertex": circle_center_px,
        "target_reference_point": target_reference_px,
    }
    render_map = {
        "coord_space": "pixel",
        "construction_kind": str(problem.construction_kind),
        "angle_value_degrees": int(problem.answer),
        "side_sign": int(problem.side_sign),
        "shape_corners": {key: _point_to_list(value) for key, value in corner_px.items()},
        "circle_center": _point_to_list(circle_center_px),
        "tangent_point": _point_to_list(tangent_point_px),
        "known_angle_vertex": _point_to_list(known_angle_vertex_px),
        "known_angle_reference_point": _point_to_list(known_angle_reference_px),
        "target_angle_vertex": _point_to_list(circle_center_px),
        "target_reference_point": _point_to_list(target_reference_px),
        "tangent_segment": [_point_to_list(_transform_local(point, scale=scale, offset=offset)) for point in tangent_endpoints],
        "known_angle_arc_bbox": bbox_to_list(bbox_from_points(known_arc, width=ctx.width, height=ctx.height, pad=2.0)),
        "target_angle_arc_bbox": bbox_to_list(bbox_from_points(target_arc, width=ctx.width, height=ctx.height, pad=2.0)),
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "scale_px_per_unit": round(float(scale), 3),
        "offset": [round(float(offset[0]), 3), round(float(offset[1]), 3)],
    }
    return RenderedAngleScene(
        image=ctx.image,
        annotation_keyed_points={key: tuple(value) for key, value in annotation.items()},
        annotation_roles=tuple(ANGLE_ANNOTATION_KEYS),
        label_bboxes=dict(label_bboxes),
        render_map=dict(render_map),
    )


def render_tangential_scene(
    ctx: _RenderContext,
    problem: ResolvedTangentialProblem,
    *,
    instance_seed: int,
    render_namespace: str,
) -> RenderedTangentialScene:
    rng = spawn_rng(int(instance_seed), str(render_namespace))
    local_vertices, local_tangencies, local_radius = _local_geometry(problem)
    local_all_points = [
        *local_vertices.values(),
        *local_tangencies.values(),
        (local_radius, local_radius),
        (-local_radius, local_radius),
        (local_radius, -local_radius),
        (-local_radius, -local_radius),
    ]
    base_rotation = float(rng.choice((0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)))
    angle = base_rotation + math.radians(float(rng.uniform(-10.0, 10.0)))
    rotated = [_rotate(point, angle) for point in local_all_points]
    min_x = min(point[0] for point in rotated)
    max_x = max(point[0] for point in rotated)
    min_y = min(point[1] for point in rotated)
    max_y = max(point[1] for point in rotated)
    span_x = max(1e-6, max_x - min_x)
    span_y = max(1e-6, max_y - min_y)
    scale = min((ctx.width - 180.0) / span_x, (ctx.height - 150.0) / span_y)
    scale *= float(rng.uniform(0.88, 0.96))
    center_after_scale = ((min_x + max_x) * scale / 2.0, (min_y + max_y) * scale / 2.0)
    target_center = (
        (ctx.width / 2.0) + float(rng.uniform(-28.0, 28.0)),
        (ctx.height / 2.0) + float(rng.uniform(-20.0, 20.0)),
    )
    offset = (target_center[0] - center_after_scale[0], target_center[1] - center_after_scale[1])

    vertices = {
        key: _transform(point, angle_radians=angle, scale=scale, offset=offset)
        for key, point in local_vertices.items()
    }
    tangencies = {
        key: _transform(point, angle_radians=angle, scale=scale, offset=offset)
        for key, point in local_tangencies.items()
    }
    center = _transform((0.0, 0.0), angle_radians=angle, scale=scale, offset=offset)
    radius_px = float(local_radius) * float(scale)
    ctx.scene_transform.resolve((*vertices.values(), *tangencies.values(), center))
    vertices = ctx.scene_transform.keyed_points(vertices)
    tangencies = ctx.scene_transform.keyed_points(tangencies)
    center = ctx.scene_transform.point(center)
    radius_px *= float(ctx.scene_transform.transform.scale)

    polygon = (vertices["A"], vertices["B"], vertices["C"], vertices["D"])
    polygon_bbox = bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=2.0)
    _assert_bboxes_inside((polygon_bbox,), width=ctx.width, height=ctx.height)
    circle_bbox = (
        center[0] - radius_px,
        center[1] - radius_px,
        center[0] + radius_px,
        center[1] + radius_px,
    )
    _assert_bboxes_inside((circle_bbox,), width=ctx.width, height=ctx.height)

    ctx.draw.polygon(polygon, fill=ctx.polygon_fill)
    ctx.draw.line([*polygon, polygon[0]], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ctx.draw.ellipse(circle_bbox, fill=ctx.circle_fill, outline=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    for side, point in tangencies.items():
        x, y = float(point[0]), float(point[1])
        dot_radius = max(3, int(ctx.line_width + 1))
        ctx.draw.ellipse(
            (x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius),
            fill=ctx.accent_color,
            outline=ctx.line_color,
            width=1,
        )

    label_bboxes: Dict[str, BBox] = {}
    label_offset = float(max(28, ctx.line_width * 8))
    poly_center = _centroid(polygon)
    for side, start_key, end_key in (
        ("AB", "A", "B"),
        ("BC", "B", "C"),
        ("CD", "C", "D"),
        ("DA", "D", "A"),
    ):
        target_side = (
            (problem.target_pair == "AB_CD" and side in {"AB", "CD"})
            or (problem.target_pair == "BC_DA" and side in {"BC", "DA"})
        )
        text = f"{side} ?" if target_side else f"{side}={int(problem.side_lengths[side])}"
        label_center = _outside_label_point(
            vertices[start_key],
            vertices[end_key],
            poly_center,
            offset=label_offset,
        )
        label_bboxes[f"{side}_label"] = _draw_text_centered(ctx, text, label_center, small=True)

    vertex_label_offset = float(max(18, ctx.line_width * 5))
    for vertex_key, point in vertices.items():
        direction = _unit(_sub(point, poly_center))
        label_center = _add(point, _mul(direction, vertex_label_offset))
        label_bboxes[f"vertex_{vertex_key}_label"] = _draw_text_centered(
            ctx,
            str(vertex_key),
            label_center,
            small=True,
        )
        x, y = float(point[0]), float(point[1])
        dot_radius = max(3, int(ctx.line_width + 1))
        ctx.draw.ellipse(
            (x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius),
            fill=ctx.line_color,
        )
    _assert_bboxes_inside(label_bboxes.values(), width=ctx.width, height=ctx.height)

    annotation = {
        "vertex_A": vertices["A"],
        "vertex_B": vertices["B"],
        "vertex_C": vertices["C"],
        "vertex_D": vertices["D"],
        "tangent_AB": tangencies["AB"],
        "tangent_BC": tangencies["BC"],
        "tangent_CD": tangencies["CD"],
        "tangent_DA": tangencies["DA"],
        "incircle_center": center,
    }
    render_map = {
        "coord_space": "pixel",
        "vertices": {key: _point_to_list(value) for key, value in vertices.items()},
        "tangency_points": {key: _point_to_list(value) for key, value in tangencies.items()},
        "incircle_center": _point_to_list(center),
        "incircle_radius_px": round(float(radius_px), 3),
        "polygon_bbox": bbox_to_list(polygon_bbox),
        "circle_bbox": bbox_to_list(circle_bbox),
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "rotation_degrees": round(math.degrees(float(angle)), 3),
        "scale_px_per_unit": round(float(scale), 3),
    }
    return RenderedTangentialScene(
        image=ctx.image,
        annotation_keyed_points={key: tuple(value) for key, value in annotation.items()},
        annotation_roles=tuple(TANGENTIAL_ANNOTATION_KEYS),
        vertices=dict(vertices),
        tangency_points=dict(tangencies),
        label_bboxes=dict(label_bboxes),
        render_map=dict(render_map),
    )


def make_tangential_prompt_examples() -> tuple[str, str]:
    annotation = {
        "vertex_A": [180, 360],
        "vertex_B": [350, 140],
        "vertex_C": [560, 220],
        "vertex_D": [500, 430],
        "tangent_AB": [280, 240],
        "tangent_BC": [440, 175],
        "tangent_CD": [535, 325],
        "tangent_DA": [330, 410],
        "incircle_center": [390, 285],
    }
    return dump_prompt_json_examples(annotation=annotation, answer=26, ensure_ascii=False)


def make_angle_prompt_examples() -> tuple[str, str]:
    annotation = {
        "shape_corner_A": [180, 120],
        "shape_corner_B": [540, 120],
        "shape_corner_C": [540, 480],
        "shape_corner_D": [180, 480],
        "circle_center": [360, 300],
        "tangent_point": [250, 160],
        "known_angle_vertex": [300, 120],
        "known_angle_reference_point": [390, 120],
        "target_angle_vertex": [360, 300],
        "target_reference_point": [360, 130],
    }
    return dump_prompt_json_examples(annotation=annotation, answer=45, ensure_ascii=False)


__all__ = [
    "ANGLE_SUPPORT",
    "CONSTRUCTION_KINDS",
    "PROMPT_BUNDLE_ID",
    "RenderedAngleScene",
    "RenderedTangentialScene",
    "ResolvedAngleProblem",
    "ResolvedTangentialProblem",
    "SCENE_ID",
    "SIDE_SIGN_SUPPORT",
    "TANGENT_CASES",
    "TARGET_PAIRS",
    "make_angle_prompt_examples",
    "make_render_context",
    "make_tangential_prompt_examples",
    "render_angle_scene",
    "render_tangential_scene",
    "resolve_angle_problem",
    "resolve_tangential_problem",
]
