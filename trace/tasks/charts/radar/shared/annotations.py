"""Annotation helpers for radar chart tasks."""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

from .profile_common import Point, _Dataset, _Rendered


def _point_center_from_bbox(bbox: Sequence[float]) -> Point:
    if len(bbox) != 4:
        raise ValueError(f"expected bbox with 4 values, got {bbox}")
    return [
        round((float(bbox[0]) + float(bbox[2])) / 2.0, 2),
        round((float(bbox[1]) + float(bbox[3])) / 2.0, 2),
    ]


def _point_for_id(rendered: _Rendered, point_id: str) -> Point:
    bbox = rendered.point_bboxes.get(str(point_id))
    if bbox is None:
        raise KeyError(f"missing radar point bbox for {point_id}")
    return _point_center_from_bbox(bbox)


def annotation_for_query(dataset: _Dataset, rendered: _Rendered) -> Tuple[str, List[Any], dict[str, Any]]:
    query_id = str(dataset.query.query_id)
    if query_id in {"highlighted_metric_threshold_panel_count", "matching_condition_panel_count"}:
        panel_labels = [str(value) for value in dataset.query.trace.get("matching_panel_labels", [])]
        boxes = [list(rendered.panel_bboxes[str(label)]) for label in panel_labels]
        return "bbox_set", list(boxes), {
            "type": "bbox_set",
            "bbox_set": list(boxes),
            "annotation_panel_labels": list(panel_labels),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
        }
    if query_id == "threshold_metric_count_for_panel":
        points = [_point_for_id(rendered, str(point_id)) for point_id in dataset.query.annotation_point_ids]
        return "point_set", list(points), {
            "type": "point_set",
            "point_set": list(points),
            "pixel_point_set": list(points),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
            "annotation_metric_labels": list(dataset.query.trace.get("matching_metric_labels", [])),
        }
    if query_id == "profile_advantage_count":
        point_ids = [str(value) for value in dataset.query.annotation_point_ids]
        if len(point_ids) % 2 != 0:
            raise ValueError("profile_advantage_count annotation must contain paired profile points")
        pairs = [
            [_point_for_id(rendered, point_ids[index]), _point_for_id(rendered, point_ids[index + 1])]
            for index in range(0, len(point_ids), 2)
        ]
        return "point_pair_set", list(pairs), {
            "type": "point_pair_set",
            "point_pair_set": list(pairs),
            "pixel_point_pair_set": list(pairs),
            "annotation_point_ids": list(point_ids),
            "advantage_metric_labels": list(dataset.query.trace.get("advantage_metric_labels", [])),
        }
    raise ValueError(f"unsupported radar annotation query_id: {query_id}")


__all__ = ["annotation_for_query"]
