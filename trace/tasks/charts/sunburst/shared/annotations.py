"""Annotation helpers for sunburst chart tasks."""

from __future__ import annotations

from collections.abc import Sequence

from .state import BBox, RenderedSunburst


def leaf_value_boxes(rendered: RenderedSunburst, leaf_ids: Sequence[str]) -> list[BBox]:
    boxes = [
        list(rendered.leaf_value_bbox_by_node_id[str(leaf_id)])
        for leaf_id in leaf_ids
        if str(leaf_id) in rendered.leaf_value_bbox_by_node_id
    ]
    if not boxes:
        raise ValueError("sunburst annotation produced no leaf value boxes")
    return boxes


__all__ = ["leaf_value_boxes"]
