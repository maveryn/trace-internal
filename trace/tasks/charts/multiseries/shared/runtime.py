"""Rendering and annotation projection helpers for multiseries chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.font_assets import font_asset_version
from ....shared.text_rendering import temporary_default_font_family
from ...shared.chart_scene import render_multiseries_chart_scene, value_axis_render_metadata
from ...shared.labeled_chart_common import resolve_chart_render_params_for_task
from .comparison_common import (
    DEFAULTS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    RENDER_DEFAULTS,
    keyed_points_from_projection,
    projected_keyed_point_annotation,
    sample_chart_font_family,
)
from .multiseries_chart_config import (
    build_multiseries_mark_specs,
    projected_multiseries_mark_annotation,
    resolve_multiseries_chart_colors,
)


@dataclass(frozen=True)
class MultiseriesRenderResult:
    image: Image.Image
    rendered_scene: Any
    render_params: Any
    mark_style: Dict[str, Any]
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str
    category_labels: list[str]
    series_labels: list[str]


def render_multiseries_dataset(
    *,
    values_by_category: Mapping[str, Mapping[str, int]],
    trace_extras: Mapping[str, Any],
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> MultiseriesRenderResult:
    category_labels = [str(label) for label in trace_extras["category_labels"]]
    series_labels = [str(label) for label in trace_extras["series_labels"]]
    mark_style = resolve_multiseries_chart_colors(
        params,
        render_defaults=RENDER_DEFAULTS,
        defaults=DEFAULTS,
        instance_seed=int(instance_seed),
        series_count=len(series_labels),
    )
    marks = build_multiseries_mark_specs(
        category_labels=category_labels,
        series_labels=series_labels,
        values_by_category=values_by_category,
        mark_style=mark_style,
    )
    render_params = resolve_chart_render_params_for_task(
        {**dict(params), **mark_style},
        render_defaults=RENDER_DEFAULTS,
        defaults=DEFAULTS,
        instance_seed=int(instance_seed),
    )
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(int(instance_seed), params)
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = render_multiseries_chart_scene(
            background,
            scene_variant=str(scene_variant),
            marks=marks,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return MultiseriesRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        render_params=render_params,
        mark_style=dict(mark_style),
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
        category_labels=list(category_labels),
        series_labels=list(series_labels),
    )


def mark_annotation_payload(
    *,
    rendered_scene: Any,
    category_labels: Sequence[str],
    series_labels: Sequence[str] | Mapping[str, Sequence[str]],
) -> tuple[Dict[str, list[float]], Dict[str, Any]]:
    projection = projected_multiseries_mark_annotation(
        rendered_scene,
        [str(label) for label in category_labels],
        series_labels,
    )
    points = keyed_points_from_projection(projection)
    return points, projected_keyed_point_annotation(projection, points)


def category_label_centers(rendered_scene: Any) -> Dict[str, list[float]]:
    return {
        str(mark["category_label"]): list(mark["category_label_center_px"])
        for mark in rendered_scene.mark_traces
    }


def render_spec_payload(result: MultiseriesRenderResult, *, scene_variant: str) -> Dict[str, Any]:
    rendered_scene = result.rendered_scene
    render_params = result.render_params
    return {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": str(scene_variant),
        "background_style": dict(result.background_meta),
        "post_image_noise": dict(result.post_noise_meta),
        "font_assets": {
            "asset_version": font_asset_version(),
            "chart_font_family": str(result.chart_font_family),
        },
        "layout_jitter": dict(render_params.layout_jitter_meta or {}),
        "text_style": {
            "label_font_size_px": int(render_params.label_font_size_px),
            "tick_font_size_px": int(render_params.tick_font_size_px),
            "label_stroke_width_px": int(render_params.label_stroke_width_px),
        },
        "axis_style": {
            "axis_line_width_px": int(render_params.axis_line_width_px),
            "grid_line_width_px": int(render_params.grid_line_width_px),
            "tick_length_px": int(render_params.tick_length_px),
        },
        "mark_style": {
            "sampling_policy": str(result.mark_style["sampling_policy"]),
            **{str(key): value for key, value in result.mark_style.items()},
        },
        "plot_bbox_px": list(rendered_scene.plot_bbox_px),
        "y_axis_max": int(rendered_scene.y_axis_max),
        "y_ticks": [int(value) for value in rendered_scene.y_ticks],
        **value_axis_render_metadata(rendered_scene),
    }


def render_map_payload(result: MultiseriesRenderResult) -> Dict[str, Any]:
    rendered_scene = result.rendered_scene
    return {
        "image_id": "img0",
        "plot_bbox_px": list(rendered_scene.plot_bbox_px),
        "legend_bbox_px": list(rendered_scene.legend_bbox_px),
        "legend_item_bboxes_px": {
            str(label): list(bbox)
            for label, bbox in rendered_scene.legend_item_bboxes_px.items()
        },
        "context_protected_bboxes_px": {
            "plot": list(rendered_scene.plot_bbox_px),
            **({"legend": list(rendered_scene.legend_bbox_px)} if rendered_scene.legend_bbox_px else {}),
        },
        "category_label_centers_px": category_label_centers(rendered_scene),
    }


__all__ = [
    "MultiseriesRenderResult",
    "category_label_centers",
    "mark_annotation_payload",
    "render_map_payload",
    "render_multiseries_dataset",
    "render_spec_payload",
]
