"""Count semantic color/object conjunctions in a dense 3D object cluster."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from trace.core.types import TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.three_d.shared.object_resources import (
    OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE,
    OBJECT_CLUSTER_SHAPE_TYPES,
)
from trace.tasks.three_d.shared.object_scene import (
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
    render_object_scene_3d,
)
from trace.tasks.three_d.shared.task_support import normalize_unit as _normalize_unit
from trace.tasks.three_d.shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from trace.tasks.three_d.shared.task_support import resolve_count as _shared_resolve_count
from ._instance_count_impl import (
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    _bbox_area,
    _bbox_is_readable,
    _camera_record,
    _can_place_cluster,
    _finalize_specs,
    _frame_record,
    _object_plural,
    _sample_cluster_xy,
    _sample_scaled_dimensions,
    _uniform_string_probability_map,
)


TASK_ID = "task_three_d__object_cluster__multi_attribute_and_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("type_and_color_count",)
PROMPT_COLOR_RGB: Dict[str, Tuple[int, int, int]] = {
    "red": (218, 74, 62),
    "blue": (64, 120, 218),
    "green": (62, 158, 92),
    "yellow": (226, 185, 60),
    "purple": (143, 91, 190),
    "orange": (226, 128, 47),
}
COLOR_SAFE_CLUSTER_SHAPE_TYPES: Tuple[str, ...] = tuple(
    shape
    for shape in (
        "sphere",
        "cube",
        "cylinder",
        "cone",
        "torus",
        "pyramid",
        "wedge",
        "star_prism",
        "diamond",
        "heart",
        "button",
        "candy_disc",
        "berry",
        "card",
        "bookmark",
        "small_box",
        "puzzle_piece",
        "cup",
        "bowl",
        "plate",
        "mini_chair",
        "mini_table",
        "stool",
        "heater",
        "flower",
        "pillow",
        "cushion",
        "glass",
        "jar",
        "can",
        "lid",
        "bucket",
        "tray",
        "coaster",
        "clip",
        "socket",
        "hook",
        "tape_roll",
        "bag",
        "chess_piece",
        "straw",
        "ticket",
        "marble",
        "bead",
        "dot",
    )
    if shape in set(OBJECT_CLUSTER_SHAPE_TYPES)
)
MIN_PROJECTED_OBJECT_AREA_PX = 260.0
MAX_PAIRWISE_OVERLAP_FRACTION = 0.72
MAX_PAIRWISE_OVERLAP_PX = 6200.0


def _property_key(shape_type: str, color_name: str) -> Tuple[str, str]:
    return (str(shape_type), str(color_name))


def _target_property_phrase(target_spec: Mapping[str, Any]) -> str:
    return f"{target_spec['target_color_name']} {target_spec['target_object_plural']}"


def _target_property_singular(target_spec: Mapping[str, Any]) -> str:
    return f"{target_spec['target_color_name']} {target_spec['target_object_name']}"


def _matches_target(spec: Mapping[str, Any], target_spec: Mapping[str, Any]) -> bool:
    return (
        str(spec.get("shape_type")) == str(target_spec["target_shape_type"])
        and str(spec.get("color_name")) == str(target_spec["target_color_name"])
    )


def _resolve_target_spec(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, float]]:
    shape_support = tuple(str(shape) for shape in COLOR_SAFE_CLUSTER_SHAPE_TYPES)
    color_support = tuple(str(color) for color in PROMPT_COLOR_RGB)
    if not shape_support:
        raise ValueError("object cluster multi-attribute count has no color-safe shape support")

    explicit_shape = params.get("target_shape_type")
    if explicit_shape is not None:
        target_shape_type = str(explicit_shape)
        if target_shape_type not in set(shape_support):
            raise ValueError(f"unsupported target_shape_type for {TASK_ID}: {target_shape_type}")
    else:
        shape_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_shape_type",
        )
        target_shape_type = str(shape_support[abs(int(shape_index)) % len(shape_support)])
    shape_probabilities = _uniform_string_probability_map(
        shape_support,
        selected=str(target_shape_type) if explicit_shape is not None else None,
    )

    explicit_color = params.get("target_color_name")
    if explicit_color is not None:
        target_color_name = str(explicit_color)
        if target_color_name not in set(color_support):
            raise ValueError(f"unsupported target_color_name for {TASK_ID}: {target_color_name}")
    else:
        color_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_color_name",
        )
        target_color_name = str(color_support[abs(int(color_index)) % len(color_support)])
    color_probabilities = _uniform_string_probability_map(
        color_support,
        selected=str(target_color_name) if explicit_color is not None else None,
    )

    object_name = str(OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE.get(str(target_shape_type), str(target_shape_type).replace("_", " ")))
    target_spec = {
        "query_id": "type_and_color_count",
        "target_shape_type": str(target_shape_type),
        "target_object_name": str(object_name),
        "target_object_plural": _object_plural(str(object_name)),
        "target_color_name": str(target_color_name),
    }
    target_spec["target_property_phrase"] = _target_property_phrase(target_spec)
    target_spec["target_property_singular"] = _target_property_singular(target_spec)
    return dict(target_spec), dict(shape_probabilities), dict(color_probabilities)


def _make_colored_cluster_object(
    *,
    rng,
    object_id: str,
    shape_type: str,
    color_name: str,
    xy: Tuple[float, float],
    matches_query: bool,
) -> Dict[str, Any]:
    dimensions_xyz, dimension_scale = _sample_scaled_dimensions(rng=rng, shape_type=str(shape_type))
    object_name = str(OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE.get(str(shape_type), str(shape_type).replace("_", " ")))
    spec = _make_object_spec(
        object_id=str(object_id),
        shape_type=str(shape_type),
        object_role="candidate",
        xy=tuple(float(value) for value in xy),
        dimensions_xyz=dimensions_xyz,
        dimension_scale=float(dimension_scale),
        label=None,
    )
    spec.update(
        {
            "object_name": str(object_name),
            "prompt_name": str(object_name),
            "nameable_for_prompt": True,
            "is_answer_candidate": False,
            "is_countable_object": True,
            "matches_query": bool(matches_query),
            "count_role": "target" if bool(matches_query) else "distractor",
            "color_name": str(color_name),
            "prompt_color_name": str(color_name),
            "fill_rgb": [int(channel) for channel in PROMPT_COLOR_RGB[str(color_name)]],
            "semantic_color": True,
        }
    )
    return spec


def _sample_shape_color_sequence(
    *,
    rng,
    target_spec: Mapping[str, Any],
    target_count: int,
    object_count: int,
) -> List[Tuple[str, str, bool, str]]:
    target_shape = str(target_spec["target_shape_type"])
    target_color = str(target_spec["target_color_name"])
    shape_support = [str(shape) for shape in COLOR_SAFE_CLUSTER_SHAPE_TYPES]
    color_support = [str(color) for color in PROMPT_COLOR_RGB]
    if int(object_count) < int(target_count):
        raise ValueError("object_count must be at least target_count")

    sequence: List[Tuple[str, str, bool, str]] = [
        (target_shape, target_color, True, "target")
        for _ in range(int(target_count))
    ]
    remaining = int(object_count) - int(target_count)

    wrong_colors = [str(color) for color in color_support if str(color) != target_color]
    wrong_shapes = [str(shape) for shape in shape_support if str(shape) != target_shape]
    rng.shuffle(wrong_colors)
    rng.shuffle(wrong_shapes)

    for color_name in wrong_colors[: min(2, remaining)]:
        sequence.append((target_shape, str(color_name), False, "same_type_wrong_color"))
    remaining = int(object_count) - len(sequence)

    for shape_type in wrong_shapes[: min(2, remaining)]:
        sequence.append((str(shape_type), target_color, False, "same_color_wrong_type"))
    remaining = int(object_count) - len(sequence)

    all_distractors = [
        (str(shape), str(color))
        for shape in shape_support
        for color in color_support
        if not (str(shape) == target_shape and str(color) == target_color)
    ]
    rng.shuffle(all_distractors)
    distractor_index = 0
    while remaining > 0:
        shape_type, color_name = all_distractors[int(distractor_index) % len(all_distractors)]
        role = "same_type_wrong_color" if str(shape_type) == target_shape else (
            "same_color_wrong_type" if str(color_name) == target_color else "unmatched_distractor"
        )
        sequence.append((str(shape_type), str(color_name), False, str(role)))
        distractor_index += 1
        remaining -= 1

    rng.shuffle(sequence)
    return list(sequence)


def _place_colored_cluster_objects(
    *,
    rng,
    sequence: Sequence[Tuple[str, str, bool, str]],
    scene_variant: str,
) -> List[Dict[str, Any]]:
    cluster_radius = {"tabletop_pile": 2.42, "shallow_tray": 2.24, "cluster_mat": 2.56}.get(str(scene_variant), 2.42)
    y_scale = {"tabletop_pile": 0.76, "shallow_tray": 0.70, "cluster_mat": 0.82}.get(str(scene_variant), 0.76)
    placed: List[Dict[str, Any]] = []
    for index, (shape_type, color_name, matches_query, count_role) in enumerate(sequence):
        for _ in range(180):
            candidate = _make_colored_cluster_object(
                rng=rng,
                object_id=f"colored_cluster_object_{int(index):02d}",
                shape_type=str(shape_type),
                color_name=str(color_name),
                xy=_sample_cluster_xy(rng, cluster_radius=float(cluster_radius), y_scale=float(y_scale)),
                matches_query=bool(matches_query),
            )
            candidate["count_role"] = str(count_role)
            if _can_place_cluster(candidate, placed):
                candidate["render_order_bias"] = round(float(rng.uniform(-0.035, 0.035)), 5)
                placed.append(candidate)
                break
        else:
            raise ValueError("could not place enough colored clustered 3D objects")
    return list(placed)


def _view_is_valid(
    *,
    specs: Sequence[Mapping[str, Any]],
    camera,
    frame,
    render_params: _RenderParams,
) -> bool:
    bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=5.0) for spec in specs]
    if any(not _bbox_is_readable(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height)) for bbox in bboxes):
        return False
    if any(_bbox_area(bbox) < MIN_PROJECTED_OBJECT_AREA_PX for bbox in bboxes):
        return False
    for index, bbox_a in enumerate(bboxes):
        area_a = _bbox_area(bbox_a)
        for bbox_b in bboxes[index + 1 :]:
            overlap = _bbox_intersection_area(bbox_a, bbox_b)
            if overlap > MAX_PAIRWISE_OVERLAP_PX:
                return False
            if overlap > float(MAX_PAIRWISE_OVERLAP_FRACTION) * min(area_a, _bbox_area(bbox_b)):
                return False
    return True


def _build_dataset(
    *,
    query_id: str,
    scene_variant: str,
    target_spec: Mapping[str, Any],
    target_count: int,
    object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    selected_camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
    for _attempt in range(720):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        sequence = _sample_shape_color_sequence(
            rng=rng,
            target_spec=target_spec,
            target_count=int(target_count),
            object_count=int(object_count),
        )
        object_specs = _place_colored_cluster_objects(
            rng=rng,
            sequence=sequence,
            scene_variant=str(scene_variant),
        )
        reference_points = [point for spec in object_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _view_is_valid(specs=object_specs, camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_specs = _finalize_specs(object_specs, camera=camera, frame=frame)
        match_specs = [spec for spec in finalized_specs if _matches_target(spec, target_spec)]
        if len(match_specs) != int(target_count):
            continue

        distances = [float(spec["camera_distance"]) for spec in finalized_specs]
        shape_counts = Counter(str(spec["shape_type"]) for spec in finalized_specs)
        color_counts = Counter(str(spec["color_name"]) for spec in finalized_specs)
        property_counts = Counter(_property_key(str(spec["shape_type"]), str(spec["color_name"])) for spec in finalized_specs)
        count_role_counts = Counter(str(spec["count_role"]) for spec in finalized_specs)
        target_ids = [str(spec["object_id"]) for spec in sorted(match_specs, key=lambda item: str(item["object_id"]))]
        dataset_target_spec = dict(target_spec)
        dataset_target_spec["target_property_phrase"] = _target_property_phrase(dataset_target_spec)
        dataset_target_spec["target_property_singular"] = _target_property_singular(dataset_target_spec)
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "object_count": int(object_count),
            "countable_object_count": int(object_count),
            "target_count": int(target_count),
            "answer_value": int(target_count),
            "target_spec": dict(dataset_target_spec),
            "target_shape_type": str(dataset_target_spec["target_shape_type"]),
            "target_object_name": str(dataset_target_spec["target_object_name"]),
            "target_object_plural": str(dataset_target_spec["target_object_plural"]),
            "target_color_name": str(dataset_target_spec["target_color_name"]),
            "target_property_phrase": str(dataset_target_spec["target_property_phrase"]),
            "target_property_singular": str(dataset_target_spec["target_property_singular"]),
            "target_object_ids": list(target_ids),
            "object_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "point_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "context_object_specs": [],
            "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
            "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
            "property_counts": {
                f"{color_name}_{shape_type}": int(count)
                for (shape_type, color_name), count in sorted(property_counts.items())
            },
            "count_role_counts": {str(key): int(value) for key, value in sorted(count_role_counts.items())},
            "camera": _camera_record(camera, yaw_band=selected_camera_yaw_band),
            "projection_frame": _frame_record(frame),
            "solver_trace": {
                "count_predicate": "shape_type == target_shape_type and color_name == target_color_name",
                "target_spec": dict(dataset_target_spec),
                "target_property_phrase": str(dataset_target_spec["target_property_phrase"]),
                "target_property_singular": str(dataset_target_spec["target_property_singular"]),
                "target_count": int(target_count),
                "object_count": int(object_count),
                "target_object_ids": list(target_ids),
                "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
                "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
                "property_counts": {
                    f"{color_name}_{shape_type}": int(count)
                    for (shape_type, color_name), count in sorted(property_counts.items())
                },
                "count_role_counts": {str(key): int(value) for key, value in sorted(count_role_counts.items())},
                "cluster_object_pool_size": len(COLOR_SAFE_CLUSTER_SHAPE_TYPES),
                "semantic_color_palette": {str(key): list(value) for key, value in sorted(PROMPT_COLOR_RGB.items())},
                "unique_integer_answer": True,
                "minimum_pairwise_camera_distance_margin": round(float(_min_pairwise(distances)), 4),
            },
        }
    raise ValueError("could not construct a valid 3D object cluster multi-attribute count scene")




_SCENE_DEFAULTS = get_scene_defaults("three_d", SCENE_ID)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


class ObjectClusterMultiAttributeAndCountBase:
    """Count clustered objects matching both object type and semantic color."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    prompt_query_key = "type_and_color_count"

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
        gen_defaults, render_defaults, prompt_defaults_config = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
            task_id=TASK_ID,
        )
        query_id, query_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            supported_variants=tuple(str(value) for value in self.supported_query_ids),
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
        )
        prompt_query_key = str(self.prompt_query_key)
        scene_variant, scene_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=gen_defaults,
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
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            prefix="object_count",
            minimum_default=int(group_default(gen_defaults, "object_count_min", 16)),
            maximum_default=int(group_default(gen_defaults, "object_count_max", 30)),
            lower=12,
            upper=32,
        )
        target_count, target_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            prefix="target_count",
            minimum_default=int(group_default(gen_defaults, "target_count_min", 2)),
            maximum_default=int(group_default(gen_defaults, "target_count_max", 8)),
            lower=1,
            upper=max(1, min(10, int(object_count) - 6)),
        )
        target_spec, target_shape_probabilities, target_color_probabilities = _resolve_target_spec(
            params=params,
            instance_seed=int(instance_seed),
        )

        render_params = _resolve_render_params(params, render_defaults=render_defaults)
        dataset = _build_dataset(
            query_id=str(prompt_query_key),
            scene_variant=str(scene_variant),
            target_spec=target_spec,
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
            compute_single_annotation=False,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )
        target_object_ids = [str(object_id) for object_id in dataset["target_object_ids"]]
        annotation_bboxes = [list(rendered.object_bboxes_px[str(object_id)]) for object_id in target_object_ids]

        prompt_defaults = required_group_defaults(
            prompt_defaults_config,
            (
                "bundle_id",
                "scene_key",
                "task_key",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        target_property_phrase = str(dataset["target_property_phrase"])
        target_property_singular = str(dataset["target_property_singular"])
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(prompt_query_key),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "target_shape_type": str(dataset["target_shape_type"]),
                "target_object_name": str(dataset["target_object_name"]),
                "target_object_plural": str(dataset["target_object_plural"]),
                "target_color_name": str(dataset["target_color_name"]),
                "target_property_phrase": str(target_property_phrase),
                "target_property_singular": str(target_property_singular),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        solver_trace = dict(dataset["solver_trace"])

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_cluster_multi_attribute_and_count",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "object_count": int(object_count),
                    "countable_object_count": int(object_count),
                    "target_spec": dict(dataset["target_spec"]),
                    "target_property_phrase": str(target_property_phrase),
                    "target_property_singular": str(target_property_singular),
                    "target_shape_type": str(dataset["target_shape_type"]),
                    "target_color_name": str(dataset["target_color_name"]),
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
                    "internal_query_id": str(prompt_query_key),
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probabilities),
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(answer_value),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "target_spec": dict(dataset["target_spec"]),
                    "target_shape_type": str(dataset["target_shape_type"]),
                    "target_shape_type_probabilities": dict(target_shape_probabilities),
                    "target_color_name": str(dataset["target_color_name"]),
                    "target_color_name_probabilities": dict(target_color_probabilities),
                    "cluster_object_pool_size": len(COLOR_SAFE_CLUSTER_SHAPE_TYPES),
                    "semantic_color_palette": {str(key): list(value) for key, value in sorted(PROMPT_COLOR_RGB.items())},
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
                "semantic_color_palette": {str(key): list(value) for key, value in sorted(PROMPT_COLOR_RGB.items())},
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
                "internal_query_id": str(prompt_query_key),
                "scene_variant": str(scene_variant),
                "object_count": int(object_count),
                "target_count": int(answer_value),
                "answer_value": int(answer_value),
                "target_spec": dict(dataset["target_spec"]),
                "target_shape_type": str(dataset["target_shape_type"]),
                "target_object_name": str(dataset["target_object_name"]),
                "target_object_plural": str(dataset["target_object_plural"]),
                "target_color_name": str(dataset["target_color_name"]),
                    "target_property_phrase": str(target_property_phrase),
                    "target_property_singular": str(target_property_singular),
                "target_object_ids": list(target_object_ids),
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "shape_counts": dict(dataset["shape_counts"]),
                "color_counts": dict(dataset["color_counts"]),
                "property_counts": dict(dataset["property_counts"]),
                "count_role_counts": dict(dataset["count_role_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "internal_question_format": str(prompt_query_key),
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "object_cluster_multi_attribute_count_object_set",
                "object_ids": list(target_object_ids),
                "target_spec": dict(dataset["target_spec"]),
                "target_property_phrase": str(target_property_phrase),
                "target_property_singular": str(target_property_singular),
                "answer_value": int(answer_value),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
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
    "COLOR_SAFE_CLUSTER_SHAPE_TYPES",
    "ObjectClusterMultiAttributeAndCountBase",
    "PROMPT_COLOR_RGB",
    "TASK_ID",
]
