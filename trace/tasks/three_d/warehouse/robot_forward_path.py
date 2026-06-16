"""Robot forward-path object task for a synthetic 3D warehouse scene."""

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
from ..shared.object_scene import (
    POINT_LABELS,
    _CameraSpec,
    _ProjectionFrame,
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
    PATH_CORRIDOR_HALF_WIDTH,
    SCENE_ID,
    SUPPORTED_ROBOT_HEADINGS,
    SUPPORTED_SCENE_VARIANTS,
    WAREHOUSE_CAMERA_YAW_BANDS_DEGREES,
    _WarehouseRenderParams,
    _bbox_area,
    _finalize_specs,
    _resolve_render_params,
    _sample_reference_and_objects,
)
from .warehouse_rendering import render_warehouse_robot_scene_3d


TASK_ID = "task_three_d__warehouse__robot_forward_path_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("first_object_ahead",)
MIN_FIRST_OBJECT_MARGIN = 0.52






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


def _visibility_ok(
    candidate_specs: Sequence[Mapping[str, Any]],
    reference_specs: Sequence[Mapping[str, Any]],
    context_specs: Sequence[Mapping[str, Any]],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    render_params: _WarehouseRenderParams,
) -> bool:
    bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=16.0) for spec in candidate_specs]
    centers = [(float(spec["screen_xy"][0]), float(spec["screen_xy"][1])) for spec in candidate_specs]
    for bbox in bboxes:
        width = float(bbox[2]) - float(bbox[0])
        height = float(bbox[3]) - float(bbox[1])
        if width < MIN_CANDIDATE_VISIBLE_PX or height < MIN_CANDIDATE_VISIBLE_PX:
            return False
        if (
            float(bbox[0]) < -24.0
            or float(bbox[1]) < -24.0
            or float(bbox[2]) > float(render_params.canvas_width + 24)
            or float(bbox[3]) > float(render_params.canvas_height + 24)
        ):
            return False
    for index, center in enumerate(centers):
        for other_index in range(index + 1, len(centers)):
            other = centers[other_index]
            if math.hypot(center[0] - other[0], center[1] - other[1]) < MIN_CANDIDATE_CENTER_SEPARATION_PX:
                return False
            if _bbox_intersection_area(bboxes[index], bboxes[other_index]) > MAX_CANDIDATE_BBOX_INTERSECTION_PX:
                return False
    reference_bboxes = []
    reference_centers = []
    for reference in reference_specs:
        ref_bbox = _object_screen_bbox(reference, camera, frame, pad_px=12.0)
        if (
            float(ref_bbox[0]) < -28.0
            or float(ref_bbox[1]) < -28.0
            or float(ref_bbox[2]) > float(render_params.canvas_width + 28)
            or float(ref_bbox[3]) > float(render_params.canvas_height + 28)
        ):
            return False
        reference_bboxes.append(list(ref_bbox))
        reference_centers.append((float(reference["screen_xy"][0]), float(reference["screen_xy"][1])))
    for candidate_index, candidate_bbox in enumerate(bboxes):
        candidate_area = max(1.0, _bbox_area(candidate_bbox))
        candidate_center = centers[candidate_index]
        for reference_index, ref_bbox in enumerate(reference_bboxes):
            overlap = _bbox_intersection_area(candidate_bbox, ref_bbox)
            ref_center = reference_centers[reference_index]
            center_distance = math.hypot(float(candidate_center[0]) - float(ref_center[0]), float(candidate_center[1]) - float(ref_center[1]))
            if center_distance < 58.0 or (overlap > 900.0 and overlap / candidate_area > 0.12):
                return False
    context_bboxes = {str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=8.0) for spec in context_specs}
    for candidate_index, candidate in enumerate(candidate_specs):
        candidate_bbox = bboxes[candidate_index]
        candidate_area = max(1.0, _bbox_area(candidate_bbox))
        for context in context_specs:
            if str(context.get("object_type")) == "shelf_rack":
                continue
            if float(context["camera_distance"]) >= float(candidate["camera_distance"]) - 0.05:
                continue
            overlap = _bbox_intersection_area(candidate_bbox, context_bboxes[str(context["object_id"])])
            if overlap > 2400.0 and overlap / candidate_area > 0.24:
                return False
    return True


