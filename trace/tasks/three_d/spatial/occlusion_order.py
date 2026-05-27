"""Occlusion-order label task for a synthetic 3D object scene."""

from __future__ import annotations

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
from ...shared.deterministic_sampling import resolve_selection_index
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
from ..shared.object_resources import SPATIAL_OCCLUSION_REFERENCE_SHAPE_TYPES
from .camera_distance import (
    NAMEABLE_SMALL_OBJECT_SHAPE_TYPES,
    POINT_LABELS,
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


TASK_ID = "task_three_d__object_scene__occlusion_order_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("in_front_of_reference",)
REFERENCE_SHAPE_TYPES: Tuple[str, ...] = SPATIAL_OCCLUSION_REFERENCE_SHAPE_TYPES
SMALL_CANDIDATE_SHAPE_TYPES: Tuple[str, ...] = tuple(NAMEABLE_SMALL_OBJECT_SHAPE_TYPES)






def _make_sampled_object(
    *,
    rng,
    object_id: str,
    shape_type: str,
    object_role: str,
    xy: Tuple[float, float],
    label: str | None = None,
) -> Dict[str, Any]:
    dimensions_xyz, dimension_scale = _sample_shape_dimensions(str(shape_type), object_role=str(object_role), rng=rng)
    return _make_object_spec(
        object_id=str(object_id),
        shape_type=str(shape_type),
        object_role=str(object_role),
        xy=xy,
        dimensions_xyz=dimensions_xyz,
        dimension_scale=float(dimension_scale),
        label=label,
    )


def _set_xy(spec: Mapping[str, Any], xy: Tuple[float, float]) -> Dict[str, Any]:
    updated = dict(spec)
    height = float(updated["dimensions_xyz"][2])
    updated["base_xyz"] = [round(float(xy[0]), 4), round(float(xy[1]), 4), 0.0]
    updated["world_xyz"] = [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(height * 0.5), 4)]
    return updated


def _prompt_name(spec: Mapping[str, Any]) -> str:
    return str(spec.get("prompt_name", spec.get("object_name", spec.get("shape_type", "object"))))


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _can_place(candidate: Mapping[str, Any], placed: Sequence[Mapping[str, Any]], *, clearance: float = 0.12) -> bool:
    for item in placed:
        cx, cy, _cz = (float(value) for value in candidate["world_xyz"])
        ix, iy, _iz = (float(value) for value in item["world_xyz"])
        min_distance = float(candidate["footprint_radius"]) + float(item["footprint_radius"]) + float(clearance)
        if math.hypot(float(cx - ix), float(cy - iy)) < min_distance:
            return False
    return True


def _unit_towards_camera(reference_spec: Mapping[str, Any], camera) -> Tuple[float, float]:
    ref_x, ref_y, _ref_z = (float(value) for value in reference_spec["world_xyz"])
    dx = float(camera.camera_position[0]) - float(ref_x)
    dy = float(camera.camera_position[1]) - float(ref_y)
    length = max(1e-6, math.hypot(dx, dy))
    return (float(dx / length), float(dy / length))


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


