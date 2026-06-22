"""Trace fragment helpers for RPG dungeon public tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .rendering import SCENE_ID
from .state import RpgDungeonScene


def rpg_dungeon_scene_ir(
    *,
    domain: str,
    scene_id: str,
    scene: RpgDungeonScene,
    relations: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the common scene-IR fragment for an RPG dungeon scene."""

    return {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "chambers": [chamber.as_dict() for chamber in scene.chambers],
        "floor_tiles": [[int(x), int(y)] for x, y in scene.floor_tiles],
        "corridor_tiles": [[int(x), int(y)] for x, y in scene.corridor_tiles],
        "blocked_tiles": [[int(x), int(y)] for x, y in scene.blocked_tiles],
        "blockers": [blocker.as_dict() for blocker in scene.blockers],
        "entities": [entity.as_dict() for entity in scene.entities],
        "relations": dict(relations),
    }


def rpg_dungeon_render_spec(scene: RpgDungeonScene, *, scene_id: str = SCENE_ID) -> dict[str, Any]:
    """Return the render-spec fragment for one dungeon scene."""

    return {
        "canvas_size": [int(scene.image.size[0]), int(scene.image.size[1])],
        "coord_space": "pixel",
        "scene_id": str(scene_id),
        "style": {
            "renderer_id": str(scene.trace.get("renderer_id", "")),
            "style_id": str(scene.trace.get("renderer_style", "")),
            "theme_id": str(scene.trace.get("theme_id", "")),
            "tile_px": int(scene.trace.get("tile_px", 0)),
            "grid_cols": int(scene.trace.get("grid_cols", 0)),
            "grid_rows": int(scene.trace.get("grid_rows", 0)),
            "layout_orientation": str(scene.trace.get("layout_orientation", "")),
            "side_counts": dict(scene.trace.get("side_counts", {})),
            "total_chest_count": int(scene.trace.get("total_chest_count", 0)),
            "monster_count": int(scene.trace.get("monster_count", 0)),
            "canvas_profile": str(scene.trace.get("canvas_profile", "")),
            "canvas_profile_probabilities": dict(scene.trace.get("canvas_profile_probabilities", {})),
        },
    }


def rpg_dungeon_reachable_chest_count_render_map(*, scene: RpgDungeonScene) -> dict[str, Any]:
    """Return task render-map fields for reachable-chest counting."""

    player = player_entity(scene)
    if player is None:
        raise ValueError("reachable-chest count render map requires a player entity")
    chest_points = entity_point_map(scene, scene.chest_entity_ids)
    chest_bboxes = entity_bbox_map(scene, scene.chest_entity_ids)
    reachable_points = entity_point_map(scene, scene.reachable_chest_ids)
    reachable_bboxes = entity_bbox_map(scene, scene.reachable_chest_ids)
    return {
        "image_id": "img0",
        "player_entity_id": str(scene.player_entity_id),
        "player_point_px": [round(float(value), 3) for value in player.point_xy],
        "player_bbox_px": [round(float(value), 3) for value in player.bbox_xyxy],
        "total_chest_count": len(scene.chest_entity_ids),
        "chest_entity_ids": [str(entity_id) for entity_id in scene.chest_entity_ids],
        "chest_points_px": chest_points,
        "chest_bboxes_px": chest_bboxes,
        "reachable_chest_ids": [str(entity_id) for entity_id in scene.reachable_chest_ids],
        "reachable_chest_points_px": reachable_points,
        "reachable_chest_bboxes_px": reachable_bboxes,
        "reachable_count": len(scene.reachable_chest_ids),
        "blocker_bboxes_px": blocker_bbox_map(scene),
        "blocker_points_px": blocker_point_map(scene),
    }


def rpg_dungeon_monster_chamber_count_render_map(*, scene: RpgDungeonScene) -> dict[str, Any]:
    """Return task render-map fields for monster-chamber counting."""

    monsters = monster_entities(scene)
    return {
        "image_id": "img0",
        "total_chest_count": len(scene.chest_entity_ids),
        "monster_count": len(monsters),
        "monster_entity_ids": [str(entity.entity_id) for entity in monsters],
        "monster_chamber_ids": [str(entity.chamber_id) for entity in monsters],
        "monster_object_types": [str(entity.object_type) for entity in monsters],
        "monster_points_px": {
            str(entity.entity_id): [round(float(entity.point_xy[0]), 3), round(float(entity.point_xy[1]), 3)]
            for entity in monsters
        },
        "monster_bboxes_px": {
            str(entity.entity_id): [round(float(value), 3) for value in entity.bbox_xyxy]
            for entity in monsters
        },
        "chest_entity_ids": [str(entity_id) for entity_id in scene.chest_entity_ids],
        "chest_bboxes_px": entity_bbox_map(scene, scene.chest_entity_ids),
    }


def monster_entities(scene: RpgDungeonScene) -> list[Any]:
    return [
        entity
        for entity in scene.entities
        if str(entity.object_type).startswith("monster_")
    ]


def entity_point_map(scene: RpgDungeonScene, entity_ids: Sequence[str] | None = None) -> dict[str, list[float]]:
    wanted = None if entity_ids is None else {str(entity_id) for entity_id in entity_ids}
    return {
        str(entity.entity_id): [round(float(entity.point_xy[0]), 3), round(float(entity.point_xy[1]), 3)]
        for entity in scene.entities
        if wanted is None or str(entity.entity_id) in wanted
    }


def entity_bbox_map(scene: RpgDungeonScene, entity_ids: Sequence[str] | None = None) -> dict[str, list[float]]:
    wanted = None if entity_ids is None else {str(entity_id) for entity_id in entity_ids}
    return {
        str(entity.entity_id): [round(float(value), 3) for value in entity.bbox_xyxy]
        for entity in scene.entities
        if wanted is None or str(entity.entity_id) in wanted
    }


def blocker_bbox_map(scene: RpgDungeonScene) -> dict[str, list[float]]:
    return {
        str(blocker.blocker_id): [round(float(value), 3) for value in blocker.bbox_xyxy]
        for blocker in scene.blockers
    }


def blocker_point_map(scene: RpgDungeonScene) -> dict[str, list[float]]:
    return {
        str(blocker.blocker_id): [round(float(blocker.point_xy[0]), 3), round(float(blocker.point_xy[1]), 3)]
        for blocker in scene.blockers
    }


def player_entity(scene: RpgDungeonScene) -> Any | None:
    for entity in scene.entities:
        if str(entity.entity_id) == str(scene.player_entity_id):
            return entity
    return None


def bbox_set_map_projection(keyed_bboxes: Mapping[str, Sequence[Sequence[float]]]) -> dict[str, Any]:
    values = {
        str(key): [[round(float(value), 3) for value in bbox] for bbox in bboxes]
        for key, bboxes in keyed_bboxes.items()
    }
    return {"type": "bbox_set_map", "bbox_set_map": values, "pixel_bbox_set_map": values}


def bbox_set_projection(bboxes: Sequence[Sequence[float]]) -> dict[str, Any]:
    values = [[round(float(value), 3) for value in bbox] for bbox in bboxes]
    return {"type": "bbox_set", "bbox_set": values, "pixel_bbox_set": values}


__all__ = [
    "bbox_set_projection",
    "bbox_set_map_projection",
    "blocker_bbox_map",
    "blocker_point_map",
    "entity_bbox_map",
    "entity_point_map",
    "monster_entities",
    "player_entity",
    "rpg_dungeon_monster_chamber_count_render_map",
    "rpg_dungeon_reachable_chest_count_render_map",
    "rpg_dungeon_render_spec",
    "rpg_dungeon_scene_ir",
]
