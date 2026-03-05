"""Shared graph-paper canvas/grid sampling helpers for geometry tasks."""

from __future__ import annotations

import math
from typing import Any, List, Mapping

from ...shared.geometry_primitives import Point, distance_sq
from ...shared.config_defaults import group_default


def resolve_square_canvas_size(
    rng,
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    fallback_min: int,
    fallback_max: int,
) -> int:
    """Resolve square canvas size with deterministic random range sampling."""
    explicit_size = params.get("canvas_size", render_defaults.get("canvas_size"))
    if explicit_size is not None:
        value = int(explicit_size)
        if value < 64:
            raise ValueError("canvas_size must be >= 64")
        return int(value)

    size_min = int(params.get("canvas_size_min", group_default(render_defaults, "canvas_size_min", fallback_min)))
    size_max = int(params.get("canvas_size_max", group_default(render_defaults, "canvas_size_max", fallback_max)))
    if size_min > size_max:
        raise ValueError("canvas_size_min must be <= canvas_size_max")
    if size_min < 64:
        raise ValueError("canvas_size_min must be >= 64")
    return int(rng.randint(int(size_min), int(size_max)))


def graph_spacing_from_cells(*, canvas_size: int, graph_cells: int, min_spacing_px: int = 4) -> int:
    """Compute graph-paper spacing from canvas size and sampled cells-per-side."""
    size_px = max(1, int(canvas_size))
    cells = max(2, int(graph_cells))
    spacing = int(round(float(size_px) / float(cells)))
    return max(int(min_spacing_px), int(spacing))


def resolve_graph_cells_per_side(
    rng,
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    canvas_size: int,
    fallback_min: int,
    fallback_max: int,
    min_spacing_px: int = 4,
) -> int:
    """Resolve graph-paper cells-per-side with deterministic random range sampling."""
    explicit_cells = params.get("graph_cells", render_defaults.get("graph_cells"))
    if explicit_cells is not None:
        value = int(explicit_cells)
        if value < 2:
            raise ValueError("graph_cells must be >= 2")
        spacing = graph_spacing_from_cells(canvas_size=int(canvas_size), graph_cells=int(value), min_spacing_px=min_spacing_px)
        if int(spacing) < int(min_spacing_px):
            raise ValueError("graph_cells is too large for current canvas_size")
        return int(value)

    cells_min = int(params.get("graph_cells_min", group_default(render_defaults, "graph_cells_min", fallback_min)))
    cells_max = int(params.get("graph_cells_max", group_default(render_defaults, "graph_cells_max", fallback_max)))
    if cells_min > cells_max:
        raise ValueError("graph_cells_min must be <= graph_cells_max")
    feasible = [
        cells
        for cells in range(max(2, int(cells_min)), int(cells_max) + 1)
        if graph_spacing_from_cells(canvas_size=int(canvas_size), graph_cells=int(cells), min_spacing_px=min_spacing_px)
        >= int(min_spacing_px)
    ]
    if not feasible:
        raise ValueError("no feasible graph_cells in range for current canvas_size")
    return int(rng.choice(feasible))


def sample_vertices_on_graph_paper(
    rng,
    *,
    count: int,
    canvas_size: int,
    margin: int,
    min_dist: float,
    spacing: int,
) -> List[Point]:
    """Sample separated points constrained to graph-paper lattice intersections."""
    spacing_px = max(4, int(spacing))
    lo = int(math.ceil(float(margin) / float(spacing_px))) * spacing_px
    hi = int(math.floor((float(canvas_size) - float(margin)) / float(spacing_px))) * spacing_px
    if lo > hi:
        raise ValueError("graph-paper intersection range is empty")

    coords = list(range(lo, hi + 1, spacing_px))
    lattice = [(float(x), float(y)) for x in coords for y in coords]
    if len(lattice) < count:
        raise ValueError("not enough graph-paper intersections for requested candidate_count")

    min_dist_sq = float(min_dist * min_dist)
    for _attempt in range(240):
        vertices: List[Point] = []
        shuffled = list(lattice)
        rng.shuffle(shuffled)
        for point in shuffled:
            if all(distance_sq(point, existing) >= min_dist_sq for existing in vertices):
                vertices.append(point)
                if len(vertices) == count:
                    return vertices
    raise ValueError("failed to place non-overlapping graph-paper vertices")
