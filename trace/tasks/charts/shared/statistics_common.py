"""Shared generation/render helpers for chart statistics tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.color_distance import sample_color_with_distance_constraints
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.labeling import assign_random_shuffled_labels
from ...shared.named_colors import darken_color
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .chart_scene import (
    ChartRenderParams,
    SUPPORTED_CHART_SCENE_VARIANTS,
    resolve_chart_render_params,
)


StatisticKind = str
SceneVariant = str
SUPPORTED_STATISTICS_SCENE_VARIANTS: Tuple[str, ...] = tuple(SUPPORTED_CHART_SCENE_VARIANTS)


@dataclass(frozen=True)
class ChartStatisticsDefaults:
    """Stable fallback defaults shared by chart statistics tasks."""

    mark_count_min: int = 5
    mark_count_max: int = 10
    value_min: int = 1
    value_max: int = 20
    canvas_width: int = 800
    canvas_height: int = 600
    plot_margin_left_px: int = 92
    plot_margin_right_px: int = 46
    plot_margin_top_px: int = 44
    plot_margin_bottom_px: int = 92
    axis_line_width_px: int = 2
    grid_line_width_px: int = 1
    tick_length_px: int = 8
    label_font_size_px: int = 22
    tick_font_size_px: int = 18
    label_stroke_width_px: int = 2
    mark_outline_width_px: int = 2
    line_width_px: int = 4
    point_radius_px: int = 8
    bar_width_fraction: float = 0.58
    mark_color_channel_min: int = 0
    mark_color_channel_max: int = 220
    mark_color_min_distance: float = 40.0
    mark_color_distance_space: str = "lab"
    balanced_task_variant_sampling: bool = True
    balanced_scene_variant_sampling: bool = True


def sorted_labels(labels: Sequence[str]) -> List[str]:
    """Return labels in deterministic alphabetical order."""

    return [str(label) for label in sorted(str(label) for label in labels)]


def resolve_value_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: ChartStatisticsDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive per-mark value bounds."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="value_min",
        max_key="value_max",
        fallback_min=int(defaults.value_min),
        fallback_max=int(defaults.value_max),
        context=f"generation defaults for {task_id}",
    )


def resolve_mark_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: ChartStatisticsDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive chart mark-count bounds."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="mark_count_min",
        max_key="mark_count_max",
        fallback_min=int(defaults.mark_count_min),
        fallback_max=int(defaults.mark_count_max),
        context=f"generation defaults for {task_id}",
    )


def resolve_target_answer_range(
    params: Mapping[str, Any],
    *,
    task_variant: StatisticKind,
    mark_count_min: int,
    mark_count_max: int,
    value_min: int,
    value_max: int,
    target_answer_ranges: Mapping[str, Tuple[int, int]],
) -> Tuple[int, int]:
    """Resolve supported target-answer bounds for one statistic."""

    if str(task_variant) == "sum":
        default_min = int(mark_count_min) * int(value_min)
        default_max = int(mark_count_max) * int(value_max)
    else:
        default_min, default_max = target_answer_ranges[str(task_variant)]
    explicit_min = params.get("target_answer_min", None)
    explicit_max = params.get("target_answer_max", None)
    if explicit_min is None and explicit_max is None:
        return int(default_min), int(default_max)
    min_value = int(default_min if explicit_min is None else explicit_min)
    max_value = int(default_max if explicit_max is None else explicit_max)
    if int(min_value) > int(max_value):
        raise ValueError("target_answer_min must be <= target_answer_max")
    return int(min_value), int(max_value)


def balanced_choice_from_values(
    values: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Select one supported integer value deterministically."""

    ordered = [int(value) for value in values]
    if not ordered:
        raise ValueError(f"no feasible values for {namespace}")
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    return int(ordered[int(selection_index) % len(ordered)])


def shuffle_values(values: Sequence[int], *, instance_seed: int, namespace: str) -> List[int]:
    """Shuffle numeric values independently of labels and chart type."""

    rng = spawn_rng(int(instance_seed), str(namespace))
    ordered = [int(value) for value in values]
    rng.shuffle(ordered)
    return ordered


def sample_chart_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    """Sample one randomized non-prefix label list for the chart marks."""

    label_rng = spawn_rng(int(instance_seed), "charts.labels")
    return assign_random_shuffled_labels(label_rng, object_count=int(count))


