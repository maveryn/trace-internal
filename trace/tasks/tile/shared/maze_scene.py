"""Shared maze scene-projection helpers for tile/path tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from .grid_graph import cell_id, coord_adjacency_to_cell_ids, open_grid_adjacency
from .tile_scene import build_tile_cell_entities as build_generic_tile_cell_entities


Coord = Tuple[int, int]


def open_adjacency_by_cell(
    *,
    rows: int,
    cols: int,
    blocked: Sequence[Sequence[bool]],
) -> Dict[str, List[str]]:
    """Build open-cell adjacency map keyed by stable symbolic cell ids."""
    adjacency = open_grid_adjacency(rows=int(rows), cols=int(cols), blocked=blocked)
    return coord_adjacency_to_cell_ids(adjacency)


def build_tile_cell_entities(
    *,
    rows: int,
    cols: int,
    blocked: Sequence[Sequence[bool]],
    start: Coord,
    goal: Coord,
) -> List[Dict[str, Any]]:
    """Build `scene_ir.entities` entries for one tile-grid scene."""
    start_id = cell_id(start)
    goal_id = cell_id(goal)
    attrs_by_coord = {
        (int(row), int(col)): {
            "blocked": bool(blocked[row][col]),
            "is_start": cell_id((row, col)) == start_id,
            "is_goal": cell_id((row, col)) == goal_id,
        }
        for row in range(int(rows))
        for col in range(int(cols))
    }
    return build_generic_tile_cell_entities(
        rows=int(rows),
        cols=int(cols),
        attrs_by_coord=attrs_by_coord,
    )
