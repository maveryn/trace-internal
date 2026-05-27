"""Wall-side relation label task for wall-mounted objects in a 3D room."""

from __future__ import annotations

from collections import Counter
import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import (
    get_domain_defaults,
    get_task_group_defaults,
    resolve_task_group_section_defaults,
)
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import (
    resolve_selection_index,
    uniform_probability_map,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.object_resources import ROOM_SIDE_RELATION_REFERENCE_OBJECT_TYPE
from ..spatial.camera_distance import POINT_LABELS, _bbox_intersection_area
from .wall_mounted_object_count import (
    ROOM_FRONT_Y,
    ROOM_HEIGHT,
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    WALL_BACK_Y,
    WALL_X,
    _build_projection_frame,
    _finalize_specs,
    _object_reference_points,
    _resolve_render_params,
    _room_object_bbox,
    _sample_room_camera,
    _wall_object_visible_bbox,
    _wall_reference_points,
    render_room_scene_3d,
)
from .wall_object_camera_distance import (
    CANDIDATE_WALL_OBJECT_TYPES,
    CONTEXT_WALL_OBJECT_TYPES,
    CONTEXT_WALL_SLOTS,
    ROOM_CAMERA_DISTANCE_YAW_BANDS,
    _build_floor_context,
    _candidate_wall_visibility_ok,
    _wall_spec_for_type,
)

TASK_ID = "task_three_d__room__wall_object_side_relation_label"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "left_of_reference_on_wall",
    "right_of_reference_on_wall",
)
REFERENCE_OBJECT_TYPE = ROOM_SIDE_RELATION_REFERENCE_OBJECT_TYPE
REFERENCE_WALL_SLOTS: Dict[str, Tuple[Tuple[float, float], ...]] = {
    "back": ((-0.95, 1.78),),
    "left": ((-0.95, 1.78),),
    "right": ((-0.05, 1.78),),
}
ANSWER_SLOTS_BY_QUERY_AND_WALL: Dict[str, Dict[str, Tuple[Tuple[float, float], ...]]] = {
    "left_of_reference_on_wall": {
        "back": ((-2.22, 1.24), (-2.02, 2.18)),
        "left": ((-2.20, 1.24), (-2.00, 2.18)),
        "right": ((1.10, 1.24), (1.88, 2.18)),
    },
    "right_of_reference_on_wall": {
        "back": ((0.42, 1.24), (1.16, 2.18)),
        "left": ((0.36, 1.24), (1.42, 2.18)),
        "right": ((-1.18, 1.24), (-1.88, 2.18)),
    },
}
DISTRACTOR_SLOTS_BY_QUERY_AND_WALL: Dict[str, Dict[str, Tuple[Tuple[float, float], ...]]] = {
    "left_of_reference_on_wall": {
        "back": ((-0.28, 1.20), (0.42, 2.14), (1.14, 1.30), (1.88, 2.02)),
        "left": ((-0.28, 1.20), (0.36, 2.14), (0.96, 1.32), (1.42, 2.02)),
        "right": ((-2.46, 1.20), (-1.82, 2.12), (-1.20, 1.32), (-0.58, 2.02)),
    },
    "right_of_reference_on_wall": {
        "back": ((-2.85, 1.20), (-2.30, 2.12), (-1.75, 1.32), (-1.30, 2.02)),
        "left": ((-2.70, 1.20), (-2.20, 2.12), (-1.70, 1.32), (-1.28, 2.02)),
        "right": ((0.58, 1.20), (1.10, 2.12), (1.62, 1.32), (2.18, 2.02)),
    },
}
REFERENCE_WALL_OBJECT_SIZE_SCALE = 1.28
SIDE_RELATION_LETTERED_WALL_OBJECT_SIZE_SCALE = 1.55
SIDE_RELATION_SCREEN_MIN_CENTER_DISTANCE_PX = 34.0
SIDE_RELATION_SCREEN_MAX_INTERSECTION_AREA_PX = 6500.0






