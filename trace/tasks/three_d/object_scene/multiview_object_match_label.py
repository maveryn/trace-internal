"""Multi-view object correspondence task for a synthetic 3D object scene."""

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
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ..shared.color_variation import resolve_three_d_object_fill_rgb
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.object_scene import (
    CAMERA_YAW_BANDS_DEGREES,
    CONTEXT_OBJECT_COLORS,
    POINT_COLORS,
    POINT_LABELS,
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    _RenderParams,
    _bbox_intersection_area,
    _build_projection_frame,
    _min_pairwise,
    _object_reference_points,
    _object_screen_bbox,
    _project_screen,
    _resolve_render_params,
    _sample_camera,
    _sample_scene_object_specs,
)
from .shared.multiview_rendering import (
    CANDIDATE_VIEW_KEY,
    REFERENCE_VIEW_KEY,
    offset_bbox as _offset_bbox,
    offset_entities as _offset_entities,
    panel_layout as _panel_layout,
    panel_render_params as _panel_render_params,
    render_multiview_scene as _render_multiview_scene,
    shift_render_maps as _shift_render_maps,
)


TASK_ID = "task_three_d__object_scene__multiview_object_match_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("same_object_in_second_view",)
MULTIVIEW_CANDIDATE_POSITION_SCALE = 0.82
MULTIVIEW_CANDIDATE_DIMENSION_SCALE = 1.18
MULTIVIEW_MIN_CANDIDATE_BBOX_AREA_PX = 980.0


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _bbox_is_readable(bbox: Sequence[float], *, width: int, height: int, min_side_px: float = 22.0) -> bool:
    box_width = float(bbox[2]) - float(bbox[0])
    box_height = float(bbox[3]) - float(bbox[1])
    if box_width < float(min_side_px) or box_height < float(min_side_px):
        return False
    return float(bbox[2]) > 6.0 and float(bbox[3]) > 6.0 and float(bbox[0]) < float(width - 6) and float(bbox[1]) < float(height - 6)


def _camera_yaw_bands_for_instance(instance_seed: int) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    first_index = abs(int(instance_seed)) % len(CAMERA_YAW_BANDS_DEGREES)
    second_index = (int(first_index) + 3) % len(CAMERA_YAW_BANDS_DEGREES)
    return (
        tuple(float(value) for value in CAMERA_YAW_BANDS_DEGREES[first_index]),
        tuple(float(value) for value in CAMERA_YAW_BANDS_DEGREES[second_index]),
    )


def _yaw_separation_degrees(yaw_a: float, yaw_b: float) -> float:
    diff = abs(float(yaw_a) - float(yaw_b)) % 360.0
    return min(float(diff), 360.0 - float(diff))


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


def _scale_candidate_for_multiview(spec: Mapping[str, Any]) -> Dict[str, Any]:
    updated = dict(spec)
    base_xyz = updated.get("base_xyz", updated.get("world_xyz", (0.0, 0.0, 0.0)))
    base_x = float(base_xyz[0]) * MULTIVIEW_CANDIDATE_POSITION_SCALE
    base_y = float(base_xyz[1]) * MULTIVIEW_CANDIDATE_POSITION_SCALE
    base_z = float(base_xyz[2]) if isinstance(base_xyz, Sequence) and len(base_xyz) >= 3 else 0.0
    width, depth, height = (
        round(float(value) * MULTIVIEW_CANDIDATE_DIMENSION_SCALE, 4)
        for value in updated["dimensions_xyz"]
    )
    footprint = 0.5 * math.sqrt(float(width) * float(width) + float(depth) * float(depth))
    updated["dimensions_xyz"] = [float(width), float(depth), float(height)]
    updated["base_xyz"] = [round(float(base_x), 4), round(float(base_y), 4), round(float(base_z), 4)]
    updated["world_xyz"] = [round(float(base_x), 4), round(float(base_y), 4), round(float(base_z + height * 0.5), 4)]
    updated["footprint_radius"] = round(float(footprint), 4)
    updated["dimension_scale"] = round(
        float(updated.get("dimension_scale", 1.0)) * MULTIVIEW_CANDIDATE_DIMENSION_SCALE,
        4,
    )
    updated["multiview_position_scale"] = round(float(MULTIVIEW_CANDIDATE_POSITION_SCALE), 4)
    updated["multiview_dimension_scale"] = round(float(MULTIVIEW_CANDIDATE_DIMENSION_SCALE), 4)
    return updated


