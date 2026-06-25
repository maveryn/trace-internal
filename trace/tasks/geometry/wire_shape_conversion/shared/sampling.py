"""Sampling helpers for wire-shape-conversion case pools."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .construction import Case, Resolver, answer_support, case_key


def _coerce_case(value: Any) -> Case:
    if isinstance(value, int):
        return int(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(int(item) for item in value)
    raise ValueError("wire_case must be an integer or numeric sequence")


def select_case_by_answer_support(
    *,
    case_label: str,
    cases: Sequence[Case],
    resolver: Resolver,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[Case, dict[str, float], tuple[int, ...]]:
    """Select a case by first sampling a supported answer uniformly."""

    explicit = params.get("wire_case")
    if explicit is not None:
        selected_case = _coerce_case(explicit)
        selected_problem = resolver(selected_case)
        support = tuple(sorted(set((*answer_support(cases, resolver), int(selected_problem.answer)))))
        selected_key = case_key(str(case_label), selected_case)
        keys = tuple(case_key(str(case_label), candidate) for candidate in cases) + (selected_key,)
        return selected_case, {key: (1.0 if key == selected_key else 0.0) for key in dict.fromkeys(keys)}, support

    answer_to_cases: dict[int, list[Case]] = {}
    for candidate in cases:
        answer_to_cases.setdefault(int(resolver(candidate).answer), []).append(candidate)
    support = tuple(sorted(answer_to_cases))
    answer_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.answer",
    )
    selected_answer = support[int(answer_index) % len(support)]
    candidate_cases = tuple(answer_to_cases[int(selected_answer)])
    case_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.answer.{selected_answer}.case",
    )
    selected_case = candidate_cases[int(case_index) % len(candidate_cases)]

    case_probabilities: dict[str, float] = {}
    answer_probability = 1.0 / float(len(support))
    for answer, grouped_cases in answer_to_cases.items():
        probability = answer_probability / float(len(grouped_cases))
        for candidate in grouped_cases:
            case_probabilities[case_key(str(case_label), candidate)] = probability
    return selected_case, case_probabilities, support


__all__ = ["select_case_by_answer_support"]
