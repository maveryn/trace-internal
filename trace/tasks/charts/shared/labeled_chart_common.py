"""Shared generation/render helpers for labeled chart task families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.color_distance import (
    sample_color_palette_with_distance_constraints,
    sample_color_with_distance_constraints,
)
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.labeling import assign_random_shuffled_labels
from ...shared.named_colors import darken_color
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .chart_scene import (
    ChartMarkSpec,
    ChartRenderParams,
    RenderedChartScene,
    SUPPORTED_CHART_SCENE_VARIANTS,
    resolve_chart_render_params,
)


StatisticKind = str
SceneVariant = str
SUPPORTED_LABELED_CHART_SCENE_VARIANTS: Tuple[str, ...] = tuple(SUPPORTED_CHART_SCENE_VARIANTS)
PIE_LIKE_SCENE_VARIANTS = frozenset({"pie", "donut"})


@dataclass(frozen=True)
class LabeledChartDefaults:
    """Stable fallback defaults shared by labeled chart tasks."""

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


def is_pie_like_scene_variant(scene_variant: str) -> bool:
    """Return whether the chart variant uses composition-style pie slices."""

    return str(scene_variant) in PIE_LIKE_SCENE_VARIANTS


def sorted_labels(labels: Sequence[str]) -> List[str]:
    """Return labels in deterministic alphabetical order."""

    return [str(label) for label in sorted(str(label) for label in labels)]


def projected_mark_evidence(
    rendered_scene: RenderedChartScene,
    labels: Sequence[str],
) -> Dict[str, Any]:
    """Project one ordered label list into reusable pixel-space chart evidence.

    Review overlays need pixel-space geometry even when the primary prompt-facing
    evidence stays symbolic (for example `label_set` or `integer_list`). This helper
    returns compact per-mark projections for the selected labels in the same order
    they were requested.
    """

    requested = [str(label) for label in labels]
    by_label = {
        str(mark_trace["label"]): mark_trace
        for mark_trace in rendered_scene.mark_traces
    }
    pixel_point_map: Dict[str, List[float]] = {}
    pixel_point_set: List[List[float]] = []
    bbox_set: List[List[float]] = []
    for label in requested:
        mark_trace = by_label.get(str(label))
        if mark_trace is None:
            continue
        center = [float(value) for value in mark_trace["mark_center_px"]]
        bbox = [float(value) for value in mark_trace["mark_bbox_px"]]
        pixel_point_map[str(label)] = list(center)
        pixel_point_set.append(list(center))
        bbox_set.append(list(bbox))
    return {
        "pixel_point_map": pixel_point_map,
        "pixel_point_set": pixel_point_set,
        "bbox_set": bbox_set,
    }


def resolve_value_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
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
    defaults: LabeledChartDefaults,
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


def apply_scene_variant_mark_count_cap(
    *,
    scene_variant: str,
    mark_count_min: int,
    mark_count_max: int,
) -> Tuple[int, int]:
    """Apply scene-specific mark-count caps for chart readability."""

    resolved_min = int(mark_count_min)
    resolved_max = int(mark_count_max)
    if str(scene_variant) in {"pie", "donut"}:
        resolved_max = min(int(resolved_max), 8)
    if int(resolved_min) > int(resolved_max):
        raise ValueError(f"no feasible mark-count support for scene_variant={scene_variant}")
    return int(resolved_min), int(resolved_max)


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


def build_chart_mark_specs(
    *,
    labels: Sequence[str],
    values: Sequence[int],
    scene_variant: str,
    mark_style: Mapping[str, Any],
) -> List[ChartMarkSpec]:
    """Build chart-mark specs with per-mark colors resolved for the scene variant."""

    resolved_labels = [str(label) for label in labels]
    resolved_values = [int(value) for value in values]
    if len(resolved_labels) != len(resolved_values):
        raise ValueError("labels and values must have the same length")

    if is_pie_like_scene_variant(str(scene_variant)):
        fill_palette = [normalize_rgb(value) for value in mark_style.get("slice_fill_palette_rgb", [])]
        outline_palette = [normalize_rgb(value) for value in mark_style.get("slice_outline_palette_rgb", [])]
        if len(fill_palette) != len(resolved_labels) or len(outline_palette) != len(resolved_labels):
            raise ValueError("pie-style chart marks require one fill/outline color per slice")
        return [
            ChartMarkSpec(
                label=str(label),
                value=int(value),
                fill_rgb=tuple(int(channel) for channel in fill_palette[index]),
                outline_rgb=tuple(int(channel) for channel in outline_palette[index]),
            )
            for index, (label, value) in enumerate(zip(resolved_labels, resolved_values))
        ]

    fill_rgb = normalize_rgb(mark_style.get("mark_fill_rgb", (86, 138, 214)))
    outline_rgb = normalize_rgb(mark_style.get("mark_outline_rgb", darken_color(fill_rgb, factor=0.55)))
    return [
        ChartMarkSpec(
            label=str(label),
            value=int(value),
            fill_rgb=tuple(int(channel) for channel in fill_rgb),
            outline_rgb=tuple(int(channel) for channel in outline_rgb),
        )
        for label, value in zip(resolved_labels, resolved_values)
    ]


def resolve_chart_mark_colors(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
    instance_seed: int,
    scene_variant: str,
    mark_count: int,
) -> Dict[str, Any]:
    """Resolve one per-instance chart mark color style block."""

    explicit_fill = params.get("mark_fill_rgb")
    explicit_outline = params.get("mark_outline_rgb")

    if not is_pie_like_scene_variant(str(scene_variant)) and (explicit_fill is not None or explicit_outline is not None):
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
    if is_pie_like_scene_variant(str(scene_variant)):
        fill_palette = sample_color_palette_with_distance_constraints(
            color_rng,
            palette_size=int(mark_count),
            channel_min=int(channel_min),
            channel_max=int(channel_max),
            anchor_colors=((255, 255, 255), (248, 248, 248)),
            min_distance=float(min_distance),
            distance_space=str(distance_space),
        )
        outline_palette = [darken_color(fill_rgb, factor=0.55) for fill_rgb in fill_palette]
        return {
            "sampling_policy": "random_rgb_palette",
            "mark_fill_rgb": [int(channel) for channel in fill_palette[0]],
            "mark_outline_rgb": [int(channel) for channel in outline_palette[0]],
            "slice_fill_palette_rgb": [[int(channel) for channel in fill_rgb] for fill_rgb in fill_palette],
            "slice_outline_palette_rgb": [[int(channel) for channel in outline_rgb] for outline_rgb in outline_palette],
            "mark_color_min_distance": float(min_distance),
            "mark_color_distance_space": str(distance_space),
        }
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


def sample_composition_with_sum(
    rng,
    *,
    target_sum: int,
    count: int,
    value_min: int,
    value_max: int,
) -> List[int]:
    """Sample one bounded integer composition with sum preserved exactly."""

    if int(count) <= 0:
        raise ValueError("composition count must be positive")
    if int(target_sum) < int(count) * int(value_min) or int(target_sum) > int(count) * int(value_max):
        raise ValueError("target_sum outside feasible support for bounded composition")

    values = [int(value_min)] * int(count)
    remaining = int(target_sum) - (int(count) * int(value_min))
    max_increment = int(value_max) - int(value_min)
    for index in range(int(count)):
        remaining_slots = int(count) - int(index) - 1
        max_possible_for_rest = int(remaining_slots) * int(max_increment)
        add_min = max(0, int(remaining) - int(max_possible_for_rest))
        add_max = min(int(max_increment), int(remaining))
        add_value = int(remaining) if int(index) == int(count) - 1 else int(rng.randint(int(add_min), int(add_max)))
        values[int(index)] += int(add_value)
        remaining -= int(add_value)
    if int(sum(values)) != int(target_sum):
        raise RuntimeError("bounded composition drifted from requested sum")
    return [int(value) for value in values]


def sample_percentage_composition(
    *,
    count: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    """Sample one positive-integer percentage composition that sums to 100."""

    composition_rng = spawn_rng(int(instance_seed), str(namespace))
    values = sample_composition_with_sum(
        composition_rng,
        target_sum=100,
        count=int(count),
        value_min=1,
        value_max=100,
    )
    composition_rng.shuffle(values)
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


def _sample_int_values(
    rng,
    *,
    count: int,
    min_value: int,
    max_value: int,
) -> List[int]:
    """Sample integer values uniformly from one inclusive range."""

    if int(count) < 0:
        raise ValueError("count must be non-negative")
    if int(min_value) > int(max_value):
        raise ValueError("min_value must be <= max_value")
    return [int(rng.randint(int(min_value), int(max_value))) for _ in range(int(count))]


def _sample_values_from_pool(
    rng,
    *,
    count: int,
    pool: Sequence[int],
) -> List[int]:
    """Sample integer values uniformly with replacement from one explicit pool."""

    values = [int(value) for value in pool]
    if not values:
        raise ValueError("pool must not be empty")
    return [int(values[rng.randint(0, len(values) - 1)]) for _ in range(int(count))]


def summarize_statistic_from_values(
    *,
    statistic_kind: StatisticKind,
    labels: Sequence[str],
    values: Sequence[int],
) -> Tuple[int, List[str], Dict[str, Any]]:
    """Resolve the statistic answer and supporting labels from one labeled value list."""

    resolved_labels = [str(label) for label in labels]
    resolved_values = [int(value) for value in values]
    if len(resolved_labels) != len(resolved_values):
        raise ValueError("labels and values must have the same length")

    marks = {str(label): int(value) for label, value in zip(resolved_labels, resolved_values)}
    if str(statistic_kind) == "max":
        target_answer = int(max(resolved_values))
        winners = [str(label) for label, value in marks.items() if int(value) == int(target_answer)]
        if len(winners) != 1:
            raise ValueError("max requires one unique winning label")
        return int(target_answer), [str(winners[0])], {"winning_label": str(winners[0])}
    if str(statistic_kind) == "min":
        target_answer = int(min(resolved_values))
        winners = [str(label) for label, value in marks.items() if int(value) == int(target_answer)]
        if len(winners) != 1:
            raise ValueError("min requires one unique winning label")
        return int(target_answer), [str(winners[0])], {"winning_label": str(winners[0])}
    if str(statistic_kind) == "range":
        min_value = int(min(resolved_values))
        max_value = int(max(resolved_values))
        min_labels = [str(label) for label, value in marks.items() if int(value) == int(min_value)]
        max_labels = [str(label) for label, value in marks.items() if int(value) == int(max_value)]
        if len(min_labels) != 1 or len(max_labels) != 1:
            raise ValueError("range requires one unique min label and one unique max label")
        return (
            int(max_value - min_value),
            sorted_labels([str(min_labels[0]), str(max_labels[0])]),
            {
                "min_label": str(min_labels[0]),
                "max_label": str(max_labels[0]),
                "min_value": int(min_value),
                "max_value": int(max_value),
            },
        )
    if str(statistic_kind) == "mean":
        total = int(sum(resolved_values))
        count = int(len(resolved_values))
        if count <= 0 or int(total) % int(count) != 0:
            raise ValueError("mean requires an integral average")
        return int(total // count), sorted_labels(resolved_labels), {"computed_sum": int(total)}
    if str(statistic_kind) == "median":
        if int(len(resolved_values)) % 2 == 0:
            raise ValueError("median requires an odd number of values")
        sorted_pairs = sorted(((int(value), str(label)) for label, value in marks.items()), key=lambda item: (item[0], item[1]))
        median_index = len(sorted_pairs) // 2
        median_value = int(sorted_pairs[median_index][0])
        median_labels = [str(label) for label, value in marks.items() if int(value) == int(median_value)]
        if len(median_labels) != 1:
            raise ValueError("median requires one unique median label")
        return (
            int(median_value),
            [str(median_labels[0])],
            {
                "median_label": str(median_labels[0]),
                "sorted_values": [int(value) for value, _ in sorted_pairs],
            },
        )
    if str(statistic_kind) == "sum":
        total = int(sum(resolved_values))
        return int(total), sorted_labels(resolved_labels), {"computed_sum": int(total)}
    if str(statistic_kind) == "mode":
        frequencies = {int(value): int(resolved_values.count(value)) for value in set(resolved_values)}
        modal_frequency = max(frequencies.values())
        winning_values = [int(value) for value, frequency in frequencies.items() if int(frequency) == int(modal_frequency)]
        if len(winning_values) != 1 or int(modal_frequency) <= 1:
            raise ValueError("mode requires one unique repeated modal value")
        modal_value = int(winning_values[0])
        evidence_labels = sorted_labels([str(label) for label, value in marks.items() if int(value) == int(modal_value)])
        return int(modal_value), evidence_labels, {"mode_frequency": int(modal_frequency)}
    raise ValueError(f"unsupported statistic_kind: {statistic_kind}")


def _sample_pie_summary_values(
    *,
    statistic_kind: StatisticKind,
    mark_count: int,
    instance_seed: int,
    task_id: str,
) -> List[int]:
    """Sample one percentage composition that satisfies the requested summary property."""

    if str(statistic_kind) not in {"max", "min", "median"}:
        raise ValueError(f"pie-like summary statistics do not support {statistic_kind}")
    sample_rng = spawn_rng(int(instance_seed), f"{task_id}.pie_summary:{str(statistic_kind)}")
    for attempt in range(256):
        values = sample_composition_with_sum(
            sample_rng,
            target_sum=100,
            count=int(mark_count),
            value_min=1,
            value_max=100,
        )
        sample_rng.shuffle(values)
        if str(statistic_kind) == "max" and len([value for value in values if int(value) == int(max(values))]) == 1:
            return [int(value) for value in values]
        if str(statistic_kind) == "min" and len([value for value in values if int(value) == int(min(values))]) == 1:
            return [int(value) for value in values]
        if str(statistic_kind) == "median":
            if int(mark_count) % 2 == 0:
                raise ValueError("pie-like median requires an odd mark count")
            ordered = sorted(int(value) for value in values)
            median_value = int(ordered[len(ordered) // 2])
            if ordered.count(int(median_value)) == 1:
                return [int(value) for value in values]
    raise RuntimeError(f"unable to construct pie-like summary values for {statistic_kind}")


def build_summary_statistics_dataset_for_variant(
    *,
    statistic_kind: StatisticKind,
    scene_variant: SceneVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
    target_answer_ranges: Mapping[str, Tuple[int, int]],
    task_id: str,
) -> Tuple[List[int], int, List[str], Dict[str, Any]]:
    """Construct values, answer, evidence labels, and trace extras for one statistic variant."""

    pie_like = bool(is_pie_like_scene_variant(str(scene_variant)))
    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    mark_count_min, mark_count_max = apply_scene_variant_mark_count_cap(
        scene_variant=str(scene_variant),
        mark_count_min=int(mark_count_min),
        mark_count_max=int(mark_count_max),
    )
    if pie_like:
        feasible_counts = [
            int(count)
            for count in range(int(mark_count_min), int(mark_count_max) + 1)
            if str(statistic_kind) != "median" or int(count) % 2 == 1
        ]
        mark_count = choose_mark_count(
            feasible_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.mark_count:{str(statistic_kind)}:pie",
        )
        labels = list(sample_chart_labels(count=int(mark_count), instance_seed=int(instance_seed)))
        values = _sample_pie_summary_values(
            statistic_kind=str(statistic_kind),
            mark_count=int(mark_count),
            instance_seed=int(instance_seed),
            task_id=task_id,
        )
        answer_value, evidence_labels, summary_trace = summarize_statistic_from_values(
            statistic_kind=str(statistic_kind),
            labels=labels,
            values=values,
        )
        trace_extras: Dict[str, Any] = {
            "value_min": 1,
            "value_max": 99,
            "value_semantics": "percentage",
            "composition_total": 100,
            "target_answer_range": [1, 99],
            "mark_count_range": [int(mark_count_min), int(mark_count_max)],
            "target_answer": int(answer_value),
            "mark_count": int(mark_count),
            "labels": [str(label) for label in labels],
            "values_by_label": {str(label): int(value) for label, value in zip(labels, values)},
            **dict(summary_trace),
        }
        return [int(value) for value in values], int(answer_value), evidence_labels, trace_extras

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
        values, _, _ = build_values_for_range(
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

    answer_value, evidence_labels, summary_trace = summarize_statistic_from_values(
        statistic_kind=str(statistic_kind),
        labels=labels,
        values=values,
    )
    if int(answer_value) != int(target_answer):
        raise RuntimeError("constructed summary values do not match the requested target answer")

    trace_extras = {
        "value_min": int(value_min),
        "value_max": int(value_max),
        "target_answer_range": [int(supported_answer_min), int(supported_answer_max)],
        "mark_count_range": [int(mark_count_min), int(mark_count_max)],
        "target_answer": int(target_answer),
        "mark_count": int(mark_count),
        "labels": [str(label) for label in labels],
        "values_by_label": {str(label): int(value) for label, value in zip(labels, values)},
        **dict(summary_trace),
    }
    return [int(value) for value in values], int(answer_value), evidence_labels, trace_extras


def _find_pie_count_query(
    *,
    count_variant: str,
    target_answer: int,
    mark_count: int,
    instance_seed: int,
    task_id: str,
) -> Tuple[List[int], Dict[str, Any]]:
    """Sample one percentage composition and compatible count query."""

    query_rng = spawn_rng(int(instance_seed), f"{task_id}.pie_query:{str(count_variant)}")
    for _ in range(256):
        values = sample_composition_with_sum(
            query_rng,
            target_sum=100,
            count=int(mark_count),
            value_min=1,
            value_max=100,
        )
        query_rng.shuffle(values)
        if str(count_variant) == "above_threshold":
            candidates = [int(threshold) for threshold in range(0, 100) if sum(1 for value in values if int(value) > int(threshold)) == int(target_answer)]
            if candidates:
                threshold = int(candidates[query_rng.randint(0, len(candidates) - 1)])
                return [int(value) for value in values], {"threshold": int(threshold), "comparison": "greater_than"}
        elif str(count_variant) == "below_threshold":
            candidates = [int(threshold) for threshold in range(1, 101) if sum(1 for value in values if int(value) < int(threshold)) == int(target_answer)]
            if candidates:
                threshold = int(candidates[query_rng.randint(0, len(candidates) - 1)])
                return [int(value) for value in values], {"threshold": int(threshold), "comparison": "less_than"}
        elif str(count_variant) == "in_interval":
            candidates: List[Tuple[int, int]] = []
            for interval_min in range(0, 101):
                for interval_max in range(int(interval_min), 101):
                    count = sum(
                        1
                        for value in values
                        if int(interval_min) <= int(value) <= int(interval_max)
                    )
                    if int(count) == int(target_answer):
                        candidates.append((int(interval_min), int(interval_max)))
            if candidates:
                interval_min, interval_max = candidates[query_rng.randint(0, len(candidates) - 1)]
                return [
                    int(value) for value in values
                ], {
                    "interval_min": int(interval_min),
                    "interval_max": int(interval_max),
                    "interval_inclusive": True,
                }
        else:
            raise ValueError(f"unsupported count_variant: {count_variant}")
    raise RuntimeError(f"unable to construct pie-like count query for {count_variant}")


def build_value_count_dataset_for_variant(
    *,
    count_variant: str,
    scene_variant: SceneVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
    task_id: str,
) -> Tuple[List[int], int, List[str], Dict[str, Any]]:
    """Construct one labeled chart dataset for threshold/interval counting tasks."""

    pie_like = bool(is_pie_like_scene_variant(str(scene_variant)))
    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    mark_count_min, mark_count_max = apply_scene_variant_mark_count_cap(
        scene_variant=str(scene_variant),
        mark_count_min=int(mark_count_min),
        mark_count_max=int(mark_count_max),
    )
    default_answer_max = min(int(mark_count_max), 10)
    supported_answer_min = int(params.get("target_answer_min", group_default(gen_defaults, "target_answer_min", 0)))
    supported_answer_max = int(params.get("target_answer_max", group_default(gen_defaults, "target_answer_max", default_answer_max)))
    if int(supported_answer_min) > int(supported_answer_max):
        raise ValueError("target_answer_min must be <= target_answer_max")

    answer_candidates = [
        int(value)
        for value in range(int(supported_answer_min), int(supported_answer_max) + 1)
        if int(value) <= int(mark_count_max)
    ]
    target_answer = balanced_choice_from_values(
        answer_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:{str(count_variant)}",
    )
    feasible_counts = [
        int(count)
        for count in range(int(mark_count_min), int(mark_count_max) + 1)
        if int(count) >= int(target_answer)
    ]
    mark_count = choose_mark_count(
        feasible_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.mark_count:{str(count_variant)}:{int(target_answer)}",
    )
    labels = list(sample_chart_labels(count=int(mark_count), instance_seed=int(instance_seed)))
    if pie_like:
        values, query_trace = _find_pie_count_query(
            count_variant=str(count_variant),
            target_answer=int(target_answer),
            mark_count=int(mark_count),
            instance_seed=int(instance_seed),
            task_id=task_id,
        )
        if str(count_variant) == "above_threshold":
            threshold = int(query_trace["threshold"])
            evidence_rule = lambda value: int(value) > int(threshold)
        elif str(count_variant) == "below_threshold":
            threshold = int(query_trace["threshold"])
            evidence_rule = lambda value: int(value) < int(threshold)
        else:
            interval_min = int(query_trace["interval_min"])
            interval_max = int(query_trace["interval_max"])
            evidence_rule = lambda value: int(interval_min) <= int(value) <= int(interval_max)
        marks = {str(label): int(value) for label, value in zip(labels, values)}
        evidence_labels = sorted_labels(
            [str(label) for label in labels if bool(evidence_rule(int(marks[str(label)])))]
        )
        if int(len(evidence_labels)) != int(target_answer):
            raise RuntimeError("constructed pie-like counting dataset does not match requested answer")
        trace_extras: Dict[str, Any] = {
            "value_min": 1,
            "value_max": 99,
            "value_semantics": "percentage",
            "composition_total": 100,
            "target_answer_range": [int(supported_answer_min), int(supported_answer_max)],
            "mark_count_range": [int(mark_count_min), int(mark_count_max)],
            "target_answer": int(target_answer),
            "mark_count": int(mark_count),
            "labels": [str(label) for label in labels],
            "values_by_label": {str(label): int(marks[str(label)]) for label in labels},
            "evidence_labels": list(evidence_labels),
            **query_trace,
        }
        return [int(value) for value in values], int(target_answer), evidence_labels, trace_extras

    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query:{str(count_variant)}")

    if str(count_variant) == "above_threshold":
        if int(target_answer) == 0:
            values = _sample_int_values(
                query_rng,
                count=int(mark_count),
                min_value=int(value_min),
                max_value=int(value_max),
            )
            threshold = int(max(values))
        elif int(target_answer) == int(mark_count):
            values = _sample_int_values(
                query_rng,
                count=int(mark_count),
                min_value=int(value_min),
                max_value=int(value_max),
            )
            threshold = int(min(values)) - 1
        else:
            threshold = int(query_rng.randint(int(value_min), int(value_max) - 1))
            low_values = _sample_int_values(
                query_rng,
                count=int(mark_count) - int(target_answer),
                min_value=int(value_min),
                max_value=int(threshold),
            )
            high_values = _sample_int_values(
                query_rng,
                count=int(target_answer),
                min_value=int(threshold) + 1,
                max_value=int(value_max),
            )
            values = shuffle_values(
                [*low_values, *high_values],
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.value_order:{str(count_variant)}",
            )
        evidence_rule = lambda value: int(value) > int(threshold)
        query_trace = {
            "threshold": int(threshold),
            "comparison": "greater_than",
        }
    elif str(count_variant) == "below_threshold":
        if int(target_answer) == 0:
            values = _sample_int_values(
                query_rng,
                count=int(mark_count),
                min_value=int(value_min),
                max_value=int(value_max),
            )
            threshold = int(min(values))
        elif int(target_answer) == int(mark_count):
            values = _sample_int_values(
                query_rng,
                count=int(mark_count),
                min_value=int(value_min),
                max_value=int(value_max),
            )
            threshold = int(max(values)) + 1
        else:
            threshold = int(query_rng.randint(int(value_min) + 1, int(value_max)))
            low_values = _sample_int_values(
                query_rng,
                count=int(target_answer),
                min_value=int(value_min),
                max_value=int(threshold) - 1,
            )
            high_values = _sample_int_values(
                query_rng,
                count=int(mark_count) - int(target_answer),
                min_value=int(threshold),
                max_value=int(value_max),
            )
            values = shuffle_values(
                [*low_values, *high_values],
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.value_order:{str(count_variant)}",
            )
        evidence_rule = lambda value: int(value) < int(threshold)
        query_trace = {
            "threshold": int(threshold),
            "comparison": "less_than",
        }
    elif str(count_variant) == "in_interval":
        if int(target_answer) == 0:
            values = _sample_int_values(
                query_rng,
                count=int(mark_count),
                min_value=int(value_min),
                max_value=int(value_max),
            )
            present_values = {int(value) for value in values}
            missing_values = [
                int(value)
                for value in range(int(value_min), int(value_max) + 1)
                if int(value) not in present_values
            ]
            interval_value = int(
                missing_values[query_rng.randint(0, len(missing_values) - 1)]
                if missing_values
                else int(value_max) + 1
            )
            interval_min = int(interval_value)
            interval_max = int(interval_value)
        elif int(target_answer) == int(mark_count):
            values = _sample_int_values(
                query_rng,
                count=int(mark_count),
                min_value=int(value_min),
                max_value=int(value_max),
            )
            interval_min = int(min(values))
            interval_max = int(max(values))
        else:
            interval_mode = ("left", "right", "both")[int(query_rng.randint(0, 2))]
            if str(interval_mode) == "left":
                interval_min = int(query_rng.randint(int(value_min) + 1, int(value_max)))
                interval_max = int(value_max)
                outside_pool = [int(value) for value in range(int(value_min), int(interval_min))]
            elif str(interval_mode) == "right":
                interval_min = int(value_min)
                interval_max = int(query_rng.randint(int(value_min), int(value_max) - 1))
                outside_pool = [int(value) for value in range(int(interval_max) + 1, int(value_max) + 1)]
            else:
                interval_min = int(query_rng.randint(int(value_min) + 1, int(value_max) - 1))
                interval_max = int(query_rng.randint(int(interval_min), int(value_max) - 1))
                outside_pool = [
                    *[int(value) for value in range(int(value_min), int(interval_min))],
                    *[int(value) for value in range(int(interval_max) + 1, int(value_max) + 1)],
                ]
            inside_values = _sample_int_values(
                query_rng,
                count=int(target_answer),
                min_value=int(interval_min),
                max_value=int(interval_max),
            )
            outside_values = _sample_values_from_pool(
                query_rng,
                count=int(mark_count) - int(target_answer),
                pool=outside_pool,
            )
            values = shuffle_values(
                [*inside_values, *outside_values],
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.value_order:{str(count_variant)}",
            )
        evidence_rule = lambda value: int(interval_min) <= int(value) <= int(interval_max)
        query_trace = {
            "interval_min": int(interval_min),
            "interval_max": int(interval_max),
            "interval_inclusive": True,
        }
    else:
        raise ValueError(f"unsupported count_variant: {count_variant}")

    marks = {str(label): int(value) for label, value in zip(labels, values)}
    evidence_labels = sorted_labels(
        [str(label) for label in labels if bool(evidence_rule(int(marks[str(label)])))]
    )
    if int(len(evidence_labels)) != int(target_answer):
        raise RuntimeError("constructed counting dataset does not match requested answer")

    trace_extras: Dict[str, Any] = {
        "value_min": int(value_min),
        "value_max": int(value_max),
        "target_answer_range": [int(supported_answer_min), int(supported_answer_max)],
        "mark_count_range": [int(mark_count_min), int(mark_count_max)],
        "target_answer": int(target_answer),
        "mark_count": int(mark_count),
        "labels": [str(label) for label in labels],
        "values_by_label": {str(label): int(marks[str(label)]) for label in labels},
        "evidence_labels": list(evidence_labels),
        **query_trace,
    }
    return [int(value) for value in values], int(target_answer), evidence_labels, trace_extras


def _default_readout_answer_range(
    readout_variant: str,
    *,
    value_min: int,
    value_max: int,
) -> Tuple[int, int]:
    """Return the default target-answer support for one two-label readout variant."""

    if str(readout_variant) == "sum_two":
        return int(2 * int(value_min)), int(2 * int(value_max))
    if str(readout_variant) == "difference_two_abs":
        return 0, int(value_max) - int(value_min)
    if str(readout_variant) in {"max_two", "min_two", "mean_two"}:
        return int(value_min), int(value_max)
    raise ValueError(f"unsupported readout_variant: {readout_variant}")


def _default_pie_readout_answer_range(readout_variant: str) -> Tuple[int, int]:
    """Return conservative default answer support for two-slice percentage readout."""

    if str(readout_variant) == "sum_two":
        return 2, 94
    if str(readout_variant) == "difference_two_abs":
        return 0, 90
    if str(readout_variant) == "max_two":
        return 1, 91
    if str(readout_variant) in {"min_two", "mean_two"}:
        return 1, 47
    raise ValueError(f"unsupported readout_variant: {readout_variant}")


def _build_query_pair_for_readout(
    readout_variant: str,
    *,
    target_answer: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    """Construct the ordered queried values for one two-label readout variant."""

    rng = spawn_rng(int(instance_seed), str(namespace))
    if str(readout_variant) == "sum_two":
        low = max(int(value_min), int(target_answer) - int(value_max))
        high = min(int(value_max), int(target_answer) - int(value_min))
        if int(low) > int(high):
            raise ValueError("sum_two target is outside feasible pair support")
        first = int(rng.randint(int(low), int(high)))
        second = int(target_answer) - int(first)
        values = [int(first), int(second)]
    elif str(readout_variant) == "difference_two_abs":
        if int(target_answer) < 0 or int(target_answer) > int(value_max) - int(value_min):
            raise ValueError("difference_two_abs target is outside feasible support")
        if int(target_answer) == 0:
            repeated = int(rng.randint(int(value_min), int(value_max)))
            values = [int(repeated), int(repeated)]
        else:
            low = int(rng.randint(int(value_min), int(value_max) - int(target_answer)))
            high = int(low) + int(target_answer)
            values = [int(low), int(high)]
    elif str(readout_variant) == "max_two":
        if int(target_answer) < int(value_min) or int(target_answer) > int(value_max):
            raise ValueError("max_two target is outside feasible support")
        other = int(rng.randint(int(value_min), int(target_answer)))
        values = [int(target_answer), int(other)]
    elif str(readout_variant) == "min_two":
        if int(target_answer) < int(value_min) or int(target_answer) > int(value_max):
            raise ValueError("min_two target is outside feasible support")
        other = int(rng.randint(int(target_answer), int(value_max)))
        values = [int(target_answer), int(other)]
    elif str(readout_variant) == "mean_two":
        if int(target_answer) < int(value_min) or int(target_answer) > int(value_max):
            raise ValueError("mean_two target is outside feasible support")
        max_delta = max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max))
        delta = int(rng.randint(0, int(max_delta)))
        values = [int(target_answer) - int(delta), int(target_answer) + int(delta)]
    else:
        raise ValueError(f"unsupported readout_variant: {readout_variant}")
    if int(rng.randint(0, 1)) == 1:
        values = [int(values[1]), int(values[0])]
    return [int(value) for value in values]


def _build_pie_query_pair_for_readout(
    readout_variant: str,
    *,
    target_answer: int,
    mark_count: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    """Construct the ordered queried percentages for one two-slice readout variant."""

    remaining_slots = int(mark_count) - 2
    if int(remaining_slots) < 0:
        raise ValueError("pie readout requires at least two marks")
    max_pair_sum = 100 - int(remaining_slots)
    rng = spawn_rng(int(instance_seed), str(namespace))

    if str(readout_variant) == "sum_two":
        if int(target_answer) < 2 or int(target_answer) > int(max_pair_sum):
            raise ValueError("sum_two target is outside feasible pie support")
        first = int(rng.randint(1, int(target_answer) - 1))
        second = int(target_answer) - int(first)
        values = [int(first), int(second)]
    elif str(readout_variant) == "difference_two_abs":
        if int(target_answer) < 0 or int(target_answer) > int(max_pair_sum) - 2:
            raise ValueError("difference_two_abs target is outside feasible pie support")
        if int(target_answer) == 0:
            repeated_max = int(max_pair_sum // 2)
            repeated = int(rng.randint(1, int(repeated_max)))
            values = [int(repeated), int(repeated)]
        else:
            low_max = int((int(max_pair_sum) - int(target_answer)) // 2)
            low = int(rng.randint(1, int(low_max)))
            values = [int(low), int(low) + int(target_answer)]
    elif str(readout_variant) == "max_two":
        if int(target_answer) < 1 or int(target_answer) > int(max_pair_sum) - 1:
            raise ValueError("max_two target is outside feasible pie support")
        other_high = int(min(int(target_answer), int(max_pair_sum) - int(target_answer)))
        other = int(rng.randint(1, int(other_high)))
        values = [int(target_answer), int(other)]
    elif str(readout_variant) == "min_two":
        if int(target_answer) < 1:
            raise ValueError("min_two target is outside feasible pie support")
        other_high = int(max_pair_sum) - int(target_answer)
        if int(other_high) < int(target_answer):
            raise ValueError("min_two target is outside feasible pie support")
        other = int(rng.randint(int(target_answer), int(other_high)))
        values = [int(target_answer), int(other)]
    elif str(readout_variant) == "mean_two":
        if int(target_answer) < 1 or (2 * int(target_answer)) > int(max_pair_sum):
            raise ValueError("mean_two target is outside feasible pie support")
        max_delta = int(target_answer) - 1
        delta = int(rng.randint(0, int(max_delta)))
        values = [int(target_answer) - int(delta), int(target_answer) + int(delta)]
    else:
        raise ValueError(f"unsupported readout_variant: {readout_variant}")

    if int(rng.randint(0, 1)) == 1:
        values = [int(values[1]), int(values[0])]
    return [int(value) for value in values]


def build_value_readout_dataset_for_variant(
    *,
    readout_variant: str,
    scene_variant: SceneVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
    task_id: str,
) -> Tuple[List[int], int, List[int], Dict[str, Any]]:
    """Construct one labeled chart dataset for two-label numeric readout tasks."""

    pie_like = bool(is_pie_like_scene_variant(str(scene_variant)))
    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    mark_count_min, mark_count_max = apply_scene_variant_mark_count_cap(
        scene_variant=str(scene_variant),
        mark_count_min=int(mark_count_min),
        mark_count_max=int(mark_count_max),
    )
    if pie_like:
        default_answer_min, default_answer_max = _default_pie_readout_answer_range(str(readout_variant))
    else:
        default_answer_min, default_answer_max = _default_readout_answer_range(
            str(readout_variant),
            value_min=int(value_min),
            value_max=int(value_max),
        )
    explicit_min = params.get("target_answer_min")
    explicit_max = params.get("target_answer_max")
    supported_answer_min = int(default_answer_min if explicit_min is None else explicit_min)
    supported_answer_max = int(default_answer_max if explicit_max is None else explicit_max)
    if int(supported_answer_min) > int(supported_answer_max):
        raise ValueError("target_answer_min must be <= target_answer_max")

    answer_candidates = [
        int(value)
        for value in range(int(supported_answer_min), int(supported_answer_max) + 1)
        if int(default_answer_min) <= int(value) <= int(default_answer_max)
    ]
    if not answer_candidates:
        raise ValueError("no feasible target answers for requested readout range")
    target_answer = balanced_choice_from_values(
        answer_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:{str(readout_variant)}",
    )
    feasible_counts = [int(count) for count in range(int(mark_count_min), int(mark_count_max) + 1) if int(count) >= 2]
    mark_count = choose_mark_count(
        feasible_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.mark_count:{str(readout_variant)}:{int(target_answer)}",
    )
    labels = list(sample_chart_labels(count=int(mark_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_labels:{str(readout_variant)}")
    query_indices = list(range(int(mark_count)))
    query_rng.shuffle(query_indices)
    first_index, second_index = int(query_indices[0]), int(query_indices[1])
    query_labels = [str(labels[first_index]), str(labels[second_index])]
    query_values = _build_query_pair_for_readout(
        str(readout_variant),
        target_answer=int(target_answer),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_values:{str(readout_variant)}",
    ) if not pie_like else _build_pie_query_pair_for_readout(
        str(readout_variant),
        target_answer=int(target_answer),
        mark_count=int(mark_count),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_values:{str(readout_variant)}:pie",
    )
    if pie_like:
        remaining_rng = spawn_rng(int(instance_seed), f"{task_id}.other_values:{str(readout_variant)}:pie")
        remaining_sum = 100 - int(sum(query_values))
        remaining_values = sample_composition_with_sum(
            remaining_rng,
            target_sum=int(remaining_sum),
            count=int(mark_count) - 2,
            value_min=1,
            value_max=100,
        )
        remaining_rng.shuffle(remaining_values)
    else:
        remaining_rng = spawn_rng(int(instance_seed), f"{task_id}.other_values:{str(readout_variant)}")
        remaining_values = _sample_int_values(
            remaining_rng,
            count=int(mark_count) - 2,
            min_value=int(value_min),
            max_value=int(value_max),
        )
    values_by_label: Dict[str, int] = {}
    remaining_iter = iter(int(value) for value in remaining_values)
    for index, label in enumerate(labels):
        if int(index) == int(first_index):
            values_by_label[str(label)] = int(query_values[0])
        elif int(index) == int(second_index):
            values_by_label[str(label)] = int(query_values[1])
        else:
            values_by_label[str(label)] = int(next(remaining_iter))
    values = [int(values_by_label[str(label)]) for label in labels]
    evidence_values = [int(values_by_label[str(label)]) for label in query_labels]

    if str(readout_variant) == "sum_two":
        answer_value = int(sum(evidence_values))
    elif str(readout_variant) == "difference_two_abs":
        answer_value = int(abs(int(evidence_values[0]) - int(evidence_values[1])))
    elif str(readout_variant) == "max_two":
        answer_value = int(max(evidence_values))
    elif str(readout_variant) == "min_two":
        answer_value = int(min(evidence_values))
    elif str(readout_variant) == "mean_two":
        total = int(sum(evidence_values))
        if int(total) % 2 != 0:
            raise RuntimeError("mean_two evidence values must sum to an even number")
        answer_value = int(total // 2)
    else:
        raise ValueError(f"unsupported readout_variant: {readout_variant}")

    if int(answer_value) != int(target_answer):
        raise RuntimeError("constructed readout dataset does not match requested answer")

    trace_extras: Dict[str, Any] = {
        "value_min": 1 if pie_like else int(value_min),
        "value_max": 99 if pie_like else int(value_max),
        **({"value_semantics": "percentage", "composition_total": 100} if pie_like else {}),
        "target_answer_range": [int(supported_answer_min), int(supported_answer_max)],
        "mark_count_range": [int(mark_count_min), int(mark_count_max)],
        "target_answer": int(target_answer),
        "mark_count": int(mark_count),
        "labels": [str(label) for label in labels],
        "values_by_label": {str(label): int(values_by_label[str(label)]) for label in labels},
        "query_labels": [str(label) for label in query_labels],
        "query_values": [int(value) for value in evidence_values],
    }
    return [int(value) for value in values], int(answer_value), [int(value) for value in evidence_values], trace_extras


def resolve_chart_render_params_for_task(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
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
    "LabeledChartDefaults",
    "PIE_LIKE_SCENE_VARIANTS",
    "SUPPORTED_LABELED_CHART_SCENE_VARIANTS",
    "StatisticKind",
    "SceneVariant",
    "balanced_choice_from_values",
    "build_chart_mark_specs",
    "build_value_readout_dataset_for_variant",
    "build_summary_statistics_dataset_for_variant",
    "build_value_count_dataset_for_variant",
    "is_pie_like_scene_variant",
    "resolve_chart_axis_variant",
    "resolve_chart_mark_colors",
    "resolve_chart_render_params_for_task",
    "resolve_mark_count_bounds",
    "resolve_value_bounds",
    "sorted_labels",
]
