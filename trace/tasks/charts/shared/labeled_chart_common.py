"""Shared generation/render helpers for labeled chart task families."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ...shared.color_distance import (
    sample_color_palette_with_distance_constraints,
    sample_color_with_distance_constraints,
)
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.named_colors import darken_color
from ...shared.render_variation import apply_layout_jitter_to_margins
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .chart_scene import (
    ChartMarkSpec,
    ChartRenderParams,
    RenderedChartScene,
    SUPPORTED_CHART_SCENE_VARIANTS,
    resolve_chart_render_params,
)
from .label_assets import resolve_chart_compact_axis_labels


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
    pie_like_mark_color_channel_max: int = 200
    pie_like_mark_color_min_distance: float = 58.0
    mark_color_distance_space: str = "lab"
    balanced_query_id_sampling: bool = True
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

    Review overlays and public pixel evidence need pixel-space geometry. This
    helper returns compact per-mark projections for the selected labels in the
    same order they were requested.
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
        bbox = [float(value) for value in mark_trace["mark_bbox_px"]]
        if str(rendered_scene.scene_variant) == "bar":
            center = [
                0.5 * (float(bbox[0]) + float(bbox[2])),
                float(bbox[1]),
            ]
        elif str(rendered_scene.scene_variant) == "horizontal_bar":
            center = [
                float(bbox[2]),
                0.5 * (float(bbox[1]) + float(bbox[3])),
            ]
        else:
            center = [float(value) for value in mark_trace["mark_center_px"]]
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
    instance_seed: int | None = None,
) -> Tuple[int, int]:
    """Resolve inclusive per-mark value bounds."""

    value_min, value_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="value_min",
        max_key="value_max",
        fallback_min=int(defaults.value_min),
        fallback_max=int(defaults.value_max),
        context=f"generation defaults for {task_id}",
    )
    enabled_raw = params.get("value_window_enabled", group_default(gen_defaults, "value_window_enabled", False))
    enabled = bool(enabled_raw)
    if isinstance(enabled_raw, str):
        enabled = str(enabled_raw).strip().lower() in {"1", "true", "yes", "on"}
    if not enabled or instance_seed is None:
        return int(value_min), int(value_max)

    hard_max = int(params.get("value_hard_max", group_default(gen_defaults, "value_hard_max", 99)))
    span_min = int(params.get("value_window_span_min", group_default(gen_defaults, "value_window_span_min", 10)))
    span_max = int(params.get("value_window_span_max", group_default(gen_defaults, "value_window_span_max", 25)))
    hard_max = min(int(value_max), int(hard_max))
    span_min = max(1, int(span_min))
    span_max = max(int(span_min), int(span_max))
    max_feasible_span = int(hard_max) - int(value_min)
    if int(max_feasible_span) <= 0:
        return int(value_min), int(value_max)
    low_span = min(int(span_min), int(max_feasible_span))
    high_span = min(int(span_max), int(max_feasible_span))
    if int(low_span) > int(high_span):
        low_span = int(high_span)
    span = hashed_choice_from_values(
        [int(value) for value in range(int(low_span), int(high_span) + 1)],
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.value_window_span",
    )
    start_max = int(hard_max) - int(span)
    if int(start_max) < int(value_min):
        return int(value_min), int(hard_max)
    start = hashed_choice_from_values(
        [int(value) for value in range(int(value_min), int(start_max) + 1)],
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.value_window_start:{int(span)}",
    )
    return int(start), int(start) + int(span)


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
    if str(scene_variant) == "radar":
        resolved_max = min(int(resolved_max), 7)
    if int(resolved_min) > int(resolved_max):
        raise ValueError(f"no feasible mark-count support for scene_variant={scene_variant}")
    return int(resolved_min), int(resolved_max)


def resolve_target_answer_range(
    params: Mapping[str, Any],
    *,
    value_min: int,
    value_max: int,
    target_answer_ranges: Mapping[str, Tuple[int, int]],
    statistic_kind: StatisticKind,
) -> Tuple[int, int]:
    """Resolve supported target-answer bounds for one statistic."""

    default_min, default_max = target_answer_ranges[str(statistic_kind)]
    explicit_min = params.get("target_answer_min", None)
    explicit_max = params.get("target_answer_max", None)
    if explicit_min is None and explicit_max is None:
        return int(default_min), int(default_max)
    min_value = int(default_min if explicit_min is None else explicit_min)
    max_value = int(default_max if explicit_max is None else explicit_max)
    if int(min_value) > int(max_value):
        raise ValueError("target_answer_min must be <= target_answer_max")
    min_value = max(int(min_value), int(value_min))
    max_value = min(int(max_value), int(value_max))
    if int(min_value) > int(max_value):
        raise ValueError("target answer bounds leave no feasible support")
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


def hashed_choice_from_values(
    values: Sequence[int],
    *,
    instance_seed: int,
    namespace: str,
) -> int:
    """Select one supported integer value without sampling-index coupling."""

    ordered = [int(value) for value in values]
    if not ordered:
        raise ValueError(f"no feasible values for {namespace}")
    selection_index = abs(int(hash64(int(instance_seed), str(namespace), 0)))
    return int(ordered[int(selection_index) % len(ordered)])


def shuffle_values(values: Sequence[int], *, instance_seed: int, namespace: str) -> List[int]:
    """Shuffle numeric values independently of labels and chart type."""

    rng = spawn_rng(int(instance_seed), str(namespace))
    ordered = [int(value) for value in values]
    rng.shuffle(ordered)
    return ordered


def sample_chart_labels(
    *,
    count: int,
    instance_seed: int,
    namespace: str = "charts.labels",
    max_chars: int = 4,
) -> Tuple[str, ...]:
    """Sample one randomized compact label list for chart marks.

    Most labeled chart scenes use this helper for visible axis/category labels.
    Keep labels short for dense chart layouts and draw from a large synthetic
    ID pool so random fonts do not make words collide on crowded axes.
    """

    label_rng = spawn_rng(int(instance_seed), str(namespace))
    resolved = resolve_chart_compact_axis_labels(
        label_rng,
        count=int(count),
        min_chars=2,
        max_chars=int(max_chars),
    )
    return tuple(str(label) for label in resolved.labels)


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
        pie_channel_max = int(
            params.get(
                "pie_like_mark_color_channel_max",
                group_default(
                    render_defaults,
                    "pie_like_mark_color_channel_max",
                    defaults.pie_like_mark_color_channel_max,
                ),
            )
        )
        pie_min_distance = float(
            params.get(
                "pie_like_mark_color_min_distance",
                group_default(
                    render_defaults,
                    "pie_like_mark_color_min_distance",
                    defaults.pie_like_mark_color_min_distance,
                ),
            )
        )
        fill_palette = sample_color_palette_with_distance_constraints(
            color_rng,
            palette_size=int(mark_count),
            channel_min=int(channel_min),
            channel_max=int(min(int(channel_max), int(pie_channel_max))),
            anchor_colors=((255, 255, 255), (248, 248, 248), (236, 238, 242)),
            min_distance=float(max(float(min_distance), float(pie_min_distance))),
            distance_space=str(distance_space),
        )
        outline_palette = [darken_color(fill_rgb, factor=0.55) for fill_rgb in fill_palette]
        return {
            "sampling_policy": "random_rgb_palette",
            "mark_fill_rgb": [int(channel) for channel in fill_palette[0]],
            "mark_outline_rgb": [int(channel) for channel in outline_palette[0]],
            "slice_fill_palette_rgb": [[int(channel) for channel in fill_rgb] for fill_rgb in fill_palette],
            "slice_outline_palette_rgb": [[int(channel) for channel in outline_rgb] for outline_rgb in outline_palette],
            "mark_color_min_distance": float(max(float(min_distance), float(pie_min_distance))),
            "pie_like_mark_color_channel_max": int(min(int(channel_max), int(pie_channel_max))),
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


def build_values_for_nth_rank(
    target_answer: int,
    *,
    count: int,
    rank_n: int,
    direction: str,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> List[int]:
    """Construct values where `target_answer` is the unique nth distinct ranked value."""

    if int(rank_n) < 2:
        raise ValueError("rank_n must be at least 2")
    if int(count) < int(rank_n):
        raise ValueError("count must be at least rank_n")
    rng = spawn_rng(int(instance_seed), f"charts.values.nth_rank:{str(direction)}:{int(rank_n)}:{int(target_answer)}")
    if str(direction) == "highest":
        above_candidates = [int(value) for value in range(int(target_answer) + 1, int(value_max) + 1)]
        if len(above_candidates) < int(rank_n) - 1:
            raise ValueError("not enough distinct values above target_answer for nth-highest construction")
        ranked_values = [int(value) for value in rng.sample(above_candidates, k=int(rank_n) - 1)]
        fill_pool = ranked_values + [int(value) for value in range(int(value_min), int(target_answer))]
    elif str(direction) == "lowest":
        below_candidates = [int(value) for value in range(int(value_min), int(target_answer))]
        if len(below_candidates) < int(rank_n) - 1:
            raise ValueError("not enough distinct values below target_answer for nth-lowest construction")
        ranked_values = [int(value) for value in rng.sample(below_candidates, k=int(rank_n) - 1)]
        fill_pool = ranked_values + [int(value) for value in range(int(target_answer) + 1, int(value_max) + 1)]
    else:
        raise ValueError(f"unsupported rank direction: {direction}")
    if not fill_pool and int(count) > int(rank_n):
        raise ValueError("rank construction has no non-target fill values")
    values = [int(value) for value in ranked_values] + [int(target_answer)]
    while len(values) < int(count):
        values.append(int(fill_pool[int(rng.randint(0, len(fill_pool) - 1))]))
    rng.shuffle(values)
    if values.count(int(target_answer)) != 1:
        raise RuntimeError("rank construction must keep target_answer unique")
    return [int(value) for value in values]


def choose_rank_n(
    feasible_ranks: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Choose one feasible order-statistic rank deterministically."""

    values = [int(value) for value in feasible_ranks]
    if not values:
        raise ValueError(f"no feasible ranks for {namespace}")
    explicit_rank = params.get("rank_n")
    if explicit_rank is not None:
        selected = int(explicit_rank)
        if int(selected) not in set(values):
            raise ValueError("explicit rank_n is outside feasible support")
        return int(selected)
    selection_index = abs(int(hash64(int(instance_seed), str(namespace), 0)))
    return int(values[int(selection_index) % len(values)])


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
    rank_n: int | None = None,
) -> Tuple[int, List[str], Dict[str, Any]]:
    """Resolve the statistic answer and supporting labels from one labeled value list."""

    resolved_labels = [str(label) for label in labels]
    resolved_values = [int(value) for value in values]
    if len(resolved_labels) != len(resolved_values):
        raise ValueError("labels and values must have the same length")

    marks = {str(label): int(value) for label, value in zip(resolved_labels, resolved_values)}
    if str(statistic_kind) == "median":
        if int(len(resolved_values)) % 2 == 0:
            raise ValueError("median requires an odd number of values")
        sorted_pairs = sorted(((int(value), str(label)) for label, value in marks.items()), key=lambda item: (item[0], item[1]))
        median_index = len(sorted_pairs) // 2
        median_value = int(sorted_pairs[median_index][0])
        support_labels = [str(label) for label, value in marks.items() if int(value) == int(median_value)]
        if len(support_labels) != 1:
            raise ValueError("median requires one unique median label")
        return (
            int(median_value),
            [str(support_labels[0])],
            {
                "support_label": str(support_labels[0]),
                "sorted_values": [int(value) for value, _ in sorted_pairs],
            },
        )
    if str(statistic_kind) in {"nth_highest", "nth_lowest"}:
        if rank_n is None:
            raise ValueError(f"{statistic_kind} requires rank_n")
        resolved_rank = int(rank_n)
        unique_values = sorted(set(int(value) for value in resolved_values), reverse=str(statistic_kind) == "nth_highest")
        if int(resolved_rank) < 1 or int(resolved_rank) > len(unique_values):
            raise ValueError(f"rank_n outside distinct value support for {statistic_kind}")
        target_value = int(unique_values[int(resolved_rank) - 1])
        ranked_labels = [str(label) for label, value in marks.items() if int(value) == int(target_value)]
        if len(ranked_labels) != 1:
            raise ValueError(f"{statistic_kind} requires one unique ranked label")
        return (
            int(target_value),
            [str(ranked_labels[0])],
            {
                "rank_n": int(resolved_rank),
                "rank_direction": "highest" if str(statistic_kind) == "nth_highest" else "lowest",
                "ranked_label": str(ranked_labels[0]),
                "ranked_distinct_values": [int(value) for value in unique_values],
            },
        )
    raise ValueError(f"unsupported statistic_kind: {statistic_kind}")


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

    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
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

    if str(statistic_kind) in {"nth_highest", "nth_lowest"}:
        rank_n_min = int(params.get("rank_n_min", group_default(gen_defaults, "rank_n_min", 3)))
        rank_n_max = int(params.get("rank_n_max", group_default(gen_defaults, "rank_n_max", 8)))
        if int(rank_n_min) > int(rank_n_max):
            raise ValueError("rank_n_min must be <= rank_n_max")
        feasible_counts = [
            int(count)
            for count in range(int(mark_count_min), int(mark_count_max) + 1)
            if int(count) >= int(rank_n_min)
        ]
        mark_count = choose_mark_count(
            feasible_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.mark_count:{str(statistic_kind)}:rank",
        )
        max_distinct_rank = int(value_max) - int(value_min) + 1
        rank_candidates = [
            int(rank)
            for rank in range(int(rank_n_min), min(int(rank_n_max), int(mark_count), int(max_distinct_rank)) + 1)
            if (
                (str(statistic_kind) == "nth_highest" and int(value_min) <= int(value_max) - (int(rank) - 1))
                or (str(statistic_kind) == "nth_lowest" and int(value_min) + (int(rank) - 1) <= int(value_max))
            )
        ]
        rank_n = choose_rank_n(
            rank_candidates,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.rank_n:{str(statistic_kind)}:{int(mark_count)}",
        )
        explicit_min = params.get("target_answer_min", None)
        explicit_max = params.get("target_answer_max", None)
        target_min = int(value_min if explicit_min is None else explicit_min)
        target_max = int(value_max if explicit_max is None else explicit_max)
        if str(statistic_kind) == "nth_highest":
            target_max = min(int(target_max), int(value_max) - (int(rank_n) - 1))
            direction = "highest"
        else:
            target_min = max(int(target_min), int(value_min) + (int(rank_n) - 1))
            direction = "lowest"
        target_candidates = [
            int(value)
            for value in range(int(target_min), int(target_max) + 1)
            if int(value_min) <= int(value) <= int(value_max)
        ]
        target_answer = balanced_choice_from_values(
            target_candidates,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_answer:{str(statistic_kind)}:{int(rank_n)}",
        )
        labels = list(
            sample_chart_labels(
                count=int(mark_count),
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.labels:{str(statistic_kind)}:{int(mark_count)}",
            )
        )
        values = build_values_for_nth_rank(
            int(target_answer),
            count=int(mark_count),
            rank_n=int(rank_n),
            direction=str(direction),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
        answer_value, evidence_labels, summary_trace = summarize_statistic_from_values(
            statistic_kind=str(statistic_kind),
            labels=labels,
            values=values,
            rank_n=int(rank_n),
        )
        if int(answer_value) != int(target_answer):
            raise RuntimeError("constructed ranked values do not match the requested target answer")
        trace_extras = {
            "value_min": int(value_min),
            "value_max": int(value_max),
            "target_answer_range": [int(min(target_candidates)), int(max(target_candidates))],
            "mark_count_range": [int(mark_count_min), int(mark_count_max)],
            "rank_n_range": [int(rank_n_min), int(rank_n_max)],
            "target_answer": int(target_answer),
            "mark_count": int(mark_count),
            "labels": [str(label) for label in labels],
            "values_by_label": {str(label): int(value) for label, value in zip(labels, values)},
            **dict(summary_trace),
        }
        return [int(value) for value in values], int(answer_value), evidence_labels, trace_extras

    supported_answer_min, supported_answer_max = resolve_target_answer_range(
        params,
        value_min=int(value_min),
        value_max=int(value_max),
        target_answer_ranges=target_answer_ranges,
        statistic_kind=str(statistic_kind),
    )
    answer_candidates = [int(value) for value in range(int(supported_answer_min), int(supported_answer_max) + 1)]
    candidate_counts_for_target = [int(count) for count in range(int(mark_count_min), int(mark_count_max) + 1)]
    explicit_mark_count = params.get("mark_count")
    if explicit_mark_count is not None:
        candidate_counts_for_target = [
            int(count)
            for count in candidate_counts_for_target
            if int(count) == int(explicit_mark_count)
        ]
    if str(statistic_kind) != "median":
        raise ValueError(f"unsupported statistic_kind: {statistic_kind}")
    answer_candidates = [
        int(value)
        for value in answer_candidates
        if any(
            int(count) % 2 == 1
            and max_symmetric_delta(int(value), value_min=int(value_min), value_max=int(value_max))
            >= (int(count) - 1) // 2
            for count in candidate_counts_for_target
        )
    ]
    target_answer = balanced_choice_from_values(
        answer_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:{str(statistic_kind)}",
    )

    feasible_counts = [
        int(count)
        for count in range(int(mark_count_min), int(mark_count_max) + 1)
        if int(count) % 2 == 1
        and max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max))
        >= (int(count) - 1) // 2
    ]

    mark_count = choose_mark_count(
        feasible_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.mark_count:{str(statistic_kind)}:{int(target_answer)}",
    )
    labels = list(
        sample_chart_labels(
            count=int(mark_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(statistic_kind)}:{int(mark_count)}",
        )
    )

    values = build_values_for_median(
        int(target_answer),
        count=int(mark_count),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
    )

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
    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
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
    labels = list(
        sample_chart_labels(
            count=int(mark_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(count_variant)}:{int(mark_count)}",
        )
    )
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


