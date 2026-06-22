"""Annotation projection helpers for sliding-block task witnesses."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, bbox_set_annotation_artifacts

from .state import RenderedSlidingBlockScene


def block_bbox_set(
    rendered_scene: RenderedSlidingBlockScene,
    *,
    block_ids: Sequence[str],
) -> AnnotationArtifacts:
    """Build a bbox-set annotation from source-board block ids."""

    bboxes = [
        [round(float(value), 3) for value in rendered_scene.block_bbox_map[str(block_id)]]
        for block_id in block_ids
    ]
    return bbox_set_annotation_artifacts(bboxes)


def block_and_option_bbox_set(
    rendered_scene: RenderedSlidingBlockScene,
    *,
    block_ids: Sequence[str],
    option_id: str,
) -> AnnotationArtifacts:
    """Build bbox-set annotation for moved source blocks plus one option panel."""

    bboxes = [
        [round(float(value), 3) for value in rendered_scene.block_bbox_map[str(block_id)]]
        for block_id in block_ids
    ]
    bboxes.append([round(float(value), 3) for value in rendered_scene.option_panel_bbox_map[str(option_id)]])
    return bbox_set_annotation_artifacts(bboxes)


__all__ = ["block_and_option_bbox_set", "block_bbox_set"]

