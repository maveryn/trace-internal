"""Named object-type counting task for a synthetic 3D object scene."""

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
from ..shared.color_variation import resolve_three_d_object_fill_rgb
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.object_scene import (
    CONTEXT_OBJECT_COLORS,
    NAMEABLE_SMALL_OBJECT_SHAPE_TYPES,
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


TASK_ID = "task_three_d__object_scene__named_object_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("object_type_count",)
COUNTABLE_SHAPE_TYPES: Tuple[str, ...] = tuple(NAMEABLE_SMALL_OBJECT_SHAPE_TYPES)
COUNT_SCENE_SLOTS: Tuple[Tuple[float, float], ...] = tuple(
    (x, y)
    for y in (-2.42, -1.34, -0.26, 0.82, 1.90)
    for x in (-2.58, -1.48, -0.38, 0.72, 1.82, 2.70)
)
COUNTABLE_DIMENSION_SCALE = 1.08
MIN_PROJECTED_OBJECT_AREA_PX = 520.0
MAX_PAIRWISE_OVERLAP_PX = 3600.0


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / max(1, len(support))
    return {str(value): float(probability) for value in support}


def _object_plural(name: str) -> str:
    raw = str(name).strip()
    if raw in {"fish", "dice"}:
        return raw
    if raw.endswith("y") and (len(raw) < 2 or raw[-2].lower() not in {"a", "e", "i", "o", "u"}):
        return f"{raw[:-1]}ies"
    if raw.endswith(("s", "x", "z", "ch", "sh")):
        return f"{raw}es"
    return f"{raw}s"


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _bbox_is_readable(bbox: Sequence[float], *, width: int, height: int, min_side_px: float = 18.0) -> bool:
    box_width = float(bbox[2]) - float(bbox[0])
    box_height = float(bbox[3]) - float(bbox[1])
    if box_width < float(min_side_px) or box_height < float(min_side_px):
        return False
    return float(bbox[2]) > 4.0 and float(bbox[3]) > 4.0 and float(bbox[0]) < float(width - 4) and float(bbox[1]) < float(height - 4)


def _scale_dimensions(dimensions_xyz: Sequence[float], scale: float) -> Tuple[float, float, float]:
    return tuple(round(float(value) * float(scale), 4) for value in dimensions_xyz)  # type: ignore[return-value]


def _make_countable_object(
    *,
    rng,
    object_id: str,
    shape_type: str,
    xy: Tuple[float, float],
    matches_query: bool,
) -> Dict[str, Any]:
    dimensions_xyz, dimension_scale = _sample_shape_dimensions(str(shape_type), object_role="candidate", rng=rng)
    scaled_dimensions = _scale_dimensions(dimensions_xyz, COUNTABLE_DIMENSION_SCALE)
    spec = _make_object_spec(
        object_id=str(object_id),
        shape_type=str(shape_type),
        object_role="candidate",
        xy=tuple(float(value) for value in xy),
        dimensions_xyz=scaled_dimensions,
        dimension_scale=float(dimension_scale) * float(COUNTABLE_DIMENSION_SCALE),
        label=None,
    )
    spec.update(
        {
            "is_answer_candidate": False,
            "is_countable_object": True,
            "matches_query": bool(matches_query),
            "count_role": "target" if bool(matches_query) else "distractor",
        }
    )
    spec["fill_rgb"] = [
        int(channel)
        for channel in resolve_three_d_object_fill_rgb(
            spec,
            palette=CONTEXT_OBJECT_COLORS,
            salt=f"{TASK_ID}.countable",
            variation_strength=0.32,
        )
    ]
    return spec


def _can_place(candidate: Mapping[str, Any], placed: Sequence[Mapping[str, Any]], *, clearance: float = 0.16) -> bool:
    cx, cy, _cz = (float(value) for value in candidate["world_xyz"])
    for item in placed:
        ix, iy, _iz = (float(value) for value in item["world_xyz"])
        min_distance = float(candidate["footprint_radius"]) + float(item["footprint_radius"]) + float(clearance)
        if math.hypot(float(cx - ix), float(cy - iy)) < float(min_distance):
            return False
    return True


def _sample_shape_sequence(
    *,
    rng,
    target_shape_type: str,
    target_count: int,
    object_count: int,
) -> List[Tuple[str, bool]]:
    distractor_pool = [str(shape) for shape in COUNTABLE_SHAPE_TYPES if str(shape) != str(target_shape_type)]
    if not distractor_pool:
        raise ValueError("named object count needs at least one distractor shape")
    shape_sequence: List[Tuple[str, bool]] = [(str(target_shape_type), True) for _ in range(int(target_count))]
    while len(shape_sequence) < int(object_count):
        shape_sequence.append((str(rng.choice(distractor_pool)), False))
    rng.shuffle(shape_sequence)
    return list(shape_sequence)


def _place_countable_objects(
    *,
    rng,
    shape_sequence: Sequence[Tuple[str, bool]],
) -> List[Dict[str, Any]]:
    slots = list(COUNT_SCENE_SLOTS)
    rng.shuffle(slots)
    placed: List[Dict[str, Any]] = []
    for index, (shape_type, matches_query) in enumerate(shape_sequence):
        for slot_index, (slot_x, slot_y) in enumerate(list(slots)):
            candidate_xy = (
                float(slot_x + rng.uniform(-0.14, 0.14)),
                float(slot_y + rng.uniform(-0.14, 0.14)),
            )
            spec = _make_countable_object(
                rng=rng,
                object_id=f"count_object_{int(index):02d}",
                shape_type=str(shape_type),
                xy=candidate_xy,
                matches_query=bool(matches_query),
            )
            if _can_place(spec, placed):
                placed.append(spec)
                slots.pop(int(slot_index))
                break
        else:
            raise ValueError("could not place enough countable 3D objects")
    return list(placed)


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


def _view_is_valid(
    *,
    specs: Sequence[Mapping[str, Any]],
    camera,
    frame,
    render_params: _RenderParams,
) -> bool:
    bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=8.0) for spec in specs]
    if any(not _bbox_is_readable(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height)) for bbox in bboxes):
        return False
    if any(_bbox_area(bbox) < MIN_PROJECTED_OBJECT_AREA_PX for bbox in bboxes):
        return False
    for index, bbox_a in enumerate(bboxes):
        for bbox_b in bboxes[index + 1 :]:
            overlap = _bbox_intersection_area(bbox_a, bbox_b)
            if overlap > MAX_PAIRWISE_OVERLAP_PX:
                return False
            if overlap > 0.42 * min(_bbox_area(bbox_a), _bbox_area(bbox_b)):
                return False
    return True


