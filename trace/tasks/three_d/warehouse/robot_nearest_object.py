"""Robot-to-reference nearest-object task for a synthetic 3D warehouse scene."""

from __future__ import annotations

import math
from collections import Counter
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
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.object_resources import (
    WAREHOUSE_NEAREST_OBJECT_CANDIDATE_TYPES,
    WAREHOUSE_NEAREST_REFERENCE_OBJECT_DIMENSIONS,
    WAREHOUSE_NEAREST_REFERENCE_OBJECT_NAME,
    WAREHOUSE_NEAREST_REFERENCE_OBJECT_RGB,
    WAREHOUSE_NEAREST_REFERENCE_OBJECT_TYPE,
)
from ..shared.object_scene import (
    POINT_LABELS,
    _bbox_intersection_area,
    _build_projection_frame,
    _canvas_floor_polygon_xy,
    _object_reference_points,
    _object_screen_bbox,
    _sample_camera,
)
from ..shared.option_panel import build_text_option_choices
from .warehouse_scene_common import (
    MAX_CANDIDATE_BBOX_INTERSECTION_PX,
    MIN_CANDIDATE_CENTER_SEPARATION_PX,
    MIN_CANDIDATE_VISIBLE_PX,
    ROBOT_ACCENT_COLORS,
    ROBOT_BASE_COLORS,
    SCENE_ID,
    SUPPORTED_ROBOT_DESIGNS,
    SUPPORTED_ROBOT_HEADINGS,
    SUPPORTED_SCENE_VARIANTS,
    WAREHOUSE_CAMERA_YAW_BANDS_DEGREES,
    _WarehouseRenderParams,
    _bbox_area,
    _dimensions_for_object,
    _finalize_specs,
    _heading_vector,
    _heading_axis,
    _local_to_world,
    _make_object_spec,
    _resolve_render_params,
    _sample_reference_and_objects,
)
from .warehouse_rendering import render_warehouse_robot_nearest_scene_3d


TASK_ID = "task_three_d__warehouse__nearest_candidate_to_reference_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("closest_robot_to_reference", "closest_object_to_robot")
SUPPORTED_AISLE_HEADINGS: Tuple[str, ...] = tuple(SUPPORTED_ROBOT_HEADINGS)
REFERENCE_OBJECT_TYPE = WAREHOUSE_NEAREST_REFERENCE_OBJECT_TYPE
REFERENCE_OBJECT_NAME = WAREHOUSE_NEAREST_REFERENCE_OBJECT_NAME
REFERENCE_OBJECT_RGB: Tuple[int, int, int] = WAREHOUSE_NEAREST_REFERENCE_OBJECT_RGB
MIN_NEAREST_ROBOT_MARGIN = 0.42
MIN_NEAREST_OBJECT_MARGIN = 0.42
MIN_REFERENCE_VISIBLE_PX = 26.0
OBJECT_CANDIDATE_TYPES: Tuple[str, ...] = WAREHOUSE_NEAREST_OBJECT_CANDIDATE_TYPES






def _resolve_camera_yaw_band(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[Tuple[float, float], Dict[str, float], int]:
    support = tuple(range(len(WAREHOUSE_CAMERA_YAW_BANDS_DEGREES)))
    explicit = params.get("camera_yaw_band_index")
    locked = params.get("_locked_camera_yaw_band_index")
    if explicit is not None:
        selected = int(explicit)
    elif locked is not None:
        selected = int(locked)
    else:
        selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.camera_yaw_band_index")
        selected = int(support[abs(int(selection_index)) % len(support)])
    if int(selected) not in set(support):
        raise ValueError(f"unsupported camera_yaw_band_index: {selected}")
    probabilities = dict(uniform_probability_map(support, selected=int(selected) if explicit is not None else None))
    return (
        tuple(float(value) for value in WAREHOUSE_CAMERA_YAW_BANDS_DEGREES[int(selected)]),
        {str(key): float(value) for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))},
        int(selected),
    )


