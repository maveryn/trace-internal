"""Dataset construction for shared room-wall 3D scenes."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ..shared.camera_projection import build_projection_frame
from ..shared.object_scene import ObjectSceneRenderParams, object_reference_points
from .wall_mounted_common import (
    FLOOR_PROP_SHAPES,
    FRONT_FLOOR_PROP_SHAPES,
    FRONT_FLOOR_PROP_SLOTS,
    QUERY_OBJECT_TYPE_BY_VARIANT,
    QUERY_TARGET_TYPES,
    ROOM_FRONT_Y,
    ROOM_HEIGHT,
    ROOM_VIEW_YAW_BANDS,
    ROOM_WALL_BASE_DIMENSIONS,
    SURFACE_DISTRACTOR_TYPES,
    SURFACE_PROP_SHAPES_BY_SCENE,
    SURFACE_PROP_TYPES,
    TASK_ID,
    WALL_BACK_Y,
    WALL_X,
    EXTRA_WALL_TYPES,
    _finalize_specs,
    _floor_distractor_for_type,
    _make_floor_prop,
    _object_name,
    _object_plural,
    _sample_room_camera,
    _slot_is_compatible,
    _support_can_hold,
    _surface_distractor_for_type,
    _wall_dimensions_for_type,
    _wall_reference_points,
    _wall_spec,
    _with_picture_scenery,
)

def _resolve_target_count(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[int, Dict[str, float]]:
    lower = int(params.get("target_count_min", group_default(gen_defaults, "target_count_min", 0)))
    upper = int(params.get("target_count_max", group_default(gen_defaults, "target_count_max", 4)))
    lower = max(0, min(6, int(lower)))
    upper = max(lower, min(6, int(upper)))
    support = tuple(range(int(lower), int(upper) + 1))
    explicit = params.get("target_count")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported target_count: {selected}")
        return int(selected), dict(uniform_probability_map(support, selected=int(selected)))
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_count",
    )
    selected = int(support[abs(int(selection_index)) % len(support)])
    return int(selected), dict(uniform_probability_map(support))

def _build_room_dataset(
    *,
    query_id: str,
    scene_variant: str,
    target_count: int,
    render_params: ObjectSceneRenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    target_type = str(QUERY_OBJECT_TYPE_BY_VARIANT[str(query_id)])
    camera = _sample_room_camera(rng, scene_variant=str(scene_variant))
    wall_slots = [
        ("back", -2.35, 1.25),
        ("back", -1.22, 2.05),
        ("back", 0.0, 1.38),
        ("back", 1.18, 2.12),
        ("back", 2.32, 1.30),
        ("left", -2.05, 1.65),
        ("left", -0.82, 2.20),
        ("left", 0.62, 1.36),
        ("left", 1.82, 2.04),
        ("right", -1.92, 1.46),
        ("right", -0.52, 2.18),
        ("right", 0.88, 1.34),
        ("right", 2.02, 2.00),
    ]
    rng.shuffle(wall_slots)
    selected_wall_specs: List[Dict[str, Any]] = []

    def take_slot(object_type: str, *, target_object: bool = False) -> Tuple[str, float, float]:
        for index, slot in enumerate(wall_slots):
            if _slot_is_compatible(slot, object_type=str(object_type), target_object=bool(target_object)):
                return wall_slots.pop(index)
        raise ValueError(f"no compatible wall slot for {object_type}")

    for index in range(int(target_count)):
        wall, hpos, z = take_slot(str(target_type), target_object=True)
        width, height = _wall_dimensions_for_type(str(target_type), rng)
        selected_wall_specs.append(
            _with_picture_scenery(_wall_spec(
                object_id=f"wall_target_{index}_{target_type}",
                object_type=str(target_type),
                wall=str(wall),
                hpos=float(hpos + rng.uniform(-0.06, 0.06)),
                z=float(z + rng.uniform(-0.05, 0.05)),
                width=float(width),
                height=float(height),
                counts_for_query=True,
            ), rng)
        )

    other_types = list(EXTRA_WALL_TYPES)
    rng.shuffle(other_types)
    other_wall_count = int(rng.randint(5, 8))
    for index in range(int(other_wall_count)):
        object_type = str(other_types[index % len(other_types)])
        wall, hpos, z = take_slot(str(object_type))
        width, height = _wall_dimensions_for_type(str(object_type), rng)
        selected_wall_specs.append(
            _with_picture_scenery(_wall_spec(
                object_id=f"wall_context_{index}_{object_type}",
                object_type=str(object_type),
                wall=str(wall),
                hpos=float(hpos + rng.uniform(-0.06, 0.06)),
                z=float(z + rng.uniform(-0.05, 0.05)),
                width=float(width),
                height=float(height),
                counts_for_query=False,
            ), rng)
        )

    floor_slots = [
        *FRONT_FLOOR_PROP_SLOTS,
        (-2.38, -1.95),
        (-1.15, -2.12),
        (0.18, -2.18),
        (1.48, -1.94),
        (2.48, -1.18),
        (-2.52, -0.35),
        (-1.08, -0.68),
        (0.62, -0.56),
        (1.98, -0.34),
        (-2.18, 1.08),
        (-0.62, 0.84),
        (1.02, 0.86),
        (2.34, 0.98),
    ]
    floor_specs: List[Dict[str, Any]] = []

    foreground_xy = tuple(float(value) for value in rng.choice(FRONT_FLOOR_PROP_SLOTS))
    floor_slots.remove(foreground_xy)
    foreground_shape = str(rng.choice(FRONT_FLOOR_PROP_SHAPES))
    floor_specs.append(
        _make_floor_prop(
            rng=rng,
            object_id=f"foreground_context_0_{foreground_shape}",
            prop_shape=str(foreground_shape),
            xy=(
                float(foreground_xy[0] + rng.uniform(-0.07, 0.07)),
                float(foreground_xy[1] + rng.uniform(-0.05, 0.05)),
            ),
        )
    )

    rng.shuffle(floor_slots)

    surface_shapes = list(SURFACE_PROP_SHAPES_BY_SCENE.get(str(scene_variant), SURFACE_PROP_SHAPES_BY_SCENE["studio_room"]))
    rng.shuffle(surface_shapes)
    surface_prop_count = min(len(surface_shapes), 3)
    for index in range(int(surface_prop_count)):
        xy = floor_slots.pop()
        prop_shape = str(surface_shapes[index])
        floor_specs.append(
            _make_floor_prop(
                rng=rng,
                object_id=f"surface_context_{index}_{prop_shape}",
                prop_shape=str(prop_shape),
                xy=(float(xy[0] + rng.uniform(-0.08, 0.08)), float(xy[1] + rng.uniform(-0.08, 0.08))),
            )
        )

    support_specs = [spec for spec in floor_specs if str(spec.get("object_type")) in set(SURFACE_PROP_TYPES)]
    same_type_distractors = int(rng.randint(1, 3))
    for index in range(int(same_type_distractors)):
        compatible_supports = [spec for spec in support_specs if _support_can_hold(str(target_type), spec)]
        if str(target_type) in set(SURFACE_DISTRACTOR_TYPES) and compatible_supports:
            rng.shuffle(compatible_supports)
            support = compatible_supports[index % len(compatible_supports)]
            floor_specs.append(
                _surface_distractor_for_type(
                    rng=rng,
                    object_id=f"surface_same_type_{index}_{target_type}",
                    object_type=str(target_type),
                    support_spec=support,
                )
            )
        else:
            xy = floor_slots.pop()
            floor_specs.append(
                _floor_distractor_for_type(
                    rng=rng,
                    object_id=f"floor_same_type_{index}_{target_type}",
                    object_type=str(target_type),
                    xy=(float(xy[0] + rng.uniform(-0.08, 0.08)), float(xy[1] + rng.uniform(-0.08, 0.08))),
                )
            )

    prop_shapes = [shape for shape in FLOOR_PROP_SHAPES if str(shape) not in set(SURFACE_PROP_TYPES)]
    rng.shuffle(prop_shapes)
    floor_prop_count = int(rng.randint(4, 6))
    for index in range(int(floor_prop_count)):
        xy = floor_slots.pop()
        prop_shape = str(prop_shapes[index % len(prop_shapes)])
        floor_specs.append(
            _make_floor_prop(
                rng=rng,
                object_id=f"floor_context_{index}_{prop_shape}",
                prop_shape=str(prop_shape),
                xy=(float(xy[0] + rng.uniform(-0.08, 0.08)), float(xy[1] + rng.uniform(-0.08, 0.08))),
            )
        )

    all_reference_points: List[Tuple[float, float, float]] = [
        (-WALL_X, ROOM_FRONT_Y, 0.0),
        (WALL_X, ROOM_FRONT_Y, 0.0),
        (-WALL_X, WALL_BACK_Y, 0.0),
        (WALL_X, WALL_BACK_Y, 0.0),
        (-WALL_X, WALL_BACK_Y, ROOM_HEIGHT),
        (WALL_X, WALL_BACK_Y, ROOM_HEIGHT),
        (-WALL_X, ROOM_FRONT_Y, ROOM_HEIGHT),
        (WALL_X, ROOM_FRONT_Y, ROOM_HEIGHT),
    ]
    for spec in selected_wall_specs:
        all_reference_points.extend(_wall_reference_points(spec))
    for spec in floor_specs:
        all_reference_points.extend(object_reference_points(spec))

    frame = build_projection_frame(camera=camera, render_params=render_params, point_worlds=all_reference_points)
    finalized_wall = _finalize_specs(selected_wall_specs, camera=camera, frame=frame)
    finalized_floor = _finalize_specs(floor_specs, camera=camera, frame=frame)
    all_finalized = [*finalized_wall, *finalized_floor]
    target_specs = [
        spec
        for spec in finalized_wall
        if bool(spec.get("counts_for_query")) and str(spec.get("object_type")) == str(target_type)
    ]
    if len(target_specs) != int(target_count):
        raise ValueError("target count mismatch")

    object_type_counts = Counter(str(spec["object_type"]) for spec in all_finalized)
    wall_object_type_counts = Counter(str(spec["object_type"]) for spec in finalized_wall)
    floor_object_type_counts = Counter(str(spec["object_type"]) for spec in finalized_floor)
    same_type_floor_distractor_count = int(sum(1 for spec in finalized_floor if str(spec["object_type"]) == str(target_type)))
    same_type_surface_distractor_count = int(
        sum(1 for spec in finalized_floor if str(spec["object_type"]) == str(target_type) and str(spec.get("mounting")) == "on_furniture")
    )
    support_surface_count = int(sum(1 for spec in finalized_floor if str(spec.get("object_type")) in set(SURFACE_PROP_TYPES)))
    sorted_targets = sorted(
        target_specs,
        key=lambda spec: (str(spec.get("wall", "")), float(spec["base_xyz"][2]), float(spec["world_xyz"][0]), float(spec["world_xyz"][1])),
    )
    return {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "target_object_type": str(target_type),
        "target_object_name": _object_name(str(target_type)),
        "target_object_plural": _object_plural(str(target_type)),
        "target_count": int(target_count),
        "wall_object_specs": list(sorted(finalized_wall, key=lambda spec: str(spec["object_id"]))),
        "floor_object_specs": list(sorted(finalized_floor, key=lambda spec: str(spec["object_id"]))),
        "object_specs": list(sorted(all_finalized, key=lambda spec: str(spec["object_id"]))),
        "target_object_ids": [str(spec["object_id"]) for spec in sorted_targets],
        "object_count": int(len(all_finalized)),
        "wall_object_count": int(len(finalized_wall)),
        "floor_object_count": int(len(finalized_floor)),
        "same_type_floor_distractor_count": int(same_type_floor_distractor_count),
        "same_type_surface_distractor_count": int(same_type_surface_distractor_count),
        "support_surface_count": int(support_surface_count),
        "object_type_counts": dict(sorted(object_type_counts.items())),
        "wall_object_type_counts": dict(sorted(wall_object_type_counts.items())),
        "floor_object_type_counts": dict(sorted(floor_object_type_counts.items())),
        "camera": {
            "camera_position": [round(float(value), 4) for value in camera.camera_position],
            "target": [round(float(value), 4) for value in camera.target],
            "yaw_degrees": round(float(camera.yaw_degrees), 4),
            "yaw_band_degrees": [round(float(value), 4) for value in ROOM_VIEW_YAW_BANDS[str(scene_variant)]],
            "pitch_degrees": round(float(camera.pitch_degrees), 4),
            "distance": round(float(camera.distance), 4),
            "right": [round(float(value), 5) for value in camera.right],
            "up": [round(float(value), 5) for value in camera.up],
            "forward": [round(float(value), 5) for value in camera.forward],
        },
        "projection_frame": {
            "scale": round(float(frame.scale), 5),
            "center_x": round(float(frame.center_x), 3),
            "center_y": round(float(frame.center_y), 3),
            "normalized_center_u": round(float(frame.normalized_center_u), 6),
            "normalized_center_v": round(float(frame.normalized_center_v), 6),
        },
        "solver_trace": {
            "predicate": "object_type == target_object_type and is_wall_mounted",
            "target_object_type": str(target_type),
            "target_object_ids": [str(spec["object_id"]) for spec in sorted_targets],
            "target_count": int(target_count),
            "same_type_floor_distractor_count": int(same_type_floor_distractor_count),
            "same_type_surface_distractor_count": int(same_type_surface_distractor_count),
            "support_surface_count": int(support_surface_count),
            "wall_object_type_counts": dict(sorted(wall_object_type_counts.items())),
            "floor_object_type_counts": dict(sorted(floor_object_type_counts.items())),
            "unique_count_answer": True,
        },
    }

__all__ = ["_resolve_target_count", "_build_room_dataset"]