def normalize_rgb(value: Sequence[int]) -> Tuple[int, int, int]:
    """Normalize one RGB-like sequence into a clamped color triple."""

    if len(value) < 3:
        raise ValueError("RGB value must contain three channels")
    return (
        max(0, min(255, int(value[0]))),
        max(0, min(255, int(value[1]))),
        max(0, min(255, int(value[2]))),
    )


def resolve_chart_mark_colors(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: ChartStatisticsDefaults,
    instance_seed: int,
) -> Dict[str, Any]:
    """Resolve one per-instance chart mark color shared across all marks."""

    explicit_fill = params.get("mark_fill_rgb")
    explicit_outline = params.get("mark_outline_rgb")

    if explicit_fill is not None or explicit_outline is not None:
        fill_rgb = normalize_rgb(explicit_fill if explicit_fill is not None else (86, 138, 214))
        outline_rgb = normalize_rgb(
            explicit_outline if explicit_outline is not None else darken_color(fill_rgb, factor=0.55)
        )
        return {
            "sampling_policy": "explicit_override",
            "mark_fill_rgb": [int(channel) for channel in fill_rgb],
            "mark_outline_rgb": [int(channel) for channel in outline_rgb],
        }

    color_rng = spawn_rng(int(instance_seed), "charts.mark_color")
    channel_min = int(
        params.get(
            "mark_color_channel_min",
            group_default(render_defaults, "mark_color_channel_min", defaults.mark_color_channel_min),
        )
    )
    channel_max = int(
        params.get(
            "mark_color_channel_max",
            group_default(render_defaults, "mark_color_channel_max", defaults.mark_color_channel_max),
        )
    )
    min_distance = float(
        params.get(
            "mark_color_min_distance",
            group_default(render_defaults, "mark_color_min_distance", defaults.mark_color_min_distance),
        )
    )
    distance_space = str(
        params.get(
            "mark_color_distance_space",
            group_default(render_defaults, "mark_color_distance_space", defaults.mark_color_distance_space),
        )
    ).strip().lower()
    fill_rgb = sample_color_with_distance_constraints(
        color_rng,
        channel_min=int(channel_min),
        channel_max=int(channel_max),
        anchor_colors=((255, 255, 255), (248, 248, 248)),
        min_distance=float(min_distance),
        distance_space=str(distance_space),
    )
    outline_rgb = darken_color(fill_rgb, factor=0.55)
    return {
        "sampling_policy": "random_rgb",
        "mark_fill_rgb": [int(channel) for channel in fill_rgb],
        "mark_outline_rgb": [int(channel) for channel in outline_rgb],
        "mark_color_min_distance": float(min_distance),
        "mark_color_distance_space": str(distance_space),
    }


def max_symmetric_delta(target_value: int, *, value_min: int, value_max: int) -> int:
    """Return the largest +/- delta that stays within the value bounds."""

    return int(min(int(target_value) - int(value_min), int(value_max) - int(target_value)))


def cyclic_pair_deltas(*, pair_count: int, max_delta: int) -> List[int]:
    """Return one deterministic list of positive deltas for symmetric value construction."""

    if int(pair_count) <= 0:
        return []
    if int(max_delta) <= 0:
        raise ValueError("symmetric construction requires at least one positive available delta")
    return [1 + (int(index) % int(max_delta)) for index in range(int(pair_count))]


