"""Pair, equality, and within-category rank datasets for multiseries charts."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from .labeled_chart_common import balanced_choice_from_values, resolve_value_bounds, sample_chart_labels, sorted_labels
from .multiseries_chart_config import (
    MultiseriesChartDefaults,
    _sample_distinct_values,
    resolve_category_count_bounds,
    resolve_series_count_bounds,
    sample_series_labels,
)

def build_pairwise_comparison_count_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], int, List[str], Dict[str, Any]]:
    """Construct one multiseries comparison-count dataset."""

    if str(query_id) not in {"series_a_gt_b_count", "series_a_lt_b_count"}:
        raise ValueError(f"unsupported multiseries query_id: {query_id}")

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
        raise ValueError("multiseries comparison requires at least two series")

    answer_min = int(params.get("target_answer_min", group_default(gen_defaults, "target_answer_min", defaults.target_answer_min)))
    answer_max = int(params.get("target_answer_max", group_default(gen_defaults, "target_answer_max", defaults.target_answer_max)))
    if int(answer_min) > int(answer_max):
        raise ValueError("target_answer_min must be <= target_answer_max")

    answer_candidates = [
        int(value)
        for value in range(int(answer_min), int(answer_max) + 1)
        if int(value) <= int(category_count_max)
    ]
    target_answer = balanced_choice_from_values(
        answer_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:{str(query_id)}",
    )
    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) >= int(target_answer)
    ]
    category_count = balanced_choice_from_values(
        feasible_category_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:{str(query_id)}:{int(target_answer)}",
    )
    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(query_id)}",
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
    query_pair = pair_candidates[query_rng.randrange(len(pair_candidates))]
    left_series, right_series = (str(query_pair[0]), str(query_pair[1]))

    category_indices = list(range(int(category_count)))
    satisfy_rng = spawn_rng(int(instance_seed), f"{task_id}.satisfying_categories")
    satisfy_rng.shuffle(category_indices)
    satisfying_indices = set(category_indices[: int(target_answer)])

    values_rng = spawn_rng(int(instance_seed), f"{task_id}.values")
    values_by_category: Dict[str, Dict[str, int]] = {}
    annotation_labels: List[str] = []
    for category_index, category_label in enumerate(category_labels):
        sampled_values = sorted(
            _sample_distinct_values(
                values_rng,
                count=int(series_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        )
        low_value = int(sampled_values[0])
        high_value = int(sampled_values[-1])
        remaining_values = [int(value) for value in sampled_values[1:-1]]
        relation_holds = bool(int(category_index) in satisfying_indices)
        if str(query_id) == "series_a_gt_b_count":
            left_value = int(high_value if relation_holds else low_value)
            right_value = int(low_value if relation_holds else high_value)
        else:
            left_value = int(low_value if relation_holds else high_value)
            right_value = int(high_value if relation_holds else low_value)
        category_values: Dict[str, int] = {
            str(left_series): int(left_value),
            str(right_series): int(right_value),
        }
        distractor_series_labels = [
            str(series_label)
            for series_label in series_labels
            if str(series_label) not in {str(left_series), str(right_series)}
        ]
        for distractor_series, distractor_value in zip(distractor_series_labels, remaining_values):
            category_values[str(distractor_series)] = int(distractor_value)
        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }
        if relation_holds:
            annotation_labels.append(str(category_label))

    annotation_labels = sorted_labels(annotation_labels)
    trace_extras: Dict[str, Any] = {
        "target_answer": int(target_answer),
        "target_answer_range": [int(answer_min), int(answer_max)],
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
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
        "comparison": "greater_than" if str(query_id) == "series_a_gt_b_count" else "less_than",
    }
    return values_by_category, int(target_answer), annotation_labels, trace_extras


def build_pair_equality_label_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], str, List[int], Dict[str, Any]]:
    """Construct one multiseries exact-equality label dataset."""

    if str(query_id) != "pair_equality_label":
        raise ValueError(f"unsupported multiseries equality query_id: {query_id}")

    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
    if int(value_min) >= int(value_max):
        raise ValueError("pair equality task requires at least two possible values")
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
        raise ValueError("multiseries equality task requires at least two series")

    feasible_category_counts = [int(count) for count in range(int(category_count_min), int(category_count_max) + 1)]
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

    category_labels = list(
        sample_chart_labels(
            count=int(category_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(query_id)}:{int(category_count)}",
        )
    )
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_pair:{str(query_id)}")
    pair_candidates = [
        (str(series_labels[left_index]), str(series_labels[right_index]))
        for left_index in range(int(series_count))
        for right_index in range(int(left_index) + 1, int(series_count))
    ]
    left_series, right_series = pair_candidates[query_rng.randrange(len(pair_candidates))]

    answer_index = balanced_choice_from_values(
        list(range(int(category_count))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.answer_index:{str(query_id)}",
    )
    answer_label = str(category_labels[int(answer_index)])
    value_rng = spawn_rng(int(instance_seed), f"{task_id}.values:{str(query_id)}")
    equal_value = int(value_rng.randint(int(value_min), int(value_max)))
    non_equal_values = [int(value) for value in range(int(value_min), int(value_max) + 1)]

    values_by_category: Dict[str, Dict[str, int]] = {}
    equality_by_category: Dict[str, bool] = {}
    gap_by_category: Dict[str, int] = {}
    for category_label in category_labels:
        if str(category_label) == str(answer_label):
            left_value = int(equal_value)
            right_value = int(equal_value)
        else:
            left_value = int(value_rng.randint(int(value_min), int(value_max)))
            right_candidates = [int(value) for value in non_equal_values if int(value) != int(left_value)]
            right_value = int(right_candidates[value_rng.randrange(len(right_candidates))])

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
        is_equal = int(left_value) == int(right_value)
        equality_by_category[str(category_label)] = bool(is_equal)
        gap_by_category[str(category_label)] = abs(int(left_value) - int(right_value))

    equality_labels = [str(label) for label, is_equal in equality_by_category.items() if bool(is_equal)]
    if equality_labels != [str(answer_label)]:
        raise RuntimeError("pair equality task failed to construct a unique equality label")

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
        "answer_equal_value": int(equal_value),
        "answer_score": 0,
        "answer_rank": 1,
        "annotation_values": [int(equal_value), int(equal_value)],
        "derived_metric": "exact_equality",
        "direction": "none",
        "rank_order": "unique_zero_gap",
        "ranked_category_labels": [str(answer_label)],
        "derived_values_by_category": {
            str(label): int(value)
            for label, value in sorted(gap_by_category.items())
        },
        "equality_by_category": {
            str(label): bool(value)
            for label, value in sorted(equality_by_category.items())
        },
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
    }
    return values_by_category, str(answer_label), [int(equal_value), int(equal_value)], trace_extras


def build_series_rank_at_category_label_dataset(
    *,
    query_id: str,
    extremum_direction: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], str, List[int], Dict[str, Any]]:
    """Construct one dataset for ranking series values within a target category."""

    if str(query_id) != "series_rank_at_category_label":
        raise ValueError(f"unsupported multiseries series-rank query_id: {query_id}")
    if str(extremum_direction) not in {"largest", "smallest"}:
        raise ValueError(f"unsupported extremum_direction: {extremum_direction}")

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
        raise ValueError("multiseries series-rank task requires at least two series")

    feasible_category_counts = [int(count) for count in range(int(category_count_min), int(category_count_max) + 1)]
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
    if int(series_count) > (int(value_max) - int(value_min) + 1):
        raise ValueError("series-rank task requires enough distinct values for the target category")

    rank_min = int(
        params.get(
            "series_rank_rank_min",
            group_default(gen_defaults, "series_rank_rank_min", group_default(gen_defaults, "rank_min", 1)),
        )
    )
    rank_max = int(
        params.get(
            "series_rank_rank_max",
            group_default(gen_defaults, "series_rank_rank_max", group_default(gen_defaults, "rank_max", 3)),
        )
    )
    if int(rank_min) < 1:
        raise ValueError("series_rank_rank_min must be >= 1")
    if int(rank_min) > int(rank_max):
        raise ValueError("series_rank_rank_min must be <= series_rank_rank_max")
    rank_candidates = [
        int(rank)
        for rank in range(int(rank_min), int(rank_max) + 1)
        if 1 <= int(rank) <= int(series_count)
    ]
    if not rank_candidates:
        raise ValueError("series-rank task requires a feasible rank")
    answer_rank = balanced_choice_from_values(
        rank_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.answer_rank:{str(query_id)}:{str(extremum_direction)}",
    )

    category_labels = list(
        sample_chart_labels(
            count=int(category_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(query_id)}:{int(category_count)}",
        )
    )
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    target_category_index = balanced_choice_from_values(
        list(range(int(category_count))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_category_index:{str(query_id)}",
    )
    target_category_label = str(category_labels[int(target_category_index)])

    value_rng = spawn_rng(int(instance_seed), f"{task_id}.values:{str(query_id)}")
    target_values = _sample_distinct_values(
        value_rng,
        count=int(series_count),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    value_rng.shuffle(target_values)

    values_by_category: Dict[str, Dict[str, int]] = {}
    for category_label in category_labels:
        if str(category_label) == str(target_category_label):
            category_values = {
                str(series_label): int(value)
                for series_label, value in zip(series_labels, target_values)
            }
        else:
            category_values = {
                str(series_label): int(value_rng.randint(int(value_min), int(value_max)))
                for series_label in series_labels
            }
        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }

    values_by_series = {
        str(series_label): int(values_by_category[str(target_category_label)][str(series_label)])
        for series_label in series_labels
    }
    if str(extremum_direction) == "smallest":
        ranked_series_items = sorted(values_by_series.items(), key=lambda item: (int(item[1]), str(item[0])))
        rank_order = "ascending"
    else:
        ranked_series_items = sorted(values_by_series.items(), key=lambda item: (-int(item[1]), str(item[0])))
        rank_order = "descending"
    answer_series_label = str(ranked_series_items[int(answer_rank) - 1][0])
    answer_score = int(values_by_series[str(answer_series_label)])
    annotation_values = [
        int(values_by_series[str(series_label)])
        for series_label in series_labels
    ]

    trace_extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "series_count": int(series_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_labels": [str(label) for label in category_labels],
        "series_labels": [str(label) for label in series_labels],
        "queried_series_labels": [str(label) for label in series_labels],
        "target_category_label": str(target_category_label),
        "target_category_index": int(target_category_index),
        "value_min": int(value_min),
        "value_max": int(value_max),
        "value_range": [int(value_min), int(value_max)],
        "answer_label": str(answer_series_label),
        "answer_series_label": str(answer_series_label),
        "answer_rank": int(answer_rank),
        "answer_score": int(answer_score),
        "annotation_values": [int(value) for value in annotation_values],
        "derived_metric": "series_value_at_target_category",
        "calculation_scope": "target_category_series_rank",
        "rank_order": str(rank_order),
        "extremum_direction": str(extremum_direction),
        "ranked_series_labels": [str(label) for label, _value in ranked_series_items],
        "ranked_category_labels": [str(target_category_label)],
        "values_by_series_at_target_category": {
            str(label): int(value)
            for label, value in sorted(values_by_series.items())
        },
        "derived_values_by_category": {
            str(label): int(values_by_series[str(label)])
            for label in series_labels
        },
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
    }
    return values_by_category, str(answer_series_label), [int(value) for value in annotation_values], trace_extras


__all__ = [
    "build_pair_equality_label_dataset",
    "build_pairwise_comparison_count_dataset",
    "build_series_rank_at_category_label_dataset",
]
