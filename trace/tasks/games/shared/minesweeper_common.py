"""Shared Minesweeper construction helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple


SUPPORTED_MINESWEEPER_QUERY_VARIANTS: Tuple[str, ...] = (
    "forced_mine_count",
    "forced_safe_count",
    "satisfied_clue_count",
)
SUPPORTED_MINESWEEPER_SCENE_VARIANTS: Tuple[str, ...] = (
    "open_grid",
    "mixed_grid",
)
Coord = Tuple[int, int]


@dataclass(frozen=True)
class MinesweeperSample:
    """One generated Minesweeper board and query-specific witnesses."""

    size: int
    query_variant: str
    answer: int | str
    mine_coords: Tuple[Coord, ...]
    revealed_coords: Tuple[Coord, ...]
    flagged_coords: Tuple[Coord, ...]
    hidden_coords: Tuple[Coord, ...]
    forced_mine_coords: Tuple[Coord, ...]
    forced_safe_coords: Tuple[Coord, ...]
    satisfied_clue_coords: Tuple[Coord, ...]
    unsatisfied_clue_coords: Tuple[Coord, ...]
    forcing_clue_coords: Tuple[Coord, ...]
    evidence_coords: Tuple[Coord, ...]
    target_answer: int | None
    distractor_hidden_count: int
    construction_mode: str


def coord_to_cell_id(coord: Coord) -> str:
    """Return the canonical visible-cell id for one Minesweeper coordinate."""

    row, col = int(coord[0]), int(coord[1])
    return f"cell_r{row}_c{col}"


def in_bounds(coord: Coord, *, size: int) -> bool:
    """Return whether one coordinate is inside the square board."""

    row, col = int(coord[0]), int(coord[1])
    return 0 <= row < int(size) and 0 <= col < int(size)


def neighbor_coords(coord: Coord, *, size: int) -> Tuple[Coord, ...]:
    """Return all 8-neighborhood coordinates for one cell."""

    row, col = int(coord[0]), int(coord[1])
    coords: list[Coord] = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if int(dr) == 0 and int(dc) == 0:
                continue
            candidate = (row + int(dr), col + int(dc))
            if in_bounds(candidate, size=int(size)):
                coords.append(candidate)
    return tuple(coords)


def clue_number(coord: Coord, *, mine_coords: Iterable[Coord], size: int) -> int:
    """Return the adjacent-mine clue number for one coordinate."""

    mines = {(int(row), int(col)) for row, col in mine_coords}
    return sum(1 for item in neighbor_coords(coord, size=int(size)) if item in mines)


def all_coords(*, size: int) -> Tuple[Coord, ...]:
    """Return all coordinates in row-major order."""

    return tuple((row, col) for row in range(int(size)) for col in range(int(size)))


def forced_cell_supports(
    *,
    size: int,
    mine_coords: Iterable[Coord],
    revealed_coords: Iterable[Coord],
    flagged_coords: Iterable[Coord],
    hidden_coords: Iterable[Coord],
    force_kind: str,
) -> Dict[Coord, Tuple[Coord, ...]]:
    """Return forced cell -> supporting clue coordinates for basic Minesweeper rules."""

    revealed = {(int(row), int(col)) for row, col in revealed_coords}
    flagged = {(int(row), int(col)) for row, col in flagged_coords}
    hidden = {(int(row), int(col)) for row, col in hidden_coords}
    mines = {(int(row), int(col)) for row, col in mine_coords}
    support: dict[Coord, set[Coord]] = {}
    for clue in sorted(revealed):
        number = clue_number(clue, mine_coords=mines, size=int(size))
        neighbors = set(neighbor_coords(clue, size=int(size)))
        adjacent_flags = neighbors & flagged
        adjacent_hidden = neighbors & hidden
        if not adjacent_hidden:
            continue
        remaining = int(number) - len(adjacent_flags)
        if remaining < 0:
            continue
        if str(force_kind) == "mine":
            if remaining == len(adjacent_hidden) and remaining > 0:
                for coord in adjacent_hidden:
                    support.setdefault(coord, set()).add(clue)
        elif str(force_kind) == "safe":
            if remaining == 0:
                for coord in adjacent_hidden:
                    support.setdefault(coord, set()).add(clue)
        else:
            raise ValueError(f"unsupported Minesweeper force_kind: {force_kind}")
    return {coord: tuple(sorted(clues)) for coord, clues in sorted(support.items())}


def forced_mine_supports(
    *,
    size: int,
    mine_coords: Iterable[Coord],
    revealed_coords: Iterable[Coord],
    flagged_coords: Iterable[Coord],
    hidden_coords: Iterable[Coord],
) -> Dict[Coord, Tuple[Coord, ...]]:
    """Return cells forced to be mines by basic revealed-number constraints."""

    return forced_cell_supports(
        size=int(size),
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
        hidden_coords=hidden_coords,
        force_kind="mine",
    )


def forced_safe_supports(
    *,
    size: int,
    mine_coords: Iterable[Coord],
    revealed_coords: Iterable[Coord],
    flagged_coords: Iterable[Coord],
    hidden_coords: Iterable[Coord],
) -> Dict[Coord, Tuple[Coord, ...]]:
    """Return cells forced to be safe by basic revealed-number constraints."""

    return forced_cell_supports(
        size=int(size),
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
        hidden_coords=hidden_coords,
        force_kind="safe",
    )


def adjacent_flag_count(coord: Coord, *, flagged_coords: Iterable[Coord], size: int) -> int:
    """Return the number of flagged neighbors around one cell."""

    flags = {(int(row), int(col)) for row, col in flagged_coords}
    return sum(1 for item in neighbor_coords(coord, size=int(size)) if item in flags)


def satisfied_clue_coords(
    *,
    size: int,
    mine_coords: Iterable[Coord],
    revealed_coords: Iterable[Coord],
    flagged_coords: Iterable[Coord],
) -> Tuple[Coord, ...]:
    """Return opened number cells whose clue exactly matches adjacent flags."""

    satisfied: list[Coord] = []
    for coord in sorted_coords(revealed_coords):
        clue = clue_number(coord, mine_coords=mine_coords, size=int(size))
        if int(clue) <= 0:
            continue
        if adjacent_flag_count(coord, flagged_coords=flagged_coords, size=int(size)) == int(clue):
            satisfied.append(coord)
    return tuple(satisfied)


def unsatisfied_clue_coords(
    *,
    size: int,
    mine_coords: Iterable[Coord],
    revealed_coords: Iterable[Coord],
    flagged_coords: Iterable[Coord],
) -> Tuple[Coord, ...]:
    """Return opened number cells whose clue still needs more adjacent flags."""

    unsatisfied: list[Coord] = []
    for coord in sorted_coords(revealed_coords):
        clue = clue_number(coord, mine_coords=mine_coords, size=int(size))
        if int(clue) <= 0:
            continue
        if adjacent_flag_count(coord, flagged_coords=flagged_coords, size=int(size)) < int(clue):
            unsatisfied.append(coord)
    return tuple(unsatisfied)


def clue_context_flags(*, clue_coords: Iterable[Coord], flagged_coords: Iterable[Coord], size: int) -> Tuple[Coord, ...]:
    """Return flagged cells adjacent to any supporting clue."""

    flags = {(int(row), int(col)) for row, col in flagged_coords}
    context: set[Coord] = set()
    for clue in clue_coords:
        context.update(set(neighbor_coords(clue, size=int(size))) & flags)
    return tuple(sorted(context))


def sorted_coords(coords: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Return canonical sorted coordinates."""

    return tuple(sorted((int(row), int(col)) for row, col in coords))


