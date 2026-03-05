"""Tile blocked-grid graph adapters and helpers."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from ...shared.graph_algorithms import (
    bfs_dist_count_by_adjacency,
    reconstruct_unique_shortest_path_by_adjacency,
)


Coord = Tuple[int, int]


def _neighbors(cell: Coord, rows: int, cols: int) -> Iterable[Coord]:
    """Yield valid 4-neighbor cells for one grid coordinate."""
    row, col = cell
    if row > 0:
        yield (row - 1, col)
    if row + 1 < rows:
        yield (row + 1, col)
    if col > 0:
        yield (row, col - 1)
    if col + 1 < cols:
        yield (row, col + 1)


def open_grid_adjacency(
    *,
    rows: int,
    cols: int,
    blocked: Sequence[Sequence[bool]],
) -> Dict[Coord, List[Coord]]:
    """Build open-cell adjacency map for one blocked grid."""
    adjacency: Dict[Coord, List[Coord]] = {}
    for row in range(int(rows)):
        for col in range(int(cols)):
            if blocked[row][col]:
                continue
            node = (int(row), int(col))
            adjacency[node] = [
                (int(next_row), int(next_col))
                for next_row, next_col in _neighbors(node, int(rows), int(cols))
                if not blocked[next_row][next_col]
            ]
    return adjacency


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
    "open_grid_adjacency",
    "coord_adjacency_to_cell_ids",
    "bfs_dist_count",
    "reconstruct_unique_shortest_path",
    "cell_id",
]