def _surface_gap(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    ax, ay, _az = (float(value) for value in a["world_xyz"])
    bx, by, _bz = (float(value) for value in b["world_xyz"])
    center_distance_xy = math.hypot(float(ax - bx), float(ay - by))
    return max(0.0, float(center_distance_xy) - float(a["footprint_radius"]) - float(b["footprint_radius"]))


def _can_place(candidate: Mapping[str, Any], placed: Sequence[Mapping[str, Any]], *, clearance: float = 0.16) -> bool:
    for item in placed:
        cx, cy, _cz = (float(value) for value in candidate["world_xyz"])
        ix, iy, _iz = (float(value) for value in item["world_xyz"])
        min_distance = float(candidate["footprint_radius"]) + float(item["footprint_radius"]) + float(clearance)
        if math.hypot(float(cx - ix), float(cy - iy)) < min_distance:
            return False
    return True


def _heading_towards(source_xy: Sequence[float], target_xy: Sequence[float]) -> str:
    dx = float(target_xy[0]) - float(source_xy[0])
    dy = float(target_xy[1]) - float(source_xy[1])
    if abs(dx) >= abs(dy):
        return "east" if dx >= 0.0 else "west"
    return "north" if dy >= 0.0 else "south"


def _make_reference_object(*, xy: Tuple[float, float], scale: float) -> Dict[str, Any]:
    dimensions = tuple(round(float(value) * float(scale), 4) for value in WAREHOUSE_NEAREST_REFERENCE_OBJECT_DIMENSIONS)
    return {
        "object_id": "warehouse_reference_red_sphere",
        "object_type": REFERENCE_OBJECT_TYPE,
        "object_name": REFERENCE_OBJECT_NAME,
        "prompt_name": REFERENCE_OBJECT_NAME,
        "object_role": "warehouse_reference_object",
        "orientation_axis": "x",
        "is_answer_candidate": False,
        "dimension_scale": round(float(scale), 4),
        "world_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(dimensions[2] * 0.5), 4)],
        "base_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), 0.0],
        "dimensions_xyz": [round(float(value), 4) for value in dimensions],
        "footprint_radius": round(float(0.5 * math.sqrt(dimensions[0] * dimensions[0] + dimensions[1] * dimensions[1])), 4),
        "fill_rgb": [int(channel) for channel in REFERENCE_OBJECT_RGB],
    }


def _make_robot_candidate(
    *,
    rng,
    object_id: str,
    xy: Tuple[float, float],
    heading: str,
    label: str | None,
    robot_design: str | None = None,
) -> Dict[str, Any]:
    orientation_axis = "x" if str(heading) in {"east", "west"} else "y"
    robot_design = str(robot_design) if robot_design is not None else str(rng.choice(SUPPORTED_ROBOT_DESIGNS))
    if robot_design not in set(SUPPORTED_ROBOT_DESIGNS):
        raise ValueError(f"unsupported robot_design: {robot_design}")
    dimensions = _dimensions_for_object("warehouse_robot", orientation_axis=str(orientation_axis), scale=float(rng.uniform(0.94, 1.10)))
    width, depth, height = dimensions
    if robot_design == "sensor_tower":
        dimensions = (round(width * 0.96, 4), round(depth * 0.96, 4), round(height * 1.22, 4))
    elif robot_design == "stacker_bot":
        dimensions = (round(width * 0.94, 4), round(depth * 0.98, 4), round(height * 1.36, 4))
    spec = _make_object_spec(
        object_id=str(object_id),
        object_type="warehouse_robot",
        object_role="warehouse_robot_candidate",
        xy=xy,
        orientation_axis=str(orientation_axis),
        dimensions_xyz=dimensions,
        dimension_scale=1.0,
        label=label,
    )
    heading_xy = _heading_vector(str(heading))
    width, depth, height = (float(value) for value in dimensions)
    gripper_extent = width * 0.76 if str(orientation_axis) == "x" else depth * 0.76
    spec.update(
        {
            "robot_design": str(robot_design),
            "robot_heading": str(heading),
            "robot_base_rgb": [int(channel) for channel in ROBOT_BASE_COLORS[int(rng.randrange(len(ROBOT_BASE_COLORS)))]],
            "robot_accent_rgb": [int(channel) for channel in ROBOT_ACCENT_COLORS[int(rng.randrange(len(ROBOT_ACCENT_COLORS)))]],
            "gripper_tip_xyz": [
                round(float(xy[0]) + float(heading_xy[0]) * float(gripper_extent), 4),
                round(float(xy[1]) + float(heading_xy[1]) * float(gripper_extent), 4),
                round(float(height * 0.58), 4),
            ],
        }
    )
    return spec


def _assign_unique_robot_option_colors(
    robot_specs: Sequence[Mapping[str, Any]],
    *,
    rng,
) -> List[Dict[str, Any]]:
    colors = [tuple(int(channel) for channel in color) for color in ROBOT_BASE_COLORS]
    rng.shuffle(colors)
    if len(robot_specs) > len(colors):
        raise ValueError("not enough unique robot colors for option descriptors")
    updated_specs: List[Dict[str, Any]] = []
    for spec, color in zip(robot_specs, colors):
        updated = dict(spec)
        updated["robot_base_rgb"] = [int(channel) for channel in color]
        updated_specs.append(updated)
    return list(updated_specs)


def _make_object_candidate(
    *,
    rng,
    object_id: str,
    object_type: str,
    xy: Tuple[float, float],
    orientation_axis: str,
    label: str | None,
) -> Dict[str, Any]:
    scale = float(rng.uniform(0.88, 1.14))
    dimensions = _dimensions_for_object(str(object_type), orientation_axis=str(orientation_axis), scale=float(scale))
    return _make_object_spec(
        object_id=str(object_id),
        object_type=str(object_type),
        object_role="warehouse_object_candidate",
        xy=xy,
        orientation_axis=str(orientation_axis),
        dimensions_xyz=dimensions,
        dimension_scale=float(scale),
        label=label,
    )


def _attach_robot_nearest_answers(
    robot_specs: Sequence[Mapping[str, Any]],
    reference_spec: Mapping[str, Any],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    candidate_count: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ordered = sorted(robot_specs, key=lambda spec: (_surface_gap(spec, reference_spec), str(spec["object_id"])))
    first = dict(ordered[0])
    second = dict(ordered[1])
    margin = float(_surface_gap(second, reference_spec) - _surface_gap(first, reference_spec))
    if margin < MIN_NEAREST_ROBOT_MARGIN:
        raise ValueError("nearest robot margin too small")
    answer_label_index = abs(
        int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.answer_label"))
    ) % int(candidate_count)
    answer_label = str(POINT_LABELS[int(answer_label_index)])
    remaining_labels = [str(label) for label in POINT_LABELS[: int(candidate_count)] if str(label) != str(answer_label)]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.answer_label_assignment")
    rng.shuffle(remaining_labels)
    relabeled: List[Dict[str, Any]] = []
    for spec in robot_specs:
        updated = dict(spec)
        is_answer = str(updated["object_id"]) == str(first["object_id"])
        label = answer_label if is_answer else remaining_labels.pop()
        distance = _surface_gap(updated, reference_spec)
        updated.update(
            {
                "object_id": f"warehouse_robot_{label}",
                "point_id": f"warehouse_robot_{label}",
                "point_label": str(label),
                "object_label": str(label),
                "is_answer_candidate": True,
                "is_nearest_robot_to_reference": bool(is_answer),
                "distance_to_reference_object": round(float(distance), 4),
            }
        )
        relabeled.append(updated)
    answer_spec = next(spec for spec in relabeled if bool(spec["is_nearest_robot_to_reference"]))
    distance_order = [
        str(spec["point_label"])
        for spec in sorted(relabeled, key=lambda item: (float(item["distance_to_reference_object"]), str(item["point_label"])))
    ]
    return list(sorted(relabeled, key=lambda spec: str(spec["point_label"]))), {
        "answer_label": str(answer_label),
        "answer_spec": dict(answer_spec),
        "nearest_margin": round(float(margin), 4),
        "distance_order": list(distance_order),
    }


def _attach_object_nearest_answers(
    candidate_specs: Sequence[Mapping[str, Any]],
    reference_spec: Mapping[str, Any],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    candidate_count: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ordered = sorted(candidate_specs, key=lambda spec: (_surface_gap(spec, reference_spec), str(spec["object_id"])))
    first = dict(ordered[0])
    second = dict(ordered[1])
    margin = float(_surface_gap(second, reference_spec) - _surface_gap(first, reference_spec))
    if margin < MIN_NEAREST_OBJECT_MARGIN:
        raise ValueError("nearest warehouse object margin too small")
    answer_label_index = abs(
        int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.answer_label"))
    ) % int(candidate_count)
    answer_label = str(POINT_LABELS[int(answer_label_index)])
    remaining_labels = [str(label) for label in POINT_LABELS[: int(candidate_count)] if str(label) != str(answer_label)]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.object_answer_label_assignment")
    rng.shuffle(remaining_labels)
    relabeled: List[Dict[str, Any]] = []
    for spec in candidate_specs:
        updated = dict(spec)
        is_answer = str(updated["object_id"]) == str(first["object_id"])
        label = answer_label if is_answer else remaining_labels.pop()
        distance = _surface_gap(updated, reference_spec)
        updated.update(
            {
                "object_id": f"warehouse_object_{label}",
                "point_id": f"warehouse_object_{label}",
                "point_label": str(label),
                "object_label": str(label),
                "is_answer_candidate": True,
                "is_nearest_object_to_reference_robot": bool(is_answer),
                "distance_to_reference_robot": round(float(distance), 4),
            }
        )
        relabeled.append(updated)
    answer_spec = next(spec for spec in relabeled if bool(spec["is_nearest_object_to_reference_robot"]))
    distance_order = [
        str(spec["point_label"])
        for spec in sorted(relabeled, key=lambda item: (float(item["distance_to_reference_robot"]), str(item["point_label"])))
    ]
    return list(sorted(relabeled, key=lambda spec: str(spec["point_label"]))), {
        "answer_label": str(answer_label),
        "answer_spec": dict(answer_spec),
        "nearest_margin": round(float(margin), 4),
        "distance_order": list(distance_order),
    }


def _sample_reference_and_robot_candidates(
    *,
    rng,
    candidate_count: int,
    context_object_count: int,
    aisle_heading: str,
    render_params: _WarehouseRenderParams,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    forward_xy = _heading_vector(str(aisle_heading))
    _unused_reference, _unused_candidates, context_specs, scene_geometry = _sample_reference_and_objects(
        rng=rng,
        candidate_count=max(5, int(candidate_count)),
        context_object_count=int(context_object_count),
        robot_heading=str(aisle_heading),
        render_params=render_params,
    )
    origin_xy = scene_geometry["origin_xy"]
    reference_xy = _local_to_world(
        forward_s=float(rng.uniform(0.18, 0.72)),
        lateral_l=float(rng.uniform(-0.16, 0.16)),
        origin_xy=origin_xy,
        forward_xy=forward_xy,
    )
    reference_spec = _make_reference_object(xy=reference_xy, scale=float(rng.uniform(0.92, 1.10)))
    # Robot placement is constrained against the semantic reference and other
    # robots here; render-time visibility checks reject severe context occlusion.
    placed: List[Dict[str, Any]] = [dict(reference_spec)]
    ref_x, ref_y, _ref_z = (float(value) for value in reference_spec["world_xyz"])

    angle = float(rng.choice([0.25, 1.10, 2.05, 2.95, 3.85, 4.80, 5.65]) + rng.uniform(-0.16, 0.16))
    answer_probe = _make_robot_candidate(rng=rng, object_id="robot_answer_probe", xy=(0.0, 0.0), heading="east", label=None)
    answer_radius = float(answer_probe["footprint_radius"])
    answer_distance = float(reference_spec["footprint_radius"]) + float(answer_radius) + float(rng.uniform(0.18, 0.30))
    answer_xy = (float(ref_x + math.cos(angle) * answer_distance), float(ref_y + math.sin(angle) * answer_distance))
    answer_heading = _heading_towards(answer_xy, reference_xy)
    answer_spec = _make_robot_candidate(rng=rng, object_id="robot_answer_slot", xy=answer_xy, heading=str(answer_heading), label="?")
    if not _can_place(answer_spec, placed, clearance=0.12):
        raise ValueError("could not place nearest robot")
    placed.append(answer_spec)

    robot_specs: List[Dict[str, Any]] = [answer_spec]
    ring_specs = [
        (1.78, -2.18),
        (2.18, -1.18),
        (2.16, 1.18),
        (1.46, 2.08),
        (-0.18, 2.26),
        (-1.46, 2.02),
        (-2.04, 0.92),
        (-2.10, -0.92),
        (-1.16, -2.08),
        (0.38, -2.34),
    ]
    rng.shuffle(ring_specs)
    for index in range(int(candidate_count) - 1):
        placed_spec: Dict[str, Any] | None = None
        for radial_distance, base_angle in ring_specs[index:] + ring_specs[:index]:
            for _jitter_attempt in range(8):
                theta = float(base_angle + rng.uniform(-0.20, 0.20))
                distance = float(radial_distance + rng.uniform(0.00, 0.42))
                xy = (float(ref_x + math.cos(theta) * distance), float(ref_y + math.sin(theta) * distance))
                heading = _heading_towards(xy, reference_xy)
                if rng.random() < 0.20:
                    heading = str(rng.choice(SUPPORTED_ROBOT_HEADINGS))
                spec = _make_robot_candidate(rng=rng, object_id=f"robot_distractor_slot_{index}", xy=xy, heading=str(heading), label="?")
                if _surface_gap(spec, reference_spec) <= _surface_gap(answer_spec, reference_spec) + MIN_NEAREST_ROBOT_MARGIN:
                    continue
                if not _can_place(spec, placed, clearance=0.14):
                    continue
                placed_spec = spec
                break
            if placed_spec is not None:
                break
        if placed_spec is None:
            raise ValueError("could not place robot distractor")
        placed.append(placed_spec)
        robot_specs.append(placed_spec)

    robot_specs = _assign_unique_robot_option_colors(robot_specs, rng=rng)
    robot_specs, answer_meta = _attach_robot_nearest_answers(
        robot_specs,
        reference_spec,
        params=params,
        instance_seed=int(instance_seed),
        candidate_count=int(candidate_count),
    )
    return [reference_spec], robot_specs, context_specs, scene_geometry, answer_meta


def _sample_robot_and_object_candidates(
    *,
    rng,
    candidate_count: int,
    context_object_count: int,
    aisle_heading: str,
    render_params: _WarehouseRenderParams,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    forward_xy = _heading_vector(str(aisle_heading))
    orientation_axis = _heading_axis(str(aisle_heading))
    _unused_reference_specs, _unused_candidates, context_specs, scene_geometry = _sample_reference_and_objects(
        rng=rng,
        candidate_count=max(5, int(candidate_count)),
        context_object_count=int(context_object_count),
        robot_heading=str(aisle_heading),
        render_params=render_params,
    )
    robot_xy = tuple(float(value) for value in scene_geometry["robot_xy"])
    robot_spec = _make_robot_candidate(
        rng=rng,
        object_id="warehouse_robot_reference",
        xy=(float(robot_xy[0]), float(robot_xy[1])),
        heading=str(aisle_heading),
        label=None,
        robot_design=str(rng.choice(("sensor_tower", "stacker_bot"))),
    )
    robot_spec.update(
        {
            "object_role": "warehouse_reference_robot",
            "is_answer_candidate": False,
            "point_id": None,
            "point_label": None,
            "object_label": None,
        }
    )
    placed: List[Dict[str, Any]] = [dict(robot_spec)]
    robot_x, robot_y, _robot_z = (float(value) for value in robot_spec["world_xyz"])

    object_types = [str(object_type) for object_type in OBJECT_CANDIDATE_TYPES]
    rng.shuffle(object_types)

    answer_type = object_types.pop()
    answer_probe = _make_object_candidate(
        rng=rng,
        object_id="object_answer_probe",
        object_type=str(answer_type),
        xy=(0.0, 0.0),
        orientation_axis=str(orientation_axis),
        label=None,
    )
    angle = float(rng.choice([0.18, 0.92, 1.72, 2.56, 3.32, 4.10, 5.12]) + rng.uniform(-0.16, 0.16))
    answer_distance = float(robot_spec["footprint_radius"]) + float(answer_probe["footprint_radius"]) + float(rng.uniform(0.22, 0.36))
    answer_xy = (float(robot_x + math.cos(angle) * answer_distance), float(robot_y + math.sin(angle) * answer_distance))
    answer_spec = _make_object_candidate(
        rng=rng,
        object_id="object_answer_slot",
        object_type=str(answer_type),
        xy=answer_xy,
        orientation_axis=str(orientation_axis),
        label="?",
    )
    if not _can_place(answer_spec, placed, clearance=0.10):
        raise ValueError("could not place nearest warehouse object")
    placed.append(answer_spec)

    candidate_specs: List[Dict[str, Any]] = [answer_spec]
    ring_specs = [
        (1.60, -2.34),
        (1.92, -1.26),
        (2.12, -0.12),
        (1.78, 1.08),
        (2.22, 2.06),
        (1.48, 2.86),
        (2.36, 3.72),
        (1.86, 4.70),
        (2.18, 5.56),
    ]
    rng.shuffle(ring_specs)
    for index in range(int(candidate_count) - 1):
        placed_spec: Dict[str, Any] | None = None
        object_type = str(object_types.pop() if object_types else rng.choice(OBJECT_CANDIDATE_TYPES))
        for radial_distance, base_angle in ring_specs[index:] + ring_specs[:index]:
            for _jitter_attempt in range(9):
                theta = float(base_angle + rng.uniform(-0.22, 0.22))
                distance = float(radial_distance + rng.uniform(0.06, 0.48))
                xy = (float(robot_x + math.cos(theta) * distance), float(robot_y + math.sin(theta) * distance))
                spec = _make_object_candidate(
                    rng=rng,
                    object_id=f"object_distractor_slot_{index}",
                    object_type=str(object_type),
                    xy=xy,
                    orientation_axis=str(orientation_axis),
                    label="?",
                )
                if _surface_gap(spec, robot_spec) <= _surface_gap(answer_spec, robot_spec) + MIN_NEAREST_OBJECT_MARGIN:
                    continue
                if not _can_place(spec, placed, clearance=0.14):
                    continue
                placed_spec = spec
                break
            if placed_spec is not None:
                break
        if placed_spec is None:
            raise ValueError("could not place warehouse object distractor")
        placed.append(placed_spec)
        candidate_specs.append(placed_spec)

    candidate_specs, answer_meta = _attach_object_nearest_answers(
        candidate_specs,
        robot_spec,
        params=params,
        instance_seed=int(instance_seed),
        candidate_count=int(candidate_count),
    )
    robot_spec["nearest_object_labels"] = [str(answer_meta["answer_label"])]
    return [robot_spec], candidate_specs, context_specs, scene_geometry, answer_meta


def _visibility_ok_nearest(
    candidate_specs: Sequence[Mapping[str, Any]],
    reference_specs: Sequence[Mapping[str, Any]],
    context_specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
    render_params: _WarehouseRenderParams,
) -> bool:
    candidate_bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=18.0) for spec in candidate_specs]
    candidate_centers = [(float(spec["screen_xy"][0]), float(spec["screen_xy"][1])) for spec in candidate_specs]
    for bbox in candidate_bboxes:
        width = float(bbox[2]) - float(bbox[0])
        height = float(bbox[3]) - float(bbox[1])
        if width < MIN_CANDIDATE_VISIBLE_PX or height < MIN_CANDIDATE_VISIBLE_PX:
            return False
        if (
            float(bbox[0]) < -28.0
            or float(bbox[1]) < -28.0
            or float(bbox[2]) > float(render_params.canvas_width + 28)
            or float(bbox[3]) > float(render_params.canvas_height + 28)
        ):
            return False
    for index, center in enumerate(candidate_centers):
        for other_index in range(index + 1, len(candidate_centers)):
            other = candidate_centers[other_index]
            if math.hypot(center[0] - other[0], center[1] - other[1]) < MIN_CANDIDATE_CENTER_SEPARATION_PX:
                return False
            if _bbox_intersection_area(candidate_bboxes[index], candidate_bboxes[other_index]) > MAX_CANDIDATE_BBOX_INTERSECTION_PX:
                return False
    reference_bboxes = []
    for reference in reference_specs:
        ref_bbox = _object_screen_bbox(reference, camera, frame, pad_px=10.0)
        width = float(ref_bbox[2]) - float(ref_bbox[0])
        height = float(ref_bbox[3]) - float(ref_bbox[1])
        if width < MIN_REFERENCE_VISIBLE_PX or height < MIN_REFERENCE_VISIBLE_PX:
            return False
        if (
            float(ref_bbox[0]) < -28.0
            or float(ref_bbox[1]) < -28.0
            or float(ref_bbox[2]) > float(render_params.canvas_width + 28)
            or float(ref_bbox[3]) > float(render_params.canvas_height + 28)
        ):
            return False
        reference_bboxes.append(list(ref_bbox))
    for candidate_index, candidate_bbox in enumerate(candidate_bboxes):
        candidate_area = max(1.0, _bbox_area(candidate_bbox))
        for ref_bbox in reference_bboxes:
            overlap = _bbox_intersection_area(candidate_bbox, ref_bbox)
            if overlap > 1800.0 and overlap / candidate_area > 0.20:
                return False
    context_bboxes = {str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=8.0) for spec in context_specs}
    checked_specs = [*candidate_specs, *reference_specs]
    checked_bboxes = candidate_bboxes + [_object_screen_bbox(spec, camera, frame, pad_px=10.0) for spec in reference_specs]
    for checked_index, checked in enumerate(checked_specs):
        checked_bbox = checked_bboxes[checked_index]
        checked_area = max(1.0, _bbox_area(checked_bbox))
        for context in context_specs:
            if str(context.get("object_type")) == "shelf_rack":
                continue
            if float(context["camera_distance"]) >= float(checked["camera_distance"]) - 0.05:
                continue
            overlap = _bbox_intersection_area(checked_bbox, context_bboxes[str(context["object_id"])])
            if overlap > 2200.0 and overlap / checked_area > 0.24:
                return False
    return True


def _build_dataset(
    *,
    params: Mapping[str, Any],
    query_id: str,
    scene_variant: str,
    aisle_heading: str,
    candidate_count: int,
    context_object_count: int,
    camera_yaw_band: Tuple[float, float],
    camera_yaw_band_index: int,
    render_params: _WarehouseRenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    for _attempt in range(520):
        camera = _sample_camera(rng, yaw_band_degrees=tuple(float(value) for value in camera_yaw_band))
        if str(query_id) == "closest_robot_to_reference":
            reference_specs, candidate_specs, context_specs, scene_geometry, answer_meta = _sample_reference_and_robot_candidates(
                rng=rng,
                candidate_count=int(candidate_count),
                context_object_count=int(context_object_count),
                aisle_heading=str(aisle_heading),
                render_params=render_params,
                params=params,
                instance_seed=int(instance_seed),
            )
        elif str(query_id) == "closest_object_to_robot":
            reference_specs, candidate_specs, context_specs, scene_geometry, answer_meta = _sample_robot_and_object_candidates(
                rng=rng,
                candidate_count=int(candidate_count),
                context_object_count=int(context_object_count),
                aisle_heading=str(aisle_heading),
                render_params=render_params,
                params=params,
                instance_seed=int(instance_seed),
            )
        else:
            raise ValueError(f"unsupported query_id: {query_id}")
        all_specs = [*reference_specs, *candidate_specs, *context_specs]
        reference_points: List[Tuple[float, float, float]] = []
        for spec in all_specs:
            if str(spec.get("object_type")) == "shelf_rack":
                continue
            reference_points.extend(_object_reference_points(spec))
            if str(spec.get("object_type")) == "warehouse_robot" and isinstance(spec.get("gripper_tip_xyz"), Sequence):
                reference_points.append(tuple(float(value) for value in spec["gripper_tip_xyz"]))
        reference_points.extend(tuple(float(value) for value in point) for point in scene_geometry["main_aisle_polygon"])
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_reference = _finalize_specs(reference_specs, camera=camera, frame=frame)
        finalized_candidates = _finalize_specs(candidate_specs, camera=camera, frame=frame)
        finalized_context = _finalize_specs(context_specs, camera=camera, frame=frame)
        if not _visibility_ok_nearest(finalized_candidates, finalized_reference, finalized_context, camera=camera, frame=frame, render_params=render_params):
            continue
        answer_label = str(answer_meta["answer_label"])
        answer_spec = next(spec for spec in finalized_candidates if str(spec["point_label"]) == answer_label)
        if str(query_id) == "closest_robot_to_reference":
            if not bool(answer_spec.get("is_nearest_robot_to_reference", False)):
                continue
            distance_by_label = {str(spec["point_label"]): round(float(spec["distance_to_reference_object"]), 4) for spec in finalized_candidates}
            nearest_by_label = {str(spec["point_label"]): bool(spec.get("is_nearest_robot_to_reference", False)) for spec in finalized_candidates}
            predicate = f"option-panel robot with the smallest ground-plane surface gap to the {REFERENCE_OBJECT_NAME}"
            reference_object_name = REFERENCE_OBJECT_NAME
            nearest_robot_by_label = dict(sorted(nearest_by_label.items()))
            nearest_object_by_label: Dict[str, bool] = {}
            answer_robot_id = str(answer_spec["object_id"])
            answer_object_id = str(answer_spec["object_id"])
            nearest_robot_candidate_labels = [str(answer_label)]
            nearest_object_candidate_labels: List[str] = []
        else:
            if not bool(answer_spec.get("is_nearest_object_to_reference_robot", False)):
                continue
            distance_by_label = {str(spec["point_label"]): round(float(spec["distance_to_reference_robot"]), 4) for spec in finalized_candidates}
            nearest_by_label = {str(spec["point_label"]): bool(spec.get("is_nearest_object_to_reference_robot", False)) for spec in finalized_candidates}
            predicate = "option-panel warehouse object with the smallest ground-plane surface gap to the robot"
            reference_object_name = "robot"
            nearest_robot_by_label = {}
            nearest_object_by_label = dict(sorted(nearest_by_label.items()))
            answer_robot_id = ""
            answer_object_id = str(answer_spec["object_id"])
            nearest_robot_candidate_labels = []
            nearest_object_candidate_labels = [str(answer_label)]
        candidate_projected_bboxes = {
            str(spec["point_label"]): [round(float(value), 3) for value in _object_screen_bbox(spec, camera, frame, pad_px=0.0)]
            for spec in finalized_candidates
        }
        candidate_object_types = {str(spec["point_label"]): str(spec["object_type"]) for spec in finalized_candidates}
        object_type_counts = Counter(str(spec["object_type"]) for spec in [*finalized_reference, *finalized_candidates, *finalized_context])
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "candidate_count": int(candidate_count),
            "context_object_count": int(context_object_count),
            "aisle_heading": str(aisle_heading),
            "reference_object": dict(finalized_reference[0]),
            "reference_object_name": str(reference_object_name),
            "reference_specs": list(finalized_reference),
            "reference_object_specs": list(finalized_reference),
            "reference_robot_specs": list(finalized_reference) if str(query_id) == "closest_object_to_robot" else [],
            "candidate_specs": sorted(finalized_candidates, key=lambda spec: str(spec["point_label"])),
            "candidate_robot_specs": sorted(finalized_candidates, key=lambda spec: str(spec["point_label"])) if str(query_id) == "closest_robot_to_reference" else [],
            "candidate_object_specs": sorted(finalized_candidates, key=lambda spec: str(spec["point_label"])) if str(query_id) == "closest_object_to_robot" else [],
            "context_object_specs": sorted(finalized_context, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted([*finalized_reference, *finalized_candidates, *finalized_context], key=lambda spec: str(spec["object_id"])),
            "target_object_ids": [str(answer_spec["object_id"])],
            "answer_label": str(answer_label),
            "answer_object_id": str(answer_object_id),
            "answer_robot_id": str(answer_robot_id),
            "answer_object_type": str(answer_spec["object_type"]),
            "nearest_candidate_labels": [str(answer_label)],
            "nearest_robot_candidate_labels": list(nearest_robot_candidate_labels),
            "nearest_object_candidate_labels": list(nearest_object_candidate_labels),
            "nearest_candidate_by_label": dict(sorted(nearest_by_label.items())),
            "nearest_robot_by_label": dict(nearest_robot_by_label),
            "nearest_object_by_label": dict(nearest_object_by_label),
            "distance_to_reference_by_label": dict(sorted(distance_by_label.items())),
            "distance_to_reference_object_by_label": dict(sorted(distance_by_label.items())) if str(query_id) == "closest_robot_to_reference" else {},
            "distance_to_reference_robot_by_label": dict(sorted(distance_by_label.items())) if str(query_id) == "closest_object_to_robot" else {},
            "distance_order_near_to_far": [str(label) for label in answer_meta["distance_order"]],
            "nearest_margin": float(answer_meta["nearest_margin"]),
            "nearest_robot_margin": float(answer_meta["nearest_margin"]) if str(query_id) == "closest_robot_to_reference" else 0.0,
            "nearest_object_margin": float(answer_meta["nearest_margin"]) if str(query_id) == "closest_object_to_robot" else 0.0,
            "candidate_projected_bboxes_by_label": dict(sorted(candidate_projected_bboxes.items())),
            "candidate_object_types_by_label": dict(sorted(candidate_object_types.items())),
            "object_type_counts": dict(sorted(object_type_counts.items())),
            "object_count": int(1 + len(finalized_candidates) + len(finalized_context)),
            "main_aisle_polygon_world": list(scene_geometry["main_aisle_polygon"]),
            "shelf_zone_polygons_world": list(scene_geometry["shelf_zone_polygons"]),
            "camera": {
                "camera_position": [round(float(value), 4) for value in camera.camera_position],
                "target": [round(float(value), 4) for value in camera.target],
                "yaw_degrees": round(float(camera.yaw_degrees), 4),
                "yaw_band_index": int(camera_yaw_band_index),
                "yaw_band_degrees": [round(float(value), 4) for value in camera_yaw_band],
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
                "predicate": str(predicate),
                "reference_object_id": str(finalized_reference[0]["object_id"]),
                "reference_object_name": str(reference_object_name),
                "nearest_candidate_by_label": dict(sorted(nearest_by_label.items())),
                "nearest_robot_by_label": dict(nearest_robot_by_label),
                "nearest_object_by_label": dict(nearest_object_by_label),
                "distance_to_reference_by_label": dict(sorted(distance_by_label.items())),
                "distance_to_reference_object_by_label": dict(sorted(distance_by_label.items())) if str(query_id) == "closest_robot_to_reference" else {},
                "distance_to_reference_robot_by_label": dict(sorted(distance_by_label.items())) if str(query_id) == "closest_object_to_robot" else {},
                "distance_order_near_to_far": [str(label) for label in answer_meta["distance_order"]],
                "answer_label": str(answer_label),
                "answer_object_id": str(answer_object_id),
                "answer_robot_id": str(answer_robot_id),
                "unique_answer": True,
            },
        }
    raise ValueError("could not construct a visible warehouse nearest-reference scene")




def _build_complexity(*, candidate_count: int, context_object_count: int, complexity_defaults: Mapping[str, Any]) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "robot_scan": float(raw_weights.get("robot_scan", 0.34)),
        "reference_grounding": float(raw_weights.get("reference_grounding", 0.22)),
        "depth_distance_reasoning": float(raw_weights.get("depth_distance_reasoning", 0.28)),
        "distractor_load": float(raw_weights.get("distractor_load", 0.16)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "robot_scan": _normalize_unit(float(candidate_count), 4.0, 6.0),
        "reference_grounding": 0.62,
        "depth_distance_reasoning": 0.58,
        "distractor_load": _normalize_unit(float(context_object_count), 7.0, 13.0),
    }
    score = sum(float(components[key]) * max(0.0, float(weights[key])) for key in weights) / float(total)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={key: round(float(value), 6) for key, value in components.items()},
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "warehouse")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_DEFAULTS = resolve_task_group_section_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    "complexity",
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


def _build_retry_locked_params(instance_seed: int, params: Mapping[str, Any]) -> Dict[str, Any]:
    locked_params = dict(params)
    query_id, _query_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
        allow_locked=True,
    )
    scene_variant, _scene_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
        allow_locked=True,
    )
    aisle_heading, _heading_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_AISLE_HEADINGS,
        explicit_key="aisle_heading",
        weights_key="aisle_heading_weights",
        balance_flag_key="balanced_aisle_heading_sampling",
        axis_namespace="aisle_heading",
        allow_locked=True,
    )
    candidate_count, _candidate_probabilities = _shared_resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="candidate_count",
        default_min=5,
        default_max=5,
        lower=4,
        upper=6,
        allow_locked=True,
    )
    context_object_count, _context_probabilities = _shared_resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="context_object_count",
        default_min=10,
        default_max=10,
        lower=8,
        upper=13,
        allow_locked=True,
    )
    _camera_yaw_band, _camera_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(params=params, instance_seed=int(instance_seed))
    locked_params.update(
        {
            "_locked_query_id": str(query_id),
            "_locked_scene_variant": str(scene_variant),
            "_locked_aisle_heading": str(aisle_heading),
            "_locked_candidate_count": int(candidate_count),
            "_locked_context_object_count": int(context_object_count),
            "_locked_camera_yaw_band_index": int(camera_yaw_band_index),
        }
    )
    return locked_params