def _canonicalize_specs(
    *,
    candidate_specs: Sequence[Mapping[str, Any]],
    context_specs: Sequence[Mapping[str, Any]],
    answer_label: str,
    target_index: int,
    rng,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    labels = [str(label) for label in POINT_LABELS[: len(candidate_specs)]]
    remaining_labels = [str(label) for label in labels if str(label) != str(answer_label)]
    rng.shuffle(remaining_labels)
    canonical_candidates: List[Dict[str, Any]] = []
    for index, spec in enumerate(candidate_specs):
        object_id = f"object_{int(index):02d}"
        label = str(answer_label) if int(index) == int(target_index) else str(remaining_labels.pop())
        updated = _scale_candidate_for_multiview(spec)
        updated.update(
            {
                "object_id": str(object_id),
                "point_id": str(object_id),
                "canonical_object_id": str(object_id),
                "stable_object_index": int(index),
                "point_label": str(label),
                "object_label": str(label),
                "is_answer_candidate": True,
            }
        )
        base_color = POINT_COLORS[int(index) % len(POINT_COLORS)]
        updated["fill_rgb"] = [
            int(channel)
            for channel in resolve_three_d_object_fill_rgb(
                updated,
                base_rgb=base_color,
                salt="multiview_object_match.candidate",
                variation_strength=0.12,
            )
        ]
        canonical_candidates.append(updated)

    canonical_context: List[Dict[str, Any]] = []
    for index, spec in enumerate(context_specs):
        object_id = f"context_{int(index):02d}_{spec['shape_type']}"
        updated = dict(spec)
        updated.update(
            {
                "object_id": str(object_id),
                "canonical_object_id": str(object_id),
                "is_answer_candidate": False,
            }
        )
        updated.pop("point_label", None)
        updated.pop("object_label", None)
        updated.pop("point_id", None)
        updated["fill_rgb"] = [
            int(channel)
            for channel in resolve_three_d_object_fill_rgb(
                updated,
                palette=CONTEXT_OBJECT_COLORS,
                salt="multiview_object_match.context",
                variation_strength=0.24,
            )
        ]
        canonical_context.append(updated)

    return list(canonical_candidates), list(canonical_context), f"object_{int(target_index):02d}"


def _view_is_valid(
    *,
    candidate_specs: Sequence[Mapping[str, Any]],
    context_specs: Sequence[Mapping[str, Any]],
    target_object_id: str,
    camera,
    frame,
    panel_params: _RenderParams,
) -> bool:
    candidate_bboxes_by_id = {
        str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=12.0)
        for spec in candidate_specs
    }
    all_bboxes_by_id = {
        str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=12.0)
        for spec in [*candidate_specs, *context_specs]
    }
    candidate_bboxes = list(candidate_bboxes_by_id.values())
    if any(not _bbox_is_readable(bbox, width=int(panel_params.canvas_width), height=int(panel_params.canvas_height)) for bbox in candidate_bboxes):
        return False
    if any(_bbox_area(bbox) < MULTIVIEW_MIN_CANDIDATE_BBOX_AREA_PX for bbox in candidate_bboxes):
        return False
    if any(
        _bbox_intersection_area(a, b) > 7200.0
        for index, a in enumerate(candidate_bboxes)
        for b in candidate_bboxes[index + 1 :]
    ):
        return False
    target_bbox = candidate_bboxes_by_id[str(target_object_id)]
    max_allowed_target_overlap = min(1250.0, 0.34 * _bbox_area(target_bbox))
    for other_id, other_bbox in all_bboxes_by_id.items():
        if str(other_id) == str(target_object_id):
            continue
        if _bbox_intersection_area(target_bbox, other_bbox) > max_allowed_target_overlap:
            return False
    screen_centers = [
        (float(_project_screen(spec["world_xyz"], camera, frame)[0]), float(_project_screen(spec["world_xyz"], camera, frame)[1]))
        for spec in candidate_specs
    ]
    return not any(
        math.hypot(a[0] - b[0], a[1] - b[1]) < 36.0
        for index, a in enumerate(screen_centers)
        for b in screen_centers[index + 1 :]
    )


