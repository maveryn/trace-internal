"""Shared generators for histogram and boxplot chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import resolve_required_int_bounds
from .chart_scene import BoxPlotSpec, HistogramBinSpec, ViolinPlotSpec
from .labeled_chart_common import (
    LabeledChartDefaults,
    balanced_choice_from_values,
    choose_mark_count,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
    resolve_value_bounds,
    sample_chart_labels,
)


HistogramQueryVariant = str
BoxPlotQueryVariant = str
DensityQueryVariant = str

_CUMULATIVE_HISTOGRAM_VARIANTS = {
    "rank_item_bin_label",
}


@dataclass(frozen=True)
class DistributionChartDefaults:
    """Stable fallback defaults for distribution-style chart tasks."""

    bin_count_min: int = 8
    bin_count_max: int = 20
    bin_width_min: int = 1
    bin_width_max: int = 1
    bin_start_min: int = 1
    bin_start_max: int = 99
    bin_frequency_min: int = 1
    bin_frequency_max: int = 20
    interval_bin_span_min: int = 5
    interval_bin_span_max: int = 15
    outside_interval_bin_count_min: int = 2
    outside_interval_bin_count_max: int = 10
    category_count_min: int = 6
    category_count_max: int = 15
    value_min: int = 1
    value_max: int = 20
    violin_category_count_min: int = 4
    violin_category_count_max: int = 7


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


def _resolve_violin_category_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="violin_category_count_min",
        max_key="violin_category_count_max",
        fallback_min=int(defaults.violin_category_count_min),
        fallback_max=int(defaults.violin_category_count_max),
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


def _resolve_interval_bin_span_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="interval_bin_span_min",
        max_key="interval_bin_span_max",
        fallback_min=int(defaults.interval_bin_span_min),
        fallback_max=int(defaults.interval_bin_span_max),
        context=f"generation defaults for {task_id}",
    )


def _resolve_outside_interval_bin_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="outside_interval_bin_count_min",
        max_key="outside_interval_bin_count_max",
        fallback_min=int(defaults.outside_interval_bin_count_min),
        fallback_max=int(defaults.outside_interval_bin_count_max),
        context=f"generation defaults for {task_id}",
    )


def _resolve_boxplot_value_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
    instance_seed: int | None = None,
) -> Tuple[int, int]:
    chart_defaults = LabeledChartDefaults(value_min=int(defaults.value_min), value_max=int(defaults.value_max))
    return resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=chart_defaults,
        task_id=task_id,
        instance_seed=instance_seed,
    )


def _build_boxplot_spec_for_median(
    *,
    label: str,
    median: int,
    value_min: int,
    value_max: int,
    rng: Any,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
) -> BoxPlotSpec:
    """Construct one valid boxplot summary around a chosen median."""

    left_cap = min(3, int(median) - int(value_min) - 1)
    right_cap = min(3, int(value_max) - int(median))
    if int(left_cap) < 1 or int(right_cap) < 1:
        raise ValueError("no feasible quartile support for requested median")
    left_delta = int(rng.randint(1, int(left_cap)))
    right_delta = int(rng.randint(1, int(right_cap)))
    q1 = int(median) - int(left_delta)
    q3 = int(median) + int(right_delta)
    whisker_min = max(int(value_min), int(q1) - int(rng.randint(0, min(2, int(q1) - int(value_min)))))
    whisker_max = min(int(value_max), int(q3) + int(rng.randint(0, min(2, int(value_max) - int(q3)))))
    return BoxPlotSpec(
        label=str(label),
        whisker_min=int(whisker_min),
        q1=int(q1),
        median=int(median),
        q3=int(q3),
        whisker_max=int(whisker_max),
        fill_rgb=fill_rgb,
        outline_rgb=outline_rgb,
    )


def _resolve_optional_positive_int_bounds(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    gen_defaults: Mapping[str, Any] | None = None,
) -> Tuple[int, int] | None:
    """Resolve one optional positive integer bounds pair."""

    defaults = gen_defaults if isinstance(gen_defaults, Mapping) else {}
    min_value = params.get(min_key, defaults.get(min_key))
    max_value = params.get(max_key, defaults.get(max_key))
    if min_value is None and max_value is None:
        return None
    if min_value is None or max_value is None:
        raise ValueError(f"{min_key} and {max_key} must be set together")
    min_int = int(min_value)
    max_int = int(max_value)
    if min_int <= 0 or max_int <= 0:
        raise ValueError(f"{min_key} and {max_key} must be positive")
    if min_int > max_int:
        raise ValueError(f"{min_key} must be <= {max_key}")
    return min_int, max_int


def _resolve_optional_nonnegative_int_bounds(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    gen_defaults: Mapping[str, Any] | None = None,
) -> Tuple[int, int] | None:
    """Resolve one optional nonnegative integer bounds pair."""

    defaults = gen_defaults if isinstance(gen_defaults, Mapping) else {}
    min_value = params.get(min_key, defaults.get(min_key))
    max_value = params.get(max_key, defaults.get(max_key))
    if min_value is None and max_value is None:
        return None
    if min_value is None or max_value is None:
        raise ValueError(f"{min_key} and {max_key} must be set together")
    min_int = int(min_value)
    max_int = int(max_value)
    if min_int < 0 or max_int < 0:
        raise ValueError(f"{min_key} and {max_key} must be nonnegative")
    if min_int > max_int:
        raise ValueError(f"{min_key} must be <= {max_key}")
    return min_int, max_int


def _build_controlled_extreme_density_specs(
    *,
    labels: Sequence[str],
    candidate_modes: Sequence[int],
    query_variant: DensityQueryVariant,
    value_min: int,
    value_max: int,
    rng: Any,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    mode_window_size_bounds: Tuple[int, int],
    winner_gap_bounds: Tuple[int, int],
) -> Tuple[List[ViolinPlotSpec], Dict[str, Any]]:
    """Build a controlled unimodal set with one narrow extreme winner."""

    category_count = int(len(labels))
    min_window_size, max_window_size = mode_window_size_bounds
    if min_window_size < category_count:
        raise ValueError("mode_window_size_min must be >= category_count")
    if max_window_size < min_window_size:
        raise ValueError("mode_window_size_max must be >= mode_window_size_min")
    max_available_window = int(len(candidate_modes))
    if min_window_size > max_available_window:
        raise ValueError("mode window is larger than the available density support")

    feasible_window_sizes = [
        int(size)
        for size in range(int(min_window_size), min(int(max_window_size), max_available_window) + 1)
        if int(size) >= category_count
    ]
    if not feasible_window_sizes:
        raise ValueError("no feasible mode window sizes for controlled density generation")
    window_size = int(rng.choice(feasible_window_sizes))

    min_gap, max_gap = winner_gap_bounds
    max_feasible_gap = int(window_size) - int(category_count) + 1
    if max_feasible_gap < 1:
        raise ValueError("controlled density mode window leaves no room for a unique extreme winner")
    feasible_gaps = [
        int(gap)
        for gap in range(int(min_gap), int(max_gap) + 1)
        if 1 <= int(gap) <= int(max_feasible_gap)
    ]
    if not feasible_gaps:
        raise ValueError("winner gap bounds are infeasible for the requested controlled density window")
    winner_gap = int(rng.choice(feasible_gaps))

    low_bound = int(candidate_modes[0])
    high_bound = int(candidate_modes[-1])
    feasible_starts = list(range(int(low_bound), int(high_bound) - int(window_size) + 2))
    if not feasible_starts:
        raise ValueError("no feasible controlled density mode windows within candidate support")
    window_start = int(rng.choice(feasible_starts))
    window_modes = list(range(int(window_start), int(window_start) + int(window_size)))

    if str(query_variant) == "highest_mode":
        winner_mode = int(window_modes[-1])
        runner_up_mode = int(winner_mode) - int(winner_gap)
        remaining_pool = [int(mode) for mode in window_modes if int(mode) < int(runner_up_mode)]
        chosen_remaining = rng.sample(remaining_pool, category_count - 2)
        chosen_modes = list(chosen_remaining) + [int(runner_up_mode), int(winner_mode)]
    elif str(query_variant) == "lowest_mode":
        winner_mode = int(window_modes[0])
        runner_up_mode = int(winner_mode) + int(winner_gap)
        remaining_pool = [int(mode) for mode in window_modes if int(mode) > int(runner_up_mode)]
        chosen_remaining = rng.sample(remaining_pool, category_count - 2)
        chosen_modes = [int(winner_mode), int(runner_up_mode)] + list(chosen_remaining)
    else:
        raise ValueError(f"unsupported controlled extreme density query_variant: {query_variant}")

    rng.shuffle(chosen_modes)
    specs: List[ViolinPlotSpec] = []
    for label, mode in zip(labels, chosen_modes):
        support_padding_low = int(rng.randint(2, min(5, int(mode) - int(value_min))))
        support_padding_high = int(rng.randint(2, min(5, int(value_max) - int(mode))))
        specs.append(
            ViolinPlotSpec(
                label=str(label),
                support_min=int(mode) - int(support_padding_low),
                support_max=int(mode) + int(support_padding_high),
                mode_values=(int(mode),),
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
            )
        )

    return specs, {
        "generation_profile": "controlled_extreme",
        "mode_window_size": int(window_size),
        "extreme_winner_gap": int(winner_gap),
    }


def _build_controlled_bimodal_density_specs(
    *,
    labels: Sequence[str],
    candidate_modes: Sequence[int],
    value_min: int,
    value_max: int,
    rng: Any,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    separation_bounds: Tuple[int, int],
    clearance_bounds: Tuple[int, int],
) -> Tuple[List[ViolinPlotSpec], Dict[str, Any]]:
    """Build a controlled bimodal set with a clearer bimodal witness."""

    category_count = int(len(labels))
    min_separation, max_separation = separation_bounds
    min_clearance, max_clearance = clearance_bounds
    feasible_pairs: List[Tuple[int, int, int, List[int]]] = []
    for clearance in range(int(min_clearance), int(max_clearance) + 1):
        for lower in candidate_modes:
            for separation in range(int(min_separation), int(max_separation) + 1):
                upper = int(lower) + int(separation)
                if int(upper) not in candidate_modes:
                    continue
                distractors = [
                    int(mode)
                    for mode in candidate_modes
                    if int(mode) not in {int(lower), int(upper)}
                    and abs(int(mode) - int(lower)) > int(clearance)
                    and abs(int(mode) - int(upper)) > int(clearance)
                ]
                if len(distractors) >= category_count - 1:
                    feasible_pairs.append((int(lower), int(upper), int(clearance), distractors))
    if not feasible_pairs:
        raise ValueError("no feasible controlled bimodal density pairs for the requested separation/clearance")

    lower, upper, distractor_clearance, distractor_pool = feasible_pairs[int(rng.randint(0, len(feasible_pairs) - 1))]
    chosen_distractors = rng.sample(distractor_pool, category_count - 1)
    specs: List[ViolinPlotSpec] = []
    for index, label in enumerate(labels):
        if int(index) == 0:
            support_min = max(int(value_min), int(lower) - int(rng.randint(1, 2)))
            support_max = min(int(value_max), int(upper) + int(rng.randint(1, 2)))
            specs.append(
                ViolinPlotSpec(
                    label=str(label),
                    support_min=int(support_min),
                    support_max=int(support_max),
                    mode_values=(int(lower), int(upper)),
                    fill_rgb=fill_rgb,
                    outline_rgb=outline_rgb,
                )
            )
        else:
            mode = int(chosen_distractors[int(index) - 1])
            support_padding_low = int(rng.randint(2, min(5, int(mode) - int(value_min))))
            support_padding_high = int(rng.randint(2, min(5, int(value_max) - int(mode))))
            specs.append(
                ViolinPlotSpec(
                    label=str(label),
                    support_min=int(mode) - int(support_padding_low),
                    support_max=int(mode) + int(support_padding_high),
                    mode_values=(int(mode),),
                    fill_rgb=fill_rgb,
                    outline_rgb=outline_rgb,
                )
            )
    rng.shuffle(specs)
    return specs, {
        "generation_profile": "controlled_bimodal",
        "bimodal_mode_separation": int(upper) - int(lower),
        "bimodal_distractor_clearance": int(distractor_clearance),
    }


def _build_controlled_support_span_density_specs(
    *,
    labels: Sequence[str],
    query_variant: DensityQueryVariant,
    value_min: int,
    value_max: int,
    rng: Any,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    support_span_bounds: Tuple[int, int],
    winner_gap_bounds: Tuple[int, int],
) -> Tuple[List[ViolinPlotSpec], Dict[str, Any]]:
    """Build a controlled violin set with one unique support-span extremum."""

    category_count = int(len(labels))
    min_span, max_span = support_span_bounds
    value_span = int(value_max) - int(value_min)
    candidate_spans = [
        int(span)
        for span in range(int(min_span), min(int(max_span), int(value_span)) + 1)
        if int(span) >= 4
    ]
    if len(candidate_spans) < int(category_count):
        raise ValueError("not enough feasible support spans for controlled violin spread generation")

    min_gap, max_gap = winner_gap_bounds
    feasible_choices: List[Tuple[int, int, int, List[int]]] = []
    for gap in range(int(min_gap), int(max_gap) + 1):
        if int(gap) < 1:
            continue
        for winner_span in candidate_spans:
            if str(query_variant) == "widest_support":
                runner_span = int(winner_span) - int(gap)
                remaining_pool = [
                    int(span)
                    for span in candidate_spans
                    if int(span) < int(runner_span)
                ]
            elif str(query_variant) == "narrowest_support":
                runner_span = int(winner_span) + int(gap)
                remaining_pool = [
                    int(span)
                    for span in candidate_spans
                    if int(span) > int(runner_span)
                ]
            else:
                raise ValueError(f"unsupported controlled support-span variant: {query_variant}")
            if int(runner_span) in set(candidate_spans) and len(remaining_pool) >= int(category_count) - 2:
                feasible_choices.append((int(gap), int(winner_span), int(runner_span), list(remaining_pool)))
    if not feasible_choices:
        raise ValueError("support-span winner gap bounds are infeasible for the requested violin setup")

    winner_gap, winner_span, runner_span, remaining_pool = feasible_choices[
        int(rng.randint(0, len(feasible_choices) - 1))
    ]
    chosen_spans = [int(winner_span), int(runner_span)] + [
        int(span)
        for span in rng.sample(remaining_pool, int(category_count) - 2)
    ]
    rng.shuffle(chosen_spans)

    specs: List[ViolinPlotSpec] = []
    for label, support_span in zip(labels, chosen_spans):
        support_min = int(rng.randint(int(value_min), int(value_max) - int(support_span)))
        support_max = int(support_min) + int(support_span)
        inner_min = int(support_min) + 2
        inner_max = int(support_max) - 2
        mode = int(rng.randint(int(inner_min), int(inner_max))) if int(inner_min) <= int(inner_max) else int(
            round((int(support_min) + int(support_max)) / 2.0)
        )
        specs.append(
            ViolinPlotSpec(
                label=str(label),
                support_min=int(support_min),
                support_max=int(support_max),
                mode_values=(int(mode),),
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
            )
        )

    return specs, {
        "generation_profile": "controlled_support_span",
        "support_span_winner_gap": int(winner_gap),
        "support_span_bounds": [int(min_span), int(max_span)],
    }


def build_density_dataset_for_variant(
    *,
    query_variant: DensityQueryVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
    mark_style: Mapping[str, Any],
) -> Tuple[List[ViolinPlotSpec], str, List[int], Dict[str, Any]]:
    """Build one violin-backed density task dataset."""

    category_count_min, category_count_max = _resolve_violin_category_count_bounds(
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
        instance_seed=int(instance_seed),
    )
    category_count = choose_mark_count(
        list(range(int(category_count_min), int(category_count_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:category_count:{str(query_variant)}",
    )
    labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    rng = spawn_rng(int(instance_seed), f"{task_id}.density.{str(query_variant)}")
    fill_rgb = tuple(int(channel) for channel in mark_style["mark_fill_rgb"])
    outline_rgb = tuple(int(channel) for channel in mark_style["mark_outline_rgb"])

    specs: List[ViolinPlotSpec] = []
    generation_meta: Dict[str, Any] = {"generation_profile": "baseline"}
    if str(query_variant) in {"highest_mode", "lowest_mode"}:
        candidate_modes = list(range(int(value_min) + 3, int(value_max) - 2))
        if len(candidate_modes) < int(category_count):
            raise ValueError("density mode support is too small for requested category count")
        mode_window_size_bounds = _resolve_optional_positive_int_bounds(
            params,
            min_key="mode_window_size_min",
            max_key="mode_window_size_max",
            gen_defaults=gen_defaults,
        )
        winner_gap_bounds = _resolve_optional_positive_int_bounds(
            params,
            min_key="extreme_winner_gap_min",
            max_key="extreme_winner_gap_max",
            gen_defaults=gen_defaults,
        )
        if mode_window_size_bounds is not None or winner_gap_bounds is not None:
            if mode_window_size_bounds is None or winner_gap_bounds is None:
                raise ValueError(
                    "controlled extreme density generation requires both mode_window_size_* and "
                    "extreme_winner_gap_* bounds"
                )
            specs, generation_meta = _build_controlled_extreme_density_specs(
                labels=labels,
                candidate_modes=candidate_modes,
                query_variant=str(query_variant),
                value_min=int(value_min),
                value_max=int(value_max),
                rng=rng,
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
                mode_window_size_bounds=mode_window_size_bounds,
                winner_gap_bounds=winner_gap_bounds,
            )
        else:
            rng.shuffle(candidate_modes)
            chosen_modes = candidate_modes[: int(category_count)]
            rng.shuffle(chosen_modes)
            for label, mode in zip(labels, chosen_modes):
                support_padding_low = int(rng.randint(2, min(5, int(mode) - int(value_min))))
                support_padding_high = int(rng.randint(2, min(5, int(value_max) - int(mode))))
                specs.append(
                    ViolinPlotSpec(
                        label=str(label),
                        support_min=int(mode) - int(support_padding_low),
                        support_max=int(mode) + int(support_padding_high),
                        mode_values=(int(mode),),
                        fill_rgb=fill_rgb,
                        outline_rgb=outline_rgb,
                    )
                )
        if str(query_variant) == "highest_mode":
            winning_spec = max(specs, key=lambda spec: int(spec.mode_values[0]))
        else:
            winning_spec = min(specs, key=lambda spec: int(spec.mode_values[0]))
        answer_label = str(winning_spec.label)
        evidence_values = [int(winning_spec.mode_values[0])]
    elif str(query_variant) == "bimodal_label":
        candidate_modes = list(range(int(value_min) + 3, int(value_max) - 2))
        bimodal_separation_bounds = _resolve_optional_positive_int_bounds(
            params,
            min_key="bimodal_mode_separation_min",
            max_key="bimodal_mode_separation_max",
            gen_defaults=gen_defaults,
        )
        bimodal_clearance_bounds = _resolve_optional_nonnegative_int_bounds(
            params,
            min_key="bimodal_distractor_clearance_min",
            max_key="bimodal_distractor_clearance_max",
            gen_defaults=gen_defaults,
        )
        if bimodal_separation_bounds is not None or bimodal_clearance_bounds is not None:
            if bimodal_separation_bounds is None or bimodal_clearance_bounds is None:
                raise ValueError(
                    "controlled bimodal density generation requires both bimodal_mode_separation_* and "
                    "bimodal_distractor_clearance_* bounds"
                )
            specs, generation_meta = _build_controlled_bimodal_density_specs(
                labels=labels,
                candidate_modes=candidate_modes,
                value_min=int(value_min),
                value_max=int(value_max),
                rng=rng,
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
                separation_bounds=bimodal_separation_bounds,
                clearance_bounds=bimodal_clearance_bounds,
            )
        else:
            rng.shuffle(candidate_modes)
            unimodal_modes = candidate_modes[: int(category_count)]
            for index, (label, mode) in enumerate(zip(labels, unimodal_modes)):
                if int(index) == 0:
                    lower = int(rng.randint(int(value_min) + 2, int(value_max) - 7))
                    upper = int(rng.randint(int(lower) + 3, int(min(value_max - 2, lower + 6))))
                    support_min = max(int(value_min), int(lower) - int(rng.randint(1, 3)))
                    support_max = min(int(value_max), int(upper) + int(rng.randint(1, 3)))
                    specs.append(
                        ViolinPlotSpec(
                            label=str(label),
                            support_min=int(support_min),
                            support_max=int(support_max),
                            mode_values=(int(lower), int(upper)),
                            fill_rgb=fill_rgb,
                            outline_rgb=outline_rgb,
                        )
                    )
                else:
                    support_padding_low = int(rng.randint(2, min(5, int(mode) - int(value_min))))
                    support_padding_high = int(rng.randint(2, min(5, int(value_max) - int(mode))))
                    specs.append(
                        ViolinPlotSpec(
                            label=str(label),
                            support_min=int(mode) - int(support_padding_low),
                            support_max=int(mode) + int(support_padding_high),
                            mode_values=(int(mode),),
                            fill_rgb=fill_rgb,
                            outline_rgb=outline_rgb,
                        )
                    )
            rng.shuffle(specs)
        winning_spec = next(spec for spec in specs if len(spec.mode_values) == 2)
        answer_label = str(winning_spec.label)
        evidence_values = sorted(int(value) for value in winning_spec.mode_values)
    elif str(query_variant) in {"widest_support", "narrowest_support"}:
        support_span_bounds = _resolve_optional_positive_int_bounds(
            params,
            min_key="support_span_min",
            max_key="support_span_max",
            gen_defaults=gen_defaults,
        )
        if support_span_bounds is None:
            support_span_bounds = (6, max(6, int(value_max) - int(value_min) - 2))
        support_winner_gap_bounds = _resolve_optional_positive_int_bounds(
            params,
            min_key="support_winner_gap_min",
            max_key="support_winner_gap_max",
            gen_defaults=gen_defaults,
        )
        if support_winner_gap_bounds is None:
            support_winner_gap_bounds = (2, 4)
        specs, generation_meta = _build_controlled_support_span_density_specs(
            labels=labels,
            query_variant=str(query_variant),
            value_min=int(value_min),
            value_max=int(value_max),
            rng=rng,
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
            support_span_bounds=support_span_bounds,
            winner_gap_bounds=support_winner_gap_bounds,
        )
        if str(query_variant) == "widest_support":
            winning_spec = max(specs, key=lambda spec: int(spec.support_max) - int(spec.support_min))
        else:
            winning_spec = min(specs, key=lambda spec: int(spec.support_max) - int(spec.support_min))
        answer_label = str(winning_spec.label)
        evidence_values = [int(winning_spec.support_min), int(winning_spec.support_max)]
    else:
        raise ValueError(f"unsupported density query_variant: {query_variant}")

    trace_extras = {
        "scene_variant": "violin",
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "value_range": [int(value_min), int(value_max)],
        **generation_meta,
        "answer_label": str(answer_label),
        "evidence_values": [int(value) for value in evidence_values],
        "support_by_label": {
            str(spec.label): {
                "support_min": int(spec.support_min),
                "support_max": int(spec.support_max),
                "support_span": int(spec.support_max) - int(spec.support_min),
                "mode_values": [int(value) for value in spec.mode_values],
                "bimodal": bool(len(spec.mode_values) == 2),
            }
            for spec in specs
        },
    }
    return specs, str(answer_label), [int(value) for value in evidence_values], trace_extras


def _build_histogram_labels(*, start_value: int, bin_width: int, bin_count: int) -> List[str]:
    labels: List[str] = []
    for index in range(int(bin_count)):
        value = int(start_value) + int(index) * int(bin_width)
        labels.append(str(int(value)))
    return labels


def _histogram_answer_range(
    *,
    query_variant: HistogramQueryVariant,
    bin_count_max: int,
) -> Tuple[int, int]:
    if str(query_variant) == "bin_count_between_values":
        return 2, min(15, int(bin_count_max))
    if str(query_variant) in _CUMULATIVE_HISTOGRAM_VARIANTS:
        return 1, 99
    if str(query_variant) in {"interval_mass", "outside_interval_mass"}:
        raise ValueError(f"{query_variant} derives its answer from sampled bar counts")
    raise ValueError(f"unsupported histogram query_variant: {query_variant}")


def _resolve_histogram_target_answer(
    params: Mapping[str, Any],
    *,
    query_variant: HistogramQueryVariant,
    instance_seed: int,
    bin_count_max: int,
    task_id: str,
) -> int:
    default_min, default_max = _histogram_answer_range(
        query_variant=str(query_variant),
        bin_count_max=int(bin_count_max),
    )
    target_min = int(params.get("target_answer_min", default_min))
    target_max = int(params.get("target_answer_max", default_max))
    if int(target_min) > int(target_max):
        raise ValueError("target_answer_min must be <= target_answer_max")
    return balanced_choice_from_values(
        list(range(int(target_min), int(target_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:target_answer:{str(query_variant)}",
    )


def build_histogram_dataset_for_variant(
    *,
    query_variant: HistogramQueryVariant,
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
    interval_bin_span_min, interval_bin_span_max = _resolve_interval_bin_span_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    outside_interval_bin_count_min, outside_interval_bin_count_max = _resolve_outside_interval_bin_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )

    rng = spawn_rng(int(instance_seed), f"{task_id}.histogram.{str(query_variant)}")
    evidence_is_outside_interval = False

    if str(query_variant) == "interval_mass":
        feasible_bin_counts = [
            int(value)
            for value in range(int(bin_count_min), int(bin_count_max) + 1)
            if int(value) >= int(interval_bin_span_min)
        ]
        if not feasible_bin_counts:
            raise ValueError("no feasible histogram interval_mass construction for requested interval span range")
        bin_count = choose_mark_count(
            feasible_bin_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:histogram_bin_count:{str(query_variant)}",
        )
        max_interval_span = min(int(interval_bin_span_max), int(bin_count))
        relevant_count = balanced_choice_from_values(
            list(range(int(interval_bin_span_min), int(max_interval_span) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:interval_bin_span:{str(query_variant)}",
        )
        evidence_start = int(rng.randint(0, int(bin_count) - int(relevant_count)))
        evidence_stop = int(evidence_start) + int(relevant_count)
        relevant_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(relevant_count))
        ]
        target_answer = int(sum(int(value) for value in relevant_values))
        background_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(bin_count) - int(relevant_count))
        ]
        query_meta = {"interval_bin_span": int(relevant_count)}
    elif str(query_variant) == "outside_interval_mass":
        feasible_bin_counts = [
            int(value)
            for value in range(int(bin_count_min), int(bin_count_max) + 1)
            if min(int(outside_interval_bin_count_max), int(value) - 2) >= int(outside_interval_bin_count_min)
        ]
        if not feasible_bin_counts:
            raise ValueError("no feasible histogram outside_interval_mass construction for requested outside-bin range")
        bin_count = choose_mark_count(
            feasible_bin_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:histogram_bin_count:{str(query_variant)}",
        )
        max_outside_count = min(int(outside_interval_bin_count_max), int(bin_count) - 2)
        outside_count = balanced_choice_from_values(
            list(range(int(outside_interval_bin_count_min), int(max_outside_count) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:outside_interval_bin_count:{str(query_variant)}",
        )
        left_outside_count = int(rng.randint(1, int(outside_count) - 1))
        right_outside_count = int(outside_count) - int(left_outside_count)
        evidence_start = int(left_outside_count)
        evidence_stop = int(bin_count) - int(right_outside_count)
        relevant_count = int(evidence_stop) - int(evidence_start)
        relevant_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(relevant_count))
        ]
        background_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(outside_count))
        ]
        target_answer = int(sum(int(value) for value in background_values))
        evidence_is_outside_interval = True
        query_meta = {
            "interval_bin_span": int(relevant_count),
            "excluded_interval_bin_span": int(relevant_count),
            "outside_bin_count": int(outside_count),
            "outside_left_bin_count": int(left_outside_count),
            "outside_right_bin_count": int(right_outside_count),
        }
    elif str(query_variant) == "bin_count_between_values":
        target_answer = _resolve_histogram_target_answer(
            params,
            query_variant=str(query_variant),
            instance_seed=int(instance_seed),
            bin_count_max=int(bin_count_max),
            task_id=task_id,
        )
        feasible_bin_counts = [
            int(value)
            for value in range(int(bin_count_min), int(bin_count_max) + 1)
            if int(value) >= int(target_answer)
        ]
        if not feasible_bin_counts:
            raise ValueError("no feasible histogram bin_count_between_values construction for requested answer range")
        bin_count = choose_mark_count(
            feasible_bin_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:histogram_bin_count:{str(query_variant)}",
        )
        relevant_count = int(target_answer)
        evidence_start = int(rng.randint(0, int(bin_count) - int(relevant_count)))
        evidence_stop = int(evidence_start) + int(relevant_count)
        relevant_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(relevant_count))
        ]
        background_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(bin_count) - int(relevant_count))
        ]
        query_meta = {"interval_bin_span": int(relevant_count)}
    elif str(query_variant) in _CUMULATIVE_HISTOGRAM_VARIANTS:
        feasible_bin_counts = [
            int(value)
            for value in range(int(bin_count_min), int(bin_count_max) + 1)
            if int(value) >= 5
        ]
        if not feasible_bin_counts:
            raise ValueError("no feasible histogram cumulative-rank construction for requested bin-count range")
        bin_count = choose_mark_count(
            feasible_bin_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:histogram_bin_count:{str(query_variant)}",
        )
        sampled_values = [
            int(rng.randint(int(bin_frequency_min), int(bin_frequency_max)))
            for _ in range(int(bin_count))
        ]
        total_count = int(sum(sampled_values))
        min_answer_index = min(2, int(bin_count) - 1)
        max_answer_index = max(int(min_answer_index), int(bin_count) - 3)
        answer_index = balanced_choice_from_values(
            list(range(int(min_answer_index), int(max_answer_index) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:answer_bin_index:{str(query_variant)}",
        )
        previous_cumulative = int(sum(sampled_values[: int(answer_index)]))
        answer_bin_count = int(sampled_values[int(answer_index)])
        target_rank = balanced_choice_from_values(
            list(range(int(previous_cumulative) + 1, int(previous_cumulative) + int(answer_bin_count) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:target_rank:{str(query_variant)}",
        )
        rank_fraction_numerator = 0
        rank_fraction_denominator = 0
        evidence_start = int(answer_index)
        evidence_stop = int(answer_index) + 1
        relevant_count = 1
        relevant_values = [int(sampled_values[int(answer_index)])]
        background_values = [
            int(value)
            for index, value in enumerate(sampled_values)
            if int(index) != int(answer_index)
        ]
        target_answer = -1
        query_meta = {
            "target_rank": int(target_rank),
            "total_count": int(total_count),
            "rank_fraction_numerator": int(rank_fraction_numerator),
            "rank_fraction_denominator": int(rank_fraction_denominator),
            "answer_bin_index": int(answer_index),
            "answer_prefix_bin_count": int(evidence_stop),
            "cumulative_count_before_answer_bin": int(previous_cumulative),
            "answer_bin_count": int(answer_bin_count),
            "cumulative_count_through_answer_bin": int(previous_cumulative) + int(answer_bin_count),
        }
    else:
        raise ValueError(f"unsupported histogram query_variant: {query_variant}")

    if int(bin_width_min) < 1 or int(bin_width_max) < int(bin_width_min):
        raise ValueError("histogram bin-width range must be positive and ordered")
    bin_width = balanced_choice_from_values(
        list(range(int(bin_width_min), int(bin_width_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:bin_width:{str(query_variant)}",
    )
    capped_bin_start_max = min(int(bin_start_max), 100 - (int(bin_count) * int(bin_width)))
    if int(capped_bin_start_max) < int(bin_start_min):
        raise ValueError("histogram bin_start range cannot keep the largest x-axis value <= 99")
    start_value = balanced_choice_from_values(
        list(range(int(bin_start_min), int(capped_bin_start_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:bin_start:{str(query_variant)}",
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

    if bool(evidence_is_outside_interval):
        evidence_labels = [str(label) for label in labels[: int(evidence_start)]]
        evidence_labels.extend(str(label) for label in labels[int(evidence_stop) :])
    else:
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
    if str(query_variant) in {"interval_mass", "bin_count_between_values", "outside_interval_mass"}:
        query_interval_label = f"{bins[int(evidence_start)].interval_start}-{bins[int(evidence_stop) - 1].interval_end}"
        query_meta["query_interval_start_value"] = int(bins[int(evidence_start)].interval_start)
        query_meta["query_interval_end_value"] = int(bins[int(evidence_stop) - 1].interval_end)
    if str(query_variant) in _CUMULATIVE_HISTOGRAM_VARIANTS:
        query_bin_label = str(bins[int(query_meta["answer_bin_index"])].label)
        target_answer = int(query_bin_label)
        query_meta["answer_bin_label"] = str(query_bin_label)
        query_meta["answer_bin_value"] = int(target_answer)

    trace_extras = {
        "scene_variant": "histogram",
        "bin_count": int(bin_count),
        "bin_count_range": [int(bin_count_min), int(bin_count_max)],
        "bin_width": int(bin_width),
        "bin_width_range": [int(bin_width_min), int(bin_width_max)],
        "bin_start": int(start_value),
        "bin_start_range": [int(bin_start_min), int(capped_bin_start_max)],
        "bin_axis_value_max": 99,
        "bin_frequency_range": [int(bin_frequency_min), int(bin_frequency_max)],
        "interval_bin_span_range": [int(interval_bin_span_min), int(interval_bin_span_max)],
        "outside_interval_bin_count_range": [
            int(outside_interval_bin_count_min),
            int(outside_interval_bin_count_max),
        ],
        "target_answer": int(target_answer),
        "target_answer_range": (
            []
            if str(query_variant) in {"interval_mass", "outside_interval_mass"}
            else (
                [int(labels[0]), int(labels[-1])]
                if str(query_variant) in _CUMULATIVE_HISTOGRAM_VARIANTS
                else list(_histogram_answer_range(query_variant=str(query_variant), bin_count_max=int(bin_count_max)))
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


def build_boxplot_median_rank_difference_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
    mark_style: Mapping[str, Any],
) -> Tuple[List[BoxPlotSpec], int, List[str], Dict[str, Any]]:
    """Build a boxplot scene for a ranked-median numeric difference query."""

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
        instance_seed=int(instance_seed),
    )
    upper_rank = max(1, int(params.get("median_rank_upper_rank", gen_defaults.get("median_rank_upper_rank", 1))))
    lower_rank_raw = params.get("median_rank_lower_rank", gen_defaults.get("median_rank_lower_rank", 3))
    lower_rank_fixed: int | None
    if str(lower_rank_raw).strip().lower() in {"lowest", "bottom", "last"}:
        lower_rank_fixed = None
    else:
        lower_rank_fixed = max(int(upper_rank) + 1, int(lower_rank_raw))
    category_count_min = max(int(category_count_min), int(lower_rank_fixed or (int(upper_rank) + 1)))
    category_count = choose_mark_count(
        list(range(int(category_count_min), int(category_count_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:category_count:median_rank_difference_value",
    )
    lower_rank = int(lower_rank_fixed or int(category_count))
    median_min = int(value_min) + 2
    median_max = int(value_max) - 2
    candidate_medians = list(range(int(median_min), int(median_max) + 1))
    if len(candidate_medians) < int(category_count):
        raise ValueError("boxplot median support is too small for requested category count")
    answer_min = max(
        1,
        int(params.get("median_rank_difference_min", gen_defaults.get("median_rank_difference_min", 1))),
    )
    answer_max_raw = params.get("median_rank_difference_max", gen_defaults.get("median_rank_difference_max"))
    answer_max = None if answer_max_raw is None else max(int(answer_min), int(answer_max_raw))

    rng = spawn_rng(int(instance_seed), f"{task_id}.boxplot.median_rank_difference_value")
    medians: List[int] | None = None
    ranked_medians: List[int] = []
    answer = 0
    for _ in range(512):
        candidate = [int(value) for value in rng.sample(candidate_medians, int(category_count))]
        ranked = sorted(candidate, reverse=True)
        diff = int(ranked[int(upper_rank) - 1]) - int(ranked[int(lower_rank) - 1])
        if int(diff) < int(answer_min):
            continue
        if answer_max is not None and int(diff) > int(answer_max):
            continue
        medians = list(candidate)
        ranked_medians = list(ranked)
        answer = int(diff)
        break
    if medians is None:
        raise ValueError("unable to construct ranked-median boxplot difference within requested answer bounds")

    labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    fill_rgb = tuple(int(channel) for channel in mark_style["mark_fill_rgb"])
    outline_rgb = tuple(int(channel) for channel in mark_style["mark_outline_rgb"])
    specs = [
        _build_boxplot_spec_for_median(
            label=str(label),
            median=int(median),
            value_min=int(value_min),
            value_max=int(value_max),
            rng=rng,
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
        )
        for label, median in zip(labels, medians)
    ]
    label_by_median = {int(spec.median): str(spec.label) for spec in specs}
    upper_median = int(ranked_medians[int(upper_rank) - 1])
    lower_median = int(ranked_medians[int(lower_rank) - 1])
    upper_label = str(label_by_median[int(upper_median)])
    lower_label = str(label_by_median[int(lower_median)])
    trace_extras = {
        "scene_variant": "boxplot",
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "value_range": [int(value_min), int(value_max)],
        "labels": [str(spec.label) for spec in specs],
        "answer_value": int(answer),
        "upper_rank": int(upper_rank),
        "lower_rank": int(lower_rank),
        "rank_pair": (
            "top_bottom"
            if int(lower_rank) == int(category_count)
            else f"top_{int(lower_rank)}"
        ),
        "upper_rank_label": str(upper_label),
        "lower_rank_label": str(lower_label),
        "upper_rank_median": int(upper_median),
        "lower_rank_median": int(lower_median),
        "evidence_labels": [str(upper_label), str(lower_label)],
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
    return specs, int(answer), [str(upper_label), str(lower_label)], trace_extras


def build_boxplot_paired_median_shift_dataset(
    *,
    query_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: DistributionChartDefaults,
    task_id: str,
    mark_style: Mapping[str, Any],
) -> Tuple[List[BoxPlotSpec], List[BoxPlotSpec], str, List[str], Dict[str, Any]]:
    """Build matched before/after boxplot panels and a median-shift label query."""

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
        instance_seed=int(instance_seed),
    )
    category_count = choose_mark_count(
        list(range(int(category_count_min), int(category_count_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:category_count:{str(query_variant)}",
    )
    median_min = int(value_min) + 2
    median_max = int(value_max) - 2
    max_shift_support = max(1, (int(median_max) - int(median_min)) // 2)
    shift_min = max(1, int(params.get("paired_median_shift_min", gen_defaults.get("paired_median_shift_min", 2))))
    shift_max = min(
        int(max_shift_support),
        max(int(shift_min), int(params.get("paired_median_shift_max", gen_defaults.get("paired_median_shift_max", 12)))),
    )
    shift_support = list(range(int(shift_min), int(shift_max) + 1))
    if len(shift_support) < int(category_count):
        raise ValueError("paired boxplot shift support is too small for requested category count")

    rng = spawn_rng(int(instance_seed), f"{task_id}.boxplot.{str(query_variant)}")
    base_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    shift_magnitudes = [int(value) for value in rng.sample(shift_support, int(category_count))]
    rng.shuffle(shift_magnitudes)
    if str(query_variant) == "paired_median_greatest_increase_label":
        signed_shifts = [int(value) for value in shift_magnitudes]
        answer_index = max(range(int(category_count)), key=lambda idx: int(signed_shifts[idx]))
        shift_direction = "increase"
    elif str(query_variant) == "paired_median_greatest_decrease_label":
        signed_shifts = [-int(value) for value in shift_magnitudes]
        answer_index = max(range(int(category_count)), key=lambda idx: -int(signed_shifts[idx]))
        shift_direction = "decrease"
    elif str(query_variant) == "paired_median_greatest_absolute_change_label":
        signed_shifts = [
            int(value) if int(rng.randint(0, 1)) == 1 else -int(value)
            for value in shift_magnitudes
        ]
        answer_index = max(range(int(category_count)), key=lambda idx: abs(int(signed_shifts[idx])))
        shift_direction = "absolute_change"
    else:
        raise ValueError(f"unsupported paired boxplot query variant: {query_variant}")

    before_fill = tuple(int(channel) for channel in mark_style["mark_fill_rgb"])
    outline_rgb = tuple(int(channel) for channel in mark_style["mark_outline_rgb"])
    after_fill = tuple(
        int(max(20, min(235, round(0.55 * float(channel) + 70.0))))
        for channel in reversed(before_fill)
    )

    before_specs: List[BoxPlotSpec] = []
    after_specs: List[BoxPlotSpec] = []
    pairs: Dict[str, Dict[str, Any]] = {}
    for base_label, shift in zip(base_labels, signed_shifts):
        if int(shift) >= 0:
            before_min = int(median_min)
            before_max = int(median_max) - int(shift)
        else:
            before_min = int(median_min) - int(shift)
            before_max = int(median_max)
        if int(before_min) > int(before_max):
            raise ValueError("no feasible paired median support for requested shift")
        before_median = int(rng.randint(int(before_min), int(before_max)))
        after_median = int(before_median) + int(shift)
        before_label = f"{str(base_label)}__before"
        after_label = f"{str(base_label)}__after"
        before_specs.append(
            _build_boxplot_spec_for_median(
                label=str(base_label),
                median=int(before_median),
                value_min=int(value_min),
                value_max=int(value_max),
                rng=rng,
                fill_rgb=before_fill,
                outline_rgb=outline_rgb,
            )
        )
        after_specs.append(
            _build_boxplot_spec_for_median(
                label=str(base_label),
                median=int(after_median),
                value_min=int(value_min),
                value_max=int(value_max),
                rng=rng,
                fill_rgb=after_fill,
                outline_rgb=outline_rgb,
            )
        )
        pairs[str(base_label)] = {
            "before_label": str(before_label),
            "after_label": str(after_label),
            "display_label": str(base_label),
            "before_panel": "before",
            "after_panel": "after",
            "before_median": int(before_median),
            "after_median": int(after_median),
            "signed_shift": int(shift),
            "absolute_shift": abs(int(shift)),
        }

    answer_label = str(base_labels[int(answer_index)])
    evidence_labels = [
        str(pairs[str(answer_label)]["before_label"]),
        str(pairs[str(answer_label)]["after_label"]),
    ]
    trace_extras = {
        "scene_variant": "boxplot",
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "rendered_boxplot_count": int(len(before_specs) + len(after_specs)),
        "rendered_boxplot_count_range": [int(category_count_min) * 2, int(category_count_max) * 2],
        "value_range": [int(value_min), int(value_max)],
        "base_labels": [str(label) for label in base_labels],
        "labels": [str(label) for label in base_labels],
        "rendered_labels": [
            *(f"{str(label)}__before" for label in base_labels),
            *(f"{str(label)}__after" for label in base_labels),
        ],
        "answer_label": str(answer_label),
        "answer_shift": int(pairs[str(answer_label)]["signed_shift"]),
        "answer_absolute_shift": int(pairs[str(answer_label)]["absolute_shift"]),
        "shift_direction": str(shift_direction),
        "evidence_labels": list(evidence_labels),
        "paired_panels": {"before": "Before", "after": "After"},
        "pairs_by_base_label": dict(pairs),
        "quartiles_by_label": {
            **{
                f"{str(spec.label)}__before": {
                    "display_label": str(spec.label),
                    "panel": "before",
                    "whisker_min": int(spec.whisker_min),
                    "q1": int(spec.q1),
                    "median": int(spec.median),
                    "q3": int(spec.q3),
                    "whisker_max": int(spec.whisker_max),
                    "iqr": int(spec.q3) - int(spec.q1),
                }
                for spec in before_specs
            },
            **{
                f"{str(spec.label)}__after": {
                    "display_label": str(spec.label),
                    "panel": "after",
                    "whisker_min": int(spec.whisker_min),
                    "q1": int(spec.q1),
                    "median": int(spec.median),
                    "q3": int(spec.q3),
                    "whisker_max": int(spec.whisker_max),
                    "iqr": int(spec.q3) - int(spec.q1),
                }
                for spec in after_specs
            }
        },
        "quartiles_by_base_label": {
            str(base_label): {
                "before": {
                    "whisker_min": int(before_spec.whisker_min),
                    "q1": int(before_spec.q1),
                    "median": int(before_spec.median),
                    "q3": int(before_spec.q3),
                    "whisker_max": int(before_spec.whisker_max),
                    "iqr": int(before_spec.q3) - int(before_spec.q1),
                },
                "after": {
                    "whisker_min": int(after_spec.whisker_min),
                    "q1": int(after_spec.q1),
                    "median": int(after_spec.median),
                    "q3": int(after_spec.q3),
                    "whisker_max": int(after_spec.whisker_max),
                    "iqr": int(after_spec.q3) - int(after_spec.q1),
                },
            }
            for base_label, before_spec, after_spec in zip(base_labels, before_specs, after_specs)
        },
        "before_medians_by_label": {
            str(spec.label): int(spec.median)
            for spec in before_specs
        },
        "after_medians_by_label": {
            str(spec.label): int(spec.median)
            for spec in after_specs
        },
    }
    return before_specs, after_specs, str(answer_label), list(evidence_labels), trace_extras


def build_boxplot_dataset_for_variant(
    *,
    query_variant: BoxPlotQueryVariant,
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
        instance_seed=int(instance_seed),
    )
    category_count = choose_mark_count(
        list(range(int(category_count_min), int(category_count_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:category_count:{str(query_variant)}",
    )
    labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    rng = spawn_rng(int(instance_seed), f"{task_id}.boxplot.{str(query_variant)}")
    fill_rgb = tuple(int(channel) for channel in mark_style["mark_fill_rgb"])
    outline_rgb = tuple(int(channel) for channel in mark_style["mark_outline_rgb"])

    def _sample_clustered_unique(pool_min: int, pool_max: int, count: int) -> List[int]:
        if int(count) <= 0:
            return []
        window_size = max(int(count) + 2, 4)
        lower = max(int(pool_min), int(pool_max) - int(window_size) + 1)
        pool = list(range(int(lower), int(pool_max) + 1))
        if len(pool) < int(count):
            pool = list(range(int(pool_min), int(pool_max) + 1))
        if len(pool) < int(count):
            raise ValueError("insufficient clustered support for unique sampling")
        rng.shuffle(pool)
        return [int(value) for value in pool[: int(count)]]

    def _sample_clustered_unique_low(pool_min: int, pool_max: int, count: int) -> List[int]:
        if int(count) <= 0:
            return []
        window_size = max(int(count) + 2, 4)
        upper = min(int(pool_max), int(pool_min) + int(window_size) - 1)
        pool = list(range(int(pool_min), int(upper) + 1))
        if len(pool) < int(count):
            pool = list(range(int(pool_min), int(pool_max) + 1))
        if len(pool) < int(count):
            raise ValueError("insufficient clustered support for unique low-end sampling")
        rng.shuffle(pool)
        return [int(value) for value in pool[: int(count)]]

    def _sample_unique_top_gap_margins(*, support_max: int, count: int, gap_min: int, gap_max: int) -> List[int]:
        if int(count) < 2:
            raise ValueError("reference-median boxplot tasks require at least two queried-side candidates")
        if int(support_max) < int(count):
            raise ValueError("reference-median margin support is too small for requested category count")
        feasible_pairs: List[Tuple[int, int]] = []
        for winner in range(1, int(support_max) + 1):
            for gap in range(int(gap_min), int(gap_max) + 1):
                runner_up = int(winner) - int(gap)
                if int(runner_up) < 1:
                    continue
                if int(runner_up) - 1 < int(count) - 2:
                    continue
                feasible_pairs.append((int(winner), int(runner_up)))
        if not feasible_pairs:
            raise ValueError("unable to construct unique reference-median winner margins")
        winner_margin, runner_up_margin = feasible_pairs[int(rng.randint(0, len(feasible_pairs) - 1))]
        other_pool = list(range(1, int(runner_up_margin)))
        other_margins = rng.sample(other_pool, int(count) - 2) if int(count) > 2 else []
        return sorted([int(winner_margin), int(runner_up_margin), *[int(value) for value in other_margins]])

    def _build_box_for_median(label: str, median: int) -> BoxPlotSpec:
        return _build_boxplot_spec_for_median(
            label=str(label),
            median=int(median),
            value_min=int(value_min),
            value_max=int(value_max),
            rng=rng,
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
        )

    def _resolve_reference_side_count(
        *,
        direction: str,
        candidate_count: int,
        median_min: int,
        median_max: int,
    ) -> int:
        min_key = "median_reference_above_count_min" if str(direction) == "above" else "median_reference_below_count_min"
        max_key = "median_reference_above_count_max" if str(direction) == "above" else "median_reference_below_count_max"
        explicit_min = params.get(min_key)
        explicit_max = params.get(max_key)
        if explicit_min is None and explicit_max is None:
            count_min = max(2, int(candidate_count) // 2)
            count_max = min(int(candidate_count), int(count_min) + 1)
        else:
            count_min = max(2, int(2 if explicit_min is None else explicit_min))
            count_max = min(
                int(candidate_count),
                max(int(count_min), int(candidate_count if explicit_max is None else explicit_max)),
            )
        feasible_counts: List[int] = []
        for active_count in range(int(count_min), int(count_max) + 1):
            passive_count = int(candidate_count) - int(active_count)
            if int(passive_count) < 0:
                continue
            if str(direction) == "above":
                threshold_min = max(int(value_min) + 3, int(median_min) + int(passive_count))
                threshold_max = int(median_max) - int(active_count)
            else:
                threshold_min = int(median_min) + int(active_count)
                threshold_max = int(median_max) - int(passive_count)
            if int(threshold_min) <= int(threshold_max):
                feasible_counts.append(int(active_count))
        if not feasible_counts:
            raise ValueError("no feasible reference-median side counts for requested category count")
        return int(rng.choice(feasible_counts))

    def _build_reference_median_specs(*, direction: str) -> Tuple[List[BoxPlotSpec], str, int, Dict[str, Any]]:
        if int(category_count) < 4:
            raise ValueError("boxplot reference-median task requires at least four categories")
        gap_min = max(1, int(params.get("median_reference_winner_gap_min", 1)))
        gap_max = max(int(gap_min), int(params.get("median_reference_winner_gap_max", gap_min)))
        median_min = int(value_min) + 2
        median_max = int(value_max) - 2
        candidate_count = int(category_count) - 1
        active_count = _resolve_reference_side_count(
            direction=str(direction),
            candidate_count=int(candidate_count),
            median_min=int(median_min),
            median_max=int(median_max),
        )
        passive_count = int(candidate_count) - int(active_count)
        if str(direction) == "above":
            threshold_min = max(int(value_min) + 3, int(median_min) + int(passive_count))
            threshold_max = int(median_max) - int(active_count)
        elif str(direction) == "below":
            threshold_min = int(median_min) + int(active_count)
            threshold_max = int(median_max) - int(passive_count)
        else:
            raise ValueError(f"unsupported reference-median direction: {direction}")
        if int(threshold_min) > int(threshold_max):
            raise ValueError("boxplot reference-median support is too small for requested category count")
        reference_threshold = int(rng.randint(int(threshold_min), int(threshold_max)))
        if str(direction) == "above":
            active_support = int(median_max) - int(reference_threshold)
            passive_medians = _sample_clustered_unique_low(
                int(median_min),
                int(reference_threshold) - 1,
                int(passive_count),
            )
        else:
            active_support = int(reference_threshold) - int(median_min)
            passive_medians = _sample_clustered_unique(
                int(reference_threshold) + 1,
                int(median_max),
                int(passive_count),
            )
        active_margins = _sample_unique_top_gap_margins(
            support_max=int(active_support),
            count=int(active_count),
            gap_min=int(gap_min),
            gap_max=int(gap_max),
        )

        shuffled_labels = list(labels)
        rng.shuffle(shuffled_labels)
        reference_label = str(shuffled_labels[0])
        candidate_labels = [str(label) for label in shuffled_labels[1:]]
        active_labels = list(candidate_labels[: int(active_count)])
        passive_labels = list(candidate_labels[int(active_count) :])
        label_to_margin = {
            str(label): int(margin)
            for label, margin in zip(active_labels, active_margins)
        }
        winner_margin = int(max(active_margins))
        winner_label = next(
            str(label)
            for label, margin in label_to_margin.items()
            if int(margin) == int(winner_margin)
        )

        label_to_box: Dict[str, BoxPlotSpec] = {}
        if str(direction) == "above":
            reference_q3 = int(reference_threshold)
            reference_q1 = int(rng.randint(int(value_min) + 1, int(reference_q3) - 2))
            reference_median = int(rng.randint(int(reference_q1) + 1, int(reference_q3) - 1))
            reference_whisker_min = max(
                int(value_min),
                int(reference_q1) - int(rng.randint(0, min(2, int(reference_q1) - int(value_min)))),
            )
            reference_whisker_max = min(
                int(value_max),
                int(reference_q3) + int(rng.randint(0, min(2, int(value_max) - int(reference_q3)))),
            )
            label_to_box[str(reference_label)] = BoxPlotSpec(
                label=str(reference_label),
                whisker_min=int(reference_whisker_min),
                q1=int(reference_q1),
                median=int(reference_median),
                q3=int(reference_q3),
                whisker_max=int(reference_whisker_max),
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
            )
            for label, margin in label_to_margin.items():
                label_to_box[str(label)] = _build_box_for_median(str(label), int(reference_threshold) + int(margin))
            reference_meta = {"reference_q3": int(reference_q3)}
        else:
            reference_q1 = int(reference_threshold)
            reference_median = int(rng.randint(int(reference_q1) + 1, int(value_max) - 1))
            reference_q3 = int(rng.randint(int(reference_median) + 1, int(value_max)))
            reference_whisker_min = max(
                int(value_min),
                int(reference_q1) - int(rng.randint(0, min(2, int(reference_q1) - int(value_min)))),
            )
            reference_whisker_max = min(
                int(value_max),
                int(reference_q3) + int(rng.randint(0, min(2, int(value_max) - int(reference_q3)))),
            )
            label_to_box[str(reference_label)] = BoxPlotSpec(
                label=str(reference_label),
                whisker_min=int(reference_whisker_min),
                q1=int(reference_q1),
                median=int(reference_median),
                q3=int(reference_q3),
                whisker_max=int(reference_whisker_max),
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
            )
            for label, margin in label_to_margin.items():
                label_to_box[str(label)] = _build_box_for_median(str(label), int(reference_threshold) - int(margin))
            reference_meta = {"reference_q1": int(reference_q1)}

        for label, median in zip(passive_labels, passive_medians):
            label_to_box[str(label)] = _build_box_for_median(str(label), int(median))
        return [label_to_box[str(label)] for label in labels], str(winner_label), int(winner_margin), {
            "reference_label": str(reference_label),
            "winner_margin": int(winner_margin),
            "reference_side_count": int(active_count),
            "reference_other_side_count": int(passive_count),
            **reference_meta,
        }

    specs: List[BoxPlotSpec] = []
    generation_meta: Dict[str, Any] = {}
    if str(query_variant) == "median_above_reference_q3":
        specs, answer_label, evidence_value, generation_meta = _build_reference_median_specs(direction="above")
    elif str(query_variant) == "median_below_reference_q1":
        specs, answer_label, evidence_value, generation_meta = _build_reference_median_specs(direction="below")
    elif str(query_variant) in {"largest_iqr", "smallest_iqr"}:
        support_min = 2
        support_max = int(value_max) - int(value_min) - 3
        feasible_iqrs = list(range(int(support_min), int(support_max) + 1))
        if len(feasible_iqrs) < int(category_count):
            raise ValueError("boxplot IQR support is too small for requested category count")
        gap_min = int(params.get("iqr_winner_gap_min", 0))
        gap_max = int(params.get("iqr_winner_gap_max", gap_min))
        if int(gap_max) > 0:
            gap_min = max(1, int(gap_min))
            gap_max = max(int(gap_min), int(gap_max))
            if str(query_variant) == "largest_iqr":
                answer_min = int(support_min) + int(gap_min) + int(category_count) - 2
                if int(answer_min) > int(support_max):
                    raise ValueError("boxplot largest-IQR gap support is too small for requested category count")
                winner_iqr = int(rng.randint(int(answer_min), int(support_max)))
                gap_cap = min(int(gap_max), int(winner_iqr) - int(support_min) - int(category_count) + 2)
                winner_gap = int(rng.randint(int(gap_min), int(gap_cap)))
                runner_up = int(winner_iqr) - int(winner_gap)
                other_iqrs = _sample_clustered_unique(
                    int(support_min),
                    int(runner_up) - 1,
                    int(category_count) - 2,
                )
                iqrs = [int(winner_iqr), int(runner_up), *other_iqrs]
            else:
                answer_max = int(support_max) - int(gap_min) - int(category_count) + 2
                if int(answer_max) < int(support_min):
                    raise ValueError("boxplot smallest-IQR gap support is too small for requested category count")
                winner_iqr = int(rng.randint(int(support_min), int(answer_max)))
                gap_cap = min(int(gap_max), int(support_max) - int(winner_iqr) - int(category_count) + 2)
                winner_gap = int(rng.randint(int(gap_min), int(gap_cap)))
                runner_up = int(winner_iqr) + int(winner_gap)
                other_iqrs = _sample_clustered_unique_low(
                    int(runner_up) + 1,
                    int(support_max),
                    int(category_count) - 2,
                )
                iqrs = [int(winner_iqr), int(runner_up), *other_iqrs]
            rng.shuffle(iqrs)
        else:
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
        if str(query_variant) == "largest_iqr":
            answer_label = max(specs, key=lambda spec: int(spec.q3) - int(spec.q1)).label
            evidence_value = max(int(spec.q3) - int(spec.q1) for spec in specs)
        else:
            answer_label = min(specs, key=lambda spec: int(spec.q3) - int(spec.q1)).label
            evidence_value = min(int(spec.q3) - int(spec.q1) for spec in specs)
    else:
        raise ValueError(f"unsupported boxplot query_variant: {query_variant}")

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
        **generation_meta,
    }
    return specs, str(answer_label), int(evidence_value), trace_extras


__all__ = [
    "DensityQueryVariant",
    "DistributionChartDefaults",
    "build_boxplot_dataset_for_variant",
    "build_boxplot_median_rank_difference_dataset",
    "build_boxplot_paired_median_shift_dataset",
    "build_density_dataset_for_variant",
    "build_histogram_dataset_for_variant",
    "projected_mark_evidence",
    "resolve_chart_axis_variant",
    "resolve_chart_mark_colors",
    "resolve_chart_render_params_for_task",
    "LabeledChartDefaults",
]
