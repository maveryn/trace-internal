"""Shared Connect Four rules helpers for games-domain tasks."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple


EMPTY = 0
RED = 1
YELLOW = -1
ROWS = 6
COLUMNS = 7
_DIRECTIONS: Tuple[Tuple[int, int], ...] = (
    (0, 1),
    (1, 0),
    (1, 1),
    (1, -1),
)

Coord = Tuple[int, int]
Board = Tuple[Tuple[int, ...], ...]


def player_name(player: int) -> str:
    """Return the prompt-facing player name for one disc value."""

    return "Red" if int(player) == int(RED) else "Yellow"


def opponent(player: int) -> int:
    """Return the opposite Connect Four player value."""

    return int(YELLOW if int(player) == int(RED) else RED)


def coord_to_cell_id(coord: Coord) -> str:
    """Return one stable scene-entity id for a board coordinate."""

    return f"cell_r{int(coord[0])}_c{int(coord[1])}"


def empty_board() -> Board:
    """Return one empty standard Connect Four board."""

    return tuple(tuple(int(EMPTY) for _ in range(COLUMNS)) for _ in range(ROWS))


def _in_bounds(row: int, col: int) -> bool:
    """Return whether one coordinate lies on the standard board."""

    return 0 <= int(row) < ROWS and 0 <= int(col) < COLUMNS


def legal_drop_rows(board: Sequence[Sequence[int]]) -> Dict[int, int]:
    """Return the landing row for each non-full column."""

    landing_rows: Dict[int, int] = {}
    for col in range(COLUMNS):
        for row in range(ROWS - 1, -1, -1):
            if int(board[row][col]) == int(EMPTY):
                landing_rows[int(col)] = int(row)
                break
    return landing_rows


def drop_disc(board: Sequence[Sequence[int]], player: int, col: int) -> Tuple[Board, Coord]:
    """Return the board after dropping one disc into one legal column."""

    landing_rows = legal_drop_rows(board)
    column = int(col)
    if int(column) not in landing_rows:
        raise ValueError(f"column {column} is full")
    row = int(landing_rows[int(column)])
    next_rows = [list(int(cell) for cell in current_row) for current_row in board]
    next_rows[int(row)][int(column)] = int(player)
    return tuple(tuple(int(cell) for cell in current_row) for current_row in next_rows), (int(row), int(column))


def occupied_cell_count(board: Sequence[Sequence[int]]) -> int:
    """Return the total number of non-empty cells on the board."""

    return sum(1 for row in board for cell in row if int(cell) != int(EMPTY))


def completed_lines_for_cell(board: Sequence[Sequence[int]], player: int, coord: Coord) -> Tuple[Tuple[Coord, ...], ...]:
    """Return every distinct connect-four line for one player that includes one cell."""

    row = int(coord[0])
    col = int(coord[1])
    if not _in_bounds(int(row), int(col)) or int(board[row][col]) != int(player):
        return tuple()

    lines: List[Tuple[Coord, ...]] = []
    seen = set()
    for row_delta, col_delta in _DIRECTIONS:
        backward: List[Coord] = []
        scan_row = int(row - row_delta)
        scan_col = int(col - col_delta)
        while _in_bounds(scan_row, scan_col) and int(board[scan_row][scan_col]) == int(player):
            backward.append((int(scan_row), int(scan_col)))
            scan_row -= int(row_delta)
            scan_col -= int(col_delta)
        forward: List[Coord] = []
        scan_row = int(row + row_delta)
        scan_col = int(col + col_delta)
        while _in_bounds(scan_row, scan_col) and int(board[scan_row][scan_col]) == int(player):
            forward.append((int(scan_row), int(scan_col)))
            scan_row += int(row_delta)
            scan_col += int(col_delta)
        ordered = list(reversed(backward)) + [(int(row), int(col))] + forward
        center_index = len(backward)
        start_min = max(0, int(center_index) - 3)
        start_max = min(int(center_index), len(ordered) - 4)
        for start in range(start_min, start_max + 1):
            segment = tuple(ordered[int(start) : int(start) + 4])
            if tuple(segment) in seen:
                continue
            seen.add(tuple(segment))
            lines.append(tuple(segment))
    return tuple(lines)


def has_connect_four(board: Sequence[Sequence[int]], player: int) -> bool:
    """Return whether one player already has a completed line on the board."""

    for row in range(ROWS):
        for col in range(COLUMNS):
            if int(board[row][col]) != int(player):
                continue
            if completed_lines_for_cell(board, int(player), (int(row), int(col))):
                return True
    return False


def winning_drop_map(board: Sequence[Sequence[int]], player: int) -> Dict[int, Tuple[Coord, Tuple[Tuple[Coord, ...], ...]]]:
    """Return every legal column whose drop wins immediately for one player."""

    winning: Dict[int, Tuple[Coord, Tuple[Tuple[Coord, ...], ...]]] = {}
    for col, row in legal_drop_rows(board).items():
        next_board, landing_coord = drop_disc(board, int(player), int(col))
        completed = completed_lines_for_cell(next_board, int(player), landing_coord)
        if completed:
            winning[int(col)] = (landing_coord, completed)
    return winning


__all__ = [
    "Board",
    "COLUMNS",
    "Coord",
    "EMPTY",
    "RED",
    "ROWS",
    "YELLOW",
    "completed_lines_for_cell",
    "coord_to_cell_id",
    "drop_disc",
    "empty_board",
    "has_connect_four",
    "legal_drop_rows",
    "occupied_cell_count",
    "opponent",
    "player_name",
    "winning_drop_map",
]
