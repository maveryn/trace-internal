"""Annotation projection helpers for darts scenes."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, point_set_annotation_artifacts

from .rendering import RenderedDartsTaskContext


def dart_center_point_set_annotation(
    rendered_context: RenderedDartsTaskContext,
    dart_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Project selected dart ids to center-point annotation artifacts."""

    centers = rendered_context.rendered_scene.render_map["dart_centers_px"]
    return point_set_annotation_artifacts(
        [
            [
                round(float(centers[str(dart_id)][0]), 3),
                round(float(centers[str(dart_id)][1]), 3),
            ]
            for dart_id in dart_ids
        ]
    )


__all__ = ["dart_center_point_set_annotation"]
