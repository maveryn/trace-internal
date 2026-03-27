"""Shared generation/render helpers for multiseries chart task families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.color_distance import sample_color_palette_with_distance_constraints
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.named_colors import darken_color
from .chart_scene import MultiSeriesChartMarkSpec
from .legend_name_assets import load_legend_name_manifest
from .labeled_chart_common import (
    LabeledChartDefaults,
    balanced_choice_from_values,
    resolve_value_bounds,
    sample_chart_labels,
    sorted_labels,
)


SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS: Tuple[str, ...] = (
    "grouped_bar",
    "grouped_horizontal_bar",
    "multi_line",
    "grouped_lollipop",
)

_SERIES_NAME_MANIFEST = "series_legend_names_random_name_2to4.txt"


@dataclass(frozen=True)
class MultiseriesChartDefaults(LabeledChartDefaults):
    """Stable fallback defaults shared by multiseries chart tasks."""

    category_count_min: int = 5
    category_count_max: int = 10
    series_count_min: int = 2
    series_count_max: int = 3
    target_answer_min: int = 0
    target_answer_max: int = 8


def resolve_category_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive category-count bounds."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=int(defaults.category_count_min),
        fallback_max=int(defaults.category_count_max),
        context=f"generation defaults for {task_id}",
    )


def resolve_series_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive series-count bounds."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="series_count_min",
        max_key="series_count_max",
        fallback_min=int(defaults.series_count_min),
        fallback_max=int(defaults.series_count_max),
        context=f"generation defaults for {task_id}",
    )


def sample_series_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    """Sample one randomized series-label tuple."""

    pool = load_legend_name_manifest(_SERIES_NAME_MANIFEST)
    if int(count) <= 0:
        raise ValueError("series count must be positive")
    if int(count) > len(pool):
        raise ValueError("series count exceeds the supported label pool")
    rng = spawn_rng(int(instance_seed), "charts.multiseries.series_labels")
    candidates = list(pool)
    rng.shuffle(candidates)
    return tuple(str(value) for value in candidates[: int(count)])


def resolve_multiseries_chart_colors(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    instance_seed: int,
    series_count: int,
) -> Dict[str, Any]:
    """Resolve one per-series color palette for multiseries charts."""

    color_rng = spawn_rng(int(instance_seed), "charts.multiseries.colors")
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
    fill_palette = sample_color_palette_with_distance_constraints(
        color_rng,
        palette_size=int(series_count),
        channel_min=int(channel_min),
        channel_max=int(channel_max),
        anchor_colors=((255, 255, 255), (248, 248, 248)),
        min_distance=float(min_distance),
        distance_space=str(distance_space),
    )
    outline_palette = [darken_color(fill_rgb, factor=0.55) for fill_rgb in fill_palette]
    return {
        "sampling_policy": "random_rgb_palette",
        "series_fill_palette_rgb": [[int(channel) for channel in fill_rgb] for fill_rgb in fill_palette],
        "series_outline_palette_rgb": [[int(channel) for channel in outline_rgb] for outline_rgb in outline_palette],
        "mark_color_min_distance": float(min_distance),
        "mark_color_distance_space": str(distance_space),
    }


def build_multiseries_mark_specs(
    *,
    category_labels: Sequence[str],
    series_labels: Sequence[str],
    values_by_category: Mapping[str, Mapping[str, int]],
    mark_style: Mapping[str, Any],
) -> List[MultiSeriesChartMarkSpec]:
    """Build chart-mark specs for one multiseries chart."""

    fill_palette = [tuple(int(channel) for channel in value) for value in mark_style["series_fill_palette_rgb"]]
    outline_palette = [tuple(int(channel) for channel in value) for value in mark_style["series_outline_palette_rgb"]]
    if len(fill_palette) != len(series_labels) or len(outline_palette) != len(series_labels):
        raise ValueError("multiseries charts require one color per series")

    specs: List[MultiSeriesChartMarkSpec] = []
    for category_rank, category_label in enumerate(category_labels):
        values_for_category = values_by_category[str(category_label)]
        for series_rank, series_label in enumerate(series_labels):
            specs.append(
                MultiSeriesChartMarkSpec(
                    category_label=str(category_label),
                    series_label=str(series_label),
                    category_rank=int(category_rank),
                    series_rank=int(series_rank),
                    value=int(values_for_category[str(series_label)]),
                    fill_rgb=fill_palette[int(series_rank)],
                    outline_rgb=outline_palette[int(series_rank)],
                )
            )
    return specs


def projected_category_evidence(
    rendered_scene,
    category_labels: Sequence[str],
) -> Dict[str, Any]:
    """Project one ordered category-label evidence list into pixel-space chart evidence."""

    requested = [str(label) for label in category_labels]
    bbox_by_category: Dict[str, List[float]] = {}
    point_by_category: Dict[str, List[float]] = {}
    for mark_trace in rendered_scene.mark_traces:
        category_label = str(mark_trace.get("category_label", ""))
        if category_label in bbox_by_category:
            continue
        group_bbox = mark_trace.get("category_group_bbox_px")
        label_center = mark_trace.get("category_label_center_px")
        if isinstance(group_bbox, list) and len(group_bbox) == 4:
            bbox_by_category[category_label] = [float(value) for value in group_bbox]
        if isinstance(label_center, list) and len(label_center) == 2:
            point_by_category[category_label] = [float(value) for value in label_center]
    return {
        "pixel_point_map": {
            str(label): list(point_by_category[str(label)])
            for label in requested
            if str(label) in point_by_category
        },
        "pixel_point_set": [
            list(point_by_category[str(label)])
            for label in requested
            if str(label) in point_by_category
        ],
        "bbox_set": [
            list(bbox_by_category[str(label)])
            for label in requested
            if str(label) in bbox_by_category
        ],
    }


def _sample_distinct_values(
    rng,
    *,
    count: int,
    value_min: int,
    value_max: int,
) -> List[int]:
    """Sample one distinct integer value list within the inclusive bounds."""

    universe = [int(value) for value in range(int(value_min), int(value_max) + 1)]
    if int(count) > len(universe):
        raise ValueError("distinct value sampling requires a larger value range")
    return [int(value) for value in rng.sample(universe, int(count))]


def build_pairwise_comparison_count_dataset(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], int, List[str], Dict[str, Any]]:
    """Construct one multiseries comparison-count dataset."""

    if str(task_variant) not in {"series_a_gt_b_count", "series_a_lt_b_count"}:
        raise ValueError(f"unsupported multiseries task_variant: {task_variant}")

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
    if int(series_count_min) < 2:
        raise ValueError("multiseries comparison requires at least two series")

    answer_min = int(params.get("target_answer_min", group_default(gen_defaults, "target_answer_min", defaults.target_answer_min)))
    answer_max = int(params.get("target_answer_max", group_default(gen_defaults, "target_answer_max", defaults.target_answer_max)))
    if int(answer_min) > int(answer_max):
        raise ValueError("target_answer_min must be <= target_answer_max")

    answer_candidates = [
        int(value)
        for value in range(int(answer_min), int(answer_max) + 1)
        if int(value) <= int(category_count_max)
    ]
    target_answer = balanced_choice_from_values(
        answer_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:{str(task_variant)}",
    )
    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) >= int(target_answer)
    ]
    category_count = balanced_choice_from_values(
        feasible_category_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:{str(task_variant)}:{int(target_answer)}",
    )
    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(task_variant)}",
    )

    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_pair")
    pair_candidates = [
        (str(series_labels[left_index]), str(series_labels[right_index]))
        for left_index in range(int(series_count))
        for right_index in range(int(left_index) + 1, int(series_count))
    ]
    query_pair = pair_candidates[query_rng.randrange(len(pair_candidates))]
    left_series, right_series = (str(query_pair[0]), str(query_pair[1]))

    category_indices = list(range(int(category_count)))
    satisfy_rng = spawn_rng(int(instance_seed), f"{task_id}.satisfying_categories")
    satisfy_rng.shuffle(category_indices)
    satisfying_indices = set(category_indices[: int(target_answer)])

    values_rng = spawn_rng(int(instance_seed), f"{task_id}.values")
    values_by_category: Dict[str, Dict[str, int]] = {}
    evidence_labels: List[str] = []
    for category_index, category_label in enumerate(category_labels):
        sampled_values = sorted(
            _sample_distinct_values(
                values_rng,
                count=int(series_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        )
        low_value = int(sampled_values[0])
        high_value = int(sampled_values[-1])
        remaining_values = [int(value) for value in sampled_values[1:-1]]
        relation_holds = bool(int(category_index) in satisfying_indices)
        if str(task_variant) == "series_a_gt_b_count":
            left_value = int(high_value if relation_holds else low_value)
            right_value = int(low_value if relation_holds else high_value)
        else:
            left_value = int(low_value if relation_holds else high_value)
            right_value = int(high_value if relation_holds else low_value)
        category_values: Dict[str, int] = {
            str(left_series): int(left_value),
            str(right_series): int(right_value),
        }
        if len(series_labels) == 3:
            distractor_series = next(
                str(series_label)
                for series_label in series_labels
                if str(series_label) not in {str(left_series), str(right_series)}
            )
            distractor_value = int(remaining_values[0]) if remaining_values else int(low_value)
            category_values[str(distractor_series)] = int(distractor_value)
        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }
        if relation_holds:
            evidence_labels.append(str(category_label))

    evidence_labels = sorted_labels(evidence_labels)
    trace_extras: Dict[str, Any] = {
        "target_answer": int(target_answer),
        "target_answer_range": [int(answer_min), int(answer_max)],
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "series_count": int(series_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_labels": [str(label) for label in category_labels],
        "series_labels": [str(label) for label in series_labels],
        "queried_series_labels": [str(left_series), str(right_series)],
        "left_series_label": str(left_series),
        "right_series_label": str(right_series),
        "value_min": int(value_min),
        "value_max": int(value_max),
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
        "comparison": "greater_than" if str(task_variant) == "series_a_gt_b_count" else "less_than",
    }
    return values_by_category, int(target_answer), evidence_labels, trace_extras


__all__ = [
    "MultiseriesChartDefaults",
    "SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS",
    "build_multiseries_mark_specs",
    "build_pairwise_comparison_count_dataset",
    "projected_category_evidence",
    "resolve_category_count_bounds",
    "resolve_multiseries_chart_colors",
    "resolve_series_count_bounds",
    "sample_series_labels",
]
