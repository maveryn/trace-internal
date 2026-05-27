"""Shared generation/render helpers for multiseries chart task families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.color_distance import sample_color_palette_with_distance_constraints
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.name_assets import load_short_name_manifest
from ...shared.named_colors import darken_color
from .chart_scene import MultiSeriesChartMarkSpec
from .labeled_chart_common import (
    LabeledChartDefaults,
    balanced_choice_from_values,
    resolve_value_bounds,
    sample_composition_with_sum,
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
    category_count_max: int = 15
    series_count_min: int = 2
    series_count_max: int = 4
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

    pool = load_short_name_manifest(_SERIES_NAME_MANIFEST)
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


def projected_multiseries_mark_evidence(
    rendered_scene,
    category_labels: Sequence[str],
    series_labels: Sequence[str] | Mapping[str, Sequence[str]],
) -> Dict[str, Any]:
    """Project category/series mark witnesses into pixel-space evidence."""

    requested_categories = [str(label) for label in category_labels]
    if isinstance(series_labels, Mapping):
        requested_series_by_category = {
            str(category): [str(series_label) for series_label in labels]
            for category, labels in series_labels.items()
        }
    else:
        shared_series = [str(series_label) for series_label in series_labels]
        requested_series_by_category = {
            str(category): list(shared_series)
            for category in requested_categories
        }

    mark_by_key: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for mark_trace in rendered_scene.mark_traces:
        category_label = str(mark_trace.get("category_label", ""))
        series_label = str(mark_trace.get("series_label", ""))
        mark_by_key[(category_label, series_label)] = mark_trace

    pixel_point_map: Dict[str, List[float]] = {}
    pixel_point_set: List[List[float]] = []
    bbox_set: List[List[float]] = []
    for category_label in requested_categories:
        for series_label in requested_series_by_category.get(str(category_label), []):
            mark_trace = mark_by_key.get((str(category_label), str(series_label)))
            if mark_trace is None:
                continue
            center = mark_trace.get("mark_center_px")
            bbox = mark_trace.get("mark_bbox_px")
            key = f"{str(category_label)}:{str(series_label)}"
            if isinstance(center, list) and len(center) == 2:
                point = [float(center[0]), float(center[1])]
                pixel_point_map[str(key)] = list(point)
                pixel_point_set.append(list(point))
            if isinstance(bbox, list) and len(bbox) == 4:
                bbox_set.append([float(value) for value in bbox])

    return {
        "pixel_point_map": pixel_point_map,
        "pixel_point_set": pixel_point_set,
        "bbox_set": bbox_set,
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
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], int, List[str], Dict[str, Any]]:
    """Construct one multiseries comparison-count dataset."""

    if str(query_id) not in {"series_a_gt_b_count", "series_a_lt_b_count"}:
        raise ValueError(f"unsupported multiseries query_id: {query_id}")

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
        namespace=f"{task_id}.target_answer:{str(query_id)}",
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
        namespace=f"{task_id}.category_count:{str(query_id)}:{int(target_answer)}",
    )
    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(query_id)}",
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
        if str(query_id) == "series_a_gt_b_count":
            left_value = int(high_value if relation_holds else low_value)
            right_value = int(low_value if relation_holds else high_value)
        else:
            left_value = int(low_value if relation_holds else high_value)
            right_value = int(high_value if relation_holds else low_value)
        category_values: Dict[str, int] = {
            str(left_series): int(left_value),
            str(right_series): int(right_value),
        }
        distractor_series_labels = [
            str(series_label)
            for series_label in series_labels
            if str(series_label) not in {str(left_series), str(right_series)}
        ]
        for distractor_series, distractor_value in zip(distractor_series_labels, remaining_values):
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
        "comparison": "greater_than" if str(query_id) == "series_a_gt_b_count" else "less_than",
    }
    return values_by_category, int(target_answer), evidence_labels, trace_extras


def _sample_score_window(
    rng,
    *,
    count: int,
    max_score: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> List[int]:
    """Sample a unique, usually tight derived-score support."""

    score_min = int(params.get("derived_score_min", group_default(gen_defaults, "derived_score_min", 1)))
    score_max = int(params.get("derived_score_max", group_default(gen_defaults, "derived_score_max", int(max_score))))
    if int(score_min) < 1:
        raise ValueError("derived_score_min must be positive")
    if int(score_max) > int(max_score):
        score_max = int(max_score)
    if int(score_min) > int(score_max):
        raise ValueError("derived_score_min must be <= derived_score_max")
    score_support_size = int(score_max) - int(score_min) + 1
    if int(count) > int(score_support_size):
        raise ValueError("delta-extremum task requires enough distinct derived scores")
    extra_min = int(params.get("score_spread_extra_min", group_default(gen_defaults, "score_spread_extra_min", 0)))
    extra_max = int(params.get("score_spread_extra_max", group_default(gen_defaults, "score_spread_extra_max", 4)))
    if int(extra_min) < 0 or int(extra_max) < 0:
        raise ValueError("score_spread_extra bounds must be non-negative")
    if int(extra_min) > int(extra_max):
        raise ValueError("score_spread_extra_min must be <= score_spread_extra_max")
    feasible_extra_max = min(int(extra_max), int(score_support_size) - int(count))
    feasible_extra_min = min(int(extra_min), int(feasible_extra_max))
    extra = rng.randint(int(feasible_extra_min), int(feasible_extra_max))
    window_size = int(count) + int(extra)
    start = rng.randint(int(score_min), int(score_max) - int(window_size) + 1)
    window = [int(value) for value in range(int(start), int(start) + int(window_size))]
    return [int(value) for value in rng.sample(window, int(count))]


def _sample_ratio_percent_window(
    rng,
    *,
    count: int,
    feasible_scores: Sequence[int],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> List[int]:
    """Sample a unique, usually tight ratio-percent score support."""

    support = sorted({int(score) for score in feasible_scores})
    if int(count) > len(support):
        raise ValueError("ratio-extremum task requires enough distinct feasible ratio scores")
    extra_min = int(params.get("ratio_score_spread_extra_min", group_default(gen_defaults, "ratio_score_spread_extra_min", 0)))
    extra_max = int(params.get("ratio_score_spread_extra_max", group_default(gen_defaults, "ratio_score_spread_extra_max", 6)))
    if int(extra_min) < 0 or int(extra_max) < 0:
        raise ValueError("ratio_score_spread_extra bounds must be non-negative")
    if int(extra_min) > int(extra_max):
        raise ValueError("ratio_score_spread_extra_min must be <= ratio_score_spread_extra_max")
    feasible_extra_max = min(int(extra_max), len(support) - int(count))
    feasible_extra_min = min(int(extra_min), int(feasible_extra_max))
    extra = rng.randint(int(feasible_extra_min), int(feasible_extra_max))
    window_size = int(count) + int(extra)
    start = rng.randint(0, len(support) - int(window_size))
    window = support[int(start) : int(start) + int(window_size)]
    return [int(value) for value in rng.sample(window, int(count))]


def _share_feasible_totals(
    *,
    score_percent: int,
    series_count: int,
    value_min: int,
    value_max: int,
    total_min: int,
    total_max: int,
) -> List[int]:
    """Return category totals that make an exact target-series share feasible."""

    totals: List[int] = []
    for total in range(int(total_min), int(total_max) + 1):
        if (int(score_percent) * int(total)) % 100 != 0:
            continue
        target_value = (int(score_percent) * int(total)) // 100
        remaining_total = int(total) - int(target_value)
        if not (int(value_min) <= int(target_value) <= int(value_max)):
            continue
        if remaining_total < (int(series_count) - 1) * int(value_min):
            continue
        if remaining_total > (int(series_count) - 1) * int(value_max):
            continue
        totals.append(int(total))
    return totals


def _pair_ratio_feasible_denominators(
    *,
    score_percent: int,
    value_min: int,
    value_max: int,
) -> List[int]:
    """Return denominator values that make an exact numerator/denominator percent feasible."""

    denominators: List[int] = []
    for denominator in range(int(value_min), int(value_max) + 1):
        if (int(score_percent) * int(denominator)) % 100 != 0:
            continue
        numerator = (int(score_percent) * int(denominator)) // 100
        if int(value_min) <= int(numerator) <= int(value_max):
            denominators.append(int(denominator))
    return denominators


def _sample_queried_pair_for_score(
    rng,
    *,
    score: int,
    value_min: int,
    value_max: int,
    direction: str,
) -> Tuple[int, int]:
    """Sample two queried-series values whose derived score is `score`."""

    if int(score) <= 0:
        raise ValueError("derived score must be positive")
    if int(value_min) + int(score) > int(value_max):
        raise ValueError("derived score does not fit within the value bounds")
    low_value = rng.randint(int(value_min), int(value_max) - int(score))
    high_value = int(low_value) + int(score)
    if str(direction) == "increase":
        return int(low_value), int(high_value)
    if str(direction) == "decrease":
        return int(high_value), int(low_value)
    if str(direction) == "absolute":
        if rng.randrange(2) == 0:
            return int(low_value), int(high_value)
        return int(high_value), int(low_value)
    raise ValueError(f"unsupported delta direction: {direction}")


def build_delta_extremum_label_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], str, List[int], Dict[str, Any]]:
    """Construct one multiseries derived-delta extremum label dataset."""

    supported_variants = {
        "ranked_largest_increase",
        "ranked_largest_decrease",
        "ranked_largest_gap",
        "ranked_smallest_gap",
    }
    if str(query_id) not in supported_variants:
        raise ValueError(f"unsupported multiseries delta query_id: {query_id}")

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
    if int(series_count_min) < 2:
        raise ValueError("multiseries delta task requires at least two series")

    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) <= (int(value_max) - int(value_min))
    ]
    if not feasible_category_counts:
        raise ValueError("category count range exceeds available unique delta support")
    category_count = balanced_choice_from_values(
        feasible_category_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:{str(query_id)}",
    )
    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(query_id)}",
    )

    rank_min = int(params.get("rank_min", group_default(gen_defaults, "rank_min", 1)))
    rank_max = int(params.get("rank_max", group_default(gen_defaults, "rank_max", 3)))
    if int(rank_min) < 1:
        raise ValueError("rank_min must be >= 1")
    if int(rank_min) > int(rank_max):
        raise ValueError("rank_min must be <= rank_max")
    rank_candidates = [
        int(rank)
        for rank in range(int(rank_min), int(rank_max) + 1)
        if 1 <= int(rank) <= int(category_count)
    ]
    if not rank_candidates:
        raise ValueError("delta-extremum task requires a feasible rank")
    answer_rank = balanced_choice_from_values(
        rank_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.answer_rank:{str(query_id)}",
    )

    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_pair")
    pair_candidates = [
        (str(series_labels[left_index]), str(series_labels[right_index]))
        for left_index in range(int(series_count))
        for right_index in range(int(left_index) + 1, int(series_count))
    ]
    left_series, right_series = pair_candidates[query_rng.randrange(len(pair_candidates))]

    score_rng = spawn_rng(int(instance_seed), f"{task_id}.derived_scores:{str(query_id)}")
    max_score = int(value_max) - int(value_min)
    scores = _sample_score_window(
        score_rng,
        count=int(category_count),
        max_score=int(max_score),
        params=params,
        gen_defaults=gen_defaults,
    )
    assignment_rng = spawn_rng(int(instance_seed), f"{task_id}.score_assignment:{str(query_id)}")
    assignment_rng.shuffle(scores)
    scores_by_category = {
        str(category_label): int(score)
        for category_label, score in zip(category_labels, scores)
    }
    if str(query_id) == "ranked_smallest_gap":
        sorted_score_items = sorted(
            scores_by_category.items(),
            key=lambda item: (int(item[1]), str(item[0])),
        )
        rank_order = "ascending"
    else:
        sorted_score_items = sorted(
            scores_by_category.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
        rank_order = "descending"
    answer_label = str(sorted_score_items[int(answer_rank) - 1][0])
    answer_score = int(scores_by_category[str(answer_label)])

    if str(query_id) == "ranked_largest_increase":
        direction = "increase"
        derived_metric = "increase"
    elif str(query_id) == "ranked_largest_decrease":
        direction = "decrease"
        derived_metric = "decrease"
    else:
        direction = "absolute"
        derived_metric = "absolute_gap"

    value_rng = spawn_rng(int(instance_seed), f"{task_id}.values:{str(query_id)}")
    values_by_category: Dict[str, Dict[str, int]] = {}
    derived_values_by_category: Dict[str, int] = {}
    evidence_values: List[int] = []
    for category_label in category_labels:
        score = int(scores_by_category[str(category_label)])
        left_value, right_value = _sample_queried_pair_for_score(
            value_rng,
            score=int(score),
            value_min=int(value_min),
            value_max=int(value_max),
            direction=str(direction),
        )
        category_values: Dict[str, int] = {
            str(left_series): int(left_value),
            str(right_series): int(right_value),
        }
        for series_label in series_labels:
            if str(series_label) in category_values:
                continue
            category_values[str(series_label)] = int(value_rng.randint(int(value_min), int(value_max)))
        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }
        if str(derived_metric) == "increase":
            derived_value = int(right_value) - int(left_value)
        elif str(derived_metric) == "decrease":
            derived_value = int(left_value) - int(right_value)
        else:
            derived_value = abs(int(right_value) - int(left_value))
        derived_values_by_category[str(category_label)] = int(derived_value)
        if str(category_label) == str(answer_label):
            evidence_values = [int(left_value), int(right_value), int(derived_value)]

    trace_extras: Dict[str, Any] = {
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
        "value_range": [int(value_min), int(value_max)],
        "answer_label": str(answer_label),
        "answer_rank": int(answer_rank),
        "answer_score": int(answer_score),
        "evidence_values": [int(value) for value in evidence_values],
        "derived_metric": str(derived_metric),
        "direction": str(direction),
        "rank_order": str(rank_order),
        "ranked_category_labels": [str(label) for label, _score in sorted_score_items],
        "derived_values_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(derived_values_by_category.items())
        },
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
    }
    return values_by_category, str(answer_label), [int(value) for value in evidence_values], trace_extras


def build_ratio_extremum_label_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], str, List[int], Dict[str, Any]]:
    """Construct one multiseries ratio/share extremum label dataset."""

    supported_variants = {
        "ranked_largest_series_share",
        "ranked_smallest_series_share",
        "ranked_largest_pair_ratio",
        "ranked_smallest_pair_ratio",
    }
    if str(query_id) not in supported_variants:
        raise ValueError(f"unsupported multiseries ratio query_id: {query_id}")

    is_share_variant = str(query_id) in {
        "ranked_largest_series_share",
        "ranked_smallest_series_share",
    }
    is_smallest_variant = str(query_id) in {
        "ranked_smallest_series_share",
        "ranked_smallest_pair_ratio",
    }

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
    if int(series_count_min) < 2:
        raise ValueError("multiseries ratio task requires at least two series")

    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(query_id)}",
    )

    if bool(is_share_variant):
        score_min = int(params.get("share_percent_min", group_default(gen_defaults, "share_percent_min", 10)))
        score_max = int(params.get("share_percent_max", group_default(gen_defaults, "share_percent_max", 75)))
        value_window_raw = params.get("value_window_enabled", group_default(gen_defaults, "value_window_enabled", False))
        value_window_enabled = bool(value_window_raw)
        if isinstance(value_window_raw, str):
            value_window_enabled = str(value_window_raw).strip().lower() in {"1", "true", "yes", "on"}
        if bool(value_window_enabled) and "category_total_min" not in params and "category_total_max" not in params:
            total_min = int(series_count) * int(value_min)
            total_max = int(series_count) * int(value_max)
        else:
            total_min = int(params.get("category_total_min", group_default(gen_defaults, "category_total_min", 35)))
            total_max = int(params.get("category_total_max", group_default(gen_defaults, "category_total_max", 160)))
        if int(total_min) > int(total_max):
            raise ValueError("category_total_min must be <= category_total_max")
        feasible_scores = [
            int(score)
            for score in range(int(score_min), int(score_max) + 1)
            if _share_feasible_totals(
                score_percent=int(score),
                series_count=int(series_count),
                value_min=int(value_min),
                value_max=int(value_max),
                total_min=int(total_min),
                total_max=int(total_max),
            )
        ]
        score_range = [int(score_min), int(score_max)]
        category_total_range = [int(total_min), int(total_max)]
    else:
        score_min = int(params.get("pair_ratio_percent_min", group_default(gen_defaults, "pair_ratio_percent_min", 40)))
        score_max = int(params.get("pair_ratio_percent_max", group_default(gen_defaults, "pair_ratio_percent_max", 260)))
        feasible_scores = [
            int(score)
            for score in range(int(score_min), int(score_max) + 1)
            if _pair_ratio_feasible_denominators(
                score_percent=int(score),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        ]
        score_range = [int(score_min), int(score_max)]
        category_total_range = None
    if int(score_min) < 1:
        raise ValueError("ratio percent minimum must be positive")
    if int(score_min) > int(score_max):
        raise ValueError("ratio percent minimum must be <= maximum")

    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) <= len(feasible_scores)
    ]
    if not feasible_category_counts:
        raise ValueError("category count range exceeds feasible ratio-percent support")
    category_count = balanced_choice_from_values(
        feasible_category_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:{str(query_id)}:{int(series_count)}",
    )

    rank_min = int(params.get("rank_min", group_default(gen_defaults, "rank_min", 1)))
    rank_max = int(params.get("rank_max", group_default(gen_defaults, "rank_max", 3)))
    if int(rank_min) < 1:
        raise ValueError("rank_min must be >= 1")
    if int(rank_min) > int(rank_max):
        raise ValueError("rank_min must be <= rank_max")
    rank_candidates = [
        int(rank)
        for rank in range(int(rank_min), int(rank_max) + 1)
        if 1 <= int(rank) <= int(category_count)
    ]
    if not rank_candidates:
        raise ValueError("ratio-extremum task requires a feasible rank")
    answer_rank = balanced_choice_from_values(
        rank_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.answer_rank:{str(query_id)}",
    )

    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_series:{str(query_id)}")
    if bool(is_share_variant):
        target_series = str(series_labels[query_rng.randrange(len(series_labels))])
        numerator_series = str(target_series)
        denominator_series = "category_total"
        queried_series_labels = [str(target_series)]
    else:
        pair_candidates = [
            (str(series_labels[numerator_index]), str(series_labels[denominator_index]))
            for numerator_index in range(int(series_count))
            for denominator_index in range(int(series_count))
            if int(numerator_index) != int(denominator_index)
        ]
        numerator_series, denominator_series = pair_candidates[query_rng.randrange(len(pair_candidates))]
        target_series = ""
        queried_series_labels = [str(numerator_series), str(denominator_series)]

    score_rng = spawn_rng(int(instance_seed), f"{task_id}.ratio_scores:{str(query_id)}")
    scores = _sample_ratio_percent_window(
        score_rng,
        count=int(category_count),
        feasible_scores=feasible_scores,
        params=params,
        gen_defaults=gen_defaults,
    )
    assignment_rng = spawn_rng(int(instance_seed), f"{task_id}.ratio_score_assignment:{str(query_id)}")
    assignment_rng.shuffle(scores)
    scores_by_category = {
        str(category_label): int(score)
        for category_label, score in zip(category_labels, scores)
    }
    if bool(is_smallest_variant):
        sorted_score_items = sorted(scores_by_category.items(), key=lambda item: (int(item[1]), str(item[0])))
        rank_order = "ascending"
    else:
        sorted_score_items = sorted(scores_by_category.items(), key=lambda item: (-int(item[1]), str(item[0])))
        rank_order = "descending"
    answer_label = str(sorted_score_items[int(answer_rank) - 1][0])
    answer_score = int(scores_by_category[str(answer_label)])

    value_rng = spawn_rng(int(instance_seed), f"{task_id}.values:{str(query_id)}")
    values_by_category: Dict[str, Dict[str, int]] = {}
    denominator_values_by_category: Dict[str, int] = {}
    ratio_percent_by_category: Dict[str, int] = {}
    evidence_values: List[int] = []
    for category_label in category_labels:
        score = int(scores_by_category[str(category_label)])
        if bool(is_share_variant):
            totals = _share_feasible_totals(
                score_percent=int(score),
                series_count=int(series_count),
                value_min=int(value_min),
                value_max=int(value_max),
                total_min=int(category_total_range[0] if category_total_range is not None else 0),
                total_max=int(category_total_range[1] if category_total_range is not None else 0),
            )
            category_total = int(totals[value_rng.randrange(len(totals))])
            numerator_value = (int(score) * int(category_total)) // 100
            remaining_total = int(category_total) - int(numerator_value)
            distractor_series_labels = [
                str(series_label)
                for series_label in series_labels
                if str(series_label) != str(target_series)
            ]
            distractor_values = sample_composition_with_sum(
                value_rng,
                target_sum=int(remaining_total),
                count=len(distractor_series_labels),
                value_min=int(value_min),
                value_max=int(value_max),
            )
            value_rng.shuffle(distractor_values)
            category_values = {
                str(target_series): int(numerator_value),
                **{
                    str(series_label): int(value)
                    for series_label, value in zip(distractor_series_labels, distractor_values)
                },
            }
            denominator_value = int(category_total)
        else:
            denominators = _pair_ratio_feasible_denominators(
                score_percent=int(score),
                value_min=int(value_min),
                value_max=int(value_max),
            )
            denominator_value = int(denominators[value_rng.randrange(len(denominators))])
            numerator_value = (int(score) * int(denominator_value)) // 100
            category_values = {
                str(numerator_series): int(numerator_value),
                str(denominator_series): int(denominator_value),
            }
            for series_label in series_labels:
                if str(series_label) in category_values:
                    continue
                category_values[str(series_label)] = int(value_rng.randint(int(value_min), int(value_max)))

        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }
        denominator_values_by_category[str(category_label)] = int(denominator_value)
        ratio_percent_by_category[str(category_label)] = int(score)
        if str(category_label) == str(answer_label):
            evidence_values = [int(numerator_value), int(denominator_value), int(score)]

    trace_extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "series_count": int(series_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_labels": [str(label) for label in category_labels],
        "series_labels": [str(label) for label in series_labels],
        "queried_series_labels": [str(label) for label in queried_series_labels],
        "target_series_label": str(target_series),
        "numerator_series_label": str(numerator_series),
        "denominator_series_label": str(denominator_series),
        "value_min": int(value_min),
        "value_max": int(value_max),
        "value_range": [int(value_min), int(value_max)],
        "score_percent_range": list(score_range),
        "category_total_range": list(category_total_range) if category_total_range is not None else None,
        "answer_label": str(answer_label),
        "answer_rank": int(answer_rank),
        "answer_score": int(answer_score),
        "answer_score_percent": int(answer_score),
        "evidence_values": [int(value) for value in evidence_values],
        "derived_metric": "series_share_percent" if bool(is_share_variant) else "pair_ratio_percent",
        "calculation_scope": "category_total_share" if bool(is_share_variant) else "queried_pair_ratio",
        "rank_order": str(rank_order),
        "ranked_category_labels": [str(label) for label, _score in sorted_score_items],
        "denominator_values_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(denominator_values_by_category.items())
        },
        "ratio_percent_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(ratio_percent_by_category.items())
        },
        "derived_values_by_category": {
            str(category_label): int(value)
            for category_label, value in sorted(ratio_percent_by_category.items())
        },
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
    }
    return values_by_category, str(answer_label), [int(value) for value in evidence_values], trace_extras


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

    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
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
    evidence_values: List[int] = []
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
            evidence_values = [int(value) for value in series_values]

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
        "evidence_values": [int(value) for value in evidence_values],
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
    return values_by_category, str(answer_label), [int(value) for value in evidence_values], trace_extras


def _sample_absolute_gap_pair(
    rng,
    *,
    gap: int,
    value_min: int,
    value_max: int,
) -> Tuple[int, int]:
    """Sample two values with the requested absolute gap."""

    left_value, right_value = _sample_queried_pair_for_score(
        rng,
        score=int(gap),
        value_min=int(value_min),
        value_max=int(value_max),
        direction="absolute",
    )
    return int(left_value), int(right_value)


def _sample_relation_pair(
    rng,
    *,
    relation_holds: bool,
    comparison: str,
    value_min: int,
    value_max: int,
) -> Tuple[int, int]:
    """Sample two values where the requested strict relation has the requested truth value."""

    max_gap = max(1, int(value_max) - int(value_min))
    relation_gap = int(rng.randint(1, int(max_gap)))
    low_value = int(rng.randint(int(value_min), int(value_max) - int(relation_gap)))
    high_value = int(low_value) + int(relation_gap)
    wants_greater = str(comparison) == "greater_than"
    if bool(relation_holds) == bool(wants_greater):
        return int(high_value), int(low_value)
    return int(low_value), int(high_value)


def _conditional_gap_target_gaps(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    task_id: str,
    filter_count: int,
    gap_min: int,
    gap_max: int,
    extremum_direction: str | None,
) -> Tuple[List[int], int, List[int], Dict[str, Any]]:
    """Construct filtered target gaps and the numeric answer for one conditional-gap variant."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.conditional_gap_values:{str(query_id)}")
    if str(query_id) == "conditional_gap_sum_value":
        answer_min = int(params.get("sum_answer_min", group_default(gen_defaults, "sum_answer_min", int(filter_count) * int(gap_min))))
        answer_max = int(params.get("sum_answer_max", group_default(gen_defaults, "sum_answer_max", int(filter_count) * int(gap_max))))
        feasible = [
            int(value)
            for value in range(max(int(answer_min), int(filter_count) * int(gap_min)), min(int(answer_max), int(filter_count) * int(gap_max)) + 1)
        ]
        answer_value = balanced_choice_from_values(
            feasible,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.answer_value:{str(query_id)}:{int(filter_count)}",
        )
        gaps = sample_composition_with_sum(
            rng,
            target_sum=int(answer_value),
            count=int(filter_count),
            value_min=int(gap_min),
            value_max=int(gap_max),
        )
        return [int(value) for value in gaps], int(answer_value), [min(feasible), max(feasible)], {}

    if str(query_id) == "conditional_gap_mean_value":
        answer_min = int(params.get("mean_answer_min", group_default(gen_defaults, "mean_answer_min", int(gap_min))))
        answer_max = int(params.get("mean_answer_max", group_default(gen_defaults, "mean_answer_max", int(gap_max))))
        feasible = [
            int(value)
            for value in range(max(int(answer_min), int(gap_min)), min(int(answer_max), int(gap_max)) + 1)
        ]
        answer_value = balanced_choice_from_values(
            feasible,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.answer_value:{str(query_id)}",
        )
        gaps = sample_composition_with_sum(
            rng,
            target_sum=int(answer_value) * int(filter_count),
            count=int(filter_count),
            value_min=int(gap_min),
            value_max=int(gap_max),
        )
        return [int(value) for value in gaps], int(answer_value), [min(feasible), max(feasible)], {}

    if str(query_id) == "conditional_gap_range_value":
        answer_min = int(params.get("range_answer_min", group_default(gen_defaults, "range_answer_min", 1)))
        answer_max = int(params.get("range_answer_max", group_default(gen_defaults, "range_answer_max", int(gap_max) - int(gap_min))))
        feasible = [
            int(value)
            for value in range(max(1, int(answer_min)), min(int(answer_max), int(gap_max) - int(gap_min)) + 1)
        ]
        answer_value = balanced_choice_from_values(
            feasible,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.answer_value:{str(query_id)}",
        )
        low_gap = int(rng.randint(int(gap_min), int(gap_max) - int(answer_value)))
        high_gap = int(low_gap) + int(answer_value)
        gaps = [int(low_gap), int(high_gap)]
        while len(gaps) < int(filter_count):
            gaps.append(int(rng.randint(int(low_gap), int(high_gap))))
        rng.shuffle(gaps)
        return [int(value) for value in gaps], int(answer_value), [min(feasible), max(feasible)], {}

    if str(query_id) == "conditional_gap_extremum_value":
        direction = str(extremum_direction or "largest")
        answer_min = int(params.get("extremum_answer_min", group_default(gen_defaults, "extremum_answer_min", int(gap_min))))
        answer_max = int(params.get("extremum_answer_max", group_default(gen_defaults, "extremum_answer_max", int(gap_max))))
        if direction == "smallest":
            feasible = [
                int(value)
                for value in range(max(int(answer_min), int(gap_min)), min(int(answer_max), int(gap_max)) + 1)
                if int(gap_max) - int(value) >= int(filter_count) - 1
            ]
            answer_value = balanced_choice_from_values(
                feasible,
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.answer_value:{str(query_id)}:{direction}:{int(filter_count)}",
            )
            distractor_pool = [int(value) for value in range(int(answer_value) + 1, int(gap_max) + 1)]
        else:
            feasible = [
                int(value)
                for value in range(max(int(answer_min), int(gap_min)), min(int(answer_max), int(gap_max)) + 1)
                if int(value) - int(gap_min) >= int(filter_count) - 1
            ]
            answer_value = balanced_choice_from_values(
                feasible,
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.answer_value:{str(query_id)}:{direction}:{int(filter_count)}",
            )
            distractor_pool = [int(value) for value in range(int(gap_min), int(answer_value))]
        gaps = [int(answer_value)] + [int(value) for value in rng.sample(distractor_pool, int(filter_count) - 1)]
        rng.shuffle(gaps)
        return [int(value) for value in gaps], int(answer_value), [min(feasible), max(feasible)], {"extremum_direction": direction}

    raise ValueError(f"unsupported multiseries conditional-gap query_id: {query_id}")


