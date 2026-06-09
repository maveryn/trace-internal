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
SUPPORTED_BINGO_QUERY_IDS: Tuple[str, ...] = (
    "completed_axis_line_count",
    "line_sum_extremum_value",
    "near_complete_row_count",
    "near_complete_column_count",
    "called_marked_number_count",
)
SUPPORTED_BINGO_LINE_AXES: Tuple[str, ...] = ("row", "column")
SUPPORTED_BINGO_EXTREMA: Tuple[str, ...] = ("max", "min")


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
    near_complete_row_indices: Tuple[int, ...] = ()
    near_complete_column_indices: Tuple[int, ...] = ()
    near_complete_gap_cell_ids: Tuple[str, ...] = ()
    called_numbers: Tuple[int, ...] = ()
    called_number_cell_ids: Tuple[str, ...] = ()
    called_marked_cell_ids: Tuple[str, ...] = ()
    line_sum_extremum: str | None = None
    line_sum_target_axis: str | None = None
    line_sum_target_line_index: int | None = None
    line_sum_target_cell_ids: Tuple[str, ...] = ()
    line_sum_target_value: int | None = None
    completed_line_sums: Tuple[Tuple[str, int, int], ...] = ()


def build_bingo_number_grid(rng) -> Tuple[Tuple[int, ...], ...]:
    """Return one `5 x 5` visible bingo number grid with realistic column ranges."""

    columns: List[List[int]] = []
    for start, end in BINGO_COLUMN_RANGES:
        sampled = [int(value) for value in rng.sample(range(int(start), int(end) + 1), BINGO_BOARD_SIZE)]
        rng.shuffle(sampled)
        columns.append(sampled)
    return tuple(
        tuple(int(columns[column_index][row_index]) for column_index in range(BINGO_BOARD_SIZE))
        for row_index in range(BINGO_BOARD_SIZE)
    )


def _build_row_count_marks(
    *,
    rng,
    target_answer: int,
    distractor_mark_prob: float,
) -> Tuple[Tuple[bool, ...], ...]:
    """Return a mark grid with exactly `target_answer` completed rows."""

    completed_rows = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), int(target_answer)))
    marks: List[List[bool]] = [[False] * BINGO_BOARD_SIZE for _ in range(BINGO_BOARD_SIZE)]
    for row_index in range(BINGO_BOARD_SIZE):
        if row_index in completed_rows:
            marks[row_index] = [True] * BINGO_BOARD_SIZE
            continue
        gap_column = int(rng.randrange(BINGO_BOARD_SIZE))
        row_marks = [bool(rng.random() < float(distractor_mark_prob)) for _ in range(BINGO_BOARD_SIZE)]
        row_marks[gap_column] = False
        marks[row_index] = row_marks
    return tuple(tuple(bool(value) for value in row) for row in marks)


def _build_column_count_marks(
    *,
    rng,
    target_answer: int,
    distractor_mark_prob: float,
) -> Tuple[Tuple[bool, ...], ...]:
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
            marks[row_index][column_index] = bool(rng.random() < float(distractor_mark_prob))
    return tuple(tuple(bool(value) for value in row) for row in marks)


def _build_near_complete_row_marks(
    *,
    rng,
    target_answer: int,
    distractor_mark_prob: float,
) -> Tuple[Tuple[bool, ...], ...]:
    """Return a mark grid with exactly `target_answer` near-complete rows."""

    target_rows = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), int(target_answer)))
    marks: List[List[bool]] = [[False] * BINGO_BOARD_SIZE for _ in range(BINGO_BOARD_SIZE)]
    for row_index in range(BINGO_BOARD_SIZE):
        if row_index in target_rows:
            gap_column = int(rng.randrange(BINGO_BOARD_SIZE))
            row_marks = [True] * BINGO_BOARD_SIZE
            row_marks[gap_column] = False
            marks[row_index] = row_marks
            continue
        false_count = int(rng.randint(2, BINGO_BOARD_SIZE))
        false_columns = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), false_count))
        row_marks = [
            False if column_index in false_columns else bool(rng.random() < float(distractor_mark_prob))
            for column_index in range(BINGO_BOARD_SIZE)
        ]
        if sum(1 for value in row_marks if not bool(value)) == 1:
            row_marks[int(rng.choice(tuple(false_columns)))] = False
        marks[row_index] = row_marks
    return tuple(tuple(bool(value) for value in row) for row in marks)


