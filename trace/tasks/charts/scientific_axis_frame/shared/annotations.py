"""Annotation projection helpers for scientific axis-frame chart scenes."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.charts.scientific_axis_frame.shared.state import AxisFrameRenderResult
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts


def bbox_map_for_tick_roles(
    *,
    rendered: AxisFrameRenderResult,
    role_tick_keys: Mapping[str, str],
) -> tuple[AnnotationArtifacts, dict[str, Any]]:
    tick_bboxes = rendered.rendered_scene.tick_label_bboxes_px
    mapped = {
        str(role): list(tick_bboxes[str(tick_key)])
        for role, tick_key in role_tick_keys.items()
    }
    projected = {
        "type": "bbox_map",
        "bbox_map": dict(mapped),
        "pixel_bbox_map": dict(mapped),
    }
    artifacts = AnnotationArtifacts(
        annotation_type="bbox_map",
        value=dict(mapped),
        annotation_gt=TypedValue(type="bbox_map", value=dict(mapped)),
        projected_annotation=dict(projected),
    )
    witness_symbolic = {
        "type": "axis_tick_label_witness",
        "tick_keys": [str(value) for value in role_tick_keys.values()],
        "annotation_bbox_map": dict(mapped),
    }
    return artifacts, witness_symbolic


__all__ = ["bbox_map_for_tick_roles"]
