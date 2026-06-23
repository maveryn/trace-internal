"""Identity-free construction math for paper-fold diagrams."""

from __future__ import annotations

from functools import lru_cache
import math
from typing import Tuple

from trace.tasks.geometry.shared.measurement_rendering import round1

from .state import FoldGeometry

FoldCase = Tuple[int, int]
FoldAnswerCases = Tuple[float, Tuple[FoldCase, ...]]

_MIN_HEIGHT_UNITS = 10
_MAX_HEIGHT_UNITS = 34
_MIN_FOLDED_OFFSET_UNITS = 4
_MIN_ANSWER_DEGREES = 50.0
_MAX_ANSWER_DEGREES = 78.0


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


@lru_cache(maxsize=1)
def fold_answer_cases() -> tuple[FoldAnswerCases, ...]:
    """Return visually stable fold cases grouped by rounded answer value.

    Sampling uses the rounded answer as the first-stage support so review and
    training data do not over-represent common integer height/offset ratios
    that collapse to the same angle.
    """

    grouped: dict[float, list[FoldCase]] = {}
    for height in range(_MIN_HEIGHT_UNITS, _MAX_HEIGHT_UNITS + 1):
        for offset in range(_MIN_FOLDED_OFFSET_UNITS, height - 2):
            geometry = fold_geometry(float(height), float(offset))
            answer = round1(geometry.half_angle_degrees)
            if _MIN_ANSWER_DEGREES <= float(answer) <= _MAX_ANSWER_DEGREES:
                grouped.setdefault(float(answer), []).append((int(height), int(offset)))
    return tuple(
        (float(answer), tuple(cases))
        for answer, cases in sorted(grouped.items(), key=lambda item: float(item[0]))
        if cases
    )


def fold_answer_support() -> tuple[float, ...]:
    """Return the rounded answer support for paper-fold angle samples."""

    return tuple(float(answer) for answer, _cases in fold_answer_cases())


__all__ = ["FoldAnswerCases", "FoldCase", "fold_answer_cases", "fold_answer_support", "fold_geometry"]
