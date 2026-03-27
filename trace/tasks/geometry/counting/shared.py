"""Shared helpers for geometry/counting task modules."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ...shared.counting_sampling import (
    counting_complexity_score,
    resolve_counting_cardinality_pair,
    resolve_counting_object_count,
    resolve_counting_target_count,
)
from ...shared.labeling import LABEL_POOL_A_L, assign_shuffled_labels

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

    half_span = max(14, int(graph_cells // 2))
    outer_x = max(7, min(int(round(float(half_span) * 0.72)), int(half_span - 3)))
    mid_x = max(3, min(int(round(float(half_span) * 0.30)), max(3, int(outer_x - 3))))
    row_y = max(5, min(int(round(float(half_span) * 0.42)), int(half_span - 3)))
    base_slots = [
        (-int(outer_x), int(row_y)),
        (-int(mid_x), int(row_y)),
        (int(mid_x), int(row_y)),
        (int(outer_x), int(row_y)),
        (-int(outer_x), 0),
        (0, 0),
        (int(outer_x), 0),
        (-int(mid_x), -int(row_y)),
        (int(mid_x), -int(row_y)),
    ]
    rng.shuffle(base_slots)
    return list(base_slots[: int(object_count)])


__all__ = [
    "COUNTING_LABEL_POOL",
    "assign_counting_labels",
    "bulky_counting_slot_centers_graph_units",
    "counting_complexity_score",
    "resolve_counting_cardinality_pair",
    "resolve_counting_object_count",
    "resolve_counting_target_count",
]
