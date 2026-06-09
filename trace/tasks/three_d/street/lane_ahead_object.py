"""Lane-ahead object task for a synthetic 3D street scene."""

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
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
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
from ..shared.object_resources import STREET_LANE_AHEAD_REFERENCE_OBJECT_TYPE, STREET_OBJECT_TYPES
from ..shared.option_panel import build_text_option_choices
from ..shared.task_support import (
    normalize_unit as _normalize_unit,
    resolve_axis_variant as _resolve_axis_variant,
    resolve_count as _resolve_count,
)
from ..shared.object_scene import (
    POINT_LABELS,
    _build_projection_frame,
    _object_reference_points,
    _sample_camera,
)
from .intersection_scene import (
    MIN_CANDIDATE_VISIBLE_PX,
    SCENE_ID,
    STREET_CAMERA_YAW_BANDS_DEGREES,
    SUPPORTED_INTERSECTION_LAYOUTS,
    SUPPORTED_SCENE_VARIANTS,
    _StreetRenderParams,
    _arm_is_present,
    _bbox_intersection_area,
    _canvas_floor_polygon_available,
    _candidate_context_visibility_ok,
    _dimensions_for_orientation,
    _finalize_specs,
    _make_street_object_spec,
    _min_pairwise,
    _missing_arm_for_layout,
    _object_screen_bbox as _street_object_screen_bbox,
    _resolve_render_params,
    _sample_context_specs,
    _sample_intersection_center,
    _translate_scene_xy,
)
from .intersection_rendering import render_street_intersection_scene_3d


TASK_ID = "task_three_d__street__lane_ahead_object_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("ahead_along_lane",)
SUPPORTED_TRAVEL_MODES: Tuple[str, ...] = ("toward_intersection", "away_from_intersection")
ROAD_ARMS: Tuple[str, ...] = ("north", "south", "east", "west")
REFERENCE_OBJECT_TYPE = STREET_LANE_AHEAD_REFERENCE_OBJECT_TYPE
LANE_OFFSET_MAGNITUDE = 0.34
LANE_CORRIDOR_HALF_WIDTH = 0.28
MIN_FORWARD_DISTANCE = 0.52
MIN_REFERENCE_CENTER_SEPARATION_PX = 46.0
MAX_REFERENCE_CANDIDATE_BBOX_INTERSECTION_PX = 5200.0
LANE_MIN_CANDIDATE_CENTER_SEPARATION_PX = 34.0
LANE_MAX_CANDIDATE_BBOX_INTERSECTION_PX = 7600.0


def _resolve_camera_yaw_band(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
) -> Tuple[Tuple[float, float], Dict[str, float], int]:
    locked = params.get("_locked_camera_yaw_band_index")
    explicit = params.get("camera_yaw_band_index")
    support = tuple(range(len(STREET_CAMERA_YAW_BANDS_DEGREES)))
    if explicit is not None:
        selected_index = int(explicit)
        if selected_index not in set(support):
            raise ValueError(f"unsupported camera_yaw_band_index: {selected_index}")
    elif locked is not None:
        selected_index = int(locked)
        if selected_index not in set(support):
            raise ValueError(f"unsupported locked camera_yaw_band_index: {selected_index}")
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.camera_yaw_band_index",
        )
        selected_index = int(support[abs(int(selection_index)) % len(support)])
    probabilities = dict(
        uniform_probability_map(
            support,
            selected=int(selected_index) if explicit is not None else None,
        )
    )
    return (
        tuple(float(value) for value in STREET_CAMERA_YAW_BANDS_DEGREES[int(selected_index)]),
        {str(key): float(value) for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))},
        int(selected_index),
    )


def _present_road_arms(intersection_layout: str) -> Tuple[str, ...]:
    return tuple(
        str(arm)
        for arm in ROAD_ARMS
        if _arm_is_present(str(intersection_layout), str(arm))
    )


def _arm_unit(road_arm: str) -> Tuple[float, float]:
    if str(road_arm) == "north":
        return (0.0, 1.0)
    if str(road_arm) == "south":
        return (0.0, -1.0)
    if str(road_arm) == "east":
        return (1.0, 0.0)
    if str(road_arm) == "west":
        return (-1.0, 0.0)
    raise ValueError(f"unsupported road arm: {road_arm}")


def _lane_relative_xy(
    road_arm: str,
    *,
    longitudinal_s: float,
    lateral_offset: float,
) -> Tuple[float, float]:
    ux, uy = _arm_unit(str(road_arm))
    if abs(uy) > 0.0:
        return (round(float(lateral_offset), 4), round(float(uy * longitudinal_s), 4))
    return (round(float(ux * longitudinal_s), 4), round(float(lateral_offset), 4))


def _travel_direction_for_mode(road_arm: str, travel_mode: str) -> Tuple[float, float]:
    ux, uy = _arm_unit(str(road_arm))
    if str(travel_mode) == "toward_intersection":
        return (-ux, -uy)
    return (ux, uy)


def _orientation_axis_for_arm(road_arm: str) -> str:
    return "y" if str(road_arm) in {"north", "south"} else "x"


