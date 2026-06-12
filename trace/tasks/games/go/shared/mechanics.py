"""Shared Go board-state helpers for group-property games tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set, Tuple


EMPTY = 0
BLACK = 1
WHITE = -1
BOARD_SIZE = 7
SUPPORTED_GO_PLAYER_COLORS: Tuple[str, ...] = ("black", "white")

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
    adjacent_enemy_coords: Tuple[Coord, ...]
    shared_liberty_coords: Tuple[Coord, ...]
    stone_specs: Tuple[GoStoneSpec, ...]
    scene_variant: str


@dataclass(frozen=True)
class GoStoneGroupCountState:
    """One visible Go board plus whole-board groups for one queried color."""

    board: Board
    target_color: int
    target_group_coords: Tuple[Tuple[Coord, ...], ...]
    representative_coords: Tuple[Coord, ...]
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


def stone_groups(board: Sequence[Sequence[int]], *, color: int) -> Tuple[Tuple[Coord, ...], ...]:
    """Return all same-color connected groups in stable row-major order."""

    board_size = int(len(board))
    target_color = int(color)
    if target_color == int(EMPTY):
        raise ValueError("stone_groups requires a non-empty stone color")
    seen: Set[Coord] = set()
    groups: List[Tuple[Coord, ...]] = []
    for row in range(board_size):
        for col in range(board_size):
            coord = (int(row), int(col))
            if coord in seen or int(board[row][col]) != int(target_color):
                continue
            group = connected_group(board, coord)
            seen.update(group)
            groups.append(tuple(sorted(group)))
    return tuple(sorted(groups, key=lambda group: group[0] if group else (9999, 9999)))


def stone_group_representative_coords(
    board: Sequence[Sequence[int]],
    *,
    color: int,
) -> Tuple[Coord, ...]:
    """Return one deterministic representative coordinate for each same-color group."""

    return tuple(group[0] for group in stone_groups(board, color=int(color)) if group)


def liberty_point_ids(liberties: Iterable[Coord]) -> Tuple[str, ...]:
    """Return stable point ids for one liberty set."""

    return tuple(coord_to_point_id(coord) for coord in liberties)


def stone_ids_for_coords(coords: Iterable[Coord]) -> Tuple[str, ...]:
    """Return stable stone ids for occupied intersections."""

    return tuple(coord_to_stone_id(coord) for coord in coords)


def adjacent_enemy_coords(board: Sequence[Sequence[int]], group: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Return unique opponent stones orthogonally adjacent to one group."""

    group_tuple = tuple((int(coord[0]), int(coord[1])) for coord in group)
    if not group_tuple:
        return tuple()
    first_row, first_col = group_tuple[0]
    group_color = int(board[int(first_row)][int(first_col)])
    if int(group_color) == int(EMPTY):
        return tuple()
    enemy_color = int(opponent(group_color))
    board_size = int(len(board))
    enemies: Set[Coord] = set()
    for coord in group_tuple:
        for neighbor in neighbors(coord, board_size=board_size):
            if int(board[neighbor[0]][neighbor[1]]) == int(enemy_color):
                enemies.add((int(neighbor[0]), int(neighbor[1])))
    return tuple(sorted(enemies))


