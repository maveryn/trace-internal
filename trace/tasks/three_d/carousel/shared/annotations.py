"""Annotation helpers for rendered conveyor objects."""

from __future__ import annotations

from typing import Mapping, Sequence

from trace.tasks.shared.annotation_artifacts import (
    AnnotationArtifacts,
    bbox_set_annotation_artifacts,
    bbox_set_map_annotation_artifacts,
)

from .rendering import RenderedConveyor


def object_bboxes_for_ids(
    rendered: RenderedConveyor,
    object_ids: Sequence[str],
) -> list[list[float]]:
    """Return pixel boxes for selected conveyor objects."""

    return [list(rendered.object_bboxes_px[str(object_id)]) for object_id in object_ids]


def bbox_set_annotation_for_objects(
    rendered: RenderedConveyor,
    object_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Build unordered bbox-set annotation artifacts for selected objects."""

    return bbox_set_annotation_artifacts(object_bboxes_for_ids(rendered, object_ids))


def bbox_set_map_annotation_for_object_groups(
    rendered: RenderedConveyor,
    keyed_object_ids: Mapping[str, Sequence[str]],
) -> AnnotationArtifacts:
    """Build role-keyed bbox-set annotation artifacts for selected object groups."""

    keyed_bboxes = {
        str(key): object_bboxes_for_ids(rendered, object_ids)
        for key, object_ids in dict(keyed_object_ids).items()
    }
    return bbox_set_map_annotation_artifacts(keyed_bboxes)


__all__ = [
    "bbox_set_annotation_for_objects",
    "bbox_set_map_annotation_for_object_groups",
    "object_bboxes_for_ids",
]
