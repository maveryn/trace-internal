"""Marker overlay rendering helpers for choropleth map tasks."""

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
from .choropleth_rendering import BBox, _MapRenderParams, _RenderedChoroplethMap, _layout_bboxes

def _clamp_marker_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return _round_bbox(
        [
            max(0.0, min(float(width) - 1.0, x0)),
            max(0.0, min(float(height) - 1.0, y0)),
            max(1.0, min(float(width), x1)),
            max(1.0, min(float(height), y1)),
        ]
    )

def _draw_marker_label(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    center: Sequence[float],
    radius: float,
    render_params: _MapRenderParams,
    style: Mapping[str, Tuple[int, int, int]],
) -> List[float]:
    x, y = float(center[0]), float(center[1])
    label_w = 28.0 if len(str(label)) <= 1 else 38.0
    label_h = 24.0
    left = x + float(radius) + 5.0
    top = y - float(radius) - 4.0
    if left + label_w > float(render_params.canvas_width) - 8.0:
        left = x - float(radius) - label_w - 5.0
    if top < 8.0:
        top = y + float(radius) + 4.0
    bbox = (
        float(left),
        float(top),
        float(left + label_w),
        float(top + label_h),
    )
    draw.rounded_rectangle(
        bbox,
        radius=6,
        fill=style["label_fill"],
        outline=style["label_outline"],
        width=2,
    )
    draw_centered_text(
        draw,
        text=str(label),
        center=(0.5 * (bbox[0] + bbox[2]), 0.5 * (bbox[1] + bbox[3])),
        font=load_font(15, bold=True),
        fill=style["label_outline"],
        stroke_fill=style["label_fill"],
        stroke_width=1,
    )
    return _clamp_marker_bbox(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height))

def _draw_marker_legend(
    draw: ImageDraw.ImageDraw,
    *,
    render_params: _MapRenderParams,
    marker_render_variant: str,
    value_min: int,
    value_max: int,
    style: Mapping[str, Tuple[int, int, int]],
) -> Dict[str, List[float]]:
    legend_bbox = tuple(float(value) for value in _layout_bboxes(render_params)[3])
    if str(render_params.legend_position) == "none":
        return {}
    draw_rounded_rect(
        draw,
        legend_bbox,
        radius=12,
        fill=render_params.legend_fill_rgb,
        outline=render_params.map_border_rgb,
        width=2,
    )
    title = "Marker value"
    title_bbox = (
        legend_bbox[0] + 12.0,
        legend_bbox[1] + 8.0,
        legend_bbox[2] - 12.0,
        legend_bbox[1] + 38.0,
    )
    draw_centered_text(
        draw,
        text=title,
        center=(0.5 * (title_bbox[0] + title_bbox[2]), 0.5 * (title_bbox[1] + title_bbox[3])),
        font=load_font(int(render_params.legend_font_size_px) + 2, bold=True),
        fill=render_params.legend_text_rgb,
        stroke_fill=render_params.legend_fill_rgb,
        stroke_width=1,
    )
    entries: Dict[str, List[float]] = {}
    values = list(range(int(value_min), int(value_max) + 1))
    count = len(values)
    if str(render_params.legend_position) in {"bottom", "top"}:
        start_x = legend_bbox[0] + 30.0
        usable_w = max(1.0, legend_bbox[2] - legend_bbox[0] - 60.0)
        row_y = legend_bbox[1] + 72.0
        for index, value in enumerate(values):
            x = start_x + (usable_w * float(index) / max(1.0, float(count - 1)))
            radius = 5.5 + ((float(value) - float(value_min)) / max(1.0, float(value_max - value_min))) * 11.0
            bbox = (x - radius, row_y - radius, x + radius, row_y + radius)
            draw.ellipse(bbox, fill=style["fill"], outline=style["outline"], width=2)
            draw_centered_text(
                draw,
                text=str(value),
                center=(float(x), float(row_y + 24.0)),
                font=load_font(12, bold=True),
                fill=render_params.legend_text_rgb,
                stroke_fill=render_params.legend_fill_rgb,
                stroke_width=1,
            )
            entries[f"marker_value_{value}"] = _round_bbox(bbox)
    else:
        start_y = legend_bbox[1] + 60.0
        step = max(30.0, min(42.0, (legend_bbox[3] - start_y - 16.0) / max(1.0, float(count))))
        for index, value in enumerate(values):
            y = start_y + (float(index) * step)
            x = legend_bbox[0] + 45.0
            radius = 5.0 + ((float(value) - float(value_min)) / max(1.0, float(value_max - value_min))) * 10.0
            bbox = (x - radius, y - radius, x + radius, y + radius)
            draw.ellipse(bbox, fill=style["fill"], outline=style["outline"], width=2)
            draw_centered_text(
                draw,
                text=str(value),
                center=(legend_bbox[0] + 96.0, y),
                font=load_font(int(render_params.legend_font_size_px), bold=True),
                fill=render_params.legend_text_rgb,
                stroke_fill=render_params.legend_fill_rgb,
                stroke_width=1,
            )
            entries[f"marker_value_{value}"] = _round_bbox(bbox)
    return entries

