"""Chart statistics task over labeled bar, line, and scatter scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, resolve_required_int_bounds, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.color_distance import sample_color_with_distance_constraints
from ...shared.labeling import assign_random_shuffled_labels
from ...shared.named_colors import darken_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.chart_scene import (
    ChartMarkSpec,
    ChartRenderParams,
    SUPPORTED_CHART_SCENE_VARIANTS,
    render_labeled_chart_scene,
    resolve_chart_render_params,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


StatisticKind = str
SceneVariant = str

_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "max",
    "min",
    "range",
    "mean",
    "median",
    "sum",
    "mode",
)
_SUMMARIZED_SCENE_VARIANTS: Tuple[str, ...] = tuple(SUPPORTED_CHART_SCENE_VARIANTS)

_TARGET_ANSWER_RANGES: Dict[str, Tuple[int, int]] = {
    "max": (4, 12),
    "min": (1, 8),
    "range": (2, 8),
    "mean": (4, 9),
    "median": (3, 10),
    "mode": (3, 10),
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for chart summary-value tasks."""

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


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "statistics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_charts_statistics_summary_value",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="statistics")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="statistics", apply_prob=0.0)


def _sorted_labels(labels: Sequence[str]) -> List[str]:
    """Return labels in deterministic alphabetical order."""

    return [str(label) for label in sorted([str(label) for label in labels])]


def _value_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve inclusive individual-value bounds."""

    return resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=int(_DEFAULTS.value_min),
        fallback_max=int(_DEFAULTS.value_max),
        context="generation defaults for task_charts_statistics_summary_value",
    )


def _mark_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve inclusive chart mark-count bounds."""

    return resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="mark_count_min",
        max_key="mark_count_max",
        fallback_min=int(_DEFAULTS.mark_count_min),
        fallback_max=int(_DEFAULTS.mark_count_max),
        context="generation defaults for task_charts_statistics_summary_value",
    )


def _target_answer_range(
    params: Mapping[str, Any],
    *,
    task_variant: StatisticKind,
    mark_count_min: int,
    mark_count_max: int,
    value_min: int,
    value_max: int,
) -> Tuple[int, int]:
    """Resolve the supported target-answer range for one statistic variant."""

    if str(task_variant) == "sum":
        default_min = int(mark_count_min) * int(value_min)
        default_max = int(mark_count_max) * int(value_max)
    else:
        default_min, default_max = _TARGET_ANSWER_RANGES[str(task_variant)]
    explicit_min = params.get("target_answer_min", None)
    explicit_max = params.get("target_answer_max", None)
    if explicit_min is None and explicit_max is None:
        return int(default_min), int(default_max)
    min_value = int(default_min if explicit_min is None else explicit_min)
    max_value = int(default_max if explicit_max is None else explicit_max)
    if int(min_value) > int(max_value):
        raise ValueError("target_answer_min must be <= target_answer_max")
    return int(min_value), int(max_value)


