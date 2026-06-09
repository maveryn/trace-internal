"""Marked-point vertical relation task for a synthetic 3D object scene."""

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
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.object_scene import (
    NAMEABLE_SMALL_OBJECT_SHAPE_TYPES,
    POINT_LABELS,
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    _RenderParams,
    _bbox_intersection_area,
    _build_projection_frame,
    _camera_yaw_band_for_instance,
    _object_reference_points,
    _object_screen_bbox,
    _project_screen,
    _resolve_render_params,
    _sample_camera,
    _sample_scene_object_specs,
    render_object_scene_3d,
)
from .marked_point_common import assign_answer_label as _assign_answer_label
from .marked_point_common import bbox_union as _bbox_union
from .marked_point_rendering import draw_marked_points as _draw_marked_points


TASK_ID = "task_three_d__object_scene__marked_point_vertical_relation_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("directly_above_reference",)
REFERENCE_SHAPE_TYPES: Tuple[str, ...] = (
    "sphere",
    "cube",
    "cylinder",
    "cone",
    "pyramid",
    "wedge",
    "torus",
    "half_cylinder",
    "cup",
    "bottle",
    "drum",
    "dice",
    "cactus",
    "helmet",
    "hat",
    "bell",
    "trophy",
    "lantern",
    "candle",
    "goblet",
    "flask",
    "clock",
    "apple",
)
MIN_DISTRACTOR_REFERENCE_XY_OFFSET = 0.48
MIN_MARKER_SCREEN_SEPARATION_PX = 78.0
MIN_ANSWER_SCREEN_ABOVE_REFERENCE_PX = 26.0
MIN_READABLE_OBJECT_AREA_PX = 520.0
MAX_PAIRWISE_OBJECT_OVERLAP_PX = 4200.0


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _bbox_is_readable(bbox: Sequence[float], *, width: int, height: int, min_side_px: float = 17.0) -> bool:
    box_width = float(bbox[2]) - float(bbox[0])
    box_height = float(bbox[3]) - float(bbox[1])
    if box_width < float(min_side_px) or box_height < float(min_side_px):
        return False
    return float(bbox[2]) > 4.0 and float(bbox[3]) > 4.0 and float(bbox[0]) < float(width - 4) and float(bbox[1]) < float(height - 4)


def _demote_small_context_spec(spec: Mapping[str, Any], *, index: int) -> Dict[str, Any]:
    updated = dict(spec)
    shape_type = str(updated["shape_type"])
    updated["object_id"] = f"vertical_context_{int(index):02d}_{shape_type}"
    updated["object_role"] = "small_context"
    updated["is_answer_candidate"] = False
    for key in ("point_id", "point_label", "object_label"):
        updated.pop(key, None)
    return updated


