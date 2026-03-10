"""Shared slope-line geometry helpers for graph-paper measurement tasks."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple

from ...shared.geometry_primitives import Point

Vector = Tuple[int, int]
GraphBounds = Tuple[int, int, int, int]


@dataclass(frozen=True)
class SlopeLineSample:
    """One sampled graph-paper line for slope measurement."""

    slope_tenths: int
    slope_value: float
    slope_vector: Vector
    axis_crossing_graph: Tuple[int, int]
    lattice_point_graph: Tuple[int, int]
    axis_crossing_pixel: Point
    lattice_point_pixel: Point
    endpoint_a_graph: Tuple[float, float]
    endpoint_b_graph: Tuple[float, float]
    endpoint_a_pixel: Point
    endpoint_b_pixel: Point


def slope_vector_from_tenths(slope_tenths: int) -> Vector:
    """Return reduced integer vector `(dx, dy)` for one slope value in tenths."""
    value = int(slope_tenths)
    if int(value) == 0:
        raise ValueError("slope_tenths must be non-zero")
    divisor = int(math.gcd(abs(int(value)), 10))
    dx = int(10 // int(divisor))
    dy = int(value // int(divisor))
    if int(dx) == 0:
        raise ValueError("resolved slope vector must keep finite slope")
    return (int(dx), int(dy))


def graph_unit_bounds_for_canvas(
    *,
    canvas_size: int,
    graph_origin: Point,
    graph_spacing: int,
    outer_margin_px: int,
) -> Tuple[int, int, int, int]:
    """Return inclusive graph-unit bounds `(x_min, x_max, y_min, y_max)`."""
    spacing = max(1, int(graph_spacing))
    size = int(canvas_size)
    origin_x, origin_y = (float(graph_origin[0]), float(graph_origin[1]))
    inset = max(0, int(outer_margin_px))
    left = float(max(0, int(inset)))
    top = float(max(0, int(inset)))
    right = float(max(int(left), int(size) - 1 - int(inset)))
    bottom = float(max(int(top), int(size) - 1 - int(inset)))
    x_min = int(math.ceil((float(left) - float(origin_x)) / float(spacing)))
    x_max = int(math.floor((float(right) - float(origin_x)) / float(spacing)))
    y_min = int(math.ceil((float(origin_y) - float(bottom)) / float(spacing)))
    y_max = int(math.floor((float(origin_y) - float(top)) / float(spacing)))
    if int(x_min) > int(x_max) or int(y_min) > int(y_max):
        raise ValueError("graph bounds are empty for current canvas/style")
    return (int(x_min), int(x_max), int(y_min), int(y_max))


def _sample_non_integer(rng, *, low: float, high: float) -> float:
    """Sample a non-integer float from one finite interval."""
    lo = float(low)
    hi = float(high)
    if not (float(lo) < float(hi)):
        raise ValueError("low must be < high when sampling non-integer float")
    for _ in range(24):
        value = float(rng.uniform(float(lo), float(hi)))
        if abs(float(value) - float(round(float(value)))) > 1e-6:
            return float(value)
    mid = float(lo + (0.37 * (float(hi) - float(lo))))
    if abs(float(mid) - float(round(float(mid)))) <= 1e-6:
        mid = float(mid + (0.11 * (float(hi) - float(lo))))
    return float(min(float(hi), max(float(lo), float(mid))))


def _axis_t_range(*, coord_min: int, coord_max: int, origin_value: float, direction_value: float) -> Tuple[float, float]:
    """Return parametric `t` range for one axis-aligned bound."""
    if abs(float(direction_value)) <= 1e-9:
        if float(coord_min) <= float(origin_value) <= float(coord_max):
            return (-float("inf"), float("inf"))
        return (float("inf"), -float("inf"))
    t0 = (float(coord_min) - float(origin_value)) / float(direction_value)
    t1 = (float(coord_max) - float(origin_value)) / float(direction_value)
    return (min(float(t0), float(t1)), max(float(t0), float(t1)))


def feasible_axis_crossings_for_slope(
    *,
    slope_tenths: int,
    bounds: GraphBounds,
    min_extension_t: float = 0.01,
) -> list[tuple[int, float, float]]:
    """Return feasible integer x-axis crossings and parametric ranges for one slope."""
    dx, dy = slope_vector_from_tenths(int(slope_tenths))
    if int(dy) == 0:
        return []
    x_min, x_max, y_min, y_max = [int(value) for value in bounds]
    min_extension = max(1e-3, float(min_extension_t))
    feasible_candidates: list[tuple[int, float, float]] = []
    for intercept_x in range(int(x_min), int(x_max) + 1):
        lattice_x = int(intercept_x + int(dx))
        lattice_y = int(dy)
        if int(lattice_x) < int(x_min) or int(lattice_x) > int(x_max):
            continue
        if int(lattice_y) < int(y_min) or int(lattice_y) > int(y_max):
            continue
        t_x = _axis_t_range(
            coord_min=int(x_min),
            coord_max=int(x_max),
            origin_value=float(intercept_x),
            direction_value=float(dx),
        )
        t_y = _axis_t_range(
            coord_min=int(y_min),
            coord_max=int(y_max),
            origin_value=0.0,
            direction_value=float(dy),
        )
        t_lo = max(float(t_x[0]), float(t_y[0]))
        t_hi = min(float(t_x[1]), float(t_y[1]))
        if float(t_lo) >= float(t_hi):
            continue
        if float(t_lo) < -float(min_extension) and float(t_hi) > (1.0 + float(min_extension)):
            feasible_candidates.append((int(intercept_x), float(t_lo), float(t_hi)))
    return feasible_candidates


def has_feasible_slope_on_bounds(
    *,
    slope_tenths: int,
    bounds: GraphBounds,
    min_extension_t: float = 0.01,
) -> bool:
    """Return true when one slope can be drawn with required x-axis/lattice constraints."""
    return bool(
        feasible_axis_crossings_for_slope(
            slope_tenths=int(slope_tenths),
            bounds=tuple(int(value) for value in bounds),
            min_extension_t=float(min_extension_t),
        )
    )


def sample_slope_line_on_graph_paper(
    rng,
    *,
    canvas_size: int,
    graph_origin: Point,
    graph_spacing: int,
    outer_margin_px: int,
    slope_tenths: int,
    min_extension_t: float = 0.01,
) -> SlopeLineSample:
    """Sample one line that crosses x-axis at an integer lattice point and another lattice point."""
    slope_value = float(int(slope_tenths)) / 10.0
    dx, dy = slope_vector_from_tenths(int(slope_tenths))
    if int(dy) == 0:
        raise ValueError("slope_tenths must map to non-zero slope")
    x_min, x_max, y_min, y_max = graph_unit_bounds_for_canvas(
        canvas_size=int(canvas_size),
        graph_origin=(float(graph_origin[0]), float(graph_origin[1])),
        graph_spacing=int(graph_spacing),
        outer_margin_px=int(outer_margin_px),
    )
    min_extension = max(1e-3, float(min_extension_t))
    feasible_candidates = feasible_axis_crossings_for_slope(
        slope_tenths=int(slope_tenths),
        bounds=(int(x_min), int(x_max), int(y_min), int(y_max)),
        min_extension_t=float(min_extension),
    )
    if not feasible_candidates:
        raise ValueError("no feasible line placement for slope on current graph-paper bounds")

    intercept_x, t_lo, t_hi = rng.choice(feasible_candidates)
    t_start = _sample_non_integer(
        rng,
        low=float(t_lo),
        high=float(-float(min_extension)),
    )
    t_end = _sample_non_integer(
        rng,
        low=float(1.0 + float(min_extension)),
        high=float(t_hi),
    )

    endpoint_a_graph = (
        float(intercept_x) + (float(t_start) * float(dx)),
        float(t_start) * float(dy),
    )
    endpoint_b_graph = (
        float(intercept_x) + (float(t_end) * float(dx)),
        float(t_end) * float(dy),
    )
    origin_x, origin_y = (float(graph_origin[0]), float(graph_origin[1]))
    spacing = float(max(1, int(graph_spacing)))

    def _graph_to_pixel(point_graph: Tuple[float, float]) -> Point:
        return (
            float(origin_x) + (float(point_graph[0]) * float(spacing)),
            float(origin_y) - (float(point_graph[1]) * float(spacing)),
        )

    axis_crossing_graph = (int(intercept_x), 0)
    lattice_point_graph = (int(intercept_x + int(dx)), int(dy))
    return SlopeLineSample(
        slope_tenths=int(slope_tenths),
        slope_value=float(slope_value),
        slope_vector=(int(dx), int(dy)),
        axis_crossing_graph=(int(axis_crossing_graph[0]), int(axis_crossing_graph[1])),
        lattice_point_graph=(int(lattice_point_graph[0]), int(lattice_point_graph[1])),
        axis_crossing_pixel=_graph_to_pixel((float(axis_crossing_graph[0]), float(axis_crossing_graph[1]))),
        lattice_point_pixel=_graph_to_pixel((float(lattice_point_graph[0]), float(lattice_point_graph[1]))),
        endpoint_a_graph=(float(endpoint_a_graph[0]), float(endpoint_a_graph[1])),
        endpoint_b_graph=(float(endpoint_b_graph[0]), float(endpoint_b_graph[1])),
        endpoint_a_pixel=_graph_to_pixel(endpoint_a_graph),
        endpoint_b_pixel=_graph_to_pixel(endpoint_b_graph),
    )


__all__ = [
    "SlopeLineSample",
    "feasible_axis_crossings_for_slope",
    "graph_unit_bounds_for_canvas",
    "has_feasible_slope_on_bounds",
    "sample_slope_line_on_graph_paper",
    "slope_vector_from_tenths",
]
