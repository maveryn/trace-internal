"""Marked-point depth extremum task for a synthetic 3D object scene."""

from __future__ import annotations

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
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
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
    POINT_LABELS,
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    _RenderParams,
    _bbox_intersection_area,
    _build_projection_frame,
    _camera_yaw_band_for_instance,
    _min_pairwise,
    _object_reference_points,
    _object_screen_bbox,
    _project_screen,
    _resolve_render_params,
    _sample_camera,
    _sample_scene_object_specs,
    render_object_scene_3d,
)
from .shared.marked_point_common import assign_answer_label as _assign_answer_label
from .shared.marked_point_common import bbox_union as _bbox_union
from .shared.marked_point_rendering import draw_marked_points as _draw_marked_points


TASK_ID = "task_three_d__object_scene__marked_point_depth_extremum_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("closest_marked_point", "farthest_marked_point")


def _demote_small_context_spec(spec: Mapping[str, Any], *, index: int) -> Dict[str, Any]:
    """Turn a sampled small answer-candidate object into an unlettered context object."""

    updated = dict(spec)
    shape_type = str(updated["shape_type"])
    updated["object_id"] = f"context_small_{int(index)}_{shape_type}"
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


def _sample_floor_marker_world(
    *,
    rng,
    objects: Sequence[Mapping[str, Any]],
    existing_points: Sequence[Sequence[float]],
    room_extent: float,
) -> Tuple[float, float, float]:
    extent = min(2.82, max(2.1, float(room_extent) - 0.34))
    for _attempt in range(160):
        x = float(rng.uniform(-extent, extent))
        y = float(rng.uniform(-extent, extent))
        point = (x, y, 0.045)
        if any(math.hypot(x - float(other[0]), y - float(other[1])) < 0.48 for other in existing_points):
            continue
        if any(
            math.hypot(x - float(obj["base_xyz"][0]), y - float(obj["base_xyz"][1]))
            < float(obj.get("footprint_radius", 0.42)) + 0.20
            for obj in objects
        ):
            continue
        return point
    raise ValueError("could not place a visible floor marker")


