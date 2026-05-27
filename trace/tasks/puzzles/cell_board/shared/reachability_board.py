"""Shared blocked-board reachability sampling helpers for tile tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .grid_graph import bfs_dist_count
from .tile_evidence import sort_coords_row_major


Coord = Tuple[int, int]


@dataclass(frozen=True)
class ReachabilityBoardSample:
    """Deterministic blocked-board sample plus reachability partitions."""

    blocked: Tuple[Tuple[bool, ...], ...]
    start_coord: Coord
    reachable_coords: Tuple[Coord, ...]
    reachable_non_start_coords: Tuple[Coord, ...]
    unreachable_open_coords: Tuple[Coord, ...]
    obstacle_fraction: float
    reachable_fraction: float


def sample_reachability_board(
    rng,
    *,
    rows: int,
    cols: int,
    obstacle_fraction_min: float,
    obstacle_fraction_max: float,
    reachable_fraction_min: float,
    reachable_fraction_max: float,
    max_attempts: int,
    min_reachable_count: int = 1,
    max_reachable_count: int | None = None,
    min_reachable_non_start_count: int = 0,
    min_unreachable_open_count: int = 0,
) -> ReachabilityBoardSample:
    """Sample one blocked board whose reachability partitions meet explicit bounds."""

    if int(rows) <= 0 or int(cols) <= 0:
        raise ValueError("rows and cols must be > 0")
    if int(max_attempts) <= 0:
        raise ValueError("max_attempts must be > 0")
    if int(min_reachable_count) < 1:
        raise ValueError("min_reachable_count must be >= 1")
    if int(min_reachable_non_start_count) < 0:
        raise ValueError("min_reachable_non_start_count must be >= 0")
    if int(min_unreachable_open_count) < 0:
        raise ValueError("min_unreachable_open_count must be >= 0")
    if max_reachable_count is not None and int(max_reachable_count) < int(min_reachable_count):
        raise ValueError("max_reachable_count must be >= min_reachable_count")

    all_coords = [(int(row), int(col)) for row in range(int(rows)) for col in range(int(cols))]
    board_cell_count = max(1, int(rows) * int(cols))

    for _ in range(int(max_attempts)):
        obstacle_fraction = float(rng.uniform(float(obstacle_fraction_min), float(obstacle_fraction_max)))
        blocked_rows = [
            [bool(rng.random() < obstacle_fraction) for _ in range(int(cols))]
            for _ in range(int(rows))
        ]
        open_cells = [coord for coord in all_coords if not blocked_rows[coord[0]][coord[1]]]
        if not open_cells:
            continue

        start = tuple(int(value) for value in rng.choice(open_cells))
        blocked_rows[start[0]][start[1]] = False

        dist_map, _count_map = bfs_dist_count(int(rows), int(cols), blocked_rows, start)
        reachable_coords = sort_coords_row_major(
            [
                (int(row), int(col))
                for row in range(int(rows))
                for col in range(int(cols))
                if int(dist_map[row][col]) >= 0
            ]
        )
        reachable_non_start_coords = sort_coords_row_major(
            [
                coord
                for coord in reachable_coords
                if coord != (int(start[0]), int(start[1]))
            ]
        )
        unreachable_open_coords = sort_coords_row_major(
            [
                (int(row), int(col))
                for row in range(int(rows))
                for col in range(int(cols))
                if (not bool(blocked_rows[row][col])) and int(dist_map[row][col]) < 0
            ]
        )

        if int(len(reachable_coords)) < int(min_reachable_count):
            continue
        if max_reachable_count is not None and int(len(reachable_coords)) > int(max_reachable_count):
            continue
        if int(len(reachable_non_start_coords)) < int(min_reachable_non_start_count):
            continue
        if int(len(unreachable_open_coords)) < int(min_unreachable_open_count):
            continue

        reachable_fraction = float(len(reachable_coords)) / float(board_cell_count)
        if reachable_fraction < float(reachable_fraction_min) or reachable_fraction > float(reachable_fraction_max):
            continue

        realized_obstacle_fraction = float(
            sum(1 for row in range(int(rows)) for col in range(int(cols)) if blocked_rows[row][col])
        ) / float(board_cell_count)

        return ReachabilityBoardSample(
            blocked=tuple(tuple(bool(value) for value in row) for row in blocked_rows),
            start_coord=(int(start[0]), int(start[1])),
            reachable_coords=tuple((int(row), int(col)) for row, col in reachable_coords),
            reachable_non_start_coords=tuple(
                (int(row), int(col)) for row, col in reachable_non_start_coords
            ),
            unreachable_open_coords=tuple(
                (int(row), int(col)) for row, col in unreachable_open_coords
            ),
            obstacle_fraction=float(realized_obstacle_fraction),
            reachable_fraction=float(reachable_fraction),
        )

    raise RuntimeError("failed to sample reachability board within configured constraints")


__all__ = [
    "Coord",
    "ReachabilityBoardSample",
    "sample_reachability_board",
]
