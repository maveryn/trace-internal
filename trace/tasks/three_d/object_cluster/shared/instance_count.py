"""Count objects of one type in a dense synthetic 3D object cluster."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.sampling import normalize_positive_weights, weighted_choice
from .....core.seed import spawn_rng
from .....core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from .....core.types import TypedValue
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....base import TaskOutput
from ....shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.output_metadata import default_task_versions
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.color_variation import resolve_three_d_object_fill_rgb
from ...shared.object_resources import (
    OBJECT_CLUSTER_DIMENSIONS,
    OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE,
    OBJECT_CLUSTER_SHAPE_TYPES,
)
from ...shared.object_scene import (
    CONTEXT_OBJECT_COLORS,
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
from ...shared.task_support import normalize_unit as _normalize_unit
from ...shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant


TASK_ID = "task_three_d__object_cluster__single_attribute_membership_count"
SCENE_ID = "object_cluster"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("type_count",)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("tabletop_pile", "shallow_tray", "cluster_mat")
SUPPORTED_COMPOSITION_MODES: Tuple[str, ...] = (
    "single_type_cluster",
    "near_homogeneous_cluster",
    "mixed_type_cluster",
)
COUNTABLE_SHAPE_TYPES: Tuple[str, ...] = tuple(str(shape) for shape in OBJECT_CLUSTER_SHAPE_TYPES)
CLUSTER_DIMENSION_SCALE = 0.96
MIN_PROJECTED_OBJECT_AREA_PX = 260.0
MAX_PAIRWISE_OVERLAP_FRACTION = 0.72
MAX_PAIRWISE_OVERLAP_PX = 6200.0
ANSWER_COUNT_BINS: Mapping[str, Tuple[int, int]] = {
    "6_10": (6, 10),
    "11_17": (11, 17),
    "18_25": (18, 25),
}
DEFAULT_ANSWER_COUNT_BIN_WEIGHTS: Mapping[str, float] = {
    "6_10": 0.35,
    "11_17": 0.40,
    "18_25": 0.25,
}

VISUAL_CONFUSION_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("pen", "pencil", "ruler", "tube", "stick", "straw"),
    ("card", "bookmark", "small_box", "ticket", "mail_envelope", "open_book"),
    ("pillow", "cushion"),
    ("candy_disc", "cd", "berry", "button", "sphere", "marble", "bead", "dot", "coaster", "lid"),
    (
        "screw",
        "paper_clip",
        "hex_nut",
        "clip",
        "socket",
        "bolt",
        "hook",
        "tape_roll",
        "torus",
    ),
    ("fork", "spoon"),
    ("plate", "bowl", "cup", "glass", "jar", "can", "lid", "bottle", "bucket", "tray", "coaster", "basket"),
    ("hammer", "paint_brush"),
    ("flower", "rose", "cactus", "leaf", "egg", "chili", "apple", "carrot", "tomato", "coffee_bean"),
    ("light_bulb", "lantern", "candle"),
    ("horseshoe", "umbrella"),
    ("mini_chair", "mini_table", "chair", "table", "stool"),
    ("small_box", "cabinet"),
    ("chess_piece", "trophy", "crown"),
)


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / max(1, len(support))
    return {str(value): float(probability) for value in support}


def _one_hot_int_probability_map(values: Sequence[int], *, selected: int) -> Dict[str, float]:
    return {str(int(value)): (1.0 if int(value) == int(selected) else 0.0) for value in values}


def _uniform_int_probability_map(values: Sequence[int]) -> Dict[str, float]:
    support = tuple(int(value) for value in values)
    if not support:
        raise ValueError("cannot build probability map over empty count support")
    probability = 1.0 / float(len(support))
    return {str(int(value)): float(probability) for value in support}


def _configured_int(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    key: str,
    default: int,
) -> int:
    return int(params.get(str(key), group_default(gen_defaults, str(key), int(default))))


def _count_probability_map_from_bins(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    support: Sequence[int],
    weights_key: str,
) -> Dict[str, float]:
    support_values = tuple(int(value) for value in support)
    if not support_values:
        raise ValueError("object cluster count support cannot be empty")
    supported_keys = {str(value) for value in support_values}
    raw_count_weights = params.get(str(weights_key), group_default(gen_defaults, str(weights_key), None))
    if isinstance(raw_count_weights, Mapping):
        weights = {
            str(key): float(value)
            for key, value in raw_count_weights.items()
            if str(key) in supported_keys
        }
        probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in support_values])
        return {str(value): float(probabilities.get(str(value), 0.0)) for value in support_values}

    raw_bin_weights = params.get(
        "answer_count_bin_weights",
        group_default(gen_defaults, "answer_count_bin_weights", DEFAULT_ANSWER_COUNT_BIN_WEIGHTS),
    )
    if not isinstance(raw_bin_weights, Mapping):
        raw_bin_weights = DEFAULT_ANSWER_COUNT_BIN_WEIGHTS
    bin_probabilities = normalize_positive_weights(
        {str(key): float(value) for key, value in raw_bin_weights.items()},
        default_keys=list(ANSWER_COUNT_BINS.keys()),
    )
    unnormalized: Dict[int, float] = {int(value): 0.0 for value in support_values}
    for bin_key, bin_probability in bin_probabilities.items():
        if str(bin_key) not in ANSWER_COUNT_BINS:
            continue
        lower, upper = ANSWER_COUNT_BINS[str(bin_key)]
        bin_support = [value for value in support_values if int(lower) <= int(value) <= int(upper)]
        if not bin_support:
            continue
        per_count_probability = float(bin_probability) / float(len(bin_support))
        for value in bin_support:
            unnormalized[int(value)] += float(per_count_probability)
    total = sum(float(value) for value in unnormalized.values())
    if total <= 0.0:
        return _uniform_int_probability_map(support_values)
    return {str(value): float(unnormalized[int(value)] / total) for value in support_values}


def _resolve_weighted_count(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    explicit_key: str,
    weights_key: str,
    minimum: int,
    maximum: int,
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    support = tuple(range(int(minimum), int(maximum) + 1))
    if not support:
        raise ValueError(f"{explicit_key} resolved no supported counts")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported {explicit_key}: {selected}")
        return int(selected), _one_hot_int_probability_map(support, selected=int(selected))
    probabilities = _count_probability_map_from_bins(
        params=params,
        gen_defaults=gen_defaults,
        support=support,
        weights_key=str(weights_key),
    )
    rng = spawn_rng(int(instance_seed), str(namespace))
    selected = int(weighted_choice(rng, probabilities, sort_keys=False))
    return int(selected), {str(value): float(probabilities[str(value)]) for value in support}


def _resolve_uniform_count(
    *,
    params: Mapping[str, Any],
    explicit_key: str,
    minimum: int,
    maximum: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    support = tuple(range(int(minimum), int(maximum) + 1))
    if not support:
        raise ValueError(f"{explicit_key} resolved no supported counts")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported {explicit_key}: {selected}")
        return int(selected), _one_hot_int_probability_map(support, selected=int(selected))
    rng = spawn_rng(int(instance_seed), str(namespace))
    probabilities = _uniform_int_probability_map(support)
    selected = int(weighted_choice(rng, probabilities, sort_keys=False))
    return int(selected), probabilities


def _object_plural(name: str) -> str:
    raw = str(name).strip()
    if raw in {"fish", "dice"}:
        return raw
    if raw.endswith("y") and (len(raw) < 2 or raw[-2].lower() not in {"a", "e", "i", "o", "u"}):
        return f"{raw[:-1]}ies"
    if raw.endswith(("s", "x", "z", "ch", "sh")):
        return f"{raw}es"
    return f"{raw}s"


def _scale_dimensions(dimensions_xyz: Sequence[float], scale: float) -> Tuple[float, float, float]:
    return tuple(round(float(value) * float(scale), 4) for value in dimensions_xyz)  # type: ignore[return-value]


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _bbox_is_readable(bbox: Sequence[float], *, width: int, height: int, min_side_px: float = 12.0) -> bool:
    box_width = float(bbox[2]) - float(bbox[0])
    box_height = float(bbox[3]) - float(bbox[1])
    if box_width < float(min_side_px) or box_height < float(min_side_px):
        return False
    return float(bbox[2]) > 4.0 and float(bbox[3]) > 4.0 and float(bbox[0]) < float(width - 4) and float(bbox[1]) < float(height - 4)


def _compatible_distractor_pool(target_shape_type: str) -> Tuple[str, ...]:
    blocked = {str(target_shape_type)}
    for group in VISUAL_CONFUSION_GROUPS:
        if str(target_shape_type) in {str(item) for item in group}:
            blocked.update(str(item) for item in group)
    pool = tuple(str(shape) for shape in COUNTABLE_SHAPE_TYPES if str(shape) not in blocked)
    if not pool:
        raise ValueError("object cluster needs at least one compatible distractor shape")
    return pool


def _sample_scaled_dimensions(*, rng, shape_type: str) -> Tuple[Tuple[float, float, float], float]:
    base = OBJECT_CLUSTER_DIMENSIONS.get(str(shape_type), (0.52, 0.52, 0.52))
    scale = float(rng.uniform(0.84, 1.12)) * float(CLUSTER_DIMENSION_SCALE)
    return _scale_dimensions(base, scale), round(float(scale), 4)


def _make_cluster_object(
    *,
    rng,
    object_id: str,
    shape_type: str,
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
        }
    )
    spec["fill_rgb"] = [
        int(channel)
        for channel in resolve_three_d_object_fill_rgb(
            spec,
            palette=CONTEXT_OBJECT_COLORS,
            salt=f"{TASK_ID}.cluster",
            variation_strength=0.34,
        )
    ]
    return spec


def _sample_shape_sequence(
    *,
    rng,
    composition_mode: str,
    target_shape_type: str,
    target_count: int,
    object_count: int,
) -> List[Tuple[str, bool]]:
    shape_sequence: List[Tuple[str, bool]] = [(str(target_shape_type), True) for _ in range(int(target_count))]
    if str(composition_mode) == "single_type_cluster":
        if int(target_count) != int(object_count):
            raise ValueError("single_type_cluster requires target_count == object_count")
        rng.shuffle(shape_sequence)
        return list(shape_sequence)
    distractor_pool = list(_compatible_distractor_pool(str(target_shape_type)))
    while len(shape_sequence) < int(object_count):
        shape_sequence.append((str(rng.choice(distractor_pool)), False))
    rng.shuffle(shape_sequence)
    return list(shape_sequence)


def _sample_cluster_xy(rng, *, cluster_radius: float, y_scale: float) -> Tuple[float, float]:
    angle = float(rng.uniform(0.0, 2.0 * math.pi))
    radius = float(rng.random() ** 0.64) * float(cluster_radius)
    return (
        float(radius * math.cos(angle) + rng.uniform(-0.12, 0.12)),
        float(radius * math.sin(angle) * float(y_scale) + rng.uniform(-0.10, 0.10)),
    )


def _can_place_cluster(candidate: Mapping[str, Any], placed: Sequence[Mapping[str, Any]]) -> bool:
    cx, cy, _cz = (float(value) for value in candidate["world_xyz"])
    for item in placed:
        ix, iy, _iz = (float(value) for value in item["world_xyz"])
        min_distance = 0.46 * (float(candidate["footprint_radius"]) + float(item["footprint_radius"]))
        if math.hypot(float(cx - ix), float(cy - iy)) < float(min_distance):
            return False
    return True


def _place_cluster_objects(
    *,
    rng,
    shape_sequence: Sequence[Tuple[str, bool]],
    scene_variant: str,
) -> List[Dict[str, Any]]:
    cluster_radius = {"tabletop_pile": 2.42, "shallow_tray": 2.24, "cluster_mat": 2.56}.get(str(scene_variant), 2.42)
    y_scale = {"tabletop_pile": 0.76, "shallow_tray": 0.70, "cluster_mat": 0.82}.get(str(scene_variant), 0.76)
    placed: List[Dict[str, Any]] = []
    for index, (shape_type, matches_query) in enumerate(shape_sequence):
        for _ in range(180):
            candidate = _make_cluster_object(
                rng=rng,
                object_id=f"cluster_object_{int(index):02d}",
                shape_type=str(shape_type),
                xy=_sample_cluster_xy(rng, cluster_radius=float(cluster_radius), y_scale=float(y_scale)),
                matches_query=bool(matches_query),
            )
            if _can_place_cluster(candidate, placed):
                candidate["render_order_bias"] = round(float(rng.uniform(-0.035, 0.035)), 5)
                placed.append(candidate)
                break
        else:
            raise ValueError("could not place enough clustered 3D objects")
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


def _resolve_composition_mode(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    explicit_mode = params.get("composition_mode")
    explicit_object_count = params.get("object_count")
    explicit_target_count = params.get("target_count")
    if explicit_mode is None and explicit_object_count is not None and explicit_target_count is not None:
        object_count = int(explicit_object_count)
        target_count = int(explicit_target_count)
        distractor_count = int(object_count) - int(target_count)
        if distractor_count < 0:
            raise ValueError("object_count must be at least target_count")
        if distractor_count == 0:
            selected = "single_type_cluster"
        elif 1 <= distractor_count <= 4:
            selected = "near_homogeneous_cluster"
        else:
            selected = "mixed_type_cluster"
        return selected, _uniform_string_probability_map(SUPPORTED_COMPOSITION_MODES, selected=str(selected))

    return _shared_resolve_axis_variant(
        params,
        task_id=TASK_ID,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_COMPOSITION_MODES,
        explicit_key="composition_mode",
        weights_key="composition_mode_weights",
        balance_flag_key="balanced_composition_mode_sampling",
        axis_namespace="composition_mode",
    )


def _count_bounds(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    minimum_key: str,
    maximum_key: str,
    fallback_minimum: int,
    fallback_maximum: int,
    lower: int,
    upper: int,
) -> Tuple[int, int]:
    minimum = _configured_int(params, gen_defaults, str(minimum_key), int(fallback_minimum))
    maximum = _configured_int(params, gen_defaults, str(maximum_key), int(fallback_maximum))
    minimum = max(int(lower), min(int(upper), int(minimum)))
    maximum = max(int(minimum), min(int(upper), int(maximum)))
    return int(minimum), int(maximum)


def _resolve_cluster_counts(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    composition_mode: str,
    instance_seed: int,
) -> Dict[str, Any]:
    explicit_object_count = params.get("object_count")
    explicit_target_count = params.get("target_count")

    if str(composition_mode) == "single_type_cluster":
        minimum, maximum = _count_bounds(
            params=params,
            gen_defaults=gen_defaults,
            minimum_key="single_type_count_min",
            maximum_key="single_type_count_max",
            fallback_minimum=_configured_int(params, gen_defaults, "target_count_min", 6),
            fallback_maximum=_configured_int(params, gen_defaults, "target_count_max", 25),
            lower=6,
            upper=25,
        )
        if explicit_object_count is not None and explicit_target_count is not None:
            if int(explicit_object_count) != int(explicit_target_count):
                raise ValueError("single_type_cluster requires matching object_count and target_count")
            selected = int(explicit_target_count)
            support = tuple(range(int(minimum), int(maximum) + 1))
            if selected not in set(support):
                raise ValueError("single_type_cluster explicit count is outside configured support")
            probabilities = _one_hot_int_probability_map(support, selected=int(selected))
        elif explicit_object_count is not None:
            selected, probabilities = _resolve_weighted_count(
                params={**dict(params), "target_count": int(explicit_object_count)},
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                explicit_key="target_count",
                weights_key="target_count_weights",
                minimum=int(minimum),
                maximum=int(maximum),
                namespace=f"{TASK_ID}.single_type_count",
            )
        else:
            selected, probabilities = _resolve_weighted_count(
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                explicit_key="target_count",
                weights_key="target_count_weights",
                minimum=int(minimum),
                maximum=int(maximum),
                namespace=f"{TASK_ID}.single_type_count",
            )
        return {
            "object_count": int(selected),
            "target_count": int(selected),
            "distractor_count": 0,
            "object_count_probabilities": dict(probabilities),
            "target_count_probabilities": dict(probabilities),
            "distractor_count_probabilities": {"0": 1.0},
        }

    if str(composition_mode) == "near_homogeneous_cluster":
        target_minimum, target_maximum = _count_bounds(
            params=params,
            gen_defaults=gen_defaults,
            minimum_key="near_homogeneous_target_count_min",
            maximum_key="near_homogeneous_target_count_max",
            fallback_minimum=_configured_int(params, gen_defaults, "target_count_min", 6),
            fallback_maximum=_configured_int(params, gen_defaults, "target_count_max", 25),
            lower=6,
            upper=25,
        )
        object_minimum, object_maximum = _count_bounds(
            params=params,
            gen_defaults=gen_defaults,
            minimum_key="near_homogeneous_object_count_min",
            maximum_key="near_homogeneous_object_count_max",
            fallback_minimum=8,
            fallback_maximum=29,
            lower=7,
            upper=30,
        )
        distractor_minimum, distractor_maximum = _count_bounds(
            params=params,
            gen_defaults=gen_defaults,
            minimum_key="near_homogeneous_distractor_count_min",
            maximum_key="near_homogeneous_distractor_count_max",
            fallback_minimum=1,
            fallback_maximum=4,
            lower=1,
            upper=4,
        )
        if explicit_object_count is not None and explicit_target_count is not None:
            object_count = int(explicit_object_count)
            target_count = int(explicit_target_count)
            distractor_count = int(object_count) - int(target_count)
            if not (int(target_minimum) <= target_count <= int(target_maximum)):
                raise ValueError("near_homogeneous_cluster explicit target_count is outside configured support")
            if not (int(object_minimum) <= object_count <= int(object_maximum)):
                raise ValueError("near_homogeneous_cluster explicit object_count is outside configured support")
            if not (int(distractor_minimum) <= distractor_count <= int(distractor_maximum)):
                raise ValueError("near_homogeneous_cluster requires 1-4 distractor objects")
            return {
                "object_count": int(object_count),
                "target_count": int(target_count),
                "distractor_count": int(distractor_count),
                "object_count_probabilities": _one_hot_int_probability_map(range(object_minimum, object_maximum + 1), selected=int(object_count)),
                "target_count_probabilities": _one_hot_int_probability_map(range(target_minimum, target_maximum + 1), selected=int(target_count)),
                "distractor_count_probabilities": _one_hot_int_probability_map(range(distractor_minimum, distractor_maximum + 1), selected=int(distractor_count)),
            }

        if explicit_object_count is not None:
            object_count = int(explicit_object_count)
            if not (int(object_minimum) <= object_count <= int(object_maximum)):
                raise ValueError("near_homogeneous_cluster explicit object_count is outside configured support")
            feasible_distractor_minimum = max(int(distractor_minimum), int(object_count) - int(target_maximum))
            feasible_distractor_maximum = min(int(distractor_maximum), int(object_count) - int(target_minimum))
            distractor_count, distractor_probabilities = _resolve_uniform_count(
                params=params,
                explicit_key="distractor_count",
                minimum=int(feasible_distractor_minimum),
                maximum=int(feasible_distractor_maximum),
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.near_homogeneous_distractor_count",
            )
            target_count = int(object_count) - int(distractor_count)
            return {
                "object_count": int(object_count),
                "target_count": int(target_count),
                "distractor_count": int(distractor_count),
                "object_count_probabilities": _one_hot_int_probability_map(range(object_minimum, object_maximum + 1), selected=int(object_count)),
                "target_count_probabilities": _one_hot_int_probability_map(range(target_minimum, target_maximum + 1), selected=int(target_count)),
                "distractor_count_probabilities": dict(distractor_probabilities),
            }

        target_count, target_probabilities = _resolve_weighted_count(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            explicit_key="target_count",
            weights_key="target_count_weights",
            minimum=int(target_minimum),
            maximum=int(target_maximum),
            namespace=f"{TASK_ID}.near_homogeneous_target_count",
        )
        feasible_distractor_minimum = max(int(distractor_minimum), int(object_minimum) - int(target_count))
        feasible_distractor_maximum = min(int(distractor_maximum), int(object_maximum) - int(target_count))
        distractor_count, distractor_probabilities = _resolve_uniform_count(
            params=params,
            explicit_key="distractor_count",
            minimum=int(feasible_distractor_minimum),
            maximum=int(feasible_distractor_maximum),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.near_homogeneous_distractor_count",
        )
        object_count = int(target_count) + int(distractor_count)
        return {
            "object_count": int(object_count),
            "target_count": int(target_count),
            "distractor_count": int(distractor_count),
            "object_count_probabilities": _one_hot_int_probability_map(range(object_minimum, object_maximum + 1), selected=int(object_count)),
            "target_count_probabilities": dict(target_probabilities),
            "distractor_count_probabilities": dict(distractor_probabilities),
        }

    if str(composition_mode) != "mixed_type_cluster":
        raise ValueError(f"unsupported composition_mode: {composition_mode}")

    target_minimum, target_maximum = _count_bounds(
        params=params,
        gen_defaults=gen_defaults,
        minimum_key="mixed_type_target_count_min",
        maximum_key="mixed_type_target_count_max",
        fallback_minimum=6,
        fallback_maximum=18,
        lower=6,
        upper=25,
    )
    object_minimum, object_maximum = _count_bounds(
        params=params,
        gen_defaults=gen_defaults,
        minimum_key="mixed_type_object_count_min",
        maximum_key="mixed_type_object_count_max",
        fallback_minimum=16,
        fallback_maximum=30,
        lower=12,
        upper=32,
    )
    minimum_mixed_distractors = _configured_int(params, gen_defaults, "mixed_type_distractor_count_min", 5)

    if explicit_object_count is not None and explicit_target_count is not None:
        object_count = int(explicit_object_count)
        target_count = int(explicit_target_count)
        distractor_count = int(object_count) - int(target_count)
        if not (int(target_minimum) <= target_count <= int(target_maximum)):
            raise ValueError("mixed_type_cluster explicit target_count is outside configured support")
        if not (int(object_minimum) <= object_count <= int(object_maximum)):
            raise ValueError("mixed_type_cluster explicit object_count is outside configured support")
        if distractor_count < int(minimum_mixed_distractors):
            raise ValueError("mixed_type_cluster requires more distractors than near_homogeneous_cluster")
        return {
            "object_count": int(object_count),
            "target_count": int(target_count),
            "distractor_count": int(distractor_count),
            "object_count_probabilities": _one_hot_int_probability_map(range(object_minimum, object_maximum + 1), selected=int(object_count)),
            "target_count_probabilities": _one_hot_int_probability_map(range(target_minimum, target_maximum + 1), selected=int(target_count)),
            "distractor_count_probabilities": {"derived": 1.0},
        }

    if explicit_object_count is not None:
        object_count = int(explicit_object_count)
        if not (int(object_minimum) <= object_count <= int(object_maximum)):
            raise ValueError("mixed_type_cluster explicit object_count is outside configured support")
        feasible_target_maximum = min(int(target_maximum), int(object_count) - int(minimum_mixed_distractors))
        target_count, target_probabilities = _resolve_weighted_count(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            explicit_key="target_count",
            weights_key="mixed_type_target_count_weights",
            minimum=int(target_minimum),
            maximum=int(feasible_target_maximum),
            namespace=f"{TASK_ID}.mixed_type_target_count",
        )
        return {
            "object_count": int(object_count),
            "target_count": int(target_count),
            "distractor_count": int(object_count) - int(target_count),
            "object_count_probabilities": _one_hot_int_probability_map(range(object_minimum, object_maximum + 1), selected=int(object_count)),
            "target_count_probabilities": dict(target_probabilities),
            "distractor_count_probabilities": {"derived": 1.0},
        }

    target_count, target_probabilities = _resolve_weighted_count(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        explicit_key="target_count",
        weights_key="mixed_type_target_count_weights",
        minimum=int(target_minimum),
        maximum=int(target_maximum),
        namespace=f"{TASK_ID}.mixed_type_target_count",
    )
    feasible_object_minimum = max(int(object_minimum), int(target_count) + int(minimum_mixed_distractors))
    object_count, object_probabilities = _resolve_uniform_count(
        params=params,
        explicit_key="object_count",
        minimum=int(feasible_object_minimum),
        maximum=int(object_maximum),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.mixed_type_object_count",
    )
    return {
        "object_count": int(object_count),
        "target_count": int(target_count),
        "distractor_count": int(object_count) - int(target_count),
        "object_count_probabilities": dict(object_probabilities),
        "target_count_probabilities": dict(target_probabilities),
        "distractor_count_probabilities": {"derived": 1.0},
    }


def _frame_record(frame) -> Dict[str, Any]:
    return {
        "scale": round(float(frame.scale), 5),
        "center_x": round(float(frame.center_x), 3),
        "center_y": round(float(frame.center_y), 3),
        "normalized_center_u": round(float(frame.normalized_center_u), 6),
        "normalized_center_v": round(float(frame.normalized_center_v), 6),
    }


def _build_cluster_dataset(
    *,
    query_id: str,
    scene_variant: str,
    composition_mode: str,
    target_shape_type: str,
    target_count: int,
    object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    selected_camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
    for _attempt in range(640):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        shape_sequence = _sample_shape_sequence(
            rng=rng,
            composition_mode=str(composition_mode),
            target_shape_type=str(target_shape_type),
            target_count=int(target_count),
            object_count=int(object_count),
        )
        object_specs = _place_cluster_objects(rng=rng, shape_sequence=shape_sequence, scene_variant=str(scene_variant))
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
        target_name = str(OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE.get(str(target_shape_type), str(target_shape_type).replace("_", " ")))
        target_ids = [str(spec["object_id"]) for spec in sorted(match_specs, key=lambda item: str(item["object_id"]))]
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "cluster_composition_mode": str(composition_mode),
            "object_count": int(object_count),
            "target_count": int(target_count),
            "distractor_count": int(object_count) - int(target_count),
            "answer_value": int(target_count),
            "target_shape_type": str(target_shape_type),
            "target_object_name": str(target_name),
            "target_object_plural": _object_plural(str(target_name)),
            "target_object_ids": list(target_ids),
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
                "object_count": int(object_count),
                "distractor_count": int(object_count) - int(target_count),
                "cluster_composition_mode": str(composition_mode),
                "target_object_ids": list(target_ids),
                "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
                "cluster_object_pool_size": len(COUNTABLE_SHAPE_TYPES),
                "unique_integer_answer": True,
                "minimum_pairwise_camera_distance_margin": round(float(_min_pairwise(distances)), 4),
            },
        }
    raise ValueError("could not construct a valid 3D object cluster count scene")




_SCENE_DEFAULTS = get_scene_defaults("three_d", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


class ObjectClusterSingleAttributeMembershipCountBase:
    """Count visible instances of one object type in a dense object cluster."""

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
        composition_mode, composition_mode_probabilities = _resolve_composition_mode(
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        count_record = _resolve_cluster_counts(
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            composition_mode=str(composition_mode),
            instance_seed=int(instance_seed),
        )
        object_count = int(count_record["object_count"])
        target_count = int(count_record["target_count"])
        distractor_count = int(count_record["distractor_count"])
        object_count_probabilities = dict(count_record["object_count_probabilities"])
        target_count_probabilities = dict(count_record["target_count_probabilities"])
        distractor_count_probabilities = dict(count_record["distractor_count_probabilities"])
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
        dataset = _build_cluster_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            composition_mode=str(composition_mode),
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
                "target_object_name": str(dataset["target_object_name"]),
                "target_object_plural": str(dataset["target_object_plural"]),
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

        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        solver_trace = dict(dataset["solver_trace"])

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_cluster_instance_count",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "cluster_composition_mode": str(composition_mode),
                    "object_count": int(object_count),
                    "countable_object_count": int(object_count),
                    "distractor_count": int(distractor_count),
                    "cluster_object_pool_size": len(COUNTABLE_SHAPE_TYPES),
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
                    "composition_mode": str(composition_mode),
                    "composition_mode_probabilities": dict(composition_mode_probabilities),
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(answer_value),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "distractor_count": int(distractor_count),
                    "distractor_count_probabilities": dict(distractor_count_probabilities),
                    "target_shape_type": str(dataset["target_shape_type"]),
                    "target_shape_type_probabilities": dict(target_shape_probabilities),
                    "cluster_object_pool_size": len(COUNTABLE_SHAPE_TYPES),
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
                "cluster_composition_mode": str(composition_mode),
                "object_count": int(object_count),
                "target_count": int(answer_value),
                "distractor_count": int(distractor_count),
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
    "COUNTABLE_SHAPE_TYPES",
    "ObjectClusterSingleAttributeMembershipCountBase",
    "SCENE_ID",
    "SUPPORTED_SCENE_VARIANTS",
    "TASK_ID",
]
