"""Shared construction helpers for bingo-card games tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple


BINGO_COLUMN_LABELS: Tuple[str, ...] = ("B", "I", "N", "G", "O")
BINGO_COLUMN_RANGES: Tuple[Tuple[int, int], ...] = (
    (1, 15),
    (16, 30),
    (31, 45),
    (46, 60),
    (61, 75),
)
BINGO_BOARD_SIZE = 5
SUPPORTED_BINGO_SCENE_VARIANTS: Tuple[str, ...] = ("single_card",)
SUPPORTED_BINGO_QUERY_VARIANTS: Tuple[str, ...] = (
    "completed_row_count",
    "completed_column_count",
    "completed_straight_line_count",
)


@dataclass(frozen=True)
class BingoCellInstance:
    """One visible bingo cell before rendering."""

    cell_id: str
    row_index: int
    column_index: int
    column_label: str
    number: int
    is_marked: bool


@dataclass(frozen=True)
class BingoCardState:
    """One deterministic bingo-card state with numbers, marks, and completed lines."""

    cells: Tuple[BingoCellInstance, ...]
    numbers_grid: Tuple[Tuple[int, ...], ...]
    mark_grid: Tuple[Tuple[bool, ...], ...]
    completed_row_indices: Tuple[int, ...]
    completed_column_indices: Tuple[int, ...]


def build_bingo_number_grid(rng) -> Tuple[Tuple[int, ...], ...]:
    """Return one `5 x 5` visible bingo number grid with realistic column ranges."""

    columns: List[List[int]] = []
    for start, end in BINGO_COLUMN_RANGES:
        sampled = sorted(int(value) for value in rng.sample(range(int(start), int(end) + 1), BINGO_BOARD_SIZE))
        columns.append(sampled)
    return tuple(
        tuple(int(columns[column_index][row_index]) for column_index in range(BINGO_BOARD_SIZE))
        for row_index in range(BINGO_BOARD_SIZE)
    )


def _build_row_count_marks(*, rng, target_answer: int) -> Tuple[Tuple[bool, ...], ...]:
    """Return a mark grid with exactly `target_answer` completed rows."""

    completed_rows = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), int(target_answer)))
    marks: List[List[bool]] = [[False] * BINGO_BOARD_SIZE for _ in range(BINGO_BOARD_SIZE)]
    for row_index in range(BINGO_BOARD_SIZE):
        if row_index in completed_rows:
            marks[row_index] = [True] * BINGO_BOARD_SIZE
            continue
        gap_column = int(rng.randrange(BINGO_BOARD_SIZE))
        row_marks = [bool(rng.random() < 0.45) for _ in range(BINGO_BOARD_SIZE)]
        row_marks[gap_column] = False
        marks[row_index] = row_marks
    return tuple(tuple(bool(value) for value in row) for row in marks)


def _build_column_count_marks(*, rng, target_answer: int) -> Tuple[Tuple[bool, ...], ...]:
    """Return a mark grid with exactly `target_answer` completed columns."""

    completed_columns = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), int(target_answer)))
    marks: List[List[bool]] = [[False] * BINGO_BOARD_SIZE for _ in range(BINGO_BOARD_SIZE)]
    gap_rows = {
        column_index: int(rng.randrange(BINGO_BOARD_SIZE))
        for column_index in range(BINGO_BOARD_SIZE)
        if column_index not in completed_columns
    }
    for row_index in range(BINGO_BOARD_SIZE):
        for column_index in range(BINGO_BOARD_SIZE):
            if column_index in completed_columns:
                marks[row_index][column_index] = True
                continue
            if gap_rows[column_index] == row_index:
                marks[row_index][column_index] = False
                continue
            marks[row_index][column_index] = bool(rng.random() < 0.45)
    return tuple(tuple(bool(value) for value in row) for row in marks)


def _build_straight_line_marks(*, rng, target_answer: int) -> Tuple[Tuple[bool, ...], ...]:
    """Return a mark grid with exactly `target_answer` completed rows or columns."""

    target = int(target_answer)
    feasible_pairs = [
        (row_count, column_count)
        for row_count in range(0, BINGO_BOARD_SIZE)
        for column_count in range(0, BINGO_BOARD_SIZE)
        if int(row_count + column_count) == target
    ]
    if not feasible_pairs:
        raise ValueError(f"no feasible straight-line decomposition for target answer {target_answer}")
    completed_row_count, completed_column_count = rng.choice(feasible_pairs)
    completed_rows = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), int(completed_row_count)))
    completed_columns = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), int(completed_column_count)))
    marks: List[List[bool]] = [[False] * BINGO_BOARD_SIZE for _ in range(BINGO_BOARD_SIZE)]
    for row_index in range(BINGO_BOARD_SIZE):
        for column_index in range(BINGO_BOARD_SIZE):
            marks[row_index][column_index] = bool(
                int(row_index) in completed_rows or int(column_index) in completed_columns
            )
    return tuple(tuple(bool(value) for value in row) for row in marks)


def _completed_rows(mark_grid: Sequence[Sequence[bool]]) -> Tuple[int, ...]:
    """Return the indices of rows whose five cells are marked."""

    return tuple(
        int(row_index)
        for row_index, row in enumerate(mark_grid)
        if all(bool(value) for value in row)
    )


def _completed_columns(mark_grid: Sequence[Sequence[bool]]) -> Tuple[int, ...]:
    """Return the indices of columns whose five cells are marked."""

    completed: List[int] = []
    for column_index in range(BINGO_BOARD_SIZE):
        if all(bool(mark_grid[row_index][column_index]) for row_index in range(BINGO_BOARD_SIZE)):
            completed.append(int(column_index))
    return tuple(int(value) for value in completed)


def build_bingo_card_state(*, rng, query_variant: str, target_answer: int) -> BingoCardState:
    """Construct one bingo-card state that satisfies the requested completed-line count."""

    variant = str(query_variant)
    if variant == "completed_row_count":
        mark_grid = _build_row_count_marks(rng=rng, target_answer=int(target_answer))
    elif variant == "completed_column_count":
        mark_grid = _build_column_count_marks(rng=rng, target_answer=int(target_answer))
    elif variant == "completed_straight_line_count":
        mark_grid = _build_straight_line_marks(rng=rng, target_answer=int(target_answer))
    else:
        raise ValueError(f"unsupported bingo query variant: {query_variant}")

    numbers_grid = build_bingo_number_grid(rng)
    completed_rows = _completed_rows(mark_grid)
    completed_columns = _completed_columns(mark_grid)

    if variant == "completed_row_count" and len(completed_rows) != int(target_answer):
        raise ValueError("constructed bingo row-count scene drifted from the target answer")
    if variant == "completed_column_count" and len(completed_columns) != int(target_answer):
        raise ValueError("constructed bingo column-count scene drifted from the target answer")
    if variant == "completed_straight_line_count" and (len(completed_rows) + len(completed_columns)) != int(target_answer):
        raise ValueError("constructed bingo straight-line scene drifted from the target answer")

    cells: List[BingoCellInstance] = []
    for row_index in range(BINGO_BOARD_SIZE):
        for column_index in range(BINGO_BOARD_SIZE):
            cells.append(
                BingoCellInstance(
                    cell_id=f"cell_r{row_index}_c{column_index}",
                    row_index=int(row_index),
                    column_index=int(column_index),
                    column_label=str(BINGO_COLUMN_LABELS[column_index]),
                    number=int(numbers_grid[row_index][column_index]),
                    is_marked=bool(mark_grid[row_index][column_index]),
                )
            )
    return BingoCardState(
        cells=tuple(cells),
        numbers_grid=tuple(tuple(int(value) for value in row) for row in numbers_grid),
        mark_grid=tuple(tuple(bool(value) for value in row) for row in mark_grid),
        completed_row_indices=tuple(int(value) for value in completed_rows),
        completed_column_indices=tuple(int(value) for value in completed_columns),
    )


def evidence_cell_ids_for_query(*, card_state: BingoCardState, query_variant: str) -> Tuple[str, ...]:
    """Return the canonical evidence cell ids for the active bingo query."""

    evidence_ids: List[str] = []
    completed_rows = set(int(value) for value in card_state.completed_row_indices)
    completed_columns = set(int(value) for value in card_state.completed_column_indices)
    for cell in card_state.cells:
        in_completed_row = int(cell.row_index) in completed_rows
        in_completed_column = int(cell.column_index) in completed_columns
        include = False
        if str(query_variant) == "completed_row_count":
            include = bool(in_completed_row and cell.is_marked)
        elif str(query_variant) == "completed_column_count":
            include = bool(in_completed_column and cell.is_marked)
        elif str(query_variant) == "completed_straight_line_count":
            include = bool((in_completed_row or in_completed_column) and cell.is_marked)
        else:
            raise ValueError(f"unsupported bingo query variant: {query_variant}")
        if include:
            evidence_ids.append(str(cell.cell_id))
    return tuple(str(value) for value in evidence_ids)


__all__ = [
    "BINGO_BOARD_SIZE",
    "BINGO_COLUMN_LABELS",
    "BINGO_COLUMN_RANGES",
    "SUPPORTED_BINGO_QUERY_VARIANTS",
    "SUPPORTED_BINGO_SCENE_VARIANTS",
    "BingoCardState",
    "BingoCellInstance",
    "build_bingo_card_state",
    "build_bingo_number_grid",
    "evidence_cell_ids_for_query",
]