def _sample_marker_world_points(
    *,
    rng,
    point_count: int,
    objects: Sequence[Mapping[str, Any]],
    room_extent: float,
) -> List[Dict[str, Any]]:
    object_pool = [dict(spec) for spec in objects]
    rng.shuffle(object_pool)
    top_count = min(max(1, int(point_count) // 3), len(object_pool), int(point_count) - 2)
    records: List[Dict[str, Any]] = []
    existing: List[Tuple[float, float, float]] = []

    for index, spec in enumerate(object_pool[:top_count]):
        base = spec["base_xyz"]
        height = float(spec["dimensions_xyz"][2])
        world = (
            round(float(base[0]), 4),
            round(float(base[1]), 4),
            round(float(base[2]) + height + 0.075, 4),
        )
        records.append(
            {
                "marker_id": f"raw_marked_point_{index}",
                "surface_kind": "object_top",
                "attached_object_id": str(spec["object_id"]),
                "world_xyz": [float(value) for value in world],
            }
        )
        existing.append(world)

    while len(records) < int(point_count):
        world = _sample_floor_marker_world(
            rng=rng,
            objects=objects,
            existing_points=existing,
            room_extent=float(room_extent),
        )
        marker_index = len(records)
        records.append(
            {
                "marker_id": f"raw_marked_point_{marker_index}",
                "surface_kind": "floor",
                "attached_object_id": None,
                "world_xyz": [round(float(value), 4) for value in world],
            }
        )
        existing.append(world)

    rng.shuffle(records)
    return records


def _build_marked_point_scene_dataset(
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
    selected_camera_yaw_band = (
        tuple(float(value) for value in camera_yaw_band)
        if camera_yaw_band is not None
        else _camera_yaw_band_for_instance(int(instance_seed))
    )
    large_context_count = max(1, min(3, int(context_object_count) // 3))
    small_context_count = max(2, int(context_object_count) - int(large_context_count))

    for _attempt in range(420):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        small_specs, large_specs = _sample_scene_object_specs(
            rng=rng,
            candidate_count=int(small_context_count),
            context_object_count=int(large_context_count),
        )
        context_specs = [
            *[_demote_small_context_spec(spec, index=index) for index, spec in enumerate(small_specs)],
            *[dict(spec) for spec in large_specs],
        ]
        marker_records = _sample_marker_world_points(
            rng=rng,
            point_count=int(point_count),
            objects=context_specs,
            room_extent=float(render_params.room_extent),
        )
        reference_points = [
            *(point for spec in context_specs for point in _object_reference_points(spec)),
            *(tuple(float(value) for value in record["world_xyz"]) for record in marker_records),
        ]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        finalized_context = _finalize_object_specs(context_specs, camera=camera, frame=frame)
        object_bboxes_by_id = {
            str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=10.0)
            for spec in finalized_context
        }
        object_bboxes = list(object_bboxes_by_id.values())
        finalized_markers: List[Dict[str, Any]] = []
        for record in marker_records:
            screen = _project_screen(record["world_xyz"], camera, frame)
            x, y = float(screen[0]), float(screen[1])
            if not (
                58.0 <= x <= float(render_params.canvas_width) - 58.0
                and 58.0 <= y <= float(render_params.canvas_height) - 58.0
            ):
                break
            finalized = dict(record)
            finalized.update(
                {
                    "screen_xy": [round(float(x), 3), round(float(y), 3)],
                    "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
                    "camera_distance": round(float(screen[7]), 4),
                }
            )
            finalized_markers.append(finalized)
        if len(finalized_markers) != int(point_count):
            continue
        screen_centers = [(float(item["screen_xy"][0]), float(item["screen_xy"][1])) for item in finalized_markers]
        if any(
            math.hypot(a[0] - b[0], a[1] - b[1]) < 82.0
            for index, a in enumerate(screen_centers)
            for b in screen_centers[index + 1 :]
        ):
            continue
        marker_bboxes_by_id = {
            str(marker["marker_id"]): [center[0] - 24.0, center[1] - 24.0, center[0] + 24.0, center[1] + 24.0]
            for marker, center in zip(finalized_markers, screen_centers)
        }
        if any(
            _bbox_intersection_area(a, b) > 4200.0
            for index, a in enumerate(object_bboxes)
            for b in object_bboxes[index + 1 :]
        ):
            continue
        heavy_marker_overlap = False
        for marker in finalized_markers:
            marker_bbox = marker_bboxes_by_id[str(marker["marker_id"])]
            attached_object_id = marker.get("attached_object_id")
            for object_id, object_bbox in object_bboxes_by_id.items():
                if attached_object_id is not None and str(attached_object_id) == str(object_id):
                    continue
                if _bbox_intersection_area(marker_bbox, object_bbox) > 1800.0:
                    heavy_marker_overlap = True
                    break
            if heavy_marker_overlap:
                break
        if heavy_marker_overlap:
            continue
        camera_distances = [float(item["camera_distance"]) for item in finalized_markers]
        if _min_pairwise(camera_distances) < 0.32:
            continue
        sorted_by_depth = sorted(finalized_markers, key=lambda item: (float(item["camera_distance"]), str(item["marker_id"])))
        if str(query_id) == "closest_marked_point":
            answer_marker_id = str(sorted_by_depth[0]["marker_id"])
            depth_margin = float(sorted_by_depth[1]["camera_distance"]) - float(sorted_by_depth[0]["camera_distance"])
        else:
            answer_marker_id = str(sorted_by_depth[-1]["marker_id"])
            depth_margin = float(sorted_by_depth[-1]["camera_distance"]) - float(sorted_by_depth[-2]["camera_distance"])
        if float(depth_margin) < 0.38:
            continue
        relabeled_markers = _assign_answer_label(
            records=finalized_markers,
            answer_marker_id=str(answer_marker_id),
            point_count=int(point_count),
            answer_label_index=int(instance_seed),
            rng=rng,
        )
        answer_marker = next(item for item in relabeled_markers if str(item["marker_id"]) == str(answer_marker_id))
        sorted_relabeled_by_depth = sorted(relabeled_markers, key=lambda item: (float(item["camera_distance"]), str(item["point_label"])))
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "point_count": int(point_count),
            "context_object_count": int(context_object_count),
            "small_context_object_count": int(small_context_count),
            "large_context_object_count": int(large_context_count),
            "point_specs": [],
            "context_object_specs": sorted(finalized_context, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted(finalized_context, key=lambda spec: str(spec["object_id"])),
            "marked_points": list(relabeled_markers),
            "answer_label": str(answer_marker["point_label"]),
            "answer_point_id": str(answer_marker["point_id"]),
            "answer_marker_id": str(answer_marker["marker_id"]),
            "answer_point_px": [round(float(value), 3) for value in answer_marker["screen_xy"]],
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
                "sort_key": "camera_distance",
                "camera_distance_order_near_to_far": [str(item["point_label"]) for item in sorted_relabeled_by_depth],
                "marker_id_order_near_to_far": [str(item["marker_id"]) for item in sorted_relabeled_by_depth],
                "camera_distances_by_label": {
                    str(item["point_label"]): round(float(item["camera_distance"]), 4)
                    for item in sorted(relabeled_markers, key=lambda marker: str(marker["point_label"]))
                },
                "unique_camera_distance_margin": round(float(_min_pairwise([float(item["camera_distance"]) for item in relabeled_markers])), 4),
                "answer_depth_margin": round(float(depth_margin), 4),
            },
        }
    raise ValueError("could not construct a valid 3D marked-point depth scene")




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
class ThreeDSpatialMarkedPointDepthExtremumLabelTask:
    """Choose the marked point closest to or farthest from the camera."""

    task_id = TASK_ID
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
            lower=5,
            upper=6,
        )
        context_object_count, context_object_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="context_object_count",
            default_min=6,
            default_max=6,
            lower=4,
            upper=8,
        )
        render_params = _resolve_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.canvas",
        )
        dataset = _build_marked_point_scene_dataset(
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
        scene_bbox = _bbox_union(
            rendered_scene.scene_bbox_px,
            *[bbox for bbox in marker_render_map["marked_point_bboxes_px"].values()],
        )
        scene_entities = [*rendered_scene.entities, *marker_entities]
        answer_support = [str(label) for label in POINT_LABELS[: int(point_count)]]

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene_marked_point_depth",
                "entities": [dict(entity) for entity in scene_entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "point_count": int(point_count),
                    "context_object_count": int(context_object_count),
                    "small_context_object_count": int(dataset["small_context_object_count"]),
                    "large_context_object_count": int(dataset["large_context_object_count"]),
                    "object_count": int(len(dataset["object_specs"])),
                    "answer_point_id": str(dataset["answer_point_id"]),
                    "answer_label": str(answer_label),
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
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_object_count_probabilities),
                    "answer_support": list(answer_support),
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
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "point_count": int(point_count),
                "context_object_count": int(context_object_count),
                "small_context_object_count": int(dataset["small_context_object_count"]),
                "large_context_object_count": int(dataset["large_context_object_count"]),
                "object_count": int(len(dataset["object_specs"])),
                "point_specs": [],
                "marked_points": [dict(point) for point in dataset["marked_points"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
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
                "type": "marked_point",
                "ids_by_role": {
                    "selected_point": str(dataset["answer_point_id"]),
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSpatialMarkedPointDepthExtremumLabelTask",
]