def _render_marker_layer(
    rendered_scene: _RenderedChoroplethMap,
    *,
    dataset: Mapping[str, Any],
    render_params: _MapRenderParams,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_RenderedChoroplethMap, Dict[str, List[List[float]]], Dict[str, List[float]], Dict[str, Any]]:
    image = rendered_scene.image.copy()
    draw = ImageDraw.Draw(image)
    style_id, style_probabilities, style = _resolve_marker_style(
        params,
        render_defaults=_RENDER_DEFAULTS,
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
    )
    marker_render_variant = str(dataset.get("marker_render_variant") or "proportional_bubble")
    show_marker_labels = str(dataset.get("query_id")) == "marker_region_extremum_label"
    value_min = int(dataset.get("marker_value_min", 1))
    value_max = int(dataset.get("marker_value_max", 5))
    marker_bboxes_by_region: Dict[str, List[List[float]]] = {}
    marker_group_bbox_map: Dict[str, List[float]] = {}
    marker_entities: List[Dict[str, Any]] = []
    region_specs = [dict(region) for region in dataset.get("regions", []) if isinstance(region, Mapping)]

    min_radius = float(params.get("marker_min_radius_px", _RENDER_DEFAULTS.get("marker_min_radius_px", 8)))
    max_radius = float(params.get("marker_max_radius_px", _RENDER_DEFAULTS.get("marker_max_radius_px", 22)))
    for region in region_specs:
        region_id = str(region["region_id"])
        center = rendered_scene.region_center_map.get(str(region_id))
        if not center:
            continue
        value = int(region.get("marker_value", value_min))
        label = str(region.get("marker_label", ""))
        bboxes: List[List[float]] = []
        radius = float(min_radius) + (
            (float(value) - float(value_min)) / max(1.0, float(value_max - value_min))
        ) * max(1.0, float(max_radius - min_radius))
        bbox = (
            float(center[0] - radius),
            float(center[1] - radius),
            float(center[0] + radius),
            float(center[1] + radius),
        )
        draw.ellipse(bbox, fill=style["fill"], outline=style["outline"], width=3)
        rounded = _clamp_marker_bbox(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height))
        bboxes.append(list(rounded))
        marker_entities.append(
            {
                "entity_id": f"{region_id}_marker",
                "entity_type": "map_marker_bubble",
                "bbox_xyxy": list(rounded),
                "attrs": {
                    "region_id": str(region_id),
                    "marker_label": str(label),
                    "marker_value": int(value),
                    "marker_render_variant": str(marker_render_variant),
                },
            }
        )
        label_radius = float(radius)
        if bool(show_marker_labels):
            label_bbox = _draw_marker_label(
                draw,
                label=str(label),
                center=center,
                radius=float(label_radius),
                render_params=render_params,
                style=style,
            )
            marker_entities.append(
                {
                    "entity_id": f"{region_id}_marker_label",
                    "entity_type": "map_marker_label",
                    "bbox_xyxy": list(label_bbox),
                    "attrs": {
                        "region_id": str(region_id),
                        "marker_label": str(label),
                        "marker_value": int(value),
                    },
                }
            )
        marker_bboxes_by_region[str(region_id)] = [list(bbox) for bbox in bboxes]
        marker_group_bbox_map[str(region_id)] = _bbox_union(bboxes)

    marker_legend_bbox_map = _draw_marker_legend(
        draw,
        render_params=render_params,
        marker_render_variant=str(marker_render_variant),
        value_min=int(value_min),
        value_max=int(value_max),
        style=style,
    )
    marker_meta = {
        "marker_render_variant": str(marker_render_variant),
        "marker_render_variant_probabilities": dict(dataset.get("marker_render_variant_probabilities", {})),
        "marker_style_variant": str(style_id),
        "marker_style_variant_probabilities": dict(style_probabilities),
        "marker_value_min": int(value_min),
        "marker_value_max": int(value_max),
        "marker_fill_rgb": [int(channel) for channel in style["fill"]],
        "marker_outline_rgb": [int(channel) for channel in style["outline"]],
        "show_marker_labels": bool(show_marker_labels),
    }
    return (
        _RenderedChoroplethMap(
            image=image,
            entities=tuple([dict(entity) for entity in rendered_scene.entities] + [dict(entity) for entity in marker_entities]),
            panel_bbox_px=list(rendered_scene.panel_bbox_px),
            title_bbox_px=list(rendered_scene.title_bbox_px),
            map_bbox_px=list(rendered_scene.map_bbox_px),
            legend_bbox_px=list(rendered_scene.legend_bbox_px),
            region_bbox_map=dict(rendered_scene.region_bbox_map),
            region_center_map=dict(rendered_scene.region_center_map),
            legend_entry_bbox_map=dict(marker_legend_bbox_map),
            render_meta={**dict(rendered_scene.render_meta), "marker_layer": dict(marker_meta)},
        ),
        {str(key): [list(bbox) for bbox in value] for key, value in marker_bboxes_by_region.items()},
        {str(key): list(value) for key, value in marker_group_bbox_map.items()},
        dict(marker_meta),
    )


__all__ = [
    '_render_marker_layer',
]
