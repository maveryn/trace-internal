"""Coordinate-composite intersection count tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ..shared.background_defaults import load_geometry_background_defaults

SCENE_ID = "coordinate_composite"
from trace.tasks.shared.fixed_query import geometry_selected_probability_map as _probability_map
from ..shared.graph_rendering import graph_paper_grid_from_frame, graph_units_to_pixel, scale_point
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.single_object_scene import finalize_graph_scene_image, make_graph_scene_canvas, resolve_graph_scene_context
from ..shared.vector2d import point_to_list as _point_to_list


GraphPoint = Tuple[float, float]
PixelPoint = Tuple[float, float]
Color = Tuple[int, int, int]

TASK_ID = "task_geometry__coordinate_composite__intersection_point_count"
PROMPT_BUNDLE_ID = "geometry_coordinate_composite_v0"

QUERY_IDS: Tuple[str, ...] = (
    "line_circle_intersection_count",
    "circle_circle_intersection_count",
    "line_polygon_intersection_count",
    "circle_polygon_intersection_count",
    "mixed_object_intersection_count",
)
TRANSFORMS: Tuple[str, ...] = ("identity", "reflect_x", "reflect_y", "rotate90", "rotate180")

_SCENE_DEFAULTS = get_scene_defaults("geometry", "coordinate_composite")
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(scene_id=SCENE_ID)
_NOISE_DEFAULTS = load_geometry_noise_defaults(scene_id=SCENE_ID)


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_size_min: int = 660
    canvas_size_max: int = 740
    graph_cells_min: int = 18
    graph_cells_max: int = 20
    line_width_min: int = 3
    line_width_max: int = 5
    circle_width_min: int = 3
    circle_width_max: int = 5
    polygon_width_min: int = 3
    polygon_width_max: int = 5


@dataclass(frozen=True)
class _LineObject:
    object_id: str
    p0: GraphPoint
    p1: GraphPoint


@dataclass(frozen=True)
class _CircleObject:
    object_id: str
    center: GraphPoint
    radius: float


@dataclass(frozen=True)
class _PolygonObject:
    object_id: str
    vertices: Tuple[GraphPoint, ...]


SceneObject = _LineObject | _CircleObject | _PolygonObject


@dataclass(frozen=True)
class _CompositeCase:
    query_id: str
    case_id: str
    objects: Tuple[SceneObject, ...]
    expected_count: int


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    case: _CompositeCase
    transform: str
    query_id_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    case_probabilities: Dict[str, float]
    transform_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    intersection_points_px: Tuple[PixelPoint, ...]
    intersection_points_graph: Tuple[GraphPoint, ...]
    object_specs: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    render_spec_extra: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_EPS = 1e-7


def _split_defaults_for_task() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    return split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
        task_id=TASK_ID,
    )


def _transform_point(point: GraphPoint, transform: str) -> GraphPoint:
    x_value = float(point[0])
    y_value = float(point[1])
    if transform == "identity":
        return (x_value, y_value)
    if transform == "reflect_x":
        return (x_value, -y_value)
    if transform == "reflect_y":
        return (-x_value, y_value)
    if transform == "rotate90":
        return (-y_value, x_value)
    if transform == "rotate180":
        return (-x_value, -y_value)
    raise ValueError(f"unsupported coordinate-composite transform: {transform}")


def _transform_object(obj: SceneObject, transform: str) -> SceneObject:
    if isinstance(obj, _LineObject):
        return _LineObject(
            object_id=str(obj.object_id),
            p0=_transform_point(obj.p0, transform),
            p1=_transform_point(obj.p1, transform),
        )
    if isinstance(obj, _CircleObject):
        return _CircleObject(
            object_id=str(obj.object_id),
            center=_transform_point(obj.center, transform),
            radius=float(obj.radius),
        )
    return _PolygonObject(
        object_id=str(obj.object_id),
        vertices=tuple(_transform_point(point, transform) for point in obj.vertices),
    )


def _line(object_id: str, p0: GraphPoint, p1: GraphPoint) -> _LineObject:
    return _LineObject(object_id=str(object_id), p0=(float(p0[0]), float(p0[1])), p1=(float(p1[0]), float(p1[1])))


def _circle(object_id: str, center: GraphPoint, radius: float) -> _CircleObject:
    return _CircleObject(object_id=str(object_id), center=(float(center[0]), float(center[1])), radius=float(radius))


def _polygon(object_id: str, vertices: Sequence[GraphPoint]) -> _PolygonObject:
    return _PolygonObject(
        object_id=str(object_id),
        vertices=tuple((float(point[0]), float(point[1])) for point in vertices),
    )


def _cases() -> Tuple[_CompositeCase, ...]:
    rect = ((-3.0, -2.0), (3.0, -2.0), (3.0, 2.0), (-3.0, 2.0))
    wide_rect = ((-4.0, -3.0), (4.0, -3.0), (4.0, 3.0), (-4.0, 3.0))
    return (
        _CompositeCase(
            query_id="line_circle_intersection_count",
            case_id="line_circle_zero_points",
            objects=(_line("line_a", (-7.0, 5.0), (7.0, 5.0)), _circle("circle_b", (0.0, 0.0), 2.0)),
            expected_count=0,
        ),
        _CompositeCase(
            query_id="line_circle_intersection_count",
            case_id="line_circle_one_tangent",
            objects=(_line("line_a", (-7.0, 2.0), (7.0, 2.0)), _circle("circle_b", (0.0, 0.0), 2.0)),
            expected_count=1,
        ),
        _CompositeCase(
            query_id="line_circle_intersection_count",
            case_id="line_circle_two_secant",
            objects=(_line("line_a", (-7.0, 0.0), (7.0, 0.0)), _circle("circle_b", (0.0, 0.0), 2.0)),
            expected_count=2,
        ),
        _CompositeCase(
            query_id="line_circle_intersection_count",
            case_id="line_circle_three_two_plus_tangent",
            objects=(
                _line("line_a", (-7.0, 0.0), (7.0, 0.0)),
                _circle("circle_b", (-3.0, 0.0), 1.0),
                _circle("circle_c", (3.0, 1.0), 1.0),
            ),
            expected_count=3,
        ),
        _CompositeCase(
            query_id="line_circle_intersection_count",
            case_id="line_circle_four_two_secants",
            objects=(
                _line("line_a", (-7.0, 0.0), (7.0, 0.0)),
                _circle("circle_b", (-3.0, 0.0), 1.0),
                _circle("circle_c", (3.0, 0.0), 1.0),
            ),
            expected_count=4,
        ),
        _CompositeCase(
            query_id="circle_circle_intersection_count",
            case_id="circle_circle_zero_separate",
            objects=(_circle("circle_a", (-5.0, 0.0), 1.5), _circle("circle_b", (1.0, 0.0), 1.5)),
            expected_count=0,
        ),
        _CompositeCase(
            query_id="circle_circle_intersection_count",
            case_id="circle_circle_one_tangent",
            objects=(_circle("circle_a", (-2.0, 0.0), 2.0), _circle("circle_b", (2.0, 0.0), 2.0)),
            expected_count=1,
        ),
        _CompositeCase(
            query_id="circle_circle_intersection_count",
            case_id="circle_circle_two_overlap",
            objects=(_circle("circle_a", (-2.0, 0.0), 3.0), _circle("circle_b", (2.0, 0.0), 3.0)),
            expected_count=2,
        ),
        _CompositeCase(
            query_id="circle_circle_intersection_count",
            case_id="circle_circle_three_mixed",
            objects=(_circle("circle_a", (0.0, 0.0), 2.0), _circle("circle_b", (4.0, 0.0), 2.0), _circle("circle_c", (0.0, 4.0), 3.0)),
            expected_count=3,
        ),
        _CompositeCase(
            query_id="circle_circle_intersection_count",
            case_id="circle_circle_four_two_pairs",
            objects=(
                _circle("circle_a", (-5.0, 0.0), 1.6),
                _circle("circle_b", (-2.5, 0.0), 1.6),
                _circle("circle_c", (2.5, 0.0), 1.6),
                _circle("circle_d", (5.0, 0.0), 1.6),
            ),
            expected_count=4,
        ),
        _CompositeCase(
            query_id="line_polygon_intersection_count",
            case_id="line_polygon_zero_external",
            objects=(_line("line_a", (-7.0, 4.0), (7.0, 4.0)), _polygon("polygon_b", rect)),
            expected_count=0,
        ),
        _CompositeCase(
            query_id="line_polygon_intersection_count",
            case_id="line_polygon_one_corner_touch",
            objects=(_line("line_a", (-7.0, 2.0), (-3.0, 2.0)), _polygon("polygon_b", rect)),
            expected_count=1,
        ),
        _CompositeCase(
            query_id="line_polygon_intersection_count",
            case_id="line_polygon_two_crossing",
            objects=(_line("line_a", (-7.0, 0.0), (7.0, 0.0)), _polygon("polygon_b", rect)),
            expected_count=2,
        ),
        _CompositeCase(
            query_id="line_polygon_intersection_count",
            case_id="line_polygon_three_cross_and_touch",
            objects=(_line("line_a", (-7.0, 0.0), (7.0, 0.0)), _line("line_b", (-7.0, 2.0), (-3.0, 2.0)), _polygon("polygon_c", rect)),
            expected_count=3,
        ),
        _CompositeCase(
            query_id="line_polygon_intersection_count",
            case_id="line_polygon_four_two_crossings",
            objects=(_line("line_a", (-7.0, 0.0), (7.0, 0.0)), _line("line_b", (0.0, -6.0), (0.0, 6.0)), _polygon("polygon_c", rect)),
            expected_count=4,
        ),
        _CompositeCase(
            query_id="circle_polygon_intersection_count",
            case_id="circle_polygon_zero_inside",
            objects=(_circle("circle_a", (0.0, 0.0), 1.0), _polygon("polygon_b", wide_rect)),
            expected_count=0,
        ),
        _CompositeCase(
            query_id="circle_polygon_intersection_count",
            case_id="circle_polygon_one_tangent",
            objects=(_circle("circle_a", (0.0, 0.0), 2.0), _polygon("polygon_b", ((-4.0, 2.0), (4.0, 2.0), (4.0, 5.0), (-4.0, 5.0)))),
            expected_count=1,
        ),
        _CompositeCase(
            query_id="circle_polygon_intersection_count",
            case_id="circle_polygon_two_tangencies",
            objects=(_circle("circle_a", (0.0, 0.0), 2.0), _polygon("polygon_b", ((-2.0, -3.0), (2.0, -3.0), (2.0, 3.0), (-2.0, 3.0)))),
            expected_count=2,
        ),
        _CompositeCase(
            query_id="circle_polygon_intersection_count",
            case_id="circle_polygon_three_tangent_plus_two",
            objects=(
                _circle("circle_a", (0.0, 0.0), 2.0),
                _polygon("polygon_b", ((-2.0, -3.0), (2.0, -3.0), (2.0, 3.0), (-2.0, 3.0))),
                _polygon("polygon_c", ((-4.0, 2.0), (4.0, 2.0), (4.0, 5.0), (-4.0, 5.0))),
            ),
            expected_count=3,
        ),
        _CompositeCase(
            query_id="circle_polygon_intersection_count",
            case_id="circle_polygon_four_crossings",
            objects=(_circle("circle_a", (0.0, 0.0), 3.0), _polygon("polygon_b", ((-4.0, -2.0), (4.0, -2.0), (4.0, 2.0), (-4.0, 2.0)))),
            expected_count=4,
        ),
        _CompositeCase(
            query_id="mixed_object_intersection_count",
            case_id="mixed_zero_separate",
            objects=(
                _line("line_a", (-7.0, -5.0), (7.0, -5.0)),
                _circle("circle_b", (0.0, 0.0), 2.0),
                _polygon("polygon_c", ((4.0, -2.0), (7.0, -2.0), (7.0, 2.0), (4.0, 2.0))),
            ),
            expected_count=0,
        ),
        _CompositeCase(
            query_id="mixed_object_intersection_count",
            case_id="mixed_one_tangent",
            objects=(
                _line("line_a", (-7.0, 2.0), (2.0, 2.0)),
                _circle("circle_b", (0.0, 0.0), 2.0),
                _polygon("polygon_c", ((4.0, -2.0), (7.0, -2.0), (7.0, 2.0), (4.0, 2.0))),
            ),
            expected_count=1,
        ),
        _CompositeCase(
            query_id="mixed_object_intersection_count",
            case_id="mixed_two_secant",
            objects=(
                _line("line_a", (-7.0, 0.0), (2.0, 0.0)),
                _circle("circle_b", (0.0, 0.0), 2.0),
                _polygon("polygon_c", ((4.0, -2.0), (7.0, -2.0), (7.0, 2.0), (4.0, 2.0))),
            ),
            expected_count=2,
        ),
        _CompositeCase(
            query_id="mixed_object_intersection_count",
            case_id="mixed_three_line_circle_rectangle",
            objects=(
                _line("line_a", (-7.0, 0.0), (7.0, 0.0)),
                _circle("circle_b", (0.0, 3.0), 3.0),
                _polygon("polygon_c", ((4.0, -2.0), (7.0, -2.0), (7.0, 2.0), (4.0, 2.0))),
            ),
            expected_count=3,
        ),
        _CompositeCase(
            query_id="mixed_object_intersection_count",
            case_id="mixed_four_line_circle_rectangle",
            objects=(
                _line("line_a", (-7.0, 1.0), (7.0, 1.0)),
                _circle("circle_b", (-2.0, 1.0), 2.0),
                _polygon("polygon_c", ((3.0, -1.0), (6.0, -1.0), (6.0, 3.0), (3.0, 3.0))),
            ),
            expected_count=4,
        ),
    )


_ALL_CASES: Tuple[_CompositeCase, ...] = _cases()
_CASES_BY_QUERY: Dict[str, Tuple[_CompositeCase, ...]] = {
    query_id: tuple(case for case in _ALL_CASES if case.query_id == query_id) for query_id in QUERY_IDS
}


def _dedupe_points(points: Iterable[GraphPoint], *, tol: float = 1e-5) -> Tuple[GraphPoint, ...]:
    unique: List[GraphPoint] = []
    for point in points:
        candidate = (float(point[0]), float(point[1]))
        if not any(abs(candidate[0] - prior[0]) <= tol and abs(candidate[1] - prior[1]) <= tol for prior in unique):
            unique.append(candidate)
    return tuple(sorted(unique, key=lambda item: (round(float(item[0]), 6), round(float(item[1]), 6))))


def _segment_intersection(a0: GraphPoint, a1: GraphPoint, b0: GraphPoint, b1: GraphPoint) -> Tuple[GraphPoint, ...]:
    ax, ay = float(a0[0]), float(a0[1])
    bx, by = float(a1[0]), float(a1[1])
    cx, cy = float(b0[0]), float(b0[1])
    dx, dy = float(b1[0]), float(b1[1])
    rx, ry = bx - ax, by - ay
    sx, sy = dx - cx, dy - cy
    denom = (rx * sy) - (ry * sx)
    if abs(denom) <= _EPS:
        return tuple()
    qpx, qpy = cx - ax, cy - ay
    t = ((qpx * sy) - (qpy * sx)) / denom
    u = ((qpx * ry) - (qpy * rx)) / denom
    if -_EPS <= t <= 1.0 + _EPS and -_EPS <= u <= 1.0 + _EPS:
        return ((ax + (t * rx), ay + (t * ry)),)
    return tuple()


def _circle_segment_intersections(circle: _CircleObject, p0: GraphPoint, p1: GraphPoint) -> Tuple[GraphPoint, ...]:
    x0, y0 = float(p0[0]) - circle.center[0], float(p0[1]) - circle.center[1]
    x1, y1 = float(p1[0]) - circle.center[0], float(p1[1]) - circle.center[1]
    dx, dy = x1 - x0, y1 - y0
    a = (dx * dx) + (dy * dy)
    b = 2.0 * ((x0 * dx) + (y0 * dy))
    c = (x0 * x0) + (y0 * y0) - (float(circle.radius) ** 2)
    disc = (b * b) - (4.0 * a * c)
    if disc < -_EPS:
        return tuple()
    roots: List[float]
    if abs(disc) <= _EPS:
        roots = [-b / (2.0 * a)]
    else:
        sqrt_disc = math.sqrt(max(0.0, disc))
        roots = [(-b - sqrt_disc) / (2.0 * a), (-b + sqrt_disc) / (2.0 * a)]
    points: List[GraphPoint] = []
    for t_value in roots:
        if -_EPS <= float(t_value) <= 1.0 + _EPS:
            points.append((circle.center[0] + x0 + (t_value * dx), circle.center[1] + y0 + (t_value * dy)))
    return _dedupe_points(points)


def _circle_circle_intersections(a: _CircleObject, b: _CircleObject) -> Tuple[GraphPoint, ...]:
    x0, y0 = float(a.center[0]), float(a.center[1])
    x1, y1 = float(b.center[0]), float(b.center[1])
    r0, r1 = float(a.radius), float(b.radius)
    dx, dy = x1 - x0, y1 - y0
    distance = math.hypot(dx, dy)
    if distance <= _EPS:
        return tuple()
    if distance > r0 + r1 + _EPS:
        return tuple()
    if distance < abs(r0 - r1) - _EPS:
        return tuple()
    along = ((r0 * r0) - (r1 * r1) + (distance * distance)) / (2.0 * distance)
    height_sq = (r0 * r0) - (along * along)
    base_x = x0 + (along * dx / distance)
    base_y = y0 + (along * dy / distance)
    if abs(height_sq) <= _EPS:
        return ((base_x, base_y),)
    if height_sq < 0.0:
        return tuple()
    height = math.sqrt(height_sq)
    rx = -dy * (height / distance)
    ry = dx * (height / distance)
    return _dedupe_points(((base_x + rx, base_y + ry), (base_x - rx, base_y - ry)))


def _polygon_edges(polygon: _PolygonObject) -> Tuple[Tuple[GraphPoint, GraphPoint], ...]:
    vertices = tuple(polygon.vertices)
    return tuple((vertices[index], vertices[(index + 1) % len(vertices)]) for index in range(len(vertices)))


def _object_pair_intersections(a: SceneObject, b: SceneObject) -> Tuple[GraphPoint, ...]:
    if isinstance(a, _LineObject) and isinstance(b, _LineObject):
        return _segment_intersection(a.p0, a.p1, b.p0, b.p1)
    if isinstance(a, _CircleObject) and isinstance(b, _CircleObject):
        return _circle_circle_intersections(a, b)
    if isinstance(a, _LineObject) and isinstance(b, _CircleObject):
        return _circle_segment_intersections(b, a.p0, a.p1)
    if isinstance(a, _CircleObject) and isinstance(b, _LineObject):
        return _circle_segment_intersections(a, b.p0, b.p1)
    if isinstance(a, _LineObject) and isinstance(b, _PolygonObject):
        return _dedupe_points(point for edge in _polygon_edges(b) for point in _segment_intersection(a.p0, a.p1, edge[0], edge[1]))
    if isinstance(a, _PolygonObject) and isinstance(b, _LineObject):
        return _object_pair_intersections(b, a)
    if isinstance(a, _CircleObject) and isinstance(b, _PolygonObject):
        return _dedupe_points(point for edge in _polygon_edges(b) for point in _circle_segment_intersections(a, edge[0], edge[1]))
    if isinstance(a, _PolygonObject) and isinstance(b, _CircleObject):
        return _object_pair_intersections(b, a)
    if isinstance(a, _PolygonObject) and isinstance(b, _PolygonObject):
        return _dedupe_points(
            point
            for edge_a in _polygon_edges(a)
            for edge_b in _polygon_edges(b)
            for point in _segment_intersection(edge_a[0], edge_a[1], edge_b[0], edge_b[1])
        )
    return tuple()


def _all_intersections(objects: Sequence[SceneObject]) -> Tuple[GraphPoint, ...]:
    points: List[GraphPoint] = []
    for index, obj_a in enumerate(objects):
        for obj_b in tuple(objects)[index + 1 :]:
            points.extend(_object_pair_intersections(obj_a, obj_b))
    return _dedupe_points(points)


def _query_intersections(query_id: str, objects: Sequence[SceneObject]) -> Tuple[GraphPoint, ...]:
    """Return the visible intersections that are in scope for one query branch."""

    normalized_query = str(query_id)
    if normalized_query == "mixed_object_intersection_count":
        return _all_intersections(objects)

    points: List[GraphPoint] = []
    for index, obj_a in enumerate(objects):
        for obj_b in tuple(objects)[index + 1 :]:
            pair = (obj_a, obj_b)
            if normalized_query == "line_circle_intersection_count":
                if not any(isinstance(item, _LineObject) for item in pair) or not any(
                    isinstance(item, _CircleObject) for item in pair
                ):
                    continue
            elif normalized_query == "circle_circle_intersection_count":
                if not (isinstance(obj_a, _CircleObject) and isinstance(obj_b, _CircleObject)):
                    continue
            elif normalized_query == "line_polygon_intersection_count":
                if not any(isinstance(item, _LineObject) for item in pair) or not any(
                    isinstance(item, _PolygonObject) for item in pair
                ):
                    continue
            elif normalized_query == "circle_polygon_intersection_count":
                if not any(isinstance(item, _CircleObject) for item in pair) or not any(
                    isinstance(item, _PolygonObject) for item in pair
                ):
                    continue
            else:
                raise ValueError(f"unsupported query_id for intersection filtering: {query_id!r}")
            points.extend(_object_pair_intersections(obj_a, obj_b))
    return _dedupe_points(points)


def _resolve_problem(instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    explicit_query = params.get("query_id")
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in QUERY_IDS:
            raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id!r}")
        query_probabilities = _probability_map(QUERY_IDS, selected=query_id)
    else:
        query_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.query_id")
        query_id = str(QUERY_IDS[int(query_index) % len(QUERY_IDS)])
        query_probabilities = _probability_map(QUERY_IDS)

    cases = _CASES_BY_QUERY[str(query_id)]
    target_counts = tuple(sorted({int(case.expected_count) for case in cases}))
    explicit_target = params.get("target_count")
    eligible_cases = tuple(cases)
    if explicit_target is not None:
        target_count = int(explicit_target)
        if target_count not in set(target_counts):
            raise ValueError(f"target_count={target_count} is not supported for {query_id}")
        eligible_cases = tuple(case for case in cases if int(case.expected_count) == int(target_count))
        target_count_probabilities = _probability_map(target_counts, selected=target_count)
    else:
        target_count_probabilities = _probability_map(target_counts)

    explicit_case = params.get("case_id")
    if explicit_case is not None:
        case_id = str(explicit_case)
        matching = tuple(case for case in eligible_cases if str(case.case_id) == case_id)
        if not matching:
            raise ValueError(f"case_id={case_id!r} is not valid for {query_id}")
        case = matching[0]
        case_probabilities = _probability_map((case.case_id for case in eligible_cases), selected=case.case_id)
    else:
        case_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.{query_id}.case_id")
        case = eligible_cases[int(case_index) % len(eligible_cases)]
        case_probabilities = _probability_map(tuple(case.case_id for case in eligible_cases))

    explicit_transform = params.get("transform")
    if explicit_transform is not None:
        transform = str(explicit_transform)
        if transform not in TRANSFORMS:
            raise ValueError(f"transform={transform!r} is not valid for {TASK_ID}")
        transform_probabilities = _probability_map(TRANSFORMS, selected=transform)
    else:
        transform_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.transform")
        transform = str(TRANSFORMS[int(transform_index) % len(TRANSFORMS)])
        transform_probabilities = _probability_map(TRANSFORMS)

    return _ResolvedProblem(
        query_id=str(query_id),
        case=case,
        transform=str(transform),
        query_id_probabilities=dict(query_probabilities),
        target_count_probabilities=dict(target_count_probabilities),
        case_probabilities=dict(case_probabilities),
        transform_probabilities=dict(transform_probabilities),
    )


def _object_to_trace(obj: SceneObject) -> Dict[str, Any]:
    if isinstance(obj, _LineObject):
        return {"id": str(obj.object_id), "kind": "line_segment", "p0": _point_to_list(obj.p0), "p1": _point_to_list(obj.p1)}
    if isinstance(obj, _CircleObject):
        return {
            "id": str(obj.object_id),
            "kind": "circle",
            "center": _point_to_list(obj.center),
            "radius": round(float(obj.radius), 3),
        }
    return {"id": str(obj.object_id), "kind": "polygon", "vertices": [_point_to_list(point) for point in obj.vertices]}


def _draw_object(
    draw: ImageDraw.ImageDraw,
    obj: SceneObject,
    *,
    color: Color,
    context: Any,
    width_px: int,
) -> Dict[str, Any]:
    scale = int(context.scene_scale)
    width_render = max(1, int(width_px) * int(scale))
    if isinstance(obj, _LineObject):
        p0 = scale_point(
            graph_units_to_pixel(obj.p0, origin=context.graph_origin, spacing=int(context.graph_spacing)),
            int(scale),
        )
        p1 = scale_point(
            graph_units_to_pixel(obj.p1, origin=context.graph_origin, spacing=int(context.graph_spacing)),
            int(scale),
        )
        draw.line([p0, p1], fill=color, width=width_render)
        return {"id": str(obj.object_id), "kind": "line_segment", "p0_px": _point_to_list(p0), "p1_px": _point_to_list(p1)}
    if isinstance(obj, _CircleObject):
        center_px = scale_point(
            graph_units_to_pixel(obj.center, origin=context.graph_origin, spacing=int(context.graph_spacing)),
            int(scale),
        )
        radius_px = float(obj.radius) * float(context.graph_spacing) * float(scale)
        bbox = [
            float(center_px[0]) - radius_px,
            float(center_px[1]) - radius_px,
            float(center_px[0]) + radius_px,
            float(center_px[1]) + radius_px,
        ]
        draw.ellipse(bbox, outline=color, width=width_render)
        return {
            "id": str(obj.object_id),
            "kind": "circle",
            "center_px": _point_to_list(center_px),
            "radius_px": round(float(radius_px), 3),
        }
    vertices = [
        scale_point(
            graph_units_to_pixel(point, origin=context.graph_origin, spacing=int(context.graph_spacing)),
            int(scale),
        )
        for point in obj.vertices
    ]
    draw.line([*vertices, vertices[0]], fill=color, width=width_render, joint="curve")
    return {"id": str(obj.object_id), "kind": "polygon", "vertices_px": [_point_to_list(point) for point in vertices]}


def _sample_object_colors(rng, *, shape_color: Color) -> Tuple[Color, ...]:
    base = tuple(int(value) for value in shape_color)
    palette: Tuple[Color, ...] = (
        base,
        (max(24, min(210, base[2] + 35)), max(24, min(175, base[0] + 12)), max(24, min(190, base[1] - 18))),
        (max(24, min(190, base[1] + 24)), max(24, min(190, base[2] - 8)), max(24, min(190, base[0] + 40))),
        (max(24, min(200, base[0] - 20)), max(24, min(190, base[1] + 30)), max(24, min(200, base[2] + 20))),
    )
    offset = int(rng.randrange(len(palette)))
    return tuple(palette[(offset + index) % len(palette)] for index in range(len(palette)))


def _render_scene(
    *,
    instance_seed: int,
    problem: _ResolvedProblem,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render")
    context = resolve_graph_scene_context(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        background_defaults=_BACKGROUND_DEFAULTS,
        fallback_canvas_min=int(group_default(render_defaults, "coordinate_composite_canvas_size_min", _DEFAULTS.canvas_size_min)),
        fallback_canvas_max=int(group_default(render_defaults, "coordinate_composite_canvas_size_max", _DEFAULTS.canvas_size_max)),
        fallback_cells_min=int(group_default(render_defaults, "coordinate_composite_graph_cells_min", _DEFAULTS.graph_cells_min)),
        fallback_cells_max=int(group_default(render_defaults, "coordinate_composite_graph_cells_max", _DEFAULTS.graph_cells_max)),
        graph_style_overrides={
            "axis_scale_labels_enabled": False,
            "origin_label_enabled": False,
            "axis_arrows_enabled": True,
        },
    )
    image, draw, background_meta = make_graph_scene_canvas(
        instance_seed=int(instance_seed),
        context=context,
        background_defaults=_BACKGROUND_DEFAULTS,
        require_graph_paper=True,
    )
    shape_style = sample_geometry_shape_style(
        rng,
        params=params,
        render_defaults=render_defaults,
        anchor_colors=extract_background_anchor_colors(background_meta),
    )
    objects = tuple(_transform_object(obj, str(problem.transform)) for obj in problem.case.objects)
    intersections = _query_intersections(str(problem.query_id), objects)
    if len(intersections) != int(problem.case.expected_count):
        raise RuntimeError(
            f"{TASK_ID} case {problem.case.case_id} expected {problem.case.expected_count} intersections, got {len(intersections)}"
        )

    line_width = int(
        rng.randint(
            int(group_default(render_defaults, "coordinate_composite_line_width_min", _DEFAULTS.line_width_min)),
            int(group_default(render_defaults, "coordinate_composite_line_width_max", _DEFAULTS.line_width_max)),
        )
    )
    object_colors = _sample_object_colors(rng, shape_color=shape_style.line_color)
    drawn_objects: List[Dict[str, Any]] = []
    for index, obj in enumerate(objects):
        drawn = _draw_object(
            draw,
            obj,
            color=tuple(int(value) for value in object_colors[int(index) % len(object_colors)]),
            context=context,
            width_px=int(line_width),
        )
        drawn["graph"] = _object_to_trace(obj)
        drawn["color"] = [int(value) for value in object_colors[int(index) % len(object_colors)]]
        drawn_objects.append(drawn)

    intersections_px = tuple(
        graph_units_to_pixel(point, origin=context.graph_origin, spacing=int(context.graph_spacing))
        for point in intersections
    )
    final_image, final_background_meta, post_noise_meta = finalize_graph_scene_image(
        image,
        instance_seed=int(instance_seed),
        context=context,
        background_meta=background_meta,
        noise_defaults=_NOISE_DEFAULTS,
    )
    render_spec_extra = {
        "graph_coordinate_frame": dict(context.graph_frame),
        "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
        "graph_layout": dict(context.graph_layout_metadata),
        "shape_style": dict(shape_style.to_trace_dict()),
        "object_colors": [[int(channel) for channel in color] for color in object_colors],
        "line_width_px": int(line_width),
    }
    render_map = {
        "objects": [dict(obj) for obj in drawn_objects],
        "intersection_points_graph": [_point_to_list(point) for point in intersections],
        "intersection_points_px": [_point_to_list(point) for point in intersections_px],
        "transform": str(problem.transform),
    }
    return _RenderedScene(
        image=final_image,
        intersection_points_px=tuple((float(point[0]), float(point[1])) for point in intersections_px),
        intersection_points_graph=tuple((float(point[0]), float(point[1])) for point in intersections),
        object_specs=tuple(_object_to_trace(obj) for obj in objects),
        render_map=render_map,
        background_meta=dict(final_background_meta),
        post_noise_meta=dict(post_noise_meta),
        render_spec_extra=render_spec_extra,
    )




@register_task
class GeometryCoordinateCompositeIntersectionPointCountTask:
    """Count visible intersection points in a composite coordinate scene."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_query_ids = QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        generation_defaults, render_defaults, prompt_defaults = _split_defaults_for_task()
        _ = generation_defaults
        problem = _resolve_problem(instance_seed=int(instance_seed), params=params)
        rendered = _render_scene(
            instance_seed=int(instance_seed),
            problem=problem,
            params=params,
            render_defaults=render_defaults,
        )
        answer_value = int(len(rendered.intersection_points_graph))
        annotation_value = [_point_to_list(point) for point in rendered.intersection_points_px]
        prompt_params = required_group_defaults(
            {
                **dict(prompt_defaults),
                "bundle_id": str(group_default(prompt_defaults, "bundle_id", PROMPT_BUNDLE_ID)),
                "scene_key": str(group_default(prompt_defaults, "scene_key", "coordinate_composite_scene")),
                "task_key": str(group_default(prompt_defaults, "task_key", "coordinate_composite_query")),
            },
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {TASK_ID}",
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=str(getattr(self, "scene_id", "") or getattr(self, "public_scene_id", "") or globals().get("SCENE_ID", "")),
            bundle_id=str(prompt_params["bundle_id"]),
            scene_key=str(prompt_params["scene_key"]),
            task_key=str(prompt_params["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_params["object_description"]),
                "json_output_contract": str(prompt_params["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_params["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_params["annotation_hint"]),
                "answer_hint": str(prompt_params["answer_hint_integer"]),
                "json_example": str(prompt_params["json_example"]),
                "json_example_answer_only": str(prompt_params["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
            preferred_mode=str(params.get("prompt_mode", "answer_and_annotation")),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_id": SCENE_ID,
            "query_id": str(problem.query_id),
            "scene_ir": {
                "scene_kind": "geometry_coordinate_composite",
                "scene_id": SCENE_ID,
                "objects": [dict(obj) for obj in rendered.object_specs],
            },
            "query_spec": {
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_id_probabilities),
                "target_count": int(answer_value),
                "target_count_probabilities": dict(problem.target_count_probabilities),
                "case_id": str(problem.case.case_id),
                "case_probabilities": dict(problem.case_probabilities),
                "transform": str(problem.transform),
                "transform_probabilities": dict(problem.transform_probabilities),
                "params": {
                    "query_id": str(problem.query_id),
                    "target_count": int(answer_value),
                    "case_id": str(problem.case.case_id),
                    "transform": str(problem.transform),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered.image.width),
                "canvas_height": int(rendered.image.height),
                "background": dict(rendered.background_meta),
                "post_image_noise": dict(rendered.post_noise_meta),
                **dict(rendered.render_spec_extra),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "formula_family": "coordinate_composite_intersection_count",
                "query_id": str(problem.query_id),
                "case_id": str(problem.case.case_id),
                "answer": int(answer_value),
                "intersection_points_graph": [_point_to_list(point) for point in rendered.intersection_points_graph],
                "intersection_points_px": [_point_to_list(point) for point in rendered.intersection_points_px],
            },
            "witness_symbolic": {
                "formula_family": "coordinate_composite_intersection_count",
                "objects_graph": [dict(obj) for obj in rendered.object_specs],
                "intersection_points_graph": [_point_to_list(point) for point in rendered.intersection_points_graph],
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": list(annotation_value),
                "pixel_point_set": list(annotation_value),
                "source": "intersection_points_graph_projected_to_pixels",
            },
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=TypedValue(type="point_set", value=list(annotation_value)),
            image=rendered.image,
            image_id=f"{TASK_ID}:{int(instance_seed)}",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GeometryCoordinateCompositeIntersectionPointCountTask"]
