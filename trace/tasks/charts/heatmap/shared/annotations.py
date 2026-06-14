"""Annotation projection helpers for heatmap chart scenes."""

from __future__ import annotations

from typing import Any, Mapping


def annotation_payload(
    *,
    annotation_cell_ids: list[str],
    rendered: Any,
) -> tuple[str, list[list[float]], dict[str, Any]]:
    """Project task-bound symbolic cell ids into pixel bbox annotations."""

    cell_ids = [str(cell_id) for cell_id in annotation_cell_ids]
    annotation_bboxes = [list(rendered.cell_bbox_map[str(cell_id)]) for cell_id in cell_ids]
    projected_annotation = {
        "type": "bbox_set",
        "bbox_set": list(annotation_bboxes),
        "pixel_bbox_set": list(annotation_bboxes),
        "bbox_map": {str(cell_id): list(rendered.cell_bbox_map[str(cell_id)]) for cell_id in cell_ids},
        "cell_ids": list(cell_ids),
    }
    return "bbox_set", list(annotation_bboxes), dict(projected_annotation)


def annotation_refs(
    *,
    annotation_cell_ids: list[str],
    annotation_value: list[list[float]],
) -> list[dict[str, Any]]:
    """Return symbolic-to-pixel annotation references for trace payloads."""

    return [
        {"cell_id": str(cell_id), "bbox_px": list(box)}
        for cell_id, box in zip(annotation_cell_ids, annotation_value)
    ]


def annotation_cell_ids_from_dataset(dataset: Mapping[str, Any]) -> list[str]:
    """Read the symbolic annotation cells chosen by the public task."""

    return [str(cell_id) for cell_id in dataset["annotation_cell_ids"]]


__all__ = ["annotation_cell_ids_from_dataset", "annotation_payload", "annotation_refs"]
