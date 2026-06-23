"""Annotation helpers for scatter-cluster chart scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from trace.core.types import TypedValue

from .state import BBox, ScatterClusterDataset, ScatterClusterRenderResult


@dataclass(frozen=True)
class ScatterClusterAnnotationBundle:
    annotation_type: str
    annotation_gt: TypedValue
    projected_annotation: dict[str, Any]
    annotation_refs: list[str]
    annotation_cluster_labels: list[str]
    annotation_point_ids: list[str]


def _point_ids_for_clusters(dataset: ScatterClusterDataset, cluster_labels: list[str]) -> list[str]:
    selected = set(str(label) for label in cluster_labels)
    return [
        str(point.point_id)
        for cluster in dataset.clusters
        if str(cluster.cluster_label) in selected
        for point in cluster.points
    ]


def cluster_bbox_annotation(
    *,
    dataset: ScatterClusterDataset,
    rendered: ScatterClusterRenderResult,
    cluster_label: str,
) -> ScatterClusterAnnotationBundle:
    rendered_scene = rendered.rendered_scene
    label = str(cluster_label)
    bbox = list(rendered_scene.cluster_bboxes[label])
    point_ids = _point_ids_for_clusters(dataset, [label])
    return ScatterClusterAnnotationBundle(
        annotation_type="bbox",
        annotation_gt=TypedValue(type="bbox", value=list(bbox)),
        projected_annotation={
            "type": "bbox",
            "bbox": list(bbox),
            "pixel_bbox": list(bbox),
            "point_ids": list(point_ids),
            "cluster_labels": [label],
            "cluster_bboxes": {label: list(bbox)},
            "cluster_envelope_bboxes": dict(rendered_scene.cluster_envelope_bboxes),
        },
        annotation_refs=[label],
        annotation_cluster_labels=[label],
        annotation_point_ids=list(point_ids),
    )


def cluster_pair_bbox_map_annotation(
    *,
    dataset: ScatterClusterDataset,
    rendered: ScatterClusterRenderResult,
    reference_cluster_label: str,
    answer_cluster_label: str,
) -> ScatterClusterAnnotationBundle:
    rendered_scene = rendered.rendered_scene
    ref_label = str(reference_cluster_label)
    answer_label = str(answer_cluster_label)
    bbox_map: dict[str, BBox] = {
        "reference_cluster": list(rendered_scene.cluster_bboxes[ref_label]),
        "answer_cluster": list(rendered_scene.cluster_bboxes[answer_label]),
    }
    cluster_labels = [ref_label, answer_label]
    point_ids = _point_ids_for_clusters(dataset, cluster_labels)
    return ScatterClusterAnnotationBundle(
        annotation_type="bbox_map",
        annotation_gt=TypedValue(type="bbox_map", value=dict(bbox_map)),
        projected_annotation={
            "type": "bbox_map",
            "bbox_map": dict(bbox_map),
            "pixel_bbox_map": dict(bbox_map),
            "point_ids": list(point_ids),
            "cluster_labels": list(cluster_labels),
            "cluster_bboxes": {label: list(rendered_scene.cluster_bboxes[label]) for label in cluster_labels},
            "cluster_envelope_bboxes": dict(rendered_scene.cluster_envelope_bboxes),
        },
        annotation_refs=list(bbox_map),
        annotation_cluster_labels=list(cluster_labels),
        annotation_point_ids=list(point_ids),
    )


def centroid_option_bbox_map_annotation(
    *,
    dataset: ScatterClusterDataset,
    rendered: ScatterClusterRenderResult,
    target_cluster_label: str,
    selected_option_label: str,
) -> ScatterClusterAnnotationBundle:
    rendered_scene = rendered.rendered_scene
    cluster_label = str(target_cluster_label)
    option_label = str(selected_option_label)
    bbox_map: dict[str, BBox] = {
        "target_cluster": list(rendered_scene.cluster_bboxes[cluster_label]),
        "selected_option_marker": list(rendered_scene.option_bboxes[option_label]),
    }
    point_ids = _point_ids_for_clusters(dataset, [cluster_label])
    return ScatterClusterAnnotationBundle(
        annotation_type="bbox_map",
        annotation_gt=TypedValue(type="bbox_map", value=dict(bbox_map)),
        projected_annotation={
            "type": "bbox_map",
            "bbox_map": dict(bbox_map),
            "pixel_bbox_map": dict(bbox_map),
            "point_ids": list(point_ids),
            "cluster_labels": [cluster_label],
            "option_labels": [option_label],
            "cluster_bboxes": {cluster_label: list(rendered_scene.cluster_bboxes[cluster_label])},
            "option_bboxes": dict(rendered_scene.option_bboxes),
            "option_centers_px": dict(rendered_scene.option_centers_px),
            "cluster_envelope_bboxes": dict(rendered_scene.cluster_envelope_bboxes),
        },
        annotation_refs=list(bbox_map),
        annotation_cluster_labels=[cluster_label],
        annotation_point_ids=list(point_ids),
    )
