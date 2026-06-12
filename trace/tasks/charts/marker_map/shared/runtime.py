"""Rendering runtime helpers for marker-map tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.font_assets import font_asset_version, sample_font_family
from ....shared.text_rendering import temporary_default_font_family
from .choropleth_assets import WORLD_MAP_ASSET_ID
from .choropleth_config import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_NAMESPACE,
)
from .choropleth_marker_rendering import _render_marker_layer
from .choropleth_rendering import (
    _MapRenderParams,
    _RenderedChoroplethMap,
    _render_choropleth_map,
    _render_world_choropleth_map,
    _resolve_render_params,
)


@dataclass(frozen=True)
class MarkerMapRenderResult:
    image: Image.Image
    rendered_scene: _RenderedChoroplethMap
    render_params: _MapRenderParams
    marker_bboxes_by_region: Dict[str, List[List[float]]]
    marker_group_bbox_map: Dict[str, List[float]]
    marker_render_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str


def render_marker_map(
    *,
    dataset: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
) -> MarkerMapRenderResult:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(
        render_style_params,
        legend_count=len(dataset["legend_bins"]),
        categorical=False,
    )
    chart_font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
        explicit_key="chart_font_family",
        weights_key="chart_font_family_weights",
    )
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    with temporary_default_font_family(str(chart_font_family)):
        if str(dataset["scene_variant"]) == "geographic_region_map":
            rendered_scene = _render_world_choropleth_map(
                background,
                scene_title=str(dataset["scene_title"]),
                map_asset_id=str(dataset.get("map_asset_id") or WORLD_MAP_ASSET_ID),
                regions=list(dataset["regions"]),
                legend_bins=list(dataset["legend_bins"]),
                render_params=render_params,
                instance_seed=int(instance_seed),
                categorical=False,
                draw_color_legend=False,
                neutral_regions=True,
                show_region_value_labels=False,
            )
        else:
            rendered_scene = _render_choropleth_map(
                background,
                scene_title=str(dataset["scene_title"]),
                rows=int(dataset["rows"]),
                cols=int(dataset["cols"]),
                regions=list(dataset["regions"]),
                legend_bins=list(dataset["legend_bins"]),
                render_params=render_params,
                instance_seed=int(instance_seed),
                categorical=False,
                draw_color_legend=False,
                neutral_regions=True,
                show_region_value_labels=False,
            )
        rendered_scene, marker_bboxes_by_region, marker_group_bbox_map, marker_render_meta = _render_marker_layer(
            rendered_scene,
            dataset=dataset,
            render_params=render_params,
            params=render_style_params,
            instance_seed=int(instance_seed),
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return MarkerMapRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        render_params=render_params,
        marker_bboxes_by_region={str(key): [list(bbox) for bbox in value] for key, value in marker_bboxes_by_region.items()},
        marker_group_bbox_map={str(key): list(value) for key, value in marker_group_bbox_map.items()},
        marker_render_meta=dict(marker_render_meta),
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
    )


def font_assets_payload(chart_font_family: str) -> Dict[str, str]:
    return {
        "font_asset_version": font_asset_version(),
        "chart_font_family": str(chart_font_family),
    }


__all__ = ["MarkerMapRenderResult", "font_assets_payload", "render_marker_map"]
