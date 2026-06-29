"""Annotation projection helpers for Tangram puzzle tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.types import TypedValue


def _round_bbox(bbox: Sequence[float]) -> list[float]:
    """Normalize one bbox into stable image-pixel coordinates."""

    return [round(float(value), 3) for value in bbox]


def bbox_set_for_piece_ids(
    piece_bbox_map: Mapping[str, Sequence[float]],
    piece_ids: Sequence[str],
) -> tuple[TypedValue, dict[str, Any], dict[str, Any]]:
    """Project counted Tangram pieces to a bbox-set annotation."""

    ordered_ids = [str(piece_id) for piece_id in piece_ids]
    missing = [piece_id for piece_id in ordered_ids if piece_id not in piece_bbox_map]
    if missing:
        raise RuntimeError(f"missing Tangram piece bboxes for {missing!r}")
    bboxes = [_round_bbox(piece_bbox_map[piece_id]) for piece_id in ordered_ids]
    projected = {
        "bbox_set": list(bboxes),
        "pixel_bbox_set": list(bboxes),
        "value": list(bboxes),
    }
    witness = {
        "type": "bbox_set",
        "value": list(bboxes),
        "ordered_item_ids": list(ordered_ids),
    }
    return TypedValue(type="bbox_set", value=list(bboxes)), projected, witness


def missing_piece_bbox_map(
    *,
    piece_bbox_map: Mapping[str, Sequence[float]],
    option_panel_bbox_map: Mapping[str, Sequence[float]],
    target_piece_id: str,
    correct_option_panel_id: str,
) -> tuple[TypedValue, dict[str, Any], dict[str, Any]]:
    """Project missing region and selected option to role-bound bbox_map."""

    target_id = str(target_piece_id)
    option_id = str(correct_option_panel_id)
    if target_id not in piece_bbox_map:
        raise RuntimeError(f"missing Tangram target bbox for {target_id!r}")
    if option_id not in option_panel_bbox_map:
        raise RuntimeError(f"missing Tangram option bbox for {option_id!r}")
    bbox_map = {
        "missing_region": _round_bbox(piece_bbox_map[target_id]),
        "selected_option": _round_bbox(option_panel_bbox_map[option_id]),
    }
    projected = {
        "bbox_map": dict(bbox_map),
        "pixel_bbox_map": dict(bbox_map),
        "value": dict(bbox_map),
    }
    witness = {
        "type": "bbox_map",
        "value": dict(bbox_map),
        "item_ids_by_key": {
            "missing_region": target_id,
            "selected_option": option_id,
        },
    }
    return TypedValue(type="bbox_map", value=dict(bbox_map)), projected, witness


__all__ = [
    "bbox_set_for_piece_ids",
    "missing_piece_bbox_map",
]
