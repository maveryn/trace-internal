"""Shared fallback defaults for geometry/measurement task-group modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class GeometryMeasurementSharedDefaults:
    """Common fallback defaults reused across geometry/measurement tasks."""

    canvas_size_min: int = 512
    canvas_size_max: int = 768
    graph_cells_min: int = 6
    graph_cells_max: int = 20
    line_width: int = 4
    label_offset_px: float = 14.0
    label_font_size_min: int = 14
    label_font_size_max: int = 32
    label_stroke_width: int = 1
    polygon_allowed_sides: Tuple[int, ...] = (3, 4, 5)
    circle_radius_min: int = 2
    circle_radius_max: int = 10
    ellipse_axis_min: int = 2
    ellipse_axis_max: int = 10
    ellipse_allow_circle: bool = False


MEASUREMENT_SHARED_DEFAULTS = GeometryMeasurementSharedDefaults()
