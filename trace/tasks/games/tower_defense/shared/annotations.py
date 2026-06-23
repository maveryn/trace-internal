"""Annotation projection helpers for tower-defense witnesses."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, bbox_set_annotation_artifacts, point_set_annotation_artifacts

from .state import RenderedTowerDefenseScene


def tower_bbox_set_annotation(
    rendered_scene: RenderedTowerDefenseScene,
    entity_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Return bbox-set annotation artifacts for selected visible towers."""

    bboxes = rendered_scene.render_map["entity_bboxes_px"]
    return bbox_set_annotation_artifacts([bboxes[str(entity_id)] for entity_id in entity_ids])


def path_node_point_set_annotation(
    rendered_scene: RenderedTowerDefenseScene,
    entity_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Return point-set annotation artifacts for selected visible path nodes."""

    points = rendered_scene.render_map["entity_points_px"]
    return point_set_annotation_artifacts([points[str(entity_id)] for entity_id in entity_ids])


__all__ = ["path_node_point_set_annotation", "tower_bbox_set_annotation"]
