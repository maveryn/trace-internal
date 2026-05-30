"""Synthetic-region dataset helpers for choropleth map tasks."""

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

def _marker_label_for_index(index: int) -> str:
    """Return spreadsheet-style labels A, B, ..., Z, AA, AB for map regions."""

    n = int(index)
    letters: List[str] = []
    while True:
        letters.append(chr(ord("A") + (n % 26)))
        n = (n // 26) - 1
        if n < 0:
            break
    return "".join(reversed(letters))

def _make_numeric_bins(bin_count: int) -> List[Dict[str, Any]]:
    bins: List[Dict[str, Any]] = []
    for index in range(int(bin_count)):
        lower = int(math.floor(index * 100 / int(bin_count)))
        upper = int(math.floor((index + 1) * 100 / int(bin_count)) - 1)
        bins.append(
            {
                "bin_id": f"legend_bin_{index}",
                "bin_index": int(index),
                "bin_label": f"{lower}-{upper}",
                "lower": int(lower),
                "upper": int(upper),
                "category": "",
            }
        )
    return bins

def _make_category_bins(bin_count: int, *, rng) -> List[Dict[str, Any]]:
    resolved_labels = resolve_chart_category_labels(
        rng,
        count=int(bin_count),
        max_chars=14,
        allow_spaces=True,
    )
    label_source = {
        "label_source_kind": str(resolved_labels.label_source_kind),
        "label_pool_kind": str(resolved_labels.label_pool_kind),
        "label_bucket": str(resolved_labels.label_bucket),
        "label_manifest": str(resolved_labels.label_manifest),
        "label_filter": dict(resolved_labels.label_filter),
        "label_bucket_probabilities": dict(resolved_labels.label_bucket_probabilities),
    }
    labels = [str(label) for label in resolved_labels.labels]
    return [
        {
            "bin_id": f"legend_bin_{index}",
            "bin_index": int(index),
            "bin_label": str(label),
            "lower": None,
            "upper": None,
            "category": str(label),
            "label_source": dict(label_source),
        }
        for index, label in enumerate(labels)
    ]

def _build_regions(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
) -> Tuple[int, int, List[Tuple[int, int]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    row_min, row_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_row_count_min",
        max_key="region_row_count_max",
        fallback_min=5,
        fallback_max=7,
        context=f"{TASK_ID} region rows",
    )
    col_min, col_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_col_count_min",
        max_key="region_col_count_max",
        fallback_min=5,
        fallback_max=7,
        context=f"{TASK_ID} region cols",
    )
    region_min, region_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_count_min",
        max_key="region_count_max",
        fallback_min=14,
        fallback_max=28,
        context=f"{TASK_ID} total regions",
    )
    grid_pairs = _grid_pair_support(
        row_min=int(row_min),
        row_max=int(row_max),
        col_min=int(col_min),
        col_max=int(col_max),
        region_min=int(region_min),
    )
    if not grid_pairs:
        raise ValueError(f"no valid grid pairs for {TASK_ID} with current row/col/region bounds")
    pair_index = _balanced_int(
        list(range(len(grid_pairs))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.grid_pair",
    )
    rows, cols = grid_pairs[int(pair_index)]
    region_support = list(range(int(region_min), min(int(region_max), int(rows) * int(cols)) + 1))
    region_count = _balanced_int(
        region_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_id}.region_count",
    )
    active_cells = _sample_connected_cells(rows=int(rows), cols=int(cols), target_count=int(region_count), rng=rng)

    if "legend_bin_count" in params:
        bin_min = bin_max = int(params["legend_bin_count"])
    else:
        bin_min, bin_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="legend_bin_count_min",
            max_key="legend_bin_count_max",
            fallback_min=4,
            fallback_max=8,
            context=f"{TASK_ID} legend bins",
        )
    bin_count = _balanced_int(
        list(range(int(bin_min), int(bin_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_id}.legend_bin_count",
    )
    legend_bins = (
        _make_category_bins(int(bin_count), rng=rng)
        if _is_categorical_query_id(str(query_id))
        else _make_numeric_bins(int(bin_count))
    )

    regions: List[Dict[str, Any]] = []
    for index, (row, col) in enumerate(active_cells):
        regions.append(
            {
                "region_id": f"region_{index}",
                "row": int(row),
                "col": int(col),
                "bin_index": int(rng.randrange(int(bin_count))),
                "bin_label": str(legend_bins[0]["bin_label"]),
            }
        )
    return int(rows), int(cols), list(active_cells), list(regions), list(legend_bins)

def _apply_bin(regions_by_id: Dict[str, Dict[str, Any]], *, region_id: str, bin_index: int, legend_bins: Sequence[Mapping[str, Any]]) -> None:
    bin_spec = dict(legend_bins[int(bin_index)])
    regions_by_id[str(region_id)]["bin_index"] = int(bin_index)
    regions_by_id[str(region_id)]["bin_label"] = str(bin_spec["bin_label"])
    regions_by_id[str(region_id)]["bin_lower"] = bin_spec.get("lower")
    regions_by_id[str(region_id)]["bin_upper"] = bin_spec.get("upper")
    regions_by_id[str(region_id)]["category"] = str(bin_spec.get("category") or "")

def _target_count_support(params: Mapping[str, Any], *, region_count: int) -> List[int]:
    answer_min, answer_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="count_answer_min",
        max_key="count_answer_max",
        fallback_min=3,
        fallback_max=14,
        context=f"{TASK_ID} answer count",
    )
    max_supported = min(int(answer_max), max(1, int(region_count) - 1))
    min_supported = min(int(answer_min), int(max_supported))
    return list(range(int(min_supported), int(max_supported) + 1))

def _sample_target_count(
    params: Mapping[str, Any],
    *,
    region_count: int,
    query_id: str,
    instance_seed: int,
) -> Tuple[int, List[int]]:
    support = _target_count_support(params, region_count=int(region_count))
    return (
        _balanced_int(
            support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.target_count",
        ),
        list(support),
    )

def _sample_count_from_param_range(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    max_supported: int,
    query_id: str,
    instance_seed: int,
    namespace_suffix: str,
) -> Tuple[int, List[int]]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"{TASK_ID} {namespace_suffix}",
    )
    support = list(range(min(int(low), int(max_supported)), min(int(high), int(max_supported)) + 1))
    support = [int(value) for value in support if int(value) >= int(low)]
    if not support:
        support = [max(1, min(int(max_supported), int(low)))]
    return (
        _balanced_int(
            support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.{namespace_suffix}",
        ),
        list(support),
    )

