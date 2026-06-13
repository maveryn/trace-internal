"""Construction primitives for circle-polygon-composite diagrams."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence

from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import geometry_selected_probability_map
from trace.tasks.geometry.shared.vector2d import mul as _mul

from .state import CONSTRUCTION_KINDS, Point, SIDE_KEYS


TANGENT_CASES: tuple[tuple[int, int, int, int], ...] = (
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
ANGLE_SUPPORT: tuple[int, ...] = (25, 30, 35, 40, 45, 50, 55, 60, 65)
SIDE_SIGN_SUPPORT: tuple[int, int] = (-1, 1)


def case_key(case: Sequence[int]) -> str:
    """Return a stable support key for one tangent-length case."""

    return "-".join(str(int(value)) for value in case)


def select_missing_side(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select which quadrilateral side length is hidden."""

    explicit = params.get("missing_side")
    if explicit is not None:
        missing_side = str(explicit)
        if missing_side not in SIDE_KEYS:
            raise ValueError(f"unsupported missing_side: {missing_side}")
        return missing_side, geometry_selected_probability_map(SIDE_KEYS, selected=missing_side)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    missing_side = str(SIDE_KEYS[int(index) % len(SIDE_KEYS)])
    return missing_side, geometry_selected_probability_map(SIDE_KEYS)


def select_tangent_case(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[tuple[int, int, int, int], dict[str, float]]:
    """Select or validate one set of four vertex tangent lengths."""

    explicit = params.get("tangent_lengths")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)) or len(explicit) != 4:
            raise ValueError("tangent_lengths must be a four-item sequence")
        case = tuple(int(value) for value in explicit)
        if any(value <= 0 for value in case):
            raise ValueError("tangent_lengths values must be positive")
        return case, {case_key(case): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    case = TANGENT_CASES[int(index) % len(TANGENT_CASES)]
    probability = 1.0 / float(len(TANGENT_CASES))
    return case, {case_key(candidate): probability for candidate in TANGENT_CASES}


def side_lengths_from_vertex_tangents(case: Sequence[int]) -> dict[str, int]:
    """Convert vertex tangent lengths into side lengths for a tangential quadrilateral."""

    t_a, t_b, t_c, t_d = [int(value) for value in case]
    return {
        "AB": int(t_a + t_b),
        "BC": int(t_b + t_c),
        "CD": int(t_c + t_d),
        "DA": int(t_d + t_a),
    }


def vertex_tangents_from_case(case: Sequence[int]) -> dict[str, int]:
    """Return per-vertex tangent lengths keyed by quadrilateral vertex."""

    t_a, t_b, t_c, t_d = [int(value) for value in case]
    return {"A": int(t_a), "B": int(t_b), "C": int(t_c), "D": int(t_d)}


def select_angle_degrees(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[int, dict[str, float]]:
    """Select or validate the target angle support value."""

    explicit = params.get("target_angle")
    if explicit is not None:
        answer = int(explicit)
        if answer not in ANGLE_SUPPORT:
            raise ValueError(f"target_angle must be one of {ANGLE_SUPPORT}")
        return answer, geometry_selected_probability_map(ANGLE_SUPPORT, selected=answer)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    answer = int(ANGLE_SUPPORT[int(index) % len(ANGLE_SUPPORT)])
    return answer, geometry_selected_probability_map(ANGLE_SUPPORT)


def select_side_sign(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[int, dict[str, float]]:
    """Select which side of the construction receives the tangent line."""

    explicit = params.get("side_sign")
    if explicit is not None:
        side_sign = int(explicit)
        if side_sign not in SIDE_SIGN_SUPPORT:
            raise ValueError("side_sign must be -1 or 1")
        return side_sign, geometry_selected_probability_map(SIDE_SIGN_SUPPORT, selected=side_sign)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    side_sign = -1 if int(index) % 2 == 0 else 1
    return side_sign, geometry_selected_probability_map(SIDE_SIGN_SUPPORT)


def validate_construction_kind(construction_kind: str) -> str:
    """Return a validated construction kind for angle-transfer diagrams."""

    kind = str(construction_kind)
    if kind not in CONSTRUCTION_KINDS:
        raise ValueError(f"unsupported construction_kind: {kind}")
    return kind


def _solve_inradius(tangents: Sequence[int]) -> float:
    """Solve the inradius whose tangent-angle gaps close the quadrilateral."""

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


def tangential_local_geometry(
    vertex_tangents: Mapping[str, int],
) -> tuple[Dict[str, Point], Dict[str, Point], float]:
    """Construct local vertices, tangency points, and inradius before rendering."""

    t_a = int(vertex_tangents["A"])
    t_b = int(vertex_tangents["B"])
    t_c = int(vertex_tangents["C"])
    t_d = int(vertex_tangents["D"])
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


__all__ = [
    "ANGLE_SUPPORT",
    "SIDE_SIGN_SUPPORT",
    "TANGENT_CASES",
    "case_key",
    "select_angle_degrees",
    "select_missing_side",
    "select_side_sign",
    "select_tangent_case",
    "side_lengths_from_vertex_tangents",
    "tangential_local_geometry",
    "validate_construction_kind",
    "vertex_tangents_from_case",
]
