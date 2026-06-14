"""Annotation helpers for rendered surface-fixture elements."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, point_set_annotation_artifacts

from .rendering import RenderedSurfaceFixture


def element_centers_for_ids(rendered: RenderedSurfaceFixture, element_ids: Sequence[str]) -> list[list[float]]:
    """Return pixel center points for selected rendered fixture elements."""

    return [
        list(rendered.element_centers_px[str(element_id)])
        for element_id in element_ids
    ]


def point_annotation_for_elements(rendered: RenderedSurfaceFixture, element_ids: Sequence[str]) -> AnnotationArtifacts:
    """Build unordered point-set annotation artifacts for selected fixture elements."""

    return point_set_annotation_artifacts(element_centers_for_ids(rendered, element_ids))


__all__ = ["element_centers_for_ids", "point_annotation_for_elements"]
