"""Shelf-level item counting task for a synthetic 3D warehouse scene."""

from __future__ import annotations

from collections import Counter
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
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.named_colors import sample_named_color_palette
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.object_scene import (
    _CameraSpec,
    _ProjectionFrame,
    _bbox_intersection_area,
    _build_projection_frame,
    _canvas_floor_polygon_xy,
    _object_reference_points,
    _object_screen_bbox,
    _sample_camera,
)
from ..shared.object_resources import WAREHOUSE_SHELF_LOAD_COLORS
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import resolve_count as _shared_resolve_count
from .warehouse_scene_common import (
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    WAREHOUSE_CAMERA_YAW_BANDS_DEGREES,
    _WarehouseRenderParams,
    _bbox_area,
    _dimensions_for_object,
    _finalize_specs,
    _heading_axis,
    _heading_vector,
    _local_to_world,
    _make_object_spec,
    _resolve_render_params,
)
from .warehouse_shelf_rendering import render_warehouse_shelf_level_count_scene_3d


TASK_ID = "task_three_d__warehouse__scoped_attribute_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "top_shelf_item_count",
    "middle_shelf_item_count",
    "bottom_shelf_item_count",
)
SUPPORTED_AISLE_HEADINGS: Tuple[str, ...] = ("east", "north", "west", "south")
SHELF_LEVELS_BY_QUERY_ID: Dict[str, Tuple[str, int]] = {
    "bottom_shelf_item_count": ("bottom", 0),
    "middle_shelf_item_count": ("middle", 1),
    "top_shelf_item_count": ("top", 2),
}
SHELF_LEVEL_NAMES: Tuple[str, ...] = ("bottom", "middle", "top")
SHELF_LEVEL_FRACS: Tuple[float, float, float] = (0.18, 0.52, 0.84)
SHELF_ITEM_TYPE = "storage_bin"
MIN_RACK_VISIBLE_SIDE_PX = 34.0
MIN_ITEM_VISIBLE_SIDE_PX = 11.0
MIN_TARGET_ITEM_VISIBLE_SIDE_PX = 13.0
MAX_ITEM_OVERLAP_RATIO = 0.34


