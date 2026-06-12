"""Count map regions whose marker value satisfies a threshold."""

from __future__ import annotations

from typing import Any, Dict, List

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions
from .shared.choropleth_config import (
    _REASONING_LOAD_BY_OBJECTIVE,
    _SCENE_VARIANT_LOADS,
    SCENE_ID,
    resolve_scene_variant,
    resolve_threshold_direction,
)
from .shared.choropleth_marker_dataset import construct_marker_threshold_dataset
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.runtime import MarkerMapRenderResult, font_assets_payload, render_marker_map


@register_task
class ChartsMarkerMapMarkerRegionThresholdCountTask:
    """Count selected map-marker bubbles above or below a sampled threshold."""

    task_id = "task_charts__marker_map__marker_region_threshold_count"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "marker_region_threshold_count"
    supported_query_ids = ("marker_region_threshold_count",)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        scene_variant, scene_variant_probabilities = resolve_scene_variant(params, instance_seed=int(instance_seed))
        threshold_direction, threshold_direction_probabilities = resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        dataset = construct_marker_threshold_dataset(
            scene_variant=str(scene_variant),
            threshold_direction=str(threshold_direction),
            threshold_direction_probabilities=threshold_direction_probabilities,
            params=params,
            instance_seed=int(instance_seed),
        )
        rendered = render_marker_map(dataset=dataset, params=params, instance_seed=int(instance_seed))
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key="marker_region_threshold_count",
            dynamic_slot_values=dynamic_slots(dataset),
            instance_seed=int(instance_seed),
        )
        annotation_region_ids = [str(region_id) for region_id in dataset["annotation_region_ids"]]
        annotation_bboxes = [
            list(rendered.marker_group_bbox_map[str(region_id)])
            for region_id in annotation_region_ids
        ]
        answer_value = int(dataset["answer_value"])
        trace_payload = _build_trace_payload(
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            scene_variant=str(scene_variant),
            scene_variant_probabilities=scene_variant_probabilities,
            annotation_region_ids=annotation_region_ids,
            annotation_bboxes=annotation_bboxes,
            answer_value=answer_value,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type="integer", value=answer_value),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_bboxes)),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id="marker_region_threshold_count",
        )




