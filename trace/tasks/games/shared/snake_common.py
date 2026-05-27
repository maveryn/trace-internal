"""Shared Snake-game helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Mapping, Sequence, Tuple


Coord = Tuple[int, int]

DIRECTION_DELTAS: Mapping[str, Coord] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}
DIRECTION_NAMES: Tuple[str, ...] = ("up", "down", "left", "right")
PLANNED_MOVE_OUTCOMES: Tuple[str, ...] = ("point", "game_over")

SUPPORTED_SNAKE_MOVE_SAFETY_QUERY_IDS: Tuple[str, ...] = (
    "safe_direction_count",
)
SUPPORTED_SNAKE_PATH_OUTCOME_QUERY_IDS: Tuple[str, ...] = (
    "path_result_option_label",
)
SUPPORTED_SNAKE_QUERY_IDS: Tuple[str, ...] = (
    SUPPORTED_SNAKE_MOVE_SAFETY_QUERY_IDS + SUPPORTED_SNAKE_PATH_OUTCOME_QUERY_IDS
)
SUPPORTED_SNAKE_SCENE_VARIANTS: Tuple[str, ...] = ("square_grid",)
SUPPORTED_SNAKE_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "neon",
    "forest",
    "paper",
    "candy",
)


@dataclass(frozen=True)
class SnakeState:
    """One visible snake state.

    `body` is ordered from the segment next to the head toward the tail.
    """

    board_size: int
    head: Coord
    body: Tuple[Coord, ...]
    food: Coord
    obstacles: Tuple[Coord, ...] = ()


@dataclass(frozen=True)
class SnakeSimulation:
    """Simulation result for one Snake move sequence."""

    outcome: str
    event_step: int
    traversed_coords: Tuple[Coord, ...]
    collision_coord: Coord | None
    final_head: Coord


@dataclass(frozen=True)
class SnakeSample:
    """Generated Snake scene state and query result."""

    query_id: str
    scene_variant: str
    style_variant: str
    answer: str | int
    state: SnakeState
    single_move: str | None
    planned_moves: Tuple[str, ...]
    safe_directions: Tuple[str, ...]
    evidence_cell_ids: Tuple[str, ...]
    target_outcome: str | None
    observed_event_step: int | None
    construction_mode: str
    result_options: Tuple[Mapping[str, object], ...] = ()


def coord_to_cell_id(coord: Coord) -> str:
    """Return a stable visible-cell id."""

    return f"cell_r{int(coord[0])}_c{int(coord[1])}"


def all_coords(size: int) -> Tuple[Coord, ...]:
    """Return all grid coordinates in reading order."""

    return tuple((row, col) for row in range(int(size)) for col in range(int(size)))


def in_bounds(coord: Coord, *, size: int) -> bool:
    """Return true when `coord` lies inside the square board."""

    return 0 <= int(coord[0]) < int(size) and 0 <= int(coord[1]) < int(size)


def step_coord(coord: Coord, direction: str) -> Coord:
    """Move one coordinate by one named cardinal direction."""

    delta = DIRECTION_DELTAS[str(direction)]
    return (int(coord[0]) + int(delta[0]), int(coord[1]) + int(delta[1]))


def neighbor_coords(coord: Coord, *, size: int) -> Tuple[Coord, ...]:
    """Return in-board cardinal neighbors."""

    return tuple(
        candidate
        for direction in DIRECTION_NAMES
        for candidate in (step_coord(coord, direction),)
        if in_bounds(candidate, size=int(size))
    )


def direction_text(direction: str) -> str:
    """Return display text for one move direction."""

    return str(direction).upper()


def move_sequence_text(moves: Sequence[str]) -> str:
    """Return compact prompt text for a planned move sequence."""

    return ", ".join(f"{index + 1}. {direction_text(move)}" for index, move in enumerate(moves))


def simulate_snake_moves(state: SnakeState, moves: Sequence[str]) -> SnakeSimulation:
    """Simulate a Snake move sequence with normal tail movement and no growth before food.

    The simulation stops at the first event: wall hit, body hit, or food reach.
    """

    size = int(state.board_size)
    head = (int(state.head[0]), int(state.head[1]))
    body = tuple((int(row), int(col)) for row, col in state.body)
    food = (int(state.food[0]), int(state.food[1]))
    obstacles = set((int(row), int(col)) for row, col in state.obstacles)
    traversed: list[Coord] = []

    for step_index, direction in enumerate(moves, start=1):
        new_head = step_coord(head, str(direction))
        if not in_bounds(new_head, size=size):
            return SnakeSimulation(
                outcome="wall",
                event_step=int(step_index),
                traversed_coords=tuple(traversed),
                collision_coord=None,
                final_head=head,
            )
        if new_head in obstacles:
            traversed.append(new_head)
            return SnakeSimulation(
                outcome="wall",
                event_step=int(step_index),
                traversed_coords=tuple(traversed),
                collision_coord=new_head,
                final_head=head,
            )

        traversed.append(new_head)
        tail_to_vacate = body[-1] if body else None
        blocked_body = set(body)
        if new_head in blocked_body and new_head != tail_to_vacate:
            return SnakeSimulation(
                outcome="body",
                event_step=int(step_index),
                traversed_coords=tuple(traversed),
                collision_coord=new_head,
                final_head=new_head,
            )
        if new_head == food:
            return SnakeSimulation(
                outcome="food",
                event_step=int(step_index),
                traversed_coords=tuple(traversed),
                collision_coord=new_head,
                final_head=new_head,
            )

        body = (head,) + body[:-1]
        head = new_head

    return SnakeSimulation(
        outcome="safe" if len(tuple(moves)) == 1 else "survives",
        event_step=0,
        traversed_coords=tuple(traversed),
        collision_coord=None,
        final_head=head,
    )


def immediate_outcome(state: SnakeState, direction: str) -> SnakeSimulation:
    """Return the one-step outcome for one direction."""

    return simulate_snake_moves(state, (str(direction),))


def safe_next_directions(state: SnakeState) -> Tuple[str, ...]:
    """Return directions whose next move does not hit wall or body."""

    safe: list[str] = []
    for direction in DIRECTION_NAMES:
        outcome = immediate_outcome(state, direction).outcome
        if outcome in {"safe", "food"}:
            safe.append(str(direction))
    return tuple(safe)


def candidate_move_sequences(length: int) -> Tuple[Tuple[str, ...], ...]:
    """Return all cardinal move sequences of one length."""

    return tuple(tuple(str(move) for move in sequence) for sequence in product(DIRECTION_NAMES, repeat=int(length)))


def validate_snake_state(state: SnakeState) -> None:
    """Validate one visible Snake state."""

    size = int(state.board_size)
    head = (int(state.head[0]), int(state.head[1]))
    body = tuple((int(row), int(col)) for row, col in state.body)
    food = (int(state.food[0]), int(state.food[1]))
    obstacles = tuple((int(row), int(col)) for row, col in state.obstacles)
    if not in_bounds(head, size=size):
        raise ValueError("snake head must be in bounds")
    if not in_bounds(food, size=size):
        raise ValueError("snake food must be in bounds")
    if food == head or food in set(body):
        raise ValueError("snake food must not overlap snake")
    if food in set(obstacles):
        raise ValueError("snake food must not overlap wall cells")
    if len(body) != len(set(body)):
        raise ValueError("snake body cells must be unique")
    if len(obstacles) != len(set(obstacles)):
        raise ValueError("snake wall cells must be unique")
    if head in set(body):
        raise ValueError("snake head must not overlap body")
    if head in set(obstacles) or set(body) & set(obstacles):
        raise ValueError("snake wall cells must not overlap snake")
    if any(not in_bounds(coord, size=size) for coord in body):
        raise ValueError("snake body cells must be in bounds")
    if any(not in_bounds(coord, size=size) for coord in obstacles):
        raise ValueError("snake wall cells must be in bounds")
    if body:
        prev = head
        for coord in body:
            if coord not in set(neighbor_coords(prev, size=size)):
                raise ValueError("snake body must be a connected cardinal chain")
            prev = coord


def validate_snake_sample(sample: SnakeSample) -> None:
    """Validate one generated Snake sample."""

    validate_snake_state(sample.state)
    query = str(sample.query_id)
    known_cell_ids = {coord_to_cell_id(coord) for coord in all_coords(sample.state.board_size)}
    if not set(sample.evidence_cell_ids) <= known_cell_ids:
        raise ValueError("snake evidence references unknown cells")

    if query == "safe_direction_count":
        expected_dirs = safe_next_directions(sample.state)
        expected_ids = tuple(coord_to_cell_id(step_coord(sample.state.head, direction)) for direction in expected_dirs)
        if int(sample.answer) != len(expected_dirs):
            raise ValueError("snake safe-direction count answer mismatch")
        if tuple(sample.safe_directions) != expected_dirs:
            raise ValueError("snake safe-direction list mismatch")
        if tuple(sample.evidence_cell_ids) != expected_ids:
            raise ValueError("snake safe-direction evidence mismatch")
    elif query == "path_result_option_label":
        if not sample.planned_moves:
            raise ValueError("planned Snake query requires planned moves")
        simulation = simulate_snake_moves(sample.state, sample.planned_moves)
        expected_ids = _planned_move_evidence_ids(sample.state, simulation)
        if not sample.result_options:
            raise ValueError("path_result_option_label requires visible options")
        labels = [str(option.get("label")) for option in sample.result_options]
        if labels != ["A", "B", "C", "D"]:
            raise ValueError("snake path-result options must be visible labels A-D")
        game_over_options = [option for option in sample.result_options if str(option.get("kind")) == "game_over"]
        point_options = [option for option in sample.result_options if str(option.get("kind")) == "point"]
        if len(game_over_options) != 1 or len(point_options) != 3:
            raise ValueError("snake path-result options must include one game-over option and three point options")
        if str(sample.answer) not in set(labels):
            raise ValueError("snake path-result answer must be one visible option label")
        answer_options = [option for option in sample.result_options if str(option.get("label")) == str(sample.answer)]
        if len(answer_options) != 1 or not bool(answer_options[0].get("is_answer")):
            raise ValueError("snake path-result answer option marker mismatch")
        if sum(1 for option in sample.result_options if bool(option.get("is_answer"))) != 1:
            raise ValueError("snake path-result must have exactly one correct visible option")
        answer_option = answer_options[0]
        if str(sample.target_outcome) == "game_over":
            if str(simulation.outcome) not in {"body", "wall"}:
                raise ValueError("snake path-result game-over target does not match simulation")
            if str(answer_option.get("kind")) != "game_over":
                raise ValueError("snake path-result game-over answer must choose the game-over option")
        elif str(sample.target_outcome) == "point":
            if str(simulation.outcome) in {"body", "wall", "food"}:
                raise ValueError("snake path-result point target does not match simulation")
            if str(answer_option.get("kind")) != "point":
                raise ValueError("snake path-result point answer must choose a point option")
            if tuple(answer_option.get("coord", ())) != tuple(int(v) for v in simulation.final_head):
                raise ValueError("snake path-result point answer coordinate mismatch")
        else:
            raise ValueError("snake path-result target outcome must be point or game_over")
        if tuple(sample.evidence_cell_ids) != expected_ids:
            raise ValueError("snake planned-move evidence mismatch")
    else:
        raise ValueError(f"unsupported snake query_id: {sample.query_id}")


def _planned_move_evidence_ids(state: SnakeState, simulation: SnakeSimulation) -> Tuple[str, ...]:
    """Return evidence cell ids for one planned move simulation."""

    coords = tuple(dict.fromkeys(simulation.traversed_coords))
    if coords:
        return tuple(coord_to_cell_id(coord) for coord in coords)
    return (coord_to_cell_id(state.head),)


def visible_snake_trace(state: SnakeState) -> Mapping[str, object]:
    """Return JSON-safe state diagnostics for trace payloads."""

    return {
        "board_size": int(state.board_size),
        "head": [int(state.head[0]), int(state.head[1])],
        "body": [[int(row), int(col)] for row, col in state.body],
        "food": [int(state.food[0]), int(state.food[1])],
        "obstacles": [[int(row), int(col)] for row, col in state.obstacles],
    }


def sorted_coords(coords: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Return coordinates in reading order."""

    return tuple(sorted(((int(row), int(col)) for row, col in coords), key=lambda item: (item[0], item[1])))


__all__ = [
    "Coord",
    "DIRECTION_DELTAS",
    "DIRECTION_NAMES",
    "PLANNED_MOVE_OUTCOMES",
    "SUPPORTED_SNAKE_MOVE_SAFETY_QUERY_IDS",
    "SUPPORTED_SNAKE_PATH_OUTCOME_QUERY_IDS",
    "SUPPORTED_SNAKE_QUERY_IDS",
    "SUPPORTED_SNAKE_SCENE_VARIANTS",
    "SUPPORTED_SNAKE_STYLE_VARIANTS",
    "SnakeSample",
    "SnakeSimulation",
    "SnakeState",
    "all_coords",
    "candidate_move_sequences",
    "coord_to_cell_id",
    "direction_text",
    "immediate_outcome",
    "in_bounds",
    "move_sequence_text",
    "neighbor_coords",
    "safe_next_directions",
    "simulate_snake_moves",
    "sorted_coords",
    "step_coord",
    "validate_snake_sample",
    "validate_snake_state",
    "visible_snake_trace",
]