def _hex_color(rgb: Sequence[int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _color_label(color_name: str, rgb: Sequence[int]) -> str:
    return f"{color_name} [{_hex_color(rgb)}]"


def _resolve_camera_yaw_band(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[Tuple[float, float], Dict[str, float], int]:
    support = tuple(range(len(WAREHOUSE_CAMERA_YAW_BANDS_DEGREES)))
    explicit = params.get("camera_yaw_band_index")
    locked = params.get("_locked_camera_yaw_band_index")
    if explicit is not None:
        selected = int(explicit)
    elif locked is not None:
        selected = int(locked)
    else:
        selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.camera_yaw_band_index")
        selected = int(support[abs(int(selection_index)) % len(support)])
    if int(selected) not in set(support):
        raise ValueError(f"unsupported camera_yaw_band_index: {selected}")
    probabilities = dict(uniform_probability_map(support, selected=int(selected) if explicit is not None else None))
    return (
        tuple(float(value) for value in WAREHOUSE_CAMERA_YAW_BANDS_DEGREES[int(selected)]),
        {str(key): float(value) for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))},
        int(selected),
    )


def _uniform_string_probability_map(support: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    if not support:
        return {}
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = round(1.0 / float(len(support)), 8)
    return {str(value): float(probability) for value in support}


def _select_target_rack_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    rack_count: int,
) -> Tuple[int, Dict[str, float]]:
    support = tuple(range(int(rack_count)))
    explicit = params.get("target_rack_index")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported target_rack_index: {selected}")
        return int(selected), dict(uniform_probability_map(support, selected=int(selected)))
    selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.target_rack_index")
    selected = int(support[abs(int(selection_index)) % len(support)])
    return int(selected), dict(uniform_probability_map(support))


def _rack_zone_polygon(spec: Mapping[str, Any], *, pad_xy: float = 0.10) -> List[Tuple[float, float, float]]:
    x, y, _z = (float(value) for value in spec["base_xyz"])
    width, depth, _height = (float(value) for value in spec["dimensions_xyz"])
    half_width = width * 0.5 + float(pad_xy)
    half_depth = depth * 0.5 + float(pad_xy)
    return [
        (round(x - half_width, 4), round(y - half_depth, 4), 0.018),
        (round(x + half_width, 4), round(y - half_depth, 4), 0.018),
        (round(x + half_width, 4), round(y + half_depth, 4), 0.018),
        (round(x - half_width, 4), round(y + half_depth, 4), 0.018),
    ]


def _make_main_aisle_polygon(
    *,
    origin_xy: Sequence[float],
    forward_xy: Sequence[float],
    start_s: float,
    end_s: float,
    half_width: float,
) -> List[Tuple[float, float, float]]:
    fx, fy = float(forward_xy[0]), float(forward_xy[1])
    lx, ly = -fy, fx
    ox, oy = float(origin_xy[0]), float(origin_xy[1])
    return [
        (round(ox + fx * start_s + lx * half_width, 4), round(oy + fy * start_s + ly * half_width, 4), 0.02),
        (round(ox + fx * end_s + lx * half_width, 4), round(oy + fy * end_s + ly * half_width, 4), 0.02),
        (round(ox + fx * end_s - lx * half_width, 4), round(oy + fy * end_s - ly * half_width, 4), 0.02),
        (round(ox + fx * start_s - lx * half_width, 4), round(oy + fy * start_s - ly * half_width, 4), 0.02),
    ]


def _make_shelf_item_spec(
    *,
    rng,
    object_id: str,
    rack_spec: Mapping[str, Any],
    shelf_level_name: str,
    shelf_level_index: int,
    item_index: int,
    item_count_on_level: int,
    matches_query: bool,
    orientation_axis: str,
) -> Dict[str, Any]:
    rack_x, rack_y, _rack_z = (float(value) for value in rack_spec["base_xyz"])
    rack_width, rack_depth, rack_height = (float(value) for value in rack_spec["dimensions_xyz"])
    width_axis_span = rack_width if str(orientation_axis) == "x" else rack_depth
    depth_axis_span = rack_depth if str(orientation_axis) == "x" else rack_width
    slot_span = max(0.30, float(width_axis_span) * 0.74)
    if int(item_count_on_level) <= 1:
        along_width = float(rng.uniform(-0.10, 0.10)) * slot_span
    else:
        fraction = (float(item_index) + 0.5) / float(item_count_on_level)
        along_width = -0.5 * slot_span + fraction * slot_span + float(rng.uniform(-0.018, 0.018))
    along_depth = float(rng.uniform(-0.14, 0.14)) * float(depth_axis_span)
    if str(orientation_axis) == "x":
        xy = (rack_x + along_width, rack_y + along_depth)
        dimensions = (
            round(float(rng.uniform(0.30, 0.40)), 4),
            round(float(rng.uniform(0.20, 0.28)), 4),
            round(float(rng.uniform(0.20, 0.28)), 4),
        )
    else:
        xy = (rack_x + along_depth, rack_y + along_width)
        dimensions = (
            round(float(rng.uniform(0.20, 0.28)), 4),
            round(float(rng.uniform(0.30, 0.40)), 4),
            round(float(rng.uniform(0.20, 0.28)), 4),
        )
    beam_height = float(rack_spec.get("shelf_beam_height", 0.09))
    level_frac = float(SHELF_LEVEL_FRACS[int(shelf_level_index)])
    base_z = min(float(rack_height) - float(dimensions[2]) - 0.01, float(rack_height) * level_frac + beam_height * 0.44)
    base_z = max(0.04, float(base_z))
    spec = _make_object_spec(
        object_id=str(object_id),
        object_type=SHELF_ITEM_TYPE,
        object_role="warehouse_shelf_item",
        xy=(round(float(xy[0]), 4), round(float(xy[1]), 4)),
        orientation_axis=str(orientation_axis),
        dimensions_xyz=tuple(float(value) for value in dimensions),
        dimension_scale=1.0,
        label=None,
    )
    color = WAREHOUSE_SHELF_LOAD_COLORS[int(rng.randrange(len(WAREHOUSE_SHELF_LOAD_COLORS)))]
    spec.update(
        {
            "base_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(base_z), 4)],
            "world_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(base_z + float(dimensions[2]) * 0.5), 4)],
            "object_name": "shelf item",
            "prompt_name": "shelf item",
            "rack_id": str(rack_spec["object_id"]),
            "rack_color_name": str(rack_spec["rack_color_name"]),
            "rack_color_label": str(rack_spec["rack_color_label"]),
            "shelf_level": str(shelf_level_name),
            "shelf_level_index": int(shelf_level_index),
            "is_countable_object": True,
            "is_answer_candidate": False,
            "matches_query": bool(matches_query),
            "count_role": "target" if bool(matches_query) else "distractor",
            "fill_rgb": [int(channel) for channel in color],
        }
    )
    return dict(spec)


def _world_point_trace(point: Sequence[float]) -> List[float]:
    return [round(float(value), 4) for value in point]


def _world_polygon_trace(polygon: Sequence[Sequence[float]]) -> List[List[float]]:
    return [_world_point_trace(point) for point in polygon]


def _sample_racks_and_items(
    *,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    aisle_heading: str,
    rack_count: int,
    target_count: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    shelf_level_name, shelf_level_index = SHELF_LEVELS_BY_QUERY_ID[str(query_id)]
    target_rack_index, target_rack_probabilities = _select_target_rack_index(
        params=params,
        instance_seed=int(instance_seed),
        rack_count=int(rack_count),
    )
    forward_xy = _heading_vector(str(aisle_heading))
    orientation_axis = _heading_axis(str(aisle_heading))
    origin_xy = (float(rng.uniform(-0.12, 0.12)), float(rng.uniform(-0.12, 0.12)))
    rack_slots = [
        (-1.72, -1.34),
        (1.92, -1.34),
        (-1.72, 1.34),
        (1.92, 1.34),
    ]
    rng.shuffle(rack_slots)
    rack_colors = sample_named_color_palette(rng, palette_size=int(rack_count))
    if len(rack_colors) < int(rack_count):
        raise ValueError("not enough distinct named colors for warehouse racks")
    rack_specs: List[Dict[str, Any]] = []
    for rack_index, (forward_s, lateral_l) in enumerate(rack_slots[: int(rack_count)]):
        xy = _local_to_world(
            forward_s=float(forward_s + rng.uniform(-0.08, 0.08)),
            lateral_l=float(lateral_l + rng.uniform(-0.08, 0.08)),
            origin_xy=origin_xy,
            forward_xy=forward_xy,
        )
        scale = float(rng.uniform(1.08, 1.22))
        base_width, base_depth, base_height = _dimensions_for_object("shelf_rack", orientation_axis=str(orientation_axis), scale=scale)
        dimensions = (round(float(base_width), 4), round(float(base_depth * 1.04), 4), round(float(base_height * rng.uniform(1.02, 1.12)), 4))
        color_name, color_rgb = rack_colors[int(rack_index)]
        rack_spec = _make_object_spec(
            object_id=f"warehouse_shelf_rack_{rack_index}",
            object_type="shelf_rack",
            object_role="warehouse_shelf_rack",
            xy=xy,
            orientation_axis=str(orientation_axis),
            dimensions_xyz=dimensions,
            dimension_scale=float(scale),
            label=None,
        )
        rack_spec.update(
            {
                "rack_index": int(rack_index),
                "rack_color_name": str(color_name),
                "rack_color_label": _color_label(str(color_name), color_rgb),
                "is_target_rack": bool(int(rack_index) == int(target_rack_index)),
                "shelf_style": "open_frame",
                "shelf_height_scale": round(float(dimensions[2] / max(1e-6, base_height)), 4),
                "shelf_level_fracs": [round(float(value), 4) for value in SHELF_LEVEL_FRACS],
                "shelf_levels": 3,
                "shelf_level_names": list(SHELF_LEVEL_NAMES),
                "shelf_beam_height": round(float(rng.uniform(0.080, 0.105)), 4),
                "shelf_post_width": round(float(rng.uniform(0.070, 0.095)), 4),
                "shelf_frame_rgb": [int(channel) for channel in color_rgb],
                "shelf_load_slots": [],
            }
        )
        rack_specs.append(rack_spec)

    item_specs: List[Dict[str, Any]] = []
    shelf_counts_by_rack_level: Dict[str, Dict[str, int]] = {}
    for rack_index, rack_spec in enumerate(rack_specs):
        rack_counts: Dict[str, int] = {}
        for level_index, level_name in enumerate(SHELF_LEVEL_NAMES):
            if int(rack_index) == int(target_rack_index) and int(level_index) == int(shelf_level_index):
                item_count = int(target_count)
            elif int(level_index) == int(shelf_level_index):
                item_count = int(rng.randint(1, 4))
            else:
                item_count = int(rng.randint(0, 4))
            rack_counts[str(level_name)] = int(item_count)
            for item_index in range(int(item_count)):
                matches_query = int(rack_index) == int(target_rack_index) and int(level_index) == int(shelf_level_index)
                item_specs.append(
                    _make_shelf_item_spec(
                        rng=rng,
                        object_id=f"rack_{rack_index}_{level_name}_item_{item_index}",
                        rack_spec=rack_spec,
                        shelf_level_name=str(level_name),
                        shelf_level_index=int(level_index),
                        item_index=int(item_index),
                        item_count_on_level=int(item_count),
                        matches_query=bool(matches_query),
                        orientation_axis=str(orientation_axis),
                    )
                )
        shelf_counts_by_rack_level[str(rack_spec["object_id"])] = dict(rack_counts)

    target_rack = rack_specs[int(target_rack_index)]
    geometry = {
        "origin_xy": [round(float(value), 4) for value in origin_xy],
        "forward_xy": [round(float(value), 4) for value in forward_xy],
        "orientation_axis": str(orientation_axis),
        "target_rack_index": int(target_rack_index),
        "target_rack_index_probabilities": {str(key): float(value) for key, value in sorted(target_rack_probabilities.items(), key=lambda item: int(item[0]))},
        "target_rack_id": str(target_rack["object_id"]),
        "target_rack_color_name": str(target_rack["rack_color_name"]),
        "target_rack_color_label": str(target_rack["rack_color_label"]),
        "target_rack_rgb": list(target_rack["shelf_frame_rgb"]),
        "target_shelf_level": str(shelf_level_name),
        "target_shelf_level_index": int(shelf_level_index),
        "shelf_counts_by_rack_level": dict(shelf_counts_by_rack_level),
        "main_aisle_polygon_world": _world_polygon_trace(
            _make_main_aisle_polygon(
                origin_xy=origin_xy,
                forward_xy=forward_xy,
                start_s=-3.70,
                end_s=3.92,
                half_width=0.98,
            )
        ),
        "rack_zone_polygons_world": [_world_polygon_trace(_rack_zone_polygon(spec)) for spec in rack_specs],
    }
    return list(rack_specs), list(item_specs), dict(geometry)


def _visible_bbox_ok(
    bbox: Sequence[float],
    *,
    render_params: _WarehouseRenderParams,
    min_side_px: float,
    margin_px: float = 4.0,
) -> bool:
    width = float(bbox[2]) - float(bbox[0])
    height = float(bbox[3]) - float(bbox[1])
    if width < float(min_side_px) or height < float(min_side_px):
        return False
    return (
        float(bbox[0]) >= -float(margin_px)
        and float(bbox[1]) >= -float(margin_px)
        and float(bbox[2]) <= float(render_params.canvas_width) + float(margin_px)
        and float(bbox[3]) <= float(render_params.canvas_height) + float(margin_px)
    )


def _visibility_ok(
    rack_specs: Sequence[Mapping[str, Any]],
    item_specs: Sequence[Mapping[str, Any]],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    render_params: _WarehouseRenderParams,
) -> bool:
    for rack in rack_specs:
        rack_bbox = _object_screen_bbox(rack, camera, frame, pad_px=8.0)
        if not _visible_bbox_ok(rack_bbox, render_params=render_params, min_side_px=MIN_RACK_VISIBLE_SIDE_PX, margin_px=20.0):
            return False
    item_bboxes: List[Tuple[Mapping[str, Any], List[float]]] = []
    for item in item_specs:
        bbox = _object_screen_bbox(item, camera, frame, pad_px=3.0)
        min_side = MIN_TARGET_ITEM_VISIBLE_SIDE_PX if bool(item.get("matches_query", False)) else MIN_ITEM_VISIBLE_SIDE_PX
        if not _visible_bbox_ok(bbox, render_params=render_params, min_side_px=min_side, margin_px=10.0):
            return False
        item_bboxes.append((item, bbox))
    for index, (item, bbox) in enumerate(item_bboxes):
        if not bool(item.get("matches_query", False)):
            continue
        area = max(1.0, _bbox_area(bbox))
        for other, other_bbox in item_bboxes[index + 1 :]:
            if str(other.get("rack_id")) != str(item.get("rack_id")) or str(other.get("shelf_level")) != str(item.get("shelf_level")):
                continue
            overlap_ratio = _bbox_intersection_area(bbox, other_bbox) / area
            if overlap_ratio > MAX_ITEM_OVERLAP_RATIO:
                return False
    return True


def _build_dataset(
    *,
    params: Mapping[str, Any],
    query_id: str,
    scene_variant: str,
    aisle_heading: str,
    rack_count: int,
    target_count: int,
    camera_yaw_band: Tuple[float, float],
    camera_yaw_band_index: int,
    render_params: _WarehouseRenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    for _attempt in range(520):
        camera = _sample_camera(rng, yaw_band_degrees=tuple(float(value) for value in camera_yaw_band))
        rack_specs, item_specs, scene_geometry = _sample_racks_and_items(
            rng=rng,
            params=params,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            aisle_heading=str(aisle_heading),
            rack_count=int(rack_count),
            target_count=int(target_count),
        )
        reference_points: List[Tuple[float, float, float]] = []
        for spec in [*rack_specs, *item_specs]:
            reference_points.extend(_object_reference_points(spec))
        reference_points.extend(tuple(float(value) for value in point) for point in scene_geometry["main_aisle_polygon_world"])
        for polygon in scene_geometry["rack_zone_polygons_world"]:
            reference_points.extend(tuple(float(value) for value in point) for point in polygon)
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_racks = _finalize_specs(rack_specs, camera=camera, frame=frame)
        finalized_items = _finalize_specs(item_specs, camera=camera, frame=frame)
        if not _visibility_ok(finalized_racks, finalized_items, camera=camera, frame=frame, render_params=render_params):
            continue
        target_item_specs = [spec for spec in finalized_items if bool(spec.get("matches_query", False))]
        if len(target_item_specs) != int(target_count):
            continue
        target_item_ids = [str(spec["object_id"]) for spec in sorted(target_item_specs, key=lambda item: str(item["object_id"]))]
        item_counts_by_level = Counter(str(spec["shelf_level"]) for spec in finalized_items)
        rack_colors = {
            str(spec["object_id"]): {
                "color_name": str(spec["rack_color_name"]),
                "color_label": str(spec["rack_color_label"]),
                "rgb": list(spec["shelf_frame_rgb"]),
            }
            for spec in finalized_racks
        }
        item_projected_bboxes = {
            str(spec["object_id"]): [round(float(value), 3) for value in _object_screen_bbox(spec, camera, frame, pad_px=0.0)]
            for spec in finalized_items
        }
        object_type_counts = Counter(str(spec["object_type"]) for spec in [*finalized_racks, *finalized_items])
        return {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "aisle_heading": str(aisle_heading),
            "rack_count": int(rack_count),
            "target_count": int(target_count),
            "answer_value": int(target_count),
            "target_rack_id": str(scene_geometry["target_rack_id"]),
            "target_rack_color_name": str(scene_geometry["target_rack_color_name"]),
            "target_rack_color_label": str(scene_geometry["target_rack_color_label"]),
            "target_rack_rgb": list(scene_geometry["target_rack_rgb"]),
            "target_shelf_level": str(scene_geometry["target_shelf_level"]),
            "target_shelf_level_index": int(scene_geometry["target_shelf_level_index"]),
            "target_item_ids": list(target_item_ids),
            "target_object_ids": list(target_item_ids),
            "rack_specs": sorted(finalized_racks, key=lambda spec: str(spec["object_id"])),
            "shelf_item_specs": sorted(finalized_items, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted([*finalized_racks, *finalized_items], key=lambda spec: str(spec["object_id"])),
            "rack_colors": dict(sorted(rack_colors.items())),
            "shelf_counts_by_rack_level": dict(scene_geometry["shelf_counts_by_rack_level"]),
            "item_counts_by_level": dict(sorted(item_counts_by_level.items())),
            "main_aisle_polygon_world": list(scene_geometry["main_aisle_polygon_world"]),
            "rack_zone_polygons_world": list(scene_geometry["rack_zone_polygons_world"]),
            "origin_xy": list(scene_geometry["origin_xy"]),
            "forward_xy": list(scene_geometry["forward_xy"]),
            "orientation_axis": str(scene_geometry["orientation_axis"]),
            "target_rack_index": int(scene_geometry["target_rack_index"]),
            "target_rack_index_probabilities": dict(scene_geometry["target_rack_index_probabilities"]),
            "item_projected_bboxes": dict(sorted(item_projected_bboxes.items())),
            "object_type_counts": dict(sorted(object_type_counts.items())),
            "object_count": int(len(finalized_racks) + len(finalized_items)),
            "camera": {
                "camera_position": [round(float(value), 4) for value in camera.camera_position],
                "target": [round(float(value), 4) for value in camera.target],
                "yaw_degrees": round(float(camera.yaw_degrees), 4),
                "yaw_band_index": int(camera_yaw_band_index),
                "yaw_band_degrees": [round(float(value), 4) for value in camera_yaw_band],
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
                "predicate": "shelf items on the queried shelf level of the queried colored rack",
                "target_rack_id": str(scene_geometry["target_rack_id"]),
                "target_rack_color_label": str(scene_geometry["target_rack_color_label"]),
                "target_shelf_level": str(scene_geometry["target_shelf_level"]),
                "target_item_ids": list(target_item_ids),
                "answer_value": int(target_count),
                "unique_answer": True,
            },
        }
    raise ValueError("could not construct a visible warehouse shelf-count scene")




_TASK_GROUP_DEFAULTS = get_scene_defaults("three_d", "warehouse")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


def _build_retry_locked_params(instance_seed: int, params: Mapping[str, Any]) -> Dict[str, Any]:
    locked_params = dict(params)
    query_id, _query_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
        allow_locked=True,
    )
    scene_variant, _scene_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
        allow_locked=True,
    )
    aisle_heading, _heading_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_AISLE_HEADINGS,
        explicit_key="aisle_heading",
        weights_key="aisle_heading_weights",
        balance_flag_key="balanced_aisle_heading_sampling",
        axis_namespace="aisle_heading",
        allow_locked=True,
    )
    rack_count, _rack_probabilities = _shared_resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="rack_count",
        default_min=2,
        default_max=4,
        lower=2,
        upper=4,
        allow_locked=True,
    )
    target_count, _target_probabilities = _shared_resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="target_count",
        default_min=0,
        default_max=5,
        lower=0,
        upper=5,
        allow_locked=True,
    )
    _camera_yaw_band, _camera_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(params=params, instance_seed=int(instance_seed))
    locked_params.update(
        {
            "_locked_query_id": str(query_id),
            "_locked_scene_variant": str(scene_variant),
            "_locked_aisle_heading": str(aisle_heading),
            "_locked_rack_count": int(rack_count),
            "_locked_target_count": int(target_count),
            "_locked_camera_yaw_band_index": int(camera_yaw_band_index),
        }
    )
    return locked_params


