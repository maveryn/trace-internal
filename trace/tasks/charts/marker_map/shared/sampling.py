"""Dataset sampling for marker-map chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import resolve_required_int_bounds
from ....shared.deterministic_sampling import uniform_probability_map
from .assets import GEOGRAPHIC_MAP_ASSETS, load_geographic_map_asset
from .data import _make_numeric_bins, _marker_label_for_index, build_synthetic_marker_regions, sample_target_count
from .defaults import _GEN_DEFAULTS, SCENE_NAMESPACE, resolve_geographic_map_variant, resolve_marker_render_variant
from .projection import _centroid_lonlat_from_rings
from .spatial_primitives import _balanced_int, _choose_random, _reading_order_region_ids

def _world_selected_count_support(params: Mapping[str, Any], *, eligible_count: int) -> List[int]:
    count_min = int(
        params.get(
            "geographic_selected_region_count_min",
            params.get("world_selected_region_count_min", _GEN_DEFAULTS.get("geographic_selected_region_count_min", 9)),
        )
    )
    count_max = int(
        params.get(
            "geographic_selected_region_count_max",
            params.get("world_selected_region_count_max", _GEN_DEFAULTS.get("geographic_selected_region_count_max", 14)),
        )
    )
    if int(count_min) > int(count_max):
        raise ValueError(f"{SCENE_NAMESPACE} geographic selected region min cannot exceed max")
    high = min(int(count_max), int(eligible_count))
    low = min(int(count_min), int(high))
    return list(range(int(low), int(high) + 1))


def build_geographic_marker_regions(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    namespace_suffix: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], List[int], Dict[str, Any]]:
    """Select question-eligible geographic regions and adapt them to marker-map region records."""

    geographic_map_variant, geographic_map_variant_probabilities = resolve_geographic_map_variant(
        params,
        instance_seed=int(instance_seed),
    )
    asset = load_geographic_map_asset(str(geographic_map_variant))
    asset_regions = [dict(region) for region in asset.get("regions", []) if isinstance(region, Mapping)]
    eligible_regions = [
        dict(region)
        for region in asset_regions
        if bool(region.get("question_eligible"))
    ]
    if not eligible_regions:
        raise ValueError("geographic map asset has no question-eligible regions")

    selected_count_support = _world_selected_count_support(params, eligible_count=len(eligible_regions))
    selected_count = _balanced_int(
        selected_count_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.selected_region_count",
    )
    selected_asset_regions = rng.sample(
        sorted(eligible_regions, key=lambda item: str(item["region_id"])),
        int(selected_count),
    )

    bin_count = int(params.get("legend_bin_count", _GEN_DEFAULTS.get("legend_bin_count", 3)))
    legend_bins = _make_numeric_bins(int(bin_count))
    regions: List[Dict[str, Any]] = []
    region_prefix = str(asset.get("region_prefix") or "geo_region")
    for asset_region in selected_asset_regions:
        region_id = f"{region_prefix}_{asset_region['region_id']}"
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
                "is_reference_region": False,
            }
        )
    asset_meta = {
        "asset_id": str(asset.get("asset_id") or GEOGRAPHIC_MAP_ASSETS[str(geographic_map_variant)]["asset_id"]),
        "map_variant": str(geographic_map_variant),
        "map_variant_probabilities": dict(geographic_map_variant_probabilities),
        "display_name": str(asset.get("display_name") or ""),
        "region_noun": str(asset.get("region_noun") or "regions"),
        "object_description": str(asset.get("object_description") or ""),
        "title_options": [str(item) for item in asset.get("title_options", [])],
        "source": dict(asset.get("source", {})) if isinstance(asset.get("source"), Mapping) else {},
    }
    return list(regions), list(legend_bins), [str(region["region_id"]) for region in regions], list(selected_count_support), dict(asset_meta)


def _marker_value_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="marker_value_min",
        max_key="marker_value_max",
        fallback_min=1,
        fallback_max=5,
        context=f"{SCENE_NAMESPACE} marker values",
    )
    if int(high) - int(low) < 2:
        raise ValueError("marker value support must contain at least three values")
    return int(low), int(high)


def _base_marker_map_dataset(
    *,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace_suffix: str,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], List[str], Any]:
    """Build the scene-neutral marker-map dataset before objective-specific answer constraints."""

    if str(scene_variant) not in {"synthetic_region_map", "geographic_region_map"}:
        raise ValueError(f"unsupported marker-map scene variant: {scene_variant}")
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.{namespace_suffix}.dataset")
    if str(scene_variant) == "geographic_region_map":
        rows = 0
        cols = 0
        active_cells: List[Tuple[int, int]] = []
        regions, legend_bins, _selected_region_ids, _selected_count_support, map_asset_meta = build_geographic_marker_regions(
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
            namespace_suffix=str(namespace_suffix),
        )
    else:
        map_asset_meta: Dict[str, Any] = {}
        rows, cols, active_cells, regions, legend_bins = build_synthetic_marker_regions(
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
            namespace_suffix=str(namespace_suffix),
        )

    regions_by_id: Dict[str, Dict[str, Any]] = {str(region["region_id"]): dict(region) for region in regions}
    region_ids = _reading_order_region_ids([str(region["region_id"]) for region in regions], regions_by_id)
    if len(region_ids) < 3:
        raise ValueError("marker map needs at least three visible regions")

    marker_render_variant, marker_render_variant_probabilities = resolve_marker_render_variant(
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

    world_scene = str(scene_variant) == "geographic_region_map"
    region_noun = str(map_asset_meta.get("region_noun") or ("countries" if world_scene else "regions"))
    map_display = str(map_asset_meta.get("display_name") or "geographic")
    object_description = (
        f"a {map_display.lower() if map_display.lower() == 'world' else map_display} map with marker bubbles over selected {region_noun}"
        if world_scene
        else "a synthetic map with marker bubbles over selected regions"
    )
    base_dataset = {
        "scene_title": str(_choose_random(_marker_title_options(), rng=rng)),
        "scene_variant": str(scene_variant),
        "map_asset_id": str(map_asset_meta.get("asset_id") or ("world_countries" if world_scene else "")),
        "geographic_map_variant": str(map_asset_meta.get("map_variant") or ""),
        "geographic_map_variant_probabilities": dict(map_asset_meta.get("map_variant_probabilities", {})),
        "map_display_name": str(map_asset_meta.get("display_name") or ""),
        "map_region_noun": str(region_noun),
        "map_object_description": str(object_description),
        "map_source": dict(map_asset_meta.get("source", {})),
        "rows": int(rows),
        "cols": int(cols),
        "active_cells": [[int(row), int(col)] for row, col in active_cells],
        "legend_bins": [dict(item) for item in legend_bins],
        "question_params": {
            "marker_render_variant": str(marker_render_variant),
            "marker_render_variant_probabilities": dict(marker_render_variant_probabilities),
            "marker_region_ids": [str(region_id) for region_id in region_ids],
        },
        "marker_render_variant": str(marker_render_variant),
        "marker_render_variant_probabilities": dict(marker_render_variant_probabilities),
        "marker_value_min": int(value_min),
        "marker_value_max": int(value_max),
    }
    return dict(base_dataset), regions_by_id, list(region_ids), rng


def _marker_title_options() -> Tuple[str, ...]:
    return (
        "Regional Marker Map",
        "Bubble Indicator Map",
        "Marker Value Map",
        "Area Marker Overview",
        "Region Bubble Map",
    )


def _finalize_marker_dataset(
    *,
    base_dataset: Mapping[str, Any],
    regions_by_id: Mapping[str, Mapping[str, Any]],
    region_ids: Sequence[str],
    annotation_region_ids: Sequence[str],
    answer_type: str,
    answer_value: Any,
    target_count: int,
    target_count_probabilities: Mapping[str, float],
    question_params: Mapping[str, Any],
    show_marker_labels: bool,
) -> Dict[str, Any]:
    final_regions = [dict(regions_by_id[str(region_id)]) for region_id in region_ids]
    return {
        **dict(base_dataset),
        "region_count": int(len(final_regions)),
        "regions": final_regions,
        "regions_by_id": {str(region["region_id"]): dict(region) for region in final_regions},
        "annotation_region_ids": [str(region_id) for region_id in annotation_region_ids],
        "answer_value": answer_value,
        "answer_type": str(answer_type),
        "target_count": int(target_count),
        "target_count_probabilities": dict(target_count_probabilities),
        "question_params": {**dict(base_dataset.get("question_params", {})), **dict(question_params)},
        "target_bin_indices": [],
        "nonmatching_bin_indices": [],
        "show_marker_labels": bool(show_marker_labels),
    }


def construct_marker_threshold_dataset(
    *,
    scene_variant: str,
    threshold_direction: str,
    threshold_direction_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Constrain marker values so exactly the sampled target regions satisfy the threshold."""

    base, regions_by_id, region_ids, rng = _base_marker_map_dataset(
        scene_variant=str(scene_variant),
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="marker_threshold_count",
    )
    value_min = int(base["marker_value_min"])
    value_max = int(base["marker_value_max"])
    target_count, target_support, target_probabilities = sample_target_count(
        params,
        region_count=len(region_ids),
        instance_seed=int(instance_seed),
        namespace_suffix="marker_threshold_count",
    )
    target_ids = set(rng.sample(list(region_ids), int(target_count)))
    annotation_region_ids = _reading_order_region_ids(list(target_ids), dict(regions_by_id))
    if str(threshold_direction) == "greater_than":
        threshold_value = _balanced_int(
            list(range(int(value_min), int(value_max))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.marker_threshold_count.threshold.greater_than",
        )
        matching_values = list(range(int(threshold_value) + 1, int(value_max) + 1))
        nonmatching_values = list(range(int(value_min), int(threshold_value) + 1))
        threshold_phrase = f"greater than {threshold_value}"
    elif str(threshold_direction) == "less_than":
        threshold_value = _balanced_int(
            list(range(int(value_min) + 1, int(value_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.marker_threshold_count.threshold.less_than",
        )
        matching_values = list(range(int(value_min), int(threshold_value)))
        nonmatching_values = list(range(int(threshold_value), int(value_max) + 1))
        threshold_phrase = f"less than {threshold_value}"
    else:
        raise ValueError(f"unsupported marker threshold direction: {threshold_direction}")

    for region_id in region_ids:
        support = matching_values if str(region_id) in target_ids else nonmatching_values
        regions_by_id[str(region_id)]["marker_value"] = int(_choose_random(support, rng=rng))
        regions_by_id[str(region_id)]["is_target_marker_region"] = bool(str(region_id) in target_ids)

    return _finalize_marker_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_type="integer",
        answer_value=int(target_count),
        target_count=int(target_count),
        target_count_probabilities=target_probabilities,
        question_params={
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "marker_value_min": int(value_min),
            "marker_value_max": int(value_max),
            "target_count_support": [int(value) for value in target_support],
        },
        show_marker_labels=False,
    )


def construct_marker_extremum_dataset(
    *,
    scene_variant: str,
    extremum_direction: str,
    extremum_direction_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Constrain marker values so one visible region has the unique selected extremum."""

    base, regions_by_id, region_ids, rng = _base_marker_map_dataset(
        scene_variant=str(scene_variant),
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="marker_extremum_label",
    )
    value_min = int(base["marker_value_min"])
    value_max = int(base["marker_value_max"])
    answer_index = _balanced_int(
        list(range(len(region_ids))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.marker_extremum_label.answer_region_index",
    )
    answer_region_id = str(region_ids[int(answer_index)])
    if str(extremum_direction) == "largest":
        answer_marker_value = int(value_max)
        distractor_values = list(range(int(value_min), int(value_max)))
        extremum_word = "largest"
    elif str(extremum_direction) == "smallest":
        answer_marker_value = int(value_min)
        distractor_values = list(range(int(value_min) + 1, int(value_max) + 1))
        extremum_word = "smallest"
    else:
        raise ValueError(f"unsupported marker extremum direction: {extremum_direction}")

    for region_id in region_ids:
        if str(region_id) == str(answer_region_id):
            regions_by_id[str(region_id)]["marker_value"] = int(answer_marker_value)
            regions_by_id[str(region_id)]["is_target_marker_region"] = True
        else:
            regions_by_id[str(region_id)]["marker_value"] = int(_choose_random(distractor_values, rng=rng))
            regions_by_id[str(region_id)]["is_target_marker_region"] = False
    answer_value = str(regions_by_id[str(answer_region_id)]["marker_label"])
    return _finalize_marker_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=[str(answer_region_id)],
        answer_type="string",
        answer_value=str(answer_value),
        target_count=1,
        target_count_probabilities=uniform_probability_map((1,)),
        question_params={
            "extremum_direction": str(extremum_direction),
            "extremum_direction_probabilities": dict(extremum_direction_probabilities),
            "extremum_word": str(extremum_word),
            "answer_region_id": str(answer_region_id),
            "answer_marker_label": str(answer_value),
            "answer_marker_value": int(answer_marker_value),
            "marker_value_min": int(value_min),
            "marker_value_max": int(value_max),
        },
        show_marker_labels=True,
    )


__all__ = [
    "build_geographic_marker_regions",
    "construct_marker_extremum_dataset",
    "construct_marker_threshold_dataset",
]
