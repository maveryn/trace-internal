"""Marker-map dataset helpers for choropleth map tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.bbox_projection import bbox_union_raw as _bbox_union, round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import required_group_defaults, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font
from ..shared.label_assets import resolve_chart_category_labels
from .choropleth_assets import (
    GEOGRAPHIC_MAP_ASSETS as _GEOGRAPHIC_MAP_ASSETS,
    WORLD_CATEGORY_TITLE_OPTIONS as _WORLD_CATEGORY_TITLE_OPTIONS,
    WORLD_MAP_ASSET_ID as _WORLD_MAP_ASSET_ID,
    WORLD_TITLE_OPTIONS as _WORLD_TITLE_OPTIONS,
    load_geographic_map_asset as _load_geographic_map_asset,
    load_world_map_asset as _load_world_map_asset,
)
from .choropleth_config import *  # noqa: F403
from .choropleth_geometry import (
    _balanced_int,
    _choose_random,
    _grid_pair_support,
    _grid_points,
    _neighbors,
    _polygon_bbox,
    _polygon_center,
    _reading_order_region_ids,
    _region_polygon,
    _region_sort_key,
    _sample_connected_cells,
    _shrink_polygon,
)
from .choropleth_geography import (
    WORLD_FILTERED_CONTINENTS as _WORLD_FILTERED_CONTINENTS,
    _border_segment_key,
    _border_segment_length,
    _centroid_lonlat_from_rings,
    _geographic_border_neighbors,
    _geographic_shared_border_lengths,
    _region_boundary_segments,
    _selected_geographic_region_adjacency,
    _synthetic_region_adjacency,
    _world_country_shared_border_lengths,
    _world_filtered_region_candidates,
)
from .choropleth_style import (
    resolve_choropleth_legend_position as _resolve_legend_position,
    resolve_choropleth_marker_style as _resolve_marker_style,
    resolve_choropleth_palette as _resolve_palette,
    resolve_choropleth_world_map_style as _resolve_world_map_style,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]

from .choropleth_region_dataset import _marker_label_for_index, _sample_target_count

def _marker_value_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="marker_value_min",
        max_key="marker_value_max",
        fallback_min=1,
        fallback_max=5,
        context=f"{TASK_ID} marker values",
    )
    if int(high) - int(low) < 2:
        raise ValueError("marker value support must contain at least three values")
    return int(low), int(high)

def _construct_marker_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    rows: int,
    cols: int,
    active_cells: Sequence[Tuple[int, int]],
    regions: Sequence[Mapping[str, Any]],
    legend_bins: Sequence[Mapping[str, Any]],
    map_asset_meta: Mapping[str, Any],
) -> Dict[str, Any]:
    regions_by_id: Dict[str, Dict[str, Any]] = {str(region["region_id"]): dict(region) for region in regions}
    region_ids = _reading_order_region_ids([str(region["region_id"]) for region in regions], regions_by_id)
    if len(region_ids) < 3:
        raise ValueError("marker map needs at least three visible regions")

    marker_render_variant, marker_render_variant_probabilities = _resolve_marker_render_variant(
        params,
        instance_seed=int(instance_seed),
    )
    value_min, value_max = _marker_value_bounds(params)
    value_support = list(range(int(value_min), int(value_max) + 1))
    for index, region_id in enumerate(region_ids):
        regions_by_id[str(region_id)]["marker_label"] = _marker_label_for_index(int(index))
        regions_by_id[str(region_id)]["marker_value"] = int(_choose_random(value_support, rng=rng))
        regions_by_id[str(region_id)]["bin_index"] = 0
        regions_by_id[str(region_id)]["bin_label"] = ""
        regions_by_id[str(region_id)]["category"] = ""

    answer_value: Any
    answer_type: str
    annotation_region_ids: List[str]
    query_params: Dict[str, Any]
    target_count = 0
    target_support: List[int] = []
    threshold_direction = ""

    if str(query_id) == "marker_region_threshold_count":
        target_count, target_support = _sample_target_count(
            params,
            region_count=len(region_ids),
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        target_ids = set(rng.sample(list(region_ids), int(target_count)))
        annotation_region_ids = _reading_order_region_ids(list(target_ids), regions_by_id)
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_value = _balanced_int(
                list(range(int(value_min), int(value_max))),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.{query_id}.marker_threshold.greater_than",
            )
            matching_values = list(range(int(threshold_value) + 1, int(value_max) + 1))
            nonmatching_values = list(range(int(value_min), int(threshold_value) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_value = _balanced_int(
                list(range(int(value_min) + 1, int(value_max) + 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.{query_id}.marker_threshold.less_than",
            )
            matching_values = list(range(int(value_min), int(threshold_value)))
            nonmatching_values = list(range(int(threshold_value), int(value_max) + 1))
            threshold_phrase = f"less than {threshold_value}"
        for region_id in region_ids:
            support = matching_values if str(region_id) in target_ids else nonmatching_values
            regions_by_id[str(region_id)]["marker_value"] = int(_choose_random(support, rng=rng))
            regions_by_id[str(region_id)]["is_target_marker_region"] = bool(str(region_id) in target_ids)
        answer_value = int(target_count)
        answer_type = "integer"
        query_params = {
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "marker_value_min": int(value_min),
            "marker_value_max": int(value_max),
        }
    elif str(query_id) == "marker_region_extremum_label":
        extremum_direction, extremum_direction_probabilities = _resolve_marker_extremum_direction(
            params,
            instance_seed=int(instance_seed),
        )
        answer_index = _balanced_int(
            list(range(len(region_ids))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.answer_region_index",
        )
        answer_region_id = str(region_ids[int(answer_index)])
        if str(extremum_direction) == "largest":
            answer_marker_value = int(value_max)
            distractor_values = list(range(int(value_min), int(value_max)))
            extremum_word = "largest"
        else:
            answer_marker_value = int(value_min)
            distractor_values = list(range(int(value_min) + 1, int(value_max) + 1))
            extremum_word = "smallest"
        for region_id in region_ids:
            if str(region_id) == str(answer_region_id):
                regions_by_id[str(region_id)]["marker_value"] = int(answer_marker_value)
                regions_by_id[str(region_id)]["is_target_marker_region"] = True
            else:
                regions_by_id[str(region_id)]["marker_value"] = int(_choose_random(distractor_values, rng=rng))
                regions_by_id[str(region_id)]["is_target_marker_region"] = False
        answer_value = str(regions_by_id[str(answer_region_id)]["marker_label"])
        answer_type = "string"
        annotation_region_ids = [str(answer_region_id)]
        target_count = 1
        target_support = [1]
        query_params = {
            "extremum_direction": str(extremum_direction),
            "extremum_direction_probabilities": dict(extremum_direction_probabilities),
            "extremum_word": str(extremum_word),
            "answer_region_id": str(answer_region_id),
            "answer_marker_label": str(answer_value),
            "answer_marker_value": int(answer_marker_value),
            "marker_value_min": int(value_min),
            "marker_value_max": int(value_max),
        }
    else:
        raise ValueError(f"unsupported marker query_id: {query_id}")

    final_regions = [dict(regions_by_id[str(region_id)]) for region_id in region_ids]
    world_scene = str(scene_variant) == "geographic_region_map"
    region_noun = str(map_asset_meta.get("region_noun") or ("countries" if world_scene else "regions"))
    map_display = str(map_asset_meta.get("display_name") or "geographic")
    object_description = (
        f"a {map_display.lower() if map_display.lower() == 'world' else map_display} map with marker bubbles over selected {region_noun}"
        if world_scene
        else "a synthetic map with marker bubbles over selected regions"
    )
    return {
        "scene_title": str(_choose_random(_MARKER_MAP_TITLE_OPTIONS, rng=rng)),
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "map_asset_id": str(map_asset_meta.get("asset_id") or (_WORLD_MAP_ASSET_ID if world_scene else "")),
        "geographic_map_variant": str(map_asset_meta.get("map_variant") or ""),
        "geographic_map_variant_probabilities": dict(map_asset_meta.get("map_variant_probabilities", {})),
        "map_display_name": str(map_asset_meta.get("display_name") or ""),
        "map_region_noun": str(region_noun),
        "map_object_description": str(object_description),
        "map_source": dict(map_asset_meta.get("source", {})),
        "rows": int(rows),
        "cols": int(cols),
        "region_count": int(len(final_regions)),
        "active_cells": [[int(row), int(col)] for row, col in active_cells],
        "legend_bins": [dict(item) for item in legend_bins],
        "regions": final_regions,
        "regions_by_id": {str(region["region_id"]): dict(region) for region in final_regions},
        "annotation_region_ids": list(annotation_region_ids),
        "answer_value": answer_value,
        "answer_type": str(answer_type),
        "target_count": int(target_count),
        "target_count_probabilities": uniform_probability_map(tuple(target_support)),
        "question_params": {
            "marker_render_variant": str(marker_render_variant),
            "marker_render_variant_probabilities": dict(marker_render_variant_probabilities),
            "marker_region_ids": [str(region_id) for region_id in region_ids],
            **dict(query_params),
        },
        "target_bin_indices": [],
        "nonmatching_bin_indices": [],
        "threshold_direction": str(threshold_direction),
        "marker_render_variant": str(marker_render_variant),
        "marker_render_variant_probabilities": dict(marker_render_variant_probabilities),
        "marker_value_min": int(value_min),
        "marker_value_max": int(value_max),
    }


__all__ = [
    '_marker_label_for_index',
    '_marker_value_bounds',
    '_construct_marker_dataset',
]
