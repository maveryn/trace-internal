"""Shared generation/render helpers for multiseries chart task families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.color_distance import sample_color_palette_with_distance_constraints
from ....shared.config_defaults import group_default, resolve_required_int_bounds
from ....shared.named_colors import darken_color
from ...shared.chart_scene import MultiSeriesChartMarkSpec
from ...shared.label_assets import resolve_chart_entity_labels
from ...shared.labeled_chart_common import (
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

    if int(count) <= 0:
        raise ValueError("series count must be positive")
    rng = spawn_rng(int(instance_seed), "charts.multiseries.series_labels")
    resolved = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=4,
        allow_spaces=False,
    )
    return tuple(str(value).title() for value in resolved.labels)


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


def projected_category_annotation(
    rendered_scene,
    category_labels: Sequence[str],
) -> Dict[str, Any]:
    """Project one ordered category-label annotation list into pixel-space chart annotation."""

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


def projected_multiseries_mark_annotation(
    rendered_scene,
    category_labels: Sequence[str],
    series_labels: Sequence[str] | Mapping[str, Sequence[str]],
) -> Dict[str, Any]:
    """Project category/series mark witnesses into pixel-space annotation."""

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


__all__ = [
    "MultiseriesChartDefaults",
    "SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS",
    "build_multiseries_mark_specs",
    "projected_category_annotation",
    "projected_multiseries_mark_annotation",
    "resolve_category_count_bounds",
    "resolve_multiseries_chart_colors",
    "resolve_series_count_bounds",
    "sample_series_labels",
]
