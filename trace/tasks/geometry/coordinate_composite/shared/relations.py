"""Coordinate-object construction and intersection relations."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from trace.tasks.geometry.shared.vector2d import point_to_list

from .state import CircleObject, GraphPoint, LineObject, PairFilter, PolygonObject, SceneObject

_EPS = 1e-7


def transform_point(point: GraphPoint, transform: str) -> GraphPoint:
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


def transform_object(obj: SceneObject, transform: str) -> SceneObject:
    if isinstance(obj, LineObject):
        return LineObject(
            object_id=str(obj.object_id),
            p0=transform_point(obj.p0, transform),
            p1=transform_point(obj.p1, transform),
        )
    if isinstance(obj, CircleObject):
        return CircleObject(
            object_id=str(obj.object_id),
            center=transform_point(obj.center, transform),
            radius=float(obj.radius),
        )
    return PolygonObject(
        object_id=str(obj.object_id),
        vertices=tuple(transform_point(point, transform) for point in obj.vertices),
    )


def line_object(object_id: str, p0: GraphPoint, p1: GraphPoint) -> LineObject:
    return LineObject(object_id=str(object_id), p0=(float(p0[0]), float(p0[1])), p1=(float(p1[0]), float(p1[1])))


def circle_object(object_id: str, center: GraphPoint, radius: float) -> CircleObject:
    return CircleObject(object_id=str(object_id), center=(float(center[0]), float(center[1])), radius=float(radius))


def polygon_object(object_id: str, vertices: Sequence[GraphPoint]) -> PolygonObject:
    return PolygonObject(
        object_id=str(object_id),
        vertices=tuple((float(point[0]), float(point[1])) for point in vertices),
    )


def object_to_trace(obj: SceneObject) -> Dict[str, Any]:
    if isinstance(obj, LineObject):
        return {"id": str(obj.object_id), "kind": "line_segment", "p0": point_to_list(obj.p0), "p1": point_to_list(obj.p1)}
    if isinstance(obj, CircleObject):
        return {
            "id": str(obj.object_id),
            "kind": "circle",
            "center": point_to_list(obj.center),
            "radius": round(float(obj.radius), 3),
        }
    return {"id": str(obj.object_id), "kind": "polygon", "vertices": [point_to_list(point) for point in obj.vertices]}


def dedupe_points(points: Iterable[GraphPoint], *, tol: float = 1e-5) -> Tuple[GraphPoint, ...]:
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


def _circle_segment_intersections(circle: CircleObject, p0: GraphPoint, p1: GraphPoint) -> Tuple[GraphPoint, ...]:
    x0, y0 = float(p0[0]) - circle.center[0], float(p0[1]) - circle.center[1]
    x1, y1 = float(p1[0]) - circle.center[0], float(p1[1]) - circle.center[1]
    dx, dy = x1 - x0, y1 - y0
    a = (dx * dx) + (dy * dy)
    b = 2.0 * ((x0 * dx) + (y0 * dy))
    c = (x0 * x0) + (y0 * y0) - (float(circle.radius) ** 2)
    disc = (b * b) - (4.0 * a * c)
    if disc < -_EPS:
        return tuple()
    if abs(disc) <= _EPS:
        roots = [-b / (2.0 * a)]
    else:
        sqrt_disc = math.sqrt(max(0.0, disc))
        roots = [(-b - sqrt_disc) / (2.0 * a), (-b + sqrt_disc) / (2.0 * a)]
    points: List[GraphPoint] = []
    for t_value in roots:
        if -_EPS <= float(t_value) <= 1.0 + _EPS:
            points.append((circle.center[0] + x0 + (t_value * dx), circle.center[1] + y0 + (t_value * dy)))
    return dedupe_points(points)


def _circle_circle_intersections(a: CircleObject, b: CircleObject) -> Tuple[GraphPoint, ...]:
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
    return dedupe_points(((base_x + rx, base_y + ry), (base_x - rx, base_y - ry)))


def _polygon_edges(polygon: PolygonObject) -> Tuple[Tuple[GraphPoint, GraphPoint], ...]:
    vertices = tuple(polygon.vertices)
    return tuple((vertices[index], vertices[(index + 1) % len(vertices)]) for index in range(len(vertices)))


def object_pair_intersections(a: SceneObject, b: SceneObject) -> Tuple[GraphPoint, ...]:
    """Return all visible boundary intersections for one unordered object pair."""

    if isinstance(a, LineObject) and isinstance(b, LineObject):
        return _segment_intersection(a.p0, a.p1, b.p0, b.p1)
    if isinstance(a, CircleObject) and isinstance(b, CircleObject):
        return _circle_circle_intersections(a, b)
    if isinstance(a, LineObject) and isinstance(b, CircleObject):
        return _circle_segment_intersections(b, a.p0, a.p1)
    if isinstance(a, CircleObject) and isinstance(b, LineObject):
        return _circle_segment_intersections(a, b.p0, b.p1)
    if isinstance(a, LineObject) and isinstance(b, PolygonObject):
        return dedupe_points(point for edge in _polygon_edges(b) for point in _segment_intersection(a.p0, a.p1, edge[0], edge[1]))
    if isinstance(a, PolygonObject) and isinstance(b, LineObject):
        return object_pair_intersections(b, a)
    if isinstance(a, CircleObject) and isinstance(b, PolygonObject):
        return dedupe_points(point for edge in _polygon_edges(b) for point in _circle_segment_intersections(a, edge[0], edge[1]))
    if isinstance(a, PolygonObject) and isinstance(b, CircleObject):
        return object_pair_intersections(b, a)
    if isinstance(a, PolygonObject) and isinstance(b, PolygonObject):
        return dedupe_points(
            point
            for edge_a in _polygon_edges(a)
            for edge_b in _polygon_edges(b)
            for point in _segment_intersection(edge_a[0], edge_a[1], edge_b[0], edge_b[1])
        )
    return tuple()


def pair_matches_filter(obj_a: SceneObject, obj_b: SceneObject, pair_filter: PairFilter) -> bool:
    if pair_filter is PairFilter.ALL:
        return True
    pair = (obj_a, obj_b)
    if pair_filter is PairFilter.LINE_CIRCLE:
        return any(isinstance(item, LineObject) for item in pair) and any(isinstance(item, CircleObject) for item in pair)
    if pair_filter is PairFilter.CIRCLE_CIRCLE:
        return isinstance(obj_a, CircleObject) and isinstance(obj_b, CircleObject)
    if pair_filter is PairFilter.LINE_POLYGON:
        return any(isinstance(item, LineObject) for item in pair) and any(isinstance(item, PolygonObject) for item in pair)
    if pair_filter is PairFilter.CIRCLE_POLYGON:
        return any(isinstance(item, CircleObject) for item in pair) and any(isinstance(item, PolygonObject) for item in pair)
    raise ValueError(f"unsupported coordinate-composite pair filter: {pair_filter!r}")


def filtered_intersections(objects: Sequence[SceneObject], pair_filter: PairFilter) -> Tuple[GraphPoint, ...]:
    points: List[GraphPoint] = []
    scene_objects = tuple(objects)
    for index, obj_a in enumerate(scene_objects):
        for obj_b in scene_objects[index + 1 :]:
            if pair_matches_filter(obj_a, obj_b, pair_filter):
                points.extend(object_pair_intersections(obj_a, obj_b))
    return dedupe_points(points)


__all__ = [
    "circle_object",
    "dedupe_points",
    "filtered_intersections",
    "line_object",
    "object_pair_intersections",
    "object_to_trace",
    "pair_matches_filter",
    "polygon_object",
    "transform_object",
    "transform_point",
]
