"""Prompt slot helpers for multiseries comparison tasks."""

from __future__ import annotations

from typing import Dict


def _ordinal(value: int) -> str:
    """Return a compact English ordinal for prompt slots."""

    if 10 <= int(value) % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(int(value) % 10, "th")
    return f"{int(value)}{suffix}"


def _ranked_phrase(rank: int, base: str) -> str:
    """Return natural rank wording for an extremum phrase."""

    if int(rank) == 1:
        return str(base)
    return f"{_ordinal(int(rank))} {str(base)}"

def _comparison_phrase(comparison: str) -> str:
    """Return prompt wording for one strict comparator."""

    if str(comparison) == "greater_than":
        return "higher than"
    if str(comparison) == "less_than":
        return "lower than"
    raise ValueError(f"unsupported comparison: {comparison}")


def _conditional_gap_aggregate_prompt_slots(aggregate_kind: str | None) -> Dict[str, str]:
    """Return prompt wording for one conditional-gap aggregate kind."""

    if str(aggregate_kind) == "sum":
        return {
            "conditional_gap_aggregate_kind": "sum",
            "conditional_gap_aggregate_instruction": "sum",
        }
    if str(aggregate_kind) == "mean":
        return {
            "conditional_gap_aggregate_kind": "mean",
            "conditional_gap_aggregate_instruction": "integer average",
        }
    if str(aggregate_kind) == "range":
        return {
            "conditional_gap_aggregate_kind": "range",
            "conditional_gap_aggregate_instruction": "range, meaning largest minus smallest",
        }
    return {
        "conditional_gap_aggregate_kind": "",
        "conditional_gap_aggregate_instruction": "",
    }

def _change_prompt_slots(change_direction: str | None) -> Dict[str, str]:
    """Return prompt slots for directional-change queries."""

    if str(change_direction) == "increase":
        return {
            "change_direction": "increase",
            "change_expression": "the second queried series minus the first queried series",
            "change_action": "increase from first to second",
        }
    if str(change_direction) == "decrease":
        return {
            "change_direction": "decrease",
            "change_expression": "the first queried series minus the second queried series",
            "change_action": "decrease from first to second",
        }
    return {
        "change_direction": "",
        "change_expression": "",
        "change_action": "",
    }


def _change_measure_prompt_slots(change_measure: str | None, change_direction: str | None) -> Dict[str, str]:
    """Return prompt wording for the sampled change measure."""

    if str(change_measure) == "directional_change":
        return {
            "change_measure": "directional change",
            "change_measure_prompt": str(_change_prompt_slots(change_direction)["change_action"]),
        }
    if str(change_measure) == "absolute_gap":
        return {
            "change_measure": "absolute gap",
            "change_measure_prompt": "absolute gap",
        }
    return {
        "change_measure": "",
        "change_measure_prompt": "",
    }


def _extremum_prompt_slots(extremum_direction: str | None, *, answer_rank: int) -> Dict[str, str]:
    """Return prompt slots for largest/smallest extremum wording."""

    if str(extremum_direction) == "smallest":
        return {
            "extremum_direction": "smallest",
            "ranked_extremum": _ranked_phrase(int(answer_rank), "smallest"),
        }
    return {
        "extremum_direction": "largest",
        "ranked_extremum": _ranked_phrase(int(answer_rank), "largest"),
    }


def _ratio_measure_prompt_slots(
    ratio_measure: str | None,
    *,
    target_series: str,
    numerator_series: str,
    denominator_series: str,
) -> Dict[str, str]:
    """Return prompt wording for the sampled ratio measure."""

    if str(ratio_measure) == "series_share":
        return {
            "ratio_measure": "series share",
            "ratio_measure_prompt": f'percentage share for "{str(target_series)}" out of each category total',
        }
    if str(ratio_measure) == "pair_ratio":
        return {
            "ratio_measure": "pair ratio",
            "ratio_measure_prompt": f'percentage ratio of "{str(numerator_series)}" to "{str(denominator_series)}"',
        }
    return {
        "ratio_measure": "",
        "ratio_measure_prompt": "",
    }