def _sample_distractor_specs(
    *,
    rng,
    labels: Sequence[str],
    shape_pool: Sequence[str],
    placed: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    ring_slots = [
        (-2.54, -2.18),
        (-1.16, -2.58),
        (1.18, -2.52),
        (2.52, -1.42),
        (2.44, 1.42),
        (1.02, 2.52),
        (-1.34, 2.46),
        (-2.52, 1.18),
    ]
    rng.shuffle(ring_slots)
    distractors: List[Dict[str, Any]] = []
    for index, label in enumerate(labels):
        shape = str(shape_pool[index % len(shape_pool)])
        placed_spec: Dict[str, Any] | None = None
        for slot_x, slot_y in ring_slots[index:] + ring_slots[:index]:
            for _jitter_attempt in range(6):
                spec = _make_sampled_object(
                    rng=rng,
                    object_id=f"object_{label}",
                    shape_type=shape,
                    object_role="candidate",
                    xy=(float(slot_x + rng.uniform(-0.13, 0.13)), float(slot_y + rng.uniform(-0.13, 0.13))),
                    label=str(label),
                )
                if _can_place(spec, placed, clearance=0.12):
                    placed_spec = spec
                    break
            if placed_spec is not None:
                break
        if placed_spec is None:
            raise ValueError("could not place 3D occlusion distractor")
        distractors.append(placed_spec)
        placed.append(placed_spec)
    return list(distractors)


def _build_occlusion_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    point_count: int,
    context_object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
    answer_label_index: int | None = None,
    camera_yaw_band: Tuple[float, float] | None = None,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    label_selection_index = int(answer_label_index) if answer_label_index is not None else int(instance_seed)
    selected_camera_yaw_band = (
        tuple(float(value) for value in camera_yaw_band)
        if camera_yaw_band is not None
        else _camera_yaw_band_for_instance(int(instance_seed))
    )
    for _attempt in range(360):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        labels = [str(label) for label in POINT_LABELS[: int(point_count)]]
        answer_label = labels[abs(int(label_selection_index)) % int(point_count)]
        remaining_labels = [str(label) for label in labels if str(label) != str(answer_label)]
        rng.shuffle(remaining_labels)

        reference_shape = str(rng.choice(REFERENCE_SHAPE_TYPES))
        reference_spec = _make_sampled_object(
            rng=rng,
            object_id=f"reference_{reference_shape}",
            shape_type=reference_shape,
            object_role="context",
            xy=(float(rng.uniform(-0.16, 0.16)), float(rng.uniform(-0.12, 0.18))),
        )
        if not bool(reference_spec.get("nameable_for_prompt", False)):
            continue

        shape_pool = list(SMALL_CANDIDATE_SHAPE_TYPES)
        rng.shuffle(shape_pool)
        answer_shape = str(shape_pool[0])
        answer_spec = _make_sampled_object(
            rng=rng,
            object_id=f"object_{answer_label}",
            shape_type=answer_shape,
            object_role="candidate",
            xy=(0.0, 0.0),
            label=answer_label,
        )

        unit_x, unit_y = _unit_towards_camera(reference_spec, camera)
        side_x, side_y = -unit_y, unit_x
        ref_x, ref_y, _ref_z = (float(value) for value in reference_spec["world_xyz"])
        forward_offset = float(reference_spec["footprint_radius"]) * rng.uniform(0.38, 0.58) + float(answer_spec["footprint_radius"]) * rng.uniform(0.04, 0.22)
        lateral_offset = float(rng.uniform(-0.16, 0.16))
        answer_xy = (
            float(ref_x + unit_x * forward_offset + side_x * lateral_offset),
            float(ref_y + unit_y * forward_offset + side_y * lateral_offset),
        )
        if max(abs(answer_xy[0]), abs(answer_xy[1])) > float(render_params.room_extent) - 0.35:
            continue
        answer_spec = _set_xy(answer_spec, answer_xy)

        placed = [dict(reference_spec), dict(answer_spec)]
        distractor_shapes = [str(shape) for shape in shape_pool[1:]] + [str(shape) for shape in shape_pool[:1]]
        try:
            distractor_specs = _sample_distractor_specs(
                rng=rng,
                labels=remaining_labels,
                shape_pool=distractor_shapes,
                placed=placed,
            )
        except ValueError:
            continue

        candidate_specs = [answer_spec, *distractor_specs]
        if len(candidate_specs) != int(point_count):
            continue
        if int(context_object_count) != 1:
            raise ValueError("occlusion-order scenes use exactly one named reference object")

        all_specs = [*candidate_specs, reference_spec]
        reference_points = [point for spec in all_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        finalized_candidates = _finalize_specs(candidate_specs, camera=camera, frame=frame)
        reference_spec = _finalize_specs([reference_spec], camera=camera, frame=frame)[0]
        all_finalized = [*finalized_candidates, reference_spec]

        reference_bbox = _object_screen_bbox(reference_spec, camera, frame, pad_px=0.0)
        candidate_bboxes = {
            str(spec["point_label"]): _object_screen_bbox(spec, camera, frame, pad_px=0.0)
            for spec in finalized_candidates
        }
        padded_candidate_bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=16.0) for spec in finalized_candidates]
        all_padded_bboxes = [
            (str(spec["object_id"]), _object_screen_bbox(spec, camera, frame, pad_px=16.0))
            for spec in all_finalized
        ]
        answer_bbox = candidate_bboxes[str(answer_label)]
        answer_overlap = float(_bbox_intersection_area(answer_bbox, reference_bbox))
        answer_overlap_fraction = answer_overlap / max(1.0, min(_bbox_area(answer_bbox), _bbox_area(reference_bbox)))
        answer_depth_margin = float(reference_spec["camera_distance"]) - float(
            next(spec for spec in finalized_candidates if str(spec["point_label"]) == str(answer_label))["camera_distance"]
        )
        if answer_overlap < 700.0 or answer_overlap_fraction < 0.10 or answer_depth_margin < 0.22:
            continue

        overlap_area_by_label: Dict[str, float] = {}
        depth_margin_by_label: Dict[str, float] = {}
        occlusion_status_by_label: Dict[str, bool] = {}
        for spec in finalized_candidates:
            label = str(spec["point_label"])
            overlap_area = float(_bbox_intersection_area(candidate_bboxes[label], reference_bbox))
            depth_margin = float(reference_spec["camera_distance"]) - float(spec["camera_distance"])
            overlap_area_by_label[label] = round(float(overlap_area), 4)
            depth_margin_by_label[label] = round(float(depth_margin), 4)
            occlusion_status_by_label[label] = bool(overlap_area >= 500.0 and depth_margin >= 0.18)

        front_labels = [str(label) for label, is_front in sorted(occlusion_status_by_label.items()) if bool(is_front)]
        if front_labels != [str(answer_label)]:
            continue
        if any(
            str(label) != str(answer_label) and float(overlap_area) > 300.0
            for label, overlap_area in overlap_area_by_label.items()
        ):
            continue

        candidate_screen_centers = [
            (float(spec["screen_xy"][0]), float(spec["screen_xy"][1]))
            for spec in finalized_candidates
        ]
        if any(
            math.hypot(a[0] - b[0], a[1] - b[1]) < 34.0
            for index, a in enumerate(candidate_screen_centers)
            for b in candidate_screen_centers[index + 1 :]
        ):
            continue
        if any(
            _bbox_intersection_area(a, b) > 12000.0
            for index, a in enumerate(padded_candidate_bboxes)
            for b in padded_candidate_bboxes[index + 1 :]
        ):
            continue
        intended_reference_answer_pair = {str(reference_spec["object_id"]), f"object_{answer_label}"}
        if any(
            _bbox_intersection_area(a, b) > 22000.0
            for index, (a_id, a) in enumerate(all_padded_bboxes)
            for b_id, b in all_padded_bboxes[index + 1 :]
            if {str(a_id), str(b_id)} != intended_reference_answer_pair
        ):
            continue

        sorted_candidates = sorted(finalized_candidates, key=lambda spec: str(spec["point_label"]))
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "point_count": int(point_count),
            "candidate_count": int(point_count),
            "context_object_count": 1,
            "object_count": int(point_count) + 1,
            "point_specs": list(sorted_candidates),
            "context_object_specs": [dict(reference_spec)],
            "object_specs": sorted([*sorted_candidates, reference_spec], key=lambda spec: str(spec["object_id"])),
            "answer_label": str(answer_label),
            "answer_point_id": f"object_{answer_label}",
            "reference_object_id": str(reference_spec["object_id"]),
            "reference_object_name": _prompt_name(reference_spec),
            "reference_shape_type": str(reference_spec["shape_type"]),
            "candidate_reference_overlap_area_by_label": dict(sorted(overlap_area_by_label.items())),
            "candidate_depth_margin_to_reference_by_label": dict(sorted(depth_margin_by_label.items())),
            "occlusion_status_by_label": dict(sorted(occlusion_status_by_label.items())),
            "camera": {
                "camera_position": [round(float(value), 4) for value in camera.camera_position],
                "target": [round(float(value), 4) for value in camera.target],
                "yaw_degrees": round(float(camera.yaw_degrees), 4),
                "yaw_band_degrees": [round(float(value), 4) for value in selected_camera_yaw_band],
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
                "sort_key": "projected_overlap_and_camera_distance",
                "candidate_only": True,
                "reference_excluded_from_options": True,
                "reference_object_id": str(reference_spec["object_id"]),
                "reference_object_name": _prompt_name(reference_spec),
                "reference_shape_type": str(reference_spec["shape_type"]),
                "candidate_reference_overlap_area_by_label": dict(sorted(overlap_area_by_label.items())),
                "candidate_depth_margin_to_reference_by_label": dict(sorted(depth_margin_by_label.items())),
                "occlusion_status_by_label": dict(sorted(occlusion_status_by_label.items())),
                "front_of_reference_labels": list(front_labels),
                "unique_front_answer": True,
                "front_depth_margin": round(float(answer_depth_margin), 4),
                "front_overlap_area": round(float(answer_overlap), 4),
            },
        }
    raise ValueError("could not construct a valid 3D occlusion-order scene")