def _build_near_complete_column_marks(
    *,
    rng,
    target_answer: int,
    distractor_mark_prob: float,
) -> Tuple[Tuple[bool, ...], ...]:
    """Return a mark grid with exactly `target_answer` near-complete columns."""

    target_columns = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), int(target_answer)))
    marks: List[List[bool]] = [[False] * BINGO_BOARD_SIZE for _ in range(BINGO_BOARD_SIZE)]
    for column_index in range(BINGO_BOARD_SIZE):
        if column_index in target_columns:
            gap_row = int(rng.randrange(BINGO_BOARD_SIZE))
            for row_index in range(BINGO_BOARD_SIZE):
                marks[row_index][column_index] = row_index != gap_row
            continue
        false_count = int(rng.randint(2, BINGO_BOARD_SIZE))
        false_rows = set(int(value) for value in rng.sample(range(BINGO_BOARD_SIZE), false_count))
        for row_index in range(BINGO_BOARD_SIZE):
            if row_index in false_rows:
                marks[row_index][column_index] = False
            else:
                marks[row_index][column_index] = bool(rng.random() < float(distractor_mark_prob))
    return tuple(tuple(bool(value) for value in row) for row in marks)


def _build_called_number_mark_state(
    *,
    rng,
    numbers_grid: Sequence[Sequence[int]],
    target_answer: int,
    called_number_count: int,
    distractor_mark_prob: float,
) -> Tuple[Tuple[Tuple[bool, ...], ...], Tuple[int, ...], Tuple[str, ...], Tuple[str, ...]]:
    """Return marks and called-number metadata with an exact marked-called count."""

    called_count = int(called_number_count)
    answer = int(target_answer)
    if called_count < 1 or called_count > BINGO_BOARD_SIZE * BINGO_BOARD_SIZE:
        raise ValueError("called-number count must fit on the visible bingo card")
    if answer < 0 or answer > called_count:
        raise ValueError("called marked-number target must be between zero and called-number count")

    coordinates = [
        (int(row_index), int(column_index))
        for row_index in range(BINGO_BOARD_SIZE)
        for column_index in range(BINGO_BOARD_SIZE)
    ]
    called_coordinates = [tuple(value) for value in rng.sample(coordinates, called_count)]
    marked_called_coordinates = set(tuple(value) for value in rng.sample(called_coordinates, answer))
    called_coordinate_set = set(tuple(value) for value in called_coordinates)

    marks: List[List[bool]] = [[False] * BINGO_BOARD_SIZE for _ in range(BINGO_BOARD_SIZE)]
    forced_unmarked_coordinate: Tuple[int, int] | None = None
    non_called_coordinates = [coord for coord in coordinates if tuple(coord) not in called_coordinate_set]
    if answer == called_count and non_called_coordinates:
        forced_unmarked_coordinate = tuple(rng.choice(non_called_coordinates))

    for row_index, column_index in coordinates:
        coord = (int(row_index), int(column_index))
        if coord in called_coordinate_set:
            marks[row_index][column_index] = coord in marked_called_coordinates
        elif forced_unmarked_coordinate is not None and coord == forced_unmarked_coordinate:
            marks[row_index][column_index] = False
        else:
            marks[row_index][column_index] = bool(rng.random() < float(distractor_mark_prob))

    called_cell_ids = tuple(
        _cell_id(row_index=int(row_index), column_index=int(column_index))
        for row_index, column_index in called_coordinates
    )
    called_marked_cell_ids = tuple(
        _cell_id(row_index=int(row_index), column_index=int(column_index))
        for row_index, column_index in called_coordinates
        if (int(row_index), int(column_index)) in marked_called_coordinates
    )
    called_numbers = tuple(
        int(numbers_grid[int(row_index)][int(column_index)])
        for row_index, column_index in called_coordinates
    )
    return (
        tuple(tuple(bool(value) for value in row) for row in marks),
        tuple(int(value) for value in called_numbers),
        tuple(str(value) for value in called_cell_ids),
        tuple(str(value) for value in called_marked_cell_ids),
    )


def _cell_id(*, row_index: int, column_index: int) -> str:
    """Return the canonical bingo cell id for one grid coordinate."""

    return f"cell_r{int(row_index)}_c{int(column_index)}"


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


def _near_complete_rows(mark_grid: Sequence[Sequence[bool]]) -> Tuple[int, ...]:
    """Return row indices with exactly one unmarked cell."""

    return tuple(
        int(row_index)
        for row_index, row in enumerate(mark_grid)
        if sum(1 for value in row if not bool(value)) == 1
    )