def _trend_signs_for_values(values: Sequence[int]) -> List[int]:
    """Return the +/- step-sign sequence for one ordered value list."""

    resolved_values = [int(value) for value in values]
    if len(resolved_values) < 2:
        raise ValueError("trend analysis requires at least two values")
    signs: List[int] = []
    for left, right in zip(resolved_values[:-1], resolved_values[1:]):
        delta = int(right) - int(left)
        if int(delta) == 0:
            raise ValueError("trend analysis requires strictly ordered adjacent values")
        signs.append(1 if int(delta) > 0 else -1)
    return [int(value) for value in signs]


def _turning_point_indices(signs: Sequence[int], *, positive_then_negative: bool) -> List[int]:
    """Return interior point indices for local peaks or troughs."""

    resolved_signs = [int(value) for value in signs]
    indices: List[int] = []
    for index in range(len(resolved_signs) - 1):
        left = int(resolved_signs[index])
        right = int(resolved_signs[index + 1])
        if bool(positive_then_negative):
            if int(left) > 0 and int(right) < 0:
                indices.append(int(index) + 1)
        else:
            if int(left) < 0 and int(right) > 0:
                indices.append(int(index) + 1)
    return [int(value) for value in indices]


def _unique_longest_run_point_indices(signs: Sequence[int], *, direction: int) -> List[int] | None:
    """Return the unique longest monotone run as point indices, or `None` on ties."""

    resolved_signs = [int(value) for value in signs]
    target_sign = 1 if int(direction) > 0 else -1
    runs: List[List[int]] = []
    index = 0
    while int(index) < len(resolved_signs):
        if int(resolved_signs[index]) != int(target_sign):
            index += 1
            continue
        run_start = int(index)
        while int(index) + 1 < len(resolved_signs) and int(resolved_signs[int(index) + 1]) == int(target_sign):
            index += 1
        run_end = int(index) + 1
        runs.append(list(range(int(run_start), int(run_end) + 1)))
        index += 1
    if not runs:
        return None
    max_length = max(len(run) for run in runs)
    winners = [list(run) for run in runs if len(run) == int(max_length)]
    if len(winners) != 1:
        return None
    return [int(value) for value in winners[0]]


