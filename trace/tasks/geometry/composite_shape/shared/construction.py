"""Support-value construction helpers for composite-shape public objectives."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .measurements import (
    QUARTER_CUT_DIMENSION_CANDIDATES,
    RADIUS_SUPPORT,
    SECTOR_DIMENSION_CANDIDATES,
    SEMICIRCLE_DIMENSION_CANDIDATES,
    dimension_values,
    sector_values,
)
from .sampling import answer_key, select_answer_balanced_case


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
    "SECTOR_DIMENSION_CANDIDATES",
    "SEMICIRCLE_DIMENSION_CANDIDATES",
    "resolve_answer_balanced_quarter_cut_dimensions",
    "resolve_answer_balanced_sector_dimensions",
    "resolve_answer_balanced_semicircle_dimensions",
    "resolve_quarter_cut_dimensions",
    "resolve_sector_dimensions",
    "resolve_semicircle_dimensions",
]
