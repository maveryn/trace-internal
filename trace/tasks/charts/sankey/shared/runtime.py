"""Runtime rendering helpers for standard Sankey tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.font_assets import font_asset_version
from ....shared.text_rendering import temporary_default_font_family
from .sankey_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    _RenderedSankey,
    _resolve_render_params,
    _sample_chart_font_family,
)
from .sankey_rendering import _render_sankey


@dataclass(frozen=True)
class SankeyRenderResult:
    image: Image.Image
    rendered_scene: _RenderedSankey
    render_params: Any
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str


def render_sankey_dataset(
    *,
    dataset: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
) -> SankeyRenderResult:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(render_style_params)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = _sample_chart_font_family(int(instance_seed), params)
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = _render_sankey(
            background,
            scene_title=str(dataset["scene_title"]),
            sources=list(dataset["sources"]),
            middles=list(dataset["middles"]),
            targets=list(dataset["targets"]),
            paths=list(dataset["paths"]),
            render_params=render_params,
            value_min=int(dataset["value_min"]),
            value_max=int(dataset["value_max"]),
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return SankeyRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        render_params=render_params,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
    )


def font_assets_payload(*, chart_font_family: str) -> dict[str, str]:
    return {
        "font_asset_version": font_asset_version(),
        "chart_font_family": str(chart_font_family),
    }


__all__ = ["SankeyRenderResult", "font_assets_payload", "render_sankey_dataset"]
