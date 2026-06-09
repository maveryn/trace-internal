"""Derived delta and ratio datasets for multiseries charts."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from .labeled_chart_common import (
    balanced_choice_from_values,
    resolve_value_bounds,
    sample_chart_labels,
    sample_composition_with_sum,
)
from .multiseries_chart_config import (
    MultiseriesChartDefaults,
    resolve_category_count_bounds,
    resolve_series_count_bounds,
    sample_series_labels,
)

def _sample_score_window(
    rng,
    *,
    count: int,
    max_score: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> List[int]:
    """Sample a unique, usually tight derived-score support."""

    score_min = int(params.get("derived_score_min", group_default(gen_defaults, "derived_score_min", 1)))
    score_max = int(params.get("derived_score_max", group_default(gen_defaults, "derived_score_max", int(max_score))))
    if int(score_min) < 1:
        raise ValueError("derived_score_min must be positive")
    if int(score_max) > int(max_score):
        score_max = int(max_score)
    if int(score_min) > int(score_max):
        raise ValueError("derived_score_min must be <= derived_score_max")
    score_support_size = int(score_max) - int(score_min) + 1
    if int(count) > int(score_support_size):
        raise ValueError("delta-extremum task requires enough distinct derived scores")
    extra_min = int(params.get("score_spread_extra_min", group_default(gen_defaults, "score_spread_extra_min", 0)))
    extra_max = int(params.get("score_spread_extra_max", group_default(gen_defaults, "score_spread_extra_max", 4)))
    if int(extra_min) < 0 or int(extra_max) < 0:
        raise ValueError("score_spread_extra bounds must be non-negative")
    if int(extra_min) > int(extra_max):
        raise ValueError("score_spread_extra_min must be <= score_spread_extra_max")
    feasible_extra_max = min(int(extra_max), int(score_support_size) - int(count))
    feasible_extra_min = min(int(extra_min), int(feasible_extra_max))
    extra = rng.randint(int(feasible_extra_min), int(feasible_extra_max))
    window_size = int(count) + int(extra)
    start = rng.randint(int(score_min), int(score_max) - int(window_size) + 1)
    window = [int(value) for value in range(int(start), int(start) + int(window_size))]
    return [int(value) for value in rng.sample(window, int(count))]


def _sample_ratio_percent_window(
    rng,
    *,
    count: int,
    feasible_scores: Sequence[int],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> List[int]:
    """Sample a unique, usually tight ratio-percent score support."""

    support = sorted({int(score) for score in feasible_scores})
    if int(count) > len(support):
        raise ValueError("ratio-extremum task requires enough distinct feasible ratio scores")
    extra_min = int(params.get("ratio_score_spread_extra_min", group_default(gen_defaults, "ratio_score_spread_extra_min", 0)))
    extra_max = int(params.get("ratio_score_spread_extra_max", group_default(gen_defaults, "ratio_score_spread_extra_max", 6)))
    if int(extra_min) < 0 or int(extra_max) < 0:
        raise ValueError("ratio_score_spread_extra bounds must be non-negative")
    if int(extra_min) > int(extra_max):
        raise ValueError("ratio_score_spread_extra_min must be <= ratio_score_spread_extra_max")
    feasible_extra_max = min(int(extra_max), len(support) - int(count))
    feasible_extra_min = min(int(extra_min), int(feasible_extra_max))
    extra = rng.randint(int(feasible_extra_min), int(feasible_extra_max))
    window_size = int(count) + int(extra)
    start = rng.randint(0, len(support) - int(window_size))
    window = support[int(start) : int(start) + int(window_size)]
    return [int(value) for value in rng.sample(window, int(count))]


def _share_feasible_totals(
    *,
    score_percent: int,
    series_count: int,
    value_min: int,
    value_max: int,
    total_min: int,
    total_max: int,
) -> List[int]:
    """Return category totals that make an exact target-series share feasible."""

    totals: List[int] = []
    for total in range(int(total_min), int(total_max) + 1):
        if (int(score_percent) * int(total)) % 100 != 0:
            continue
        target_value = (int(score_percent) * int(total)) // 100
        remaining_total = int(total) - int(target_value)
        if not (int(value_min) <= int(target_value) <= int(value_max)):
            continue
        if remaining_total < (int(series_count) - 1) * int(value_min):
            continue
        if remaining_total > (int(series_count) - 1) * int(value_max):
            continue
        totals.append(int(total))
    return totals


def _pair_ratio_feasible_denominators(
    *,
    score_percent: int,
    value_min: int,
    value_max: int,
) -> List[int]:
    """Return denominator values that make an exact numerator/denominator percent feasible."""

    denominators: List[int] = []
    for denominator in range(int(value_min), int(value_max) + 1):
        if (int(score_percent) * int(denominator)) % 100 != 0:
            continue
        numerator = (int(score_percent) * int(denominator)) // 100
        if int(value_min) <= int(numerator) <= int(value_max):
            denominators.append(int(denominator))
    return denominators


def _sample_queried_pair_for_score(
    rng,
    *,
    score: int,
    value_min: int,
    value_max: int,
    direction: str,
) -> Tuple[int, int]:
    """Sample two queried-series values whose derived score is `score`."""

    if int(score) <= 0:
        raise ValueError("derived score must be positive")
    if int(value_min) + int(score) > int(value_max):
        raise ValueError("derived score does not fit within the value bounds")
    low_value = rng.randint(int(value_min), int(value_max) - int(score))
    high_value = int(low_value) + int(score)
    if str(direction) == "increase":
        return int(low_value), int(high_value)
    if str(direction) == "decrease":
        return int(high_value), int(low_value)
    if str(direction) == "absolute":
        if rng.randrange(2) == 0:
            return int(low_value), int(high_value)
        return int(high_value), int(low_value)
    raise ValueError(f"unsupported delta direction: {direction}")


def build_delta_extremum_label_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], str, List[int], Dict[str, Any]]:
    """Construct one multiseries derived-delta extremum label dataset."""

    supported_variants = {
        "ranked_largest_increase",
        "ranked_largest_decrease",
        "ranked_largest_gap",
        "ranked_smallest_gap",
    }
    if str(query_id) not in supported_variants:
        raise ValueError(f"unsupported multiseries delta query_id: {query_id}")

    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
    category_count_min, category_count_max = resolve_category_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    series_count_min, series_count_max = resolve_series_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    if int(series_count_min) < 2:
        raise ValueError("multiseries delta task requires at least two series")

    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) <= (int(value_max) - int(value_min))
    ]
    if not feasible_category_counts:
        raise ValueError("category count range exceeds available unique delta support")
    category_count = balanced_choice_from_values(
        feasible_category_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:{str(query_id)}",
    )
    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(query_id)}",
    )

    rank_min = int(params.get("rank_min", group_default(gen_defaults, "rank_min", 1)))
    rank_max = int(params.get("rank_max", group_default(gen_defaults, "rank_max", 3)))
    if int(rank_min) < 1:
        raise ValueError("rank_min must be >= 1")
    if int(rank_min) > int(rank_max):
        raise ValueError("rank_min must be <= rank_max")
    rank_candidates = [
        int(rank)
        for rank in range(int(rank_min), int(rank_max) + 1)
        if 1 <= int(rank) <= int(category_count)
    ]
    if not rank_candidates:
        raise ValueError("delta-extremum task requires a feasible rank")
    answer_rank = balanced_choice_from_values(
        rank_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.answer_rank:{str(query_id)}",
    )

    category_labels = list(
        sample_chart_labels(
            count=int(category_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(query_id)}:{int(category_count)}",
        )
    )
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_pair")
    pair_candidates = [
        (str(series_labels[left_index]), str(series_labels[right_index]))
        for left_index in range(int(series_count))
        for right_index in range(int(left_index) + 1, int(series_count))
    ]
    left_series, right_series = pair_candidates[query_rng.randrange(len(pair_candidates))]

    score_rng = spawn_rng(int(instance_seed), f"{task_id}.derived_scores:{str(query_id)}")
    max_score = int(value_max) - int(value_min)
    scores = _sample_score_window(
        score_rng,
        count=int(category_count),
        max_score=int(max_score),
        params=params,
        gen_defaults=gen_defaults,
    )
    assignment_rng = spawn_rng(int(instance_seed), f"{task_id}.score_assignment:{str(query_id)}")
    assignment_rng.shuffle(scores)
    scores_by_category = {
        str(category_label): int(score)
        for category_label, score in zip(category_labels, scores)
    }
    if str(query_id) == "ranked_smallest_gap":
        sorted_score_items = sorted(
            scores_by_category.items(),
            key=lambda item: (int(item[1]), str(item[0])),
        )
        rank_order = "ascending"
    else:
        sorted_score_items = sorted(
            scores_by_category.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
        rank_order = "descending"
    answer_label = str(sorted_score_items[int(answer_rank) - 1][0])
    answer_score = int(scores_by_category[str(answer_label)])

    if str(query_id) == "ranked_largest_increase":
        direction = "increase"
        derived_metric = "increase"
    elif str(query_id) == "ranked_largest_decrease":
        direction = "decrease"
        derived_metric = "decrease"
    else:
        direction = "absolute"
        derived_metric = "absolute_gap"

    value_rng = spawn_rng(int(instance_seed), f"{task_id}.values:{str(query_id)}")
    values_by_category: Dict[str, Dict[str, int]] = {}
    derived_values_by_category: Dict[str, int] = {}
    annotation_values: List[int] = []
    for category_label in category_labels:
        score = int(scores_by_category[str(category_label)])
        left_value, right_value = _sample_queried_pair_for_score(
            value_rng,
            score=int(score),
            value_min=int(value_min),
            value_max=int(value_max),
            direction=str(direction),
        )
        category_values: Dict[str, int] = {
            str(left_series): int(left_value),
            str(right_series): int(right_value),
        }
        for series_label in series_labels:
            if str(series_label) in category_values:
                continue
            category_values[str(series_label)] = int(value_rng.randint(int(value_min), int(value_max)))
        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }
        if str(derived_metric) == "increase":
            derived_value = int(right_value) - int(left_value)
        elif str(derived_metric) == "decrease":
            derived_value = int(left_value) - int(right_value)
        else:
            derived_value = abs(int(right_value) - int(left_value))
        derived_values_by_category[str(category_label)] = int(derived_value)
        if str(category_label) == str(answer_label):
            annotation_values = [int(left_value), int(right_value), int(derived_value)]

    trace_extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "series_count": int(series_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_labels": [str(label) for label in category_labels],
        "series_labels": [str(label) for label in series_labels],
        "queried_series_labels": [str(left_series), str(right_series)],
        "left_series_label": str(left_series),
        "right_series_label": str(right_series),
        "value_min": int(value_min),
        "value_max": int(value_max),
        "value_range": [int(value_min), int(value_max)],
        "answer_label": str(answer_label),
        "answer_rank": int(answer_rank),
        "answer_score": int(answer_score),
        "annotation_values": [int(value) for value in annotation_values],
        "derived_metric": str(derived_metric),
        "direction": str(direction),
        "rank_order": str(rank_order),
        "ranked_category_labels": [str(label) for label, _score in sorted_score_items],
        "derived_values_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(derived_values_by_category.items())
        },
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
    }
    return values_by_category, str(answer_label), [int(value) for value in annotation_values], trace_extras


def build_ratio_extremum_label_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], str, List[int], Dict[str, Any]]:
    """Construct one multiseries ratio/share extremum label dataset."""

    supported_variants = {
        "ranked_largest_series_share",
        "ranked_smallest_series_share",
        "ranked_largest_pair_ratio",
        "ranked_smallest_pair_ratio",
    }
    if str(query_id) not in supported_variants:
        raise ValueError(f"unsupported multiseries ratio query_id: {query_id}")

    is_share_variant = str(query_id) in {
        "ranked_largest_series_share",
        "ranked_smallest_series_share",
    }
    is_smallest_variant = str(query_id) in {
        "ranked_smallest_series_share",
        "ranked_smallest_pair_ratio",
    }

    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
    category_count_min, category_count_max = resolve_category_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    series_count_min, series_count_max = resolve_series_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    if int(series_count_min) < 2:
        raise ValueError("multiseries ratio task requires at least two series")

    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(query_id)}",
    )

    if bool(is_share_variant):
        score_min = int(params.get("share_percent_min", group_default(gen_defaults, "share_percent_min", 10)))
        score_max = int(params.get("share_percent_max", group_default(gen_defaults, "share_percent_max", 75)))
        value_window_raw = params.get("value_window_enabled", group_default(gen_defaults, "value_window_enabled", False))
        value_window_enabled = bool(value_window_raw)
        if isinstance(value_window_raw, str):
            value_window_enabled = str(value_window_raw).strip().lower() in {"1", "true", "yes", "on"}
        if bool(value_window_enabled) and "category_total_min" not in params and "category_total_max" not in params:
            total_min = int(series_count) * int(value_min)
            total_max = int(series_count) * int(value_max)
        else:
            total_min = int(params.get("category_total_min", group_default(gen_defaults, "category_total_min", 35)))
            total_max = int(params.get("category_total_max", group_default(gen_defaults, "category_total_max", 160)))
        if int(total_min) > int(total_max):
            raise ValueError("category_total_min must be <= category_total_max")
        feasible_scores = [
            int(score)
            for score in range(int(score_min), int(score_max) + 1)
            if _share_feasible_totals(
                score_percent=int(score),
                series_count=int(series_count),
                value_min=int(value_min),
                value_max=int(value_max),
                total_min=int(total_min),
                total_max=int(total_max),
            )
        ]
        score_range = [int(score_min), int(score_max)]
        category_total_range = [int(total_min), int(total_max)]
    else:
        score_min = int(params.get("pair_ratio_percent_min", group_default(gen_defaults, "pair_ratio_percent_min", 40)))
        score_max = int(params.get("pair_ratio_percent_max", group_default(gen_defaults, "pair_ratio_percent_max", 260)))
        feasible_scores = [
            int(score)
            for score in range(int(score_min), int(score_max) + 1)
            if _pair_ratio_feasible_denominators(
                score_percent=int(score),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        ]
        score_range = [int(score_min), int(score_max)]
        category_total_range = None
    if int(score_min) < 1:
        raise ValueError("ratio percent minimum must be positive")
    if int(score_min) > int(score_max):
        raise ValueError("ratio percent minimum must be <= maximum")

    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) <= len(feasible_scores)
    ]
    if not feasible_category_counts:
        raise ValueError("category count range exceeds feasible ratio-percent support")
    category_count = balanced_choice_from_values(
        feasible_category_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:{str(query_id)}:{int(series_count)}",
    )

    rank_min = int(params.get("rank_min", group_default(gen_defaults, "rank_min", 1)))
    rank_max = int(params.get("rank_max", group_default(gen_defaults, "rank_max", 3)))
    if int(rank_min) < 1:
        raise ValueError("rank_min must be >= 1")
    if int(rank_min) > int(rank_max):
        raise ValueError("rank_min must be <= rank_max")
    rank_candidates = [
        int(rank)
        for rank in range(int(rank_min), int(rank_max) + 1)
        if 1 <= int(rank) <= int(category_count)
    ]
    if not rank_candidates:
        raise ValueError("ratio-extremum task requires a feasible rank")
    answer_rank = balanced_choice_from_values(
        rank_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.answer_rank:{str(query_id)}",
    )

    category_labels = list(
        sample_chart_labels(
            count=int(category_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(query_id)}:{int(category_count)}",
        )
    )
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_series:{str(query_id)}")
    if bool(is_share_variant):
        target_series = str(series_labels[query_rng.randrange(len(series_labels))])
        numerator_series = str(target_series)
        denominator_series = "category_total"
        queried_series_labels = [str(target_series)]
    else:
        pair_candidates = [
            (str(series_labels[numerator_index]), str(series_labels[denominator_index]))
            for numerator_index in range(int(series_count))
            for denominator_index in range(int(series_count))
            if int(numerator_index) != int(denominator_index)
        ]
        numerator_series, denominator_series = pair_candidates[query_rng.randrange(len(pair_candidates))]
        target_series = ""
        queried_series_labels = [str(numerator_series), str(denominator_series)]

    score_rng = spawn_rng(int(instance_seed), f"{task_id}.ratio_scores:{str(query_id)}")
    scores = _sample_ratio_percent_window(
        score_rng,
        count=int(category_count),
        feasible_scores=feasible_scores,
        params=params,
        gen_defaults=gen_defaults,
    )
    assignment_rng = spawn_rng(int(instance_seed), f"{task_id}.ratio_score_assignment:{str(query_id)}")
    assignment_rng.shuffle(scores)
    scores_by_category = {
        str(category_label): int(score)
        for category_label, score in zip(category_labels, scores)
    }
    if bool(is_smallest_variant):
        sorted_score_items = sorted(scores_by_category.items(), key=lambda item: (int(item[1]), str(item[0])))
        rank_order = "ascending"
    else:
        sorted_score_items = sorted(scores_by_category.items(), key=lambda item: (-int(item[1]), str(item[0])))
        rank_order = "descending"
    answer_label = str(sorted_score_items[int(answer_rank) - 1][0])
    answer_score = int(scores_by_category[str(answer_label)])

    value_rng = spawn_rng(int(instance_seed), f"{task_id}.values:{str(query_id)}")
    values_by_category: Dict[str, Dict[str, int]] = {}
    denominator_values_by_category: Dict[str, int] = {}
    ratio_percent_by_category: Dict[str, int] = {}
    annotation_values: List[int] = []
    for category_label in category_labels:
        score = int(scores_by_category[str(category_label)])
        if bool(is_share_variant):
            totals = _share_feasible_totals(
                score_percent=int(score),
                series_count=int(series_count),
                value_min=int(value_min),
                value_max=int(value_max),
                total_min=int(category_total_range[0] if category_total_range is not None else 0),
                total_max=int(category_total_range[1] if category_total_range is not None else 0),
            )
            category_total = int(totals[value_rng.randrange(len(totals))])
            numerator_value = (int(score) * int(category_total)) // 100
            remaining_total = int(category_total) - int(numerator_value)
            distractor_series_labels = [
                str(series_label)
                for series_label in series_labels
                if str(series_label) != str(target_series)
            ]
            distractor_values = sample_composition_with_sum(
                value_rng,
                target_sum=int(remaining_total),
                count=len(distractor_series_labels),
                value_min=int(value_min),
                value_max=int(value_max),
            )
            value_rng.shuffle(distractor_values)
            category_values = {
                str(target_series): int(numerator_value),
                **{
                    str(series_label): int(value)
                    for series_label, value in zip(distractor_series_labels, distractor_values)
                },
            }
            denominator_value = int(category_total)
        else:
            denominators = _pair_ratio_feasible_denominators(
                score_percent=int(score),
                value_min=int(value_min),
                value_max=int(value_max),
            )
            denominator_value = int(denominators[value_rng.randrange(len(denominators))])
            numerator_value = (int(score) * int(denominator_value)) // 100
            category_values = {
                str(numerator_series): int(numerator_value),
                str(denominator_series): int(denominator_value),
            }
            for series_label in series_labels:
                if str(series_label) in category_values:
                    continue
                category_values[str(series_label)] = int(value_rng.randint(int(value_min), int(value_max)))

        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }
        denominator_values_by_category[str(category_label)] = int(denominator_value)
        ratio_percent_by_category[str(category_label)] = int(score)
        if str(category_label) == str(answer_label):
            annotation_values = [int(numerator_value), int(denominator_value), int(score)]

    trace_extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "series_count": int(series_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_labels": [str(label) for label in category_labels],
        "series_labels": [str(label) for label in series_labels],
        "queried_series_labels": [str(label) for label in queried_series_labels],
        "target_series_label": str(target_series),
        "numerator_series_label": str(numerator_series),
        "denominator_series_label": str(denominator_series),
        "value_min": int(value_min),
        "value_max": int(value_max),
        "value_range": [int(value_min), int(value_max)],
        "score_percent_range": list(score_range),
        "category_total_range": list(category_total_range) if category_total_range is not None else None,
        "answer_label": str(answer_label),
        "answer_rank": int(answer_rank),
        "answer_score": int(answer_score),
        "answer_score_percent": int(answer_score),
        "annotation_values": [int(value) for value in annotation_values],
        "derived_metric": "series_share_percent" if bool(is_share_variant) else "pair_ratio_percent",
        "calculation_scope": "category_total_share" if bool(is_share_variant) else "queried_pair_ratio",
        "rank_order": str(rank_order),
        "ranked_category_labels": [str(label) for label, _score in sorted_score_items],
        "denominator_values_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(denominator_values_by_category.items())
        },
        "ratio_percent_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(ratio_percent_by_category.items())
        },
        "derived_values_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(ratio_percent_by_category.items())
        },
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
    }
    return values_by_category, str(answer_label), [int(value) for value in annotation_values], trace_extras


__all__ = [
    "build_delta_extremum_label_dataset",
    "build_ratio_extremum_label_dataset",
]
