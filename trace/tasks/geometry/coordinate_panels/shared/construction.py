"""Quadrilateral construction primitives for coordinate-panel scenes."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from trace.tasks.geometry.shared.quadrilateral_prototypes import classify_quadrilateral_kind

from .state import GraphPoint

ALL_EXACT_SHAPE_KINDS: Tuple[str, ...] = (
    "square",
    "rectangle_non_square",
    "rhombus_non_square",
    "parallelogram_only",
)

SQUARE_VECTORS: Tuple[GraphPoint, ...] = (
    (2, 0),
    (3, 0),
    (0, 2),
    (0, 3),
    (2, 1),
    (1, 2),
    (2, -1),
    (1, -2),
    (3, 1),
    (1, 3),
    (3, -1),
    (1, -3),
)
RECTANGLE_VECTOR_PAIRS: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((4, 0), (0, 2)),
    ((3, 0), (0, 2)),
    ((2, 0), (0, 4)),
    ((2, 1), (-2, 4)),
    ((1, 2), (-4, 2)),
    ((2, -1), (2, 4)),
    ((1, -2), (4, 2)),
)
RHOMBUS_VECTOR_PAIRS: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((2, 1), (1, 2)),
    ((3, 1), (1, 3)),
    ((3, 2), (2, 3)),
    ((2, -1), (1, -2)),
    ((3, -1), (1, -3)),
    ((3, -2), (2, -3)),
)
PARALLELOGRAM_VECTOR_PAIRS: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((4, 0), (1, 2)),
    ((3, 0), (1, 2)),
    ((2, 1), (3, -1)),
    ((3, 1), (1, 2)),
    ((4, 1), (-1, 2)),
    ((2, -1), (3, 1)),
)


def transform_vector(vector: GraphPoint, transform_index: int) -> GraphPoint:
    x_value, y_value = int(vector[0]), int(vector[1])
    variants = (
        (x_value, y_value),
        (-x_value, y_value),
        (x_value, -y_value),
        (-x_value, -y_value),
        (y_value, x_value),
        (-y_value, x_value),
        (y_value, -x_value),
        (-y_value, -x_value),
    )
    return tuple(int(value) for value in variants[int(transform_index) % len(variants)])  # type: ignore[return-value]


def vector_pair_for_kind(kind: str, rng) -> Tuple[GraphPoint, GraphPoint]:
    if str(kind) == "square":
        u = tuple(int(value) for value in rng.choice(SQUARE_VECTORS))
        v = (-int(u[1]), int(u[0]))
    elif str(kind) == "rectangle_non_square":
        u, v = rng.choice(RECTANGLE_VECTOR_PAIRS)
    elif str(kind) == "rhombus_non_square":
        u, v = rng.choice(RHOMBUS_VECTOR_PAIRS)
    elif str(kind) == "parallelogram_only":
        u, v = rng.choice(PARALLELOGRAM_VECTOR_PAIRS)
    else:
        raise ValueError(f"unsupported quadrilateral kind: {kind}")

    transform = int(rng.randrange(8))
    u_t = transform_vector(tuple(u), int(transform))
    v_t = transform_vector(tuple(v), int(transform))
    if bool(rng.randrange(2)):
        u_t, v_t = v_t, u_t
    return u_t, v_t


def translate_points_within(points: Sequence[GraphPoint], *, rng, max_abs: int) -> Tuple[GraphPoint, ...]:
    min_x = min(int(point[0]) for point in points)
    max_x = max(int(point[0]) for point in points)
    min_y = min(int(point[1]) for point in points)
    max_y = max(int(point[1]) for point in points)
    shift_x_min = int(-int(max_abs) - int(min_x))
    shift_x_max = int(int(max_abs) - int(max_x))
    shift_y_min = int(-int(max_abs) - int(min_y))
    shift_y_max = int(int(max_abs) - int(max_y))
    if shift_x_min > shift_x_max or shift_y_min > shift_y_max:
        raise ValueError("shape does not fit inside graph bounds")
    shift = (int(rng.randint(shift_x_min, shift_x_max)), int(rng.randint(shift_y_min, shift_y_max)))
    return tuple((int(x_value) + int(shift[0]), int(y_value) + int(shift[1])) for x_value, y_value in points)


def signed_area(vertices: Sequence[GraphPoint]) -> float:
    total = 0.0
    for index, point in enumerate(vertices):
        nxt = vertices[(int(index) + 1) % len(vertices)]
        total += (float(point[0]) * float(nxt[1])) - (float(nxt[0]) * float(point[1]))
    return 0.5 * float(total)


def order_points_around_centroid(points: Sequence[GraphPoint]) -> Tuple[GraphPoint, ...] | None:
    unique = tuple((int(x_value), int(y_value)) for x_value, y_value in points)
    if len(unique) != 4 or len(set(unique)) != 4:
        return None
    cx = sum(float(point[0]) for point in unique) / 4.0
    cy = sum(float(point[1]) for point in unique) / 4.0
    ordered = tuple(
        sorted(
            unique,
            key=lambda point: math.atan2(float(point[1]) - float(cy), float(point[0]) - float(cx)),
        )
    )
    if abs(float(signed_area(ordered))) <= 1e-9:
        return None
    return ordered


def is_convex(vertices: Sequence[GraphPoint]) -> bool:
    signs: List[int] = []
    for index in range(len(vertices)):
        a = vertices[index]
        b = vertices[(index + 1) % len(vertices)]
        c = vertices[(index + 2) % len(vertices)]
        cross = ((int(b[0]) - int(a[0])) * (int(c[1]) - int(b[1]))) - (
            (int(b[1]) - int(a[1])) * (int(c[0]) - int(b[0]))
        )
        if int(cross) == 0:
            return False
        signs.append(1 if int(cross) > 0 else -1)
    return len(set(signs)) == 1


def classify_point_set(points: Sequence[GraphPoint]) -> str:
    ordered = order_points_around_centroid(points)
    if ordered is None or not is_convex(ordered):
        return "other"
    return str(classify_quadrilateral_kind(tuple((float(x_value), float(y_value)) for x_value, y_value in ordered)))


def is_ambiguous_for_prompt(kind: str, target_kind: str) -> bool:
    if str(kind) == str(target_kind):
        return True
    if str(target_kind) == "parallelogram_only" and str(kind) in ALL_EXACT_SHAPE_KINDS:
        return True
    if str(target_kind) in {"rectangle_non_square", "rhombus_non_square"} and str(kind) == "square":
        return True
    return False


def sample_ordered_quadrilateral(kind: str, *, rng, max_abs: int) -> Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint]:
    for _ in range(400):
        u, v = vector_pair_for_kind(str(kind), rng)
        base_points: Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint] = (
            (0, 0),
            (int(u[0]), int(u[1])),
            (int(u[0]) + int(v[0]), int(u[1]) + int(v[1])),
            (int(v[0]), int(v[1])),
        )
        try:
            translated = translate_points_within(base_points, rng=rng, max_abs=int(max_abs))
        except ValueError:
            continue
        start = int(rng.randrange(4))
        ordered = tuple(translated[(start + index) % 4] for index in range(4))
        if bool(rng.randrange(2)):
            ordered = (ordered[0], ordered[3], ordered[2], ordered[1])
        if classify_point_set(ordered) == str(kind):
            return ordered  # type: ignore[return-value]
    raise RuntimeError(f"failed to sample {kind} quadrilateral")


def sample_other_quadrilateral(*, rng, max_abs: int) -> Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint]:
    for _ in range(1200):
        base_kind = str(rng.choice(ALL_EXACT_SHAPE_KINDS))
        points = list(sample_ordered_quadrilateral(base_kind, rng=rng, max_abs=int(max_abs)))
        index = int(rng.randrange(4))
        for delta in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            mutated = list(points)
            mutated[index] = (int(mutated[index][0]) + int(delta[0]), int(mutated[index][1]) + int(delta[1]))
            if any(max(abs(int(coord)) for coord in point) > int(max_abs) for point in mutated):
                continue
            if len(set(mutated)) != 4:
                continue
            if classify_point_set(mutated) == "other":
                return tuple(mutated)  # type: ignore[return-value]
    raise RuntimeError("failed to sample other quadrilateral point set")


def sample_panel_points(kind: str, *, rng, max_abs: int) -> Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint]:
    if str(kind) == "other":
        return sample_other_quadrilateral(rng=rng, max_abs=int(max_abs))
    return sample_ordered_quadrilateral(str(kind), rng=rng, max_abs=int(max_abs))


def shape_distractor_kinds(target_kind: str, *, rng, count: int) -> List[str]:
    if str(target_kind) == "square":
        base = ["rectangle_non_square", "rhombus_non_square", "parallelogram_only", "other", "other"]
    elif str(target_kind) == "rectangle_non_square":
        base = ["rhombus_non_square", "parallelogram_only", "other", "other", "other"]
    elif str(target_kind) == "rhombus_non_square":
        base = ["rectangle_non_square", "parallelogram_only", "other", "other", "other"]
    elif str(target_kind) == "parallelogram_only":
        base = ["other", "other", "other", "other", "other"]
    else:
        base = ["other"] * int(count)
    while len(base) < int(count):
        base.append("other")
    rng.shuffle(base)
    return list(base[: int(count)])


__all__ = [
    "ALL_EXACT_SHAPE_KINDS",
    "classify_point_set",
    "is_ambiguous_for_prompt",
    "sample_panel_points",
    "shape_distractor_kinds",
]
