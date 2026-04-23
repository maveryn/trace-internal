"""Shared generation/render helpers for stacked-composition chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from .labeled_chart_common import (
    LabeledChartDefaults,
    balanced_choice_from_values,
    compose_with_sum,
    resolve_value_bounds,
    sample_chart_labels,
)
from .multiseries_chart_common import (
    build_multiseries_mark_specs,
    resolve_category_count_bounds,
    resolve_multiseries_chart_colors,
    resolve_series_count_bounds,
    sample_series_labels,
)


TaskVariant = str
SceneVariant = str

SUPPORTED_COMPOSITION_TASK_VARIANTS: Tuple[str, ...] = (
    "category_subset_sum",
    "series_across_categories_sum",
    "subset_margin_sum",
)
STACKED_COMPOSITION_SCENE_VARIANTS: Tuple[str, ...] = (
    "stacked_bar",
    "stacked_horizontal_bar",
)
SUPPORTED_COMPOSITION_SCENE_VARIANTS: Tuple[str, ...] = STACKED_COMPOSITION_SCENE_VARIANTS
_SCENE_VARIANTS_BY_TASK_VARIANT: Dict[str, Tuple[str, ...]] = {
    str(task_variant): STACKED_COMPOSITION_SCENE_VARIANTS
    for task_variant in SUPPORTED_COMPOSITION_TASK_VARIANTS
}


@dataclass(frozen=True)
class CompositionChartDefaults(LabeledChartDefaults):
    """Stable fallback defaults shared by stacked-composition chart tasks."""

    category_count_min: int = 6
    category_count_max: int = 9
    series_count_min: int = 5
    series_count_max: int = 7
    query_category_subset_size_min: int = 3
    query_category_subset_size_max: int = 4
    query_series_subset_size_min: int = 3
    query_series_subset_size_max: int = 4
    comparison_subset_size_min: int = 2
    comparison_subset_size_max: int = 3
    value_min: int = 4
    value_max: int = 18
    canvas_width: int = 1120
    canvas_height: int = 720
    plot_margin_left_px: int = 120
    plot_margin_right_px: int = 72
    plot_margin_top_px: int = 44
    plot_margin_bottom_px: int = 112


def supported_scene_variants_for_task_variant(task_variant: str) -> Tuple[str, ...]:
    """Return the supported scene variants for one composition query variant."""

    variants = _SCENE_VARIANTS_BY_TASK_VARIANT.get(str(task_variant))
    if variants is None:
        raise ValueError(f"unsupported composition task_variant: {task_variant}")
    return tuple(str(value) for value in variants)


def _choose_count(
    *,
    params: Mapping[str, Any],
    explicit_key: str,
    supported_values: Sequence[int],
    instance_seed: int,
    namespace: str,
) -> int:
    """Choose one explicit-or-balanced count from the supported values."""

    ordered = [int(value) for value in supported_values]
    if not ordered:
        raise ValueError(f"no feasible values for {namespace}")
    explicit_value = params.get(str(explicit_key))
    if explicit_value is not None:
        selected = int(explicit_value)
        if int(selected) not in set(ordered):
            raise ValueError(f"explicit {explicit_key} is outside feasible support")
        return int(selected)
    return balanced_choice_from_values(
        ordered,
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def _resolve_subset_size_bounds(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    min_key: str,
    max_key: str,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve one min/max subset-size range."""

    min_default = int(getattr(defaults, str(min_key)))
    max_default = int(getattr(defaults, str(max_key)))
    subset_min = int(params.get(str(min_key), group_default(gen_defaults, str(min_key), int(min_default))))
    subset_max = int(params.get(str(max_key), group_default(gen_defaults, str(max_key), int(max_default))))
    if int(subset_min) <= 0 or int(subset_max) <= 0:
        raise ValueError(f"{task_id}: subset sizes must be positive")
    if int(subset_min) > int(subset_max):
        raise ValueError(f"{task_id}: {min_key} cannot exceed {max_key}")
    return int(subset_min), int(subset_max)


def _values_by_label(labels: Sequence[str], values: Sequence[int]) -> Dict[str, int]:
    """Map ordered labels to ordered integer values."""

    return {
        str(label): int(value)
        for label, value in zip(labels, values)
    }


def _sample_stack_values(
    rng,
    *,
    series_count: int,
    value_min: int,
    value_max: int,
) -> List[int]:
    """Sample one ordered positive stack-value list."""

    return [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(series_count))]


