"""Annotation helpers for incircle-tangent diagrams."""

from __future__ import annotations

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts, keyed_bbox_annotation_artifacts

from .state import RenderedIncircleScene


def incircle_label_bbox_annotation(rendered: RenderedIncircleScene) -> PixelAnnotationArtifacts:
    """Build keyed bbox annotation for task-selected visible labels."""

    return keyed_bbox_annotation_artifacts(
        rendered.label_bboxes,
        roles=rendered.annotation_roles,
    )


__all__ = ["incircle_label_bbox_annotation"]
