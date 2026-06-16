"""Identity-free case sampling for concentric-chord diagrams."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .state import ConcentricChordCase

MIN_INNER_RADIUS_RATIO = 0.25
MAX_INNER_RADIUS_RATIO = 0.80
MAX_OUTER_RADIUS = 300

IndexedConcentricChordCase = tuple[int, ConcentricChordCase]


def _validate_case(case: ConcentricChordCase) -> ConcentricChordCase:
    if int(case.outer_radius) ** 2 != int(case.inner_radius) ** 2 + int(case.half_chord) ** 2:
        raise ValueError("concentric chord case must satisfy R^2 = r^2 + (c/2)^2")
    ratio = float(case.inner_radius) / float(case.outer_radius)
    if ratio < MIN_INNER_RADIUS_RATIO or ratio > MAX_INNER_RADIUS_RATIO:
        raise ValueError("concentric chord case must keep visible circle separation")
    return case


def _build_pythagorean_cases() -> tuple[ConcentricChordCase, ...]:
    cases: list[ConcentricChordCase] = []
    for outer_radius in range(5, MAX_OUTER_RADIUS + 1):
        for inner_radius in range(2, outer_radius):
            half_chord_squared = (outer_radius * outer_radius) - (inner_radius * inner_radius)
            half_chord = int(half_chord_squared**0.5)
            if half_chord * half_chord != half_chord_squared:
                continue
            case = ConcentricChordCase(
                outer_radius=int(outer_radius),
                inner_radius=int(inner_radius),
                half_chord=int(half_chord),
            )
            try:
                cases.append(_validate_case(case))
            except ValueError:
                continue
    if not cases:
        raise RuntimeError("concentric chord case pool must not be empty")
    return tuple(cases)


PYTHAGOREAN_CASES: tuple[ConcentricChordCase, ...] = _build_pythagorean_cases()


def _answer_key(value: Any) -> str:
    if isinstance(value, float):
        return f"{float(value):.1f}"
    return str(value)


def _answer_sort_key(key: str) -> tuple[int, float | str]:
    try:
        return (0, float(key))
    except ValueError:
        return (1, str(key))


def group_concentric_chord_cases_by_answer(
    *,
    answer_fn: Callable[[ConcentricChordCase], Any],
    cases: Sequence[ConcentricChordCase] = PYTHAGOREAN_CASES,
) -> dict[str, tuple[IndexedConcentricChordCase, ...]]:
    """Group indexed cases by the final answer exposed by one public task."""

    grouped: dict[str, list[IndexedConcentricChordCase]] = defaultdict(list)
    for index, case in enumerate(cases):
        grouped[_answer_key(answer_fn(case))].append((int(index), case))
    if not grouped:
        raise ValueError("answer-balanced concentric chord pool must not be empty")
    return {key: tuple(values) for key, values in grouped.items()}


def _balanced_answer_index(
    *,
    answer_count: int,
    instance_seed: int,
    namespace: str,
) -> int:
    if int(answer_count) <= 0:
        raise ValueError("answer_count must be positive")
    offset = resolve_selection_index(
        params={},
        instance_seed=0,
        namespace=f"{namespace}.answer_offset",
    )
    return int(int(instance_seed) + int(offset)) % int(answer_count)


def select_answer_balanced_concentric_chord_case(
    *,
    answer_cases: Mapping[str, Sequence[IndexedConcentricChordCase]],
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[ConcentricChordCase, int, dict[str, float]]:
    """Select a case by target answer first, then by case within that answer."""

    keys = tuple(sorted((str(key) for key in answer_cases), key=_answer_sort_key))
    if not keys:
        raise ValueError("answer_cases must contain at least one answer")
    support_probabilities = {key: 1.0 / float(len(keys)) for key in keys}

    explicit_case = params.get("case_index")
    if explicit_case is not None:
        case_index = int(explicit_case) % len(PYTHAGOREAN_CASES)
        case = PYTHAGOREAN_CASES[int(case_index)]
        return _validate_case(case), int(case_index), support_probabilities

    answer_index = _balanced_answer_index(
        answer_count=len(keys),
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    answer = keys[int(answer_index)]
    cases = tuple(answer_cases[str(answer)])
    case_selection = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.case.{answer}",
    )
    case_index, case = cases[int(case_selection) % len(cases)]
    return _validate_case(case), int(case_index), support_probabilities


def select_concentric_chord_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[ConcentricChordCase, int]:
    """Select one case, honoring explicit review/debug measurement overrides."""

    explicit_case = params.get("case_index")
    if explicit_case is not None:
        index = int(explicit_case) % len(PYTHAGOREAN_CASES)
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
        index = int(selection_index) % len(PYTHAGOREAN_CASES)
    base_case = PYTHAGOREAN_CASES[int(index)]
    case = ConcentricChordCase(
        outer_radius=int(params.get("outer_radius", base_case.outer_radius)),
        inner_radius=int(params.get("inner_radius", base_case.inner_radius)),
        half_chord=int(params.get("half_chord", base_case.half_chord)),
    )
    return _validate_case(case), int(index)


__all__ = [
    "MAX_INNER_RADIUS_RATIO",
    "MIN_INNER_RADIUS_RATIO",
    "PYTHAGOREAN_CASES",
    "group_concentric_chord_cases_by_answer",
    "select_answer_balanced_concentric_chord_case",
    "select_concentric_chord_case",
]
