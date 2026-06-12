
from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.tasks.charts.sankey.shared.runtime import SankeyRenderResult, font_assets_payload
from trace.tasks.charts.sankey.shared.sankey_common import (
    NODE_SIDE_TOTAL_QUERY_IDS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_VARIANT_LOADS,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


def annotation_payload(*, dataset: Mapping[str, Any], rendered: SankeyRenderResult) -> Dict[str, Any]:
    query = dict(dataset["query"])
    annotation_segment_ids = [str(segment_id) for segment_id in query["annotation_segment_ids"]]
    rendered_scene = rendered.rendered_scene
    annotation_bboxes = [
        list(rendered_scene.segment_label_bbox_map[str(segment_id)])
        for segment_id in annotation_segment_ids
    ]
    return {
        "type": "bbox_set",
        "bboxes": list(annotation_bboxes),
        "projected": {
            "type": "bbox_set",
            "bbox_set": list(annotation_bboxes),
            "pixel_bbox_set": list(annotation_bboxes),
            "segment_ids": list(annotation_segment_ids),
            "segment_label_bbox_map": {
                str(segment_id): list(rendered_scene.segment_label_bbox_map[str(segment_id)])
                for segment_id in annotation_segment_ids
            },
            "segment_bbox_map": {
                str(segment_id): list(rendered_scene.segment_bbox_map[str(segment_id)])
                for segment_id in annotation_segment_ids
            },
        },
        "segment_ids": list(annotation_segment_ids),
    }




def build_trace_payload(
    *,
    dataset: Mapping[str, Any],
    rendered: SankeyRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    annotation_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    query = dict(dataset["query"])
    rendered_scene = rendered.rendered_scene
    annotation_segment_ids = [str(segment_id) for segment_id in annotation_payload["segment_ids"]]
    query_params = {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "query_id_probabilities": dict(query_id_probabilities),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "source_count": int(dataset["source_count"]),
        "middle_count": int(dataset["middle_count"]),
        "target_count": int(dataset["target_count"]),
        "path_count": int(dataset["path_count"]),
        "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
        "path_side_counts": dict(dataset["path_side_counts"]),
        "source_label": str(query.get("source_label", "")),
        "middle_label": str(query.get("middle_label", "")),
        "target_label": str(query.get("target_label", "")),
        "route_count": int(query.get("route_count", 1)),
        "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
        "node_side": str(query.get("node_side", "")),
        "connected_count": int(query["connected_count"]) if "connected_count" in query else None,
        "node_side_total": int(query["node_side_total"]) if "node_side_total" in query else None,
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_sankey",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_value": int(dataset["answer_value"]),
                "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
                "annotation_segment_ids": list(annotation_segment_ids),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params=query_params,
        ),
        "render_spec": {
            "scene_variant": str(scene_variant),
            "canvas_width": int(rendered.render_params.canvas_width),
            "canvas_height": int(rendered.render_params.canvas_height),
            "source_count": int(dataset["source_count"]),
            "middle_count": int(dataset["middle_count"]),
            "target_count": int(dataset["target_count"]),
            "path_count": int(dataset["path_count"]),
            "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
            "value_min": int(dataset["value_min"]),
            "value_max": int(dataset["value_max"]),
            "min_flow_width_px": int(rendered.render_params.min_flow_width_px),
            "max_flow_width_px": int(rendered.render_params.max_flow_width_px),
            "layout_jitter": dict(rendered.render_params.layout_jitter_meta),
            "background_style": dict(rendered.background_meta),
            "font_assets": font_assets_payload(chart_font_family=rendered.chart_font_family),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "panel_bbox_px": list(rendered_scene.panel_bbox_px),
            "title_bbox_px": list(rendered_scene.title_bbox_px),
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "node_bboxes_px": dict(rendered_scene.node_bbox_map),
            "node_label_bboxes_px": dict(rendered_scene.node_label_bbox_map),
            "segment_bboxes_px": dict(rendered_scene.segment_bbox_map),
            "segment_label_bboxes_px": dict(rendered_scene.segment_label_bbox_map),
            "segment_centers_px": dict(rendered_scene.segment_center_map),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "question_format": "sankey_node_side_total_value"
            if str(query_id) in NODE_SIDE_TOTAL_QUERY_IDS
            else "sankey_path_value",
            "scene_title": str(dataset["scene_title"]),
            "sources": [dict(node) for node in dataset["sources"]],
            "middles": [dict(node) for node in dataset["middles"]],
            "targets": [dict(node) for node in dataset["targets"]],
            "paths": [dict(path) for path in dataset["paths"]],
            "paths_by_id": {str(key): dict(value) for key, value in dict(dataset["paths_by_id"]).items()},
            "source_count": int(dataset["source_count"]),
            "middle_count": int(dataset["middle_count"]),
            "target_count": int(dataset["target_count"]),
            "path_count": int(dataset["path_count"]),
            "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
            "path_side_counts": dict(dataset["path_side_counts"]),
            "value_min": int(dataset["value_min"]),
            "value_max": int(dataset["value_max"]),
            "answer_value": int(dataset["answer_value"]),
            "answer_type": "integer",
            "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
            "annotation_segment_ids": list(annotation_segment_ids),
            "query_path_details": [dict(path) for path in query["path_details"]],
            "node_side": str(query.get("node_side", "")),
            "connected_count": int(query["connected_count"]) if "connected_count" in query else None,
            "node_side_total": int(query["node_side_total"]) if "node_side_total" in query else None,
            "expression": str(query["expression"]),
            "annotation_semantics": str(query_id),
        },
        "witness_symbolic": {
            "type": "sankey_node_side_total_value_witness"
            if str(query_id) in NODE_SIDE_TOTAL_QUERY_IDS
            else "sankey_path_value_witness",
            "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
            "annotation_segment_ids": list(annotation_segment_ids),
            "answer_value": int(dataset["answer_value"]),
            "expression": str(query["expression"]),
        },
        "projected_annotation": dict(annotation_payload["projected"]),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