def _make_lane_object_spec(
    *,
    rng,
    object_id: str,
    object_type: str,
    object_role: str,
    road_arm: str,
    relative_xy: Sequence[float],
    lane_id: str | None,
    lane_lateral_offset: float | None,
    lane_longitudinal_s: float | None,
    intersection_center_xy: Tuple[float, float],
    street_extent: float,
    label: str | None,
    jitter: float,
    scale_range: Tuple[float, float],
) -> Dict[str, Any]:
    jittered_xy = (
        float(relative_xy[0]) + float(rng.uniform(-float(jitter), float(jitter))),
        float(relative_xy[1]) + float(rng.uniform(-float(jitter), float(jitter))),
    )
    xy = _translate_scene_xy(
        jittered_xy,
        center_xy=intersection_center_xy,
        extent=float(street_extent),
        margin=0.44,
    )
    orientation_axis = _orientation_axis_for_arm(str(road_arm))
    scale = float(rng.uniform(float(scale_range[0]), float(scale_range[1])))
    dimensions = _dimensions_for_orientation(
        str(object_type),
        orientation_axis=str(orientation_axis),
        scale=float(scale),
    )
    spec = _make_street_object_spec(
        object_id=str(object_id),
        object_type=str(object_type),
        object_role=str(object_role),
        xy=tuple(float(value) for value in xy),
        intersection_center_xy=tuple(float(value) for value in intersection_center_xy),
        orientation_axis=str(orientation_axis),
        dimensions_xyz=dimensions,
        label=label,
        dimension_scale=float(scale),
    )
    spec["road_arm"] = str(road_arm)
    spec["relative_road_xy"] = [round(float(jittered_xy[0]), 4), round(float(jittered_xy[1]), 4)]
    if lane_id is not None:
        spec["lane_id"] = str(lane_id)
    if lane_lateral_offset is not None:
        spec["lane_lateral_offset"] = round(float(lane_lateral_offset), 4)
    if lane_longitudinal_s is not None:
        spec["lane_longitudinal_s"] = round(float(lane_longitudinal_s), 4)
    return spec


def _lane_relation_to_reference(
    spec: Mapping[str, Any],
    *,
    reference_spec: Mapping[str, Any],
    direction_xy: Sequence[float],
) -> Tuple[float, float, bool]:
    ref_x, ref_y = (float(value) for value in reference_spec["base_xyz"][:2])
    cand_x, cand_y = (float(value) for value in spec["base_xyz"][:2])
    dx = cand_x - ref_x
    dy = cand_y - ref_y
    dir_x, dir_y = float(direction_xy[0]), float(direction_xy[1])
    norm = math.hypot(dir_x, dir_y) or 1.0
    dir_x /= norm
    dir_y /= norm
    forward = dx * dir_x + dy * dir_y
    lateral = abs(dx * (-dir_y) + dy * dir_x)
    ahead = (
        str(spec.get("road_arm")) == str(reference_spec.get("road_arm"))
        and str(spec.get("lane_id")) == str(reference_spec.get("lane_id"))
        and float(forward) >= MIN_FORWARD_DISTANCE
        and float(lateral) <= LANE_CORRIDOR_HALF_WIDTH
    )
    return round(float(forward), 4), round(float(lateral), 4), bool(ahead)


