
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from PIL import Image

from trace.tasks.charts.scatter_cluster.shared.cluster_common import (
    _Dataset,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
)
from trace.tasks.charts.scatter_cluster.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.scatter_cluster.shared.runtime import (
    ScatterClusterInputs,
    ScatterClusterRenderResult,
    font_assets_payload,
    render_scatter_cluster_dataset,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


@dataclass(frozen=True)
class ScatterClusterTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: str
    annotation_type: str
    annotation_value: Dict[str, List[float]]
    image: Image.Image
    query_id: str
    trace_payload: Dict[str, Any]


def annotation_payload(*, dataset: _Dataset, rendered: ScatterClusterRenderResult) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    annotation_cluster_labels = [str(label) for label in dataset.query.annotation_cluster_labels]
    annotation_point_ids = [
        str(point.point_id)
        for cluster in dataset.clusters
        if str(cluster.cluster_label) in set(annotation_cluster_labels)
        for point in cluster.points
    ]
    if str(dataset.query.query_id) == "centroid_option_selection_label":
        target_cluster_label = str(dataset.query.trace["target_cluster_label"])
        annotation_bbox_map: Dict[str, List[float]] = {
            "target_cluster": list(rendered_scene.cluster_bboxes[str(target_cluster_label)]),
            "selected_option_marker": list(rendered_scene.option_bboxes[str(dataset.query.answer_label)]),
        }
    elif str(dataset.query.query_id) == "cluster_separation_extremum_label":
        reference_label = str(dataset.query.trace["reference_cluster_label"])
        annotation_bbox_map = {
            "reference_cluster": list(rendered_scene.cluster_bboxes[str(reference_label)]),
            "answer_cluster": list(rendered_scene.cluster_bboxes[str(dataset.query.answer_label)]),
        }
    else:
        annotation_bbox_map = {
            "answer_cluster": list(rendered_scene.cluster_bboxes[str(dataset.query.answer_label)])
        }
    return {
        "type": "keyed_bbox_map",
        "keyed_bbox_map": dict(annotation_bbox_map),
        "point_ids": list(annotation_point_ids),
        "cluster_labels": list(annotation_cluster_labels),
        "projected": {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_bbox_map),
            "pixel_keyed_bbox_map": dict(annotation_bbox_map),
            "point_ids": list(annotation_point_ids),
            "cluster_labels": list(annotation_cluster_labels),
            "cluster_bboxes": {
                str(label): list(rendered_scene.cluster_bboxes[str(label)])
                for label in annotation_cluster_labels
            },
            "option_bboxes": dict(rendered_scene.option_bboxes),
            "option_centers_px": dict(rendered_scene.option_centers_px),
            "cluster_envelope_bboxes": dict(rendered_scene.cluster_envelope_bboxes),
        },
    }




def _values_by_cluster(dataset: _Dataset) -> Dict[str, Any]:
    return {
        str(cluster.cluster_label): {
            "center": [round(float(cluster.center_x), 3), round(float(cluster.center_y), 3)],
            "slope": round(float(cluster.slope), 4),
            "spread_x": round(float(cluster.spread_x), 3),
            "spread_y": round(float(cluster.spread_y), 3),
            "area_envelope": (
                {
                    "center": [
                        round(float(cluster.area_envelope.center_x), 3),
                        round(float(cluster.area_envelope.center_y), 3),
                    ],
                    "radius_x": round(float(cluster.area_envelope.radius_x), 3),
                    "radius_y": round(float(cluster.area_envelope.radius_y), 3),
                    "angle_degrees": round(float(cluster.area_envelope.angle_degrees), 3),
                    "area_value": round(float(cluster.area_envelope.area_value), 4),
                }
                if cluster.area_envelope is not None
                else None
            ),
            "points": [
                {
                    "point_id": str(point.point_id),
                    "x_value": round(float(point.x_value), 3),
                    "y_value": round(float(point.y_value), 3),
                }
                for point in cluster.points
            ],
        }
        for cluster in dataset.clusters
    }


def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: ScatterClusterRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    inputs: ScatterClusterInputs,
    annotation_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    annotation_point_ids = [str(point_id) for point_id in annotation_payload["point_ids"]]
    annotation_cluster_labels = [str(label) for label in annotation_payload["cluster_labels"]]
    total_points = int(sum(len(cluster.points) for cluster in dataset.clusters))
    query_params = {
        "query_id": str(query_id),
        "scene_variant": str(dataset.scene_variant),
        "query_id_probabilities": dict(query_id_probabilities),
        "scene_variant_probabilities": {str(dataset.scene_variant): 1.0},
        "cluster_count": int(inputs.cluster_count),
        "points_per_cluster": int(inputs.points_per_cluster),
        **dict(dataset.query.trace),
    }
    option_labels = [str(marker.option_label) for marker in dataset.option_markers]
    return {
        "scene_ir": {
            "scene_kind": "chart_scatter_cluster",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer": str(dataset.query.answer_label),
                "annotation_point_ids": list(annotation_point_ids),
                "annotation_cluster_labels": list(annotation_cluster_labels),
                "option_labels": list(option_labels),
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
            "cluster_bboxes_px": dict(rendered_scene.cluster_bboxes),
            "cluster_envelope_bboxes_px": dict(rendered_scene.cluster_envelope_bboxes),
            "cluster_label_bboxes_px": dict(rendered_scene.cluster_label_bboxes),
            "legend_bboxes_px": dict(rendered_scene.legend_bboxes),
            "option_bboxes_px": dict(rendered_scene.option_bboxes),
            "option_centers_px": dict(rendered_scene.option_centers_px),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(dataset.scene_variant),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": {str(dataset.scene_variant): 1.0},
            "question_format": "scatter_cluster_query",
            "answer": str(dataset.query.answer_label),
            "answer_type": str(dataset.query.answer_type),
            "cluster_labels": list(inputs.labels),
            "cluster_count": int(inputs.cluster_count),
            "points_per_cluster": int(inputs.points_per_cluster),
            "total_point_count": int(total_points),
            "option_labels": list(option_labels),
            "values_by_cluster": _values_by_cluster(dataset),
            "annotation_point_ids": list(annotation_point_ids),
            "annotation_cluster_labels": list(annotation_cluster_labels),
            **dict(dataset.query.trace),
        },
        "witness_symbolic": {
            "type": "scatter_cluster_witness",
            "point_ids": list(annotation_point_ids),
            "cluster_labels": list(annotation_cluster_labels),
            "answer": str(dataset.query.answer_label),
        },
        "projected_annotation": dict(annotation_payload["projected"]),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def build_scatter_cluster_task_components(
    *,
    dataset: _Dataset,
    inputs: ScatterClusterInputs,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> ScatterClusterTaskComponents:
    rendered = render_scatter_cluster_dataset(
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
        inputs=inputs,
        annotation_payload=annotation,
    )
    return ScatterClusterTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type=str(dataset.query.answer_type),
        answer_value=str(dataset.query.answer_label),
        annotation_type=str(annotation["type"]),
        annotation_value=dict(annotation["keyed_bbox_map"]),
        image=rendered.image,
        query_id=str(query_id),
        trace_payload=trace_payload,
    )


