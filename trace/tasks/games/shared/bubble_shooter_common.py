"""Shared Bubble-shooter helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


SUPPORTED_BUBBLE_SHOOTER_QUERY_IDS: Tuple[str, ...] = (
    "pop_count",
    "drop_count",
    "pop_color_label",
)
SUPPORTED_BUBBLE_SHOOTER_SCENE_VARIANTS: Tuple[str, ...] = (
    "open_pack",
    "dense_pack",
)
SUPPORTED_BUBBLE_SHOOTER_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "pastel",
    "neon",
    "paper",
    "arcade",
)
BUBBLE_COLOR_KEYS: Tuple[str, ...] = (
    "red",
    "yellow",
    "blue",
    "green",
    "purple",
    "orange",
)
BUBBLE_OPTION_LABELS: Tuple[str, ...] = tuple("ABCDEF")

Coord = Tuple[int, int]
Board = Tuple[Tuple[str | None, ...], ...]


@dataclass(frozen=True)
class BubbleShooterOption:
    """One labeled next-bubble color option."""

    label: str
    color_key: str
    is_answer: bool


@dataclass(frozen=True)
class BubbleShotOutcome:
    """Computed effect of shooting one bubble to one landing slot."""

    landing_coord: Coord
    color_key: str
    connected_same_color_coords: Tuple[Coord, ...]
    popped_coords: Tuple[Coord, ...]
    dropped_coords: Tuple[Coord, ...]


@dataclass(frozen=True)
class BubbleShooterSample:
    """Generated Bubble-shooter board state and query answer."""

    row_count: int
    col_count: int
    query_id: str
    scene_variant: str
    style_variant: str
    board: Board
    landing_coord: Coord
    shooter_color_key: str | None
    answer: int | str
    target_answer: int | str
    option_specs: Tuple[BubbleShooterOption, ...]
    outcome: BubbleShotOutcome
    evidence_entity_ids: Tuple[str, ...]
    construction_mode: str


def bubble_entity_id(coord: Coord) -> str:
    """Return the stable entity id for one visible board bubble."""

    row, col = coord
    return f"bubble_r{int(row)}_c{int(col)}"


def landing_slot_entity_id() -> str:
    """Return the stable entity id for the marked landing slot."""

    return "landing_slot"


def shooter_bubble_entity_id() -> str:
    """Return the stable entity id for the visible shooter bubble."""

    return "shooter_bubble"


def option_entity_id(label: str) -> str:
    """Return the stable entity id for one labeled color option."""

    return f"option_{str(label)}"


def board_from_mapping(*, rows: int, cols: int, values: Mapping[Coord, str]) -> Board:
    """Return an immutable board from sparse coordinate values."""

    return tuple(
        tuple(values.get((row, col)) for col in range(int(cols)))
        for row in range(int(rows))
    )


def board_value(board: Sequence[Sequence[str | None]], coord: Coord) -> str | None:
    """Return the board value at one coordinate."""

    return board[int(coord[0])][int(coord[1])]


def all_bubble_coords(rows: int, cols: int) -> Tuple[Coord, ...]:
    """Return all row-major bubble-grid coordinates."""

    return tuple((row, col) for row in range(int(rows)) for col in range(int(cols)))


def occupied_coords(board: Sequence[Sequence[str | None]]) -> Tuple[Coord, ...]:
    """Return every occupied board coordinate."""

    return tuple(
        (row, col)
        for row, row_values in enumerate(board)
        for col, value in enumerate(row_values)
        if value is not None
    )


def empty_coords(board: Sequence[Sequence[str | None]]) -> Tuple[Coord, ...]:
    """Return every empty board coordinate."""

    return tuple(
        (row, col)
        for row, row_values in enumerate(board)
        for col, value in enumerate(row_values)
        if value is None
    )


def sorted_coords(coords: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Return canonical sorted coordinates."""

    return tuple(sorted((int(row), int(col)) for row, col in coords))