def _finalize_object_specs(
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
    return finalized_specs


def _sample_small_object_specs(*, rng, object_count: int) -> List[Dict[str, Any]]:
    small_specs, large_specs = _sample_scene_object_specs(
        rng=rng,
        candidate_count=int(object_count),
        context_object_count=0,
    )
    if large_specs:
        raise ValueError("vertical marked-point scene should not include large context props")
    return [_demote_small_context_spec(spec, index=index) for index, spec in enumerate(small_specs)]


def _choose_reference_spec(*, rng, specs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    candidates = [dict(spec) for spec in specs if str(spec["shape_type"]) in set(REFERENCE_SHAPE_TYPES)]
    if not candidates:
        raise ValueError("no suitable vertical-reference object sampled")
    rng.shuffle(candidates)
    return dict(candidates[0])


def _make_marker_record(
    *,
    marker_id: str,
    world_xyz: Sequence[float],
    surface_kind: str,
    attached_object_id: str | None,
) -> Dict[str, Any]:
    return {
        "marker_id": str(marker_id),
        "surface_kind": str(surface_kind),
        "attached_object_id": None if attached_object_id is None else str(attached_object_id),
        "world_xyz": [round(float(value), 4) for value in world_xyz],
    }


def _sample_vertical_marker_records(
    *,
    rng,
    reference_spec: Mapping[str, Any],
    objects: Sequence[Mapping[str, Any]],
    point_count: int,
    room_extent: float,
    room_height: float,
) -> Tuple[List[Dict[str, Any]], str, float]:
    if int(point_count) != 6:
        raise ValueError("vertical marked-point task expects exactly six point options")

    ref_x, ref_y, ref_base_z = (float(value) for value in reference_spec["base_xyz"])
    ref_height = float(reference_spec["dimensions_xyz"][2])
    ref_top_z = float(ref_base_z + ref_height)
    answer_gap = float(rng.uniform(0.58, 0.84))
    answer_marker_id = "raw_vertical_answer"
    records = [
        _make_marker_record(
            marker_id=answer_marker_id,
            world_xyz=(ref_x, ref_y, min(float(room_height) - 0.20, ref_top_z + answer_gap)),
            surface_kind="directly_above_reference",
            attached_object_id=str(reference_spec["object_id"]),
        )
    ]
    extent = min(2.84, max(2.10, float(room_extent) - 0.34))
    max_z = max(1.25, float(room_height) - 0.22)
    min_xy_offset = float("inf")
    attempts = 0
    other_objects = [dict(spec) for spec in objects if str(spec["object_id"]) != str(reference_spec["object_id"])]

    while len(records) < int(point_count) and attempts < 520:
        attempts += 1
        use_other_object = bool(other_objects) and rng.random() < 0.36
        if use_other_object:
            obj = dict(other_objects[int(rng.randrange(len(other_objects)))])
            base_x, base_y, base_z = (float(value) for value in obj["base_xyz"])
            obj_top = float(base_z + float(obj["dimensions_xyz"][2]))
            x = base_x + rng.uniform(-0.13, 0.13)
            y = base_y + rng.uniform(-0.13, 0.13)
            z = min(max_z, obj_top + rng.uniform(0.34, 0.80))
        else:
            angle = float(rng.uniform(0.0, math.tau))
            radius = float(rng.uniform(0.62, 1.46))
            x = max(-extent, min(extent, ref_x + math.cos(angle) * radius))
            y = max(-extent, min(extent, ref_y + math.sin(angle) * radius))
            z = min(max_z, ref_top_z + rng.uniform(0.18, 1.16))
        xy_offset = math.hypot(float(x - ref_x), float(y - ref_y))
        if xy_offset < MIN_DISTRACTOR_REFERENCE_XY_OFFSET:
            continue
        if any(math.hypot(float(x - float(record["world_xyz"][0])), float(y - float(record["world_xyz"][1]))) < 0.34 for record in records):
            continue
        min_xy_offset = min(float(min_xy_offset), float(xy_offset))
        records.append(
            _make_marker_record(
                marker_id=f"raw_vertical_distractor_{len(records)}",
                world_xyz=(x, y, max(0.12, z)),
                surface_kind="offset_floating_point",
                attached_object_id=None,
            )
        )

    if len(records) != int(point_count):
        raise ValueError("could not place six vertical-relation marked points")
    return records, str(answer_marker_id), float(min_xy_offset)


def _finalize_marker_records(
    records: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
    render_params: _RenderParams,
) -> List[Dict[str, Any]]:
    finalized_markers: List[Dict[str, Any]] = []
    for record in records:
        screen = _project_screen(record["world_xyz"], camera, frame)
        x, y = float(screen[0]), float(screen[1])
        if not (
            58.0 <= x <= float(render_params.canvas_width) - 58.0
            and 58.0 <= y <= float(render_params.canvas_height) - 58.0
        ):
            raise ValueError("marked point projects outside the readable image area")
        finalized = dict(record)
        finalized.update(
            {
                "screen_xy": [round(float(x), 3), round(float(y), 3)],
                "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
                "camera_distance": round(float(screen[7]), 4),
            }
        )
        finalized_markers.append(finalized)
    return finalized_markers


def _validate_projection(
    *,
    finalized_objects: Sequence[Mapping[str, Any]],
    finalized_markers: Sequence[Mapping[str, Any]],
    reference_spec: Mapping[str, Any],
    answer_marker_id: str,
    camera,
    frame,
    render_params: _RenderParams,
) -> Tuple[Dict[str, List[float]], float]:
    object_bboxes_by_id = {
        str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=10.0)
        for spec in finalized_objects
    }
    if any(
        not _bbox_is_readable(
            bbox,
            width=int(render_params.canvas_width),
            height=int(render_params.canvas_height),
        )
        for bbox in object_bboxes_by_id.values()
    ):
        raise ValueError("small object bbox is not readable")
    if any(_bbox_area(bbox) < MIN_READABLE_OBJECT_AREA_PX for bbox in object_bboxes_by_id.values()):
        raise ValueError("small object projected area is too small")
    object_bboxes = list(object_bboxes_by_id.values())
    if any(
        _bbox_intersection_area(a, b) > MAX_PAIRWISE_OBJECT_OVERLAP_PX
        for index, a in enumerate(object_bboxes)
        for b in object_bboxes[index + 1 :]
    ):
        raise ValueError("small object overlap is too high")

    marker_centers = [(float(item["screen_xy"][0]), float(item["screen_xy"][1])) for item in finalized_markers]
    if any(
        math.hypot(a[0] - b[0], a[1] - b[1]) < MIN_MARKER_SCREEN_SEPARATION_PX
        for index, a in enumerate(marker_centers)
        for b in marker_centers[index + 1 :]
    ):
        raise ValueError("marked point centers are too close")

    reference_id = str(reference_spec["object_id"])
    reference_bbox = object_bboxes_by_id[reference_id]
    answer_marker = next(marker for marker in finalized_markers if str(marker["marker_id"]) == str(answer_marker_id))
    answer_x, answer_y = (float(answer_marker["screen_xy"][0]), float(answer_marker["screen_xy"][1]))
    reference_center_x = 0.5 * (float(reference_bbox[0]) + float(reference_bbox[2]))
    if answer_y > float(reference_bbox[1]) - MIN_ANSWER_SCREEN_ABOVE_REFERENCE_PX:
        raise ValueError("answer marker is not visibly above the named reference")
    if abs(float(answer_x - reference_center_x)) > max(80.0, 0.68 * (float(reference_bbox[2]) - float(reference_bbox[0]))):
        raise ValueError("answer marker is not visually aligned with the named reference")

    marker_radius = 24.0
    for marker in finalized_markers:
        marker_bbox = [
            float(marker["screen_xy"][0]) - marker_radius,
            float(marker["screen_xy"][1]) - marker_radius,
            float(marker["screen_xy"][0]) + marker_radius,
            float(marker["screen_xy"][1]) + marker_radius,
        ]
        for object_id, object_bbox in object_bboxes_by_id.items():
            if str(marker["marker_id"]) == str(answer_marker_id) and str(object_id) == reference_id:
                continue
            if _bbox_intersection_area(marker_bbox, object_bbox) > 1250.0:
                raise ValueError("marked point overlaps an unrelated object too much")
    return object_bboxes_by_id, float(reference_center_x)


def _build_vertical_relation_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    point_count: int,
    object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
    camera_yaw_band: Tuple[float, float] | None = None,
) -> Dict[str, Any]:
    if str(query_id) != "directly_above_reference":
        raise ValueError(f"unsupported query_id: {query_id}")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    selected_camera_yaw_band = (
        tuple(float(value) for value in camera_yaw_band)
        if camera_yaw_band is not None
        else _camera_yaw_band_for_instance(int(instance_seed))
    )

    for _attempt in range(620):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        object_specs = _sample_small_object_specs(rng=rng, object_count=int(object_count))
        prompt_name_counts = Counter(str(spec["prompt_name"]) for spec in object_specs)
        if any(int(count) != 1 for count in prompt_name_counts.values()):
            continue
        try:
            reference_spec = _choose_reference_spec(rng=rng, specs=object_specs)
            marker_records, answer_marker_id, min_distractor_xy_offset = _sample_vertical_marker_records(
                rng=rng,
                reference_spec=reference_spec,
                objects=object_specs,
                point_count=int(point_count),
                room_extent=float(render_params.room_extent),
                room_height=float(render_params.room_height),
            )
        except ValueError:
            continue

        reference_points = [
            *(point for spec in object_specs for point in _object_reference_points(spec)),
            *(tuple(float(value) for value in record["world_xyz"]) for record in marker_records),
        ]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        finalized_objects = _finalize_object_specs(object_specs, camera=camera, frame=frame)
        reference_spec = next(spec for spec in finalized_objects if str(spec["object_id"]) == str(reference_spec["object_id"]))
        try:
            finalized_markers = _finalize_marker_records(
                marker_records,
                camera=camera,
                frame=frame,
                render_params=render_params,
            )
            object_bboxes_by_id, reference_center_x = _validate_projection(
                finalized_objects=finalized_objects,
                finalized_markers=finalized_markers,
                reference_spec=reference_spec,
                answer_marker_id=str(answer_marker_id),
                camera=camera,
                frame=frame,
                render_params=render_params,
            )
        except ValueError:
            continue

        relabeled_markers = _assign_answer_label(
            records=finalized_markers,
            answer_marker_id=str(answer_marker_id),
            point_count=int(point_count),
            answer_label_index=int(instance_seed),
            rng=rng,
        )
        answer_marker = next(marker for marker in relabeled_markers if str(marker["marker_id"]) == str(answer_marker_id))
        reference_id = str(reference_spec["object_id"])
        ref_x, ref_y, _ref_z = (float(value) for value in reference_spec["base_xyz"])
        xy_offsets_by_label = {
            str(marker["point_label"]): round(
                math.hypot(float(marker["world_xyz"][0]) - ref_x, float(marker["world_xyz"][1]) - ref_y),
                4,
            )
            for marker in relabeled_markers
        }
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "point_count": int(point_count),
            "object_count": int(object_count),
            "context_object_count": int(object_count),
            "point_specs": [],
            "context_object_specs": sorted(finalized_objects, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted(finalized_objects, key=lambda spec: str(spec["object_id"])),
            "marked_points": list(relabeled_markers),
            "answer_label": str(answer_marker["point_label"]),
            "answer_point_id": str(answer_marker["point_id"]),
            "answer_marker_id": str(answer_marker["marker_id"]),
            "answer_point_px": [round(float(value), 3) for value in answer_marker["screen_xy"]],
            "reference_object_id": str(reference_id),
            "reference_object_name": str(reference_spec["prompt_name"]),
            "reference_shape_type": str(reference_spec["shape_type"]),
            "reference_prompt_name_count": int(prompt_name_counts[str(reference_spec["prompt_name"])]),
            "reference_bbox_px": [round(float(value), 3) for value in object_bboxes_by_id[str(reference_id)]],
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
                "relation": "directly_above_reference",
                "relation_frame": "world_vertical_z",
                "reference_object_id": str(reference_id),
                "reference_object_name": str(reference_spec["prompt_name"]),
                "reference_shape_type": str(reference_spec["shape_type"]),
                "reference_world_xy": [round(float(ref_x), 4), round(float(ref_y), 4)],
                "reference_screen_center_x": round(float(reference_center_x), 3),
                "answer_marker_id": str(answer_marker["marker_id"]),
                "answer_label": str(answer_marker["point_label"]),
                "xy_offsets_from_reference_by_label": dict(sorted(xy_offsets_by_label.items())),
                "minimum_distractor_reference_xy_offset": round(float(min_distractor_xy_offset), 4),
                "unique_directly_above_answer": True,
            },
        }
    raise ValueError("could not construct a valid 3D marked-point vertical relation scene")