def build_conditional_gap_value_dataset(
    *,
    query_id: str,
    condition_comparison: str,
    extremum_direction: str | None,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MultiseriesChartDefaults,
    task_id: str,
) -> Tuple[Dict[str, Dict[str, int]], int, List[str], Dict[str, List[str]], Dict[str, Any]]:
    """Construct one filtered multiseries gap-arithmetic dataset."""

    supported_variants = {
        "conditional_gap_sum_value",
        "conditional_gap_mean_value",
        "conditional_gap_range_value",
        "conditional_gap_extremum_value",
    }
    if str(query_id) not in supported_variants:
        raise ValueError(f"unsupported multiseries conditional-gap query_id: {query_id}")
    if str(condition_comparison) not in {"greater_than", "less_than"}:
        raise ValueError(f"unsupported condition_comparison: {condition_comparison}")

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
    series_count_min = max(4, int(series_count_min))
    if int(series_count_min) > int(series_count_max):
        raise ValueError("conditional-gap multiseries task requires at least four series")

    feasible_category_counts = [
        int(count)
        for count in range(int(category_count_min), int(category_count_max) + 1)
        if int(count) >= 4
    ]
    category_count = balanced_choice_from_values(
        feasible_category_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:{str(query_id)}",
    )
    feasible_series_counts = [int(count) for count in range(int(series_count_min), int(series_count_max) + 1)]
    series_count = balanced_choice_from_values(
        feasible_series_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:{str(query_id)}",
    )

    filter_min = int(params.get("filtered_category_count_min", group_default(gen_defaults, "filtered_category_count_min", 3)))
    filter_max = int(params.get("filtered_category_count_max", group_default(gen_defaults, "filtered_category_count_max", 6)))
    filter_min = max(2, int(filter_min))
    filter_max = max(int(filter_min), int(filter_max))
    feasible_filter_counts = [
        int(count)
        for count in range(int(filter_min), int(filter_max) + 1)
        if 2 <= int(count) < int(category_count)
    ]
    filter_count = balanced_choice_from_values(
        feasible_filter_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.filtered_category_count:{str(query_id)}:{int(category_count)}",
    )

    gap_min = int(params.get("target_gap_min", group_default(gen_defaults, "target_gap_min", 2)))
    gap_max = int(params.get("target_gap_max", group_default(gen_defaults, "target_gap_max", 18)))
    gap_min = max(1, int(gap_min))
    gap_max = min(int(gap_max), int(value_max) - int(value_min))
    if int(gap_min) > int(gap_max):
        raise ValueError("target gap bounds do not fit in the sampled value window")

    filtered_gaps, answer_value, answer_range, extra_trace = _conditional_gap_target_gaps(
        query_id=str(query_id),
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        task_id=task_id,
        filter_count=int(filter_count),
        gap_min=int(gap_min),
        gap_max=int(gap_max),
        extremum_direction=extremum_direction,
    )

    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_series")
    query_series = list(series_labels)
    query_rng.shuffle(query_series)
    condition_left_series, condition_right_series, target_left_series, target_right_series = [
        str(label) for label in query_series[:4]
    ]

    category_indices = list(range(int(category_count)))
    filter_rng = spawn_rng(int(instance_seed), f"{task_id}.filtered_categories:{str(query_id)}")
    filter_rng.shuffle(category_indices)
    filtered_indices = set(category_indices[: int(filter_count)])
    filtered_gap_by_index = {
        int(category_index): int(gap)
        for category_index, gap in zip(sorted(filtered_indices), filtered_gaps)
    }

    value_rng = spawn_rng(int(instance_seed), f"{task_id}.values:{str(query_id)}")
    values_by_category: Dict[str, Dict[str, int]] = {}
    target_gap_by_category: Dict[str, int] = {}
    condition_holds_by_category: Dict[str, bool] = {}
    for category_index, category_label in enumerate(category_labels):
        relation_holds = bool(int(category_index) in filtered_indices)
        condition_left_value, condition_right_value = _sample_relation_pair(
            value_rng,
            relation_holds=bool(relation_holds),
            comparison=str(condition_comparison),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        target_gap = int(
            filtered_gap_by_index[int(category_index)]
            if bool(relation_holds)
            else value_rng.randint(int(gap_min), int(gap_max))
        )
        target_left_value, target_right_value = _sample_absolute_gap_pair(
            value_rng,
            gap=int(target_gap),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        category_values: Dict[str, int] = {
            str(condition_left_series): int(condition_left_value),
            str(condition_right_series): int(condition_right_value),
            str(target_left_series): int(target_left_value),
            str(target_right_series): int(target_right_value),
        }
        for series_label in series_labels:
            if str(series_label) in category_values:
                continue
            category_values[str(series_label)] = int(value_rng.randint(int(value_min), int(value_max)))
        values_by_category[str(category_label)] = {
            str(series_label): int(category_values[str(series_label)])
            for series_label in series_labels
        }
        target_gap_by_category[str(category_label)] = int(target_gap)
        condition_holds_by_category[str(category_label)] = bool(relation_holds)

    filtered_category_labels = [
        str(label)
        for index, label in enumerate(category_labels)
        if int(index) in filtered_indices
    ]
    filtered_gap_values = [int(target_gap_by_category[str(label)]) for label in filtered_category_labels]
    if str(query_id) == "conditional_gap_sum_value":
        realized_answer = int(sum(filtered_gap_values))
    elif str(query_id) == "conditional_gap_mean_value":
        realized_answer = int(sum(filtered_gap_values) // len(filtered_gap_values))
    elif str(query_id) == "conditional_gap_range_value":
        realized_answer = int(max(filtered_gap_values) - min(filtered_gap_values))
    elif str(extra_trace.get("extremum_direction", extremum_direction or "largest")) == "smallest":
        realized_answer = int(min(filtered_gap_values))
    else:
        realized_answer = int(max(filtered_gap_values))
    if int(realized_answer) != int(answer_value):
        raise RuntimeError("conditional-gap answer drifted from constructed target")

    evidence_series = [
        str(condition_left_series),
        str(condition_right_series),
        str(target_left_series),
        str(target_right_series),
    ]
    evidence_series_by_category = {
        str(label): list(evidence_series)
        for label in filtered_category_labels
    }

    trace_extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "series_count": int(series_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "filtered_category_count": int(filter_count),
        "filtered_category_count_range": [int(filter_min), int(filter_max)],
        "category_labels": [str(label) for label in category_labels],
        "series_labels": [str(label) for label in series_labels],
        "condition_series_labels": [str(condition_left_series), str(condition_right_series)],
        "target_series_labels": [str(target_left_series), str(target_right_series)],
        "queried_series_labels": list(evidence_series),
        "condition_left_series_label": str(condition_left_series),
        "condition_right_series_label": str(condition_right_series),
        "target_left_series_label": str(target_left_series),
        "target_right_series_label": str(target_right_series),
        "condition_comparison": str(condition_comparison),
        "value_min": int(value_min),
        "value_max": int(value_max),
        "value_range": [int(value_min), int(value_max)],
        "target_gap_range": [int(gap_min), int(gap_max)],
        "answer_value": int(answer_value),
        "answer_range": [int(answer_range[0]), int(answer_range[1])],
        "filtered_category_labels": [str(label) for label in filtered_category_labels],
        "filtered_gap_values": [int(value) for value in filtered_gap_values],
        "target_gap_by_category": {
            str(label): int(value)
            for label, value in sorted(target_gap_by_category.items())
        },
        "condition_holds_by_category": {
            str(label): bool(value)
            for label, value in sorted(condition_holds_by_category.items())
        },
        "evidence_series_labels_by_category": dict(evidence_series_by_category),
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in sorted(series_values.items())
            }
            for category_label, series_values in values_by_category.items()
        },
        **dict(extra_trace),
    }
    return (
        values_by_category,
        int(answer_value),
        [str(label) for label in filtered_category_labels],
        evidence_series_by_category,
        trace_extras,
    )


__all__ = [
    "MultiseriesChartDefaults",
    "SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS",
    "build_category_total_extremum_label_dataset",
    "build_conditional_gap_value_dataset",
    "build_delta_extremum_label_dataset",
    "build_multiseries_mark_specs",
    "build_pairwise_comparison_count_dataset",
    "build_ratio_extremum_label_dataset",
    "projected_category_evidence",
    "resolve_category_count_bounds",
    "resolve_multiseries_chart_colors",
    "resolve_series_count_bounds",
    "sample_series_labels",
]
