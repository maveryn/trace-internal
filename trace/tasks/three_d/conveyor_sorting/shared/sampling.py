"""Sampling helpers for conveyor carousel scopes and object layouts."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.named_colors import sample_named_color_palette
from trace.tasks.three_d.shared.camera_projection import (
    CameraSpec,
    build_projection_frame,
    project_screen,
    vec_cross,
    vec_norm,
    vec_sub,
)
from trace.tasks.three_d.shared.object_resources import OBJECT_CLUSTER_DIMENSIONS
from trace.tasks.three_d.shared.projected_object_geometry import object_reference_points
from trace.tasks.three_d.shared.task_support import (
    resolve_axis_variant_for_namespace,
    resolve_count_for_namespace,
)

from .state import (
    BELT_GEOMETRY,
    BELT_KEYS,
    BELT_LABELS,
    COLOR_CONFUSION_EXCLUSIONS,
    CONVEYOR_COLOR_READOUT_SHAPE_TYPES,
    CONVEYOR_OBJECT_SHAPE_TYPES,
    SCENE_ID,
    SEMANTIC_COLOR_RGB,
    SEMANTIC_COLOR_SUPPORT,
    SUPPORTED_SCENE_VARIANTS,
    public_object_name,
    public_object_plural,
)


PREDICATE_OBJECT_TYPE = "object_type"
PREDICATE_COLOR = "color"

CAMERA_YAW_BANDS_DEGREES: Tuple[Tuple[float, float], ...] = (
    (-66.0, -42.0),
    (42.0, 66.0),
    (-138.0, -114.0),
    (114.0, 138.0),
)


@dataclass(frozen=True)
class ResolvedConveyorAxes:
    """Resolved conveyor scene axes for one generated instance."""

    scene_variant: str
    scene_variant_probabilities: Dict[str, float]


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / float(max(1, len(support)))
    return {str(value): float(probability) for value in support}


def _configured_int(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], key: str, default: int) -> int:
    return int(params.get(str(key), group_default(gen_defaults, str(key), int(default))))


def resolve_conveyor_axes(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> ResolvedConveyorAxes:
    """Resolve the conveyor carousel scene variant."""

    scene_variant, scene_probabilities = resolve_axis_variant_for_namespace(
        params,
        namespace=f"{namespace}.scene_variant",
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
    )
    return ResolvedConveyorAxes(
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_probabilities),
    )


def _confusable_color_names(color_name: str) -> set[str]:
    return set(str(color) for color in COLOR_CONFUSION_EXCLUSIONS.get(str(color_name), ()))


def _sample_readout_palette(rng: Any, *, target_color: str, size: int) -> Tuple[str, ...]:
    blocked = _confusable_color_names(str(target_color)) | {str(target_color)}
    candidates = [str(color) for color in SEMANTIC_COLOR_SUPPORT if str(color) not in blocked]
    rng.shuffle(candidates)
    selected = [str(target_color), *candidates[: max(0, int(size) - 1)]]
    rng.shuffle(selected)
    return tuple(selected[: int(size)])


def _sample_shape(rng: Any, support: Sequence[str], *, exclude: Sequence[str] = ()) -> str:
    choices = [str(shape) for shape in support if str(shape) not in set(str(item) for item in exclude)]
    if not choices:
        raise ValueError("empty conveyor object shape support")
    return str(choices[int(rng.randrange(len(choices)))])


def _resolve_target_shape(
    *,
    params: Mapping[str, Any],
    rng: Any,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("target_shape_type")
    support = tuple(str(shape) for shape in CONVEYOR_OBJECT_SHAPE_TYPES)
    if explicit is not None:
        shape = str(explicit)
        if shape not in set(support):
            raise ValueError(f"unsupported target_shape_type: {shape}")
        return shape, _uniform_string_probability_map(support, selected=shape)
    shape = _sample_shape(rng, support)
    return str(shape), _uniform_string_probability_map(support)


def _resolve_target_color(
    *,
    params: Mapping[str, Any],
    rng: Any,
) -> tuple[str, Dict[str, float]]:
    support = tuple(str(color) for color in SEMANTIC_COLOR_SUPPORT)
    explicit = params.get("target_color_name")
    if explicit is not None:
        color = str(explicit)
        if color not in set(support):
            raise ValueError(f"unsupported target_color_name: {color}")
        return color, _uniform_string_probability_map(support, selected=color)
    color = str(support[int(rng.randrange(len(support)))])
    return color, _uniform_string_probability_map(support)


def _resolve_target_belt(
    *,
    params: Mapping[str, Any],
    rng: Any,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("target_belt_key")
    support = tuple(str(key) for key in BELT_KEYS)
    if explicit is not None:
        belt_key = str(explicit)
        if belt_key not in set(support):
            raise ValueError(f"unsupported target_belt_key: {belt_key}")
        return belt_key, _uniform_string_probability_map(support, selected=belt_key)
    belt_key = str(support[int(rng.randrange(len(support)))])
    return belt_key, _uniform_string_probability_map(support)


def _belt_point(belt_key: str, theta: float, radial_offset: float = 0.0) -> tuple[float, float]:
    geometry = BELT_GEOMETRY[str(belt_key)]
    radius_x = float(geometry["radius_x"]) + float(radial_offset)
    radius_y = float(geometry["radius_y"]) + float(radial_offset) * 0.62
    return (round(radius_x * math.cos(float(theta)), 4), round(radius_y * math.sin(float(theta)), 4))


def _slot_positions_for_belt(
    *,
    rng: Any,
    belt_key: str,
    slots_per_belt: int,
) -> list[tuple[float, float, float]]:
    start = float(rng.uniform(0.0, 2.0 * math.pi))
    slots: list[tuple[float, float, float]] = []
    for index in range(int(slots_per_belt)):
        theta = start + (2.0 * math.pi * float(index) / float(slots_per_belt)) + rng.uniform(-0.035, 0.035)
        width = float(BELT_GEOMETRY[str(belt_key)]["band_width"])
        radial_offset = rng.uniform(-0.18 * width, 0.18 * width)
        x, y = _belt_point(str(belt_key), float(theta), radial_offset=float(radial_offset))
        slots.append((float(x), float(y), round(math.degrees(float(theta)) % 360.0, 3)))
    rng.shuffle(slots)
    return slots


def _object_dimensions(shape_type: str, *, scale: float) -> tuple[float, float, float]:
    base = OBJECT_CLUSTER_DIMENSIONS.get(str(shape_type), (0.52, 0.52, 0.52))
    return tuple(round(float(value) * float(scale), 4) for value in base)


def _make_object_spec(
    *,
    rng: Any,
    object_id: str,
    shape_type: str,
    color_name: str,
    slot: Sequence[float],
    belt_key: str,
    matches_query: bool,
    count_role: str,
    dimension_scale: float,
) -> Dict[str, Any]:
    """Create one countable conveyor carousel object spec."""

    dimensions = _object_dimensions(str(shape_type), scale=float(dimension_scale))
    height = float(dimensions[2])
    color_rgb = SEMANTIC_COLOR_RGB[str(color_name)]
    theta_degrees = float(slot[2])
    return {
        "object_id": str(object_id),
        "object_type": str(shape_type),
        "shape_type": str(shape_type),
        "object_name": public_object_name(str(shape_type)),
        "prompt_name": public_object_name(str(shape_type)),
        "public_name": public_object_name(str(shape_type)),
        "nameable_for_prompt": True,
        "is_countable_object": True,
        "matches_query": bool(matches_query),
        "count_role": str(count_role),
        "belt_key": str(belt_key),
        "belt_label": str(BELT_LABELS[str(belt_key)]),
        "angular_position_degrees": round(float(theta_degrees), 3),
        "color_name": str(color_name),
        "prompt_color_name": str(color_name),
        "fill_rgb": [int(channel) for channel in color_rgb],
        "semantic_color": True,
        "dimensions_xyz": [float(value) for value in dimensions],
        "world_xyz": [round(float(slot[0]), 4), round(float(slot[1]), 4), round(0.08 + height * 0.5, 4)],
        "base_xyz": [round(float(slot[0]), 4), round(float(slot[1]), 4), 0.08],
        "orientation_deg": round(float(theta_degrees + 90.0 + rng.uniform(-18.0, 18.0)), 3),
        "render_order_bias": round(float(rng.uniform(-0.015, 0.015)), 5),
        "renderer_id": "object_scene_shape",
        "object_role": "target" if bool(matches_query) else "distractor",
    }


def _sample_slot(
    slots_by_belt: Dict[str, list[tuple[float, float, float]]],
    *,
    belt_key: str,
) -> tuple[float, float, float]:
    slots = slots_by_belt.get(str(belt_key), [])
    if not slots:
        raise ValueError(f"no free conveyor carousel slots for {belt_key}")
    return slots.pop()


def _sample_other_belt_slot(
    slots_by_belt: Dict[str, list[tuple[float, float, float]]],
    *,
    rng: Any,
    target_belt_key: str,
) -> tuple[str, tuple[float, float, float]]:
    candidates = [
        str(belt_key)
        for belt_key in BELT_KEYS
        if str(belt_key) != str(target_belt_key) and bool(slots_by_belt.get(str(belt_key)))
    ]
    if not candidates:
        raise ValueError("no non-target conveyor carousel slots available")
    belt_key = str(candidates[int(rng.randrange(len(candidates)))])
    return belt_key, _sample_slot(slots_by_belt, belt_key=belt_key)


def _sample_carousel_camera(rng: Any, yaw_band_degrees: Sequence[float]) -> CameraSpec:
    yaw_degrees = float(rng.uniform(float(yaw_band_degrees[0]), float(yaw_band_degrees[1])))
    pitch_degrees = float(rng.uniform(39.0, 50.0))
    distance = float(rng.uniform(7.8, 9.2))
    yaw = math.radians(float(yaw_degrees))
    pitch = math.radians(float(pitch_degrees))
    target = (0.0, 0.0, 0.58)
    camera_position = (
        float(distance * math.cos(pitch) * math.sin(yaw)),
        float(-distance * math.cos(pitch) * math.cos(yaw)),
        float(target[2] + distance * math.sin(pitch)),
    )
    forward = vec_norm(vec_sub(target, camera_position))
    right = vec_norm(vec_cross(forward, (0.0, 0.0, 1.0)))
    up = vec_norm(vec_cross(right, forward))
    return CameraSpec(
        camera_position=tuple(camera_position),
        target=tuple(target),
        right=tuple(right),
        up=tuple(up),
        forward=tuple(forward),
        yaw_degrees=float(yaw_degrees),
        pitch_degrees=float(pitch_degrees),
        distance=float(distance),
    )


def _carousel_reference_points() -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for belt_key in BELT_KEYS:
        width = float(BELT_GEOMETRY[str(belt_key)]["band_width"])
        for angle_index in range(32):
            theta = 2.0 * math.pi * float(angle_index) / 32.0
            for radial_offset in (-0.5 * width, 0.5 * width):
                x, y = _belt_point(str(belt_key), theta, radial_offset=float(radial_offset))
                points.append((float(x), float(y), 0.04))
    points.extend([(0.0, 0.0, 0.04), (0.0, 0.0, 0.62)])
    return points


def _finalize_camera_and_projection(
    *,
    rng: Any,
    render_params: Any,
    object_specs: Sequence[Mapping[str, Any]],
) -> tuple[Any, Any, dict[str, Any], dict[str, Any]]:
    """Sample camera and bind projection metadata for finalized objects."""

    band_index = int(rng.randrange(len(CAMERA_YAW_BANDS_DEGREES)))
    yaw_band = CAMERA_YAW_BANDS_DEGREES[int(band_index)]
    camera = _sample_carousel_camera(rng, yaw_band)
    reference_points = [point for spec in object_specs for point in object_reference_points(spec)]
    frame = build_projection_frame(
        camera=camera,
        render_params=render_params,
        point_worlds=[*_carousel_reference_points(), *reference_points],
    )
    camera_meta = {
        "camera_position": [round(float(value), 4) for value in camera.camera_position],
        "target": [round(float(value), 4) for value in camera.target],
        "yaw_degrees": round(float(camera.yaw_degrees), 4),
        "yaw_band_degrees": [round(float(value), 4) for value in yaw_band],
        "yaw_band_index": int(band_index),
        "pitch_degrees": round(float(camera.pitch_degrees), 4),
        "distance": round(float(camera.distance), 4),
        "right": [round(float(value), 5) for value in camera.right],
        "up": [round(float(value), 5) for value in camera.up],
        "forward": [round(float(value), 5) for value in camera.forward],
    }
    frame_meta = {
        "scale": round(float(frame.scale), 5),
        "center_x": round(float(frame.center_x), 3),
        "center_y": round(float(frame.center_y), 3),
        "normalized_center_u": round(float(frame.normalized_center_u), 6),
        "normalized_center_v": round(float(frame.normalized_center_v), 6),
    }
    return camera, frame, camera_meta, frame_meta


def _screen_finalize_specs(
    *,
    object_specs: Sequence[Mapping[str, Any]],
    camera: Any,
    frame: Any,
) -> list[dict[str, Any]]:
    finalized: list[dict[str, Any]] = []
    for spec in object_specs:
        updated = dict(spec)
        screen = project_screen(updated["world_xyz"], camera, frame)
        updated["screen_xy"] = [round(float(screen[0]), 3), round(float(screen[1]), 3)]
        updated["camera_distance"] = round(float(screen[7]), 5)
        finalized.append(updated)
    return sorted(finalized, key=lambda item: str(item["object_id"]))


def build_belt_count_dataset(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_params: Any,
    axes: ResolvedConveyorAxes,
    predicate_kind: str,
    namespace: str,
) -> dict[str, Any]:
    """Build an elliptical conveyor carousel dataset for one belt-scoped count."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.dataset")
    target_belt_key, target_belt_probabilities = _resolve_target_belt(params=params, rng=rng)
    target_belt_label = str(BELT_LABELS[str(target_belt_key)])
    target_count, target_count_probabilities = resolve_count_for_namespace(
        params,
        namespace=f"{namespace}.target_count",
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        key="target_count",
        default_min=1,
        default_max=8,
        lower=1,
        upper=8,
    )
    object_count_min = _configured_int(params, gen_defaults, "object_count_min", 9)
    object_count_max = _configured_int(params, gen_defaults, "object_count_max", 18)
    total_min = max(int(target_count) + 4, int(object_count_min))
    total_max = max(total_min, int(object_count_max))
    object_count, object_count_probabilities = resolve_count_for_namespace(
        params,
        namespace=f"{namespace}.object_count",
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        key="object_count",
        default_min=total_min,
        default_max=total_max,
        lower=total_min,
        upper=22,
    )
    slots_per_belt = max(14, _configured_int(params, gen_defaults, "slots_per_belt", 20))
    dimension_scale = float(params.get("object_dimension_scale", group_default(gen_defaults, "object_dimension_scale", 0.64)))
    slots_by_belt = {
        str(belt_key): _slot_positions_for_belt(rng=rng, belt_key=str(belt_key), slots_per_belt=int(slots_per_belt))
        for belt_key in BELT_KEYS
    }
    belt_records = [
        {
            "belt_key": str(belt_key),
            "belt_label": str(BELT_LABELS[str(belt_key)]),
            "geometry": dict(BELT_GEOMETRY[str(belt_key)]),
            "slot_count": int(slots_per_belt),
        }
        for belt_key in BELT_KEYS
    ]

    object_specs: List[Dict[str, Any]] = []
    target_object_ids: list[str] = []

    if str(predicate_kind) == PREDICATE_OBJECT_TYPE:
        target_shape, target_shape_probabilities = _resolve_target_shape(params=params, rng=rng)
        active_colors = sample_named_color_palette(rng, palette_size=4)
        color_names = tuple(str(name) for name, _rgb in active_colors)
        if not color_names:
            raise ValueError("empty conveyor visual color palette")
        target_color_name = ""
        target_color_probabilities: Dict[str, float] = {}
        for index in range(int(target_count)):
            slot = _sample_slot(slots_by_belt, belt_key=target_belt_key)
            color_name = str(color_names[index % len(color_names)])
            object_id = f"obj_{len(object_specs):03d}"
            target_object_ids.append(object_id)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=object_id,
                    shape_type=str(target_shape),
                    color_name=color_name,
                    slot=slot,
                    belt_key=target_belt_key,
                    matches_query=True,
                    count_role="target",
                    dimension_scale=float(dimension_scale),
                )
            )
        if slots_by_belt[str(target_belt_key)] and int(target_count) <= 6:
            slot = _sample_slot(slots_by_belt, belt_key=target_belt_key)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=f"obj_{len(object_specs):03d}",
                    shape_type=_sample_shape(rng, CONVEYOR_OBJECT_SHAPE_TYPES, exclude=(target_shape,)),
                    color_name=str(color_names[int(rng.randrange(len(color_names)))]),
                    slot=slot,
                    belt_key=target_belt_key,
                    matches_query=False,
                    count_role="same_belt_distractor",
                    dimension_scale=float(dimension_scale),
                )
            )
        while len(object_specs) < int(object_count):
            belt_key, slot = _sample_other_belt_slot(slots_by_belt, rng=rng, target_belt_key=target_belt_key)
            same_shape_elsewhere = len(object_specs) < int(target_count) + 4 and rng.random() < 0.75
            shape_type = str(target_shape) if same_shape_elsewhere else _sample_shape(rng, CONVEYOR_OBJECT_SHAPE_TYPES)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=f"obj_{len(object_specs):03d}",
                    shape_type=shape_type,
                    color_name=str(color_names[int(rng.randrange(len(color_names)))]),
                    slot=slot,
                    belt_key=belt_key,
                    matches_query=False,
                    count_role="other_belt_distractor",
                    dimension_scale=float(dimension_scale),
                )
            )
        target_prompt_phrase = public_object_plural(str(target_shape))
    elif str(predicate_kind) == PREDICATE_COLOR:
        target_color_name, target_color_probabilities = _resolve_target_color(params=params, rng=rng)
        target_shape = ""
        target_shape_probabilities = {}
        color_names = _sample_readout_palette(rng, target_color=str(target_color_name), size=4)
        for _index in range(int(target_count)):
            slot = _sample_slot(slots_by_belt, belt_key=target_belt_key)
            object_id = f"obj_{len(object_specs):03d}"
            target_object_ids.append(object_id)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=object_id,
                    shape_type=_sample_shape(rng, CONVEYOR_COLOR_READOUT_SHAPE_TYPES),
                    color_name=str(target_color_name),
                    slot=slot,
                    belt_key=target_belt_key,
                    matches_query=True,
                    count_role="target",
                    dimension_scale=float(dimension_scale),
                )
            )
        if slots_by_belt[str(target_belt_key)] and int(target_count) <= 6:
            wrong_colors = [color for color in color_names if str(color) != str(target_color_name)]
            slot = _sample_slot(slots_by_belt, belt_key=target_belt_key)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=f"obj_{len(object_specs):03d}",
                    shape_type=_sample_shape(rng, CONVEYOR_COLOR_READOUT_SHAPE_TYPES),
                    color_name=str(wrong_colors[int(rng.randrange(len(wrong_colors)))]),
                    slot=slot,
                    belt_key=target_belt_key,
                    matches_query=False,
                    count_role="same_belt_distractor",
                    dimension_scale=float(dimension_scale),
                )
            )
        while len(object_specs) < int(object_count):
            belt_key, slot = _sample_other_belt_slot(slots_by_belt, rng=rng, target_belt_key=target_belt_key)
            same_color_elsewhere = len(object_specs) < int(target_count) + 4 and rng.random() < 0.75
            color_name = str(target_color_name) if same_color_elsewhere else str(color_names[int(rng.randrange(len(color_names)))])
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=f"obj_{len(object_specs):03d}",
                    shape_type=_sample_shape(rng, CONVEYOR_COLOR_READOUT_SHAPE_TYPES),
                    color_name=color_name,
                    slot=slot,
                    belt_key=belt_key,
                    matches_query=False,
                    count_role="other_belt_distractor",
                    dimension_scale=float(dimension_scale),
                )
            )
        target_prompt_phrase = str(target_color_name)
    else:
        raise ValueError(f"unsupported conveyor predicate kind: {predicate_kind}")

    camera, frame, camera_meta, frame_meta = _finalize_camera_and_projection(
        rng=rng,
        render_params=render_params,
        object_specs=object_specs,
    )
    finalized_specs = _screen_finalize_specs(object_specs=object_specs, camera=camera, frame=frame)
    shape_counts = Counter(str(spec["shape_type"]) for spec in finalized_specs)
    color_counts = Counter(str(spec["color_name"]) for spec in finalized_specs)
    belt_counts = Counter(str(spec["belt_key"]) for spec in finalized_specs)
    target_belt_object_ids = [
        str(spec["object_id"])
        for spec in finalized_specs
        if str(spec["belt_key"]) == str(target_belt_key)
    ]
    return {
        "scene_id": SCENE_ID,
        "scene_variant": str(axes.scene_variant),
        "layout_family": "elliptical_carousel",
        "predicate_kind": str(predicate_kind),
        "belt_records": [dict(record) for record in belt_records],
        "target_belt_key": str(target_belt_key),
        "target_belt_label": str(target_belt_label),
        "target_shape_type": str(target_shape),
        "target_object_name": public_object_name(str(target_shape)) if target_shape else "",
        "target_object_plural": public_object_plural(str(target_shape)) if target_shape else "",
        "target_color_name": str(target_color_name),
        "target_prompt_phrase": str(target_prompt_phrase),
        "answer_value": int(target_count),
        "target_count": int(target_count),
        "target_object_ids": list(target_object_ids),
        "target_belt_object_ids": list(target_belt_object_ids),
        "object_count": int(len(finalized_specs)),
        "object_specs": [dict(spec) for spec in finalized_specs],
        "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
        "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
        "belt_counts": {str(key): int(value) for key, value in sorted(belt_counts.items())},
        "target_shape_type_probabilities": dict(target_shape_probabilities),
        "target_color_name_probabilities": dict(target_color_probabilities),
        "target_count_probabilities": dict(target_count_probabilities),
        "object_count_probabilities": dict(object_count_probabilities),
        "target_belt_probabilities": dict(target_belt_probabilities),
        "semantic_color_palette": {str(key): list(value) for key, value in sorted(SEMANTIC_COLOR_RGB.items())},
        "camera": dict(camera_meta),
        "projection_frame": dict(frame_meta),
        "solver_trace": {
            "count_predicate": str(predicate_kind),
            "scope": {
                "belt_key": str(target_belt_key),
                "belt_label": str(target_belt_label),
            },
            "target_shape_type": str(target_shape),
            "target_color_name": str(target_color_name),
            "target_count": int(target_count),
            "target_object_ids": list(target_object_ids),
            "target_belt_object_ids": list(target_belt_object_ids),
            "answer_value": int(target_count),
            "unique_integer_answer": True,
        },
    }


__all__ = [
    "PREDICATE_COLOR",
    "PREDICATE_OBJECT_TYPE",
    "ResolvedConveyorAxes",
    "build_belt_count_dataset",
    "resolve_conveyor_axes",
]