@register_task
class ThreeDWarehouseScopedAttributeCountTask:
    """Count shelf items on one level of a uniquely colored warehouse rack."""

    task_id = TASK_ID
    domain = "three_d"
    scene_id = "warehouse"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        retry_params = _build_retry_locked_params(int(instance_seed), params)
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(spawn_rng(int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            try:
                return self._generate_once(int(attempt_seed), params=retry_params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
            allow_locked=True,
        )
        scene_variant, scene_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
            allow_locked=True,
        )
        aisle_heading, aisle_heading_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_AISLE_HEADINGS,
            explicit_key="aisle_heading",
            weights_key="aisle_heading_weights",
            balance_flag_key="balanced_aisle_heading_sampling",
            axis_namespace="aisle_heading",
            allow_locked=True,
        )
        rack_count, rack_count_probabilities = _shared_resolve_count(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="rack_count",
            default_min=2,
            default_max=4,
            lower=2,
            upper=4,
            allow_locked=True,
        )
        target_count, target_count_probabilities = _shared_resolve_count(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="target_count",
            default_min=0,
            default_max=5,
            lower=0,
            upper=5,
            allow_locked=True,
        )
        camera_yaw_band, camera_yaw_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(params=params, instance_seed=int(instance_seed))
        render_params = _resolve_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.canvas",
        )
        dataset = _build_dataset(
            params=params,
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            aisle_heading=str(aisle_heading),
            rack_count=int(rack_count),
            target_count=int(target_count),
            camera_yaw_band=tuple(camera_yaw_band),
            camera_yaw_band_index=int(camera_yaw_band_index),
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
        rendered_scene = render_warehouse_shelf_level_count_scene_3d(
            background,
            dataset=dataset,
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
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
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "shelf_level_name": str(dataset["target_shelf_level"]),
                "rack_color_name": str(dataset["target_rack_color_name"]),
                "rack_color_label": str(dataset["target_rack_color_label"]),
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
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in rendered_scene.annotation_bboxes]
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        solver_trace = dict(dataset["solver_trace"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_warehouse_shelf_level_count",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "aisle_heading": str(aisle_heading),
                    "rack_count": int(dataset["rack_count"]),
                    "shelf_item_count": len(dataset["shelf_item_specs"]),
                    "target_rack_id": str(dataset["target_rack_id"]),
                    "target_rack_color_label": str(dataset["target_rack_color_label"]),
                    "target_shelf_level": str(dataset["target_shelf_level"]),
                    "target_item_ids": [str(value) for value in dataset["target_item_ids"]],
                    "answer_value": int(answer_value),
                    "view_family": "synthetic_perspective_3d_warehouse_shelf",
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
                    "aisle_heading": str(aisle_heading),
                    "aisle_heading_probabilities": dict(aisle_heading_probabilities),
                    "rack_count": int(rack_count),
                    "rack_count_probabilities": dict(rack_count_probabilities),
                    "target_count": int(answer_value),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "target_rack_index": int(dataset["target_rack_index"]),
                    "target_rack_index_probabilities": dict(dataset["target_rack_index_probabilities"]),
                    "target_shelf_level": str(dataset["target_shelf_level"]),
                    "target_shelf_level_probabilities": _uniform_string_probability_map(SHELF_LEVEL_NAMES),
                    "camera_yaw_band_index": int(camera_yaw_band_index),
                    "camera_yaw_band_probabilities": dict(camera_yaw_probabilities),
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
                "rack_count": int(dataset["rack_count"]),
                "shelf_levels": list(SHELF_LEVEL_NAMES),
                "full_bleed_floor": True,
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "warehouse_bbox_px": list(rendered_scene.warehouse_bbox_px),
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "rack_bboxes_px": {str(key): list(value) for key, value in rendered_scene.rack_bboxes_px.items()},
                "rack_centers_px": {str(key): list(value) for key, value in rendered_scene.rack_centers_px.items()},
                "shelf_item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.shelf_item_bboxes_px.items()},
                "shelf_item_centers_px": {str(key): list(value) for key, value in rendered_scene.shelf_item_centers_px.items()},
                "target_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.target_item_bboxes_px.items()},
                "target_object_centers_px": {str(key): list(value) for key, value in rendered_scene.target_item_centers_px.items()},
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "aisle_heading": str(aisle_heading),
                "rack_count": int(dataset["rack_count"]),
                "shelf_item_count": len(dataset["shelf_item_specs"]),
                "object_count": int(dataset["object_count"]),
                "target_count": int(answer_value),
                "answer_value": int(answer_value),
                "target_rack_id": str(dataset["target_rack_id"]),
                "target_rack_color_name": str(dataset["target_rack_color_name"]),
                "target_rack_color_label": str(dataset["target_rack_color_label"]),
                "target_rack_rgb": list(dataset["target_rack_rgb"]),
                "target_shelf_level": str(dataset["target_shelf_level"]),
                "target_shelf_level_index": int(dataset["target_shelf_level_index"]),
                "target_item_ids": [str(value) for value in dataset["target_item_ids"]],
                "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                "rack_specs": [dict(spec) for spec in dataset["rack_specs"]],
                "shelf_item_specs": [dict(spec) for spec in dataset["shelf_item_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "rack_colors": dict(dataset["rack_colors"]),
                "shelf_counts_by_rack_level": dict(dataset["shelf_counts_by_rack_level"]),
                "item_counts_by_level": dict(dataset["item_counts_by_level"]),
                "main_aisle_polygon_world": list(dataset["main_aisle_polygon_world"]),
                "rack_zone_polygons_world": list(dataset["rack_zone_polygons_world"]),
                "origin_xy": list(dataset["origin_xy"]),
                "forward_xy": list(dataset["forward_xy"]),
                "orientation_axis": str(dataset["orientation_axis"]),
                "item_projected_bboxes": dict(dataset["item_projected_bboxes"]),
                "object_type_counts": dict(dataset["object_type_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "view_family": "synthetic_perspective_3d_warehouse_shelf",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "warehouse_shelf_level_object_set",
                "object_ids": [str(value) for value in dataset["target_item_ids"]],
                "target_rack_id": str(dataset["target_rack_id"]),
                "target_rack_color_label": str(dataset["target_rack_color_label"]),
                "target_shelf_level": str(dataset["target_shelf_level"]),
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


__all__ = ["ThreeDWarehouseScopedAttributeCountTask"]
