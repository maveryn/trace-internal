"""Runtime sampling and rendering helpers for scatter-cluster chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence

from PIL import Image

from .....core.seed import spawn_rng
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.font_assets import font_asset_version
from ....shared.text_rendering import temporary_default_font_family
from .cluster_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    TASK_ID,
    _Dataset,
    _Rendered,
    _gen_int,
    _resolve_render_params,
    _sample_chart_font_family,
)
from .cluster_rendering import _render_scatter
from .cluster_sampling import _sample_cluster_labels, _target_answer_label


@dataclass(frozen=True)
class ScatterClusterInputs:
    cluster_count: int
    labels: tuple[str, ...]
    points_per_cluster: int
    answer_label: str


@dataclass(frozen=True)
class ScatterClusterRenderResult:
    image: Image.Image
    rendered_scene: _Rendered
    render_params: Any
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str


def sample_cluster_inputs(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> ScatterClusterInputs:
    cluster_min = _gen_int(params, "cluster_count_min", 5)
    cluster_max = _gen_int(params, "cluster_count_max", 8)
    cluster_count_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.cluster_count")
    cluster_count = int(cluster_count_rng.randint(int(cluster_min), int(cluster_max)))
    cluster_count = max(4, min(8, int(cluster_count)))
    labels = _sample_cluster_labels(cluster_count=int(cluster_count), instance_seed=int(instance_seed))
    points_min = _gen_int(params, "points_per_cluster_min", 8)
    points_max = _gen_int(params, "points_per_cluster_max", 12)
    point_count_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.point_count")
    points_per_cluster = int(point_count_rng.randint(int(points_min), int(points_max)))
    answer_label = _target_answer_label(params, instance_seed=int(instance_seed), labels=labels)
    return ScatterClusterInputs(
        cluster_count=int(cluster_count),
        labels=tuple(str(label) for label in labels),
        points_per_cluster=int(points_per_cluster),
        answer_label=str(answer_label),
    )


def render_scatter_cluster_dataset(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> ScatterClusterRenderResult:
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
        rendered_scene = _render_scatter(background, dataset=dataset, render_params=render_params)
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return ScatterClusterRenderResult(
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


__all__ = [
    "ScatterClusterInputs",
    "ScatterClusterRenderResult",
    "font_assets_payload",
    "render_scatter_cluster_dataset",
    "sample_cluster_inputs",
]
