"""Camera-distance label task for wall-mounted objects in a 3D room scene."""

from __future__ import annotations

from collections import Counter
import math
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
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
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
    ROOM_CAMERA_DISTANCE_CANDIDATE_WALL_OBJECT_TYPES,
    ROOM_CAMERA_DISTANCE_CONTEXT_WALL_OBJECT_TYPES,
)
from ..shared.option_panel import build_text_option_choices
from ..shared.camera_projection import build_projection_frame
from ..shared.object_scene import (
    POINT_LABELS,
    bbox_intersection_area,
    object_reference_points,
    resolve_object_scene_render_params,
)
from .wall_mounted_common import (
    FLOOR_PROP_SHAPES,
    ROOM_FRONT_Y,
    ROOM_HEIGHT,
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    WALL_BACK_Y,
    WALL_X,
    _finalize_specs,
    _make_floor_prop,
    _room_object_bbox,
    _sample_room_camera,
    _wall_object_visible_bbox,
    _wall_object_visible_size_ok,
    _wall_dimensions_for_type,
    _wall_reference_points,
    _wall_spec,
    _with_picture_scenery,
)
from .wall_mounted_rendering import render_room_scene_3d


TASK_ID = "task_three_d__room__wall_object_camera_distance_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("closest_to_camera",)
CANDIDATE_WALL_OBJECT_TYPES: Tuple[str, ...] = ROOM_CAMERA_DISTANCE_CANDIDATE_WALL_OBJECT_TYPES
CONTEXT_WALL_OBJECT_TYPES: Tuple[str, ...] = ROOM_CAMERA_DISTANCE_CONTEXT_WALL_OBJECT_TYPES
ROOM_CAMERA_DISTANCE_YAW_BANDS: Dict[str, Tuple[float, float]] = {
    "living_room": (-8.0, -3.0),
    "office_room": (3.0, 8.0),
    "studio_room": (-4.0, 4.0),
}
CANDIDATE_WALL_SLOTS: Tuple[Tuple[str, float, float], ...] = (
    ("left", -0.82, 1.22),
    ("left", 1.16, 2.04),
    ("back", -2.08, 1.28),
    ("back", 1.18, 2.12),
    ("right", -0.82, 1.26),
    ("right", 1.16, 2.06),
)
CONTEXT_WALL_SLOTS: Tuple[Tuple[str, float, float], ...] = (
    ("left", -0.46, 1.82),
    ("left", 1.48, 2.22),
    ("back", -0.42, 1.55),
    ("back", 2.36, 1.34),
    ("right", -0.46, 1.82),
    ("right", 2.04, 1.42),
)
LETTERED_WALL_OBJECT_SIZE_SCALE = 1.35
LETTERED_WALL_OBJECT_MIN_VISIBLE_PX = 34.0








def _candidate_slots(candidate_count: int) -> List[Tuple[str, float, float]]:
    if int(candidate_count) > len(CANDIDATE_WALL_SLOTS):
        raise ValueError("room wall camera-distance task supports at most six candidates")
    return list(CANDIDATE_WALL_SLOTS[: int(candidate_count)])


def _sample_candidate_types(rng, candidate_count: int) -> List[str]:
    types = [str(item) for item in CANDIDATE_WALL_OBJECT_TYPES]
    rng.shuffle(types)
    return list(types[: int(candidate_count)])


def _wall_spec_for_type(
    *,
    rng,
    object_id: str,
    object_type: str,
    wall: str,
    hpos: float,
    z: float,
    counts_for_query: bool,
    size_scale: float = 1.0,
) -> Dict[str, Any]:
    width, height = _wall_dimensions_for_type(str(object_type), rng)
    width = float(width) * float(size_scale)
    height = float(height) * float(size_scale)
    return _with_picture_scenery(
        _wall_spec(
            object_id=str(object_id),
            object_type=str(object_type),
            wall=str(wall),
            hpos=float(hpos + rng.uniform(-0.045, 0.045)),
            z=float(z + rng.uniform(-0.035, 0.035)),
            width=float(width),
            height=float(height),
            counts_for_query=bool(counts_for_query),
        ),
        rng,
    )


