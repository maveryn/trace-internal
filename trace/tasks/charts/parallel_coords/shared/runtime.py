"""Rendering and annotation helpers for parallel-coordinates chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.font_assets import font_asset_version
from ....shared.text_rendering import temporary_default_font_family
from .profile_common import (
    _QUERY_LOADS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    Point,
    _Dataset,
    _Rendered,
    _resolve_render_params,
    _sample_chart_font_family,
)
from .profile_rendering import _render_parallel_coordinates


@dataclass(frozen=True)
class ParallelCoordsRenderResult:
    image: Image.Image
    rendered_scene: _Rendered
    render_params: Any
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str


def _bbox_center(bbox: Sequence[float]) -> Tuple[float, float]:
    if len(bbox) != 4:
        raise ValueError(f"expected bbox with 4 values, got {bbox}")
    return (float(bbox[0] + bbox[2]) / 2.0, float(bbox[1] + bbox[3]) / 2.0)


def _round_point(x: float, y: float) -> Point:
    return [round(float(x), 2), round(float(y), 2)]


def _axis_point(dataset: _Dataset, rendered: _Rendered, profile_id: str, axis_index: int) -> Tuple[float, float]:
    bbox = rendered.point_bboxes_px[f"{profile_id}:axis_{int(axis_index)}"]
    return _bbox_center(bbox)


def _segment_midpoint(dataset: _Dataset, rendered: _Rendered, profile_id: str) -> Point:
    x0, y0 = _axis_point(dataset, rendered, str(profile_id), int(dataset.query.axis_i))
    x1, y1 = _axis_point(dataset, rendered, str(profile_id), int(dataset.query.axis_j))
    return _round_point((float(x0) + float(x1)) / 2.0, (float(y0) + float(y1)) / 2.0)


def _crossing_point(dataset: _Dataset, rendered: _Rendered, first_profile_id: str, second_profile_id: str) -> Point:
    axis_i = int(dataset.query.axis_i)
    axis_j = int(dataset.query.axis_j)
    x0, y0 = _axis_point(dataset, rendered, str(first_profile_id), axis_i)
    x1, y1 = _axis_point(dataset, rendered, str(first_profile_id), axis_j)
    _, other_y0 = _axis_point(dataset, rendered, str(second_profile_id), axis_i)
    _, other_y1 = _axis_point(dataset, rendered, str(second_profile_id), axis_j)
    first_delta = float(y1) - float(y0)
    second_delta = float(other_y1) - float(other_y0)
    denom = float(first_delta) - float(second_delta)
    if abs(float(denom)) < 1e-9:
        return _round_point((float(x0) + float(x1)) / 2.0, (float(y0) + float(y1)) / 2.0)
    t = (float(other_y0) - float(y0)) / float(denom)
    t = max(0.0, min(1.0, float(t)))
    return _round_point(float(x0) + (float(x1) - float(x0)) * t, float(y0) + first_delta * t)


def render_dataset(*, dataset: _Dataset, params: dict[str, Any], instance_seed: int) -> ParallelCoordsRenderResult:
    render_params = _resolve_render_params({**dict(params), "_render_style_seed": int(instance_seed)})
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = _sample_chart_font_family(int(instance_seed), params)
    with temporary_default_font_family(str(chart_font_family)):
        rendered = _render_parallel_coordinates(background, dataset=dataset, render_params=render_params)
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return ParallelCoordsRenderResult(
        image=image,
        rendered_scene=rendered,
        render_params=render_params,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
    )


def annotation_payload(dataset: _Dataset, rendered: _Rendered) -> tuple[str, Dict[str, Point] | List[Point], Dict[str, Any]]:
    profiles_by_id = {str(profile.profile_id): profile for profile in dataset.profiles}
    if dataset.query.crossing_pairs:
        points: List[Point] = [
            _crossing_point(dataset, rendered, str(first_profile_id), str(second_profile_id))
            for first_profile_id, second_profile_id in dataset.query.crossing_pairs
        ]
        projected = {
            "type": "point_set",
            "point_set": list(points),
            "pixel_point_set": list(points),
            "crossing_pair_labels": [
                [str(profiles_by_id[str(first)].label), str(profiles_by_id[str(second)].label)]
                for first, second in dataset.query.crossing_pairs
            ],
        }
        return "point_set", list(points), projected
    points_by_label: Dict[str, Point] = {}
    for profile_id in dataset.query.annotation_profile_ids:
        profile = profiles_by_id[str(profile_id)]
        points_by_label[str(profile.label)] = _segment_midpoint(dataset, rendered, str(profile_id))
    projected = {
        "type": "keyed_point_map",
        "keyed_point_map": dict(points_by_label),
        "pixel_keyed_point_map": dict(points_by_label),
        "point_set": list(points_by_label.values()),
        "pixel_point_set": list(points_by_label.values()),
    }
    return "keyed_point_map", dict(points_by_label), projected


def profile_rows(dataset: _Dataset) -> list[dict[str, Any]]:
    return [
        {
            "profile_id": str(profile.profile_id),
            "label": str(profile.label),
            "values": [int(value) for value in profile.values],
            "color_rgb": list(profile.color_rgb),
        }
        for profile in dataset.profiles
    ]




def render_spec_payload(result: ParallelCoordsRenderResult, dataset: _Dataset) -> dict[str, Any]:
    rendered = result.rendered_scene
    render_params = result.render_params
    return {
        "scene_variant": str(dataset.scene_variant),
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "plot_bbox_px": list(rendered.plot_bbox_px),
        "axis_x_px": {str(key): float(value) for key, value in rendered.axis_x_px.items()},
        "line_width_px": int(render_params.line_width_px),
        "point_radius_px": int(render_params.point_radius_px),
        "layout_jitter": dict(render_params.layout_jitter_meta),
        "font_assets": {
            "font_asset_version": font_asset_version(),
            "chart_font_family": str(result.chart_font_family),
        },
        "background_style": dict(result.background_meta),
        "post_image_noise": dict(result.post_noise_meta),
    }


def render_map_payload(result: ParallelCoordsRenderResult) -> dict[str, Any]:
    rendered = result.rendered_scene
    return {
        "image_id": "img0",
        "plot_bbox_px": list(rendered.plot_bbox_px),
        "axis_x_px": {str(key): float(value) for key, value in rendered.axis_x_px.items()},
        "point_bboxes_px": dict(rendered.point_bboxes_px),
        "segment_bboxes_px": dict(rendered.segment_bboxes_px),
        "profile_bboxes_px": dict(rendered.profile_bboxes_px),
        "label_bboxes_px": dict(rendered.label_bboxes_px),
        "threshold_bboxes_px": {str(key): list(value) for key, value in rendered.threshold_bboxes_px.items()},
    }


