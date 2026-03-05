"""Shared geometric layout-constraint helpers for task generators/tests.

These helpers support deterministic enforcement of non-overlap/touch policies
when tasks declare that multi-entity layouts must preserve minimum clearance.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .geometry_primitives import Point, distance_sq

Segment = Tuple[Point, Point]


def _as_point(value: Any) -> Point:
    """Parse one point-like payload into `(x, y)` floats."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("expected point-like value `[x, y]`")
    x_value = float(value[0])
    y_value = float(value[1])
    return (x_value, y_value)


def _point_to_segment_distance(point: Point, seg_start: Point, seg_end: Point) -> float:
    """Return minimum distance from one point to a closed segment."""
    start_x, start_y = float(seg_start[0]), float(seg_start[1])
    end_x, end_y = float(seg_end[0]), float(seg_end[1])
    point_x, point_y = float(point[0]), float(point[1])
    seg_dx = end_x - start_x
    seg_dy = end_y - start_y
    seg_len_sq = (seg_dx * seg_dx) + (seg_dy * seg_dy)
    if seg_len_sq <= 1e-12:
        return math.sqrt(distance_sq(point, seg_start))
    projection_t = ((point_x - start_x) * seg_dx + (point_y - start_y) * seg_dy) / seg_len_sq
    projection_t = max(0.0, min(1.0, projection_t))
    nearest = (start_x + projection_t * seg_dx, start_y + projection_t * seg_dy)
    return math.sqrt(distance_sq(point, nearest))


def _orientation(point_a: Point, point_b: Point, point_c: Point) -> int:
    """Return orientation sign for ordered triplet `point_a, point_b, point_c`."""
    value = (float(point_b[1]) - float(point_a[1])) * (float(point_c[0]) - float(point_b[0])) - (
        float(point_b[0]) - float(point_a[0])
    ) * (float(point_c[1]) - float(point_b[1]))
    epsilon = 1e-8
    if abs(value) <= epsilon:
        return 0
    return 1 if value > 0 else -1


def _on_segment(seg_start: Point, point: Point, seg_end: Point) -> bool:
    """Return whether collinear `point` lies on closed segment `seg_start -> seg_end`."""
    return (
        min(float(seg_start[0]), float(seg_end[0])) - 1e-8 <= float(point[0]) <= max(float(seg_start[0]), float(seg_end[0])) + 1e-8
        and min(float(seg_start[1]), float(seg_end[1])) - 1e-8 <= float(point[1]) <= max(float(seg_start[1]), float(seg_end[1])) + 1e-8
    )


def _segments_intersect(seg_a_start: Point, seg_a_end: Point, seg_b_start: Point, seg_b_end: Point) -> bool:
    """Return whether two closed segments intersect (including touching)."""
    orientation_1 = _orientation(seg_a_start, seg_a_end, seg_b_start)
    orientation_2 = _orientation(seg_a_start, seg_a_end, seg_b_end)
    orientation_3 = _orientation(seg_b_start, seg_b_end, seg_a_start)
    orientation_4 = _orientation(seg_b_start, seg_b_end, seg_a_end)

    if orientation_1 != orientation_2 and orientation_3 != orientation_4:
        return True
    if orientation_1 == 0 and _on_segment(seg_a_start, seg_b_start, seg_a_end):
        return True
    if orientation_2 == 0 and _on_segment(seg_a_start, seg_b_end, seg_a_end):
        return True
    if orientation_3 == 0 and _on_segment(seg_b_start, seg_a_start, seg_b_end):
        return True
    if orientation_4 == 0 and _on_segment(seg_b_start, seg_a_end, seg_b_end):
        return True
    return False


def _segment_to_segment_distance(seg_a_start: Point, seg_a_end: Point, seg_b_start: Point, seg_b_end: Point) -> float:
    """Return minimum distance between two closed segments."""
    if _segments_intersect(seg_a_start, seg_a_end, seg_b_start, seg_b_end):
        return 0.0
    return min(
        _point_to_segment_distance(seg_a_start, seg_b_start, seg_b_end),
        _point_to_segment_distance(seg_a_end, seg_b_start, seg_b_end),
        _point_to_segment_distance(seg_b_start, seg_a_start, seg_a_end),
        _point_to_segment_distance(seg_b_end, seg_a_start, seg_a_end),
    )


def mapping_entities_have_min_clearance(
    entities: Mapping[str, Mapping[str, Any]],
    *,
    point_keys: Sequence[str],
    segment_keys: Sequence[Tuple[str, str]],
    min_clearance: float,
) -> bool:
    """Return whether entity geometries preserve pairwise minimum clearance.

    Args:
      entities: Entity-id to attribute mapping.
      point_keys: Attribute names whose values are point-like (`[x, y]`).
      segment_keys: Attribute-name pairs `(start_key, end_key)` defining line segments.
      min_clearance: Minimum required distance in pixels between any two entities.
    """
    threshold = float(min_clearance)
    if threshold < 0.0:
        raise ValueError("min_clearance must be >= 0")
    threshold_sq = float(threshold * threshold)

    parsed: Dict[str, Tuple[List[Point], List[Segment]]] = {}
    for entity_id, entity_attrs in entities.items():
        if not isinstance(entity_attrs, Mapping):
            raise ValueError(f"entity attrs for `{entity_id}` must be a mapping")
        points = [_as_point(entity_attrs[key]) for key in point_keys]
        segments = [(_as_point(entity_attrs[start_key]), _as_point(entity_attrs[end_key])) for start_key, end_key in segment_keys]
        parsed[str(entity_id)] = (points, segments)

    entity_ids = list(parsed.keys())
    for left_index, left_id in enumerate(entity_ids):
        left_points, left_segments = parsed[left_id]
        for right_id in entity_ids[left_index + 1 :]:
            right_points, right_segments = parsed[right_id]

            for left_point in left_points:
                for right_point in right_points:
                    if distance_sq(left_point, right_point) < threshold_sq:
                        return False

            for left_point in left_points:
                for right_segment in right_segments:
                    if _point_to_segment_distance(left_point, right_segment[0], right_segment[1]) < threshold:
                        return False

            for right_point in right_points:
                for left_segment in left_segments:
                    if _point_to_segment_distance(right_point, left_segment[0], left_segment[1]) < threshold:
                        return False

            for left_segment in left_segments:
                for right_segment in right_segments:
                    if _segment_to_segment_distance(left_segment[0], left_segment[1], right_segment[0], right_segment[1]) < threshold:
                        return False

    return True
