"""Shared dataset builders and render defaults for region+legend map tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.color_distance import DEFAULT_COLOR_DISTANCE_SPACE, sample_color_palette_with_distance_constraints
from ...shared.config_defaults import (
    group_default,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
)
from ...shared.deterministic_sampling import resolve_selection_index
from .common import resolve_maps_axis_variant


Cell = Tuple[int, int]

SUPPORTED_MAP_REGION_SCENE_VARIANTS: Tuple[str, ...] = (
    "map_strip",
    "map_card",
    "map_outline",
    "region_map",
)
SUPPORTED_MAP_REGION_TASK_VARIANTS: Tuple[str, ...] = (
    "max_category_region",
    "min_category_region",
    "matches_legend_bin",
)
_CATEGORY_LABELS: Tuple[str, ...] = ("Low", "Moderate", "High", "Very high")


@dataclass(frozen=True)
class MapRegionDefaults:
    """Default generation bounds for stylized choropleth region maps."""

    region_count_min: int = 5
    region_count_max: int = 7
    grid_cols_min: int = 6
    grid_cols_max: int = 7
    grid_rows_min: int = 4
    grid_rows_max: int = 5
    category_count: int = 4
    color_min_distance: float = 60.0
    color_channel_min: int = 68
    color_channel_max: int = 224
    min_cells_per_region: int = 2


@dataclass(frozen=True)
class MapRegionRenderParams:
    """Resolved rendering knobs for region+legend map scenes."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    map_panel_width_px: int
    map_panel_height_px: int
    map_padding_px: int
    legend_panel_width_px: int
    legend_panel_height_px: int
    panel_gap_px: int
    legend_item_gap_px: int
    legend_swatch_size_px: int
    region_border_width_px: int
    outer_border_width_px: int
    panel_corner_radius_px: int
    label_font_size_px: int
    legend_font_size_px: int
    title_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    legend_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    label_color_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]
    divider_rgb: Tuple[int, int, int]


def _resolve_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer generation or rendering parameter."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def resolve_region_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active region-map scene variant."""

    return resolve_maps_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_MAP_REGION_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_region_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic region-association variant."""

    return resolve_maps_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_MAP_REGION_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_region_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> MapRegionRenderParams:
    """Resolve rendering params for region+legend map scenes."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        raw = params.get(str(key), group_default(render_defaults, str(key), list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must be a length-3 RGB sequence")
        return tuple(int(value) for value in raw)

    return MapRegionRenderParams(
        canvas_width=int(_resolve_int_param(params, render_defaults, "canvas_width", 1200)),
        canvas_height=int(_resolve_int_param(params, render_defaults, "canvas_height", 820)),
        scene_margin_left_px=int(_resolve_int_param(params, render_defaults, "scene_margin_left_px", 56)),
        scene_margin_right_px=int(_resolve_int_param(params, render_defaults, "scene_margin_right_px", 56)),
        scene_margin_top_px=int(_resolve_int_param(params, render_defaults, "scene_margin_top_px", 56)),
        scene_margin_bottom_px=int(_resolve_int_param(params, render_defaults, "scene_margin_bottom_px", 56)),
        map_panel_width_px=int(_resolve_int_param(params, render_defaults, "map_panel_width_px", 702)),
        map_panel_height_px=int(_resolve_int_param(params, render_defaults, "map_panel_height_px", 560)),
        map_padding_px=int(_resolve_int_param(params, render_defaults, "map_padding_px", 20)),
        legend_panel_width_px=int(_resolve_int_param(params, render_defaults, "legend_panel_width_px", 270)),
        legend_panel_height_px=int(_resolve_int_param(params, render_defaults, "legend_panel_height_px", 280)),
        panel_gap_px=int(_resolve_int_param(params, render_defaults, "panel_gap_px", 40)),
        legend_item_gap_px=int(_resolve_int_param(params, render_defaults, "legend_item_gap_px", 18)),
        legend_swatch_size_px=int(_resolve_int_param(params, render_defaults, "legend_swatch_size_px", 28)),
        region_border_width_px=int(_resolve_int_param(params, render_defaults, "region_border_width_px", 3)),
        outer_border_width_px=int(_resolve_int_param(params, render_defaults, "outer_border_width_px", 3)),
        panel_corner_radius_px=int(_resolve_int_param(params, render_defaults, "panel_corner_radius_px", 28)),
        label_font_size_px=int(_resolve_int_param(params, render_defaults, "label_font_size_px", 30)),
        legend_font_size_px=int(_resolve_int_param(params, render_defaults, "legend_font_size_px", 26)),
        title_font_size_px=int(_resolve_int_param(params, render_defaults, "title_font_size_px", 30)),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        legend_fill_rgb=_triple("legend_fill_rgb", (251, 252, 255)),
        border_color_rgb=_triple("border_color_rgb", (84, 93, 108)),
        label_color_rgb=_triple("label_color_rgb", (33, 38, 46)),
        label_stroke_rgb=_triple("label_stroke_rgb", (255, 255, 255)),
        divider_rgb=_triple("divider_rgb", (210, 214, 222)),
    )