@register_task
class ThreeDWarehouseNearestCandidateToReferenceLabelTask:
    """Choose the option-panel warehouse item closest to a reference item."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "warehouse"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        retry_params = _build_retry_locked_params(int(instance_seed), params)
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(spawn_rng(int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            try:
                return self._generate_once(int(attempt_seed), params=retry_params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
            allow_locked=True,
        )
        scene_variant, scene_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
            allow_locked=True,
        )
        aisle_heading, aisle_heading_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_AISLE_HEADINGS,
            explicit_key="aisle_heading",
            weights_key="aisle_heading_weights",
            balance_flag_key="balanced_aisle_heading_sampling",
            axis_namespace="aisle_heading",
            allow_locked=True,
        )
        candidate_count, candidate_count_probabilities = _shared_resolve_count(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="candidate_count",
            default_min=5,
            default_max=5,
            lower=4,
            upper=6,
            allow_locked=True,
        )
        context_object_count, context_count_probabilities = _shared_resolve_count(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="context_object_count",
            default_min=10,
            default_max=10,
            lower=8,
            upper=13,
            allow_locked=True,
        )
        camera_yaw_band, camera_yaw_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(params=params, instance_seed=int(instance_seed))
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_dataset(
            params=params,
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            aisle_heading=str(aisle_heading),
            candidate_count=int(candidate_count),
            context_object_count=int(context_object_count),
            camera_yaw_band=tuple(camera_yaw_band),
            camera_yaw_band_index=int(camera_yaw_band_index),
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
        option_choices = build_text_option_choices(dataset["candidate_specs"])
        rendered_scene = render_warehouse_robot_nearest_scene_3d(
            background,
            dataset=dataset,
            render_params=render_params,
            option_choices=option_choices,
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
                "annotation_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_config = dict(_PROMPT_DEFAULTS)
        prompt_config.update(prompt_defaults)
        object_description = str(prompt_config.get(f"object_description_{query_id}", prompt_defaults["object_description"]))
        annotation_hint = str(prompt_config.get(f"annotation_hint_{query_id}", prompt_defaults["annotation_hint"]))
        answer_hint = str(prompt_config.get(f"answer_hint_{query_id}", prompt_defaults["answer_hint"]))
        json_example = str(prompt_config.get(f"json_example_{query_id}", prompt_defaults["json_example"]))
        json_example_answer_only = str(
            prompt_config.get(f"json_example_answer_only_{query_id}", prompt_defaults["json_example_answer_only"])
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "reference_object_name": str(dataset["reference_object_name"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(answer_hint),
                "annotation_hint": str(annotation_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_label = str(dataset["answer_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in rendered_scene.annotation_bboxes]
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        complexity = _build_complexity(
            candidate_count=int(dataset["candidate_count"]),
            context_object_count=int(dataset["context_object_count"]),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )
        solver_trace = dict(dataset["solver_trace"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_warehouse_robot",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "candidate_count": int(dataset["candidate_count"]),
                    "context_object_count": int(dataset["context_object_count"]),
                    "aisle_heading": str(dataset["aisle_heading"]),
                    "reference_object_name": str(dataset["reference_object_name"]),
                    "nearest_candidate_by_label": dict(dataset["nearest_candidate_by_label"]),
                    "nearest_robot_by_label": dict(dataset["nearest_robot_by_label"]),
                    "nearest_object_by_label": dict(dataset["nearest_object_by_label"]),
                    "answer_label": str(answer_label),
                    "answer_object_id": str(dataset["answer_object_id"]),
                    "answer_robot_id": str(dataset["answer_robot_id"]),
                    "view_family": "synthetic_perspective_3d_warehouse_robot",
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probabilities),
                    "aisle_heading": str(aisle_heading),
                    "aisle_heading_probabilities": dict(aisle_heading_probabilities),
                    "candidate_count": int(candidate_count),
                    "candidate_count_probabilities": dict(candidate_count_probabilities),
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_count_probabilities),
                    "camera_yaw_band_index": int(camera_yaw_band_index),
                    "camera_yaw_band_probabilities": dict(camera_yaw_probabilities),
                    "answer_label_probabilities": {str(label): round(1.0 / float(candidate_count), 8) for label in POINT_LABELS[: int(candidate_count)]},
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(image.height),
                "scene_canvas_height": int(render_params.canvas_height),
                "option_panel_height_px": int(rendered_scene.option_panel_height_px),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "label_font_size_px": int(render_params.label_font_size_px),
                "aisle_heading": str(dataset["aisle_heading"]),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "warehouse_bbox_px": list(rendered_scene.warehouse_bbox_px),
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "candidate_bboxes_px": {str(key): list(value) for key, value in rendered_scene.candidate_bboxes_px.items()},
                "candidate_centers_px": {str(key): list(value) for key, value in rendered_scene.candidate_centers_px.items()},
                "option_panel_bbox_px": list(rendered_scene.option_panel_bbox_px),
                "option_panel_height_px": int(rendered_scene.option_panel_height_px),
                "option_choice_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_choice_bboxes_px.items()
                },
                "option_choices": [dict(choice) for choice in rendered_scene.option_choices],
                "context_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.context_object_bboxes_px.items()},
                "context_object_centers_px": {str(key): list(value) for key, value in rendered_scene.context_object_centers_px.items()},
                "reference_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.reference_object_bboxes_px.items()},
                "reference_object_centers_px": {str(key): list(value) for key, value in rendered_scene.reference_object_centers_px.items()},
                "target_object_bboxes_px": {str(key): list(rendered_scene.object_bboxes_px[str(key)]) for key in dataset["target_object_ids"]},
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "candidate_count": int(dataset["candidate_count"]),
                "context_object_count": int(dataset["context_object_count"]),
                "object_count": int(dataset["object_count"]),
                "answer_label": str(answer_label),
                "answer_object_id": str(dataset["answer_object_id"]),
                "answer_robot_id": str(dataset["answer_robot_id"]),
                "answer_object_type": str(dataset["answer_object_type"]),
                "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                "reference_object": dict(dataset["reference_object"]),
                "reference_specs": [dict(spec) for spec in dataset["reference_specs"]],
                "reference_object_specs": [dict(spec) for spec in dataset["reference_object_specs"]],
                "reference_robot_specs": [dict(spec) for spec in dataset["reference_robot_specs"]],
                "candidate_specs": [dict(spec) for spec in dataset["candidate_specs"]],
                "option_choices": [dict(choice) for choice in rendered_scene.option_choices],
                "option_descriptor_by_label": {
                    str(choice["label"]): str(choice["descriptor"])
                    for choice in rendered_scene.option_choices
                },
                "candidate_robot_specs": [dict(spec) for spec in dataset["candidate_robot_specs"]],
                "candidate_object_specs": [dict(spec) for spec in dataset["candidate_object_specs"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "aisle_heading": str(dataset["aisle_heading"]),
                "reference_object_name": str(dataset["reference_object_name"]),
                "main_aisle_polygon_world": list(dataset["main_aisle_polygon_world"]),
                "shelf_zone_polygons_world": list(dataset["shelf_zone_polygons_world"]),
                "nearest_candidate_labels": list(dataset["nearest_candidate_labels"]),
                "nearest_robot_candidate_labels": list(dataset["nearest_robot_candidate_labels"]),
                "nearest_object_candidate_labels": list(dataset["nearest_object_candidate_labels"]),
                "nearest_candidate_by_label": dict(dataset["nearest_candidate_by_label"]),
                "nearest_robot_by_label": dict(dataset["nearest_robot_by_label"]),
                "nearest_object_by_label": dict(dataset["nearest_object_by_label"]),
                "distance_to_reference_by_label": dict(dataset["distance_to_reference_by_label"]),
                "distance_to_reference_object_by_label": dict(dataset["distance_to_reference_object_by_label"]),
                "distance_to_reference_robot_by_label": dict(dataset["distance_to_reference_robot_by_label"]),
                "distance_order_near_to_far": list(dataset["distance_order_near_to_far"]),
                "nearest_margin": float(dataset["nearest_margin"]),
                "nearest_robot_margin": float(dataset["nearest_robot_margin"]),
                "nearest_object_margin": float(dataset["nearest_object_margin"]),
                "candidate_projected_bboxes_by_label": dict(dataset["candidate_projected_bboxes_by_label"]),
                "candidate_object_types_by_label": dict(dataset["candidate_object_types_by_label"]),
                "object_type_counts": dict(dataset["object_type_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "view_family": "synthetic_perspective_3d_warehouse_robot",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {"type": "object", "id": str(dataset["answer_object_id"]), "answer": str(answer_label)},
            "projected_annotation": {"bbox_set": [list(bbox) for bbox in annotation_bboxes]},
            "background": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = [
    "MIN_NEAREST_OBJECT_MARGIN",
    "MIN_NEAREST_ROBOT_MARGIN",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDWarehouseNearestCandidateToReferenceLabelTask",
]