def _sample_disjoint_label_subsets(
    *,
    labels: Sequence[str],
    subset_size: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[List[str], List[str]]:
    """Sample two disjoint ordered label subsets of equal size."""

    if int(2 * subset_size) > int(len(labels)):
        raise ValueError("subset size is too large for disjoint subset sampling")
    rng = spawn_rng(int(instance_seed), str(namespace))
    indices = list(range(len(labels)))
    rng.shuffle(indices)
    left_indices = sorted(indices[: int(subset_size)])
    right_indices = sorted(indices[int(subset_size) : int(2 * subset_size)])
    return (
        [str(labels[int(index)]) for index in left_indices],
        [str(labels[int(index)]) for index in right_indices],
    )


def _sample_total_pair_for_relation(
    rng,
    *,
    subset_size: int,
    value_min: int,
    value_max: int,
    left_greater: bool,
) -> Tuple[int, int]:
    """Sample one pair of subset totals with the requested ordering relation."""

    min_total = int(subset_size) * int(value_min)
    max_total = int(subset_size) * int(value_max)
    if int(min_total) >= int(max_total):
        raise ValueError("subset totals need non-degenerate support")
    if bool(left_greater):
        right_total = int(rng.randint(int(min_total), int(max_total) - 1))
        left_total = int(rng.randint(int(right_total) + 1, int(max_total)))
        return int(left_total), int(right_total)
    left_total = int(rng.randint(int(min_total), int(max_total)))
    right_total = int(rng.randint(int(left_total), int(max_total)))
    return int(left_total), int(right_total)


def _build_category_subset_sum_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one stacked-chart dataset for `category_subset_sum`."""

    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
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
    query_series_subset_size_min, query_series_subset_size_max = _resolve_subset_size_bounds(
        params=params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        min_key="query_series_subset_size_min",
        max_key="query_series_subset_size_max",
        task_id=task_id,
    )

    feasible_series_counts = [
        int(series_count)
        for series_count in range(int(series_count_min), int(series_count_max) + 1)
        if int(series_count) >= int(query_series_subset_size_min)
    ]
    series_count = _choose_count(
        params=params,
        explicit_key="series_count",
        supported_values=feasible_series_counts,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:category_subset_sum",
    )
    category_count = _choose_count(
        params=params,
        explicit_key="category_count",
        supported_values=range(int(category_count_min), int(category_count_max) + 1),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:category_subset_sum",
    )

    feasible_subset_sizes = [
        int(size)
        for size in range(int(query_series_subset_size_min), int(query_series_subset_size_max) + 1)
        if int(size) <= int(series_count)
    ]
    query_series_subset_size = _choose_count(
        params=params,
        explicit_key="query_series_subset_size",
        supported_values=feasible_subset_sizes,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_series_subset_size:category_subset_sum",
    )

    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))

    query_rng = spawn_rng(int(instance_seed), f"{task_id}.category_subset_sum.query")
    query_category_label = str(category_labels[int(query_rng.randrange(len(category_labels)))])
    subset_indices = list(range(len(series_labels)))
    query_rng.shuffle(subset_indices)
    subset_indices = sorted(subset_indices[: int(query_series_subset_size)])
    query_series_subset_labels = [str(series_labels[int(index)]) for index in subset_indices]

    target_answer_min = int(
        params.get(
            "target_answer_min",
            group_default(gen_defaults, "target_answer_min", int(query_series_subset_size) * int(value_min)),
        )
    )
    target_answer_max = int(
        params.get(
            "target_answer_max",
            group_default(gen_defaults, "target_answer_max", int(query_series_subset_size) * int(value_max)),
        )
    )
    feasible_answers = [
        int(value)
        for value in range(int(target_answer_min), int(target_answer_max) + 1)
        if int(query_series_subset_size) * int(value_min) <= int(value) <= int(query_series_subset_size) * int(value_max)
    ]
    target_answer = balanced_choice_from_values(
        feasible_answers,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:category_subset_sum",
    )

    values_rng = spawn_rng(int(instance_seed), f"{task_id}.category_subset_sum.values")
    values_by_category: Dict[str, Dict[str, int]] = {}
    evidence_values: List[int] | None = None
    evidence_cells: List[Dict[str, Any]] = []
    subset_label_set = set(str(label) for label in query_series_subset_labels)

    for category_label in category_labels:
        stack_values = _sample_stack_values(
            values_rng,
            series_count=int(series_count),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        if str(category_label) == str(query_category_label):
            selected_values = compose_with_sum(
                int(target_answer),
                count=int(query_series_subset_size),
                value_min=int(value_min),
                value_max=int(value_max),
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.category_subset_sum.compose",
            )
            selected_iter = iter(int(value) for value in selected_values)
            for series_index, series_label in enumerate(series_labels):
                if str(series_label) in subset_label_set:
                    stack_values[int(series_index)] = int(next(selected_iter))
            evidence_values = [int(stack_values[int(series_labels.index(str(label)))]) for label in query_series_subset_labels]
            evidence_cells = [
                {
                    "category_label": str(query_category_label),
                    "series_label": str(label),
                }
                for label in query_series_subset_labels
            ]
        values_by_category[str(category_label)] = _values_by_label(series_labels, stack_values)

    if evidence_values is None:
        raise RuntimeError("category_subset_sum failed to assign evidence values")

    return {
        "scene_mode": "stacked",
        "series_labels": list(series_labels),
        "category_labels": list(category_labels),
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in values_by_category[str(category_label)].items()
            }
            for category_label in category_labels
        },
        "query_category_label": str(query_category_label),
        "query_category_labels": [str(query_category_label)],
        "query_series_label": "",
        "query_series_subset_labels": list(query_series_subset_labels),
        "query_category_subset_labels": [],
        "left_series_subset_labels": [],
        "right_series_subset_labels": [],
        "evidence_labels": list(query_series_subset_labels),
        "evidence_values": [int(value) for value in evidence_values],
        "evidence_cells": list(evidence_cells),
        "answer_value": int(target_answer),
        "series_count": int(series_count),
        "category_count": int(category_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "query_series_subset_size": int(query_series_subset_size),
        "query_series_subset_size_range": [int(query_series_subset_size_min), int(query_series_subset_size_max)],
        "target_answer": int(target_answer),
        "target_answer_range": [int(min(feasible_answers)), int(max(feasible_answers))],
        "value_semantics": "integer",
        "composition_scope": "stack",
        "operation_kind": "category_subset_sum",
    }


def _build_series_across_categories_sum_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one stacked-chart dataset for `series_across_categories_sum`."""

    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
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
    query_category_subset_size_min, query_category_subset_size_max = _resolve_subset_size_bounds(
        params=params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        min_key="query_category_subset_size_min",
        max_key="query_category_subset_size_max",
        task_id=task_id,
    )

    feasible_category_counts = [
        int(category_count)
        for category_count in range(int(category_count_min), int(category_count_max) + 1)
        if int(category_count) >= int(query_category_subset_size_min)
    ]
    category_count = _choose_count(
        params=params,
        explicit_key="category_count",
        supported_values=feasible_category_counts,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:series_across_categories_sum",
    )
    series_count = _choose_count(
        params=params,
        explicit_key="series_count",
        supported_values=range(int(series_count_min), int(series_count_max) + 1),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:series_across_categories_sum",
    )

    feasible_subset_sizes = [
        int(size)
        for size in range(int(query_category_subset_size_min), int(query_category_subset_size_max) + 1)
        if int(size) <= int(category_count)
    ]
    query_category_subset_size = _choose_count(
        params=params,
        explicit_key="query_category_subset_size",
        supported_values=feasible_subset_sizes,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_category_subset_size:series_across_categories_sum",
    )

    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))

    query_rng = spawn_rng(int(instance_seed), f"{task_id}.series_across_categories_sum.query")
    query_series_label = str(series_labels[int(query_rng.randrange(len(series_labels)))])
    subset_indices = list(range(len(category_labels)))
    query_rng.shuffle(subset_indices)
    subset_indices = sorted(subset_indices[: int(query_category_subset_size)])
    query_category_subset_labels = [str(category_labels[int(index)]) for index in subset_indices]

    target_answer_min = int(
        params.get(
            "target_answer_min",
            group_default(gen_defaults, "target_answer_min", int(query_category_subset_size) * int(value_min)),
        )
    )
    target_answer_max = int(
        params.get(
            "target_answer_max",
            group_default(gen_defaults, "target_answer_max", int(query_category_subset_size) * int(value_max)),
        )
    )
    feasible_answers = [
        int(value)
        for value in range(int(target_answer_min), int(target_answer_max) + 1)
        if int(query_category_subset_size) * int(value_min) <= int(value) <= int(query_category_subset_size) * int(value_max)
    ]
    target_answer = balanced_choice_from_values(
        feasible_answers,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:series_across_categories_sum",
    )

    values_rng = spawn_rng(int(instance_seed), f"{task_id}.series_across_categories_sum.values")
    values_by_category: Dict[str, Dict[str, int]] = {}
    evidence_values: List[int] | None = None
    evidence_cells: List[Dict[str, Any]] = []

    query_series_index = int(series_labels.index(str(query_series_label)))
    selected_values = compose_with_sum(
        int(target_answer),
        count=int(query_category_subset_size),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_across_categories_sum.compose",
    )
    selected_by_category = {
        str(category_label): int(value)
        for category_label, value in zip(query_category_subset_labels, selected_values)
    }

    for category_label in category_labels:
        stack_values = _sample_stack_values(
            values_rng,
            series_count=int(series_count),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        if str(category_label) in set(query_category_subset_labels):
            stack_values[int(query_series_index)] = int(selected_by_category[str(category_label)])
        values_by_category[str(category_label)] = _values_by_label(series_labels, stack_values)

    evidence_values = [
        int(values_by_category[str(category_label)][str(query_series_label)])
        for category_label in query_category_subset_labels
    ]
    evidence_cells = [
        {
            "category_label": str(category_label),
            "series_label": str(query_series_label),
        }
        for category_label in query_category_subset_labels
    ]

    return {
        "scene_mode": "stacked",
        "series_labels": list(series_labels),
        "category_labels": list(category_labels),
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in values_by_category[str(category_label)].items()
            }
            for category_label in category_labels
        },
        "query_category_label": "",
        "query_category_labels": list(query_category_subset_labels),
        "query_series_label": str(query_series_label),
        "query_series_subset_labels": [],
        "query_category_subset_labels": list(query_category_subset_labels),
        "left_series_subset_labels": [],
        "right_series_subset_labels": [],
        "evidence_labels": list(query_category_subset_labels),
        "evidence_values": [int(value) for value in evidence_values],
        "evidence_cells": list(evidence_cells),
        "answer_value": int(target_answer),
        "series_count": int(series_count),
        "category_count": int(category_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "query_category_subset_size": int(query_category_subset_size),
        "query_category_subset_size_range": [int(query_category_subset_size_min), int(query_category_subset_size_max)],
        "target_answer": int(target_answer),
        "target_answer_range": [int(min(feasible_answers)), int(max(feasible_answers))],
        "value_semantics": "integer",
        "composition_scope": "stack",
        "operation_kind": "series_across_categories_sum",
    }


