"""Runtime rendering helpers for population-pyramid chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from PIL import Image

from .....core.visual.noise import apply_post_image_noise
from .pyramid import POST_IMAGE_NOISE_DEFAULTS, _Dataset, _Rendered, _render_dataset


@dataclass(frozen=True)
class PopulationPyramidRenderResult:
    image: Image.Image
    rendered_scene: _Rendered
    post_noise_meta: Dict[str, Any]


def render_population_pyramid_dataset(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> PopulationPyramidRenderResult:
    rendered_scene = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return PopulationPyramidRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        post_noise_meta=dict(post_noise_meta),
    )


__all__ = ["PopulationPyramidRenderResult", "render_population_pyramid_dataset"]
