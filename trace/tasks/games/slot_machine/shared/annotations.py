"""Annotation projection helpers for slot-machine tasks."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, segment_set_annotation_artifacts

from .rendering import RenderedSlotMachineScene
from .state import payline_id


def payline_segment_set_annotation(
    rendered_scene: RenderedSlotMachineScene,
    rows: Sequence[int],
) -> AnnotationArtifacts:
    """Build a segment-set annotation for selected horizontal paylines."""

    segments = [
        rendered_scene.render_map["payline_segments_px"][payline_id(int(row))]
        for row in rows
    ]
    return segment_set_annotation_artifacts(segments)


__all__ = ["payline_segment_set_annotation"]
