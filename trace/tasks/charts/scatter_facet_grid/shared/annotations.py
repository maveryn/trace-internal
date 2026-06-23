"""Annotation helpers for scatter-facet-grid chart scenes."""

from __future__ import annotations

from typing import Any

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, bbox_annotation_artifacts

from .state import Dataset, ScatterFacetRenderResult


def density_region_bbox_annotation(
    *,
    dataset: Dataset,
    rendered: ScatterFacetRenderResult,
) -> tuple[AnnotationArtifacts, dict[str, Any]]:
    """Build the scalar bbox annotation for the answer panel's dense region."""

    answer_label = str(dataset.query.answer_label)
    bbox = list(rendered.rendered_scene.density_region_bboxes[answer_label])
    base = bbox_annotation_artifacts(bbox)
    projected = {
        **dict(base.projected_annotation),
        "answer_panel_label": answer_label,
        "annotation_point_ids": list(dataset.query.annotation_point_ids),
    }
    artifacts = AnnotationArtifacts(
        annotation_type=str(base.annotation_type),
        value=list(base.value),
        annotation_gt=base.annotation_gt,
        projected_annotation=dict(projected),
    )
    witness_symbolic = {
        "type": "scatter_facet_grid_density_region",
        "answer_panel_label": answer_label,
        "target_region": str(dataset.query.target_region),
        "annotation_point_ids": list(dataset.query.annotation_point_ids),
    }
    return artifacts, witness_symbolic


__all__ = ["density_region_bbox_annotation"]
