"""Spatial relation counting task for a synthetic 3D object scene."""

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
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.color_variation import resolve_three_d_object_fill_rgb
from ..shared.object_resources import (
    SPATIAL_OBJECT_RELATION_ELEVATED_COMPATIBLE_SHAPES,
    SPATIAL_OBJECT_RELATION_INSIDE_PROP_TYPES,
    SPATIAL_OBJECT_RELATION_ON_TOP_PROP_TYPES,
    SPATIAL_OBJECT_RELATION_UNDER_PROP_TYPES,
)
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.object_scene import (
    CONTEXT_OBJECT_COLORS,
    NAMEABLE_SMALL_OBJECT_SHAPE_TYPES,
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    _RenderParams,
    _bbox_intersection_area,
    _build_projection_frame,
    _camera_yaw_band_for_instance,
    _make_object_spec,
    _min_pairwise,
    _object_reference_points,
    _object_screen_bbox,
    _project_screen,
    _resolve_render_params,
    _sample_camera,
    _sample_shape_dimensions,
    render_object_scene_3d,
)


TASK_ID = "task_three_d__object_scene__relation_attribute_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "on_top_of_reference_count",
    "under_reference_count",
    "inside_reference_count",
)
ON_TOP_REFERENCE_SHAPES: Tuple[str, ...] = tuple(SPATIAL_OBJECT_RELATION_ON_TOP_PROP_TYPES)
UNDER_REFERENCE_SHAPES: Tuple[str, ...] = tuple(SPATIAL_OBJECT_RELATION_UNDER_PROP_TYPES)
INSIDE_REFERENCE_SHAPES: Tuple[str, ...] = tuple(SPATIAL_OBJECT_RELATION_INSIDE_PROP_TYPES)
ELEVATED_COUNTABLE_SHAPES: Tuple[str, ...] = tuple(SPATIAL_OBJECT_RELATION_ELEVATED_COMPATIBLE_SHAPES)
UNDER_COUNTABLE_SHAPES: Tuple[str, ...] = (
    "sphere",
    "cube",
    "cylinder",
    "cone",
    "torus",
    "pyramid",
    "wedge",
)
DISTRACTOR_SHAPE_TYPES: Tuple[str, ...] = tuple(NAMEABLE_SMALL_OBJECT_SHAPE_TYPES)
RELATION_SMALL_DIMENSION_SCALE = 0.62
MIN_PROJECTED_OBJECT_AREA_PX = 420.0
MAX_PAIRWISE_OVERLAP_PX = 3900.0


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / max(1, len(support))
    return {str(value): float(probability) for value in support}


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _bbox_is_readable(bbox: Sequence[float], *, width: int, height: int, min_side_px: float = 17.0) -> bool:
    box_width = float(bbox[2]) - float(bbox[0])
    box_height = float(bbox[3]) - float(bbox[1])
    if box_width < float(min_side_px) or box_height < float(min_side_px):
        return False
    return float(bbox[2]) > 4.0 and float(bbox[3]) > 4.0 and float(bbox[0]) < float(width - 4) and float(bbox[1]) < float(height - 4)


def _set_object_base_z(spec: Mapping[str, Any], base_z: float) -> Dict[str, Any]:
    updated = dict(spec)
    height = float(updated["dimensions_xyz"][2])
    updated["base_xyz"] = [
        round(float(updated["base_xyz"][0]), 4),
        round(float(updated["base_xyz"][1]), 4),
        round(float(base_z), 4),
    ]
    updated["world_xyz"] = [
        round(float(updated["world_xyz"][0]), 4),
        round(float(updated["world_xyz"][1]), 4),
        round(float(base_z) + height * 0.5, 4),
    ]
    return updated


def _scale_dimensions(dimensions_xyz: Sequence[float], scale: float) -> Tuple[float, float, float]:
    width, depth, height = (float(value) * float(scale) for value in dimensions_xyz)
    return (round(float(width), 4), round(float(depth), 4), round(float(height), 4))


