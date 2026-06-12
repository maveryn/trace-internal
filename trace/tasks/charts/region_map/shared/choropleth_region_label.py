"""Region-map task component assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.font_assets import font_asset_version, sample_font_family
from ....shared.text_rendering import temporary_default_font_family
from .choropleth_assets import WORLD_MAP_ASSET_ID as _WORLD_MAP_ASSET_ID
from .choropleth_config import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    TASK_ID,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_VARIANT_LOADS,
    _is_categorical_query_id,
    _is_group_filtered_value_query_id,
    _is_marker_query_id,
    _is_region_sum_value_query_id,
)
from .choropleth_dataset import _construct_dataset
from .choropleth_marker_rendering import _render_marker_layer
from .choropleth_rendering import (
    _render_choropleth_map,
    _render_world_choropleth_map,
    _resolve_render_params,
)
from .prompts import build_prompt_artifacts, dynamic_slots


@dataclass(frozen=True)
class RegionMapTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: List[List[float]]
    image: Image.Image
    trace_payload: Dict[str, Any]
    query_id: str


@dataclass(frozen=True)
class RegionMapRendered:
    rendered_scene: Any
    image: Image.Image
    render_params: Any
    chart_font_family: str
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    marker_bboxes_by_region: Dict[str, List[List[float]]]
    marker_group_bbox_map: Dict[str, List[float]]
    marker_render_meta: Dict[str, Any]


def build_region_map_task_components(
    *,
    query_id: str,
    scene_variant: str,
    query_id_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
) -> RegionMapTaskComponents:
    dataset = _construct_dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        params=dict(params),
        instance_seed=int(instance_seed),
    )
    rendered = render_region_map_dataset(
        dataset=dataset,
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        params=params,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_artifacts(
        prompt_query_key=str(query_id),
        dynamic_slot_values=dynamic_slots(
            dataset=dataset,
            query_id=str(query_id),
            scene_variant=str(scene_variant),
        ),
        instance_seed=int(instance_seed),
    )
    annotation_region_ids = [str(region_id) for region_id in dataset["annotation_region_ids"]]
    if _is_marker_query_id(str(query_id)):
        annotation_bboxes = [
            list(rendered.marker_group_bbox_map[str(region_id)])
            for region_id in annotation_region_ids
        ]
    else:
        annotation_bboxes = [
            list(rendered.rendered_scene.region_bbox_map[str(region_id)])
            for region_id in annotation_region_ids
        ]
    answer_value = (
        str(dataset["answer_value"])
        if str(dataset["answer_type"]) == "string"
        else int(dataset["answer_value"])
    )
    trace_payload = build_trace_payload(
        dataset=dataset,
        rendered=rendered,
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        query_id_probabilities=query_id_probabilities,
        scene_variant_probabilities=scene_variant_probabilities,
        annotation_region_ids=annotation_region_ids,
        annotation_bboxes=annotation_bboxes,
        answer_value=answer_value,
    )
    return RegionMapTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type=str(dataset["answer_type"]),
        answer_value=answer_value,
        annotation_type="bbox_set",
        annotation_value=list(annotation_bboxes),
        image=rendered.image,
        trace_payload=trace_payload,
        query_id=str(query_id),
    )


def render_region_map_dataset(
    *,
    dataset: Mapping[str, Any],
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> RegionMapRendered:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(
        render_style_params,
        query_id=str(query_id),
        legend_count=len(dataset["legend_bins"]),
    )
    chart_font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.chart_font",
        params=params,
        explicit_key="chart_font_family",
        weights_key="chart_font_family_weights",
    )
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    categorical = _is_categorical_query_id(str(query_id))
    marker_task = _is_marker_query_id(str(query_id))
    show_region_value_labels = _is_region_sum_value_query_id(str(query_id))
    marker_bboxes_by_region: Dict[str, List[List[float]]] = {}
    marker_group_bbox_map: Dict[str, List[float]] = {}
    marker_render_meta: Dict[str, Any] = {}
    with temporary_default_font_family(str(chart_font_family)):
        if str(scene_variant) == "geographic_region_map":
            rendered_scene = _render_world_choropleth_map(
                background,
                scene_title=str(dataset["scene_title"]),
                map_asset_id=str(dataset.get("map_asset_id") or _WORLD_MAP_ASSET_ID),
                regions=list(dataset["regions"]),
                legend_bins=list(dataset["legend_bins"]),
                render_params=render_params,
                instance_seed=int(instance_seed),
                categorical=bool(categorical),
                draw_color_legend=not bool(marker_task),
                neutral_regions=bool(marker_task),
                show_region_value_labels=bool(show_region_value_labels),
            )
        else:
            rendered_scene = _render_choropleth_map(
                background,
                scene_title=str(dataset["scene_title"]),
                rows=int(dataset["rows"]),
                cols=int(dataset["cols"]),
                regions=list(dataset["regions"]),
                legend_bins=list(dataset["legend_bins"]),
                render_params=render_params,
                instance_seed=int(instance_seed),
                categorical=bool(categorical),
                draw_color_legend=not bool(marker_task),
                neutral_regions=bool(marker_task),
                show_region_value_labels=bool(show_region_value_labels),
            )
        if bool(marker_task):
            rendered_scene, marker_bboxes_by_region, marker_group_bbox_map, marker_render_meta = _render_marker_layer(
                rendered_scene,
                dataset=dict(dataset),
                render_params=render_params,
                params=render_style_params,
                instance_seed=int(instance_seed),
            )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return RegionMapRendered(
        rendered_scene=rendered_scene,
        image=image,
        render_params=render_params,
        chart_font_family=str(chart_font_family),
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        marker_bboxes_by_region=dict(marker_bboxes_by_region),
        marker_group_bbox_map=dict(marker_group_bbox_map),
        marker_render_meta=dict(marker_render_meta),
    )




def build_trace_payload(
    *,
    dataset: Mapping[str, Any],
    rendered: RegionMapRendered,
    prompt_artifacts: Any,
    query_id: str,
    scene_variant: str,
    query_id_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float],
    annotation_region_ids: List[str],
    annotation_bboxes: List[List[float]],
    answer_value: Any,
) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    qparams = dict(dataset["question_params"])
    query_params = {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "query_id_probabilities": dict(query_id_probabilities),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
        "geographic_map_variant_probabilities": dict(dataset.get("geographic_map_variant_probabilities", {})),
        "region_count": int(dataset["region_count"]),
        "legend_bin_count": int(len(dataset["legend_bins"])),
        "target_count": int(dataset["target_count"]),
        "target_count_probabilities": dict(dataset["target_count_probabilities"]),
        **dict(qparams),
    }
    projected_annotation = {
        "type": "bbox_set",
        "bbox_set": list(annotation_bboxes),
        "pixel_bbox_set": list(annotation_bboxes),
        "bbox_map": {str(region_id): list(rendered_scene.region_bbox_map[str(region_id)]) for region_id in annotation_region_ids},
        "region_ids": list(annotation_region_ids),
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_region_map",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_value": answer_value,
                "annotation_region_ids": list(annotation_region_ids),
                "target_bin_indices": [int(value) for value in dataset["target_bin_indices"]],
            },
        },
        "query_spec": {
            "query_id": str(query_id),
            "template_id": str(prompt_artifacts.prompt_variant.get("prompt_bundle_id", "charts_region_map_v1")),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": {
            "scene_variant": str(scene_variant),
            "map_asset_id": str(dataset.get("map_asset_id") or ""),
            "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
            "geographic_map_variant_probabilities": dict(dataset.get("geographic_map_variant_probabilities", {})),
            "map_display_name": str(dataset.get("map_display_name") or ""),
            "map_region_noun": str(dataset.get("map_region_noun") or ""),
            "map_source": dict(dataset.get("map_source", {})),
            "canvas_width": int(rendered.render_params.canvas_width),
            "canvas_height": int(rendered.render_params.canvas_height),
            "rows": int(dataset["rows"]),
            "cols": int(dataset["cols"]),
            "active_cells": [[int(row), int(col)] for row, col in dataset["active_cells"]],
            "selected_region_ids": [str(region["region_id"]) for region in dataset["regions"]],
            "legend_bins": [dict(item) for item in dataset["legend_bins"]],
            "legend_position": str(rendered.render_params.legend_position),
            "legend_position_probabilities": dict(rendered.render_params.legend_position_probabilities),
            "show_region_value_labels": bool(_is_region_sum_value_query_id(str(query_id))),
            "map_palette_rgb": [[int(channel) for channel in color] for color in rendered.render_params.map_palette_rgb],
            "map_palette_variant": str(rendered.render_params.map_palette_variant),
            "map_palette_variant_probabilities": dict(rendered.render_params.map_palette_variant_probabilities),
            "background_style": dict(rendered.background_meta),
            "font_assets": {
                "font_asset_version": font_asset_version(),
                "chart_font_family": str(rendered.chart_font_family),
            },
            "region_gap_px": int(rendered.render_params.region_gap_px),
            "layout_jitter": dict(rendered.render_params.layout_jitter_meta),
            "map_render_style": dict(rendered_scene.render_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "panel_bbox_px": list(rendered_scene.panel_bbox_px),
            "title_bbox_px": list(rendered_scene.title_bbox_px),
            "map_bbox_px": list(rendered_scene.map_bbox_px),
            "legend_bbox_px": list(rendered_scene.legend_bbox_px),
            "region_bboxes_px": dict(rendered_scene.region_bbox_map),
            "region_centers_px": dict(rendered_scene.region_center_map),
            "legend_entry_bboxes_px": dict(rendered_scene.legend_entry_bbox_map),
            **(
                {"world_projection_bbox_px": list(rendered_scene.render_meta["world_projection_bbox_px"])}
                if "world_projection_bbox_px" in rendered_scene.render_meta
                else {}
            ),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "question_format": "map_region_value" if _is_region_sum_value_query_id(str(query_id)) else "map_region_count",
            "scene_title": str(dataset["scene_title"]),
            "map_asset_id": str(dataset.get("map_asset_id") or ""),
            "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
            "map_display_name": str(dataset.get("map_display_name") or ""),
            "map_region_noun": str(dataset.get("map_region_noun") or ""),
            "rows": int(dataset["rows"]),
            "cols": int(dataset["cols"]),
            "region_count": int(dataset["region_count"]),
            "active_cells": [[int(row), int(col)] for row, col in dataset["active_cells"]],
            "legend_bins": [dict(item) for item in dataset["legend_bins"]],
            "regions": [dict(item) for item in dataset["regions"]],
            "regions_by_id": {str(key): dict(value) for key, value in dict(dataset["regions_by_id"]).items()},
            "answer_value": answer_value,
            "answer_type": str(dataset["answer_type"]),
            "annotation_region_ids": list(annotation_region_ids),
            "target_bin_indices": [int(value) for value in dataset["target_bin_indices"]],
            "nonmatching_bin_indices": [int(value) for value in dataset["nonmatching_bin_indices"]],
            "threshold_direction": str(dataset["threshold_direction"]),
            "annotation_semantics": str(query_id),
        },
        "witness_symbolic": {
            "type": "map_region_value_witness" if _is_region_sum_value_query_id(str(query_id)) else "map_region_count_witness",
            "candidate_region_ids": list(annotation_region_ids),
            "answer_value": answer_value,
        },
        "projected_annotation": dict(projected_annotation),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


__all__ = [
    "RegionMapTaskComponents",
    "build_region_map_task_components",
    "render_region_map_dataset",
]