def _resolve_choice(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    key: str,
    support: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    values = tuple(str(value) for value in support)
    explicit = params.get(str(key))
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(values):
            raise ValueError(f"unsupported {key}: {selected}")
        return selected, {
            value: (1.0 if value == selected else 0.0) for value in values
        }
    selection_index = resolve_selection_index(
        params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.{key}"
    )
    selected = values[abs(int(selection_index)) % len(values)]
    probability = round(1.0 / float(len(values)), 8)
    return selected, {value: probability for value in values}




def _reference_slot(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    reference_wall: str,
) -> Tuple[float, float]:
    slots = tuple(REFERENCE_WALL_SLOTS[str(reference_wall)])
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.reference_slot",
    )
    hpos, z = slots[abs(int(selection_index)) % len(slots)]
    return float(hpos), float(z)


def _candidate_slots(
    *,
    rng,
    candidate_count: int,
    reference_wall: str,
    query_variant: str,
) -> List[Tuple[str, float, float, bool]]:
    answer_slots = list(
        ANSWER_SLOTS_BY_QUERY_AND_WALL[str(query_variant)][str(reference_wall)]
    )
    distractor_slots = list(
        DISTRACTOR_SLOTS_BY_QUERY_AND_WALL[str(query_variant)][str(reference_wall)]
    )
    rng.shuffle(answer_slots)
    rng.shuffle(distractor_slots)
    if int(candidate_count) - 1 > len(distractor_slots):
        raise ValueError("could not sample enough same-wall distractors")
    answer_hpos, answer_z = answer_slots[0]
    slots: List[Tuple[str, float, float, bool]] = [
        (str(reference_wall), float(answer_hpos), float(answer_z), True)
    ]
    slots.extend(
        (str(reference_wall), float(hpos), float(z), False)
        for hpos, z in distractor_slots[: max(0, int(candidate_count) - 1)]
    )
    if len(slots) < int(candidate_count):
        raise ValueError("could not sample enough wall-side candidates")
    rng.shuffle(slots)
    return list(slots[: int(candidate_count)])


def _sample_candidate_types(
    *,
    rng,
    candidate_count: int,
) -> List[str]:
    candidate_types = [
        str(item)
        for item in CANDIDATE_WALL_OBJECT_TYPES
        if str(item) != REFERENCE_OBJECT_TYPE
    ]
    if int(candidate_count) > len(candidate_types):
        raise ValueError("not enough unique candidate wall object types")
    rng.shuffle(candidate_types)
    return list(candidate_types[: int(candidate_count)])


def _build_context_wall_specs(
    *,
    rng,
    context_wall_count: int,
    excluded_wall: str,
) -> List[Dict[str, Any]]:
    context_types = [str(item) for item in CONTEXT_WALL_OBJECT_TYPES]
    rng.shuffle(context_types)
    context_slots = [
        slot for slot in CONTEXT_WALL_SLOTS if str(slot[0]) != str(excluded_wall)
    ]
    rng.shuffle(context_slots)
    specs: List[Dict[str, Any]] = []
    for index in range(int(context_wall_count)):
        wall, hpos, z = context_slots[index % len(context_slots)]
        object_type = str(context_types[index % len(context_types)])
        specs.append(
            _wall_spec_for_type(
                rng=rng,
                object_id=f"context_wall_object_{index}_{object_type}",
                object_type=str(object_type),
                wall=str(wall),
                hpos=float(hpos),
                z=float(z),
                counts_for_query=False,
            )
        )
    return list(specs)


def _wall_axis_hpos(spec: Mapping[str, Any]) -> float:
    world = spec.get("world_xyz", (0.0, 0.0, 0.0))
    if str(spec.get("wall")) == "back":
        return float(world[0])
    return float(world[1])


def _wall_left_coordinate(wall: str, hpos: float) -> float:
    if str(wall) == "right":
        return float(hpos)
    return -float(hpos)


def _is_left_of_reference_on_wall(
    spec: Mapping[str, Any],
    reference_spec: Mapping[str, Any],
    *,
    margin: float = 0.28,
) -> bool:
    if str(spec.get("wall")) != str(reference_spec.get("wall")):
        return False
    wall = str(reference_spec["wall"])
    candidate_coord = _wall_left_coordinate(wall, _wall_axis_hpos(spec))
    reference_coord = _wall_left_coordinate(wall, _wall_axis_hpos(reference_spec))
    return bool(candidate_coord > reference_coord + float(margin))


