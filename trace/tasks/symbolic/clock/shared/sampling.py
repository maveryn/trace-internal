"""Sampling primitives for symbolic clock-display scenes."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ....shared.config_defaults import group_default
from ....shared.time_format import clock_hand_angle_gap_deg, clock_total_minutes


def resolve_clock_time_support(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    fallback_hour_min: int,
    fallback_hour_max: int,
    fallback_minute_min: int,
    fallback_minute_max: int,
    fallback_minute_step: int,
    context: str,
) -> Tuple[Tuple[int, int], Tuple[int, int, int], Tuple[int, ...]]:
    """Resolve hour/minute supports and canonical 12-hour clock times."""

    hour_min = int(params.get("hour_min", group_default(gen_defaults, "hour_min", fallback_hour_min)))
    hour_max = int(params.get("hour_max", group_default(gen_defaults, "hour_max", fallback_hour_max)))
    minute_min = int(params.get("minute_min", group_default(gen_defaults, "minute_min", fallback_minute_min)))
    minute_max = int(params.get("minute_max", group_default(gen_defaults, "minute_max", fallback_minute_max)))
    minute_step = int(params.get("minute_step", group_default(gen_defaults, "minute_step", fallback_minute_step)))
    if not (1 <= hour_min <= hour_max <= 12):
        raise ValueError(f"{context} hours must satisfy 1 <= min <= max <= 12")
    if not (0 <= minute_min <= minute_max <= 59):
        raise ValueError(f"{context} minutes must satisfy 0 <= min <= max <= 59")
    if minute_step <= 0:
        raise ValueError(f"{context} minute_step must be positive")
    values = tuple(
        clock_total_minutes(hour, minute)
        for hour in range(hour_min, hour_max + 1)
        for minute in range(minute_min, minute_max + 1, minute_step)
    )
    return (int(hour_min), int(hour_max)), (int(minute_min), int(minute_max), int(minute_step)), values


def feasible_clock_times(times: Tuple[int, ...], *, min_hand_angle_gap_deg: float) -> Tuple[int, ...]:
    """Filter time values to analog displays with separated hour/minute hands."""

    return tuple(
        int(total)
        for total in times
        if float(clock_hand_angle_gap_deg(int(total))) >= float(min_hand_angle_gap_deg)
    )


__all__ = ["feasible_clock_times", "resolve_clock_time_support"]