def _build_subset_margin_sum_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one stacked-chart dataset for `subset_margin_sum`."""

    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
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
    comparison_subset_size_min, comparison_subset_size_max = _resolve_subset_size_bounds(
        params=params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        min_key="comparison_subset_size_min",
        max_key="comparison_subset_size_max",
        task_id=task_id,
    )

    feasible_series_counts = [
        int(series_count)
        for series_count in range(int(series_count_min), int(series_count_max) + 1)
        if int(series_count) >= int(2 * comparison_subset_size_min)
    ]
    series_count = _choose_count(
        params=params,
        explicit_key="series_count",
        supported_values=feasible_series_counts,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:subset_margin_sum",
    )
    category_count = _choose_count(
        params=params,
        explicit_key="category_count",
        supported_values=range(int(category_count_min), int(category_count_max) + 1),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:subset_margin_sum",
    )

    feasible_subset_sizes = [
        int(size)
        for size in range(int(comparison_subset_size_min), int(comparison_subset_size_max) + 1)
        if int(2 * size) <= int(series_count)
    ]
    comparison_subset_size = _choose_count(
        params=params,
        explicit_key="comparison_subset_size",
        supported_values=feasible_subset_sizes,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.comparison_subset_size:subset_margin_sum",
    )

    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    left_series_subset_labels, right_series_subset_labels = _sample_disjoint_label_subsets(
        labels=series_labels,
        subset_size=int(comparison_subset_size),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.subset_margin_sum.label_subsets",
    )

    max_margin_per_category = int(comparison_subset_size) * int(value_max - value_min)
    if int(max_margin_per_category) <= 0:
        raise ValueError("subset_margin_sum requires non-degenerate per-category margin support")
    target_answer_min = int(
        params.get(
            "target_answer_min",
            group_default(gen_defaults, "target_answer_min", max(4, int(comparison_subset_size))),
        )
    )
    target_answer_max = int(
        params.get(
            "target_answer_max",
            group_default(
                gen_defaults,
                "target_answer_max",
                int(category_count) * int(max_margin_per_category),
            ),
        )
    )
    feasible_answers = [
        int(value)
        for value in range(int(target_answer_min), int(target_answer_max) + 1)
        if 0 < int(value) <= int(category_count) * int(max_margin_per_category)
    ]
    target_answer = balanced_choice_from_values(
        feasible_answers,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:subset_margin_sum",
    )

    feasible_positive_category_counts = [
        int(count)
        for count in range(1, int(category_count) + 1)
        if int(count) <= int(target_answer) <= int(count) * int(max_margin_per_category)
    ]
    positive_category_count = _choose_count(
        params=params,
        explicit_key="positive_category_count",
        supported_values=feasible_positive_category_counts,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.positive_category_count:subset_margin_sum",
    )
    positive_margins = compose_with_sum(
        int(target_answer),
        count=int(positive_category_count),
        value_min=1,
        value_max=int(max_margin_per_category),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.subset_margin_sum.positive_margins",
    )

    relation_rng = spawn_rng(int(instance_seed), f"{task_id}.subset_margin_sum.relation")
    positive_category_indices = list(range(len(category_labels)))
    relation_rng.shuffle(positive_category_indices)
    positive_category_indices = list(positive_category_indices[: int(positive_category_count)])
    positive_margin_by_index = {
        int(category_index): int(margin)
        for category_index, margin in zip(positive_category_indices, positive_margins)
    }
    positive_category_index_set = set(int(index) for index in positive_category_indices)

    values_rng = spawn_rng(int(instance_seed), f"{task_id}.subset_margin_sum.values")
    values_by_category: Dict[str, Dict[str, int]] = {}
    evidence_values: List[int] = []
    evidence_cells: List[Dict[str, Any]] = []
    positive_margin_by_category: Dict[str, int] = {}

    left_label_set = set(str(label) for label in left_series_subset_labels)
    right_label_set = set(str(label) for label in right_series_subset_labels)

    for category_index, category_label in enumerate(category_labels):
        stack_values = _sample_stack_values(
            values_rng,
            series_count=int(series_count),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        left_total, right_total = _sample_total_pair_for_relation(
            values_rng,
            subset_size=int(comparison_subset_size),
            value_min=int(value_min),
            value_max=int(value_max),
            left_greater=(int(category_index) in positive_category_index_set),
        )
        if int(category_index) in positive_category_index_set:
            margin = int(positive_margin_by_index[int(category_index)])
            max_right_total = int(comparison_subset_size) * int(value_max) - int(margin)
            if int(max_right_total) < int(comparison_subset_size) * int(value_min):
                raise ValueError("positive margin exceeds feasible per-category total support")
            right_total = int(values_rng.randint(int(comparison_subset_size) * int(value_min), int(max_right_total)))
            left_total = int(right_total) + int(margin)
        else:
            margin = int(left_total) - int(right_total)
        left_values = compose_with_sum(
            int(left_total),
            count=int(comparison_subset_size),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.subset_margin_sum.left:{category_index}",
        )
        right_values = compose_with_sum(
            int(right_total),
            count=int(comparison_subset_size),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.subset_margin_sum.right:{category_index}",
        )
        left_iter = iter(int(value) for value in left_values)
        right_iter = iter(int(value) for value in right_values)
        for series_index, series_label in enumerate(series_labels):
            if str(series_label) in left_label_set:
                stack_values[int(series_index)] = int(next(left_iter))
            elif str(series_label) in right_label_set:
                stack_values[int(series_index)] = int(next(right_iter))
        values_by_category[str(category_label)] = _values_by_label(series_labels, stack_values)

        evidence_values.append(int(margin))
        positive_margin_by_category[str(category_label)] = int(max(0, int(margin)))
        for label in left_series_subset_labels:
            evidence_cells.append({"category_label": str(category_label), "series_label": str(label)})
        for label in right_series_subset_labels:
            evidence_cells.append({"category_label": str(category_label), "series_label": str(label)})

    return {
        "scene_mode": "stacked",
        "series_labels": list(series_labels),
        "category_labels": list(category_labels),
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in values_by_category[str(category_label)].items()
            }
            for category_label in category_labels
        },
        "query_category_label": "",
        "query_category_labels": list(category_labels),
        "query_series_label": "",
        "query_series_subset_labels": [],
        "query_category_subset_labels": [],
        "left_series_subset_labels": list(left_series_subset_labels),
        "right_series_subset_labels": list(right_series_subset_labels),
        "evidence_labels": list(category_labels),
        "evidence_values": [int(value) for value in evidence_values],
        "evidence_cells": list(evidence_cells),
        "answer_value": int(target_answer),
        "series_count": int(series_count),
        "category_count": int(category_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "comparison_subset_size": int(comparison_subset_size),
        "comparison_subset_size_range": [int(comparison_subset_size_min), int(comparison_subset_size_max)],
        "positive_category_count": int(positive_category_count),
        "target_answer": int(target_answer),
        "target_answer_range": [int(min(feasible_answers)), int(max(feasible_answers))],
        "positive_margin_by_category": dict(positive_margin_by_category),
        "value_semantics": "integer",
        "composition_scope": "stack",
        "operation_kind": "subset_margin_sum",
    }


def build_composition_subset_dataset_for_variant(
    *,
    task_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one stacked-composition dataset for the requested query variant."""

    if str(scene_variant) not in set(supported_scene_variants_for_task_variant(str(task_variant))):
        raise ValueError(f"scene_variant={scene_variant} is incompatible with task_variant={task_variant}")
    if str(task_variant) == "category_subset_sum":
        return _build_category_subset_sum_dataset(
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=gen_defaults,
            defaults=defaults,
            task_id=task_id,
        )
    if str(task_variant) == "series_across_categories_sum":
        return _build_series_across_categories_sum_dataset(
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=gen_defaults,
            defaults=defaults,
            task_id=task_id,
        )
    if str(task_variant) == "subset_margin_sum":
        return _build_subset_margin_sum_dataset(
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=gen_defaults,
            defaults=defaults,
            task_id=task_id,
        )
    raise ValueError(f"unsupported composition task_variant: {task_variant}")


