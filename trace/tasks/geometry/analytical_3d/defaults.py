"""Shared fallback defaults for geometry/analytical_3d task-group modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeometryAnalytical3DSharedDefaults:
    """Common fallback defaults reused across geometry/analytical_3d tasks."""

    canvas_size_min: int = 512
    canvas_size_max: int = 768
    graph_cells_min: int = 6
    graph_cells_max: int = 12
    line_width: int = 4
    helper_line_width: int = 2
    label_offset_px: float = 14.0
    label_font_size_min: int = 14
    label_font_size_max: int = 30
    label_stroke_width: int = 1
    answer_min: int = 8
    answer_max: int = 96


ANALYTICAL_3D_SHARED_DEFAULTS = GeometryAnalytical3DSharedDefaults()