def _make_sampled_object(
    *,
    rng,
    object_id: str,
    shape_type: str,
    object_role: str,
    xy: Tuple[float, float],
    base_z: float = 0.0,
    matches_query: bool = False,
) -> Dict[str, Any]:
    dimensions_xyz, dimension_scale = _sample_shape_dimensions(str(shape_type), object_role=str(object_role), rng=rng)
    if str(object_role) == "candidate":
        dimensions_xyz = _scale_dimensions(dimensions_xyz, RELATION_SMALL_DIMENSION_SCALE)
        dimension_scale = round(float(dimension_scale) * float(RELATION_SMALL_DIMENSION_SCALE), 4)
    spec = _make_object_spec(
        object_id=str(object_id),
        shape_type=str(shape_type),
        object_role=str(object_role),
        xy=tuple(float(value) for value in xy),
        dimensions_xyz=dimensions_xyz,
        dimension_scale=float(dimension_scale),
        label=None,
    )
    if float(base_z) != 0.0:
        spec = _set_object_base_z(spec, float(base_z))
    if str(object_role) == "candidate":
        spec.update(
            {
                "is_answer_candidate": False,
                "is_countable_object": True,
                "matches_query": bool(matches_query),
                "count_role": "target" if bool(matches_query) else "distractor",
            }
        )
        spec["fill_rgb"] = [
            int(channel)
            for channel in resolve_three_d_object_fill_rgb(
                spec,
                palette=CONTEXT_OBJECT_COLORS,
                salt=f"{TASK_ID}.countable",
                variation_strength=0.30,
            )
        ]
    return spec


def _reference_shape_support(query_id: str, *, target_count: int) -> Tuple[str, ...]:
    if str(query_id) == "on_top_of_reference_count":
        return ("table",) if int(target_count) >= 3 else ON_TOP_REFERENCE_SHAPES
    if str(query_id) == "under_reference_count":
        return ("table",) if int(target_count) >= 3 else UNDER_REFERENCE_SHAPES
    return INSIDE_REFERENCE_SHAPES


def _countable_shape_pool(query_id: str, *, matches_query: bool) -> Tuple[str, ...]:
    if not bool(matches_query):
        return DISTRACTOR_SHAPE_TYPES
    if str(query_id) in {"on_top_of_reference_count", "inside_reference_count"}:
        return ELEVATED_COUNTABLE_SHAPES
    return UNDER_COUNTABLE_SHAPES


def _target_base_z(query_id: str, reference_spec: Mapping[str, Any]) -> float:
    if str(query_id) == "on_top_of_reference_count":
        return round(float(reference_spec["base_xyz"][2]) + float(reference_spec["dimensions_xyz"][2]) + 0.03, 4)
    if str(query_id) == "inside_reference_count":
        return round(float(reference_spec["base_xyz"][2]) + float(reference_spec["dimensions_xyz"][2]) * 0.18 + 0.02, 4)
    return 0.0


def _relation_truth(query_id: str, candidate_spec: Mapping[str, Any], reference_spec: Mapping[str, Any]) -> bool:
    cx, cy, _cz = (float(value) for value in candidate_spec["world_xyz"])
    rx, ry, _rz = (float(value) for value in reference_spec["world_xyz"])
    c_base = float(candidate_spec["base_xyz"][2])
    r_base = float(reference_spec["base_xyz"][2])
    r_width, r_depth, r_height = (float(value) for value in reference_spec["dimensions_xyz"])
    dx = abs(float(cx - rx))
    dy = abs(float(cy - ry))
    if str(query_id) == "on_top_of_reference_count":
        return bool(dx <= r_width * 0.42 and dy <= r_depth * 0.42 and c_base >= r_base + r_height * 0.90)
    if str(query_id) == "under_reference_count":
        return bool(dx <= r_width * 0.40 and dy <= r_depth * 0.38 and c_base < r_base + r_height * 0.18)
    return bool(dx <= r_width * 0.33 and dy <= r_depth * 0.34 and c_base < r_base + r_height * 0.35)


def _target_offsets(query_id: str, reference_spec: Mapping[str, Any], *, target_count: int) -> List[Tuple[float, float]]:
    width, depth, _height = (float(value) for value in reference_spec["dimensions_xyz"])
    if str(query_id) == "inside_reference_count":
        scale_x, scale_y = 0.30, 0.28
    elif str(query_id) == "under_reference_count":
        scale_x, scale_y = 0.32, 0.28
    else:
        scale_x, scale_y = 0.34, 0.30
    base_offsets = [
        (-1.0, -0.55),
        (1.0, -0.55),
        (0.0, 0.55),
        (0.0, -1.15),
    ]
    return [
        (round(float(dx) * float(width) * float(scale_x), 4), round(float(dy) * float(depth) * float(scale_y), 4))
        for dx, dy in base_offsets[: int(target_count)]
    ]


