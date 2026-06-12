
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from PIL import Image

from trace.tasks.charts.scatter_readout.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.scatter_readout.shared.runtime import (
    ScatterReadoutRenderResult,
    font_assets_payload,
    render_scatter_readout_dataset,
)
from trace.tasks.charts.scatter_readout.shared.series_readout import (
    UNANSWERABLE_ANSWER,
    _Dataset,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _build_keyed_annotation_bboxes,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


@dataclass(frozen=True)
class ScatterReadoutTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: int | str
    annotation_type: str
    annotation_value: Dict[str, List[float]]
    image: Image.Image
    query_id: str
    trace_payload: Dict[str, Any]


def answer_value(dataset: _Dataset) -> int | str:
    if str(dataset.query.answer_type) == "integer":
        return int(dataset.query.answer)
    return str(dataset.query.answer)


def annotation_payload(*, dataset: _Dataset, rendered: ScatterReadoutRenderResult) -> Dict[str, Any]:
    keyed_bboxes = _build_keyed_annotation_bboxes(dataset, rendered.rendered_scene)
    return {
        "type": "keyed_bbox_map",
        "bbox_map": dict(keyed_bboxes),
        "projected": {
            "type": "keyed_bbox_map",
            "bbox_map": dict(keyed_bboxes),
            "pixel_bbox_map": dict(keyed_bboxes),
        },
    }


def _point_records(dataset: _Dataset) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for series_item in dataset.series:
        for point in series_item.points:
            rows.append(
                {
                    "point_id": str(point.point_id),
                    "series_label": str(point.series_label),
                    "x_label": str(point.x_label),
                    "x_index": int(point.x_index),
                    "y_value": int(point.y_value),
                }
            )
    return rows


def _series_records(dataset: _Dataset) -> List[Dict[str, Any]]:
    return [
        {
            "label": str(series_item.label),
            "color_rgb": list(series_item.color_rgb),
            "marker_shape": str(series_item.marker_shape),
            "point_ids": [str(point.point_id) for point in series_item.points],
        }
        for series_item in dataset.series
    ]




def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: ScatterReadoutRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    annotation_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    resolved_answer = answer_value(dataset)
    query_params = {
        "query_id": str(query_id),
        "scene_variant": str(dataset.scene_variant),
        "query_id_probabilities": dict(query_id_probabilities),
        "scene_variant_probabilities": {str(dataset.scene_variant): 1.0},
        "series_count": len(dataset.series),
        "x_count": len(dataset.x_labels),
        **dict(dataset.query.trace),
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_scatter_readout",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer": resolved_answer,
                "annotation_bbox_keys": list(annotation_payload["bbox_map"].keys()),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params=query_params,
        ),
        "render_spec": {
            "scene_variant": str(dataset.scene_variant),
            "canvas_width": int(rendered.render_params.canvas_width),
            "canvas_height": int(rendered.render_params.canvas_height),
            "coord_space": "pixel",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "point_radius_px": int(rendered.render_params.point_radius_px),
            "layout_jitter": dict(rendered.render_params.layout_jitter_meta),
            "font_assets": font_assets_payload(chart_font_family=rendered.chart_font_family),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "point_bboxes_px": dict(rendered_scene.point_bboxes),
            "value_label_bboxes_px": dict(rendered_scene.value_label_bboxes),
            "point_annotation_bboxes_px": dict(rendered_scene.point_annotation_bboxes),
            "x_label_bboxes_px": dict(rendered_scene.x_label_bboxes),
            "legend_bboxes_px": dict(rendered_scene.legend_bboxes),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(dataset.scene_variant),
            "question_format": "scatter_series_readout_query",
            "answer": resolved_answer,
            "answer_type": str(dataset.query.answer_type),
            "series": list(_series_records(dataset)),
            "points": list(_point_records(dataset)),
            "x_labels": list(dataset.x_labels),
            "series_count": len(dataset.series),
            "x_count": len(dataset.x_labels),
            "annotation_bbox_map": dict(annotation_payload["bbox_map"]),
            "query_id_probabilities": dict(query_id_probabilities),
            **dict(dataset.query.trace),
        },
        "witness_symbolic": {
            "type": "scatter_readout_witness",
            "annotation_bbox_map": dict(annotation_payload["bbox_map"]),
            "answer": resolved_answer,
            **dict(dataset.query.trace),
        },
        "projected_annotation": dict(annotation_payload["projected"]),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def build_scatter_readout_task_components(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> ScatterReadoutTaskComponents:
    rendered = render_scatter_readout_dataset(
        dataset=dataset,
        params=params,
        instance_seed=int(instance_seed),
    )
    annotation = annotation_payload(dataset=dataset, rendered=rendered)
    prompt_artifacts = build_prompt_artifacts(
        prompt_query_key=str(query_id),
        dynamic_slot_values=dynamic_slots(dataset=dataset),
        instance_seed=int(instance_seed),
    )
    trace_payload = build_trace_payload(
        dataset=dataset,
        rendered=rendered,
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        query_id_probabilities=query_id_probabilities,
        annotation_payload=annotation,
    )
    answer = answer_value(dataset)
    return ScatterReadoutTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type=str(dataset.query.answer_type),
        answer_value=UNANSWERABLE_ANSWER if answer == UNANSWERABLE_ANSWER else answer,
        annotation_type=str(annotation["type"]),
        annotation_value=dict(annotation["bbox_map"]),
        image=rendered.image,
        query_id=str(query_id),
        trace_payload=trace_payload,
    )


