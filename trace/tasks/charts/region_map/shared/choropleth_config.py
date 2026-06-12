"""Configuration and query-selection helpers for choropleth map tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ....shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.labeled_chart_common import resolve_chart_axis_variant
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults
from .choropleth_assets import (
    SUPPORTED_GEOGRAPHIC_MAP_VARIANTS as _SUPPORTED_GEOGRAPHIC_MAP_VARIANTS,
    normalize_geographic_map_variant as _normalize_geographic_map_variant,
)

TASK_ID = "charts_map_choropleth_region_count_base"
_SUPPORTED_REGION_VALUE_QUERY_IDS: Tuple[str, ...] = (
    "numeric_threshold_region_count",
    "numeric_interval_region_count",
)
_SUPPORTED_REGION_CATEGORY_QUERY_IDS: Tuple[str, ...] = (
    "categorical_region_count",
)
_SUPPORTED_WORLD_FILTERED_QUERY_IDS: Tuple[str, ...] = (
    "continent_region_count",
    "continent_category_region_count",
    "continent_threshold_region_count",
)
_SUPPORTED_REGION_SET_VALUE_QUERY_IDS: Tuple[str, ...] = (
    "named_region_set_total_value",
)
_SUPPORTED_GROUP_FILTERED_VALUE_QUERY_IDS: Tuple[str, ...] = (
    "group_filtered_region_value",
)
_SUPPORTED_ADJACENT_QUERY_IDS: Tuple[str, ...] = (
    "adjacent_same_category_count",
    "adjacent_category_count",
    "adjacent_numeric_threshold_count",
)
_SUPPORTED_MARKER_QUERY_IDS: Tuple[str, ...] = (
    "marker_region_threshold_count",
    "marker_region_extremum_label",
)
_SUPPORTED_MARKER_RENDER_VARIANTS: Tuple[str, ...] = (
    "proportional_bubble",
)
_SUPPORTED_MARKER_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = _SUPPORTED_REGION_VALUE_QUERY_IDS + _SUPPORTED_REGION_CATEGORY_QUERY_IDS
_SUPPORTED_ALL_QUERY_IDS: Tuple[str, ...] = (
    _SUPPORTED_QUERY_IDS
    + _SUPPORTED_WORLD_FILTERED_QUERY_IDS
    + _SUPPORTED_REGION_SET_VALUE_QUERY_IDS
    + _SUPPORTED_GROUP_FILTERED_VALUE_QUERY_IDS
    + _SUPPORTED_ADJACENT_QUERY_IDS
    + _SUPPORTED_MARKER_QUERY_IDS
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("synthetic_region_map", "geographic_region_map")
_SUPPORTED_THRESHOLD_DIRECTIONS: Tuple[str, ...] = ("greater_than", "less_than")

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Regional Value Map",
    "District Value Map",
    "Service Area Map",
    "Planning Region Map",
    "County Indicator Map",
)
_MARKER_MAP_TITLE_OPTIONS: Tuple[str, ...] = (
    "Regional Marker Map",
    "Bubble Indicator Map",
    "Marker Value Map",
    "Area Marker Overview",
    "Region Bubble Map",
)


_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "numeric_threshold_region_count": 0.50,
    "numeric_interval_region_count": 0.62,
    "categorical_region_count": 0.46,
    "continent_region_count": 0.56,
    "continent_category_region_count": 0.68,
    "continent_threshold_region_count": 0.70,
    "named_region_set_total_value": 0.72,
    "group_filtered_region_value": 0.82,
    "adjacent_same_category_count": 0.64,
    "adjacent_category_count": 0.66,
    "adjacent_numeric_threshold_count": 0.72,
    "marker_region_threshold_count": 0.58,
    "marker_region_extremum_label": 0.54,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "synthetic_region_map": 0.58,
    "geographic_region_map": 0.72,
}


_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "region_map")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="region_map")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="region_map", apply_prob=0.0)

def _is_categorical_query_id(query_id: str) -> bool:
    return str(query_id) in {
        "categorical_region_count",
        "continent_category_region_count",
        "adjacent_same_category_count",
        "adjacent_category_count",
    }

def _is_world_filtered_query_id(query_id: str) -> bool:
    return str(query_id) in set(_SUPPORTED_WORLD_FILTERED_QUERY_IDS)

def _is_region_set_value_query_id(query_id: str) -> bool:
    return str(query_id) in set(_SUPPORTED_REGION_SET_VALUE_QUERY_IDS)

def _is_group_filtered_value_query_id(query_id: str) -> bool:
    return str(query_id) in set(_SUPPORTED_GROUP_FILTERED_VALUE_QUERY_IDS)

def _is_region_sum_value_query_id(query_id: str) -> bool:
    return _is_region_set_value_query_id(str(query_id)) or _is_group_filtered_value_query_id(str(query_id))

def _is_adjacent_query_id(query_id: str) -> bool:
    return str(query_id) in set(_SUPPORTED_ADJACENT_QUERY_IDS)

def _is_marker_query_id(query_id: str) -> bool:
    return str(query_id) in set(_SUPPORTED_MARKER_QUERY_IDS)

def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )

def _resolve_geographic_map_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    alias_params = dict(params)
    if "map_asset_variant" in alias_params and "geographic_map_variant" not in alias_params:
        alias_params["geographic_map_variant"] = alias_params.get("map_asset_variant")
    if "map_asset_id" in alias_params and "geographic_map_variant" not in alias_params:
        alias_params["geographic_map_variant"] = _normalize_geographic_map_variant(alias_params.get("map_asset_id"))
    return resolve_chart_axis_variant(
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_GEOGRAPHIC_MAP_VARIANTS,
        task_id=TASK_ID,
        explicit_key="geographic_map_variant",
        weights_key="geographic_map_variant_weights",
        balance_flag_key="balanced_geographic_map_variant_sampling",
        axis_namespace="geographic_map_variant",
    )

def _resolve_threshold_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_THRESHOLD_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="threshold_direction",
        weights_key="threshold_direction_weights",
        balance_flag_key="balanced_threshold_direction_sampling",
        axis_namespace="threshold_direction",
    )

def _resolve_marker_render_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_MARKER_RENDER_VARIANTS,
        task_id=TASK_ID,
        explicit_key="marker_render_variant",
        weights_key="marker_render_variant_weights",
        balance_flag_key="balanced_marker_render_variant_sampling",
        axis_namespace="marker_render_variant",
    )

def _resolve_marker_extremum_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_MARKER_EXTREMUM_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="marker_extremum_direction",
        weights_key="marker_extremum_direction_weights",
        balance_flag_key="balanced_marker_extremum_direction_sampling",
        axis_namespace="marker_extremum_direction",
    )

def _json_examples(query_id: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_id)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
    )


