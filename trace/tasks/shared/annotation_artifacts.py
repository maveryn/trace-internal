"""Shared public annotation artifact builders for task generators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from ...core.types import TypedValue


@dataclass(frozen=True)
class AnnotationArtifacts:
    """Normalized annotation value plus matching public projection payload."""

    annotation_type: str
    value: Any
    annotation_gt: TypedValue
    projected_annotation: dict[str, Any]


def _round_point(point: Sequence[float], *, ndigits: int = 3) -> list[float]:
    return [
        round(float(point[0]), int(ndigits)),
        round(float(point[1]), int(ndigits)),
    ]


def _round_bbox(bbox: Sequence[float], *, ndigits: int = 3) -> list[float]:
    return [round(float(value), int(ndigits)) for value in bbox[:4]]


def bbox_set_annotation_artifacts(
    bboxes: Sequence[Sequence[float]],
    *,
    ndigits: int = 3,
) -> AnnotationArtifacts:
    """Build public annotation artifacts for an unordered bbox set."""

    value = [_round_bbox(bbox, ndigits=int(ndigits)) for bbox in bboxes]
    projected_annotation = {
        "type": "bbox_set",
        "bbox_set": [list(bbox) for bbox in value],
        "pixel_bbox_set": [list(bbox) for bbox in value],
    }
    return AnnotationArtifacts(
        annotation_type="bbox_set",
        value=[list(bbox) for bbox in value],
        annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in value]),
        projected_annotation=projected_annotation,
    )


def point_set_annotation_artifacts(
    points: Sequence[Sequence[float]],
    *,
    ndigits: int = 3,
) -> AnnotationArtifacts:
    """Build public annotation artifacts for an unordered point set."""

    value = [_round_point(point, ndigits=int(ndigits)) for point in points]
    projected_annotation = {
        "type": "point_set",
        "point_set": [list(point) for point in value],
        "pixel_point_set": [list(point) for point in value],
    }
    return AnnotationArtifacts(
        annotation_type="point_set",
        value=[list(point) for point in value],
        annotation_gt=TypedValue(type="point_set", value=[list(point) for point in value]),
        projected_annotation=projected_annotation,
    )


def point_pair_set_annotation_artifacts(
    point_pairs: Sequence[Sequence[Sequence[float]]],
    *,
    ndigits: int = 3,
) -> AnnotationArtifacts:
    """Build public annotation artifacts for unordered point-pair witnesses."""

    value = [
        [_round_point(point, ndigits=int(ndigits)) for point in pair[:2]]
        for pair in point_pairs
    ]
    projected_annotation = {
        "type": "point_pair_set",
        "point_pair_set": [[list(point) for point in pair] for pair in value],
        "pixel_point_pair_set": [[list(point) for point in pair] for pair in value],
    }
    return AnnotationArtifacts(
        annotation_type="point_pair_set",
        value=[[list(point) for point in pair] for pair in value],
        annotation_gt=TypedValue(
            type="point_pair_set",
            value=[[list(point) for point in pair] for pair in value],
        ),
        projected_annotation=projected_annotation,
    )


__all__ = [
    "AnnotationArtifacts",
    "bbox_set_annotation_artifacts",
    "point_pair_set_annotation_artifacts",
    "point_set_annotation_artifacts",
]