def _sample_reference_and_candidate_specs(
    *,
    rng,
    candidate_count: int,
    intersection_center_xy: Tuple[float, float],
    intersection_layout: str,
    reference_road_arm: str,
    travel_mode: str,
    lane_side: int,
    street_extent: float,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Tuple[float, float]]:
    present_arms = _present_road_arms(str(intersection_layout))
    if str(reference_road_arm) not in set(present_arms):
        raise ValueError("reference road arm is not present in this layout")
    lane_offset = float(lane_side) * LANE_OFFSET_MAGNITUDE
    lane_id = f"{reference_road_arm}:{lane_offset:+.2f}"
    if str(travel_mode) == "toward_intersection":
        reference_s = float(rng.uniform(2.82, 3.16))
        answer_s = reference_s - float(rng.uniform(1.00, 1.25))
        behind_s = min(3.94, reference_s + float(rng.uniform(0.72, 0.96)))
        adjacent_s = max(0.98, answer_s - float(rng.uniform(0.52, 0.82)))
        off_lane_s = max(0.98, answer_s - float(rng.uniform(0.22, 0.54)))
    else:
        reference_s = float(rng.uniform(1.42, 1.74))
        answer_s = reference_s + float(rng.uniform(1.00, 1.25))
        behind_s = max(0.78, reference_s - float(rng.uniform(0.62, 0.90)))
        adjacent_s = min(3.86, answer_s + float(rng.uniform(0.52, 0.82)))
        off_lane_s = min(3.86, answer_s + float(rng.uniform(0.22, 0.54)))
    off_lane_offset = max(-0.88, min(0.88, lane_offset + float(lane_side) * 0.52))
    direction_xy = _travel_direction_for_mode(str(reference_road_arm), str(travel_mode))
    reference_relative = _lane_relative_xy(
        str(reference_road_arm),
        longitudinal_s=float(reference_s),
        lateral_offset=float(lane_offset),
    )
    reference_spec = _make_lane_object_spec(
        rng=rng,
        object_id="reference_lane_car",
        object_type=REFERENCE_OBJECT_TYPE,
        object_role="street_reference",
        road_arm=str(reference_road_arm),
        relative_xy=reference_relative,
        lane_id=str(lane_id),
        lane_lateral_offset=float(lane_offset),
        lane_longitudinal_s=float(reference_s),
        intersection_center_xy=tuple(float(value) for value in intersection_center_xy),
        street_extent=float(street_extent),
        label=None,
        jitter=0.035,
        scale_range=(0.94, 1.04),
    )
    reference_spec.update(
        {
            "is_named_reference": True,
            "travel_mode": str(travel_mode),
            "travel_direction_vector_xy": [round(float(direction_xy[0]), 4), round(float(direction_xy[1]), 4)],
        }
    )

    raw_slots: List[Dict[str, Any]] = [
        {
            "road_arm": str(reference_road_arm),
            "relative_xy": _lane_relative_xy(str(reference_road_arm), longitudinal_s=float(answer_s), lateral_offset=float(lane_offset)),
            "lane_id": str(lane_id),
            "lane_lateral_offset": float(lane_offset),
            "lane_longitudinal_s": float(answer_s),
            "relation_hint": "ahead_same_lane",
            "jitter": 0.035,
        },
        {
            "road_arm": str(reference_road_arm),
            "relative_xy": _lane_relative_xy(str(reference_road_arm), longitudinal_s=float(behind_s), lateral_offset=float(lane_offset)),
            "lane_id": str(lane_id),
            "lane_lateral_offset": float(lane_offset),
            "lane_longitudinal_s": float(behind_s),
            "relation_hint": "behind_same_lane",
            "jitter": 0.055,
        },
        {
            "road_arm": str(reference_road_arm),
            "relative_xy": _lane_relative_xy(str(reference_road_arm), longitudinal_s=float(adjacent_s), lateral_offset=-float(lane_offset)),
            "lane_id": f"{reference_road_arm}:{-lane_offset:+.2f}",
            "lane_lateral_offset": -float(lane_offset),
            "lane_longitudinal_s": float(adjacent_s),
            "relation_hint": "ahead_adjacent_lane",
            "jitter": 0.055,
        },
        {
            "road_arm": str(reference_road_arm),
            "relative_xy": _lane_relative_xy(str(reference_road_arm), longitudinal_s=float(off_lane_s), lateral_offset=float(off_lane_offset)),
            "lane_id": f"{reference_road_arm}:off:{off_lane_offset:+.2f}",
            "lane_lateral_offset": float(off_lane_offset),
            "lane_longitudinal_s": float(off_lane_s),
            "relation_hint": "ahead_off_lane",
            "jitter": 0.055,
        },
    ]
    other_arms = [str(arm) for arm in present_arms if str(arm) != str(reference_road_arm)]
    rng.shuffle(other_arms)
    for arm in other_arms:
        for s_value, side in ((1.82, 1), (2.48, -1), (3.08, 1)):
            other_offset = float(side) * LANE_OFFSET_MAGNITUDE
            raw_slots.append(
                {
                    "road_arm": str(arm),
                    "relative_xy": _lane_relative_xy(str(arm), longitudinal_s=float(s_value + rng.uniform(-0.12, 0.12)), lateral_offset=float(other_offset)),
                    "lane_id": f"{arm}:{other_offset:+.2f}",
                    "lane_lateral_offset": float(other_offset),
                    "lane_longitudinal_s": float(s_value),
                    "relation_hint": "other_road_arm",
                    "jitter": 0.075,
                }
            )
    answer_slot = raw_slots[0]
    distractor_slots = raw_slots[1:]
    rng.shuffle(distractor_slots)
    selected_slots = [answer_slot, *distractor_slots[: int(candidate_count) - 1]]
    if len(selected_slots) < int(candidate_count):
        raise ValueError("not enough lane-ahead candidate slots")
    candidate_types = [
        str(item)
        for item in STREET_OBJECT_TYPES
        if str(item) != REFERENCE_OBJECT_TYPE
    ]
    if int(candidate_count) > len(candidate_types):
        raise ValueError("not enough unique street candidate types")
    rng.shuffle(candidate_types)
    candidate_specs: List[Dict[str, Any]] = []
    for index, slot in enumerate(selected_slots):
        object_type = str(candidate_types[index])
        spec = _make_lane_object_spec(
            rng=rng,
            object_id=f"candidate_{index}_{object_type}",
            object_type=str(object_type),
            object_role="street_candidate",
            road_arm=str(slot["road_arm"]),
            relative_xy=slot["relative_xy"],
            lane_id=str(slot["lane_id"]),
            lane_lateral_offset=float(slot["lane_lateral_offset"]),
            lane_longitudinal_s=float(slot["lane_longitudinal_s"]),
            intersection_center_xy=tuple(float(value) for value in intersection_center_xy),
            street_extent=float(street_extent),
            label="?",
            jitter=float(slot["jitter"]),
            scale_range=(0.84, 1.00),
        )
        spec["lane_relation_hint"] = str(slot["relation_hint"])
        candidate_specs.append(spec)
    return dict(reference_spec), list(candidate_specs), tuple(float(value) for value in direction_xy)


