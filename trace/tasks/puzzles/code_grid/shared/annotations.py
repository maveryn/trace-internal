"""Annotation helpers for code-grid puzzle tasks."""

from __future__ import annotations

from trace.core.types import TypedValue

from trace.tasks.puzzles.shared.word_grid import Cell, cell_key


def bbox_sequence_for_cells(
    item_bbox_map: dict[str, list[float]],
    cells: tuple[Cell, ...],
) -> tuple[TypedValue, dict[str, object], dict[str, object]]:
    """Return bbox-sequence annotation for ordered grid cells."""

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


__all__ = ["bbox_sequence_for_cells"]
