"""Construction primitives for circle-centerline-overlap diagrams."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import geometry_selected_probability_map

from .state import BOUNDARY_PAIRS, BOUNDARY_TARGET_ROLES, LABEL_MODES, CircleOverlapCase


CIRCLE_OVERLAP_CASES: tuple[CircleOverlapCase, ...] = (
    CircleOverlapCase(5, 15, 5, 2, 2),
    CircleOverlapCase(6, 14, 8, 3, 4),
    CircleOverlapCase(7, 12, 6, 2, 3),
    CircleOverlapCase(6, 13, 11, 3, 2),
    CircleOverlapCase(8, 16, 7, 4, 3),
    CircleOverlapCase(6, 12, 10, 2, 5),
    CircleOverlapCase(9, 15, 8, 3, 4),
    CircleOverlapCase(6, 12, 9, 3, 2),
    CircleOverlapCase(9, 14, 9, 4, 5),
    CircleOverlapCase(7, 16, 10, 4, 6),
)


def segment_length(case: CircleOverlapCase, pair: str, role: str) -> int:
    """Return one boundary-to-center or center-to-boundary segment length."""

    if str(pair) == "AB":
        left_radius, right_radius, distance = int(case.radius_a), int(case.radius_b), int(case.distance_ab)
    elif str(pair) == "BC":
        left_radius, right_radius, distance = int(case.radius_b), int(case.radius_c), int(case.distance_bc)
    else:
        raise ValueError(f"unsupported boundary pair: {pair}")
    if str(role) == "left_center_to_right_boundary":
        return int(distance) - int(right_radius)
    if str(role) == "left_boundary_to_right_center":
        return int(distance) - int(left_radius)
    raise ValueError(f"unsupported boundary target role: {role}")


def validate_overlap_case(case: CircleOverlapCase) -> None:
    """Reject invalid radii/overlap combinations before rendering."""

    radii = (int(case.radius_a), int(case.radius_b), int(case.radius_c))
    if min(radii) <= 0:
        raise ValueError("circle radii must be positive")
    if int(case.overlap_ab) <= 0 or int(case.overlap_bc) <= 0:
        raise ValueError("adjacent overlaps must be positive")
    d_ab = int(case.distance_ab)
    d_bc = int(case.distance_bc)
    d_ac = int(case.distance_ac)
    if not (abs(case.radius_a - case.radius_b) + 1 < d_ab < case.radius_a + case.radius_b):
        raise ValueError("AB must be a proper adjacent overlap without containment")
    if not (abs(case.radius_b - case.radius_c) + 1 < d_bc < case.radius_b + case.radius_c):
        raise ValueError("BC must be a proper adjacent overlap without containment")
    if d_ac <= int(case.radius_a) + int(case.radius_c) + 1:
        raise ValueError("non-adjacent circles A and C must not overlap")
    for pair in BOUNDARY_PAIRS:
        for role in BOUNDARY_TARGET_ROLES:
            if segment_length(case, pair, role) < 3:
                raise ValueError("boundary segment answers must be at least 3")


def select_overlap_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[CircleOverlapCase, dict[str, float]]:
    """Select or validate one deterministic overlap case."""

    explicit = params.get("overlap_case")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)) or len(explicit) != 5:
            raise ValueError("overlap_case must be [radius_a, radius_b, radius_c, overlap_ab, overlap_bc]")
        case = CircleOverlapCase(*(int(value) for value in explicit))
        validate_overlap_case(case)
        return case, {case.key: 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    case = CIRCLE_OVERLAP_CASES[int(index) % len(CIRCLE_OVERLAP_CASES)]
    probability = 1.0 / float(len(CIRCLE_OVERLAP_CASES))
    return case, {candidate.key: probability for candidate in CIRCLE_OVERLAP_CASES}


def select_label_mode(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select the radius/diameter readout style for circle labels."""

    explicit = params.get("label_mode")
    if explicit is not None:
        value = str(explicit)
        if value not in LABEL_MODES:
            raise ValueError(f"label_mode must be one of {LABEL_MODES}")
        return value, geometry_selected_probability_map(LABEL_MODES, selected=value)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = LABEL_MODES[int(index) % len(LABEL_MODES)]
    return str(value), geometry_selected_probability_map(LABEL_MODES)


def select_boundary_pair(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select the adjacent circle pair used by a boundary segment."""

    explicit = params.get("boundary_pair")
    if explicit is not None:
        value = str(explicit)
        if value not in BOUNDARY_PAIRS:
            raise ValueError(f"boundary_pair must be one of {BOUNDARY_PAIRS}")
        return value, geometry_selected_probability_map(BOUNDARY_PAIRS, selected=value)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = BOUNDARY_PAIRS[int(index) % len(BOUNDARY_PAIRS)]
    return str(value), geometry_selected_probability_map(BOUNDARY_PAIRS)


def select_boundary_target_role(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select which half-overlap centerline segment is unknown."""

    explicit = params.get("boundary_target_role")
    if explicit is not None:
        value = str(explicit)
        if value not in BOUNDARY_TARGET_ROLES:
            raise ValueError(f"boundary_target_role must be one of {BOUNDARY_TARGET_ROLES}")
        return value, geometry_selected_probability_map(BOUNDARY_TARGET_ROLES, selected=value)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = BOUNDARY_TARGET_ROLES[int(index) % len(BOUNDARY_TARGET_ROLES)]
    return str(value), geometry_selected_probability_map(BOUNDARY_TARGET_ROLES)


def boundary_names(pair: str, role: str) -> tuple[str, str, tuple[str, str], tuple[str, str]]:
    """Return target and known segment labels for one adjacent boundary pair."""

    if str(pair) == "AB":
        left_center, right_center = "A", "B"
        left_boundary, right_boundary = "X", "Y"
    elif str(pair) == "BC":
        left_center, right_center = "B", "C"
        left_boundary, right_boundary = "U", "V"
    else:
        raise ValueError(f"unsupported boundary pair: {pair}")
    if str(role) == "left_center_to_right_boundary":
        target_name = f"{left_center}{right_boundary}"
        known_name = f"{left_boundary}{right_center}"
        target_points = (left_center, right_boundary)
        known_points = (left_boundary, right_center)
    elif str(role) == "left_boundary_to_right_center":
        target_name = f"{left_boundary}{right_center}"
        known_name = f"{left_center}{right_boundary}"
        target_points = (left_boundary, right_center)
        known_points = (left_center, right_boundary)
    else:
        raise ValueError(f"unsupported boundary target role: {role}")
    return target_name, known_name, target_points, known_points


def center_distance_answer_support(selected: int) -> dict[str, float]:
    """Return support probabilities for possible full centerline distances."""

    support = tuple(sorted({int(case.distance_ac) for case in CIRCLE_OVERLAP_CASES}))
    return geometry_selected_probability_map(support, selected=int(selected))


def boundary_segment_answer_support(selected: int) -> dict[str, float]:
    """Return support probabilities for possible boundary segment lengths."""

    support = tuple(
        sorted(
            {
                segment_length(case, pair, role)
                for case in CIRCLE_OVERLAP_CASES
                for pair in BOUNDARY_PAIRS
                for role in BOUNDARY_TARGET_ROLES
            }
        )
    )
    return geometry_selected_probability_map(support, selected=int(selected))


__all__ = [
    "CIRCLE_OVERLAP_CASES",
    "boundary_names",
    "boundary_segment_answer_support",
    "center_distance_answer_support",
    "segment_length",
    "select_boundary_pair",
    "select_boundary_target_role",
    "select_label_mode",
    "select_overlap_case",
    "validate_overlap_case",
]