def shared_liberty_coords(board: Sequence[Sequence[int]], group: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Return liberties of one group that also touch at least one opponent stone."""

    group_tuple = tuple((int(coord[0]), int(coord[1])) for coord in group)
    if not group_tuple:
        return tuple()
    first_row, first_col = group_tuple[0]
    group_color = int(board[int(first_row)][int(first_col)])
    if int(group_color) == int(EMPTY):
        return tuple()
    enemy_color = int(opponent(group_color))
    board_size = int(len(board))
    shared: Set[Coord] = set()
    for liberty in group_liberties(board, group_tuple):
        for neighbor in neighbors(liberty, board_size=board_size):
            if int(board[neighbor[0]][neighbor[1]]) == int(enemy_color):
                shared.add((int(liberty[0]), int(liberty[1])))
                break
    return tuple(sorted(shared))


def supported_targets_for_mode(count_mode: str = "marked_group_liberty_count") -> Tuple[int, ...]:
    """Return supported count targets for one Go group-property query."""

    variant = str(count_mode)
    if variant in {"marked_black_group_liberty_count", "marked_white_group_liberty_count"}:
        variant = "marked_group_liberty_count"
    if variant == "marked_group_liberty_count":
        return (1, 2, 3, 4, 6)
    if variant == "marked_group_adjacent_enemy_count":
        return (1, 2, 3, 4, 5, 6)
    if variant == "marked_group_shared_liberty_count":
        return (1, 2, 3, 4, 5)
    if variant in {"black_stone_group_count", "white_stone_group_count"}:
        return tuple(range(1, 9))
    raise ValueError(f"unsupported Go count mode: {count_mode}")


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


def _minimum_group_size_for_adjacent_enemies(target_answer: int) -> int:
    """Return a small group size likely to expose enough boundary enemy slots."""

    return max(2, int(math.ceil((float(target_answer) - 2.0) / 2.0)))


def _minimum_group_size_for_shared_liberties(target_answer: int) -> int:
    """Return a small group size likely to expose enough shared-liberty slots."""

    return max(2, int(math.ceil((float(target_answer) + 1.0) / 2.0)))


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


def _can_place_separate_target_group(
    rows: Sequence[Sequence[int]],
    group: Iterable[Coord],
    *,
    target_color: int,
    board_size: int,
) -> bool:
    """Return whether a sampled group can be placed without joining existing target groups."""

    group_set = {(int(row), int(col)) for row, col in group}
    if not group_set:
        return False
    for row, col in group_set:
        if int(rows[int(row)][int(col)]) != int(EMPTY):
            return False
    for row, col in group_set:
        for neighbor in neighbors((int(row), int(col)), board_size=int(board_size)):
            if neighbor not in group_set and int(rows[neighbor[0]][neighbor[1]]) == int(target_color):
                return False
    return True


def _stone_group_size_max_for_target_count(target_answer: int) -> int:
    """Return a readable target-group size cap for one requested component count."""

    target = int(target_answer)
    if target >= 7:
        return 1
    if target >= 5:
        return 2
    return 4


def build_go_stone_group_count_state(
    *,
    rng,
    count_mode: str,
    scene_variant: str,
    target_answer: int,
    board_size: int = BOARD_SIZE,
    max_internal_attempts: int = 1024,
) -> GoStoneGroupCountState:
    """Construct one visible Go board with an exact same-color group count."""

    target = int(target_answer)
    if int(board_size) < 5:
        raise ValueError("Go group-count boards require board_size >= 5")
    variant = str(count_mode)
    if variant == "black_stone_group_count":
        target_color = int(BLACK)
    elif variant == "white_stone_group_count":
        target_color = int(WHITE)
    else:
        raise ValueError(f"unsupported Go group-count count mode: {count_mode}")
    if target not in supported_targets_for_mode(variant):
        raise ValueError(f"unsupported Go target {target} for {variant}")
    if str(scene_variant) not in {"open_board", "crowded_board"}:
        raise ValueError(f"unsupported Go scene variant: {scene_variant}")

    opponent_color = int(opponent(target_color))
    extras_min, extras_max = (4, 10) if str(scene_variant) == "open_board" else (10, 18)

    for _ in range(max(1, int(max_internal_attempts))):
        rows = [[int(EMPTY) for _ in range(int(board_size))] for _ in range(int(board_size))]
        group_size_max = _stone_group_size_max_for_target_count(int(target))
        placed_groups: List[Tuple[Coord, ...]] = []
        failed = False
        for _group_index in range(int(target)):
            group: Tuple[Coord, ...] = tuple()
            for _placement_attempt in range(192):
                group_size = int(rng.randint(1, int(group_size_max)))
                candidate = _sample_connected_group(
                    rng,
                    board_size=int(board_size),
                    size=int(group_size),
                    favor_center=False,
                )
                if not _can_place_separate_target_group(
                    rows,
                    candidate,
                    target_color=int(target_color),
                    board_size=int(board_size),
                ):
                    continue
                group = tuple(sorted(candidate))
                break
            if not group:
                failed = True
                break
            for row, col in group:
                rows[int(row)][int(col)] = int(target_color)
            placed_groups.append(group)
        if failed:
            continue

        board = _board_from_rows(rows)
        if len(stone_groups(board, color=int(target_color))) != int(target):
            continue
        if not all_groups_have_liberty(board):
            continue

        empty_coords = [
            (int(row), int(col))
            for row in range(int(board_size))
            for col in range(int(board_size))
            if int(board[row][col]) == int(EMPTY)
        ]
        rng.shuffle(empty_coords)
        extras_target = int(rng.randint(int(extras_min), int(extras_max)))
        mutable_rows = [list(int(cell) for cell in row) for row in board]
        extras_added = 0
        for row, col in empty_coords:
            if extras_added >= int(extras_target):
                break
            mutable_rows[int(row)][int(col)] = int(opponent_color)
            candidate_board = _board_from_rows(mutable_rows)
            if len(stone_groups(candidate_board, color=int(target_color))) != int(target):
                mutable_rows[int(row)][int(col)] = int(EMPTY)
                continue
            if not all_groups_have_liberty(candidate_board):
                mutable_rows[int(row)][int(col)] = int(EMPTY)
                continue
            extras_added += 1

        board = _board_from_rows(mutable_rows)
        target_groups = stone_groups(board, color=int(target_color))
        if len(target_groups) != int(target):
            continue
        representatives = stone_group_representative_coords(board, color=int(target_color))
        if len(representatives) != int(target):
            continue
        if not all_groups_have_liberty(board):
            continue

        return GoStoneGroupCountState(
            board=board,
            target_color=int(target_color),
            target_group_coords=tuple(tuple(group) for group in target_groups),
            representative_coords=tuple(representatives),
            stone_specs=_stone_specs(board, marked_group_coords=()),
            scene_variant=str(scene_variant),
        )

    raise RuntimeError(
        f"failed to construct a visible Go board with target {target} for {count_mode}/{scene_variant}"
    )


def build_go_board_state(
    *,
    rng,
    count_mode: str,
    scene_variant: str,
    target_answer: int,
    player_color: str | None = None,
    board_size: int = BOARD_SIZE,
    max_internal_attempts: int = 512,
) -> GoBoardState:
    """Construct one visible Go board with a marked group and exact query answer."""

    target = int(target_answer)
    if int(board_size) < 5:
        raise ValueError("Go liberty boards require board_size >= 5")
    variant = str(count_mode)
    if variant == "marked_black_group_liberty_count":
        variant = "marked_group_liberty_count"
        player_color = "black"
    elif variant == "marked_white_group_liberty_count":
        variant = "marked_group_liberty_count"
        player_color = "white"
    if variant not in {
        "marked_group_liberty_count",
        "marked_group_adjacent_enemy_count",
        "marked_group_shared_liberty_count",
    }:
        raise ValueError(f"unsupported Go count mode: {count_mode}")
    if target not in supported_targets_for_mode(variant):
        raise ValueError(f"unsupported Go target {target} for {variant}")
    color = str(player_color or "black")
    if color not in SUPPORTED_GO_PLAYER_COLORS:
        raise ValueError(f"unsupported Go player_color: {player_color}")
    if str(scene_variant) not in {"open_board", "crowded_board"}:
        raise ValueError(f"unsupported Go scene variant: {scene_variant}")

    marked_group_color = int(BLACK if color == "black" else WHITE)
    opponent_color = int(opponent(marked_group_color))
    extras_min, extras_max = (4, 10) if str(scene_variant) == "open_board" else (12, 20)

    for _ in range(max(1, int(max_internal_attempts))):
        if variant == "marked_group_adjacent_enemy_count":
            group_size_min = _minimum_group_size_for_adjacent_enemies(int(target))
            group_size_max = min(8, int(group_size_min) + 3)
            group_size = int(rng.randint(int(group_size_min), int(group_size_max)))
            favor_center = bool(int(target) >= 6)
        elif variant == "marked_group_shared_liberty_count":
            group_size_min = _minimum_group_size_for_shared_liberties(int(target))
            group_size_max = min(8, int(group_size_min) + 3)
            group_size = int(rng.randint(int(group_size_min), int(group_size_max)))
            favor_center = True
        else:
            group_size_min = _minimum_group_size_for_target(int(target))
            group_size_max = min(6, int(group_size_min) + 2)
            group_size = int(rng.randint(int(group_size_min), int(group_size_max)))
            favor_center = bool(int(target) >= 6)
        group = _sample_connected_group(
            rng,
            board_size=int(board_size),
            size=int(group_size),
            favor_center=bool(favor_center),
        )
        if not group:
            continue
        boundary = _boundary_neighbors(group, board_size=int(board_size))
        if variant == "marked_group_liberty_count":
            if len(boundary) < int(target):
                continue
            liberties = tuple(sorted(boundary[index] for index in rng.sample(range(len(boundary)), int(target))))
            enemy_boundary = tuple(sorted(coord for coord in boundary if coord not in set(liberties)))
        elif variant == "marked_group_adjacent_enemy_count":
            if len(boundary) <= int(target):
                continue
            enemy_boundary = tuple(sorted(boundary[index] for index in rng.sample(range(len(boundary)), int(target))))
            enemy_set = set(enemy_boundary)
            liberties = tuple(sorted(coord for coord in boundary if coord not in enemy_set))
        else:
            if len(boundary) < int(target):
                continue
            liberties = tuple(sorted(boundary))
            shared_targets = tuple(sorted(boundary[index] for index in rng.sample(range(len(boundary)), int(target))))
            enemy_boundary = tuple()

        liberty_set = set(liberties)
        enemy_boundary_set = set(enemy_boundary)
        rows = [[int(EMPTY) for _ in range(int(board_size))] for _ in range(int(board_size))]
        for row, col in group:
            rows[int(row)][int(col)] = int(marked_group_color)
        for row, col in boundary:
            if (int(row), int(col)) in enemy_boundary_set:
                rows[int(row)][int(col)] = int(opponent_color)
        if variant == "marked_group_shared_liberty_count":
            used_marker_cells: Set[Coord] = set()
            for liberty in shared_targets:
                marker_candidates = [
                    coord
                    for coord in neighbors(liberty, board_size=int(board_size))
                    if coord not in set(group)
                    and coord not in liberty_set
                    and coord not in used_marker_cells
                ]
                if not marker_candidates:
                    break
                marker = marker_candidates[int(rng.randrange(len(marker_candidates)))]
                rows[int(marker[0])][int(marker[1])] = int(opponent_color)
                used_marker_cells.add((int(marker[0]), int(marker[1])))
            if len(used_marker_cells) != int(target):
                continue
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
            candidate_group = connected_group(candidate_board, group[0])
            if set(candidate_group) != set(group):
                mutable_rows[int(row)][int(col)] = int(EMPTY)
                continue
            if variant == "marked_group_shared_liberty_count":
                if tuple(sorted(group_liberties(candidate_board, candidate_group))) != tuple(sorted(liberties)):
                    mutable_rows[int(row)][int(col)] = int(EMPTY)
                    continue
                if len(shared_liberty_coords(candidate_board, candidate_group)) != int(target):
                    mutable_rows[int(row)][int(col)] = int(EMPTY)
                    continue
            extras_added += 1
        board = _board_from_rows(mutable_rows)
        marked_group = connected_group(board, group[0])
        liberties_now = group_liberties(board, marked_group)
        adjacent_enemies_now = adjacent_enemy_coords(board, marked_group)
        shared_liberties_now = shared_liberty_coords(board, marked_group)
        if set(marked_group) != set(group):
            continue
        if variant == "marked_group_liberty_count" and len(liberties_now) != int(target):
            continue
        if variant == "marked_group_adjacent_enemy_count" and len(adjacent_enemies_now) != int(target):
            continue
        if variant == "marked_group_shared_liberty_count" and len(shared_liberties_now) != int(target):
            continue
        if variant != "marked_group_adjacent_enemy_count" and tuple(sorted(liberties_now)) != tuple(sorted(liberties)):
            continue

        return GoBoardState(
            board=board,
            marked_group_color=int(marked_group_color),
            marked_group_coords=tuple(sorted(marked_group)),
            liberty_coords=tuple(sorted(liberties_now)),
            adjacent_enemy_coords=tuple(sorted(adjacent_enemies_now)),
            shared_liberty_coords=tuple(sorted(shared_liberties_now)),
            stone_specs=_stone_specs(board, marked_group_coords=marked_group),
            scene_variant=str(scene_variant),
        )

    raise RuntimeError(
        f"failed to construct a visible Go board with target {target} for {count_mode}/{color}/{scene_variant}"
    )


__all__ = [
    "BLACK",
    "BOARD_SIZE",
    "Board",
    "Coord",
    "EMPTY",
    "GoBoardState",
    "GoStoneGroupCountState",
    "GoStoneSpec",
    "SUPPORTED_GO_PLAYER_COLORS",
    "WHITE",
    "adjacent_enemy_coords",
    "all_groups_have_liberty",
    "build_go_board_state",
    "build_go_stone_group_count_state",
    "color_name",
    "connected_group",
    "coord_to_point_id",
    "coord_to_stone_id",
    "group_liberties",
    "liberty_point_ids",
    "neighbors",
    "opponent",
    "shared_liberty_coords",
    "stone_ids_for_coords",
    "stone_group_representative_coords",
    "stone_groups",
    "supported_targets_for_mode",
]
