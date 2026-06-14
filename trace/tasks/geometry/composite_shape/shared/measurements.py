"""Formula and support helpers for composite-shape measurements."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.tasks.geometry.shared.measurement_rendering import fmt_measure, round1
from trace.tasks.shared.fixed_query import geometry_probability_map, geometry_selected_probability_map

WIDTH_SUPPORT: Tuple[int, ...] = tuple(range(8, 19))
HEIGHT_SUPPORT: Tuple[int, ...] = (6, 8, 10, 12, 14, 16)
RADIUS_SUPPORT: Tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10, 11, 12)
THETA_SUPPORT: Tuple[int, ...] = (45, 60, 75, 90, 105, 120, 135, 150)


def dimension_values(index: int) -> tuple[int, int, int]:
    """Return width, height, and radius support values for curved composites."""

    width_units = WIDTH_SUPPORT[int(index) % len(WIDTH_SUPPORT)]
    height_units = HEIGHT_SUPPORT[(int(index) // len(WIDTH_SUPPORT)) % len(HEIGHT_SUPPORT)]
    radius_units = max(3, int(height_units // 2))
    return int(width_units), int(height_units), int(radius_units)


def sector_values(index: int) -> tuple[int, int]:
    """Return central-angle and radius support values for sector tasks."""

    theta = THETA_SUPPORT[int(index) % len(THETA_SUPPORT)]
    radius = RADIUS_SUPPORT[(int(index) // len(THETA_SUPPORT)) % len(RADIUS_SUPPORT)]
    return int(theta), int(radius)


def one_hot_support(values: Sequence[Any], selected: Any) -> Dict[str, float]:
    """Return a one-hot support probability map with JSON-stable keys."""

    return geometry_selected_probability_map(
        values,
        selected,
        is_selected=lambda value, target: float(value) == float(target),
    )


def uniform_support(values: Sequence[Any]) -> Dict[str, float]:
    """Return a uniform support probability map for trace metadata."""

    return geometry_probability_map(values, sort_unique=True)


def semicircle_area(radius_units: int) -> float:
    """Return the area of a semicircle with the supplied radius."""

    return 0.5 * math.pi * float(radius_units) ** 2


def semicircle_arc_length(radius_units: int) -> float:
    """Return the arc length of a semicircle with the supplied radius."""

    return math.pi * float(radius_units)


def quarter_sector_values(radius_units: int) -> tuple[float, float]:
    """Return the area and arc length of a quarter-circle cutout."""

    sector_area = 0.25 * math.pi * float(radius_units) ** 2
    arc_length = 0.5 * math.pi * float(radius_units)
    return float(sector_area), float(arc_length)


def sector_arc_length(theta_degrees: int, radius_units: int) -> float:
    """Return a sector arc length for a central angle in degrees."""

    return (float(theta_degrees) / 360.0) * 2.0 * math.pi * float(radius_units)


def sector_area(theta_degrees: int, radius_units: int) -> float:
    """Return a sector area for a central angle in degrees."""

    return (float(theta_degrees) / 360.0) * math.pi * float(radius_units) ** 2


def format_given(value: float) -> str:
    """Format one visible decimal given with one digit."""

    return f"{float(value):.1f}"


def numeric_prompt_slots(values: Mapping[str, Any]) -> Dict[str, str]:
    """Return prompt slots for optional numeric values used by templates."""

    return {
        "total_area": format_given(float(values.get("total_area", 0.0))),
        "arc_length": format_given(float(values.get("arc_length", 0.0))),
        "sector_area": format_given(float(values.get("sector_area", 0.0))),
    }


__all__ = [
    "HEIGHT_SUPPORT",
    "RADIUS_SUPPORT",
    "THETA_SUPPORT",
    "WIDTH_SUPPORT",
    "dimension_values",
    "fmt_measure",
    "format_given",
    "numeric_prompt_slots",
    "one_hot_support",
    "quarter_sector_values",
    "round1",
    "sector_arc_length",
    "sector_area",
    "sector_values",
    "semicircle_arc_length",
    "semicircle_area",
    "uniform_support",
]
