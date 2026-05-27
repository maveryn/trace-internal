"""Shared public evidence helpers for icon tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


def _bbox_center(bbox: Sequence[int | float]) -> list[float]:
    return [
        round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
        round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
    ]


def matching_scene_cell_bbox_evidence(
    *,
    scene_cells: Sequence[Mapping[str, Any]],
    matching_labels: Sequence[str],
) -> Dict[str, Any]:
    """Return bbox-set evidence for matching labeled Scene cells."""

    requested_labels = [str(label) for label in matching_labels]
    requested_set = set(requested_labels)
    cells_by_label: Dict[str, Mapping[str, Any]] = {
        str(cell.get("label")): cell
        for cell in scene_cells
        if isinstance(cell, Mapping) and str(cell.get("label")) in requested_set
    }
    missing = [label for label in requested_labels if label not in cells_by_label]
    if missing:
        raise RuntimeError(f"missing Scene cell bbox evidence for labels: {missing}")

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
        "evidence_type": "bbox_set",
        "evidence_value": [list(bbox) for bbox in bboxes],
        "labels_top_left": list(labels_top_left),
        "witness_symbolic": {
            "matching_cell_labels": list(requested_labels),
            "matching_cell_labels_top_left": list(labels_top_left),
        },
        "projected_evidence": {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in bboxes],
            "pixel_bbox_set": [list(bbox) for bbox in bboxes],
            "pixel_point_set": [_bbox_center(bbox) for bbox in bboxes],
        },
    }


__all__ = ["matching_scene_cell_bbox_evidence"]
