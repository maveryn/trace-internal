"""Runtime rendering helpers for radial Sankey tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.text_rendering import temporary_default_font_family
from ...shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .radial_sankey_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    _RenderedRadialSankey,
    _resolve_render_params,
)
from .radial_sankey_rendering import _render_radial_sankey


@dataclass(frozen=True)
class RadialSankeyRenderResult:
    image: Image.Image
    rendered_scene: _RenderedRadialSankey
    render_params: Any
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str


def render_radial_sankey_dataset(
    *,
    dataset: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> RadialSankeyRenderResult:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(render_style_params)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = _render_radial_sankey(
            background,
            scene_title=str(dataset["scene_title"]),
            sources=list(dataset["sources"]),
            targets=list(dataset["targets"]),
            links=list(dataset["links"]),
            render_params=render_params,
            value_min=int(dataset["value_min"]),
            value_max=int(dataset["value_max"]),
            instance_seed=int(instance_seed),
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return RadialSankeyRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        render_params=render_params,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
    )


def font_assets_payload(*, chart_font_family: str) -> dict[str, Any]:
    return chart_font_asset_metadata(str(chart_font_family))


__all__ = ["RadialSankeyRenderResult", "font_assets_payload", "render_radial_sankey_dataset"]