def resolve_chart_axis_variant(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    supported_variants: Sequence[str],
    task_id: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced chart task/scene variant axis."""

    variant_rng = spawn_rng(int(instance_seed), f"{task_id}.{axis_namespace}")
    selected_variant, probabilities = resolve_variant(
        variant_rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=supported_variants,
        explicit_key=explicit_key,
        weights_key=weights_key,
    )
    variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_variant),
        variant_probabilities=probabilities,
        supported_variants=supported_variants,
        balance_flag_key=balance_flag_key,
        explicit_key=explicit_key,
        weights_key=weights_key,
        sampling_namespace=f"{task_id}:{axis_namespace}",
    )
    return str(variant), {str(key): float(value) for key, value in sorted(probabilities.items())}


def compose_with_sum(
    target_sum: int,
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    """Compose one value list of fixed length that sums to `target_sum`."""

    if int(target_sum) < int(count) * int(value_min) or int(target_sum) > int(count) * int(value_max):
        raise ValueError("target_sum outside feasible support for mark count")
    values = [int(value_min)] * int(count)
    remaining = int(target_sum) - (int(count) * int(value_min))
    rng = spawn_rng(int(instance_seed), str(namespace))
    for index in range(int(count)):
        remaining_slots = int(count) - int(index) - 1
        max_for_this = int(value_max) - int(value_min)
        max_possible_for_rest = int(remaining_slots) * max_for_this
        add_min = max(0, int(remaining) - int(max_possible_for_rest))
        add_max = min(int(max_for_this), int(remaining))
        add_value = int(remaining) if int(index) == int(count) - 1 else int(rng.randint(int(add_min), int(add_max)))
        values[int(index)] += int(add_value)
        remaining -= int(add_value)
    if int(sum(values)) != int(target_sum):
        raise RuntimeError("sum composition drifted from requested target")
    return [int(value) for value in values]


def build_values_for_max(
    target_answer: int,
    *,
    count: int,
    value_min: int,
    instance_seed: int,
) -> List[int]:
    """Construct values with one unique maximum equal to `target_answer`."""

    if int(target_answer) <= int(value_min):
        raise ValueError("max target must exceed value_min")
    rng = spawn_rng(int(instance_seed), "charts.values.max")
    values = [int(target_answer)]
    for _ in range(int(count) - 1):
        values.append(int(rng.randint(int(value_min), int(target_answer) - 1)))
    return shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.max")


def build_values_for_min(
    target_answer: int,
    *,
    count: int,
    value_max: int,
    instance_seed: int,
) -> List[int]:
    """Construct values with one unique minimum equal to `target_answer`."""

    if int(target_answer) >= int(value_max):
        raise ValueError("min target must be below value_max")
    rng = spawn_rng(int(instance_seed), "charts.values.min")
    values = [int(target_answer)]
    for _ in range(int(count) - 1):
        values.append(int(rng.randint(int(target_answer) + 1, int(value_max))))
    return shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.min")


def build_values_for_range(
    target_answer: int,
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> Tuple[List[int], int, int]:
    """Construct values with unique min/max whose difference is `target_answer`."""

    feasible_mins = [int(candidate) for candidate in range(int(value_min), int(value_max) - int(target_answer) + 1)]
    if not feasible_mins:
        raise ValueError("no feasible min values for requested range target")
    min_value = balanced_choice_from_values(
        feasible_mins,
        params={},
        instance_seed=int(instance_seed),
        namespace=f"charts.range_min:{int(target_answer)}",
    )
    max_value_resolved = int(min_value) + int(target_answer)
    interior = [int(value) for value in range(int(min_value) + 1, int(max_value_resolved))]
    if len(interior) < 1:
        raise ValueError("range target leaves no interior values for required mark count")
    rng = spawn_rng(int(instance_seed), "charts.values.range")
    values = [int(min_value), int(max_value_resolved)]
    for _ in range(int(count) - 2):
        values.append(int(interior[rng.randint(0, len(interior) - 1)]))
    shuffled = shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.range")
    return shuffled, int(min_value), int(max_value_resolved)


def build_values_for_mean(
    target_answer: int,
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> List[int]:
    """Construct values with integer mean equal to `target_answer`."""

    pair_count = int(count) // 2
    max_delta = max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max))
    deltas = cyclic_pair_deltas(pair_count=int(pair_count), max_delta=int(max_delta))
    values: List[int] = []
    for delta in deltas:
        values.append(int(target_answer) - int(delta))
        values.append(int(target_answer) + int(delta))
    if int(count) % 2 == 1:
        values.append(int(target_answer))
    if len(values) != int(count):
        raise RuntimeError("mean construction produced the wrong number of values")
    if int(sum(values)) != int(count) * int(target_answer):
        raise RuntimeError("mean construction does not preserve requested mean")
    return shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.mean")


def build_values_for_median(
    target_answer: int,
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> List[int]:
    """Construct values with unique median equal to `target_answer`."""

    if int(count) % 2 == 0:
        raise ValueError("median construction requires an odd mark count")
    pair_count = (int(count) - 1) // 2
    max_delta = max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max))
    deltas = cyclic_pair_deltas(pair_count=int(pair_count), max_delta=int(max_delta))
    values: List[int] = [int(target_answer)]
    for delta in deltas:
        values.append(int(target_answer) - int(delta))
        values.append(int(target_answer) + int(delta))
    if len(values) != int(count):
        raise RuntimeError("median construction produced the wrong number of values")
    if sorted(values)[len(values) // 2] != int(target_answer):
        raise RuntimeError("median construction does not preserve requested median")
    return shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.median")


def build_values_for_mode(
    target_answer: int,
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> List[int]:
    """Construct values with one unique modal value equal to `target_answer`."""

    modal_frequency = 2 if int(count) <= 5 else 3
    available_values = [int(value) for value in range(int(value_min), int(value_max) + 1) if int(value) != int(target_answer)]
    if int(count) - int(modal_frequency) > len(available_values):
        raise ValueError("mode construction does not have enough distinct non-modal values")
    rng = spawn_rng(int(instance_seed), "charts.values.mode")
    rng.shuffle(available_values)
    values = [int(target_answer)] * int(modal_frequency)
    values.extend(int(value) for value in available_values[: int(count) - int(modal_frequency)])
    if len(values) != int(count):
        raise RuntimeError("mode construction produced the wrong number of values")
    if min(values) < int(value_min) or max(values) > int(value_max):
        raise ValueError("mode construction falls outside supported value bounds")
    modal_frequency = sum(1 for value in values if int(value) == int(target_answer))
    if modal_frequency <= 1:
        raise RuntimeError("mode construction must repeat the modal value")
    if max(values.count(value) for value in set(values)) != int(modal_frequency):
        raise RuntimeError("mode construction must produce one unique modal value")
    return shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.mode")


def choose_mark_count(
    feasible_counts: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Choose one feasible mark count deterministically."""

    values = [int(value) for value in feasible_counts]
    if not values:
        raise ValueError(f"no feasible mark counts for {namespace}")
    explicit_count = params.get("mark_count")
    if explicit_count is not None:
        selected = int(explicit_count)
        if int(selected) not in set(values):
            raise ValueError("explicit mark_count is outside feasible support")
        return int(selected)
    return balanced_choice_from_values(values, params=params, instance_seed=int(instance_seed), namespace=str(namespace))


def build_summary_statistics_dataset_for_variant(
    *,
    statistic_kind: StatisticKind,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: ChartStatisticsDefaults,
    target_answer_ranges: Mapping[str, Tuple[int, int]],
    task_id: str,
) -> Tuple[List[int], int, List[str], Dict[str, Any]]:
    """Construct values, answer, evidence labels, and trace extras for one statistic variant."""

    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    supported_answer_min, supported_answer_max = resolve_target_answer_range(
        params,
        task_variant=str(statistic_kind),
        mark_count_min=int(mark_count_min),
        mark_count_max=int(mark_count_max),
        value_min=int(value_min),
        value_max=int(value_max),
        target_answer_ranges=target_answer_ranges,
    )
    answer_candidates = [int(value) for value in range(int(supported_answer_min), int(supported_answer_max) + 1)]
    target_answer = balanced_choice_from_values(
        answer_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:{str(statistic_kind)}",
    )

    if str(statistic_kind) in {"max", "min", "range", "sum"}:
        feasible_counts = [int(value) for value in range(int(mark_count_min), int(mark_count_max) + 1)]
    elif str(statistic_kind) == "mean":
        feasible_counts = [
            int(count)
            for count in range(int(mark_count_min), int(mark_count_max) + 1)
            if max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max)) >= 1
        ]
    elif str(statistic_kind) == "median":
        feasible_counts = [
            int(count)
            for count in range(int(mark_count_min), int(mark_count_max) + 1)
            if int(count) % 2 == 1
            and max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max)) >= 1
        ]
    else:
        feasible_counts = [
            int(count)
            for count in range(int(mark_count_min), int(mark_count_max) + 1)
            if int(count) - (2 if int(count) <= 5 else 3) <= int(value_max) - int(value_min)
        ]

    if str(statistic_kind) == "sum":
        feasible_counts = [
            int(count)
            for count in feasible_counts
            if int(target_answer) >= int(count) * int(value_min)
            and int(target_answer) <= int(count) * int(value_max)
        ]
    if str(statistic_kind) == "max":
        feasible_counts = [int(count) for count in feasible_counts if int(target_answer) > int(value_min)]
    if str(statistic_kind) == "min":
        feasible_counts = [int(count) for count in feasible_counts if int(target_answer) < int(value_max)]
    if str(statistic_kind) == "range":
        feasible_counts = [
            int(count)
            for count in feasible_counts
            if int(value_max) - int(value_min) >= int(target_answer) and int(target_answer) >= 2
        ]

    mark_count = choose_mark_count(
        feasible_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.mark_count:{str(statistic_kind)}:{int(target_answer)}",
    )
    labels = list(sample_chart_labels(count=int(mark_count), instance_seed=int(instance_seed)))

    if str(statistic_kind) == "max":
        values = build_values_for_max(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            instance_seed=int(instance_seed),
        )
    elif str(statistic_kind) == "min":
        values = build_values_for_min(
            int(target_answer),
            count=int(mark_count),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    elif str(statistic_kind) == "range":
        values, min_value, max_value = build_values_for_range(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    elif str(statistic_kind) == "mean":
        values = build_values_for_mean(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    elif str(statistic_kind) == "median":
        values = build_values_for_median(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    elif str(statistic_kind) == "sum":
        values = compose_with_sum(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
            namespace="charts.values.sum",
        )
        values = shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.sum")
    elif str(statistic_kind) == "mode":
        values = build_values_for_mode(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    else:
        raise ValueError(f"unsupported statistic_kind: {statistic_kind}")

    marks = {str(label): int(value) for label, value in zip(labels, values)}
    evidence_labels: List[str]
    trace_extras: Dict[str, Any] = {
        "value_min": int(value_min),
        "value_max": int(value_max),
        "target_answer_range": [int(supported_answer_min), int(supported_answer_max)],
        "mark_count_range": [int(mark_count_min), int(mark_count_max)],
        "target_answer": int(target_answer),
        "mark_count": int(mark_count),
        "labels": [str(label) for label in labels],
        "values_by_label": {str(label): int(marks[str(label)]) for label in labels},
    }

    if str(statistic_kind) == "max":
        winning_label = next(str(label) for label in labels if int(marks[str(label)]) == int(target_answer))
        evidence_labels = [str(winning_label)]
        trace_extras["winning_label"] = str(winning_label)
    elif str(statistic_kind) == "min":
        winning_label = next(str(label) for label in labels if int(marks[str(label)]) == int(target_answer))
        evidence_labels = [str(winning_label)]
        trace_extras["winning_label"] = str(winning_label)
    elif str(statistic_kind) == "range":
        min_label = next(str(label) for label in labels if int(marks[str(label)]) == int(min_value))
        max_label = next(str(label) for label in labels if int(marks[str(label)]) == int(max_value))
        evidence_labels = sorted_labels([str(min_label), str(max_label)])
        trace_extras["min_label"] = str(min_label)
        trace_extras["max_label"] = str(max_label)
        trace_extras["min_value"] = int(min_value)
        trace_extras["max_value"] = int(max_value)
    elif str(statistic_kind) == "mean":
        evidence_labels = sorted_labels(labels)
        trace_extras["computed_sum"] = int(sum(values))
    elif str(statistic_kind) == "median":
        sorted_pairs = sorted(((int(value), str(label)) for label, value in marks.items()), key=lambda item: (item[0], item[1]))
        median_label = str(sorted_pairs[len(sorted_pairs) // 2][1])
        evidence_labels = [str(median_label)]
        trace_extras["median_label"] = str(median_label)
        trace_extras["sorted_values"] = [int(value) for value, _ in sorted_pairs]
    elif str(statistic_kind) == "sum":
        evidence_labels = sorted_labels(labels)
        trace_extras["computed_sum"] = int(sum(values))
    else:
        evidence_labels = sorted_labels([str(label) for label, value in marks.items() if int(value) == int(target_answer)])
        trace_extras["mode_frequency"] = int(len(evidence_labels))

    if str(statistic_kind) == "mean" and int(sum(values)) != int(target_answer) * int(mark_count):
        raise RuntimeError("constructed mean values do not match requested answer")
    if str(statistic_kind) == "median":
        sorted_values = sorted(int(value) for value in values)
        if int(sorted_values[len(sorted_values) // 2]) != int(target_answer):
            raise RuntimeError("constructed median values do not match requested answer")
    if str(statistic_kind) == "mode":
        frequencies = {int(value): int(values.count(value)) for value in set(values)}
        modal_frequency = max(frequencies.values())
        winning_values = [value for value, frequency in frequencies.items() if int(frequency) == int(modal_frequency)]
        if winning_values != [int(target_answer)]:
            raise RuntimeError("constructed mode values do not match requested answer")

    return [int(value) for value in values], int(target_answer), evidence_labels, trace_extras


def resolve_chart_render_params_for_task(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: ChartStatisticsDefaults,
) -> ChartRenderParams:
    """Resolve one chart render-parameter block."""

    resolved = {
        "canvas_width": int(params.get("canvas_width", group_default(render_defaults, "canvas_width", defaults.canvas_width))),
        "canvas_height": int(params.get("canvas_height", group_default(render_defaults, "canvas_height", defaults.canvas_height))),
        "plot_margin_left_px": int(params.get("plot_margin_left_px", group_default(render_defaults, "plot_margin_left_px", defaults.plot_margin_left_px))),
        "plot_margin_right_px": int(params.get("plot_margin_right_px", group_default(render_defaults, "plot_margin_right_px", defaults.plot_margin_right_px))),
        "plot_margin_top_px": int(params.get("plot_margin_top_px", group_default(render_defaults, "plot_margin_top_px", defaults.plot_margin_top_px))),
        "plot_margin_bottom_px": int(params.get("plot_margin_bottom_px", group_default(render_defaults, "plot_margin_bottom_px", defaults.plot_margin_bottom_px))),
        "axis_line_width_px": int(params.get("axis_line_width_px", group_default(render_defaults, "axis_line_width_px", defaults.axis_line_width_px))),
        "grid_line_width_px": int(params.get("grid_line_width_px", group_default(render_defaults, "grid_line_width_px", defaults.grid_line_width_px))),
        "tick_length_px": int(params.get("tick_length_px", group_default(render_defaults, "tick_length_px", defaults.tick_length_px))),
        "label_font_size_px": int(params.get("label_font_size_px", group_default(render_defaults, "label_font_size_px", defaults.label_font_size_px))),
        "tick_font_size_px": int(params.get("tick_font_size_px", group_default(render_defaults, "tick_font_size_px", defaults.tick_font_size_px))),
        "label_stroke_width_px": int(params.get("label_stroke_width_px", group_default(render_defaults, "label_stroke_width_px", defaults.label_stroke_width_px))),
        "mark_outline_width_px": int(params.get("mark_outline_width_px", group_default(render_defaults, "mark_outline_width_px", defaults.mark_outline_width_px))),
        "line_width_px": int(params.get("line_width_px", group_default(render_defaults, "line_width_px", defaults.line_width_px))),
        "point_radius_px": int(params.get("point_radius_px", group_default(render_defaults, "point_radius_px", defaults.point_radius_px))),
        "bar_width_fraction": float(params.get("bar_width_fraction", group_default(render_defaults, "bar_width_fraction", defaults.bar_width_fraction))),
        "axis_color_rgb": params.get("axis_color_rgb", group_default(render_defaults, "axis_color_rgb", [74, 78, 86])),
        "grid_color_rgb": params.get("grid_color_rgb", group_default(render_defaults, "grid_color_rgb", [224, 227, 232])),
        "mark_fill_rgb": params.get("mark_fill_rgb", group_default(render_defaults, "mark_fill_rgb", [86, 138, 214])),
        "mark_outline_rgb": params.get("mark_outline_rgb", group_default(render_defaults, "mark_outline_rgb", [50, 76, 116])),
        "text_color_rgb": params.get("text_color_rgb", group_default(render_defaults, "text_color_rgb", [38, 41, 48])),
        "text_stroke_rgb": params.get("text_stroke_rgb", group_default(render_defaults, "text_stroke_rgb", [255, 255, 255])),
        "plot_fill_rgb": params.get("plot_fill_rgb", group_default(render_defaults, "plot_fill_rgb", [255, 255, 255])),
    }
    return resolve_chart_render_params(resolved)


__all__ = [
    "ChartStatisticsDefaults",
    "SUPPORTED_STATISTICS_SCENE_VARIANTS",
    "StatisticKind",
    "SceneVariant",
    "balanced_choice_from_values",
    "build_summary_statistics_dataset_for_variant",
    "resolve_chart_axis_variant",
    "resolve_chart_mark_colors",
    "resolve_chart_render_params_for_task",
    "resolve_mark_count_bounds",
    "resolve_value_bounds",
    "sorted_labels",
]
