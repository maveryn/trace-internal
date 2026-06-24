"""Trace fragment helpers for isometric harbor public tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .spatial_primitives import rounded_bbox
from .state import IsoHarborScene


def bbox_set_projection(bboxes: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Return the unordered bbox-set projection payload."""

    values = [rounded_bbox(bbox) for bbox in bboxes]
    return {"type": "bbox_set", "bbox_set": values, "pixel_bbox_set": values}


def isometric_harbor_scene_ir(
    *,
    domain: str,
    scene_id: str,
    scene: IsoHarborScene,
    relations: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the common scene-IR fragment for one isometric harbor scene."""

    return {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "tiles": [tile.as_dict() for tile in scene.tiles],
        "entities": [entity.as_dict() for entity in scene.entities],
        "relations": dict(relations),
    }


def isometric_harbor_render_spec(scene: IsoHarborScene, *, scene_id: str) -> dict[str, Any]:
    """Return the render-spec fragment for one harbor scene."""

    projection = dict(scene.trace.get("projection", {})) if isinstance(scene.trace, Mapping) else {}
    return {
        "canvas_size": [int(scene.image.size[0]), int(scene.image.size[1])],
        "coord_space": "pixel",
        "scene_id": str(scene_id),
        "style": {
            "renderer_id": str(scene.trace.get("renderer_id", "")),
            "style_id": str(scene.trace.get("renderer_style", "")),
            "theme_id": str(scene.trace.get("theme_id", "")),
            "canvas_profile": str(scene.trace.get("canvas_profile", "")),
            "canvas_profile_probabilities": dict(scene.trace.get("canvas_profile_probabilities", {})),
            "projection": projection,
            "tile_count": int(scene.trace.get("tile_count", 0)),
            "background_rgb": list(scene.trace.get("background_rgb", [])),
            "terrain_tile_counts": dict(scene.trace.get("terrain_tile_counts", {})),
            "entity_count": int(scene.trace.get("entity_count", 0)),
        },
    }


def isometric_harbor_boat_count_render_map(
    *,
    scene: IsoHarborScene,
    target_side: str,
    counted_entity_ids: Sequence[str],
) -> dict[str, Any]:
    """Return task render-map fields for boat-side counting."""

    entities_by_id = {str(entity.entity_id): entity for entity in scene.entities}
    counted_ids = [str(entity_id) for entity_id in counted_entity_ids]
    counted_bboxes = [rounded_bbox(entities_by_id[entity_id].bbox_xyxy) for entity_id in counted_ids if entity_id in entities_by_id]
    boat_sides = {
        str(entity.entity_id): str(entity.metadata.get("dock_side", ""))
        for entity in scene.entities
        if str(entity.object_type) == "boat"
    }
    return {
        "image_id": "img0",
        "target_side": str(target_side),
        "counted_entity_ids": counted_ids,
        "counted_entity_bboxes_px": counted_bboxes,
        "boat_sides_by_id": boat_sides,
        "boat_bboxes_px_by_id": {
            str(entity.entity_id): rounded_bbox(entity.bbox_xyxy)
            for entity in scene.entities
            if str(entity.object_type) == "boat"
        },
        "boat_counts_by_side": dict(scene.trace.get("boat_counts_by_side", {})),
        "answer_count": len(counted_ids),
    }


__all__ = [
    "bbox_set_projection",
    "isometric_harbor_boat_count_render_map",
    "isometric_harbor_render_spec",
    "isometric_harbor_scene_ir",
]
