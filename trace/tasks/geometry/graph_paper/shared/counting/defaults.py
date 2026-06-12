"""Shared fallback defaults for geometry/counting scene-package modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeometryCountingSharedDefaults:
    """Common fallback defaults reused across geometry/counting tasks."""

    canvas_size_min: int = 512
    canvas_size_max: int = 768
    graph_cells_min: int = 20
    graph_cells_max: int = 28
    line_width: int = 4
    label_offset_px: float = 14.0
    object_label_offset_px: float = 14.0
    label_font_size_min: int = 14
    label_font_size_max: int = 30
    label_stroke_width: int = 1
    object_count_min: int = 6
    object_count_max: int = 10


COUNTING_SHARED_DEFAULTS = GeometryCountingSharedDefaults()