def _reference_visibility_ok(
    reference_spec: Mapping[str, Any],
    candidate_specs: Sequence[Mapping[str, Any]],
    context_specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
    render_params: _StreetRenderParams,
) -> bool:
    reference_bbox = _street_object_screen_bbox(reference_spec, camera, frame, pad_px=16.0)
    width = float(reference_bbox[2]) - float(reference_bbox[0])
    height = float(reference_bbox[3]) - float(reference_bbox[1])
    if width < MIN_CANDIDATE_VISIBLE_PX or height < MIN_CANDIDATE_VISIBLE_PX:
        return False
    if (
        float(reference_bbox[0]) < -24.0
        or float(reference_bbox[1]) < -24.0
        or float(reference_bbox[2]) > float(render_params.canvas_width + 24)
        or float(reference_bbox[3]) > float(render_params.canvas_height + 24)
    ):
        return False
    ref_center = (float(reference_spec["screen_xy"][0]), float(reference_spec["screen_xy"][1]))
    for candidate in candidate_specs:
        cand_center = (float(candidate["screen_xy"][0]), float(candidate["screen_xy"][1]))
        if math.hypot(ref_center[0] - cand_center[0], ref_center[1] - cand_center[1]) < MIN_REFERENCE_CENTER_SEPARATION_PX:
            return False
        candidate_bbox = _street_object_screen_bbox(candidate, camera, frame, pad_px=16.0)
        if _bbox_intersection_area(reference_bbox, candidate_bbox) > MAX_REFERENCE_CANDIDATE_BBOX_INTERSECTION_PX:
            return False
    for context in context_specs:
        if float(context["camera_distance"]) >= float(reference_spec["camera_distance"]) - 0.05:
            continue
        context_bbox = _street_object_screen_bbox(context, camera, frame, pad_px=10.0)
        overlap = _bbox_intersection_area(reference_bbox, context_bbox)
        if overlap > 900.0 and overlap / max(1.0, (width * height)) > 0.10:
            return False
    return True


def _lane_candidate_screen_separation_ok(
    specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
    render_params: _StreetRenderParams,
) -> bool:
    bboxes = [_street_object_screen_bbox(spec, camera, frame, pad_px=14.0) for spec in specs]
    centers = [(float(spec["screen_xy"][0]), float(spec["screen_xy"][1])) for spec in specs]
    for bbox in bboxes:
        width = float(bbox[2]) - float(bbox[0])
        height = float(bbox[3]) - float(bbox[1])
        if width < 18.0 or height < 18.0:
            return False
        if (
            float(bbox[0]) < -30.0
            or float(bbox[1]) < -30.0
            or float(bbox[2]) > float(render_params.canvas_width + 30)
            or float(bbox[3]) > float(render_params.canvas_height + 30)
        ):
            return False
    for index, center in enumerate(centers):
        for other_index in range(index + 1, len(centers)):
            other = centers[other_index]
            if math.hypot(center[0] - other[0], center[1] - other[1]) < LANE_MIN_CANDIDATE_CENTER_SEPARATION_PX:
                return False
            if _bbox_intersection_area(bboxes[index], bboxes[other_index]) > LANE_MAX_CANDIDATE_BBOX_INTERSECTION_PX:
                return False
    return True


