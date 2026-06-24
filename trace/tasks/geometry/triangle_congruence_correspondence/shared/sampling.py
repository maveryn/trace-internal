"""Sampling primitives for triangle-congruence correspondence cases."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Mapping, Sequence, TypeVar

from trace.core.seed import spawn_rng

T = TypeVar("T")


def choose_case_by_answer(
    *,
    cases: Sequence[T],
    answer_fn: Callable[[T], int],
    params: Mapping[str, object],
    instance_seed: int,
    namespace: str,
) -> tuple[T, dict[str, float]]:
    """Sample answer support uniformly, then sample one construction for it."""

    answer_to_cases: dict[int, list[T]] = defaultdict(list)
    for case in cases:
        answer_to_cases[int(answer_fn(case))].append(case)
    if not answer_to_cases:
        raise ValueError("empty triangle-congruence case pool")
    forced_answer = params.get("target_answer")
    answers = sorted(answer_to_cases)
    if forced_answer is not None:
        answer = int(forced_answer)
        if answer not in answer_to_cases:
            raise ValueError(f"target_answer={answer!r} is not supported")
    else:
        answer_rng = spawn_rng(int(instance_seed), f"{namespace}.answer")
        answer = int(answers[int(answer_rng.randrange(len(answers)))])
    variants = tuple(answer_to_cases[answer])
    variant_rng = spawn_rng(int(instance_seed), f"{namespace}.variant.{answer}")
    selected = variants[int(variant_rng.randrange(len(variants)))]
    probability = 1.0 / float(len(answers))
    return selected, {str(value): probability for value in answers}


__all__ = ["choose_case_by_answer"]
