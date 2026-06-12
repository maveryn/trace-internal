"""Runtime rendering and trace helpers for combo-mark chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.combo_mark.shared.panel_common import (
    ComboDataset,
    ComboScene,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    RENDERING_DEFAULTS,
    SCENE_NAMESPACE,
)
from trace.tasks.charts.combo_mark.shared.panel_rendering import render_combo_scene, render_params
from trace.tasks.charts.shared.visual_defaults import (
    chart_font_asset_metadata,
    sample_chart_font_family,
)
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.text_rendering import temporary_default_font_family


@dataclass(frozen=True)
class ComboRenderArtifacts:
    scene: ComboScene
    render_params: Any
    background_style: dict[str, Any]
    font_assets: dict[str, Any]
    post_image_noise: dict[str, Any]


def render_dataset(
    *,
    dataset: ComboDataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> ComboRenderArtifacts:
    background, background_meta = make_background_canvas(
        canvas_width=int(params.get("canvas_width", group_default(RENDERING_DEFAULTS, "canvas_width", 1080))),
        canvas_height=int(params.get("canvas_height", group_default(RENDERING_DEFAULTS, "canvas_height", 660))),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
    )
    resolved_render_params = render_params(params, instance_seed=int(instance_seed))
    with temporary_default_font_family(str(chart_font_family)):
        scene = render_combo_scene(
            background,
            labels=dataset.labels,
            primary_values=dataset.primary_values,
            line_values=dataset.line_values,
            scene_variant=str(dataset.scene_variant),
            primary_name=str(dataset.primary_name),
            line_name=str(dataset.line_name),
            params=params,
            instance_seed=int(instance_seed),
        )
    image, post_noise_meta = apply_post_image_noise(
        scene.image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    scene = ComboScene(
        image=image,
        labels=tuple(scene.labels),
        primary_values=tuple(scene.primary_values),
        line_values=tuple(scene.line_values),
        primary_points=tuple(scene.primary_points),
        line_points=tuple(scene.line_points),
        entities=tuple(dict(entity) for entity in scene.entities),
        scene_variant=str(scene.scene_variant),
        primary_name=str(scene.primary_name),
        line_name=str(scene.line_name),
        primary_axis_max=int(scene.primary_axis_max),
        line_axis_max=int(scene.line_axis_max),
        plot_bbox=tuple(int(value) for value in scene.plot_bbox),
        legend_bbox=tuple(float(value) for value in scene.legend_bbox),
    )
    return ComboRenderArtifacts(
        scene=scene,
        render_params=resolved_render_params,
        background_style=dict(background_meta),
        font_assets=chart_font_asset_metadata(str(chart_font_family)),
        post_image_noise=dict(post_noise_meta),
    )


def build_trace_scaffold(
    *,
    artifacts: ComboRenderArtifacts,
    annotation: AnnotationArtifacts,
    relations: Mapping[str, Any],
) -> dict[str, Any]:
    scene = artifacts.scene
    p = artifacts.render_params
    return {
        "scene_ir": {
            "scene_kind": "chart_combo_panel",
            "entities": [dict(entity) for entity in scene.entities],
            "relations": dict(relations),
        },
        "render_spec": {
            "scene_id": "combo_mark",
            "scene_variant": str(scene.scene_variant),
            "plot_bbox": list(scene.plot_bbox),
            "primary_axis_max": int(scene.primary_axis_max),
            "line_axis_max": int(scene.line_axis_max),
            "layout_jitter": dict(p.layout_jitter_meta),
            "text_style": {
                "tick_font_size_px": int(p.tick_font_size),
                "label_font_size_px": int(p.label_font_size),
                "value_font_size_px": int(p.value_font_size),
                "legend_font_size_px": int(p.legend_font_size),
                "font_assets": dict(artifacts.font_assets),
            },
            "background": dict(artifacts.background_style),
            "post_image_noise": dict(artifacts.post_image_noise),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(scene.plot_bbox),
            "legend_bbox_px": list(scene.legend_bbox),
            "context_protected_bboxes_px": {
                "plot": list(scene.plot_bbox),
                "legend": list(scene.legend_bbox),
            },
            "primary_points_px": [list(point) for point in scene.primary_points],
            "line_points_px": [list(point) for point in scene.line_points],
            "entities": [dict(entity) for entity in scene.entities],
        },
        "execution_trace": {
            "answer": relations.get("answer"),
            "answer_type": relations.get("answer_type"),
            **dict(relations),
        },
        "witness_symbolic": {
            "type": str(annotation.annotation_type),
            "count": int(len(annotation.value)),
        },
        "projected_annotation": dict(annotation.projected_annotation),
        "background": dict(artifacts.background_style),
        "post_image_noise": dict(artifacts.post_image_noise),
    }


__all__ = ["ComboRenderArtifacts", "build_trace_scaffold", "render_dataset"]
