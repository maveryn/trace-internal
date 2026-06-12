"""Runtime rendering helpers for radial-progress tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.font_assets import font_asset_version
from ....shared.text_rendering import temporary_default_font_family
from .progress_chart import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    _Dataset,
    _Rendered,
    _render_chart,
    _render_int,
    _sample_chart_font_family,
)


@dataclass(frozen=True)
class RadialProgressRenderResult:
    image: Image.Image
    rendered_scene: _Rendered
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str


def render_radial_progress_dataset(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> RadialProgressRenderResult:
    background, background_meta = make_background_canvas(
        canvas_width=_render_int(params, "canvas_width", 1320),
        canvas_height=_render_int(params, "canvas_height", 900),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = _sample_chart_font_family(int(instance_seed), params)
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = _render_chart(
            background=background,
            dataset=dataset,
            params=params,
            instance_seed=int(instance_seed),
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return RadialProgressRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
    )


def font_assets_payload(*, chart_font_family: str) -> dict[str, str]:
    return {
        "font_asset_version": str(font_asset_version()),
        "chart_font_family": str(chart_font_family),
    }


__all__ = ["RadialProgressRenderResult", "font_assets_payload", "render_radial_progress_dataset"]
