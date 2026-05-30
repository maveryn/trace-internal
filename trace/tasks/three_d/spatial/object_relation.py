"""Object-relation label task for a synthetic 3D object scene."""

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
from ..shared.object_resources import (
    SPATIAL_OBJECT_RELATION_ELEVATED_COMPATIBLE_SHAPES,
    SPATIAL_OBJECT_RELATION_INSIDE_PROP_TYPES,
    SPATIAL_OBJECT_RELATION_ON_TOP_PROP_TYPES,
    SPATIAL_OBJECT_RELATION_UNDER_PROP_TYPES,
)
from ..shared.object_scene import (
    LARGE_CONTEXT_SHAPE_TYPES,
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


TASK_ID = "task_three_d__object_scene__object_relation_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("on_top_of_prop", "under_prop", "inside_prop")
ON_TOP_PROP_TYPES: Tuple[str, ...] = SPATIAL_OBJECT_RELATION_ON_TOP_PROP_TYPES
UNDER_PROP_TYPES: Tuple[str, ...] = SPATIAL_OBJECT_RELATION_UNDER_PROP_TYPES
INSIDE_PROP_TYPES: Tuple[str, ...] = SPATIAL_OBJECT_RELATION_INSIDE_PROP_TYPES
ELEVATED_COMPATIBLE_SHAPES: Tuple[str, ...] = SPATIAL_OBJECT_RELATION_ELEVATED_COMPATIBLE_SHAPES






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


def _make_sampled_object(
    *,
    rng,
    object_id: str,
    shape_type: str,
    object_role: str,
    xy: Tuple[float, float],
    label: str | None = None,
    base_z: float = 0.0,
) -> Dict[str, Any]:
    dimensions_xyz, dimension_scale = _sample_shape_dimensions(str(shape_type), object_role=str(object_role), rng=rng)
    spec = _make_object_spec(
        object_id=str(object_id),
        shape_type=str(shape_type),
        object_role=str(object_role),
        xy=xy,
        dimensions_xyz=dimensions_xyz,
        dimension_scale=float(dimension_scale),
        label=label,
    )
    if float(base_z) != 0.0:
        spec = _set_object_base_z(spec, float(base_z))
    return spec


def _query_reference_shapes(query_id: str) -> Tuple[str, ...]:
    if str(query_id) == "on_top_of_prop":
        return ON_TOP_PROP_TYPES
    if str(query_id) == "under_prop":
        return UNDER_PROP_TYPES
    return INSIDE_PROP_TYPES


def _answer_base_z(query_id: str, reference_spec: Mapping[str, Any]) -> float:
    if str(query_id) == "on_top_of_prop":
        return round(float(reference_spec["base_xyz"][2]) + float(reference_spec["dimensions_xyz"][2]) + 0.03, 4)
    if str(query_id) == "inside_prop":
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
    inside_footprint = dx <= r_width * 0.33 and dy <= r_depth * 0.33
    if str(query_id) == "on_top_of_prop":
        return bool(inside_footprint and c_base >= r_base + r_height * 0.92)
    if str(query_id) == "under_prop":
        return bool(inside_footprint and c_base < r_base + r_height * 0.18)
    return bool(dx <= r_width * 0.24 and dy <= r_depth * 0.24 and c_base < r_base + r_height * 0.35)


def _candidate_slots(query_id: str) -> List[Tuple[float, float]]:
    if str(query_id) == "inside_prop":
        return [(-2.35, -1.85), (-1.4, 2.18), (1.42, -2.18), (2.35, 1.76), (-2.38, 1.42)]
    return [(-2.35, -1.95), (-1.42, 2.16), (1.42, -2.16), (2.35, 1.82), (0.0, -2.42)]


def _build_relation_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    point_count: int,
    context_object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
    camera_yaw_band: Tuple[float, float] | None = None,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    relation_index = SUPPORTED_QUERY_IDS.index(str(query_id))
    selected_camera_yaw_band = (
        tuple(float(value) for value in camera_yaw_band)
        if camera_yaw_band is not None
        else _camera_yaw_band_for_instance(int(instance_seed))
    )
    for _attempt in range(300):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        answer_label = str(POINT_LABELS[abs(int(instance_seed) + relation_index * 2) % int(point_count)])
        remaining_labels = [str(label) for label in POINT_LABELS[: int(point_count)] if str(label) != answer_label]
        rng.shuffle(remaining_labels)

        reference_shape = str(rng.choice(_query_reference_shapes(str(query_id))))
        reference_spec = _make_sampled_object(
            rng=rng,
            object_id=f"context_reference_{reference_shape}",
            shape_type=reference_shape,
            object_role="context",
            xy=(0.0, 0.18),
        )
        answer_shape_pool = list(
            ELEVATED_COMPATIBLE_SHAPES if str(query_id) in {"on_top_of_prop", "inside_prop"} else NAMEABLE_SMALL_OBJECT_SHAPE_TYPES
        )
        answer_shape = str(rng.choice(answer_shape_pool))
        answer_base_z = _answer_base_z(str(query_id), reference_spec)
        answer_xy = (
            float(reference_spec["world_xyz"][0] + rng.uniform(-0.08, 0.08)),
            float(reference_spec["world_xyz"][1] + rng.uniform(-0.08, 0.08)),
        )
        answer_spec = _make_sampled_object(
            rng=rng,
            object_id=f"object_{answer_label}",
            shape_type=answer_shape,
            object_role="candidate",
            xy=answer_xy,
            label=answer_label,
            base_z=float(answer_base_z),
        )
        if str(query_id) == "inside_prop":
            answer_spec.update(
                {
                    "contained_by_object_id": str(reference_spec["object_id"]),
                    "render_order_bias": -12.0,
                    "visibility_role": "contained_answer_foreground",
                }
            )

        shape_pool = [str(shape) for shape in NAMEABLE_SMALL_OBJECT_SHAPE_TYPES if str(shape) != answer_shape]
        rng.shuffle(shape_pool)
        distractor_slots = list(_candidate_slots(str(query_id)))
        rng.shuffle(distractor_slots)
        candidate_specs = [answer_spec]
        for index, label in enumerate(remaining_labels):
            shape = str(shape_pool[index % len(shape_pool)])
            slot_x, slot_y = distractor_slots[index % len(distractor_slots)]
            spec = _make_sampled_object(
                rng=rng,
                object_id=f"object_{label}",
                shape_type=shape,
                object_role="candidate",
                xy=(float(slot_x + rng.uniform(-0.10, 0.10)), float(slot_y + rng.uniform(-0.10, 0.10))),
                label=str(label),
            )
            candidate_specs.append(spec)

        context_specs = [reference_spec]
        extra_context_shapes = [str(shape) for shape in LARGE_CONTEXT_SHAPE_TYPES if str(shape) != reference_shape]
        rng.shuffle(extra_context_shapes)
        extra_slots = [(-2.25, 1.18), (2.18, 1.25), (-2.18, -0.88), (2.18, -0.88)]
        rng.shuffle(extra_slots)
        for index in range(max(0, int(context_object_count) - 1)):
            shape = str(extra_context_shapes[index % len(extra_context_shapes)])
            slot_x, slot_y = extra_slots[index % len(extra_slots)]
            context_specs.append(
                _make_sampled_object(
                    rng=rng,
                    object_id=f"context_{index}_{shape}",
                    shape_type=shape,
                    object_role="context",
                    xy=(float(slot_x + rng.uniform(-0.08, 0.08)), float(slot_y + rng.uniform(-0.08, 0.08))),
                )
            )

        if not _relation_truth(str(query_id), answer_spec, reference_spec):
            continue
        relation_status_by_label = {
            str(spec["point_label"]): bool(_relation_truth(str(query_id), spec, reference_spec)) for spec in candidate_specs
        }
        if sum(1 for value in relation_status_by_label.values() if bool(value)) != 1:
            continue

        all_specs = [*candidate_specs, *context_specs]
        reference_points = [point for spec in all_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        screens = [_project_screen(spec["world_xyz"], camera, frame) for spec in candidate_specs]
        context_screens = [_project_screen(spec["world_xyz"], camera, frame) for spec in context_specs]
        screen_centers = [(screen[0], screen[1]) for screen in screens]
        screen_bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=16.0) for spec in candidate_specs]
        all_screen_bboxes = [
            (str(spec["object_id"]), _object_screen_bbox(spec, camera, frame, pad_px=16.0))
            for spec in all_specs
        ]
        intended_relation_pair = {str(answer_spec["object_id"]), str(reference_spec["object_id"])}
        if any(
            math.hypot(a[0] - b[0], a[1] - b[1]) < 48.0
            for index, a in enumerate(screen_centers)
            for b in screen_centers[index + 1 :]
        ):
            continue
        if any(
            _bbox_intersection_area(a, b) > 5200.0
            for index, a in enumerate(screen_bboxes)
            for b in screen_bboxes[index + 1 :]
        ):
            continue
        if any(
            _bbox_intersection_area(a, b) > 18000.0
            for index, (a_id, a) in enumerate(all_screen_bboxes)
            for b_id, b in all_screen_bboxes[index + 1 :]
            if {str(a_id), str(b_id)} != intended_relation_pair
        ):
            continue

        finalized_specs: List[Dict[str, Any]] = []
        for index, spec in enumerate(candidate_specs):
            screen = screens[index]
            finalized = dict(spec)
            finalized.update(
                {
                    "screen_xy": [round(float(screen[0]), 3), round(float(screen[1]), 3)],
                    "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
                    "camera_distance": round(float(screen[7]), 4),
                }
            )
            finalized_specs.append(finalized)
        finalized_context_specs: List[Dict[str, Any]] = []
        for index, spec in enumerate(context_specs):
            screen = context_screens[index]
            finalized = dict(spec)
            finalized.update(
                {
                    "screen_xy": [round(float(screen[0]), 3), round(float(screen[1]), 3)],
                    "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
                    "camera_distance": round(float(screen[7]), 4),
                }
            )
            finalized_context_specs.append(finalized)

        answer_spec = next(spec for spec in finalized_specs if str(spec["point_label"]) == str(answer_label))
        sorted_by_label = sorted(finalized_specs, key=lambda spec: str(spec["point_label"]))
        sorted_context = sorted(finalized_context_specs, key=lambda spec: str(spec["object_id"]))
        relation_true_labels = [str(label) for label, value in sorted(relation_status_by_label.items()) if bool(value)]
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "point_count": int(point_count),
            "candidate_count": int(point_count),
            "context_object_count": int(context_object_count),
            "object_count": int(point_count) + int(context_object_count),
            "point_specs": list(sorted_by_label),
            "context_object_specs": list(sorted_context),
            "object_specs": sorted([*sorted_by_label, *sorted_context], key=lambda spec: str(spec["object_id"])),
            "answer_label": str(answer_spec["point_label"]),
            "answer_point_id": str(answer_spec["point_id"]),
            "reference_object_id": str(reference_spec["object_id"]),
            "reference_object_name": str(reference_spec["prompt_name"]),
            "relation_status_by_label": dict(relation_status_by_label),
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
                "relation_kind": str(query_id),
                "candidate_only": True,
                "reference_object_id": str(reference_spec["object_id"]),
                "reference_object_name": str(reference_spec["prompt_name"]),
                "reference_shape_type": str(reference_spec["shape_type"]),
                "relation_status_by_label": dict(sorted(relation_status_by_label.items())),
                "relation_true_labels": relation_true_labels,
                "unique_relation_answer": True,
                "candidate_camera_distance_margin": round(float(_min_pairwise([float(spec["camera_distance"]) for spec in finalized_specs])), 4),
            },
        }
    raise ValueError("could not construct a valid 3D object-relation scene")




