"""Reference-nearest label task for a synthetic 3D object scene."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
)
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    split_scene_generation_rendering_prompt_defaults,
)
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.object_resources import SPATIAL_REFERENCE_NEAREST_REFERENCE_SHAPE_TYPES
from ..shared.object_scene import (
    LARGE_CONTEXT_SHAPE_TYPES,
    NAMEABLE_CONTEXT_SHAPE_TYPES,
    NAMED_SMALL_OBJECT_SHAPE_TYPES,
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
    _resolve_render_params,
    _sample_camera,
    _sample_shape_dimensions,
)
from ..shared.object_scene_output import build_option_label_object_scene_output as _build_option_label_object_scene_output
from .shared.relations import can_place as _can_place
from .shared.relations import finalize_specs as _finalize_specs
from .shared.relations import make_sampled_object as _make_sampled_object
from .shared.relations import prompt_name as _prompt_name


TASK_ID = "task_three_d__object_scene__reference_nearest_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("closest_to_reference",)
REFERENCE_SHAPE_TYPES: Tuple[str, ...] = SPATIAL_REFERENCE_NEAREST_REFERENCE_SHAPE_TYPES
SMALL_CANDIDATE_SHAPE_TYPES: Tuple[str, ...] = tuple(NAMED_SMALL_OBJECT_SHAPE_TYPES)
LARGE_CANDIDATE_SHAPE_TYPES: Tuple[str, ...] = tuple(NAMEABLE_CONTEXT_SHAPE_TYPES)
def _surface_gap(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    ax, ay, _az = (float(value) for value in a["world_xyz"])
    bx, by, _bz = (float(value) for value in b["world_xyz"])
    center_distance_xy = math.hypot(float(ax - bx), float(ay - by))
    return max(0.0, float(center_distance_xy) - float(a["footprint_radius"]) - float(b["footprint_radius"]))
def _candidate_role(shape_type: str) -> str:
    return "context" if str(shape_type) in set(LARGE_CONTEXT_SHAPE_TYPES) else "candidate"


def _sample_candidate_shapes(*, rng, reference_name: str, candidate_count: int, large_candidate_count: int) -> List[str]:
    small_pool = [str(shape) for shape in SMALL_CANDIDATE_SHAPE_TYPES]
    large_pool = [str(shape) for shape in LARGE_CANDIDATE_SHAPE_TYPES]
    rng.shuffle(small_pool)
    rng.shuffle(large_pool)
    selected: List[str] = []
    selected_names = {str(reference_name)}
    for shape in large_pool:
        probe = _make_sampled_object(rng=rng, object_id=f"probe_{shape}", shape_type=shape, object_role="context", xy=(0.0, 0.0))
        if _prompt_name(probe) not in selected_names:
            selected.append(shape)
            selected_names.add(_prompt_name(probe))
        if len([item for item in selected if item in set(LARGE_CONTEXT_SHAPE_TYPES)]) >= int(large_candidate_count):
            break
    for shape in small_pool + large_pool:
        role = _candidate_role(str(shape))
        probe = _make_sampled_object(rng=rng, object_id=f"probe_{shape}", shape_type=shape, object_role=role, xy=(0.0, 0.0))
        if _prompt_name(probe) in selected_names:
            continue
        selected.append(str(shape))
        selected_names.add(_prompt_name(probe))
        if len(selected) >= int(candidate_count):
            break
    if len(selected) < int(candidate_count):
        raise ValueError("could not sample enough unique candidate object names")
    return list(selected[: int(candidate_count)])
def _build_reference_nearest_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    point_count: int,
    large_candidate_count: int,
    render_params: _RenderParams,
    instance_seed: int,
    camera_yaw_band: Tuple[float, float] | None = None,
) -> Dict[str, Any]:
    """Build a nearest-to-reference scene with one labeled candidate closest to the reference object in world space."""
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    selected_camera_yaw_band = (
        tuple(float(value) for value in camera_yaw_band)
        if camera_yaw_band is not None
        else _camera_yaw_band_for_instance(int(instance_seed))
    )
    for _attempt in range(420):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        reference_shape = str(rng.choice(REFERENCE_SHAPE_TYPES))
        reference_role = _candidate_role(reference_shape)
        reference_spec = _make_sampled_object(
            rng=rng,
            object_id=f"reference_{reference_shape}",
            shape_type=reference_shape,
            object_role=reference_role,
            xy=(float(rng.uniform(-0.22, 0.22)), float(rng.uniform(-0.16, 0.24))),
        )
        if not bool(reference_spec.get("nameable_for_prompt", False)):
            continue

        labels = [str(label) for label in POINT_LABELS[: int(point_count)]]
        answer_label = labels[abs(int(instance_seed)) % int(point_count)]
        remaining_labels = [str(label) for label in labels if str(label) != str(answer_label)]
        rng.shuffle(remaining_labels)

        candidate_shapes = _sample_candidate_shapes(
            rng=rng,
            reference_name=_prompt_name(reference_spec),
            candidate_count=int(point_count),
            large_candidate_count=int(large_candidate_count),
        )
        answer_shape = str(candidate_shapes[0])
        distractor_shapes = list(candidate_shapes[1:])
        rng.shuffle(distractor_shapes)

        placed: List[Dict[str, Any]] = [dict(reference_spec)]
        ref_x, ref_y, _ref_z = (float(value) for value in reference_spec["world_xyz"])
        ref_radius = float(reference_spec["footprint_radius"])
        answer_role = _candidate_role(answer_shape)
        answer_dimensions, answer_scale = _sample_shape_dimensions(answer_shape, object_role=answer_role, rng=rng)
        answer_probe = _make_object_spec(
            object_id=f"object_{answer_label}",
            shape_type=answer_shape,
            object_role=answer_role,
            xy=(0.0, 0.0),
            dimensions_xyz=answer_dimensions,
            dimension_scale=float(answer_scale),
            label=answer_label,
        )
        answer_radius = float(answer_probe["footprint_radius"])
        angle = float(rng.choice([0.0, 0.72, 1.45, 2.25, 3.05, 3.85, 4.65, 5.45]) + rng.uniform(-0.18, 0.18))
        answer_gap = float(rng.uniform(0.16, 0.38))
        answer_distance = ref_radius + answer_radius + answer_gap
        answer_xy = (float(ref_x + math.cos(angle) * answer_distance), float(ref_y + math.sin(angle) * answer_distance))
        answer_spec = _make_object_spec(
            object_id=f"object_{answer_label}",
            shape_type=answer_shape,
            object_role=answer_role,
            xy=answer_xy,
            dimensions_xyz=answer_dimensions,
            dimension_scale=float(answer_scale),
            label=answer_label,
        )
        if not _can_place(answer_spec, placed, clearance=0.10):
            continue
        placed.append(answer_spec)

        candidate_specs = [answer_spec]
        ring_slots = [
            (-2.48, -2.12),
            (-1.10, -2.56),
            (1.22, -2.48),
            (2.52, -1.42),
            (2.38, 1.42),
            (0.98, 2.52),
            (-1.28, 2.46),
            (-2.48, 1.18),
        ]
        rng.shuffle(ring_slots)
        for index, label in enumerate(remaining_labels):
            shape = str(distractor_shapes[index % len(distractor_shapes)])
            role = _candidate_role(shape)
            dimensions, scale = _sample_shape_dimensions(shape, object_role=role, rng=rng)
            placed_spec: Dict[str, Any] | None = None
            for slot_x, slot_y in ring_slots[index:] + ring_slots[:index]:
                for _jitter_attempt in range(6):
                    xy = (
                        float(slot_x + rng.uniform(-0.12, 0.12)),
                        float(slot_y + rng.uniform(-0.12, 0.12)),
                    )
                    spec = _make_object_spec(
                        object_id=f"object_{label}",
                        shape_type=shape,
                        object_role=role,
                        xy=xy,
                        dimensions_xyz=dimensions,
                        dimension_scale=float(scale),
                        label=str(label),
                    )
                    if _surface_gap(reference_spec, spec) <= answer_gap + 0.34:
                        continue
                    if not _can_place(spec, placed, clearance=0.12):
                        continue
                    placed_spec = spec
                    break
                if placed_spec is not None:
                    break
            if placed_spec is None:
                break
            candidate_specs.append(placed_spec)
            placed.append(placed_spec)
        if len(candidate_specs) != int(point_count):
            continue

        all_specs = [*candidate_specs, reference_spec]
        reference_points = [point for spec in all_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        finalized_candidates = _finalize_specs(candidate_specs, camera=camera, frame=frame)
        finalized_context = _finalize_specs([reference_spec], camera=camera, frame=frame)
        reference_spec = finalized_context[0]
        all_finalized = [*finalized_candidates, reference_spec]

        candidate_screen_centers = [
            (float(spec["screen_xy"][0]), float(spec["screen_xy"][1]))
            for spec in finalized_candidates
        ]
        candidate_screen_bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=16.0) for spec in finalized_candidates]
        all_screen_bboxes = [
            (str(spec["object_id"]), _object_screen_bbox(spec, camera, frame, pad_px=16.0))
            for spec in all_finalized
        ]
        intended_reference_answer_pair = {str(reference_spec["object_id"]), f"object_{answer_label}"}
        if any(
            math.hypot(a[0] - b[0], a[1] - b[1]) < 34.0
            for index, a in enumerate(candidate_screen_centers)
            for b in candidate_screen_centers[index + 1 :]
        ):
            continue
        if any(
            _bbox_intersection_area(a, b) > 15000.0
            for index, a in enumerate(candidate_screen_bboxes)
            for b in candidate_screen_bboxes[index + 1 :]
        ):
            continue
        if any(
            _bbox_intersection_area(a, b) > 42000.0
            for index, (a_id, a) in enumerate(all_screen_bboxes)
            for b_id, b in all_screen_bboxes[index + 1 :]
            if {str(a_id), str(b_id)} != intended_reference_answer_pair
        ):
            continue

        gaps_by_label = {
            str(spec["point_label"]): round(float(_surface_gap(reference_spec, spec)), 4)
            for spec in finalized_candidates
        }
        sorted_by_gap = sorted(finalized_candidates, key=lambda spec: (float(gaps_by_label[str(spec["point_label"])]), str(spec["point_label"])))
        if str(sorted_by_gap[0]["point_label"]) != str(answer_label):
            continue
        if _min_pairwise([float(value) for value in gaps_by_label.values()]) < 0.16:
            continue
        if len(sorted_by_gap) > 1:
            margin = float(gaps_by_label[str(sorted_by_gap[1]["point_label"])]) - float(gaps_by_label[str(sorted_by_gap[0]["point_label"])])
            if margin < 0.24:
                continue
        else:
            margin = 999.0

        sorted_candidates = sorted(finalized_candidates, key=lambda spec: str(spec["point_label"]))
        distance_order = [str(spec["point_label"]) for spec in sorted_by_gap]
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "point_count": int(point_count),
            "candidate_count": int(point_count),
            "large_candidate_count": int(sum(1 for spec in finalized_candidates if str(spec["shape_type"]) in set(LARGE_CONTEXT_SHAPE_TYPES))),
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
            "candidate_reference_gaps_by_label": dict(sorted(gaps_by_label.items())),
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
                "sort_key": "surface_gap_to_reference",
                "candidate_only": True,
                "reference_excluded_from_options": True,
                "reference_object_id": str(reference_spec["object_id"]),
                "reference_object_name": _prompt_name(reference_spec),
                "reference_shape_type": str(reference_spec["shape_type"]),
                "candidate_reference_gaps_by_label": dict(sorted(gaps_by_label.items())),
                "reference_nearest_order": list(distance_order),
                "unique_reference_nearest_answer": True,
                "reference_nearest_margin": round(float(margin), 4),
            },
        }
    raise ValueError("could not construct a valid 3D reference-nearest scene")






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
class ThreeDSpatialReferenceNearestLabelTask:
    """Choose the lettered 3D object closest to a named reference object."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    domain = "three_d"
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
        """Generate one reference-nearest instance while preserving the accepted distance ranking in trace and annotation."""
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
        large_candidate_count, large_candidate_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="large_candidate_count",
            minimum_default=2,
            maximum_default=2,
            lower=0,
            upper=min(3, int(point_count)),
        )
        render_params = _resolve_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.canvas",
        )
        dataset = _build_reference_nearest_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            large_candidate_count=int(large_candidate_count),
            render_params=render_params,
            instance_seed=int(instance_seed),
            camera_yaw_band=camera_yaw_band,
        )
        relation_fields = {
            "large_candidate_count": int(dataset["large_candidate_count"]),
            "context_object_count": int(dataset["context_object_count"]),
            "reference_object_id": str(dataset["reference_object_id"]),
            "reference_object_name": str(dataset["reference_object_name"]),
            "reference_shape_type": str(dataset["reference_shape_type"]),
            "candidate_reference_gaps_by_label": dict(dataset["candidate_reference_gaps_by_label"]),
            "answer_point_id": str(dataset["answer_point_id"]),
        }
        return _build_option_label_object_scene_output(
            objective_name=TASK_ID,
            task_domain=self.domain,
            instance_seed=int(instance_seed),
            params=params,
            dataset=dataset,
            branch_key=str(query_id),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            context_object_count=int(dataset["context_object_count"]),
            render_params=render_params,
            prompt_defaults_config=_PROMPT_DEFAULTS,
            background_defaults=_BACKGROUND_DEFAULTS,
            noise_defaults=_NOISE_DEFAULTS,
            query_probabilities=query_probabilities,
            scene_probabilities=scene_probabilities,
            point_count_probabilities=point_count_probabilities,
            context_object_count_probabilities={str(dataset["context_object_count"]): 1.0},
            dynamic_slots={
                "reference_name": str(dataset["reference_object_name"]),
            },
            relation_fields=relation_fields,
            query_params_extra={
                "large_candidate_count": int(dataset["large_candidate_count"]),
                "large_candidate_count_probabilities": dict(large_candidate_count_probabilities),
                "reference_object_id": str(dataset["reference_object_id"]),
                "reference_object_name": str(dataset["reference_object_name"]),
            },
            execution_extra={
                "large_candidate_count": int(dataset["large_candidate_count"]),
                "context_object_count": int(dataset["context_object_count"]),
                "reference_object_id": str(dataset["reference_object_id"]),
                "reference_object_name": str(dataset["reference_object_name"]),
                "reference_shape_type": str(dataset["reference_shape_type"]),
                "candidate_reference_gaps_by_label": dict(dataset["candidate_reference_gaps_by_label"]),
            },
        )



__all__ = ["ThreeDSpatialReferenceNearestLabelTask"]
