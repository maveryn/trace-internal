"""Annotation projection helpers for marble-chain game tasks."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, point_set_annotation_artifacts

from .state import RenderedMarbleScene


def marble_point_set_annotation(
    *,
    rendered: RenderedMarbleScene,
    entity_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Project selected entity centers into a public point-set annotation."""

    points = [
        list(rendered.render_map["entity_points_px"][str(entity_id)])
        for entity_id in entity_ids
        if str(entity_id) in rendered.render_map["entity_points_px"]
    ]
    return point_set_annotation_artifacts(points)


__all__ = ["marble_point_set_annotation"]
