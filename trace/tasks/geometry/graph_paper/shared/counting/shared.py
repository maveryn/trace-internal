"""Shared helpers for geometry/counting task modules."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....shared.counting_sampling import (
    resolve_counting_cardinality_pair,
    resolve_counting_object_count,
    resolve_counting_target_count,
)
from .....shared.geometry_primitives import Point
from .....shared.labeling import LABEL_POOL_A_L, assign_shuffled_labels

COUNTING_LABEL_POOL: Tuple[str, ...] = LABEL_POOL_A_L


def assign_counting_labels(rng, *, object_count: int, label_pool: Sequence[str] = COUNTING_LABEL_POOL) -> Tuple[str, ...]:
    """Assign one shuffled subset of object labels for a counting scene."""

    return assign_shuffled_labels(rng, object_count=int(object_count), label_pool=label_pool)


def bulky_counting_slot_centers_graph_units(
    *,
    object_count: int,
    graph_cells: int,
    rng,
) -> List[Tuple[int, int]]:
    """Return a roomy hidden-grid slot bank for bulky non-grid counting objects.

    Mixed-shape and polygon-counting scenes need more breathing room than
    line-like counting scenes, so they share a wider three-row slot layout.
    """

    half_span = max(18, int(graph_cells // 2))
    outer_x = max(8, min(int(round(float(half_span) * 0.78)), int(half_span - 4)))
    mid_x = max(4, min(int(round(float(half_span) * 0.28)), max(4, int(outer_x - 5))))
    row_y = max(7, min(int(round(float(half_span) * 0.48)), int(half_span - 4)))
    base_slots = [
        (-int(outer_x), int(row_y)),
        (-int(mid_x), int(row_y)),
        (int(mid_x), int(row_y)),
        (int(outer_x), int(row_y)),
        (-int(outer_x), 0),
        (-int(mid_x), 0),
        (int(mid_x), 0),
        (int(outer_x), 0),
        (-int(mid_x), -int(row_y)),
        (int(mid_x), -int(row_y)),
        (-int(outer_x), -int(row_y)),
        (int(outer_x), -int(row_y)),
    ]
    rng.shuffle(base_slots)
    return list(base_slots[: int(object_count)])


def bounds_from_points(points: Sequence[Point]) -> Tuple[float, float, float, float]:
    """Return one axis-aligned bounds tuple for a point sequence."""

    if not points:
        raise ValueError("cannot compute bounds for an empty point sequence")
    return (
        min(float(point[0]) for point in points),
        min(float(point[1]) for point in points),
        max(float(point[0]) for point in points),
        max(float(point[1]) for point in points),
    )


def bounds_have_clearance(
    bounds: Sequence[Tuple[float, float, float, float]],
    *,
    min_clearance_px: float,
) -> bool:
    """Return true when all object bounding boxes are separated by a margin."""

    margin = float(min_clearance_px)
    boxes = [tuple(float(value) for value in box) for box in bounds]
    for index, box_a in enumerate(boxes):
        ax1, ay1, ax2, ay2 = box_a
        for box_b in boxes[index + 1 :]:
            bx1, by1, bx2, by2 = box_b
            separated = (
                float(ax2) + margin <= float(bx1)
                or float(bx2) + margin <= float(ax1)
                or float(ay2) + margin <= float(by1)
                or float(by2) + margin <= float(ay1)
            )
            if not separated:
                return False
    return True


__all__ = [
    "COUNTING_LABEL_POOL",
    "assign_counting_labels",
    "bounds_from_points",
    "bounds_have_clearance",
    "bulky_counting_slot_centers_graph_units",
    "resolve_counting_cardinality_pair",
    "resolve_counting_object_count",
    "resolve_counting_target_count",
]
