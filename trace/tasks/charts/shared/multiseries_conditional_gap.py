"""Conditional-gap datasets for multiseries charts."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

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
from .multiseries_derived_datasets import _sample_queried_pair_for_score

def _sample_absolute_gap_pair(
    rng,
    *,
    gap: int,
    value_min: int,
    value_max: int,
) -> Tuple[int, int]:
    """Sample two values with the requested absolute gap."""

    left_value, right_value = _sample_queried_pair_for_score(
        rng,
        score=int(gap),
        value_min=int(value_min),
        value_max=int(value_max),
        direction="absolute",
    )
    return int(left_value), int(right_value)


def _sample_relation_pair(
    rng,
    *,
    relation_holds: bool,
    comparison: str,
    value_min: int,
    value_max: int,
) -> Tuple[int, int]:
    """Sample two values where the requested strict relation has the requested truth value."""

    max_gap = max(1, int(value_max) - int(value_min))
    relation_gap = int(rng.randint(1, int(max_gap)))
    low_value = int(rng.randint(int(value_min), int(value_max) - int(relation_gap)))
    high_value = int(low_value) + int(relation_gap)
    wants_greater = str(comparison) == "greater_than"
    if bool(relation_holds) == bool(wants_greater):
        return int(high_value), int(low_value)
    return int(low_value), int(high_value)


def _conditional_gap_target_gaps(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    task_id: str,
    filter_count: int,
    gap_min: int,
    gap_max: int,
    extremum_direction: str | None,
) -> Tuple[List[int], int, List[int], Dict[str, Any]]:
    """Construct filtered target gaps and the numeric answer for one conditional-gap variant."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.conditional_gap_values:{str(query_id)}")
    if str(query_id) == "conditional_gap_sum_value":
        answer_min = int(params.get("sum_answer_min", group_default(gen_defaults, "sum_answer_min", int(filter_count) * int(gap_min))))
        answer_max = int(params.get("sum_answer_max", group_default(gen_defaults, "sum_answer_max", int(filter_count) * int(gap_max))))
        feasible = [
            int(value)
            for value in range(max(int(answer_min), int(filter_count) * int(gap_min)), min(int(answer_max), int(filter_count) * int(gap_max)) + 1)
        ]
        answer_value = balanced_choice_from_values(
            feasible,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.answer_value:{str(query_id)}:{int(filter_count)}",
        )
        gaps = sample_composition_with_sum(
            rng,
            target_sum=int(answer_value),
            count=int(filter_count),
            value_min=int(gap_min),
            value_max=int(gap_max),
        )
        return [int(value) for value in gaps], int(answer_value), [min(feasible), max(feasible)], {}

    if str(query_id) == "conditional_gap_mean_value":
        answer_min = int(params.get("mean_answer_min", group_default(gen_defaults, "mean_answer_min", int(gap_min))))
        answer_max = int(params.get("mean_answer_max", group_default(gen_defaults, "mean_answer_max", int(gap_max))))
        feasible = [
            int(value)
            for value in range(max(int(answer_min), int(gap_min)), min(int(answer_max), int(gap_max)) + 1)
        ]
        answer_value = balanced_choice_from_values(
            feasible,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.answer_value:{str(query_id)}",
        )
        gaps = sample_composition_with_sum(
            rng,
            target_sum=int(answer_value) * int(filter_count),
            count=int(filter_count),
            value_min=int(gap_min),
            value_max=int(gap_max),
        )
        return [int(value) for value in gaps], int(answer_value), [min(feasible), max(feasible)], {}

    if str(query_id) == "conditional_gap_range_value":
        answer_min = int(params.get("range_answer_min", group_default(gen_defaults, "range_answer_min", 1)))
        answer_max = int(params.get("range_answer_max", group_default(gen_defaults, "range_answer_max", int(gap_max) - int(gap_min))))
        feasible = [
            int(value)
            for value in range(max(1, int(answer_min)), min(int(answer_max), int(gap_max) - int(gap_min)) + 1)
        ]
        answer_value = balanced_choice_from_values(
            feasible,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.answer_value:{str(query_id)}",
        )
        low_gap = int(rng.randint(int(gap_min), int(gap_max) - int(answer_value)))
        high_gap = int(low_gap) + int(answer_value)
        gaps = [int(low_gap), int(high_gap)]
        while len(gaps) < int(filter_count):
            gaps.append(int(rng.randint(int(low_gap), int(high_gap))))
        rng.shuffle(gaps)
        return [int(value) for value in gaps], int(answer_value), [min(feasible), max(feasible)], {}

    if str(query_id) == "conditional_gap_extremum_value":
        direction = str(extremum_direction or "largest")
        answer_min = int(params.get("extremum_answer_min", group_default(gen_defaults, "extremum_answer_min", int(gap_min))))
        answer_max = int(params.get("extremum_answer_max", group_default(gen_defaults, "extremum_answer_max", int(gap_max))))
        if direction == "smallest":
            feasible = [
                int(value)
                for value in range(max(int(answer_min), int(gap_min)), min(int(answer_max), int(gap_max)) + 1)
                if int(gap_max) - int(value) >= int(filter_count) - 1
            ]
            answer_value = balanced_choice_from_values(
                feasible,
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.answer_value:{str(query_id)}:{direction}:{int(filter_count)}",
            )
            distractor_pool = [int(value) for value in range(int(answer_value) + 1, int(gap_max) + 1)]
        else:
            feasible = [
                int(value)
                for value in range(max(int(answer_min), int(gap_min)), min(int(answer_max), int(gap_max)) + 1)
                if int(value) - int(gap_min) >= int(filter_count) - 1
            ]
            answer_value = balanced_choice_from_values(
                feasible,
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.answer_value:{str(query_id)}:{direction}:{int(filter_count)}",
            )
            distractor_pool = [int(value) for value in range(int(gap_min), int(answer_value))]
        gaps = [int(answer_value)] + [int(value) for value in rng.sample(distractor_pool, int(filter_count) - 1)]
        rng.shuffle(gaps)
        return [int(value) for value in gaps], int(answer_value), [min(feasible), max(feasible)], {"extremum_direction": direction}

    raise ValueError(f"unsupported multiseries conditional-gap query_id: {query_id}")


