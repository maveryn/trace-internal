"""Robot forward-path object task for a synthetic 3D warehouse scene."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

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
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.task_support import float_value as _float_value
from ..shared.task_support import int_value as _int_value
from ..shared.color_variation import resolve_three_d_object_fill_rgb
from ..shared.object_resources import (
    WAREHOUSE_CONTEXT_OBJECT_TYPES,
    WAREHOUSE_OBJECT_BASE_DIMENSIONS,
    WAREHOUSE_OBJECT_COLORS,
    WAREHOUSE_OBJECT_NAMES,
    WAREHOUSE_OBJECT_TYPES,
    WAREHOUSE_RADIAL_OBJECT_TYPES,
    WAREHOUSE_ROBOT_ACCENT_COLORS,
    WAREHOUSE_ROBOT_BASE_COLORS,
    WAREHOUSE_ROBOT_DESIGNS,
    WAREHOUSE_ROBOT_HEADINGS,
    WAREHOUSE_SHELF_FRAME_COLORS,
    WAREHOUSE_SHELF_LOAD_COLORS,
    WAREHOUSE_SHELF_RACK_STYLES,
)
from ..spatial.camera_distance import (
    POINT_LABELS,
    _CameraSpec,
    _ProjectionFrame,
    _bbox_intersection_area,
    _bbox_union,
    _build_projection_frame,
    _canvas_floor_polygon_xy,
    _draw_box_object,
    _draw_box_parts_object,
    _draw_cone_object,
    _draw_cylinder_object,
    _draw_line,
    _draw_option_label,
    _draw_pyramid_object,
    _draw_wedge_object,
    _grid_values_for_range,
    _object_reference_points,
    _object_screen_bbox,
    _polygon_axis_line_segment,
    _project_screen,
    _project_xy,
    _sample_camera,
    _shade,
    _sub_box_spec,
    _tint,
)


TASK_ID = "task_three_d__warehouse__robot_forward_path_label"
SCENE_ID = "warehouse"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = ("first_object_ahead",)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("storage_aisle", "loading_zone", "packing_floor")
SUPPORTED_ROBOT_HEADINGS: Tuple[str, ...] = WAREHOUSE_ROBOT_HEADINGS
SUPPORTED_ROBOT_DESIGNS: Tuple[str, ...] = WAREHOUSE_ROBOT_DESIGNS
SUPPORTED_SHELF_RACK_STYLES: Tuple[str, ...] = WAREHOUSE_SHELF_RACK_STYLES
WAREHOUSE_CAMERA_YAW_BANDS_DEGREES: Tuple[Tuple[float, float], ...] = (
    (-54.0, -28.0),
    (28.0, 54.0),
    (-146.0, -116.0),
    (116.0, 146.0),
)
CONTEXT_OBJECT_TYPES: Tuple[str, ...] = WAREHOUSE_CONTEXT_OBJECT_TYPES
OBJECT_NAMES: Dict[str, str] = dict(WAREHOUSE_OBJECT_NAMES)
OBJECT_COLORS: Dict[str, Tuple[int, int, int]] = dict(WAREHOUSE_OBJECT_COLORS)
ROBOT_BASE_COLORS: Tuple[Tuple[int, int, int], ...] = WAREHOUSE_ROBOT_BASE_COLORS
ROBOT_ACCENT_COLORS: Tuple[Tuple[int, int, int], ...] = WAREHOUSE_ROBOT_ACCENT_COLORS
SHELF_FRAME_COLORS: Tuple[Tuple[int, int, int], ...] = WAREHOUSE_SHELF_FRAME_COLORS
SHELF_LOAD_COLORS: Tuple[Tuple[int, int, int], ...] = WAREHOUSE_SHELF_LOAD_COLORS
PATH_CORRIDOR_HALF_WIDTH = 0.42
MIN_FORWARD_DISTANCE = 0.72
MIN_FIRST_OBJECT_MARGIN = 0.52
MIN_CANDIDATE_VISIBLE_PX = 24.0
MIN_CANDIDATE_CENTER_SEPARATION_PX = 30.0
MAX_CANDIDATE_BBOX_INTERSECTION_PX = 9000.0


@dataclass(frozen=True)
class _WarehouseRenderParams:
    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    room_extent: float
    grid_step: float
    marker_radius_px: int
    label_font_size_px: int
    line_width_px: int
    floor_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    aisle_rgb: Tuple[int, int, int]
    shelf_zone_rgb: Tuple[int, int, int]
    path_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedWarehouseScene:
    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    warehouse_bbox_px: List[float]
    object_bboxes_px: Dict[str, List[float]]
    object_centers_px: Dict[str, List[float]]
    candidate_bboxes_px: Dict[str, List[float]]
    candidate_centers_px: Dict[str, List[float]]
    context_object_bboxes_px: Dict[str, List[float]]
    context_object_centers_px: Dict[str, List[float]]
    reference_object_bboxes_px: Dict[str, List[float]]
    reference_object_centers_px: Dict[str, List[float]]
    evidence_bboxes: List[List[float]]
    evidence_entity_ids: List[str]






def _resolve_render_params(params: Mapping[str, Any], *, render_defaults: Mapping[str, Any]) -> _WarehouseRenderParams:
    merged = dict(render_defaults)
    merged.update(dict(params))
    return _WarehouseRenderParams(
        canvas_width=_int_value(merged, "canvas_width", 1180),
        canvas_height=_int_value(merged, "canvas_height", 920),
        scene_margin_left_px=_int_value(merged, "scene_margin_left_px", 48),
        scene_margin_right_px=_int_value(merged, "scene_margin_right_px", 48),
        scene_margin_top_px=_int_value(merged, "scene_margin_top_px", 42),
        scene_margin_bottom_px=_int_value(merged, "scene_margin_bottom_px", 52),
        room_extent=_float_value(merged, "room_extent", 4.6),
        grid_step=_float_value(merged, "grid_step", 0.72),
        marker_radius_px=_int_value(merged, "marker_radius_px", 20),
        label_font_size_px=_int_value(merged, "label_font_size_px", 25),
        line_width_px=_int_value(merged, "line_width_px", 2),
        floor_rgb=_rgb(merged.get("floor_rgb", (221, 226, 220)), (221, 226, 220)),
        grid_rgb=_rgb(merged.get("grid_rgb", (174, 184, 179)), (174, 184, 179)),
        aisle_rgb=_rgb(merged.get("aisle_rgb", (207, 215, 211)), (207, 215, 211)),
        shelf_zone_rgb=_rgb(merged.get("shelf_zone_rgb", (190, 196, 194)), (190, 196, 194)),
        path_rgb=_rgb(merged.get("path_rgb", (236, 195, 72)), (236, 195, 72)),
        text_rgb=_rgb(merged.get("text_rgb", (24, 28, 36)), (24, 28, 36)),
        text_stroke_rgb=_rgb(merged.get("text_stroke_rgb", (255, 255, 255)), (255, 255, 255)),
    )






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


def _heading_vector(robot_heading: str) -> Tuple[float, float]:
    if str(robot_heading) == "east":
        return (1.0, 0.0)
    if str(robot_heading) == "west":
        return (-1.0, 0.0)
    if str(robot_heading) == "north":
        return (0.0, 1.0)
    if str(robot_heading) == "south":
        return (0.0, -1.0)
    raise ValueError(f"unsupported robot_heading: {robot_heading}")


def _heading_axis(robot_heading: str) -> str:
    return "x" if str(robot_heading) in {"east", "west"} else "y"


def _local_to_world(
    *,
    forward_s: float,
    lateral_l: float,
    origin_xy: Sequence[float],
    forward_xy: Sequence[float],
) -> Tuple[float, float]:
    fx, fy = float(forward_xy[0]), float(forward_xy[1])
    lx, ly = -fy, fx
    return (
        round(float(origin_xy[0]) + fx * float(forward_s) + lx * float(lateral_l), 4),
        round(float(origin_xy[1]) + fy * float(forward_s) + ly * float(lateral_l), 4),
    )


def _world_to_robot_path(
    xy: Sequence[float],
    *,
    robot_xy: Sequence[float],
    forward_xy: Sequence[float],
) -> Tuple[float, float]:
    fx, fy = float(forward_xy[0]), float(forward_xy[1])
    lx, ly = -fy, fx
    rx = float(xy[0]) - float(robot_xy[0])
    ry = float(xy[1]) - float(robot_xy[1])
    return (round(rx * fx + ry * fy, 4), round(rx * lx + ry * ly, 4))


def _dimensions_for_object(object_type: str, *, orientation_axis: str, scale: float) -> Tuple[float, float, float]:
    length, width, height = WAREHOUSE_OBJECT_BASE_DIMENSIONS.get(str(object_type), (0.64, 0.52, 0.52))
    if str(object_type) in WAREHOUSE_RADIAL_OBJECT_TYPES:
        return (round(width * scale, 4), round(width * scale, 4), round(height * scale, 4))
    if str(orientation_axis) == "y":
        return (round(width * scale, 4), round(length * scale, 4), round(height * scale, 4))
    return (round(length * scale, 4), round(width * scale, 4), round(height * scale, 4))


def _make_object_spec(
    *,
    object_id: str,
    object_type: str,
    object_role: str,
    xy: Tuple[float, float],
    orientation_axis: str,
    dimensions_xyz: Tuple[float, float, float],
    dimension_scale: float,
    label: str | None,
) -> Dict[str, Any]:
    width, depth, height = (float(value) for value in dimensions_xyz)
    footprint_radius = 0.5 * math.sqrt(width * width + depth * depth)
    spec: Dict[str, Any] = {
        "object_id": str(object_id),
        "object_type": str(object_type),
        "object_name": str(OBJECT_NAMES.get(str(object_type), str(object_type).replace("_", " "))),
        "prompt_name": str(OBJECT_NAMES.get(str(object_type), str(object_type).replace("_", " "))),
        "object_role": str(object_role),
        "orientation_axis": str(orientation_axis),
        "is_answer_candidate": bool(label),
        "dimension_scale": round(float(dimension_scale), 4),
        "world_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(height * 0.5), 4)],
        "base_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), 0.0],
        "dimensions_xyz": [round(width, 4), round(depth, 4), round(height, 4)],
        "footprint_radius": round(float(footprint_radius), 4),
    }
    if label is not None:
        spec.update({"point_id": f"warehouse_object_{label}", "point_label": str(label), "object_label": str(label)})
    return spec


def _finalize_specs(specs: Sequence[Mapping[str, Any]], *, camera: _CameraSpec, frame: _ProjectionFrame) -> List[Dict[str, Any]]:
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


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _visibility_ok(
    candidate_specs: Sequence[Mapping[str, Any]],
    reference_specs: Sequence[Mapping[str, Any]],
    context_specs: Sequence[Mapping[str, Any]],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    render_params: _WarehouseRenderParams,
) -> bool:
    bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=16.0) for spec in candidate_specs]
    centers = [(float(spec["screen_xy"][0]), float(spec["screen_xy"][1])) for spec in candidate_specs]
    for bbox in bboxes:
        width = float(bbox[2]) - float(bbox[0])
        height = float(bbox[3]) - float(bbox[1])
        if width < MIN_CANDIDATE_VISIBLE_PX or height < MIN_CANDIDATE_VISIBLE_PX:
            return False
        if (
            float(bbox[0]) < -24.0
            or float(bbox[1]) < -24.0
            or float(bbox[2]) > float(render_params.canvas_width + 24)
            or float(bbox[3]) > float(render_params.canvas_height + 24)
        ):
            return False
    for index, center in enumerate(centers):
        for other_index in range(index + 1, len(centers)):
            other = centers[other_index]
            if math.hypot(center[0] - other[0], center[1] - other[1]) < MIN_CANDIDATE_CENTER_SEPARATION_PX:
                return False
            if _bbox_intersection_area(bboxes[index], bboxes[other_index]) > MAX_CANDIDATE_BBOX_INTERSECTION_PX:
                return False
    reference_bboxes = []
    reference_centers = []
    for reference in reference_specs:
        ref_bbox = _object_screen_bbox(reference, camera, frame, pad_px=12.0)
        if (
            float(ref_bbox[0]) < -28.0
            or float(ref_bbox[1]) < -28.0
            or float(ref_bbox[2]) > float(render_params.canvas_width + 28)
            or float(ref_bbox[3]) > float(render_params.canvas_height + 28)
        ):
            return False
        reference_bboxes.append(list(ref_bbox))
        reference_centers.append((float(reference["screen_xy"][0]), float(reference["screen_xy"][1])))
    for candidate_index, candidate_bbox in enumerate(bboxes):
        candidate_area = max(1.0, _bbox_area(candidate_bbox))
        candidate_center = centers[candidate_index]
        for reference_index, ref_bbox in enumerate(reference_bboxes):
            overlap = _bbox_intersection_area(candidate_bbox, ref_bbox)
            ref_center = reference_centers[reference_index]
            center_distance = math.hypot(float(candidate_center[0]) - float(ref_center[0]), float(candidate_center[1]) - float(ref_center[1]))
            if center_distance < 58.0 or (overlap > 900.0 and overlap / candidate_area > 0.12):
                return False
    context_bboxes = {str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=8.0) for spec in context_specs}
    for candidate_index, candidate in enumerate(candidate_specs):
        candidate_bbox = bboxes[candidate_index]
        candidate_area = max(1.0, _bbox_area(candidate_bbox))
        for context in context_specs:
            if str(context.get("object_type")) == "shelf_rack":
                continue
            if float(context["camera_distance"]) >= float(candidate["camera_distance"]) - 0.05:
                continue
            overlap = _bbox_intersection_area(candidate_bbox, context_bboxes[str(context["object_id"])])
            if overlap > 2400.0 and overlap / candidate_area > 0.24:
                return False
    return True


def _scene_palette(scene_variant: str, render_params: _WarehouseRenderParams) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    if str(scene_variant) == "loading_zone":
        return (218, 222, 217), (162, 172, 168), (198, 207, 203), (183, 190, 188)
    if str(scene_variant) == "packing_floor":
        return (226, 224, 214), (178, 174, 158), (211, 208, 194), (190, 186, 170)
    return render_params.floor_rgb, render_params.grid_rgb, render_params.aisle_rgb, render_params.shelf_zone_rgb


def _alpha_polygon(
    image: Image.Image,
    points: Sequence[Sequence[float]],
    *,
    fill: Tuple[int, int, int, int],
    outline: Tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.polygon([(float(x), float(y)) for x, y in points], fill=fill)
    if outline is not None and points:
        overlay_draw.line([(float(x), float(y)) for x, y in points] + [(float(points[0][0]), float(points[0][1]))], fill=outline, width=max(1, int(width)))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _projected_bbox(points: Sequence[Sequence[float]]) -> List[float]:
    return [
        round(float(min(float(point[0]) for point in points)), 3),
        round(float(min(float(point[1]) for point in points)), 3),
        round(float(max(float(point[0]) for point in points)), 3),
        round(float(max(float(point[1]) for point in points)), 3),
    ]


def _draw_warehouse_floor(
    image: Image.Image,
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    render_params: _WarehouseRenderParams,
    scene_variant: str,
    dataset: Mapping[str, Any],
) -> Tuple[Image.Image, List[float], List[Dict[str, Any]]]:
    draw = ImageDraw.Draw(image)
    floor_rgb, grid_rgb, aisle_rgb, shelf_zone_rgb = _scene_palette(str(scene_variant), render_params)
    draw.rectangle((0, 0, int(render_params.canvas_width), int(render_params.canvas_height)), fill=floor_rgb)
    floor_polygon_xy = _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params)
    grid_world_bbox = None
    if floor_polygon_xy:
        min_x = min(float(point[0]) for point in floor_polygon_xy)
        max_x = max(float(point[0]) for point in floor_polygon_xy)
        min_y = min(float(point[1]) for point in floor_polygon_xy)
        max_y = max(float(point[1]) for point in floor_polygon_xy)
        grid_world_bbox = [round(min_x, 4), round(min_y, 4), round(max_x, 4), round(max_y, 4)]
        for value in _grid_values_for_range(min_y, max_y, float(render_params.grid_step)):
            segment = _polygon_axis_line_segment(floor_polygon_xy, axis="y", value=float(value))
            if segment is None:
                continue
            _draw_line(draw, _project_xy((segment[0][0], segment[0][1], 0.0), camera, frame), _project_xy((segment[1][0], segment[1][1], 0.0), camera, frame), fill=grid_rgb, width=render_params.line_width_px)
        for value in _grid_values_for_range(min_x, max_x, float(render_params.grid_step)):
            segment = _polygon_axis_line_segment(floor_polygon_xy, axis="x", value=float(value))
            if segment is None:
                continue
            _draw_line(draw, _project_xy((segment[0][0], segment[0][1], 0.0), camera, frame), _project_xy((segment[1][0], segment[1][1], 0.0), camera, frame), fill=grid_rgb, width=render_params.line_width_px)
    for polygon_world, color in (
        (dataset["shelf_zone_polygons_world"][0], shelf_zone_rgb),
        (dataset["shelf_zone_polygons_world"][1], shelf_zone_rgb),
        (dataset["main_aisle_polygon_world"], aisle_rgb),
    ):
        polygon_screen = [_project_xy(point, camera, frame) for point in polygon_world]
        draw.polygon(polygon_screen, fill=color)
    path_polygon_screen = [_project_xy(point, camera, frame) for point in dataset["robot_path_corridor_polygon_world"]]
    image = _alpha_polygon(
        image,
        path_polygon_screen,
        fill=(*render_params.path_rgb, 50),
        outline=(*render_params.path_rgb, 120),
        width=max(1, int(render_params.line_width_px)),
    )
    stage_bbox = [0.0, 0.0, float(render_params.canvas_width), float(render_params.canvas_height)]
    entities = [
        {
            "entity_id": "warehouse_floor",
            "entity_type": "three_d_warehouse_floor",
            "bbox_px": list(stage_bbox),
            "attrs": {
                "scene_variant": str(scene_variant),
                "full_bleed_floor": True,
                "grid_mode": "screen_ray_floor_plane",
                "grid_world_bbox": list(grid_world_bbox) if grid_world_bbox is not None else None,
                "floor_rgb": list(floor_rgb),
            },
        },
        {
            "entity_id": "robot_forward_path_corridor",
            "entity_type": "three_d_warehouse_robot_path_corridor",
            "bbox_px": _projected_bbox(path_polygon_screen),
            "attrs": {
                "robot_heading": str(dataset["robot_heading"]),
                "corridor_half_width": float(dataset["path_corridor_half_width"]),
                "path_polygon_world": [list(point) for point in dataset["robot_path_corridor_polygon_world"]],
            },
        },
    ]
    return image, stage_bbox, entities


def _draw_warehouse_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    object_type = str(spec["object_type"])
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    if object_type == "warehouse_robot":
        accent = _rgb(spec.get("robot_accent_rgb"), ROBOT_ACCENT_COLORS[0])
        robot_design = str(spec.get("robot_design", "low_cart"))
        if robot_design == "sensor_tower":
            parts = [
                _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.04), dimensions_xyz=(width, depth, height * 0.34)),
                _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.34), dimensions_xyz=(width * 0.36, depth * 0.40, height * 0.46)),
                _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.78), dimensions_xyz=(width * 0.56, depth * 0.50, height * 0.20)),
            ]
            accent_indices = {2}
        elif robot_design == "stacker_bot":
            parts = [
                _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.04), dimensions_xyz=(width, depth, height * 0.32)),
                _sub_box_spec(spec, offset_xyz=(-width * 0.28, -depth * 0.28, height * 0.24), dimensions_xyz=(width * 0.10, depth * 0.10, height * 0.72)),
                _sub_box_spec(spec, offset_xyz=(width * 0.28, -depth * 0.28, height * 0.24), dimensions_xyz=(width * 0.10, depth * 0.10, height * 0.72)),
                _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.28, height * 0.78), dimensions_xyz=(width * 0.72, depth * 0.08, height * 0.12)),
                _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.22, height * 0.30), dimensions_xyz=(width * 0.56, depth * 0.12, height * 0.10)),
            ]
            accent_indices = {3, 4}
        else:
            parts = [
                _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.04), dimensions_xyz=(width, depth, height * 0.50)),
                _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.48), dimensions_xyz=(width * 0.58, depth * 0.54, height * 0.30)),
                _sub_box_spec(spec, offset_xyz=(width * 0.24, 0.0, height * 0.74), dimensions_xyz=(width * 0.16, depth * 0.18, height * 0.20)),
            ]
            accent_indices = {2}
        heading = str(spec.get("robot_heading", "east" if str(spec.get("orientation_axis")) == "x" else "north"))
        heading_xy = _heading_vector(heading) if heading in set(SUPPORTED_ROBOT_HEADINGS) else (1.0, 0.0)
        fx, fy = float(heading_xy[0]), float(heading_xy[1])
        arm_base_z = height * 0.50
        if abs(fx) > 0.0:
            arm_dims = (width * 0.46, depth * 0.13, height * 0.12)
            arm_offset = (fx * width * 0.43, 0.0, arm_base_z)
            finger_dims = (width * 0.24, depth * 0.065, height * 0.10)
            finger_forward = fx * width * 0.74
            finger_offsets = [
                (finger_forward, -depth * 0.16, arm_base_z - height * 0.01),
                (finger_forward, depth * 0.16, arm_base_z - height * 0.01),
            ]
        else:
            arm_dims = (width * 0.13, depth * 0.46, height * 0.12)
            arm_offset = (0.0, fy * depth * 0.43, arm_base_z)
            finger_dims = (width * 0.065, depth * 0.24, height * 0.10)
            finger_forward = fy * depth * 0.74
            finger_offsets = [
                (-width * 0.16, finger_forward, arm_base_z - height * 0.01),
                (width * 0.16, finger_forward, arm_base_z - height * 0.01),
            ]
        parts.append(_sub_box_spec(spec, offset_xyz=arm_offset, dimensions_xyz=arm_dims))
        arm_index = len(parts) - 1
        for finger_offset in finger_offsets:
            parts.append(_sub_box_spec(spec, offset_xyz=finger_offset, dimensions_xyz=finger_dims))
        accent_indices = set(accent_indices) | {arm_index, arm_index + 1, arm_index + 2}
        bboxes: List[List[float]] = []
        for index, part in enumerate(sorted(enumerate(parts), key=lambda item: float(_project_screen(item[1]["world_xyz"], camera, frame)[7]), reverse=True)):
            part_index, part_spec = part
            part_fill = accent if part_index in accent_indices else (_tint(fill, 0.05) if index % 2 == 0 else _shade(fill, 0.92))
            bboxes.append(_draw_box_object(draw, part_spec, camera=camera, frame=frame, fill=part_fill))
        return _bbox_union(*bboxes)
    if object_type == "shelf_rack":
        return _draw_shelf_rack_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type in {"crate_stack", "box_stack"}:
        parts = [
            _sub_box_spec(spec, offset_xyz=(-width * 0.18, -depth * 0.16, 0.0), dimensions_xyz=(width * 0.50, depth * 0.50, height * 0.52)),
            _sub_box_spec(spec, offset_xyz=(width * 0.18, depth * 0.14, 0.0), dimensions_xyz=(width * 0.50, depth * 0.50, height * 0.48)),
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.48), dimensions_xyz=(width * 0.54, depth * 0.52, height * 0.50)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "pallet_load":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth, height * 0.18)),
            _sub_box_spec(spec, offset_xyz=(-width * 0.18, 0.0, height * 0.15), dimensions_xyz=(width * 0.52, depth * 0.80, height * 0.46)),
            _sub_box_spec(spec, offset_xyz=(width * 0.22, -depth * 0.08, height * 0.15), dimensions_xyz=(width * 0.42, depth * 0.58, height * 0.50)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "tool_cart":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.05), dimensions_xyz=(width, depth, height * 0.72)),
            _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.45, height * 0.46), dimensions_xyz=(width * 0.88, 0.08, height * 0.12)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "workbench":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.58), dimensions_xyz=(width, depth, height * 0.16)),
            _sub_box_spec(spec, offset_xyz=(-width * 0.38, -depth * 0.34, 0.0), dimensions_xyz=(0.09, 0.09, height * 0.74)),
            _sub_box_spec(spec, offset_xyz=(width * 0.38, -depth * 0.34, 0.0), dimensions_xyz=(0.09, 0.09, height * 0.74)),
            _sub_box_spec(spec, offset_xyz=(-width * 0.38, depth * 0.34, 0.0), dimensions_xyz=(0.09, 0.09, height * 0.74)),
            _sub_box_spec(spec, offset_xyz=(width * 0.38, depth * 0.34, 0.0), dimensions_xyz=(0.09, 0.09, height * 0.74)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "rolling_bin":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.08), dimensions_xyz=(width, depth, height * 0.80)),
            _sub_box_spec(spec, offset_xyz=(-width * 0.30, -depth * 0.28, 0.0), dimensions_xyz=(0.12, 0.12, height * 0.16)),
            _sub_box_spec(spec, offset_xyz=(width * 0.30, -depth * 0.28, 0.0), dimensions_xyz=(0.12, 0.12, height * 0.16)),
            _sub_box_spec(spec, offset_xyz=(-width * 0.30, depth * 0.28, 0.0), dimensions_xyz=(0.12, 0.12, height * 0.16)),
            _sub_box_spec(spec, offset_xyz=(width * 0.30, depth * 0.28, 0.0), dimensions_xyz=(0.12, 0.12, height * 0.16)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "pallet_jack":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.02), dimensions_xyz=(width * 0.72, depth * 0.34, height * 0.32)),
            _sub_box_spec(spec, offset_xyz=(width * 0.28, -depth * 0.24, 0.02), dimensions_xyz=(width * 0.46, depth * 0.12, height * 0.16)),
            _sub_box_spec(spec, offset_xyz=(width * 0.28, depth * 0.24, 0.02), dimensions_xyz=(width * 0.46, depth * 0.12, height * 0.16)),
            _sub_box_spec(spec, offset_xyz=(-width * 0.38, 0.0, height * 0.20), dimensions_xyz=(0.09, 0.10, height * 0.82)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "forklift":
        parts = [
            _sub_box_spec(spec, offset_xyz=(-width * 0.10, 0.0, 0.0), dimensions_xyz=(width * 0.62, depth, height * 0.58)),
            _sub_box_spec(spec, offset_xyz=(width * 0.34, 0.0, 0.0), dimensions_xyz=(0.10, depth * 0.92, height)),
            _sub_box_spec(spec, offset_xyz=(width * 0.52, -depth * 0.24, 0.02), dimensions_xyz=(width * 0.44, depth * 0.12, height * 0.10)),
            _sub_box_spec(spec, offset_xyz=(width * 0.52, depth * 0.24, 0.02), dimensions_xyz=(width * 0.44, depth * 0.12, height * 0.10)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "safety_barrier":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.34), dimensions_xyz=(width, depth, height * 0.18)),
            _sub_box_spec(spec, offset_xyz=(-width * 0.38, 0.0, 0.0), dimensions_xyz=(0.10, depth, height)),
            _sub_box_spec(spec, offset_xyz=(width * 0.38, 0.0, 0.0), dimensions_xyz=(0.10, depth, height)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "wrapped_bundle":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth, height)),
            _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.18, height * 0.34), dimensions_xyz=(width * 1.04, 0.06, height * 0.14)),
            _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.18, height * 0.34), dimensions_xyz=(width * 1.04, 0.06, height * 0.14)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "hand_truck":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.02), dimensions_xyz=(width * 0.72, depth * 0.20, height * 0.16)),
            _sub_box_spec(spec, offset_xyz=(-width * 0.26, 0.0, height * 0.20), dimensions_xyz=(0.08, depth * 0.88, height * 0.88)),
            _sub_box_spec(spec, offset_xyz=(width * 0.26, 0.0, height * 0.20), dimensions_xyz=(0.08, depth * 0.88, height * 0.88)),
            _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.34, height * 0.82), dimensions_xyz=(width * 0.70, 0.08, height * 0.10)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "stacked_pipes":
        parts = [
            _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.25, 0.0), dimensions_xyz=(width, depth * 0.24, height * 0.30)),
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.24), dimensions_xyz=(width * 0.96, depth * 0.24, height * 0.30)),
            _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.25, 0.0), dimensions_xyz=(width, depth * 0.24, height * 0.30)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "ladder":
        parts = [
            _sub_box_spec(spec, offset_xyz=(-width * 0.22, 0.0, 0.0), dimensions_xyz=(0.08, depth, height)),
            _sub_box_spec(spec, offset_xyz=(width * 0.22, 0.0, 0.0), dimensions_xyz=(0.08, depth, height)),
            _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.26, height * 0.22), dimensions_xyz=(width, 0.06, 0.08)),
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.46), dimensions_xyz=(width, 0.06, 0.08)),
            _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.26, height * 0.70), dimensions_xyz=(width, 0.06, 0.08)),
        ]
        return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    if object_type == "barrel":
        bbox = _draw_cylinder_object(draw, spec, camera=camera, frame=frame, fill=(154, 99, 48))
        x0, y0, x1, y1 = (float(value) for value in bbox)
        width_px = max(1.0, x1 - x0)
        height_px = max(1.0, y1 - y0)
        hoop_rgb = (58, 66, 74)
        wood_line = (92, 55, 31)
        for frac in (0.20, 0.50, 0.80):
            y = y0 + height_px * frac
            band = [x0 + width_px * 0.10, y - height_px * 0.035, x1 - width_px * 0.10, y + height_px * 0.035]
            draw.rectangle(tuple(band), fill=hoop_rgb, outline=(31, 36, 43), width=1)
        for frac in (0.32, 0.50, 0.68):
            x_line = x0 + width_px * frac
            _draw_line(draw, (x_line, y0 + height_px * 0.14), (x_line, y1 - height_px * 0.12), fill=wood_line, width=1)
        tap = [
            x0 + width_px * 0.58,
            y0 + height_px * 0.42,
            x0 + width_px * 0.75,
            y0 + height_px * 0.52,
        ]
        draw.rectangle(tuple(tap), fill=(202, 157, 76), outline=(44, 35, 26), width=1)
        return _bbox_union(bbox, tap)
    if object_type in {"tire_stack", "trash_can", "warning_bollard", "fire_extinguisher"}:
        return _draw_cylinder_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "traffic_cone":
        return _draw_cone_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "floor_sign":
        return _draw_pyramid_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "charging_dock":
        return _draw_wedge_object(draw, spec, camera=camera, frame=frame, fill=fill)
    return _draw_box_object(draw, spec, camera=camera, frame=frame, fill=fill)


def _fill_for_object(spec: Mapping[str, Any], *, scene_variant: str) -> Tuple[int, int, int]:
    if str(spec.get("object_type")) == "warehouse_robot" and isinstance(spec.get("robot_base_rgb"), Sequence):
        return _rgb(spec.get("robot_base_rgb"), OBJECT_COLORS["warehouse_robot"])
    if str(spec.get("object_type")) == "shelf_rack" and isinstance(spec.get("shelf_frame_rgb"), Sequence):
        return _rgb(spec.get("shelf_frame_rgb"), OBJECT_COLORS["shelf_rack"])
    base_rgb = OBJECT_COLORS.get(str(spec["object_type"]), (126, 136, 146))
    variation_strength = 0.24 if bool(spec.get("is_answer_candidate", False)) else 0.18
    return resolve_three_d_object_fill_rgb(
        spec,
        base_rgb=base_rgb,
        salt=f"{scene_variant}.warehouse.{spec['object_type']}",
        variation_strength=variation_strength,
    )


def _draw_ground_shadow(draw: ImageDraw.ImageDraw, spec: Mapping[str, Any], *, camera: _CameraSpec, frame: _ProjectionFrame) -> None:
    base = _project_screen(spec["base_xyz"], camera, frame)
    width, depth, _height = (float(value) for value in spec["dimensions_xyz"])
    radius = max(10.0, 19.0 * (7.0 / max(2.4, float(spec["camera_distance"]))) ** 0.26)
    radius *= max(0.70, min(1.52, (width + depth) * 0.50))
    draw.ellipse((base[0] - radius, base[1] - radius * 0.32, base[0] + radius, base[1] + radius * 0.32), fill=(120, 128, 132), outline=None)


def _draw_shelf_rack_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    shelf_style = str(spec.get("shelf_style", "open_frame"))
    level_fracs = [float(value) for value in spec.get("shelf_level_fracs", (0.10, 0.48, 0.86))]
    if not level_fracs:
        level_fracs = [0.10, 0.48, 0.86]
    beam_height = float(spec.get("shelf_beam_height", 0.09))
    post_width = float(spec.get("shelf_post_width", 0.08))
    beam_depth_scale = 0.90 if shelf_style == "open_frame" else 1.0
    if shelf_style == "heavy_low":
        beam_depth_scale = 1.08
    parts: List[Dict[str, Any]] = []
    for level_frac in level_fracs:
        level_z = max(0.02, min(height - beam_height, height * float(level_frac)))
        parts.append(
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, 0.0, level_z),
                dimensions_xyz=(width, depth * beam_depth_scale, beam_height),
            )
        )
    post_height = height * (0.96 if shelf_style != "heavy_low" else 0.82)
    x_offsets = [-width * 0.43, width * 0.43]
    if shelf_style in {"loaded_bins", "heavy_low"}:
        x_offsets = [-width * 0.43, 0.0, width * 0.43]
    y_offsets = [-depth * 0.38, depth * 0.38]
    for offset_x in x_offsets:
        for offset_y in y_offsets:
            parts.append(
                _sub_box_spec(
                    spec,
                    offset_xyz=(offset_x, offset_y, 0.0),
                    dimensions_xyz=(post_width, post_width, post_height),
                )
            )
    if shelf_style in {"mixed_crates", "heavy_low"}:
        parts.append(
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, -depth * 0.43, height * 0.18),
                dimensions_xyz=(width * 0.92, post_width * 0.62, height * 0.48),
            )
        )
    bboxes: List[List[float]] = [_draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)]
    for load_index, raw_load in enumerate(spec.get("shelf_load_slots", ())):
        if not isinstance(raw_load, Mapping):
            continue
        color_index = int(raw_load.get("color_index", load_index)) % len(SHELF_LOAD_COLORS)
        load_fill = SHELF_LOAD_COLORS[color_index]
        load_part = _sub_box_spec(
            spec,
            offset_xyz=(
                width * float(raw_load.get("x_frac", 0.0)),
                depth * float(raw_load.get("y_frac", 0.0)),
                height * float(raw_load.get("z_frac", 0.12)),
            ),
            dimensions_xyz=(
                width * float(raw_load.get("w_frac", 0.18)),
                depth * float(raw_load.get("d_frac", 0.46)),
                height * float(raw_load.get("h_frac", 0.16)),
            ),
        )
        bboxes.append(_draw_box_object(draw, load_part, camera=camera, frame=frame, fill=load_fill))
    return _bbox_union(*bboxes)


def _draw_reference_marker(
    draw: ImageDraw.ImageDraw,
    *,
    robot_spec: Mapping[str, Any],
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    dataset: Mapping[str, Any],
) -> Tuple[List[float], List[float]]:
    bbox = _object_screen_bbox(robot_spec, camera, frame, pad_px=9.0)
    draw.rectangle(tuple(float(value) for value in bbox), outline=(220, 34, 34), width=4)
    start_world = tuple(float(value) for value in dataset["robot_arrow_start_world"])
    end_world = tuple(float(value) for value in dataset["robot_arrow_end_world"])
    start = _project_xy(start_world, camera, frame)
    end = _project_xy(end_world, camera, frame)
    _draw_line(draw, start, end, fill=(220, 34, 34), width=5)
    vx, vy = float(end[0] - start[0]), float(end[1] - start[1])
    length = max(1.0, math.hypot(vx, vy))
    ux, uy = vx / length, vy / length
    px, py = -uy, ux
    arrow = [
        (end[0], end[1]),
        (end[0] - ux * 24 + px * 10, end[1] - uy * 24 + py * 10),
        (end[0] - ux * 24 - px * 10, end[1] - uy * 24 - py * 10),
    ]
    draw.polygon(arrow, fill=(220, 34, 34), outline=(112, 20, 20))
    marker_bbox = _bbox_union(bbox, [start[0], start[1], start[0], start[1]], _projected_bbox(arrow))
    return list(bbox), list(marker_bbox)


def render_warehouse_robot_scene_3d(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: _WarehouseRenderParams,
) -> _RenderedWarehouseScene:
    image = background.convert("RGB")
    camera = _camera_from_dataset(dataset)
    frame = _frame_from_dataset(dataset)
    scene_variant = str(dataset["scene_variant"])
    image, warehouse_bbox, entities = _draw_warehouse_floor(
        image,
        camera=camera,
        frame=frame,
        render_params=render_params,
        scene_variant=scene_variant,
        dataset=dataset,
    )
    draw = ImageDraw.Draw(image)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    candidate_specs = [dict(spec) for spec in dataset["candidate_object_specs"]]
    context_specs = [dict(spec) for spec in dataset["context_object_specs"]]
    reference_specs = [dict(spec) for spec in dataset["reference_object_specs"]]
    all_specs = [*candidate_specs, *context_specs, *reference_specs]
    shelf_specs = [spec for spec in all_specs if str(spec.get("object_type")) == "shelf_rack"]
    non_shelf_specs = [spec for spec in all_specs if str(spec.get("object_type")) != "shelf_rack"]
    ordered_specs = [
        *sorted(shelf_specs, key=lambda item: float(item["camera_distance"]), reverse=True),
        *sorted(non_shelf_specs, key=lambda item: float(item["camera_distance"]), reverse=True),
    ]
    for spec in ordered_specs:
        _draw_ground_shadow(draw, spec, camera=camera, frame=frame)
    point_bboxes: Dict[str, List[float]] = {}
    point_centers: Dict[str, List[float]] = {}
    object_bboxes: Dict[str, List[float]] = {}
    object_centers: Dict[str, List[float]] = {}
    context_bboxes: Dict[str, List[float]] = {}
    context_centers: Dict[str, List[float]] = {}
    reference_bboxes: Dict[str, List[float]] = {}
    reference_centers: Dict[str, List[float]] = {}

    for spec in ordered_specs:
        fill = _fill_for_object(spec, scene_variant=scene_variant)
        bbox = _draw_warehouse_object(draw, spec, camera=camera, frame=frame, fill=fill)
        label = str(spec.get("point_label", ""))
        center = [round(float(spec["screen_xy"][0]), 3), round(float(spec["screen_xy"][1]), 3)]
        if bool(spec.get("is_answer_candidate", False)):
            label_bbox = _draw_option_label(draw, label=label, center=(float(center[0]), float(center[1])), font=label_font)
            bbox = _bbox_union(bbox, label_bbox)
            point_bboxes[str(label)] = list(bbox)
            point_centers[str(label)] = list(center)
        elif str(spec.get("object_role")) == "warehouse_reference_robot":
            reference_bboxes[str(spec["object_id"])] = list(bbox)
            reference_centers[str(spec["object_id"])] = list(center)
        else:
            context_bboxes[str(spec["object_id"])] = list(bbox)
            context_centers[str(spec["object_id"])] = list(center)
        object_bboxes[str(spec["object_id"])] = list(bbox)
        object_centers[str(spec["object_id"])] = list(center)
        entities.append(
            {
                "entity_id": str(spec["object_id"]),
                "entity_type": "three_d_warehouse_candidate_object" if bool(spec.get("is_answer_candidate", False)) else ("three_d_warehouse_reference_robot" if str(spec.get("object_role")) == "warehouse_reference_robot" else "three_d_warehouse_context_object"),
                "bbox_px": list(bbox),
                "attrs": {
                    "point_label": str(label) if label else None,
                    "object_label": str(label) if label else None,
                    "object_type": str(spec["object_type"]),
                    "object_name": str(spec.get("object_name", spec["object_type"])),
                    "object_role": str(spec["object_role"]),
                    "shelf_style": str(spec.get("shelf_style")) if str(spec.get("object_type")) == "shelf_rack" else None,
                    "shelf_levels": int(spec.get("shelf_levels", 0)) if str(spec.get("object_type")) == "shelf_rack" else None,
                    "shelf_load_count": len(spec.get("shelf_load_slots", ())) if str(spec.get("object_type")) == "shelf_rack" else None,
                    "shelf_frame_rgb": list(spec.get("shelf_frame_rgb", ())) if str(spec.get("object_type")) == "shelf_rack" else None,
                    "shelf_height_scale": float(spec.get("shelf_height_scale", 1.0)) if str(spec.get("object_type")) == "shelf_rack" else None,
                    "robot_design": str(spec.get("robot_design")) if str(spec.get("object_type")) == "warehouse_robot" else None,
                    "robot_base_rgb": list(spec.get("robot_base_rgb", ())) if str(spec.get("object_type")) == "warehouse_robot" else None,
                    "robot_accent_rgb": list(spec.get("robot_accent_rgb", ())) if str(spec.get("object_type")) == "warehouse_robot" else None,
                    "is_answer_candidate": bool(spec.get("is_answer_candidate", False)),
                    "is_in_forward_path_corridor": bool(spec.get("is_in_forward_path_corridor", False)),
                    "is_first_reached_object": bool(spec.get("is_first_reached_object", False)),
                    "forward_distance_from_robot": float(spec.get("forward_distance_from_robot", 0.0)),
                    "lateral_offset_from_robot": float(spec.get("lateral_offset_from_robot", 0.0)),
                    "fill_rgb": [int(channel) for channel in fill],
                    "world_xyz": list(spec["world_xyz"]),
                    "base_xyz": list(spec["base_xyz"]),
                    "dimensions_xyz": list(spec["dimensions_xyz"]),
                    "screen_xy": list(center),
                    "camera_distance": float(spec["camera_distance"]),
                },
            }
        )

    robot_spec = reference_specs[0]
    robot_bbox, robot_marker_bbox = _draw_reference_marker(draw, robot_spec=robot_spec, camera=camera, frame=frame, dataset=dataset)
    entities.append(
        {
            "entity_id": "robot_reference_marker",
            "entity_type": "three_d_warehouse_robot_reference_marker",
            "bbox_px": list(robot_marker_bbox),
            "attrs": {
                "reference_object_id": str(robot_spec["object_id"]),
                "reference_marker": "red_bbox",
                "reference_marker_bbox_px": list(robot_bbox),
                "reference_direction_marker_bbox_px": list(robot_marker_bbox),
                "robot_heading": str(dataset["robot_heading"]),
                "travel_direction_vector_xy": list(dataset["travel_direction_vector_xy"]),
            },
        }
    )
    for label, center in sorted(point_centers.items()):
        _draw_option_label(draw, label=str(label), center=(float(center[0]), float(center[1])), font=label_font)

    answer_label = str(dataset["answer_label"])
    evidence_bbox = list(point_bboxes[answer_label])
    scene_bboxes = [list(warehouse_bbox), list(robot_marker_bbox)] + [list(bbox) for bbox in object_bboxes.values()]
    scene_bbox = [
        round(float(min(bbox[0] for bbox in scene_bboxes)), 3),
        round(float(min(bbox[1] for bbox in scene_bboxes)), 3),
        round(float(max(bbox[2] for bbox in scene_bboxes)), 3),
        round(float(max(bbox[3] for bbox in scene_bboxes)), 3),
    ]
    return _RenderedWarehouseScene(
        image=image,
        entities=list(entities),
        scene_bbox_px=list(scene_bbox),
        warehouse_bbox_px=list(warehouse_bbox),
        object_bboxes_px=dict(object_bboxes),
        object_centers_px=dict(object_centers),
        candidate_bboxes_px=dict(point_bboxes),
        candidate_centers_px=dict(point_centers),
        context_object_bboxes_px=dict(context_bboxes),
        context_object_centers_px=dict(context_centers),
        reference_object_bboxes_px=dict(reference_bboxes),
        reference_object_centers_px=dict(reference_centers),
        evidence_bboxes=[list(evidence_bbox)],
        evidence_entity_ids=[str(dataset["answer_object_id"])],
    )


def _camera_from_dataset(dataset: Mapping[str, Any]) -> _CameraSpec:
    raw = dataset["camera"]
    return _CameraSpec(
        camera_position=tuple(float(value) for value in raw["camera_position"]),
        target=tuple(float(value) for value in raw["target"]),
        right=tuple(float(value) for value in raw["right"]),
        up=tuple(float(value) for value in raw["up"]),
        forward=tuple(float(value) for value in raw["forward"]),
        yaw_degrees=float(raw["yaw_degrees"]),
        pitch_degrees=float(raw["pitch_degrees"]),
        distance=float(raw["distance"]),
    )


def _frame_from_dataset(dataset: Mapping[str, Any]) -> _ProjectionFrame:
    raw = dataset["projection_frame"]
    return _ProjectionFrame(
        scale=float(raw["scale"]),
        center_x=float(raw["center_x"]),
        center_y=float(raw["center_y"]),
        normalized_center_u=float(raw["normalized_center_u"]),
        normalized_center_v=float(raw["normalized_center_v"]),
    )


def _make_path_polygon(
    *,
    robot_xy: Sequence[float],
    forward_xy: Sequence[float],
    start_s: float,
    end_s: float,
    half_width: float,
) -> List[Tuple[float, float, float]]:
    fx, fy = float(forward_xy[0]), float(forward_xy[1])
    lx, ly = -fy, fx
    rx, ry = float(robot_xy[0]), float(robot_xy[1])
    return [
        (rx + fx * start_s + lx * half_width, ry + fy * start_s + ly * half_width, 0.022),
        (rx + fx * end_s + lx * half_width, ry + fy * end_s + ly * half_width, 0.022),
        (rx + fx * end_s - lx * half_width, ry + fy * end_s - ly * half_width, 0.022),
        (rx + fx * start_s - lx * half_width, ry + fy * start_s - ly * half_width, 0.022),
    ]


def _sample_reference_and_objects(
    *,
    rng,
    candidate_count: int,
    context_object_count: int,
    robot_heading: str,
    render_params: _WarehouseRenderParams,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    forward_xy = _heading_vector(str(robot_heading))
    orientation_axis = _heading_axis(str(robot_heading))
    origin_xy = (float(rng.uniform(-0.18, 0.18)), float(rng.uniform(-0.18, 0.18)))
    robot_s = -1.72
    robot_xy = _local_to_world(forward_s=robot_s, lateral_l=0.0, origin_xy=origin_xy, forward_xy=forward_xy)
    robot_design = str(rng.choice(SUPPORTED_ROBOT_DESIGNS))
    robot_dims = _dimensions_for_object("warehouse_robot", orientation_axis=str(orientation_axis), scale=float(rng.uniform(0.96, 1.08)))
    robot_width, robot_depth, robot_height = robot_dims
    if robot_design == "sensor_tower":
        robot_dims = (round(robot_width * 0.96, 4), round(robot_depth * 0.96, 4), round(robot_height * 1.26, 4))
    elif robot_design == "stacker_bot":
        robot_dims = (round(robot_width * 0.94, 4), round(robot_depth * 0.98, 4), round(robot_height * 1.42, 4))
    robot_spec = _make_object_spec(
        object_id="warehouse_robot_reference",
        object_type="warehouse_robot",
        object_role="warehouse_reference_robot",
        xy=robot_xy,
        orientation_axis=str(orientation_axis),
        dimensions_xyz=robot_dims,
        dimension_scale=1.0,
        label=None,
    )
    robot_base_rgb = ROBOT_BASE_COLORS[int(rng.randrange(len(ROBOT_BASE_COLORS)))]
    robot_accent_rgb = ROBOT_ACCENT_COLORS[int(rng.randrange(len(ROBOT_ACCENT_COLORS)))]
    robot_spec.update(
        {
            "robot_design": str(robot_design),
            "robot_heading": str(robot_heading),
            "robot_base_rgb": [int(channel) for channel in robot_base_rgb],
            "robot_accent_rgb": [int(channel) for channel in robot_accent_rgb],
        }
    )

    required_slots = [
        ("first_path", robot_s + float(rng.uniform(1.42, 1.72)), float(rng.uniform(-0.08, 0.08))),
        ("later_path", robot_s + float(rng.uniform(2.78, 3.22)), float(rng.uniform(-0.10, 0.10))),
    ]
    distractor_slots = [
        ("side_close", robot_s + float(rng.uniform(1.02, 1.42)), float(rng.choice((-1.0, 1.0))) * float(rng.uniform(1.14, 1.42))),
        ("behind_near", robot_s - float(rng.uniform(1.10, 1.52)), float(rng.choice((-1.0, 1.0))) * float(rng.uniform(1.42, 1.92))),
        ("adjacent_aisle", robot_s + float(rng.uniform(1.54, 2.22)), float(rng.choice((-1.0, 1.0))) * float(rng.uniform(1.70, 2.08))),
        ("side_far", robot_s + float(rng.uniform(2.42, 3.06)), float(rng.choice((-1.0, 1.0))) * float(rng.uniform(1.12, 1.54))),
    ]
    rng.shuffle(distractor_slots)
    candidate_local_slots = [*required_slots, *distractor_slots[: max(0, int(candidate_count) - len(required_slots))]]
    rng.shuffle(candidate_local_slots)
    object_types = list(WAREHOUSE_OBJECT_TYPES)
    path_object_types = [
        "crate_stack",
        "pallet_load",
        "barrel",
        "box_stack",
        "tire_stack",
        "safety_barrier",
        "storage_bin",
        "rolling_bin",
        "wrapped_bundle",
    ]
    rng.shuffle(object_types)
    rng.shuffle(path_object_types)
    candidate_specs: List[Dict[str, Any]] = []
    for index, (slot_role, forward_s, lateral_l) in enumerate(candidate_local_slots[: int(candidate_count)]):
        object_type = str(path_object_types.pop() if slot_role in {"first_path", "later_path"} and path_object_types else object_types[index % len(object_types)])
        xy = _local_to_world(forward_s=float(forward_s), lateral_l=float(lateral_l), origin_xy=origin_xy, forward_xy=forward_xy)
        scale = float(rng.uniform(0.90, 1.12))
        dimensions = _dimensions_for_object(str(object_type), orientation_axis=str(orientation_axis), scale=float(scale))
        spec = _make_object_spec(
            object_id=f"candidate_slot_{slot_role}_{index}",
            object_type=str(object_type),
            object_role="warehouse_candidate",
            xy=xy,
            orientation_axis=str(orientation_axis),
            dimensions_xyz=dimensions,
            dimension_scale=float(scale),
            label="?",
        )
        forward_from_robot, lateral_from_robot = _world_to_robot_path(xy, robot_xy=robot_xy, forward_xy=forward_xy)
        in_corridor = float(forward_from_robot) >= MIN_FORWARD_DISTANCE and abs(float(lateral_from_robot)) <= PATH_CORRIDOR_HALF_WIDTH
        spec.update(
            {
                "slot_role": str(slot_role),
                "forward_distance_from_robot": round(float(forward_from_robot), 4),
                "lateral_offset_from_robot": round(float(lateral_from_robot), 4),
                "is_in_forward_path_corridor": bool(in_corridor),
            }
        )
        candidate_specs.append(spec)

    shelf_specs: List[Dict[str, Any]] = []
    shelf_slots = [
        (1.72, -2.82),
        (3.66, -2.70),
        (1.82, 2.82),
        (3.78, 2.70),
    ]
    for index, (forward_s, lateral_l) in enumerate(shelf_slots):
        xy = _local_to_world(
            forward_s=float(forward_s + rng.uniform(-0.12, 0.12)),
            lateral_l=float(lateral_l + rng.uniform(-0.16, 0.16)),
            origin_xy=origin_xy,
            forward_xy=forward_xy,
        )
        shelf_style = str(rng.choice(SUPPORTED_SHELF_RACK_STYLES))
        if shelf_style == "loaded_bins":
            level_fracs = [0.10, 0.34, 0.58, 0.84]
            load_count = int(rng.randint(4, 8))
            height_scale = float(rng.uniform(0.84, 1.08))
        elif shelf_style == "mixed_crates":
            level_fracs = [0.12, 0.48, 0.82]
            load_count = int(rng.randint(2, 5))
            height_scale = float(rng.uniform(0.74, 0.98))
        elif shelf_style == "tall_sparse":
            level_fracs = [0.08, 0.30, 0.56, 0.82]
            load_count = int(rng.randint(1, 3))
            height_scale = float(rng.uniform(1.04, 1.24))
        elif shelf_style == "heavy_low":
            level_fracs = [0.14, 0.62]
            load_count = int(rng.randint(1, 4))
            height_scale = float(rng.uniform(0.56, 0.76))
        else:
            level_fracs = [0.12, 0.54, 0.86] if rng.random() < 0.55 else [0.16, 0.76]
            load_count = int(rng.randint(0, 2))
            height_scale = float(rng.uniform(0.68, 1.04))
        scale = float(rng.uniform(1.00, 1.18))
        base_width, base_depth, base_height = _dimensions_for_object("shelf_rack", orientation_axis=str(orientation_axis), scale=float(scale))
        dimensions = (base_width, base_depth, round(float(base_height * height_scale), 4))
        load_slots: List[Dict[str, Any]] = []
        loadable_levels = level_fracs[:-1] if len(level_fracs) > 1 else level_fracs
        for load_index in range(load_count):
            level_frac = float(rng.choice(loadable_levels))
            load_slots.append(
                {
                    "x_frac": round(float(rng.uniform(-0.30, 0.30)), 4),
                    "y_frac": round(float(rng.uniform(-0.18, 0.18)), 4),
                    "z_frac": round(min(0.86, level_frac + float(rng.uniform(0.035, 0.060))), 4),
                    "w_frac": round(float(rng.uniform(0.12, 0.24)), 4),
                    "d_frac": round(float(rng.uniform(0.38, 0.66)), 4),
                    "h_frac": round(float(rng.uniform(0.10, 0.18)), 4),
                    "color_index": int((index * 3 + load_index + rng.randrange(len(SHELF_LOAD_COLORS))) % len(SHELF_LOAD_COLORS)),
                }
            )
        shelf_spec = _make_object_spec(
            object_id=f"context_shelf_rack_{index}",
            object_type="shelf_rack",
            object_role="warehouse_context",
            xy=xy,
            orientation_axis=str(orientation_axis),
            dimensions_xyz=dimensions,
            dimension_scale=float(scale),
            label=None,
        )
        shelf_spec.update(
            {
                "shelf_style": str(shelf_style),
                "shelf_height_scale": round(float(height_scale), 4),
                "shelf_level_fracs": [round(float(value), 4) for value in level_fracs],
                "shelf_levels": int(len(level_fracs)),
                "shelf_beam_height": round(float(rng.uniform(0.075, 0.125)), 4),
                "shelf_post_width": round(float(rng.uniform(0.070, 0.115)), 4),
                "shelf_frame_rgb": [int(channel) for channel in SHELF_FRAME_COLORS[int(rng.randrange(len(SHELF_FRAME_COLORS)))]],
                "shelf_load_slots": list(load_slots),
            }
        )
        shelf_specs.append(shelf_spec)
    context_specs: List[Dict[str, Any]] = list(shelf_specs)
    optional_context_slots = [
        ("charging_dock", robot_s - 0.90, -1.70),
        ("conveyor", 2.96, 1.28),
        ("pallet", -2.58, 1.72),
        ("crate_stack", -2.72, -1.62),
        ("barrel", 3.34, -1.18),
        ("storage_bin", 3.24, 1.46),
        ("safety_barrier", -2.84, 0.96),
        ("tool_cart", 0.18, 2.46),
        ("traffic_cone", 0.32, -2.46),
        ("pallet_load", 3.68, 1.88),
        ("workbench", -0.32, -2.60),
        ("rolling_bin", 1.64, 2.54),
        ("trash_can", -2.30, -2.28),
        ("warning_bollard", -0.08, 1.48),
        ("wrapped_bundle", 2.30, -2.54),
        ("fire_extinguisher", -1.84, 2.42),
        ("hand_truck", 1.04, -2.62),
        ("stacked_pipes", 3.54, -2.08),
    ]
    rng.shuffle(optional_context_slots)
    target_optional = max(0, int(context_object_count) - len(context_specs))
    for index, (object_type, forward_s, lateral_l) in enumerate(optional_context_slots[:target_optional]):
        xy = _local_to_world(
            forward_s=float(forward_s + rng.uniform(-0.12, 0.12)),
            lateral_l=float(lateral_l + rng.uniform(-0.10, 0.10)),
            origin_xy=origin_xy,
            forward_xy=forward_xy,
        )
        scale = float(rng.uniform(0.90, 1.12))
        dimensions = _dimensions_for_object(str(object_type), orientation_axis=str(orientation_axis), scale=float(scale))
        context_specs.append(
            _make_object_spec(
                object_id=f"context_{index}_{object_type}",
                object_type=str(object_type),
                object_role="warehouse_context",
                xy=xy,
                orientation_axis=str(orientation_axis),
                dimensions_xyz=dimensions,
                dimension_scale=float(scale),
                label=None,
            )
        )
    path_corridor_polygon = _make_path_polygon(robot_xy=robot_xy, forward_xy=forward_xy, start_s=0.20, end_s=3.50, half_width=PATH_CORRIDOR_HALF_WIDTH)
    main_aisle_polygon = _make_path_polygon(robot_xy=robot_xy, forward_xy=forward_xy, start_s=-1.06, end_s=4.30, half_width=1.28)
    left_shelf_zone = _make_path_polygon(robot_xy=robot_xy, forward_xy=forward_xy, start_s=1.04, end_s=4.72, half_width=0.42)
    right_shelf_zone = _make_path_polygon(robot_xy=robot_xy, forward_xy=forward_xy, start_s=1.04, end_s=4.72, half_width=0.42)
    fx, fy = forward_xy
    lx, ly = -fy, fx
    shifted_left = [(x + lx * 2.76, y + ly * 2.76, z) for x, y, z in left_shelf_zone]
    shifted_right = [(x - lx * 2.76, y - ly * 2.76, z) for x, y, z in right_shelf_zone]
    scene_geometry = {
        "origin_xy": [round(float(value), 4) for value in origin_xy],
        "robot_xy": [round(float(value), 4) for value in robot_xy],
        "forward_xy": [round(float(value), 4) for value in forward_xy],
        "path_corridor_polygon": [[round(float(value), 4) for value in point] for point in path_corridor_polygon],
        "main_aisle_polygon": [[round(float(value), 4) for value in point] for point in main_aisle_polygon],
        "shelf_zone_polygons": [
            [[round(float(value), 4) for value in point] for point in shifted_left],
            [[round(float(value), 4) for value in point] for point in shifted_right],
        ],
    }
    return [robot_spec], candidate_specs, context_specs, scene_geometry


def _attach_path_answers(
    candidate_specs: Sequence[Mapping[str, Any]],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    candidate_count: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    path_candidates = [
        dict(spec)
        for spec in candidate_specs
        if bool(spec.get("is_in_forward_path_corridor", False))
    ]
    if len(path_candidates) < 2:
        raise ValueError("warehouse scene requires at least two path-corridor candidates")
    ordered = sorted(path_candidates, key=lambda spec: (float(spec["forward_distance_from_robot"]), str(spec["object_id"])))
    first = dict(ordered[0])
    second = dict(ordered[1])
    if float(second["forward_distance_from_robot"]) - float(first["forward_distance_from_robot"]) < MIN_FIRST_OBJECT_MARGIN:
        raise ValueError("first reached object margin too small")
    answer_label_index = abs(
        int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.answer_label"))
    ) % int(candidate_count)
    answer_label = str(POINT_LABELS[int(answer_label_index)])
    remaining_labels = [str(label) for label in POINT_LABELS[: int(candidate_count)] if str(label) != str(answer_label)]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.answer_label_assignment")
    rng.shuffle(remaining_labels)
    relabeled: List[Dict[str, Any]] = []
    for spec in candidate_specs:
        updated = dict(spec)
        is_answer = str(updated["object_id"]) == str(first["object_id"])
        label = answer_label if is_answer else remaining_labels.pop()
        updated.update(
            {
                "object_id": f"warehouse_object_{label}",
                "point_id": f"warehouse_object_{label}",
                "point_label": str(label),
                "object_label": str(label),
                "is_answer_candidate": True,
                "is_first_reached_object": bool(is_answer),
            }
        )
        relabeled.append(updated)
    ordered_all = sorted(relabeled, key=lambda spec: (float(spec["forward_distance_from_robot"]), abs(float(spec["lateral_offset_from_robot"])), str(spec["point_label"])))
    answer_spec = next(spec for spec in relabeled if bool(spec["is_first_reached_object"]))
    path_labels = sorted(
        [str(spec["point_label"]) for spec in relabeled if bool(spec.get("is_in_forward_path_corridor", False))],
        key=lambda label: next(float(spec["forward_distance_from_robot"]) for spec in relabeled if str(spec["point_label"]) == str(label)),
    )
    return list(sorted(relabeled, key=lambda spec: str(spec["point_label"]))), {
        "answer_label": str(answer_label),
        "answer_spec": dict(answer_spec),
        "path_labels": list(path_labels),
        "forward_order_labels": [str(spec["point_label"]) for spec in ordered_all],
        "first_reached_margin": round(float(second["forward_distance_from_robot"]) - float(first["forward_distance_from_robot"]), 4),
    }


def _build_dataset(
    *,
    params: Mapping[str, Any],
    query_variant: str,
    scene_variant: str,
    robot_heading: str,
    candidate_count: int,
    context_object_count: int,
    camera_yaw_band: Tuple[float, float],
    camera_yaw_band_index: int,
    render_params: _WarehouseRenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    for _attempt in range(420):
        camera = _sample_camera(rng, yaw_band_degrees=tuple(float(value) for value in camera_yaw_band))
        reference_specs, candidate_specs, context_specs, scene_geometry = _sample_reference_and_objects(
            rng=rng,
            candidate_count=int(candidate_count),
            context_object_count=int(context_object_count),
            robot_heading=str(robot_heading),
            render_params=render_params,
        )
        candidate_specs, answer_meta = _attach_path_answers(candidate_specs, params=params, instance_seed=int(instance_seed), candidate_count=int(candidate_count))
        robot_spec = dict(reference_specs[0])
        forward_xy = scene_geometry["forward_xy"]
        robot_xy = scene_geometry["robot_xy"]
        all_specs = [*reference_specs, *candidate_specs, *context_specs]
        reference_points: List[Tuple[float, float, float]] = []
        for spec in all_specs:
            if str(spec.get("object_type")) == "shelf_rack":
                continue
            reference_points.extend(_object_reference_points(spec))
        reference_points.extend(tuple(float(value) for value in point) for point in scene_geometry["path_corridor_polygon"])
        reference_points.extend(tuple(float(value) for value in point) for point in scene_geometry["main_aisle_polygon"])
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_reference = _finalize_specs(reference_specs, camera=camera, frame=frame)
        finalized_candidates = _finalize_specs(candidate_specs, camera=camera, frame=frame)
        finalized_context = _finalize_specs(context_specs, camera=camera, frame=frame)
        if not _visibility_ok(finalized_candidates, finalized_reference, finalized_context, camera=camera, frame=frame, render_params=render_params):
            continue
        answer_label = str(answer_meta["answer_label"])
        answer_spec = next(spec for spec in finalized_candidates if str(spec["point_label"]) == answer_label)
        if not bool(answer_spec.get("is_first_reached_object", False)):
            continue
        path_labels = [
            str(spec["point_label"])
            for spec in sorted(finalized_candidates, key=lambda item: (float(item["forward_distance_from_robot"]), str(item["point_label"])))
            if bool(spec.get("is_in_forward_path_corridor", False))
        ]
        first_reached_by_label = {str(spec["point_label"]): bool(spec.get("is_first_reached_object", False)) for spec in finalized_candidates}
        in_path_by_label = {str(spec["point_label"]): bool(spec.get("is_in_forward_path_corridor", False)) for spec in finalized_candidates}
        forward_distance_by_label = {str(spec["point_label"]): round(float(spec["forward_distance_from_robot"]), 4) for spec in finalized_candidates}
        lateral_offset_by_label = {str(spec["point_label"]): round(float(spec["lateral_offset_from_robot"]), 4) for spec in finalized_candidates}
        candidate_object_types = {str(spec["point_label"]): str(spec["object_type"]) for spec in finalized_candidates}
        candidate_projected_bboxes = {
            str(spec["point_label"]): [round(float(value), 3) for value in _object_screen_bbox(spec, camera, frame, pad_px=0.0)]
            for spec in finalized_candidates
        }
        object_type_counts = Counter(str(spec["object_type"]) for spec in [*finalized_reference, *finalized_candidates, *finalized_context])
        robot_arrow_start = (
            float(robot_xy[0]) + float(forward_xy[0]) * 0.26,
            float(robot_xy[1]) + float(forward_xy[1]) * 0.26,
            0.12,
        )
        robot_arrow_end = (
            float(robot_xy[0]) + float(forward_xy[0]) * 0.88,
            float(robot_xy[1]) + float(forward_xy[1]) * 0.88,
            0.12,
        )
        return {
            "query_variant": str(query_variant),
            "scene_variant": str(scene_variant),
            "candidate_count": int(candidate_count),
            "context_object_count": int(context_object_count),
            "robot_heading": str(robot_heading),
            "robot_design": str(finalized_reference[0].get("robot_design", "low_cart")),
            "travel_direction_vector_xy": [round(float(value), 4) for value in forward_xy],
            "path_corridor_half_width": float(PATH_CORRIDOR_HALF_WIDTH),
            "robot_path_corridor_polygon_world": list(scene_geometry["path_corridor_polygon"]),
            "main_aisle_polygon_world": list(scene_geometry["main_aisle_polygon"]),
            "shelf_zone_polygons_world": list(scene_geometry["shelf_zone_polygons"]),
            "robot_arrow_start_world": [round(float(value), 4) for value in robot_arrow_start],
            "robot_arrow_end_world": [round(float(value), 4) for value in robot_arrow_end],
            "reference_object": dict(finalized_reference[0]),
            "reference_object_specs": list(finalized_reference),
            "candidate_object_specs": sorted(finalized_candidates, key=lambda spec: str(spec["point_label"])),
            "context_object_specs": sorted(finalized_context, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted([*finalized_reference, *finalized_candidates, *finalized_context], key=lambda spec: str(spec["object_id"])),
            "target_object_ids": [str(answer_spec["object_id"])],
            "answer_label": str(answer_label),
            "answer_object_id": str(answer_spec["object_id"]),
            "answer_object_type": str(answer_spec["object_type"]),
            "first_reached_candidate_labels": [str(answer_label)],
            "forward_path_candidate_labels": list(path_labels),
            "first_reached_by_label": dict(sorted(first_reached_by_label.items())),
            "in_forward_path_corridor_by_label": dict(sorted(in_path_by_label.items())),
            "forward_distance_from_robot_by_label": dict(sorted(forward_distance_by_label.items())),
            "lateral_offset_from_robot_by_label": dict(sorted(lateral_offset_by_label.items())),
            "forward_order_near_to_far": [str(label) for label in answer_meta["forward_order_labels"]],
            "first_reached_margin": float(answer_meta["first_reached_margin"]),
            "candidate_object_types_by_label": dict(sorted(candidate_object_types.items())),
            "candidate_projected_bboxes_by_label": dict(sorted(candidate_projected_bboxes.items())),
            "object_type_counts": dict(sorted(object_type_counts.items())),
            "object_count": int(1 + len(finalized_candidates) + len(finalized_context)),
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
                "predicate": "first lettered object reached by the red-boxed robot moving straight along its arrow",
                "robot_heading": str(robot_heading),
                "travel_direction_vector_xy": [round(float(value), 4) for value in forward_xy],
                "first_reached_by_label": dict(sorted(first_reached_by_label.items())),
                "in_forward_path_corridor_by_label": dict(sorted(in_path_by_label.items())),
                "forward_distance_from_robot_by_label": dict(sorted(forward_distance_by_label.items())),
                "lateral_offset_from_robot_by_label": dict(sorted(lateral_offset_by_label.items())),
                "forward_order_near_to_far": [str(label) for label in answer_meta["forward_order_labels"]],
                "answer_label": str(answer_label),
                "answer_object_id": str(answer_spec["object_id"]),
                "unique_answer": True,
            },
        }
    raise ValueError("could not construct a visible warehouse robot scene")




def _build_complexity(*, candidate_count: int, context_object_count: int, complexity_defaults: Mapping[str, Any]) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.30)),
        "movement_projection": float(raw_weights.get("movement_projection", 0.36)),
        "corridor_filtering": float(raw_weights.get("corridor_filtering", 0.22)),
        "distractor_load": float(raw_weights.get("distractor_load", 0.12)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(float(candidate_count), 4.0, 7.0),
        "movement_projection": 0.70,
        "corridor_filtering": 0.66,
        "distractor_load": _normalize_unit(float(context_object_count), 6.0, 12.0),
    }
    score = sum(float(components[key]) * max(0.0, float(weights[key])) for key in weights) / float(total)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={key: round(float(value), 6) for key, value in components.items()},
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "warehouse")
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


def _build_retry_locked_params(instance_seed: int, params: Mapping[str, Any]) -> Dict[str, Any]:
    locked_params = dict(params)
    query_variant, _query_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
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
    robot_heading, _heading_probabilities = _shared_resolve_axis_variant(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_ROBOT_HEADINGS,
        explicit_key="robot_heading",
        weights_key="robot_heading_weights",
        balance_flag_key="balanced_robot_heading_sampling",
        axis_namespace="robot_heading",
        allow_locked=True,
    )
    candidate_count, _candidate_probabilities = _shared_resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="candidate_count",
        default_min=5,
        default_max=5,
        lower=5,
        upper=6,
        allow_locked=True,
    )
    context_object_count, _context_probabilities = _shared_resolve_count(
        params=params,
        task_id=TASK_ID,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        key="context_object_count",
        default_min=11,
        default_max=11,
        lower=8,
        upper=13,
        allow_locked=True,
    )
    _camera_yaw_band, _camera_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(params=params, instance_seed=int(instance_seed))
    locked_params.update(
        {
            "_locked_query_variant": str(query_variant),
            "_locked_scene_variant": str(scene_variant),
            "_locked_robot_heading": str(robot_heading),
            "_locked_candidate_count": int(candidate_count),
            "_locked_context_object_count": int(context_object_count),
            "_locked_camera_yaw_band_index": int(camera_yaw_band_index),
        }
    )
    return locked_params


@register_task
class ThreeDWarehouseRobotForwardPathLabelTask:
    """Choose the first object a red-boxed robot would reach when moving forward."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "warehouse"
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
        query_variant, query_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_QUERY_VARIANTS,
            explicit_key="query_variant",
            weights_key="query_variant_weights",
            balance_flag_key="balanced_query_variant_sampling",
            axis_namespace="query_variant",
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
        robot_heading, robot_heading_probabilities = _shared_resolve_axis_variant(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_ROBOT_HEADINGS,
            explicit_key="robot_heading",
            weights_key="robot_heading_weights",
            balance_flag_key="balanced_robot_heading_sampling",
            axis_namespace="robot_heading",
            allow_locked=True,
        )
        candidate_count, candidate_count_probabilities = _shared_resolve_count(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="candidate_count",
            default_min=5,
            default_max=5,
            lower=5,
            upper=6,
            allow_locked=True,
        )
        context_object_count, context_count_probabilities = _shared_resolve_count(
            params=params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="context_object_count",
            default_min=11,
            default_max=11,
            lower=8,
            upper=13,
            allow_locked=True,
        )
        camera_yaw_band, camera_yaw_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(params=params, instance_seed=int(instance_seed))
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_dataset(
            params=params,
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            robot_heading=str(robot_heading),
            candidate_count=int(candidate_count),
            context_object_count=int(context_object_count),
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
        rendered_scene = render_warehouse_robot_scene_3d(background, dataset=dataset, render_params=render_params)
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
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
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
        answer_label = str(dataset["answer_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in rendered_scene.evidence_bboxes]
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        complexity = _build_complexity(
            candidate_count=int(dataset["candidate_count"]),
            context_object_count=int(dataset["context_object_count"]),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )
        solver_trace = dict(dataset["solver_trace"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_warehouse_robot",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "candidate_count": int(dataset["candidate_count"]),
                    "context_object_count": int(dataset["context_object_count"]),
                    "robot_heading": str(dataset["robot_heading"]),
                    "robot_design": str(dataset["robot_design"]),
                    "travel_direction_vector_xy": list(dataset["travel_direction_vector_xy"]),
                    "first_reached_by_label": dict(dataset["first_reached_by_label"]),
                    "answer_label": str(answer_label),
                    "answer_object_id": str(dataset["answer_object_id"]),
                    "view_family": "synthetic_perspective_3d_warehouse_robot",
                },
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "query_variant_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probabilities),
                    "robot_heading": str(robot_heading),
                    "robot_heading_probabilities": dict(robot_heading_probabilities),
                    "candidate_count": int(candidate_count),
                    "candidate_count_probabilities": dict(candidate_count_probabilities),
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_count_probabilities),
                    "camera_yaw_band_index": int(camera_yaw_band_index),
                    "camera_yaw_band_probabilities": dict(camera_yaw_probabilities),
                    "answer_label_probabilities": {str(label): round(1.0 / float(candidate_count), 8) for label in POINT_LABELS[: int(candidate_count)]},
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
                "label_font_size_px": int(render_params.label_font_size_px),
                "robot_heading": str(dataset["robot_heading"]),
                "robot_design": str(dataset["robot_design"]),
                "travel_direction_vector_xy": list(dataset["travel_direction_vector_xy"]),
                "path_corridor_half_width": float(dataset["path_corridor_half_width"]),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "warehouse_bbox_px": list(rendered_scene.warehouse_bbox_px),
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "candidate_bboxes_px": {str(key): list(value) for key, value in rendered_scene.candidate_bboxes_px.items()},
                "candidate_centers_px": {str(key): list(value) for key, value in rendered_scene.candidate_centers_px.items()},
                "context_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.context_object_bboxes_px.items()},
                "context_object_centers_px": {str(key): list(value) for key, value in rendered_scene.context_object_centers_px.items()},
                "reference_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.reference_object_bboxes_px.items()},
                "reference_object_centers_px": {str(key): list(value) for key, value in rendered_scene.reference_object_centers_px.items()},
                "target_object_bboxes_px": {str(key): list(rendered_scene.object_bboxes_px[str(key)]) for key in dataset["target_object_ids"]},
            },
            "execution_trace": {
                "query_variant": "default",
                "query_id": str(query_variant),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "candidate_count": int(dataset["candidate_count"]),
                "context_object_count": int(dataset["context_object_count"]),
                "object_count": int(dataset["object_count"]),
                "answer_label": str(answer_label),
                "answer_object_id": str(dataset["answer_object_id"]),
                "answer_object_type": str(dataset["answer_object_type"]),
                "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                "reference_object": dict(dataset["reference_object"]),
                "reference_object_specs": [dict(spec) for spec in dataset["reference_object_specs"]],
                "candidate_object_specs": [dict(spec) for spec in dataset["candidate_object_specs"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "robot_heading": str(dataset["robot_heading"]),
                "robot_design": str(dataset["robot_design"]),
                "travel_direction_vector_xy": list(dataset["travel_direction_vector_xy"]),
                "path_corridor_half_width": float(dataset["path_corridor_half_width"]),
                "robot_path_corridor_polygon_world": list(dataset["robot_path_corridor_polygon_world"]),
                "first_reached_candidate_labels": list(dataset["first_reached_candidate_labels"]),
                "forward_path_candidate_labels": list(dataset["forward_path_candidate_labels"]),
                "first_reached_by_label": dict(dataset["first_reached_by_label"]),
                "in_forward_path_corridor_by_label": dict(dataset["in_forward_path_corridor_by_label"]),
                "forward_distance_from_robot_by_label": dict(dataset["forward_distance_from_robot_by_label"]),
                "lateral_offset_from_robot_by_label": dict(dataset["lateral_offset_from_robot_by_label"]),
                "forward_order_near_to_far": list(dataset["forward_order_near_to_far"]),
                "first_reached_margin": float(dataset["first_reached_margin"]),
                "candidate_object_types_by_label": dict(dataset["candidate_object_types_by_label"]),
                "candidate_projected_bboxes_by_label": dict(dataset["candidate_projected_bboxes_by_label"]),
                "object_type_counts": dict(dataset["object_type_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_variant),
                "view_family": "synthetic_perspective_3d_warehouse_robot",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {"type": "object", "id": str(dataset["answer_object_id"]), "answer": str(answer_label)},
            "projected_evidence": {"bbox_set": [list(bbox) for bbox in evidence_bboxes]},
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
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query_variant),
        )


__all__ = ["ThreeDWarehouseRobotForwardPathLabelTask"]