def _build_trace_payload(
    *,
    dataset: Dict[str, Any],
    rendered: MarkerMapRenderResult,
    prompt_artifacts,
    scene_variant: str,
    scene_variant_probabilities: Dict[str, float],
    annotation_region_ids: List[str],
    annotation_bboxes: List[List[float]],
    answer_value: int,
) -> Dict[str, Any]:
    qparams = dict(dataset["question_params"])
    query_params = {
        "query_id": "marker_region_threshold_count",
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
        "geographic_map_variant_probabilities": dict(dataset.get("geographic_map_variant_probabilities", {})),
        "region_count": int(dataset["region_count"]),
        "target_count": int(dataset["target_count"]),
        "target_count_probabilities": dict(dataset["target_count_probabilities"]),
        **dict(qparams),
    }
    projected_annotation = {
        "type": "bbox_set",
        "bbox_set": list(annotation_bboxes),
        "pixel_bbox_set": list(annotation_bboxes),
        "bbox_map": {str(region_id): list(rendered.marker_group_bbox_map[str(region_id)]) for region_id in annotation_region_ids},
        "region_ids": list(annotation_region_ids),
        "marker_bboxes_by_region": {
            str(region_id): list(rendered.marker_bboxes_by_region.get(str(region_id), []))
            for region_id in annotation_region_ids
        },
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_marker_map",
            "entities": [dict(entity) for entity in rendered.rendered_scene.entities],
            "relations": {
                "query_id": "marker_region_threshold_count",
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "annotation_region_ids": list(annotation_region_ids),
            },
        },
        "query_spec": {
            "query_id": "marker_region_threshold_count",
            "template_id": "charts_marker_map_v1",
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": _render_spec(dataset=dataset, rendered=rendered, scene_variant=scene_variant),
        "render_map": _render_map(dataset=dataset, rendered=rendered),
        "execution_trace": {
            "query_id": "marker_region_threshold_count",
            "scene_variant": str(scene_variant),
            "question_format": "map_marker_threshold_count",
            "scene_title": str(dataset["scene_title"]),
            "map_asset_id": str(dataset.get("map_asset_id") or ""),
            "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
            "map_display_name": str(dataset.get("map_display_name") or ""),
            "map_region_noun": str(dataset.get("map_region_noun") or ""),
            "rows": int(dataset["rows"]),
            "cols": int(dataset["cols"]),
            "region_count": int(dataset["region_count"]),
            "active_cells": [[int(row), int(col)] for row, col in dataset["active_cells"]],
            "regions": [dict(item) for item in dataset["regions"]],
            "regions_by_id": {str(key): dict(value) for key, value in dict(dataset["regions_by_id"]).items()},
            "answer_value": int(answer_value),
            "answer_type": "integer",
            "annotation_region_ids": list(annotation_region_ids),
            "annotation_semantics": "marker_region_threshold_count",
        },
        "witness_symbolic": {
            "type": "map_marker_threshold_count_witness",
            "candidate_region_ids": list(annotation_region_ids),
            "answer_value": int(answer_value),
        },
        "projected_annotation": dict(projected_annotation),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def _render_spec(
    *,
    dataset: Dict[str, Any],
    rendered: MarkerMapRenderResult,
    scene_variant: str,
) -> Dict[str, Any]:
    render_params = rendered.render_params
    return {
        "scene_variant": str(scene_variant),
        "map_asset_id": str(dataset.get("map_asset_id") or ""),
        "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
        "geographic_map_variant_probabilities": dict(dataset.get("geographic_map_variant_probabilities", {})),
        "map_display_name": str(dataset.get("map_display_name") or ""),
        "map_region_noun": str(dataset.get("map_region_noun") or ""),
        "map_source": dict(dataset.get("map_source", {})),
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "rows": int(dataset["rows"]),
        "cols": int(dataset["cols"]),
        "active_cells": [[int(row), int(col)] for row, col in dataset["active_cells"]],
        "selected_region_ids": [str(region["region_id"]) for region in dataset["regions"]],
        "legend_position": str(render_params.legend_position),
        "legend_position_probabilities": dict(render_params.legend_position_probabilities),
        "marker_render": dict(rendered.marker_render_meta),
        "map_palette_rgb": [[int(channel) for channel in color] for color in render_params.map_palette_rgb],
        "map_palette_variant": str(render_params.map_palette_variant),
        "map_palette_variant_probabilities": dict(render_params.map_palette_variant_probabilities),
        "background_style": dict(rendered.background_meta),
        "font_assets": font_assets_payload(rendered.chart_font_family),
        "region_gap_px": int(render_params.region_gap_px),
        "layout_jitter": dict(render_params.layout_jitter_meta),
        "map_render_style": dict(rendered.rendered_scene.render_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def _render_map(*, dataset: Dict[str, Any], rendered: MarkerMapRenderResult) -> Dict[str, Any]:
    render_map = {
        "panel_bbox_px": list(rendered.rendered_scene.panel_bbox_px),
        "title_bbox_px": list(rendered.rendered_scene.title_bbox_px),
        "map_bbox_px": list(rendered.rendered_scene.map_bbox_px),
        "legend_bbox_px": list(rendered.rendered_scene.legend_bbox_px),
        "region_bboxes_px": dict(rendered.rendered_scene.region_bbox_map),
        "region_centers_px": dict(rendered.rendered_scene.region_center_map),
        "legend_entry_bboxes_px": dict(rendered.rendered_scene.legend_entry_bbox_map),
        "marker_group_bboxes_px": dict(rendered.marker_group_bbox_map),
        "marker_bboxes_px": dict(rendered.marker_bboxes_by_region),
    }
    if "world_projection_bbox_px" in rendered.rendered_scene.render_meta:
        render_map["world_projection_bbox_px"] = list(rendered.rendered_scene.render_meta["world_projection_bbox_px"])
    return render_map


__all__ = ["ChartsMarkerMapMarkerRegionThresholdCountTask"]
