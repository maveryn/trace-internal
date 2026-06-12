"""Geographic-region dataset helpers for marker-map tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from .choropleth_assets import GEOGRAPHIC_MAP_ASSETS, load_geographic_map_asset
from .choropleth_config import _GEN_DEFAULTS, SCENE_NAMESPACE, resolve_geographic_map_variant
from .choropleth_geography import _centroid_lonlat_from_rings
from .choropleth_geometry import _balanced_int
from .choropleth_region_dataset import _make_numeric_bins


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


__all__ = [
    "_world_selected_count_support",
    "build_geographic_marker_regions",
]
