"""Shared 2048 board mechanics for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Tuple


SIZE = 4
EMPTY = 0
Coord = Tuple[int, int]
Board = Tuple[Tuple[int, ...], ...]

SUPPORTED_2048_QUERY_IDS: Tuple[str, ...] = (
    "merge_count",
    "score_value",
    "max_tile_value",
    "move_result_board_label",
)
MOVE_RESULT_QUERY_IDS: Tuple[str, ...] = (
    "merge_count",
    "score_value",
    "max_tile_value",
)
SUPPORTED_2048_SCENE_VARIANTS: Tuple[str, ...] = ("standard_board",)
SUPPORTED_2048_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "dark",
    "paper",
    "neon",
    "pastel",
)
SUPPORTED_2048_DIRECTIONS: Tuple[str, ...] = ("up", "down", "left", "right")
SUPPORTED_2048_RESULT_BOARD_LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(6))


@dataclass(frozen=True)
class Move2048Result:
    """Fully traced result of applying one 2048 move."""

    direction: str
    before: Board
    after: Board
    merge_pairs: Tuple[Tuple[Coord, Coord], ...]
    score: int
    moved: bool
    result_sources: Mapping[Coord, Tuple[Coord, ...]]


@dataclass(frozen=True)
class Sample2048:
    """Generated 2048 board state and grounded query target."""

    query_id: str
    scene_variant: str
    style_variant: str
    answer: str | int
    board: Board
    move_direction: str
    move_result: Move2048Result
    all_move_results: Mapping[str, Move2048Result]
    annotation_cell_ids: Tuple[str, ...]
    construction_mode: str
    result_option_boards: Mapping[str, Board] = field(default_factory=dict)


def coord_to_cell_id(coord: Coord) -> str:
    """Return a stable id for one board cell."""

    row, col = int(coord[0]), int(coord[1])
    return f"cell_r{row}_c{col}"


def validate_board(board: Board) -> None:
    """Validate one 4 x 4 2048 board."""

    if len(board) != SIZE or any(len(row) != SIZE for row in board):
        raise ValueError("2048 board must be 4 x 4")
    for row in board:
        for value in row:
            int_value = int(value)
            if int_value < 0:
                raise ValueError("2048 board values must be non-negative")
            if int_value != EMPTY and (int_value & (int_value - 1)) != 0:
                raise ValueError("2048 non-empty tile values must be powers of two")


def _line_coords(index: int, direction: str) -> Tuple[Coord, ...]:
    """Return board coordinates in move-compression order for one line."""

    if str(direction) == "left":
        return tuple((int(index), col) for col in range(SIZE))
    if str(direction) == "right":
        return tuple((int(index), col) for col in range(SIZE - 1, -1, -1))
    if str(direction) == "up":
        return tuple((row, int(index)) for row in range(SIZE))
    if str(direction) == "down":
        return tuple((row, int(index)) for row in range(SIZE - 1, -1, -1))
    raise ValueError(f"unsupported 2048 move direction: {direction!r}")


def simulate_2048_move(board: Board, direction: str) -> Move2048Result:
    """Apply standard 2048 slide-and-merge rules for one move."""

    validate_board(board)
    if str(direction) not in SUPPORTED_2048_DIRECTIONS:
        raise ValueError(f"unsupported 2048 move direction: {direction!r}")

    result = [[EMPTY for _ in range(SIZE)] for _ in range(SIZE)]
    merge_pairs: list[Tuple[Coord, Coord]] = []
    result_sources: dict[Coord, Tuple[Coord, ...]] = {}
    score = 0

    for line_index in range(SIZE):
        coords = _line_coords(line_index, str(direction))
        tiles: list[tuple[int, Tuple[Coord, ...]]] = []
        for coord in coords:
            value = int(board[int(coord[0])][int(coord[1])])
            if value != EMPTY:
                tiles.append((int(value), (coord,)))

        compressed: list[tuple[int, Tuple[Coord, ...]]] = []
        cursor = 0
        while cursor < len(tiles):
            value, sources = tiles[cursor]
            if cursor + 1 < len(tiles) and int(tiles[cursor + 1][0]) == int(value):
                merged_sources = tuple(sources + tiles[cursor + 1][1])
                merged_value = int(value) * 2
                compressed.append((int(merged_value), merged_sources))
                merge_pairs.append((merged_sources[0], merged_sources[1]))
                score += int(merged_value)
                cursor += 2
            else:
                compressed.append((int(value), tuple(sources)))
                cursor += 1

        for output_index, (value, sources) in enumerate(compressed):
            dest = coords[int(output_index)]
            result[int(dest[0])][int(dest[1])] = int(value)
            result_sources[dest] = tuple(sources)

    after = tuple(tuple(int(value) for value in row) for row in result)
    return Move2048Result(
        direction=str(direction),
        before=tuple(tuple(int(value) for value in row) for row in board),
        after=after,
        merge_pairs=tuple(tuple(pair) for pair in merge_pairs),
        score=int(score),
        moved=after != tuple(tuple(int(value) for value in row) for row in board),
        result_sources=dict(result_sources),
    )


def board_empty_count(board: Board) -> int:
    """Return the number of empty cells on one 2048 board."""

    return sum(1 for row in board for value in row if int(value) == EMPTY)


def board_max_tile(board: Board) -> int:
    """Return the largest visible tile value on one 2048 board."""

    values = [int(value) for row in board for value in row]
    return max(values) if values else EMPTY


def validate_2048_sample(sample: Sample2048) -> None:
    """Validate answer/annotation consistency for one generated 2048 sample."""

    validate_board(sample.board)
    if str(sample.query_id) not in SUPPORTED_2048_QUERY_IDS:
        raise ValueError(f"unsupported 2048 query_id: {sample.query_id}")
    if str(sample.move_direction) not in SUPPORTED_2048_DIRECTIONS:
        raise ValueError("2048 sample has unsupported move direction")

    expected_answer: str | int
    expected_coords: Tuple[Coord, ...]
    if str(sample.query_id) == "merge_count":
        expected_answer = int(len(sample.move_result.merge_pairs))
        expected_coords = tuple(coord for pair in sample.move_result.merge_pairs for coord in pair)
    elif str(sample.query_id) == "score_value":
        expected_answer = int(sample.move_result.score)
        expected_coords = tuple(coord for pair in sample.move_result.merge_pairs for coord in pair)
    elif str(sample.query_id) == "max_tile_value":
        max_value = board_max_tile(sample.move_result.after)
        max_cells = [coord for coord, sources in sample.move_result.result_sources.items() if sample.move_result.after[coord[0]][coord[1]] == max_value and sources]
        expected_answer = int(max_value)
        expected_coords = tuple(coord for cell in max_cells for coord in sample.move_result.result_sources[cell])
    elif str(sample.query_id) == "move_result_board_label":
        options = dict(sample.result_option_boards or {})
        if not options:
            raise ValueError("move_result_board_label requires result board options")
        expected_labels = [
            str(label)
            for label, board in options.items()
            if tuple(tuple(int(value) for value in row) for row in board) == sample.move_result.after
        ]
        if len(expected_labels) != 1:
            raise ValueError("move_result_board_label requires exactly one matching option")
        expected_answer = str(expected_labels[0])
        expected_coords = tuple()
    else:  # pragma: no cover - guarded above.
        raise ValueError(f"unsupported 2048 query_id: {sample.query_id}")

    if sample.answer != expected_answer:
        raise ValueError("2048 answer does not match active query")
    expected_ids = (
        (f"result_option_{expected_answer}",)
        if str(sample.query_id) == "move_result_board_label"
        else tuple(coord_to_cell_id(coord) for coord in expected_coords)
    )
    if tuple(sample.annotation_cell_ids) != expected_ids:
        raise ValueError("2048 annotation ids do not match active query")


__all__ = [
    "Board",
    "Coord",
    "EMPTY",
    "MOVE_RESULT_QUERY_IDS",
    "SIZE",
    "SUPPORTED_2048_DIRECTIONS",
    "SUPPORTED_2048_QUERY_IDS",
    "SUPPORTED_2048_RESULT_BOARD_LABELS",
    "SUPPORTED_2048_SCENE_VARIANTS",
    "SUPPORTED_2048_STYLE_VARIANTS",
    "Move2048Result",
    "Sample2048",
    "board_empty_count",
    "board_max_tile",
    "coord_to_cell_id",
    "simulate_2048_move",
    "validate_2048_sample",
]
