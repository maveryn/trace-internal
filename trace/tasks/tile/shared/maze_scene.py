"""Shared maze scene-projection helpers for tile/path tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from .path_grid import cell_id, coord_adjacency_to_cell_ids, open_grid_adjacency


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
    scene_entities: List[Dict[str, Any]] = []
    for row in range(rows):
        for col in range(cols):
            current_id = cell_id((row, col))
            scene_entities.append(
                {
                    "entity_id": current_id,
                    "entity_type": "tile_cell",
                    "attrs": {
                        "row": int(row),
                        "col": int(col),
                        "blocked": bool(blocked[row][col]),
                        "is_start": current_id == start_id,
                        "is_goal": current_id == goal_id,
                    },
                }
            )
    return scene_entities
