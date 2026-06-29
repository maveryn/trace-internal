"""Annotation projection helpers for maze-exit puzzle tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.types import TypedValue


def _round_bbox(bbox: Sequence[float]) -> list[float]:
    """Normalize one image-pixel bbox into stable float coordinates."""

    return [round(float(value), 3) for value in bbox]


def item_bbox_set(
    item_bbox_map: Mapping[str, Sequence[float]],
    item_ids: Sequence[str],
) -> tuple[TypedValue, dict[str, Any], dict[str, Any]]:
    """Return bbox_set annotation artifacts for an ordered set of maze exits."""

    bboxes = [_round_bbox(item_bbox_map[str(item_id)]) for item_id in item_ids]
    projected = {
        "bbox_set": list(bboxes),
        "pixel_bbox_set": list(bboxes),
        "value": list(bboxes),
    }
    witness = {
        "type": "bbox_set",
        "value": list(bboxes),
        "ordered_item_ids": [str(item_id) for item_id in item_ids],
    }
    return TypedValue(type="bbox_set", value=list(bboxes)), projected, witness


def single_item_bbox(
    item_bbox_map: Mapping[str, Sequence[float]],
    item_id: str,
) -> tuple[TypedValue, dict[str, Any], dict[str, Any]]:
    """Return scalar bbox annotation artifacts for one maze exit."""

    bbox = _round_bbox(item_bbox_map[str(item_id)])
    projected = {
        "bbox": list(bbox),
        "pixel_bbox": list(bbox),
        "value": list(bbox),
    }
    witness = {
        "type": "bbox",
        "value": list(bbox),
        "ordered_item_ids": [str(item_id)],
    }
    return TypedValue(type="bbox", value=list(bbox)), projected, witness


__all__ = ["item_bbox_set", "single_item_bbox"]