def bubble_neighbors(coord: Coord, *, rows: int, cols: int) -> Tuple[Coord, ...]:
    """Return in-bounds neighbors in an odd-row offset bubble grid."""

    row, col = int(coord[0]), int(coord[1])
    if row % 2 == 0:
        candidates = (
            (row, col - 1),
            (row, col + 1),
            (row - 1, col - 1),
            (row - 1, col),
            (row + 1, col - 1),
            (row + 1, col),
        )
    else:
        candidates = (
            (row, col - 1),
            (row, col + 1),
            (row - 1, col),
            (row - 1, col + 1),
            (row + 1, col),
            (row + 1, col + 1),
        )
    return tuple(
        (int(next_row), int(next_col))
        for next_row, next_col in candidates
        if 0 <= int(next_row) < int(rows) and 0 <= int(next_col) < int(cols)
    )


def connected_component(
    board: Sequence[Sequence[str | None]],
    *,
    start: Coord,
    allowed_colors: Iterable[str] | None = None,
) -> Tuple[Coord, ...]:
    """Return one connected occupied component."""

    rows = len(board)
    cols = len(board[0]) if rows else 0
    start_value = board_value(board, start)
    if start_value is None:
        return tuple()
    allowed = set(str(value) for value in allowed_colors) if allowed_colors is not None else {str(start_value)}
    stack = [tuple(start)]
    seen: set[Coord] = set()
    while stack:
        coord = stack.pop()
        if coord in seen:
            continue
        if board_value(board, coord) not in allowed:
            continue
        seen.add(coord)
        for neighbor in bubble_neighbors(coord, rows=rows, cols=cols):
            if neighbor not in seen and board_value(board, neighbor) in allowed:
                stack.append(neighbor)
    return sorted_coords(seen)


def same_color_component_from_landing(
    board: Sequence[Sequence[str | None]],
    *,
    landing_coord: Coord,
    color_key: str,
) -> Tuple[Coord, ...]:
    """Return existing same-color bubbles connected to a placed bubble."""

    rows = len(board)
    cols = len(board[0]) if rows else 0
    color = str(color_key)
    seen: set[Coord] = set()
    stack = [
        neighbor
        for neighbor in bubble_neighbors(landing_coord, rows=rows, cols=cols)
        if board_value(board, neighbor) == color
    ]
    while stack:
        coord = stack.pop()
        if coord in seen:
            continue
        if board_value(board, coord) != color:
            continue
        seen.add(coord)
        for neighbor in bubble_neighbors(coord, rows=rows, cols=cols):
            if neighbor not in seen and board_value(board, neighbor) == color:
                stack.append(neighbor)
    return sorted_coords(seen)


def top_connected_occupied(
    board: Sequence[Sequence[str | None]],
    *,
    removed: Iterable[Coord] = (),
) -> Tuple[Coord, ...]:
    """Return occupied cells connected to the top row after removals."""

    rows = len(board)
    cols = len(board[0]) if rows else 0
    removed_set = {tuple(coord) for coord in removed}
    starts = [
        (0, col)
        for col in range(cols)
        if (0, col) not in removed_set and board_value(board, (0, col)) is not None
    ]
    stack = list(starts)
    seen: set[Coord] = set()
    while stack:
        coord = stack.pop()
        if coord in seen or coord in removed_set:
            continue
        if board_value(board, coord) is None:
            continue
        seen.add(coord)
        for neighbor in bubble_neighbors(coord, rows=rows, cols=cols):
            if neighbor not in seen and neighbor not in removed_set and board_value(board, neighbor) is not None:
                stack.append(neighbor)
    return sorted_coords(seen)


def compute_shot_outcome(
    board: Sequence[Sequence[str | None]],
    *,
    landing_coord: Coord,
    color_key: str,
) -> BubbleShotOutcome:
    """Compute pop and drop effects for one placed bubble."""

    if board_value(board, landing_coord) is not None:
        raise ValueError("bubble shooter landing coordinate must be empty")
    same_color = same_color_component_from_landing(
        board,
        landing_coord=landing_coord,
        color_key=str(color_key),
    )
    popped = same_color if len(same_color) + 1 >= 3 else tuple()
    occupied_after_pop = set(occupied_coords(board)) - set(popped)
    anchored = set(top_connected_occupied(board, removed=popped))
    dropped = sorted_coords(coord for coord in occupied_after_pop if coord not in anchored)
    return BubbleShotOutcome(
        landing_coord=tuple(landing_coord),
        color_key=str(color_key),
        connected_same_color_coords=tuple(same_color),
        popped_coords=tuple(popped),
        dropped_coords=tuple(dropped),
    )


