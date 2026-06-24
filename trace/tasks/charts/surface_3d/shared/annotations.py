"""Annotation artifact helpers for 3D chart scene witnesses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import (
    AnnotationArtifacts,
    bbox_annotation_artifacts,
)


def bbox_for_single_witness(bbox: Sequence[float]) -> AnnotationArtifacts:
    """Build scalar bbox artifacts for one selected 3D chart witness."""

    return bbox_annotation_artifacts(bbox)


def bbox_map_for_roles(values: Mapping[str, Sequence[float]], *, ndigits: int = 3) -> AnnotationArtifacts:
    """Build keyed bbox artifacts when start/end roles must stay bound."""

    rounded = {
        str(role): [round(float(value), int(ndigits)) for value in list(bbox)[:4]]
        for role, bbox in values.items()
    }
    projected = {
        "type": "bbox_map",
        "bbox_map": {role: list(bbox) for role, bbox in rounded.items()},
        "pixel_bbox_map": {role: list(bbox) for role, bbox in rounded.items()},
    }
    return AnnotationArtifacts(
        annotation_type="bbox_map",
        value={role: list(bbox) for role, bbox in rounded.items()},
        annotation_gt=TypedValue(type="bbox_map", value={role: list(bbox) for role, bbox in rounded.items()}),
        projected_annotation=dict(projected),
    )


__all__ = ["bbox_for_single_witness", "bbox_map_for_roles"]
