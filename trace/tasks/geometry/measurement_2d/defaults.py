"""Shared fallback defaults for geometry/measurement_2d task-group modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class GeometryMeasurementSharedDefaults:
    """Common fallback defaults reused across geometry/measurement_2d tasks."""

    canvas_size_min: int = 256
    canvas_size_max: int = 512
    graph_cells_min: int = 6
    graph_cells_max: int = 12
    line_width: int = 4
    label_offset_px: float = 14.0
    label_font_size_min: int = 14
    label_font_size_max: int = 32
    label_stroke_width: int = 1
    polygon_allowed_sides: Tuple[int, ...] = (3, 4, 5)


MEASUREMENT_SHARED_DEFAULTS = GeometryMeasurementSharedDefaults()