def _build_multiview_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    point_count: int,
    context_object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    view_a_yaw_band, view_b_yaw_band = _camera_yaw_bands_for_instance(int(instance_seed))
    answer_label = str(POINT_LABELS[abs(int(instance_seed)) % int(point_count)])
    panel_layout = _panel_layout(render_params)
    panel_params = _panel_render_params(render_params, panel_layout[REFERENCE_VIEW_KEY])

    for _attempt in range(420):
        camera_a = _sample_camera(rng, yaw_band_degrees=view_a_yaw_band)
        camera_b = _sample_camera(rng, yaw_band_degrees=view_b_yaw_band)
        if _yaw_separation_degrees(float(camera_a.yaw_degrees), float(camera_b.yaw_degrees)) < 72.0:
            continue
        raw_candidates, raw_context = _sample_scene_object_specs(
            rng=rng,
            candidate_count=int(point_count),
            context_object_count=int(context_object_count),
        )
        target_index = int(rng.randrange(int(point_count)))
        candidate_specs, context_specs, target_object_id = _canonicalize_specs(
            candidate_specs=raw_candidates,
            context_specs=raw_context,
            answer_label=str(answer_label),
            target_index=int(target_index),
            rng=rng,
        )
        all_specs = [*candidate_specs, *context_specs]
        reference_points = [point for spec in all_specs for point in _object_reference_points(spec)]
        frame_a = _build_projection_frame(camera=camera_a, render_params=panel_params, point_worlds=reference_points)
        frame_b = _build_projection_frame(camera=camera_b, render_params=panel_params, point_worlds=reference_points)
        if not _view_is_valid(
            candidate_specs=candidate_specs,
            context_specs=context_specs,
            target_object_id=str(target_object_id),
            camera=camera_a,
            frame=frame_a,
            panel_params=panel_params,
        ):
            continue
        if not _view_is_valid(
            candidate_specs=candidate_specs,
            context_specs=context_specs,
            target_object_id=str(target_object_id),
            camera=camera_b,
            frame=frame_b,
            panel_params=panel_params,
        ):
            continue

        view_a_candidates = _finalize_specs(candidate_specs, camera=camera_a, frame=frame_a)
        view_a_context = _finalize_specs(context_specs, camera=camera_a, frame=frame_a)
        view_b_candidates = _finalize_specs(candidate_specs, camera=camera_b, frame=frame_b)
        view_b_context = _finalize_specs(context_specs, camera=camera_b, frame=frame_b)
        matched_spec = next(spec for spec in view_b_candidates if str(spec["object_id"]) == str(target_object_id))
        if str(matched_spec["point_label"]) != str(answer_label):
            continue
        camera_a_distances = [float(spec["camera_distance"]) for spec in view_a_candidates]
        camera_b_distances = [float(spec["camera_distance"]) for spec in view_b_candidates]
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "point_count": int(point_count),
            "candidate_count": int(point_count),
            "context_object_count": int(context_object_count),
            "object_count": int(point_count) + int(context_object_count),
            "answer_label": str(answer_label),
            "answer_point_id": str(target_object_id),
            "target_object_id": str(target_object_id),
            "target_shape_type": str(matched_spec["shape_type"]),
            "target_object_name": str(matched_spec["object_name"]),
            "point_specs": sorted(view_b_candidates, key=lambda spec: str(spec["point_label"])),
            "context_object_specs": sorted(view_b_context, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted([*view_b_candidates, *view_b_context], key=lambda spec: str(spec["object_id"])),
            "canonical_point_specs": sorted(candidate_specs, key=lambda spec: str(spec["object_id"])),
            "canonical_context_object_specs": sorted(context_specs, key=lambda spec: str(spec["object_id"])),
            "views": {
                REFERENCE_VIEW_KEY: {
                    "view_role": "source_reference",
                    "point_specs": sorted(view_a_candidates, key=lambda spec: str(spec["point_label"])),
                    "context_object_specs": sorted(view_a_context, key=lambda spec: str(spec["object_id"])),
                    "camera": _camera_record(camera_a, yaw_band=view_a_yaw_band),
                    "projection_frame": _frame_record(frame_a),
                },
                CANDIDATE_VIEW_KEY: {
                    "view_role": "answer_candidates",
                    "point_specs": sorted(view_b_candidates, key=lambda spec: str(spec["point_label"])),
                    "context_object_specs": sorted(view_b_context, key=lambda spec: str(spec["object_id"])),
                    "camera": _camera_record(camera_b, yaw_band=view_b_yaw_band),
                    "projection_frame": _frame_record(frame_b),
                },
            },
            "solver_trace": {
                "match_key": "canonical_object_id",
                "target_object_id": str(target_object_id),
                "answer_label": str(answer_label),
                "candidate_labels_by_object_id": {
                    str(spec["object_id"]): str(spec["point_label"])
                    for spec in sorted(view_b_candidates, key=lambda spec: str(spec["object_id"]))
                },
                "same_object_unique_answer": True,
                "view_yaw_separation_degrees": round(
                    float(_yaw_separation_degrees(float(camera_a.yaw_degrees), float(camera_b.yaw_degrees))),
                    4,
                ),
                "view_a_unique_camera_distance_margin": round(float(_min_pairwise(camera_a_distances)), 4),
                "view_b_unique_camera_distance_margin": round(float(_min_pairwise(camera_b_distances)), 4),
            },
        }
    raise ValueError("could not construct a valid 3D multiview object-match scene")


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
class ThreeDSpatialMultiviewObjectMatchLabelTask:
    """Match a red-boxed object across two camera views of the same 3D scene."""

    task_id = TASK_ID
    domain = "three_d"
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
        point_count, point_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="point_count",
            minimum_default=int(group_default(_GEN_DEFAULTS, "point_count_min", 6)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "point_count_max", 6)),
            lower=4,
            upper=8,
        )
        context_object_count, context_object_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="context_object_count",
            minimum_default=int(group_default(_GEN_DEFAULTS, "context_object_count_min", 2)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "context_object_count_max", 2)),
            lower=0,
            upper=3,
        )
        render_params = _resolve_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.canvas",
        )
        dataset = _build_multiview_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            context_object_count=int(context_object_count),
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        rendered_image, rendered_by_view, background_meta = _render_multiview_scene(
            dataset=dataset,
            render_params=render_params,
            instance_seed=int(instance_seed),
            params=params,
            background_defaults=_BACKGROUND_DEFAULTS,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )
        panel_layout = _panel_layout(render_params)
        reference_panel = panel_layout[REFERENCE_VIEW_KEY]
        candidate_panel = panel_layout[CANDIDATE_VIEW_KEY]
        rendered_reference = rendered_by_view[REFERENCE_VIEW_KEY]
        rendered_candidate = rendered_by_view[CANDIDATE_VIEW_KEY]
        answer_label = str(dataset["answer_label"])
        target_object_id = str(dataset["target_object_id"])
        reference_bbox = _offset_bbox(
            rendered_reference.object_bboxes_px[target_object_id],
            dx=float(reference_panel["x"]),
            dy=float(reference_panel["y"]),
        )
        candidate_bbox = _offset_bbox(
            rendered_candidate.point_bboxes_px[answer_label],
            dx=float(candidate_panel["x"]),
            dy=float(candidate_panel["y"]),
        )
        annotation_bbox_map = {
            "reference_view_object": list(reference_bbox),
            "second_view_match": list(candidate_bbox),
        }

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

        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bbox_map))
        solver_trace = dict(dataset["solver_trace"])
        reference_maps = _shift_render_maps(rendered_reference, panel=reference_panel)
        candidate_maps = _shift_render_maps(rendered_candidate, panel=candidate_panel)
        scene_entities = [
            *_offset_entities(rendered_reference.entities, dx=float(reference_panel["x"]), dy=float(reference_panel["y"]), view_key=REFERENCE_VIEW_KEY),
            *_offset_entities(rendered_candidate.entities, dx=float(candidate_panel["x"]), dy=float(candidate_panel["y"]), view_key=CANDIDATE_VIEW_KEY),
        ]

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene_multiview",
                "entities": [dict(entity) for entity in scene_entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "point_count": int(point_count),
                    "candidate_count": int(point_count),
                    "context_object_count": int(context_object_count),
                    "object_count": int(dataset["object_count"]),
                    "view_count": 2,
                    "view_keys": [REFERENCE_VIEW_KEY, CANDIDATE_VIEW_KEY],
                    "target_object_id": str(target_object_id),
                    "target_shape_type": str(dataset["target_shape_type"]),
                    "target_object_name": str(dataset["target_object_name"]),
                    "answer_label": str(answer_label),
                    "view_family": "two_camera_synthetic_perspective_3d_scene",
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
                    "point_count_probabilities": dict(point_count_probabilities),
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_object_count_probabilities),
                    "object_count": int(dataset["object_count"]),
                    "target_object_id": str(target_object_id),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
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
                "panel_layout": dict(panel_layout),
                "panel_render": {
                    "canvas_width": int(_panel_render_params(render_params, reference_panel).canvas_width),
                    "canvas_height": int(_panel_render_params(render_params, reference_panel).canvas_height),
                    "label_font_size_px": int(_panel_render_params(render_params, reference_panel).label_font_size_px),
                },
                "views": {
                    REFERENCE_VIEW_KEY: {
                        "camera": dict(dataset["views"][REFERENCE_VIEW_KEY]["camera"]),
                        "projection_frame": dict(dataset["views"][REFERENCE_VIEW_KEY]["projection_frame"]),
                    },
                    CANDIDATE_VIEW_KEY: {
                        "camera": dict(dataset["views"][CANDIDATE_VIEW_KEY]["camera"]),
                        "projection_frame": dict(dataset["views"][CANDIDATE_VIEW_KEY]["projection_frame"]),
                    },
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": [0.0, 0.0, float(render_params.canvas_width), float(render_params.canvas_height)],
                "views": {
                    REFERENCE_VIEW_KEY: dict(reference_maps),
                    CANDIDATE_VIEW_KEY: dict(candidate_maps),
                },
                "reference_view_object_bbox_px": list(reference_bbox),
                "second_view_match_bbox_px": list(candidate_bbox),
                "point_bboxes_px": dict(candidate_maps["point_bboxes_px"]),
                "point_centers_px": dict(candidate_maps["point_centers_px"]),
                "object_bboxes_px": dict(candidate_maps["object_bboxes_px"]),
                "object_centers_px": dict(candidate_maps["object_centers_px"]),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "point_count": int(point_count),
                "candidate_count": int(point_count),
                "context_object_count": int(context_object_count),
                "object_count": int(dataset["object_count"]),
                "answer_label": str(answer_label),
                "answer_point_id": str(dataset["answer_point_id"]),
                "target_object_id": str(target_object_id),
                "target_shape_type": str(dataset["target_shape_type"]),
                "target_object_name": str(dataset["target_object_name"]),
                "canonical_point_specs": [dict(spec) for spec in dataset["canonical_point_specs"]],
                "canonical_context_object_specs": [dict(spec) for spec in dataset["canonical_context_object_specs"]],
                "point_specs": [dict(spec) for spec in dataset["point_specs"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "views": {
                    REFERENCE_VIEW_KEY: {
                        "point_specs": [dict(spec) for spec in dataset["views"][REFERENCE_VIEW_KEY]["point_specs"]],
                        "context_object_specs": [dict(spec) for spec in dataset["views"][REFERENCE_VIEW_KEY]["context_object_specs"]],
                        "camera": dict(dataset["views"][REFERENCE_VIEW_KEY]["camera"]),
                        "projection_frame": dict(dataset["views"][REFERENCE_VIEW_KEY]["projection_frame"]),
                    },
                    CANDIDATE_VIEW_KEY: {
                        "point_specs": [dict(spec) for spec in dataset["views"][CANDIDATE_VIEW_KEY]["point_specs"]],
                        "context_object_specs": [dict(spec) for spec in dataset["views"][CANDIDATE_VIEW_KEY]["context_object_specs"]],
                        "camera": dict(dataset["views"][CANDIDATE_VIEW_KEY]["camera"]),
                        "projection_frame": dict(dataset["views"][CANDIDATE_VIEW_KEY]["projection_frame"]),
                    },
                },
                "question_format": str(query_id),
                "view_family": "two_camera_synthetic_perspective_3d_scene",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "keyed_object_match",
                "ids_by_role": {
                    "reference_view_object": str(target_object_id),
                    "second_view_match": str(target_object_id),
                },
                "answer_label": str(answer_label),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_bbox_map),
                "pixel_keyed_bbox_map": dict(annotation_bbox_map),
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


__all__ = ["ThreeDSpatialMultiviewObjectMatchLabelTask"]
