"""Annotation helpers for word-search puzzle tasks."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.puzzles.shared.word_grid import Cell, cell_key


def bbox_sequence_for_cells(
    item_bbox_map: dict[str, list[float]],
    cells: tuple[Cell, ...],
) -> tuple[TypedValue, dict[str, object], dict[str, object]]:
    """Return ordered bbox-sequence annotation for a visible cell path."""

    sequence = [
        [round(float(value), 3) for value in item_bbox_map[cell_key(cell)]]
        for cell in cells
    ]
    annotation_gt = TypedValue(type="bbox_sequence", value=list(sequence))
    projected_annotation = {
        "type": "bbox_sequence",
        "bbox_sequence": list(sequence),
        "value": list(sequence),
    }
    witness_symbolic = {"type": "bbox_sequence", "value": list(sequence)}
    return annotation_gt, projected_annotation, witness_symbolic


def bbox_set_for_cells(
    item_bbox_map: dict[str, list[float]],
    cells: tuple[Cell, ...],
) -> tuple[TypedValue, dict[str, object], dict[str, object]]:
    """Return unordered bbox-set annotation for countable grid cells."""

    bboxes = [
        [round(float(value), 3) for value in item_bbox_map[cell_key(cell)]]
        for cell in cells
    ]
    annotation_gt = TypedValue(type="bbox_set", value=list(bboxes))
    projected_annotation = {
        "type": "bbox_set",
        "bbox_set": list(bboxes),
        "value": list(bboxes),
    }
    witness_symbolic = {"type": "bbox_set", "value": list(bboxes)}
    return annotation_gt, projected_annotation, witness_symbolic


def segment_set_for_cell_pairs(
    cell_centers_px: dict[str, tuple[float, float]],
    cell_pairs: tuple[tuple[Cell, Cell], ...],
) -> tuple[TypedValue, dict[str, object], dict[str, object]]:
    """Return unordered segment-set annotation from start/end cell centers."""

    segments: list[list[list[float]]] = []
    for start_cell, end_cell in cell_pairs:
        start = cell_centers_px[cell_key(start_cell)]
        end = cell_centers_px[cell_key(end_cell)]
        segments.append(
            [
                [round(float(start[0]), 3), round(float(start[1]), 3)],
                [round(float(end[0]), 3), round(float(end[1]), 3)],
            ]
        )
    annotation_gt = TypedValue(type="segment_set", value=list(segments))
    projected_annotation = {
        "type": "segment_set",
        "segment_set": list(segments),
        "value": list(segments),
    }
    witness_symbolic = {"type": "segment_set", "value": list(segments)}
    return annotation_gt, projected_annotation, witness_symbolic


__all__ = [
    "bbox_sequence_for_cells",
    "bbox_set_for_cells",
    "segment_set_for_cell_pairs",
]
