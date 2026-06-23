"""Dataset sampling for region-map chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.deterministic_sampling import uniform_probability_map
from .assets import GEOGRAPHIC_MAP_ASSETS, WORLD_CATEGORY_TITLE_OPTIONS, WORLD_TITLE_OPTIONS, load_geographic_map_asset
from .data import (
    _make_category_bins,
    _make_numeric_bins,
    apply_bin,
    apply_numeric_value,
    assign_matching_bins,
    assign_region_display_labels,
    assign_values_from_bins,
    build_synthetic_regions,
    sample_count_from_param_range,
    sample_numeric_value_for_bin,
    sample_target_count,
)
from .defaults import SCENE_NAMESPACE, resolve_geographic_map_variant
from .projection import (
    WORLD_FILTERED_CONTINENTS,
    _centroid_lonlat_from_rings,
    _selected_geographic_region_adjacency,
    _synthetic_region_adjacency,
    _world_filtered_region_candidates,
)
from .spatial_primitives import _balanced_int, _choose_random, _reading_order_region_ids


def _world_selected_count_support(params: Mapping[str, Any], *, eligible_count: int) -> List[int]:
    count_min = int(
        params.get(
            "geographic_selected_region_count_min",
            params.get("world_selected_region_count_min", 18),
        )
    )
    count_max = int(
        params.get(
            "geographic_selected_region_count_max",
            params.get("world_selected_region_count_max", 28),
        )
    )
    if int(count_min) > int(count_max):
        raise ValueError(f"{SCENE_NAMESPACE} geographic selected region min cannot exceed max")
    high = min(int(count_max), int(eligible_count))
    low = min(int(count_min), int(high))
    return list(range(int(low), int(high) + 1))


def _build_geographic_regions(
    *,
    categorical: bool,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    namespace_suffix: str,
    force_world: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], List[int], Dict[str, Any]]:
    """Sample visible geographic regions and legend bins without task identity routing."""

    if bool(force_world):
        geographic_map_variant = "world_countries"
        geographic_map_variant_probabilities = {"world_countries": 1.0}
    else:
        geographic_map_variant, geographic_map_variant_probabilities = resolve_geographic_map_variant(
            params,
            instance_seed=int(instance_seed),
        )
    asset = load_geographic_map_asset(str(geographic_map_variant))
    asset_regions = [dict(region) for region in asset.get("regions", []) if isinstance(region, Mapping)]
    eligible_regions = [dict(region) for region in asset_regions if bool(region.get("question_eligible"))]
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

    bin_count = int(params.get("legend_bin_count", params.get("legend_bin_count_min", 4)))
    if "legend_bin_count" not in params and "legend_bin_count_max" in params:
        bin_min = int(params.get("legend_bin_count_min", 4))
        bin_max = int(params.get("legend_bin_count_max", 6))
        bin_count = _balanced_int(
            list(range(int(bin_min), int(bin_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.legend_bin_count",
        )
    legend_bins = _make_category_bins(int(bin_count), rng=rng) if bool(categorical) else _make_numeric_bins(int(bin_count))
    regions = _adapt_asset_regions(selected_asset_regions, asset=asset, legend_bins=legend_bins, rng=rng)
    asset_meta = _asset_meta(asset, map_variant=str(geographic_map_variant), probabilities=geographic_map_variant_probabilities)
    return list(regions), list(legend_bins), [str(region["region_id"]) for region in regions], list(selected_count_support), dict(asset_meta)


def _adapt_asset_regions(
    asset_regions: Sequence[Mapping[str, Any]],
    *,
    asset: Mapping[str, Any],
    legend_bins: Sequence[Mapping[str, Any]],
    rng,
) -> List[Dict[str, Any]]:
    region_prefix = str(asset.get("region_prefix") or "geo_region")
    regions: List[Dict[str, Any]] = []
    for asset_region in asset_regions:
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
                "bin_index": int(rng.randrange(int(len(legend_bins)))),
                "bin_label": str(legend_bins[0]["bin_label"]),
                "category": "",
                "is_reference_region": False,
            }
        )
    return list(regions)


def _asset_meta(asset: Mapping[str, Any], *, map_variant: str, probabilities: Mapping[str, float]) -> Dict[str, Any]:
    return {
        "asset_id": str(asset.get("asset_id") or GEOGRAPHIC_MAP_ASSETS[str(map_variant)]["asset_id"]),
        "map_variant": str(map_variant),
        "map_variant_probabilities": dict(probabilities),
        "display_name": str(asset.get("display_name") or ""),
        "region_noun": str(asset.get("region_noun") or "regions"),
        "object_description": str(asset.get("object_description") or ""),
        "title_options": [str(item) for item in asset.get("title_options", [])],
        "category_title_options": [str(item) for item in asset.get("category_title_options", [])],
        "source": dict(asset.get("source", {})) if isinstance(asset.get("source"), Mapping) else {},
    }


def _base_region_map_dataset(
    *,
    scene_variant: str,
    categorical: bool,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace_suffix: str,
    force_world: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], List[str], Any]:
    """Build a synthetic or geographic map base shared by semantic constructors."""

    if str(scene_variant) not in {"synthetic_region_map", "geographic_region_map"}:
        raise ValueError(f"unsupported region-map scene variant: {scene_variant}")
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.{namespace_suffix}.dataset")
    if str(scene_variant) == "geographic_region_map":
        rows = 0
        cols = 0
        active_cells: List[Tuple[int, int]] = []
        regions, legend_bins, _selected_region_ids, _selected_count_support, map_asset_meta = _build_geographic_regions(
            categorical=bool(categorical),
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
            namespace_suffix=str(namespace_suffix),
            force_world=bool(force_world),
        )
    else:
        map_asset_meta: Dict[str, Any] = {}
        rows, cols, active_cells, regions, legend_bins = build_synthetic_regions(
            categorical=bool(categorical),
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
            namespace_suffix=str(namespace_suffix),
        )
    regions_by_id = {str(region["region_id"]): dict(region) for region in regions}
    region_ids = _reading_order_region_ids([str(region["region_id"]) for region in regions], regions_by_id)
    world_scene = str(scene_variant) == "geographic_region_map"
    if world_scene and bool(categorical):
        title_options = list(map_asset_meta.get("category_title_options", [])) or list(WORLD_CATEGORY_TITLE_OPTIONS)
    else:
        title_options = list(map_asset_meta.get("title_options", [])) if world_scene else []
        if not title_options:
            title_options = list(WORLD_TITLE_OPTIONS) if world_scene else [
                "Regional Value Map",
                "District Value Map",
                "Service Area Map",
                "Planning Region Map",
                "County Indicator Map",
            ]
    region_noun = str(map_asset_meta.get("region_noun") or ("countries" if world_scene else "regions"))
    return (
        {
            "scene_title": str(_choose_random(title_options, rng=rng)),
            "scene_variant": str(scene_variant),
            "map_asset_id": str(map_asset_meta.get("asset_id") or ""),
            "geographic_map_variant": str(map_asset_meta.get("map_variant") or ""),
            "geographic_map_variant_probabilities": dict(map_asset_meta.get("map_variant_probabilities", {})),
            "map_display_name": str(map_asset_meta.get("display_name") or ""),
            "map_region_noun": str(region_noun),
            "map_object_description": str(map_asset_meta.get("object_description") or ""),
            "map_source": dict(map_asset_meta.get("source", {})),
            "rows": int(rows),
            "cols": int(cols),
            "active_cells": [[int(row), int(col)] for row, col in active_cells],
            "legend_bins": [dict(item) for item in legend_bins],
            "question_params": {},
        },
        dict(regions_by_id),
        list(region_ids),
        rng,
    )


def _finalize_region_dataset(
    *,
    base_dataset: Mapping[str, Any],
    regions_by_id: Mapping[str, Mapping[str, Any]],
    region_ids: Sequence[str],
    annotation_region_ids: Sequence[str],
    answer_value: int,
    target_count: int,
    target_count_probabilities: Mapping[str, float],
    question_params: Mapping[str, Any],
    target_bin_indices: Sequence[int],
    nonmatching_bin_indices: Sequence[int],
    threshold_direction: str = "",
) -> Dict[str, Any]:
    final_regions = [dict(regions_by_id[str(region_id)]) for region_id in region_ids]
    return {
        **dict(base_dataset),
        "region_count": int(len(final_regions)),
        "regions": final_regions,
        "regions_by_id": {str(region["region_id"]): dict(region) for region in final_regions},
        "annotation_region_ids": [str(region_id) for region_id in annotation_region_ids],
        "answer_value": int(answer_value),
        "answer_type": "integer",
        "target_count": int(target_count),
        "target_count_probabilities": dict(target_count_probabilities),
        "question_params": {**dict(base_dataset.get("question_params", {})), **dict(question_params)},
        "target_bin_indices": [int(value) for value in target_bin_indices],
        "nonmatching_bin_indices": [int(value) for value in nonmatching_bin_indices],
        "threshold_direction": str(threshold_direction),
    }


def _threshold_bins(
    *,
    threshold_direction: str,
    legend_bins: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
    instance_seed: int,
    namespace_suffix: str,
) -> Tuple[int, str, List[int], List[int]]:
    bin_count = int(len(legend_bins))
    if str(threshold_direction) == "greater_than":
        threshold_bin = _balanced_int(
            list(range(0, bin_count - 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.threshold.greater_than",
        )
        threshold_value = int(legend_bins[int(threshold_bin)]["upper"])
        return (
            int(threshold_value),
            f"greater than {threshold_value}",
            list(range(int(threshold_bin) + 1, bin_count)),
            list(range(0, int(threshold_bin) + 1)),
        )
    if str(threshold_direction) == "less_than":
        threshold_bin = _balanced_int(
            list(range(1, bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.threshold.less_than",
        )
        threshold_value = int(legend_bins[int(threshold_bin)]["lower"])
        return (
            int(threshold_value),
            f"less than {threshold_value}",
            list(range(0, int(threshold_bin))),
            list(range(int(threshold_bin), bin_count)),
        )
    raise ValueError(f"unsupported threshold direction: {threshold_direction}")


def construct_numeric_threshold_dataset(
    *,
    scene_variant: str,
    threshold_direction: str,
    threshold_direction_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Assign bins so exactly the selected regions satisfy one numeric threshold."""

    base, regions_by_id, region_ids, rng = _base_region_map_dataset(
        scene_variant=str(scene_variant),
        categorical=False,
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="numeric_threshold_regions",
    )
    target_count, target_support, target_probabilities = sample_target_count(
        params,
        region_count=len(region_ids),
        instance_seed=int(instance_seed),
        namespace_suffix="numeric_threshold_regions",
    )
    selected_ids = set(rng.sample(list(region_ids), int(target_count)))
    annotation_region_ids = _reading_order_region_ids(list(selected_ids), regions_by_id)
    threshold_value, threshold_phrase, target_bin_indices, nonmatching_bin_indices = _threshold_bins(
        threshold_direction=str(threshold_direction),
        legend_bins=base["legend_bins"],
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="numeric_threshold_regions",
    )
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=annotation_region_ids,
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(target_count),
        target_count=int(target_count),
        target_count_probabilities=target_probabilities,
        question_params={
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        },
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
        threshold_direction=str(threshold_direction),
    )


