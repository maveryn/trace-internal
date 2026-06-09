"""Category-total datasets for multiseries charts."""

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

def build_category_total_extremum_label_dataset(
    *,
    query_id: str,
    extremum_direction: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], str, List[int], Dict[str, Any]]:
    """Construct one category-total extremum label dataset."""

    if str(query_id) != "category_total_extremum_label":
        raise ValueError(f"unsupported multiseries category-total query_id: {query_id}")
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
    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(query_id)}",
    )

    total_min = int(series_count) * int(value_min)
    total_max = int(series_count) * int(value_max)
    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) <= (int(total_max) - int(total_min) + 1)
    ]
    if not feasible_category_counts:
        raise ValueError("category-total task requires enough unique total support")
    category_count = balanced_choice_from_values(
        feasible_category_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:{str(query_id)}:{int(series_count)}",
    )

    rank_min = int(
        params.get(
            "category_total_rank_min",
            group_default(gen_defaults, "category_total_rank_min", group_default(gen_defaults, "rank_min", 1)),
        )
    )
    rank_max = int(
        params.get(
            "category_total_rank_max",
            group_default(gen_defaults, "category_total_rank_max", group_default(gen_defaults, "rank_max", 2)),
        )
    )
    if int(rank_min) < 1:
        raise ValueError("category_total_rank_min must be >= 1")
    if int(rank_min) > int(rank_max):
        raise ValueError("category_total_rank_min must be <= category_total_rank_max")
    rank_candidates = [
        int(rank)
        for rank in range(int(rank_min), int(rank_max) + 1)
        if 1 <= int(rank) <= int(category_count)
    ]
    if not rank_candidates:
        raise ValueError("category-total task requires a feasible rank")
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
    total_rng = spawn_rng(int(instance_seed), f"{task_id}.category_totals:{str(query_id)}")
    category_totals = total_rng.sample(
        [int(value) for value in range(int(total_min), int(total_max) + 1)],
        int(category_count),
    )
    assignment_rng = spawn_rng(int(instance_seed), f"{task_id}.category_total_assignment:{str(query_id)}")
    assignment_rng.shuffle(category_totals)
    totals_by_category = {
        str(category_label): int(total)
        for category_label, total in zip(category_labels, category_totals)
    }
    if str(extremum_direction) == "smallest":
        sorted_total_items = sorted(totals_by_category.items(), key=lambda item: (int(item[1]), str(item[0])))
        rank_order = "ascending"
    else:
        sorted_total_items = sorted(totals_by_category.items(), key=lambda item: (-int(item[1]), str(item[0])))
        rank_order = "descending"
    answer_label = str(sorted_total_items[int(answer_rank) - 1][0])
    answer_total = int(totals_by_category[str(answer_label)])

    value_rng = spawn_rng(int(instance_seed), f"{task_id}.category_total_values:{str(query_id)}")
    values_by_category: Dict[str, Dict[str, int]] = {}
    annotation_values: List[int] = []
    for category_label in category_labels:
        series_values = sample_composition_with_sum(
            value_rng,
            target_sum=int(totals_by_category[str(category_label)]),
            count=int(series_count),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        value_rng.shuffle(series_values)
        values_by_category[str(category_label)] = {
            str(series_label): int(value)
            for series_label, value in zip(series_labels, series_values)
        }
        if str(category_label) == str(answer_label):
            annotation_values = [int(value) for value in series_values]

    trace_extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "series_count": int(series_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_labels": [str(label) for label in category_labels],
        "series_labels": [str(label) for label in series_labels],
        "queried_series_labels": [str(label) for label in series_labels],
        "value_min": int(value_min),
        "value_max": int(value_max),
        "value_range": [int(value_min), int(value_max)],
        "category_total_range": [int(total_min), int(total_max)],
        "answer_label": str(answer_label),
        "answer_rank": int(answer_rank),
        "answer_score": int(answer_total),
        "annotation_values": [int(value) for value in annotation_values],
        "derived_metric": "category_total",
        "calculation_scope": "category_total",
        "rank_order": str(rank_order),
        "extremum_direction": str(extremum_direction),
        "ranked_category_labels": [str(label) for label, _score in sorted_total_items],
        "category_totals_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(totals_by_category.items())
        },
        "derived_values_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(totals_by_category.items())
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


__all__ = ["build_category_total_extremum_label_dataset"]
