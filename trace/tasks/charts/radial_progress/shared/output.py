
from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.charts.radial_progress.shared.progress_chart import (
    SCENE_ID,
    _Dataset,
    _QUERY_LOADS,
    _SCENE_LOADS,
)
from trace.tasks.charts.radial_progress.shared.runtime import RadialProgressRenderResult, font_assets_payload
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


def annotation_payload(*, dataset: _Dataset, rendered: RadialProgressRenderResult) -> dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    annotation_item_ids = [str(value) for value in dataset.query.annotation_item_ids]
    item_by_id = {item.item_id: item for item in dataset.items}
    annotation_labels = [str(item_by_id[item_id].label) for item_id in annotation_item_ids]
    annotation_bboxes = [list(rendered_scene.item_bboxes_px[str(item_id)]) for item_id in annotation_item_ids]
    return {
        "item_ids": list(annotation_item_ids),
        "labels": list(annotation_labels),
        "bboxes": list(annotation_bboxes),
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": list(annotation_bboxes),
            "bbox_map": {str(item_id): list(rendered_scene.item_bboxes_px[str(item_id)]) for item_id in annotation_item_ids},
            "item_ids": list(annotation_item_ids),
            "item_labels": list(annotation_labels),
        },
    }




def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: RadialProgressRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    answer_value: int | str,
    annotation_payload: Mapping[str, Any],
) -> dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    qparams = dict(dataset.query.params)
    label_to_value = {str(item.label): int(item.value) for item in dataset.items}
    is_label_answer = str(dataset.query.answer_type) == "string"
    query_params = {
        "query_id": str(dataset.query_id),
        "query_id_probabilities": dict(dataset.query_probabilities),
        "scene_variant": str(dataset.scene_variant),
        "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
        "item_count": int(len(dataset.items)),
        "answer_value": answer_value,
        **dict(qparams),
    }
    question_format = "radial_progress_extremum_remaining_label" if is_label_answer else "radial_progress_condition_count"
    witness_type = "radial_progress_extremum_remaining_label_witness" if is_label_answer else "radial_progress_condition_count_witness"
    return {
        "scene_ir": {
            "scene_kind": SCENE_ID,
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(dataset.query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer_value": answer_value,
                "annotation_item_ids": list(annotation_payload["item_ids"]),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(dataset.query_id),
            params=dict(query_params),
        ),
        "render_spec": {
            "scene_variant": str(dataset.scene_variant),
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "category_labels": [str(item.label) for item in dataset.items],
            "render_meta": dict(rendered_scene.render_meta),
            "font_assets": font_assets_payload(chart_font_family=rendered.chart_font_family),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "item_bboxes_px": dict(rendered_scene.item_bboxes_px),
            "progress_bboxes_px": dict(rendered_scene.progress_bboxes_px),
        },
        "execution_trace": {
            "query_id": str(dataset.query_id),
            "question_format": str(question_format),
            "scene_variant": str(dataset.scene_variant),
            "item_count": int(len(dataset.items)),
            "items": [dict(entity) for entity in rendered_scene.entities],
            "label_to_value": dict(label_to_value),
            "answer_value": answer_value,
            "answer_type": str(dataset.query.answer_type),
            "annotation_item_ids": list(annotation_payload["item_ids"]),
            "annotation_labels": list(annotation_payload["labels"]),
            **dict(qparams),
        },
        "witness_symbolic": {
            "type": str(witness_type),
            "answer_value": answer_value,
            "annotation_item_ids": list(annotation_payload["item_ids"]),
        },
        "projected_annotation": dict(annotation_payload["projected_annotation"]),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


