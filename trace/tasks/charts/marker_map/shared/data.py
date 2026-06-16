"""Synthetic-region data helpers for marker-map charts."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....shared.config_defaults import resolve_required_int_bounds
from ....shared.deterministic_sampling import uniform_probability_map
from .defaults import _GEN_DEFAULTS, SCENE_NAMESPACE
from .spatial_primitives import (
    _balanced_int,
    _grid_pair_support,
    _sample_connected_cells,
)


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


def build_synthetic_marker_regions(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    namespace_suffix: str,
) -> Tuple[int, int, List[Tuple[int, int]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Sample a connected synthetic grid-map shape and neutral legend bins for marker overlays."""

    row_min, row_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_row_count_min",
        max_key="region_row_count_max",
        fallback_min=4,
        fallback_max=7,
        context=f"{SCENE_NAMESPACE} region rows",
    )
    col_min, col_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_col_count_min",
        max_key="region_col_count_max",
        fallback_min=4,
        fallback_max=7,
        context=f"{SCENE_NAMESPACE} region cols",
    )
    region_min, region_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_count_min",
        max_key="region_count_max",
        fallback_min=9,
        fallback_max=14,
        context=f"{SCENE_NAMESPACE} total regions",
    )
    grid_pairs = _grid_pair_support(
        row_min=int(row_min),
        row_max=int(row_max),
        col_min=int(col_min),
        col_max=int(col_max),
        region_min=int(region_min),
    )
    if not grid_pairs:
        raise ValueError(f"no valid grid pairs for {SCENE_NAMESPACE} with current row/col/region bounds")
    pair_index = _balanced_int(
        list(range(len(grid_pairs))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.grid_pair",
    )
    rows, cols = grid_pairs[int(pair_index)]
    region_support = list(range(int(region_min), min(int(region_max), int(rows) * int(cols)) + 1))
    region_count = _balanced_int(
        region_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.region_count",
    )
    active_cells = _sample_connected_cells(rows=int(rows), cols=int(cols), target_count=int(region_count), rng=rng)

    bin_count = int(params.get("legend_bin_count", _GEN_DEFAULTS.get("legend_bin_count", 3)))
    legend_bins = _make_numeric_bins(int(bin_count))
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


def target_count_support(params: Mapping[str, Any], *, region_count: int) -> List[int]:
    answer_min, answer_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="count_answer_min",
        max_key="count_answer_max",
        fallback_min=1,
        fallback_max=5,
        context=f"{SCENE_NAMESPACE} answer count",
    )
    max_supported = min(int(answer_max), max(1, int(region_count) - 1))
    min_supported = min(int(answer_min), int(max_supported))
    return list(range(int(min_supported), int(max_supported) + 1))


def sample_target_count(
    params: Mapping[str, Any],
    *,
    region_count: int,
    instance_seed: int,
    namespace_suffix: str,
) -> Tuple[int, List[int], Dict[str, float]]:
    support = target_count_support(params, region_count=int(region_count))
    target_count = _balanced_int(
        support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.{namespace_suffix}.target_count",
    )
    return int(target_count), list(support), uniform_probability_map(tuple(support))


__all__ = [
    "_make_numeric_bins",
    "_marker_label_for_index",
    "build_synthetic_marker_regions",
    "sample_target_count",
    "target_count_support",
]