def _is_right_of_reference_on_wall(
    spec: Mapping[str, Any],
    reference_spec: Mapping[str, Any],
    *,
    margin: float = 0.28,
) -> bool:
    if str(spec.get("wall")) != str(reference_spec.get("wall")):
        return False
    wall = str(reference_spec["wall"])
    candidate_coord = _wall_left_coordinate(wall, _wall_axis_hpos(spec))
    reference_coord = _wall_left_coordinate(wall, _wall_axis_hpos(reference_spec))
    return bool(candidate_coord < reference_coord - float(margin))


def _is_selected_side_of_reference_on_wall(
    spec: Mapping[str, Any],
    reference_spec: Mapping[str, Any],
    *,
    query_variant: str,
) -> bool:
    if str(query_variant) == "left_of_reference_on_wall":
        return _is_left_of_reference_on_wall(spec, reference_spec)
    if str(query_variant) == "right_of_reference_on_wall":
        return _is_right_of_reference_on_wall(spec, reference_spec)
    raise ValueError(f"unsupported side-relation query variant: {query_variant}")


def _side_relation_screen_separation_ok(
    candidate_specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
) -> bool:
    bboxes = [_room_object_bbox(spec, camera, frame) for spec in candidate_specs]
    centers = [
        (float(spec["screen_xy"][0]), float(spec["screen_xy"][1]))
        for spec in candidate_specs
    ]
    for index, bbox in enumerate(bboxes):
        for other_index in range(index + 1, len(bboxes)):
            center_distance = math.hypot(
                centers[index][0] - centers[other_index][0],
                centers[index][1] - centers[other_index][1],
            )
            if center_distance < SIDE_RELATION_SCREEN_MIN_CENTER_DISTANCE_PX:
                return False
            if (
                _bbox_intersection_area(bbox, bboxes[other_index])
                > SIDE_RELATION_SCREEN_MAX_INTERSECTION_AREA_PX
            ):
                return False
    return True


