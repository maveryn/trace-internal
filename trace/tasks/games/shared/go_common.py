"""Shared Go board-state helpers for liberty-count games tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set, Tuple


EMPTY = 0
BLACK = 1
WHITE = -1
BOARD_SIZE = 7

Coord = Tuple[int, int]
Board = Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class GoStoneSpec:
    """One visible stone on the Go board."""

    stone_id: str
    point_id: str
    row: int
    col: int
    color: str
    is_marked_group: bool


@dataclass(frozen=True)
class GoBoardState:
    """One visible Go board plus the highlighted group and its liberties."""

    board: Board
    marked_group_color: int
    marked_group_coords: Tuple[Coord, ...]
    liberty_coords: Tuple[Coord, ...]
    stone_specs: Tuple[GoStoneSpec, ...]
    scene_variant: str


def color_name(color: int) -> str:
    """Return the canonical prompt-facing color name for one stone value."""

    return "Black" if int(color) == int(BLACK) else "White"


def coord_to_point_id(coord: Coord) -> str:
    """Return one stable entity id for a board intersection."""

    return f"point_r{int(coord[0])}_c{int(coord[1])}"


def coord_to_stone_id(coord: Coord) -> str:
    """Return one stable entity id for an occupied intersection."""

    return f"stone_r{int(coord[0])}_c{int(coord[1])}"


def opponent(color: int) -> int:
    """Return the opposite Go color."""

    return int(WHITE if int(color) == int(BLACK) else BLACK)


def neighbors(coord: Coord, *, board_size: int = BOARD_SIZE) -> Tuple[Coord, ...]:
    """Return orthogonal in-bounds neighbors for one intersection."""

    row, col = int(coord[0]), int(coord[1])
    candidates = (
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    )
    return tuple(
        (int(next_row), int(next_col))
        for next_row, next_col in candidates
        if 0 <= int(next_row) < int(board_size) and 0 <= int(next_col) < int(board_size)
    )


def _board_from_rows(rows: Sequence[Sequence[int]]) -> Board:
    """Return one immutable board from row-major cells."""

    return tuple(tuple(int(cell) for cell in row) for row in rows)


def connected_group(board: Sequence[Sequence[int]], start: Coord) -> Tuple[Coord, ...]:
    """Return the full same-color connected group containing `start`."""

    row, col = int(start[0]), int(start[1])
    color = int(board[row][col])
    if int(color) == int(EMPTY):
        return tuple()
    board_size = int(len(board))
    seen: Set[Coord] = set()
    stack: List[Coord] = [(int(row), int(col))]
    while stack:
        coord = stack.pop()
        if coord in seen:
            continue
        seen.add(coord)
        for neighbor in neighbors(coord, board_size=board_size):
            if int(board[neighbor[0]][neighbor[1]]) == int(color) and neighbor not in seen:
                stack.append(neighbor)
    return tuple(sorted(seen))


def group_liberties(board: Sequence[Sequence[int]], group: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Return the empty orthogonal liberties for one connected group."""

    board_size = int(len(board))
    liberties: Set[Coord] = set()
    for row, col in group:
        for neighbor in neighbors((int(row), int(col)), board_size=board_size):
            if int(board[neighbor[0]][neighbor[1]]) == int(EMPTY):
                liberties.add((int(neighbor[0]), int(neighbor[1])))
    return tuple(sorted(liberties))


def all_groups_have_liberty(board: Sequence[Sequence[int]]) -> bool:
    """Return whether every occupied group on the board has at least one liberty."""

    board_size = int(len(board))
    seen: Set[Coord] = set()
    for row in range(board_size):
        for col in range(board_size):
            if int(board[row][col]) == int(EMPTY) or (row, col) in seen:
                continue
            group = connected_group(board, (int(row), int(col)))
            seen.update(group)
            if not group_liberties(board, group):
                return False
    return True


def liberty_point_ids(liberties: Iterable[Coord]) -> Tuple[str, ...]:
    """Return stable point ids for one liberty set."""

    return tuple(coord_to_point_id(coord) for coord in liberties)


def supported_targets_for_query() -> Tuple[int, ...]:
    """Return the supported visible liberty counts for the active Go task."""

    return (1, 2, 3, 4, 5, 6, 7, 8)


def _sample_connected_group(rng, *, board_size: int, size: int, favor_center: bool) -> Tuple[Coord, ...]:
    """Sample one connected group footprint with optional center bias."""

    if bool(favor_center):
        row_support = tuple(range(1, int(board_size) - 1))
        col_support = tuple(range(1, int(board_size) - 1))
    else:
        row_support = tuple(range(int(board_size)))
        col_support = tuple(range(int(board_size)))
    start = (int(rng.choice(row_support)), int(rng.choice(col_support)))
    group: Set[Coord] = {start}
    frontier: Set[Coord] = set(neighbors(start, board_size=board_size))
    while len(group) < int(size) and frontier:
        ordered_frontier = sorted(frontier)
        coord = ordered_frontier[int(rng.randrange(len(ordered_frontier)))]
        frontier.remove(coord)
        group.add(coord)
        for neighbor in neighbors(coord, board_size=board_size):
            if neighbor not in group:
                frontier.add(neighbor)
    if len(group) != int(size):
        return tuple()
    return tuple(sorted(group))


def _boundary_neighbors(group: Iterable[Coord], *, board_size: int) -> Tuple[Coord, ...]:
    """Return the orthogonal boundary coordinates around a connected group."""

    group_set = {(
        int(coord[0]),
        int(coord[1]),
    ) for coord in group}
    boundary: Set[Coord] = set()
    for coord in group_set:
        for neighbor in neighbors(coord, board_size=board_size):
            if neighbor not in group_set:
                boundary.add(neighbor)
    return tuple(sorted(boundary))


