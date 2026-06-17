"""Annotation helpers for the pattern-grid icons scene."""

from __future__ import annotations

from typing import Any, Dict, Sequence

from ...shared.annotation import bbox_annotation


def violating_cell_bbox_annotation(bbox: Sequence[int | float]) -> Dict[str, Any]:
    """Return scalar bbox annotation for the single violating grid cell."""

    return bbox_annotation(bbox)


__all__ = ["violating_cell_bbox_annotation"]
