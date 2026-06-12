"""Runtime rendering helpers for scatter-points chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.text_rendering import temporary_default_font_family
from ...shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .points_query import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    TASK_ID,
    _Dataset,
    _Rendered,
    _render_scatter_points,
    _resolve_render_params,
)


@dataclass(frozen=True)
class ScatterPointsRenderResult:
    image: Image.Image
    rendered_scene: _Rendered
    render_params: Any
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str


def render_scatter_points_dataset(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> ScatterPointsRenderResult:
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
        namespace=TASK_ID,
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = _render_scatter_points(
            background,
            dataset=dataset,
            render_params=render_params,
            instance_seed=int(instance_seed),
            params=params,
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return ScatterPointsRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        render_params=render_params,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
    )


def font_assets_payload(*, chart_font_family: str) -> dict[str, Any]:
    return chart_font_asset_metadata(str(chart_font_family))


__all__ = ["ScatterPointsRenderResult", "font_assets_payload", "render_scatter_points_dataset"]