def _resolve_choice(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    namespace: str,
    context: str,
) -> Tuple[int, Tuple[int, int]]:
    """Resolve one deterministic integer choice inside the configured support."""

    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=str(context),
    )
    selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))
    chosen = int(lower + (selection % (upper - lower + 1)))
    return int(chosen), (int(lower), int(upper))


def _neighbors(cell: Cell, *, cols: int, rows: int) -> List[Cell]:
    """Return 4-neighbor cells inside the hidden region grid."""

    cell_x, cell_y = int(cell[0]), int(cell[1])
    candidates = (
        (cell_x - 1, cell_y),
        (cell_x + 1, cell_y),
        (cell_x, cell_y - 1),
        (cell_x, cell_y + 1),
    )
    return [
        (int(nx), int(ny))
        for nx, ny in candidates
        if 0 <= int(nx) < int(cols) and 0 <= int(ny) < int(rows)
    ]


def _grow_region_partition(
    *,
    cols: int,
    rows: int,
    region_count: int,
    min_cells_per_region: int,
    rng,
) -> List[List[Cell]]:
    """Partition a hidden grid into contiguous regions by seeded growth."""

    all_cells = [(int(cell_x), int(cell_y)) for cell_y in range(int(rows)) for cell_x in range(int(cols))]
    if int(region_count) > len(all_cells):
        raise ValueError("region_count exceeds grid capacity")

    for _ in range(96):
        seeds = list(rng.sample(all_cells, int(region_count)))
        assignments: Dict[Cell, int] = {cell: int(index) for index, cell in enumerate(seeds)}
        region_cells: List[List[Cell]] = [[seed] for seed in seeds]
        unassigned = {cell for cell in all_cells if cell not in assignments}

        while unassigned:
            region_indices = list(range(int(region_count)))
            rng.shuffle(region_indices)
            region_indices.sort(key=lambda index: (len(region_cells[int(index)]), rng.random()))
            placed = False
            for region_index in region_indices:
                frontier: List[Cell] = []
                for region_cell in region_cells[int(region_index)]:
                    for neighbor in _neighbors(region_cell, cols=int(cols), rows=int(rows)):
                        if neighbor in unassigned:
                            frontier.append(neighbor)
                unique_frontier = sorted(set(frontier))
                if not unique_frontier:
                    continue
                chosen_cell = unique_frontier[int(rng.randrange(len(unique_frontier)))]
                assignments[chosen_cell] = int(region_index)
                region_cells[int(region_index)].append(chosen_cell)
                unassigned.remove(chosen_cell)
                placed = True
                break
            if not placed:
                break

        if unassigned:
            continue
        if min(len(cells) for cells in region_cells) < int(min_cells_per_region):
            continue
        return [sorted(cells, key=lambda item: (int(item[1]), int(item[0]))) for cells in region_cells]
    raise RuntimeError("failed to construct contiguous region partition")


