"""Annotation helpers for trapezoid-extension scenes."""

from __future__ import annotations

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts, keyed_bbox_annotation_artifacts

from .state import RenderedTrapezoidExtensionScene

ANNOTATION_KEYS: tuple[str, str, str, str] = (
    "target_cue",
    "original_trapezoid",
    "dashed_parallelogram_completion",
    "supporting_visible_labels",
)


def trapezoid_extension_annotation(rendered: RenderedTrapezoidExtensionScene) -> PixelAnnotationArtifacts:
    """Build role-bound bbox-map annotation for rendered trapezoid witnesses."""

    return keyed_bbox_annotation_artifacts(
        rendered.annotation_bboxes,
        roles=ANNOTATION_KEYS,
        include_point_centers=True,
    )


__all__ = ["ANNOTATION_KEYS", "trapezoid_extension_annotation"]