def _summarize_trend_variant_from_signs(
    *,
    trend_variant: str,
    signs: Sequence[int],
) -> Tuple[int, List[int], Dict[str, Any]] | None:
    """Resolve one trend-query answer from a sign sequence."""

    resolved_signs = [int(value) for value in signs]
    if str(trend_variant) == "peak_count":
        indices = _turning_point_indices(resolved_signs, positive_then_negative=True)
        return int(len(indices)), [int(value) for value in indices], {"turning_kind": "peak"}
    if str(trend_variant) == "trough_count":
        indices = _turning_point_indices(resolved_signs, positive_then_negative=False)
        return int(len(indices)), [int(value) for value in indices], {"turning_kind": "trough"}
    if str(trend_variant) == "longest_increasing_streak":
        indices = _unique_longest_run_point_indices(resolved_signs, direction=1)
        if indices is None:
            return None
        return (
            int(len(indices)),
            [int(value) for value in indices],
            {"streak_direction": "increasing"},
        )
    if str(trend_variant) == "longest_decreasing_streak":
        indices = _unique_longest_run_point_indices(resolved_signs, direction=-1)
        if indices is None:
            return None
        return (
            int(len(indices)),
            [int(value) for value in indices],
            {"streak_direction": "decreasing"},
        )
    raise ValueError(f"unsupported trend_variant: {trend_variant}")