def _near_complete_columns(mark_grid: Sequence[Sequence[bool]]) -> Tuple[int, ...]:
    """Return column indices with exactly one unmarked cell."""

    near_complete: List[int] = []
    for column_index in range(BINGO_BOARD_SIZE):
        unmarked_count = sum(
            1
            for row_index in range(BINGO_BOARD_SIZE)
            if not bool(mark_grid[row_index][column_index])
        )
        if int(unmarked_count) == 1:
            near_complete.append(int(column_index))
    return tuple(int(value) for value in near_complete)


def _near_complete_gap_cell_ids(
    *,
    mark_grid: Sequence[Sequence[bool]],
    line_axis: str,
    line_indices: Sequence[int],
) -> Tuple[str, ...]:
    """Return the single unmarked gap cell id for each near-complete line."""

    gap_ids: List[str] = []
    axis = str(line_axis)
    for line_index in line_indices:
        if axis == "row":
            gap_columns = [
                int(column_index)
                for column_index in range(BINGO_BOARD_SIZE)
                if not bool(mark_grid[int(line_index)][column_index])
            ]
            if len(gap_columns) != 1:
                raise ValueError("near-complete row annotation requires exactly one gap")
            gap_ids.append(_cell_id(row_index=int(line_index), column_index=int(gap_columns[0])))
        elif axis == "column":
            gap_rows = [
                int(row_index)
                for row_index in range(BINGO_BOARD_SIZE)
                if not bool(mark_grid[row_index][int(line_index)])
            ]
            if len(gap_rows) != 1:
                raise ValueError("near-complete column annotation requires exactly one gap")
            gap_ids.append(_cell_id(row_index=int(gap_rows[0]), column_index=int(line_index)))
        else:
            raise ValueError(f"unsupported bingo line axis: {line_axis}")
    return tuple(str(value) for value in gap_ids)


def _has_unmarked_cell(mark_grid: Sequence[Sequence[bool]]) -> bool:
    """Return true when the visible card retains at least one unmarked cell."""

    return any(not bool(value) for row in mark_grid for value in row)


def _completed_line_sums_for_axis(
    *,
    numbers_grid: Sequence[Sequence[int]],
    line_axis: str,
    completed_line_indices: Sequence[int],
) -> Tuple[Tuple[str, int, int], ...]:
    """Return `(axis, index, sum)` records for completed lines on one axis."""

    axis = str(line_axis)
    sums: List[Tuple[str, int, int]] = []
    for line_index in completed_line_indices:
        if axis == "row":
            value = sum(int(numbers_grid[int(line_index)][column_index]) for column_index in range(BINGO_BOARD_SIZE))
        elif axis == "column":
            value = sum(int(numbers_grid[row_index][int(line_index)]) for row_index in range(BINGO_BOARD_SIZE))
        else:
            raise ValueError(f"unsupported bingo line axis: {line_axis}")
        sums.append((axis, int(line_index), int(value)))
    return tuple(sums)


def _select_unique_line_sum_extremum(
    *,
    line_sums: Sequence[Tuple[str, int, int]],
    extremum: str,
) -> Tuple[str, int, int]:
    """Return the unique min/max line-sum record or raise if tied/missing."""

    if not line_sums:
        raise ValueError("line-sum extremum query requires at least one completed line")
    mode = str(extremum)
    if mode == "max":
        target_value = max(int(value) for _axis, _line_index, value in line_sums)
    elif mode == "min":
        target_value = min(int(value) for _axis, _line_index, value in line_sums)
    else:
        raise ValueError(f"unsupported bingo line-sum extremum: {extremum}")
    winners = [record for record in line_sums if int(record[2]) == int(target_value)]
    if len(winners) != 1:
        raise ValueError("line-sum extremum must be unique")
    return winners[0]


