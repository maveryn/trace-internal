"""Annotation helpers for two-anchor icon scenes."""

from __future__ import annotations

from typing import Sequence

from ...shared.annotation import bbox_set_annotation
from ...shared.icon_scene import sort_bboxes_reading_order


def matching_icon_bbox_set_annotation(bboxes: Sequence[Sequence[int | float]]) -> dict:
    """Return sorted bbox-set annotation for counted non-anchor icons."""

    return bbox_set_annotation(sort_bboxes_reading_order(bboxes))


__all__ = ["matching_icon_bbox_set_annotation"]

