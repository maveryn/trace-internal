"""Trace fragment helpers for RPG house public tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .rendering import SCENE_ID
from .state import RpgHouseScene


def rpg_house_scene_ir(
    *,
    domain: str,
    scene_id: str,
    scene: RpgHouseScene,
    relations: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the common scene-IR fragment for an RPG house scene."""

    return {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "rooms": [room.as_dict() for room in scene.rooms],
        "doors": [door.as_dict() for door in scene.doors],
        "entities": [entity.as_dict() for entity in scene.entities],
        "relations": dict(relations),
    }


def rpg_house_render_spec(scene: RpgHouseScene, *, scene_id: str = SCENE_ID) -> dict[str, Any]:
    """Return the render-spec fragment for one scene."""

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
            "canvas_profile": str(scene.trace.get("canvas_profile", "")),
            "canvas_profile_probabilities": dict(scene.trace.get("canvas_profile_probabilities", {})),
            "label_font": dict(scene.trace.get("label_font", {})),
        },
    }


def rpg_house_reachability_render_map(
    *,
    scene: RpgHouseScene,
    start_room_id: str,
    candidate_room_ids: Sequence[str],
    answer_room_id: str,
) -> dict[str, Any]:
    """Return task render-map fields for the room-reachability task."""

    room_boxes = room_bbox_map(scene)
    door_boxes = door_bbox_map(scene)
    candidate_ids = [str(room_id) for room_id in candidate_room_ids]
    return {
        "image_id": "img0",
        "room_bboxes_px": room_boxes,
        "door_bboxes_px": door_boxes,
        "start_room_id": str(start_room_id),
        "start_room_bbox_px": room_boxes[str(start_room_id)],
        "candidate_room_ids": candidate_ids,
        "candidate_room_bboxes_px": {room_id: room_boxes[room_id] for room_id in candidate_ids},
        "answer_room_id": str(answer_room_id),
        "answer_room_bbox_px": room_boxes[str(answer_room_id)],
    }


def room_bbox_map(scene: RpgHouseScene) -> dict[str, list[float]]:
    return {
        str(room.room_id): [round(float(value), 3) for value in room.bbox_xyxy]
        for room in scene.rooms
    }


def door_bbox_map(scene: RpgHouseScene) -> dict[str, list[float]]:
    return {
        str(door.door_id): [round(float(value), 3) for value in door.bbox_xyxy]
        for door in scene.doors
    }


def bbox_projection(bbox: Sequence[float]) -> dict[str, Any]:
    values = [round(float(value), 3) for value in bbox[:4]]
    return {"type": "bbox", "bbox": values, "pixel_bbox": values}


__all__ = [
    "bbox_projection",
    "door_bbox_map",
    "room_bbox_map",
    "rpg_house_reachability_render_map",
    "rpg_house_render_spec",
    "rpg_house_scene_ir",
]
