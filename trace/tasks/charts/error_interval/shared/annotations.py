"""Annotation projection helpers for error-interval charts."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.charts.error_interval.shared.state import _Dataset, _Rendered


def annotation_payload(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
) -> tuple[str, list[list[float]], Dict[str, Any], list[dict[str, Any]]]:
    """Return bbox-set annotation for the task-selected interval marks."""

    item_by_id = {str(item.item_id): item for item in dataset.items}
    annotation_item_ids = [str(value) for value in dataset.query.annotation_item_ids]
    annotation = [list(rendered.interval_bboxes_px[str(item_id)]) for item_id in annotation_item_ids]
    records = [
        {
            "item_id": str(item_id),
            "item_label": str(item_by_id[str(item_id)].label),
            "lower": int(item_by_id[str(item_id)].lower),
            "midpoint": int(item_by_id[str(item_id)].midpoint),
            "upper": int(item_by_id[str(item_id)].upper),
            "interval_width": int(item_by_id[str(item_id)].upper) - int(item_by_id[str(item_id)].lower),
            "interval_bbox_px": list(rendered.interval_bboxes_px[str(item_id)]),
        }
        for item_id in annotation_item_ids
    ]
    projected = {
        "type": "bbox_set",
        "bbox_set": list(annotation),
        "pixel_bbox_set": list(annotation),
        "bbox_map": {str(item_id): list(rendered.interval_bboxes_px[str(item_id)]) for item_id in annotation_item_ids},
        "item_ids": list(annotation_item_ids),
        "item_labels": [str(record["item_label"]) for record in records],
        "annotation_refs": [dict(record) for record in records],
    }
    return "bbox_set", list(annotation), dict(projected), [dict(record) for record in records]


__all__ = ["annotation_payload"]
