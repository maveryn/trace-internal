"""Annotation helpers for tangent-packing scenes."""

from __future__ import annotations

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts, keyed_bbox_annotation_artifacts

from .state import RenderedTangentPackingScene

ANNOTATION_KEYS: tuple[str, str, str] = ("target_cue", "packing_region", "support_measurement")


def tangent_packing_annotation(rendered: RenderedTangentPackingScene) -> PixelAnnotationArtifacts:
    """Build role-bound bbox-map annotation for rendered tangent-packing witnesses."""

    return keyed_bbox_annotation_artifacts(
        rendered.annotation_bboxes,
        roles=ANNOTATION_KEYS,
        include_point_centers=True,
    )


__all__ = ["ANNOTATION_KEYS", "tangent_packing_annotation"]
