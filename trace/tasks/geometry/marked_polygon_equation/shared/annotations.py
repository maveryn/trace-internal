"""Annotation projection for marked polygon equation diagrams."""

from __future__ import annotations

from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts, keyed_point_annotation_artifacts

from .state import RenderedMarkedEquationScene


def marked_equation_point_annotation(rendered: RenderedMarkedEquationScene) -> PixelAnnotationArtifacts:
    """Return keyed visible-vertex points for the rendered construction."""

    return keyed_point_annotation_artifacts(rendered.annotation_points)


__all__ = ["marked_equation_point_annotation"]
