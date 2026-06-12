"""Annotation helpers for the boxplot chart scene."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts


def keyed_point_artifacts(
    role_to_point: Mapping[str, Sequence[float]],
    role_to_label: Mapping[str, str],
) -> tuple[AnnotationArtifacts, dict[str, Any]]:
    """Build keyed point annotations and symbolic role metadata."""

    keyed_points = {
        str(role): [round(float(point[0]), 3), round(float(point[1]), 3)]
        for role, point in role_to_point.items()
    }
    projected_annotation = {
        "type": "keyed_point_map",
        "keyed_point_map": dict(keyed_points),
        "pixel_keyed_point_map": dict(keyed_points),
    }
    artifacts = AnnotationArtifacts(
        annotation_type="keyed_point_map",
        value=dict(keyed_points),
        annotation_gt=TypedValue(type="keyed_point_map", value=dict(keyed_points)),
        projected_annotation=projected_annotation,
    )
    witness_symbolic = {
        "type": "object_key_map",
        "keys": {str(role): str(label) for role, label in role_to_label.items()},
    }
    return artifacts, witness_symbolic


__all__ = ["keyed_point_artifacts"]
