"""Annotation projection helpers for slot-machine tasks."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, segment_set_annotation_artifacts

from .rendering import RenderedSlotMachineScene
from .state import payline_entity_id


def payline_segment_set_annotation(
    rendered_scene: RenderedSlotMachineScene,
    payline_keys: Sequence[str],
) -> AnnotationArtifacts:
    """Build a segment-set annotation for selected conceptual paylines."""

    segments = [
        rendered_scene.render_map["payline_segments_px"][payline_entity_id(str(payline_key))]
        for payline_key in payline_keys
    ]
    return segment_set_annotation_artifacts(segments)


__all__ = ["payline_segment_set_annotation"]
