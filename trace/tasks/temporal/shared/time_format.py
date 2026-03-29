"""Shared temporal-domain helpers for analog-clock time formatting and offsets."""

from __future__ import annotations

from typing import Tuple


MINUTES_PER_CLOCK_CYCLE = 12 * 60


def clock_total_minutes(hour_12: int, minute: int) -> int:
    """Return canonical total minutes on a 12-hour clock."""

    hour = int(hour_12)
    minute_value = int(minute)
    if not 1 <= hour <= 12:
        raise ValueError("hour_12 must be in 1..12")
    if not 0 <= minute_value <= 59:
        raise ValueError("minute must be in 0..59")
    normalized_hour = 0 if int(hour) == 12 else int(hour)
    return int((normalized_hour * 60) + minute_value)


def split_clock_total_minutes(total_minutes: int) -> Tuple[int, int]:
    """Return `(hour_12, minute)` from canonical 12-hour total minutes."""

    total = int(total_minutes) % int(MINUTES_PER_CLOCK_CYCLE)
    hour_24_mod = int(total // 60)
    minute = int(total % 60)
    hour_12 = 12 if int(hour_24_mod) == 0 else int(hour_24_mod)
    return int(hour_12), int(minute)


def format_clock_hhmm(total_minutes: int) -> str:
    """Format one canonical 12-hour clock time as zero-padded `HH:MM`."""

    hour_12, minute = split_clock_total_minutes(int(total_minutes))
    return f"{int(hour_12):02d}:{int(minute):02d}"


def clock_hand_angle_gap_deg(total_minutes: int) -> float:
    """Return the smaller absolute angle gap between the two analog-clock hands."""

    shown_hour, shown_minute = split_clock_total_minutes(int(total_minutes))
    hour_angle = (30.0 * float(shown_hour % 12)) + (0.5 * float(shown_minute))
    minute_angle = 6.0 * float(shown_minute)
    raw_gap = abs(float(hour_angle) - float(minute_angle)) % 360.0
    return float(min(raw_gap, 360.0 - raw_gap))


def add_clock_minutes(total_minutes: int, delta_minutes: int) -> int:
    """Advance or rewind one 12-hour clock value by `delta_minutes`."""

    return int(int(total_minutes) + int(delta_minutes)) % int(MINUTES_PER_CLOCK_CYCLE)


__all__ = [
    "MINUTES_PER_CLOCK_CYCLE",
    "add_clock_minutes",
    "clock_hand_angle_gap_deg",
    "clock_total_minutes",
    "format_clock_hhmm",
    "split_clock_total_minutes",
]
