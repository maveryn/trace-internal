"""Annotation projection helpers for logic-grid puzzle tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.types import TypedValue


def round_bbox_map(projected: Mapping[str, Any]) -> dict[str, list[float]]:
    """Return rounded role-bound bbox values from a projection dictionary."""

    values = projected.get("bbox_map", {})
    if not isinstance(values, Mapping):
        raise ValueError("logic-grid projection missing bbox_map")
    return {
        str(role): [round(float(value), 3) for value in bbox]
        for role, bbox in values.items()
    }


def selected_option_annotation(
    *,
    board_bbox_px: Sequence[float],
    option_panel_bbox_map: Mapping[str, Sequence[float]],
    selected_option_panel_id: str,
) -> tuple[TypedValue, dict[str, Any], dict[str, Any]]:
    """Build role-bound source-grid and selected-option bbox annotation."""

    option_id = str(selected_option_panel_id)
    if option_id not in option_panel_bbox_map:
        raise RuntimeError(f"missing option bbox for selected panel {option_id!r}")
    bbox_map = {
        "source_grid": [round(float(value), 3) for value in board_bbox_px],
        "selected_option": [
            round(float(value), 3)
            for value in option_panel_bbox_map[option_id]
        ],
    }
    projection = {
        "type": "bbox_map",
        "bbox_map": dict(bbox_map),
        "pixel_bbox_map": dict(bbox_map),
        "value": dict(bbox_map),
    }
    symbolic = {"type": "bbox_map", "value": dict(bbox_map)}
    return TypedValue(type="bbox_map", value=dict(bbox_map)), symbolic, projection
