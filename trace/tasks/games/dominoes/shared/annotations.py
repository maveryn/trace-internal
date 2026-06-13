"""Annotation projection helpers for dominoes scene tasks."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, bbox_set_annotation_artifacts

from .rendering import RenderedDominoTaskContext


def domino_bbox_set_annotation(
    rendered_context: RenderedDominoTaskContext,
    tile_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Project selected domino tile ids into an unordered bbox-set annotation."""

    render_map = rendered_context.rendered_scene.render_map
    bboxes = [
        list(render_map["domino_bboxes_px"][str(tile_id)])
        for tile_id in tile_ids
    ]
    return bbox_set_annotation_artifacts(bboxes)


__all__ = ["domino_bbox_set_annotation"]
