"""Sampling helpers for conveyor sorting scene axes and object layouts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.named_colors import sample_named_color_palette
from trace.tasks.three_d.shared.camera_projection import (
    build_projection_frame,
    project_screen,
    sample_camera,
)
from trace.tasks.three_d.shared.object_resources import OBJECT_CLUSTER_DIMENSIONS
from trace.tasks.three_d.shared.projected_object_geometry import object_reference_points
from trace.tasks.three_d.shared.task_support import (
    resolve_axis_variant_for_namespace,
    resolve_count_for_namespace,
)

from .state import (
    COLOR_CONFUSION_EXCLUSIONS,
    CONVEYOR_COLOR_READOUT_SHAPE_TYPES,
    CONVEYOR_OBJECT_SHAPE_TYPES,
    LANE_COUNT_BY_SCENE_VARIANT,
    LANE_LABELS,
    SCENE_ID,
    SEGMENT_KEYS,
    SEGMENT_LABELS,
    SEMANTIC_COLOR_RGB,
    SEMANTIC_COLOR_SUPPORT,
    SUPPORTED_SCENE_VARIANTS,
    public_object_name,
    public_object_plural,
)


PREDICATE_OBJECT_TYPE = "object_type"
PREDICATE_COLOR = "color"

CAMERA_YAW_BANDS_DEGREES: Tuple[Tuple[float, float], ...] = (
    (-70.0, -48.0),
    (48.0, 70.0),
    (-132.0, -112.0),
    (112.0, 132.0),
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


def _uniform_int_probability_map(values: Sequence[int], *, selected: int | None = None) -> Dict[str, float]:
    support = tuple(int(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in support}
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
    """Resolve the conveyor station scene variant."""

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


def _segment_ranges() -> Dict[str, Tuple[float, float]]:
    x0, x1 = -2.88, 2.88
    segment_width = (x1 - x0) / 3.0
    return {
        str(segment): (x0 + index * segment_width, x0 + (index + 1) * segment_width)
        for index, segment in enumerate(SEGMENT_KEYS)
    }


def _lane_y_positions(lane_count: int) -> list[float]:
    if int(lane_count) == 1:
        return [0.0]
    if int(lane_count) == 2:
        return [-0.62, 0.62]
    return [-1.06, 0.0, 1.06]


def _slot_positions_for_cell(
    *,
    rng: Any,
    lane_index: int,
    segment_key: str,
    lane_y: float,
) -> list[tuple[float, float]]:
    x0, x1 = _segment_ranges()[str(segment_key)]
    slots: list[tuple[float, float]] = []
    for row_index, y_offset in enumerate((-0.23, 0.23)):
        for col_index in range(4):
            fraction = (col_index + 0.5) / 4.0
            x = float(x0 + fraction * (x1 - x0) + rng.uniform(-0.09, 0.09))
            y = float(lane_y + y_offset + rng.uniform(-0.045, 0.045))
            slots.append((round(x, 4), round(y, 4)))
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
    xy: Sequence[float],
    lane_index: int,
    lane_label: str,
    segment_key: str,
    segment_label: str,
    matches_query: bool,
    count_role: str,
    dimension_scale: float,
) -> Dict[str, Any]:
    """Create one countable conveyor object spec.

    Invariant: scene-local placement metadata, semantic target membership, and
    shared object-rendering fields are bound in one record before projection so
    answer, annotation, and trace all refer to the same object identity.
    """

    dimensions = _object_dimensions(str(shape_type), scale=float(dimension_scale))
    height = float(dimensions[2])
    color_rgb = SEMANTIC_COLOR_RGB[str(color_name)]
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
        "lane_index": int(lane_index),
        "lane_label": str(lane_label),
        "segment_key": str(segment_key),
        "segment_label": str(segment_label),
        "color_name": str(color_name),
        "prompt_color_name": str(color_name),
        "fill_rgb": [int(channel) for channel in color_rgb],
        "semantic_color": True,
        "dimensions_xyz": [float(value) for value in dimensions],
        "world_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), round(0.08 + height * 0.5, 4)],
        "base_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), 0.08],
        "orientation_deg": round(float(rng.uniform(-15.0, 15.0)), 3),
        "render_order_bias": round(float(rng.uniform(-0.015, 0.015)), 5),
        "renderer_id": "object_scene_shape",
        "object_role": "target" if bool(matches_query) else "distractor",
    }


def _sample_slot(
    slots_by_cell: Dict[tuple[int, str], list[tuple[float, float]]],
    *,
    rng: Any,
    lane_index: int,
    segment_key: str,
) -> tuple[float, float]:
    key = (int(lane_index), str(segment_key))
    slots = slots_by_cell.get(key, [])
    if not slots:
        raise ValueError(f"no free conveyor slots for {key}")
    return slots.pop()


def _sample_other_cell(
    *,
    rng: Any,
    lane_count: int,
    target_lane_index: int,
    target_segment_key: str,
    slots_by_cell: Mapping[tuple[int, str], Sequence[tuple[float, float]]],
) -> tuple[int, str]:
    candidates = [
        (lane_index, segment_key)
        for lane_index in range(int(lane_count))
        for segment_key in SEGMENT_KEYS
        if (lane_index != int(target_lane_index) or str(segment_key) != str(target_segment_key))
        and bool(slots_by_cell.get((lane_index, str(segment_key))))
    ]
    if not candidates:
        raise ValueError("no non-target conveyor slots available")
    return candidates[int(rng.randrange(len(candidates)))]


def _finalize_camera_and_projection(
    *,
    rng: Any,
    render_params: Any,
    object_specs: Sequence[Mapping[str, Any]],
) -> tuple[Any, Any, dict[str, Any], dict[str, Any]]:
    """Sample camera and bind projection metadata for finalized objects.

    The conveyor grammar is world-space first: belt geometry and object specs
    are fixed before camera projection, then all object screen centers are
    derived from this single camera/frame pair.
    """

    band_index = int(rng.randrange(len(CAMERA_YAW_BANDS_DEGREES)))
    yaw_band = CAMERA_YAW_BANDS_DEGREES[int(band_index)]
    camera = sample_camera(rng, yaw_band_degrees=yaw_band)
    belt_corners = [
        (x, y, 0.02)
        for x in (-3.05, 3.05)
        for y in (-1.55, 1.55)
    ]
    reference_points = [point for spec in object_specs for point in object_reference_points(spec)]
    frame = build_projection_frame(
        camera=camera,
        render_params=render_params,
        point_worlds=[*belt_corners, *reference_points],
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


def build_segment_count_dataset(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_params: Any,
    axes: ResolvedConveyorAxes,
    predicate_kind: str,
    namespace: str,
) -> dict[str, Any]:
    """Build a conveyor station dataset for one scoped segment count objective.

    Public query ids are owned by the task module. Shared sampling only receives
    the semantic predicate family needed to build the objective program.
    """

    rng = spawn_rng(int(instance_seed), f"{namespace}.dataset")
    lane_count = int(LANE_COUNT_BY_SCENE_VARIANT[str(axes.scene_variant)])
    lane_positions = _lane_y_positions(int(lane_count))
    target_lane_index = int(params.get("target_lane_index", rng.randrange(int(lane_count))))
    if target_lane_index < 0 or target_lane_index >= int(lane_count):
        raise ValueError(f"unsupported target_lane_index: {target_lane_index}")
    target_segment_key = str(params.get("target_segment_key", SEGMENT_KEYS[int(rng.randrange(len(SEGMENT_KEYS)))]))
    if target_segment_key not in set(SEGMENT_KEYS):
        raise ValueError(f"unsupported target_segment_key: {target_segment_key}")
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
    object_count_min = _configured_int(params, gen_defaults, "object_count_min", 8)
    object_count_max = _configured_int(params, gen_defaults, "object_count_max", 18)
    total_min = max(int(target_count) + 3, int(object_count_min))
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
        upper=24,
    )
    dimension_scale = float(params.get("object_dimension_scale", group_default(gen_defaults, "object_dimension_scale", 0.64)))

    slots_by_cell: Dict[tuple[int, str], list[tuple[float, float]]] = {}
    lane_records: list[dict[str, Any]] = []
    segment_records: list[dict[str, Any]] = []
    for lane_index, lane_y in enumerate(lane_positions):
        lane_label = LANE_LABELS[int(lane_index)]
        lane_records.append({"lane_index": int(lane_index), "lane_label": str(lane_label), "center_y": round(float(lane_y), 4)})
        for segment_key in SEGMENT_KEYS:
            slots_by_cell[(lane_index, str(segment_key))] = _slot_positions_for_cell(
                rng=rng,
                lane_index=int(lane_index),
                segment_key=str(segment_key),
                lane_y=float(lane_y),
            )
            x0, x1 = _segment_ranges()[str(segment_key)]
            segment_records.append(
                {
                    "lane_index": int(lane_index),
                    "lane_label": str(lane_label),
                    "segment_key": str(segment_key),
                    "segment_label": str(SEGMENT_LABELS[str(segment_key)]),
                    "world_bbox_xy": [round(float(x0), 4), round(float(lane_y - 0.47), 4), round(float(x1), 4), round(float(lane_y + 0.47), 4)],
                }
            )

    target_lane_label = LANE_LABELS[int(target_lane_index)]
    target_segment_label = SEGMENT_LABELS[str(target_segment_key)]
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
            xy = _sample_slot(slots_by_cell, rng=rng, lane_index=target_lane_index, segment_key=target_segment_key)
            color_name = str(color_names[index % len(color_names)])
            object_id = f"obj_{len(object_specs):03d}"
            target_object_ids.append(object_id)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=object_id,
                    shape_type=str(target_shape),
                    color_name=color_name,
                    xy=xy,
                    lane_index=target_lane_index,
                    lane_label=target_lane_label,
                    segment_key=target_segment_key,
                    segment_label=target_segment_label,
                    matches_query=True,
                    count_role="target",
                    dimension_scale=float(dimension_scale),
                )
            )
        if slots_by_cell[(target_lane_index, target_segment_key)] and int(target_count) <= 6:
            xy = _sample_slot(slots_by_cell, rng=rng, lane_index=target_lane_index, segment_key=target_segment_key)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=f"obj_{len(object_specs):03d}",
                    shape_type=_sample_shape(rng, CONVEYOR_OBJECT_SHAPE_TYPES, exclude=(target_shape,)),
                    color_name=str(color_names[int(rng.randrange(len(color_names)))]),
                    xy=xy,
                    lane_index=target_lane_index,
                    lane_label=target_lane_label,
                    segment_key=target_segment_key,
                    segment_label=target_segment_label,
                    matches_query=False,
                    count_role="same_segment_distractor",
                    dimension_scale=float(dimension_scale),
                )
            )
        while len(object_specs) < int(object_count):
            lane_index, segment_key = _sample_other_cell(
                rng=rng,
                lane_count=lane_count,
                target_lane_index=target_lane_index,
                target_segment_key=target_segment_key,
                slots_by_cell=slots_by_cell,
            )
            same_shape_elsewhere = len(object_specs) < int(target_count) + 3 and rng.random() < 0.75
            shape_type = str(target_shape) if same_shape_elsewhere else _sample_shape(rng, CONVEYOR_OBJECT_SHAPE_TYPES, exclude=())
            xy = _sample_slot(slots_by_cell, rng=rng, lane_index=lane_index, segment_key=segment_key)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=f"obj_{len(object_specs):03d}",
                    shape_type=shape_type,
                    color_name=str(color_names[int(rng.randrange(len(color_names)))]),
                    xy=xy,
                    lane_index=lane_index,
                    lane_label=LANE_LABELS[int(lane_index)],
                    segment_key=segment_key,
                    segment_label=SEGMENT_LABELS[str(segment_key)],
                    matches_query=False,
                    count_role="outside_scope_distractor",
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
            xy = _sample_slot(slots_by_cell, rng=rng, lane_index=target_lane_index, segment_key=target_segment_key)
            object_id = f"obj_{len(object_specs):03d}"
            target_object_ids.append(object_id)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=object_id,
                    shape_type=_sample_shape(rng, CONVEYOR_COLOR_READOUT_SHAPE_TYPES),
                    color_name=str(target_color_name),
                    xy=xy,
                    lane_index=target_lane_index,
                    lane_label=target_lane_label,
                    segment_key=target_segment_key,
                    segment_label=target_segment_label,
                    matches_query=True,
                    count_role="target",
                    dimension_scale=float(dimension_scale),
                )
            )
        if slots_by_cell[(target_lane_index, target_segment_key)] and int(target_count) <= 6:
            wrong_colors = [color for color in color_names if str(color) != str(target_color_name)]
            xy = _sample_slot(slots_by_cell, rng=rng, lane_index=target_lane_index, segment_key=target_segment_key)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=f"obj_{len(object_specs):03d}",
                    shape_type=_sample_shape(rng, CONVEYOR_COLOR_READOUT_SHAPE_TYPES),
                    color_name=str(wrong_colors[int(rng.randrange(len(wrong_colors)))]),
                    xy=xy,
                    lane_index=target_lane_index,
                    lane_label=target_lane_label,
                    segment_key=target_segment_key,
                    segment_label=target_segment_label,
                    matches_query=False,
                    count_role="same_segment_distractor",
                    dimension_scale=float(dimension_scale),
                )
            )
        while len(object_specs) < int(object_count):
            lane_index, segment_key = _sample_other_cell(
                rng=rng,
                lane_count=lane_count,
                target_lane_index=target_lane_index,
                target_segment_key=target_segment_key,
                slots_by_cell=slots_by_cell,
            )
            same_color_elsewhere = len(object_specs) < int(target_count) + 3 and rng.random() < 0.75
            color_name = str(target_color_name) if same_color_elsewhere else str(color_names[int(rng.randrange(len(color_names)))])
            xy = _sample_slot(slots_by_cell, rng=rng, lane_index=lane_index, segment_key=segment_key)
            object_specs.append(
                _make_object_spec(
                    rng=rng,
                    object_id=f"obj_{len(object_specs):03d}",
                    shape_type=_sample_shape(rng, CONVEYOR_COLOR_READOUT_SHAPE_TYPES),
                    color_name=color_name,
                    xy=xy,
                    lane_index=lane_index,
                    lane_label=LANE_LABELS[int(lane_index)],
                    segment_key=segment_key,
                    segment_label=SEGMENT_LABELS[str(segment_key)],
                    matches_query=False,
                    count_role="outside_scope_distractor",
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
    segment_counts = Counter(f"{spec['lane_label']}:{spec['segment_key']}" for spec in finalized_specs)

    target_segment_object_ids = [
        str(spec["object_id"])
        for spec in finalized_specs
        if int(spec["lane_index"]) == int(target_lane_index) and str(spec["segment_key"]) == str(target_segment_key)
    ]
    return {
        "scene_id": SCENE_ID,
        "scene_variant": str(axes.scene_variant),
        "predicate_kind": str(predicate_kind),
        "lane_count": int(lane_count),
        "lane_records": [dict(record) for record in lane_records],
        "segment_records": [dict(record) for record in segment_records],
        "target_lane_index": int(target_lane_index),
        "target_lane_label": str(target_lane_label),
        "target_segment_key": str(target_segment_key),
        "target_segment_label": str(target_segment_label),
        "target_shape_type": str(target_shape),
        "target_object_name": public_object_name(str(target_shape)) if target_shape else "",
        "target_object_plural": public_object_plural(str(target_shape)) if target_shape else "",
        "target_color_name": str(target_color_name),
        "target_prompt_phrase": str(target_prompt_phrase),
        "answer_value": int(target_count),
        "target_count": int(target_count),
        "target_object_ids": list(target_object_ids),
        "target_segment_object_ids": list(target_segment_object_ids),
        "object_count": int(len(finalized_specs)),
        "object_specs": [dict(spec) for spec in finalized_specs],
        "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
        "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
        "segment_counts": {str(key): int(value) for key, value in sorted(segment_counts.items())},
        "target_shape_type_probabilities": dict(target_shape_probabilities),
        "target_color_name_probabilities": dict(target_color_probabilities),
        "target_count_probabilities": dict(target_count_probabilities),
        "object_count_probabilities": dict(object_count_probabilities),
        "lane_count_probabilities": _uniform_int_probability_map(
            tuple(LANE_COUNT_BY_SCENE_VARIANT.values()),
            selected=int(lane_count),
        ),
        "target_lane_probabilities": _uniform_string_probability_map(LANE_LABELS[: int(lane_count)]),
        "target_segment_probabilities": _uniform_string_probability_map(SEGMENT_KEYS),
        "semantic_color_palette": {str(key): list(value) for key, value in sorted(SEMANTIC_COLOR_RGB.items())},
        "camera": dict(camera_meta),
        "projection_frame": dict(frame_meta),
        "solver_trace": {
            "count_predicate": str(predicate_kind),
            "scope": {
                "lane_label": str(target_lane_label),
                "segment_key": str(target_segment_key),
                "segment_label": str(target_segment_label),
            },
            "target_shape_type": str(target_shape),
            "target_color_name": str(target_color_name),
            "target_count": int(target_count),
            "target_object_ids": list(target_object_ids),
            "target_segment_object_ids": list(target_segment_object_ids),
            "answer_value": int(target_count),
            "unique_integer_answer": True,
        },
    }


__all__ = [
    "PREDICATE_COLOR",
    "PREDICATE_OBJECT_TYPE",
    "ResolvedConveyorAxes",
    "build_segment_count_dataset",
    "resolve_conveyor_axes",
]
