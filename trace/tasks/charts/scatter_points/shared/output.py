
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from PIL import Image

from trace.tasks.charts.scatter_points.shared.points_query import (
    _Dataset,
    _REASONING_LOAD_BY_QUERY,
    _SCENE_LOAD_BY_VARIANT,
    _category_records,
    _point_records,
)
from trace.tasks.charts.scatter_points.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.scatter_points.shared.runtime import (
    ScatterPointsRenderResult,
    font_assets_payload,
    render_scatter_points_dataset,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


@dataclass(frozen=True)
class ScatterPointsTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: int | str
    annotation_type: str
    annotation_value: List[List[float]]
    image: Image.Image
    query_id: str
    trace_payload: Dict[str, Any]


def annotation_payload(*, dataset: _Dataset, rendered: ScatterPointsRenderResult) -> Dict[str, Any]:
    annotation_point_ids = [str(point_id) for point_id in dataset.query.annotation_point_ids]
    point_set = [list(rendered.rendered_scene.point_centers[str(point_id)]) for point_id in annotation_point_ids]
    return {
        "type": "point_set",
        "point_set": list(point_set),
        "point_ids": list(annotation_point_ids),
        "projected": {
            "type": "point_set",
            "point_set": list(point_set),
            "pixel_point_set": list(point_set),
            "point_ids": list(annotation_point_ids),
        },
    }


def answer_value(dataset: _Dataset) -> int | str:
    if str(dataset.query.answer_type) == "integer":
        return int(dataset.query.answer)
    return str(dataset.query.answer)




def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: ScatterPointsRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    annotation_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    annotation_point_ids = [str(point_id) for point_id in annotation_payload["point_ids"]]
    resolved_answer = answer_value(dataset)
    total_points = len(dataset.points)
    query_params = {
        "query_id": str(query_id),
        "scene_variant": str(dataset.scene_variant),
        "query_id_probabilities": dict(query_id_probabilities),
        "scene_variant_probabilities": {str(dataset.scene_variant): 1.0},
        "point_count": int(total_points),
        "category_count": len(dataset.categories),
        **dict(dataset.query.trace),
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_scatter_points",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer": resolved_answer,
                "annotation_point_ids": list(annotation_point_ids),
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
            "panel_bbox_px": list(rendered_scene.panel_bbox_px),
            "point_radius_px": int(rendered.render_params.point_radius_px),
            "layout_jitter": dict(rendered.render_params.layout_jitter_meta),
            "font_assets": font_assets_payload(chart_font_family=rendered.chart_font_family),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "panel_bbox_px": list(rendered_scene.panel_bbox_px),
            "point_bboxes_px": dict(rendered_scene.point_bboxes),
            "point_centers_px": dict(rendered_scene.point_centers),
            "legend_bboxes_px": dict(rendered_scene.legend_bboxes),
            "threshold_guide_bbox_px": list(rendered_scene.threshold_guide_bbox_px),
            "title_bbox_px": list(rendered_scene.title_bbox_px),
            "x_axis_label_bbox_px": list(rendered_scene.x_axis_label_bbox_px),
            "y_axis_label_bbox_px": list(rendered_scene.y_axis_label_bbox_px),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(dataset.scene_variant),
            "question_format": "scatter_points_query",
            "answer": resolved_answer,
            "answer_type": str(dataset.query.answer_type),
            "points": list(_point_records(dataset.points)),
            "categories": list(_category_records(dataset.categories)),
            "point_count": int(total_points),
            "category_count": len(dataset.categories),
            "annotation_point_ids": list(annotation_point_ids),
            "title_text": str(rendered_scene.title_text),
            "query_id_probabilities": dict(query_id_probabilities),
            **dict(dataset.query.trace),
        },
        "witness_symbolic": {
            "type": "scatter_points_witness",
            "point_ids": list(annotation_point_ids),
            "answer": resolved_answer,
            **dict(dataset.query.trace),
        },
        "projected_annotation": dict(annotation_payload["projected"]),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def build_scatter_points_task_components(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> ScatterPointsTaskComponents:
    rendered = render_scatter_points_dataset(
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
    return ScatterPointsTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type=str(dataset.query.answer_type),
        answer_value=answer_value(dataset),
        annotation_type=str(annotation["type"]),
        annotation_value=list(annotation["point_set"]),
        image=rendered.image,
        query_id=str(query_id),
        trace_payload=trace_payload,
    )