def construct_numeric_interval_dataset(
    *,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Assign bins so exactly the selected regions fall inside one numeric interval."""

    base, regions_by_id, region_ids, rng = _base_region_map_dataset(
        scene_variant=str(scene_variant),
        categorical=False,
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="numeric_interval_regions",
    )
    target_count, _target_support, target_probabilities = sample_target_count(
        params,
        region_count=len(region_ids),
        instance_seed=int(instance_seed),
        namespace_suffix="numeric_interval_regions",
    )
    selected_ids = set(rng.sample(list(region_ids), int(target_count)))
    annotation_region_ids = _reading_order_region_ids(list(selected_ids), regions_by_id)
    bin_count = int(len(base["legend_bins"]))
    max_span = min(4, max(2, bin_count - 1))
    span = _balanced_int(
        list(range(2, max_span + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.numeric_interval_regions.interval_span",
    )
    low_bin = _balanced_int(
        list(range(0, bin_count - int(span) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.numeric_interval_regions.interval_low_bin",
    )
    high_bin = int(low_bin) + int(span) - 1
    target_bin_indices = list(range(int(low_bin), int(high_bin) + 1))
    nonmatching_bin_indices = [index for index in range(bin_count) if index not in set(target_bin_indices)]
    lower = int(base["legend_bins"][int(low_bin)]["lower"])
    upper = int(base["legend_bins"][int(high_bin)]["upper"])
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=annotation_region_ids,
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(target_count),
        target_count=int(target_count),
        target_count_probabilities=target_probabilities,
        question_params={
            "interval_lower": int(lower),
            "interval_upper": int(upper),
            "interval_phrase": f"between {lower} and {upper}, inclusive",
            "interval_bin_span": int(span),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        },
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
    )


def construct_categorical_count_dataset(
    *,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Assign categories so exactly the selected regions match the target category."""

    base, regions_by_id, region_ids, rng = _base_region_map_dataset(
        scene_variant=str(scene_variant),
        categorical=True,
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="category_regions",
    )
    target_count, _target_support, target_probabilities = sample_target_count(
        params,
        region_count=len(region_ids),
        instance_seed=int(instance_seed),
        namespace_suffix="category_regions",
    )
    selected_ids = set(rng.sample(list(region_ids), int(target_count)))
    annotation_region_ids = _reading_order_region_ids(list(selected_ids), regions_by_id)
    bin_count = int(len(base["legend_bins"]))
    category_index = _balanced_int(
        list(range(bin_count)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.category_regions.category_index",
    )
    target_bin_indices = [int(category_index)]
    nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=annotation_region_ids,
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(target_count),
        target_count=int(target_count),
        target_count_probabilities=target_probabilities,
        question_params={
            "category_index": int(category_index),
            "category_label": str(base["legend_bins"][int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        },
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
    )


def _world_filtered_base(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    namespace_suffix: str,
    target_count: int,
    same_group_count: int = 0,
    categorical: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], List[str], List[str], str, List[str]]:
    """Create a world-map subset with a feasible target continent and distractors."""

    asset = load_geographic_map_asset("world_countries")
    asset_regions = [dict(region) for region in asset.get("regions", []) if isinstance(region, Mapping)]
    eligible_regions = _world_filtered_region_candidates([dict(region) for region in asset_regions if bool(region.get("question_eligible"))])
    selected_count_support = _world_selected_count_support(params, eligible_count=len(eligible_regions))
    selected_count = _balanced_int(
        selected_count_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.selected_region_count",
    )
    regions_by_continent = {
        continent: [dict(region) for region in eligible_regions if str(region.get("continent") or "") == str(continent)]
        for continent in WORLD_FILTERED_CONTINENTS
    }
    feasible_continents = [
        str(continent)
        for continent, continent_regions in regions_by_continent.items()
        if len(continent_regions) >= int(target_count) + int(same_group_count)
        and (len(eligible_regions) - len(continent_regions)) >= int(selected_count) - int(target_count) - int(same_group_count)
    ]
    if not feasible_continents:
        raise ValueError("no feasible continent can support the requested filtered world map")
    continent_index = _balanced_int(
        list(range(len(feasible_continents))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.target_continent",
    )
    target_continent = str(feasible_continents[int(continent_index)])
    same_continent_pool = sorted(regions_by_continent[str(target_continent)], key=lambda item: str(item["region_id"]))
    target_regions = rng.sample(same_continent_pool, int(target_count))
    remaining_same_pool = [dict(region) for region in same_continent_pool if str(region["region_id"]) not in {str(item["region_id"]) for item in target_regions}]
    same_group_distractors = rng.sample(remaining_same_pool, int(same_group_count)) if int(same_group_count) > 0 else []
    other_pool = sorted(
        [dict(region) for region in eligible_regions if str(region.get("continent") or "") != str(target_continent)],
        key=lambda item: str(item["region_id"]),
    )
    other_count = int(selected_count) - int(target_count) - int(same_group_count)
    distractor_regions = rng.sample(other_pool, int(other_count))
    selected_asset_regions = list(target_regions) + list(same_group_distractors) + list(distractor_regions)
    rng.shuffle(selected_asset_regions)
    bin_count = int(params.get("legend_bin_count", params.get("legend_bin_count_min", 4)))
    if "legend_bin_count" not in params and "legend_bin_count_max" in params:
        bin_min = int(params.get("legend_bin_count_min", 4))
        bin_max = int(params.get("legend_bin_count_max", 6))
        bin_count = _balanced_int(
            list(range(int(bin_min), int(bin_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.legend_bin_count",
        )
    legend_bins = _make_category_bins(int(bin_count), rng=rng) if bool(categorical) else _make_numeric_bins(int(bin_count))
    regions = _adapt_asset_regions(selected_asset_regions, asset=asset, legend_bins=legend_bins, rng=rng)
    regions_by_id = {str(region["region_id"]): dict(region) for region in regions}
    region_ids = _reading_order_region_ids([str(region["region_id"]) for region in regions], regions_by_id)
    asset_meta = _asset_meta(asset, map_variant="world_countries", probabilities={"world_countries": 1.0})
    base = {
        "scene_title": str(_choose_random(asset_meta.get("title_options") or WORLD_TITLE_OPTIONS, rng=rng)),
        "scene_variant": "geographic_region_map",
        "map_asset_id": str(asset_meta["asset_id"]),
        "geographic_map_variant": "world_countries",
        "geographic_map_variant_probabilities": {"world_countries": 1.0},
        "map_display_name": str(asset_meta.get("display_name") or "World"),
        "map_region_noun": str(asset_meta.get("region_noun") or "countries"),
        "map_object_description": str(asset_meta.get("object_description") or ""),
        "map_source": dict(asset_meta.get("source", {})),
        "rows": 0,
        "cols": 0,
        "active_cells": [],
        "legend_bins": [dict(item) for item in legend_bins],
        "question_params": {},
    }
    target_asset_ids = {str(item["region_id"]) for item in target_regions}
    annotation_region_ids = _reading_order_region_ids(
        [
            str(region_id)
            for region_id, region in regions_by_id.items()
            if str(region.get("asset_region_id") or "") in target_asset_ids
        ],
        regions_by_id,
    )
    same_group_ids = [
        f"country_{region['region_id']}"
        for region in same_group_distractors
    ]
    return dict(base), dict(regions_by_id), list(region_ids), list(annotation_region_ids), str(target_continent), list(same_group_ids)


def construct_continent_count_dataset(*, params: Mapping[str, Any], instance_seed: int) -> Dict[str, Any]:
    """Select world regions so the answer is the count in one visible continent."""

    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.continent_regions.dataset")
    selected_support = _world_selected_count_support(params, eligible_count=1000)
    selected_count = min(max(selected_support[0], 16), selected_support[-1])
    target_count, _target_support, target_probabilities = sample_target_count(
        params,
        region_count=int(selected_count),
        instance_seed=int(instance_seed),
        namespace_suffix="continent_regions",
    )
    base, regions_by_id, region_ids, annotation_region_ids, continent, _same_group_ids = _world_filtered_base(
        params=params,
        instance_seed=int(instance_seed),
        rng=rng,
        namespace_suffix="continent_regions",
        target_count=int(target_count),
    )
    for region_id in region_ids:
        apply_bin(
            regions_by_id,
            region_id=str(region_id),
            bin_index=int(rng.randrange(len(base["legend_bins"]))),
            legend_bins=base["legend_bins"],
        )
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(len(annotation_region_ids)),
        target_count=int(len(annotation_region_ids)),
        target_count_probabilities=target_probabilities,
        question_params={
            "continent_label": str(continent),
            "target_continent": str(continent),
            "target_bin_indices": [],
        },
        target_bin_indices=[],
        nonmatching_bin_indices=list(range(len(base["legend_bins"]))),
    )


def construct_continent_category_dataset(*, params: Mapping[str, Any], instance_seed: int) -> Dict[str, Any]:
    """Select world regions so continent and category predicates bind the answer."""

    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.continent_category_regions.dataset")
    target_count, _target_support, target_probabilities = sample_target_count(
        params,
        region_count=24,
        instance_seed=int(instance_seed),
        namespace_suffix="continent_category_regions",
    )
    base, regions_by_id, region_ids, annotation_region_ids, continent, _same_group_ids = _world_filtered_base(
        params=params,
        instance_seed=int(instance_seed),
        rng=rng,
        namespace_suffix="continent_category_regions",
        target_count=int(target_count),
        categorical=True,
    )
    category_index = _balanced_int(
        list(range(len(base["legend_bins"]))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.continent_category_regions.category_index",
    )
    target_bin_indices = [int(category_index)]
    nonmatching_bin_indices = [index for index in range(len(base["legend_bins"])) if int(index) != int(category_index)]
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=annotation_region_ids,
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(len(annotation_region_ids)),
        target_count=int(len(annotation_region_ids)),
        target_count_probabilities=target_probabilities,
        question_params={
            "continent_label": str(continent),
            "target_continent": str(continent),
            "category_index": int(category_index),
            "category_label": str(base["legend_bins"][int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        },
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
    )


def construct_continent_threshold_dataset(
    *,
    threshold_direction: str,
    threshold_direction_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Select world regions so continent and numeric threshold jointly bind the answer."""

    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.continent_threshold_regions.dataset")
    target_count, _target_support, target_probabilities = sample_target_count(
        params,
        region_count=24,
        instance_seed=int(instance_seed),
        namespace_suffix="continent_threshold_regions",
    )
    base, regions_by_id, region_ids, annotation_region_ids, continent, _same_group_ids = _world_filtered_base(
        params=params,
        instance_seed=int(instance_seed),
        rng=rng,
        namespace_suffix="continent_threshold_regions",
        target_count=int(target_count),
    )
    threshold_value, threshold_phrase, target_bin_indices, nonmatching_bin_indices = _threshold_bins(
        threshold_direction=str(threshold_direction),
        legend_bins=base["legend_bins"],
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="continent_threshold_regions",
    )
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=annotation_region_ids,
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(len(annotation_region_ids)),
        target_count=int(len(annotation_region_ids)),
        target_count_probabilities=target_probabilities,
        question_params={
            "continent_label": str(continent),
            "target_continent": str(continent),
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        },
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
        threshold_direction=str(threshold_direction),
    )


def construct_named_region_set_total_dataset(
    *,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Label selected regions and expose visible values whose sum is the answer."""

    base, regions_by_id, region_ids, rng = _base_region_map_dataset(
        scene_variant=str(scene_variant),
        categorical=False,
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="named_region_set_total",
    )
    assign_region_display_labels(regions_by_id)
    for region_id in region_ids:
        value = sample_numeric_value_for_bin(int(rng.randrange(len(base["legend_bins"]))), base["legend_bins"], rng=rng)
        apply_numeric_value(regions_by_id, region_id=str(region_id), value=int(value), legend_bins=base["legend_bins"])
    target_count, _support, target_probabilities = sample_count_from_param_range(
        params,
        min_key="region_set_size_min",
        max_key="region_set_size_max",
        fallback_min=3,
        fallback_max=5,
        max_supported=max(1, len(region_ids) - 1),
        instance_seed=int(instance_seed),
        namespace_suffix="named_region_set_total.region_set_size",
    )
    annotation_region_ids = _reading_order_region_ids(rng.sample(list(region_ids), int(target_count)), regions_by_id)
    labels = [str(regions_by_id[str(region_id)].get("region_label") or "") for region_id in annotation_region_ids]
    target_bin_indices = sorted({int(regions_by_id[str(region_id)]["bin_index"]) for region_id in annotation_region_ids})
    answer_value = int(sum(int(regions_by_id[str(region_id)]["region_value"]) for region_id in annotation_region_ids))
    set_name = str(_choose_random(("Focus set", "Review set", "Priority set", "Audit set", "Target set"), rng=rng))
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(answer_value),
        target_count=int(target_count),
        target_count_probabilities=target_probabilities,
        question_params={
            "region_set_name": str(set_name),
            "region_set_region_ids": [str(region_id) for region_id in annotation_region_ids],
            "region_set_labels": labels,
            "region_set_label_list": ", ".join(f'"{label}"' for label in labels),
            "target_region_values": {
                str(region_id): int(regions_by_id[str(region_id)]["region_value"])
                for region_id in annotation_region_ids
            },
            "target_bin_indices": [int(value) for value in target_bin_indices],
        },
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=[index for index in range(len(base["legend_bins"])) if index not in set(target_bin_indices)],
    )


def construct_group_filtered_total_dataset(
    *,
    threshold_direction: str,
    threshold_direction_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Build a world-map value-sum task with same-continent threshold distractors."""

    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.group_filtered_total.dataset")
    target_count, _support, target_probabilities = sample_count_from_param_range(
        params,
        min_key="group_filtered_target_count_min",
        max_key="group_filtered_target_count_max",
        fallback_min=2,
        fallback_max=5,
        max_supported=12,
        instance_seed=int(instance_seed),
        namespace_suffix="group_filtered_total.target_count",
    )
    same_group_count, _same_support, _same_probabilities = sample_count_from_param_range(
        params,
        min_key="group_filtered_same_group_distractor_count_min",
        max_key="group_filtered_same_group_distractor_count_max",
        fallback_min=1,
        fallback_max=3,
        max_supported=6,
        instance_seed=int(instance_seed),
        namespace_suffix="group_filtered_total.same_group_distractor_count",
    )
    base, regions_by_id, region_ids, annotation_region_ids, continent, same_group_ids = _world_filtered_base(
        params=params,
        instance_seed=int(instance_seed),
        rng=rng,
        namespace_suffix="group_filtered_total",
        target_count=int(target_count),
        same_group_count=int(same_group_count),
    )
    threshold_value, threshold_phrase, target_bin_indices, nonmatching_bin_indices = _threshold_bins(
        threshold_direction=str(threshold_direction),
        legend_bins=base["legend_bins"],
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="group_filtered_total",
    )
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=annotation_region_ids,
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    assign_values_from_bins(regions_by_id=regions_by_id, region_ids=region_ids, legend_bins=base["legend_bins"], rng=rng)
    answer_value = int(sum(int(regions_by_id[str(region_id)]["region_value"]) for region_id in annotation_region_ids))
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(answer_value),
        target_count=int(target_count),
        target_count_probabilities=target_probabilities,
        question_params={
            "continent_label": str(continent),
            "target_continent": str(continent),
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
            "same_group_distractor_region_ids": [str(region_id) for region_id in same_group_ids],
            "target_region_values": {
                str(region_id): int(regions_by_id[str(region_id)]["region_value"])
                for region_id in annotation_region_ids
            },
        },
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
        threshold_direction=str(threshold_direction),
    )


def _synthetic_adjacent_base(
    *,
    categorical: bool,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace_suffix: str,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], List[str], List[str], str, Any, Dict[str, float]]:
    """Choose a highlighted synthetic region with enough neighboring answer candidates."""

    base, regions_by_id, region_ids, rng = _base_region_map_dataset(
        scene_variant="synthetic_region_map",
        categorical=bool(categorical),
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix=str(namespace_suffix),
    )
    adjacency = _synthetic_region_adjacency(regions_by_id)
    answer_min = int(params.get("count_answer_min", 1))
    answer_max = int(params.get("count_answer_max", 4))
    feasible_counts = sorted(
        {
            count
            for neighbor_ids in adjacency.values()
            for count in range(int(answer_min), min(int(answer_max), len(neighbor_ids)) + 1)
        }
    )
    if not feasible_counts:
        raise ValueError("no feasible adjacent-region count in selected map")
    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        target_count = feasible_counts[abs(int(sample_cursor)) % len(feasible_counts)]
    else:
        target_count = _balanced_int(
            feasible_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.adjacent_target_count",
        )
    target_count_probabilities = uniform_probability_map(tuple(feasible_counts))
    reference_candidates = [
        str(region_id)
        for region_id, neighbor_ids in adjacency.items()
        if len(neighbor_ids) >= int(target_count)
    ]
    reference_index = _balanced_int(
        list(range(len(reference_candidates))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.reference_region",
    )
    reference_region_id = str(reference_candidates[int(reference_index)])
    regions_by_id[str(reference_region_id)]["is_reference_region"] = True
    neighbor_ids = list(adjacency.get(str(reference_region_id), []))
    annotation_region_ids = _reading_order_region_ids(rng.sample(neighbor_ids, int(target_count)), regions_by_id)
    base["question_params"] = {
        "reference_region_id": str(reference_region_id),
        "adjacent_neighbor_region_ids": [str(value) for value in neighbor_ids],
    }
    return (
        dict(base),
        dict(regions_by_id),
        list(region_ids),
        list(annotation_region_ids),
        str(reference_region_id),
        rng,
        dict(target_count_probabilities),
    )


def construct_adjacent_same_category_dataset(*, params: Mapping[str, Any], instance_seed: int) -> Dict[str, Any]:
    """Color neighbors so selected adjacent regions match the highlighted category."""

    base, regions_by_id, region_ids, annotation_region_ids, reference_region_id, rng, target_probabilities = _synthetic_adjacent_base(
        categorical=True,
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="same_category_neighbors",
    )
    category_index = _balanced_int(
        list(range(len(base["legend_bins"]))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.same_category_neighbors.category_index",
    )
    target_bin_indices = [int(category_index)]
    nonmatching_bin_indices = [index for index in range(len(base["legend_bins"])) if int(index) != int(category_index)]
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=[*annotation_region_ids, str(reference_region_id)],
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    qparams = {
        **dict(base["question_params"]),
        "category_index": int(category_index),
        "category_label": str(base["legend_bins"][int(category_index)]["bin_label"]),
        "target_bin_indices": [int(category_index)],
    }
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(len(annotation_region_ids)),
        target_count=int(len(annotation_region_ids)),
        target_count_probabilities=target_probabilities,
        question_params=qparams,
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
    )


def construct_adjacent_category_dataset(*, params: Mapping[str, Any], instance_seed: int) -> Dict[str, Any]:
    """Color neighbors so selected adjacent regions match a prompted category."""

    base, regions_by_id, region_ids, annotation_region_ids, _reference_region_id, rng, target_probabilities = _synthetic_adjacent_base(
        categorical=True,
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="category_neighbors",
    )
    category_index = _balanced_int(
        list(range(len(base["legend_bins"]))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.category_neighbors.category_index",
    )
    target_bin_indices = [int(category_index)]
    nonmatching_bin_indices = [index for index in range(len(base["legend_bins"])) if int(index) != int(category_index)]
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=annotation_region_ids,
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    qparams = {
        **dict(base["question_params"]),
        "category_index": int(category_index),
        "category_label": str(base["legend_bins"][int(category_index)]["bin_label"]),
        "target_bin_indices": [int(category_index)],
    }
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(len(annotation_region_ids)),
        target_count=int(len(annotation_region_ids)),
        target_count_probabilities=target_probabilities,
        question_params=qparams,
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
    )


def construct_adjacent_numeric_threshold_dataset(
    *,
    threshold_direction: str,
    threshold_direction_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Assign neighbor bins so selected adjacent regions satisfy one threshold."""

    base, regions_by_id, region_ids, annotation_region_ids, _reference_region_id, rng, target_probabilities = _synthetic_adjacent_base(
        categorical=False,
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="threshold_neighbors",
    )
    threshold_value, threshold_phrase, target_bin_indices, nonmatching_bin_indices = _threshold_bins(
        threshold_direction=str(threshold_direction),
        legend_bins=base["legend_bins"],
        params=params,
        instance_seed=int(instance_seed),
        namespace_suffix="threshold_neighbors",
    )
    assign_matching_bins(
        regions_by_id=regions_by_id,
        selected_ids=annotation_region_ids,
        matching_bins=target_bin_indices,
        nonmatching_bins=nonmatching_bin_indices,
        legend_bins=base["legend_bins"],
        rng=rng,
    )
    qparams = {
        **dict(base["question_params"]),
        "threshold_direction": str(threshold_direction),
        "threshold_direction_probabilities": dict(threshold_direction_probabilities),
        "threshold_value": int(threshold_value),
        "threshold_phrase": str(threshold_phrase),
        "target_bin_indices": [int(value) for value in target_bin_indices],
    }
    return _finalize_region_dataset(
        base_dataset=base,
        regions_by_id=regions_by_id,
        region_ids=region_ids,
        annotation_region_ids=annotation_region_ids,
        answer_value=int(len(annotation_region_ids)),
        target_count=int(len(annotation_region_ids)),
        target_count_probabilities=target_probabilities,
        question_params=qparams,
        target_bin_indices=target_bin_indices,
        nonmatching_bin_indices=nonmatching_bin_indices,
        threshold_direction=str(threshold_direction),
    )


__all__ = [
    "construct_adjacent_category_dataset",
    "construct_adjacent_numeric_threshold_dataset",
    "construct_adjacent_same_category_dataset",
    "construct_categorical_count_dataset",
    "construct_continent_category_dataset",
    "construct_continent_count_dataset",
    "construct_continent_threshold_dataset",
    "construct_group_filtered_total_dataset",
    "construct_named_region_set_total_dataset",
    "construct_numeric_interval_dataset",
    "construct_numeric_threshold_dataset",
]