def _attach_path_answers(
    candidate_specs: Sequence[Mapping[str, Any]],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    candidate_count: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    path_candidates = [
        dict(spec)
        for spec in candidate_specs
        if bool(spec.get("is_in_forward_path_corridor", False))
    ]
    if len(path_candidates) < 2:
        raise ValueError("warehouse scene requires at least two path-corridor candidates")
    ordered = sorted(path_candidates, key=lambda spec: (float(spec["forward_distance_from_robot"]), str(spec["object_id"])))
    first = dict(ordered[0])
    second = dict(ordered[1])
    if float(second["forward_distance_from_robot"]) - float(first["forward_distance_from_robot"]) < MIN_FIRST_OBJECT_MARGIN:
        raise ValueError("first reached object margin too small")
    answer_label_index = abs(
        int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.answer_label"))
    ) % int(candidate_count)
    answer_label = str(POINT_LABELS[int(answer_label_index)])
    remaining_labels = [str(label) for label in POINT_LABELS[: int(candidate_count)] if str(label) != str(answer_label)]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.answer_label_assignment")
    rng.shuffle(remaining_labels)
    relabeled: List[Dict[str, Any]] = []
    for spec in candidate_specs:
        updated = dict(spec)
        is_answer = str(updated["object_id"]) == str(first["object_id"])
        label = answer_label if is_answer else remaining_labels.pop()
        updated.update(
            {
                "object_id": f"warehouse_object_{label}",
                "point_id": f"warehouse_object_{label}",
                "point_label": str(label),
                "object_label": str(label),
                "is_answer_candidate": True,
                "is_first_reached_object": bool(is_answer),
            }
        )
        relabeled.append(updated)
    ordered_all = sorted(relabeled, key=lambda spec: (float(spec["forward_distance_from_robot"]), abs(float(spec["lateral_offset_from_robot"])), str(spec["point_label"])))
    answer_spec = next(spec for spec in relabeled if bool(spec["is_first_reached_object"]))
    path_labels = sorted(
        [str(spec["point_label"]) for spec in relabeled if bool(spec.get("is_in_forward_path_corridor", False))],
        key=lambda label: next(float(spec["forward_distance_from_robot"]) for spec in relabeled if str(spec["point_label"]) == str(label)),
    )
    return list(sorted(relabeled, key=lambda spec: str(spec["point_label"]))), {
        "answer_label": str(answer_label),
        "answer_spec": dict(answer_spec),
        "path_labels": list(path_labels),
        "forward_order_labels": [str(spec["point_label"]) for spec in ordered_all],
        "first_reached_margin": round(float(second["forward_distance_from_robot"]) - float(first["forward_distance_from_robot"]), 4),
    }


def _build_dataset(
    *,
    params: Mapping[str, Any],
    query_id: str,
    scene_variant: str,
    robot_heading: str,
    candidate_count: int,
    context_object_count: int,
    camera_yaw_band: Tuple[float, float],
    camera_yaw_band_index: int,
    render_params: _WarehouseRenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    for _attempt in range(420):
        camera = _sample_camera(rng, yaw_band_degrees=tuple(float(value) for value in camera_yaw_band))
        reference_specs, candidate_specs, context_specs, scene_geometry = _sample_reference_and_objects(
            rng=rng,
            candidate_count=int(candidate_count),
            context_object_count=int(context_object_count),
            robot_heading=str(robot_heading),
            render_params=render_params,
        )
        candidate_specs, answer_meta = _attach_path_answers(candidate_specs, params=params, instance_seed=int(instance_seed), candidate_count=int(candidate_count))
        robot_spec = dict(reference_specs[0])
        forward_xy = scene_geometry["forward_xy"]
        robot_xy = scene_geometry["robot_xy"]
        all_specs = [*reference_specs, *candidate_specs, *context_specs]
        reference_points: List[Tuple[float, float, float]] = []
        for spec in all_specs:
            if str(spec.get("object_type")) == "shelf_rack":
                continue
            reference_points.extend(_object_reference_points(spec))
        reference_points.extend(tuple(float(value) for value in point) for point in scene_geometry["path_corridor_polygon"])
        reference_points.extend(tuple(float(value) for value in point) for point in scene_geometry["main_aisle_polygon"])
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_reference = _finalize_specs(reference_specs, camera=camera, frame=frame)
        finalized_candidates = _finalize_specs(candidate_specs, camera=camera, frame=frame)
        finalized_context = _finalize_specs(context_specs, camera=camera, frame=frame)
        if not _visibility_ok(finalized_candidates, finalized_reference, finalized_context, camera=camera, frame=frame, render_params=render_params):
            continue
        answer_label = str(answer_meta["answer_label"])
        answer_spec = next(spec for spec in finalized_candidates if str(spec["point_label"]) == answer_label)
        if not bool(answer_spec.get("is_first_reached_object", False)):
            continue
        path_labels = [
            str(spec["point_label"])
            for spec in sorted(finalized_candidates, key=lambda item: (float(item["forward_distance_from_robot"]), str(item["point_label"])))
            if bool(spec.get("is_in_forward_path_corridor", False))
        ]
        first_reached_by_label = {str(spec["point_label"]): bool(spec.get("is_first_reached_object", False)) for spec in finalized_candidates}
        in_path_by_label = {str(spec["point_label"]): bool(spec.get("is_in_forward_path_corridor", False)) for spec in finalized_candidates}
        forward_distance_by_label = {str(spec["point_label"]): round(float(spec["forward_distance_from_robot"]), 4) for spec in finalized_candidates}
        lateral_offset_by_label = {str(spec["point_label"]): round(float(spec["lateral_offset_from_robot"]), 4) for spec in finalized_candidates}
        candidate_object_types = {str(spec["point_label"]): str(spec["object_type"]) for spec in finalized_candidates}
        candidate_projected_bboxes = {
            str(spec["point_label"]): [round(float(value), 3) for value in _object_screen_bbox(spec, camera, frame, pad_px=0.0)]
            for spec in finalized_candidates
        }
        object_type_counts = Counter(str(spec["object_type"]) for spec in [*finalized_reference, *finalized_candidates, *finalized_context])
        robot_arrow_start = (
            float(robot_xy[0]) + float(forward_xy[0]) * 0.26,
            float(robot_xy[1]) + float(forward_xy[1]) * 0.26,
            0.12,
        )
        robot_arrow_end = (
            float(robot_xy[0]) + float(forward_xy[0]) * 0.88,
            float(robot_xy[1]) + float(forward_xy[1]) * 0.88,
            0.12,
        )
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "candidate_count": int(candidate_count),
            "context_object_count": int(context_object_count),
            "robot_heading": str(robot_heading),
            "robot_design": str(finalized_reference[0].get("robot_design", "low_cart")),
            "travel_direction_vector_xy": [round(float(value), 4) for value in forward_xy],
            "path_corridor_half_width": float(PATH_CORRIDOR_HALF_WIDTH),
            "robot_path_corridor_polygon_world": list(scene_geometry["path_corridor_polygon"]),
            "main_aisle_polygon_world": list(scene_geometry["main_aisle_polygon"]),
            "shelf_zone_polygons_world": list(scene_geometry["shelf_zone_polygons"]),
            "robot_arrow_start_world": [round(float(value), 4) for value in robot_arrow_start],
            "robot_arrow_end_world": [round(float(value), 4) for value in robot_arrow_end],
            "reference_object": dict(finalized_reference[0]),
            "reference_object_specs": list(finalized_reference),
            "candidate_object_specs": sorted(finalized_candidates, key=lambda spec: str(spec["point_label"])),
            "context_object_specs": sorted(finalized_context, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted([*finalized_reference, *finalized_candidates, *finalized_context], key=lambda spec: str(spec["object_id"])),
            "target_object_ids": [str(answer_spec["object_id"])],
            "answer_label": str(answer_label),
            "answer_object_id": str(answer_spec["object_id"]),
            "answer_object_type": str(answer_spec["object_type"]),
            "first_reached_candidate_labels": [str(answer_label)],
            "forward_path_candidate_labels": list(path_labels),
            "first_reached_by_label": dict(sorted(first_reached_by_label.items())),
            "in_forward_path_corridor_by_label": dict(sorted(in_path_by_label.items())),
            "forward_distance_from_robot_by_label": dict(sorted(forward_distance_by_label.items())),
            "lateral_offset_from_robot_by_label": dict(sorted(lateral_offset_by_label.items())),
            "forward_order_near_to_far": [str(label) for label in answer_meta["forward_order_labels"]],
            "first_reached_margin": float(answer_meta["first_reached_margin"]),
            "candidate_object_types_by_label": dict(sorted(candidate_object_types.items())),
            "candidate_projected_bboxes_by_label": dict(sorted(candidate_projected_bboxes.items())),
            "object_type_counts": dict(sorted(object_type_counts.items())),
            "object_count": int(1 + len(finalized_candidates) + len(finalized_context)),
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
                "predicate": "first lettered object reached by the red-boxed robot moving straight along its arrow",
                "robot_heading": str(robot_heading),
                "travel_direction_vector_xy": [round(float(value), 4) for value in forward_xy],
                "first_reached_by_label": dict(sorted(first_reached_by_label.items())),
                "in_forward_path_corridor_by_label": dict(sorted(in_path_by_label.items())),
                "forward_distance_from_robot_by_label": dict(sorted(forward_distance_by_label.items())),
                "lateral_offset_from_robot_by_label": dict(sorted(lateral_offset_by_label.items())),
                "forward_order_near_to_far": [str(label) for label in answer_meta["forward_order_labels"]],
                "answer_label": str(answer_label),
                "answer_object_id": str(answer_spec["object_id"]),
                "unique_answer": True,
            },
        }
    raise ValueError("could not construct a visible warehouse robot scene")






_TASK_GROUP_DEFAULTS = get_scene_defaults("three_d", "warehouse")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
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
    robot_heading, _heading_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_ROBOT_HEADINGS,
        explicit_key="robot_heading",
        weights_key="robot_heading_weights",
        balance_flag_key="balanced_robot_heading_sampling",
        axis_namespace="robot_heading",
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
        lower=5,
        upper=6,
        allow_locked=True,
    )
    context_object_count, _context_probabilities = _shared_resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="context_object_count",
        default_min=11,
        default_max=11,
        lower=8,
        upper=13,
        allow_locked=True,
    )
    _camera_yaw_band, _camera_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(params=params, instance_seed=int(instance_seed))
    locked_params.update(
        {
            "_locked_query_id": str(query_id),
            "_locked_scene_variant": str(scene_variant),
            "_locked_robot_heading": str(robot_heading),
            "_locked_candidate_count": int(candidate_count),
            "_locked_context_object_count": int(context_object_count),
            "_locked_camera_yaw_band_index": int(camera_yaw_band_index),
        }
    )
    return locked_params