def _build_count_scene_dataset(
    *,
    query_id: str,
    scene_variant: str,
    target_shape_type: str,
    target_count: int,
    object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    selected_camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
    for _attempt in range(520):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        shape_sequence = _sample_shape_sequence(
            rng=rng,
            target_shape_type=str(target_shape_type),
            target_count=int(target_count),
            object_count=int(object_count),
        )
        object_specs = _place_countable_objects(rng=rng, shape_sequence=shape_sequence)
        reference_points = [point for spec in object_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _view_is_valid(specs=object_specs, camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_specs = _finalize_specs(object_specs, camera=camera, frame=frame)
        match_specs = [spec for spec in finalized_specs if bool(spec.get("matches_query", False))]
        if len(match_specs) != int(target_count):
            continue
        distances = [float(spec["camera_distance"]) for spec in finalized_specs]
        shape_counts = Counter(str(spec["shape_type"]) for spec in finalized_specs)
        target_name = str(match_specs[0].get("object_name", str(target_shape_type).replace("_", " ")))
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "object_count": int(object_count),
            "target_count": int(target_count),
            "answer_value": int(target_count),
            "target_shape_type": str(target_shape_type),
            "target_object_name": str(target_name),
            "target_object_plural": _object_plural(str(target_name)),
            "target_object_ids": [str(spec["object_id"]) for spec in sorted(match_specs, key=lambda item: str(item["object_id"]))],
            "object_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "point_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "context_object_specs": [],
            "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
            "camera": _camera_record(camera, yaw_band=selected_camera_yaw_band),
            "projection_frame": _frame_record(frame),
            "solver_trace": {
                "count_predicate": "shape_type == target_shape_type",
                "target_shape_type": str(target_shape_type),
                "target_object_plural": _object_plural(str(target_name)),
                "target_count": int(target_count),
                "target_object_ids": [str(spec["object_id"]) for spec in sorted(match_specs, key=lambda item: str(item["object_id"]))],
                "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
                "unique_integer_answer": True,
                "minimum_pairwise_camera_distance_margin": round(float(_min_pairwise(distances)), 4),
            },
        }
    raise ValueError("could not construct a valid 3D named object count scene")


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


def _build_complexity(
    *,
    object_count: int,
    target_count: int,
    scene_variant: str,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.50)),
        "target_count": float(raw_weights.get("target_count", 0.24)),
        "distractor_load": float(raw_weights.get("distractor_load", 0.18)),
        "scene_variant_load": float(raw_weights.get("scene_variant_load", 0.08)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(int(object_count), 10, 18),
        "target_count": _normalize_unit(int(target_count), 1, 6),
        "distractor_load": _normalize_unit(int(object_count) - int(target_count), 7, 15),
        "scene_variant_load": {
            "floor_grid_room": 0.30,
            "tabletop_room": 0.34,
            "studio_platform": 0.38,
        }.get(str(scene_variant), 0.32),
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
class ThreeDSpatialNamedObjectCountTask:
    """Count visible small objects of one named type in an object scene."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "spatial"
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
        object_count, object_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="object_count",
            minimum_default=int(group_default(_GEN_DEFAULTS, "object_count_min", 13)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "object_count_max", 16)),
            lower=8,
            upper=20,
        )
        target_count, target_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            prefix="target_count",
            minimum_default=int(group_default(_GEN_DEFAULTS, "target_count_min", 2)),
            maximum_default=int(group_default(_GEN_DEFAULTS, "target_count_max", 5)),
            lower=1,
            upper=max(1, min(8, int(object_count) - 4)),
        )
        target_support = tuple(str(shape) for shape in COUNTABLE_SHAPE_TYPES)
        explicit_target_shape = params.get("target_shape_type")
        if explicit_target_shape is not None:
            target_shape_type = str(explicit_target_shape)
            if target_shape_type not in set(target_support):
                raise ValueError(f"unsupported target_shape_type: {target_shape_type}")
        else:
            target_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.target_shape_type",
            )
            target_shape_type = str(target_support[abs(int(target_index)) % len(target_support)])
        target_shape_probabilities = _uniform_string_probability_map(
            target_support,
            selected=str(target_shape_type) if explicit_target_shape is not None else None,
        )

        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_count_scene_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            target_shape_type=str(target_shape_type),
            target_count=int(target_count),
            object_count=int(object_count),
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
        rendered = render_object_scene_3d(
            background,
            dataset=dataset,
            render_params=render_params,
            draw_candidate_labels=False,
            compute_single_evidence=False,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )
        target_object_ids = [str(object_id) for object_id in dataset["target_object_ids"]]
        evidence_bboxes = [list(rendered.object_bboxes_px[str(object_id)]) for object_id in target_object_ids]

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
                "target_object_name": str(dataset["target_object_name"]),
                "target_object_plural": str(dataset["target_object_plural"]),
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

        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        solver_trace = dict(dataset["solver_trace"])
        complexity = _build_complexity(
            object_count=int(object_count),
            target_count=int(answer_value),
            scene_variant=str(scene_variant),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene_named_object_count",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "object_count": int(object_count),
                    "countable_object_count": int(object_count),
                    "target_shape_type": str(dataset["target_shape_type"]),
                    "target_object_name": str(dataset["target_object_name"]),
                    "target_object_plural": str(dataset["target_object_plural"]),
                    "target_count": int(answer_value),
                    "target_object_ids": list(target_object_ids),
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
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(answer_value),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "target_shape_type": str(dataset["target_shape_type"]),
                    "target_shape_type_probabilities": dict(target_shape_probabilities),
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
                "room_extent": float(render_params.room_extent),
                "full_bleed_floor": bool(render_params.full_bleed_floor),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered.scene_bbox_px),
                "room_bbox_px": list(rendered.room_bbox_px),
                "object_bboxes_px": dict(rendered.object_bboxes_px),
                "object_centers_px": dict(rendered.object_centers_px),
                "target_object_bboxes_px": {
                    str(object_id): list(rendered.object_bboxes_px[str(object_id)])
                    for object_id in target_object_ids
                },
                "target_object_centers_px": {
                    str(object_id): list(rendered.object_centers_px[str(object_id)])
                    for object_id in target_object_ids
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "object_count": int(object_count),
                "target_count": int(answer_value),
                "answer_value": int(answer_value),
                "target_shape_type": str(dataset["target_shape_type"]),
                "target_object_name": str(dataset["target_object_name"]),
                "target_object_plural": str(dataset["target_object_plural"]),
                "target_object_ids": list(target_object_ids),
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "shape_counts": dict(dataset["shape_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "counted_object_set",
                "object_ids": list(target_object_ids),
                "target_shape_type": str(dataset["target_shape_type"]),
                "answer_value": int(answer_value),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in evidence_bboxes],
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


__all__ = ["ThreeDSpatialNamedObjectCountTask"]
