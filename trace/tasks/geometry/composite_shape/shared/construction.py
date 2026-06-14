"""Support-value construction helpers for composite-shape public objectives."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .measurements import RADIUS_SUPPORT, dimension_values, sector_values


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
