"""Geometry construction primitives for graph-paper tasks."""

from __future__ import annotations

from math import pi
from random import Random
from typing import Sequence

from .state import Point


def rectangle_points(
    center: Point, width: float, height: float
) -> tuple[Point, Point, Point, Point]:
    """Return graph-unit rectangle vertices around a center."""

    cx, cy = float(center[0]), float(center[1])
    w, h = float(width) / 2.0, float(height) / 2.0
    return ((cx - w, cy - h), (cx + w, cy - h), (cx + w, cy + h), (cx - w, cy + h))


def right_triangle_points(
    center: Point, base: float, height: float
) -> tuple[Point, Point, Point]:
    """Return graph-unit right-triangle vertices around a center."""

    cx, cy = float(center[0]), float(center[1])
    return (
        (cx - base / 2.0, cy - height / 2.0),
        (cx + base / 2.0, cy - height / 2.0),
        (cx - base / 2.0, cy + height / 2.0),
    )


def polygon_area(points: Sequence[Point]) -> float:
    """Shoelace area for graph-unit polygon points."""

    total = 0.0
    pts = list(points)
    for index, point in enumerate(pts):
        nxt = pts[(index + 1) % len(pts)]
        total += float(point[0]) * float(nxt[1]) - float(nxt[0]) * float(point[1])
    return abs(total) / 2.0


def polygon_perimeter(points: Sequence[Point]) -> float:
    """Perimeter for graph-unit polygon points."""

    total = 0.0
    pts = list(points)
    for index, point in enumerate(pts):
        nxt = pts[(index + 1) % len(pts)]
        total += (
            (float(point[0]) - float(nxt[0])) ** 2
            + (float(point[1]) - float(nxt[1])) ** 2
        ) ** 0.5
    return total


def pi_expression(coefficient: int) -> str:
    """Return a compact kπ expression."""

    value = int(coefficient)
    if value == 1:
        return "π"
    return f"{value}π"


def regular_polygon(
    center: Point, sides: int, radius: float, *, phase: float = 0.0
) -> tuple[Point, ...]:
    """Return graph-unit vertices of a regular polygon."""

    from math import cos, sin

    cx, cy = float(center[0]), float(center[1])
    return tuple(
        (
            cx + float(radius) * cos(float(phase) + 2.0 * pi * index / int(sides)),
            cy + float(radius) * sin(float(phase) + 2.0 * pi * index / int(sides)),
        )
        for index in range(int(sides))
    )


def concave_polygon(
    center: Point, sides: int, radius: float, rng: Random
) -> tuple[Point, ...]:
    """Return a visually clear inward-notch polygon for convexity counting."""

    del sides
    cx, cy = float(center[0]), float(center[1])
    scale = float(radius)
    points = [
        (-1.0, -0.85),
        (1.0, -0.85),
        (-0.2, 0.0),
        (1.0, 0.85),
        (-1.0, 0.85),
    ]
    if int(rng.randrange(0, 2)) == 1:
        points = [(-x, y) for x, y in points]
    quarter_turns = int(rng.randrange(0, 4))
    for _ in range(quarter_turns):
        points = [(-y, x) for x, y in points]
    return tuple((cx + (scale * x), cy + (scale * y)) for x, y in points)
