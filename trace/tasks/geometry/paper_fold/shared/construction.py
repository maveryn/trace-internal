"""Identity-free construction math for paper-fold diagrams."""

from __future__ import annotations

import math
from typing import Tuple

from trace.tasks.geometry.shared.measurement_rendering import round1

from .state import FoldGeometry

FOLD_CASES: Tuple[Tuple[int, int], ...] = (
    (10, 6),
    (12, 8),
    (14, 6),
    (15, 9),
    (16, 10),
    (18, 12),
    (20, 14),
    (12, 5),
    (14, 10),
    (16, 7),
    (18, 9),
    (20, 11),
)


def fold_geometry(height_units: float, folded_offset_units: float) -> FoldGeometry:
    """Return the analytic geometry for a corner folded onto the bottom edge."""

    height = float(height_units)
    offset = float(folded_offset_units)
    upper = (height * height + offset * offset) / (2.0 * height)
    lower = height - upper
    crease_top_x = (height * height + offset * offset) / (2.0 * offset)
    width_units = max(18.0, crease_top_x + 4.0, offset + 7.0)
    half_angle = 90.0 - math.degrees(math.atan(offset / height))
    return FoldGeometry(
        height_units=height,
        folded_offset_units=offset,
        width_units=width_units,
        upper_segment_units=upper,
        lower_segment_units=lower,
        half_angle_degrees=half_angle,
        total_angle_degrees=2.0 * half_angle,
    )


def fold_answer_support() -> tuple[float, ...]:
    """Return answer support induced by the configured folded-corner cases."""

    return tuple(round1(fold_geometry(height, offset).half_angle_degrees) for height, offset in FOLD_CASES)


__all__ = ["FOLD_CASES", "fold_answer_support", "fold_geometry"]
