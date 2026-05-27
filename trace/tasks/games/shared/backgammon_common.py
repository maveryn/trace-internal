"""Shared Backgammon rules and scene contracts for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple


BACKGAMMON_QUERY_VARIANTS: Tuple[str, ...] = (
    "legal_move_count",
    "hit_move_count",
    "blocked_destination_count",
)
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
    """Computed single-die destination sets for black-to-move scenes."""

    legal_destinations: Tuple[int, ...]
    hit_destinations: Tuple[int, ...]
    blocked_destinations: Tuple[int, ...]


@dataclass(frozen=True)
class BackgammonSample:
    """One generated Backgammon position plus answer/evidence contract."""

    points: Mapping[int, BackgammonPoint]
    dice: Tuple[int, int]
    query_variant: str
    answer: int
    target_destinations: Tuple[int, ...]
    outcome: BackgammonOutcome
    style_variant: str
    target_answer: int


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


def compute_black_single_die_destinations(
    points: Mapping[int, BackgammonPoint],
    *,
    dice: Tuple[int, int],
) -> BackgammonOutcome:
    """Compute destination-point sets for black moving from high points to low points."""

    candidate_destinations: set[int] = set()
    for source in POINT_IDS:
        stack = stack_at(points, int(source))
        if str(stack.owner) != PLAYER_BLACK or int(stack.count) <= 0:
            continue
        for die in dice:
            dest = int(source) - int(die)
            if int(dest) in POINT_IDS:
                candidate_destinations.add(int(dest))

    blocked = tuple(sorted(point for point in candidate_destinations if is_blocked_by_white(points, point)))
    legal = tuple(sorted(point for point in candidate_destinations if point not in set(blocked)))
    hit = tuple(sorted(point for point in legal if is_white_blot(points, point)))
    return BackgammonOutcome(
        legal_destinations=legal,
        hit_destinations=hit,
        blocked_destinations=blocked,
    )


def target_destinations_for_query(outcome: BackgammonOutcome, *, query_variant: str) -> Tuple[int, ...]:
    """Return the query-specific destination set."""

    query = str(query_variant)
    if query == "legal_move_count":
        return tuple(outcome.legal_destinations)
    if query == "hit_move_count":
        return tuple(outcome.hit_destinations)
    if query == "blocked_destination_count":
        return tuple(outcome.blocked_destinations)
    raise ValueError(f"unsupported Backgammon query_variant: {query}")


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
    outcome = compute_black_single_die_destinations(sample.points, dice=sample.dice)
    expected = target_destinations_for_query(outcome, query_variant=str(sample.query_variant))
    if tuple(expected) != tuple(sample.target_destinations):
        raise ValueError("target destinations do not match recomputed outcome")
    if int(sample.answer) != len(expected):
        raise ValueError("answer does not match target destination count")


__all__ = [
    "BACKGAMMON_QUERY_VARIANTS",
    "BACKGAMMON_STYLE_VARIANTS",
    "PLAYER_BLACK",
    "PLAYER_WHITE",
    "POINT_IDS",
    "BackgammonOutcome",
    "BackgammonPoint",
    "BackgammonSample",
    "checker_entity_id",
    "compute_black_single_die_destinations",
    "die_entity_id",
    "empty_points",
    "is_blocked_by_white",
    "is_white_blot",
    "point_entity_id",
    "stack_at",
    "target_destinations_for_query",
    "validate_backgammon_sample",
]
