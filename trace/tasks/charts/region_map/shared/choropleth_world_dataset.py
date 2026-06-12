"""World-map dataset helpers for choropleth map tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .....core.seed import spawn_rng
from ....shared.bbox_projection import bbox_union_raw as _bbox_union, round_bbox as _round_bbox
from ....shared.color_distance import coerce_rgb as _rgb
from ....shared.config_defaults import required_group_defaults, resolve_required_int_bounds
from ....shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ....shared.drawing import draw_centered_text, draw_rounded_rect
from ....shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ....shared.text_rendering import fit_font_to_box, load_font
from ...shared.label_assets import resolve_chart_category_labels
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

from .choropleth_region_dataset import (
    _apply_bin,
    _assign_matching_bins,
    _assign_region_display_labels,
    _assign_values_from_bins,
    _make_category_bins,
    _make_numeric_bins,
    _sample_count_from_param_range,
    _sample_target_count,
    _value_bin_index,
)
def _world_selected_count_support(params: Mapping[str, Any], *, eligible_count: int) -> List[int]:
    count_min = int(
        params.get(
            "geographic_selected_region_count_min",
            params.get(
                "world_selected_region_count_min",
                _GEN_DEFAULTS.get(
                    "geographic_selected_region_count_min",
                    _GEN_DEFAULTS.get("world_selected_region_count_min", 18),
                ),
            ),
        )
    )
    count_max = int(
        params.get(
            "geographic_selected_region_count_max",
            params.get(
                "world_selected_region_count_max",
                _GEN_DEFAULTS.get(
                    "geographic_selected_region_count_max",
                    _GEN_DEFAULTS.get("world_selected_region_count_max", 28),
                ),
            ),
        )
    )
    if int(count_min) > int(count_max):
        raise ValueError(f"{TASK_ID} geographic selected region min cannot exceed max")
    high = min(int(count_max), int(eligible_count))
    low = min(int(count_min), int(high))
    return list(range(int(low), int(high) + 1))

def _build_world_regions(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], List[int], Dict[str, Any]]:
    world_filtered = _is_world_filtered_query_id(str(query_id))
    group_filtered_value = _is_group_filtered_value_query_id(str(query_id))
    geographic_adjacent = _is_adjacent_query_id(str(query_id))
    supported_world_variants = {
        "numeric_threshold_region_count",
        "numeric_interval_region_count",
        "categorical_region_count",
        *_SUPPORTED_WORLD_FILTERED_QUERY_IDS,
        *_SUPPORTED_REGION_SET_VALUE_QUERY_IDS,
        *_SUPPORTED_GROUP_FILTERED_VALUE_QUERY_IDS,
        *_SUPPORTED_ADJACENT_QUERY_IDS,
        *_SUPPORTED_MARKER_QUERY_IDS,
    }
    if str(query_id) not in supported_world_variants:
        raise ValueError(
            "geographic_region_map does not support this query id"
        )
    geographic_map_variant, geographic_map_variant_probabilities = _resolve_geographic_map_variant(
        params,
        instance_seed=int(instance_seed),
    )
    if (bool(world_filtered) or bool(group_filtered_value)) and str(geographic_map_variant) != "world_countries":
        raise ValueError("filtered world map tasks require geographic_map_variant=world_countries")
    asset = _load_geographic_map_asset(str(geographic_map_variant))
    asset_regions = [dict(region) for region in asset.get("regions", []) if isinstance(region, Mapping)]
    eligible_regions = [
        dict(region)
        for region in asset_regions
        if bool(region.get("question_eligible"))
    ]
    if not eligible_regions:
        raise ValueError("world map asset has no question-eligible regions")

    filtered_eligible_regions = _world_filtered_region_candidates(eligible_regions) if bool(world_filtered) or bool(group_filtered_value) else eligible_regions
    if (bool(world_filtered) or bool(group_filtered_value)) and not filtered_eligible_regions:
        raise ValueError("world map asset has no eligible filtered-continent regions")

    selected_count_support = _world_selected_count_support(params, eligible_count=len(filtered_eligible_regions))
    selected_count = _balanced_int(
        selected_count_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_id}.world_selected_region_count",
    )
    forced_target_asset_ids: List[str] = []
    forced_target_count = 0
    forced_target_support: List[int] = []
    target_continent = ""
    reference_asset_region_id = ""
    reference_region_id = ""
    reference_country_label = ""
    adjacent_min_shared_length_deg = 0.0
    adjacent_neighbor_asset_ids: List[str] = []
    same_group_distractor_asset_ids: List[str] = []
    if bool(world_filtered):
        forced_target_count, forced_target_support = _sample_target_count(
            params,
            region_count=int(selected_count),
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        regions_by_continent: Dict[str, List[Dict[str, Any]]] = {
            continent: [
                dict(region)
                for region in filtered_eligible_regions
                if str(region.get("continent") or "") == str(continent)
            ]
            for continent in _WORLD_FILTERED_CONTINENTS
        }
        feasible_continents = [
            str(continent)
            for continent, continent_regions in regions_by_continent.items()
            if len(continent_regions) >= int(forced_target_count)
            and (len(filtered_eligible_regions) - len(continent_regions)) >= int(selected_count) - int(forced_target_count)
        ]
        if not feasible_continents:
            raise ValueError("no feasible continent can support the requested filtered count")
        continent_index = _balanced_int(
            list(range(len(feasible_continents))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.target_continent",
        )
        target_continent = str(feasible_continents[int(continent_index)])
        target_pool = sorted(regions_by_continent[str(target_continent)], key=lambda item: str(item["region_id"]))
        distractor_pool = sorted(
            [
                dict(region)
                for region in filtered_eligible_regions
                if str(region.get("continent") or "") != str(target_continent)
            ],
            key=lambda item: str(item["region_id"]),
        )
        target_regions = rng.sample(target_pool, int(forced_target_count))
        distractor_regions = rng.sample(distractor_pool, int(selected_count) - int(forced_target_count))
        selected_asset_regions = list(target_regions) + list(distractor_regions)
        rng.shuffle(selected_asset_regions)
        forced_target_asset_ids = [str(region["region_id"]) for region in target_regions]
    elif bool(group_filtered_value):
        forced_target_count, forced_target_support = _sample_count_from_param_range(
            params,
            min_key="group_filtered_target_count_min",
            max_key="group_filtered_target_count_max",
            fallback_min=2,
            fallback_max=5,
            max_supported=max(1, int(selected_count) - 2),
            query_id=str(query_id),
            instance_seed=int(instance_seed),
            namespace_suffix="group_filtered_target_count",
        )
        same_group_count, _same_group_support = _sample_count_from_param_range(
            params,
            min_key="group_filtered_same_group_distractor_count_min",
            max_key="group_filtered_same_group_distractor_count_max",
            fallback_min=1,
            fallback_max=3,
            max_supported=max(1, int(selected_count) - int(forced_target_count) - 1),
            query_id=str(query_id),
            instance_seed=int(instance_seed),
            namespace_suffix="group_filtered_same_group_distractor_count",
        )
        regions_by_continent = {
            continent: [
                dict(region)
                for region in filtered_eligible_regions
                if str(region.get("continent") or "") == str(continent)
            ]
            for continent in _WORLD_FILTERED_CONTINENTS
        }
        feasible_continents = [
            str(continent)
            for continent, continent_regions in regions_by_continent.items()
            if len(continent_regions) >= int(forced_target_count) + int(same_group_count)
            and (len(filtered_eligible_regions) - len(continent_regions)) >= int(selected_count) - int(forced_target_count) - int(same_group_count)
        ]
        if not feasible_continents:
            raise ValueError("no feasible continent can support the requested filtered value task")
        continent_index = _balanced_int(
            list(range(len(feasible_continents))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.target_continent",
        )
        target_continent = str(feasible_continents[int(continent_index)])
        same_continent_pool = sorted(regions_by_continent[str(target_continent)], key=lambda item: str(item["region_id"]))
        target_regions = rng.sample(same_continent_pool, int(forced_target_count))
        remaining_same_continent = [
            dict(region)
            for region in same_continent_pool
            if str(region["region_id"]) not in {str(item["region_id"]) for item in target_regions}
        ]
        same_group_distractors = rng.sample(remaining_same_continent, int(same_group_count))
        distractor_pool = sorted(
            [
                dict(region)
                for region in filtered_eligible_regions
                if str(region.get("continent") or "") != str(target_continent)
            ],
            key=lambda item: str(item["region_id"]),
        )
        distractor_needed = int(selected_count) - int(forced_target_count) - int(same_group_count)
        selected_asset_regions = list(target_regions) + list(same_group_distractors) + rng.sample(distractor_pool, int(distractor_needed))
        rng.shuffle(selected_asset_regions)
        forced_target_asset_ids = [str(region["region_id"]) for region in target_regions]
        same_group_distractor_asset_ids = [str(region["region_id"]) for region in same_group_distractors]
    elif bool(geographic_adjacent):
        adjacent_min_shared_length_deg = float(
            params.get(
                "adjacent_min_shared_length_deg",
                _GEN_DEFAULTS.get("adjacent_min_shared_length_deg", 0.15),
            )
        )
        reference_min_area_sqdeg = float(
            params.get(
                "adjacent_reference_min_area_sqdeg",
                _GEN_DEFAULTS.get("adjacent_reference_min_area_sqdeg", 0.0),
            )
        )
        neighbor_min_area_sqdeg = float(
            params.get(
                "adjacent_neighbor_min_area_sqdeg",
                _GEN_DEFAULTS.get("adjacent_neighbor_min_area_sqdeg", 0.0),
            )
        )
        adjacent_neighbor_count_min = int(params.get("adjacent_neighbor_count_min", _GEN_DEFAULTS.get("adjacent_neighbor_count_min", 2)))
        adjacent_neighbor_count_max = int(params.get("adjacent_neighbor_count_max", _GEN_DEFAULTS.get("adjacent_neighbor_count_max", 6)))
        all_regions_by_id = {str(region["region_id"]): dict(region) for region in asset_regions}
        eligible_by_id = {str(region["region_id"]): dict(region) for region in eligible_regions}
        eligible_ids = set(eligible_by_id.keys())
        border_neighbors = _geographic_border_neighbors(
            str(geographic_map_variant),
            min_shared_length_deg=float(adjacent_min_shared_length_deg),
        )
        candidate_neighbors_by_ref: Dict[str, List[str]] = {}
        for candidate_id in sorted(eligible_ids):
            candidate = eligible_by_id[str(candidate_id)]
            if float(candidate.get("area_sqdeg") or 0.0) < float(reference_min_area_sqdeg):
                continue
            neighbor_ids = [
                str(neighbor_id)
                for neighbor_id in border_neighbors.get(str(candidate_id), [])
                if str(neighbor_id) in eligible_ids
                and float(all_regions_by_id[str(neighbor_id)].get("area_sqdeg") or 0.0) >= float(neighbor_min_area_sqdeg)
            ]
            if len(neighbor_ids) >= int(adjacent_neighbor_count_min):
                candidate_neighbors_by_ref[str(candidate_id)] = sorted(neighbor_ids)
        if not candidate_neighbors_by_ref:
            raise ValueError("no feasible reference region can support adjacent-region count")
        feasible_reference_ids = sorted(candidate_neighbors_by_ref.keys())
        reference_index = _balanced_int(
            list(range(len(feasible_reference_ids))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.adjacent_reference_region",
        )
        reference_asset_region_id = str(feasible_reference_ids[int(reference_index)])
        reference_region = dict(eligible_by_id[str(reference_asset_region_id)])
        reference_country_label = str(reference_region.get("display_name") or reference_asset_region_id)
        neighbor_pool = list(candidate_neighbors_by_ref[str(reference_asset_region_id)])
        neighbor_count_support = list(
            range(
                int(adjacent_neighbor_count_min),
                min(int(adjacent_neighbor_count_max), len(neighbor_pool)) + 1,
            )
        )
        neighbor_count = _balanced_int(
            neighbor_count_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.adjacent_neighbor_count",
        )
        adjacent_neighbor_asset_ids = sorted(rng.sample(neighbor_pool, int(neighbor_count)))
        distractor_pool = [
            dict(region)
            for region in sorted(eligible_regions, key=lambda item: str(item["region_id"]))
            if str(region["region_id"]) not in {str(reference_asset_region_id), *set(adjacent_neighbor_asset_ids)}
        ]
        selected_count = max(int(selected_count), 1 + len(adjacent_neighbor_asset_ids))
        selected_asset_regions = [
            dict(reference_region),
            *[dict(all_regions_by_id[str(region_id)]) for region_id in adjacent_neighbor_asset_ids],
        ]
        distractor_needed = max(0, int(selected_count) - len(selected_asset_regions))
        if distractor_needed > len(distractor_pool):
            distractor_needed = len(distractor_pool)
        selected_asset_regions.extend(rng.sample(distractor_pool, int(distractor_needed)))
        rng.shuffle(selected_asset_regions)
    else:
        selected_asset_regions = rng.sample(
            sorted(eligible_regions, key=lambda item: str(item["region_id"])),
            int(selected_count),
        )

    if "legend_bin_count" in params:
        bin_min = bin_max = int(params["legend_bin_count"])
    else:
        bin_min, bin_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="legend_bin_count_min",
            max_key="legend_bin_count_max",
            fallback_min=3,
            fallback_max=4,
            context=f"{TASK_ID} world legend bins",
        )
    bin_count = _balanced_int(
        list(range(int(bin_min), int(bin_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_id}.world_legend_bin_count",
    )
    legend_bins = (
        _make_category_bins(int(bin_count), rng=rng)
        if _is_categorical_query_id(str(query_id))
        else _make_numeric_bins(int(bin_count))
    )

    regions: List[Dict[str, Any]] = []
    region_prefix = str(asset.get("region_prefix") or "geo_region")
    for asset_region in selected_asset_regions:
        region_id = f"{region_prefix}_{asset_region['region_id']}"
        is_reference_region = bool(geographic_adjacent) and str(asset_region["region_id"]) == str(reference_asset_region_id)
        if bool(is_reference_region):
            reference_region_id = str(region_id)
        bbox_lonlat = [float(value) for value in asset_region.get("bbox_lonlat", [0.0, 0.0, 0.0, 0.0])]
        regions.append(
            {
                "region_id": str(region_id),
                "asset_region_id": str(asset_region["region_id"]),
                "display_name": str(asset_region.get("display_name") or asset_region["region_id"]),
                "continent": str(asset_region.get("continent") or ""),
                "admin0_a3": str(asset_region.get("admin0_a3") or ""),
                "subregion": str(asset_region.get("subregion") or ""),
                "bbox_lonlat": [round(float(value), 3) for value in bbox_lonlat],
                "centroid_lonlat": _centroid_lonlat_from_rings(asset_region.get("rings", [])),
                "bin_index": int(rng.randrange(int(bin_count))),
                "bin_label": str(legend_bins[0]["bin_label"]),
                "category": "",
                "is_reference_region": bool(is_reference_region),
            }
        )
    asset_meta = {
        "asset_id": str(asset.get("asset_id") or _GEOGRAPHIC_MAP_ASSETS[str(geographic_map_variant)]["asset_id"]),
        "map_variant": str(geographic_map_variant),
        "map_variant_probabilities": dict(geographic_map_variant_probabilities),
        "display_name": str(asset.get("display_name") or ""),
        "region_noun": str(asset.get("region_noun") or "regions"),
        "object_description": str(asset.get("object_description") or ""),
        "title_options": [str(item) for item in asset.get("title_options", [])],
        "category_title_options": list(_WORLD_CATEGORY_TITLE_OPTIONS),
        "forced_target_count": int(forced_target_count),
        "forced_target_support": [int(value) for value in forced_target_support],
        "target_continent": str(target_continent),
        "reference_region_id": str(reference_region_id),
        "reference_asset_region_id": str(reference_asset_region_id),
        "reference_country_label": str(reference_country_label),
        "adjacent_min_shared_length_deg": float(adjacent_min_shared_length_deg),
        "adjacent_neighbor_asset_ids": [str(region_id) for region_id in adjacent_neighbor_asset_ids],
        "same_group_distractor_asset_ids": [str(region_id) for region_id in same_group_distractor_asset_ids],
        "forced_target_region_ids": [
            f"{region_prefix}_{asset_region_id}"
            for asset_region_id in forced_target_asset_ids
        ],
        "source": dict(asset.get("source", {})) if isinstance(asset.get("source"), Mapping) else {},
    }
    return list(regions), list(legend_bins), [str(region["region_id"]) for region in regions], list(selected_count_support), dict(asset_meta)


__all__ = [
    '_world_selected_count_support',
    '_build_world_regions',
]

