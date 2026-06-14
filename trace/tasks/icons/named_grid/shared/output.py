"""Scene-neutral trace fragments for named-grid icon tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ...shared.icon_task_rendering import icon_render_style_trace

from .defaults import SCENE_ID
from .state import NamedGridScenePayload
from .styles import named_grid_style_trace


def scene_ir_fragment(
    scene: NamedGridScenePayload,
    *,
    scene_kind: str,
    entities: list[dict[str, Any]],
    relations: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build the scene-level IR wrapper around task-owned relations."""

    return {
        "scene_kind": str(scene_kind),
        "scene_id": SCENE_ID,
        "entities": list(entities),
        "relations": dict(relations),
        "frames": {
            "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
            "panels": dict(scene.panel_geometry),
        },
    }


def render_spec_fragment(scene: NamedGridScenePayload, *, render_params: Mapping[str, Any]) -> Dict[str, Any]:
    """Build named-grid render metadata shared by all objectives."""

    return {
        "canvas_size": list(scene.panel_geometry["canvas_size"]),
        "coord_space": "pixel",
        "scene_id": SCENE_ID,
        "panel_geometry": dict(scene.panel_geometry),
        "grid_bbox_xyxy": [int(value) for value in scene.grid_bbox_xyxy],
        "cell_size_px": int(scene.cell_size_px),
        "style": {
            **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=scene.sampled_palette_rgb),
            **named_grid_style_trace(render_params),
        },
    }


def cell_bbox_map(scene: NamedGridScenePayload, *, rows: int, cols: int) -> Dict[str, list[int]]:
    """Return one keyed cell bbox for every row/column address."""

    return {
        f"r{int(row) + 1}c{int(col) + 1}": [int(value) for value in scene.cell_bboxes_xyxy[int(row)][int(col)]]
        for row in range(int(rows))
        for col in range(int(cols))
    }


def object_bbox_map(scene: NamedGridScenePayload) -> Dict[str, list[int]]:
    """Return object bboxes keyed by stable rendered icon instance id."""

    return {
        str(icon.instance_id): [int(value) for value in icon.bbox_xyxy]
        for icon in scene.icons
    }


def render_map_fragment(
    scene: NamedGridScenePayload,
    *,
    rows: int,
    cols: int,
    extra_fields: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build the shared render map plus task-owned annotation aliases."""

    payload: Dict[str, Any] = {
        "image_id": "img0",
        "object_bboxes_px": object_bbox_map(scene),
        "cell_bboxes_px": cell_bbox_map(scene, rows=int(rows), cols=int(cols)),
    }
    if extra_fields:
        payload.update(dict(extra_fields))
    return payload


__all__ = [
    "cell_bbox_map",
    "object_bbox_map",
    "render_map_fragment",
    "render_spec_fragment",
    "scene_ir_fragment",
]
