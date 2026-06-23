"""Annotation helpers for paper-fold diagrams."""

from __future__ import annotations

from typing import Mapping, Sequence

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts, keyed_bbox_annotation_artifacts

from .state import BBox


def paper_fold_bbox_annotation(
    bboxes: Mapping[str, BBox],
    *,
    roles: Sequence[str],
) -> PixelAnnotationArtifacts:
    """Build role-bound bbox annotation for the angle cue and given label."""

    return keyed_bbox_annotation_artifacts(bboxes, roles=tuple(str(role) for role in roles))


__all__ = ["paper_fold_bbox_annotation"]
