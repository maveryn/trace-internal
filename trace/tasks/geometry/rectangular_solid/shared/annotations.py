"""Annotation conversion helpers for rectangular-solid scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.geometry.shared.annotation_values import (
    keyed_bbox_annotation_artifacts,
    keyed_point_annotation_artifacts,
)
from trace.tasks.geometry.shared.measurement_rendering import bbox_to_list
from trace.tasks.geometry.shared.vector2d import point_to_list

from .state import RenderedRectangularSolidScene


def point_map_annotation(rendered: RenderedRectangularSolidScene) -> tuple[TypedValue, dict[str, Any]]:
    """Build public keyed point annotation from a rendered cuboid scene."""

    artifacts = keyed_point_annotation_artifacts(
        rendered.annotation_keyed_points,
        roles=rendered.annotation_roles,
    )
    return TypedValue(type=artifacts.annotation_type, value=dict(artifacts.value)), dict(artifacts.projected_annotation)


def bbox_map_annotation(rendered: RenderedRectangularSolidScene) -> tuple[TypedValue, dict[str, Any]]:
    """Build public keyed bbox annotation from a rendered frame or net scene."""

    artifacts = keyed_bbox_annotation_artifacts(
        rendered.annotation_keyed_bboxes,
        roles=rendered.annotation_roles,
        include_point_centers=True,
    )
    return TypedValue(type=artifacts.annotation_type, value=dict(artifacts.value)), dict(artifacts.projected_annotation)


def json_ready_points(points: Mapping[str, Sequence[float]]) -> dict[str, list[float]]:
    """Serialize a keyed point mapping for trace payloads."""

    return {str(key): point_to_list(value) for key, value in points.items()}


def json_ready_bboxes(bboxes: Mapping[str, Sequence[float]]) -> dict[str, list[float]]:
    """Serialize a keyed bbox mapping for trace payloads."""

    return {str(key): bbox_to_list(value) for key, value in bboxes.items()}


__all__ = [
    "bbox_map_annotation",
    "json_ready_bboxes",
    "json_ready_points",
    "point_map_annotation",
]
