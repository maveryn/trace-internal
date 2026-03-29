"""Shared temporal-domain helpers for clocks, calendars, and schedule time labels."""

from __future__ import annotations

from typing import Tuple


MINUTES_PER_CLOCK_CYCLE = 12 * 60
WEEKDAY_NAMES: Tuple[str, ...] = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
WEEKDAY_ABBREVIATIONS: Tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTH_NAMES: Tuple[str, ...] = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


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


def weekday_name(weekday_index: int) -> str:
    """Return the full weekday name for a Monday-first weekday index."""

    index = int(weekday_index)
    if not 0 <= index < len(WEEKDAY_NAMES):
        raise ValueError("weekday_index must be in 0..6")
    return str(WEEKDAY_NAMES[index])


def weekday_abbreviation(weekday_index: int) -> str:
    """Return the short weekday label for a Monday-first weekday index."""

    index = int(weekday_index)
    if not 0 <= index < len(WEEKDAY_ABBREVIATIONS):
        raise ValueError("weekday_index must be in 0..6")
    return str(WEEKDAY_ABBREVIATIONS[index])


def month_name(month_index: int) -> str:
    """Return the full month name for a one-based Gregorian month index."""

    index = int(month_index)
    if not 1 <= index <= 12:
        raise ValueError("month_index must be in 1..12")
    return str(MONTH_NAMES[index])


def ordinal_label(value: int) -> str:
    """Return one English ordinal label such as ``1st`` or ``3rd``."""

    number = int(value)
    if number <= 0:
        raise ValueError("ordinal_label requires a positive integer")
    if 10 <= (number % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def format_day_time_hhmm(total_minutes: int) -> str:
    """Format one day-time minute count as zero-padded 24-hour ``HH:MM``."""

    total = int(total_minutes)
    hour = int(total // 60)
    minute = int(total % 60)
    if not 0 <= hour <= 23:
        raise ValueError("format_day_time_hhmm requires total_minutes within one day")
    if not 0 <= minute <= 59:
        raise ValueError("format_day_time_hhmm requires minute remainder within 0..59")
    return f"{int(hour):02d}:{int(minute):02d}"


__all__ = [
    "MONTH_NAMES",
    "MINUTES_PER_CLOCK_CYCLE",
    "WEEKDAY_ABBREVIATIONS",
    "WEEKDAY_NAMES",
    "add_clock_minutes",
    "clock_hand_angle_gap_deg",
    "clock_total_minutes",
    "format_day_time_hhmm",
    "format_clock_hhmm",
    "month_name",
    "ordinal_label",
    "split_clock_total_minutes",
    "weekday_abbreviation",
    "weekday_name",
]
