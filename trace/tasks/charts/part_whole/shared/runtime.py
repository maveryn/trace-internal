"""Rendering and annotation projection helpers for part-whole tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import group_default
from ....shared.font_assets import font_asset_version
from .share_arithmetic_common import (
    DEFAULTS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    RENDER_DEFAULTS,
    PartWholeDataset,
    RenderedShareChart,
)
from .share_arithmetic_dataset import annotation_value_for_label, public_annotation_key
from .share_arithmetic_rendering import _render_share_chart


@dataclass(frozen=True)
class PartWholeRenderResult:
    image: Image.Image
    rendered_scene: RenderedShareChart
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    canvas_width: int
    canvas_height: int


def render_part_whole_dataset(
    *,
    dataset: PartWholeDataset,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> PartWholeRenderResult:
    canvas_width = int(params.get("canvas_width", group_default(RENDER_DEFAULTS, "canvas_width", DEFAULTS.canvas_width)))
    canvas_height = int(params.get("canvas_height", group_default(RENDER_DEFAULTS, "canvas_height", DEFAULTS.canvas_height)))
    background, background_meta = make_background_canvas(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    rendered_scene = _render_share_chart(
        base_image=background,
        dataset=dataset,
        scene_variant=str(scene_variant),
        params=params,
        instance_seed=int(instance_seed),
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return PartWholeRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
    )


def annotation_payload(
    *,
    dataset: PartWholeDataset,
    rendered_scene: RenderedShareChart,
) -> Dict[str, Any]:
    values_by_label = {str(category.label): int(category.value) for category in dataset.categories}
    extras = dict(dataset.trace_extras)
    annotation_values = [
        annotation_value_for_label(str(label), extras=extras, values_by_label=values_by_label)
        for label in dataset.annotation_labels
    ]
    annotation_bboxes = [
        list(rendered_scene.annotation_bbox_by_label[str(label)])
        for label in dataset.annotation_labels
        if str(label) in rendered_scene.annotation_bbox_by_label
    ]
    annotation_points = [
        list(rendered_scene.annotation_point_by_label[str(label)])
        for label in dataset.annotation_labels
        if str(label) in rendered_scene.annotation_point_by_label
    ]
    annotation_keyed_points = {
        public_annotation_key(str(label)): list(rendered_scene.annotation_point_by_label[str(label)])
        for label in dataset.annotation_labels
        if str(label) in rendered_scene.annotation_point_by_label
    }
    annotation_keys = [public_annotation_key(str(label)) for label in dataset.annotation_labels]
    projected_annotation = {
        "type": "keyed_point_map",
        "keyed_point_map": dict(annotation_keyed_points),
        "pixel_keyed_point_map": dict(annotation_keyed_points),
        "point_set": list(annotation_points),
        "pixel_point_set": list(annotation_points),
        "bbox_set": list(annotation_bboxes),
        "annotation_labels": [str(label) for label in dataset.annotation_labels],
        "annotation_keys": [str(key) for key in annotation_keys],
    }
    return {
        "values": [int(value) for value in annotation_values],
        "bboxes": list(annotation_bboxes),
        "points": list(annotation_points),
        "keyed_points": dict(annotation_keyed_points),
        "keys": [str(key) for key in annotation_keys],
        "projected_annotation": dict(projected_annotation),
    }


def font_assets_payload() -> Dict[str, str]:
    return {"asset_version": font_asset_version()}


__all__ = ["PartWholeRenderResult", "annotation_payload", "font_assets_payload", "render_part_whole_dataset"]
