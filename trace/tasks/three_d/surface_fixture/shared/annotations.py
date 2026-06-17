"""Annotation helpers for rendered surface-fixture elements."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, bbox_set_annotation_artifacts

from .rendering import RenderedSurfaceFixture


def element_centers_for_ids(rendered: RenderedSurfaceFixture, element_ids: Sequence[str]) -> list[list[float]]:
    """Return pixel center points for selected rendered fixture elements."""

    return [
        list(rendered.element_centers_px[str(element_id)])
        for element_id in element_ids
    ]


def element_bboxes_for_ids(rendered: RenderedSurfaceFixture, element_ids: Sequence[str]) -> list[list[float]]:
    """Return pixel boxes for selected rendered fixture elements."""

    return [
        list(rendered.element_bboxes_px[str(element_id)])
        for element_id in element_ids
    ]


def bbox_set_annotation_for_elements(
    rendered: RenderedSurfaceFixture,
    element_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Build unordered bbox-set annotation artifacts for selected fixture elements."""

    return bbox_set_annotation_artifacts(element_bboxes_for_ids(rendered, element_ids))


__all__ = ["bbox_set_annotation_for_elements", "element_bboxes_for_ids", "element_centers_for_ids"]