def _build_lane_ahead_dataset(
    *,
    params: Mapping[str, Any],
    query_id: str,
    scene_variant: str,
    intersection_layout: str,
    travel_mode: str,
    candidate_count: int,
    context_object_count: int,
    camera_yaw_band: Tuple[float, float],
    camera_yaw_band_index: int,
    render_params: _StreetRenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    present_arms = _present_road_arms(str(intersection_layout))
    for _attempt in range(520):
        intersection_center_xy = _sample_intersection_center(
            rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            render_params=render_params,
        )
        reference_road_arm = str(present_arms[int(rng.randrange(0, len(present_arms)))])
        lane_side = -1 if int(rng.randrange(0, 2)) == 0 else 1
        camera = _sample_camera(rng, yaw_band_degrees=tuple(float(value) for value in camera_yaw_band))
        reference_spec, candidate_specs, direction_xy = _sample_reference_and_candidate_specs(
            rng=rng,
            candidate_count=int(candidate_count),
            intersection_center_xy=tuple(float(value) for value in intersection_center_xy),
            intersection_layout=str(intersection_layout),
            reference_road_arm=str(reference_road_arm),
            travel_mode=str(travel_mode),
            lane_side=int(lane_side),
            street_extent=float(render_params.street_extent),
        )
        context_specs = _sample_context_specs(
            rng=rng,
            scene_variant=str(scene_variant),
            context_object_count=int(context_object_count),
            intersection_center_xy=tuple(intersection_center_xy),
            intersection_layout=str(intersection_layout),
            road_half_width=float(render_params.road_half_width),
            street_extent=float(render_params.street_extent),
        )
        all_specs = [reference_spec, *candidate_specs, *context_specs]
        reference_points: List[Tuple[float, float, float]] = [
            (-render_params.street_extent, -render_params.street_extent, 0.0),
            (render_params.street_extent, -render_params.street_extent, 0.0),
            (render_params.street_extent, render_params.street_extent, 0.0),
            (-render_params.street_extent, render_params.street_extent, 0.0),
            (-render_params.street_extent, -render_params.street_extent, 1.7),
            (render_params.street_extent, render_params.street_extent, 1.7),
        ]
        for spec in all_specs:
            reference_points.extend(_object_reference_points(spec))
        frame = _build_projection_frame(
            camera=camera,
            render_params=render_params,
            point_worlds=reference_points,
        )
        if not _canvas_floor_polygon_available(camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_reference = _finalize_specs([reference_spec], camera=camera, frame=frame)[0]
        finalized_candidates = _finalize_specs(candidate_specs, camera=camera, frame=frame)
        finalized_context = _finalize_specs(context_specs, camera=camera, frame=frame)
        if not _lane_candidate_screen_separation_ok(
            finalized_candidates,
            camera=camera,
            frame=frame,
            render_params=render_params,
        ):
            continue
        if not _reference_visibility_ok(
            finalized_reference,
            finalized_candidates,
            finalized_context,
            camera=camera,
            frame=frame,
            render_params=render_params,
        ):
            continue
        if not _candidate_context_visibility_ok(
            finalized_candidates,
            [finalized_reference, *finalized_context],
            camera=camera,
            frame=frame,
        ):
            continue

        relation_rows: List[Tuple[Dict[str, Any], float, float, bool]] = []
        for spec in finalized_candidates:
            forward, lateral, ahead = _lane_relation_to_reference(
                spec,
                reference_spec=finalized_reference,
                direction_xy=direction_xy,
            )
            updated = dict(spec)
            updated["forward_distance_from_reference"] = float(forward)
            updated["lateral_distance_from_reference_lane"] = float(lateral)
            updated["ahead_along_lane"] = bool(ahead)
            relation_rows.append((updated, float(forward), float(lateral), bool(ahead)))
        satisfying = [row for row in relation_rows if bool(row[3])]
        if len(satisfying) != 1:
            continue
        answer_object_id = str(satisfying[0][0]["object_id"])
        locked_answer_label_index = params.get("_locked_answer_label_index")
        if locked_answer_label_index is None:
            answer_label_index = abs(
                int(
                    resolve_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{TASK_ID}.answer_label",
                    )
                )
            ) % int(candidate_count)
        else:
            answer_label_index = abs(int(locked_answer_label_index)) % int(candidate_count)
        answer_label = str(POINT_LABELS[int(answer_label_index)])
        remaining_labels = [
            str(label)
            for label in POINT_LABELS[: int(candidate_count)]
            if str(label) != str(answer_label)
        ]
        rng.shuffle(remaining_labels)
        relabeled_candidates: List[Dict[str, Any]] = []
        for spec, _forward, _lateral, _ahead in relation_rows:
            updated = dict(spec)
            label = str(answer_label) if str(updated["object_id"]) == answer_object_id else str(remaining_labels.pop())
            updated.update(
                {
                    "object_id": f"street_object_{label}",
                    "point_id": f"street_object_{label}",
                    "point_label": str(label),
                    "object_label": str(label),
                    "is_answer_candidate": True,
                }
            )
            relabeled_candidates.append(updated)

        answer_spec = next(spec for spec in relabeled_candidates if str(spec["point_label"]) == str(answer_label))
        all_finalized = [finalized_reference, *relabeled_candidates, *finalized_context]
        ahead_flags = {
            str(spec["point_label"]): bool(spec["ahead_along_lane"])
            for spec in relabeled_candidates
        }
        forward_by_label = {
            str(spec["point_label"]): round(float(spec["forward_distance_from_reference"]), 4)
            for spec in relabeled_candidates
        }
        lateral_by_label = {
            str(spec["point_label"]): round(float(spec["lateral_distance_from_reference_lane"]), 4)
            for spec in relabeled_candidates
        }
        lane_relation_by_label = {
            str(spec["point_label"]): str(spec.get("lane_relation_hint", ""))
            for spec in relabeled_candidates
        }
        candidate_road_arms = {
            str(spec["point_label"]): str(spec["road_arm"])
            for spec in relabeled_candidates
        }
        candidate_ground_xy = {
            str(spec["point_label"]): [round(float(spec["base_xyz"][0]), 4), round(float(spec["base_xyz"][1]), 4)]
            for spec in relabeled_candidates
        }
        candidate_object_types = {
            str(spec["point_label"]): str(spec["object_type"]) for spec in relabeled_candidates
        }
        candidate_projected_bboxes = {
            str(spec["point_label"]): [
                round(float(value), 3)
                for value in _street_object_screen_bbox(spec, camera, frame, pad_px=0.0)
            ]
            for spec in relabeled_candidates
        }
        reference_bbox = [
            round(float(value), 3)
            for value in _street_object_screen_bbox(finalized_reference, camera, frame, pad_px=0.0)
        ]
        object_type_counts = Counter(str(spec["object_type"]) for spec in all_finalized)
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "intersection_layout": str(intersection_layout),
            "missing_road_arm": _missing_arm_for_layout(str(intersection_layout)),
            "present_road_arms": list(present_arms),
            "travel_mode": str(travel_mode),
            "candidate_count": int(candidate_count),
            "context_object_count": int(context_object_count),
            "intersection_center_xy": [round(float(intersection_center_xy[0]), 4), round(float(intersection_center_xy[1]), 4)],
            "reference_object": {
                "object_id": str(finalized_reference["object_id"]),
                "object_type": str(finalized_reference["object_type"]),
                "prompt_name": str(finalized_reference["prompt_name"]),
                "road_arm": str(finalized_reference["road_arm"]),
                "lane_id": str(finalized_reference["lane_id"]),
                "lane_lateral_offset": float(finalized_reference["lane_lateral_offset"]),
                "lane_longitudinal_s": float(finalized_reference["lane_longitudinal_s"]),
                "travel_mode": str(travel_mode),
                "travel_direction_vector_xy": [round(float(direction_xy[0]), 4), round(float(direction_xy[1]), 4)],
                "world_xyz": list(finalized_reference["world_xyz"]),
                "base_xyz": list(finalized_reference["base_xyz"]),
                "screen_xy": list(finalized_reference["screen_xy"]),
                "bbox_px": list(reference_bbox),
            },
            "candidate_object_specs": sorted(relabeled_candidates, key=lambda spec: str(spec["point_label"])),
            "reference_object_specs": [dict(finalized_reference)],
            "context_object_specs": sorted(finalized_context, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted(all_finalized, key=lambda spec: str(spec["object_id"])),
            "target_object_ids": [str(answer_spec["object_id"])],
            "answer_label": str(answer_label),
            "answer_object_id": str(answer_spec["object_id"]),
            "answer_object_type": str(answer_spec["object_type"]),
            "answer_road_arm": str(answer_spec["road_arm"]),
            "answer_forward_distance": round(float(answer_spec["forward_distance_from_reference"]), 4),
            "ahead_along_lane_by_label": dict(sorted(ahead_flags.items())),
            "ahead_along_lane_candidate_labels": sorted([str(label) for label, flag in ahead_flags.items() if bool(flag)]),
            "forward_distance_from_reference_by_label": dict(sorted(forward_by_label.items())),
            "lateral_distance_from_reference_lane_by_label": dict(sorted(lateral_by_label.items())),
            "lane_relation_by_label": dict(sorted(lane_relation_by_label.items())),
            "candidate_road_arm_by_label": dict(sorted(candidate_road_arms.items())),
            "candidate_ground_xy_by_label": dict(sorted(candidate_ground_xy.items())),
            "candidate_object_types_by_label": dict(sorted(candidate_object_types.items())),
            "candidate_projected_bboxes_by_label": dict(sorted(candidate_projected_bboxes.items())),
            "object_type_counts": dict(sorted(object_type_counts.items())),
            "object_count": int(len(all_finalized)),
            "min_pairwise_candidate_ground_gap": round(
                float(
                    _min_pairwise(
                        [
                            float(spec["ground_distance_to_intersection"])
                            for spec in relabeled_candidates
                        ]
                    )
                ),
                4,
            ),
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
                "predicate": "option-panel candidate ahead of the red-boxed reference in the same lane corridor and travel direction",
                "reference_object": {
                    "object_id": str(finalized_reference["object_id"]),
                    "object_type": str(finalized_reference["object_type"]),
                    "road_arm": str(finalized_reference["road_arm"]),
                    "lane_id": str(finalized_reference["lane_id"]),
                    "travel_mode": str(travel_mode),
                    "travel_direction_vector_xy": [round(float(direction_xy[0]), 4), round(float(direction_xy[1]), 4)],
                },
                "present_road_arms": list(present_arms),
                "intersection_layout": str(intersection_layout),
                "missing_road_arm": _missing_arm_for_layout(str(intersection_layout)),
                "ahead_along_lane_by_label": dict(sorted(ahead_flags.items())),
                "forward_distance_from_reference_by_label": dict(sorted(forward_by_label.items())),
                "lateral_distance_from_reference_lane_by_label": dict(sorted(lateral_by_label.items())),
                "lane_relation_by_label": dict(sorted(lane_relation_by_label.items())),
                "answer_label": str(answer_label),
                "answer_object_id": str(answer_spec["object_id"]),
                "answer_forward_distance": round(float(answer_spec["forward_distance_from_reference"]), 4),
                "unique_answer": True,
            },
        }
    raise ValueError("could not construct a visible street lane-ahead scene")


