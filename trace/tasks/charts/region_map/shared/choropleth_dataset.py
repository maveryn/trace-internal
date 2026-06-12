"""Top-level dataset constructor for choropleth map tasks."""

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

from .choropleth_marker_dataset import _construct_marker_dataset
from .choropleth_region_dataset import (
    _apply_bin,
    _apply_numeric_value,
    _assign_matching_bins,
    _assign_region_display_labels,
    _assign_values_from_bins,
    _build_regions,
    _make_category_bins,
    _make_numeric_bins,
    _sample_count_from_param_range,
    _sample_numeric_value_for_bin,
    _sample_target_count,
    _target_count_support,
    _value_bin_index,
)
from .choropleth_world_dataset import _build_world_regions

def _construct_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    if str(scene_variant) not in _SUPPORTED_SCENE_VARIANTS:
        raise ValueError(f"unsupported scene_variant: {scene_variant}")
    if _is_group_filtered_value_query_id(str(query_id)) and str(scene_variant) != "geographic_region_map":
        raise ValueError("group-filtered region value tasks require a geographic map")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    if str(scene_variant) == "geographic_region_map":
        rows = 0
        cols = 0
        active_cells: List[Tuple[int, int]] = []
        regions, legend_bins, _selected_region_ids, _selected_count_support, map_asset_meta = _build_world_regions(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
        )
    else:
        map_asset_meta = {}
        rows, cols, active_cells, regions, legend_bins = _build_regions(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
        )
    regions_by_id: Dict[str, Dict[str, Any]] = {str(region["region_id"]): dict(region) for region in regions}
    region_ids = [str(region["region_id"]) for region in regions]
    if _is_marker_query_id(str(query_id)):
        return _construct_marker_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
            rows=int(rows),
            cols=int(cols),
            active_cells=list(active_cells),
            regions=list(regions),
            legend_bins=list(legend_bins),
            map_asset_meta=dict(map_asset_meta),
        )
    world_filtered = str(scene_variant) == "geographic_region_map" and _is_world_filtered_query_id(str(query_id))
    group_filtered_value = str(scene_variant) == "geographic_region_map" and _is_group_filtered_value_query_id(str(query_id))
    adjacent = _is_adjacent_query_id(str(query_id))
    if bool(world_filtered) or bool(group_filtered_value):
        target_count = int(map_asset_meta.get("forced_target_count") or 0)
        target_support = [int(value) for value in map_asset_meta.get("forced_target_support", [])]
        if int(target_count) <= 0 or not target_support:
            raise ValueError("world filtered/value task did not construct a target count")
        selected_ids = {
            str(region_id)
            for region_id in map_asset_meta.get("forced_target_region_ids", [])
        }
    elif bool(adjacent):
        if str(scene_variant) == "geographic_region_map":
            adjacency = _selected_geographic_region_adjacency(
                regions_by_id,
                map_variant=str(map_asset_meta.get("map_variant") or "world_countries"),
                min_shared_length_deg=float(map_asset_meta.get("adjacent_min_shared_length_deg") or 0.15),
            )
        else:
            adjacency = _synthetic_region_adjacency(regions_by_id)
        answer_min, answer_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="count_answer_min",
            max_key="count_answer_max",
            fallback_min=1,
            fallback_max=4,
            context=f"{TASK_ID} adjacent answer count",
        )
        feasible_counts = sorted(
            {
                count
                for neighbor_ids in adjacency.values()
                for count in range(int(answer_min), min(int(answer_max), len(neighbor_ids)) + 1)
            }
        )
        if not feasible_counts:
            raise ValueError("no feasible adjacent-region count in selected map")
        target_count = _balanced_int(
            feasible_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.adjacent_target_count",
        )
        target_support = list(feasible_counts)
        reference_candidates = [
            str(region_id)
            for region_id, neighbor_ids in adjacency.items()
            if len(neighbor_ids) >= int(target_count)
        ]
        forced_reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if forced_reference_region_id in reference_candidates:
            reference_region_id = str(forced_reference_region_id)
        else:
            reference_index = _balanced_int(
                list(range(len(reference_candidates))),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.{query_id}.adjacent_reference_candidate",
            )
            reference_region_id = str(reference_candidates[int(reference_index)])
        regions_by_id[str(reference_region_id)]["is_reference_region"] = True
        neighbor_ids = list(adjacency.get(str(reference_region_id), []))
        selected_ids = set(rng.sample(neighbor_ids, int(target_count)))
        map_asset_meta["reference_region_id"] = str(reference_region_id)
        map_asset_meta["adjacent_neighbor_region_ids"] = list(neighbor_ids)
    elif _is_region_set_value_query_id(str(query_id)):
        target_count, target_support = _sample_count_from_param_range(
            params,
            min_key="region_set_size_min",
            max_key="region_set_size_max",
            fallback_min=3,
            fallback_max=5,
            max_supported=max(1, len(region_ids) - 1),
            query_id=str(query_id),
            instance_seed=int(instance_seed),
            namespace_suffix="region_set_size",
        )
        selected_ids = set(rng.sample(list(region_ids), int(target_count)))
    else:
        target_count, target_support = _sample_target_count(
            params,
            region_count=len(region_ids),
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        selected_ids = set(rng.sample(list(region_ids), int(target_count)))
    annotation_region_ids = _reading_order_region_ids(list(selected_ids), regions_by_id)

    query_params: Dict[str, Any]
    threshold_direction = ""
    threshold_direction_probabilities: Dict[str, float] = {}
    target_bin_indices: List[int] = []
    nonmatching_bin_indices: List[int] = []
    bin_count = int(len(legend_bins))
    answer_value: int | None = None
    if _is_region_sum_value_query_id(str(query_id)):
        _assign_region_display_labels(regions_by_id)

    if str(query_id) == "numeric_threshold_region_count":
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_bin = _balanced_int(
                list(range(0, bin_count - 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.threshold_bin.greater_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["upper"])
            target_bin_indices = list(range(int(threshold_bin) + 1, bin_count))
            nonmatching_bin_indices = list(range(0, int(threshold_bin) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_bin = _balanced_int(
                list(range(1, bin_count)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.threshold_bin.less_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["lower"])
            target_bin_indices = list(range(0, int(threshold_bin)))
            nonmatching_bin_indices = list(range(int(threshold_bin), bin_count))
            threshold_phrase = f"less than {threshold_value}"
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=annotation_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
    elif str(query_id) == "numeric_interval_region_count":
        max_span = min(4, max(2, bin_count - 1))
        span = _balanced_int(
            list(range(2, max_span + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.interval_span",
        )
        low_bin = _balanced_int(
            list(range(0, bin_count - int(span) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.interval_low_bin",
        )
        high_bin = int(low_bin) + int(span) - 1
        target_bin_indices = list(range(int(low_bin), int(high_bin) + 1))
        nonmatching_bin_indices = [index for index in range(bin_count) if index not in set(target_bin_indices)]
        if not nonmatching_bin_indices:
            raise ValueError("interval query must leave at least one nonmatching legend bin")
        lower = int(legend_bins[int(low_bin)]["lower"])
        upper = int(legend_bins[int(high_bin)]["upper"])
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=annotation_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "interval_lower": int(lower),
            "interval_upper": int(upper),
            "interval_phrase": f"between {lower} and {upper}, inclusive",
            "interval_bin_span": int(span),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
    elif str(query_id) == "categorical_region_count":
        category_index = _balanced_int(
            list(range(bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.category_index",
        )
        target_bin_indices = [int(category_index)]
        nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=annotation_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "category_index": int(category_index),
            "category_label": str(legend_bins[int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        }
    elif str(query_id) == "named_region_set_total_value":
        for region_id in region_ids:
            value = _sample_numeric_value_for_bin(
                int(rng.randrange(bin_count)),
                legend_bins,
                rng=rng,
            )
            _apply_numeric_value(
                regions_by_id,
                region_id=str(region_id),
                value=int(value),
                legend_bins=legend_bins,
            )
        set_names = ("Focus set", "Review set", "Priority set", "Audit set", "Target set")
        set_name = str(_choose_random(set_names, rng=rng))
        annotation_region_labels = [
            str(regions_by_id[str(region_id)].get("region_label") or "")
            for region_id in annotation_region_ids
        ]
        target_bin_indices = sorted({int(regions_by_id[str(region_id)]["bin_index"]) for region_id in annotation_region_ids})
        nonmatching_bin_indices = [index for index in range(bin_count) if index not in set(target_bin_indices)]
        query_params = {
            "region_set_name": str(set_name),
            "region_set_region_ids": [str(region_id) for region_id in annotation_region_ids],
            "region_set_labels": [str(label) for label in annotation_region_labels],
            "region_set_label_list": ", ".join(f'"{str(label)}"' for label in annotation_region_labels),
            "target_region_values": {
                str(region_id): int(regions_by_id[str(region_id)]["region_value"])
                for region_id in annotation_region_ids
            },
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
        answer_value = int(sum(int(regions_by_id[str(region_id)]["region_value"]) for region_id in annotation_region_ids))
    elif str(query_id) == "group_filtered_region_value":
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_bin = _balanced_int(
                list(range(0, bin_count - 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.group_filtered_threshold_bin.greater_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["upper"])
            target_bin_indices = list(range(int(threshold_bin) + 1, bin_count))
            nonmatching_bin_indices = list(range(0, int(threshold_bin) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_bin = _balanced_int(
                list(range(1, bin_count)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.group_filtered_threshold_bin.less_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["lower"])
            target_bin_indices = list(range(0, int(threshold_bin)))
            nonmatching_bin_indices = list(range(int(threshold_bin), bin_count))
            threshold_phrase = f"less than {threshold_value}"
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=annotation_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        _assign_values_from_bins(
            regions_by_id=regions_by_id,
            region_ids=region_ids,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "continent_label": str(map_asset_meta.get("target_continent") or ""),
            "target_continent": str(map_asset_meta.get("target_continent") or ""),
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
            "same_group_distractor_region_ids": [
                str(region_id)
                for region_id in (
                    f"country_{asset_region_id}"
                    for asset_region_id in map_asset_meta.get("same_group_distractor_asset_ids", [])
                )
                if str(region_id) in regions_by_id
            ],
            "target_region_values": {
                str(region_id): int(regions_by_id[str(region_id)]["region_value"])
                for region_id in annotation_region_ids
            },
        }
        answer_value = int(sum(int(regions_by_id[str(region_id)]["region_value"]) for region_id in annotation_region_ids))
    elif str(query_id) == "adjacent_same_category_count":
        reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if not reference_region_id:
            raise ValueError("adjacent same-category task did not construct a reference region")
        category_index = _balanced_int(
            list(range(bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.adjacent_same_category_index",
        )
        target_bin_indices = [int(category_index)]
        nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=[*annotation_region_ids, str(reference_region_id)],
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "reference_region_id": str(reference_region_id),
            "adjacent_neighbor_region_ids": [str(value) for value in map_asset_meta.get("adjacent_neighbor_region_ids", [])],
            "category_index": int(category_index),
            "category_label": str(legend_bins[int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        }
    elif str(query_id) == "adjacent_category_count":
        reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if not reference_region_id:
            raise ValueError("adjacent category task did not construct a reference region")
        category_index = _balanced_int(
            list(range(bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.adjacent_category_index",
        )
        target_bin_indices = [int(category_index)]
        nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=annotation_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "reference_region_id": str(reference_region_id),
            "adjacent_neighbor_region_ids": [str(value) for value in map_asset_meta.get("adjacent_neighbor_region_ids", [])],
            "category_index": int(category_index),
            "category_label": str(legend_bins[int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        }
    elif str(query_id) == "adjacent_numeric_threshold_count":
        reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if not reference_region_id:
            raise ValueError("adjacent threshold task did not construct a reference region")
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_bin = _balanced_int(
                list(range(0, bin_count - 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.adjacent_threshold_bin.greater_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["upper"])
            target_bin_indices = list(range(int(threshold_bin) + 1, bin_count))
            nonmatching_bin_indices = list(range(0, int(threshold_bin) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_bin = _balanced_int(
                list(range(1, bin_count)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.adjacent_threshold_bin.less_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["lower"])
            target_bin_indices = list(range(0, int(threshold_bin)))
            nonmatching_bin_indices = list(range(int(threshold_bin), bin_count))
            threshold_phrase = f"less than {threshold_value}"
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=annotation_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "reference_region_id": str(reference_region_id),
            "adjacent_neighbor_region_ids": [str(value) for value in map_asset_meta.get("adjacent_neighbor_region_ids", [])],
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
    elif str(query_id) == "continent_region_count":
        for region_id in region_ids:
            _apply_bin(
                regions_by_id,
                region_id=str(region_id),
                bin_index=int(rng.randrange(bin_count)),
                legend_bins=legend_bins,
            )
        target_bin_indices = []
        nonmatching_bin_indices = list(range(bin_count))
        query_params = {
            "continent_label": str(map_asset_meta.get("target_continent") or ""),
            "target_continent": str(map_asset_meta.get("target_continent") or ""),
            "target_bin_indices": [],
        }
    elif str(query_id) == "continent_category_region_count":
        category_index = _balanced_int(
            list(range(bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.continent_category_index",
        )
        target_bin_indices = [int(category_index)]
        nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=annotation_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        outside_continent_ids = [
            str(region_id)
            for region_id in region_ids
            if str(region_id) not in set(annotation_region_ids)
            and str(regions_by_id[str(region_id)].get("continent") or "") != str(map_asset_meta.get("target_continent") or "")
        ]
        for region_id in rng.sample(outside_continent_ids, min(len(outside_continent_ids), max(1, int(target_count)))):
            _apply_bin(
                regions_by_id,
                region_id=str(region_id),
                bin_index=int(_choose_random(target_bin_indices, rng=rng)),
                legend_bins=legend_bins,
            )
        query_params = {
            "continent_label": str(map_asset_meta.get("target_continent") or ""),
            "target_continent": str(map_asset_meta.get("target_continent") or ""),
            "category_index": int(category_index),
            "category_label": str(legend_bins[int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        }
    elif str(query_id) == "continent_threshold_region_count":
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_bin = _balanced_int(
                list(range(0, bin_count - 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.continent_threshold_bin.greater_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["upper"])
            target_bin_indices = list(range(int(threshold_bin) + 1, bin_count))
            nonmatching_bin_indices = list(range(0, int(threshold_bin) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_bin = _balanced_int(
                list(range(1, bin_count)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.continent_threshold_bin.less_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["lower"])
            target_bin_indices = list(range(0, int(threshold_bin)))
            nonmatching_bin_indices = list(range(int(threshold_bin), bin_count))
            threshold_phrase = f"less than {threshold_value}"
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=annotation_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        outside_continent_ids = [
            str(region_id)
            for region_id in region_ids
            if str(region_id) not in set(annotation_region_ids)
            and str(regions_by_id[str(region_id)].get("continent") or "") != str(map_asset_meta.get("target_continent") or "")
        ]
        for region_id in rng.sample(outside_continent_ids, min(len(outside_continent_ids), max(1, int(target_count)))):
            _apply_bin(
                regions_by_id,
                region_id=str(region_id),
                bin_index=int(_choose_random(target_bin_indices, rng=rng)),
                legend_bins=legend_bins,
            )
        query_params = {
            "continent_label": str(map_asset_meta.get("target_continent") or ""),
            "target_continent": str(map_asset_meta.get("target_continent") or ""),
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    if answer_value is None:
        answer_value = int(target_count)

    final_regions = [dict(regions_by_id[str(region_id)]) for region_id in region_ids]
    regions_by_id = {str(region["region_id"]): dict(region) for region in final_regions}
    world_scene = str(scene_variant) == "geographic_region_map"
    if world_scene and _is_categorical_query_id(str(query_id)):
        title_options = list(map_asset_meta.get("category_title_options", []))
    else:
        title_options = list(map_asset_meta.get("title_options", [])) if world_scene else []
    if not title_options:
        title_options = list(
            _WORLD_CATEGORY_TITLE_OPTIONS
            if world_scene and _is_categorical_query_id(str(query_id))
            else (_WORLD_TITLE_OPTIONS if world_scene else _TITLE_OPTIONS)
        )
    return {
        "scene_title": str(_choose_random(title_options, rng=rng)),
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "map_asset_id": str(map_asset_meta.get("asset_id") or (_WORLD_MAP_ASSET_ID if world_scene else "")),
        "geographic_map_variant": str(map_asset_meta.get("map_variant") or ""),
        "geographic_map_variant_probabilities": dict(map_asset_meta.get("map_variant_probabilities", {})),
        "map_display_name": str(map_asset_meta.get("display_name") or ""),
        "map_region_noun": str(map_asset_meta.get("region_noun") or ""),
        "map_object_description": str(map_asset_meta.get("object_description") or ""),
        "map_source": dict(map_asset_meta.get("source", {})),
        "rows": int(rows),
        "cols": int(cols),
        "region_count": int(len(final_regions)),
        "active_cells": [[int(row), int(col)] for row, col in active_cells],
        "legend_bins": [dict(item) for item in legend_bins],
        "regions": final_regions,
        "regions_by_id": dict(regions_by_id),
        "annotation_region_ids": list(annotation_region_ids),
        "answer_value": int(answer_value),
        "answer_type": "integer",
        "target_count": int(target_count),
        "target_count_probabilities": uniform_probability_map(tuple(target_support)),
        "question_params": dict(query_params),
        "target_bin_indices": [int(value) for value in target_bin_indices],
        "nonmatching_bin_indices": [int(value) for value in nonmatching_bin_indices],
        "threshold_direction": str(threshold_direction),
    }


__all__ = [
    "_construct_dataset",
]