def _build_room_wall_side_relation_dataset(
    *,
    params: Mapping[str, Any],
    query_variant: str,
    scene_variant: str,
    candidate_count: int,
    context_wall_count: int,
    floor_context_count: int,
    reference_wall: str,
    render_params,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    reference_hpos, reference_z = _reference_slot(
        params={},
        instance_seed=int(instance_seed),
        reference_wall=str(reference_wall),
    )
    for _attempt in range(420):
        camera = _sample_room_camera(
            rng,
            scene_variant=str(scene_variant),
            yaw_band_degrees=tuple(
                float(value)
                for value in ROOM_CAMERA_DISTANCE_YAW_BANDS[str(scene_variant)]
            ),
        )
        reference_spec = _wall_spec_for_type(
            rng=rng,
            object_id=f"reference_wall_object_{REFERENCE_OBJECT_TYPE}",
            object_type=REFERENCE_OBJECT_TYPE,
            wall=str(reference_wall),
            hpos=float(reference_hpos),
            z=float(reference_z),
            counts_for_query=False,
            size_scale=REFERENCE_WALL_OBJECT_SIZE_SCALE,
        )
        reference_spec["is_named_reference"] = True
        candidate_types = _sample_candidate_types(
            rng=rng,
            candidate_count=int(candidate_count),
        )
        slots = _candidate_slots(
            rng=rng,
            candidate_count=int(candidate_count),
            reference_wall=str(reference_wall),
            query_variant=str(query_variant),
        )
        candidate_wall_specs: List[Dict[str, Any]] = []
        for index, (wall, hpos, z, intended_answer) in enumerate(slots):
            object_type = str(candidate_types[index])
            spec = _wall_spec_for_type(
                rng=rng,
                object_id=f"candidate_wall_object_{index}_{object_type}",
                object_type=str(object_type),
                wall=str(wall),
                hpos=float(hpos),
                z=float(z),
                counts_for_query=True,
                size_scale=SIDE_RELATION_LETTERED_WALL_OBJECT_SIZE_SCALE,
            )
            spec["is_answer_candidate"] = True
            spec["intended_side_relation"] = bool(intended_answer)
            spec["intended_left_of_reference"] = bool(
                str(query_variant) == "left_of_reference_on_wall" and intended_answer
            )
            spec["intended_right_of_reference"] = bool(
                str(query_variant) == "right_of_reference_on_wall" and intended_answer
            )
            candidate_wall_specs.append(spec)

        context_wall_specs = _build_context_wall_specs(
            rng=rng,
            context_wall_count=int(context_wall_count),
            excluded_wall=str(reference_wall),
        )
        floor_specs = _build_floor_context(
            rng=rng,
            scene_variant=str(scene_variant),
            floor_context_count=int(floor_context_count),
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
        for spec in [reference_spec, *candidate_wall_specs, *context_wall_specs]:
            all_reference_points.extend(_wall_reference_points(spec))
        for spec in floor_specs:
            all_reference_points.extend(_object_reference_points(spec))

        frame = _build_projection_frame(
            camera=camera,
            render_params=render_params,
            point_worlds=all_reference_points,
        )
        finalized_reference = _finalize_specs(
            [reference_spec], camera=camera, frame=frame
        )[0]
        finalized_candidates = _finalize_specs(
            candidate_wall_specs, camera=camera, frame=frame
        )
        finalized_context_wall = _finalize_specs(
            context_wall_specs, camera=camera, frame=frame
        )
        finalized_floor = _finalize_specs(floor_specs, camera=camera, frame=frame)
        if not _candidate_wall_visibility_ok(
            [finalized_reference, *finalized_candidates],
            camera=camera,
            frame=frame,
        ):
            continue
        if not _side_relation_screen_separation_ok(
            [finalized_reference, *finalized_candidates],
            camera=camera,
            frame=frame,
        ):
            continue

        satisfying = [
            spec
            for spec in finalized_candidates
            if _is_selected_side_of_reference_on_wall(
                spec,
                finalized_reference,
                query_variant=str(query_variant),
            )
        ]
        if len(satisfying) != 1:
            continue
        answer_object_id = str(satisfying[0]["object_id"])
        answer_label_index = abs(
            int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}.answer_label",
                )
            )
        ) % int(candidate_count)
        answer_label = str(POINT_LABELS[int(answer_label_index)])
        remaining_labels = [
            str(label)
            for label in POINT_LABELS[: int(candidate_count)]
            if str(label) != str(answer_label)
        ]
        rng.shuffle(remaining_labels)
        relabeled_candidates: List[Dict[str, Any]] = []
        for spec in finalized_candidates:
            updated = dict(spec)
            label = (
                str(answer_label)
                if str(updated["object_id"]) == answer_object_id
                else str(remaining_labels.pop())
            )
            updated.update(
                {
                    "object_id": f"wall_object_{label}",
                    "point_id": f"wall_object_{label}",
                    "point_label": str(label),
                    "object_label": str(label),
                    "is_answer_candidate": True,
                }
            )
            relabeled_candidates.append(updated)

        answer_spec = next(
            spec
            for spec in relabeled_candidates
            if str(spec["point_label"]) == str(answer_label)
        )
        finalized_wall = [
            finalized_reference,
            *relabeled_candidates,
            *finalized_context_wall,
        ]
        all_finalized = [*finalized_wall, *finalized_floor]
        reference_prompt_name = str(finalized_reference["prompt_name"])
        reference_prompt_name_count = sum(
            1
            for spec in all_finalized
            if str(spec.get("prompt_name")) == reference_prompt_name
        )
        if int(reference_prompt_name_count) != 1:
            continue
        wall_object_type_counts = Counter(
            str(spec["object_type"]) for spec in finalized_wall
        )
        floor_object_type_counts = Counter(
            str(spec["object_type"]) for spec in finalized_floor
        )
        object_type_counts = Counter(str(spec["object_type"]) for spec in all_finalized)
        left_relation_flags = {
            str(spec["point_label"]): _is_left_of_reference_on_wall(
                spec, finalized_reference
            )
            for spec in relabeled_candidates
        }
        right_relation_flags = {
            str(spec["point_label"]): _is_right_of_reference_on_wall(
                spec, finalized_reference
            )
            for spec in relabeled_candidates
        }
        selected_relation_flags = (
            left_relation_flags
            if str(query_variant) == "left_of_reference_on_wall"
            else right_relation_flags
        )
        candidate_walls = {
            str(spec["point_label"]): str(spec["wall"]) for spec in relabeled_candidates
        }
        candidate_wall_hpos = {
            str(spec["point_label"]): round(float(_wall_axis_hpos(spec)), 4)
            for spec in relabeled_candidates
        }
        candidate_wall_left_coordinates = {
            str(spec["point_label"]): round(
                float(_wall_left_coordinate(str(spec["wall"]), _wall_axis_hpos(spec))),
                4,
            )
            for spec in relabeled_candidates
        }
        candidate_projected_bboxes = {
            str(spec["point_label"]): [
                round(float(value), 3)
                for value in _room_object_bbox(spec, camera, frame)
            ]
            for spec in relabeled_candidates
        }
        candidate_visible_bboxes = {
            str(spec["point_label"]): [
                round(float(value), 3)
                for value in _wall_object_visible_bbox(spec, camera, frame)
            ]
            for spec in relabeled_candidates
        }
        reference_bbox = [
            round(float(value), 3)
            for value in _room_object_bbox(finalized_reference, camera, frame)
        ]
        return {
            "query_variant": str(query_variant),
            "scene_variant": str(scene_variant),
            "candidate_count": int(candidate_count),
            "context_wall_count": int(context_wall_count),
            "floor_context_count": int(floor_context_count),
            "reference_object": {
                "object_id": str(finalized_reference["object_id"]),
                "object_type": str(finalized_reference["object_type"]),
                "prompt_name": reference_prompt_name,
                "wall": str(finalized_reference["wall"]),
                "wall_axis_hpos": round(float(_wall_axis_hpos(finalized_reference)), 4),
                "wall_left_coordinate": round(
                    float(
                        _wall_left_coordinate(
                            str(finalized_reference["wall"]),
                            _wall_axis_hpos(finalized_reference),
                        )
                    ),
                    4,
                ),
                "world_xyz": list(finalized_reference["world_xyz"]),
                "screen_xy": list(finalized_reference["screen_xy"]),
                "bbox_px": list(reference_bbox),
                "prompt_name_count": int(reference_prompt_name_count),
            },
            "wall_object_specs": list(
                sorted(finalized_wall, key=lambda spec: str(spec["object_id"]))
            ),
            "floor_object_specs": list(
                sorted(finalized_floor, key=lambda spec: str(spec["object_id"]))
            ),
            "object_specs": list(
                sorted(all_finalized, key=lambda spec: str(spec["object_id"]))
            ),
            "candidate_object_specs": list(
                sorted(relabeled_candidates, key=lambda spec: str(spec["point_label"]))
            ),
            "target_object_ids": [str(answer_spec["object_id"])],
            "answer_label": str(answer_label),
            "answer_object_id": str(answer_spec["object_id"]),
            "answer_object_type": str(answer_spec["object_type"]),
            "answer_wall": str(answer_spec["wall"]),
            "left_of_reference_on_wall_by_label": dict(
                sorted(left_relation_flags.items())
            ),
            "right_of_reference_on_wall_by_label": dict(
                sorted(right_relation_flags.items())
            ),
            "selected_side_relation_by_label": dict(
                sorted(selected_relation_flags.items())
            ),
            "candidate_walls_by_label": dict(sorted(candidate_walls.items())),
            "candidate_wall_hpos_by_label": dict(sorted(candidate_wall_hpos.items())),
            "candidate_wall_left_coordinates_by_label": dict(
                sorted(candidate_wall_left_coordinates.items())
            ),
            "candidate_projected_bboxes_by_label": dict(
                sorted(candidate_projected_bboxes.items())
            ),
            "candidate_visible_bboxes_by_label": dict(
                sorted(candidate_visible_bboxes.items())
            ),
            "wall_object_count": int(len(finalized_wall)),
            "floor_object_count": int(len(finalized_floor)),
            "object_count": int(len(all_finalized)),
            "object_type_counts": dict(sorted(object_type_counts.items())),
            "wall_object_type_counts": dict(sorted(wall_object_type_counts.items())),
            "floor_object_type_counts": dict(sorted(floor_object_type_counts.items())),
            "camera": {
                "camera_position": [
                    round(float(value), 4) for value in camera.camera_position
                ],
                "target": [round(float(value), 4) for value in camera.target],
                "yaw_degrees": round(float(camera.yaw_degrees), 4),
                "yaw_band_degrees": [
                    round(float(value), 4)
                    for value in ROOM_CAMERA_DISTANCE_YAW_BANDS[str(scene_variant)]
                ],
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
                "predicate": (
                    "lettered wall-mounted candidate with wall-left coordinate "
                    + (
                        "greater than"
                        if str(query_variant) == "left_of_reference_on_wall"
                        else "less than"
                    )
                    + " the unlettered TV reference on the same wall"
                ),
                "reference_object": {
                    "object_id": str(finalized_reference["object_id"]),
                    "object_type": str(finalized_reference["object_type"]),
                    "prompt_name": reference_prompt_name,
                    "wall": str(finalized_reference["wall"]),
                    "prompt_name_count": int(reference_prompt_name_count),
                    "wall_axis_hpos": round(
                        float(_wall_axis_hpos(finalized_reference)), 4
                    ),
                    "wall_left_coordinate": round(
                        float(
                            _wall_left_coordinate(
                                str(finalized_reference["wall"]),
                                _wall_axis_hpos(finalized_reference),
                            )
                        ),
                        4,
                    ),
                },
                "left_of_reference_on_wall_by_label": dict(
                    sorted(left_relation_flags.items())
                ),
                "right_of_reference_on_wall_by_label": dict(
                    sorted(right_relation_flags.items())
                ),
                "selected_side_relation_by_label": dict(
                    sorted(selected_relation_flags.items())
                ),
                "candidate_walls_by_label": dict(sorted(candidate_walls.items())),
                "candidate_wall_hpos_by_label": dict(
                    sorted(candidate_wall_hpos.items())
                ),
                "candidate_wall_left_coordinates_by_label": dict(
                    sorted(candidate_wall_left_coordinates.items())
                ),
                "answer_label": str(answer_label),
                "answer_object_id": str(answer_spec["object_id"]),
                "answer_wall": str(answer_spec["wall"]),
                "unique_answer": True,
            },
        }
    raise ValueError(
        "could not construct a room side-relation scene with a unique visible answer"
    )