def build_stacked_composition_mark_specs(
    *,
    category_labels: Sequence[str],
    series_labels: Sequence[str],
    values_by_category: Mapping[str, Mapping[str, int]],
    mark_style: Mapping[str, Any],
):
    """Build multiseries mark specs for one stacked composition chart."""

    return build_multiseries_mark_specs(
        category_labels=category_labels,
        series_labels=series_labels,
        values_by_category=values_by_category,
        mark_style=mark_style,
    )


def resolve_stacked_chart_colors(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    instance_seed: int,
    series_count: int,
) -> Dict[str, Any]:
    """Resolve one per-series color palette for stacked charts."""

    return resolve_multiseries_chart_colors(
        params,
        render_defaults=render_defaults,
        defaults=defaults,
        instance_seed=int(instance_seed),
        series_count=int(series_count),
    )


def projected_composition_evidence(
    *,
    rendered_scene,
    evidence_cells: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Project composition evidence into reusable pixel-space overlays."""

    selected_traces = []
    for evidence_cell in evidence_cells:
        wanted_category = str(evidence_cell.get("category_label", ""))
        wanted_series = str(evidence_cell.get("series_label", ""))
        match = next(
            (
                mark_trace
                for mark_trace in rendered_scene.mark_traces
                if str(mark_trace.get("category_label", "")) == wanted_category
                and str(mark_trace.get("series_label", "")) == wanted_series
            ),
            None,
        )
        if match is not None:
            selected_traces.append(match)
    return {
        "pixel_point_set": [list(mark_trace["mark_center_px"]) for mark_trace in selected_traces],
        "bbox_set": [list(mark_trace["mark_bbox_px"]) for mark_trace in selected_traces],
    }


__all__ = [
    "CompositionChartDefaults",
    "STACKED_COMPOSITION_SCENE_VARIANTS",
    "SUPPORTED_COMPOSITION_SCENE_VARIANTS",
    "SUPPORTED_COMPOSITION_TASK_VARIANTS",
    "build_composition_subset_dataset_for_variant",
    "build_stacked_composition_mark_specs",
    "projected_composition_evidence",
    "resolve_stacked_chart_colors",
    "supported_scene_variants_for_task_variant",
]
