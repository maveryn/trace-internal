"""Shared 4-neighbor graph adapters for rectangular tile grids."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from ...shared.graph_algorithms import (
    bfs_dist_count_by_adjacency,
    connected_components_by_adjacency,
    reconstruct_unique_shortest_path_by_adjacency,
)


Coord = Tuple[int, int]


def iter_four_neighbors(cell: Coord) -> Iterable[Coord]:
    """Yield the four axis-aligned neighboring grid coordinates."""
    row, col = int(cell[0]), int(cell[1])
    yield (int(row - 1), int(col))
    yield (int(row + 1), int(col))
    yield (int(row), int(col - 1))
    yield (int(row), int(col + 1))


def open_grid_adjacency(
    *,
    rows: int,
    cols: int,
    blocked: Sequence[Sequence[bool]],
) -> Dict[Coord, List[Coord]]:
    """Build open-cell adjacency map for one blocked rectangular grid."""
    adjacency: Dict[Coord, List[Coord]] = {}
    for row in range(int(rows)):
        for col in range(int(cols)):
            if blocked[row][col]:
                continue
            node = (int(row), int(col))
            neighbors: List[Coord] = []
            if row > 0 and not blocked[row - 1][col]:
                neighbors.append((int(row - 1), int(col)))
            if row + 1 < int(rows) and not blocked[row + 1][col]:
                neighbors.append((int(row + 1), int(col)))
            if col > 0 and not blocked[row][col - 1]:
                neighbors.append((int(row), int(col - 1)))
            if col + 1 < int(cols) and not blocked[row][col + 1]:
                neighbors.append((int(row), int(col + 1)))
            adjacency[node] = neighbors
    return adjacency


def active_coord_adjacency(active_coords: Sequence[Coord]) -> Dict[Coord, List[Coord]]:
    """Build 4-neighbor adjacency for one deterministic set of active coordinates."""
    active = sorted({(int(row), int(col)) for row, col in active_coords})
    active_set = set(active)
    return {
        coord: [neighbor for neighbor in iter_four_neighbors(coord) if neighbor in active_set]
        for coord in active
    }


def connected_components_for_active_coords(active_coords: Sequence[Coord]) -> List[List[Coord]]:
    """Return row-major connected components for active 4-neighbor tile coordinates."""
    ordered = sorted({(int(row), int(col)) for row, col in active_coords})
    adjacency = active_coord_adjacency(ordered)
    return [
        [(int(row), int(col)) for row, col in component]
        for component in connected_components_by_adjacency(adjacency, node_order=ordered)
    ]


def degree_by_active_coord(active_coords: Sequence[Coord]) -> Dict[Coord, int]:
    """Return 4-neighbor degree for each active coordinate in canonical order."""
    ordered = sorted({(int(row), int(col)) for row, col in active_coords})
    adjacency = active_coord_adjacency(ordered)
    return {
        (int(row), int(col)): int(len(neighbors))
        for (row, col), neighbors in sorted(adjacency.items())
    }


def coord_adjacency_to_cell_ids(adjacency: Mapping[Coord, Sequence[Coord]]) -> Dict[str, List[str]]:
    """Convert coordinate adjacency to deterministic symbolic cell-id adjacency."""
    return {
        cell_id((int(row), int(col))): sorted(
            cell_id((int(next_row), int(next_col)))
            for next_row, next_col in neighbors_list
        )
        for (row, col), neighbors_list in sorted(adjacency.items())
    }


def bfs_dist_count(rows: int, cols: int, blocked: Sequence[Sequence[bool]], start: Coord) -> Tuple[List[List[int]], List[List[int]]]:
    """Compute BFS distance and shortest-path count from one start cell."""
    dist = [[-1 for _ in range(int(cols))] for _ in range(int(rows))]
    count = [[0 for _ in range(int(cols))] for _ in range(int(rows))]

    adjacency = open_grid_adjacency(rows=int(rows), cols=int(cols), blocked=blocked)
    dist_map, count_map = bfs_dist_count_by_adjacency(adjacency, start=(int(start[0]), int(start[1])))
    for (row, col), value in dist_map.items():
        dist[int(row)][int(col)] = int(value)
    for (row, col), value in count_map.items():
        count[int(row)][int(col)] = int(value)
    return dist, count


def reconstruct_unique_shortest_path(
    rows: int,
    cols: int,
    blocked: Sequence[Sequence[bool]],
    start: Coord,
    goal: Coord,
    dist_start: Sequence[Sequence[int]],
    dist_goal: Sequence[Sequence[int]],
) -> List[Coord] | None:
    """Reconstruct shortest path when exactly one witness path exists."""
    adjacency = open_grid_adjacency(rows=int(rows), cols=int(cols), blocked=blocked)

    dist_start_map = {
        (int(row), int(col)): int(dist_start[row][col])
        for row in range(int(rows))
        for col in range(int(cols))
        if int(dist_start[row][col]) >= 0
    }
    dist_goal_map = {
        (int(row), int(col)): int(dist_goal[row][col])
        for row in range(int(rows))
        for col in range(int(cols))
        if int(dist_goal[row][col]) >= 0
    }
    path = reconstruct_unique_shortest_path_by_adjacency(
        adjacency,
        start=(int(start[0]), int(start[1])),
        goal=(int(goal[0]), int(goal[1])),
        dist_start=dist_start_map,
        dist_goal=dist_goal_map,
    )
    if path is None:
        return None
    return [(int(row), int(col)) for row, col in path]


def cell_id(coord: Coord) -> str:
    """Build stable symbolic cell id for row/column coordinates."""
    return f"cell_{coord[0]}_{coord[1]}"


__all__ = [
    "active_coord_adjacency",
    "bfs_dist_count",
    "cell_id",
    "connected_components_for_active_coords",
    "degree_by_active_coord",
    "coord_adjacency_to_cell_ids",
    "iter_four_neighbors",
    "open_grid_adjacency",
    "reconstruct_unique_shortest_path",
]
