"""Trace fragment helpers for RPG interior public tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .rendering import SCENE_ID
from .state import RpgInteriorEntity, RpgInteriorScene


def rpg_interior_scene_ir(
    *,
    domain: str,
    scene_id: str,
    scene: RpgInteriorScene,
    relations: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the common scene-IR fragment for an RPG interior scene."""

    return {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "entities": [entity.as_dict() for entity in scene.entities],
        "regions": [region.as_dict() for region in scene.regions],
        "relations": dict(relations),
    }


def rpg_interior_render_spec(scene: RpgInteriorScene, *, scene_id: str = SCENE_ID) -> dict[str, Any]:
    """Return the render-spec fragment for one scene."""

    return {
        "canvas_size": [int(scene.image.size[0]), int(scene.image.size[1])],
        "coord_space": "pixel",
        "scene_id": str(scene_id),
        "style": {
            "renderer_id": str(scene.trace.get("renderer_id", "")),
            "style_id": str(scene.trace.get("renderer_style", "")),
            "theme_id": str(scene.trace.get("theme_id", "")),
            "interior_type": str(scene.trace.get("interior_type", "")),
            "tile_px": int(scene.trace.get("tile_px", 0)),
            "grid_cols": int(scene.trace.get("grid_cols", 0)),
            "grid_rows": int(scene.trace.get("grid_rows", 0)),
            "canvas_profile": str(scene.trace.get("canvas_profile", "")),
            "canvas_profile_probabilities": dict(scene.trace.get("canvas_profile_probabilities", {})),
        },
    }


def rpg_interior_render_map(
    *,
    scene: RpgInteriorScene,
    counted_entity_ids: Sequence[str],
) -> dict[str, Any]:
    """Return task render-map fields for count tasks."""

    entity_bboxes = entity_bbox_map(scene)
    region_bboxes = region_bbox_map(scene)
    counted_ids = [str(entity_id) for entity_id in counted_entity_ids]
    return {
        "image_id": "img0",
        "entity_bboxes_px": entity_bboxes,
        "region_bboxes_px": region_bboxes,
        "counted_entity_ids": counted_ids,
        "counted_entity_bboxes_px": [entity_bboxes[entity_id] for entity_id in counted_ids],
        "counted_entity_points_px": annotation_points(scene, counted_ids),
    }


def entity_bbox_map(scene: RpgInteriorScene) -> dict[str, list[float]]:
    return {
        str(entity.entity_id): [round(float(value), 3) for value in entity.bbox_xyxy]
        for entity in scene.entities
    }


def region_bbox_map(scene: RpgInteriorScene) -> dict[str, list[float]]:
    return {
        str(region.region_id): [round(float(value), 3) for value in region.bbox_xyxy]
        for region in scene.regions
    }


def annotation_points(scene: RpgInteriorScene, entity_ids: Sequence[str]) -> list[list[float]]:
    by_id = {str(entity.entity_id): entity for entity in scene.entities}
    return [
        [round(float(value), 3) for value in by_id[str(entity_id)].point_xy]
        for entity_id in entity_ids
    ]


def point_set_projection(points: Sequence[Sequence[float]]) -> dict[str, Any]:
    values = [[round(float(value), 3) for value in point[:2]] for point in points]
    return {"type": "point_set", "point_set": values, "pixel_point_set": values}


def counted_zone_objects(
    scene: RpgInteriorScene,
    *,
    target_object_type: str,
    target_zone_id: str,
) -> tuple[RpgInteriorEntity, ...]:
    """Return countable objects matching the task predicate."""

    return tuple(
        entity
        for entity in scene.entities
        if entity.countable
        and str(entity.object_type) == str(target_object_type)
        and str(entity.zone_id) == str(target_zone_id)
    )


__all__ = [
    "annotation_points",
    "counted_zone_objects",
    "entity_bbox_map",
    "point_set_projection",
    "region_bbox_map",
    "rpg_interior_render_map",
    "rpg_interior_render_spec",
    "rpg_interior_scene_ir",
]
