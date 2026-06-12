
from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.charts.radial_sankey.shared.radial_sankey_common import (
    SCENE_ID,
    TRANSFER_TOTAL_QUERY_IDS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_VARIANT_LOADS,
)
from trace.tasks.charts.radial_sankey.shared.runtime import RadialSankeyRenderResult, font_assets_payload
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


def annotation_payload(*, dataset: Mapping[str, Any], rendered: RadialSankeyRenderResult) -> dict[str, Any]:
    query = dict(dataset["query"])
    rendered_scene = rendered.rendered_scene
    annotation_link_ids = [str(link_id) for link_id in query["annotation_link_ids"]]
    annotation_node_ids = [str(node_id) for node_id in query.get("annotation_node_ids", [])]
    annotation_bboxes = [
        list(rendered_scene.link_label_bbox_map[str(link_id)])
        for link_id in annotation_link_ids
    ] + [
        list(rendered_scene.node_bbox_map[str(node_id)])
        for node_id in annotation_node_ids
    ]
    return {
        "link_ids": list(annotation_link_ids),
        "node_ids": list(annotation_node_ids),
        "bboxes": list(annotation_bboxes),
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": list(annotation_bboxes),
            "pixel_bbox_set": list(annotation_bboxes),
            "link_ids": list(annotation_link_ids),
            "node_ids": list(annotation_node_ids),
            "link_label_bbox_map": {
                str(link_id): list(rendered_scene.link_label_bbox_map[str(link_id)])
                for link_id in annotation_link_ids
            },
            "node_bbox_map": {
                str(node_id): list(rendered_scene.node_bbox_map[str(node_id)])
                for node_id in annotation_node_ids
            },
        },
    }




def build_trace_payload(
    *,
    dataset: Mapping[str, Any],
    rendered: RadialSankeyRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    annotation_payload: Mapping[str, Any],
) -> dict[str, Any]:
    query = dict(dataset["query"])
    rendered_scene = rendered.rendered_scene
    render_params = rendered.render_params
    query_params = {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "query_id_probabilities": dict(query_id_probabilities),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "source_count": int(dataset["source_count"]),
        "target_count": int(dataset["target_count"]),
        "link_count": int(dataset["link_count"]),
        "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
        "link_side_counts": dict(dataset["link_side_counts"]),
        "source_label": str(query.get("source_label", "")),
        "target_label": str(query.get("target_label", "")),
        "source_labels": [str(value) for value in query.get("source_labels", [])],
        "target_labels": [str(value) for value in query.get("target_labels", [])],
        "source_labels_joined": str(query.get("source_labels_joined", "")),
        "target_labels_joined": str(query.get("target_labels_joined", "")),
        "group_size": int(query.get("group_size", 0)),
        "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
        "comparison_link_ids": [str(link_id) for link_id in query.get("comparison_link_ids", [])],
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_radial_sankey",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_value": dataset["answer_value"],
                "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
                "annotation_link_ids": list(annotation_payload["link_ids"]),
                "annotation_node_ids": list(annotation_payload["node_ids"]),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params=dict(query_params),
        ),
        "render_spec": {
            "scene_variant": str(scene_variant),
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "source_count": int(dataset["source_count"]),
            "target_count": int(dataset["target_count"]),
            "link_count": int(dataset["link_count"]),
            "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
            "value_min": int(dataset["value_min"]),
            "value_max": int(dataset["value_max"]),
            "min_flow_width_px": int(render_params.min_flow_width_px),
            "max_flow_width_px": int(render_params.max_flow_width_px),
            "flow_alpha": int(render_params.flow_alpha),
            "radial_color_scheme": str(render_params.color_scheme_name),
            "flow_palette_rgb": [list(color) for color in render_params.flow_palette_rgb],
            "source_node_fill_rgb": list(render_params.source_node_fill_rgb),
            "target_node_fill_rgb": list(render_params.target_node_fill_rgb),
            "ring_line_rgb": list(render_params.ring_line_rgb),
            "layout_jitter": dict(render_params.layout_jitter_meta),
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
            "link_bboxes_px": dict(rendered_scene.link_bbox_map),
            "link_label_bboxes_px": dict(rendered_scene.link_label_bbox_map),
            "link_centers_px": dict(rendered_scene.link_center_map),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "question_format": "radial_sankey_transfer_total_value"
            if str(query_id) in TRANSFER_TOTAL_QUERY_IDS
            else "radial_sankey_dominant_endpoint_label",
            "scene_title": str(dataset["scene_title"]),
            "sources": [dict(node) for node in dataset["sources"]],
            "targets": [dict(node) for node in dataset["targets"]],
            "links": [dict(link) for link in dataset["links"]],
            "links_by_id": {str(key): dict(value) for key, value in dict(dataset["links_by_id"]).items()},
            "source_count": int(dataset["source_count"]),
            "target_count": int(dataset["target_count"]),
            "link_count": int(dataset["link_count"]),
            "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
            "link_side_counts": dict(dataset["link_side_counts"]),
            "value_min": int(dataset["value_min"]),
            "value_max": int(dataset["value_max"]),
            "answer_value": dataset["answer_value"],
            "answer_type": str(dataset["answer_type"]),
            "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
            "comparison_link_ids": [str(link_id) for link_id in query.get("comparison_link_ids", [])],
            "annotation_link_ids": list(annotation_payload["link_ids"]),
            "annotation_node_ids": list(annotation_payload["node_ids"]),
            "query_link_details": [dict(link) for link in query["link_details"]],
            "source_label": str(query.get("source_label", "")),
            "target_label": str(query.get("target_label", "")),
            "source_labels": [str(value) for value in query.get("source_labels", [])],
            "target_labels": [str(value) for value in query.get("target_labels", [])],
            "group_size": int(query.get("group_size", 0)),
            "expression": str(query["expression"]),
            "annotation_semantics": str(query_id),
        },
        "witness_symbolic": {
            "type": "radial_sankey_transfer_total_value_witness"
            if str(query_id) in TRANSFER_TOTAL_QUERY_IDS
            else "radial_sankey_dominant_endpoint_label_witness",
            "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
            "annotation_link_ids": list(annotation_payload["link_ids"]),
            "annotation_node_ids": list(annotation_payload["node_ids"]),
            "answer_value": dataset["answer_value"],
            "expression": str(query["expression"]),
        },
        "projected_annotation": dict(annotation_payload["projected_annotation"]),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