def _candidate_screen_separation_ok(candidate_specs: Sequence[Mapping[str, Any]], *, camera, frame) -> bool:
    bboxes = [_room_object_bbox(spec, camera, frame) for spec in candidate_specs]
    centers = [(float(spec["screen_xy"][0]), float(spec["screen_xy"][1])) for spec in candidate_specs]
    for index, bbox in enumerate(bboxes):
        for other_index in range(index + 1, len(bboxes)):
            if math.hypot(centers[index][0] - centers[other_index][0], centers[index][1] - centers[other_index][1]) < 48.0:
                return False
            if bbox_intersection_area(bbox, bboxes[other_index]) > 2100.0:
                return False
    return True


def _candidate_wall_visibility_ok(candidate_specs: Sequence[Mapping[str, Any]], *, camera, frame) -> bool:
    if not _wall_object_visible_size_ok(
        candidate_specs,
        camera=camera,
        frame=frame,
        min_width_px=LETTERED_WALL_OBJECT_MIN_VISIBLE_PX,
        min_height_px=LETTERED_WALL_OBJECT_MIN_VISIBLE_PX,
    ):
        return False
    for spec in candidate_specs:
        bbox = _wall_object_visible_bbox(spec, camera, frame)
        width = float(bbox[2]) - float(bbox[0])
        height = float(bbox[3]) - float(bbox[1])
        if str(spec.get("wall")) in {"left", "right"}:
            aspect = min(width, height) / max(width, height)
            if width < LETTERED_WALL_OBJECT_MIN_VISIBLE_PX or aspect < 0.36:
                return False
    return True


def _build_floor_context(
    *,
    rng,
    scene_variant: str,
    floor_context_count: int,
) -> List[Dict[str, Any]]:
    floor_slots = [
        (-2.38, -1.95),
        (-1.15, -2.12),
        (0.18, -2.18),
        (1.48, -1.94),
        (2.48, -1.18),
        (-2.52, -0.35),
        (-1.08, -0.68),
        (0.62, -0.56),
        (1.98, -0.34),
        (-2.18, 1.08),
        (-0.62, 0.84),
        (1.02, 0.86),
        (2.34, 0.98),
    ]
    rng.shuffle(floor_slots)
    prop_shapes = list(FLOOR_PROP_SHAPES)
    rng.shuffle(prop_shapes)
    floor_specs: List[Dict[str, Any]] = []
    for index in range(int(floor_context_count)):
        xy = floor_slots.pop()
        prop_shape = str(prop_shapes[index % len(prop_shapes)])
        floor_specs.append(
            _make_floor_prop(
                rng=rng,
                object_id=f"floor_context_{index}_{prop_shape}",
                prop_shape=str(prop_shape),
                xy=(float(xy[0] + rng.uniform(-0.08, 0.08)), float(xy[1] + rng.uniform(-0.08, 0.08))),
            )
        )
    return list(floor_specs)


