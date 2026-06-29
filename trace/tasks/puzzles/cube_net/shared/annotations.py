"""Annotation projection helpers for cube-net puzzle tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from trace.core.types import TypedValue


def round_annotation_bbox(bbox: Sequence[float]) -> list[float]:
    """Round a pixel bbox into the JSON-stable annotation representation."""

    return [round(float(value), 3) for value in bbox]


def bbox_map_typed_value(annotation: Mapping[str, Sequence[float]]) -> TypedValue:
    """Build a typed bbox_map annotation from keyed semantic witnesses."""

    value = {
        str(key): round_annotation_bbox(bbox)
        for key, bbox in annotation.items()
    }
    return TypedValue(type="bbox_map", value=dict(value))


def projected_bbox_map(annotation: Mapping[str, Sequence[float]]) -> Dict[str, Any]:
    """Build the projected-annotation payload for reward/review code."""

    value = {
        str(key): round_annotation_bbox(bbox)
        for key, bbox in annotation.items()
    }
    return {
        "type": "bbox_map",
        "bbox_map": dict(value),
        "pixel_bbox_map": dict(value),
        "value": dict(value),
    }


__all__ = ["bbox_map_typed_value", "projected_bbox_map", "round_annotation_bbox"]