def _build_complexity(
    *,
    query_id: str,
    scene_variant: str,
    point_count: int,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.36)),
        "object_relation": float(raw_weights.get("object_relation", 0.40)),
        "occlusion_load": float(raw_weights.get("occlusion_load", 0.16)),
        "scene_variant_load": float(raw_weights.get("scene_variant_load", 0.08)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(int(point_count), 4, 8),
        "object_relation": {
            "on_top_of_prop": 0.50,
            "under_prop": 0.58,
            "inside_prop": 0.64,
        }.get(str(query_id), 0.56),
        "occlusion_load": {
            "on_top_of_prop": 0.38,
            "under_prop": 0.56,
            "inside_prop": 0.62,
        }.get(str(query_id), 0.50),
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
class ThreeDSpatialObjectRelationLabelTask:
    """Choose the small lettered 3D object in a relation to a named prop."""

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
            minimum_default=2,
            maximum_default=2,
            lower=1,
            upper=3,
        )
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_relation_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            context_object_count=int(context_object_count),
            render_params=render_params,
            instance_seed=int(instance_seed),
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
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
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
                    "relation_kind": str(query_id),
                    "reference_object_id": str(dataset["reference_object_id"]),
                    "reference_object_name": str(dataset["reference_object_name"]),
                    "relation_status_by_label": dict(dataset["relation_status_by_label"]),
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
                    "object_count": int(dataset["object_count"]),
                    "point_count_probabilities": dict(point_count_probabilities),
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_object_count_probabilities),
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
                "relation_status_by_label": dict(dataset["relation_status_by_label"]),
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


__all__ = ["ThreeDSpatialObjectRelationLabelTask"]
