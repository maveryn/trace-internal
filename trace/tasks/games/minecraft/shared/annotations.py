"""Annotation projection helpers for Minecraft-like block-world scenes."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, point_set_annotation_artifacts

from .state import RenderedMinecraftScene


def minecraft_point_set_annotation(
    *,
    rendered: RenderedMinecraftScene,
    entity_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Project entity ids to the public unordered point-set annotation."""

    points = [
        list(rendered.render_map["entity_points_px"][str(entity_id)])
        for entity_id in tuple(str(value) for value in entity_ids)
    ]
    return point_set_annotation_artifacts(points)


__all__ = ["minecraft_point_set_annotation"]