def _distractor_slots() -> List[Tuple[float, float]]:
    return [
        (-2.62, -2.18),
        (-1.62, -1.36),
        (-2.36, 1.44),
        (-0.82, 2.34),
        (0.82, -2.36),
        (1.82, -1.46),
        (2.52, 1.36),
        (1.28, 2.22),
        (-2.62, 0.18),
        (2.58, 0.02),
        (0.0, -2.72),
        (0.0, 2.58),
        (-3.02, -0.92),
        (3.02, 0.88),
        (-2.98, 2.36),
        (2.98, -2.28),
        (-1.06, 2.92),
        (1.10, -2.98),
        (-3.08, 0.76),
        (3.10, -0.78),
    ]


def _can_place(candidate: Mapping[str, Any], placed: Sequence[Mapping[str, Any]], *, clearance: float = 0.10) -> bool:
    cx, cy, _cz = (float(value) for value in candidate["world_xyz"])
    c_base = float(candidate["base_xyz"][2])
    for item in placed:
        ix, iy, _iz = (float(value) for value in item["world_xyz"])
        i_base = float(item["base_xyz"][2])
        if abs(float(c_base - i_base)) > 0.24:
            continue
        min_distance = float(candidate["footprint_radius"]) + float(item["footprint_radius"]) + float(clearance)
        if math.hypot(float(cx - ix), float(cy - iy)) < float(min_distance):
            return False
    return True


def _sample_countable_specs(
    *,
    rng,
    query_id: str,
    reference_spec: Mapping[str, Any],
    target_count: int,
    object_count: int,
) -> List[Dict[str, Any]]:
    target_base_z = _target_base_z(str(query_id), reference_spec)
    ref_x, ref_y, _ref_z = (float(value) for value in reference_spec["world_xyz"])
    target_shape_pool = list(_countable_shape_pool(str(query_id), matches_query=True))
    distractor_shape_pool = list(_countable_shape_pool(str(query_id), matches_query=False))
    rng.shuffle(target_shape_pool)
    rng.shuffle(distractor_shape_pool)
    placed: List[Dict[str, Any]] = []
    object_specs: List[Dict[str, Any]] = []
    for index, offset in enumerate(_target_offsets(str(query_id), reference_spec, target_count=int(target_count))):
        shape_type = str(target_shape_pool[index % len(target_shape_pool)])
        spec = _make_sampled_object(
            rng=rng,
            object_id=f"count_object_{int(index):02d}",
            shape_type=str(shape_type),
            object_role="candidate",
            xy=(float(ref_x + offset[0] + rng.uniform(-0.035, 0.035)), float(ref_y + offset[1] + rng.uniform(-0.035, 0.035))),
            base_z=float(target_base_z),
            matches_query=True,
        )
        if str(query_id) == "inside_reference_count":
            spec.update(
                {
                    "contained_by_object_id": str(reference_spec["object_id"]),
                    "render_order_bias": -12.0,
                    "visibility_role": "contained_count_foreground",
                }
            )
        elif str(query_id) == "on_top_of_reference_count":
            spec.update({"render_order_bias": -6.0, "visibility_role": "on_top_count_foreground"})
        if not _can_place(spec, placed, clearance=0.03):
            raise ValueError("could not place relation target objects")
        placed.append(spec)
        object_specs.append(spec)

    slots = _distractor_slots()
    rng.shuffle(slots)
    slot_index = 0
    while len(object_specs) < int(object_count):
        if slot_index >= len(slots):
            raise ValueError("not enough distractor slots for relation count")
        slot_x, slot_y = slots[slot_index]
        slot_index += 1
        shape_type = str(distractor_shape_pool[len(object_specs) % len(distractor_shape_pool)])
        spec = _make_sampled_object(
            rng=rng,
            object_id=f"count_object_{len(object_specs):02d}",
            shape_type=str(shape_type),
            object_role="candidate",
            xy=(float(slot_x + rng.uniform(-0.12, 0.12)), float(slot_y + rng.uniform(-0.12, 0.12))),
            matches_query=False,
        )
        if _relation_truth(str(query_id), spec, reference_spec):
            continue
        if not _can_place(spec, placed, clearance=0.12):
            continue
        placed.append(spec)
        object_specs.append(spec)
    return list(object_specs)


