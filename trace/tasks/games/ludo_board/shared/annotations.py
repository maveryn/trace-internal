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


def _round_point(point: Sequence[float]) -> list[float]:
    return [round(float(point[0]), 3), round(float(point[1]), 3)]


def _bbox_center(bbox: Sequence[float]) -> list[float]:
    return [
        round(0.5 * (float(bbox[0]) + float(bbox[2])), 3),
        round(0.5 * (float(bbox[1]) + float(bbox[3])), 3),
    ]


def keyed_ludo_point_annotation(
    *,
    role_points: Mapping[str, Sequence[float]],
    role_entity_ids: Mapping[str, str],
) -> LudoAnnotationBundle:
    """Create a keyed point annotation from already task-bound visual roles."""

    value = {str(role): _round_point(point) for role, point in role_points.items()}
    artifacts = AnnotationArtifacts(
        annotation_type="keyed_point_map",
        value=dict(value),
        annotation_gt=TypedValue(type="keyed_point_map", value=dict(value)),
        projected_annotation={
            "type": "keyed_point_map",
            "keyed_point_map": dict(value),
            "pixel_keyed_point_map": dict(value),
        },
    )
    ids = {str(role): str(entity_id) for role, entity_id in role_entity_ids.items()}
    return LudoAnnotationBundle(
        annotation_gt=artifacts.annotation_gt,
        projected_annotation=dict(artifacts.projected_annotation),
        witness_symbolic={"type": artifacts.annotation_type, "ids": dict(ids)},
        entity_ids=dict(ids),
    )


def _render_map_point(render_map: Mapping[str, Any], source: Sequence[str]) -> Sequence[float]:
    if len(source) == 1:
        value = render_map[str(source[0])]
    elif len(source) == 2:
        value = render_map[str(source[0])][str(source[1])]
    else:
        raise ValueError("Ludo render-map point source must have one or two path segments")
    if isinstance(value, Sequence) and len(value) >= 2:
        if len(value) == 2:
            return value
        if len(value) >= 4:
            return _bbox_center(value)
    raise ValueError("Ludo render-map point source must resolve to a point or bbox")


def keyed_ludo_render_map_point_annotation(
    *,
    rendered: Any,
    role_sources: Mapping[str, Sequence[str]],
    role_entity_ids: Mapping[str, str],
) -> LudoAnnotationBundle:
    """Project keyed point roles from renderer map paths chosen by the task."""

    return keyed_ludo_point_annotation(
        role_points={
            str(role): _render_map_point(rendered.render_map, source)
            for role, source in dict(role_sources).items()
        },
        role_entity_ids=role_entity_ids,
    )


__all__ = ["LudoAnnotationBundle", "keyed_ludo_point_annotation", "keyed_ludo_render_map_point_annotation"]
