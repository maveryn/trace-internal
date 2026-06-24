"""Scene-local measurement and formatting helpers."""

from __future__ import annotations

from typing import Sequence

from .state import BBox

DEGREE_SYMBOL = chr(176)
VERTEX_LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")


def probability_map(options: Sequence[str], *, selected: str | None = None) -> dict[str, float]:
    """Return a uniform probability map, optionally collapsed to one selected option."""

    resolved = tuple(str(option) for option in options)
    if not resolved:
        return {}
    if selected is not None:
        return {option: (1.0 if option == str(selected) else 0.0) for option in resolved}
    probability = 1.0 / float(len(resolved))
    return {option: probability for option in resolved}


def polygon_angle_sum(side_count: int) -> int:
    """Return the interior-angle sum for a polygon with ``side_count`` sides."""

    return int(side_count - 2) * 180


def polygon_kind(side_count: int) -> str:
    """Return a prompt-friendly polygon kind name."""

    if int(side_count) == 3:
        return "triangle"
    if int(side_count) == 4:
        return "quadrilateral"
    if int(side_count) == 5:
        return "pentagon"
    if int(side_count) == 6:
        return "hexagon"
    return f"{int(side_count)}-gon"


def angle_name(labels: Sequence[str], index: int) -> str:
    """Return the three-letter angle name at one vertex."""

    side_count = len(labels)
    prev_label = str(labels[(int(index) - 1) % side_count])
    vertex_label = str(labels[int(index) % side_count])
    next_label = str(labels[(int(index) + 1) % side_count])
    return f"{prev_label}{vertex_label}{next_label}"


def format_degrees(value: int) -> str:
    """Format an integer degree measure for on-image labels."""

    return f"{int(value)}{DEGREE_SYMBOL}"


def format_linear_expression(coefficient: int, constant: int) -> str:
    """Format one linear expression in x."""

    coeff = int(coefficient)
    const = int(constant)
    if coeff == 1:
        body = "x"
    elif coeff == -1:
        body = "-x"
    else:
        body = f"{coeff}x"
    if const > 0:
        return f"{body}+{const}"
    if const < 0:
        return f"{body}{const}"
    return body


def format_angle_expression(coefficient: int, constant: int) -> str:
    """Format one linear expression as an angle measure."""

    expression = format_linear_expression(coefficient, constant)
    if int(coefficient) == 1 and int(constant) == 0:
        return f"x{DEGREE_SYMBOL}"
    return f"({expression}){DEGREE_SYMBOL}"


def bbox_overlaps(a: BBox, b: BBox, *, pad: float = 3.0) -> bool:
    """Return whether two bboxes overlap after padding."""

    ax0, ay0, ax1, ay1 = [float(value) for value in a]
    bx0, by0, bx1, by1 = [float(value) for value in b]
    return not (
        ax1 + float(pad) < bx0
        or bx1 + float(pad) < ax0
        or ay1 + float(pad) < by0
        or by1 + float(pad) < ay0
    )


def assert_non_overlapping(bboxes: Sequence[BBox]) -> None:
    """Reject overlapping label boxes."""

    for left_index, left in enumerate(bboxes):
        for right in bboxes[left_index + 1 :]:
            if bbox_overlaps(left, right, pad=2.0):
                raise ValueError("polygon angle label layout overlaps")


__all__ = [
    "DEGREE_SYMBOL",
    "VERTEX_LABELS",
    "angle_name",
    "assert_non_overlapping",
    "bbox_overlaps",
    "format_angle_expression",
    "format_degrees",
    "format_linear_expression",
    "polygon_angle_sum",
    "polygon_kind",
    "probability_map",
]