def validate_board_contract(
    *,
    size: int,
    mine_coords: Sequence[Coord],
    revealed_coords: Sequence[Coord],
    flagged_coords: Sequence[Coord],
    hidden_coords: Sequence[Coord],
) -> None:
    """Validate that one Minesweeper state is internally consistent."""

    all_set = set(all_coords(size=int(size)))
    mines = set(sorted_coords(mine_coords))
    revealed = set(sorted_coords(revealed_coords))
    flagged = set(sorted_coords(flagged_coords))
    hidden = set(sorted_coords(hidden_coords))
    if revealed & flagged or revealed & hidden or flagged & hidden:
        raise ValueError("Minesweeper state partitions overlap")
    if revealed | flagged | hidden != all_set:
        raise ValueError("Minesweeper state partitions do not cover the board")
    if not flagged <= mines:
        raise ValueError("Minesweeper flags must mark true mines")
    if mines & revealed:
        raise ValueError("Revealed Minesweeper cells cannot contain mines")
    if not (mines - flagged) <= hidden:
        raise ValueError("Unflagged Minesweeper mines must remain hidden")


__all__ = [
    "Coord",
    "MinesweeperSample",
    "SUPPORTED_MINESWEEPER_QUERY_VARIANTS",
    "SUPPORTED_MINESWEEPER_SCENE_VARIANTS",
    "adjacent_flag_count",
    "all_coords",
    "clue_context_flags",
    "clue_number",
    "coord_to_cell_id",
    "forced_mine_supports",
    "forced_safe_supports",
    "neighbor_coords",
    "satisfied_clue_coords",
    "sorted_coords",
    "unsatisfied_clue_coords",
    "validate_board_contract",
]
