"""Tangram shape catalogs and coordinate primitives."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from .state import PieceSpec, Point

BASE_PIECES: tuple[PieceSpec, ...] = (
    PieceSpec(
        piece_id="piece_1",
        shape_id="right_triangle",
        shape_name="triangle",
        points=((0.0, 0.0), (2.0, 0.0), (0.0, 2.0)),
    ),
    PieceSpec(
        piece_id="piece_2",
        shape_id="right_triangle",
        shape_name="triangle",
        points=((2.0, 0.0), (4.0, 0.0), (4.0, 2.0)),
    ),
    PieceSpec(
        piece_id="piece_3",
        shape_id="right_triangle",
        shape_name="triangle",
        points=((0.0, 2.0), (0.0, 4.0), (2.0, 4.0)),
    ),
    PieceSpec(
        piece_id="piece_4",
        shape_id="right_triangle",
        shape_name="triangle",
        points=((4.0, 2.0), (4.0, 4.0), (2.0, 4.0)),
    ),
    PieceSpec(
        piece_id="piece_5",
        shape_id="diamond",
        shape_name="diamond",
        points=((1.0, 1.0), (2.0, 0.0), (3.0, 1.0), (2.0, 2.0)),
    ),
    PieceSpec(
        piece_id="piece_6",
        shape_id="left_notched_piece",
        shape_name="notched polygon",
        points=((0.0, 2.0), (1.0, 1.0), (2.0, 2.0), (1.0, 3.0), (0.0, 4.0)),
    ),
    PieceSpec(
        piece_id="piece_7",
        shape_id="right_notched_piece",
        shape_name="mirrored notched polygon",
        points=((4.0, 2.0), (3.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0)),
    ),
)

CONTACTS: dict[str, tuple[str, ...]] = {
    "piece_1": ("piece_5", "piece_6"),
    "piece_2": ("piece_5", "piece_7"),
    "piece_3": ("piece_6",),
    "piece_4": ("piece_7",),
    "piece_5": ("piece_1", "piece_2", "piece_6", "piece_7"),
    "piece_6": ("piece_1", "piece_3", "piece_5"),
    "piece_7": ("piece_2", "piece_4", "piece_5"),
}

OPTION_SHAPES: dict[str, tuple[Point, ...]] = {
    "right_triangle": ((0.0, 0.0), (2.0, 0.0), (0.0, 2.0)),
    "diamond": ((1.0, 0.0), (2.0, 1.0), (1.0, 2.0), (0.0, 1.0)),
    "left_notched_piece": (
        (0.0, 1.0),
        (1.0, 0.0),
        (2.0, 1.0),
        (1.0, 2.0),
        (0.0, 3.0),
    ),
    "right_notched_piece": (
        (2.0, 1.0),
        (1.0, 0.0),
        (0.0, 1.0),
        (1.0, 2.0),
        (2.0, 3.0),
    ),
    "trapezoid": ((0.2, 0.0), (1.8, 0.0), (2.2, 1.3), (0.0, 1.3)),
    "kite": ((1.0, 0.0), (2.1, 0.85), (1.0, 2.2), (0.0, 0.85)),
    "skinny_triangle": ((0.0, 0.0), (2.0, 0.0), (1.0, 1.45)),
    "parallelogram": ((0.45, 0.0), (2.0, 0.0), (1.55, 1.2), (0.0, 1.2)),
    "wide_pentagon": (
        (0.3, 0.0),
        (1.7, 0.0),
        (2.1, 0.85),
        (1.0, 1.6),
        (-0.1, 0.85),
    ),
}

MIRROR_DISTRACTOR_EXCLUSIONS: dict[str, str] = {
    "left_notched_piece": "right_notched_piece",
    "right_notched_piece": "left_notched_piece",
}

PIECE_FILLS: tuple[tuple[int, int, int], ...] = (
    (74, 122, 178),
    (219, 142, 82),
    (86, 155, 118),
    (190, 91, 105),
    (139, 104, 184),
    (214, 181, 78),
    (73, 154, 176),
)


def piece_by_id(piece_id: str) -> PieceSpec:
    """Return one base piece by stable id."""

    for piece in BASE_PIECES:
        if str(piece.piece_id) == str(piece_id):
            return piece
    raise ValueError(f"unknown Tangram piece id: {piece_id!r}")


def bounds(points: Sequence[Point]) -> tuple[float, float, float, float]:
    """Return the axis-aligned bounds of one point sequence."""

    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def round_bbox(points: Sequence[Point]) -> list[float]:
    """Return stable rounded pixel bounds for one polygon."""

    x0, y0, x1, y1 = bounds(points)
    return [round(float(value), 3) for value in (x0, y0, x1, y1)]


def centroid(points: Sequence[Point]) -> Point:
    """Return the arithmetic center of one polygon vertex list."""

    if not points:
        return 0.0, 0.0
    return (
        sum(float(point[0]) for point in points) / float(len(points)),
        sum(float(point[1]) for point in points) / float(len(points)),
    )


def rotate_points(
    points: Sequence[Point], *, degrees: float, center: Point
) -> list[Point]:
    """Rotate points around one center by degrees."""

    theta = math.radians(float(degrees))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    cx, cy = float(center[0]), float(center[1])
    out: list[Point] = []
    for x, y in points:
        dx = float(x) - cx
        dy = float(y) - cy
        out.append((cx + dx * cos_t - dy * sin_t, cy + dx * sin_t + dy * cos_t))
    return out


def normalize_points_to_box(
    points: Sequence[Point],
    box: Sequence[float],
    *,
    padding_px: float,
    rotation_degrees: float = 0.0,
) -> list[Point]:
    """Scale and center a polygon into a target pixel box."""

    local = [(float(x), float(y)) for x, y in points]
    cx, cy = centroid(local)
    if abs(float(rotation_degrees)) > 1e-6:
        local = rotate_points(local, degrees=float(rotation_degrees), center=(cx, cy))
    min_x, min_y, max_x, max_y = bounds(local)
    width = max(1e-6, max_x - min_x)
    height = max(1e-6, max_y - min_y)
    x0, y0, x1, y1 = [float(value) for value in box]
    target_width = max(1.0, float(x1 - x0 - 2.0 * float(padding_px)))
    target_height = max(1.0, float(y1 - y0 - 2.0 * float(padding_px)))
    scale = min(target_width / width, target_height / height)
    offset_x = float(x0 + 0.5 * (x1 - x0 - width * scale) - min_x * scale)
    offset_y = float(y0 + 0.5 * (y1 - y0 - height * scale) - min_y * scale)
    return [
        (float(offset_x + x * scale), float(offset_y + y * scale)) for x, y in local
    ]


def flatten_points(point_groups: Iterable[Sequence[Point]]) -> list[Point]:
    """Flatten polygon point groups for bbox computations."""

    return [point for group in point_groups for point in group]


__all__ = [
    "BASE_PIECES",
    "CONTACTS",
    "MIRROR_DISTRACTOR_EXCLUSIONS",
    "OPTION_SHAPES",
    "PIECE_FILLS",
    "bounds",
    "centroid",
    "flatten_points",
    "normalize_points_to_box",
    "piece_by_id",
    "rotate_points",
    "round_bbox",
]