def validate_bubble_shooter_sample(sample: BubbleShooterSample) -> None:
    """Validate the public answer/evidence contract for one Bubble-shooter sample."""

    if int(sample.row_count) <= 0 or int(sample.col_count) <= 0:
        raise ValueError("bubble shooter board dimensions must be positive")
    if len(sample.board) != int(sample.row_count) or any(len(row) != int(sample.col_count) for row in sample.board):
        raise ValueError("bubble shooter board dimensions do not match row_count/col_count")
    if board_value(sample.board, sample.landing_coord) is not None:
        raise ValueError("bubble shooter landing slot must be empty")

    known_entities = {bubble_entity_id(coord) for coord in occupied_coords(sample.board)}
    known_entities.add(landing_slot_entity_id())
    known_entities.add(shooter_bubble_entity_id())
    known_entities.update(option_entity_id(option.label) for option in sample.option_specs)
    if not set(sample.evidence_entity_ids) <= known_entities:
        raise ValueError("bubble shooter evidence references unknown entities")

    outcome = compute_shot_outcome(
        sample.board,
        landing_coord=sample.landing_coord,
        color_key=str(sample.outcome.color_key),
    )
    if outcome != sample.outcome:
        raise ValueError("bubble shooter stored outcome does not match board computation")

    query = str(sample.query_id)
    if query == "pop_count":
        if sample.shooter_color_key != sample.outcome.color_key:
            raise ValueError("pop_count shooter color must match outcome color")
        if int(sample.answer) != len(sample.outcome.popped_coords):
            raise ValueError("pop_count answer must equal popped existing bubbles")
        expected = {bubble_entity_id(coord) for coord in sample.outcome.popped_coords}
    elif query == "drop_count":
        if sample.shooter_color_key != sample.outcome.color_key:
            raise ValueError("drop_count shooter color must match outcome color")
        if int(sample.answer) != len(sample.outcome.dropped_coords):
            raise ValueError("drop_count answer must equal dropped bubbles")
        expected = {bubble_entity_id(coord) for coord in sample.outcome.dropped_coords}
    elif query == "pop_color_label":
        answer_options = [option for option in sample.option_specs if option.is_answer]
        if len(answer_options) != 1:
            raise ValueError("pop_color_label requires exactly one answer option")
        if str(sample.answer) != str(answer_options[0].label):
            raise ValueError("pop_color_label answer must be the selected option label")
        pop_positive = [
            option
            for option in sample.option_specs
            if len(
                compute_shot_outcome(
                    sample.board,
                    landing_coord=sample.landing_coord,
                    color_key=str(option.color_key),
                ).popped_coords
            )
            > 0
        ]
        if len(pop_positive) != 1 or str(pop_positive[0].label) != str(sample.answer):
            raise ValueError("pop_color_label must have exactly one displayed popping color")
        expected = {bubble_entity_id(coord) for coord in sample.outcome.popped_coords}
    else:
        raise ValueError(f"unsupported bubble shooter query_id: {sample.query_id}")

    if set(sample.evidence_entity_ids) != expected:
        raise ValueError("bubble shooter evidence ids do not match active query")


__all__ = [
    "BUBBLE_COLOR_KEYS",
    "BUBBLE_OPTION_LABELS",
    "SUPPORTED_BUBBLE_SHOOTER_QUERY_IDS",
    "SUPPORTED_BUBBLE_SHOOTER_SCENE_VARIANTS",
    "SUPPORTED_BUBBLE_SHOOTER_STYLE_VARIANTS",
    "Board",
    "BubbleShooterOption",
    "BubbleShooterSample",
    "BubbleShotOutcome",
    "Coord",
    "all_bubble_coords",
    "board_from_mapping",
    "board_value",
    "bubble_entity_id",
    "bubble_neighbors",
    "compute_shot_outcome",
    "connected_component",
    "empty_coords",
    "landing_slot_entity_id",
    "occupied_coords",
    "option_entity_id",
    "same_color_component_from_landing",
    "shooter_bubble_entity_id",
    "sorted_coords",
    "top_connected_occupied",
    "validate_bubble_shooter_sample",
]
