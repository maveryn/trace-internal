"""Trace fragment helpers for isometric farmstead public tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .state import IsoFarmsteadScene


def rounded_bbox(bbox: Sequence[float]) -> list[float]:
    """Return one rounded bbox in final pixel coordinates."""

    return [round(float(value), 3) for value in bbox[:4]]


def bbox_projection(bbox: Sequence[float]) -> dict[str, Any]:
    """Return the scalar bbox projection payload."""

    value = rounded_bbox(bbox)
    return {"type": "bbox", "bbox": value, "pixel_bbox": value, "value": value}


def bbox_set_projection(bboxes: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Return the unordered bbox-set projection payload."""

    values = [rounded_bbox(bbox) for bbox in bboxes]
    return {"type": "bbox_set", "bbox_set": values, "pixel_bbox_set": values}


def isometric_farmstead_scene_ir(
    *,
    domain: str,
    scene_id: str,
    scene: IsoFarmsteadScene,
    relations: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the common scene-IR fragment for one isometric farmstead scene."""

    return {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "tiles": [tile.as_dict() for tile in scene.tiles],
        "entities": [entity.as_dict() for entity in scene.entities],
        "transitions": [transition.as_dict() for transition in scene.transitions],
        "relations": dict(relations),
    }


def isometric_farmstead_render_spec(scene: IsoFarmsteadScene, *, scene_id: str) -> dict[str, Any]:
    """Return the render-spec fragment for one farmstead scene."""

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
            "levels": list(scene.trace.get("levels", [])),
            "tile_count": int(scene.trace.get("tile_count", 0)),
            "entity_count": int(scene.trace.get("entity_count", 0)),
        },
    }


def isometric_farmstead_elevation_render_map(
    *,
    scene: IsoFarmsteadScene,
    candidate_tile_ids_by_label: Mapping[str, str],
    selected_label: str,
) -> dict[str, Any]:
    """Return task render-map fields for terrain-elevation option selection."""

    tiles_by_id = {str(tile.tile_id): tile for tile in scene.tiles}
    label_bboxes = {
        str(label): rounded_bbox(scene.label_bboxes_by_tile_id[str(tile_id)])
        for label, tile_id in candidate_tile_ids_by_label.items()
        if str(tile_id) in scene.label_bboxes_by_tile_id
    }
    tile_bboxes = {
        str(label): rounded_bbox(tiles_by_id[str(tile_id)].bbox_xyxy)
        for label, tile_id in candidate_tile_ids_by_label.items()
    }
    tile_levels = {
        str(label): int(tiles_by_id[str(tile_id)].level)
        for label, tile_id in candidate_tile_ids_by_label.items()
    }
    selected_tile_id = str(candidate_tile_ids_by_label[str(selected_label)])
    selected_tile = tiles_by_id[selected_tile_id]
    return {
        "image_id": "img0",
        "candidate_tile_ids_by_label": dict(candidate_tile_ids_by_label),
        "candidate_tile_bboxes_px_by_label": tile_bboxes,
        "candidate_label_bboxes_px_by_label": label_bboxes,
        "candidate_levels_by_label": tile_levels,
        "selected_label": str(selected_label),
        "selected_tile_id": selected_tile_id,
        "selected_tile_level": int(selected_tile.level),
        "selected_tile_bbox_px": rounded_bbox(selected_tile.bbox_xyxy),
    }


def isometric_farmstead_object_count_render_map(
    *,
    scene: IsoFarmsteadScene,
    target_object_type: str,
    target_level: int,
    counted_entity_ids: Sequence[str],
) -> dict[str, Any]:
    """Return task render-map fields for terrain-level object counting."""

    entities_by_id = {str(entity.entity_id): entity for entity in scene.entities}
    level_object_counts: dict[str, dict[str, int]] = {}
    for entity in scene.entities:
        level_key = str(int(entity.level))
        object_key = str(entity.object_type)
        level_object_counts.setdefault(level_key, {})
        level_object_counts[level_key][object_key] = int(level_object_counts[level_key].get(object_key, 0)) + 1
    counted_ids = [str(entity_id) for entity_id in counted_entity_ids]
    counted_bboxes = [rounded_bbox(entities_by_id[entity_id].bbox_xyxy) for entity_id in counted_ids if entity_id in entities_by_id]
    return {
        "image_id": "img0",
        "target_object_type": str(target_object_type),
        "target_level": int(target_level),
        "counted_entity_ids": counted_ids,
        "counted_entity_bboxes_px": counted_bboxes,
        "entity_levels_by_id": {str(entity.entity_id): int(entity.level) for entity in scene.entities},
        "entity_object_types_by_id": {str(entity.entity_id): str(entity.object_type) for entity in scene.entities},
        "level_object_counts": level_object_counts,
        "answer_count": len(counted_ids),
    }


__all__ = [
    "bbox_set_projection",
    "bbox_projection",
    "isometric_farmstead_elevation_render_map",
    "isometric_farmstead_object_count_render_map",
    "isometric_farmstead_render_spec",
    "isometric_farmstead_scene_ir",
    "rounded_bbox",
]
