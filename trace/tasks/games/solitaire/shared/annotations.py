"""Annotation projection helpers for solitaire tableau scenes."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, bbox_set_annotation_artifacts

from .state import RenderedSolitaireScene, SolitaireSample


def move_legality_bbox_map(sample: SolitaireSample, rendered: RenderedSolitaireScene) -> AnnotationArtifacts:
    """Bind source-card and target roles to their rendered bounding boxes."""

    entity_bboxes = rendered.render_map["entity_bboxes_px"]
    value = {
        "source_card": list(entity_bboxes[str(sample.metadata["legal_source_id"])]),
        "target": list(entity_bboxes[str(sample.metadata["legal_target_id"])]),
    }
    projected = {
        "type": "bbox_map",
        "bbox_map": dict(value),
        "pixel_bbox_map": dict(value),
    }
    return AnnotationArtifacts(
        annotation_type="bbox_map",
        value=dict(value),
        annotation_gt=TypedValue(type="bbox_map", value=dict(value)),
        projected_annotation=projected,
    )


def entity_bbox_set(sample: SolitaireSample, rendered: RenderedSolitaireScene) -> AnnotationArtifacts:
    """Bind all sampled annotation entity ids to an unordered bbox set."""

    entity_bboxes: Mapping[str, Any] = rendered.render_map["entity_bboxes_px"]
    bboxes = [
        list(entity_bboxes[str(entity_id)])
        for entity_id in sample.annotation_entity_ids
        if str(entity_id) in entity_bboxes
    ]
    return bbox_set_annotation_artifacts(bboxes)
