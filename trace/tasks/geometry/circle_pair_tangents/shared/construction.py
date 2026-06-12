"""Construction primitives for external common tangent diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import geometry_selected_probability_map

from .state import LARGER_CIRCLE_SIDES, TANGENT_SIDES, TangentCase


TANGENT_CASES: tuple[TangentCase, ...] = (
    TangentCase(3, 8, 13, 12),
    TangentCase(2, 11, 15, 12),
    TangentCase(4, 12, 17, 15),
    TangentCase(3, 15, 20, 16),
    TangentCase(5, 12, 25, 24),
    TangentCase(6, 16, 26, 24),
    TangentCase(4, 24, 29, 21),
    TangentCase(6, 22, 34, 30),
)


@dataclass(frozen=True)
class TangentLayout:
    """A sampled tangent case with concrete left/right and above/below placement."""

    case: TangentCase
    radius_o1: int
    radius_o2: int
    larger_circle_side: str
    tangent_side: str
    tangent_case_probabilities: dict[str, float]
    larger_side_probabilities: dict[str, float]
    tangent_side_probabilities: dict[str, float]


def validate_tangent_case(case: TangentCase) -> None:
    """Reject tangent cases that do not satisfy the external tangent formula."""

    if int(case.small_radius) <= 0 or int(case.large_radius) <= 0:
        raise ValueError("circle radii must be positive")
    if int(case.large_radius) <= int(case.small_radius):
        raise ValueError("large_radius must be greater than small_radius")
    if int(case.center_distance) <= int(case.large_radius) + int(case.small_radius) - 1:
        raise ValueError("circles must be separated enough for a clear external tangent")
    expected = int(case.center_distance) ** 2 - int(case.radius_difference) ** 2
    if expected <= 0 or int(case.tangent_length) ** 2 != expected:
        raise ValueError("tangent_case must satisfy t^2 = d^2 - (r_large-r_small)^2")


def select_tangent_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[TangentCase, dict[str, float]]:
    """Select or validate one deterministic integer tangent case."""

    explicit = params.get("tangent_case")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)) or len(explicit) != 4:
            raise ValueError("tangent_case must be [small_radius, large_radius, center_distance, tangent_length]")
        case = TangentCase(*(int(value) for value in explicit))
        validate_tangent_case(case)
        return case, {case.key: 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    case = TANGENT_CASES[int(index) % len(TANGENT_CASES)]
    probability = 1.0 / float(len(TANGENT_CASES))
    return case, {candidate.key: probability for candidate in TANGENT_CASES}


def select_larger_circle_side(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select which circle center receives the larger radius."""

    explicit = params.get("larger_circle_side")
    if explicit is not None:
        value = str(explicit)
        if value not in LARGER_CIRCLE_SIDES:
            raise ValueError(f"larger_circle_side must be one of {LARGER_CIRCLE_SIDES}")
        return value, geometry_selected_probability_map(LARGER_CIRCLE_SIDES, selected=value)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = LARGER_CIRCLE_SIDES[int(index) % len(LARGER_CIRCLE_SIDES)]
    return str(value), geometry_selected_probability_map(LARGER_CIRCLE_SIDES)


def select_tangent_side(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select whether the common tangent is drawn above or below the centers."""

    explicit = params.get("tangent_side")
    if explicit is not None:
        value = str(explicit)
        if value not in TANGENT_SIDES:
            raise ValueError(f"tangent_side must be one of {TANGENT_SIDES}")
        return value, geometry_selected_probability_map(TANGENT_SIDES, selected=value)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = TANGENT_SIDES[int(index) % len(TANGENT_SIDES)]
    return str(value), geometry_selected_probability_map(TANGENT_SIDES)


def radii_for_center_order(case: TangentCase, larger_circle_side: str) -> tuple[int, int]:
    """Return ``(radius_o1, radius_o2)`` for the selected larger-circle side."""

    if str(larger_circle_side) == "left":
        return int(case.large_radius), int(case.small_radius)
    if str(larger_circle_side) == "right":
        return int(case.small_radius), int(case.large_radius)
    raise ValueError(f"larger_circle_side must be one of {LARGER_CIRCLE_SIDES}")


def tangent_answer_support(*, selected: int, metric: str) -> dict[str, float]:
    """Return support probabilities for one tangent answer metric."""

    if str(metric) == "center_distance":
        support = tuple(sorted({int(case.center_distance) for case in TANGENT_CASES}))
    elif str(metric) == "tangent_length":
        support = tuple(sorted({int(case.tangent_length) for case in TANGENT_CASES}))
    else:
        raise ValueError("metric must be center_distance or tangent_length")
    return geometry_selected_probability_map(support, selected=int(selected))


def select_tangent_layout(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    sampling_namespace: str,
) -> TangentLayout:
    """Select the case and visual side choices for one tangent diagram."""

    case, case_probabilities = select_tangent_case(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{sampling_namespace}.tangent_case",
    )
    larger_side, larger_side_probabilities = select_larger_circle_side(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{sampling_namespace}.larger_circle_side",
    )
    tangent_side, tangent_side_probabilities = select_tangent_side(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{sampling_namespace}.tangent_side",
    )
    radius_o1, radius_o2 = radii_for_center_order(case, larger_side)
    return TangentLayout(
        case=case,
        radius_o1=int(radius_o1),
        radius_o2=int(radius_o2),
        larger_circle_side=str(larger_side),
        tangent_side=str(tangent_side),
        tangent_case_probabilities=dict(case_probabilities),
        larger_side_probabilities=dict(larger_side_probabilities),
        tangent_side_probabilities=dict(tangent_side_probabilities),
    )


__all__ = [
    "TANGENT_CASES",
    "TangentLayout",
    "radii_for_center_order",
    "select_larger_circle_side",
    "select_tangent_case",
    "select_tangent_side",
    "select_tangent_layout",
    "tangent_answer_support",
    "validate_tangent_case",
]
