"""Logic-grid board construction and validation rules."""

from __future__ import annotations

from typing import List, Sequence, Tuple


def build_row_uniqueness_board(symbol_pool: Sequence[str], *, rng) -> List[List[str]]:
    """Build rows where each row is a permutation of the visible symbols."""

    symbols = [str(value) for value in symbol_pool]
    rows: List[List[str]] = []
    for _ in range(len(symbols)):
        row = list(symbols)
        rng.shuffle(row)
        rows.append([str(value) for value in row])
    return rows


def build_column_uniqueness_board(symbol_pool: Sequence[str], *, rng) -> List[List[str]]:
    """Build columns where each column is a permutation of the symbols."""

    symbols = [str(value) for value in symbol_pool]
    columns: List[List[str]] = []
    for _ in range(len(symbols)):
        column = list(symbols)
        rng.shuffle(column)
        columns.append([str(value) for value in column])
    board_size = len(symbols)
    return [
        [str(columns[col_index][row_index]) for col_index in range(board_size)]
        for row_index in range(board_size)
    ]


def build_row_and_column_uniqueness_board(symbol_pool: Sequence[str], *, rng) -> List[List[str]]:
    """Build a Latin-style board with each symbol once per row and column."""

    symbols = [str(value) for value in symbol_pool]
    board_size = len(symbols)
    row_shift_order = list(range(board_size))
    col_permutation = list(range(board_size))
    symbol_permutation = list(symbols)
    rng.shuffle(row_shift_order)
    rng.shuffle(col_permutation)
    rng.shuffle(symbol_permutation)
    return [
        [
            str(symbol_permutation[(row_shift_order[row_index] + col_permutation[col_index]) % board_size])
            for col_index in range(board_size)
        ]
        for row_index in range(board_size)
    ]


def king_neighbor_coords(board_size: int, row_index: int, col_index: int) -> List[Tuple[int, int]]:
    """Return all in-bounds king-move neighbors for one board cell."""

    neighbors: List[Tuple[int, int]] = []
    for delta_row in (-1, 0, 1):
        for delta_col in (-1, 0, 1):
            if int(delta_row) == 0 and int(delta_col) == 0:
                continue
            nbr_row = int(row_index + delta_row)
            nbr_col = int(col_index + delta_col)
            if 0 <= nbr_row < int(board_size) and 0 <= nbr_col < int(board_size):
                neighbors.append((int(nbr_row), int(nbr_col)))
    return neighbors


def king_neighbor_symbol_set(
    board_values: Sequence[Sequence[str | None]],
    *,
    row_index: int,
    col_index: int,
) -> set[str]:
    """Return assigned neighboring symbols around one cell."""

    board_size = int(len(board_values))
    seen: set[str] = set()
    for nbr_row, nbr_col in king_neighbor_coords(board_size, int(row_index), int(col_index)):
        value = board_values[int(nbr_row)][int(nbr_col)]
        if value is not None:
            seen.add(str(value))
    return seen


def allowed_king_symbols(
    board_values: Sequence[Sequence[str | None]],
    *,
    row_index: int,
    col_index: int,
    symbol_pool: Sequence[str],
) -> List[str]:
    """Return symbols that preserve the king-neighbor non-touch rule."""

    blocked = king_neighbor_symbol_set(
        board_values,
        row_index=int(row_index),
        col_index=int(col_index),
    )
    return [str(symbol) for symbol in symbol_pool if str(symbol) not in blocked]


def fill_board_with_king_non_touch(
    board_values: List[List[str | None]],
    *,
    symbol_pool: Sequence[str],
    rng,
) -> bool:
    """Backtrack-fill remaining cells under the king-neighbor rule."""

    pending: List[Tuple[int, int, List[str]]] = []
    for row_index, row in enumerate(board_values):
        for col_index, value in enumerate(row):
            if value is not None:
                continue
            allowed = allowed_king_symbols(
                board_values,
                row_index=int(row_index),
                col_index=int(col_index),
                symbol_pool=symbol_pool,
            )
            if not allowed:
                return False
            pending.append((int(row_index), int(col_index), list(allowed)))
    if not pending:
        return True

    row_index, col_index, allowed = min(
        pending,
        key=lambda item: (len(item[2]), item[0], item[1]),
    )
    rng.shuffle(allowed)
    for symbol in allowed:
        board_values[int(row_index)][int(col_index)] = str(symbol)
        if fill_board_with_king_non_touch(
            board_values,
            symbol_pool=symbol_pool,
            rng=rng,
        ):
            return True
        board_values[int(row_index)][int(col_index)] = None
    return False