def _build_values_from_trend_signs(
    *,
    signs: Sequence[int],
    value_min: int,
    value_max: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    """Construct one bounded integer value list that realizes the requested sign pattern."""

    resolved_signs = [int(value) for value in signs]
    prefix_values = [0]
    current = 0
    for sign in resolved_signs:
        current += 2 * int(sign)
        prefix_values.append(int(current))
    min_prefix = min(prefix_values)
    max_prefix = max(prefix_values)
    feasible_bases = [
        int(base)
        for base in range(int(value_min) - int(min_prefix), int(value_max) - int(max_prefix) + 1)
    ]
    if not feasible_bases:
        raise ValueError("no feasible base value for requested trend sign sequence")
    base_value = balanced_choice_from_values(
        feasible_bases,
        params={},
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    return [int(base_value) + int(prefix) for prefix in prefix_values]


def _trend_sign_value_span(signs: Sequence[int]) -> int:
    """Return the numeric span required by the fixed step trend construction."""

    current = 0
    prefix_values = [0]
    for sign in signs:
        current += 2 * int(sign)
        prefix_values.append(int(current))
    return int(max(prefix_values) - min(prefix_values))


def build_trend_structure_dataset_for_variant(
    *,
    trend_variant: str,
    scene_variant: SceneVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
    task_id: str,
) -> Tuple[List[int], int, List[str], Dict[str, Any]]:
    """Construct one ordered labeled-chart dataset for trend-structure queries."""

    del scene_variant
    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    candidate_mark_counts = [
        int(count)
        for count in range(int(mark_count_min), int(mark_count_max) + 1)
        if int(count) >= 3
    ]
    explicit_mark_count = params.get("mark_count")
    if explicit_mark_count is not None:
        candidate_mark_counts = [int(count) for count in candidate_mark_counts if int(count) == int(explicit_mark_count)]
    if not candidate_mark_counts:
        raise ValueError("trend structure tasks require at least three ordered marks")

    feasible_by_answer: Dict[int, List[Tuple[int, Tuple[int, ...], List[int], Dict[str, Any]]]] = {}
    for mark_count in candidate_mark_counts:
        sign_length = int(mark_count) - 1
        for sign_sequence in product((-1, 1), repeat=int(sign_length)):
            if _trend_sign_value_span(sign_sequence) > int(value_max) - int(value_min):
                continue
            resolved = _summarize_trend_variant_from_signs(
                trend_variant=str(trend_variant),
                signs=sign_sequence,
            )
            if resolved is None:
                continue
            answer_value, evidence_indices, metric_extras = resolved
            feasible_by_answer.setdefault(int(answer_value), []).append(
                (
                    int(mark_count),
                    tuple(int(value) for value in sign_sequence),
                    [int(value) for value in evidence_indices],
                    dict(metric_extras),
                )
            )
    if not feasible_by_answer:
        raise ValueError(f"no feasible trend support for variant={trend_variant}")

    if str(trend_variant) in {"peak_count", "trough_count"}:
        default_answer_min, default_answer_max = 0, max(int(value) for value in feasible_by_answer)
    elif str(trend_variant) in {"longest_increasing_streak", "longest_decreasing_streak"}:
        default_answer_min, default_answer_max = 2, max(int(value) for value in feasible_by_answer)
    else:
        raise ValueError(f"unsupported trend_variant: {trend_variant}")

    explicit_min = params.get("target_answer_min")
    explicit_max = params.get("target_answer_max")
    supported_answer_min = int(default_answer_min if explicit_min is None else explicit_min)
    supported_answer_max = int(default_answer_max if explicit_max is None else explicit_max)
    if int(supported_answer_min) > int(supported_answer_max):
        raise ValueError("target_answer_min must be <= target_answer_max")

    answer_candidates = [
        int(answer)
        for answer in sorted(feasible_by_answer.keys())
        if int(supported_answer_min) <= int(answer) <= int(supported_answer_max)
    ]
    if not answer_candidates:
        raise ValueError("no feasible target answers for requested trend answer range")
    if "_sample_cursor" in params:
        target_answer = balanced_choice_from_values(
            answer_candidates,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_answer:{str(trend_variant)}",
        )
    else:
        # Review collection does not pass `_sample_cursor`, so use a second
        # decorrelated deterministic hash stream for answer selection instead
        # of coupling the answer too tightly to the semantic-variant seed path.
        selection_index = abs(int(hash64(int(instance_seed), "trend-target", 16)))
        target_answer = int(answer_candidates[int(selection_index) % len(answer_candidates)])
    candidate_sequences = list(feasible_by_answer[int(target_answer)])
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.sequence:{str(trend_variant)}:{int(target_answer)}",
    )
    mark_count, sign_sequence, evidence_indices, metric_extras = candidate_sequences[
        int(selection_index) % len(candidate_sequences)
    ]

    values = _build_values_from_trend_signs(
        signs=sign_sequence,
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.values:{str(trend_variant)}:{int(target_answer)}",
    )
    labels = list(
        sample_chart_labels(
            count=int(mark_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(trend_variant)}:{int(mark_count)}",
        )
    )
    ordered_evidence_labels = [str(labels[int(index)]) for index in evidence_indices]
    evidence_labels = sorted_labels(ordered_evidence_labels)

    trace_extras: Dict[str, Any] = {
        "value_min": int(value_min),
        "value_max": int(value_max),
        "target_answer_range": [int(supported_answer_min), int(supported_answer_max)],
        "mark_count_range": [int(mark_count_min), int(mark_count_max)],
        "target_answer": int(target_answer),
        "mark_count": int(mark_count),
        "labels": [str(label) for label in labels],
        "values_by_label": {str(label): int(value) for label, value in zip(labels, values)},
        "evidence_labels": list(evidence_labels),
        "ordered_evidence_labels": [str(label) for label in ordered_evidence_labels],
        "evidence_point_indices": [int(value) for value in evidence_indices],
        "step_signs": [int(value) for value in sign_sequence],
        "step_directions": ["up" if int(value) > 0 else "down" for value in sign_sequence],
        **dict(metric_extras),
    }
    return [int(value) for value in values], int(target_answer), evidence_labels, trace_extras


def _resolve_trend_threshold_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    value_min: int,
    value_max: int,
) -> Tuple[int, int]:
    """Resolve inclusive threshold bounds for ordered threshold-crossing charts."""

    axis_span = int(value_max) - int(value_min)
    configured_margin = params.get("threshold_edge_margin", group_default(gen_defaults, "threshold_edge_margin", None))
    if configured_margin is None:
        edge_margin = max(1, min(5, int(axis_span) // 4))
    else:
        edge_margin = max(1, int(configured_margin))
    fallback_min = int(value_min) + int(edge_margin)
    fallback_max = int(value_max) - int(edge_margin)
    value_window_raw = params.get("value_window_enabled", group_default(gen_defaults, "value_window_enabled", False))
    value_window_enabled = bool(value_window_raw)
    if isinstance(value_window_raw, str):
        value_window_enabled = str(value_window_raw).strip().lower() in {"1", "true", "yes", "on"}
    if bool(value_window_enabled) and "threshold_min" not in params and "threshold_max" not in params:
        threshold_min = int(fallback_min)
        threshold_max = int(fallback_max)
    else:
        threshold_min = int(params.get("threshold_min", group_default(gen_defaults, "threshold_min", fallback_min)))
        threshold_max = int(params.get("threshold_max", group_default(gen_defaults, "threshold_max", fallback_max)))
    threshold_min = max(int(threshold_min), int(value_min) + 1)
    threshold_max = min(int(threshold_max), int(value_max) - 1)
    if int(threshold_min) > int(threshold_max):
        raise ValueError("threshold bounds leave no feasible support")
    return int(threshold_min), int(threshold_max)


def _crossing_comparison_for_variant(crossing_variant: str) -> str:
    """Return the strict comparison semantics for one threshold-crossing variant."""

    if str(crossing_variant) in {"first_crosses_above_threshold", "linear_projection_crosses_above"}:
        return "greater_than"
    if str(crossing_variant) in {"first_crosses_below_threshold", "linear_projection_crosses_below"}:
        return "less_than"
    raise ValueError(f"unsupported threshold-crossing variant: {crossing_variant}")


def _build_direct_threshold_crossing_values(
    *,
    crossing_variant: str,
    mark_count: int,
    target_index: int,
    threshold: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
    task_id: str,
) -> List[int]:
    """Build one sequence where the first threshold crossing occurs at target_index."""

    rng = spawn_rng(
        int(instance_seed),
        f"{task_id}.direct_values:{str(crossing_variant)}:{int(mark_count)}:{int(target_index)}:{int(threshold)}",
    )
    comparison = _crossing_comparison_for_variant(str(crossing_variant))
    if str(comparison) == "greater_than":
        low_pool = [int(value) for value in range(int(value_min), int(threshold) + 1)]
        high_pool = [int(value) for value in range(int(threshold) + 1, int(value_max) + 1)]
    else:
        low_pool = [int(value) for value in range(int(value_min), int(threshold))]
        high_pool = [int(value) for value in range(int(threshold), int(value_max) + 1)]
    if not low_pool or not high_pool:
        raise ValueError("threshold leaves no feasible crossing values")

    values: List[int] = []
    if str(comparison) == "greater_than":
        values.extend(_sample_values_from_pool(rng, count=int(target_index), pool=low_pool))
        values.append(int(high_pool[int(rng.randint(0, len(high_pool) - 1))]))
        values.extend(
            _sample_values_from_pool(
                rng,
                count=int(mark_count) - int(target_index) - 1,
                pool=high_pool,
            )
        )
    else:
        values.extend(_sample_values_from_pool(rng, count=int(target_index), pool=high_pool))
        values.append(int(low_pool[int(rng.randint(0, len(low_pool) - 1))]))
        values.extend(
            _sample_values_from_pool(
                rng,
                count=int(mark_count) - int(target_index) - 1,
                pool=low_pool,
            )
        )
    return [int(value) for value in values]


def _projection_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
) -> Tuple[int, int, int, int]:
    """Resolve observed and projected support for projected threshold crossings."""

    observed_min = int(params.get("observed_count_min", group_default(gen_defaults, "observed_count_min", 5)))
    observed_max = int(params.get("observed_count_max", group_default(gen_defaults, "observed_count_max", 8)))
    projection_min = int(params.get("projection_count_min", group_default(gen_defaults, "projection_count_min", 3)))
    projection_max = int(params.get("projection_count_max", group_default(gen_defaults, "projection_count_max", 5)))
    if int(observed_min) > int(observed_max):
        raise ValueError("observed_count_min must be <= observed_count_max")
    if int(projection_min) > int(projection_max):
        raise ValueError("projection_count_min must be <= projection_count_max")
    if int(observed_min) < 2:
        raise ValueError("projection variants require at least two observed marks")
    if int(projection_min) < 1:
        raise ValueError("projection variants require at least one projected mark")
    return int(observed_min), int(observed_max), int(projection_min), int(projection_max)


def _decouple_sample_cursor_after_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Return params whose sampling index advances within each selected query id."""

    explicit_index = params.get("_sample_cursor")
    if explicit_index is None:
        return params
    weights = gen_defaults.get("query_id_weights", {})
    if not isinstance(weights, Mapping):
        return params
    variant_count = 0
    for key, value in weights.items():
        if float(value) <= 0.0:
            continue
        try:
            _crossing_comparison_for_variant(str(key))
        except ValueError:
            continue
        variant_count += 1
    if int(variant_count) <= 1:
        return params
    decoupled = dict(params)
    decoupled["_sample_cursor"] = abs(int(explicit_index)) // int(variant_count)
    return decoupled


def _seed_cycled_choice_from_values(
    values: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Select support values with a compact seed cycle when no sample cursor exists."""

    ordered = [int(value) for value in values]
    if not ordered:
        raise ValueError(f"no feasible values for {namespace}")
    if params.get("_sample_cursor") is not None:
        return balanced_choice_from_values(
            ordered,
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
    return int(ordered[abs(int(instance_seed)) % len(ordered)])


def _build_projected_threshold_crossing_values(
    *,
    crossing_variant: str,
    observed_count: int,
    projection_count: int,
    target_step: int,
    threshold: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
    task_id: str,
) -> Tuple[List[int], int, int]:
    """Build one linear observed series plus projected values crossing at target_step."""

    rng = spawn_rng(
        int(instance_seed),
        f"{task_id}.projected_values:{str(crossing_variant)}:{int(observed_count)}:{int(projection_count)}:{int(target_step)}:{int(threshold)}",
    )
    comparison = _crossing_comparison_for_variant(str(crossing_variant))
    delta_min = 1
    delta_max = max(2, min(12, int(value_max) - int(value_min)))
    feasible_pairs: List[Tuple[int, int, List[int]]] = []
    for delta in range(int(delta_min), int(delta_max) + 1):
        for overshoot in range(1, int(delta) + 1):
            delta = int(delta)
            overshoot = int(overshoot)
            if str(comparison) == "greater_than":
                last_observed = int(threshold) - (int(target_step) * int(delta)) + int(overshoot)
                projected = [int(last_observed) + (int(step) * int(delta)) for step in range(1, int(projection_count) + 1)]
                observed = [
                    int(last_observed) - (int(observed_count) - 1 - int(index)) * int(delta)
                    for index in range(int(observed_count))
                ]
            else:
                last_observed = int(threshold) + (int(target_step) * int(delta)) - int(overshoot)
                projected = [int(last_observed) - (int(step) * int(delta)) for step in range(1, int(projection_count) + 1)]
                observed = [
                    int(last_observed) + (int(observed_count) - 1 - int(index)) * int(delta)
                    for index in range(int(observed_count))
                ]
            values = [int(value) for value in observed] + [int(value) for value in projected]
            if any(int(value) < int(value_min) or int(value) > int(value_max) for value in values):
                continue
            before_projected = projected[: max(0, int(target_step) - 1)]
            if str(comparison) == "greater_than":
                if any(int(value) > int(threshold) for value in values[: int(observed_count)]):
                    continue
                if any(int(value) > int(threshold) for value in before_projected):
                    continue
                if int(projected[int(target_step) - 1]) <= int(threshold):
                    continue
            else:
                if any(int(value) < int(threshold) for value in values[: int(observed_count)]):
                    continue
                if any(int(value) < int(threshold) for value in before_projected):
                    continue
                if int(projected[int(target_step) - 1]) >= int(threshold):
                    continue
            feasible_pairs.append((int(delta), int(overshoot), [int(value) for value in values]))
    if not feasible_pairs:
        raise RuntimeError(f"unable to construct projected threshold crossing for {crossing_variant}")
    delta, overshoot, values = feasible_pairs[int(rng.randint(0, len(feasible_pairs) - 1))]
    return [int(value) for value in values], int(delta), int(overshoot)


def build_trend_threshold_crossing_dataset_for_variant(
    *,
    crossing_variant: str,
    scene_variant: SceneVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
    task_id: str,
) -> Tuple[List[int], str, List[str], Dict[str, Any]]:
    """Construct one ordered labeled-chart dataset for threshold-crossing queries."""

    if str(scene_variant) in PIE_LIKE_SCENE_VARIANTS or str(scene_variant) in {"radar", "scatter", "horizontal_bar"}:
        raise ValueError(f"unsupported threshold-crossing scene_variant: {scene_variant}")

    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
    threshold_min, threshold_max = _resolve_trend_threshold_bounds(
        params,
        gen_defaults=gen_defaults,
        value_min=int(value_min),
        value_max=int(value_max),
    )
    threshold = balanced_choice_from_values(
        [int(value) for value in range(int(threshold_min), int(threshold_max) + 1)],
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.threshold:{str(crossing_variant)}",
    )

    comparison = _crossing_comparison_for_variant(str(crossing_variant))
    is_projection = str(crossing_variant).startswith("linear_projection_")
    if not bool(is_projection):
        mark_count_min, mark_count_max = resolve_mark_count_bounds(
            params,
            gen_defaults=gen_defaults,
            defaults=defaults,
            task_id=task_id,
        )
        feasible_counts = [int(count) for count in range(int(mark_count_min), int(mark_count_max) + 1) if int(count) >= 5]
        mark_count = choose_mark_count(
            feasible_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.mark_count:{str(crossing_variant)}",
        )
        index_min = int(params.get("crossing_index_min", group_default(gen_defaults, "crossing_index_min", 2)))
        index_max = int(params.get("crossing_index_max", group_default(gen_defaults, "crossing_index_max", int(mark_count) - 2)))
        index_min = max(1, int(index_min))
        index_max = min(int(index_max), int(mark_count) - 2)
        if int(index_min) > int(index_max):
            raise ValueError("no feasible crossing index support")
        crossing_index = balanced_choice_from_values(
            [int(value) for value in range(int(index_min), int(index_max) + 1)],
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.crossing_index:{str(crossing_variant)}:{int(mark_count)}",
        )
        labels = list(
            sample_chart_labels(
                count=int(mark_count),
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.labels:{str(crossing_variant)}:{int(mark_count)}",
            )
        )
        values = _build_direct_threshold_crossing_values(
            crossing_variant=str(crossing_variant),
            mark_count=int(mark_count),
            target_index=int(crossing_index),
            threshold=int(threshold),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
            task_id=str(task_id),
        )
        answer_label = str(labels[int(crossing_index)])
        ordered_evidence_labels = [str(label) for label in labels[: int(crossing_index) + 1]]
        trace_extras = {
            "value_min": int(value_min),
            "value_max": int(value_max),
            "threshold": int(threshold),
            "threshold_range": [int(threshold_min), int(threshold_max)],
            "comparison": str(comparison),
            "mark_count_range": [int(mark_count_min), int(mark_count_max)],
            "mark_count": int(mark_count),
            "labels": [str(label) for label in labels],
            "values_by_label": {str(label): int(value) for label, value in zip(labels, values)},
            "answer_label": str(answer_label),
            "answer_index": int(crossing_index),
            "crossing_index": int(crossing_index),
            "crossing_label": str(answer_label),
            "pre_crossing_label": str(labels[int(crossing_index) - 1]) if int(crossing_index) > 0 else "",
            "ordered_evidence_labels": [str(label) for label in ordered_evidence_labels],
            "observed_labels": [str(label) for label in labels],
            "projected_labels": [],
            "point_kind_by_label": {str(label): "observed" for label in labels},
            "projection_delta": None,
            "projection_steps_to_cross": None,
        }
        return [int(value) for value in values], str(answer_label), sorted_labels(ordered_evidence_labels), trace_extras

    observed_min, observed_max, projection_min, projection_max = _projection_count_bounds(
        params,
        gen_defaults=gen_defaults,
    )
    support_params = _decouple_sample_cursor_after_query_id(params, gen_defaults=gen_defaults)
    observed_count = _seed_cycled_choice_from_values(
        [int(value) for value in range(int(observed_min), int(observed_max) + 1)],
        params=support_params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.observed_count:{str(crossing_variant)}",
    )
    projection_count = balanced_choice_from_values(
        [int(value) for value in range(int(projection_min), int(projection_max) + 1)],
        params=support_params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.projection_count:{str(crossing_variant)}",
    )
    step_min = int(params.get("projection_step_min", group_default(gen_defaults, "projection_step_min", 1)))
    step_max = int(params.get("projection_step_max", group_default(gen_defaults, "projection_step_max", int(projection_count))))
    step_min = max(1, int(step_min))
    step_max = min(int(step_max), int(projection_count))
    if int(step_min) > int(step_max):
        raise ValueError("no feasible projection step support")
    target_step = balanced_choice_from_values(
        [int(value) for value in range(int(step_min), int(step_max) + 1)],
        params=support_params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.projection_step:{str(crossing_variant)}:{int(projection_count)}",
    )
    total_count = int(observed_count) + int(projection_count)
    labels = list(
        sample_chart_labels(
            count=int(total_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:projected:{str(crossing_variant)}:{int(total_count)}",
        )
    )
    values, projection_delta, overshoot = _build_projected_threshold_crossing_values(
        crossing_variant=str(crossing_variant),
        observed_count=int(observed_count),
        projection_count=int(projection_count),
        target_step=int(target_step),
        threshold=int(threshold),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )
    answer_index = int(observed_count) + int(target_step) - 1
    answer_label = str(labels[int(answer_index)])
    observed_labels = [str(label) for label in labels[: int(observed_count)]]
    projected_labels = [str(label) for label in labels[int(observed_count):]]
    ordered_evidence_labels = [str(labels[int(observed_count) - 2]), str(labels[int(observed_count) - 1])] + [
        str(label) for label in labels[int(observed_count): int(answer_index) + 1]
    ]
    trace_extras = {
        "value_min": int(value_min),
        "value_max": int(value_max),
        "threshold": int(threshold),
        "threshold_range": [int(threshold_min), int(threshold_max)],
        "comparison": str(comparison),
        "mark_count_range": [int(observed_min) + int(projection_min), int(observed_max) + int(projection_max)],
        "mark_count": int(total_count),
        "observed_count": int(observed_count),
        "observed_count_range": [int(observed_min), int(observed_max)],
        "projection_count": int(projection_count),
        "projection_count_range": [int(projection_min), int(projection_max)],
        "projection_step_range": [int(step_min), int(step_max)],
        "labels": [str(label) for label in labels],
        "values_by_label": {str(label): int(value) for label, value in zip(labels, values)},
        "answer_label": str(answer_label),
        "answer_index": int(answer_index),
        "crossing_index": int(answer_index),
        "crossing_label": str(answer_label),
        "pre_crossing_label": str(labels[int(answer_index) - 1]) if int(answer_index) > 0 else "",
        "ordered_evidence_labels": [str(label) for label in ordered_evidence_labels],
        "observed_labels": [str(label) for label in observed_labels],
        "projected_labels": [str(label) for label in projected_labels],
        "point_kind_by_label": {
            **{str(label): "observed" for label in observed_labels},
            **{str(label): "projected" for label in projected_labels},
        },
        "projection_delta": int(projection_delta),
        "projection_overshoot": int(overshoot),
        "projection_steps_to_cross": int(target_step),
    }
    return [int(value) for value in values], str(answer_label), sorted_labels(ordered_evidence_labels), trace_extras


def _signed_change_support(
    *,
    value_min: int,
    value_max: int,
    min_abs_change: int,
    max_abs_change: int,
) -> List[int]:
    """Return feasible nonzero signed endpoint changes."""

    max_possible = int(value_max) - int(value_min)
    lower = max(1, int(min_abs_change))
    upper = min(int(max_abs_change), int(max_possible))
    if int(lower) > int(upper):
        return []
    return [int(value) for value in range(-int(upper), -int(lower) + 1)] + [
        int(value) for value in range(int(lower), int(upper) + 1)
    ]


def _start_values_for_delta(
    *,
    delta: int,
    value_min: int,
    value_max: int,
) -> List[int]:
    """Return feasible starting values for one signed endpoint delta."""

    return [
        int(value)
        for value in range(int(value_min), int(value_max) + 1)
        if int(value_min) <= int(value) + int(delta) <= int(value_max)
    ]


def _percent_change_support(
    *,
    value_min: int,
    value_max: int,
    percent_min: int,
    percent_max: int,
    percent_step: int,
) -> Dict[int, List[Tuple[int, int]]]:
    """Return feasible integer-percent endpoint transitions."""

    step = max(1, int(percent_step))
    support: Dict[int, List[Tuple[int, int]]] = {}
    for percent in range(int(percent_min), int(percent_max) + 1, int(step)):
        if int(percent) == 0 or int(percent) <= -100:
            continue
        multiplier = int(100) + int(percent)
        transitions: List[Tuple[int, int]] = []
        for start_value in range(int(value_min), int(value_max) + 1):
            numerator = int(start_value) * int(multiplier)
            if int(numerator) % 100 != 0:
                continue
            end_value = int(numerator // 100)
            if int(value_min) <= int(end_value) <= int(value_max) and int(end_value) != int(start_value):
                transitions.append((int(start_value), int(end_value)))
        if transitions:
            support[int(percent)] = list(transitions)
    return support


def build_trend_interval_change_dataset_for_variant(
    *,
    interval_variant: str,
    scene_variant: SceneVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
    task_id: str,
) -> Tuple[List[int], int, List[str], Dict[str, Any]]:
    """Construct one ordered labeled-chart dataset for interval-change value queries."""

    if str(scene_variant) in PIE_LIKE_SCENE_VARIANTS or str(scene_variant) in {"radar", "scatter"}:
        raise ValueError(f"unsupported interval-change scene_variant: {scene_variant}")

    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    feasible_counts = [int(count) for count in range(int(mark_count_min), int(mark_count_max) + 1) if int(count) >= 4]
    mark_count = choose_mark_count(
        feasible_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.mark_count:{str(interval_variant)}",
    )

    gap_min = int(params.get("interval_gap_min", group_default(gen_defaults, "interval_gap_min", 2)))
    gap_max = int(params.get("interval_gap_max", group_default(gen_defaults, "interval_gap_max", 6)))
    gap_min = max(1, int(gap_min))
    gap_max = min(int(gap_max), int(mark_count) - 1)
    if int(gap_min) > int(gap_max):
        raise ValueError("no feasible interval gap support")
    gap = balanced_choice_from_values(
        [int(value) for value in range(int(gap_min), int(gap_max) + 1)],
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.interval_gap:{str(interval_variant)}:{int(mark_count)}",
    )
    start_index = balanced_choice_from_values(
        [int(value) for value in range(0, int(mark_count) - int(gap))],
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.start_index:{str(interval_variant)}:{int(mark_count)}:{int(gap)}",
    )
    end_index = int(start_index) + int(gap)

    min_abs_change = int(params.get("change_abs_min", group_default(gen_defaults, "change_abs_min", 5)))
    max_abs_change = int(params.get("change_abs_max", group_default(gen_defaults, "change_abs_max", 60)))
    if str(interval_variant) == "absolute_change_between_labels":
        signed_support = _signed_change_support(
            value_min=int(value_min),
            value_max=int(value_max),
            min_abs_change=int(min_abs_change),
            max_abs_change=int(max_abs_change),
        )
        abs_support = sorted({abs(int(value)) for value in signed_support})
        target_abs_change = balanced_choice_from_values(
            abs_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.absolute_change",
        )
        direction = balanced_choice_from_values(
            [-1, 1],
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.absolute_change_direction:{int(target_abs_change)}",
        )
        delta = int(direction) * int(target_abs_change)
        start_candidates = _start_values_for_delta(delta=int(delta), value_min=int(value_min), value_max=int(value_max))
        answer_value = int(target_abs_change)
    elif str(interval_variant) == "signed_change_between_labels":
        signed_support = _signed_change_support(
            value_min=int(value_min),
            value_max=int(value_max),
            min_abs_change=int(min_abs_change),
            max_abs_change=int(max_abs_change),
        )
        delta = balanced_choice_from_values(
            signed_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.signed_change",
        )
        start_candidates = _start_values_for_delta(delta=int(delta), value_min=int(value_min), value_max=int(value_max))
        answer_value = int(delta)
    elif str(interval_variant) == "percent_change_between_labels":
        percent_support = _percent_change_support(
            value_min=int(value_min),
            value_max=int(value_max),
            percent_min=int(params.get("percent_change_min", group_default(gen_defaults, "percent_change_min", -75))),
            percent_max=int(params.get("percent_change_max", group_default(gen_defaults, "percent_change_max", 150))),
            percent_step=int(params.get("percent_change_step", group_default(gen_defaults, "percent_change_step", 5))),
        )
        percent = balanced_choice_from_values(
            sorted(percent_support.keys()),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.percent_change",
        )
        transition_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.percent_transition:{int(percent)}",
        )
        start_value, end_value = percent_support[int(percent)][int(transition_index) % len(percent_support[int(percent)])]
        delta = int(end_value) - int(start_value)
        start_candidates = [int(start_value)]
        answer_value = int(percent)
    elif str(interval_variant) == "average_rate_over_interval":
        rate_candidates = _signed_change_support(
            value_min=int(value_min),
            value_max=int(value_max),
            min_abs_change=int(params.get("average_rate_abs_min", group_default(gen_defaults, "average_rate_abs_min", 2))),
            max_abs_change=int(params.get("average_rate_abs_max", group_default(gen_defaults, "average_rate_abs_max", 12))),
        )
        feasible_gaps_by_rate = {
            int(rate): [
                int(candidate_gap)
                for candidate_gap in range(int(gap_min), int(gap_max) + 1)
                if _start_values_for_delta(
                    delta=int(rate) * int(candidate_gap),
                    value_min=int(value_min),
                    value_max=int(value_max),
                )
            ]
            for rate in rate_candidates
        }
        rate_support = [
            int(rate)
            for rate, feasible_gaps in feasible_gaps_by_rate.items()
            if feasible_gaps
        ]
        rate = balanced_choice_from_values(
            rate_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.average_rate",
        )
        gap = balanced_choice_from_values(
            feasible_gaps_by_rate[int(rate)],
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.average_rate_gap:{int(rate)}:{int(mark_count)}",
        )
        start_index = balanced_choice_from_values(
            [int(value) for value in range(0, int(mark_count) - int(gap))],
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.start_index:{str(interval_variant)}:{int(mark_count)}:{int(gap)}",
        )
        end_index = int(start_index) + int(gap)
        delta = int(rate) * int(gap)
        start_candidates = _start_values_for_delta(delta=int(delta), value_min=int(value_min), value_max=int(value_max))
        answer_value = int(rate)
    else:
        raise ValueError(f"unsupported interval-change variant: {interval_variant}")

    if not start_candidates:
        raise ValueError("no feasible start values for interval-change query")
    start_value = balanced_choice_from_values(
        start_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.start_value:{str(interval_variant)}:{int(delta)}",
    )
    end_value = int(start_value) + int(delta)

    rng = spawn_rng(
        int(instance_seed),
        f"{task_id}.values:{str(interval_variant)}:{int(mark_count)}:{int(start_index)}:{int(end_index)}:{int(start_value)}:{int(end_value)}",
    )
    values = [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(mark_count))]
    values[int(start_index)] = int(start_value)
    values[int(end_index)] = int(end_value)
    labels = list(
        sample_chart_labels(
            count=int(mark_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(interval_variant)}:{int(mark_count)}",
        )
    )
    ordered_evidence_labels = [str(labels[index]) for index in range(int(start_index), int(end_index) + 1)]
    evidence_labels = list(ordered_evidence_labels)
    trace_extras: Dict[str, Any] = {
        "value_min": int(value_min),
        "value_max": int(value_max),
        "mark_count_range": [int(mark_count_min), int(mark_count_max)],
        "mark_count": int(mark_count),
        "interval_gap": int(gap),
        "interval_gap_range": [int(gap_min), int(gap_max)],
        "start_index": int(start_index),
        "end_index": int(end_index),
        "start_label": str(labels[int(start_index)]),
        "end_label": str(labels[int(end_index)]),
        "start_value": int(start_value),
        "end_value": int(end_value),
        "delta": int(delta),
        "answer_value": int(answer_value),
        "labels": [str(label) for label in labels],
        "values_by_label": {str(label): int(value) for label, value in zip(labels, values)},
        "evidence_labels": list(evidence_labels),
        "ordered_evidence_labels": [str(label) for label in ordered_evidence_labels],
        "evidence_point_indices": [int(index) for index in range(int(start_index), int(end_index) + 1)],
        "change_abs_range": [int(min_abs_change), int(max_abs_change)],
        "percent_change_range": [
            int(params.get("percent_change_min", group_default(gen_defaults, "percent_change_min", -75))),
            int(params.get("percent_change_max", group_default(gen_defaults, "percent_change_max", 150))),
        ],
        "percent_change_step": int(params.get("percent_change_step", group_default(gen_defaults, "percent_change_step", 5))),
        "average_rate_abs_range": [
            int(params.get("average_rate_abs_min", group_default(gen_defaults, "average_rate_abs_min", 2))),
            int(params.get("average_rate_abs_max", group_default(gen_defaults, "average_rate_abs_max", 12))),
        ],
    }
    return [int(value) for value in values], int(answer_value), evidence_labels, trace_extras


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
    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
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
    labels = list(
        sample_chart_labels(
            count=int(mark_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(readout_variant)}:{int(mark_count)}",
        )
    )
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
    instance_seed: int | None = None,
) -> ChartRenderParams:
    """Resolve one chart render-parameter block."""

    def _selection_index(key: str) -> int:
        seed = 0 if instance_seed is None else int(instance_seed)
        return abs(int(hash64(int(seed), f"chart_render:{str(key)}", 91421)))

    def _resolve_int(key: str, fallback: int, *, minimum: int = 1) -> int:
        if params.get(str(key)) is not None:
            return max(int(minimum), int(params[str(key)]))
        low_raw = params.get(f"{str(key)}_min", group_default(render_defaults, f"{str(key)}_min", None))
        high_raw = params.get(f"{str(key)}_max", group_default(render_defaults, f"{str(key)}_max", None))
        if low_raw is not None or high_raw is not None:
            default_value = int(group_default(render_defaults, str(key), int(fallback)))
            low = int(default_value if low_raw is None else low_raw)
            high = int(default_value if high_raw is None else high_raw)
            if int(low) > int(high):
                raise ValueError(f"{str(key)}_min must be <= {str(key)}_max")
            return max(int(minimum), int(low) + (_selection_index(str(key)) % (int(high) - int(low) + 1)))
        return max(int(minimum), int(group_default(render_defaults, str(key), int(fallback))))

    def _resolve_float(key: str, fallback: float, *, steps: int = 15) -> float:
        if params.get(str(key)) is not None:
            return float(params[str(key)])
        low_raw = params.get(f"{str(key)}_min", group_default(render_defaults, f"{str(key)}_min", None))
        high_raw = params.get(f"{str(key)}_max", group_default(render_defaults, f"{str(key)}_max", None))
        if low_raw is not None or high_raw is not None:
            default_value = float(group_default(render_defaults, str(key), float(fallback)))
            low = float(default_value if low_raw is None else low_raw)
            high = float(default_value if high_raw is None else high_raw)
            if float(low) > float(high):
                raise ValueError(f"{str(key)}_min must be <= {str(key)}_max")
            step_count = max(1, int(steps))
            offset = _selection_index(str(key)) % (int(step_count) + 1)
            return float(low + ((high - low) * (float(offset) / float(step_count))))
        return float(group_default(render_defaults, str(key), float(fallback)))

    def _resolve_rgb(key: str, fallback: Sequence[int]) -> Sequence[int]:
        if params.get(str(key)) is not None:
            return params[str(key)]
        options = params.get(f"{str(key)}_options", group_default(render_defaults, f"{str(key)}_options", None))
        if isinstance(options, Sequence) and options and not isinstance(options, (str, bytes)):
            selected = options[_selection_index(str(key)) % len(options)]
            return selected
        return group_default(render_defaults, str(key), list(fallback))

    def _resolve_bool(key: str, fallback: bool) -> bool:
        value = params.get(str(key), group_default(render_defaults, str(key), bool(fallback)))
        if isinstance(value, str):
            return str(value).strip().lower() in {"1", "true", "yes", "on", "always"}
        return bool(value)

    def _resolve_str(key: str, fallback: str) -> str:
        return str(params.get(str(key), group_default(render_defaults, str(key), str(fallback))))

    def _resolve_choice(key: str, fallback: str) -> str:
        explicit = params.get(str(key), group_default(render_defaults, str(key), None))
        if explicit is not None:
            return str(explicit)
        options = params.get(f"{str(key)}_options", group_default(render_defaults, f"{str(key)}_options", None))
        if isinstance(options, Sequence) and options and not isinstance(options, (str, bytes)):
            return str(options[_selection_index(str(key)) % len(options)])
        return str(fallback)

    def _resolve_float_value(key: str, fallback: float) -> float:
        return float(params.get(str(key), group_default(render_defaults, str(key), float(fallback))))

    def _resolve_style() -> str:
        explicit = params.get("guide_line_style", group_default(render_defaults, "guide_line_style", None))
        if explicit is not None:
            return str(explicit)
        styles = params.get("guide_line_styles", group_default(render_defaults, "guide_line_styles", ("dashed", "dotted")))
        if isinstance(styles, Sequence) and styles and not isinstance(styles, (str, bytes)):
            return str(styles[_selection_index("guide_line_style") % len(styles)])
        return "dashed"

    def _resolve_guide_mode() -> str:
        mode = _resolve_str("guide_line_mode", "off").strip().lower()
        if mode != "variant":
            return str(mode)
        probability = max(0.0, min(1.0, _resolve_float_value("guide_line_prob", 0.5)))
        draw_value = (_selection_index("guide_line_enabled") % 10_000) / 10_000.0
        return "always" if float(draw_value) < float(probability) else "off"

    margin_left = int(params.get("plot_margin_left_px", group_default(render_defaults, "plot_margin_left_px", defaults.plot_margin_left_px)))
    margin_right = int(params.get("plot_margin_right_px", group_default(render_defaults, "plot_margin_right_px", defaults.plot_margin_right_px)))
    margin_top = int(params.get("plot_margin_top_px", group_default(render_defaults, "plot_margin_top_px", defaults.plot_margin_top_px)))
    margin_bottom = int(params.get("plot_margin_bottom_px", group_default(render_defaults, "plot_margin_bottom_px", defaults.plot_margin_bottom_px)))
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=render_defaults,
        instance_seed=instance_seed,
        namespace="charts.labeled.layout",
    )

    resolved = {
        "canvas_width": int(params.get("canvas_width", group_default(render_defaults, "canvas_width", defaults.canvas_width))),
        "canvas_height": int(params.get("canvas_height", group_default(render_defaults, "canvas_height", defaults.canvas_height))),
        "plot_margin_left_px": int(margin_left),
        "plot_margin_right_px": int(margin_right),
        "plot_margin_top_px": int(margin_top),
        "plot_margin_bottom_px": int(margin_bottom),
        "axis_line_width_px": _resolve_int("axis_line_width_px", defaults.axis_line_width_px),
        "grid_line_width_px": _resolve_int("grid_line_width_px", defaults.grid_line_width_px),
        "tick_length_px": int(params.get("tick_length_px", group_default(render_defaults, "tick_length_px", defaults.tick_length_px))),
        "label_font_size_px": int(params.get("label_font_size_px", group_default(render_defaults, "label_font_size_px", defaults.label_font_size_px))),
        "tick_font_size_px": int(params.get("tick_font_size_px", group_default(render_defaults, "tick_font_size_px", defaults.tick_font_size_px))),
        "label_stroke_width_px": _resolve_int("label_stroke_width_px", defaults.label_stroke_width_px),
        "mark_outline_width_px": _resolve_int("mark_outline_width_px", defaults.mark_outline_width_px),
        "line_width_px": _resolve_int("line_width_px", defaults.line_width_px),
        "point_radius_px": _resolve_int("point_radius_px", defaults.point_radius_px),
        "bar_width_fraction": _resolve_float("bar_width_fraction", defaults.bar_width_fraction),
        "axis_color_rgb": _resolve_rgb("axis_color_rgb", [74, 78, 86]),
        "grid_color_rgb": _resolve_rgb("grid_color_rgb", [224, 227, 232]),
        "mark_fill_rgb": params.get("mark_fill_rgb", group_default(render_defaults, "mark_fill_rgb", [86, 138, 214])),
        "mark_outline_rgb": params.get("mark_outline_rgb", group_default(render_defaults, "mark_outline_rgb", [50, 76, 116])),
        "text_color_rgb": _resolve_rgb("text_color_rgb", [38, 41, 48]),
        "text_stroke_rgb": _resolve_rgb("text_stroke_rgb", [255, 255, 255]),
        "plot_fill_rgb": _resolve_rgb("plot_fill_rgb", [255, 255, 255]),
        "value_axis_window_enabled": _resolve_bool("value_axis_window_enabled", False),
        "value_axis_span_min": int(params.get("value_axis_span_min", group_default(render_defaults, "value_axis_span_min", 10))),
        "value_axis_span_max": int(params.get("value_axis_span_max", group_default(render_defaults, "value_axis_span_max", 25))),
        "value_axis_hard_max": int(params.get("value_axis_hard_max", group_default(render_defaults, "value_axis_hard_max", 99))),
        "value_axis_major_tick_step": int(params.get("value_axis_major_tick_step", group_default(render_defaults, "value_axis_major_tick_step", 5))),
        "value_axis_minor_tick_step": int(params.get("value_axis_minor_tick_step", group_default(render_defaults, "value_axis_minor_tick_step", 1))),
        "value_axis_allow_nonzero_min": _resolve_bool("value_axis_allow_nonzero_min", True),
        "guide_line_mode": _resolve_guide_mode(),
        "guide_line_prob": _resolve_float_value("guide_line_prob", 0.0),
        "guide_line_style": _resolve_style(),
        "guide_line_width_px": int(params.get("guide_line_width_px", group_default(render_defaults, "guide_line_width_px", 1))),
        "guide_line_color_rgb": _resolve_rgb("guide_line_color_rgb", [150, 156, 166]),
        "_guide_style_seed": _selection_index("guide_line_style"),
        "layout_jitter_dx_px": int(layout_jitter_meta.get("dx_px", 0)),
        "layout_jitter_dy_px": int(layout_jitter_meta.get("dy_px", 0)),
        "layout_jitter_meta": dict(layout_jitter_meta),
        "violin_mode_line_style": _resolve_choice("violin_mode_line_style", "full"),
        "violin_fill_style": _resolve_choice("violin_fill_style", "solid"),
        "violin_width_scale": _resolve_float("violin_width_scale", 1.0),
        "violin_smoothing_scale": _resolve_float("violin_smoothing_scale", 1.0),
        "violin_palette_mode": _resolve_choice("violin_palette_mode", "single"),
        "violin_palette_offset": _resolve_int("violin_palette_offset", 0, minimum=0),
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
    "build_trend_interval_change_dataset_for_variant",
    "build_trend_threshold_crossing_dataset_for_variant",
    "build_trend_structure_dataset_for_variant",
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
