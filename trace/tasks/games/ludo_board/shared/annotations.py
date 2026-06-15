"""Annotation projection helpers for Ludo board scene tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts


@dataclass(frozen=True)
class LudoAnnotationBundle:
    """Task-bound annotation plus symbolic witness ids."""

    annotation_gt: TypedValue
    projected_annotation: Mapping[str, Any]
    witness_symbolic: Mapping[str, Any]
    entity_ids: Mapping[str, str]


def _round_bbox(bbox: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in bbox[:4]]


def keyed_ludo_bbox_annotation(
    *,
    role_bboxes: Mapping[str, Sequence[float]],
    role_entity_ids: Mapping[str, str],
) -> LudoAnnotationBundle:
    """Create a keyed bbox annotation from already task-bound visual roles."""

    value = {str(role): _round_bbox(bbox) for role, bbox in role_bboxes.items()}
    artifacts = AnnotationArtifacts(
        annotation_type="keyed_bbox_map",
        value=dict(value),
        annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(value)),
        projected_annotation={
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(value),
            "pixel_keyed_bbox_map": dict(value),
        },
    )
    ids = {str(role): str(entity_id) for role, entity_id in role_entity_ids.items()}
    return LudoAnnotationBundle(
        annotation_gt=artifacts.annotation_gt,
        projected_annotation=dict(artifacts.projected_annotation),
        witness_symbolic={"type": artifacts.annotation_type, "ids": dict(ids)},
        entity_ids=dict(ids),
    )


def _render_map_bbox(render_map: Mapping[str, Any], source: Sequence[str]) -> Sequence[float]:
    if len(source) == 1:
        return render_map[str(source[0])]
    if len(source) == 2:
        return render_map[str(source[0])][str(source[1])]
    raise ValueError("Ludo render-map bbox source must have one or two path segments")


def keyed_ludo_render_map_bbox_annotation(
    *,
    rendered: Any,
    role_sources: Mapping[str, Sequence[str]],
    role_entity_ids: Mapping[str, str],
) -> LudoAnnotationBundle:
    """Project keyed bbox roles from renderer map paths chosen by the task."""

    return keyed_ludo_bbox_annotation(
        role_bboxes={
            str(role): _render_map_bbox(rendered.render_map, source)
            for role, source in dict(role_sources).items()
        },
        role_entity_ids=role_entity_ids,
    )


__all__ = ["LudoAnnotationBundle", "keyed_ludo_bbox_annotation", "keyed_ludo_render_map_bbox_annotation"]