def _region_sort_key(cells: Iterable[Cell]) -> Tuple[float, float]:
    """Return one deterministic reading-order key for a region."""

    cell_list = [(int(cell_x), int(cell_y)) for cell_x, cell_y in cells]
    min_y = min(int(cell_y) for _, cell_y in cell_list)
    avg_x = sum(int(cell_x) for cell_x, _ in cell_list) / float(len(cell_list))
    return (float(min_y), float(avg_x))


def _sample_category_colors(
    *,
    count: int,
    min_distance: float,
    channel_min: int,
    channel_max: int,
    rng,
) -> List[Tuple[int, int, int]]:
    """Sample one stable legend palette with Lab-distance separation."""

    palette = list(
        sample_color_palette_with_distance_constraints(
            rng,
            palette_size=int(count),
            channel_min=int(channel_min),
            channel_max=int(channel_max),
            anchor_colors=((247, 248, 250), (251, 252, 255), (255, 255, 255)),
            min_distance=float(min_distance),
            distance_space=DEFAULT_COLOR_DISTANCE_SPACE,
        )
    )
    return [tuple(int(channel) for channel in color) for color in palette]


def _build_category_assignment(
    *,
    task_variant: str,
    region_count: int,
    answer_index: int,
    query_category_index: int,
    rng,
) -> Tuple[List[int], int]:
    """Construct region-category assignments with one unambiguous answer."""

    assignments = [0] * int(region_count)
    variant = str(task_variant)
    answer_idx = int(answer_index)
    if variant == "max_category_region":
        assignments[answer_idx] = len(_CATEGORY_LABELS) - 1
        for index in range(int(region_count)):
            if int(index) == int(answer_idx):
                continue
            assignments[index] = int(rng.randrange(len(_CATEGORY_LABELS) - 1))
        return assignments, len(_CATEGORY_LABELS) - 1
    if variant == "min_category_region":
        assignments[answer_idx] = 0
        for index in range(int(region_count)):
            if int(index) == int(answer_idx):
                continue
            assignments[index] = int(1 + rng.randrange(len(_CATEGORY_LABELS) - 1))
        return assignments, 0
    if variant == "matches_legend_bin":
        target_category = int(query_category_index)
        assignments[answer_idx] = int(target_category)
        remaining_categories = [index for index in range(len(_CATEGORY_LABELS)) if int(index) != int(target_category)]
        for index in range(int(region_count)):
            if int(index) == int(answer_idx):
                continue
            assignments[index] = int(remaining_categories[int(rng.randrange(len(remaining_categories)))])
        return assignments, int(target_category)
    raise ValueError(f"unsupported region task variant: {task_variant}")


