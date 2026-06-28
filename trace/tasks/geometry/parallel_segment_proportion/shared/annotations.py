"""Annotation helpers for parallel-segment proportion diagrams."""

from __future__ import annotations

from typing import Mapping

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts, keyed_point_annotation_artifacts

from .state import Point


POINT_ROLES: tuple[str, ...] = ("A", "B", "C", "D", "E")


def point_map_annotation_artifacts(points: Mapping[str, Point]) -> PixelAnnotationArtifacts:
    """Build a keyed point-map annotation for visible construction witnesses."""

    return keyed_point_annotation_artifacts(points, roles=POINT_ROLES)


__all__ = ["POINT_ROLES", "point_map_annotation_artifacts"]