@register_task
class ThreeDWarehouseRobotForwardPathLabelTask:
    """Choose the first object a red-boxed robot would reach when moving forward."""

    task_id = TASK_ID
    domain = "three_d"
    scene_id = "warehouse"
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
        robot_heading, robot_heading_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_ROBOT_HEADINGS,
            explicit_key="robot_heading",
            weights_key="robot_heading_weights",
            balance_flag_key="balanced_robot_heading_sampling",
            axis_namespace="robot_heading",
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
            lower=5,
            upper=6,
            allow_locked=True,
        )
        context_object_count, context_count_probabilities = _shared_resolve_count(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="context_object_count",
            default_min=11,
            default_max=11,
            lower=8,
            upper=13,
            allow_locked=True,
        )
        camera_yaw_band, camera_yaw_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(params=params, instance_seed=int(instance_seed))
        render_params = _resolve_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.canvas",
        )
        dataset = _build_dataset(
            params=params,
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            robot_heading=str(robot_heading),
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
        rendered_scene = render_warehouse_robot_scene_3d(
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
            scene_id=self.scene_id,
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
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in rendered_scene.annotation_bboxes]
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        solver_trace = dict(dataset["solver_trace"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_warehouse_robot",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "candidate_count": int(dataset["candidate_count"]),
                    "context_object_count": int(dataset["context_object_count"]),
                    "robot_heading": str(dataset["robot_heading"]),
                    "robot_design": str(dataset["robot_design"]),
                    "travel_direction_vector_xy": list(dataset["travel_direction_vector_xy"]),
                    "first_reached_by_label": dict(dataset["first_reached_by_label"]),
                    "answer_label": str(answer_label),
                    "answer_object_id": str(dataset["answer_object_id"]),
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
                    "robot_heading": str(robot_heading),
                    "robot_heading_probabilities": dict(robot_heading_probabilities),
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
                "scene_canvas_preset": str(render_params.canvas_preset),
                "scene_canvas_width": int(render_params.canvas_width),
                "scene_canvas_height": int(render_params.canvas_height),
                "scene_canvas_policy": str(render_params.canvas_policy),
                "final_canvas_width": int(image.width),
                "final_canvas_height": int(image.height),
                "final_canvas_pixels": int(image.width) * int(image.height),
                "option_panel_height_px": int(rendered_scene.option_panel_height_px),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "label_font_size_px": int(render_params.label_font_size_px),
                "robot_heading": str(dataset["robot_heading"]),
                "robot_design": str(dataset["robot_design"]),
                "travel_direction_vector_xy": list(dataset["travel_direction_vector_xy"]),
                "path_corridor_half_width": float(dataset["path_corridor_half_width"]),
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
                "answer_object_type": str(dataset["answer_object_type"]),
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
                "robot_heading": str(dataset["robot_heading"]),
                "robot_design": str(dataset["robot_design"]),
                "travel_direction_vector_xy": list(dataset["travel_direction_vector_xy"]),
                "path_corridor_half_width": float(dataset["path_corridor_half_width"]),
                "robot_path_corridor_polygon_world": list(dataset["robot_path_corridor_polygon_world"]),
                "first_reached_candidate_labels": list(dataset["first_reached_candidate_labels"]),
                "forward_path_candidate_labels": list(dataset["forward_path_candidate_labels"]),
                "first_reached_by_label": dict(dataset["first_reached_by_label"]),
                "in_forward_path_corridor_by_label": dict(dataset["in_forward_path_corridor_by_label"]),
                "forward_distance_from_robot_by_label": dict(dataset["forward_distance_from_robot_by_label"]),
                "lateral_offset_from_robot_by_label": dict(dataset["lateral_offset_from_robot_by_label"]),
                "forward_order_near_to_far": list(dataset["forward_order_near_to_far"]),
                "first_reached_margin": float(dataset["first_reached_margin"]),
                "candidate_object_types_by_label": dict(dataset["candidate_object_types_by_label"]),
                "candidate_projected_bboxes_by_label": dict(dataset["candidate_projected_bboxes_by_label"]),
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["ThreeDWarehouseRobotForwardPathLabelTask"]
