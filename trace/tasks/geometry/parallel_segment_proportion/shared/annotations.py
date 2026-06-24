"""Annotation helpers for parallel-segment proportion diagrams."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts

from .state import Segment


def _round_point(point: Sequence[float]) -> list[float]:
    return [round(float(point[0]), 3), round(float(point[1]), 3)]


def segment_set_annotation_artifacts(segments: Sequence[Segment]) -> PixelAnnotationArtifacts:
    """Build an unordered segment-set annotation for proportional segment witnesses."""

    value = [[_round_point(start), _round_point(end)] for start, end in segments]
    projected = {
        "type": "segment_set",
        "segment_set": list(value),
        "pixel_segment_set": list(value),
    }
    return PixelAnnotationArtifacts(
        annotation_type="segment_set",
        value=list(value),
        projected_annotation=projected,
    )


__all__ = ["segment_set_annotation_artifacts"]
