"""Support-value construction helpers for composite-shape public objectives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .measurements import (
    QUARTER_CUT_DIMENSION_CANDIDATES,
    RADIUS_SUPPORT,
    SECTOR_DIMENSION_CANDIDATES,
    SEMICIRCLE_DIMENSION_CANDIDATES,
    dimension_values,
    round1,
    sector_values,
    semicircle_arc_length,
    semicircle_area,
    semicircle_side_remainder_straight_boundary,
)
from .sampling import answer_key, select_answer_balanced_case


@dataclass(frozen=True)
class ResolvedSemicirclePerimeterCase:
    """Selected dimensions and trace fields for one semicircle perimeter problem."""

    width_units: int
    height_units: int
    radius_units: int
    answer: float
    dimensions: dict[str, Any]
    answer_probabilities: dict[str, float]
    execution_fields: dict[str, Any]


def resolve_semicircle_dimensions(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[int, int, int]:
    """Resolve rectangle width, height, and semicircle radius support values."""

    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    width_units, height_units, radius_units = dimension_values(int(index))
    width_units = int(params.get("width_units", width_units))
    height_units = int(params.get("height_units", height_units))
    radius_units = int(params.get("radius_units", max(3, int(height_units // 2))))
    return int(width_units), int(height_units), int(radius_units)


def resolve_answer_balanced_semicircle_dimensions(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    answer_cases: Mapping[str, tuple[tuple[int, int, int], ...]],
    answer_fn: Callable[[tuple[int, int, int]], Any],
) -> tuple[int, int, int, dict[str, float]]:
    """Resolve semicircle dimensions by balancing over final answers."""

    (
        width_units,
        height_units,
        radius_units,
    ), support_probabilities = select_answer_balanced_case(
        answer_cases,
        instance_seed=int(instance_seed),
        params=params,
        namespace=str(namespace),
    )
    explicit = any(
        key in params for key in ("width_units", "height_units", "radius_units")
    )
    width_units = int(params.get("width_units", width_units))
    height_units = int(params.get("height_units", height_units))
    if "radius_units" in params:
        radius_units = int(params["radius_units"])
    elif "height_units" in params:
        radius_units = max(3, int(height_units // 2))
    if explicit:
        selected_answer = answer_key(
            answer_fn((int(width_units), int(height_units), int(radius_units)))
        )
        return int(width_units), int(height_units), int(radius_units), {selected_answer: 1.0}
    return int(width_units), int(height_units), int(radius_units), support_probabilities


def resolve_semicircle_side_remainder_perimeter_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    answer_cases: Mapping[str, tuple[tuple[int, int, int], ...]],
    answer_fn: Callable[[tuple[int, int, int]], Any],
) -> ResolvedSemicirclePerimeterCase:
    """Resolve dimensions and formula fields for semicircle side-remainder perimeters."""

    width_units, height_units, radius_units, answer_probabilities = (
        resolve_answer_balanced_semicircle_dimensions(
            instance_seed=int(instance_seed),
            params=params,
            namespace=str(namespace),
            answer_cases=answer_cases,
            answer_fn=answer_fn,
        )
    )
    arc_length = semicircle_arc_length(radius_units)
    straight_boundary_length = semicircle_side_remainder_straight_boundary(
        width_units,
        height_units,
        radius_units,
    )
    answer = round1(float(answer_fn((width_units, height_units, radius_units))))
    dimensions = {
        "width_units": int(width_units),
        "height_units": int(height_units),
        "radius_units": int(radius_units),
        "semicircle_area": round1(semicircle_area(radius_units)),
        "arc_length": round1(arc_length),
        "straight_boundary_length": round1(straight_boundary_length),
        "answer_value": answer,
    }
    return ResolvedSemicirclePerimeterCase(
        width_units=int(width_units),
        height_units=int(height_units),
        radius_units=int(radius_units),
        answer=float(answer),
        dimensions=dimensions,
        answer_probabilities=dict(answer_probabilities),
        execution_fields={
            "perimeter_formula": "2*width + 2*height - 2*radius + pi*radius",
            "answer_rounding": "nearest_tenth",
        },
    )


def resolve_quarter_cut_dimensions(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[int, int, int]:
    """Resolve rectangle and radius values for a quarter-sector cutout."""

    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    width_units, height_units, _radius_hint = dimension_values(int(index))
    radius_units = RADIUS_SUPPORT[int(index) % len(RADIUS_SUPPORT)]
    radius_units = int(params.get("radius_units", radius_units))
    width_units = max(int(radius_units) + 4, int(params.get("width_units", width_units)))
    height_units = max(int(radius_units) + 3, int(params.get("height_units", height_units)))
    return int(width_units), int(height_units), int(radius_units)


def resolve_answer_balanced_quarter_cut_dimensions(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    answer_cases: Mapping[str, tuple[tuple[int, int, int], ...]],
    answer_fn: Callable[[tuple[int, int, int]], Any],
) -> tuple[int, int, int, dict[str, float]]:
    """Resolve quarter-sector cut dimensions by final answer support."""

    (
        width_units,
        height_units,
        radius_units,
    ), support_probabilities = select_answer_balanced_case(
        answer_cases,
        instance_seed=int(instance_seed),
        params=params,
        namespace=str(namespace),
    )
    explicit = any(
        key in params for key in ("width_units", "height_units", "radius_units")
    )
    radius_units = int(params.get("radius_units", radius_units))
    width_units = max(int(radius_units) + 4, int(params.get("width_units", width_units)))
    height_units = max(
        int(radius_units) + 3,
        int(params.get("height_units", height_units)),
    )
    if explicit:
        selected_answer = answer_key(
            answer_fn((int(width_units), int(height_units), int(radius_units)))
        )
        return int(width_units), int(height_units), int(radius_units), {selected_answer: 1.0}
    return int(width_units), int(height_units), int(radius_units), support_probabilities


def resolve_sector_dimensions(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[int, int]:
    """Resolve central angle and radius values for a circular sector."""

    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    theta_degrees, radius_units = sector_values(int(index))
    theta_degrees = int(params.get("theta_degrees", theta_degrees))
    radius_units = int(params.get("radius_units", radius_units))
    return int(theta_degrees), int(radius_units)


def resolve_answer_balanced_sector_dimensions(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    answer_cases: Mapping[str, tuple[tuple[int, int], ...]],
    answer_fn: Callable[[tuple[int, int]], Any],
) -> tuple[int, int, dict[str, float]]:
    """Resolve sector dimensions by balancing over final rounded angle answers."""

    (
        theta_degrees,
        radius_units,
    ), support_probabilities = select_answer_balanced_case(
        answer_cases,
        instance_seed=int(instance_seed),
        params=params,
        namespace=str(namespace),
    )
    explicit = any(key in params for key in ("theta_degrees", "radius_units"))
    theta_degrees = int(params.get("theta_degrees", theta_degrees))
    radius_units = int(params.get("radius_units", radius_units))
    if explicit:
        selected_answer = answer_key(answer_fn((int(theta_degrees), int(radius_units))))
        return int(theta_degrees), int(radius_units), {selected_answer: 1.0}
    return int(theta_degrees), int(radius_units), support_probabilities


__all__ = [
    "QUARTER_CUT_DIMENSION_CANDIDATES",
    "ResolvedSemicirclePerimeterCase",
    "SECTOR_DIMENSION_CANDIDATES",
    "SEMICIRCLE_DIMENSION_CANDIDATES",
    "resolve_answer_balanced_quarter_cut_dimensions",
    "resolve_answer_balanced_sector_dimensions",
    "resolve_answer_balanced_semicircle_dimensions",
    "resolve_quarter_cut_dimensions",
    "resolve_sector_dimensions",
    "resolve_semicircle_side_remainder_perimeter_case",
    "resolve_semicircle_dimensions",
]
