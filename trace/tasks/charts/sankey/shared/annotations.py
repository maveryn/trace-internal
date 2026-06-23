"""Annotation projection helpers for standard Sankey charts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .state import SankeyRenderResult


def bbox_set_annotation(
    *,
    rendered: SankeyRenderResult,
    segment_refs: Sequence[str],
) -> dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    refs = [str(segment_id) for segment_id in segment_refs]
    boxes = [list(rendered_scene.segment_label_bbox_map[str(segment_id)]) for segment_id in refs]
    return {
        "type": "bbox_set",
        "value": list(boxes),
        "segment_refs": list(refs),
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": list(boxes),
            "pixel_bbox_set": list(boxes),
            "segment_ids": list(refs),
            "segment_label_bbox_map": {
                str(segment_id): list(rendered_scene.segment_label_bbox_map[str(segment_id)])
                for segment_id in refs
            },
            "segment_bbox_map": {
                str(segment_id): list(rendered_scene.segment_bbox_map[str(segment_id)])
                for segment_id in refs
            },
        },
    }


__all__ = ["bbox_set_annotation"]
