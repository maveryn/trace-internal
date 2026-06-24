"""Annotation helpers for scatter-point chart scenes."""

from __future__ import annotations

from typing import Any

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, point_set_annotation_artifacts

from .state import Dataset, ScatterPointsRenderResult


def point_set_annotation_for_ids(
    *,
    dataset: Dataset,
    rendered: ScatterPointsRenderResult,
) -> tuple[AnnotationArtifacts, dict[str, Any]]:
    """Project the selected point ids into public point-set annotations."""

    point_ids = [str(point_id) for point_id in dataset.query.annotation_point_ids]
    points = [list(rendered.rendered_scene.point_centers[str(point_id)]) for point_id in point_ids]
    base = point_set_annotation_artifacts(points)
    projected = {
        **dict(base.projected_annotation),
        "point_ids": list(point_ids),
    }
    artifacts = AnnotationArtifacts(
        annotation_type=str(base.annotation_type),
        value=list(base.value),
        annotation_gt=base.annotation_gt,
        projected_annotation=dict(projected),
    )
    witness_symbolic = {
        "type": "scatter_point_set",
        "point_ids": list(point_ids),
    }
    return artifacts, witness_symbolic


__all__ = ["point_set_annotation_for_ids"]
