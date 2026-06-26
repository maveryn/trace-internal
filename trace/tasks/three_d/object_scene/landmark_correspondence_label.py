"""Multi-view landmark correspondence task for synthetic 3D object scenes."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ..shared.canvas import render_params_canvas_metadata
from ..shared.color_variation import resolve_three_d_object_fill_rgb
from ..shared.object_landmarks import (
    LANDMARK_CORRESPONDENCE_SHAPE_TYPES,
    ObjectLandmarkSpec,
    landmark_world_xyz,
    object_landmarks_for_shape,
)
from ..shared.object_scene import (
    POINT_COLORS,
    POINT_LABELS,
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    _RenderParams,
    _build_projection_frame,
    _make_object_spec,
    _object_reference_points,
    _object_screen_bbox,
    _project_screen,
    _resolve_render_params,
    _sample_camera,
    _sample_shape_dimensions,
)
from .shared.components import LANDMARK_MARKER_RADIUS_PX, render_landmark_scene as _render_landmark_scene
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from .shared.layout import (
    CANDIDATE_VIEW_KEY,
    REFERENCE_VIEW_KEY,
    bbox_area as _bbox_area,
    bbox_is_readable as _bbox_is_readable,
    camera_record as _camera_record,
    camera_yaw_bands_for_instance as _camera_yaw_bands_for_instance,
    frame_record as _frame_record,
    offset_bbox as _offset_bbox,
    offset_entities as _offset_entities,
    offset_point as _offset_point,
    offset_point_map as _offset_point_map,
    panel_layout as _panel_layout,
    panel_render_params as _panel_render_params,
    shift_render_maps as _shift_render_maps,
    yaw_separation_degrees as _yaw_separation_degrees,
)


TASK_ID = "task_three_d__object_scene__landmark_correspondence_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("landmark_correspondence",)
LANDMARK_OPTION_COUNT = 4
LANDMARK_PANEL_ROOM_EXTENT = 1.95
LANDMARK_OBJECT_SCALE_RANGE = (1.62, 2.08)
LANDMARK_MIN_OBJECT_BBOX_AREA_PX = 9000.0
LANDMARK_MIN_POINT_SEPARATION_PX = 36.0

def _point_within_canvas(point: Sequence[float], *, width: int, height: int, margin_px: float = 26.0) -> bool:
    return (
        float(margin_px) <= float(point[0]) <= float(width) - float(margin_px)
        and float(margin_px) <= float(point[1]) <= float(height) - float(margin_px)
    )


def _point_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _landmark_panel_params(render_params: _RenderParams, panel: Mapping[str, int]) -> _RenderParams:
    base_params = _panel_render_params(render_params, panel)
    return replace(
        base_params,
        scene_margin_left_px=24,
        scene_margin_right_px=24,
        scene_margin_top_px=22,
        scene_margin_bottom_px=26,
        room_extent=min(float(base_params.room_extent), LANDMARK_PANEL_ROOM_EXTENT),
        label_font_size_px=max(24, int(base_params.label_font_size_px)),
        full_bleed_floor=True,
    )


def _scaled_object_spec(
    *,
    object_id: str,
    shape_type: str,
    xy: Tuple[float, float],
    scale_multiplier: float,
    rng,
) -> Dict[str, Any]:
    dimensions_xyz, dimension_scale = _sample_shape_dimensions(str(shape_type), object_role="candidate", rng=rng)
    dimensions = tuple(round(float(value) * float(scale_multiplier), 4) for value in dimensions_xyz)
    spec = _make_object_spec(
        object_id=str(object_id),
        shape_type=str(shape_type),
        object_role="candidate",
        xy=(float(xy[0]), float(xy[1])),
        dimensions_xyz=dimensions,
        dimension_scale=round(float(dimension_scale) * float(scale_multiplier), 4),
        label=None,
    )
    spec.update(
        {
            "is_answer_candidate": False,
            "landmark_correspondence_object": True,
            "landmark_scale_multiplier": round(float(scale_multiplier), 4),
        }
    )
    return spec


def _finalize_spec(spec: Mapping[str, Any], *, camera, frame) -> Dict[str, Any]:
    screen = _project_screen(spec["world_xyz"], camera, frame)
    finalized = dict(spec)
    finalized.update(
        {
            "screen_xy": [round(float(screen[0]), 3), round(float(screen[1]), 3)],
            "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
            "camera_distance": round(float(screen[7]), 4),
        }
    )
    return finalized


def _landmark_point(
    spec: Mapping[str, Any],
    landmark: ObjectLandmarkSpec,
    *,
    camera,
    frame,
) -> List[float]:
    projected = _project_screen(landmark_world_xyz(spec, landmark, camera=camera), camera, frame)
    return [round(float(projected[0]), 3), round(float(projected[1]), 3)]


def _landmark_points_by_id(
    spec: Mapping[str, Any],
    landmarks: Sequence[ObjectLandmarkSpec],
    *,
    camera,
    frame,
) -> Dict[str, List[float]]:
    return {
        str(landmark.landmark_id): _landmark_point(spec, landmark, camera=camera, frame=frame)
        for landmark in landmarks
    }


def _landmark_world_points(
    spec: Mapping[str, Any],
    landmarks: Sequence[ObjectLandmarkSpec],
    *,
    camera,
) -> List[Tuple[float, float, float]]:
    return [landmark_world_xyz(spec, landmark, camera=camera) for landmark in landmarks]


def _apply_landmark_colors(
    left_spec: Mapping[str, Any],
    right_spec: Mapping[str, Any],
    *,
    color_index: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    left = dict(left_spec)
    right = dict(right_spec)
    left_base = POINT_COLORS[int(color_index) % len(POINT_COLORS)]
    right_base = POINT_COLORS[(int(color_index) + 3) % len(POINT_COLORS)]
    left["fill_rgb"] = [
        int(channel)
        for channel in resolve_three_d_object_fill_rgb(
            left,
            base_rgb=left_base,
            salt="landmark_correspondence.left",
            variation_strength=0.12,
        )
    ]
    right["fill_rgb"] = [
        int(channel)
        for channel in resolve_three_d_object_fill_rgb(
            right,
            base_rgb=right_base,
            salt="landmark_correspondence.right",
            variation_strength=0.12,
        )
    ]
    return left, right


def _view_is_valid(
    *,
    object_spec: Mapping[str, Any],
    landmark_points: Sequence[Sequence[float]],
    camera,
    frame,
    panel_params: _RenderParams,
) -> bool:
    bbox = _object_screen_bbox(object_spec, camera, frame, pad_px=14.0)
    if not _bbox_is_readable(
        bbox,
        width=int(panel_params.canvas_width),
        height=int(panel_params.canvas_height),
        min_side_px=76.0,
    ):
        return False
    if _bbox_area(bbox) < LANDMARK_MIN_OBJECT_BBOX_AREA_PX:
        return False
    if any(
        not _point_within_canvas(
            point,
            width=int(panel_params.canvas_width),
            height=int(panel_params.canvas_height),
            margin_px=30.0,
        )
        for point in landmark_points
    ):
        return False
    return not any(
        _point_distance(a, b) < LANDMARK_MIN_POINT_SEPARATION_PX
        for index, a in enumerate(landmark_points)
        for b in landmark_points[index + 1 :]
    )


def _build_landmark_dataset(
    *,
    query_id: str,
    scene_variant: str,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    """Build paired camera views with one reference landmark and one matching candidate landmark under shared 3D geometry."""
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    view_a_yaw_band, view_b_yaw_band = _camera_yaw_bands_for_instance(int(instance_seed) + 11)
    panel_layout = _panel_layout(render_params)
    panel_params = _landmark_panel_params(render_params, panel_layout[REFERENCE_VIEW_KEY])
    shape_types = list(LANDMARK_CORRESPONDENCE_SHAPE_TYPES)

    for _attempt in range(520):
        shape_type = str(shape_types[int(rng.randrange(len(shape_types)))])
        landmarks = list(object_landmarks_for_shape(shape_type))
        if len(landmarks) != LANDMARK_OPTION_COUNT:
            continue
        target_landmark = landmarks[int(rng.randrange(len(landmarks)))]
        option_labels = list(POINT_LABELS[:LANDMARK_OPTION_COUNT])
        rng.shuffle(option_labels)
        answer_label = str(option_labels[0])
        labeled_landmarks: Dict[str, ObjectLandmarkSpec] = {answer_label: target_landmark}
        distractor_landmarks = [landmark for landmark in landmarks if landmark.landmark_id != target_landmark.landmark_id]
        rng.shuffle(distractor_landmarks)
        for label, landmark in zip(option_labels[1:], distractor_landmarks):
            labeled_landmarks[str(label)] = landmark

        camera_a = _sample_camera(rng, yaw_band_degrees=view_a_yaw_band)
        camera_b = _sample_camera(rng, yaw_band_degrees=view_b_yaw_band)
        yaw_separation = _yaw_separation_degrees(float(camera_a.yaw_degrees), float(camera_b.yaw_degrees))
        if yaw_separation < 72.0:
            continue

        left_scale = float(rng.uniform(*LANDMARK_OBJECT_SCALE_RANGE))
        right_scale = float(rng.uniform(*LANDMARK_OBJECT_SCALE_RANGE))
        if abs(float(left_scale) - float(right_scale)) < 0.10:
            right_scale = min(float(LANDMARK_OBJECT_SCALE_RANGE[1]), float(right_scale) + 0.16)
        left_spec = _scaled_object_spec(
            object_id="reference_object",
            shape_type=str(shape_type),
            xy=(float(rng.uniform(-0.26, 0.18)), float(rng.uniform(-0.22, 0.26))),
            scale_multiplier=float(left_scale),
            rng=rng,
        )
        right_spec = _scaled_object_spec(
            object_id="candidate_object",
            shape_type=str(shape_type),
            xy=(float(rng.uniform(-0.18, 0.30)), float(rng.uniform(-0.28, 0.20))),
            scale_multiplier=float(right_scale),
            rng=rng,
        )
        left_spec, right_spec = _apply_landmark_colors(left_spec, right_spec, color_index=int(rng.randrange(len(POINT_COLORS))))

        left_world_points = [
            *_object_reference_points(left_spec),
            *_landmark_world_points(left_spec, landmarks, camera=camera_a),
        ]
        right_world_points = [
            *_object_reference_points(right_spec),
            *_landmark_world_points(right_spec, landmarks, camera=camera_b),
        ]
        frame_a = _build_projection_frame(camera=camera_a, render_params=panel_params, point_worlds=left_world_points)
        frame_b = _build_projection_frame(camera=camera_b, render_params=panel_params, point_worlds=right_world_points)
        left_points_by_id = _landmark_points_by_id(left_spec, landmarks, camera=camera_a, frame=frame_a)
        right_points_by_label = {
            str(label): _landmark_point(right_spec, landmark, camera=camera_b, frame=frame_b)
            for label, landmark in labeled_landmarks.items()
        }
        if not _view_is_valid(
            object_spec=left_spec,
            landmark_points=[left_points_by_id[str(target_landmark.landmark_id)]],
            camera=camera_a,
            frame=frame_a,
            panel_params=panel_params,
        ):
            continue
        if not _view_is_valid(
            object_spec=right_spec,
            landmark_points=list(right_points_by_label.values()),
            camera=camera_b,
            frame=frame_b,
            panel_params=panel_params,
        ):
            continue

        left_final = _finalize_spec(left_spec, camera=camera_a, frame=frame_a)
        right_final = _finalize_spec(right_spec, camera=camera_b, frame=frame_b)
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "shape_type": str(shape_type),
            "object_name": str(right_final["object_name"]),
            "answer_label": str(answer_label),
            "target_landmark_id": str(target_landmark.landmark_id),
            "target_landmark_name": str(target_landmark.display_name),
            "candidate_count": int(LANDMARK_OPTION_COUNT),
            "point_specs": [dict(right_final)],
            "context_object_specs": [],
            "object_specs": [dict(right_final)],
            "views": {
                REFERENCE_VIEW_KEY: {
                    "view_role": "source_landmark",
                    "object_spec": dict(left_final),
                    "point_specs": [dict(left_final)],
                    "context_object_specs": [],
                    "camera": _camera_record(camera_a, yaw_band=view_a_yaw_band),
                    "projection_frame": _frame_record(frame_a),
                    "reference_landmark_point_px": list(left_points_by_id[str(target_landmark.landmark_id)]),
                    "landmark_points_px_by_id": dict(left_points_by_id),
                },
                CANDIDATE_VIEW_KEY: {
                    "view_role": "candidate_landmarks",
                    "object_spec": dict(right_final),
                    "point_specs": [dict(right_final)],
                    "context_object_specs": [],
                    "camera": _camera_record(camera_b, yaw_band=view_b_yaw_band),
                    "projection_frame": _frame_record(frame_b),
                    "candidate_landmark_points_px_by_label": {
                        str(label): list(point)
                        for label, point in sorted(right_points_by_label.items(), key=lambda item: str(item[0]))
                    },
                    "candidate_landmarks_by_label": {
                        str(label): {
                            "landmark_id": str(landmark.landmark_id),
                            "display_name": str(landmark.display_name),
                            "coordinate_mode": str(landmark.coordinate_mode),
                            "local_xyz": [round(float(value), 4) for value in landmark.local_xyz],
                        }
                        for label, landmark in sorted(labeled_landmarks.items(), key=lambda item: str(item[0]))
                    },
                },
            },
            "solver_trace": {
                "answer_label": str(answer_label),
                "target_landmark_id": str(target_landmark.landmark_id),
                "landmark_ids_by_label": {
                    str(label): str(landmark.landmark_id)
                    for label, landmark in sorted(labeled_landmarks.items(), key=lambda item: str(item[0]))
                },
                "same_landmark_unique_answer": True,
                "view_yaw_separation_degrees": round(float(yaw_separation), 4),
                "shape_pool": list(LANDMARK_CORRESPONDENCE_SHAPE_TYPES),
            },
        }
    raise ValueError("could not construct a valid 3D landmark-correspondence scene")




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
class ThreeDSpatialLandmarkCorrespondenceLabelTask:
    """Match a marked local landmark across two object views."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
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
        """Generate one landmark correspondence instance where both panels, labels, and point-map annotation share one dataset."""
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
        render_params = _resolve_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.canvas",
        )
        dataset = _build_landmark_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        render_panel_layout = _panel_layout(render_params)
        panel_params = _landmark_panel_params(render_params, render_panel_layout[REFERENCE_VIEW_KEY])
        rendered_image, rendered_by_view, background_meta, marker_bboxes = _render_landmark_scene(
            dataset=dataset,
            render_params=render_params,
            panel_params=panel_params,
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
        reference_point = _offset_point(
            dataset["views"][REFERENCE_VIEW_KEY]["reference_landmark_point_px"],
            dx=float(reference_panel["x"]),
            dy=float(reference_panel["y"]),
        )
        candidate_points_by_label = _offset_point_map(
            dataset["views"][CANDIDATE_VIEW_KEY]["candidate_landmark_points_px_by_label"],
            dx=float(candidate_panel["x"]),
            dy=float(candidate_panel["y"]),
        )
        matched_point = list(candidate_points_by_label[str(answer_label)])
        annotation_point_map = {
            "reference_landmark": list(reference_point),
            "matched_landmark": list(matched_point),
        }

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
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
            dynamic_slots={
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        annotation_gt = TypedValue(type="point_map", value=dict(annotation_point_map))
        solver_trace = dict(dataset["solver_trace"])
        reference_maps = _shift_render_maps(rendered_reference, panel=reference_panel)
        candidate_maps = _shift_render_maps(rendered_candidate, panel=candidate_panel)
        scene_entities = [
            *_offset_entities(
                rendered_reference.entities,
                dx=float(reference_panel["x"]),
                dy=float(reference_panel["y"]),
                view_key=REFERENCE_VIEW_KEY,
            ),
            *_offset_entities(
                rendered_candidate.entities,
                dx=float(candidate_panel["x"]),
                dy=float(candidate_panel["y"]),
                view_key=CANDIDATE_VIEW_KEY,
            ),
        ]
        scene_entities.extend(
            [
                {
                    "entity_id": "reference_landmark_marker",
                    "entity_type": "landmark_marker",
                    "bbox_px": list(marker_bboxes["reference_landmark_marker_bbox_px"]),
                    "attrs": {
                        "view_key": REFERENCE_VIEW_KEY,
                        "marker_label": "REF",
                        "landmark_id": str(dataset["target_landmark_id"]),
                        "point_px": list(reference_point),
                    },
                },
                *[
                    {
                        "entity_id": f"candidate_landmark_marker_{label}",
                        "entity_type": "landmark_marker",
                        "bbox_px": list(bbox),
                        "attrs": {
                            "view_key": CANDIDATE_VIEW_KEY,
                            "marker_label": str(label),
                            "landmark_id": str(
                                dataset["views"][CANDIDATE_VIEW_KEY]["candidate_landmarks_by_label"][str(label)]["landmark_id"]
                            ),
                            "is_answer": str(label) == str(answer_label),
                            "point_px": list(candidate_points_by_label[str(label)]),
                        },
                    }
                    for label, bbox in sorted(
                        marker_bboxes["candidate_landmark_marker_bboxes_px_by_label"].items(),
                        key=lambda item: str(item[0]),
                    )
                ],
            ]
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene_landmark_correspondence",
                "entities": [dict(entity) for entity in scene_entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "view_count": 2,
                    "view_keys": [REFERENCE_VIEW_KEY, CANDIDATE_VIEW_KEY],
                    "shape_type": str(dataset["shape_type"]),
                    "object_name": str(dataset["object_name"]),
                    "target_landmark_id": str(dataset["target_landmark_id"]),
                    "target_landmark_name": str(dataset["target_landmark_name"]),
                    "answer_label": str(answer_label),
                    "candidate_count": int(dataset["candidate_count"]),
                    "view_family": "two_camera_single_object_landmark_correspondence",
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
                    "candidate_count": int(dataset["candidate_count"]),
                    "shape_type": str(dataset["shape_type"]),
                    "answer_support": list(POINT_LABELS[:LANDMARK_OPTION_COUNT]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "scene_canvas_preset": str(render_params.canvas_preset),
                "scene_canvas_width": int(render_params.canvas_width),
                "scene_canvas_height": int(render_params.canvas_height),
                "scene_canvas_policy": str(render_params.canvas_policy),
                **render_params_canvas_metadata(render_params),
                "final_canvas_width": int(image.width),
                "final_canvas_height": int(image.height),
                "final_canvas_pixels": int(image.width) * int(image.height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "panel_layout": dict(panel_layout),
                "panel_render": {
                    "canvas_width": int(_landmark_panel_params(render_params, reference_panel).canvas_width),
                    "canvas_height": int(_landmark_panel_params(render_params, reference_panel).canvas_height),
                    "label_font_size_px": int(_landmark_panel_params(render_params, reference_panel).label_font_size_px),
                    "landmark_marker_radius_px": float(LANDMARK_MARKER_RADIUS_PX),
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
                "reference_landmark_point_px": list(reference_point),
                "matched_landmark_point_px": list(matched_point),
                "candidate_landmark_points_px_by_label": dict(candidate_points_by_label),
                "reference_landmark_marker_bbox_px": list(marker_bboxes["reference_landmark_marker_bbox_px"]),
                "candidate_landmark_marker_bboxes_px_by_label": dict(
                    marker_bboxes["candidate_landmark_marker_bboxes_px_by_label"]
                ),
                "reference_object_bbox_px": list(
                    _offset_bbox(
                        rendered_reference.object_bboxes_px["reference_object"],
                        dx=float(reference_panel["x"]),
                        dy=float(reference_panel["y"]),
                    )
                ),
                "candidate_object_bbox_px": list(
                    _offset_bbox(
                        rendered_candidate.object_bboxes_px["candidate_object"],
                        dx=float(candidate_panel["x"]),
                        dy=float(candidate_panel["y"]),
                    )
                ),
                "object_bboxes_px": dict(candidate_maps["object_bboxes_px"]),
                "object_centers_px": dict(candidate_maps["object_centers_px"]),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_label": str(answer_label),
                "shape_type": str(dataset["shape_type"]),
                "object_name": str(dataset["object_name"]),
                "target_landmark_id": str(dataset["target_landmark_id"]),
                "target_landmark_name": str(dataset["target_landmark_name"]),
                "candidate_count": int(dataset["candidate_count"]),
                "point_specs": [dict(spec) for spec in dataset["point_specs"]],
                "context_object_specs": [],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "views": {
                    REFERENCE_VIEW_KEY: {
                        "object_spec": dict(dataset["views"][REFERENCE_VIEW_KEY]["object_spec"]),
                        "point_specs": [dict(spec) for spec in dataset["views"][REFERENCE_VIEW_KEY]["point_specs"]],
                        "camera": dict(dataset["views"][REFERENCE_VIEW_KEY]["camera"]),
                        "projection_frame": dict(dataset["views"][REFERENCE_VIEW_KEY]["projection_frame"]),
                        "reference_landmark_point_px": list(
                            dataset["views"][REFERENCE_VIEW_KEY]["reference_landmark_point_px"]
                        ),
                        "landmark_points_px_by_id": dict(dataset["views"][REFERENCE_VIEW_KEY]["landmark_points_px_by_id"]),
                    },
                    CANDIDATE_VIEW_KEY: {
                        "object_spec": dict(dataset["views"][CANDIDATE_VIEW_KEY]["object_spec"]),
                        "point_specs": [dict(spec) for spec in dataset["views"][CANDIDATE_VIEW_KEY]["point_specs"]],
                        "camera": dict(dataset["views"][CANDIDATE_VIEW_KEY]["camera"]),
                        "projection_frame": dict(dataset["views"][CANDIDATE_VIEW_KEY]["projection_frame"]),
                        "candidate_landmark_points_px_by_label": dict(
                            dataset["views"][CANDIDATE_VIEW_KEY]["candidate_landmark_points_px_by_label"]
                        ),
                        "candidate_landmarks_by_label": dict(
                            dataset["views"][CANDIDATE_VIEW_KEY]["candidate_landmarks_by_label"]
                        ),
                    },
                },
                "question_format": str(query_id),
                "view_family": "two_camera_single_object_landmark_correspondence",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "keyed_landmark_match",
                "ids_by_role": {
                    "reference_landmark": str(dataset["target_landmark_id"]),
                    "matched_landmark": str(dataset["target_landmark_id"]),
                },
                "answer_label": str(answer_label),
            },
            "projected_annotation": {
                "type": "point_map",
                "point_map": dict(annotation_point_map),
                "pixel_point_map": dict(annotation_point_map),
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
    "LANDMARK_CORRESPONDENCE_SHAPE_TYPES",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDSpatialLandmarkCorrespondenceLabelTask",
]
