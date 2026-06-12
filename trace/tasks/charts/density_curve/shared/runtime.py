"""Runtime helpers for density-curve chart tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.density_curve.shared.density_curve import (
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    SCENE_NAMESPACE,
    SCENE_VARIANT,
    _Dataset,
    _REASONING_LOAD_BY_QUERY,
    _Rendered,
    density_curve_count_bounds,
    render_density_curve_scene,
    resolve_density_curve_render_params,
)
from trace.tasks.charts.shared.information_style import prepare_chart_information_scene
from trace.tasks.shared.font_assets import font_asset_version, sample_font_family
from trace.tasks.shared.text_rendering import temporary_default_font_family


def render_dataset(
    dataset: _Dataset,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[_Rendered, Dict[str, Any]]:
    render_params = resolve_density_curve_render_params(params, instance_seed=int(instance_seed))
    render_params, background, background_meta, information_style_meta = prepare_chart_information_scene(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        render_params=render_params,
        protected_colors=(),
    )
    chart_font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
        exclude_tags=("display",),
        explicit_key="chart_font_family",
        weights_key="chart_font_family_weights",
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered = render_density_curve_scene(
            background.copy(),
            dataset=dataset,
            render_params=render_params,
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    rendered = replace(rendered, image=image)
    render_meta = {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": SCENE_VARIANT,
        "background_style": dict(background_meta),
        "information_scene_style": dict(information_style_meta),
        "post_image_noise": dict(post_noise_meta),
        "layout_jitter": dict(render_params.layout_jitter_meta or {}),
        "font_assets": {
            "asset_version": str(font_asset_version()),
            "chart_font_family": str(chart_font_family),
        },
        "chart_font_family": str(chart_font_family),
        "font_asset_version": str(font_asset_version()),
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
        "plot_bbox_px": list(rendered.plot_bbox_px),
        "legend_bbox_px": list(rendered.legend_bbox_px),
        **dict(rendered.render_meta),
    }
    return rendered, dict(render_meta)


def answer_typed_value(dataset: _Dataset) -> TypedValue:
    return TypedValue(type="string", value=str(dataset.query.answer_label))


def annotation_payload(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
) -> tuple[str, Dict[str, list[float]], Dict[str, Any]]:
    answer_label = str(dataset.query.answer_label)
    annotation_map_source = {
        "answer_mean_marker": rendered.mean_marker_bboxes_px,
        "answer_mode_marker": rendered.mode_marker_bboxes_px,
        "answer_interval_mass": rendered.interval_mass_bboxes_px,
        "answer_density_at_x": rendered.density_at_x_points_px,
    }[str(dataset.query.annotation_key)]
    annotation_value = list(annotation_map_source[str(answer_label)])
    annotation_type = "keyed_point_map" if str(dataset.query.annotation_key) == "answer_density_at_x" else "keyed_bbox_map"
    annotation = {str(dataset.query.annotation_key): list(annotation_value)}
    projected = {
        "type": str(annotation_type),
        "answer_label": str(answer_label),
    }
    if str(annotation_type) == "keyed_point_map":
        projected["keyed_point_map"] = dict(annotation)
        projected["pixel_keyed_point_map"] = dict(annotation)
    else:
        projected["keyed_bbox_map"] = dict(annotation)
        projected["pixel_keyed_bbox_map"] = dict(annotation)
    return str(annotation_type), dict(annotation), dict(projected)


def curve_records(dataset: _Dataset) -> list[dict[str, Any]]:
    return [
        {
            "label": str(curve.label),
            "family": str(curve.family),
            "component_count": int(curve.component_count),
            "color_rgb": [int(channel) for channel in curve.color_rgb],
            "line_style": str(curve.line_style),
            "mean_x": round(float(curve.mean_x), 4),
            "mode_x": round(float(curve.mode_x), 4),
            "mode_y": round(float(curve.mode_y), 8),
            "interval_mass": round(float(curve.interval_mass), 6),
            "density_at_x": round(float(curve.density_at_x), 8),
        }
        for curve in dataset.curves
    ]


def build_trace_scaffold(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
    render_meta: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
    answer_label: str,
) -> Dict[str, Any]:
    return {
        "scene_ir": {
            "scene_kind": "chart_density_curve",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_variant": SCENE_VARIANT,
                "answer_label": str(answer_label),
                "annotation_key": str(dataset.query.annotation_key),
            },
        },
        "render_spec": dict(render_meta),
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "legend_item_bboxes_px": dict(rendered.legend_item_bboxes_px),
            "curve_bboxes_px": dict(rendered.curve_bboxes_px),
            "mean_marker_bboxes_px": dict(rendered.mean_marker_bboxes_px),
            "mode_marker_bboxes_px": dict(rendered.mode_marker_bboxes_px),
            "interval_mass_bboxes_px": dict(rendered.interval_mass_bboxes_px),
            "density_at_x_points_px": dict(rendered.density_at_x_points_px),
        },
        "execution_trace": {
            **dict(dataset.query.trace),
            "scene_id": SCENE_ID,
            "scene_variant": SCENE_VARIANT,
            "answer": str(answer_label),
            "curve_records": curve_records(dataset),
            "question_format": "density_curve_label_selection",
        },
        "witness_symbolic": {
            "type": "object_set",
            "value": [str(answer_label)],
        },
        "projected_annotation": dict(projected_annotation),
    }