def _balanced_choice_from_values(
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


def _shuffle_values(values: Sequence[int], *, instance_seed: int, namespace: str) -> List[int]:
    """Shuffle numeric values independently of labels and chart type."""

    rng = spawn_rng(int(instance_seed), str(namespace))
    ordered = [int(value) for value in values]
    rng.shuffle(ordered)
    return ordered


def _sample_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    """Sample one randomized non-prefix label list for the chart marks."""

    label_rng = spawn_rng(int(instance_seed), "charts.labels")
    return assign_random_shuffled_labels(
        label_rng,
        object_count=int(count),
    )


def _normalize_rgb(value: Sequence[int]) -> Tuple[int, int, int]:
    """Normalize one RGB-like sequence into a clamped color triple."""

    if len(value) < 3:
        raise ValueError("RGB value must contain three channels")
    return (
        max(0, min(255, int(value[0]))),
        max(0, min(255, int(value[1]))),
        max(0, min(255, int(value[2]))),
    )


def _resolve_mark_colors(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    """Resolve one per-instance chart mark color shared across all marks."""

    explicit_fill = params.get("mark_fill_rgb")
    explicit_outline = params.get("mark_outline_rgb")

    if explicit_fill is not None or explicit_outline is not None:
        fill_rgb = _normalize_rgb(explicit_fill if explicit_fill is not None else (86, 138, 214))
        outline_rgb = _normalize_rgb(
            explicit_outline if explicit_outline is not None else darken_color(fill_rgb, factor=0.55)
        )
        return {
            "sampling_policy": "explicit_override",
            "mark_fill_rgb": [int(channel) for channel in fill_rgb],
            "mark_outline_rgb": [int(channel) for channel in outline_rgb],
        }

    color_rng = spawn_rng(int(instance_seed), "charts.mark_color")
    channel_min = int(params.get("mark_color_channel_min", group_default(_RENDER_DEFAULTS, "mark_color_channel_min", _DEFAULTS.mark_color_channel_min)))
    channel_max = int(params.get("mark_color_channel_max", group_default(_RENDER_DEFAULTS, "mark_color_channel_max", _DEFAULTS.mark_color_channel_max)))
    min_distance = float(params.get("mark_color_min_distance", group_default(_RENDER_DEFAULTS, "mark_color_min_distance", _DEFAULTS.mark_color_min_distance)))
    distance_space = str(
        params.get(
            "mark_color_distance_space",
            group_default(_RENDER_DEFAULTS, "mark_color_distance_space", _DEFAULTS.mark_color_distance_space),
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


def _max_symmetric_delta(target_value: int, *, value_min: int, value_max: int) -> int:
    """Return the largest +/- delta that stays within the value bounds."""

    return int(min(int(target_value) - int(value_min), int(value_max) - int(target_value)))


def _cyclic_pair_deltas(*, pair_count: int, max_delta: int) -> List[int]:
    """Return one deterministic list of positive deltas for symmetric value construction."""

    if int(pair_count) <= 0:
        return []
    if int(max_delta) <= 0:
        raise ValueError("symmetric construction requires at least one positive available delta")
    return [1 + (int(index) % int(max_delta)) for index in range(int(pair_count))]


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic statistic variant for the task."""

    variant_rng = spawn_rng(int(instance_seed), "charts.task_variant")
    selected_variant, probabilities = resolve_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUPPORTED_TASK_VARIANTS,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
    )
    variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_variant),
        variant_probabilities=probabilities,
        supported_variants=_SUPPORTED_TASK_VARIANTS,
        balance_flag_key="balanced_task_variant_sampling",
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        sampling_namespace="task_charts_statistics_summary_value:task_variant",
    )
    return str(variant), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the chart-type scene variant for one instance."""

    variant_rng = spawn_rng(int(instance_seed), "charts.scene_variant")
    selected_variant, probabilities = resolve_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUMMARIZED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_variant),
        variant_probabilities=probabilities,
        supported_variants=_SUMMARIZED_SCENE_VARIANTS,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace="task_charts_statistics_summary_value:scene_variant",
    )
    return str(variant), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _compose_with_sum(
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
        min_required_for_rest = 0
        max_possible_for_rest = int(remaining_slots) * max_for_this
        add_min = max(0, int(remaining) - int(max_possible_for_rest))
        add_max = min(int(max_for_this), int(remaining) - int(min_required_for_rest))
        if int(index) == int(count) - 1:
            add_value = int(remaining)
        else:
            add_value = int(rng.randint(int(add_min), int(add_max)))
        values[int(index)] += int(add_value)
        remaining -= int(add_value)
    if int(sum(values)) != int(target_sum):
        raise RuntimeError("sum composition drifted from requested target")
    return [int(value) for value in values]


def _build_values_for_max(
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
    return _shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.max")


def _build_values_for_min(
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
    return _shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.min")


def _build_values_for_range(
    target_answer: int,
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> Tuple[List[int], int, int]:
    """Construct values with unique min/max whose difference is `target_answer`."""

    feasible_mins = [
        int(candidate)
        for candidate in range(int(value_min), int(value_max) - int(target_answer) + 1)
    ]
    if not feasible_mins:
        raise ValueError("no feasible min values for requested range target")
    min_value = _balanced_choice_from_values(
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
    shuffled = _shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.range")
    return shuffled, int(min_value), int(max_value_resolved)


def _build_values_for_mean(
    target_answer: int,
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> List[int]:
    """Construct values with integer mean equal to `target_answer`."""

    pair_count = int(count) // 2
    max_delta = _max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max))
    deltas = _cyclic_pair_deltas(pair_count=int(pair_count), max_delta=int(max_delta))
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
    return _shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.mean")


def _build_values_for_median(
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
    max_delta = _max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max))
    deltas = _cyclic_pair_deltas(pair_count=int(pair_count), max_delta=int(max_delta))
    values: List[int] = [int(target_answer)]
    for delta in deltas:
        values.append(int(target_answer) - int(delta))
        values.append(int(target_answer) + int(delta))
    if len(values) != int(count):
        raise RuntimeError("median construction produced the wrong number of values")
    if sorted(values)[len(values) // 2] != int(target_answer):
        raise RuntimeError("median construction does not preserve requested median")
    return _shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.median")


def _build_values_for_mode(
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
    return _shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.mode")


def _choose_mark_count(
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
    return _balanced_choice_from_values(
        values,
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def _build_dataset_for_variant(
    *,
    task_variant: StatisticKind,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[List[int], int, List[str], Dict[str, Any]]:
    """Construct values, answer, evidence labels, and trace extras for one statistic variant."""

    value_min, value_max = _value_bounds(params)
    mark_count_min, mark_count_max = _mark_count_bounds(params)
    supported_answer_min, supported_answer_max = _target_answer_range(
        params,
        task_variant=str(task_variant),
        mark_count_min=int(mark_count_min),
        mark_count_max=int(mark_count_max),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    answer_candidates = [int(value) for value in range(int(supported_answer_min), int(supported_answer_max) + 1)]
    target_answer = _balanced_choice_from_values(
        answer_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"charts.target_answer:{str(task_variant)}",
    )

    if str(task_variant) in {"max", "min", "range", "sum"}:
        feasible_counts = [int(value) for value in range(int(mark_count_min), int(mark_count_max) + 1)]
    elif str(task_variant) == "mean":
        feasible_counts = [
            int(count)
            for count in range(int(mark_count_min), int(mark_count_max) + 1)
            if _max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max)) >= 1
        ]
    elif str(task_variant) == "median":
        feasible_counts = [
            int(count)
            for count in range(int(mark_count_min), int(mark_count_max) + 1)
            if int(count) % 2 == 1
            and _max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max)) >= 1
        ]
    else:
        feasible_counts = [
            int(count)
            for count in range(int(mark_count_min), int(mark_count_max) + 1)
            if int(count) - (2 if int(count) <= 5 else 3) <= int(value_max) - int(value_min)
        ]

    if str(task_variant) == "sum":
        feasible_counts = [
            int(count)
            for count in feasible_counts
            if int(target_answer) >= int(count) * int(value_min)
            and int(target_answer) <= int(count) * int(value_max)
        ]
    if str(task_variant) == "max":
        feasible_counts = [int(count) for count in feasible_counts if int(target_answer) > int(value_min)]
    if str(task_variant) == "min":
        feasible_counts = [int(count) for count in feasible_counts if int(target_answer) < int(value_max)]
    if str(task_variant) == "range":
        feasible_counts = [
            int(count)
            for count in feasible_counts
            if int(value_max) - int(value_min) >= int(target_answer) and int(target_answer) >= 2
        ]
    mark_count = _choose_mark_count(
        feasible_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"charts.mark_count:{str(task_variant)}:{int(target_answer)}",
    )

    labels = list(_sample_labels(count=int(mark_count), instance_seed=int(instance_seed)))

    if str(task_variant) == "max":
        values = _build_values_for_max(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            instance_seed=int(instance_seed),
        )
    elif str(task_variant) == "min":
        values = _build_values_for_min(
            int(target_answer),
            count=int(mark_count),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    elif str(task_variant) == "range":
        values, min_value, max_value = _build_values_for_range(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    elif str(task_variant) == "mean":
        values = _build_values_for_mean(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    elif str(task_variant) == "median":
        values = _build_values_for_median(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    elif str(task_variant) == "sum":
        values = _compose_with_sum(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
            namespace="charts.values.sum",
        )
        values = _shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.sum")
    elif str(task_variant) == "mode":
        values = _build_values_for_mode(
            int(target_answer),
            count=int(mark_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
    else:
        raise ValueError(f"unsupported task_variant: {task_variant}")

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

    if str(task_variant) == "max":
        winning_label = next(str(label) for label in labels if int(marks[str(label)]) == int(target_answer))
        evidence_labels = [str(winning_label)]
        trace_extras["winning_label"] = str(winning_label)
    elif str(task_variant) == "min":
        winning_label = next(str(label) for label in labels if int(marks[str(label)]) == int(target_answer))
        evidence_labels = [str(winning_label)]
        trace_extras["winning_label"] = str(winning_label)
    elif str(task_variant) == "range":
        min_label = next(str(label) for label in labels if int(marks[str(label)]) == int(min_value))
        max_label = next(str(label) for label in labels if int(marks[str(label)]) == int(max_value))
        evidence_labels = _sorted_labels([str(min_label), str(max_label)])
        trace_extras["min_label"] = str(min_label)
        trace_extras["max_label"] = str(max_label)
        trace_extras["min_value"] = int(min_value)
        trace_extras["max_value"] = int(max_value)
    elif str(task_variant) == "mean":
        evidence_labels = _sorted_labels(labels)
        trace_extras["computed_sum"] = int(sum(values))
    elif str(task_variant) == "median":
        sorted_pairs = sorted(((int(value), str(label)) for label, value in marks.items()), key=lambda item: (item[0], item[1]))
        median_label = str(sorted_pairs[len(sorted_pairs) // 2][1])
        evidence_labels = [str(median_label)]
        trace_extras["median_label"] = str(median_label)
        trace_extras["sorted_values"] = [int(value) for value, _ in sorted_pairs]
    elif str(task_variant) == "sum":
        evidence_labels = _sorted_labels(labels)
        trace_extras["computed_sum"] = int(sum(values))
    else:
        evidence_labels = _sorted_labels(
            [str(label) for label, value in marks.items() if int(value) == int(target_answer)]
        )
        trace_extras["mode_frequency"] = int(len(evidence_labels))

    if str(task_variant) == "mean" and int(sum(values)) != int(target_answer) * int(mark_count):
        raise RuntimeError("constructed mean values do not match requested answer")
    if str(task_variant) == "median":
        sorted_values = sorted(int(value) for value in values)
        if int(sorted_values[len(sorted_values) // 2]) != int(target_answer):
            raise RuntimeError("constructed median values do not match requested answer")
    if str(task_variant) == "mode":
        frequencies = {int(value): int(values.count(value)) for value in set(values)}
        modal_frequency = max(frequencies.values())
        winning_values = [value for value, frequency in frequencies.items() if int(frequency) == int(modal_frequency)]
        if winning_values != [int(target_answer)]:
            raise RuntimeError("constructed mode values do not match requested answer")

    return [int(value) for value in values], int(target_answer), evidence_labels, trace_extras


def _render_params(params: Mapping[str, Any]) -> ChartRenderParams:
    """Resolve one chart render-parameter block."""

    resolved = {
        "canvas_width": int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        "canvas_height": int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        "plot_margin_left_px": int(
            params.get("plot_margin_left_px", group_default(_RENDER_DEFAULTS, "plot_margin_left_px", _DEFAULTS.plot_margin_left_px))
        ),
        "plot_margin_right_px": int(
            params.get("plot_margin_right_px", group_default(_RENDER_DEFAULTS, "plot_margin_right_px", _DEFAULTS.plot_margin_right_px))
        ),
        "plot_margin_top_px": int(
            params.get("plot_margin_top_px", group_default(_RENDER_DEFAULTS, "plot_margin_top_px", _DEFAULTS.plot_margin_top_px))
        ),
        "plot_margin_bottom_px": int(
            params.get("plot_margin_bottom_px", group_default(_RENDER_DEFAULTS, "plot_margin_bottom_px", _DEFAULTS.plot_margin_bottom_px))
        ),
        "axis_line_width_px": int(
            params.get("axis_line_width_px", group_default(_RENDER_DEFAULTS, "axis_line_width_px", _DEFAULTS.axis_line_width_px))
        ),
        "grid_line_width_px": int(
            params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", _DEFAULTS.grid_line_width_px))
        ),
        "tick_length_px": int(params.get("tick_length_px", group_default(_RENDER_DEFAULTS, "tick_length_px", _DEFAULTS.tick_length_px))),
        "label_font_size_px": int(
            params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))
        ),
        "tick_font_size_px": int(
            params.get("tick_font_size_px", group_default(_RENDER_DEFAULTS, "tick_font_size_px", _DEFAULTS.tick_font_size_px))
        ),
        "label_stroke_width_px": int(
            params.get(
                "label_stroke_width_px",
                group_default(_RENDER_DEFAULTS, "label_stroke_width_px", _DEFAULTS.label_stroke_width_px),
            )
        ),
        "mark_outline_width_px": int(
            params.get(
                "mark_outline_width_px",
                group_default(_RENDER_DEFAULTS, "mark_outline_width_px", _DEFAULTS.mark_outline_width_px),
            )
        ),
        "line_width_px": int(params.get("line_width_px", group_default(_RENDER_DEFAULTS, "line_width_px", _DEFAULTS.line_width_px))),
        "point_radius_px": int(
            params.get("point_radius_px", group_default(_RENDER_DEFAULTS, "point_radius_px", _DEFAULTS.point_radius_px))
        ),
        "bar_width_fraction": float(
            params.get("bar_width_fraction", group_default(_RENDER_DEFAULTS, "bar_width_fraction", _DEFAULTS.bar_width_fraction))
        ),
        "axis_color_rgb": params.get("axis_color_rgb", group_default(_RENDER_DEFAULTS, "axis_color_rgb", [74, 78, 86])),
        "grid_color_rgb": params.get("grid_color_rgb", group_default(_RENDER_DEFAULTS, "grid_color_rgb", [224, 227, 232])),
        "mark_fill_rgb": params.get("mark_fill_rgb", group_default(_RENDER_DEFAULTS, "mark_fill_rgb", [86, 138, 214])),
        "mark_outline_rgb": params.get("mark_outline_rgb", group_default(_RENDER_DEFAULTS, "mark_outline_rgb", [50, 76, 116])),
        "text_color_rgb": params.get("text_color_rgb", group_default(_RENDER_DEFAULTS, "text_color_rgb", [38, 41, 48])),
        "text_stroke_rgb": params.get("text_stroke_rgb", group_default(_RENDER_DEFAULTS, "text_stroke_rgb", [255, 255, 255])),
        "plot_fill_rgb": params.get("plot_fill_rgb", group_default(_RENDER_DEFAULTS, "plot_fill_rgb", [255, 255, 255])),
    }
    return resolve_chart_render_params(resolved)


@register_task
class ChartsStatisticsSummaryValueTask:
    """Return one summary statistic from a labeled chart."""

    task_id = "task_charts_statistics_summary_value"
    domain = "charts"
    task_group = "statistics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        values, answer_value, evidence_labels, trace_extras = _build_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
        )

        labels = [str(label) for label in trace_extras["labels"]]
        marks = [ChartMarkSpec(label=str(label), value=int(value)) for label, value in zip(labels, values)]
        mark_style = _resolve_mark_colors(params, instance_seed=int(instance_seed))
        render_params = _render_params({**dict(params), **mark_style})

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_labeled_chart_scene(
            background,
            scene_variant=str(scene_variant),
            marks=marks,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_bar",
                "object_description_line",
                "object_description_scatter",
                "evidence_hint_max",
                "evidence_hint_min",
                "evidence_hint_range",
                "evidence_hint_mean",
                "evidence_hint_median",
                "evidence_hint_sum",
                "evidence_hint_mode",
                "json_example_max",
                "json_example_min",
                "json_example_range",
                "json_example_mean",
                "json_example_median",
                "json_example_sum",
                "json_example_mode",
                "json_example_answer_only_max",
                "json_example_answer_only_min",
                "json_example_answer_only_range",
                "json_example_answer_only_mean",
                "json_example_answer_only_median",
                "json_example_answer_only_sum",
                "json_example_answer_only_mode",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(task_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(task_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(task_variant)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="label_set", value=list(evidence_labels))
        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        values_by_label = {
            str(mark["label"]): int(mark["value"])
            for mark in rendered_scene.mark_traces
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_statistics",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "evidence_labels": list(evidence_labels),
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "mark_count": int(trace_extras["mark_count"]),
                    "target_answer": int(trace_extras["target_answer"]),
                    "target_answer_range": list(trace_extras["target_answer_range"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "tick_font_size_px": int(render_params.tick_font_size_px),
                    "label_stroke_width_px": int(render_params.label_stroke_width_px),
                },
                "axis_style": {
                    "axis_line_width_px": int(render_params.axis_line_width_px),
                    "grid_line_width_px": int(render_params.grid_line_width_px),
                    "tick_length_px": int(render_params.tick_length_px),
                },
                "mark_style": {
                    "sampling_policy": str(mark_style["sampling_policy"]),
                    "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                    **{
                        str(key): value
                        for key, value in mark_style.items()
                        if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                    },
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "label_centers_px": dict(label_centers),
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "evidence_labels": list(evidence_labels),
                "labels": [str(label) for label in labels],
                "values": [int(value) for value in values],
                "values_by_label": dict(values_by_label),
                "mark_count": int(trace_extras["mark_count"]),
                "mark_count_range": list(trace_extras["mark_count_range"]),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "numeric_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                },
                **{str(key): value for key, value in trace_extras.items() if key not in {"labels", "values_by_label", "mark_count", "mark_count_range", "target_answer", "target_answer_range"}},
            },
            "witness_symbolic": {
                "type": "label_set",
                "labels": list(evidence_labels),
            },
            "projected_evidence": {
                "label_set": list(evidence_labels),
            },
        }

        complexity = TaskComplexity(
            complexity_score=float(0.18 + 0.05 * int(trace_extras["mark_count"]) + 0.03 * len(evidence_labels)),
            complexity_components={
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "mark_count": int(trace_extras["mark_count"]),
                "evidence_size": int(len(evidence_labels)),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["ChartsStatisticsSummaryValueTask"]