def _build_complexity(
    *,
    candidate_count: int,
    wall_object_count: int,
    floor_object_count: int,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.34)),
        "wall_plane_ordering": float(raw_weights.get("wall_plane_ordering", 0.42)),
        "reference_binding": float(raw_weights.get("reference_binding", 0.18)),
        "ambiguity": float(raw_weights.get("ambiguity", 0.10)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(
            float(wall_object_count + floor_object_count), 12.0, 19.0
        ),
        "wall_plane_ordering": _normalize_unit(float(candidate_count), 4.0, 5.0),
        "reference_binding": 0.72,
        "ambiguity": 0.42,
    }
    score = sum(
        float(components[key]) * max(0.0, float(weights[key])) for key in weights
    ) / float(total)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            key: round(float(value), 6) for key, value in components.items()
        },
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "room")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=TASK_ID,
    )
)
_COMPLEXITY_DEFAULTS = resolve_task_group_section_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    "complexity",
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = (
    _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
)
_BACKGROUND_DEFAULTS = (
    _VISUAL_DEFAULTS.get("background", {})
    if isinstance(_VISUAL_DEFAULTS, Mapping)
    else {}
)
_NOISE_DEFAULTS = (
    _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
)


@register_task
class ThreeDRoomWallObjectSideRelationLabelTask:
    """Choose the lettered wall object left or right of an unlettered TV."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "room"
    default_dataset_enabled = True

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(
                    spawn_rng(
                        int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}"
                    ).randrange(1, 2**62)
                )
            )
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(
            f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}"
        )

    def _generate_once(
        self, instance_seed: int, *, params: Dict[str, Any]
    ) -> TaskOutput:
        query_variant, query_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_QUERY_VARIANTS,
            explicit_key="query_variant",
            weights_key="query_variant_weights",
            balance_flag_key="balanced_query_variant_sampling",
            axis_namespace="query_variant",
        )
        scene_variant, scene_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        candidate_count, candidate_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="candidate_count",
            default_min=5,
            default_max=5,
            lower=4,
            upper=5,
        )
        context_wall_count, context_wall_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="context_wall_count",
            default_min=4,
            default_max=4,
            lower=2,
            upper=6,
        )
        floor_context_count, floor_context_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="floor_context_count",
            default_min=6,
            default_max=6,
            lower=3,
            upper=8,
        )
        reference_wall, reference_wall_probabilities = _resolve_choice(
            params,
            instance_seed=int(instance_seed),
            key="reference_wall",
            support=("back", "left", "right"),
        )
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_room_wall_side_relation_dataset(
            params=params,
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            candidate_count=int(candidate_count),
            context_wall_count=int(context_wall_count),
            floor_context_count=int(floor_context_count),
            reference_wall=str(reference_wall),
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_room_scene_3d(
            background, dataset=dataset, render_params=render_params
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "answer_hint",
                "evidence_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        reference_name = str(dataset["reference_object"]["prompt_name"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "reference_name": reference_name,
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(
                    prompt_defaults["json_output_contract_answer_only"]
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(
                    prompt_defaults["json_example_answer_only"]
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_label = str(dataset["answer_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in rendered_scene.evidence_bboxes
        ]
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        complexity = _build_complexity(
            candidate_count=int(dataset["candidate_count"]),
            wall_object_count=int(dataset["wall_object_count"]),
            floor_object_count=int(dataset["floor_object_count"]),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )
        solver_trace = dict(dataset["solver_trace"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_room_scene",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "candidate_count": int(dataset["candidate_count"]),
                    "context_wall_count": int(dataset["context_wall_count"]),
                    "floor_context_count": int(dataset["floor_context_count"]),
                    "wall_object_count": int(dataset["wall_object_count"]),
                    "floor_object_count": int(dataset["floor_object_count"]),
                    "object_count": int(dataset["object_count"]),
                    "reference_object": dict(dataset["reference_object"]),
                    "left_of_reference_on_wall_by_label": dict(
                        dataset["left_of_reference_on_wall_by_label"]
                    ),
                    "right_of_reference_on_wall_by_label": dict(
                        dataset["right_of_reference_on_wall_by_label"]
                    ),
                    "selected_side_relation_by_label": dict(
                        dataset["selected_side_relation_by_label"]
                    ),
                    "candidate_walls_by_label": dict(
                        dataset["candidate_walls_by_label"]
                    ),
                    "candidate_wall_hpos_by_label": dict(
                        dataset["candidate_wall_hpos_by_label"]
                    ),
                    "candidate_wall_left_coordinates_by_label": dict(
                        dataset["candidate_wall_left_coordinates_by_label"]
                    ),
                    "candidate_visible_bboxes_by_label": dict(
                        dataset["candidate_visible_bboxes_by_label"]
                    ),
                    "answer_label": str(answer_label),
                    "answer_object_id": str(dataset["answer_object_id"]),
                    "view_family": "synthetic_perspective_3d_room",
                },
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(
                    prompt_artifacts.prompt_variant_active_key
                ),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "query_variant_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probabilities),
                    "candidate_count": int(candidate_count),
                    "candidate_count_probabilities": dict(
                        candidate_count_probabilities
                    ),
                    "context_wall_count": int(context_wall_count),
                    "context_wall_count_probabilities": dict(
                        context_wall_count_probabilities
                    ),
                    "floor_context_count": int(floor_context_count),
                    "floor_context_count_probabilities": dict(
                        floor_context_count_probabilities
                    ),
                    "reference_wall": str(reference_wall),
                    "reference_wall_probabilities": dict(reference_wall_probabilities),
                    "reference_object_type": REFERENCE_OBJECT_TYPE,
                    "reference_name": str(reference_name),
                    "object_count": int(dataset["object_count"]),
                    "answer_label_probabilities": {
                        str(label): round(1.0 / float(candidate_count), 8)
                        for label in POINT_LABELS[: int(candidate_count)]
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "label_font_size_px": int(render_params.label_font_size_px),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "room_bbox_px": list(rendered_scene.room_bbox_px),
                "object_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.object_bboxes_px.items()
                },
                "object_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.object_centers_px.items()
                },
                "wall_object_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.wall_object_bboxes_px.items()
                },
                "wall_object_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.wall_object_centers_px.items()
                },
                "floor_object_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.floor_object_bboxes_px.items()
                },
                "floor_object_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.floor_object_centers_px.items()
                },
                "target_object_bboxes_px": {
                    str(key): list(rendered_scene.object_bboxes_px[str(key)])
                    for key in dataset["target_object_ids"]
                },
                "reference_object_bbox_px": list(
                    rendered_scene.object_bboxes_px[
                        str(dataset["reference_object"]["object_id"])
                    ]
                ),
            },
            "execution_trace": {
                "query_variant": "default",
                "query_id": str(query_variant),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "candidate_count": int(dataset["candidate_count"]),
                "context_wall_count": int(dataset["context_wall_count"]),
                "floor_context_count": int(dataset["floor_context_count"]),
                "answer_label": str(answer_label),
                "answer_object_id": str(dataset["answer_object_id"]),
                "answer_object_type": str(dataset["answer_object_type"]),
                "answer_wall": str(dataset["answer_wall"]),
                "target_object_ids": [
                    str(value) for value in dataset["target_object_ids"]
                ],
                "reference_object": dict(dataset["reference_object"]),
                "candidate_object_specs": [
                    dict(spec) for spec in dataset["candidate_object_specs"]
                ],
                "wall_object_specs": [
                    dict(spec) for spec in dataset["wall_object_specs"]
                ],
                "floor_object_specs": [
                    dict(spec) for spec in dataset["floor_object_specs"]
                ],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "object_count": int(dataset["object_count"]),
                "wall_object_count": int(dataset["wall_object_count"]),
                "floor_object_count": int(dataset["floor_object_count"]),
                "left_of_reference_on_wall_by_label": dict(
                    dataset["left_of_reference_on_wall_by_label"]
                ),
                "right_of_reference_on_wall_by_label": dict(
                    dataset["right_of_reference_on_wall_by_label"]
                ),
                "selected_side_relation_by_label": dict(
                    dataset["selected_side_relation_by_label"]
                ),
                "candidate_walls_by_label": dict(dataset["candidate_walls_by_label"]),
                "candidate_wall_hpos_by_label": dict(
                    dataset["candidate_wall_hpos_by_label"]
                ),
                "candidate_wall_left_coordinates_by_label": dict(
                    dataset["candidate_wall_left_coordinates_by_label"]
                ),
                "candidate_projected_bboxes_by_label": dict(
                    dataset["candidate_projected_bboxes_by_label"]
                ),
                "candidate_visible_bboxes_by_label": dict(
                    dataset["candidate_visible_bboxes_by_label"]
                ),
                "object_type_counts": dict(dataset["object_type_counts"]),
                "wall_object_type_counts": dict(dataset["wall_object_type_counts"]),
                "floor_object_type_counts": dict(dataset["floor_object_type_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_variant),
                "view_family": "synthetic_perspective_3d_room",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "object",
                "id": str(dataset["answer_object_id"]),
                "answer": str(answer_label),
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query_variant),
        )


__all__ = ["ThreeDRoomWallObjectSideRelationLabelTask"]
