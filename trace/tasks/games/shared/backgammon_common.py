"""Shared Backgammon rules and scene contracts for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple


BACKGAMMON_DESTINATION_QUERY_IDS: Tuple[str, ...] = (
    "legal_move_count",
    "hit_move_count",
    "blocked_destination_count",
)
BACKGAMMON_POINT_STATE_QUERY_IDS: Tuple[str, ...] = (
    "black_single_checker_point_count",
    "white_single_checker_point_count",
    "black_two_or_more_checker_point_count",
    "white_two_or_more_checker_point_count",
)
BACKGAMMON_QUERY_IDS: Tuple[str, ...] = BACKGAMMON_DESTINATION_QUERY_IDS + BACKGAMMON_POINT_STATE_QUERY_IDS
BACKGAMMON_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "navy",
    "parchment",
    "slate",
    "tournament",
)
PLAYER_BLACK = "black"
PLAYER_WHITE = "white"
POINT_IDS: Tuple[int, ...] = tuple(range(1, 25))


@dataclass(frozen=True)
class BackgammonPoint:
    """Visible checker stack on one numbered Backgammon point."""

    owner: str | None
    count: int


@dataclass(frozen=True)
class BackgammonOutcome:
    """Computed single-die destination sets for one active player."""

    legal_destinations: Tuple[int, ...]
    hit_destinations: Tuple[int, ...]
    blocked_destinations: Tuple[int, ...]


@dataclass(frozen=True)
class BackgammonSample:
    """One generated Backgammon position plus answer/annotation contract."""

    points: Mapping[int, BackgammonPoint]
    dice: Tuple[int, int]
    active_player: str
    query_id: str
    answer: int
    target_destinations: Tuple[int, ...]
    outcome: BackgammonOutcome
    style_variant: str
    target_answer: int
    target_points: Tuple[int, ...] = ()


def point_entity_id(point_id: int) -> str:
    """Return the stable entity id for one numbered board point."""

    return f"point_{int(point_id)}"


def checker_entity_id(point_id: int, stack_index: int) -> str:
    """Return the stable entity id for one visible checker."""

    return f"checker_p{int(point_id)}_{int(stack_index)}"


def die_entity_id(index: int) -> str:
    """Return the stable entity id for one visible die."""

    return f"die_{int(index)}"


def empty_points() -> dict[int, BackgammonPoint]:
    """Return an empty 24-point Backgammon board."""

    return {point: BackgammonPoint(owner=None, count=0) for point in POINT_IDS}


def stack_at(points: Mapping[int, BackgammonPoint], point_id: int) -> BackgammonPoint:
    """Return the stack at one point, treating missing points as empty."""

    stack = points.get(int(point_id))
    if stack is None:
        return BackgammonPoint(owner=None, count=0)
    return stack


def is_blocked_by_white(points: Mapping[int, BackgammonPoint], point_id: int) -> bool:
    """Return true when a destination has two or more white checkers."""

    stack = stack_at(points, int(point_id))
    return str(stack.owner) == PLAYER_WHITE and int(stack.count) >= 2


def is_white_blot(points: Mapping[int, BackgammonPoint], point_id: int) -> bool:
    """Return true when a destination has exactly one white checker."""

    stack = stack_at(points, int(point_id))
    return str(stack.owner) == PLAYER_WHITE and int(stack.count) == 1


def opponent_for_player(active_player: str) -> str:
    """Return the opposing checker color for one active player."""

    player = str(active_player)
    if player == PLAYER_BLACK:
        return PLAYER_WHITE
    if player == PLAYER_WHITE:
        return PLAYER_BLACK
    raise ValueError(f"unsupported Backgammon player: {active_player!r}")


def destination_for_player(source: int, die: int, *, active_player: str) -> int:
    """Return one single-die destination point for the active player."""

    if str(active_player) == PLAYER_BLACK:
        return int(source) - int(die)
    if str(active_player) == PLAYER_WHITE:
        return int(source) + int(die)
    raise ValueError(f"unsupported Backgammon player: {active_player!r}")


def is_blocked_by_opponent(points: Mapping[int, BackgammonPoint], point_id: int, *, active_player: str) -> bool:
    """Return true when a destination has two or more opposing checkers."""

    stack = stack_at(points, int(point_id))
    return str(stack.owner) == opponent_for_player(str(active_player)) and int(stack.count) >= 2


def is_opponent_blot(points: Mapping[int, BackgammonPoint], point_id: int, *, active_player: str) -> bool:
    """Return true when a destination has exactly one opposing checker."""

    stack = stack_at(points, int(point_id))
    return str(stack.owner) == opponent_for_player(str(active_player)) and int(stack.count) == 1


def compute_single_die_destinations(
    points: Mapping[int, BackgammonPoint],
    *,
    dice: Tuple[int, int],
    active_player: str,
) -> BackgammonOutcome:
    """Compute destination-point sets for the active player and shown dice."""

    player = str(active_player)
    candidate_destinations: set[int] = set()
    for source in POINT_IDS:
        stack = stack_at(points, int(source))
        if str(stack.owner) != player or int(stack.count) <= 0:
            continue
        for die in dice:
            dest = destination_for_player(int(source), int(die), active_player=player)
            if int(dest) in POINT_IDS:
                candidate_destinations.add(int(dest))

    blocked = tuple(sorted(point for point in candidate_destinations if is_blocked_by_opponent(points, point, active_player=player)))
    legal = tuple(sorted(point for point in candidate_destinations if point not in set(blocked)))
    hit = tuple(sorted(point for point in legal if is_opponent_blot(points, point, active_player=player)))
    return BackgammonOutcome(
        legal_destinations=legal,
        hit_destinations=hit,
        blocked_destinations=blocked,
    )


def compute_black_single_die_destinations(
    points: Mapping[int, BackgammonPoint],
    *,
    dice: Tuple[int, int],
) -> BackgammonOutcome:
    """Compute destination-point sets for black moving from high points to low points."""
    return compute_single_die_destinations(points, dice=dice, active_player=PLAYER_BLACK)


def target_destinations_for_query(outcome: BackgammonOutcome, *, query_id: str) -> Tuple[int, ...]:
    """Return the query-specific destination set."""

    query = str(query_id)
    if query == "legal_move_count":
        return tuple(outcome.legal_destinations)
    if query == "hit_move_count":
        return tuple(outcome.hit_destinations)
    if query == "blocked_destination_count":
        return tuple(outcome.blocked_destinations)
    raise ValueError(f"unsupported Backgammon query_id: {query}")


def point_matches_state_query(point: BackgammonPoint, *, query_id: str) -> bool:
    """Return true when one point stack satisfies a point-state query."""

    query = str(query_id)
    if query == "black_single_checker_point_count":
        return str(point.owner) == PLAYER_BLACK and int(point.count) == 1
    if query == "white_single_checker_point_count":
        return str(point.owner) == PLAYER_WHITE and int(point.count) == 1
    if query == "black_two_or_more_checker_point_count":
        return str(point.owner) == PLAYER_BLACK and int(point.count) >= 2
    if query == "white_two_or_more_checker_point_count":
        return str(point.owner) == PLAYER_WHITE and int(point.count) >= 2
    raise ValueError(f"unsupported Backgammon point-state query_id: {query}")


def target_points_for_state_query(points: Mapping[int, BackgammonPoint], *, query_id: str) -> Tuple[int, ...]:
    """Return numbered board points satisfying one point-state query."""

    return tuple(
        int(point)
        for point in POINT_IDS
        if point_matches_state_query(stack_at(points, int(point)), query_id=str(query_id))
    )


def validate_backgammon_sample(sample: BackgammonSample) -> None:
    """Validate the generated Backgammon sample against the public contract."""

    if tuple(int(value) for value in sample.dice) != tuple(sample.dice):
        raise ValueError("dice must be integers")
    if len(set(int(value) for value in sample.dice)) != len(sample.dice):
        raise ValueError("Backgammon calibration scenes avoid doubles")
    if any(int(value) < 1 or int(value) > 6 for value in sample.dice):
        raise ValueError("dice values must be in 1..6")
    for point in POINT_IDS:
        stack = stack_at(sample.points, point)
        if stack.owner is None:
            if int(stack.count) != 0:
                raise ValueError("empty points must have count 0")
            continue
        if str(stack.owner) not in {PLAYER_BLACK, PLAYER_WHITE}:
            raise ValueError(f"unsupported checker owner: {stack.owner}")
        if int(stack.count) < 1:
            raise ValueError("occupied points must have positive checker count")
    if str(sample.active_player) not in {PLAYER_BLACK, PLAYER_WHITE}:
        raise ValueError(f"unsupported active player: {sample.active_player}")
    if str(sample.query_id) in BACKGAMMON_DESTINATION_QUERY_IDS:
        outcome = compute_single_die_destinations(
            sample.points,
            dice=sample.dice,
            active_player=str(sample.active_player),
        )
        expected = target_destinations_for_query(outcome, query_id=str(sample.query_id))
        if tuple(expected) != tuple(sample.target_destinations):
            raise ValueError("target destinations do not match recomputed outcome")
        if tuple(sample.target_points or sample.target_destinations) != tuple(expected):
            raise ValueError("target points do not match target destinations")
        if int(sample.answer) != len(expected):
            raise ValueError("answer does not match target destination count")
        return
    if str(sample.query_id) in BACKGAMMON_POINT_STATE_QUERY_IDS:
        expected_points = target_points_for_state_query(sample.points, query_id=str(sample.query_id))
        if tuple(expected_points) != tuple(sample.target_points):
            raise ValueError("target points do not match recomputed point-state query")
        if tuple(sample.target_destinations):
            raise ValueError("point-state queries must not report target destinations")
        if int(sample.answer) != len(expected_points):
            raise ValueError("answer does not match target point count")
        return
    raise ValueError(f"unsupported Backgammon query_id: {sample.query_id}")


__all__ = [
    "BACKGAMMON_QUERY_IDS",
    "BACKGAMMON_DESTINATION_QUERY_IDS",
    "BACKGAMMON_POINT_STATE_QUERY_IDS",
    "BACKGAMMON_STYLE_VARIANTS",
    "PLAYER_BLACK",
    "PLAYER_WHITE",
    "POINT_IDS",
    "BackgammonOutcome",
    "BackgammonPoint",
    "BackgammonSample",
    "checker_entity_id",
    "compute_black_single_die_destinations",
    "compute_single_die_destinations",
    "destination_for_player",
    "die_entity_id",
    "empty_points",
    "is_blocked_by_white",
    "is_blocked_by_opponent",
    "is_opponent_blot",
    "is_white_blot",
    "opponent_for_player",
    "point_matches_state_query",
    "point_entity_id",
    "stack_at",
    "target_destinations_for_query",
    "target_points_for_state_query",
    "validate_backgammon_sample",
]
