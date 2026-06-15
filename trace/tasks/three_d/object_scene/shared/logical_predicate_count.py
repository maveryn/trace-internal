"""Logical color/object predicate counting task for a synthetic 3D object scene."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from .....core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from .....core.types import TypedValue
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....base import TaskOutput
from ....shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.named_colors import available_named_colors
from ....shared.output_metadata import default_task_versions
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.task_support import normalize_unit as _normalize_unit
from ...shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ...shared.task_support import resolve_count as _shared_resolve_count
from ...shared.object_scene import (
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


SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID = "task_three_d__object_scene__single_attribute_membership_count"
MULTI_ATTRIBUTE_AND_COUNT_TASK_ID = "task_three_d__object_scene__multi_attribute_and_count"
MULTI_ATTRIBUTE_OR_COUNT_TASK_ID = "task_three_d__object_scene__multi_attribute_or_count"
MULTI_ATTRIBUTE_XOR_COUNT_TASK_ID = "task_three_d__object_scene__multi_attribute_xor_count"
MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID = "task_three_d__object_scene__multi_attribute_exclusion_count"
TASK_ID = SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID
SOURCE_ID = "three_d_object_scene_logical_predicate_count_source"
SINGLE_ATTRIBUTE_QUERY_IDS: Tuple[str, ...] = (
    "object_type_count",
    "object_type_union_count",
    "color_union_count",
)
MULTI_ATTRIBUTE_AND_QUERY_IDS: Tuple[str, ...] = ("object_type_and_color_count",)
MULTI_ATTRIBUTE_OR_QUERY_IDS: Tuple[str, ...] = ("object_type_or_color_count",)
MULTI_ATTRIBUTE_XOR_QUERY_IDS: Tuple[str, ...] = ("exactly_one_object_type_or_color_count",)
MULTI_ATTRIBUTE_EXCLUSION_QUERY_IDS: Tuple[str, ...] = (
    "object_type_and_not_color_count",
    "color_and_not_object_type_count",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    *SINGLE_ATTRIBUTE_QUERY_IDS,
    "object_type_and_color_count",
    "object_type_or_color_count",
    "exactly_one_object_type_or_color_count",
    "object_type_and_not_color_count",
    "color_and_not_object_type_count",
)
COLOR_SAFE_SHAPE_TYPES: Tuple[str, ...] = (
    "sphere",
    "cube",
    "cylinder",
    "cone",
    "torus",
    "pyramid",
    "wedge",
)
PROMPT_COLOR_RGB: Dict[str, Tuple[int, int, int]] = {
    str(name): (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    for name, rgb in available_named_colors()
}
COUNT_SCENE_SLOTS: Tuple[Tuple[float, float], ...] = tuple(
    (x, y)
    for y in (-2.42, -1.34, -0.26, 0.82, 1.90)
    for x in (-2.58, -1.48, -0.38, 0.72, 1.82, 2.70)
)
COUNTABLE_DIMENSION_SCALE = 1.12
MIN_PROJECTED_OBJECT_AREA_PX = 560.0
MAX_PAIRWISE_OVERLAP_PX = 3600.0


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / max(1, len(support))
    return {str(value): float(probability) for value in support}


def _selected_probability_map(values: Sequence[str], selected_values: Sequence[str]) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    selected = {str(value) for value in selected_values}
    probability = 1.0 / max(1, len(selected))
    return {str(value): (float(probability) if str(value) in selected else 0.0) for value in support}


def _object_plural(name: str) -> str:
    raw = str(name).strip()
    if raw in {"fish", "dice"}:
        return raw
    if raw.endswith("y") and (len(raw) < 2 or raw[-2].lower() not in {"a", "e", "i", "o", "u"}):
        return f"{raw[:-1]}ies"
    if raw.endswith(("s", "x", "z", "ch", "sh")):
        return f"{raw}es"
    return f"{raw}s"


def _object_name_for_shape(shape_type: str) -> str:
    probe = _make_object_spec(
        object_id="name_probe",
        shape_type=str(shape_type),
        object_role="candidate",
        xy=(0.0, 0.0),
        dimensions_xyz=(0.5, 0.5, 0.5),
        dimension_scale=1.0,
        label=None,
    )
    return str(probe["object_name"])


def _object_plural_for_shape(shape_type: str) -> str:
    return _object_plural(_object_name_for_shape(str(shape_type)))


def _join_with_or(items: Sequence[str]) -> str:
    values = [str(item) for item in items]
    if len(values) <= 1:
        return values[0] if values else ""
    if len(values) == 2:
        return f"{values[0]} or {values[1]}"
    return f"{', '.join(values[:-1])}, or {values[-1]}"


def _property_key(shape_type: str, color_name: str) -> Tuple[str, str]:
    return (str(shape_type), str(color_name))


def _all_exact_property_keys() -> List[Tuple[str, str]]:
    return [(str(shape), str(color)) for shape in COLOR_SAFE_SHAPE_TYPES for color in PROMPT_COLOR_RGB]


def _target_spec_matches_key(target_spec: Mapping[str, Any], key: Tuple[str, str]) -> bool:
    shape_type, color_name = _property_key(str(key[0]), str(key[1]))
    query_id = str(target_spec["query_id"])
    target_shape_type = target_spec.get("target_shape_type")
    target_color_name = target_spec.get("target_color_name")
    target_shape_types = {str(value) for value in target_spec.get("target_shape_types", [])}
    target_color_names = {str(value) for value in target_spec.get("target_color_names", [])}

    if query_id == "object_type_count":
        return str(shape_type) == str(target_shape_type)
    if query_id == "object_type_union_count":
        return str(shape_type) in target_shape_types
    if query_id == "color_union_count":
        return str(color_name) in target_color_names
    if query_id == "object_type_and_color_count":
        return str(shape_type) == str(target_shape_type) and str(color_name) == str(target_color_name)
    if query_id == "object_type_or_color_count":
        return str(shape_type) == str(target_shape_type) or str(color_name) == str(target_color_name)
    if query_id == "exactly_one_object_type_or_color_count":
        return (str(shape_type) == str(target_shape_type)) ^ (str(color_name) == str(target_color_name))
    if query_id == "object_type_and_not_color_count":
        return str(shape_type) == str(target_shape_type) and str(color_name) != str(target_color_name)
    if query_id == "color_and_not_object_type_count":
        return str(color_name) == str(target_color_name) and str(shape_type) != str(target_shape_type)
    raise ValueError(f"unsupported logical predicate query_id: {query_id}")


def _target_property_phrase(target_spec: Mapping[str, Any], *, count: int | None = None) -> str:
    query_id = str(target_spec["query_id"])
    amount = int(count) if count is not None else 2
    noun = "object" if int(amount) == 1 else "objects"
    target_shape_type = target_spec.get("target_shape_type")
    target_color_name = target_spec.get("target_color_name")
    target_object_plural = str(target_spec.get("target_object_plural", "objects"))

    if query_id == "object_type_count":
        return str(target_object_plural)
    if query_id == "object_type_union_count":
        return str(target_spec["target_object_union_phrase"])
    if query_id == "color_union_count":
        return str(target_spec["target_color_union_phrase"])
    if query_id == "object_type_and_color_count":
        object_name = _object_name_for_shape(str(target_shape_type))
        object_noun = object_name if int(amount) == 1 else _object_plural(object_name)
        return f"{target_color_name} {object_noun}"
    if query_id == "object_type_or_color_count":
        return f"{target_object_plural} or {target_color_name} {noun}"
    if query_id == "exactly_one_object_type_or_color_count":
        return f"{noun} that are either {target_object_plural} or {target_color_name}, but not both"
    if query_id == "object_type_and_not_color_count":
        return f"{target_object_plural} that are not {target_color_name}"
    if query_id == "color_and_not_object_type_count":
        return f"{target_color_name} {noun} that are not {target_object_plural}"
    raise ValueError(f"unsupported logical predicate query_id: {query_id}")


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _bbox_is_readable(bbox: Sequence[float], *, width: int, height: int, min_side_px: float = 18.0) -> bool:
    box_width = float(bbox[2]) - float(bbox[0])
    box_height = float(bbox[3]) - float(bbox[1])
    if box_width < float(min_side_px) or box_height < float(min_side_px):
        return False
    return float(bbox[2]) > 4.0 and float(bbox[3]) > 4.0 and float(bbox[0]) < float(width - 4) and float(bbox[1]) < float(height - 4)


def _scale_dimensions(dimensions_xyz: Sequence[float], scale: float) -> Tuple[float, float, float]:
    return tuple(round(float(value) * float(scale), 4) for value in dimensions_xyz)  # type: ignore[return-value]


def _make_countable_object(
    *,
    rng,
    object_id: str,
    shape_type: str,
    color_name: str,
    xy: Tuple[float, float],
    matches_query: bool,
) -> Dict[str, Any]:
    dimensions_xyz, dimension_scale = _sample_shape_dimensions(str(shape_type), object_role="candidate", rng=rng)
    scaled_dimensions = _scale_dimensions(dimensions_xyz, COUNTABLE_DIMENSION_SCALE)
    spec = _make_object_spec(
        object_id=str(object_id),
        shape_type=str(shape_type),
        object_role="candidate",
        xy=tuple(float(value) for value in xy),
        dimensions_xyz=scaled_dimensions,
        dimension_scale=float(dimension_scale) * float(COUNTABLE_DIMENSION_SCALE),
        label=None,
    )
    spec.update(
        {
            "is_answer_candidate": False,
            "is_countable_object": True,
            "matches_query": bool(matches_query),
            "count_role": "target" if bool(matches_query) else "distractor",
            "color_name": str(color_name),
            "prompt_color_name": str(color_name),
            "fill_rgb": [int(channel) for channel in PROMPT_COLOR_RGB[str(color_name)]],
        }
    )
    return spec


def _can_place(candidate: Mapping[str, Any], placed: Sequence[Mapping[str, Any]], *, clearance: float = 0.16) -> bool:
    cx, cy, _cz = (float(value) for value in candidate["world_xyz"])
    for item in placed:
        ix, iy, _iz = (float(value) for value in item["world_xyz"])
        min_distance = float(candidate["footprint_radius"]) + float(item["footprint_radius"]) + float(clearance)
        if math.hypot(float(cx - ix), float(cy - iy)) < float(min_distance):
            return False
    return True


def _preferred_distractor_keys(target_spec: Mapping[str, Any]) -> List[Tuple[str, str]]:
    target_shape_type = target_spec.get("target_shape_type")
    target_color_name = target_spec.get("target_color_name")
    target_shape_types = {str(value) for value in target_spec.get("target_shape_types", [])}
    target_color_names = {str(value) for value in target_spec.get("target_color_names", [])}
    preferred: List[Tuple[str, str]] = []
    if target_shape_type is not None:
        preferred.extend((str(target_shape_type), str(color)) for color in PROMPT_COLOR_RGB if str(color) != str(target_color_name))
    if target_color_name is not None:
        preferred.extend((str(shape), str(target_color_name)) for shape in COLOR_SAFE_SHAPE_TYPES if str(shape) != str(target_shape_type))
    for shape_type in target_shape_types:
        preferred.extend((str(shape_type), str(color)) for color in PROMPT_COLOR_RGB)
    for color_name in target_color_names:
        preferred.extend((str(shape), str(color_name)) for shape in COLOR_SAFE_SHAPE_TYPES)
    seen: set[Tuple[str, str]] = set()
    filtered: List[Tuple[str, str]] = []
    for key in preferred:
        normalized = _property_key(str(key[0]), str(key[1]))
        if normalized in seen or _target_spec_matches_key(target_spec, normalized):
            continue
        seen.add(normalized)
        filtered.append(normalized)
    return list(filtered)


def _sample_shape_color_sequence(
    *,
    rng,
    target_spec: Mapping[str, Any],
    target_count: int,
    object_count: int,
) -> List[Tuple[str, str, bool]]:
    matching_pairs = [key for key in _all_exact_property_keys() if _target_spec_matches_key(target_spec, key)]
    all_distractors = [key for key in _all_exact_property_keys() if not _target_spec_matches_key(target_spec, key)]
    if not matching_pairs or not all_distractors:
        raise ValueError("logical predicate needs both matching and distractor property support")

    sequence: List[Tuple[str, str, bool]] = []
    for _ in range(int(target_count)):
        shape_type, color_name = tuple(rng.choice(matching_pairs))
        sequence.append((str(shape_type), str(color_name), True))

    preferred = _preferred_distractor_keys(target_spec)
    rng.shuffle(preferred)
    for shape_type, color_name in preferred[:3]:
        if len(sequence) >= int(object_count):
            break
        sequence.append((str(shape_type), str(color_name), False))

    rng.shuffle(all_distractors)
    distractor_index = 0
    while len(sequence) < int(object_count):
        shape_type, color_name = all_distractors[int(distractor_index) % len(all_distractors)]
        sequence.append((str(shape_type), str(color_name), False))
        distractor_index += 1
    rng.shuffle(sequence)
    return list(sequence)


def _place_countable_objects(
    *,
    rng,
    shape_color_sequence: Sequence[Tuple[str, str, bool]],
) -> List[Dict[str, Any]]:
    slots = list(COUNT_SCENE_SLOTS)
    rng.shuffle(slots)
    placed: List[Dict[str, Any]] = []
    for index, (shape_type, color_name, matches_query) in enumerate(shape_color_sequence):
        for slot_index, (slot_x, slot_y) in enumerate(list(slots)):
            candidate_xy = (
                float(slot_x + rng.uniform(-0.14, 0.14)),
                float(slot_y + rng.uniform(-0.14, 0.14)),
            )
            spec = _make_countable_object(
                rng=rng,
                object_id=f"logical_object_{int(index):02d}",
                shape_type=str(shape_type),
                color_name=str(color_name),
                xy=candidate_xy,
                matches_query=bool(matches_query),
            )
            if _can_place(spec, placed):
                placed.append(spec)
                slots.pop(int(slot_index))
                break
        else:
            raise ValueError("could not place enough logical predicate count 3D objects")
    return list(placed)


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
    specs: Sequence[Mapping[str, Any]],
    camera,
    frame,
    render_params: _RenderParams,
) -> bool:
    bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=8.0) for spec in specs]
    if any(not _bbox_is_readable(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height)) for bbox in bboxes):
        return False
    if any(_bbox_area(bbox) < MIN_PROJECTED_OBJECT_AREA_PX for bbox in bboxes):
        return False
    for index, bbox_a in enumerate(bboxes):
        for bbox_b in bboxes[index + 1 :]:
            overlap = _bbox_intersection_area(bbox_a, bbox_b)
            if overlap > MAX_PAIRWISE_OVERLAP_PX:
                return False
            if overlap > 0.42 * min(_bbox_area(bbox_a), _bbox_area(bbox_b)):
                return False
    return True


def _build_logical_count_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    target_spec: Mapping[str, Any],
    target_count: int,
    object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{SOURCE_ID}.dataset")
    selected_camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
    for _attempt in range(520):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        sequence = _sample_shape_color_sequence(
            rng=rng,
            target_spec=target_spec,
            target_count=int(target_count),
            object_count=int(object_count),
        )
        object_specs = _place_countable_objects(rng=rng, shape_color_sequence=sequence)
        reference_points = [point for spec in object_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _view_is_valid(specs=object_specs, camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_specs = _finalize_specs(object_specs, camera=camera, frame=frame)
        match_specs = [spec for spec in finalized_specs if _target_spec_matches_key(target_spec, _property_key(str(spec["shape_type"]), str(spec["color_name"])))]
        if len(match_specs) != int(target_count):
            continue
        distances = [float(spec["camera_distance"]) for spec in finalized_specs]
        shape_counts = Counter(str(spec["shape_type"]) for spec in finalized_specs)
        color_counts = Counter(str(spec["color_name"]) for spec in finalized_specs)
        property_counts = Counter(_property_key(str(spec["shape_type"]), str(spec["color_name"])) for spec in finalized_specs)
        target_object_ids = [str(spec["object_id"]) for spec in sorted(match_specs, key=lambda item: str(item["object_id"]))]
        dataset_target_spec = dict(target_spec)
        dataset_target_spec["target_property_phrase"] = _target_property_phrase(dataset_target_spec, count=int(target_count))
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "object_count": int(object_count),
            "countable_object_count": int(object_count),
            "target_count": int(target_count),
            "answer_value": int(target_count),
            "target_spec": dict(dataset_target_spec),
            "target_shape_type": dataset_target_spec.get("target_shape_type"),
            "target_shape_types": list(dataset_target_spec.get("target_shape_types", [])),
            "target_object_name": dataset_target_spec.get("target_object_name"),
            "target_object_plural": dataset_target_spec.get("target_object_plural"),
            "target_object_union_phrase": dataset_target_spec.get("target_object_union_phrase"),
            "target_color_name": dataset_target_spec.get("target_color_name"),
            "target_color_names": list(dataset_target_spec.get("target_color_names", [])),
            "target_color_union_phrase": dataset_target_spec.get("target_color_union_phrase"),
            "target_property_phrase": str(dataset_target_spec["target_property_phrase"]),
            "target_object_ids": list(target_object_ids),
            "object_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "point_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "context_object_specs": [],
            "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
            "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
            "property_counts": {
                f"{color_name}_{shape_type}": int(count)
                for (shape_type, color_name), count in sorted(property_counts.items())
            },
            "camera": _camera_record(camera, yaw_band=selected_camera_yaw_band),
            "projection_frame": _frame_record(frame),
            "solver_trace": {
                "count_predicate": str(query_id),
                "target_spec": dict(dataset_target_spec),
                "target_property_phrase": str(dataset_target_spec["target_property_phrase"]),
                "target_count": int(target_count),
                "target_object_ids": list(target_object_ids),
                "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
                "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
                "property_counts": {
                    f"{color_name}_{shape_type}": int(count)
                    for (shape_type, color_name), count in sorted(property_counts.items())
                },
                "unique_integer_answer": True,
                "minimum_pairwise_camera_distance_margin": round(float(_min_pairwise(distances)), 4),
            },
        }
    raise ValueError("could not construct a valid 3D logical predicate count scene")


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


def _predicate_logic_load(query_id: str) -> float:
    return {
        "object_type_union_count": 0.42,
        "color_union_count": 0.42,
        "object_type_and_color_count": 0.46,
        "object_type_or_color_count": 0.70,
        "exactly_one_object_type_or_color_count": 0.88,
        "object_type_and_not_color_count": 0.72,
        "color_and_not_object_type_count": 0.72,
    }.get(str(query_id), 0.55)




def _resolve_string_subset(
    *,
    params: Mapping[str, Any],
    key: str,
    support: Sequence[str],
    instance_seed: int,
    namespace: str,
    count: int,
) -> Tuple[List[str], Dict[str, float], bool]:
    support_values = tuple(str(value) for value in support)
    explicit_value = params.get(str(key))
    if explicit_value is not None:
        if isinstance(explicit_value, str):
            selected_values = [value.strip() for value in explicit_value.split(",") if value.strip()]
        else:
            selected_values = [str(value) for value in explicit_value]
        if len(selected_values) != len(set(selected_values)):
            raise ValueError(f"{key} contains duplicate values")
        unsupported = [value for value in selected_values if value not in set(support_values)]
        if unsupported:
            raise ValueError(f"unsupported {key} values for {TASK_ID}: {unsupported}")
        if not selected_values:
            raise ValueError(f"{key} must not be empty")
        return list(selected_values), _selected_probability_map(support_values, selected_values), True

    start_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    ordered = list(support_values)
    rng = spawn_rng(int(instance_seed), f"{namespace}.shuffle")
    rng.shuffle(ordered)
    selected = [str(ordered[(abs(int(start_index)) + offset) % len(ordered)]) for offset in range(int(count))]
    return list(selected), _selected_probability_map(support_values, selected), False


def _build_target_spec(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, float]]:
    shape_support = tuple(str(shape) for shape in COLOR_SAFE_SHAPE_TYPES)
    color_support = tuple(str(color) for color in PROMPT_COLOR_RGB)
    query = str(query_id)

    if query == "object_type_count":
        explicit_shape = params.get("target_shape_type")
        if explicit_shape is not None:
            target_shape_type = str(explicit_shape)
            if target_shape_type not in set(shape_support):
                raise ValueError(f"unsupported target_shape_type for {task_id}: {target_shape_type}")
        else:
            shape_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.{query}.target_shape_type",
            )
            target_shape_type = str(shape_support[abs(int(shape_index)) % len(shape_support)])
        object_name = _object_name_for_shape(str(target_shape_type))
        object_plural = _object_plural(str(object_name))
        target_spec = {
            "query_id": str(query),
            "target_shape_type": str(target_shape_type),
            "target_object_name": str(object_name),
            "target_object_plural": str(object_plural),
        }
        target_spec["target_property_phrase"] = _target_property_phrase(target_spec)
        return dict(target_spec), _uniform_string_probability_map(
            shape_support,
            selected=str(target_shape_type) if explicit_shape is not None else None,
        ), {}

    if query == "object_type_union_count":
        union_count = 3 if int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.target_shape_union_count")) % 3 == 0 else 2
        target_shape_types, shape_probabilities, _explicit = _resolve_string_subset(
            params=params,
            key="target_shape_types",
            support=shape_support,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_shape_types",
            count=int(union_count),
        )
        if len(target_shape_types) < 2:
            raise ValueError(f"object_type_union_count requires at least two target_shape_types for {task_id}")
        target_object_plurals = [_object_plural_for_shape(shape) for shape in target_shape_types]
        target_spec = {
            "query_id": str(query),
            "target_shape_types": list(target_shape_types),
            "target_object_plurals": list(target_object_plurals),
            "target_object_union_phrase": _join_with_or(target_object_plurals),
        }
        return dict(target_spec), dict(shape_probabilities), {}

    if query == "color_union_count":
        target_color_names, color_probabilities, _explicit = _resolve_string_subset(
            params=params,
            key="target_color_names",
            support=color_support,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_color_names",
            count=2,
        )
        if len(target_color_names) < 2:
            raise ValueError(f"color_union_count requires at least two target_color_names for {task_id}")
        target_spec = {
            "query_id": str(query),
            "target_color_names": list(target_color_names),
            "target_color_union_phrase": _join_with_or([f"{color} objects" for color in target_color_names]),
        }
        return dict(target_spec), {}, dict(color_probabilities)

    explicit_shape = params.get("target_shape_type")
    if explicit_shape is not None:
        target_shape_type = str(explicit_shape)
        if target_shape_type not in set(shape_support):
            raise ValueError(f"unsupported target_shape_type for {task_id}: {target_shape_type}")
    else:
        shape_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query}.target_shape_type",
        )
        target_shape_type = str(shape_support[abs(int(shape_index)) % len(shape_support)])
    shape_probabilities = _uniform_string_probability_map(
        shape_support,
        selected=str(target_shape_type) if explicit_shape is not None else None,
    )

    explicit_color = params.get("target_color_name")
    if explicit_color is not None:
        target_color_name = str(explicit_color)
        if target_color_name not in set(color_support):
            raise ValueError(f"unsupported target_color_name for {task_id}: {target_color_name}")
    else:
        color_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query}.target_color_name",
        )
        target_color_name = str(color_support[abs(int(color_index)) % len(color_support)])
    color_probabilities = _uniform_string_probability_map(
        color_support,
        selected=str(target_color_name) if explicit_color is not None else None,
    )

    object_name = _object_name_for_shape(str(target_shape_type))
    object_plural = _object_plural(str(object_name))
    target_spec = {
        "query_id": str(query),
        "target_shape_type": str(target_shape_type),
        "target_object_name": str(object_name),
        "target_object_plural": str(object_plural),
        "target_color_name": str(target_color_name),
    }
    target_spec["target_property_phrase"] = _target_property_phrase(target_spec)
    return dict(target_spec), dict(shape_probabilities), dict(color_probabilities)


_SCENE_DEFAULTS = get_scene_defaults("three_d", SCENE_ID)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


def _resolve_task_defaults(task_id: str) -> Tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    gen_defaults, render_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )


class _ThreeDSpatialLogicalPredicateCountBase:
    """Count objects satisfying a static logical type/color predicate."""

    task_id = TASK_ID
    supported_query_ids: Tuple[str, ...] = SUPPORTED_QUERY_IDS
    domain = "three_d"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_id = str(self.task_id)
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{task_id}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        task_id = str(self.task_id)
        query_id, query_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=task_id,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            supported_variants=self.supported_query_ids,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
        )
        scene_variant, scene_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=task_id,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        object_count, object_count_probabilities = _shared_resolve_count(
            params,
            task_id=task_id,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            prefix="object_count",
            minimum_default=int(group_default(gen_defaults, "object_count_min", 12)),
            maximum_default=int(group_default(gen_defaults, "object_count_max", 15)),
            lower=8,
            upper=20,
        )
        target_count, target_count_probabilities = _shared_resolve_count(
            params,
            task_id=task_id,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            prefix="target_count",
            minimum_default=int(group_default(gen_defaults, "target_count_min", 2)),
            maximum_default=int(group_default(gen_defaults, "target_count_max", 5)),
            lower=1,
            upper=max(1, min(8, int(object_count) - 4)),
        )
        target_spec, target_shape_probabilities, target_color_probabilities = _build_target_spec(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
            task_id=task_id,
        )

        render_params = _resolve_render_params(params, render_defaults=render_defaults)
        dataset = _build_logical_count_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            target_spec=target_spec,
            target_count=int(target_count),
            object_count=int(object_count),
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
            prompt_defaults_config,
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
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_shape_type": str(dataset.get("target_shape_type") or ""),
                "target_object_name": str(dataset.get("target_object_name") or ""),
                "target_object_plural": str(dataset.get("target_object_plural") or ""),
                "target_object_union_phrase": str(dataset.get("target_object_union_phrase") or ""),
                "target_color_name": str(dataset.get("target_color_name") or ""),
                "target_color_union_phrase": str(dataset.get("target_color_union_phrase") or ""),
                "target_property_phrase": str(dataset["target_property_phrase"]),
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

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene_logical_predicate_count",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "object_count": int(object_count),
                    "countable_object_count": int(object_count),
                    "target_spec": dict(dataset["target_spec"]),
                    "target_property_phrase": str(dataset["target_property_phrase"]),
                    "target_count": int(answer_value),
                    "target_object_ids": list(target_object_ids),
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
                    "target_spec": dict(dataset["target_spec"]),
                    "target_shape_type": dataset.get("target_shape_type"),
                    "target_shape_types": list(dataset.get("target_shape_types", [])),
                    "target_shape_type_probabilities": dict(target_shape_probabilities),
                    "target_color_name": dataset.get("target_color_name"),
                    "target_color_names": list(dataset.get("target_color_names", [])),
                    "target_color_name_probabilities": dict(target_color_probabilities),
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
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "object_count": int(object_count),
                "countable_object_count": int(object_count),
                "target_count": int(answer_value),
                "answer_value": int(answer_value),
                "target_spec": dict(dataset["target_spec"]),
                "target_shape_type": dataset.get("target_shape_type"),
                "target_shape_types": list(dataset.get("target_shape_types", [])),
                "target_object_name": dataset.get("target_object_name"),
                "target_object_plural": dataset.get("target_object_plural"),
                "target_object_union_phrase": dataset.get("target_object_union_phrase"),
                "target_color_name": dataset.get("target_color_name"),
                "target_color_names": list(dataset.get("target_color_names", [])),
                "target_color_union_phrase": dataset.get("target_color_union_phrase"),
                "target_property_phrase": str(dataset["target_property_phrase"]),
                "target_object_ids": list(target_object_ids),
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "shape_counts": dict(dataset["shape_counts"]),
                "color_counts": dict(dataset["color_counts"]),
                "property_counts": dict(dataset["property_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "logical_predicate_count_object_set",
                "object_ids": list(target_object_ids),
                "target_spec": dict(dataset["target_spec"]),
                "target_property_phrase": str(dataset["target_property_phrase"]),
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = [
    "MULTI_ATTRIBUTE_AND_COUNT_TASK_ID",
    "MULTI_ATTRIBUTE_AND_QUERY_IDS",
    "MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID",
    "MULTI_ATTRIBUTE_EXCLUSION_QUERY_IDS",
    "MULTI_ATTRIBUTE_OR_COUNT_TASK_ID",
    "MULTI_ATTRIBUTE_OR_QUERY_IDS",
    "MULTI_ATTRIBUTE_XOR_COUNT_TASK_ID",
    "MULTI_ATTRIBUTE_XOR_QUERY_IDS",
    "SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID",
    "SINGLE_ATTRIBUTE_QUERY_IDS",
    "_ThreeDSpatialLogicalPredicateCountBase",
]