def build_bingo_card_state(
    *,
    rng,
    query_id: str,
    target_answer: int,
    line_axis: str | None = None,
    extremum: str | None = None,
    called_number_count: int | None = None,
    distractor_mark_prob: float = 0.45,
) -> BingoCardState:
    """Construct one bingo-card state that satisfies the requested completed-line count."""

    variant = str(query_id)
    if variant == "completed_row_count":
        variant = "completed_axis_line_count"
        line_axis = "row"
    elif variant == "completed_column_count":
        variant = "completed_axis_line_count"
        line_axis = "column"
    elif variant == "near_complete_row_count":
        line_axis = "row"
    elif variant == "near_complete_column_count":
        line_axis = "column"

    axis = str(line_axis or "row")
    mark_prob = max(0.0, min(1.0, float(distractor_mark_prob)))
    line_sum_extremum: str | None = None
    line_sum_target_axis: str | None = None
    line_sum_target_line_index: int | None = None
    line_sum_target_cell_ids: Tuple[str, ...] = ()
    line_sum_target_value: int | None = None
    completed_line_sums: Tuple[Tuple[str, int, int], ...] = ()
    called_numbers: Tuple[int, ...] = ()
    called_number_cell_ids: Tuple[str, ...] = ()
    called_marked_cell_ids: Tuple[str, ...] = ()
    numbers_grid: Tuple[Tuple[int, ...], ...] | None = None

    if variant == "completed_axis_line_count" and axis == "row":
        mark_grid = _build_row_count_marks(
            rng=rng,
            target_answer=int(target_answer),
            distractor_mark_prob=float(mark_prob),
        )
    elif variant == "completed_axis_line_count" and axis == "column":
        mark_grid = _build_column_count_marks(
            rng=rng,
            target_answer=int(target_answer),
            distractor_mark_prob=float(mark_prob),
        )
    elif variant == "line_sum_extremum_value" and axis == "row":
        line_sum_extremum = str(extremum or "max")
        mark_grid = _build_row_count_marks(
            rng=rng,
            target_answer=int(target_answer),
            distractor_mark_prob=float(mark_prob),
        )
    elif variant == "line_sum_extremum_value" and axis == "column":
        line_sum_extremum = str(extremum or "max")
        mark_grid = _build_column_count_marks(
            rng=rng,
            target_answer=int(target_answer),
            distractor_mark_prob=float(mark_prob),
        )
    elif variant == "near_complete_row_count":
        mark_grid = _build_near_complete_row_marks(
            rng=rng,
            target_answer=int(target_answer),
            distractor_mark_prob=float(mark_prob),
        )
    elif variant == "near_complete_column_count":
        mark_grid = _build_near_complete_column_marks(
            rng=rng,
            target_answer=int(target_answer),
            distractor_mark_prob=float(mark_prob),
        )
    elif variant == "called_marked_number_count":
        numbers_grid = build_bingo_number_grid(rng)
        (
            mark_grid,
            called_numbers,
            called_number_cell_ids,
            called_marked_cell_ids,
        ) = _build_called_number_mark_state(
            rng=rng,
            numbers_grid=numbers_grid,
            target_answer=int(target_answer),
            called_number_count=int(called_number_count or max(1, int(target_answer))),
            distractor_mark_prob=float(mark_prob),
        )
    else:
        raise ValueError(f"unsupported bingo query id: {query_id}")

    if numbers_grid is None:
        numbers_grid = build_bingo_number_grid(rng)
    completed_rows = _completed_rows(mark_grid)
    completed_columns = _completed_columns(mark_grid)
    near_complete_rows = _near_complete_rows(mark_grid)
    near_complete_columns = _near_complete_columns(mark_grid)
    near_complete_gap_cell_ids: Tuple[str, ...] = ()
    if not _has_unmarked_cell(mark_grid):
        raise ValueError("bingo card scenes require at least one unmarked cell")

    if variant == "completed_axis_line_count" and axis == "row" and len(completed_rows) != int(target_answer):
        raise ValueError("constructed bingo row-count scene drifted from the target answer")
    if variant == "completed_axis_line_count" and axis == "column" and len(completed_columns) != int(target_answer):
        raise ValueError("constructed bingo column-count scene drifted from the target answer")
    if variant == "near_complete_row_count":
        if len(near_complete_rows) != int(target_answer):
            raise ValueError("constructed bingo near-complete row scene drifted from the target answer")
        near_complete_gap_cell_ids = _near_complete_gap_cell_ids(
            mark_grid=mark_grid,
            line_axis="row",
            line_indices=near_complete_rows,
        )
    if variant == "near_complete_column_count":
        if len(near_complete_columns) != int(target_answer):
            raise ValueError("constructed bingo near-complete column scene drifted from the target answer")
        near_complete_gap_cell_ids = _near_complete_gap_cell_ids(
            mark_grid=mark_grid,
            line_axis="column",
            line_indices=near_complete_columns,
        )
    if variant == "called_marked_number_count":
        if len(called_marked_cell_ids) != int(target_answer):
            raise ValueError("constructed bingo called-number scene drifted from the target answer")
        if len(called_numbers) != int(called_number_count or max(1, int(target_answer))):
            raise ValueError("constructed bingo called-number scene drifted from the called-number count")
    if variant == "line_sum_extremum_value":
        if line_sum_extremum not in SUPPORTED_BINGO_EXTREMA:
            raise ValueError(f"unsupported bingo line-sum extremum: {line_sum_extremum}")
        completed_indices = completed_rows if axis == "row" else completed_columns
        if len(completed_indices) != int(target_answer):
            raise ValueError("line-sum scene drifted from the requested completed-line count")
        completed_line_sums = _completed_line_sums_for_axis(
            numbers_grid=numbers_grid,
            line_axis=str(axis),
            completed_line_indices=completed_indices,
        )
        selected_axis, selected_index, selected_value = _select_unique_line_sum_extremum(
            line_sums=completed_line_sums,
            extremum=str(line_sum_extremum),
        )
        line_sum_target_axis = str(selected_axis)
        line_sum_target_line_index = int(selected_index)
        line_sum_target_value = int(selected_value)
        if str(selected_axis) == "row":
            line_sum_target_cell_ids = tuple(
                _cell_id(row_index=int(selected_index), column_index=int(column_index))
                for column_index in range(BINGO_BOARD_SIZE)
            )
        else:
            line_sum_target_cell_ids = tuple(
                _cell_id(row_index=int(row_index), column_index=int(selected_index))
                for row_index in range(BINGO_BOARD_SIZE)
            )

    cells: List[BingoCellInstance] = []
    for row_index in range(BINGO_BOARD_SIZE):
        for column_index in range(BINGO_BOARD_SIZE):
            cells.append(
                BingoCellInstance(
                    cell_id=_cell_id(row_index=int(row_index), column_index=int(column_index)),
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
        near_complete_row_indices=tuple(int(value) for value in near_complete_rows),
        near_complete_column_indices=tuple(int(value) for value in near_complete_columns),
        near_complete_gap_cell_ids=tuple(str(value) for value in near_complete_gap_cell_ids),
        called_numbers=tuple(int(value) for value in called_numbers),
        called_number_cell_ids=tuple(str(value) for value in called_number_cell_ids),
        called_marked_cell_ids=tuple(str(value) for value in called_marked_cell_ids),
        line_sum_extremum=line_sum_extremum,
        line_sum_target_axis=line_sum_target_axis,
        line_sum_target_line_index=line_sum_target_line_index,
        line_sum_target_cell_ids=tuple(str(value) for value in line_sum_target_cell_ids),
        line_sum_target_value=line_sum_target_value,
        completed_line_sums=tuple(
            (str(axis_name), int(line_index), int(value))
            for axis_name, line_index, value in completed_line_sums
        ),
    )


def annotation_cell_ids_for_query(*, card_state: BingoCardState, query_id: str, line_axis: str | None = None) -> Tuple[str, ...]:
    """Return the canonical annotation cell ids for the active bingo query."""

    annotation_ids: List[str] = []
    completed_rows = set(int(value) for value in card_state.completed_row_indices)
    completed_columns = set(int(value) for value in card_state.completed_column_indices)
    variant = str(query_id)
    if variant == "completed_row_count":
        variant = "completed_axis_line_count"
        line_axis = "row"
    elif variant == "completed_column_count":
        variant = "completed_axis_line_count"
        line_axis = "column"
    elif variant == "near_complete_row_count":
        line_axis = "row"
    elif variant == "near_complete_column_count":
        line_axis = "column"
    axis = str(line_axis or "row")
    if variant == "line_sum_extremum_value":
        if not card_state.line_sum_target_cell_ids:
            raise ValueError("line-sum annotation requires target line cell ids")
        return tuple(str(value) for value in card_state.line_sum_target_cell_ids)
    if variant in {"near_complete_row_count", "near_complete_column_count"}:
        return tuple(str(value) for value in card_state.near_complete_gap_cell_ids)
    if variant == "called_marked_number_count":
        return tuple(str(value) for value in card_state.called_marked_cell_ids)

    for cell in card_state.cells:
        in_completed_row = int(cell.row_index) in completed_rows
        in_completed_column = int(cell.column_index) in completed_columns
        include = False
        if variant == "completed_axis_line_count" and axis == "row":
            include = bool(in_completed_row and cell.is_marked)
        elif variant == "completed_axis_line_count" and axis == "column":
            include = bool(in_completed_column and cell.is_marked)
        else:
            raise ValueError(f"unsupported bingo query id: {query_id}")
        if include:
            annotation_ids.append(str(cell.cell_id))
    return tuple(str(value) for value in annotation_ids)


__all__ = [
    "BINGO_BOARD_SIZE",
    "BINGO_COLUMN_LABELS",
    "BINGO_COLUMN_RANGES",
    "SUPPORTED_BINGO_EXTREMA",
    "SUPPORTED_BINGO_LINE_AXES",
    "SUPPORTED_BINGO_QUERY_IDS",
    "SUPPORTED_BINGO_SCENE_VARIANTS",
    "BingoCardState",
    "BingoCellInstance",
    "build_bingo_card_state",
    "build_bingo_number_grid",
    "annotation_cell_ids_for_query",
]
