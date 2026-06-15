"""Counterfactual color/object counting task for a synthetic 3D object scene."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.named_colors import available_named_colors
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.object_scene import (
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


TASK_ID = "task_three_d__object_scene__counterfactual_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("attribute_count_after_edits",)
QUERY_ID_ALIASES: Dict[str, str] = {"shape_color_count_after_edits": "attribute_count_after_edits"}
PREDICATE_KINDS: Tuple[str, ...] = ("color", "object", "color_object")
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


def _property_key(shape_type: str, color_name: str) -> Tuple[str, str]:
    return (str(shape_type), str(color_name))


def _make_predicate(*, predicate_kind: str, shape_type: str | None = None, color_name: str | None = None) -> Dict[str, Any]:
    kind = str(predicate_kind)
    if kind not in set(PREDICATE_KINDS):
        raise ValueError(f"unsupported counterfactual predicate kind: {predicate_kind}")
    if kind in {"object", "color_object"} and not shape_type:
        raise ValueError(f"predicate kind {kind} requires shape_type")
    if kind in {"color", "color_object"} and not color_name:
        raise ValueError(f"predicate kind {kind} requires color_name")
    return {
        "predicate_kind": str(kind),
        "shape_type": str(shape_type) if shape_type is not None else None,
        "color_name": str(color_name) if color_name is not None else None,
    }


def _predicate_matches_key(predicate: Mapping[str, Any], key: Tuple[str, str]) -> bool:
    shape_type, color_name = _property_key(str(key[0]), str(key[1]))
    predicate_shape = predicate.get("shape_type")
    predicate_color = predicate.get("color_name")
    if predicate_shape is not None and str(predicate_shape) != str(shape_type):
        return False
    if predicate_color is not None and str(predicate_color) != str(color_name):
        return False
    return True


def _predicate_relation_to_target(edit_predicate: Mapping[str, Any], target_predicate: Mapping[str, Any]) -> str:
    edit_shape = edit_predicate.get("shape_type")
    edit_color = edit_predicate.get("color_name")
    target_shape = target_predicate.get("shape_type")
    target_color = target_predicate.get("color_name")

    if edit_shape is not None and target_shape is not None and str(edit_shape) != str(target_shape):
        return "disjoint"
    if edit_color is not None and target_color is not None and str(edit_color) != str(target_color):
        return "disjoint"

    target_attrs = {"shape_type": target_shape, "color_name": target_color}
    edit_attrs = {"shape_type": edit_shape, "color_name": edit_color}
    is_subset = True
    for attr_name, target_value in target_attrs.items():
        if target_value is None:
            continue
        edit_value = edit_attrs[attr_name]
        if edit_value is None or str(edit_value) != str(target_value):
            is_subset = False
            break
    return "subset" if bool(is_subset) else "ambiguous"


def _predicate_phrase(predicate: Mapping[str, Any], *, count: int | None = None) -> str:
    kind = str(predicate["predicate_kind"])
    amount = int(count) if count is not None else 2
    shape_type = predicate.get("shape_type")
    color_name = predicate.get("color_name")
    if kind == "color":
        noun = "object" if int(amount) == 1 else "objects"
        return f"{color_name} {noun}"
    if kind == "object":
        object_name = _object_name_for_shape(str(shape_type))
        noun = object_name if int(amount) == 1 else _object_plural(object_name)
        return str(noun)
    if kind == "color_object":
        object_name = _object_name_for_shape(str(shape_type))
        noun = object_name if int(amount) == 1 else _object_plural(object_name)
        return f"{color_name} {noun}"
    raise ValueError(f"unsupported predicate kind: {kind}")


def _quantity_phrase(amount: int, predicate: Mapping[str, Any]) -> str:
    return f"{int(amount)} {_predicate_phrase(predicate, count=int(amount))}"


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
            "count_role": "initial_target" if bool(matches_query) else "distractor",
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


def _all_exact_property_keys() -> List[Tuple[str, str]]:
    return [(str(shape), str(color)) for shape in COLOR_SAFE_SHAPE_TYPES for color in PROMPT_COLOR_RGB]


def _sample_shape_color_sequence(
    *,
    rng,
    target_predicate: Mapping[str, Any],
    target_count: int,
    object_count: int,
) -> List[Tuple[str, str, bool]]:
    color_names = list(PROMPT_COLOR_RGB)
    shape_types = list(COLOR_SAFE_SHAPE_TYPES)
    matching_pairs = [key for key in _all_exact_property_keys() if _predicate_matches_key(target_predicate, key)]
    all_distractors = [key for key in _all_exact_property_keys() if not _predicate_matches_key(target_predicate, key)]
    if not matching_pairs or not all_distractors:
        raise ValueError("counterfactual predicate has no matching or distractor property support")

    sequence: List[Tuple[str, str, bool]] = []
    for _ in range(int(target_count)):
        shape_type, color_name = tuple(rng.choice(matching_pairs))
        sequence.append((str(shape_type), str(color_name), True))

    target_shape = target_predicate.get("shape_type")
    target_color = target_predicate.get("color_name")
    preferred_distractors: List[Tuple[str, str]] = []
    if target_shape is not None:
        preferred_distractors.extend((str(target_shape), str(color)) for color in color_names if color != target_color)
    if target_color is not None:
        preferred_distractors.extend((str(shape), str(target_color)) for shape in shape_types if shape != target_shape)
    preferred_distractors = [
        _property_key(shape, color)
        for shape, color in preferred_distractors
        if not _predicate_matches_key(target_predicate, _property_key(shape, color))
    ]
    rng.shuffle(preferred_distractors)
    for shape, color in preferred_distractors[:2]:
        if len(sequence) >= int(object_count):
            break
        sequence.append((str(shape), str(color), False))

    rng.shuffle(all_distractors)
    distractor_index = 0
    while len(sequence) < int(object_count):
        shape, color = all_distractors[int(distractor_index) % len(all_distractors)]
        sequence.append((str(shape), str(color), False))
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
                object_id=f"counter_object_{int(index):02d}",
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
            raise ValueError("could not place enough counterfactual count 3D objects")
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


def _predicate_count(current_counts: Counter[Tuple[str, str]], predicate: Mapping[str, Any]) -> int:
    return int(sum(int(count) for key, count in current_counts.items() if _predicate_matches_key(predicate, key)))


def _candidate_edit_predicates(target_predicate: Mapping[str, Any], *, relation: str) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for color_name in PROMPT_COLOR_RGB:
        candidates.append(_make_predicate(predicate_kind="color", color_name=str(color_name)))
    for shape_type in COLOR_SAFE_SHAPE_TYPES:
        candidates.append(_make_predicate(predicate_kind="object", shape_type=str(shape_type)))
    for shape_type in COLOR_SAFE_SHAPE_TYPES:
        for color_name in PROMPT_COLOR_RGB:
            candidates.append(
                _make_predicate(
                    predicate_kind="color_object",
                    shape_type=str(shape_type),
                    color_name=str(color_name),
                )
            )
    return [
        predicate
        for predicate in candidates
        if _predicate_relation_to_target(predicate, target_predicate) == str(relation)
    ]


def _remove_from_counts(
    *,
    rng,
    current_counts: Counter[Tuple[str, str]],
    predicate: Mapping[str, Any],
    amount: int,
) -> Dict[str, int]:
    remaining = int(amount)
    exact_keys = [key for key in _all_exact_property_keys() if _predicate_matches_key(predicate, key) and int(current_counts[key]) > 0]
    rng.shuffle(exact_keys)
    removed: Dict[str, int] = {}
    for key in exact_keys:
        if remaining <= 0:
            break
        take = min(int(current_counts[key]), int(remaining))
        current_counts[key] -= int(take)
        removed[f"{key[1]}_{key[0]}"] = int(take)
        remaining -= int(take)
    if remaining != 0:
        raise ValueError("counterfactual step would remove more objects than available")
    return dict(removed)


def _add_to_counts(
    *,
    rng,
    current_counts: Counter[Tuple[str, str]],
    predicate: Mapping[str, Any],
    amount: int,
) -> Dict[str, int]:
    exact_keys = [key for key in _all_exact_property_keys() if _predicate_matches_key(predicate, key)]
    if not exact_keys:
        raise ValueError("counterfactual add predicate has no exact support")
    rng.shuffle(exact_keys)
    added: Dict[str, int] = {}
    for index in range(int(amount)):
        key = exact_keys[int(index) % len(exact_keys)]
        current_counts[key] += 1
        added[f"{key[1]}_{key[0]}"] = int(added.get(f"{key[1]}_{key[0]}", 0)) + 1
    return dict(added)


def _sample_edit_step(
    *,
    rng,
    current_counts: Counter[Tuple[str, str]],
    target_predicate: Mapping[str, Any],
    relation: str,
) -> Dict[str, Any]:
    candidate_predicates = _candidate_edit_predicates(target_predicate, relation=str(relation))
    rng.shuffle(candidate_predicates)
    prefer_remove = bool(rng.random() < 0.45)
    operations = ("remove", "add") if prefer_remove else ("add", "remove")
    for operation in operations:
        for predicate in candidate_predicates:
            available = _predicate_count(current_counts, predicate)
            if operation == "remove" and int(available) <= 0:
                continue
            max_amount = min(2, int(available)) if operation == "remove" else 2
            if max_amount <= 0:
                continue
            amount = int(rng.randint(1, int(max_amount)))
            relation_to_target = _predicate_relation_to_target(predicate, target_predicate)
            target_delta = int(amount) if str(operation) == "add" else -int(amount)
            if relation_to_target == "disjoint":
                target_delta = 0
            if relation_to_target == "ambiguous":
                continue
            if operation == "remove":
                exact_deltas = _remove_from_counts(
                    rng=rng,
                    current_counts=current_counts,
                    predicate=predicate,
                    amount=int(amount),
                )
            else:
                exact_deltas = _add_to_counts(
                    rng=rng,
                    current_counts=current_counts,
                    predicate=predicate,
                    amount=int(amount),
                )
            return {
                "operation": str(operation),
                "amount": int(amount),
                "predicate": dict(predicate),
                "predicate_kind": str(predicate["predicate_kind"]),
                "shape_type": predicate.get("shape_type"),
                "object_name": _object_name_for_shape(str(predicate["shape_type"]))
                if predicate.get("shape_type") is not None
                else None,
                "object_plural": _object_plural(_object_name_for_shape(str(predicate["shape_type"])))
                if predicate.get("shape_type") is not None
                else None,
                "color_name": predicate.get("color_name"),
                "property_phrase": _predicate_phrase(predicate),
                "predicate_relation_to_target": str(relation_to_target),
                "affects_target_property": bool(relation_to_target == "subset"),
                "target_delta": int(target_delta),
                "exact_property_deltas": dict(exact_deltas),
            }
    raise ValueError(f"could not sample {relation} counterfactual edit step")


def _build_counterfactual_steps(
    *,
    rng,
    initial_counts: Counter[Tuple[str, str]],
    target_predicate: Mapping[str, Any],
    edit_step_count: int,
) -> Tuple[List[Dict[str, Any]], str, int]:
    current_counts: Counter[Tuple[str, str]] = Counter(initial_counts)
    initial_target_count = _predicate_count(current_counts, target_predicate)
    target_step_indices = {0}
    if int(edit_step_count) >= 3:
        target_step_indices.add(2)
    steps: List[Dict[str, Any]] = []
    for step_index in range(int(edit_step_count)):
        relation = "subset" if int(step_index) in target_step_indices else "disjoint"
        step = _sample_edit_step(
            rng=rng,
            current_counts=current_counts,
            target_predicate=target_predicate,
            relation=str(relation),
        )
        verb = "Add" if str(step["operation"]) == "add" else "Remove"
        step_text = f"{verb} {_quantity_phrase(int(step['amount']), step['predicate'])}."
        step.update({"step_index": int(step_index) + 1, "step_text": str(step_text)})
        steps.append(dict(step))
    final_target_count = _predicate_count(current_counts, target_predicate)
    if final_target_count == initial_target_count:
        raise ValueError("counterfactual target count did not change")
    edit_steps_text = "\n".join(f"{step['step_index']}. {step['step_text']}" for step in steps)
    return list(steps), str(edit_steps_text), int(final_target_count)


def _build_counterfactual_count_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    target_predicate: Mapping[str, Any],
    target_count: int,
    object_count: int,
    edit_step_count: int,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    selected_camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
    for _attempt in range(520):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        sequence = _sample_shape_color_sequence(
            rng=rng,
            target_predicate=target_predicate,
            target_count=int(target_count),
            object_count=int(object_count),
        )
        object_specs = _place_countable_objects(rng=rng, shape_color_sequence=sequence)
        reference_points = [point for spec in object_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _view_is_valid(specs=object_specs, camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_specs = _finalize_specs(object_specs, camera=camera, frame=frame)
        initial_target_specs = [spec for spec in finalized_specs if bool(spec.get("matches_query", False))]
        if len(initial_target_specs) != int(target_count):
            continue
        initial_counts: Counter[Tuple[str, str]] = Counter(
            _property_key(str(spec["shape_type"]), str(spec["color_name"])) for spec in finalized_specs
        )
        try:
            counterfactual_steps, edit_steps_text, final_count = _build_counterfactual_steps(
                rng=rng,
                initial_counts=initial_counts,
                target_predicate=target_predicate,
                edit_step_count=int(edit_step_count),
            )
        except ValueError:
            continue
        distances = [float(spec["camera_distance"]) for spec in finalized_specs]
        target_shape_type = target_predicate.get("shape_type")
        target_color_name = target_predicate.get("color_name")
        target_name = _object_name_for_shape(str(target_shape_type)) if target_shape_type is not None else None
        target_object_ids = [str(spec["object_id"]) for spec in sorted(initial_target_specs, key=lambda item: str(item["object_id"]))]
        property_counts = {
            f"{color_name}_{shape_type}": int(count)
            for (shape_type, color_name), count in sorted(initial_counts.items())
        }
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "object_count": int(object_count),
            "countable_object_count": int(object_count),
            "initial_target_count": int(target_count),
            "answer_value": int(final_count),
            "target_predicate": dict(target_predicate),
            "target_predicate_kind": str(target_predicate["predicate_kind"]),
            "target_shape_type": str(target_shape_type) if target_shape_type is not None else None,
            "target_object_name": str(target_name) if target_name is not None else None,
            "target_object_plural": _object_plural(str(target_name)) if target_name is not None else None,
            "target_color_name": str(target_color_name) if target_color_name is not None else None,
            "target_property_phrase": _predicate_phrase(target_predicate),
            "target_object_ids": list(target_object_ids),
            "object_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "point_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "context_object_specs": [],
            "initial_property_counts": dict(property_counts),
            "counterfactual_steps": list(counterfactual_steps),
            "edit_steps_text": str(edit_steps_text),
            "camera": _camera_record(camera, yaw_band=selected_camera_yaw_band),
            "projection_frame": _frame_record(frame),
            "solver_trace": {
                "count_predicate": "final count of target color/object predicate after counterfactual edits",
                "target_predicate": dict(target_predicate),
                "target_predicate_kind": str(target_predicate["predicate_kind"]),
                "target_shape_type": str(target_shape_type) if target_shape_type is not None else None,
                "target_object_plural": _object_plural(str(target_name)) if target_name is not None else None,
                "target_color_name": str(target_color_name) if target_color_name is not None else None,
                "target_property_phrase": _predicate_phrase(target_predicate),
                "initial_target_count": int(target_count),
                "counterfactual_steps": list(counterfactual_steps),
                "final_target_count": int(final_count),
                "target_delta_total": int(final_count) - int(target_count),
                "initial_target_object_ids": list(target_object_ids),
                "initial_property_counts": dict(property_counts),
                "minimum_pairwise_camera_distance_margin": round(float(_min_pairwise(distances)), 4),
                "unique_integer_answer": True,
            },
        }
    raise ValueError("could not construct a valid 3D counterfactual attribute count scene")


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




_SCENE_DEFAULTS = get_scene_defaults("three_d", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


@register_task
class ThreeDObjectSceneCounterfactualCountTask:
    """Count a color/object property after textual add/remove edits."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params)
        if str(params.get("query_id", "")) in QUERY_ID_ALIASES:
            params["query_id"] = str(QUERY_ID_ALIASES[str(params["query_id"])])
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
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
            minimum_default=int(group_default(_GEN_DEFAULTS, "object_count_min", 12)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "object_count_max", 15)),
            lower=8,
            upper=20,
        )
        target_count, target_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="target_count",
            minimum_default=int(group_default(_GEN_DEFAULTS, "target_count_min", 2)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "target_count_max", 5)),
            lower=1,
            upper=max(1, min(8, int(object_count) - 4)),
        )
        edit_step_count, edit_step_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="edit_step_count",
            minimum_default=int(group_default(_GEN_DEFAULTS, "edit_step_count_min", 2)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "edit_step_count_max", 3)),
            lower=1,
            upper=3,
        )

        predicate_kind_support = tuple(str(kind) for kind in PREDICATE_KINDS)
        explicit_predicate_kind = params.get("target_predicate_kind")
        if explicit_predicate_kind is None:
            if params.get("target_shape_type") is not None and params.get("target_color_name") is not None:
                explicit_predicate_kind = "color_object"
            elif params.get("target_shape_type") is not None:
                explicit_predicate_kind = "object"
            elif params.get("target_color_name") is not None:
                explicit_predicate_kind = "color"
        if explicit_predicate_kind is not None:
            target_predicate_kind = str(explicit_predicate_kind)
            if target_predicate_kind not in set(predicate_kind_support):
                raise ValueError(f"unsupported target_predicate_kind for {self.task_id}: {target_predicate_kind}")
        else:
            predicate_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.target_predicate_kind",
            )
            target_predicate_kind = str(predicate_kind_support[abs(int(predicate_index)) % len(predicate_kind_support)])
        predicate_kind_probabilities = _uniform_string_probability_map(
            predicate_kind_support,
            selected=str(target_predicate_kind) if explicit_predicate_kind is not None else None,
        )

        shape_support = tuple(str(shape) for shape in COLOR_SAFE_SHAPE_TYPES)
        target_shape_type: str | None = None
        if str(target_predicate_kind) in {"object", "color_object"}:
            explicit_shape = params.get("target_shape_type")
            if explicit_shape is not None:
                target_shape_type = str(explicit_shape)
                if target_shape_type not in set(shape_support):
                    raise ValueError(f"unsupported target_shape_type for {self.task_id}: {target_shape_type}")
            else:
                shape_index = resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}.target_shape_type",
                )
                target_shape_type = str(shape_support[abs(int(shape_index)) % len(shape_support)])
            shape_probabilities = _uniform_string_probability_map(
                shape_support,
                selected=str(target_shape_type) if explicit_shape is not None else None,
            )
        else:
            shape_probabilities = {}

        color_support = tuple(str(color) for color in PROMPT_COLOR_RGB)
        target_color_name: str | None = None
        if str(target_predicate_kind) in {"color", "color_object"}:
            explicit_color = params.get("target_color_name")
            if explicit_color is not None:
                target_color_name = str(explicit_color)
                if target_color_name not in set(color_support):
                    raise ValueError(f"unsupported target_color_name for {self.task_id}: {target_color_name}")
            else:
                color_index = resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}.target_color_name",
                )
                target_color_name = str(color_support[abs(int(color_index)) % len(color_support)])
            color_probabilities = _uniform_string_probability_map(
                color_support,
                selected=str(target_color_name) if explicit_color is not None else None,
            )
        else:
            color_probabilities = {}

        target_predicate = _make_predicate(
            predicate_kind=str(target_predicate_kind),
            shape_type=target_shape_type,
            color_name=target_color_name,
        )

        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_counterfactual_count_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            target_predicate=target_predicate,
            target_count=int(target_count),
            object_count=int(object_count),
            edit_step_count=int(edit_step_count),
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
                "target_property_phrase": str(dataset["target_property_phrase"]),
                "edit_steps_text": str(dataset["edit_steps_text"]),
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
                "scene_kind": "three_d_object_scene_counterfactual_attribute_count",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "object_count": int(object_count),
                    "countable_object_count": int(object_count),
                    "target_predicate": dict(dataset["target_predicate"]),
                    "target_predicate_kind": str(dataset["target_predicate_kind"]),
                    "target_shape_type": dataset["target_shape_type"],
                    "target_color_name": dataset["target_color_name"],
                    "target_property_phrase": str(dataset["target_property_phrase"]),
                    "initial_target_count": int(dataset["initial_target_count"]),
                    "final_target_count": int(answer_value),
                    "initial_target_object_ids": list(target_object_ids),
                    "counterfactual_steps": [dict(step) for step in dataset["counterfactual_steps"]],
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
                    "target_count": int(dataset["initial_target_count"]),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "edit_step_count": int(edit_step_count),
                    "edit_step_count_probabilities": dict(edit_step_count_probabilities),
                    "target_predicate_kind": str(dataset["target_predicate_kind"]),
                    "target_predicate_kind_probabilities": dict(predicate_kind_probabilities),
                    "target_predicate": dict(dataset["target_predicate"]),
                    "target_shape_type": dataset["target_shape_type"],
                    "target_shape_type_probabilities": dict(shape_probabilities),
                    "target_color_name": dataset["target_color_name"],
                    "target_color_name_probabilities": dict(color_probabilities),
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
                "initial_target_object_bboxes_px": {
                    str(object_id): list(rendered.object_bboxes_px[str(object_id)])
                    for object_id in target_object_ids
                },
                "initial_target_object_centers_px": {
                    str(object_id): list(rendered.object_centers_px[str(object_id)])
                    for object_id in target_object_ids
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "object_count": int(object_count),
                "countable_object_count": int(object_count),
                "initial_target_count": int(dataset["initial_target_count"]),
                "answer_value": int(answer_value),
                "final_target_count": int(answer_value),
                "target_predicate": dict(dataset["target_predicate"]),
                "target_predicate_kind": str(dataset["target_predicate_kind"]),
                "target_shape_type": dataset["target_shape_type"],
                "target_object_name": dataset["target_object_name"],
                "target_object_plural": dataset["target_object_plural"],
                "target_color_name": dataset["target_color_name"],
                "target_property_phrase": str(dataset["target_property_phrase"]),
                "initial_target_object_ids": list(target_object_ids),
                "counterfactual_steps": [dict(step) for step in dataset["counterfactual_steps"]],
                "edit_steps_text": str(dataset["edit_steps_text"]),
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "initial_property_counts": dict(dataset["initial_property_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "counterfactual_count_initial_target_set",
                "object_ids": list(target_object_ids),
                "target_predicate": dict(dataset["target_predicate"]),
                "target_predicate_kind": str(dataset["target_predicate_kind"]),
                "target_shape_type": dataset["target_shape_type"],
                "target_color_name": dataset["target_color_name"],
                "initial_target_count": int(dataset["initial_target_count"]),
                "final_answer_value": int(answer_value),
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


__all__ = ["ThreeDObjectSceneCounterfactualCountTask"]
