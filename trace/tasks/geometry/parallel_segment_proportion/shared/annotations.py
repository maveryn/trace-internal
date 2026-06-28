"""Annotation helpers for parallel-segment proportion diagrams."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts

from .state import Point


def _round_point(point: Sequence[float]) -> list[float]:
    return [round(float(point[0]), 3), round(float(point[1]), 3)]


def point_set_annotation_artifacts(points: Sequence[Point]) -> PixelAnnotationArtifacts:
    """Build an unordered point-set annotation for visible construction witnesses."""

    value = [_round_point(point) for point in points]
    projected = {
        "type": "point_set",
        "point_set": list(value),
        "pixel_point_set": list(value),
    }
    return PixelAnnotationArtifacts(
        annotation_type="point_set",
        value=list(value),
        projected_annotation=projected,
    )


__all__ = ["point_set_annotation_artifacts"]