def build_conditional_gap_value_dataset(
    *,
    query_id: str,
    condition_comparison: str,
    extremum_direction: str | None,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], int, List[str], Dict[str, List[str]], Dict[str, Any]]:
    """Construct one filtered multiseries gap-arithmetic dataset."""

    supported_variants = {
        "conditional_gap_sum_value",
        "conditional_gap_mean_value",
        "conditional_gap_range_value",
        "conditional_gap_extremum_value",
    }
    if str(query_id) not in supported_variants:
        raise ValueError(f"unsupported multiseries conditional-gap query_id: {query_id}")
    if str(condition_comparison) not in {"greater_than", "less_than"}:
        raise ValueError(f"unsupported condition_comparison: {condition_comparison}")

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
    series_count_min = max(4, int(series_count_min))
    if int(series_count_min) > int(series_count_max):
        raise ValueError("conditional-gap multiseries task requires at least four series")

    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) >= 4
    ]
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

    filter_min = int(params.get("filtered_category_count_min", group_default(gen_defaults, "filtered_category_count_min", 3)))
    filter_max = int(params.get("filtered_category_count_max", group_default(gen_defaults, "filtered_category_count_max", 6)))
    filter_min = max(2, int(filter_min))
    filter_max = max(int(filter_min), int(filter_max))
    feasible_filter_counts = [
        int(count)
        for count in range(int(filter_min), int(filter_max) + 1)
        if 2 <= int(count) < int(category_count)
    ]
    filter_count = balanced_choice_from_values(
        feasible_filter_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.filtered_category_count:{str(query_id)}:{int(category_count)}",
    )

    gap_min = int(params.get("target_gap_min", group_default(gen_defaults, "target_gap_min", 2)))
    gap_max = int(params.get("target_gap_max", group_default(gen_defaults, "target_gap_max", 18)))
    gap_min = max(1, int(gap_min))
    gap_max = min(int(gap_max), int(value_max) - int(value_min))
    if int(gap_min) > int(gap_max):
        raise ValueError("target gap bounds do not fit in the sampled value window")

    filtered_gaps, answer_value, answer_range, extra_trace = _conditional_gap_target_gaps(
        query_id=str(query_id),
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        task_id=task_id,
        filter_count=int(filter_count),
        gap_min=int(gap_min),
        gap_max=int(gap_max),
        extremum_direction=extremum_direction,
    )

    category_labels = list(
        sample_chart_labels(
            count=int(category_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(query_id)}:{int(category_count)}",
        )
    )
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_series")
    query_series = list(series_labels)
    query_rng.shuffle(query_series)
    condition_left_series, condition_right_series, target_left_series, target_right_series = [
        str(label) for label in query_series[:4]
    ]

    category_indices = list(range(int(category_count)))
    filter_rng = spawn_rng(int(instance_seed), f"{task_id}.filtered_categories:{str(query_id)}")
    filter_rng.shuffle(category_indices)
    filtered_indices = set(category_indices[: int(filter_count)])
    filtered_gap_by_index = {
        int(category_index): int(gap)
        for category_index, gap in zip(sorted(filtered_indices), filtered_gaps)
    }

    value_rng = spawn_rng(int(instance_seed), f"{task_id}.values:{str(query_id)}")
    values_by_category: Dict[str, Dict[str, int]] = {}
    target_gap_by_category: Dict[str, int] = {}
    condition_holds_by_category: Dict[str, bool] = {}
    for category_index, category_label in enumerate(category_labels):
        relation_holds = bool(int(category_index) in filtered_indices)
        condition_left_value, condition_right_value = _sample_relation_pair(
            value_rng,
            relation_holds=bool(relation_holds),
            comparison=str(condition_comparison),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        target_gap = int(
            filtered_gap_by_index[int(category_index)]
            if bool(relation_holds)
            else value_rng.randint(int(gap_min), int(gap_max))
        )
        target_left_value, target_right_value = _sample_absolute_gap_pair(
            value_rng,
            gap=int(target_gap),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        category_values: Dict[str, int] = {
            str(condition_left_series): int(condition_left_value),
            str(condition_right_series): int(condition_right_value),
            str(target_left_series): int(target_left_value),
            str(target_right_series): int(target_right_value),
        }
        for series_label in series_labels:
            if str(series_label) in category_values:
                continue
            category_values[str(series_label)] = int(value_rng.randint(int(value_min), int(value_max)))
        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }
        target_gap_by_category[str(category_label)] = int(target_gap)
        condition_holds_by_category[str(category_label)] = bool(relation_holds)

    filtered_category_labels = [
        str(label)
        for index, label in enumerate(category_labels)
        if int(index) in filtered_indices
    ]
    filtered_gap_values = [int(target_gap_by_category[str(label)]) for label in filtered_category_labels]
    if str(query_id) == "conditional_gap_sum_value":
        realized_answer = int(sum(filtered_gap_values))
    elif str(query_id) == "conditional_gap_mean_value":
        realized_answer = int(sum(filtered_gap_values) // len(filtered_gap_values))
    elif str(query_id) == "conditional_gap_range_value":
        realized_answer = int(max(filtered_gap_values) - min(filtered_gap_values))
    elif str(extra_trace.get("extremum_direction", extremum_direction or "largest")) == "smallest":
        realized_answer = int(min(filtered_gap_values))
    else:
        realized_answer = int(max(filtered_gap_values))
    if int(realized_answer) != int(answer_value):
        raise RuntimeError("conditional-gap answer drifted from constructed target")

    annotation_series = [
        str(condition_left_series),
        str(condition_right_series),
        str(target_left_series),
        str(target_right_series),
    ]
    annotation_series_by_category = {
        str(label): list(annotation_series)
        for label in filtered_category_labels
    }

    trace_extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "series_count": int(series_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "filtered_category_count": int(filter_count),
        "filtered_category_count_range": [int(filter_min), int(filter_max)],
        "category_labels": [str(label) for label in category_labels],
        "series_labels": [str(label) for label in series_labels],
        "condition_series_labels": [str(condition_left_series), str(condition_right_series)],
        "target_series_labels": [str(target_left_series), str(target_right_series)],
        "queried_series_labels": list(annotation_series),
        "condition_left_series_label": str(condition_left_series),
        "condition_right_series_label": str(condition_right_series),
        "target_left_series_label": str(target_left_series),
        "target_right_series_label": str(target_right_series),
        "condition_comparison": str(condition_comparison),
        "value_min": int(value_min),
        "value_max": int(value_max),
        "value_range": [int(value_min), int(value_max)],
        "target_gap_range": [int(gap_min), int(gap_max)],
        "answer_value": int(answer_value),
        "answer_range": [int(answer_range[0]), int(answer_range[1])],
        "filtered_category_labels": [str(label) for label in filtered_category_labels],
        "filtered_gap_values": [int(value) for value in filtered_gap_values],
        "target_gap_by_category": {
            str(label): int(value)
            for label, value in sorted(target_gap_by_category.items())
        },
        "condition_holds_by_category": {
            str(label): bool(value)
            for label, value in sorted(condition_holds_by_category.items())
        },
        "annotation_series_labels_by_category": dict(annotation_series_by_category),
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
        **dict(extra_trace),
    }
    return (
        values_by_category,
        int(answer_value),
        [str(label) for label in filtered_category_labels],
        annotation_series_by_category,
        trace_extras,
    )


__all__ = ["build_conditional_gap_value_dataset"]
