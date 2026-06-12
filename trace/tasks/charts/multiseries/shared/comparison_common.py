"""Shared constants and neutral helpers for the multiseries chart scene."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ....shared.font_assets import sample_font_family
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults
from .multiseries_chart_config import MultiseriesChartDefaults


DOMAIN = "charts"
SCENE_ID = "multiseries"
SCENE_NAMESPACE = "charts_multiseries"
PROMPT_BUNDLE_ID = "charts_multiseries_v1"

CHANGE_QUERY_ID = "ranked_change_extremum"
RATIO_QUERY_ID = "ranked_ratio_extremum"
PAIRWISE_QUERY_ID = "series_comparison_count"
EQUALITY_QUERY_ID = "pair_equality_label"
SERIES_RANK_QUERY_ID = "series_rank_at_category_label"
CATEGORY_TOTAL_QUERY_ID = "category_total_extremum_label"

SUPPORTED_CHANGE_MEASURES: Tuple[str, ...] = ("directional_change", "absolute_gap")
SUPPORTED_RATIO_MEASURES: Tuple[str, ...] = ("series_share", "pair_ratio")
SUPPORTED_CHANGE_DIRECTIONS: Tuple[str, ...] = ("increase", "decrease")
SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")
SUPPORTED_COMPARISONS: Tuple[str, ...] = ("greater_than", "less_than")

DEFAULTS = MultiseriesChartDefaults()
_SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
GEN_DEFAULTS, RENDER_DEFAULTS, PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    **{"task" "_id": SCENE_NAMESPACE},
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)

REASONING_LOAD_BY_OBJECTIVE: Dict[str, float] = {
    PAIRWISE_QUERY_ID: 0.0,
    EQUALITY_QUERY_ID: 0.35,
    SERIES_RANK_QUERY_ID: 0.28,
    CHANGE_QUERY_ID: 0.75,
    RATIO_QUERY_ID: 0.20,
    CATEGORY_TOTAL_QUERY_ID: 0.46,
}
REASONING_LOAD_BY_MEASURE: Dict[str, float] = {
    "directional_change": 0.65,
    "absolute_gap": 0.85,
    "series_share": 0.21,
    "pair_ratio": 0.14,
}
SCENE_VARIANT_LOADS: Dict[str, float] = {
    "grouped_bar": 0.0,
    "grouped_horizontal_bar": 0.50,
    "grouped_lollipop": 0.55,
    "multi_line": 1.0,
}
FAMILY_RANGE_KEYS: Tuple[str, ...] = (
    "category_count_min",
    "category_count_max",
    "series_count_min",
    "series_count_max",
    "value_min",
    "value_max",
)


def sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    """Sample the shared chart text font for this multiseries render."""

    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def keyed_points_from_projection(annotation_projection: Mapping[str, Any]) -> Dict[str, list[float]]:
    """Normalize projected category/series mark centers into a keyed point map."""

    return {
        str(key): [float(point[0]), float(point[1])]
        for key, point in dict(annotation_projection.get("pixel_point_map", {})).items()
    }


def projected_keyed_point_annotation(
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


def normalize_multiseries_visual_scan(trace_extras: Mapping[str, Any]) -> float:
    """Normalize multiseries visual load from category and series counts."""

    category_range = trace_extras.get("category_count_range", [0, 0])
    series_range = trace_extras.get("series_count_range", [0, 0])
    category_bounds = [
        min(
            int(GEN_DEFAULTS.get("delta_category_count_min", category_range[0])),
            int(GEN_DEFAULTS.get("ratio_category_count_min", category_range[0])),
        ),
        max(
            int(GEN_DEFAULTS.get("delta_category_count_max", category_range[1])),
            int(GEN_DEFAULTS.get("ratio_category_count_max", category_range[1])),
        ),
    ]
    series_bounds = [
        min(
            int(GEN_DEFAULTS.get("delta_series_count_min", series_range[0])),
            int(GEN_DEFAULTS.get("ratio_series_count_min", series_range[0])),
        ),
        max(
            int(GEN_DEFAULTS.get("delta_series_count_max", series_range[1])),
            int(GEN_DEFAULTS.get("ratio_series_count_max", series_range[1])),
        ),
    ]
    category_norm = normalize_int_with_bounds(int(trace_extras["category_count"]), category_bounds)
    series_norm = normalize_int_with_bounds(int(trace_extras["series_count"]), series_bounds)
    return min(1.0, (0.70 * float(category_norm)) + (0.30 * float(series_norm)))


