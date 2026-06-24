"""Annotation helpers for right-triangle altitude theorem diagrams."""

from __future__ import annotations

from trace.tasks.geometry.shared.vector2d import point_to_list

from .state import RenderedRightTriangleAltitudeScene


def point_map_for_roles(
    rendered: RenderedRightTriangleAltitudeScene,
    roles: tuple[str, ...],
) -> dict[str, list[float]]:
    """Return pixel points for the requested visible point labels."""

    points = dict(rendered.annotation_points)
    missing = [role for role in roles if role not in points]
    if missing:
        raise ValueError(f"missing right-triangle altitude annotation roles: {missing}")
    return {str(role): point_to_list(points[str(role)]) for role in roles}


__all__ = ["point_map_for_roles"]
