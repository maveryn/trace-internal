"""Annotation helpers for scatter-readout chart scenes."""

from __future__ import annotations

from typing import Any

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts

from .state import QueryBinding, ScatterReadoutRenderResult


def bbox_map_annotation_for_binding(
    *,
    binding: QueryBinding,
    rendered: ScatterReadoutRenderResult,
) -> tuple[AnnotationArtifacts, dict[str, Any]]:
    """Project a role-bound readout binding into public bbox-map annotations."""

    scene = rendered.rendered_scene
    keyed: dict[str, list[float]] = {}
    target_point = str(binding.target_point_id)
    if target_point:
        keyed["target_point_readout"] = list(scene.point_annotation_bboxes[str(target_point)])

    comparison_point = str(binding.trace.get("comparison_point_id", ""))
    if comparison_point:
        keyed["comparison_point_readout"] = list(scene.point_annotation_bboxes[str(comparison_point)])

    if str(binding.annotation_x_label):
        keyed["x_axis_label"] = list(scene.x_label_bboxes[str(binding.annotation_x_label)])

    projected = {
        "type": "bbox_map",
        "bbox_map": dict(keyed),
        "pixel_bbox_map": dict(keyed),
        "bbox_set": list(keyed.values()),
        "point_id": str(binding.target_point_id),
        "point_ids": [str(point_id) for point_id in binding.annotation_point_ids],
    }
    artifacts = AnnotationArtifacts(
        annotation_type="bbox_map",
        value=dict(keyed),
        annotation_gt=TypedValue(type="bbox_map", value=dict(keyed)),
        projected_annotation=dict(projected),
    )
    witness_symbolic = {
        "type": "scatter_readout_bbox_map",
        "annotation_bbox_map": dict(keyed),
        "point_ids": [str(point_id) for point_id in binding.annotation_point_ids],
        "x_axis_label": str(binding.annotation_x_label),
    }
    return artifacts, witness_symbolic


__all__ = ["bbox_map_annotation_for_binding"]