def _value_bin_index(value: int, legend_bins: Sequence[Mapping[str, Any]]) -> int:
    for index, bin_spec in enumerate(legend_bins):
        lower = bin_spec.get("lower")
        upper = bin_spec.get("upper")
        if lower is None or upper is None:
            continue
        if int(lower) <= int(value) <= int(upper):
            return int(index)
    return max(0, min(len(legend_bins) - 1, int(value) * max(1, len(legend_bins)) // 100))

def _sample_numeric_value_for_bin(bin_index: int, legend_bins: Sequence[Mapping[str, Any]], *, rng) -> int:
    bin_spec = dict(legend_bins[int(bin_index)])
    lower = int(bin_spec.get("lower") if bin_spec.get("lower") is not None else 0)
    upper = int(bin_spec.get("upper") if bin_spec.get("upper") is not None else 99)
    if int(upper) < int(lower):
        upper = int(lower)
    return int(rng.randrange(int(lower), int(upper) + 1))

def _apply_numeric_value(
    regions_by_id: Dict[str, Dict[str, Any]],
    *,
    region_id: str,
    value: int,
    legend_bins: Sequence[Mapping[str, Any]],
) -> None:
    bin_index = _value_bin_index(int(value), legend_bins)
    _apply_bin(
        regions_by_id,
        region_id=str(region_id),
        bin_index=int(bin_index),
        legend_bins=legend_bins,
    )
    regions_by_id[str(region_id)]["region_value"] = int(value)

def _assign_values_from_bins(
    *,
    regions_by_id: Dict[str, Dict[str, Any]],
    region_ids: Sequence[str],
    legend_bins: Sequence[Mapping[str, Any]],
    rng,
) -> None:
    for region_id in region_ids:
        bin_index = int(regions_by_id[str(region_id)]["bin_index"])
        regions_by_id[str(region_id)]["region_value"] = _sample_numeric_value_for_bin(
            int(bin_index),
            legend_bins,
            rng=rng,
        )

def _assign_region_display_labels(regions_by_id: Dict[str, Dict[str, Any]]) -> None:
    ordered_ids = _reading_order_region_ids(list(regions_by_id.keys()), regions_by_id)
    for index, region_id in enumerate(ordered_ids):
        regions_by_id[str(region_id)]["region_label"] = _marker_label_for_index(int(index))

def _assign_matching_bins(
    *,
    regions_by_id: Dict[str, Dict[str, Any]],
    selected_ids: Sequence[str],
    matching_bins: Sequence[int],
    nonmatching_bins: Sequence[int],
    legend_bins: Sequence[Mapping[str, Any]],
    rng,
) -> None:
    selected = {str(region_id) for region_id in selected_ids}
    for region_id in sorted(regions_by_id.keys(), key=_region_sort_key):
        support = list(matching_bins) if str(region_id) in selected else list(nonmatching_bins)
        _apply_bin(
            regions_by_id,
            region_id=str(region_id),
            bin_index=int(_choose_random(support, rng=rng)),
            legend_bins=legend_bins,
        )


__all__ = [
    '_marker_label_for_index',
    '_make_numeric_bins',
    '_make_category_bins',
    '_build_regions',
    '_apply_bin',
    '_target_count_support',
    '_sample_target_count',
    '_sample_count_from_param_range',
    '_value_bin_index',
    '_sample_numeric_value_for_bin',
    '_apply_numeric_value',
    '_assign_values_from_bins',
    '_assign_region_display_labels',
    '_assign_matching_bins',
]
