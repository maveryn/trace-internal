"""Shared bbox projection helpers for evidence/anchor payloads."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple


BBox = Tuple[float, float, float, float]


def bbox_center(bbox: BBox) -> Tuple[float, float]:
    """Return center point of one bbox `(x0, y0, x1, y1)`."""
    return ((float(bbox[0]) + float(bbox[2])) / 2.0, (float(bbox[1]) + float(bbox[3])) / 2.0)


def ordered_ids_to_point_path_and_bbox_set(
    *,
    ordered_ids: Sequence[str],
    bbox_map: Mapping[str, BBox],
) -> Tuple[List[List[float]], List[List[float]]]:
    """Project ordered entity ids into point-path and bbox-set payloads."""
    point_path: List[List[float]] = []
    bbox_set: List[List[float]] = []
    for entity_id in ordered_ids:
        bbox = bbox_map[entity_id]
        center = bbox_center(bbox)
        bbox_set.append([float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])])
        point_path.append([float(center[0]), float(center[1])])
    return point_path, bbox_set


def pixel_anchor_map_from_bboxes(bbox_map: Mapping[str, BBox]) -> Dict[str, Dict[str, Any]]:
    """Build deterministic pixel anchor payloads from per-entity bboxes."""
    return {
        entity_id: {
            "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
            "point": [float(center[0]), float(center[1])],
            "coord_space": "pixel",
        }
        for entity_id, bbox in sorted(bbox_map.items())
        for center in [bbox_center(bbox)]
    }


__all__ = [
    "BBox",
    "bbox_center",
    "ordered_ids_to_point_path_and_bbox_set",
    "pixel_anchor_map_from_bboxes",
]
