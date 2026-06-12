"""Annotation projection helpers for circle-polygon-composite render outputs."""

from __future__ import annotations

from typing import Dict

from trace.tasks.geometry.shared.vector2d import point_to_list

from .state import RenderedAngleScene, RenderedTangentialScene


def keyed_point_annotation(
    rendered: RenderedAngleScene | RenderedTangentialScene,
) -> Dict[str, list[float]]:
    """Serialize rendered keyed witness points into prompt-facing annotation_gt."""

    return {str(key): point_to_list(value) for key, value in rendered.annotation_keyed_points.items()}


__all__ = ["keyed_point_annotation"]