def _finalize_specs(
    specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
) -> List[Dict[str, Any]]:
    finalized_specs: List[Dict[str, Any]] = []
    for spec in specs:
        screen = _project_screen(spec["world_xyz"], camera, frame)
        finalized = dict(spec)
        finalized.update(
            {
                "screen_xy": [round(float(screen[0]), 3), round(float(screen[1]), 3)],
                "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
                "camera_distance": round(float(screen[7]), 4),
            }
        )
        finalized_specs.append(finalized)
    return list(finalized_specs)


def _view_is_valid(
    *,
    object_specs: Sequence[Mapping[str, Any]],
    reference_spec: Mapping[str, Any],
    target_object_ids: Sequence[str],
    camera,
    frame,
    render_params: _RenderParams,
) -> bool:
    object_bboxes = {
        str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=8.0)
        for spec in object_specs
    }
    reference_bbox = _object_screen_bbox(reference_spec, camera, frame, pad_px=8.0)
    if not _bbox_is_readable(reference_bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height), min_side_px=48.0):
        return False
    if any(not _bbox_is_readable(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height)) for bbox in object_bboxes.values()):
        return False
    if any(_bbox_area(bbox) < MIN_PROJECTED_OBJECT_AREA_PX for bbox in object_bboxes.values()):
        return False
    targets = {str(object_id) for object_id in target_object_ids}
    for object_id, bbox in object_bboxes.items():
        if str(object_id) in targets:
            continue
        if _bbox_intersection_area(bbox, reference_bbox) > 0.18 * _bbox_area(bbox):
            return False
    for index, (id_a, bbox_a) in enumerate(object_bboxes.items()):
        for id_b, bbox_b in list(object_bboxes.items())[index + 1 :]:
            overlap = _bbox_intersection_area(bbox_a, bbox_b)
            if overlap > MAX_PAIRWISE_OVERLAP_PX:
                return False
            if str(id_a) not in targets or str(id_b) not in targets:
                if overlap > 0.46 * min(_bbox_area(bbox_a), _bbox_area(bbox_b)):
                    return False
    return True


def _build_relation_count_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    object_count: int,
    target_count: int,
    reference_shape_type: str,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    selected_camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
    for _attempt in range(520):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        reference_spec = _make_sampled_object(
            rng=rng,
            object_id=f"relation_reference_{reference_shape_type}",
            shape_type=str(reference_shape_type),
            object_role="context",
            xy=(float(rng.uniform(-0.08, 0.08)), float(rng.uniform(0.03, 0.20))),
        )
        object_specs = _sample_countable_specs(
            rng=rng,
            query_id=str(query_id),
            reference_spec=reference_spec,
            target_count=int(target_count),
            object_count=int(object_count),
        )
        target_specs = [spec for spec in object_specs if bool(spec.get("matches_query", False))]
        target_object_ids = [str(spec["object_id"]) for spec in sorted(target_specs, key=lambda item: str(item["object_id"]))]
        if len(target_object_ids) != int(target_count):
            continue
        relation_status_by_object_id = {
            str(spec["object_id"]): bool(_relation_truth(str(query_id), spec, reference_spec))
            for spec in object_specs
        }
        if sum(1 for value in relation_status_by_object_id.values() if bool(value)) != int(target_count):
            continue
        reference_points = [
            point
            for spec in [*object_specs, reference_spec]
            for point in _object_reference_points(spec)
        ]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _view_is_valid(
            object_specs=object_specs,
            reference_spec=reference_spec,
            target_object_ids=target_object_ids,
            camera=camera,
            frame=frame,
            render_params=render_params,
        ):
            continue

        finalized_objects = _finalize_specs(object_specs, camera=camera, frame=frame)
        finalized_reference = _finalize_specs([reference_spec], camera=camera, frame=frame)[0]
        shape_counts = Counter(str(spec["shape_type"]) for spec in finalized_objects)
        distances = [float(spec["camera_distance"]) for spec in finalized_objects]
        target_object_ids = [
            str(spec["object_id"])
            for spec in sorted(finalized_objects, key=lambda item: str(item["object_id"]))
            if bool(spec.get("matches_query", False))
        ]
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "object_count": int(object_count),
            "countable_object_count": int(object_count),
            "target_count": int(target_count),
            "answer_value": int(target_count),
            "reference_object_id": str(finalized_reference["object_id"]),
            "reference_object_name": str(finalized_reference["prompt_name"]),
            "reference_shape_type": str(finalized_reference["shape_type"]),
            "target_object_ids": list(target_object_ids),
            "point_specs": sorted(finalized_objects, key=lambda spec: str(spec["object_id"])),
            "context_object_specs": [dict(finalized_reference)],
            "object_specs": sorted([*finalized_objects, finalized_reference], key=lambda spec: str(spec["object_id"])),
            "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
            "relation_status_by_object_id": dict(sorted(relation_status_by_object_id.items())),
            "camera": _camera_record(camera, yaw_band=selected_camera_yaw_band),
            "projection_frame": _frame_record(frame),
            "solver_trace": {
                "relation_kind": str(query_id),
                "count_predicate": "object is a countable small object satisfying relation to reference prop",
                "reference_object_id": str(finalized_reference["object_id"]),
                "reference_object_name": str(finalized_reference["prompt_name"]),
                "reference_shape_type": str(finalized_reference["shape_type"]),
                "target_count": int(target_count),
                "target_object_ids": list(target_object_ids),
                "relation_status_by_object_id": dict(sorted(relation_status_by_object_id.items())),
                "unique_integer_answer": True,
                "candidate_camera_distance_margin": round(float(_min_pairwise(distances)), 4),
            },
        }
    raise ValueError("could not construct a valid 3D spatial relation count scene")


