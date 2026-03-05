"""Shared answer-conditioned sampling helpers for value-query tasks.

These helpers build candidate value mappings where the target query answer is
fixed by construction, then verify the mapping through the canonical
`run_value_query` operator. They are deterministic given RNG state and inputs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from .value_queries import QueryOutcome, run_value_query


_TARGET_X_QUERY_TYPES = {"closest_to_x", "smallest_above_x", "largest_below_x"}


def resolve_candidate_count(
    rng,
    *,
    query_type: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    fallback_min: int,
    fallback_max: int,
) -> int:
    """Resolve candidate count with optional median odd-count constraint."""
    explicit_count = params.get("candidate_count", generation_defaults.get("candidate_count"))
    if explicit_count is not None:
        return int(explicit_count)

    count_min = int(params.get("candidate_count_min", generation_defaults.get("candidate_count_min", int(fallback_min))))
    count_max = int(params.get("candidate_count_max", generation_defaults.get("candidate_count_max", int(fallback_max))))
    if count_min > count_max:
        raise ValueError("candidate_count_min must be <= candidate_count_max")
    if count_min < 2:
        raise ValueError("candidate_count_min must be >= 2")

    candidate_counts = list(range(count_min, count_max + 1))
    if str(query_type) == "median":
        candidate_counts = [value for value in candidate_counts if value % 2 == 1]
        if not candidate_counts:
            raise ValueError("median query requires at least one odd candidate_count in range")
    return int(rng.choice(candidate_counts))


def _can_sample_values(*, options: List[int], count: int, allow_duplicates: bool) -> bool:
    """Return whether `count` values can be sampled from `options`."""
    required = int(count)
    if required <= 0:
        return True
    if not options:
        return False
    if bool(allow_duplicates):
        return True
    return len(options) >= required


def _sample_values_from_options(rng, *, options: List[int], count: int, allow_duplicates: bool) -> List[int] | None:
    """Sample values from one option pool, with or without replacement."""
    required = int(count)
    if required <= 0:
        return []
    if not _can_sample_values(options=options, count=required, allow_duplicates=allow_duplicates):
        return None
    if bool(allow_duplicates):
        return [int(rng.choice(options)) for _ in range(required)]
    return [int(value) for value in rng.sample(options, required)]


def feasible_answer_values(
    *,
    query_type: str,
    candidates: List[int],
    candidate_count: int,
    target_x: int,
    allow_duplicate_distractors: bool,
) -> List[int]:
    """Compute all answer values that are realizable for one query setting."""
    values = sorted(int(value) for value in candidates)
    query = str(query_type)
    n = int(candidate_count)
    target = int(target_x)

    if query == "min":
        return [
            int(answer)
            for answer in values
            if _can_sample_values(
                options=[value for value in values if value > answer],
                count=n - 1,
                allow_duplicates=allow_duplicate_distractors,
            )
        ]

    if query == "max":
        return [
            int(answer)
            for answer in values
            if _can_sample_values(
                options=[value for value in values if value < answer],
                count=n - 1,
                allow_duplicates=allow_duplicate_distractors,
            )
        ]

    if query == "median":
        half = n // 2
        return [
            int(answer)
            for answer in values
            if _can_sample_values(
                options=[value for value in values if value < answer],
                count=half,
                allow_duplicates=allow_duplicate_distractors,
            )
            and _can_sample_values(
                options=[value for value in values if value > answer],
                count=half,
                allow_duplicates=allow_duplicate_distractors,
            )
        ]

    if query == "closest_to_x":
        return [
            int(answer)
            for answer in values
            if _can_sample_values(
                options=[
                    value
                    for value in values
                    if value != answer and abs(int(value) - target) > abs(int(answer) - target)
                ],
                count=n - 1,
                allow_duplicates=allow_duplicate_distractors,
            )
        ]

    if query == "smallest_above_x":
        return [
            int(answer)
            for answer in values
            if answer > target
            and _can_sample_values(
                options=[
                    value
                    for value in values
                    if value != answer and (value <= target or value > answer)
                ],
                count=n - 1,
                allow_duplicates=allow_duplicate_distractors,
            )
        ]

    if query == "largest_below_x":
        return [
            int(answer)
            for answer in values
            if answer < target
            and _can_sample_values(
                options=[
                    value
                    for value in values
                    if value != answer and (value >= target or value < answer)
                ],
                count=n - 1,
                allow_duplicates=allow_duplicate_distractors,
            )
        ]

    if query == "difference_max_min":
        feasible_gaps: List[int] = []
        candidate_set = sorted(
            {
                int(high - low)
                for low in values
                for high in values
                if int(high) > int(low)
            }
        )
        for gap in candidate_set:
            pairs = [(low, high) for low in values for high in values if int(high - low) == int(gap)]
            can_realize = False
            for low, high in pairs:
                interior = [value for value in values if low < value < high]
                if _can_sample_values(
                    options=interior,
                    count=n - 2,
                    allow_duplicates=allow_duplicate_distractors,
                ):
                    can_realize = True
                    break
            if can_realize:
                feasible_gaps.append(int(gap))
        return feasible_gaps

    raise ValueError(f"unsupported query_type: {query}")


def _construct_values_for_answer(
    rng,
    *,
    query_type: str,
    answer_value: int,
    candidates: List[int],
    candidate_count: int,
    target_x: int,
    allow_duplicate_distractors: bool,
) -> List[int] | None:
    """Construct candidate values so query answer equals `answer_value`."""
    query = str(query_type)
    values = sorted(int(value) for value in candidates)
    answer = int(answer_value)
    n = int(candidate_count)
    target = int(target_x)

    if query == "min":
        distractors = _sample_values_from_options(
            rng,
            options=[value for value in values if value > answer],
            count=n - 1,
            allow_duplicates=allow_duplicate_distractors,
        )
        if distractors is None:
            return None
        return [answer, *distractors]

    if query == "max":
        distractors = _sample_values_from_options(
            rng,
            options=[value for value in values if value < answer],
            count=n - 1,
            allow_duplicates=allow_duplicate_distractors,
        )
        if distractors is None:
            return None
        return [answer, *distractors]

    if query == "median":
        half = n // 2
        lower = _sample_values_from_options(
            rng,
            options=[value for value in values if value < answer],
            count=half,
            allow_duplicates=allow_duplicate_distractors,
        )
        upper = _sample_values_from_options(
            rng,
            options=[value for value in values if value > answer],
            count=half,
            allow_duplicates=allow_duplicate_distractors,
        )
        if lower is None or upper is None:
            return None
        return [answer, *lower, *upper]

    if query == "closest_to_x":
        distractors = _sample_values_from_options(
            rng,
            options=[
                value
                for value in values
                if value != answer and abs(int(value) - target) > abs(int(answer) - target)
            ],
            count=n - 1,
            allow_duplicates=allow_duplicate_distractors,
        )
        if distractors is None:
            return None
        return [answer, *distractors]

    if query == "smallest_above_x":
        distractors = _sample_values_from_options(
            rng,
            options=[
                value
                for value in values
                if value != answer and (value <= target or value > answer)
            ],
            count=n - 1,
            allow_duplicates=allow_duplicate_distractors,
        )
        if distractors is None:
            return None
        return [answer, *distractors]

    if query == "largest_below_x":
        distractors = _sample_values_from_options(
            rng,
            options=[
                value
                for value in values
                if value != answer and (value >= target or value < answer)
            ],
            count=n - 1,
            allow_duplicates=allow_duplicate_distractors,
        )
        if distractors is None:
            return None
        return [answer, *distractors]

    if query == "difference_max_min":
        pairs = [(low, high) for low in values for high in values if int(high - low) == answer]
        valid_pairs: List[Tuple[int, int]] = []
        for low, high in pairs:
            interior = [value for value in values if low < value < high]
            if _can_sample_values(
                options=interior,
                count=n - 2,
                allow_duplicates=allow_duplicate_distractors,
            ):
                valid_pairs.append((int(low), int(high)))
        if not valid_pairs:
            return None
        low, high = rng.choice(valid_pairs)
        interior_values = _sample_values_from_options(
            rng,
            options=[value for value in values if low < value < high],
            count=n - 2,
            allow_duplicates=allow_duplicate_distractors,
        )
        if interior_values is None:
            return None
        return [int(low), int(high), *interior_values]

    raise ValueError(f"unsupported query_type: {query}")


def sample_values_and_outcome_for_answer(
    rng,
    *,
    ids: List[str],
    query_type: str,
    answer_value: int,
    candidates: List[int],
    candidate_count: int,
    target_x: int,
    allow_duplicate_distractors: bool,
) -> tuple[Dict[str, int], QueryOutcome] | None:
    """Build one id->value mapping for fixed answer target and verify it."""
    sampled_values = _construct_values_for_answer(
        rng,
        query_type=query_type,
        answer_value=int(answer_value),
        candidates=candidates,
        candidate_count=candidate_count,
        target_x=target_x,
        allow_duplicate_distractors=allow_duplicate_distractors,
    )
    if sampled_values is None or len(sampled_values) != len(ids):
        return None

    shuffled_values = list(sampled_values)
    rng.shuffle(shuffled_values)
    values_by_id = {entity_id: int(value) for entity_id, value in zip(ids, shuffled_values)}

    outcome = run_value_query(
        values_by_id,
        query_type=query_type,
        target_x=(target_x if query_type in _TARGET_X_QUERY_TYPES else None),
        require_unique_values=(not allow_duplicate_distractors),
    )
    if int(outcome.answer_value) != int(answer_value):
        return None
    return values_by_id, outcome


__all__ = [
    "feasible_answer_values",
    "resolve_candidate_count",
    "sample_values_and_outcome_for_answer",
]
