"""Shared Sudoku construction helpers for puzzle-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple


SIZE = 9
BOX_SIZE = 3
DIGITS: Tuple[int, ...] = tuple(range(1, 10))
SUPPORTED_SUDOKU_QUERY_IDS: Tuple[str, ...] = (
    "marked_cell_value",
    "marked_cell_candidate_count",
    "unit_missing_digits_count",
    "repeated_digit_count",
)
SUPPORTED_SUDOKU_SCENE_VARIANTS: Tuple[str, ...] = (
    "sparse_grid",
    "filled_grid",
)
SUPPORTED_SUDOKU_UNIT_TYPES: Tuple[str, ...] = (
    "row",
    "column",
    "box",
)

Coord = Tuple[int, int]
Board = Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class SudokuSample:
    """One generated Sudoku-style board and query-specific witnesses."""

    board: Board
    solution: Board
    query_id: str
    answer: int
    annotation_coords: Tuple[Coord, ...]
    marked_cell: Coord | None
    highlighted_unit_type: str | None
    highlighted_unit_index: int | None
    repeated_digit_values: Tuple[int, ...]
    missing_digit_values: Tuple[int, ...]
    visible_count: int
    construction_mode: str


def coord_to_cell_id(coord: Coord) -> str:
    """Return the canonical visible-cell id for one Sudoku coordinate."""

    row, col = int(coord[0]), int(coord[1])
    return f"cell_r{row}_c{col}"


def unit_coords(unit_type: str, unit_index: int) -> Tuple[Coord, ...]:
    """Return coordinates for one row, column, or 3 by 3 box."""

    kind = str(unit_type)
    index = int(unit_index)
    if kind == "row":
        return tuple((index, col) for col in range(SIZE))
    if kind == "column":
        return tuple((row, index) for row in range(SIZE))
    if kind == "box":
        start_row = int(index // BOX_SIZE) * BOX_SIZE
        start_col = int(index % BOX_SIZE) * BOX_SIZE
        return tuple(
            (row, col)
            for row in range(start_row, start_row + BOX_SIZE)
            for col in range(start_col, start_col + BOX_SIZE)
        )
    raise ValueError(f"unsupported Sudoku unit_type: {unit_type}")


def box_index_for_coord(coord: Coord) -> int:
    """Return the 0-based 3 by 3 box index for one coordinate."""

    row, col = int(coord[0]), int(coord[1])
    return int(row // BOX_SIZE) * BOX_SIZE + int(col // BOX_SIZE)


def peer_coords(coord: Coord) -> Tuple[Coord, ...]:
    """Return every row, column, or box peer for one coordinate."""

    row, col = int(coord[0]), int(coord[1])
    peers = set(unit_coords("row", row))
    peers.update(unit_coords("column", col))
    peers.update(unit_coords("box", box_index_for_coord((row, col))))
    peers.discard((row, col))
    return tuple(sorted(peers))


def candidate_digits(board: Board, coord: Coord) -> Tuple[int, ...]:
    """Return valid candidate digits for one empty cell under standard Sudoku rules."""

    row, col = int(coord[0]), int(coord[1])
    if int(board[row][col]) != 0:
        return ()
    used = {
        int(board[r][c])
        for r, c in peer_coords((row, col))
        if int(board[r][c]) != 0
    }
    return tuple(digit for digit in DIGITS if int(digit) not in used)


def repeated_digits_in_unit(board: Board, *, unit_type: str, unit_index: int) -> Tuple[int, ...]:
    """Return sorted digit values that appear more than once in one visible unit."""

    counts: dict[int, int] = {}
    for row, col in unit_coords(str(unit_type), int(unit_index)):
        value = int(board[row][col])
        if value == 0:
            continue
        counts[value] = int(counts.get(value, 0)) + 1
    return tuple(sorted(digit for digit, count in counts.items() if int(count) > 1))


def missing_digits_in_unit(board: Board, *, unit_type: str, unit_index: int) -> Tuple[int, ...]:
    """Return sorted digit values that are absent from one visible unit."""

    visible = {
        int(board[row][col])
        for row, col in unit_coords(str(unit_type), int(unit_index))
        if int(board[row][col]) != 0
    }
    return tuple(digit for digit in DIGITS if int(digit) not in visible)


def freeze_board(board: Sequence[Sequence[int]]) -> Board:
    """Freeze a mutable 9 by 9 board into the canonical tuple form."""

    frozen = tuple(tuple(int(cell) for cell in row) for row in board)
    if len(frozen) != SIZE or any(len(row) != SIZE for row in frozen):
        raise ValueError("Sudoku board must be 9 by 9")
    return frozen


def mutable_empty_board() -> list[list[int]]:
    """Return one mutable empty Sudoku board."""

    return [[0 for _ in range(SIZE)] for _ in range(SIZE)]


def visible_cell_count(board: Board | Sequence[Sequence[int]]) -> int:
    """Return the number of non-empty cells on one board."""

    return sum(1 for row in board for cell in row if int(cell) != 0)


def _shuffled_groups(rng) -> list[int]:
    """Return a Sudoku-valid shuffled row/column ordering."""

    bands = list(range(BOX_SIZE))
    rng.shuffle(bands)
    order: list[int] = []
    for band in bands:
        offsets = list(range(BOX_SIZE))
        rng.shuffle(offsets)
        order.extend((int(band) * BOX_SIZE) + int(offset) for offset in offsets)
    return order


def build_sudoku_solution(rng) -> Board:
    """Build one fully solved Sudoku board by permuting a canonical pattern."""

    row_order = _shuffled_groups(rng)
    col_order = _shuffled_groups(rng)
    digits = list(DIGITS)
    rng.shuffle(digits)

    def pattern(row: int, col: int) -> int:
        return int((BOX_SIZE * (row % BOX_SIZE) + row // BOX_SIZE + col) % SIZE)

    return freeze_board(
        [
            [int(digits[pattern(row, col)]) for col in col_order]
            for row in row_order
        ]
    )


def coords_with_solution_value(solution: Board, digit: int) -> Tuple[Coord, ...]:
    """Return every coordinate whose solution digit equals `digit`."""

    target = int(digit)
    return tuple(
        (row, col)
        for row in range(SIZE)
        for col in range(SIZE)
        if int(solution[row][col]) == int(target)
    )


def add_random_solution_givens(
    *,
    rng,
    board: list[list[int]],
    solution: Board,
    excluded_coords: Iterable[Coord],
    target_visible_count: int,
) -> None:
    """Fill random empty cells from the solution until the requested visible count."""

    excluded = {(int(row), int(col)) for row, col in excluded_coords}
    candidates = [
        (row, col)
        for row in range(SIZE)
        for col in range(SIZE)
        if (row, col) not in excluded and int(board[row][col]) == 0
    ]
    rng.shuffle(candidates)
    for row, col in candidates:
        if visible_cell_count(board) >= int(target_visible_count):
            break
        board[row][col] = int(solution[row][col])


__all__ = [
    "BOX_SIZE",
    "DIGITS",
    "SIZE",
    "Board",
    "Coord",
    "SUPPORTED_SUDOKU_QUERY_IDS",
    "SUPPORTED_SUDOKU_SCENE_VARIANTS",
    "SUPPORTED_SUDOKU_UNIT_TYPES",
    "SudokuSample",
    "add_random_solution_givens",
    "box_index_for_coord",
    "build_sudoku_solution",
    "candidate_digits",
    "coord_to_cell_id",
    "coords_with_solution_value",
    "freeze_board",
    "missing_digits_in_unit",
    "mutable_empty_board",
    "peer_coords",
    "repeated_digits_in_unit",
    "unit_coords",
    "visible_cell_count",
]
