"""Object placement and projection dataset assembly for dense clusters."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.three_d.shared.color_variation import resolve_three_d_object_fill_rgb
from trace.tasks.three_d.shared.object_scene import (
    CONTEXT_OBJECT_COLORS,
    ObjectSceneRenderParams,
    _bbox_intersection_area,
    _build_projection_frame,
    _camera_yaw_band_for_instance,
    _make_object_spec,
    _min_pairwise,
    _object_reference_points,
    _object_screen_bbox,
    _project_screen,
    _sample_camera,
)

from .defaults import (
    CLUSTER_DIMENSION_SCALE,
    MAX_PAIRWISE_OVERLAP_FRACTION,
    MAX_PAIRWISE_OVERLAP_PX,
    MAX_RENDERED_PAIRWISE_OVERLAP_FRACTION,
    MAX_RENDERED_PAIRWISE_OVERLAP_PX,
    MIN_PROJECTED_OBJECT_AREA_PX,
    PLACEMENT_FOOTPRINT_SEPARATION_FACTOR,
    PROMPT_COLOR_RGB,
    cluster_dimensions,
    object_name_for_shape,
)
from .state import ClusterSequenceItem


def scale_dimensions(dimensions_xyz: Sequence[float], scale: float) -> Tuple[float, float, float]:
    """Scale one resource footprint for dense-cluster placement."""

    return tuple(round(float(value) * float(scale), 4) for value in dimensions_xyz)  # type: ignore[return-value]


def bbox_area(bbox: Sequence[float]) -> float:
    """Return the pixel area of one projected object box."""

    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def bbox_is_readable(
    bbox: Sequence[float],
    *,
    width: int,
    height: int,
    min_side_px: float = 12.0,
) -> bool:
    """Check that a projected object remains visible inside the canvas."""

    box_width = float(bbox[2]) - float(bbox[0])
    box_height = float(bbox[3]) - float(bbox[1])
    if box_width < float(min_side_px) or box_height < float(min_side_px):
        return False
    return float(bbox[2]) > 4.0 and float(bbox[3]) > 4.0 and float(bbox[0]) < float(width - 4) and float(bbox[1]) < float(height - 4)


def sample_scaled_dimensions(*, rng, shape_type: str) -> Tuple[Tuple[float, float, float], float]:
    """Sample small per-instance scale while preserving object-resource proportions."""

    base = cluster_dimensions(str(shape_type))
    scale = float(rng.uniform(0.84, 1.12)) * float(CLUSTER_DIMENSION_SCALE)
    return scale_dimensions(base, scale), round(float(scale), 4)


def make_cluster_object(
    *,
    rng,
    object_id: str,
    item: ClusterSequenceItem,
    xy: Tuple[float, float],
) -> Dict[str, Any]:
    """Create a renderable object spec from a semantic count item."""

    dimensions_xyz, dimension_scale = sample_scaled_dimensions(rng=rng, shape_type=str(item.shape_type))
    object_name = object_name_for_shape(str(item.shape_type))
    spec = _make_object_spec(
        object_id=str(object_id),
        shape_type=str(item.shape_type),
        object_role="candidate",
        xy=tuple(float(value) for value in xy),
        dimensions_xyz=dimensions_xyz,
        dimension_scale=float(dimension_scale),
        label=None,
    )
    color_name = str(item.color_name)
    fill_rgb = (
        [int(channel) for channel in PROMPT_COLOR_RGB[color_name]]
        if color_name in PROMPT_COLOR_RGB
        else [
            int(channel)
            for channel in resolve_three_d_object_fill_rgb(
                spec,
                palette=CONTEXT_OBJECT_COLORS,
                salt="object_cluster.semantic_fill",
                variation_strength=0.34,
            )
        ]
    )
    spec.update(
        {
            "object_name": str(object_name),
            "prompt_name": str(object_name),
            "nameable_for_prompt": True,
            "is_answer_candidate": False,
            "is_countable_object": True,
            "matches_query": bool(item.matches_query),
            "count_role": str(item.count_role),
            "color_name": str(color_name),
            "prompt_color_name": str(color_name),
            "fill_rgb": list(fill_rgb),
            "semantic_color": color_name in PROMPT_COLOR_RGB,
        }
    )
    return spec


def sample_cluster_xy(rng, *, cluster_radius: float, y_scale: float) -> Tuple[float, float]:
    """Sample an elliptical dense-cluster floor coordinate."""

    angle = float(rng.uniform(0.0, 2.0 * math.pi))
    radius = float(rng.random() ** 0.64) * float(cluster_radius)
    return (
        float(radius * math.cos(angle) + rng.uniform(-0.12, 0.12)),
        float(radius * math.sin(angle) * float(y_scale) + rng.uniform(-0.10, 0.10)),
    )


def can_place_cluster(candidate: Mapping[str, Any], placed: Sequence[Mapping[str, Any]]) -> bool:
    """Check floor-space separation before camera projection."""

    cx, cy, _cz = (float(value) for value in candidate["world_xyz"])
    for item in placed:
        ix, iy, _iz = (float(value) for value in item["world_xyz"])
        min_distance = float(PLACEMENT_FOOTPRINT_SEPARATION_FACTOR) * (
            float(candidate["footprint_radius"]) + float(item["footprint_radius"])
        )
        if math.hypot(float(cx - ix), float(cy - iy)) < float(min_distance):
            return False
    return True


def place_cluster_objects(
    *,
    rng,
    sequence: Sequence[ClusterSequenceItem],
    scene_variant: str,
) -> List[Dict[str, Any]]:
    """Place every semantic object item into a dense but separable 3D cluster."""

    cluster_radius = {"tabletop_pile": 2.96, "shallow_tray": 2.78, "cluster_mat": 3.12}.get(str(scene_variant), 2.96)
    y_scale = {"tabletop_pile": 0.88, "shallow_tray": 0.82, "cluster_mat": 0.94}.get(str(scene_variant), 0.88)
    placed: List[Dict[str, Any]] = []
    for index, item in enumerate(sequence):
        for _ in range(360):
            candidate = make_cluster_object(
                rng=rng,
                object_id=f"cluster_object_{int(index):02d}",
                item=item,
                xy=sample_cluster_xy(rng, cluster_radius=float(cluster_radius), y_scale=float(y_scale)),
            )
            if can_place_cluster(candidate, placed):
                candidate["render_order_bias"] = round(float(rng.uniform(-0.035, 0.035)), 5)
                placed.append(candidate)
                break
        else:
            raise ValueError("could not place enough clustered 3D objects")
    return list(placed)


def finalize_specs(
    specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
) -> List[Dict[str, Any]]:
    """Attach projected screen and camera coordinates to object specs."""

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


def view_is_valid(
    *,
    specs: Sequence[Mapping[str, Any]],
    camera,
    frame,
    render_params: ObjectSceneRenderParams,
) -> bool:
    """Validate projection readability and cap pairwise object occlusion."""

    bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=5.0) for spec in specs]
    if any(
        not bbox_is_readable(
            bbox,
            width=int(render_params.canvas_width),
            height=int(render_params.canvas_height),
        )
        for bbox in bboxes
    ):
        return False
    if any(bbox_area(bbox) < MIN_PROJECTED_OBJECT_AREA_PX for bbox in bboxes):
        return False
    for index, bbox_a in enumerate(bboxes):
        area_a = bbox_area(bbox_a)
        for bbox_b in bboxes[index + 1 :]:
            overlap = _bbox_intersection_area(bbox_a, bbox_b)
            if overlap > MAX_PAIRWISE_OVERLAP_PX:
                return False
            if overlap > float(MAX_PAIRWISE_OVERLAP_FRACTION) * min(area_a, bbox_area(bbox_b)):
                return False
    return True


def rendered_bboxes_are_valid(
    object_bboxes_px: Mapping[str, Sequence[float]],
    *,
    width: int,
    height: int,
) -> bool:
    """Validate the final rendered object boxes that reviewers actually inspect."""

    bboxes = [list(bbox) for bbox in object_bboxes_px.values()]
    if any(
        not bbox_is_readable(
            bbox,
            width=int(width),
            height=int(height),
        )
        for bbox in bboxes
    ):
        return False
    for index, bbox_a in enumerate(bboxes):
        area_a = bbox_area(bbox_a)
        for bbox_b in bboxes[index + 1 :]:
            overlap = _bbox_intersection_area(bbox_a, bbox_b)
            if overlap > float(MAX_RENDERED_PAIRWISE_OVERLAP_PX):
                return False
            if overlap > float(MAX_RENDERED_PAIRWISE_OVERLAP_FRACTION) * min(area_a, bbox_area(bbox_b)):
                return False
    return True


def camera_record(camera, *, yaw_band: Sequence[float]) -> Dict[str, Any]:
    """Serialize camera vectors and angles for deterministic trace replay."""

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


def frame_record(frame) -> Dict[str, Any]:
    """Serialize projection-frame parameters for deterministic trace replay."""

    return {
        "scale": round(float(frame.scale), 5),
        "center_x": round(float(frame.center_x), 3),
        "center_y": round(float(frame.center_y), 3),
        "normalized_center_u": round(float(frame.normalized_center_u), 6),
        "normalized_center_v": round(float(frame.normalized_center_v), 6),
    }


def build_dataset_from_sequence(
    *,
    source_namespace: str,
    scene_kind: str,
    prompt_query_key: str,
    scene_variant: str,
    render_params: ObjectSceneRenderParams,
    instance_seed: int,
    sequence: Sequence[ClusterSequenceItem],
    target_spec: Mapping[str, Any],
    answer_value: int,
    expected_annotation_count: int,
    extra_trace: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Project one semantic object sequence into a valid rendered dataset."""

    rng = spawn_rng(int(instance_seed), f"{source_namespace}.dataset")
    selected_camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
    for _attempt in range(720):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        object_specs = place_cluster_objects(rng=rng, sequence=sequence, scene_variant=str(scene_variant))
        reference_points = [point for spec in object_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not view_is_valid(specs=object_specs, camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_specs = finalize_specs(object_specs, camera=camera, frame=frame)
        target_specs = [spec for spec in finalized_specs if bool(spec.get("matches_query", False))]
        if len(target_specs) != int(expected_annotation_count):
            continue

        distances = [float(spec["camera_distance"]) for spec in finalized_specs]
        shape_counts = Counter(str(spec["shape_type"]) for spec in finalized_specs)
        color_counts = Counter(str(spec["color_name"]) for spec in finalized_specs)
        property_counts = Counter((str(spec["shape_type"]), str(spec["color_name"])) for spec in finalized_specs)
        count_role_counts = Counter(str(spec["count_role"]) for spec in finalized_specs)
        target_object_ids = [str(spec["object_id"]) for spec in sorted(target_specs, key=lambda item: str(item["object_id"]))]
        role_object_ids: Dict[str, List[str]] = {}
        for spec in sorted(finalized_specs, key=lambda item: str(item["object_id"])):
            role = str(spec.get("count_role", ""))
            if role:
                role_object_ids.setdefault(role, []).append(str(spec["object_id"]))
        trace_extra = dict(extra_trace or {})
        dataset_target_spec = dict(target_spec)
        return {
            "scene_kind": str(scene_kind),
            "query_key": str(prompt_query_key),
            "scene_variant": str(scene_variant),
            "object_count": len(finalized_specs),
            "countable_object_count": len(finalized_specs),
            "target_count": int(expected_annotation_count),
            "answer_value": int(answer_value),
            "target_spec": dict(dataset_target_spec),
            "target_shape_type": dataset_target_spec.get("target_shape_type"),
            "target_shape_types": list(dataset_target_spec.get("target_shape_types", [])),
            "target_object_name": dataset_target_spec.get("target_object_name"),
            "target_object_plural": dataset_target_spec.get("target_object_plural"),
            "target_object_union_phrase": dataset_target_spec.get("target_object_union_phrase"),
            "target_color_name": dataset_target_spec.get("target_color_name"),
            "target_color_names": list(dataset_target_spec.get("target_color_names", [])),
            "singleton_shape_types": list(dataset_target_spec.get("singleton_shape_types", [])),
            "left_operand_phrase": dataset_target_spec.get("left_operand_phrase"),
            "right_operand_phrase": dataset_target_spec.get("right_operand_phrase"),
            "arithmetic_operation": dataset_target_spec.get("arithmetic_operation"),
            "target_property_phrase": str(dataset_target_spec.get("target_property_phrase", "counted objects")),
            "target_object_ids": list(target_object_ids),
            "counted_object_ids": list(trace_extra.get("counted_object_ids", target_object_ids)),
            "role_object_ids": {str(role): list(ids) for role, ids in sorted(role_object_ids.items())},
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
            "camera": camera_record(camera, yaw_band=selected_camera_yaw_band),
            "projection_frame": frame_record(frame),
            "solver_trace": {
                "count_predicate": str(dataset_target_spec.get("mode", "object_cluster_count")),
                "target_spec": dict(dataset_target_spec),
                "target_property_phrase": str(dataset_target_spec.get("target_property_phrase", "counted objects")),
                "target_count": int(expected_annotation_count),
                "answer_value": int(answer_value),
                "target_object_ids": list(target_object_ids),
                "role_object_ids": {str(role): list(ids) for role, ids in sorted(role_object_ids.items())},
                "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
                "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
                "property_counts": {
                    f"{color_name}_{shape_type}": int(count)
                    for (shape_type, color_name), count in sorted(property_counts.items())
                },
                "count_role_counts": {str(key): int(value) for key, value in sorted(count_role_counts.items())},
                "semantic_color_palette": {str(key): list(value) for key, value in sorted(PROMPT_COLOR_RGB.items())},
                "unique_integer_answer": True,
                "minimum_pairwise_camera_distance_margin": round(float(_min_pairwise(distances)), 4),
                **trace_extra,
            },
            **trace_extra,
        }
    raise ValueError("could not construct a valid 3D object-cluster dataset")


__all__ = [
    "build_dataset_from_sequence",
    "rendered_bboxes_are_valid",
]
