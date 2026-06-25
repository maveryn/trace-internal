"""Trace fragment helpers for RPG tactical map tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .state import RpgTacticalMapScene


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


def bbox_sequence_projection(bboxes: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Return the ordered bbox-sequence projection payload."""

    values = [rounded_bbox(bbox) for bbox in bboxes]
    return {"type": "bbox_sequence", "bbox_sequence": values, "pixel_bbox_sequence": values}


def rpg_tactical_map_scene_ir(
    *,
    domain: str,
    scene_id: str,
    scene: RpgTacticalMapScene,
    relations: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the common scene-IR fragment for one tactical map."""

    return {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "tiles": [tile.as_dict() for tile in scene.tiles],
        "units": [unit.as_dict() for unit in scene.units],
        "relations": dict(relations),
    }


def rpg_tactical_map_render_spec(scene: RpgTacticalMapScene, *, scene_id: str) -> dict[str, Any]:
    """Return the render-spec fragment for one scene."""

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
            "grid_cols": int(scene.trace.get("grid_cols", 0)),
            "grid_rows": int(scene.trace.get("grid_rows", 0)),
            "tile_px": int(scene.trace.get("tile_px", 0)),
            "label_font": dict(scene.trace.get("label_font", {})),
        },
    }


def movement_reachable_render_map(
    *,
    scene: RpgTacticalMapScene,
    candidate_tile_ids_by_label: Mapping[str, str],
    selected_label: str,
    movement_costs_by_tile_id: Mapping[str, int],
    movement_budget: int,
) -> dict[str, Any]:
    """Return task render-map fields for movement-reachability selection."""

    tiles_by_id = {str(tile.tile_id): tile for tile in scene.tiles}
    selected_tile_id = str(candidate_tile_ids_by_label[str(selected_label)])
    selected_tile = tiles_by_id[selected_tile_id]
    candidate_tile_bboxes = {
        str(label): rounded_bbox(tiles_by_id[str(tile_id)].bbox_xyxy)
        for label, tile_id in candidate_tile_ids_by_label.items()
    }
    candidate_label_bboxes = {
        str(label): rounded_bbox(scene.label_bboxes_by_tile_id[str(tile_id)])
        for label, tile_id in candidate_tile_ids_by_label.items()
        if str(tile_id) in scene.label_bboxes_by_tile_id
    }
    candidate_terrain = {
        str(label): str(tiles_by_id[str(tile_id)].terrain)
        for label, tile_id in candidate_tile_ids_by_label.items()
    }
    candidate_costs = {
        str(label): (
            int(movement_costs_by_tile_id[str(tile_id)])
            if str(tile_id) in movement_costs_by_tile_id
            else None
        )
        for label, tile_id in candidate_tile_ids_by_label.items()
    }
    return {
        "image_id": "img0",
        "movement_budget": int(movement_budget),
        "candidate_tile_ids_by_label": dict(candidate_tile_ids_by_label),
        "candidate_tile_bboxes_px_by_label": candidate_tile_bboxes,
        "candidate_label_bboxes_px_by_label": candidate_label_bboxes,
        "candidate_terrain_by_label": candidate_terrain,
        "candidate_shortest_costs_by_label": candidate_costs,
        "selected_label": str(selected_label),
        "selected_tile_id": selected_tile_id,
        "selected_tile_bbox_px": rounded_bbox(selected_tile.bbox_xyxy),
        "player_unit": scene.units[0].as_dict() if scene.units else {},
    }


def movement_reachable_count_render_map(
    *,
    scene: RpgTacticalMapScene,
    counted_tile_ids: Sequence[str],
    movement_costs_by_tile_id: Mapping[str, int],
    movement_budget: int,
) -> dict[str, Any]:
    """Return task render-map fields for movement-reachability counting."""

    tiles_by_id = {str(tile.tile_id): tile for tile in scene.tiles}
    counted_ids = [str(tile_id) for tile_id in counted_tile_ids]
    return {
        "image_id": "img0",
        "movement_budget": int(movement_budget),
        "counted_tile_ids": list(counted_ids),
        "counted_tile_bboxes_px": [
            rounded_bbox(tiles_by_id[str(tile_id)].bbox_xyxy)
            for tile_id in counted_ids
        ],
        "counted_tile_costs_by_id": {
            str(tile_id): int(movement_costs_by_tile_id[str(tile_id)])
            for tile_id in counted_ids
        },
        "answer_count": int(len(counted_ids)),
        "player_unit": scene.units[0].as_dict() if scene.units else {},
    }


def movement_attack_range_render_map(
    *,
    scene: RpgTacticalMapScene,
    candidate_tile_ids_by_label: Mapping[str, str],
    selected_label: str,
    movement_costs_by_tile_id: Mapping[str, int],
    movement_budget: int,
    attack_range: int,
    reachable_move_tile_ids: Sequence[str],
    attackable_tile_ids: Sequence[str],
    attack_sources_by_tile_id: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Return render-map fields for move-then-cardinal-attack selection."""

    tiles_by_id = {str(tile.tile_id): tile for tile in scene.tiles}
    selected_tile_id = str(candidate_tile_ids_by_label[str(selected_label)])
    start_tile_id = str(scene.units[0].tile_id) if scene.units else ""
    start_tile = tiles_by_id.get(start_tile_id)
    candidate_tile_bboxes = {
        str(label): rounded_bbox(tiles_by_id[str(tile_id)].bbox_xyxy)
        for label, tile_id in candidate_tile_ids_by_label.items()
    }
    candidate_label_bboxes = {
        str(label): rounded_bbox(scene.label_bboxes_by_tile_id[str(tile_id)])
        for label, tile_id in candidate_tile_ids_by_label.items()
        if str(tile_id) in scene.label_bboxes_by_tile_id
    }
    attackable_set = {str(tile_id) for tile_id in attackable_tile_ids}
    candidate_start_distances = {
        str(label): (
            abs(int(tiles_by_id[str(tile_id)].row) - int(start_tile.row))
            + abs(int(tiles_by_id[str(tile_id)].col) - int(start_tile.col))
        )
        for label, tile_id in candidate_tile_ids_by_label.items()
    } if start_tile is not None else {}
    nearest_labels: list[str] = []
    minimum_candidate_distance: int | None = None
    if candidate_start_distances:
        minimum_candidate_distance = min(int(distance) for distance in candidate_start_distances.values())
        nearest_labels = sorted(
            str(label)
            for label, distance in candidate_start_distances.items()
            if int(distance) == int(minimum_candidate_distance)
        )
    return {
        "image_id": "img0",
        "movement_budget": int(movement_budget),
        "attack_range": int(attack_range),
        "attack_rule": "after_movement_cardinal_distance_ignores_terrain_cost",
        "candidate_tile_ids_by_label": dict(candidate_tile_ids_by_label),
        "candidate_tile_bboxes_px_by_label": candidate_tile_bboxes,
        "candidate_label_bboxes_px_by_label": candidate_label_bboxes,
        "candidate_terrain_by_label": {
            str(label): str(tiles_by_id[str(tile_id)].terrain)
            for label, tile_id in candidate_tile_ids_by_label.items()
        },
        "candidate_shortest_move_costs_by_label": {
            str(label): (
                int(movement_costs_by_tile_id[str(tile_id)])
                if str(tile_id) in movement_costs_by_tile_id
                else None
            )
            for label, tile_id in candidate_tile_ids_by_label.items()
        },
        "candidate_attackable_by_label": {
            str(label): str(tile_id) in attackable_set
            for label, tile_id in candidate_tile_ids_by_label.items()
        },
        "candidate_attack_source_tile_ids_by_label": {
            str(label): [str(source_id) for source_id in attack_sources_by_tile_id.get(str(tile_id), ())]
            for label, tile_id in candidate_tile_ids_by_label.items()
        },
        "candidate_start_manhattan_by_label": dict(candidate_start_distances),
        "minimum_candidate_start_manhattan": minimum_candidate_distance,
        "nearest_candidate_labels": list(nearest_labels),
        "selected_start_manhattan": (
            int(candidate_start_distances[str(selected_label)])
            if str(selected_label) in candidate_start_distances
            else None
        ),
        "selected_is_unique_nearest_by_start_manhattan": bool(nearest_labels == [str(selected_label)]),
        "reachable_move_tile_ids": [str(tile_id) for tile_id in reachable_move_tile_ids],
        "attackable_tile_ids": [str(tile_id) for tile_id in attackable_tile_ids],
        "selected_label": str(selected_label),
        "selected_tile_id": selected_tile_id,
        "selected_tile_bbox_px": rounded_bbox(tiles_by_id[selected_tile_id].bbox_xyxy),
        "player_unit": scene.units[0].as_dict() if scene.units else {},
    }


def movement_cost_value_render_map(
    *,
    scene: RpgTacticalMapScene,
    target_tile_id: str,
    shortest_path_tile_ids: Sequence[str],
    movement_costs_by_tile_id: Mapping[str, int],
    start_tile_id: str,
    target_manhattan_distance: int,
    answer_value: int,
) -> dict[str, Any]:
    """Return render-map fields for marked-destination movement-cost value tasks."""

    tiles_by_id = {str(tile.tile_id): tile for tile in scene.tiles}
    target_tile = tiles_by_id[str(target_tile_id)]
    path_tile_ids = [str(tile_id) for tile_id in shortest_path_tile_ids]
    return {
        "image_id": "img0",
        "target_tile_id": str(target_tile_id),
        "target_tile_bbox_px": rounded_bbox(target_tile.bbox_xyxy),
        "target_terrain": str(target_tile.terrain),
        "start_tile_id": str(start_tile_id),
        "shortest_path_tile_ids": list(path_tile_ids),
        "shortest_path_tile_bboxes_px": [
            rounded_bbox(tiles_by_id[str(tile_id)].bbox_xyxy)
            for tile_id in path_tile_ids
        ],
        "shortest_path_terrains": [
            str(tiles_by_id[str(tile_id)].terrain)
            for tile_id in path_tile_ids
        ],
        "shortest_path_entry_costs": [
            int(tiles_by_id[str(tile_id)].movement_cost)
            if index > 0 and tiles_by_id[str(tile_id)].movement_cost is not None
            else 0
            for index, tile_id in enumerate(path_tile_ids)
        ],
        "target_manhattan_distance": int(target_manhattan_distance),
        "movement_costs_by_tile_id": {
            str(tile_id): int(cost)
            for tile_id, cost in movement_costs_by_tile_id.items()
        },
        "target_shortest_movement_cost": int(answer_value),
        "answer_value": int(answer_value),
        "player_unit": scene.units[0].as_dict() if scene.units else {},
    }


def terrain_type_count_render_map(
    *,
    scene: RpgTacticalMapScene,
    target_terrain: str,
    counted_tile_ids: Sequence[str],
) -> dict[str, Any]:
    """Return task render-map fields for counting one terrain type."""

    tiles_by_id = {str(tile.tile_id): tile for tile in scene.tiles}
    counted_ids = [str(tile_id) for tile_id in counted_tile_ids]
    return {
        "image_id": "img0",
        "target_terrain": str(target_terrain),
        "counted_tile_ids": list(counted_ids),
        "counted_tile_bboxes_px": [
            rounded_bbox(tiles_by_id[str(tile_id)].bbox_xyxy)
            for tile_id in counted_ids
        ],
        "answer_count": int(len(counted_ids)),
        "player_unit": scene.units[0].as_dict() if scene.units else {},
    }


__all__ = [
    "bbox_projection",
    "bbox_sequence_projection",
    "bbox_set_projection",
    "movement_attack_range_render_map",
    "movement_cost_value_render_map",
    "movement_reachable_count_render_map",
    "movement_reachable_render_map",
    "rounded_bbox",
    "rpg_tactical_map_render_spec",
    "rpg_tactical_map_scene_ir",
    "terrain_type_count_render_map",
]
