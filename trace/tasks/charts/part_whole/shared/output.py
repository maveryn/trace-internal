
from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.charts.part_whole.shared.runtime import PartWholeRenderResult, font_assets_payload
from trace.tasks.charts.part_whole.shared.share_arithmetic_common import (
    REASONING_LOAD_BY_QUERY_ID,
    SCENE_VARIANT_LOADS,
    PartWholeDataset,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec




def build_trace_payload(
    *,
    dataset: PartWholeDataset,
    rendered: PartWholeRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    annotation_payload: Mapping[str, Any],
) -> dict[str, Any]:
    extras = dict(dataset.trace_extras)
    rendered_scene = rendered.rendered_scene
    values_by_label = {str(category.label): int(category.value) for category in dataset.categories}
    annotation_keys = list(annotation_payload["keys"])
    return {
        "scene_ir": {
            "scene_kind": f"chart_{str(scene_variant)}_composition_share_arithmetic",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "category_labels": [str(category.label) for category in dataset.categories],
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params={
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "category_count": int(extras["category_count"]),
                "annotation_labels": [str(label) for label in dataset.annotation_labels],
                "annotation_keys": [str(key) for key in annotation_keys],
            },
        ),
        "render_spec": {
            "canvas_width": int(rendered.canvas_width),
            "canvas_height": int(rendered.canvas_height),
            "coord_space": "pixel",
            "scene_variant": str(scene_variant),
            "background_style": dict(rendered.background_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
            "font_assets": font_assets_payload(),
            "layout_jitter": dict(rendered_scene.layout_jitter_meta),
            "table_position": str(rendered_scene.layout_jitter_meta.get("table_position", "right")),
            "table_columns": int(rendered_scene.layout_jitter_meta.get("table_columns", 1)),
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "table_bbox_px": list(rendered_scene.table_bbox_px),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "table_bbox_px": list(rendered_scene.table_bbox_px),
            "chart_traces": [dict(trace) for trace in rendered_scene.chart_traces],
            "category_traces": [dict(trace) for trace in rendered_scene.category_traces],
            "annotation_bbox_by_label": {
                str(label): list(bbox)
                for label, bbox in rendered_scene.annotation_bbox_by_label.items()
            },
            "annotation_point_by_label": {
                str(label): list(point)
                for label, point in rendered_scene.annotation_point_by_label.items()
            },
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "answer_value": int(dataset.answer_value),
            "category_count": int(extras["category_count"]),
            "category_count_range": list(extras["category_count_range"]),
            "category_values": {str(label): int(value) for label, value in values_by_label.items()},
            "categories": [
                {
                    "label": str(category.label),
                    "value": int(category.value),
                    "fill_rgb": [int(channel) for channel in category.color_rgb],
                }
                for category in dataset.categories
            ],
            "annotation_labels": [str(label) for label in dataset.annotation_labels],
            "annotation_keys": [str(key) for key in annotation_keys],
            "annotation_values": [int(value) for value in annotation_payload["values"]],
            "question_format": "numeric_open",
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            **dict(extras),
        },
        "witness_symbolic": {
            "type": "composition_share_arithmetic",
            "query_id": str(query_id),
            "answer_value": int(dataset.answer_value),
            "annotation_values": [int(value) for value in annotation_payload["values"]],
            "calculation": dict(extras),
        },
        "projected_annotation": dict(annotation_payload["projected_annotation"]),
    }