def _camera_record(camera, *, yaw_band: Sequence[float]) -> Dict[str, Any]:
    return {
        "camera_position": [round(float(value), 4) for value in camera.camera_position],
        "target": [round(float(value), 4) for value in camera.target],
        "yaw_degrees": round(float(camera.yaw_degrees), 4),
        "yaw_band_degrees": [round(float(value), 4) for value in yaw_band],
        "pitch_degrees": round(float(camera.pitch_degrees), 4),
        "distance": round(float(camera.distance), 4),
        "right": [round(float(value), 5) for value in camera.right],
        "up": [round(float(value), 5) for value in camera.up],
        "forward": [round(float(value), 5) for value in camera.forward],
    }


def _frame_record(frame) -> Dict[str, Any]:
    return {
        "scale": round(float(frame.scale), 5),
        "center_x": round(float(frame.center_x), 3),
        "center_y": round(float(frame.center_y), 3),
        "normalized_center_u": round(float(frame.normalized_center_u), 6),
        "normalized_center_v": round(float(frame.normalized_center_v), 6),
    }


def _build_complexity(
    *,
    query_id: str,
    object_count: int,
    target_count: int,
    scene_variant: str,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.40)),
        "relation_reasoning": float(raw_weights.get("relation_reasoning", 0.34)),
        "target_count": float(raw_weights.get("target_count", 0.16)),
        "scene_variant_load": float(raw_weights.get("scene_variant_load", 0.10)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(int(object_count), 8, 16),
        "relation_reasoning": {
            "on_top_of_reference_count": 0.52,
            "under_reference_count": 0.62,
            "inside_reference_count": 0.66,
        }.get(str(query_id), 0.56),
        "target_count": _normalize_unit(int(target_count), 0, 4),
        "scene_variant_load": {
            "floor_grid_room": 0.30,
            "tabletop_room": 0.34,
            "studio_platform": 0.38,
        }.get(str(scene_variant), 0.32),
    }
    score = sum(float(components[key]) * max(0.0, float(weights[key])) for key in weights) / float(total)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={key: round(float(value), 6) for key, value in components.items()},
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "spatial")
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


