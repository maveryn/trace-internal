"""Annotation projection helpers for dumbbell charts."""

from __future__ import annotations

from typing import Any

from trace.tasks.charts.dumbbell.shared.state import DumbbellDataset, RenderedDumbbell


def annotation_payload(
    *,
    dataset: DumbbellDataset,
    rendered: RenderedDumbbell,
) -> tuple[str, list[list[float]], dict[str, Any], list[dict[str, Any]]]:
    """Project task-bound row annotations into bbox-set payloads."""

    rows_by_id = {str(row.row_id): row for row in dataset.rows}
    annotation_rows = [str(row_id) for row_id in dataset.query.annotation_row_ids]
    annotation = [list(rendered.row_pair_bboxes_px[str(row_id)]) for row_id in annotation_rows]
    records = [
        {
            "row_id": str(row_id),
            "row_label": str(rows_by_id[str(row_id)].label),
            "value_a": int(rows_by_id[str(row_id)].value_a),
            "value_b": int(rows_by_id[str(row_id)].value_b),
            "gap": int(rows_by_id[str(row_id)].gap),
            "row_pair_bbox_px": list(rendered.row_pair_bboxes_px[str(row_id)]),
            "connector_bbox_px": list(rendered.connector_bboxes_px[str(row_id)]),
            "point_a_bbox_px": list(rendered.point_bboxes_px[f"{row_id}:series_a"]),
            "point_b_bbox_px": list(rendered.point_bboxes_px[f"{row_id}:series_b"]),
        }
        for row_id in annotation_rows
    ]
    projected = {
        "type": "bbox_set",
        "bbox_set": list(annotation),
        "pixel_bbox_set": list(annotation),
        "row_ids": list(annotation_rows),
        "annotation_refs": [dict(record) for record in records],
    }
    return "bbox_set", list(annotation), dict(projected), [dict(record) for record in records]


__all__ = ["annotation_payload"]
