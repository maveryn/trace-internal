"""Annotation helpers for split-triangle angle-chase diagrams."""

from __future__ import annotations

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts, keyed_point_annotation_artifacts

from .state import RenderedSplitTriangleScene


def split_triangle_point_annotation(rendered: RenderedSplitTriangleScene) -> PixelAnnotationArtifacts:
    """Use visible vertex labels as the public point-map annotation keys."""

    return keyed_point_annotation_artifacts(
        rendered.annotation_points,
        roles=tuple(rendered.annotation_points.keys()),
    )


__all__ = ["split_triangle_point_annotation"]