def _minimum_group_size_for_target(target_answer: int) -> int:
    """Return a small connected-group size that can support the requested liberties."""

    return max(1, int(math.ceil((float(target_answer) - 2.0) / 2.0)))


def _stone_specs(board: Sequence[Sequence[int]], *, marked_group_coords: Iterable[Coord]) -> Tuple[GoStoneSpec, ...]:
    """Return visible stone specs in stable row-major order."""

    board_size = int(len(board))
    marked_group = {(int(coord[0]), int(coord[1])) for coord in marked_group_coords}
    specs: List[GoStoneSpec] = []
    for row in range(board_size):
        for col in range(board_size):
            color = int(board[row][col])
            if int(color) == int(EMPTY):
                continue
            coord = (int(row), int(col))
            specs.append(
                GoStoneSpec(
                    stone_id=coord_to_stone_id(coord),
                    point_id=coord_to_point_id(coord),
                    row=int(row),
                    col=int(col),
                    color=str(color_name(int(color)).lower()),
                    is_marked_group=coord in marked_group,
                )
            )
    return tuple(specs)


def build_go_board_state(
    *,
    rng,
    query_variant: str,
    scene_variant: str,
    target_answer: int,
    board_size: int = BOARD_SIZE,
    max_internal_attempts: int = 512,
) -> GoBoardState:
    """Construct one visible `7 x 7` Go board with a marked group and exact liberties."""

    target = int(target_answer)
    if target not in supported_targets_for_query():
        raise ValueError(f"unsupported Go liberty target: {target}")
    if int(board_size) != int(BOARD_SIZE):
        raise ValueError("the active Go task keeps the board fixed to 7x7")
    if str(query_variant) not in {"marked_black_group_liberty_count", "marked_white_group_liberty_count"}:
        raise ValueError(f"unsupported Go query variant: {query_variant}")
    if str(scene_variant) not in {"open_board", "crowded_board"}:
        raise ValueError(f"unsupported Go scene variant: {scene_variant}")

    marked_group_color = int(BLACK if str(query_variant) == "marked_black_group_liberty_count" else WHITE)
    opponent_color = int(opponent(marked_group_color))
    extras_min, extras_max = (4, 10) if str(scene_variant) == "open_board" else (12, 20)

    for _ in range(max(1, int(max_internal_attempts))):
        group_size_min = _minimum_group_size_for_target(int(target))
        group_size_max = min(5, int(group_size_min) + 2)
        group_size = int(rng.randint(int(group_size_min), int(group_size_max)))
        group = _sample_connected_group(
            rng,
            board_size=int(board_size),
            size=int(group_size),
            favor_center=bool(int(target) >= 6),
        )
        if not group:
            continue
        boundary = _boundary_neighbors(group, board_size=int(board_size))
        if len(boundary) < int(target):
            continue

        liberties = tuple(
            sorted(
                boundary[index]
                for index in rng.sample(range(len(boundary)), int(target))
            )
        )
        liberty_set = set(liberties)
        rows = [[int(EMPTY) for _ in range(int(board_size))] for _ in range(int(board_size))]
        for row, col in group:
            rows[int(row)][int(col)] = int(marked_group_color)
        for row, col in boundary:
            if (int(row), int(col)) in liberty_set:
                continue
            rows[int(row)][int(col)] = int(opponent_color)
        board = _board_from_rows(rows)
        if not all_groups_have_liberty(board):
            continue

        empty_coords = [
            (int(row), int(col))
            for row in range(int(board_size))
            for col in range(int(board_size))
            if int(board[row][col]) == int(EMPTY) and (int(row), int(col)) not in liberty_set
        ]
        rng.shuffle(empty_coords)
        extras_target = int(rng.randint(int(extras_min), int(extras_max)))
        mutable_rows = [list(int(cell) for cell in row) for row in board]
        extras_added = 0
        for row, col in empty_coords:
            if extras_added >= int(extras_target):
                break
            stone_color = int(marked_group_color if float(rng.random()) < 0.45 else opponent_color)
            mutable_rows[int(row)][int(col)] = int(stone_color)
            candidate_board = _board_from_rows(mutable_rows)
            if not all_groups_have_liberty(candidate_board):
                mutable_rows[int(row)][int(col)] = int(EMPTY)
                continue
            extras_added += 1
        board = _board_from_rows(mutable_rows)
        marked_group = connected_group(board, group[0])
        liberties_now = group_liberties(board, marked_group)
        if set(marked_group) != set(group):
            continue
        if tuple(sorted(liberties_now)) != tuple(sorted(liberties)):
            continue

        return GoBoardState(
            board=board,
            marked_group_color=int(marked_group_color),
            marked_group_coords=tuple(sorted(marked_group)),
            liberty_coords=tuple(sorted(liberties_now)),
            stone_specs=_stone_specs(board, marked_group_coords=marked_group),
            scene_variant=str(scene_variant),
        )

    raise RuntimeError(
        f"failed to construct a visible Go board with {target} liberties for {query_variant}/{scene_variant}"
    )


__all__ = [
    "BLACK",
    "BOARD_SIZE",
    "Board",
    "Coord",
    "EMPTY",
    "GoBoardState",
    "GoStoneSpec",
    "WHITE",
    "all_groups_have_liberty",
    "build_go_board_state",
    "color_name",
    "connected_group",
    "coord_to_point_id",
    "coord_to_stone_id",
    "group_liberties",
    "liberty_point_ids",
    "neighbors",
    "opponent",
    "supported_targets_for_query",
]
