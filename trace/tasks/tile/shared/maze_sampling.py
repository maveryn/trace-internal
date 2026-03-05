"""Shared maze sampling and layout-invariant checks for tile/path tasks."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .path_grid import bfs_dist_count, reconstruct_unique_shortest_path


Coord = Tuple[int, int]


def sample_unique_shortest_path_maze(
    rng,
    *,
    rows: int,
    cols: int,
    min_shortest_len: int,
    obstacle_prob_min: float,
    obstacle_prob_max: float,
    max_attempts: int,
) -> Tuple[List[List[bool]], Coord, Coord, List[Coord], int]:
    """Sample one maze with an open start/goal and unique shortest-path witness."""
    cells = [(row, col) for row in range(rows) for col in range(cols)]
    for _ in range(max_attempts):
        obstacle_prob = rng.uniform(obstacle_prob_min, obstacle_prob_max)
        blocked = [[rng.random() < obstacle_prob for _ in range(cols)] for _ in range(rows)]

        open_cells = [coord for coord in cells if not blocked[coord[0]][coord[1]]]
        if len(open_cells) < 2:
            continue

        start = rng.choice(open_cells)
        goal = rng.choice(open_cells)
        if start == goal:
            continue

        dist_start, count_start = bfs_dist_count(rows, cols, blocked, start)
        shortest = dist_start[goal[0]][goal[1]]
        if shortest < int(min_shortest_len):
            continue
        if count_start[goal[0]][goal[1]] != 1:
            continue

        dist_goal, _ = bfs_dist_count(rows, cols, blocked, goal)
        path = reconstruct_unique_shortest_path(rows, cols, blocked, start, goal, dist_start, dist_goal)
        if path is None:
            continue
        if len(path) - 1 != shortest:
            continue
        return blocked, start, goal, path, shortest

    raise RuntimeError("failed to sample unique shortest-path maze")


def validate_open_path_entities(
    *,
    blocked: Sequence[Sequence[bool]],
    start: Coord,
    goal: Coord,
    path: Sequence[Coord],
) -> None:
    """Validate core occupancy/path invariants for open start-goal maze entities."""
    if start == goal:
        raise RuntimeError("invalid maze layout: start and goal must differ")
    if blocked[start[0]][start[1]] or blocked[goal[0]][goal[1]]:
        raise RuntimeError("invalid maze layout: start/goal must be open cells")
    if len(set(path)) != len(path):
        raise RuntimeError("invalid maze layout: path contains duplicate cells")