def _build_complexity(
    *,
    scene_variant: str,
    point_count: int,
    object_count: int,
    vertical_margin: float,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.36)),
        "vertical_relation": float(raw_weights.get("vertical_relation", 0.38)),
        "reference_binding": float(raw_weights.get("reference_binding", 0.16)),
        "scene_variant_load": float(raw_weights.get("scene_variant_load", 0.10)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(int(point_count) + int(object_count), 10, 16),
        "vertical_relation": 1.0 - _normalize_unit(float(vertical_margin), 0.48, 1.35),
        "reference_binding": 0.58,
        "scene_variant_load": {
            "floor_grid_room": 0.28,
            "tabletop_room": 0.33,
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
class ThreeDSpatialMarkedPointVerticalRelationLabelTask:
    """Choose the marked point directly above a uniquely named small reference object."""

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
            key="point_count",
            default_min=6,
            default_max=6,
            lower=6,
            upper=6,
        )
        object_count, object_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="object_count",
            default_min=8,
            default_max=8,
            lower=6,
            upper=11,
        )
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_vertical_relation_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            object_count=int(object_count),
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
        rendered_scene = render_object_scene_3d(
            background,
            dataset=dataset,
            render_params=render_params,
            draw_candidate_labels=False,
            compute_single_annotation=False,
        )
        marked_image, marker_render_map, marker_entities = _draw_marked_points(
            rendered_scene.image,
            marked_points=dataset["marked_points"],
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            marked_image,
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

        answer_label = str(dataset["answer_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        annotation_point_map = {"selected_point": list(dataset["answer_point_px"])}
        annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_point_map))
        solver_trace = dict(dataset["solver_trace"])
        complexity = _build_complexity(
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            object_count=int(object_count),
            vertical_margin=float(solver_trace.get("minimum_distractor_reference_xy_offset", 0.48)),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )
        scene_bbox = _bbox_union(
            rendered_scene.scene_bbox_px,
            *[bbox for bbox in marker_render_map["marked_point_bboxes_px"].values()],
        )
        scene_entities = [*rendered_scene.entities, *marker_entities]
        answer_support = [str(label) for label in POINT_LABELS[: int(point_count)]]

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene_marked_point_vertical_relation",
                "entities": [dict(entity) for entity in scene_entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "point_count": int(point_count),
                    "object_count": int(object_count),
                    "reference_object_id": str(dataset["reference_object_id"]),
                    "reference_object_name": str(dataset["reference_object_name"]),
                    "reference_shape_type": str(dataset["reference_shape_type"]),
                    "answer_point_id": str(dataset["answer_point_id"]),
                    "answer_label": str(answer_label),
                    "relation_frame": "world_vertical_z",
                    "view_family": "synthetic_perspective_3d_marked_points",
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
                    "point_count_probabilities": dict(point_count_probabilities),
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "answer_support": list(answer_support),
                    "reference_shape_type": str(dataset["reference_shape_type"]),
                    "reference_shape_support": list(REFERENCE_SHAPE_TYPES),
                    "scene_object_shape_support": list(NAMEABLE_SMALL_OBJECT_SHAPE_TYPES),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(image.height),
                "scene_canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "label_font_size_px": int(render_params.label_font_size_px),
                "marker_radius_px": int(max(12.0, float(render_params.marker_radius_px) * 0.66)),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(scene_bbox),
                "room_bbox_px": list(rendered_scene.room_bbox_px),
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "context_object_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.context_object_bboxes_px.items()
                },
                "context_object_centers_px": {
                    str(key): list(value) for key, value in rendered_scene.context_object_centers_px.items()
                },
                **dict(marker_render_map),
                "selected_point_px": list(dataset["answer_point_px"]),
                "reference_object_bbox_px": list(rendered_scene.object_bboxes_px[str(dataset["reference_object_id"])]),
                "reference_object_center_px": list(rendered_scene.object_centers_px[str(dataset["reference_object_id"])]),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "point_count": int(point_count),
                "object_count": int(object_count),
                "point_specs": [],
                "marked_points": [dict(point) for point in dataset["marked_points"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "reference_object_id": str(dataset["reference_object_id"]),
                "reference_object_name": str(dataset["reference_object_name"]),
                "reference_shape_type": str(dataset["reference_shape_type"]),
                "reference_prompt_name_count": int(dataset["reference_prompt_name_count"]),
                "answer_label": str(answer_label),
                "answer_point_id": str(dataset["answer_point_id"]),
                "answer_marker_id": str(dataset["answer_marker_id"]),
                "answer_point_px": list(dataset["answer_point_px"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "view_family": "synthetic_perspective_3d_marked_points",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "marked_point_vertical_relation",
                "ids_by_role": {
                    "selected_point": str(dataset["answer_point_id"]),
                    "reference_object": str(dataset["reference_object_id"]),
                },
                "answer_label": str(answer_label),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_point_map),
                "pixel_keyed_point_map": dict(annotation_point_map),
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


__all__ = [
    "MIN_DISTRACTOR_REFERENCE_XY_OFFSET",
    "REFERENCE_SHAPE_TYPES",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSpatialMarkedPointVerticalRelationLabelTask",
]
