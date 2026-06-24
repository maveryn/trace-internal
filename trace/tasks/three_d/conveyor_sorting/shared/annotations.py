"""Annotation helpers for rendered conveyor sorting objects."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, bbox_set_annotation_artifacts

from .rendering import RenderedConveyorSorting


def object_bboxes_for_ids(
    rendered: RenderedConveyorSorting,
    object_ids: Sequence[str],
) -> list[list[float]]:
    """Return pixel boxes for selected conveyor objects."""

    return [list(rendered.object_bboxes_px[str(object_id)]) for object_id in object_ids]


def bbox_set_annotation_for_objects(
    rendered: RenderedConveyorSorting,
    object_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Build unordered bbox-set annotation artifacts for selected objects."""

    return bbox_set_annotation_artifacts(object_bboxes_for_ids(rendered, object_ids))


__all__ = ["bbox_set_annotation_for_objects", "object_bboxes_for_ids"]
