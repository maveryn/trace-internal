"""Annotation projection helpers for Pac-Man scenes."""

from __future__ import annotations

from typing import Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import (
    AnnotationArtifacts,
    point_annotation_artifacts,
    point_set_annotation_artifacts,
)


def entity_points_for_ids(rendered_scene, entity_ids: Sequence[str]) -> list[list[float]]:
    """Return rendered entity center points for the requested ids."""

    entity_points = rendered_scene.render_map["entity_points_px"]
    return [list(entity_points[str(entity_id)]) for entity_id in entity_ids]


def point_set_for_entity_ids(rendered_scene, entity_ids: Sequence[str]) -> AnnotationArtifacts:
    """Project entity ids to an unordered point-set annotation."""

    return point_set_annotation_artifacts(entity_points_for_ids(rendered_scene, entity_ids))


def point_for_entity_id(rendered_scene, entity_id: str) -> AnnotationArtifacts:
    """Project one entity id to a scalar point annotation."""

    point = rendered_scene.render_map["entity_points_px"][str(entity_id)]
    return point_annotation_artifacts(point)


def keyed_point_set_for_entity_ids(
    rendered_scene,
    keyed_entity_ids: Mapping[str, Sequence[str]],
) -> AnnotationArtifacts:
    """Project keyed semantic witness roles to keyed point sets."""

    keyed_points = {
        str(key): entity_points_for_ids(rendered_scene, tuple(str(entity_id) for entity_id in entity_ids))
        for key, entity_ids in keyed_entity_ids.items()
    }
    projected = {
        "type": "keyed_point_set_map",
        "keyed_point_set_map": {key: [list(point) for point in points] for key, points in keyed_points.items()},
        "pixel_keyed_point_set_map": {key: [list(point) for point in points] for key, points in keyed_points.items()},
    }
    value = {key: [list(point) for point in points] for key, points in keyed_points.items()}
    return AnnotationArtifacts(
        annotation_type="keyed_point_set_map",
        value=value,
        annotation_gt=TypedValue(type="keyed_point_set_map", value=value),
        projected_annotation=projected,
    )


__all__ = [
    "entity_points_for_ids",
    "keyed_point_set_for_entity_ids",
    "point_for_entity_id",
    "point_set_for_entity_ids",
]
