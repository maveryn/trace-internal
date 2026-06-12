"""Shared fallback defaults for geometry/comparison scene-package modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeometryComparisonSharedDefaults:
    """Common fallback defaults reused across geometry/comparison tasks."""

    canvas_size_min: int = 512
    canvas_size_max: int = 768
    graph_cells_min: int = 18
    graph_cells_max: int = 24
    line_width: int = 4
    label_offset_px: float = 14.0
    object_label_offset_px: float = 14.0
    label_font_size_min: int = 14
    label_font_size_max: int = 30
    label_stroke_width: int = 1
    object_count_min: int = 4
    object_count_max: int = 8
    min_normalized_gap: float = 0.2


COMPARISON_SHARED_DEFAULTS = GeometryComparisonSharedDefaults()