@register_task
class ThreeDObjectSceneRelationAttributeCountTask:
    """Count small objects in a spatial relation to one named prop."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "spatial"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return self._generate_once(int(attempt_seed), params=params, camera_yaw_band=camera_yaw_band)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        camera_yaw_band: Tuple[float, float] | None = None,
    ) -> TaskOutput:
        query_id, query_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
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
        object_count, object_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="object_count",
            minimum_default=int(group_default(_GEN_DEFAULTS, "object_count_min", 10)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "object_count_max", 12)),
            lower=7,
            upper=16,
        )
        target_count, target_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="target_count",
            minimum_default=int(group_default(_GEN_DEFAULTS, "target_count_min", 2)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "target_count_max", 3)),
            lower=0,
            upper=max(0, min(4, int(object_count) - 5)),
        )
        reference_support = _reference_shape_support(str(query_id), target_count=int(target_count))
        explicit_reference_shape = params.get("reference_shape_type")
        if explicit_reference_shape is not None:
            reference_shape_type = str(explicit_reference_shape)
            if reference_shape_type not in set(reference_support):
                raise ValueError(f"unsupported reference_shape_type for {query_id}: {reference_shape_type}")
        else:
            reference_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.reference_shape_type",
            )
            reference_shape_type = str(reference_support[abs(int(reference_index)) % len(reference_support)])
        reference_shape_probabilities = _uniform_string_probability_map(
            reference_support,
            selected=str(reference_shape_type) if explicit_reference_shape is not None else None,
        )

        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_relation_count_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            object_count=int(object_count),
            target_count=int(target_count),
            reference_shape_type=str(reference_shape_type),
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
        rendered = render_object_scene_3d(
            background,
            dataset=dataset,
            render_params=render_params,
            draw_candidate_labels=False,
            compute_single_annotation=False,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )
        target_object_ids = [str(object_id) for object_id in dataset["target_object_ids"]]
        annotation_bboxes = [list(rendered.object_bboxes_px[str(object_id)]) for object_id in target_object_ids]

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
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "reference_name": str(dataset["reference_object_name"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        solver_trace = dict(dataset["solver_trace"])
        complexity = _build_complexity(
            query_id=str(query_id),
            object_count=int(object_count),
            target_count=int(answer_value),
            scene_variant=str(scene_variant),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene_spatial_relation_count",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "object_count": int(dataset["object_count"]),
                    "countable_object_count": int(dataset["countable_object_count"]),
                    "target_count": int(answer_value),
                    "target_object_ids": list(target_object_ids),
                    "relation_kind": str(query_id),
                    "reference_object_id": str(dataset["reference_object_id"]),
                    "reference_object_name": str(dataset["reference_object_name"]),
                    "reference_shape_type": str(dataset["reference_shape_type"]),
                    "relation_status_by_object_id": dict(dataset["relation_status_by_object_id"]),
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
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(answer_value),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "reference_shape_type": str(dataset["reference_shape_type"]),
                    "reference_shape_probabilities": dict(reference_shape_probabilities),
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
                "room_extent": float(render_params.room_extent),
                "full_bleed_floor": bool(render_params.full_bleed_floor),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered.scene_bbox_px),
                "room_bbox_px": list(rendered.room_bbox_px),
                "object_bboxes_px": dict(rendered.object_bboxes_px),
                "object_centers_px": dict(rendered.object_centers_px),
                "target_object_bboxes_px": {
                    str(object_id): list(rendered.object_bboxes_px[str(object_id)])
                    for object_id in target_object_ids
                },
                "target_object_centers_px": {
                    str(object_id): list(rendered.object_centers_px[str(object_id)])
                    for object_id in target_object_ids
                },
                "reference_object_bbox_px": list(rendered.object_bboxes_px[str(dataset["reference_object_id"])]),
                "reference_object_center_px": list(rendered.object_centers_px[str(dataset["reference_object_id"])]),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "object_count": int(dataset["object_count"]),
                "countable_object_count": int(dataset["countable_object_count"]),
                "target_count": int(answer_value),
                "answer_value": int(answer_value),
                "target_object_ids": list(target_object_ids),
                "reference_object_id": str(dataset["reference_object_id"]),
                "reference_object_name": str(dataset["reference_object_name"]),
                "reference_shape_type": str(dataset["reference_shape_type"]),
                "relation_status_by_object_id": dict(dataset["relation_status_by_object_id"]),
                "point_specs": [dict(spec) for spec in dataset["point_specs"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "shape_counts": dict(dataset["shape_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "counted_relation_object_set",
                "object_ids": list(target_object_ids),
                "reference_object_id": str(dataset["reference_object_id"]),
                "answer_value": int(answer_value),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
            },
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


__all__ = ["ThreeDObjectSceneRelationAttributeCountTask"]
