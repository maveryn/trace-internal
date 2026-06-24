"""Annotation helpers for survey-traverse scenes."""

from __future__ import annotations

from trace.tasks.geometry.shared.annotation_values import (
    PixelAnnotationArtifacts,
    keyed_bbox_annotation_artifacts,
    keyed_point_annotation_artifacts,
)

from .state import RenderedAreaScene, RenderedPointScene


def point_scene_annotation(rendered: RenderedPointScene) -> PixelAnnotationArtifacts:
    """Build point-map annotation artifacts from the rendered point witnesses."""

    return keyed_point_annotation_artifacts(
        rendered.annotation_points,
        roles=rendered.annotation_roles,
    )


def area_scene_annotation(rendered: RenderedAreaScene) -> PixelAnnotationArtifacts:
    """Build bbox-map annotation artifacts from the rendered area witnesses."""

    return keyed_bbox_annotation_artifacts(
        rendered.annotation_bboxes,
        roles=rendered.annotation_roles,
        include_point_centers=False,
    )


__all__ = ["area_scene_annotation", "point_scene_annotation"]
