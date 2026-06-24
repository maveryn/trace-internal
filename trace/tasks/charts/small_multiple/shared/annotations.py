"""Annotation projection helpers for small-multiple composition charts."""

from __future__ import annotations

from typing import Sequence

from .rendering import bbox_center_point
from .state import AnnotationRole, PanelSpec, RenderedSmallMultiples


def annotation_map_key(role: str, panel: str, segment: str | None = None) -> str:
    if segment is None:
        return f"{str(role)}|{str(panel)}"
    return f"{str(role)}|{str(panel)}|{str(segment)}"


def format_annotation_key_list(keys: Sequence[str]) -> str:
    return ", ".join(f'"{str(key)}"' for key in keys)


def point_map_for_roles(
    rendered: RenderedSmallMultiples,
    roles: Sequence[AnnotationRole],
) -> dict[str, list[float]]:
    points: dict[str, list[float]] = {}
    for role in roles:
        if role.segment is None:
            bbox = rendered.total_bbox_by_panel.get(str(role.panel))
        else:
            bbox = rendered.annotation_bbox_by_key.get((str(role.panel), str(role.segment)))
        if bbox is None:
            raise RuntimeError(f"missing small-multiple annotation target for {role}")
        points[annotation_map_key(str(role.role), str(role.panel), None if role.segment is None else str(role.segment))] = bbox_center_point(bbox)
    if not points:
        raise RuntimeError("empty small-multiple annotation")
    return points


def point_map_payload(points: dict[str, list[float]]) -> dict[str, object]:
    point_set = [list(point) for point in points.values()]
    return {
        "type": "point_map",
        "point_map": dict(points),
        "pixel_point_map": dict(points),
        "point_set": list(point_set),
        "pixel_point_set": list(point_set),
    }


def roles_for_panel_segments(
    panels: Sequence[PanelSpec],
    role_segments: Sequence[tuple[str, str]],
    *,
    include_total: bool = False,
) -> tuple[AnnotationRole, ...]:
    roles: list[AnnotationRole] = []
    for panel in panels:
        roles.extend(
            AnnotationRole(str(role), str(panel.label), str(segment))
            for role, segment in role_segments
        )
        if include_total:
            roles.append(AnnotationRole("total", str(panel.label)))
    return tuple(roles)