def build_region_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MapRegionDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one stylized choropleth region-map dataset instance."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    region_count, region_count_range = _resolve_choice(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        min_key="region_count_min",
        max_key="region_count_max",
        fallback_min=int(defaults.region_count_min),
        fallback_max=int(defaults.region_count_max),
        namespace=f"{task_id}.region_count",
        context=f"{task_id} region count",
    )
    grid_cols, grid_cols_range = _resolve_choice(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        min_key="grid_cols_min",
        max_key="grid_cols_max",
        fallback_min=int(defaults.grid_cols_min),
        fallback_max=int(defaults.grid_cols_max),
        namespace=f"{task_id}.grid_cols",
        context=f"{task_id} grid cols",
    )
    grid_rows, grid_rows_range = _resolve_choice(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        min_key="grid_rows_min",
        max_key="grid_rows_max",
        fallback_min=int(defaults.grid_rows_min),
        fallback_max=int(defaults.grid_rows_max),
        namespace=f"{task_id}.grid_rows",
        context=f"{task_id} grid rows",
    )
    color_channel_min, color_channel_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="color_channel_min",
        max_key="color_channel_max",
        fallback_min=int(defaults.color_channel_min),
        fallback_max=int(defaults.color_channel_max),
        context=f"{task_id} color channels",
    )
    color_min_distance, _ = resolve_required_float_bounds(
        params,
        gen_defaults,
        min_key="color_min_distance",
        max_key="color_min_distance",
        fallback_min=float(defaults.color_min_distance),
        fallback_max=float(defaults.color_min_distance),
        context=f"{task_id} color distance",
    )
    min_cells_per_region = int(
        params.get(
            "min_cells_per_region",
            group_default(gen_defaults, "min_cells_per_region", int(defaults.min_cells_per_region)),
        )
    )

    region_cells = _grow_region_partition(
        cols=int(grid_cols),
        rows=int(grid_rows),
        region_count=int(region_count),
        min_cells_per_region=int(min_cells_per_region),
        rng=rng,
    )
    sorted_regions = sorted(region_cells, key=_region_sort_key)
    region_labels = [chr(ord("A") + int(index)) for index in range(int(region_count))]

    answer_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.answer_region")) % int(region_count)
    query_category_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.query_category")) % len(_CATEGORY_LABELS)
    category_assignments, effective_query_category = _build_category_assignment(
        task_variant=str(task_variant),
        region_count=int(region_count),
        answer_index=int(answer_index),
        query_category_index=int(query_category_index),
        rng=rng,
    )
    category_colors = _sample_category_colors(
        count=int(defaults.category_count),
        min_distance=float(color_min_distance),
        channel_min=int(color_channel_min),
        channel_max=int(color_channel_max),
        rng=rng,
    )

    region_specs: List[Dict[str, Any]] = []
    for index, cells in enumerate(sorted_regions):
        region_label = str(region_labels[int(index)])
        category_index = int(category_assignments[int(index)])
        region_specs.append(
            {
                "region_id": f"region_{region_label}",
                "region_label": str(region_label),
                "region_bbox_id": f"region_bbox_{region_label}",
                "cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cells],
                "category_index": int(category_index),
                "category_label": str(_CATEGORY_LABELS[int(category_index)]),
                "fill_rgb": [int(channel) for channel in category_colors[int(category_index)]],
            }
        )

    legend_specs = [
        {
            "legend_entry_id": f"legend_entry_{int(index)}",
            "category_index": int(index),
            "category_label": str(_CATEGORY_LABELS[int(index)]),
            "fill_rgb": [int(channel) for channel in category_colors[int(index)]],
        }
        for index in range(len(_CATEGORY_LABELS))
    ]
    answer_region = region_specs[int(answer_index)]

    if str(task_variant) == "max_category_region":
        question_text = "Which labeled region is in the highest category on the legend?"
    elif str(task_variant) == "min_category_region":
        question_text = "Which labeled region is in the lowest category on the legend?"
    elif str(task_variant) == "matches_legend_bin":
        question_text = (
            f"Which labeled region is in the '{str(_CATEGORY_LABELS[int(effective_query_category)])}' category on the legend?"
        )
    else:
        raise ValueError(f"unsupported region task variant: {task_variant}")

    return {
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "grid_cols_range": [int(grid_cols_range[0]), int(grid_cols_range[1])],
        "grid_rows_range": [int(grid_rows_range[0]), int(grid_rows_range[1])],
        "region_count": int(region_count),
        "region_count_range": [int(region_count_range[0]), int(region_count_range[1])],
        "category_count": len(_CATEGORY_LABELS),
        "category_labels": [str(item) for item in _CATEGORY_LABELS],
        "legend_specs": legend_specs,
        "region_specs": region_specs,
        "answer_region_label": str(answer_region["region_label"]),
        "answer_region_id": str(answer_region["region_id"]),
        "answer_region_bbox_id": str(answer_region["region_bbox_id"]),
        "question_text": str(question_text),
        "query_category_label": str(_CATEGORY_LABELS[int(effective_query_category)]),
        "query_category_index": int(effective_query_category),
        "view_family": "region_legend_map",
        "question_format": "region_association_label",
        "color_min_distance": float(color_min_distance),
        "color_distance_space": DEFAULT_COLOR_DISTANCE_SPACE,
    }


__all__ = [
    "MapRegionDefaults",
    "MapRegionRenderParams",
    "SUPPORTED_MAP_REGION_SCENE_VARIANTS",
    "SUPPORTED_MAP_REGION_TASK_VARIANTS",
    "build_region_dataset_for_variant",
    "resolve_region_render_params",
    "resolve_region_scene_variant",
    "resolve_region_task_variant",
]