def _build_room_wall_camera_distance_dataset(
    *,
    query_id: str,
    scene_variant: str,
    candidate_count: int,
    context_wall_count: int,
    floor_context_count: int,
    render_params,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    for _attempt in range(360):
        camera = _sample_room_camera(
            rng,
            scene_variant=str(scene_variant),
            yaw_band_degrees=tuple(float(value) for value in ROOM_CAMERA_DISTANCE_YAW_BANDS[str(scene_variant)]),
        )
        candidate_types = _sample_candidate_types(rng, int(candidate_count))
        slots = _candidate_slots(int(candidate_count))
        rng.shuffle(slots)
        candidate_wall_specs: List[Dict[str, Any]] = []
        for index, (wall, hpos, z) in enumerate(slots):
            object_type = str(candidate_types[index])
            spec = _wall_spec_for_type(
                rng=rng,
                object_id=f"candidate_wall_object_{index}_{object_type}",
                object_type=str(object_type),
                wall=str(wall),
                hpos=float(hpos),
                z=float(z),
                counts_for_query=True,
                size_scale=LETTERED_WALL_OBJECT_SIZE_SCALE,
            )
            spec["is_answer_candidate"] = True
            candidate_wall_specs.append(spec)

        context_types = [str(item) for item in CONTEXT_WALL_OBJECT_TYPES]
        rng.shuffle(context_types)
        context_slots = list(CONTEXT_WALL_SLOTS)
        rng.shuffle(context_slots)
        context_wall_specs: List[Dict[str, Any]] = []
        for index in range(int(context_wall_count)):
            wall, hpos, z = context_slots[index % len(context_slots)]
            object_type = str(context_types[index % len(context_types)])
            context_wall_specs.append(
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

        floor_specs = _build_floor_context(rng=rng, scene_variant=str(scene_variant), floor_context_count=int(floor_context_count))
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
        for spec in [*candidate_wall_specs, *context_wall_specs]:
            all_reference_points.extend(_wall_reference_points(spec))
        for spec in floor_specs:
            all_reference_points.extend(object_reference_points(spec))

        frame = build_projection_frame(camera=camera, render_params=render_params, point_worlds=all_reference_points)
        finalized_candidates = _finalize_specs(candidate_wall_specs, camera=camera, frame=frame)
        finalized_context_wall = _finalize_specs(context_wall_specs, camera=camera, frame=frame)
        finalized_floor = _finalize_specs(floor_specs, camera=camera, frame=frame)
        if not _candidate_wall_visibility_ok(finalized_candidates, camera=camera, frame=frame):
            continue
        if not _candidate_screen_separation_ok(finalized_candidates, camera=camera, frame=frame):
            continue

        sorted_by_distance = sorted(finalized_candidates, key=lambda spec: (float(spec["camera_distance"]), str(spec["object_id"])))
        distances = [float(spec["camera_distance"]) for spec in sorted_by_distance]
        if len(distances) >= 2 and abs(float(distances[1]) - float(distances[0])) < 0.22:
            continue
        answer_object_id = str(sorted_by_distance[0]["object_id"])
        answer_label_index = abs(
            int(resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.answer_label"))
        ) % int(candidate_count)
        answer_label = str(POINT_LABELS[int(answer_label_index)])
        remaining_labels = [str(label) for label in POINT_LABELS[: int(candidate_count)] if str(label) != str(answer_label)]
        rng.shuffle(remaining_labels)
        relabeled_candidates: List[Dict[str, Any]] = []
        for spec in finalized_candidates:
            updated = dict(spec)
            label = str(answer_label) if str(updated["object_id"]) == answer_object_id else str(remaining_labels.pop())
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

        relabeled_by_original_distance = sorted(relabeled_candidates, key=lambda spec: (float(spec["camera_distance"]), str(spec["point_label"])))
        answer_spec = next(spec for spec in relabeled_candidates if str(spec["point_label"]) == str(answer_label))
        finalized_wall = [*relabeled_candidates, *finalized_context_wall]
        all_finalized = [*finalized_wall, *finalized_floor]
        wall_object_type_counts = Counter(str(spec["object_type"]) for spec in finalized_wall)
        floor_object_type_counts = Counter(str(spec["object_type"]) for spec in finalized_floor)
        object_type_counts = Counter(str(spec["object_type"]) for spec in all_finalized)
        candidate_camera_distances = {str(spec["point_label"]): round(float(spec["camera_distance"]), 4) for spec in relabeled_candidates}
        candidate_walls = {str(spec["point_label"]): str(spec["wall"]) for spec in relabeled_candidates}
        candidate_projected_bboxes = {
            str(spec["point_label"]): [round(float(value), 3) for value in _room_object_bbox(spec, camera, frame)]
            for spec in relabeled_candidates
        }
        candidate_visible_bboxes = {
            str(spec["point_label"]): [
                round(float(value), 3)
                for value in _wall_object_visible_bbox(spec, camera, frame)
            ]
            for spec in relabeled_candidates
        }
        camera_distance_margin = float(relabeled_by_original_distance[1]["camera_distance"]) - float(answer_spec["camera_distance"])
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "candidate_count": int(candidate_count),
            "context_wall_count": int(context_wall_count),
            "floor_context_count": int(floor_context_count),
            "wall_object_specs": list(sorted(finalized_wall, key=lambda spec: str(spec["object_id"]))),
            "floor_object_specs": list(sorted(finalized_floor, key=lambda spec: str(spec["object_id"]))),
            "object_specs": list(sorted(all_finalized, key=lambda spec: str(spec["object_id"]))),
            "candidate_object_specs": list(sorted(relabeled_candidates, key=lambda spec: str(spec["point_label"]))),
            "target_object_ids": [str(answer_spec["object_id"])],
            "answer_label": str(answer_label),
            "answer_object_id": str(answer_spec["object_id"]),
            "answer_object_type": str(answer_spec["object_type"]),
            "answer_wall": str(answer_spec["wall"]),
            "wall_object_count": int(len(finalized_wall)),
            "floor_object_count": int(len(finalized_floor)),
            "object_count": int(len(all_finalized)),
            "candidate_camera_distances_by_label": dict(sorted(candidate_camera_distances.items())),
            "candidate_walls_by_label": dict(sorted(candidate_walls.items())),
            "candidate_projected_bboxes_by_label": dict(sorted(candidate_projected_bboxes.items())),
            "candidate_visible_bboxes_by_label": dict(sorted(candidate_visible_bboxes.items())),
            "camera_distance_order_near_to_far": [str(spec["point_label"]) for spec in relabeled_by_original_distance],
            "camera_distance_margin": round(float(camera_distance_margin), 4),
            "object_type_counts": dict(sorted(object_type_counts.items())),
            "wall_object_type_counts": dict(sorted(wall_object_type_counts.items())),
            "floor_object_type_counts": dict(sorted(floor_object_type_counts.items())),
            "camera": {
                "camera_position": [round(float(value), 4) for value in camera.camera_position],
                "target": [round(float(value), 4) for value in camera.target],
                "yaw_degrees": round(float(camera.yaw_degrees), 4),
                "yaw_band_degrees": [round(float(value), 4) for value in ROOM_CAMERA_DISTANCE_YAW_BANDS[str(scene_variant)]],
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
                "predicate": "minimum finalized camera_distance among option-panel wall-mounted candidates",
                "candidate_camera_distances_by_label": dict(sorted(candidate_camera_distances.items())),
                "candidate_walls_by_label": dict(sorted(candidate_walls.items())),
                "camera_distance_order_near_to_far": [str(spec["point_label"]) for spec in relabeled_by_original_distance],
                "answer_label": str(answer_label),
                "answer_object_id": str(answer_spec["object_id"]),
                "answer_wall": str(answer_spec["wall"]),
                "camera_distance_margin": round(float(camera_distance_margin), 4),
                "unique_answer": True,
            },
        }
    raise ValueError("could not construct a room wall camera-distance scene with a unique visible closest candidate")




_TASK_GROUP_DEFAULTS = get_scene_defaults("three_d", "room")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


@register_task
class ThreeDRoomWallObjectCameraDistanceLabelTask:
    """Choose the option-panel wall-mounted object closest to the camera."""

    task_id = TASK_ID
    domain = "three_d"
    scene_id = "room"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
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
        candidate_count, candidate_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="candidate_count",
            default_min=6,
            default_max=6,
            lower=4,
            upper=6,
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
        render_params = resolve_object_scene_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.canvas",
        )
        dataset = _build_room_wall_camera_distance_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            candidate_count=int(candidate_count),
            context_wall_count=int(context_wall_count),
            floor_context_count=int(floor_context_count),
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
        rendered_scene = render_room_scene_3d(
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
                    "candidate_camera_distances_by_label": dict(dataset["candidate_camera_distances_by_label"]),
                    "candidate_walls_by_label": dict(dataset["candidate_walls_by_label"]),
                    "candidate_projected_bboxes_by_label": dict(dataset["candidate_projected_bboxes_by_label"]),
                    "candidate_visible_bboxes_by_label": dict(dataset["candidate_visible_bboxes_by_label"]),
                    "camera_distance_order_near_to_far": [str(value) for value in dataset["camera_distance_order_near_to_far"]],
                    "answer_label": str(answer_label),
                    "answer_object_id": str(dataset["answer_object_id"]),
                    "view_family": "synthetic_perspective_3d_room",
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
                    "candidate_count": int(candidate_count),
                    "candidate_count_probabilities": dict(candidate_count_probabilities),
                    "context_wall_count": int(context_wall_count),
                    "context_wall_count_probabilities": dict(context_wall_count_probabilities),
                    "floor_context_count": int(floor_context_count),
                    "floor_context_count_probabilities": dict(floor_context_count_probabilities),
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
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "room_bbox_px": list(rendered_scene.room_bbox_px),
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "option_panel_bbox_px": list(rendered_scene.option_panel_bbox_px),
                "option_panel_height_px": int(rendered_scene.option_panel_height_px),
                "option_choice_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_choice_bboxes_px.items()
                },
                "option_choices": [dict(choice) for choice in rendered_scene.option_choices],
                "wall_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.wall_object_bboxes_px.items()},
                "wall_object_centers_px": {str(key): list(value) for key, value in rendered_scene.wall_object_centers_px.items()},
                "floor_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.floor_object_bboxes_px.items()},
                "floor_object_centers_px": {str(key): list(value) for key, value in rendered_scene.floor_object_centers_px.items()},
                "target_object_bboxes_px": {str(key): list(rendered_scene.object_bboxes_px[str(key)]) for key in dataset["target_object_ids"]},
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "candidate_count": int(dataset["candidate_count"]),
                "context_wall_count": int(dataset["context_wall_count"]),
                "floor_context_count": int(dataset["floor_context_count"]),
                "answer_label": str(answer_label),
                "answer_object_id": str(dataset["answer_object_id"]),
                "answer_object_type": str(dataset["answer_object_type"]),
                "answer_wall": str(dataset["answer_wall"]),
                "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                "candidate_object_specs": [dict(spec) for spec in dataset["candidate_object_specs"]],
                "option_choices": [dict(choice) for choice in rendered_scene.option_choices],
                "option_descriptor_by_label": {
                    str(choice["label"]): str(choice["descriptor"])
                    for choice in rendered_scene.option_choices
                },
                "wall_object_specs": [dict(spec) for spec in dataset["wall_object_specs"]],
                "floor_object_specs": [dict(spec) for spec in dataset["floor_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "object_count": int(dataset["object_count"]),
                "wall_object_count": int(dataset["wall_object_count"]),
                "floor_object_count": int(dataset["floor_object_count"]),
                "candidate_camera_distances_by_label": dict(dataset["candidate_camera_distances_by_label"]),
                "candidate_walls_by_label": dict(dataset["candidate_walls_by_label"]),
                "candidate_projected_bboxes_by_label": dict(dataset["candidate_projected_bboxes_by_label"]),
                "candidate_visible_bboxes_by_label": dict(dataset["candidate_visible_bboxes_by_label"]),
                "camera_distance_order_near_to_far": [str(value) for value in dataset["camera_distance_order_near_to_far"]],
                "camera_distance_margin": float(dataset["camera_distance_margin"]),
                "object_type_counts": dict(dataset["object_type_counts"]),
                "wall_object_type_counts": dict(dataset["wall_object_type_counts"]),
                "floor_object_type_counts": dict(dataset["floor_object_type_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "view_family": "synthetic_perspective_3d_room",
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["ThreeDRoomWallObjectCameraDistanceLabelTask"]
