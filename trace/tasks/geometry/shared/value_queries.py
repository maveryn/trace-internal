"""Reusable value-query operators for tasks with candidate value sets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class QueryOutcome:
    """Result of executing one value-query type over candidates."""

    answer_value: int
    selected_ids: list[str]
    selected_values: list[int]
    aux: Dict[str, Any]


def supported_value_query_types() -> list[str]:
    """Canonical value-query types supported by this shared utility."""
    return [
        "min",
        "max",
        "median",
        "closest_to_x",
        "smallest_above_x",
        "largest_below_x",
        "difference_max_min",
    ]


def _ensure_unique_mapping(values_by_id: Mapping[str, int]) -> None:
    """Enforce one-to-one id/value mapping for unique-answer query semantics."""
    seen: Dict[int, str] = {}
    for entity_id, value in values_by_id.items():
        ivalue = int(value)
        if ivalue in seen:
            raise ValueError(
                f"duplicate candidate values are not allowed for unique-answer queries: {ivalue}"
            )
        seen[ivalue] = str(entity_id)


def _id_for_value(values_by_id: Mapping[str, int], value: int) -> str:
    """Return the unique candidate id associated with a concrete value."""
    matches = [entity_id for entity_id, candidate_value in values_by_id.items() if int(candidate_value) == int(value)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one id for value {value}, found {len(matches)}")
    return str(matches[0])


def run_value_query(
    values_by_id: Mapping[str, int],
    *,
    query_type: str,
    target_x: int | None = None,
) -> QueryOutcome:
    """Execute one value query and return answer + selected candidate ids."""
    if not values_by_id:
        raise ValueError("values_by_id must be non-empty")

    allowed = set(supported_value_query_types())
    query = str(query_type)
    if query not in allowed:
        raise ValueError(f"unsupported query_type: {query}")

    _ensure_unique_mapping(values_by_id)
    values = sorted(int(v) for v in values_by_id.values())

    if query == "min":
        value = values[0]
        selected_ids = [_id_for_value(values_by_id, value)]
        return QueryOutcome(answer_value=value, selected_ids=selected_ids, selected_values=[value], aux={})

    if query == "max":
        value = values[-1]
        selected_ids = [_id_for_value(values_by_id, value)]
        return QueryOutcome(answer_value=value, selected_ids=selected_ids, selected_values=[value], aux={})

    if query == "median":
        if len(values) % 2 == 0:
            raise ValueError("median query requires an odd number of candidates")
        value = values[len(values) // 2]
        selected_ids = [_id_for_value(values_by_id, value)]
        return QueryOutcome(answer_value=value, selected_ids=selected_ids, selected_values=[value], aux={})

    if query == "closest_to_x":
        if target_x is None:
            raise ValueError("closest_to_x query requires target_x")
        target = int(target_x)
        distances = [(abs(value - target), value) for value in values]
        distances.sort()
        if len(distances) > 1 and distances[0][0] == distances[1][0]:
            raise ValueError("closest_to_x tie detected")
        value = int(distances[0][1])
        selected_ids = [_id_for_value(values_by_id, value)]
        return QueryOutcome(
            answer_value=value,
            selected_ids=selected_ids,
            selected_values=[value],
            aux={"target_x": target, "distance": int(abs(value - target))},
        )

    if query == "smallest_above_x":
        if target_x is None:
            raise ValueError("smallest_above_x query requires target_x")
        target = int(target_x)
        above = [value for value in values if value > target]
        if not above:
            raise ValueError("no value above target_x")
        value = above[0]
        selected_ids = [_id_for_value(values_by_id, value)]
        return QueryOutcome(
            answer_value=value,
            selected_ids=selected_ids,
            selected_values=[value],
            aux={"target_x": target, "margin": int(value - target)},
        )

    if query == "largest_below_x":
        if target_x is None:
            raise ValueError("largest_below_x query requires target_x")
        target = int(target_x)
        below = [value for value in values if value < target]
        if not below:
            raise ValueError("no value below target_x")
        value = below[-1]
        selected_ids = [_id_for_value(values_by_id, value)]
        return QueryOutcome(
            answer_value=value,
            selected_ids=selected_ids,
            selected_values=[value],
            aux={"target_x": target, "margin": int(target - value)},
        )

    if query == "difference_max_min":
        min_value = values[0]
        max_value = values[-1]
        max_id = _id_for_value(values_by_id, max_value)
        min_id = _id_for_value(values_by_id, min_value)
        return QueryOutcome(
            answer_value=int(max_value - min_value),
            selected_ids=[max_id, min_id],
            selected_values=[max_value, min_value],
            aux={"max_value": max_value, "min_value": min_value},
        )

    raise ValueError(f"unhandled query_type: {query}")
