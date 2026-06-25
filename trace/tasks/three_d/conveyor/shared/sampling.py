"""Sampling helpers for straight 3D conveyor belt scenes."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.three_d.shared.camera_projection import (
    CameraSpec,
    build_projection_frame,
    project_screen,
    vec_cross,
    vec_norm,
    vec_sub,
)
from trace.tasks.three_d.shared.projected_object_geometry import object_reference_points
from trace.tasks.three_d.shared.task_support import (
    resolve_axis_variant_for_namespace,
    resolve_count_for_namespace,
)

from .state import (
    CONVEYOR_OBJECT_SHAPE_TYPES,
    HORIZONTAL_LANE_KEYS,
    LANE_LABELS,
    SCENE_ID,
    SEMANTIC_COLOR_RGB,
    SUPPORTED_SCENE_VARIANTS,
    VERTICAL_LANE_KEYS,
    object_dimensions,
    public_object_name,
    public_object_plural,
    sample_visual_color_names,
)


PREDICATE_BELT_TOTAL = "belt_total"
LAYOUT_HORIZONTAL = "horizontal_lanes"
LAYOUT_VERTICAL = "vertical_lanes"


@dataclass(frozen=True)
class ResolvedConveyorAxes:
    """Resolved straight conveyor scene axes for one generated instance."""

    scene_variant: str
    scene_variant_probabilities: Dict[str, float]


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / float(max(1, len(support)))
    return {str(value): float(probability) for value in support}


def resolve_conveyor_axes(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> ResolvedConveyorAxes:
    """Resolve the straight conveyor scene variant."""

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


def _resolve_layout_orientation(
    *,
    params: Mapping[str, Any],
    rng: Any,
    render_params: Any,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("layout_orientation")
    support = (LAYOUT_HORIZONTAL, LAYOUT_VERTICAL)
    if explicit is not None:
        orientation = str(explicit)
        if orientation not in set(support):
            raise ValueError(f"unsupported layout_orientation: {orientation}")
        return orientation, _uniform_string_probability_map(support, selected=orientation)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    if width > height:
        return LAYOUT_HORIZONTAL, {LAYOUT_HORIZONTAL: 1.0, LAYOUT_VERTICAL: 0.0}
    if height > width:
        return LAYOUT_VERTICAL, {LAYOUT_HORIZONTAL: 0.0, LAYOUT_VERTICAL: 1.0}
    orientation = str(support[int(rng.randrange(len(support)))])
    return orientation, _uniform_string_probability_map(support)


def _lane_keys_for_orientation(layout_orientation: str) -> Tuple[str, ...]:
    return HORIZONTAL_LANE_KEYS if str(layout_orientation) == LAYOUT_HORIZONTAL else VERTICAL_LANE_KEYS


def _resolve_target_lane(
    *,
    params: Mapping[str, Any],
    rng: Any,
    lane_keys: Sequence[str],
) -> tuple[str, Dict[str, float]]:
    support = tuple(str(key) for key in lane_keys)
    explicit = params.get("target_lane_key", params.get("target_belt_key"))
    if explicit is not None:
        lane_key = str(explicit)
        if lane_key not in set(support):
            raise ValueError(f"unsupported target_lane_key for layout: {lane_key}")
        return lane_key, _uniform_string_probability_map(support, selected=lane_key)
    lane_key = str(support[int(rng.randrange(len(support)))])
    return lane_key, _uniform_string_probability_map(support)


def _resolve_shape(*, params: Mapping[str, Any], rng: Any) -> tuple[str, Dict[str, float]]:
    support = tuple(str(shape) for shape in CONVEYOR_OBJECT_SHAPE_TYPES)
    explicit = params.get("target_shape_type")
    if explicit is not None:
        shape = str(explicit)
        if shape not in set(support):
            raise ValueError(f"unsupported target_shape_type: {shape}")
        return shape, _uniform_string_probability_map(support, selected=shape)
    shape = str(support[int(rng.randrange(len(support)))])
    return shape, _uniform_string_probability_map(support)


def _resolve_lane_count(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    key: str,
) -> tuple[int, Dict[str, float]]:
    count, probabilities = resolve_count_for_namespace(
        params,
        namespace=str(namespace),
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        key=str(key),
        default_min=1,
        default_max=8,
        lower=1,
        upper=8,
    )
    return int(count), dict(probabilities)


def _lane_center_value(layout_orientation: str, lane_key: str) -> float:
    if str(layout_orientation) == LAYOUT_HORIZONTAL:
        return {"top": 1.55, "middle": 0.0, "bottom": -1.55}[str(lane_key)]
    return {"left": -2.25, "middle": 0.0, "right": 2.25}[str(lane_key)]


def _lane_records(layout_orientation: str) -> list[dict[str, Any]]:
    lane_keys = _lane_keys_for_orientation(str(layout_orientation))
    records: list[dict[str, Any]] = []
    for lane_key in lane_keys:
        records.append(
            {
                "lane_key": str(lane_key),
                "lane_label": str(LANE_LABELS[str(lane_key)]),
                "layout_orientation": str(layout_orientation),
                "center_value": float(_lane_center_value(str(layout_orientation), str(lane_key))),
                "max_count": 8,
            }
        )
    return records


def _slot_positions_for_lane(
    *,
    rng: Any,
    layout_orientation: str,
    lane_key: str,
    count: int,
) -> list[tuple[float, float, float]]:
    count = int(count)
    if count <= 0:
        return []
    center = _lane_center_value(str(layout_orientation), str(lane_key))
    slots: list[tuple[float, float, float]] = []
    if str(layout_orientation) == LAYOUT_HORIZONTAL:
        length = 6.15
        spacing = length / float(max(1, count))
        start = -0.5 * length + 0.5 * spacing
        for index in range(count):
            x = start + spacing * float(index) + rng.uniform(-0.13, 0.13)
            y = center + rng.uniform(-0.10, 0.10)
            slots.append((round(float(x), 4), round(float(y), 4), 0.0))
    else:
        length = 5.15
        spacing = length / float(max(1, count))
        start = -0.5 * length + 0.5 * spacing
        for index in range(count):
            x = center + rng.uniform(-0.10, 0.10)
            y = start + spacing * float(index) + rng.uniform(-0.13, 0.13)
            slots.append((round(float(x), 4), round(float(y), 4), 90.0))
    rng.shuffle(slots)
    return slots


def _make_object_spec(
    *,
    rng: Any,
    object_id: str,
    shape_type: str,
    color_name: str,
    lane_key: str,
    layout_orientation: str,
    slot: Sequence[float],
    matches_query: bool,
    count_role: str,
    dimension_scale: float,
) -> Dict[str, Any]:
    """Create one countable lane object bound to metadata and projection.

    The lane key, prompt-facing belt label, semantic color, and world position
    are all recorded here so answer filtering and annotation projection use the
    same finalized object record.
    """

    dimensions = object_dimensions(str(shape_type), scale=float(dimension_scale))
    height = float(dimensions[2])
    color_rgb = SEMANTIC_COLOR_RGB[str(color_name)]
    orientation_base = float(slot[2])
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
        "lane_key": str(lane_key),
        "lane_label": str(LANE_LABELS[str(lane_key)]),
        "belt_key": str(lane_key),
        "belt_label": str(LANE_LABELS[str(lane_key)]),
        "layout_orientation": str(layout_orientation),
        "color_name": str(color_name),
        "prompt_color_name": str(color_name),
        "fill_rgb": [int(channel) for channel in color_rgb],
        "semantic_color": True,
        "dimensions_xyz": [float(value) for value in dimensions],
        "world_xyz": [round(float(slot[0]), 4), round(float(slot[1]), 4), round(0.08 + height * 0.5, 4)],
        "base_xyz": [round(float(slot[0]), 4), round(float(slot[1]), 4), 0.08],
        "orientation_deg": round(float(orientation_base + rng.uniform(-15.0, 15.0)), 3),
        "render_order_bias": round(float(rng.uniform(-0.015, 0.015)), 5),
        "renderer_id": "object_scene_shape",
        "object_role": "target" if bool(matches_query) else "distractor",
    }


def _sample_line_camera(rng: Any) -> CameraSpec:
    yaw_degrees = float(rng.uniform(-4.0, 4.0))
    pitch_degrees = float(rng.uniform(53.0, 59.0))
    distance = float(rng.uniform(8.0, 8.8))
    yaw = math.radians(float(yaw_degrees))
    pitch = math.radians(float(pitch_degrees))
    target = (0.0, 0.0, 0.42)
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


def _lane_reference_points(layout_orientation: str) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    half_width = 0.33
    if str(layout_orientation) == LAYOUT_HORIZONTAL:
        x0, x1 = -3.45, 3.45
        for lane_key in HORIZONTAL_LANE_KEYS:
            y = _lane_center_value(str(layout_orientation), str(lane_key))
            points.extend([(x0, y - half_width, 0.02), (x0, y + half_width, 0.02), (x1, y - half_width, 0.02), (x1, y + half_width, 0.02)])
    else:
        y0, y1 = -2.95, 2.95
        for lane_key in VERTICAL_LANE_KEYS:
            x = _lane_center_value(str(layout_orientation), str(lane_key))
            points.extend([(x - half_width, y0, 0.02), (x + half_width, y0, 0.02), (x - half_width, y1, 0.02), (x + half_width, y1, 0.02)])
    return points


def _finalize_camera_and_projection(
    *,
    rng: Any,
    render_params: Any,
    layout_orientation: str,
    object_specs: Sequence[Mapping[str, Any]],
) -> tuple[CameraSpec, Any, dict[str, Any], dict[str, Any]]:
    camera = _sample_line_camera(rng)
    reference_points = [point for spec in object_specs for point in object_reference_points(spec)]
    frame = build_projection_frame(
        camera=camera,
        render_params=render_params,
        point_worlds=[*_lane_reference_points(str(layout_orientation)), *reference_points],
    )
    camera_meta = {
        "camera_position": [round(float(value), 4) for value in camera.camera_position],
        "target": [round(float(value), 4) for value in camera.target],
        "yaw_degrees": round(float(camera.yaw_degrees), 4),
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
    camera: CameraSpec,
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


def build_belt_total_count_dataset(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_params: Any,
    axes: ResolvedConveyorAxes,
    namespace: str,
) -> dict[str, Any]:
    """Build a straight three-lane conveyor dataset for one lane-total count."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.dataset")
    layout_orientation, layout_orientation_probabilities = _resolve_layout_orientation(
        params=params,
        rng=rng,
        render_params=render_params,
    )
    lane_keys = _lane_keys_for_orientation(str(layout_orientation))
    target_lane_key, target_lane_probabilities = _resolve_target_lane(params=params, rng=rng, lane_keys=lane_keys)
    target_lane_label = str(LANE_LABELS[str(target_lane_key)])
    target_count, target_count_probabilities = _resolve_lane_count(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.{target_lane_key}.target_count",
        key="target_count",
    )
    target_shape, target_shape_probabilities = _resolve_shape(params=params, rng=rng)
    color_names = sample_visual_color_names(rng, palette_size=4)
    if not color_names:
        raise ValueError("empty conveyor visual color palette")
    dimension_scale = float(params.get("object_dimension_scale", group_default(gen_defaults, "object_dimension_scale", 0.66)))

    lane_counts: Dict[str, int] = {}
    lane_count_probabilities: Dict[str, Dict[str, float]] = {}
    for lane_key in lane_keys:
        if str(lane_key) == str(target_lane_key):
            lane_counts[str(lane_key)] = int(target_count)
            lane_count_probabilities[str(lane_key)] = dict(target_count_probabilities)
        else:
            count, probabilities = _resolve_lane_count(
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                namespace=f"{namespace}.{lane_key}.distractor_count",
                key=f"{lane_key}_object_count",
            )
            lane_counts[str(lane_key)] = int(count)
            lane_count_probabilities[str(lane_key)] = dict(probabilities)

    object_specs: List[Dict[str, Any]] = []
    target_object_ids: list[str] = []
    for lane_key in lane_keys:
        slots = _slot_positions_for_lane(
            rng=rng,
            layout_orientation=str(layout_orientation),
            lane_key=str(lane_key),
            count=int(lane_counts[str(lane_key)]),
        )
        for index, slot in enumerate(slots):
            object_id = f"obj_{len(object_specs):03d}"
            matches_query = str(lane_key) == str(target_lane_key)
            if matches_query:
                target_object_ids.append(str(object_id))
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=str(object_id),
                    shape_type=str(target_shape),
                    color_name=str(color_names[(index + len(object_specs)) % len(color_names)]),
                    lane_key=str(lane_key),
                    layout_orientation=str(layout_orientation),
                    slot=slot,
                    matches_query=bool(matches_query),
                    count_role="target" if matches_query else "lane_distractor",
                    dimension_scale=float(dimension_scale),
                )
            )

    camera, frame, camera_meta, frame_meta = _finalize_camera_and_projection(
        rng=rng,
        render_params=render_params,
        layout_orientation=str(layout_orientation),
        object_specs=object_specs,
    )
    finalized_specs = _screen_finalize_specs(object_specs=object_specs, camera=camera, frame=frame)
    shape_counts = Counter(str(spec["shape_type"]) for spec in finalized_specs)
    color_counts = Counter(str(spec["color_name"]) for spec in finalized_specs)
    lane_counts_final = Counter(str(spec["lane_key"]) for spec in finalized_specs)
    target_lane_object_ids = [
        str(spec["object_id"])
        for spec in finalized_specs
        if str(spec["lane_key"]) == str(target_lane_key)
    ]
    return {
        "scene_id": SCENE_ID,
        "scene_variant": str(axes.scene_variant),
        "layout_family": "straight_parallel_conveyors",
        "layout_orientation": str(layout_orientation),
        "layout_orientation_probabilities": dict(layout_orientation_probabilities),
        "predicate_kind": PREDICATE_BELT_TOTAL,
        "lane_records": _lane_records(str(layout_orientation)),
        "target_lane_key": str(target_lane_key),
        "target_lane_label": str(target_lane_label),
        "target_belt_key": str(target_lane_key),
        "target_belt_label": str(target_lane_label),
        "target_shape_type": str(target_shape),
        "target_object_name": public_object_name(str(target_shape)),
        "target_object_plural": public_object_plural(str(target_shape)),
        "answer_value": int(target_count),
        "target_count": int(target_count),
        "target_object_ids": list(target_object_ids),
        "target_lane_object_ids": list(target_lane_object_ids),
        "target_belt_object_ids": list(target_lane_object_ids),
        "object_count": int(len(finalized_specs)),
        "object_specs": [dict(spec) for spec in finalized_specs],
        "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
        "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
        "lane_counts": {str(key): int(value) for key, value in sorted(lane_counts_final.items())},
        "belt_counts": {str(key): int(value) for key, value in sorted(lane_counts_final.items())},
        "target_shape_type_probabilities": dict(target_shape_probabilities),
        "target_count_probabilities": dict(target_count_probabilities),
        "lane_count_probabilities": {str(key): dict(value) for key, value in lane_count_probabilities.items()},
        "target_lane_key_probabilities": dict(target_lane_probabilities),
        "target_belt_key_probabilities": dict(target_lane_probabilities),
        "target_belt_probabilities": dict(target_lane_probabilities),
        "semantic_color_palette": {str(key): list(value) for key, value in sorted(SEMANTIC_COLOR_RGB.items())},
        "camera": dict(camera_meta),
        "projection_frame": dict(frame_meta),
        "solver_trace": {
            "count_predicate": PREDICATE_BELT_TOTAL,
            "scope": {
                "lane_key": str(target_lane_key),
                "lane_label": str(target_lane_label),
            },
            "target_shape_type": str(target_shape),
            "target_count": int(target_count),
            "target_object_ids": list(target_object_ids),
            "target_lane_object_ids": list(target_lane_object_ids),
            "answer_value": int(target_count),
            "unique_integer_answer": True,
        },
    }


__all__ = [
    "LAYOUT_HORIZONTAL",
    "LAYOUT_VERTICAL",
    "PREDICATE_BELT_TOTAL",
    "ResolvedConveyorAxes",
    "build_belt_total_count_dataset",
    "resolve_conveyor_axes",
]
