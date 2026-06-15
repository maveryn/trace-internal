"""Annotation helpers for container volume-transfer diagrams."""

from __future__ import annotations

from typing import Dict, Sequence

from trace.tasks.geometry.shared.measurement_rendering import bbox_to_list

from .state import RenderedScene


def annotation_bbox_map(rendered: RenderedScene, keys: Sequence[str]) -> Dict[str, list[float]]:
    return {str(key): bbox_to_list(rendered.annotation_bboxes[str(key)]) for key in keys}


__all__ = ["annotation_bbox_map"]
