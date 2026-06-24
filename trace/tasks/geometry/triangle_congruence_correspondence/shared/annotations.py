"""Annotation helpers for triangle-congruence correspondence scenes."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts, keyed_point_annotation_artifacts

from .state import RenderedTriangleCongruenceScene


def point_map_for_visible_labels(
    rendered: RenderedTriangleCongruenceScene,
    labels: Sequence[str],
) -> PixelAnnotationArtifacts:
    """Build a point-map annotation for selected visible point labels."""

    unique_labels = tuple(dict.fromkeys(str(label) for label in labels))
    return keyed_point_annotation_artifacts(rendered.annotation_keyed_points, roles=unique_labels)


__all__ = ["point_map_for_visible_labels"]
