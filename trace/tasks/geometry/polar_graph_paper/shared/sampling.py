"""Sampling helpers for polar graph paper readout tasks."""

from __future__ import annotations

from collections.abc import Mapping
import random
from typing import Any

from .state import PolarReadoutCase, ReadoutComponent


def _int_param(
    params: Mapping[str, Any],
    name: str,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    value = int(params.get(name, default))
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}, got {value}")
    return value


def _angle_support(step_degrees: int) -> tuple[int, ...]:
    if step_degrees <= 0 or 360 % step_degrees != 0:
        raise ValueError("sample_angle_step_degrees must divide 360")
    return tuple(range(0, 360, step_degrees))


def select_polar_readout_case(
    *,
    rng: random.Random,
    component: ReadoutComponent,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> PolarReadoutCase:
    """Sample one grid-aligned point and bind the requested readout value."""

    radius_min = _int_param(generation_defaults, "radius_min", default=1, minimum=1)
    radius_max = _int_param(
        generation_defaults,
        "radius_max",
        default=8,
        minimum=radius_min,
    )
    angle_step = _int_param(
        generation_defaults,
        "sample_angle_step_degrees",
        default=30,
        minimum=1,
        maximum=180,
    )
    angle_support = _angle_support(angle_step)
    radius_support = tuple(range(radius_min, radius_max + 1))

    if "radius" in params:
        radius = _int_param(params, "radius", default=radius_min, minimum=radius_min, maximum=radius_max)
    else:
        radius = rng.choice(radius_support)

    if "theta_degrees" in params:
        theta_degrees = _int_param(params, "theta_degrees", default=0, minimum=0, maximum=359)
        if theta_degrees not in angle_support:
            raise ValueError("theta_degrees must lie on the configured angular support")
    else:
        theta_degrees = rng.choice(angle_support)

    if component == "radius":
        correct_value = radius
    elif component == "angle_degrees":
        correct_value = theta_degrees
    else:  # pragma: no cover - typing guard
        raise ValueError(f"unknown readout component: {component}")

    return PolarReadoutCase(
        component=component,
        radius=radius,
        theta_degrees=theta_degrees,
        correct_value=correct_value,
    )