def _build_complexity(
    *,
    candidate_count: int,
    context_object_count: int,
    travel_mode: str,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.28)),
        "lane_direction": float(raw_weights.get("lane_direction", 0.34)),
        "road_corridor_binding": float(raw_weights.get("road_corridor_binding", 0.24)),
        "perspective_depth": float(raw_weights.get("perspective_depth", 0.14)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(float(candidate_count + context_object_count + 1), 10.0, 17.0),
        "lane_direction": 0.78 if str(travel_mode) == "toward_intersection" else 0.84,
        "road_corridor_binding": 0.74,
        "perspective_depth": 0.62,
    }
    score = sum(float(components[key]) * max(0.0, float(weights[key])) for key in weights) / float(total)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={key: round(float(value), 6) for key, value in components.items()},
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "street")
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
    """Lock public sampling axes so retries do not bias review distributions."""

    locked_params = dict(params)
    query_id, _query_probabilities = _resolve_axis_variant(
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
    scene_variant, _scene_probabilities = _resolve_axis_variant(
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
    intersection_layout, _intersection_layout_probabilities = _resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_INTERSECTION_LAYOUTS,
        explicit_key="intersection_layout",
        weights_key="intersection_layout_weights",
        balance_flag_key="balanced_intersection_layout_sampling",
        axis_namespace="intersection_layout",
        allow_locked=True,
    )
    travel_mode, _travel_mode_probabilities = _resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_TRAVEL_MODES,
        explicit_key="travel_mode",
        weights_key="travel_mode_weights",
        balance_flag_key="balanced_travel_mode_sampling",
        axis_namespace="travel_mode",
        allow_locked=True,
    )
    candidate_count, _candidate_count_probabilities = _resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="candidate_count",
        default_min=5,
        default_max=5,
        lower=5,
        upper=6,
        allow_locked=True,
    )
    context_object_count, _context_object_count_probabilities = _resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="context_object_count",
        default_min=8,
        default_max=8,
        lower=6,
        upper=12,
        allow_locked=True,
    )
    _camera_yaw_band, _camera_yaw_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(
        params=params,
        instance_seed=int(instance_seed),
    )
    answer_label_index = abs(
        int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.answer_label",
            )
        )
    ) % int(candidate_count)
    locked_params.update(
        {
            "_locked_query_id": str(query_id),
            "_locked_scene_variant": str(scene_variant),
            "_locked_intersection_layout": str(intersection_layout),
            "_locked_travel_mode": str(travel_mode),
            "_locked_candidate_count": int(candidate_count),
            "_locked_context_object_count": int(context_object_count),
            "_locked_camera_yaw_band_index": int(camera_yaw_band_index),
            "_locked_answer_label_index": int(answer_label_index),
        }
    )
    return locked_params


