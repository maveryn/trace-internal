"""Annotation helpers for measuring-tool scenes."""

from __future__ import annotations

from typing import Mapping, Sequence

from trace.tasks.geometry.shared.annotation_values import (
    PixelAnnotationArtifacts,
    keyed_point_annotation_artifacts,
)


def measuring_tool_point_annotation(
    points: Mapping[str, Sequence[float]],
    *,
    roles: Sequence[str],
) -> PixelAnnotationArtifacts:
    """Build role-bound pixel point annotation for a visible measurement."""

    return keyed_point_annotation_artifacts(points, roles=tuple(str(role) for role in roles))


__all__ = ["measuring_tool_point_annotation"]
