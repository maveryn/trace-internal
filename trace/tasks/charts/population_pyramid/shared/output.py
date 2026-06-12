
from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.charts.population_pyramid.shared.pyramid import (
    _Dataset,
    _QUERY_REASONING_LOADS,
)
from trace.tasks.charts.population_pyramid.shared.runtime import PopulationPyramidRenderResult
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


def annotation_bboxes(*, dataset: _Dataset, rendered: PopulationPyramidRenderResult) -> list[list[float]]:
    return [
        list(rendered.rendered_scene.row_bar_bboxes_px[str(row_id)])
        for row_id in dataset.query.annotation_row_ids
    ]




def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: PopulationPyramidRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    annotation_bboxes_px: list[list[float]],
) -> dict[str, Any]:
    rows = [
        {
            "row_id": str(row.row_id),
            "label": str(row.label),
            "left_value": int(row.left_value),
            "right_value": int(row.right_value),
            "gap": int(row.gap),
            "total": int(row.total),
        }
        for row in dataset.rows
    ]
    row_labels = [str(row.label) for row in dataset.rows]
    query_params = dict(dataset.query.params)
    return {
        "scene_ir": {
            "scene_kind": "population_pyramid_chart",
            "entities": [dict(entity) for entity in rendered.rendered_scene.entities],
            "relations": {
                "query_id": str(dataset.query_id),
                "left_series_label": str(dataset.left_series_label),
                "right_series_label": str(dataset.right_series_label),
                "row_labels": list(row_labels),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(dataset.query_id),
            params={
                "query_id": str(dataset.query_id),
                "query_id_probabilities": dict(dataset.query_id_probabilities),
                "answer_value": dataset.query.answer,
                "annotation_row_ids": [str(row_id) for row_id in dataset.query.annotation_row_ids],
                **dict(query_params),
            },
        ),
        "render_spec": {
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "coord_space": "pixel",
            "left_series_label": str(dataset.left_series_label),
            "right_series_label": str(dataset.right_series_label),
            "left_color_rgb": [int(channel) for channel in dataset.left_color_rgb],
            "right_color_rgb": [int(channel) for channel in dataset.right_color_rgb],
            "plot_bbox_px": list(rendered.rendered_scene.plot_bbox_px),
            "render_meta": dict(rendered.rendered_scene.render_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered.rendered_scene.plot_bbox_px),
            "row_bar_bboxes_px": dict(rendered.rendered_scene.row_bar_bboxes_px),
            "left_bar_bboxes_px": dict(rendered.rendered_scene.left_bar_bboxes_px),
            "right_bar_bboxes_px": dict(rendered.rendered_scene.right_bar_bboxes_px),
            "row_label_bboxes_px": dict(rendered.rendered_scene.row_label_bboxes_px),
        },
        "execution_trace": {
            "query_id": str(dataset.query_id),
            "question_format": "population_pyramid",
            "left_series_label": str(dataset.left_series_label),
            "right_series_label": str(dataset.right_series_label),
            "row_count": int(len(dataset.rows)),
            "row_labels": list(row_labels),
            "rows": list(rows),
            "answer_value": dataset.query.answer,
            "answer_type": str(dataset.query.answer_type),
            "annotation_row_ids": [str(row_id) for row_id in dataset.query.annotation_row_ids],
            **dict(query_params),
        },
        "witness_symbolic": {
            "type": "population_pyramid_witness",
            "query_id": str(dataset.query_id),
            "answer_value": dataset.query.answer,
            "annotation_row_ids": [str(row_id) for row_id in dataset.query.annotation_row_ids],
        },
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in annotation_bboxes_px],
            "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes_px],
            "row_ids": [str(row_id) for row_id in dataset.query.annotation_row_ids],
        },
        "post_image_noise": dict(rendered.post_noise_meta),
    }


