"""Shared generators for histogram and boxplot chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import resolve_required_int_bounds
from .chart_scene import BoxPlotSpec, HistogramBinSpec
from .labeled_chart_common import (
    LabeledChartDefaults,
    balanced_choice_from_values,
    choose_mark_count,
    compose_with_sum,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
    sample_chart_labels,
)


HistogramTaskVariant = str
BoxPlotTaskVariant = str


@dataclass(frozen=True)
class DistributionChartDefaults:
    """Stable fallback defaults for distribution-style chart tasks."""

    bin_count_min: int = 4
    bin_count_max: int = 7
    bin_width_min: int = 2
    bin_width_max: int = 4
    bin_start_min: int = 0
    bin_start_max: int = 12
    bin_frequency_min: int = 1
    bin_frequency_max: int = 12
    interval_bin_span_min: int = 2
    interval_bin_span_max: int = 4
    category_count_min: int = 4
    category_count_max: int = 7
    value_min: int = 1
    value_max: int = 20


def _resolve_histogram_bin_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="bin_count_min",
        max_key="bin_count_max",
        fallback_min=int(defaults.bin_count_min),
        fallback_max=int(defaults.bin_count_max),
        context=f"generation defaults for {task_id}",
    )


def _resolve_boxplot_category_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=int(defaults.category_count_min),
        fallback_max=int(defaults.category_count_max),
        context=f"generation defaults for {task_id}",
    )


def _resolve_bin_width_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="bin_width_min",
        max_key="bin_width_max",
        fallback_min=int(defaults.bin_width_min),
        fallback_max=int(defaults.bin_width_max),
        context=f"generation defaults for {task_id}",
    )


def _resolve_bin_start_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="bin_start_min",
        max_key="bin_start_max",
        fallback_min=int(defaults.bin_start_min),
        fallback_max=int(defaults.bin_start_max),
        context=f"generation defaults for {task_id}",
    )


def _resolve_bin_frequency_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="bin_frequency_min",
        max_key="bin_frequency_max",
        fallback_min=int(defaults.bin_frequency_min),
        fallback_max=int(defaults.bin_frequency_max),
        context=f"generation defaults for {task_id}",
    )


def _resolve_boxplot_value_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="value_min",
        max_key="value_max",
        fallback_min=int(defaults.value_min),
        fallback_max=int(defaults.value_max),
        context=f"generation defaults for {task_id}",
    )


def _build_histogram_labels(*, start_value: int, bin_width: int, bin_count: int) -> List[str]:
    labels: List[str] = []
    for index in range(int(bin_count)):
        lower = int(start_value) + int(index) * int(bin_width)
        upper = int(lower) + int(bin_width) - 1
        labels.append(f"{int(lower)}-{int(upper)}")
    return labels


def _histogram_answer_range(
    *,
    task_variant: HistogramTaskVariant,
    bin_count_max: int,
    bin_frequency_min: int,
    bin_frequency_max: int,
) -> Tuple[int, int]:
    if str(task_variant) == "modal_bin_count":
        return max(4, int(bin_frequency_min) + 1), int(bin_frequency_max)
    if str(task_variant) == "interval_mass":
        return max(4, 2 * int(bin_frequency_min)), min(24, 4 * int(bin_frequency_max))
    if str(task_variant) == "cumulative_count_to_bin":
        return max(4, 2 * int(bin_frequency_min)), min(36, int(bin_count_max) * int(bin_frequency_max))
    raise ValueError(f"unsupported histogram task_variant: {task_variant}")


def _resolve_histogram_target_answer(
    params: Mapping[str, Any],
    *,
    task_variant: HistogramTaskVariant,
    instance_seed: int,
    bin_count_max: int,
    bin_frequency_min: int,
    bin_frequency_max: int,
    task_id: str,
) -> int:
    default_min, default_max = _histogram_answer_range(
        task_variant=str(task_variant),
        bin_count_max=int(bin_count_max),
        bin_frequency_min=int(bin_frequency_min),
        bin_frequency_max=int(bin_frequency_max),
    )
    target_min = int(params.get("target_answer_min", default_min))
    target_max = int(params.get("target_answer_max", default_max))
    if int(target_min) > int(target_max):
        raise ValueError("target_answer_min must be <= target_answer_max")
    return balanced_choice_from_values(
        list(range(int(target_min), int(target_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:target_answer:{str(task_variant)}",
    )


def build_histogram_dataset_for_variant(
    *,
    task_variant: HistogramTaskVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
    mark_style: Mapping[str, Any],
) -> Tuple[List[HistogramBinSpec], int, List[str], Dict[str, Any]]:
    """Build one histogram dataset and query for the requested variant."""

    bin_count_min, bin_count_max = _resolve_histogram_bin_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    bin_width_min, bin_width_max = _resolve_bin_width_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    bin_start_min, bin_start_max = _resolve_bin_start_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    bin_frequency_min, bin_frequency_max = _resolve_bin_frequency_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )

    target_answer = _resolve_histogram_target_answer(
        params,
        task_variant=str(task_variant),
        instance_seed=int(instance_seed),
        bin_count_max=int(bin_count_max),
        bin_frequency_min=int(bin_frequency_min),
        bin_frequency_max=int(bin_frequency_max),
        task_id=task_id,
    )
    rng = spawn_rng(int(instance_seed), f"{task_id}.histogram.{str(task_variant)}")

    if str(task_variant) == "modal_bin_count":
        feasible_bin_counts = [
            int(value)
            for value in range(int(bin_count_min), int(bin_count_max) + 1)
            if int(target_answer) <= int(bin_frequency_max) and int(target_answer) > int(bin_frequency_min)
        ]
        bin_count = choose_mark_count(
            feasible_bin_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:histogram_bin_count:{str(task_variant)}",
        )
        evidence_start = int(rng.randint(0, int(bin_count) - 1))
        evidence_stop = int(evidence_start) + 1
        relevant_count = 1
        relevant_values = [int(target_answer)]
        background_values = [
            int(rng.randint(int(bin_frequency_min), int(target_answer) - 1))
            for _ in range(int(bin_count) - 1)
        ]
        query_meta = {"modal_bin_label": None}
    elif str(task_variant) == "interval_mass":
        feasible_specs: List[Tuple[int, int]] = []
        for candidate_bin_count in range(int(bin_count_min), int(bin_count_max) + 1):
            max_interval_span = min(int(defaults.interval_bin_span_max), int(candidate_bin_count))
            for interval_span in range(int(defaults.interval_bin_span_min), int(max_interval_span) + 1):
                if int(interval_span) * int(bin_frequency_min) <= int(target_answer) <= int(interval_span) * int(bin_frequency_max):
                    feasible_specs.append((int(candidate_bin_count), int(interval_span)))
        if not feasible_specs:
            raise ValueError("no feasible histogram interval_mass construction for requested answer range")
        selected_index = int(rng.randint(0, len(feasible_specs) - 1))
        bin_count, relevant_count = feasible_specs[selected_index]
        evidence_start = int(rng.randint(0, int(bin_count) - int(relevant_count)))
        evidence_stop = int(evidence_start) + int(relevant_count)
        relevant_values = compose_with_sum(
            int(target_answer),
            count=int(relevant_count),
            value_min=int(bin_frequency_min),
            value_max=int(bin_frequency_max),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.interval_sum",
        )
        background_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(bin_count) - int(relevant_count))
        ]
        query_meta = {"interval_bin_span": int(relevant_count)}
    elif str(task_variant) == "cumulative_count_to_bin":
        feasible_specs = []
        for candidate_bin_count in range(int(bin_count_min), int(bin_count_max) + 1):
            for prefix_count in range(2, int(candidate_bin_count) + 1):
                if int(prefix_count) * int(bin_frequency_min) <= int(target_answer) <= int(prefix_count) * int(bin_frequency_max):
                    feasible_specs.append((int(candidate_bin_count), int(prefix_count)))
        if not feasible_specs:
            raise ValueError("no feasible histogram cumulative construction for requested answer range")
        selected_index = int(rng.randint(0, len(feasible_specs) - 1))
        bin_count, relevant_count = feasible_specs[selected_index]
        evidence_start = 0
        evidence_stop = int(relevant_count)
        relevant_values = compose_with_sum(
            int(target_answer),
            count=int(relevant_count),
            value_min=int(bin_frequency_min),
            value_max=int(bin_frequency_max),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.cumulative_sum",
        )
        background_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(bin_count) - int(relevant_count))
        ]
        query_meta = {"prefix_bin_count": int(relevant_count)}
    else:
        raise ValueError(f"unsupported histogram task_variant: {task_variant}")

    bin_width = balanced_choice_from_values(
        list(range(int(bin_width_min), int(bin_width_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:bin_width:{str(task_variant)}",
    )
    start_value = balanced_choice_from_values(
        list(range(int(bin_start_min), int(bin_start_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:bin_start:{str(task_variant)}",
    )
    labels = _build_histogram_labels(
        start_value=int(start_value),
        bin_width=int(bin_width),
        bin_count=int(bin_count),
    )
    values: List[int] = []
    background_iter = iter(background_values)
    for index in range(int(bin_count)):
        if int(evidence_start) <= int(index) < int(evidence_stop):
            values.append(int(relevant_values[int(index) - int(evidence_start)]))
        else:
            values.append(int(next(background_iter)))

    evidence_labels = [str(label) for label in labels[int(evidence_start) : int(evidence_stop)]]
    bins: List[HistogramBinSpec] = []
    fill_rgb = tuple(int(channel) for channel in mark_style["mark_fill_rgb"])
    outline_rgb = tuple(int(channel) for channel in mark_style["mark_outline_rgb"])
    for index, (label, count_value) in enumerate(zip(labels, values)):
        lower = int(start_value) + int(index) * int(bin_width)
        upper = int(lower) + int(bin_width) - 1
        bins.append(
            HistogramBinSpec(
                label=str(label),
                count=int(count_value),
                interval_start=int(lower),
                interval_end=int(upper),
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
            )
        )

    query_interval_label = ""
    query_bin_label = ""
    if str(task_variant) == "modal_bin_count":
        query_meta["modal_bin_label"] = str(evidence_labels[0])
    elif str(task_variant) == "interval_mass":
        query_interval_label = f"{bins[int(evidence_start)].interval_start}-{bins[int(evidence_stop) - 1].interval_end}"
    elif str(task_variant) == "cumulative_count_to_bin":
        query_bin_label = str(evidence_labels[-1])

    trace_extras = {
        "scene_variant": "histogram",
        "bin_count": int(bin_count),
        "bin_count_range": [int(bin_count_min), int(bin_count_max)],
        "bin_width": int(bin_width),
        "bin_width_range": [int(bin_width_min), int(bin_width_max)],
        "bin_start": int(start_value),
        "bin_start_range": [int(bin_start_min), int(bin_start_max)],
        "bin_frequency_range": [int(bin_frequency_min), int(bin_frequency_max)],
        "target_answer": int(target_answer),
        "target_answer_range": list(
            _histogram_answer_range(
                task_variant=str(task_variant),
                bin_count_max=int(bin_count_max),
                bin_frequency_min=int(bin_frequency_min),
                bin_frequency_max=int(bin_frequency_max),
            )
        ),
        "labels": [str(label) for label in labels],
        "bin_counts": [int(value) for value in values],
        "evidence_labels": [str(label) for label in evidence_labels],
        "query_interval_label": str(query_interval_label),
        "query_bin_label": str(query_bin_label),
        **{str(key): value for key, value in query_meta.items()},
    }
    return bins, int(target_answer), [str(label) for label in evidence_labels], trace_extras


def build_boxplot_dataset_for_variant(
    *,
    task_variant: BoxPlotTaskVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
    mark_style: Mapping[str, Any],
) -> Tuple[List[BoxPlotSpec], str, int, Dict[str, Any]]:
    """Build one categorical boxplot scene and label-answer query."""

    category_count_min, category_count_max = _resolve_boxplot_category_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    value_min, value_max = _resolve_boxplot_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    category_count = choose_mark_count(
        list(range(int(category_count_min), int(category_count_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:category_count:{str(task_variant)}",
    )
    labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    rng = spawn_rng(int(instance_seed), f"{task_id}.boxplot.{str(task_variant)}")
    fill_rgb = tuple(int(channel) for channel in mark_style["mark_fill_rgb"])
    outline_rgb = tuple(int(channel) for channel in mark_style["mark_outline_rgb"])

    specs: List[BoxPlotSpec] = []
    if str(task_variant) == "highest_median":
        candidate_medians = list(range(int(value_min) + 3, int(value_max) - 3))
        if len(candidate_medians) < int(category_count):
            raise ValueError("boxplot median support is too small for requested category count")
        rng.shuffle(candidate_medians)
        medians = candidate_medians[: int(category_count)]
        rng.shuffle(medians)
        for label, median in zip(labels, medians):
            left_delta = int(rng.randint(1, min(3, int(median) - int(value_min) - 1)))
            right_delta = int(rng.randint(1, min(3, int(value_max) - int(median) - 1)))
            q1 = int(median) - int(left_delta)
            q3 = int(median) + int(right_delta)
            whisker_min = max(int(value_min), int(q1) - int(rng.randint(0, min(2, int(q1) - int(value_min)))))
            whisker_max = min(int(value_max), int(q3) + int(rng.randint(0, min(2, int(value_max) - int(q3)))))
            specs.append(
                BoxPlotSpec(
                    label=str(label),
                    whisker_min=int(whisker_min),
                    q1=int(q1),
                    median=int(median),
                    q3=int(q3),
                    whisker_max=int(whisker_max),
                    fill_rgb=fill_rgb,
                    outline_rgb=outline_rgb,
                )
            )
        answer_label = max(specs, key=lambda spec: int(spec.median)).label
        evidence_value = max(int(spec.median) for spec in specs)
    elif str(task_variant) in {"largest_iqr", "smallest_iqr"}:
        feasible_iqrs = list(range(2, min(10, int(value_max) - int(value_min))))
        if len(feasible_iqrs) < int(category_count):
            raise ValueError("boxplot IQR support is too small for requested category count")
        rng.shuffle(feasible_iqrs)
        iqrs = feasible_iqrs[: int(category_count)]
        rng.shuffle(iqrs)
        for label, iqr in zip(labels, iqrs):
            q1_min = int(value_min) + 1
            q1_max = int(value_max) - int(iqr) - 2
            if int(q1_min) > int(q1_max):
                raise ValueError("no feasible q1 support for boxplot IQR construction")
            q1 = int(rng.randint(int(q1_min), int(q1_max)))
            q3 = int(q1) + int(iqr)
            median = int(rng.randint(int(q1) + 1, int(q3) - 1))
            whisker_min = max(int(value_min), int(q1) - int(rng.randint(0, min(2, int(q1) - int(value_min)))))
            whisker_max = min(int(value_max), int(q3) + int(rng.randint(0, min(2, int(value_max) - int(q3)))))
            specs.append(
                BoxPlotSpec(
                    label=str(label),
                    whisker_min=int(whisker_min),
                    q1=int(q1),
                    median=int(median),
                    q3=int(q3),
                    whisker_max=int(whisker_max),
                    fill_rgb=fill_rgb,
                    outline_rgb=outline_rgb,
                )
            )
        if str(task_variant) == "largest_iqr":
            answer_label = max(specs, key=lambda spec: int(spec.q3) - int(spec.q1)).label
            evidence_value = max(int(spec.q3) - int(spec.q1) for spec in specs)
        else:
            answer_label = min(specs, key=lambda spec: int(spec.q3) - int(spec.q1)).label
            evidence_value = min(int(spec.q3) - int(spec.q1) for spec in specs)
    else:
        raise ValueError(f"unsupported boxplot task_variant: {task_variant}")

    trace_extras = {
        "scene_variant": "boxplot",
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "value_range": [int(value_min), int(value_max)],
        "labels": [str(spec.label) for spec in specs],
        "answer_label": str(answer_label),
        "evidence_value": int(evidence_value),
        "quartiles_by_label": {
            str(spec.label): {
                "whisker_min": int(spec.whisker_min),
                "q1": int(spec.q1),
                "median": int(spec.median),
                "q3": int(spec.q3),
                "whisker_max": int(spec.whisker_max),
                "iqr": int(spec.q3) - int(spec.q1),
            }
            for spec in specs
        },
    }
    return specs, str(answer_label), int(evidence_value), trace_extras


__all__ = [
    "DistributionChartDefaults",
    "build_boxplot_dataset_for_variant",
    "build_histogram_dataset_for_variant",
    "projected_mark_evidence",
    "resolve_chart_axis_variant",
    "resolve_chart_mark_colors",
    "resolve_chart_render_params_for_task",
    "LabeledChartDefaults",
]
