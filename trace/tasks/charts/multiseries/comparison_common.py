"""Shared constants and small helpers for multiseries comparison tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ...shared.font_assets import sample_font_family
from ..shared.complexity import normalize_int_with_bounds, resolve_chart_complexity_weights
from ..shared.multiseries_chart_common import MultiseriesChartDefaults
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_multiseries_comparison_query_base"
_CHANGE_QUERY_ID = "ranked_change_extremum"
_RATIO_QUERY_ID = "ranked_ratio_extremum"
_PAIRWISE_QUERY_ID = "series_comparison_count"
_EQUALITY_QUERY_ID = "pair_equality_label"
_SERIES_RANK_QUERY_ID = "series_rank_at_category_label"
_CONDITIONAL_AGGREGATE_QUERY_ID = "conditional_gap_aggregate_value"
_CONDITIONAL_SUM_QUERY_ID = "conditional_gap_sum_value"
_CONDITIONAL_MEAN_QUERY_ID = "conditional_gap_mean_value"
_CONDITIONAL_RANGE_QUERY_ID = "conditional_gap_range_value"
_CONDITIONAL_EXTREMUM_QUERY_ID = "conditional_gap_extremum_value"
_CATEGORY_TOTAL_QUERY_ID = "category_total_extremum_label"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    _CHANGE_QUERY_ID,
    _RATIO_QUERY_ID,
    _PAIRWISE_QUERY_ID,
    _EQUALITY_QUERY_ID,
    _SERIES_RANK_QUERY_ID,
    _CONDITIONAL_AGGREGATE_QUERY_ID,
    _CONDITIONAL_EXTREMUM_QUERY_ID,
    _CATEGORY_TOTAL_QUERY_ID,
)
_SUPPORTED_CHANGE_MEASURES: Tuple[str, ...] = (
    "directional_change",
    "absolute_gap",
)
_SUPPORTED_RATIO_MEASURES: Tuple[str, ...] = (
    "series_share",
    "pair_ratio",
)
_SUPPORTED_CHANGE_DIRECTIONS: Tuple[str, ...] = (
    "increase",
    "decrease",
)
_SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = (
    "largest",
    "smallest",
)
_SUPPORTED_COMPARISONS: Tuple[str, ...] = (
    "greater_than",
    "less_than",
)
_SUPPORTED_CONDITIONAL_GAP_AGGREGATE_KINDS: Tuple[str, ...] = (
    "sum",
    "mean",
    "range",
)
_CONDITIONAL_GAP_AGGREGATE_KIND_TO_INTERNAL: Dict[str, str] = {
    "sum": _CONDITIONAL_SUM_QUERY_ID,
    "mean": _CONDITIONAL_MEAN_QUERY_ID,
    "range": _CONDITIONAL_RANGE_QUERY_ID,
}
_CONDITIONAL_QUERY_IDS: Tuple[str, ...] = (
    _CONDITIONAL_AGGREGATE_QUERY_ID,
    _CONDITIONAL_EXTREMUM_QUERY_ID,
)

_DEFAULTS = MultiseriesChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "multiseries")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="multiseries")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="multiseries", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    _PAIRWISE_QUERY_ID: 0.0,
    _EQUALITY_QUERY_ID: 0.35,
    _SERIES_RANK_QUERY_ID: 0.28,
    _CHANGE_QUERY_ID: 0.75,
    _RATIO_QUERY_ID: 0.20,
    _CONDITIONAL_AGGREGATE_QUERY_ID: 0.70,
    _CONDITIONAL_EXTREMUM_QUERY_ID: 0.66,
    _CATEGORY_TOTAL_QUERY_ID: 0.46,
}
_CONDITIONAL_AGGREGATE_REASONING_LOADS: Dict[str, float] = {
    "sum": 0.62,
    "mean": 0.70,
    "range": 0.78,
}
_REASONING_LOAD_BY_MEASURE: Dict[str, float] = {
    "directional_change": 0.65,
    "absolute_gap": 0.85,
    "series_share": 0.21,
    "pair_ratio": 0.14,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "grouped_bar": 0.0,
    "grouped_horizontal_bar": 0.50,
    "grouped_lollipop": 0.55,
    "multi_line": 1.0,
}
_FAMILY_RANGE_KEYS: Tuple[str, ...] = (
    "category_count_min",
    "category_count_max",
    "series_count_min",
    "series_count_max",
    "value_min",
    "value_max",
)


def _sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    """Sample the shared chart text font for this multiseries render."""

    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def _keyed_points_from_projection(annotation_projection: Mapping[str, Any]) -> Dict[str, list[float]]:
    """Normalize projected category/series mark centers into keyed point-map annotation."""

    return {
        str(key): [float(point[0]), float(point[1])]
        for key, point in dict(annotation_projection.get("pixel_point_map", {})).items()
    }


def _projected_keyed_point_annotation(
    annotation_projection: Mapping[str, Any],
    keyed_points: Mapping[str, list[float]],
) -> Dict[str, Any]:
    """Build the public projected-annotation payload for keyed mark witnesses."""

    point_set = [[float(point[0]), float(point[1])] for point in annotation_projection.get("pixel_point_set", [])]
    return {
        "type": "keyed_point_map",
        "keyed_point_map": {str(key): list(point) for key, point in keyed_points.items()},
        "pixel_keyed_point_map": {str(key): list(point) for key, point in keyed_points.items()},
        "point_set": list(point_set),
        "pixel_point_set": list(point_set),
        "bbox_set": [list(bbox) for bbox in annotation_projection.get("bbox_set", [])],
        "pixel_point_map": {str(key): list(point) for key, point in keyed_points.items()},
    }

def _normalize_multiseries_visual_scan(trace_extras: Mapping[str, Any]) -> float:
    """Normalize multiseries visual load from category and series counts."""

    if "filtered_category_count" in trace_extras:
        category_range = trace_extras.get("category_count_range", [0, 0])
        series_range = trace_extras.get("series_count_range", [0, 0])
        filter_range = trace_extras.get("filtered_category_count_range", [0, 0])
        total_marks = int(trace_extras["category_count"]) * int(trace_extras["series_count"])
        total_bounds = [
            int(category_range[0]) * int(series_range[0]),
            int(category_range[1]) * int(series_range[1]),
        ]
        mark_scan = normalize_int_with_bounds(int(total_marks), total_bounds)
        filter_scan = normalize_int_with_bounds(
            int(trace_extras["filtered_category_count"]),
            (int(filter_range[0]), int(filter_range[1])),
        )
        return min(1.0, (0.72 * float(mark_scan)) + (0.28 * float(filter_scan)))

    category_range = trace_extras.get("category_count_range", [0, 0])
    series_range = trace_extras.get("series_count_range", [0, 0])
    category_bounds = [
        min(
            int(_GEN_DEFAULTS.get("delta_category_count_min", category_range[0])),
            int(_GEN_DEFAULTS.get("ratio_category_count_min", category_range[0])),
        ),
        max(
            int(_GEN_DEFAULTS.get("delta_category_count_max", category_range[1])),
            int(_GEN_DEFAULTS.get("ratio_category_count_max", category_range[1])),
        ),
    ]
    series_bounds = [
        min(
            int(_GEN_DEFAULTS.get("delta_series_count_min", series_range[0])),
            int(_GEN_DEFAULTS.get("ratio_series_count_min", series_range[0])),
        ),
        max(
            int(_GEN_DEFAULTS.get("delta_series_count_max", series_range[1])),
            int(_GEN_DEFAULTS.get("ratio_series_count_max", series_range[1])),
        ),
    ]
    category_norm = normalize_int_with_bounds(int(trace_extras["category_count"]), category_bounds)
    series_norm = normalize_int_with_bounds(int(trace_extras["series_count"]), series_bounds)
    return min(1.0, (0.70 * float(category_norm)) + (0.30 * float(series_norm)))
