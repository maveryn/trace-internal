"""Annotation helpers for combo-mark chart tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts


def keyed_point_artifacts(points: Mapping[str, Sequence[float]]) -> AnnotationArtifacts:
    value = {
        str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
        for key, point in points.items()
    }
    projected = {
        "type": "keyed_point_map",
        "keyed_point_map": dict(value),
        "pixel_keyed_point_map": dict(value),
    }
    return AnnotationArtifacts(
        annotation_type="keyed_point_map",
        value=dict(value),
        annotation_gt=TypedValue(type="keyed_point_map", value=dict(value)),
        projected_annotation=projected,
    )


__all__ = ["keyed_point_artifacts"]
