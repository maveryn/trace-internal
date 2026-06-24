"""Annotation projection helpers for styled table chart tasks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from trace.core.types import TypedValue

from .rendering import RenderedTableScene


def cell_boxes(rendered: RenderedTableScene, cell_ids: Sequence[str]) -> list[list[float]]:
    """Return table-cell bounding boxes in the requested cell-id order."""

    lookup = {
        str(cell_trace["cell_id"]): [round(float(value), 3) for value in cell_trace["bbox_px"]]
        for cell_trace in rendered.cell_traces
    }
    return [list(lookup[str(cell_id)]) for cell_id in cell_ids if str(cell_id) in lookup]


def cell_box(rendered: RenderedTableScene, cell_id: str) -> list[float]:
    """Return one table-cell bounding box."""

    boxes = cell_boxes(rendered, [str(cell_id)])
    if len(boxes) != 1:
        raise ValueError(f"missing table cell annotation target: {cell_id}")
    return list(boxes[0])


def column_box(rendered: RenderedTableScene, column_header: str) -> list[float]:
    """Return one numeric column-region bounding box."""

    if str(column_header) not in rendered.column_region_bboxes:
        raise ValueError(f"missing table column annotation target: {column_header}")
    return [round(float(value), 3) for value in rendered.column_region_bboxes[str(column_header)]]


def boxed_set_projection(boxes: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Return projected annotation payload for a bbox set."""

    values = [[round(float(value), 3) for value in box] for box in boxes]
    return {"type": "bbox_set", "bbox_set": values}


def boxed_projection(box: Sequence[float]) -> dict[str, Any]:
    """Return projected annotation payload for a single bbox."""

    value = [round(float(item), 3) for item in box]
    return {"type": "bbox", "bbox": value}


def boxed_set_map_projection(box_map: Mapping[str, Sequence[Sequence[float]]]) -> dict[str, Any]:
    """Return projected annotation payload for keyed bbox sets."""

    value = {
        str(key): [[round(float(item), 3) for item in box] for box in boxes]
        for key, boxes in box_map.items()
    }
    return {"type": "bbox_set_map", "bbox_set_map": value}


def annotation_value_from_projection(projected: Mapping[str, Any]) -> TypedValue:
    """Build the verifier annotation value from one projected table annotation."""

    kind = str(projected["type"])
    if kind == "bbox":
        return TypedValue(type="bbox", value=list(projected["bbox"]))
    if kind == "bbox_set":
        return TypedValue(type="bbox_set", value=list(projected["bbox_set"]))
    if kind == "bbox_set_map":
        return TypedValue(type="bbox_set_map", value=dict(projected["bbox_set_map"]))
    raise ValueError(f"unsupported table annotation type: {kind}")


__all__ = [
    "annotation_value_from_projection",
    "boxed_projection",
    "boxed_set_map_projection",
    "boxed_set_projection",
    "cell_box",
    "cell_boxes",
    "column_box",
]
