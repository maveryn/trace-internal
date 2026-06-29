"""Matchstick-number transition rules."""

from __future__ import annotations

from typing import Dict, List, Tuple


DIGIT_SEGMENTS: Dict[int, frozenset[str]] = {
    0: frozenset(("a", "b", "c", "d", "e", "f")),
    1: frozenset(("b", "c")),
    2: frozenset(("a", "b", "g", "e", "d")),
    3: frozenset(("a", "b", "c", "d", "g")),
    4: frozenset(("f", "g", "b", "c")),
    5: frozenset(("a", "f", "g", "c", "d")),
    6: frozenset(("a", "f", "e", "d", "c", "g")),
    7: frozenset(("a", "b", "c")),
    8: frozenset(("a", "b", "c", "d", "e", "f", "g")),
    9: frozenset(("a", "b", "c", "d", "f", "g")),
}
SEGMENT_POINTS: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]] = {
    "a": ((0.0, 0.0), (1.0, 0.0)),
    "b": ((1.0, 0.0), (1.0, 1.0)),
    "c": ((1.0, 1.0), (1.0, 2.0)),
    "d": ((0.0, 2.0), (1.0, 2.0)),
    "e": ((0.0, 1.0), (0.0, 2.0)),
    "f": ((0.0, 0.0), (0.0, 1.0)),
    "g": ((0.0, 1.0), (1.0, 1.0)),
}


def number_digits(value: int) -> Tuple[int, int]:
    """Return the two seven-segment digits for one rendered number."""

    text = f"{int(value):02d}"
    return int(text[0]), int(text[1])


def number_text(value: int) -> str:
    """Format one rendered matchstick number as two digits."""

    return f"{int(value):02d}"


def number_segment_keys(value: int) -> frozenset[str]:
    """Return stable segment ids for all sticks in a two-digit number."""

    keys: List[str] = []
    for digit_index, digit in enumerate(number_digits(int(value))):
        for segment in sorted(DIGIT_SEGMENTS[int(digit)]):
            keys.append(f"digit{digit_index}:{segment}")
    return frozenset(keys)


def number_transition_allowed(
    source_number: int,
    target_number: int,
    *,
    stick_delta: int,
) -> bool:
    """Return whether target is reachable by adding or removing one stick."""

    source = number_segment_keys(int(source_number))
    target = number_segment_keys(int(target_number))
    removed = source - target
    added = target - source
    if int(stick_delta) == 1:
        return not removed and len(added) == 1
    if int(stick_delta) == -1:
        return len(removed) == 1 and not added
    raise ValueError(f"unsupported matchstick stick_delta: {stick_delta}")


def changed_digit_index(source_number: int, target_number: int) -> int:
    """Return which of the two digits changed, or -1 if neither changed."""

    source_digits = number_digits(int(source_number))
    target_digits = number_digits(int(target_number))
    changed = [
        index
        for index, (left, right) in enumerate(zip(source_digits, target_digits))
        if int(left) != int(right)
    ]
    return int(changed[0]) if changed else -1


def number_segments(value: int) -> list[tuple[str, tuple[float, float], tuple[float, float]]]:
    """Return drawable segment ids and normalized endpoints for one number."""

    segments: list[tuple[str, tuple[float, float], tuple[float, float]]] = []
    gap = 0.42
    for digit_index, digit in enumerate(number_digits(int(value))):
        base_x = float(digit_index) * (1.0 + gap)
        for segment in sorted(DIGIT_SEGMENTS[int(digit)]):
            start, end = SEGMENT_POINTS[str(segment)]
            segments.append(
                (
                    f"digit{digit_index}:{segment}",
                    (base_x + start[0], start[1]),
                    (base_x + end[0], end[1]),
                )
            )
    return segments


__all__ = [
    "DIGIT_SEGMENTS",
    "SEGMENT_POINTS",
    "changed_digit_index",
    "number_segment_keys",
    "number_segments",
    "number_text",
    "number_transition_allowed",
]