def _build_complexity(
    *,
    scene_variant: str,
    point_count: int,
    depth_margin: float,
    overlap_area: float,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.34)),
        "occlusion_ordering": float(raw_weights.get("occlusion_ordering", 0.42)),
        "ambiguity": float(raw_weights.get("ambiguity", 0.16)),
        "scene_variant_load": float(raw_weights.get("scene_variant_load", 0.08)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(int(point_count), 4, 8),
        "occlusion_ordering": 0.68,
        "ambiguity": 0.5 * (1.0 - _normalize_unit(float(depth_margin), 0.18, 0.8))
        + 0.5 * (1.0 - _normalize_unit(float(overlap_area), 600.0, 3600.0)),
        "scene_variant_load": {
            "floor_grid_room": 0.28,
            "tabletop_room": 0.32,
            "studio_platform": 0.36,
        }.get(str(scene_variant), 0.30),
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
class ThreeDSpatialOcclusionOrderLabelTask:
    """Choose the lettered 3D object visually in front of a named reference object."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "spatial"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
        answer_seed = int(instance_seed)
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return self._generate_once(
                    int(attempt_seed),
                    params=params,
                    camera_yaw_band=camera_yaw_band,
                    answer_seed=answer_seed,
                )
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        camera_yaw_band: Tuple[float, float] | None = None,
        answer_seed: int | None = None,
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
        point_count, point_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="point_count",
            minimum_default=6,
            maximum_default=6,
            lower=4,
            upper=8,
        )
        context_object_count, context_object_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="context_object_count",
            minimum_default=1,
            maximum_default=1,
            lower=1,
            upper=1,
        )
        answer_label_index = resolve_selection_index(
            params=params,
            instance_seed=int(answer_seed) if answer_seed is not None else int(instance_seed),
            namespace=f"{TASK_ID}.answer_label",
        )
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_occlusion_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            context_object_count=int(context_object_count),
            render_params=render_params,
            instance_seed=int(instance_seed),
            answer_label_index=int(answer_label_index),
            camera_yaw_band=camera_yaw_band,
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_object_scene_3d(background, dataset=dataset, render_params=render_params)
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
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "reference_name": str(dataset["reference_object_name"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_label = str(dataset["answer_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in rendered_scene.evidence_bboxes]
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        solver_trace = dict(dataset["solver_trace"])
        complexity = _build_complexity(
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            depth_margin=float(solver_trace.get("front_depth_margin", 0.22)),
            overlap_area=float(solver_trace.get("front_overlap_area", 700.0)),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "point_count": int(point_count),
                    "candidate_count": int(point_count),
                    "context_object_count": int(context_object_count),
                    "object_count": int(dataset["object_count"]),
                    "candidate_shape_types": [str(spec["shape_type"]) for spec in dataset["point_specs"]],
                    "context_shape_types": [str(spec["shape_type"]) for spec in dataset["context_object_specs"]],
                    "candidate_object_names": [str(spec["object_name"]) for spec in dataset["point_specs"]],
                    "context_object_names": [str(spec["object_name"]) for spec in dataset["context_object_specs"]],
                    "view_family": "synthetic_perspective_3d_scene",
                    "reference_object_id": str(dataset["reference_object_id"]),
                    "reference_object_name": str(dataset["reference_object_name"]),
                    "reference_shape_type": str(dataset["reference_shape_type"]),
                    "occlusion_status_by_label": dict(dataset["occlusion_status_by_label"]),
                    "candidate_reference_overlap_area_by_label": dict(dataset["candidate_reference_overlap_area_by_label"]),
                    "candidate_depth_margin_to_reference_by_label": dict(dataset["candidate_depth_margin_to_reference_by_label"]),
                    "answer_point_id": str(dataset["answer_point_id"]),
                    "answer_label": str(answer_label),
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
                    "point_count": int(point_count),
                    "candidate_count": int(point_count),
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_object_count_probabilities),
                    "point_count_probabilities": dict(point_count_probabilities),
                    "object_count": int(dataset["object_count"]),
                    "reference_object_id": str(dataset["reference_object_id"]),
                    "reference_object_name": str(dataset["reference_object_name"]),
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
                "point_bboxes_px": {str(key): list(value) for key, value in rendered_scene.point_bboxes_px.items()},
                "point_centers_px": {str(key): list(value) for key, value in rendered_scene.point_centers_px.items()},
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "context_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.context_object_bboxes_px.items()},
                "context_object_centers_px": {str(key): list(value) for key, value in rendered_scene.context_object_centers_px.items()},
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "point_count": int(point_count),
                "candidate_count": int(point_count),
                "context_object_count": int(context_object_count),
                "object_count": int(dataset["object_count"]),
                "point_specs": [dict(spec) for spec in dataset["point_specs"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "answer_label": str(answer_label),
                "answer_point_id": str(dataset["answer_point_id"]),
                "reference_object_id": str(dataset["reference_object_id"]),
                "reference_object_name": str(dataset["reference_object_name"]),
                "reference_shape_type": str(dataset["reference_shape_type"]),
                "occlusion_status_by_label": dict(dataset["occlusion_status_by_label"]),
                "candidate_reference_overlap_area_by_label": dict(dataset["candidate_reference_overlap_area_by_label"]),
                "candidate_depth_margin_to_reference_by_label": dict(dataset["candidate_depth_margin_to_reference_by_label"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "view_family": "synthetic_perspective_3d_scene",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(item) for item in rendered_scene.evidence_entity_ids],
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
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["ThreeDSpatialOcclusionOrderLabelTask"]
