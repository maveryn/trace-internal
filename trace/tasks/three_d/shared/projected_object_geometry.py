"""Scene-neutral projected-object geometry helpers for three_d renderers."""

from __future__ import annotations

from typing import Any, List, Mapping, Sequence, Tuple

from .camera_projection import project_xy


def object_reference_points(spec: Mapping[str, Any]) -> List[Tuple[float, float, float]]:
    """Return object bounding reference points in world coordinates."""

    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    return [
        (x + dx * width * 0.5, y + dy * depth * 0.5, base_z + z)
        for dx in (-1.0, 1.0)
        for dy in (-1.0, 1.0)
        for z in (0.0, height)
    ] + [(x, y, base_z + height * 0.5)]


def object_screen_bbox(
    spec: Mapping[str, Any],
    camera: Any,
    frame: Any,
    *,
    pad_px: float = 0.0,
) -> List[float]:
    """Project one object spec to a padded screen-space bounding box."""

    points = [project_xy(point, camera, frame) for point in object_reference_points(spec)]
    return [
        round(float(min(point[0] for point in points) - pad_px), 3),
        round(float(min(point[1] for point in points) - pad_px), 3),
        round(float(max(point[0] for point in points) + pad_px), 3),
        round(float(max(point[1] for point in points) + pad_px), 3),
    ]


def bbox_intersection_area(a: Sequence[float], b: Sequence[float]) -> float:
    """Return the pixel-space intersection area for two bboxes."""

    width = max(0.0, min(float(a[2]), float(b[2])) - max(float(a[0]), float(b[0])))
    height = max(0.0, min(float(a[3]), float(b[3])) - max(float(a[1]), float(b[1])))
    return float(width * height)


_object_reference_points = object_reference_points
_object_screen_bbox = object_screen_bbox
_bbox_intersection_area = bbox_intersection_area


__all__ = [
    "_bbox_intersection_area",
    "_object_reference_points",
    "_object_screen_bbox",
    "bbox_intersection_area",
    "object_reference_points",
    "object_screen_bbox",
]
