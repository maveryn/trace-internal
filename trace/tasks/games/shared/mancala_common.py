"""Shared Mancala rules helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple


TOP = -1
BOTTOM = 1


@dataclass(frozen=True)
class MancalaState:
    """Visible Kalah-style Mancala state used by games tasks."""

    top_pits: Tuple[int, ...]
    bottom_pits: Tuple[int, ...]
    top_store: int
    bottom_store: int


@dataclass(frozen=True)
class MancalaMoveOutcome:
    """Outcome for one bottom-row starting pit."""

    start_index: int
    stones: int
    last_cup_kind: str
    last_cup_index: int | None
    grants_extra_turn: bool
    causes_capture: bool
    captured_opposite_index: int | None


def player_name(player: int) -> str:
    """Return the prompt-facing player name for one Mancala side."""

    return "Blue" if int(player) == int(BOTTOM) else "Orange"


def pit_entity_id(*, side: str, index: int) -> str:
    """Return one stable entity id for a pit."""

    return f"{str(side)}_pit_{int(index)}"


def store_entity_id(*, side: str) -> str:
    """Return one stable entity id for a store."""

    return f"{str(side)}_store"


def total_stones(state: MancalaState) -> int:
    """Return the total number of visible stones in one state."""

    return int(sum(int(value) for value in state.top_pits + state.bottom_pits) + int(state.top_store) + int(state.bottom_store))


def _to_internal_cycle(state: MancalaState) -> List[int]:
    """Return the bottom-player sowing cycle with the opponent store in slot 13."""

    internal = [0 for _ in range(14)]
    for index, value in enumerate(state.bottom_pits):
        internal[int(index)] = int(value)
    internal[6] = int(state.bottom_store)
    for internal_index, display_index in zip(range(7, 13), range(5, -1, -1)):
        internal[int(internal_index)] = int(state.top_pits[int(display_index)])
    internal[13] = int(state.top_store)
    return internal


def evaluate_bottom_moves(state: MancalaState) -> Tuple[MancalaMoveOutcome, ...]:
    """Return one move outcome for each bottom-row pit, treating Blue as the player to move."""

    original_internal = _to_internal_cycle(state)
    outcomes: List[MancalaMoveOutcome] = []
    for start_index in range(6):
        stones = int(original_internal[int(start_index)])
        if int(stones) <= 0:
            outcomes.append(
                MancalaMoveOutcome(
                    start_index=int(start_index),
                    stones=int(stones),
                    last_cup_kind="empty",
                    last_cup_index=None,
                    grants_extra_turn=False,
                    causes_capture=False,
                    captured_opposite_index=None,
                )
            )
            continue
        internal = list(int(value) for value in original_internal)
        internal[int(start_index)] = 0
        cursor = int(start_index)
        remaining = int(stones)
        while int(remaining) > 0:
            cursor = int((int(cursor) + 1) % 14)
            if int(cursor) == 13:
                continue
            internal[int(cursor)] += 1
            remaining -= 1
        grants_extra_turn = int(cursor) == 6
        causes_capture = False
        captured_opposite_index: int | None = None
        if 0 <= int(cursor) <= 5:
            opposite_internal = int(12 - int(cursor))
            if int(internal[int(cursor)]) == 1 and int(original_internal[int(cursor)]) == 0 and int(internal[int(opposite_internal)]) > 0:
                causes_capture = True
                captured_opposite_index = int(cursor)
        if int(cursor) == 6:
            last_cup_kind = "bottom_store"
            last_cup_index = None
        elif 0 <= int(cursor) <= 5:
            last_cup_kind = "bottom_pit"
            last_cup_index = int(cursor)
        else:
            last_cup_kind = "top_pit"
            last_cup_index = int(12 - int(cursor))
        outcomes.append(
            MancalaMoveOutcome(
                start_index=int(start_index),
                stones=int(stones),
                last_cup_kind=str(last_cup_kind),
                last_cup_index=last_cup_index,
                grants_extra_turn=bool(grants_extra_turn),
                causes_capture=bool(causes_capture),
                captured_opposite_index=captured_opposite_index,
            )
        )
    return tuple(outcomes)


__all__ = [
    "BOTTOM",
    "MancalaMoveOutcome",
    "MancalaState",
    "TOP",
    "evaluate_bottom_moves",
    "pit_entity_id",
    "player_name",
    "store_entity_id",
    "total_stones",
]
