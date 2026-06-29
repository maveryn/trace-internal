"""Annotation projection helpers for polyomino missing-piece puzzles."""

from __future__ import annotations

from trace.tasks.shared.annotation_artifacts import (
    AnnotationArtifacts,
    bbox_map_annotation_artifacts,
)

from .state import RenderedPolyominoMissingScene


def option_and_missing_region_annotation(
    *,
    rendered_scene: RenderedPolyominoMissingScene,
    selected_option_panel_id: str,
) -> AnnotationArtifacts:
    """Return role-keyed boxes for the selected option and missing region."""

    item_bboxes = rendered_scene.bbox_map
    return bbox_map_annotation_artifacts(
        {
            "selected_option": item_bboxes[str(selected_option_panel_id)],
            "missing_region": item_bboxes["missing_region"],
        }
    )


__all__ = ["option_and_missing_region_annotation"]
