"""Shared public annotation helpers for icon tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


def _bbox_center(bbox: Sequence[int | float]) -> list[float]:
    return [
        round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
        round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
    ]


def _normalize_point(point: Sequence[int | float], *, context: str) -> list[float]:
    if not isinstance(point, Sequence) or len(point) != 2:
        raise RuntimeError(f"invalid point annotation for {context}: {point}")
    return [round(float(point[0]), 3), round(float(point[1]), 3)]


def matching_scene_cell_bbox_annotation(
    *,
    scene_cells: Sequence[Mapping[str, Any]],
    matching_labels: Sequence[str],
) -> Dict[str, Any]:
    """Return bbox-set annotation for matching labeled Scene cells."""

    requested_labels = [str(label) for label in matching_labels]
    requested_set = set(requested_labels)
    cells_by_label: Dict[str, Mapping[str, Any]] = {
        str(cell.get("label")): cell
        for cell in scene_cells
        if isinstance(cell, Mapping) and str(cell.get("label")) in requested_set
    }
    missing = [label for label in requested_labels if label not in cells_by_label]
    if missing:
        raise RuntimeError(f"missing Scene cell bbox annotation for labels: {missing}")

    matched_cells = list(cells_by_label.values())
    matched_cells.sort(
        key=lambda cell: (
            float((cell.get("cell_bbox_xyxy") or [0, 0, 0, 0])[1]),
            float((cell.get("cell_bbox_xyxy") or [0, 0, 0, 0])[0]),
            str(cell.get("label")),
        )
    )
    bboxes: list[list[int]] = []
    labels_top_left: list[str] = []
    for cell in matched_cells:
        bbox = cell.get("cell_bbox_xyxy")
        if not isinstance(bbox, Sequence) or len(bbox) != 4:
            raise RuntimeError(f"invalid Scene cell bbox for label {cell.get('label')}: {bbox}")
        bboxes.append([int(round(float(value))) for value in bbox])
        labels_top_left.append(str(cell.get("label")))

    return {
        "annotation_type": "bbox_set",
        "annotation_value": [list(bbox) for bbox in bboxes],
        "labels_top_left": list(labels_top_left),
        "witness_symbolic": {
            "matching_cell_labels": list(requested_labels),
            "matching_cell_labels_top_left": list(labels_top_left),
        },
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in bboxes],
            "pixel_bbox_set": [list(bbox) for bbox in bboxes],
            "pixel_point_set": [_bbox_center(bbox) for bbox in bboxes],
        },
    }


def matching_scene_cell_point_annotation(
    *,
    scene_cells: Sequence[Mapping[str, Any]],
    matching_labels: Sequence[str],
) -> Dict[str, Any]:
    """Return point-set annotation for matching labeled Scene cell centers."""

    bbox_artifacts = matching_scene_cell_bbox_annotation(
        scene_cells=scene_cells,
        matching_labels=matching_labels,
    )
    bboxes = bbox_artifacts["annotation_value"]
    points = [_bbox_center(bbox) for bbox in bboxes]
    return {
        "annotation_type": "point_set",
        "annotation_value": [list(point) for point in points],
        "labels_top_left": list(bbox_artifacts["labels_top_left"]),
        "witness_symbolic": dict(bbox_artifacts["witness_symbolic"]),
        "projected_annotation": {
            "type": "point_set",
            "point_set": [list(point) for point in points],
            "pixel_point_set": [list(point) for point in points],
        },
    }


def point_set_annotation(
    points: Sequence[Sequence[int | float]],
) -> Dict[str, Any]:
    """Return typed point-set annotation for homogeneous icon witnesses."""

    normalized_points = [
        _normalize_point(point, context=f"point_set index {index}")
        for index, point in enumerate(points)
    ]
    return {
        "annotation_type": "point_set",
        "annotation_value": [list(point) for point in normalized_points],
        "projected_annotation": {
            "type": "point_set",
            "point_set": [list(point) for point in normalized_points],
            "pixel_point_set": [list(point) for point in normalized_points],
        },
    }


def point_set_from_bboxes(
    bboxes: Sequence[Sequence[int | float]],
) -> Dict[str, Any]:
    """Return point-set annotation using bbox centers as witnesses."""

    normalized_bboxes: list[list[int]] = []
    for index, bbox in enumerate(bboxes):
        if not isinstance(bbox, Sequence) or len(bbox) != 4:
            raise RuntimeError(f"invalid source bbox for point_set annotation at index {index}: {bbox}")
        normalized_bboxes.append([int(round(float(value))) for value in bbox])
    return point_set_annotation(_bbox_center(bbox) for bbox in normalized_bboxes)


def bbox_set_annotation(
    bboxes: Sequence[Sequence[int | float]],
) -> Dict[str, Any]:
    """Return typed bbox-set annotation for homogeneous icon witnesses."""

    normalized_bboxes: list[list[int]] = []
    for index, bbox in enumerate(bboxes):
        if not isinstance(bbox, Sequence) or len(bbox) != 4:
            raise RuntimeError(f"invalid bbox_set annotation at index {index}: {bbox}")
        normalized_bboxes.append([int(round(float(value))) for value in bbox])
    return {
        "annotation_type": "bbox_set",
        "annotation_value": [list(bbox) for bbox in normalized_bboxes],
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in normalized_bboxes],
            "pixel_bbox_set": [list(bbox) for bbox in normalized_bboxes],
            "pixel_point_set": [_bbox_center(bbox) for bbox in normalized_bboxes],
        },
    }


def keyed_point_map_annotation(
    role_points: Mapping[str, Sequence[int | float]],
) -> Dict[str, Any]:
    """Return keyed-point annotation for role-bound icon witnesses."""

    keyed_points = {
        str(role): _normalize_point(point, context=f"role {role!r}")
        for role, point in role_points.items()
    }
    return {
        "annotation_type": "keyed_point_map",
        "annotation_value": {str(key): list(value) for key, value in keyed_points.items()},
        "projected_annotation": {
            "type": "keyed_point_map",
            "keyed_point_map": {str(key): list(value) for key, value in keyed_points.items()},
            "pixel_keyed_point_map": {str(key): list(value) for key, value in keyed_points.items()},
        },
    }


def keyed_point_map_from_bboxes(
    role_bboxes: Mapping[str, Sequence[int | float]],
) -> Dict[str, Any]:
    """Return keyed-point annotation using role bbox centers as witnesses."""

    role_points: dict[str, list[float]] = {}
    for role, bbox in role_bboxes.items():
        if not isinstance(bbox, Sequence) or len(bbox) != 4:
            raise RuntimeError(f"invalid keyed source bbox for role {role!r}: {bbox}")
        role_points[str(role)] = _bbox_center(bbox)
    return keyed_point_map_annotation(role_points)


def keyed_bbox_map_annotation(
    role_bboxes: Mapping[str, Sequence[int | float]],
) -> Dict[str, Any]:
    """Return keyed-bbox annotation for role-bound icon witnesses."""

    keyed_bboxes: dict[str, list[int]] = {}
    for role, bbox in role_bboxes.items():
        if not isinstance(bbox, Sequence) or len(bbox) != 4:
            raise RuntimeError(f"invalid keyed bbox for role {role!r}: {bbox}")
        keyed_bboxes[str(role)] = [int(round(float(value))) for value in bbox]
    return {
        "annotation_type": "keyed_bbox_map",
        "annotation_value": {str(key): list(value) for key, value in keyed_bboxes.items()},
        "projected_annotation": {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": {str(key): list(value) for key, value in keyed_bboxes.items()},
            "pixel_keyed_bbox_map": {str(key): list(value) for key, value in keyed_bboxes.items()},
        },
    }


def keyed_bbox_set_map_annotation(
    role_bbox_sets: Mapping[str, Sequence[Sequence[int | float]]],
) -> Dict[str, Any]:
    """Return keyed bbox-set annotation for role-bound witness groups."""

    keyed_bbox_sets: dict[str, list[list[int]]] = {}
    for role, bboxes in role_bbox_sets.items():
        if not isinstance(bboxes, Sequence):
            raise RuntimeError(f"invalid keyed bbox set for role {role!r}: {bboxes}")
        normalized_bboxes: list[list[int]] = []
        for index, bbox in enumerate(bboxes):
            if not isinstance(bbox, Sequence) or len(bbox) != 4:
                raise RuntimeError(f"invalid keyed bbox for role {role!r} at index {index}: {bbox}")
            normalized_bboxes.append([int(round(float(value))) for value in bbox])
        keyed_bbox_sets[str(role)] = list(normalized_bboxes)
    return {
        "annotation_type": "keyed_bbox_set_map",
        "annotation_value": {str(key): [list(bbox) for bbox in value] for key, value in keyed_bbox_sets.items()},
        "projected_annotation": {
            "type": "keyed_bbox_set_map",
            "keyed_bbox_set_map": {str(key): [list(bbox) for bbox in value] for key, value in keyed_bbox_sets.items()},
            "pixel_keyed_bbox_set_map": {str(key): [list(bbox) for bbox in value] for key, value in keyed_bbox_sets.items()},
        },
    }


__all__ = [
    "bbox_set_annotation",
    "keyed_bbox_map_annotation",
    "keyed_bbox_set_map_annotation",
    "keyed_point_map_annotation",
    "keyed_point_map_from_bboxes",
    "matching_scene_cell_bbox_annotation",
    "matching_scene_cell_point_annotation",
    "point_set_annotation",
    "point_set_from_bboxes",
]
