"""Core helpers for labeled chart task families."""

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
from .label_assets import resolve_chart_axis_labels

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

def projected_mark_annotation(
    rendered_scene: RenderedChartScene,
    labels: Sequence[str],
) -> Dict[str, Any]:
    """Project one ordered label list into reusable pixel-space chart annotation.

    Review overlays and public pixel annotation need pixel-space geometry. This
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
    """Sample one randomized short label list for chart marks.

    Most labeled chart scenes use this helper for visible axis/category labels.
    Keep labels short for dense chart layouts while allowing occasional
    semantic buckets such as ordered temporal labels.
    """

    label_rng = spawn_rng(int(instance_seed), str(namespace))
    resolved = resolve_chart_axis_labels(
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
    enabled = bool(params.get(str(balance_flag_key), group_default(gen_defaults, str(balance_flag_key), True)))
    overridden = params.get(str(explicit_key)) is not None or params.get(str(weights_key)) is not None
    positive_probabilities = [float(value) for value in probabilities.values() if float(value) > 0.0]
    uniform_probabilities = bool(positive_probabilities) and max(positive_probabilities) - min(positive_probabilities) <= 1e-9
    if (
        params.get("_sample_cursor") is not None
        and bool(enabled)
        and (not bool(overridden))
        and bool(uniform_probabilities)
    ):
        positive_variants = {
            str(key)
            for key, value in probabilities.items()
            if float(value) > 0.0
        }
        values = [str(item) for item in supported_variants if str(item) in positive_variants]
        if values:
            offset = abs(int(hash64(0, f"{task_id}:{axis_namespace}", 27183)))
            variant = str(values[(abs(int(params["_sample_cursor"])) + int(offset)) % len(values)])
        else:
            variant = str(selected_variant)
    else:
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

__all__ = [
    'StatisticKind',
    'SceneVariant',
    'SUPPORTED_LABELED_CHART_SCENE_VARIANTS',
    'PIE_LIKE_SCENE_VARIANTS',
    'LabeledChartDefaults',
    'is_pie_like_scene_variant',
    'sorted_labels',
    'projected_mark_annotation',
    'resolve_value_bounds',
    'resolve_mark_count_bounds',
    'apply_scene_variant_mark_count_cap',
    'resolve_target_answer_range',
    'balanced_choice_from_values',
    'hashed_choice_from_values',
    'shuffle_values',
    'sample_chart_labels',
    'normalize_rgb',
    'build_chart_mark_specs',
    'resolve_chart_mark_colors',
    'max_symmetric_delta',
    'cyclic_pair_deltas',
    'resolve_chart_axis_variant',
]
