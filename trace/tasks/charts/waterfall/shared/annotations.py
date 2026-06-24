"""Annotation artifact builders for waterfall chart tasks."""

from __future__ import annotations

from typing import Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts


def _round_bbox(bbox: Sequence[float], *, ndigits: int = 3) -> list[float]:
    return [round(float(value), int(ndigits)) for value in list(bbox)[:4]]


def bbox_map_artifacts(
    values: Mapping[str, Sequence[float]],
    *,
    ndigits: int = 3,
) -> AnnotationArtifacts:
    """Build public bbox-map annotation artifacts."""

    rounded = {str(key): _round_bbox(value, ndigits=int(ndigits)) for key, value in values.items()}
    projected = {
        "type": "bbox_map",
        "bbox_map": {key: list(value) for key, value in rounded.items()},
        "pixel_bbox_map": {key: list(value) for key, value in rounded.items()},
        "bbox_set": [list(value) for value in rounded.values()],
    }
    return AnnotationArtifacts(
        annotation_type="bbox_map",
        value={key: list(value) for key, value in rounded.items()},
        annotation_gt=TypedValue(
            type="bbox_map",
            value={key: list(value) for key, value in rounded.items()},
        ),
        projected_annotation=dict(projected),
    )


def bbox_set_map_artifacts(
    values: Mapping[str, Sequence[Sequence[float]]],
    *,
    ndigits: int = 3,
) -> AnnotationArtifacts:
    """Build keyed bbox-set artifacts while preserving each semantic role."""

    rounded = {
        str(key): [_round_bbox(bbox, ndigits=int(ndigits)) for bbox in boxes]
        for key, boxes in values.items()
    }
    projected = {
        "type": "bbox_set_map",
        "bbox_set_map": {
            key: [list(bbox) for bbox in boxes]
            for key, boxes in rounded.items()
        },
        "pixel_bbox_set_map": {
            key: [list(bbox) for bbox in boxes]
            for key, boxes in rounded.items()
        },
        "bbox_set": [
            list(bbox)
            for boxes in rounded.values()
            for bbox in boxes
        ],
    }
    return AnnotationArtifacts(
        annotation_type="bbox_set_map",
        value={
            key: [list(bbox) for bbox in boxes]
            for key, boxes in rounded.items()
        },
        annotation_gt=TypedValue(
            type="bbox_set_map",
            value={
                key: [list(bbox) for bbox in boxes]
                for key, boxes in rounded.items()
            },
        ),
        projected_annotation=dict(projected),
    )


__all__ = ["bbox_map_artifacts", "bbox_set_map_artifacts"]
