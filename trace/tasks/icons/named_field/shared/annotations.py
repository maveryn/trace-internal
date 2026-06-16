"""Annotation projection helpers for named-field icon tasks."""

from __future__ import annotations

from typing import Any, Sequence

from ...shared.annotation import point_set_annotation
from ...shared.icon_scene import sort_bboxes_reading_order

from .metrics import boolean_counted_instance_ids, counterfactual_counted_instance_ids


def _bbox_center(bbox: Sequence[int | float]) -> list[float]:
    if not isinstance(bbox, Sequence) or len(bbox) != 4:
        raise RuntimeError(f"invalid bbox for point annotation: {bbox}")
    return [
        round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
        round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
    ]


def point_set_from_bboxes(bboxes: Sequence[Sequence[int | float]]) -> dict[str, Any]:
    """Return the standard point-set annotation payload from icon bboxes."""

    sorted_bboxes = sort_bboxes_reading_order(tuple(bboxes))
    return dict(point_set_annotation([_bbox_center(bbox) for bbox in sorted_bboxes]))


def boolean_annotation_bboxes(sample: Any, instances: Sequence[Any]) -> list[list[int]]:
    """Return sorted bboxes for icons counted by a Boolean predicate."""

    counted = set(boolean_counted_instance_ids(sample, instances))
    return sort_bboxes_reading_order(tuple(instance.bbox_xyxy for instance in instances if str(instance.instance_id) in counted))


def counterfactual_annotation_bboxes(sample: Any, instances: Sequence[Any]) -> list[list[int]]:
    """Return sorted bboxes for pre-edit icons counted after the hypothetical edit."""

    counted = set(counterfactual_counted_instance_ids(sample))
    return sort_bboxes_reading_order(tuple(instance.bbox_xyxy for instance in instances if str(instance.instance_id) in counted))


__all__ = [
    "boolean_annotation_bboxes",
    "counterfactual_annotation_bboxes",
    "point_set_from_bboxes",
]
