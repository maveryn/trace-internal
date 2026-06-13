"""Dartboard scoring rules for darts scene tasks."""

from __future__ import annotations

from typing import List, Mapping, Tuple

from .rendering import DARTBOARD_SAMPLE_RADIUS_FRACTIONS, STANDARD_DART_SECTORS
from .state import DartsScoreSlot


RING_RADIUS_FRACTIONS: Mapping[str, Tuple[float, float]] = DARTBOARD_SAMPLE_RADIUS_FRACTIONS
_RING_SCORE_KIND = {
    "inner_bull": "bull",
    "outer_bull": "bull",
    "inner_single": "single",
    "outer_single": "single",
    "triple": "triple",
    "double": "double",
}


def score_slot_public_ring(slot: DartsScoreSlot) -> str:
    """Return the prompt-facing ring family for one slot."""

    return _RING_SCORE_KIND[str(slot.ring)]


def score_slot_in_ring(slot: DartsScoreSlot, *, target_ring: str) -> bool:
    """Return whether one score slot belongs to the requested public ring."""

    return str(score_slot_public_ring(slot)) == str(target_ring)


def score_slot_at_least(slot: DartsScoreSlot, *, threshold: int) -> bool:
    """Return whether one score slot meets a score threshold."""

    return int(slot.score) >= int(threshold)


def _all_score_slots() -> Tuple[DartsScoreSlot, ...]:
    """Return the supported dart scoring slots."""

    slots: List[DartsScoreSlot] = [
        DartsScoreSlot(sector_value=None, ring="inner_bull", score=50),
        DartsScoreSlot(sector_value=None, ring="outer_bull", score=25),
    ]
    for sector_value in STANDARD_DART_SECTORS:
        slots.extend(
            (
                DartsScoreSlot(sector_value=int(sector_value), ring="inner_single", score=int(sector_value)),
                DartsScoreSlot(sector_value=int(sector_value), ring="outer_single", score=int(sector_value)),
                DartsScoreSlot(sector_value=int(sector_value), ring="triple", score=int(sector_value) * 3),
                DartsScoreSlot(sector_value=int(sector_value), ring="double", score=int(sector_value) * 2),
            )
        )
    return tuple(slots)


SCORE_SLOTS = _all_score_slots()


__all__ = [
    "RING_RADIUS_FRACTIONS",
    "SCORE_SLOTS",
    "score_slot_at_least",
    "score_slot_in_ring",
    "score_slot_public_ring",
]
