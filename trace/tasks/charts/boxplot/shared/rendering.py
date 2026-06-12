"""Rendering and trace helpers for the boxplot chart scene."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.boxplot.shared.defaults import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    RENDER_FALLBACKS,
    RENDERING_DEFAULTS,
    SCENE_NAMESPACE,
    SCENE_VARIANT,
)
from trace.tasks.charts.shared.chart_scene import (
    BoxPlotSpec,
    RenderedChartScene,
    render_boxplot_scene,
    render_paired_boxplot_scene,
    value_axis_render_metadata,
)
from trace.tasks.charts.shared.distribution_chart_common import (
    projected_mark_annotation,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from trace.tasks.charts.shared.visual_defaults import (
    chart_font_asset_metadata,
    sample_chart_font_family,
)
from trace.tasks.shared.text_rendering import temporary_default_font_family


@dataclass(frozen=True)
class BoxplotRenderArtifacts:
    rendered_scene: RenderedChartScene
    background_style: dict[str, Any]
    font_assets: dict[str, Any]
    mark_style: dict[str, Any]
    post_image_noise: dict[str, Any]


def resolve_mark_style(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    mark_count: int = 1,
) -> dict[str, Any]:
    return dict(
        resolve_chart_mark_colors(
            params,
            render_defaults=RENDERING_DEFAULTS,
            defaults=RENDER_FALLBACKS,
            instance_seed=int(instance_seed),
            scene_variant=SCENE_VARIANT,
            mark_count=int(mark_count),
        )
    )


def _render_params(params: Mapping[str, Any], mark_style: Mapping[str, Any], *, instance_seed: int) -> Any:
    return resolve_chart_render_params_for_task(
        {**dict(params), **dict(mark_style)},
        render_defaults=RENDERING_DEFAULTS,
        defaults=RENDER_FALLBACKS,
        instance_seed=int(instance_seed),
    )


def render_single_boxplot_scene(
    *,
    boxplots: Sequence[BoxPlotSpec],
    params: Mapping[str, Any],
    mark_style: Mapping[str, Any],
    instance_seed: int,
) -> BoxplotRenderArtifacts:
    render_params = _render_params(params, mark_style, instance_seed=int(instance_seed))
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = render_boxplot_scene(
            background,
            boxplots=boxplots,
            render_params=render_params,
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return BoxplotRenderArtifacts(
        rendered_scene=replace(rendered_scene, image=image),
        background_style=dict(background_meta),
        font_assets=chart_font_asset_metadata(str(chart_font_family)),
        mark_style=dict(mark_style),
        post_image_noise=dict(post_noise_meta),
    )


def render_paired_boxplot_panels(
    *,
    before_boxplots: Sequence[BoxPlotSpec],
    after_boxplots: Sequence[BoxPlotSpec],
    params: Mapping[str, Any],
    mark_style: Mapping[str, Any],
    before_title: str,
    after_title: str,
    instance_seed: int,
) -> BoxplotRenderArtifacts:
    """Render before/after boxplot panels with a shared value axis and labels."""

    render_params = _render_params(params, mark_style, instance_seed=int(instance_seed))
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = render_paired_boxplot_scene(
            background,
            before_boxplots=before_boxplots,
            after_boxplots=after_boxplots,
            render_params=render_params,
            before_title=str(before_title),
            after_title=str(after_title),
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return BoxplotRenderArtifacts(
        rendered_scene=replace(rendered_scene, image=image),
        background_style=dict(background_meta),
        font_assets=chart_font_asset_metadata(str(chart_font_family)),
        mark_style=dict(mark_style),
        post_image_noise=dict(post_noise_meta),
    )


def point_map_for_labels(
    rendered_scene: RenderedChartScene,
    labels: Sequence[str],
) -> dict[str, list[float]]:
    projection = projected_mark_annotation(rendered_scene, [str(label) for label in labels])
    points = [list(point) for point in projection["pixel_point_set"]]
    return {
        str(label): [round(float(point[0]), 3), round(float(point[1]), 3)]
        for label, point in zip(labels, points)
    }


def label_centers(rendered_scene: RenderedChartScene) -> dict[str, list[float]]:
    return {
        str(mark["label"]): list(mark["label_center_px"])
        for mark in rendered_scene.mark_traces
    }


def render_trace_sections(artifacts: BoxplotRenderArtifacts) -> tuple[dict[str, Any], dict[str, Any]]:
    rendered_scene = artifacts.rendered_scene
    render_spec = {
        "canvas_width": int(rendered_scene.image.size[0]),
        "canvas_height": int(rendered_scene.image.size[1]),
        "coord_space": "pixel",
        "scene_variant": SCENE_VARIANT,
        "background_style": dict(artifacts.background_style),
        "font_assets": dict(artifacts.font_assets),
        "post_image_noise": dict(artifacts.post_image_noise),
        "text_style": {
            "label_font_size_px": int(RENDERING_DEFAULTS.get("label_font_size_px", 22)),
            "tick_font_size_px": int(RENDERING_DEFAULTS.get("tick_font_size_px", 18)),
            "label_stroke_width_px": int(RENDERING_DEFAULTS.get("label_stroke_width_px", 2)),
        },
        "mark_style": dict(artifacts.mark_style),
        "plot_bbox_px": list(rendered_scene.plot_bbox_px),
        "y_axis_max": int(rendered_scene.y_axis_max),
        "y_ticks": [int(value) for value in rendered_scene.y_ticks],
        **value_axis_render_metadata(rendered_scene),
    }
    render_map = {
        "image_id": "img0",
        "plot_bbox_px": list(rendered_scene.plot_bbox_px),
        "label_centers_px": label_centers(rendered_scene),
    }
    return render_spec, render_map


def build_trace_scaffold(
    *,
    artifacts: BoxplotRenderArtifacts,
    relations: Mapping[str, Any],
    question_format: str,
    witness_symbolic: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
) -> dict[str, Any]:
    render_spec, render_map = render_trace_sections(artifacts)
    rendered_scene = artifacts.rendered_scene
    return {
        "scene_ir": {
            "scene_kind": "chart_boxplot_distribution",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": dict(relations),
        },
        "render_spec": render_spec,
        "render_map": render_map,
        "execution_trace": {
            "question_format": str(question_format),
            "labels": [str(mark["label"]) for mark in rendered_scene.mark_traces],
            **dict(relations),
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
    }


__all__ = [
    "BoxplotRenderArtifacts",
    "build_trace_scaffold",
    "point_map_for_labels",
    "render_paired_boxplot_panels",
    "render_single_boxplot_scene",
    "resolve_mark_style",
]