@register_task
class ThreeDStreetLaneAheadObjectLabelTask:
    """Choose the option-panel street object ahead of a red-boxed reference vehicle."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "street"
    default_dataset_enabled = True

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        last_error: Exception | None = None
        retry_params = _build_retry_locked_params(int(instance_seed), params)
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(
                    spawn_rng(
                        int(instance_seed),
                        f"{TASK_ID}.attempt_seed.{attempt_index}",
                    ).randrange(1, 2**62)
                )
            )
            try:
                return self._generate_once(int(attempt_seed), params=retry_params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(
            f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}"
        )

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_probabilities = _resolve_axis_variant(
            params,
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
        scene_variant, scene_probabilities = _resolve_axis_variant(
            params,
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
        intersection_layout, intersection_layout_probabilities = _resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_INTERSECTION_LAYOUTS,
            explicit_key="intersection_layout",
            weights_key="intersection_layout_weights",
            balance_flag_key="balanced_intersection_layout_sampling",
            axis_namespace="intersection_layout",
            allow_locked=True,
        )
        travel_mode, travel_mode_probabilities = _resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_TRAVEL_MODES,
            explicit_key="travel_mode",
            weights_key="travel_mode_weights",
            balance_flag_key="balanced_travel_mode_sampling",
            axis_namespace="travel_mode",
            allow_locked=True,
        )
        candidate_count, candidate_count_probabilities = _resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="candidate_count",
            default_min=5,
            default_max=5,
            lower=5,
            upper=6,
            allow_locked=True,
        )
        context_object_count, context_object_count_probabilities = _resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="context_object_count",
            default_min=8,
            default_max=8,
            lower=6,
            upper=12,
            allow_locked=True,
        )
        camera_yaw_band, camera_yaw_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(
            params,
            instance_seed=int(instance_seed),
        )
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_lane_ahead_dataset(
            params=params,
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            intersection_layout=str(intersection_layout),
            travel_mode=str(travel_mode),
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
        option_choices = build_text_option_choices(dataset["candidate_object_specs"])
        rendered_scene = render_street_intersection_scene_3d(
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

        answer_label = str(dataset["answer_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in rendered_scene.annotation_bboxes
        ]
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        complexity = _build_complexity(
            candidate_count=int(dataset["candidate_count"]),
            context_object_count=int(dataset["context_object_count"]),
            travel_mode=str(dataset["travel_mode"]),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )
        solver_trace = dict(dataset["solver_trace"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_street_intersection",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "candidate_count": int(dataset["candidate_count"]),
                    "context_object_count": int(dataset["context_object_count"]),
                    "object_count": int(dataset["object_count"]),
                    "intersection_center_xy": list(dataset["intersection_center_xy"]),
                    "intersection_layout": str(dataset["intersection_layout"]),
                    "missing_road_arm": dataset["missing_road_arm"],
                    "present_road_arms": list(dataset["present_road_arms"]),
                    "travel_mode": str(dataset["travel_mode"]),
                    "reference_object": dict(dataset["reference_object"]),
                    "ahead_along_lane_by_label": dict(dataset["ahead_along_lane_by_label"]),
                    "forward_distance_from_reference_by_label": dict(dataset["forward_distance_from_reference_by_label"]),
                    "lateral_distance_from_reference_lane_by_label": dict(dataset["lateral_distance_from_reference_lane_by_label"]),
                    "lane_relation_by_label": dict(dataset["lane_relation_by_label"]),
                    "candidate_road_arm_by_label": dict(dataset["candidate_road_arm_by_label"]),
                    "candidate_object_types_by_label": dict(dataset["candidate_object_types_by_label"]),
                    "answer_label": str(answer_label),
                    "answer_object_id": str(dataset["answer_object_id"]),
                    "view_family": "synthetic_perspective_3d_street",
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
                    "intersection_layout": str(intersection_layout),
                    "intersection_layout_probabilities": dict(intersection_layout_probabilities),
                    "travel_mode": str(travel_mode),
                    "travel_mode_probabilities": dict(travel_mode_probabilities),
                    "candidate_count": int(candidate_count),
                    "candidate_count_probabilities": dict(candidate_count_probabilities),
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_object_count_probabilities),
                    "camera_yaw_band": str(camera_yaw_band_index),
                    "camera_yaw_band_index": int(camera_yaw_band_index),
                    "camera_yaw_band_probabilities": dict(camera_yaw_probabilities),
                    "intersection_center_xy": list(dataset["intersection_center_xy"]),
                    "object_count": int(dataset["object_count"]),
                    "answer_label_probabilities": {
                        str(label): round(1.0 / float(candidate_count), 8)
                        for label in POINT_LABELS[: int(candidate_count)]
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(image.height),
                "scene_canvas_height": int(render_params.canvas_height),
                "option_panel_height_px": int(rendered_scene.option_panel_height_px),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "intersection_layout": str(dataset["intersection_layout"]),
                "missing_road_arm": dataset["missing_road_arm"],
                "present_road_arms": list(dataset["present_road_arms"]),
                "travel_mode": str(dataset["travel_mode"]),
                "intersection_center_xy": list(dataset["intersection_center_xy"]),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "label_font_size_px": int(render_params.label_font_size_px),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "street_bbox_px": list(rendered_scene.street_bbox_px),
                "object_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.object_bboxes_px.items()
                },
                "object_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.object_centers_px.items()
                },
                "candidate_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.candidate_bboxes_px.items()
                },
                "candidate_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.candidate_centers_px.items()
                },
                "option_panel_bbox_px": list(rendered_scene.option_panel_bbox_px),
                "option_panel_height_px": int(rendered_scene.option_panel_height_px),
                "option_choice_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.option_choice_bboxes_px.items()
                },
                "option_choices": [dict(choice) for choice in rendered_scene.option_choices],
                "context_object_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.context_object_bboxes_px.items()
                },
                "context_object_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.context_object_centers_px.items()
                },
                "target_object_bboxes_px": {
                    str(key): list(rendered_scene.object_bboxes_px[str(key)])
                    for key in dataset["target_object_ids"]
                },
                "reference_object_bbox_px": list(
                    rendered_scene.object_bboxes_px[str(dataset["reference_object"]["object_id"])]
                ),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "candidate_count": int(dataset["candidate_count"]),
                "context_object_count": int(dataset["context_object_count"]),
                "object_count": int(dataset["object_count"]),
                "intersection_layout": str(dataset["intersection_layout"]),
                "missing_road_arm": dataset["missing_road_arm"],
                "present_road_arms": list(dataset["present_road_arms"]),
                "travel_mode": str(dataset["travel_mode"]),
                "answer_label": str(answer_label),
                "answer_object_id": str(dataset["answer_object_id"]),
                "answer_object_type": str(dataset["answer_object_type"]),
                "answer_road_arm": str(dataset["answer_road_arm"]),
                "answer_forward_distance": float(dataset["answer_forward_distance"]),
                "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                "reference_object": dict(dataset["reference_object"]),
                "reference_object_specs": [dict(spec) for spec in dataset["reference_object_specs"]],
                "candidate_object_specs": [dict(spec) for spec in dataset["candidate_object_specs"]],
                "option_choices": [dict(choice) for choice in rendered_scene.option_choices],
                "option_descriptor_by_label": {
                    str(choice["label"]): str(choice["descriptor"])
                    for choice in rendered_scene.option_choices
                },
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "intersection_center_xy": list(dataset["intersection_center_xy"]),
                "ahead_along_lane_by_label": dict(dataset["ahead_along_lane_by_label"]),
                "ahead_along_lane_candidate_labels": list(dataset["ahead_along_lane_candidate_labels"]),
                "forward_distance_from_reference_by_label": dict(dataset["forward_distance_from_reference_by_label"]),
                "lateral_distance_from_reference_lane_by_label": dict(dataset["lateral_distance_from_reference_lane_by_label"]),
                "lane_relation_by_label": dict(dataset["lane_relation_by_label"]),
                "candidate_road_arm_by_label": dict(dataset["candidate_road_arm_by_label"]),
                "candidate_ground_xy_by_label": dict(dataset["candidate_ground_xy_by_label"]),
                "candidate_object_types_by_label": dict(dataset["candidate_object_types_by_label"]),
                "candidate_projected_bboxes_by_label": dict(dataset["candidate_projected_bboxes_by_label"]),
                "object_type_counts": dict(dataset["object_type_counts"]),
                "min_pairwise_candidate_ground_gap": float(dataset["min_pairwise_candidate_ground_gap"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "view_family": "synthetic_perspective_3d_street",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "object",
                "id": str(dataset["answer_object_id"]),
                "answer": str(answer_label),
            },
            "projected_annotation": {
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
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


__all__ = ["ThreeDStreetLaneAheadObjectLabelTask"]
