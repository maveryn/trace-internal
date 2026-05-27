"""Camera-distance extremum task for a synthetic 3D object scene."""

from __future__ import annotations

import math
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
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import float_value as _float_value
from ..shared.task_support import int_value as _int_value
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.color_variation import resolve_three_d_object_fill_rgb
from ..shared.object_resources import (
    OBJECT_SCENE_CONTEXT_DIMENSIONS,
    OBJECT_SCENE_CONTEXT_SHAPE_TYPES,
    OBJECT_SCENE_NAME_BY_SHAPE_TYPE,
    OBJECT_SCENE_SHAPE_TYPES,
    OBJECT_SCENE_SMALL_DIMENSIONS,
    OBJECT_SCENE_SMALL_SHAPE_TYPES,
)


TASK_ID = "task_three_d__object_scene__camera_distance_extremum_label"
SCENE_ID = "object_scene"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = ("closest_to_camera", "farthest_from_camera")
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("floor_grid_room", "tabletop_room", "studio_platform")
POINT_LABELS: Tuple[str, ...] = tuple("ABCDEFGH")
SMALL_OBJECT_SHAPE_TYPES: Tuple[str, ...] = OBJECT_SCENE_SMALL_SHAPE_TYPES
LARGE_CONTEXT_SHAPE_TYPES: Tuple[str, ...] = OBJECT_SCENE_CONTEXT_SHAPE_TYPES
SHAPE_TYPES: Tuple[str, ...] = OBJECT_SCENE_SHAPE_TYPES
OBJECT_NAME_BY_SHAPE_TYPE: Dict[str, str] = dict(OBJECT_SCENE_NAME_BY_SHAPE_TYPE)
NAMEABLE_SMALL_OBJECT_SHAPE_TYPES: Tuple[str, ...] = OBJECT_SCENE_SMALL_SHAPE_TYPES
NAMEABLE_CONTEXT_SHAPE_TYPES: Tuple[str, ...] = OBJECT_SCENE_CONTEXT_SHAPE_TYPES
POINT_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (224, 71, 61),
    (59, 122, 221),
    (56, 166, 103),
    (153, 82, 205),
    (232, 154, 44),
    (42, 170, 188),
    (213, 78, 139),
    (119, 150, 58),
    (237, 103, 55),
    (83, 104, 216),
    (48, 178, 150),
    (177, 93, 67),
)
CONTEXT_OBJECT_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (150, 105, 72),
    (91, 128, 159),
    (109, 143, 88),
    (157, 101, 139),
    (185, 137, 61),
    (87, 151, 149),
    (164, 91, 74),
    (111, 119, 153),
    (130, 142, 67),
    (177, 111, 111),
    (119, 100, 158),
    (102, 139, 121),
)
CAMERA_YAW_BANDS_DEGREES: Tuple[Tuple[float, float], ...] = (
    (-145.0, -108.0),
    (-82.0, -48.0),
    (-42.0, -20.0),
    (20.0, 42.0),
    (48.0, 82.0),
    (108.0, 145.0),
)


def _object_name(shape_type: str) -> str:
    return str(OBJECT_NAME_BY_SHAPE_TYPE.get(str(shape_type), str(shape_type).replace("_", " ")))


def _nameable_for_prompt(shape_type: str, *, object_role: str) -> bool:
    if str(object_role) == "context":
        return str(shape_type) in set(NAMEABLE_CONTEXT_SHAPE_TYPES)
    return str(shape_type) in set(NAMEABLE_SMALL_OBJECT_SHAPE_TYPES)


@dataclass(frozen=True)
class _CameraSpec:
    camera_position: Tuple[float, float, float]
    target: Tuple[float, float, float]
    right: Tuple[float, float, float]
    up: Tuple[float, float, float]
    forward: Tuple[float, float, float]
    yaw_degrees: float
    pitch_degrees: float
    distance: float


@dataclass(frozen=True)
class _ProjectionFrame:
    scale: float
    center_x: float
    center_y: float
    normalized_center_u: float
    normalized_center_v: float


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    room_extent: float
    room_height: float
    grid_step: float
    marker_radius_px: int
    label_font_size_px: int
    line_width_px: int
    floor_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    edge_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    full_bleed_floor: bool
    full_bleed_floor_extent_multiplier: float


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    point_bboxes_px: Dict[str, List[float]]
    point_centers_px: Dict[str, List[float]]
    object_bboxes_px: Dict[str, List[float]]
    object_centers_px: Dict[str, List[float]]
    context_object_bboxes_px: Dict[str, List[float]]
    context_object_centers_px: Dict[str, List[float]]
    room_bbox_px: List[float]
    evidence_bboxes: List[List[float]]
    evidence_entity_ids: List[str]






def _bool_value(mapping: Mapping[str, Any], key: str, default: bool) -> bool:
    value = mapping.get(str(key), bool(default))
    if isinstance(value, str):
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _vec_sub(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    return (float(a[0]) - float(b[0]), float(a[1]) - float(b[1]), float(a[2]) - float(b[2]))


def _vec_dot(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1]) + float(a[2]) * float(b[2])


def _vec_cross(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _vec_norm(v: Sequence[float]) -> Tuple[float, float, float]:
    length = max(1e-9, math.sqrt(sum(float(component) * float(component) for component in v)))
    return (float(v[0]) / length, float(v[1]) / length, float(v[2]) / length)


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((float(a[index]) - float(b[index])) ** 2 for index in range(3)))


def _min_pairwise(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 999.0
    return min(abs(float(a) - float(b)) for index, a in enumerate(values) for b in values[index + 1 :])




def _resolve_point_count(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any], instance_seed: int) -> Tuple[int, Dict[str, float]]:
    min_count = int(params.get("point_count_min", group_default(gen_defaults, "point_count_min", 5)))
    max_count = int(params.get("point_count_max", group_default(gen_defaults, "point_count_max", 7)))
    min_count = max(3, min(8, int(min_count)))
    max_count = max(min_count, min(8, int(max_count)))
    support = tuple(range(int(min_count), int(max_count) + 1))
    explicit = params.get("point_count")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported point_count: {selected}")
        return int(selected), {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in support}
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.point_count",
    )
    selected = int(support[abs(int(selection_index)) % len(support)])
    probability = 1.0 / float(len(support))
    return int(selected), {str(value): float(probability) for value in support}


def _resolve_context_object_count(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[int, Dict[str, float]]:
    min_count = int(params.get("context_object_count_min", group_default(gen_defaults, "context_object_count_min", 2)))
    max_count = int(params.get("context_object_count_max", group_default(gen_defaults, "context_object_count_max", 2)))
    min_count = max(0, min(3, int(min_count)))
    max_count = max(min_count, min(3, int(max_count)))
    support = tuple(range(int(min_count), int(max_count) + 1))
    explicit = params.get("context_object_count")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported context_object_count: {selected}")
        return int(selected), {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in support}
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.context_object_count",
    )
    selected = int(support[abs(int(selection_index)) % len(support)])
    probability = 1.0 / float(len(support))
    return int(selected), {str(value): float(probability) for value in support}


def _resolve_render_params(params: Mapping[str, Any], *, render_defaults: Mapping[str, Any]) -> _RenderParams:
    merged = dict(render_defaults)
    merged.update(dict(params))
    return _RenderParams(
        canvas_width=_int_value(merged, "canvas_width", 1180),
        canvas_height=_int_value(merged, "canvas_height", 900),
        scene_margin_left_px=_int_value(merged, "scene_margin_left_px", 70),
        scene_margin_right_px=_int_value(merged, "scene_margin_right_px", 70),
        scene_margin_top_px=_int_value(merged, "scene_margin_top_px", 54),
        scene_margin_bottom_px=_int_value(merged, "scene_margin_bottom_px", 64),
        room_extent=_float_value(merged, "room_extent", 3.2),
        room_height=_float_value(merged, "room_height", 3.0),
        grid_step=_float_value(merged, "grid_step", 0.8),
        marker_radius_px=_int_value(merged, "marker_radius_px", 22),
        label_font_size_px=_int_value(merged, "label_font_size_px", 24),
        line_width_px=_int_value(merged, "line_width_px", 2),
        floor_rgb=_rgb(merged.get("floor_rgb", (232, 239, 242)), (232, 239, 242)),
        grid_rgb=_rgb(merged.get("grid_rgb", (184, 197, 207)), (184, 197, 207)),
        edge_rgb=_rgb(merged.get("edge_rgb", (93, 108, 124)), (93, 108, 124)),
        text_rgb=_rgb(merged.get("text_rgb", (30, 34, 42)), (30, 34, 42)),
        text_stroke_rgb=_rgb(merged.get("text_stroke_rgb", (255, 255, 255)), (255, 255, 255)),
        full_bleed_floor=_bool_value(merged, "full_bleed_floor", False),
        full_bleed_floor_extent_multiplier=_float_value(merged, "full_bleed_floor_extent_multiplier", 3.0),
    )


def _camera_yaw_band_for_instance(instance_seed: int) -> Tuple[float, float]:
    band_index = abs(int(instance_seed)) % len(CAMERA_YAW_BANDS_DEGREES)
    return tuple(float(value) for value in CAMERA_YAW_BANDS_DEGREES[int(band_index)])


def _sample_camera(rng, *, yaw_band_degrees: Tuple[float, float] | None = None) -> _CameraSpec:
    yaw_lower, yaw_upper = (
        tuple(float(value) for value in yaw_band_degrees)
        if yaw_band_degrees is not None
        else tuple(float(value) for value in rng.choice(CAMERA_YAW_BANDS_DEGREES))
    )
    yaw_degrees = float(rng.uniform(float(yaw_lower), float(yaw_upper)))
    pitch_degrees = float(rng.uniform(18.0, 33.0))
    distance = float(rng.uniform(7.2, 8.8))
    yaw = math.radians(float(yaw_degrees))
    pitch = math.radians(float(pitch_degrees))
    target = (0.0, 0.0, 0.72)
    camera_position = (
        float(distance * math.cos(pitch) * math.sin(yaw)),
        float(-distance * math.cos(pitch) * math.cos(yaw)),
        float(target[2] + distance * math.sin(pitch)),
    )
    forward = _vec_norm(_vec_sub(target, camera_position))
    world_up = (0.0, 0.0, 1.0)
    right = _vec_norm(_vec_cross(forward, world_up))
    up = _vec_norm(_vec_cross(right, forward))
    return _CameraSpec(
        camera_position=tuple(camera_position),
        target=tuple(target),
        right=tuple(right),
        up=tuple(up),
        forward=tuple(forward),
        yaw_degrees=float(yaw_degrees),
        pitch_degrees=float(pitch_degrees),
        distance=float(distance),
    )


def _project_normalized(point: Sequence[float], camera: _CameraSpec) -> Tuple[float, float, float, float, float, float]:
    rel = _vec_sub(point, camera.camera_position)
    cx = _vec_dot(rel, camera.right)
    cy = _vec_dot(rel, camera.up)
    cz = max(1e-6, _vec_dot(rel, camera.forward))
    return (float(cx / cz), float(cy / cz), float(cz), float(cx), float(cy), float(_distance(point, camera.camera_position)))


def _stage_reference_points(extent: float) -> List[Tuple[float, float, float]]:
    e = float(extent)
    return [
        (x, y, 0.0)
        for x in (-e, e)
        for y in (-e, e)
    ] + [(0.0, 0.0, 0.0), (0.0, e, 0.0), (0.0, -e, 0.0)]


def _build_projection_frame(
    *,
    camera: _CameraSpec,
    render_params: _RenderParams,
    point_worlds: Sequence[Sequence[float]],
) -> _ProjectionFrame:
    points = list(point_worlds) + _stage_reference_points(render_params.room_extent)
    normalized = [_project_normalized(point, camera) for point in points]
    min_u = min(value[0] for value in normalized)
    max_u = max(value[0] for value in normalized)
    min_v = min(value[1] for value in normalized)
    max_v = max(value[1] for value in normalized)
    usable_width = float(render_params.canvas_width - render_params.scene_margin_left_px - render_params.scene_margin_right_px)
    usable_height = float(render_params.canvas_height - render_params.scene_margin_top_px - render_params.scene_margin_bottom_px)
    scale = min(usable_width / max(0.01, max_u - min_u), usable_height / max(0.01, max_v - min_v))
    return _ProjectionFrame(
        scale=float(scale),
        center_x=float(render_params.scene_margin_left_px + 0.5 * usable_width),
        center_y=float(render_params.scene_margin_top_px + 0.5 * usable_height),
        normalized_center_u=float(0.5 * (min_u + max_u)),
        normalized_center_v=float(0.5 * (min_v + max_v)),
    )


def _project_screen(point: Sequence[float], camera: _CameraSpec, frame: _ProjectionFrame) -> Tuple[float, float, float, float, float, float, float, float]:
    u, v, cz, cx, cy, distance = _project_normalized(point, camera)
    x = float(frame.center_x + (u - frame.normalized_center_u) * frame.scale)
    y = float(frame.center_y - (v - frame.normalized_center_v) * frame.scale)
    return (float(x), float(y), float(u), float(v), float(cz), float(cx), float(cy), float(distance))


def _project_xy(point: Sequence[float], camera: _CameraSpec, frame: _ProjectionFrame) -> Tuple[float, float]:
    projected = _project_screen(point, camera, frame)
    return (float(projected[0]), float(projected[1]))


def _screen_to_normalized(screen_x: float, screen_y: float, frame: _ProjectionFrame) -> Tuple[float, float]:
    u = (float(screen_x) - float(frame.center_x)) / max(1e-9, float(frame.scale)) + float(frame.normalized_center_u)
    v = (float(frame.center_y) - float(screen_y)) / max(1e-9, float(frame.scale)) + float(frame.normalized_center_v)
    return (float(u), float(v))


def _screen_to_floor_xy(
    screen_x: float,
    screen_y: float,
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
) -> Tuple[float, float] | None:
    u, v = _screen_to_normalized(float(screen_x), float(screen_y), frame)
    direction = (
        float(camera.forward[0]) + float(u) * float(camera.right[0]) + float(v) * float(camera.up[0]),
        float(camera.forward[1]) + float(u) * float(camera.right[1]) + float(v) * float(camera.up[1]),
        float(camera.forward[2]) + float(u) * float(camera.right[2]) + float(v) * float(camera.up[2]),
    )
    if float(direction[2]) >= -1e-7:
        return None
    t = -float(camera.camera_position[2]) / float(direction[2])
    if float(t) <= 1e-7:
        return None
    return (
        float(camera.camera_position[0]) + float(t) * float(direction[0]),
        float(camera.camera_position[1]) + float(t) * float(direction[1]),
    )


def _canvas_floor_polygon_xy(
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    render_params: _RenderParams,
) -> List[Tuple[float, float]]:
    width = float(render_params.canvas_width)
    height = float(render_params.canvas_height)
    polygon: List[Tuple[float, float]] = []
    for screen_x, screen_y in ((0.0, 0.0), (width, 0.0), (width, height), (0.0, height)):
        floor_xy = _screen_to_floor_xy(screen_x, screen_y, camera=camera, frame=frame)
        if floor_xy is None:
            return []
        polygon.append(floor_xy)
    return polygon


def _grid_values_for_range(min_value: float, max_value: float, step: float) -> List[float]:
    grid_step = max(0.05, float(step))
    start = math.floor(float(min_value) / grid_step) * grid_step
    end = math.ceil(float(max_value) / grid_step) * grid_step
    count = int(max(1, math.ceil((float(end) - float(start)) / grid_step))) + 1
    return [round(float(start) + index * grid_step, 6) for index in range(count + 1)]


def _dedupe_line_points(points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    unique: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for point in points:
        unique[(round(float(point[0]) * 1_000_000), round(float(point[1]) * 1_000_000))] = (
            float(point[0]),
            float(point[1]),
        )
    return list(unique.values())


def _polygon_axis_line_segment(
    polygon_xy: Sequence[Tuple[float, float]],
    *,
    axis: str,
    value: float,
) -> Tuple[Tuple[float, float], Tuple[float, float]] | None:
    intersections: List[Tuple[float, float]] = []
    eps = 1e-8
    for index, point_a in enumerate(polygon_xy):
        point_b = polygon_xy[(index + 1) % len(polygon_xy)]
        x1, y1 = float(point_a[0]), float(point_a[1])
        x2, y2 = float(point_b[0]), float(point_b[1])
        if str(axis) == "x":
            delta_1 = x1 - float(value)
            delta_2 = x2 - float(value)
            if abs(delta_1) <= eps and abs(delta_2) <= eps:
                intersections.extend([(float(value), y1), (float(value), y2)])
            elif delta_1 * delta_2 <= eps and abs(x2 - x1) > eps:
                t = (float(value) - x1) / (x2 - x1)
                if -eps <= t <= 1.0 + eps:
                    intersections.append((float(value), y1 + t * (y2 - y1)))
        else:
            delta_1 = y1 - float(value)
            delta_2 = y2 - float(value)
            if abs(delta_1) <= eps and abs(delta_2) <= eps:
                intersections.extend([(x1, float(value)), (x2, float(value))])
            elif delta_1 * delta_2 <= eps and abs(y2 - y1) > eps:
                t = (float(value) - y1) / (y2 - y1)
                if -eps <= t <= 1.0 + eps:
                    intersections.append((x1 + t * (x2 - x1), float(value)))
    unique_points = _dedupe_line_points(intersections)
    if len(unique_points) < 2:
        return None
    if str(axis) == "x":
        sorted_points = sorted(unique_points, key=lambda point: float(point[1]))
    else:
        sorted_points = sorted(unique_points, key=lambda point: float(point[0]))
    return (sorted_points[0], sorted_points[-1])


def _base_shape_dimensions(shape_type: str, *, object_role: str = "candidate") -> Tuple[float, float, float]:
    small_dimensions = OBJECT_SCENE_SMALL_DIMENSIONS
    context_dimensions = OBJECT_SCENE_CONTEXT_DIMENSIONS
    dimensions = context_dimensions if str(object_role) == "context" else small_dimensions
    fallback = context_dimensions.get(str(shape_type)) or small_dimensions.get(str(shape_type)) or (0.52, 0.52, 0.52)
    return tuple(float(value) for value in dimensions.get(str(shape_type), fallback))


def _sample_shape_dimensions(
    shape_type: str,
    *,
    object_role: str,
    rng,
) -> Tuple[Tuple[float, float, float], float]:
    base_width, base_depth, base_height = _base_shape_dimensions(str(shape_type), object_role=str(object_role))
    if str(object_role) == "context":
        scale = float(rng.uniform(0.96, 1.20))
    else:
        scale = float(rng.uniform(0.86, 1.16))
    return (
        (
            round(float(base_width * scale), 4),
            round(float(base_depth * scale), 4),
            round(float(base_height * scale), 4),
        ),
        round(float(scale), 4),
    )


def _object_reference_points(spec: Mapping[str, Any]) -> List[Tuple[float, float, float]]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    return [
        (x + dx * width * 0.5, y + dy * depth * 0.5, base_z + z)
        for dx in (-1.0, 1.0)
        for dy in (-1.0, 1.0)
        for z in (0.0, height)
    ] + [(x, y, base_z + height * 0.5)]


def _object_screen_bbox(spec: Mapping[str, Any], camera: _CameraSpec, frame: _ProjectionFrame, *, pad_px: float = 0.0) -> List[float]:
    points = [_project_xy(point, camera, frame) for point in _object_reference_points(spec)]
    return [
        round(float(min(point[0] for point in points) - pad_px), 3),
        round(float(min(point[1] for point in points) - pad_px), 3),
        round(float(max(point[0] for point in points) + pad_px), 3),
        round(float(max(point[1] for point in points) + pad_px), 3),
    ]


def _bbox_intersection_area(a: Sequence[float], b: Sequence[float]) -> float:
    width = max(0.0, min(float(a[2]), float(b[2])) - max(float(a[0]), float(b[0])))
    height = max(0.0, min(float(a[3]), float(b[3])) - max(float(a[1]), float(b[1])))
    return float(width * height)


def _bbox_union(*bboxes: Sequence[float]) -> List[float]:
    return [
        round(float(min(float(bbox[0]) for bbox in bboxes)), 3),
        round(float(min(float(bbox[1]) for bbox in bboxes)), 3),
        round(float(max(float(bbox[2]) for bbox in bboxes)), 3),
        round(float(max(float(bbox[3]) for bbox in bboxes)), 3),
    ]


def _make_object_spec(
    *,
    object_id: str,
    shape_type: str,
    object_role: str,
    xy: Tuple[float, float],
    dimensions_xyz: Tuple[float, float, float],
    dimension_scale: float,
    label: str | None = None,
) -> Dict[str, Any]:
    width, depth, height = (float(value) for value in dimensions_xyz)
    footprint = 0.5 * math.sqrt(float(width) * float(width) + float(depth) * float(depth))
    object_name = _object_name(str(shape_type))
    spec = {
        "object_id": str(object_id),
        "shape_type": str(shape_type),
        "object_name": str(object_name),
        "prompt_name": str(object_name),
        "nameable_for_prompt": bool(_nameable_for_prompt(str(shape_type), object_role=str(object_role))),
        "object_role": str(object_role),
        "is_answer_candidate": bool(label),
        "dimension_scale": round(float(dimension_scale), 4),
        "world_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(height * 0.5), 4)],
        "base_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), 0.0],
        "dimensions_xyz": [round(float(width), 4), round(float(depth), 4), round(float(height), 4)],
        "footprint_radius": round(float(footprint), 4),
    }
    if label is not None:
        spec.update(
            {
                "point_id": f"object_{label}",
                "point_label": str(label),
                "object_label": str(label),
            }
        )
    return spec


def _sample_scene_object_specs(
    *,
    rng,
    candidate_count: int,
    context_object_count: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    candidate_shape_types = list(SMALL_OBJECT_SHAPE_TYPES)
    context_shape_types = list(LARGE_CONTEXT_SHAPE_TYPES)
    rng.shuffle(candidate_shape_types)
    rng.shuffle(context_shape_types)
    candidate_shape_types = candidate_shape_types[: int(candidate_count)]
    context_shape_types = context_shape_types[: int(context_object_count)]
    labels = list(POINT_LABELS[: int(candidate_count)])
    rng.shuffle(labels)
    context_slots = [(-1.85, 0.0), (1.85, 0.0), (0.0, 1.82), (-1.72, 1.72), (1.72, 1.72), (0.0, -1.78)]
    candidate_slots = [
        (x, y)
        for x in (-2.55, -1.28, 0.0, 1.28, 2.55)
        for y in (-2.55, -1.28, 0.0, 1.28, 2.55)
    ]
    rng.shuffle(context_slots)
    rng.shuffle(candidate_slots)
    placed: List[Dict[str, Any]] = []
    context_specs: List[Dict[str, Any]] = []
    candidate_specs: List[Dict[str, Any]] = []

    def place_object(shape_type: str, *, object_role: str, object_id: str, label: str | None, slots: Sequence[Tuple[float, float]]) -> Dict[str, Any]:
        dimensions_xyz, dimension_scale = _sample_shape_dimensions(str(shape_type), object_role=str(object_role), rng=rng)
        width, depth, _height = (float(value) for value in dimensions_xyz)
        footprint = 0.5 * math.sqrt(float(width) * float(width) + float(depth) * float(depth))
        jitter = 0.10 if str(object_role) == "context" else 0.16
        for slot_x, slot_y in slots:
            candidate_xy = (
                float(slot_x + rng.uniform(-jitter, jitter)),
                float(slot_y + rng.uniform(-jitter, jitter)),
            )
            if all(
                math.hypot(candidate_xy[0] - float(item["world_xyz"][0]), candidate_xy[1] - float(item["world_xyz"][1]))
                >= float(footprint + float(item["footprint_radius"]) + 0.10)
                for item in placed
            ):
                return _make_object_spec(
                    object_id=str(object_id),
                    shape_type=str(shape_type),
                    object_role=str(object_role),
                    xy=candidate_xy,
                    dimensions_xyz=dimensions_xyz,
                    dimension_scale=float(dimension_scale),
                    label=label,
                )
        raise ValueError(f"could not place {object_role} 3D object: {shape_type}")

    for index, shape_type in enumerate(context_shape_types):
        spec = place_object(
            str(shape_type),
            object_role="context",
            object_id=f"context_{index}_{shape_type}",
            label=None,
            slots=context_slots,
        )
        context_specs.append(spec)
        placed.append(spec)

    for index, shape_type in enumerate(candidate_shape_types):
        label = str(labels[index])
        spec = place_object(
            str(shape_type),
            object_role="candidate",
            object_id=f"object_{label}",
            label=label,
            slots=candidate_slots,
        )
        candidate_specs.append(spec)
        placed.append(spec)

    if len(candidate_specs) < int(candidate_count):
        raise ValueError("could not sample enough small candidate 3D objects")
    if len(context_specs) < int(context_object_count):
        raise ValueError("could not sample enough large context 3D objects")
    return list(candidate_specs), list(context_specs)


def _build_scene_dataset(
    *,
    query_variant: str,
    scene_variant: str,
    point_count: int,
    context_object_count: int,
    render_params: _RenderParams,
    instance_seed: int,
    camera_yaw_band: Tuple[float, float] | None = None,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    selected_camera_yaw_band = (
        tuple(float(value) for value in camera_yaw_band)
        if camera_yaw_band is not None
        else _camera_yaw_band_for_instance(int(instance_seed))
    )
    for _attempt in range(300):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        point_specs, context_object_specs = _sample_scene_object_specs(
            rng=rng,
            candidate_count=int(point_count),
            context_object_count=int(context_object_count),
        )
        all_specs = list(point_specs) + list(context_object_specs)
        reference_points = [point for spec in all_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        screens = [_project_screen(spec["world_xyz"], camera, frame) for spec in point_specs]
        context_screens = [_project_screen(spec["world_xyz"], camera, frame) for spec in context_object_specs]
        screen_centers = [(screen[0], screen[1]) for screen in screens]
        screen_bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=16.0) for spec in point_specs]
        all_screen_bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=16.0) for spec in all_specs]
        if any(
            math.hypot(a[0] - b[0], a[1] - b[1]) < 54.0
            for index, a in enumerate(screen_centers)
            for b in screen_centers[index + 1 :]
        ):
            continue
        if any(
            _bbox_intersection_area(a, b) > 3200.0
            for index, a in enumerate(screen_bboxes)
            for b in screen_bboxes[index + 1 :]
        ):
            continue
        if any(
            _bbox_intersection_area(a, b) > 9200.0
            for index, a in enumerate(all_screen_bboxes)
            for b in all_screen_bboxes[index + 1 :]
        ):
            continue
        camera_distances = [float(screen[7]) for screen in screens]
        if _min_pairwise(camera_distances) < 0.24:
            continue
        finalized_specs: List[Dict[str, Any]] = []
        for index, spec in enumerate(point_specs):
            screen = screens[index]
            finalized = dict(spec)
            finalized.update(
                {
                    "screen_xy": [round(float(screen[0]), 3), round(float(screen[1]), 3)],
                    "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
                    "camera_distance": round(float(screen[7]), 4),
                }
            )
            finalized_specs.append(finalized)
        finalized_context_specs: List[Dict[str, Any]] = []
        for index, spec in enumerate(context_object_specs):
            screen = context_screens[index]
            finalized = dict(spec)
            finalized.update(
                {
                    "screen_xy": [round(float(screen[0]), 3), round(float(screen[1]), 3)],
                    "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
                    "camera_distance": round(float(screen[7]), 4),
                }
            )
            finalized_context_specs.append(finalized)
        pre_label_sorted_by_distance = sorted(finalized_specs, key=lambda spec: (float(spec["camera_distance"]), str(spec["object_id"])))
        if str(query_variant) == "closest_to_camera":
            answer_object_id = str(pre_label_sorted_by_distance[0]["object_id"])
        else:
            answer_object_id = str(pre_label_sorted_by_distance[-1]["object_id"])
        query_offset = 0 if str(query_variant) == "closest_to_camera" else 3
        answer_label_index = abs(int(instance_seed) + int(query_offset)) % int(point_count)
        answer_label = str(POINT_LABELS[answer_label_index])
        remaining_labels = [str(label) for label in POINT_LABELS[: int(point_count)] if str(label) != answer_label]
        rng.shuffle(remaining_labels)
        relabeled_specs: List[Dict[str, Any]] = []
        for spec in finalized_specs:
            updated = dict(spec)
            label = answer_label if str(updated["object_id"]) == answer_object_id else str(remaining_labels.pop())
            updated.update(
                {
                    "point_id": f"object_{label}",
                    "point_label": str(label),
                    "object_id": f"object_{label}",
                    "object_label": str(label),
                }
            )
            relabeled_specs.append(updated)
        finalized_specs = list(relabeled_specs)
        sorted_by_distance = sorted(finalized_specs, key=lambda spec: (float(spec["camera_distance"]), str(spec["point_label"])))
        answer_spec = next(spec for spec in finalized_specs if str(spec["point_label"]) == str(answer_label))
        return {
            "query_variant": str(query_variant),
            "scene_variant": str(scene_variant),
            "point_count": int(point_count),
            "candidate_count": int(point_count),
            "context_object_count": int(context_object_count),
            "object_count": int(point_count) + int(context_object_count),
            "point_specs": sorted(finalized_specs, key=lambda spec: str(spec["point_label"])),
            "context_object_specs": sorted(finalized_context_specs, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted([*finalized_specs, *finalized_context_specs], key=lambda spec: str(spec["object_id"])),
            "answer_label": str(answer_spec["point_label"]),
            "answer_point_id": str(answer_spec["point_id"]),
            "camera": {
                "camera_position": [round(float(value), 4) for value in camera.camera_position],
                "target": [round(float(value), 4) for value in camera.target],
                "yaw_degrees": round(float(camera.yaw_degrees), 4),
                "yaw_band_degrees": [round(float(value), 4) for value in selected_camera_yaw_band],
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
                "sort_key": "camera_distance",
                "candidate_only": True,
                "camera_distance_order_near_to_far": [str(spec["point_label"]) for spec in sorted_by_distance],
                "shape_order_near_to_far": [str(spec["shape_type"]) for spec in sorted_by_distance],
                "context_object_ids": [str(spec["object_id"]) for spec in sorted(finalized_context_specs, key=lambda spec: str(spec["object_id"]))],
                "context_shape_types": [str(spec["shape_type"]) for spec in sorted(finalized_context_specs, key=lambda spec: str(spec["object_id"]))],
                "unique_camera_distance_margin": round(float(_min_pairwise([float(spec["camera_distance"]) for spec in finalized_specs])), 4),
            },
        }
    raise ValueError("could not construct a valid 3D camera-distance scene")


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


def _draw_line(draw: ImageDraw.ImageDraw, p1: Sequence[float], p2: Sequence[float], *, fill: Tuple[int, int, int], width: int) -> None:
    draw.line((float(p1[0]), float(p1[1]), float(p2[0]), float(p2[1])), fill=fill, width=max(1, int(width)))


def _draw_room(
    draw: ImageDraw.ImageDraw,
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    render_params: _RenderParams,
    scene_variant: str,
) -> Tuple[List[float], List[Dict[str, Any]]]:
    extent = float(render_params.room_extent)
    floor = [
        _project_xy((-extent, -extent, 0.0), camera, frame),
        _project_xy((extent, -extent, 0.0), camera, frame),
        _project_xy((extent, extent, 0.0), camera, frame),
        _project_xy((-extent, extent, 0.0), camera, frame),
    ]
    if str(scene_variant) == "tabletop_room":
        floor_fill = (226, 218, 199)
        border_rgb = (128, 108, 86)
        grid_rgb = (190, 176, 151)
    elif str(scene_variant) == "studio_platform":
        floor_fill = (231, 235, 244)
        border_rgb = (88, 100, 118)
        grid_rgb = (181, 192, 211)
    else:
        floor_fill = render_params.floor_rgb
        border_rgb = render_params.edge_rgb
        grid_rgb = render_params.grid_rgb
    full_bleed = bool(render_params.full_bleed_floor)
    if full_bleed:
        draw.rectangle(
            (0, 0, int(render_params.canvas_width), int(render_params.canvas_height)),
            fill=floor_fill,
        )
    else:
        draw.polygon(floor, fill=floor_fill)
        draw.line(floor + [floor[0]], fill=border_rgb, width=max(1, int(render_params.line_width_px) + 1))

    grid_mode = "bounded_stage"
    grid_world_bbox: List[float] | None = None
    if full_bleed:
        floor_polygon_xy = _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params)
        if floor_polygon_xy:
            grid_mode = "screen_ray_floor_plane"
            min_x = min(float(point[0]) for point in floor_polygon_xy)
            max_x = max(float(point[0]) for point in floor_polygon_xy)
            min_y = min(float(point[1]) for point in floor_polygon_xy)
            max_y = max(float(point[1]) for point in floor_polygon_xy)
            grid_world_bbox = [round(min_x, 4), round(min_y, 4), round(max_x, 4), round(max_y, 4)]
            grid_x_values = _grid_values_for_range(min_x, max_x, float(render_params.grid_step))
            grid_y_values = _grid_values_for_range(min_y, max_y, float(render_params.grid_step))
            for value in grid_y_values:
                segment = _polygon_axis_line_segment(floor_polygon_xy, axis="y", value=float(value))
                if segment is None:
                    continue
                _draw_line(
                    draw,
                    _project_xy((segment[0][0], segment[0][1], 0.0), camera, frame),
                    _project_xy((segment[1][0], segment[1][1], 0.0), camera, frame),
                    fill=grid_rgb,
                    width=render_params.line_width_px,
                )
            for value in grid_x_values:
                segment = _polygon_axis_line_segment(floor_polygon_xy, axis="x", value=float(value))
                if segment is None:
                    continue
                _draw_line(
                    draw,
                    _project_xy((segment[0][0], segment[0][1], 0.0), camera, frame),
                    _project_xy((segment[1][0], segment[1][1], 0.0), camera, frame),
                    fill=grid_rgb,
                    width=render_params.line_width_px,
                )
            grid_extent = max(abs(min_x), abs(max_x), abs(min_y), abs(max_y))
        else:
            grid_mode = "bounded_stage_fallback"
            grid_extent = min(
                float(extent) * max(1.0, float(render_params.full_bleed_floor_extent_multiplier)),
                max(float(extent), float(camera.distance) * 0.74),
            )
            grid_count = int(math.ceil((2.0 * grid_extent) / float(render_params.grid_step)))
            grid_values = [round(-grid_extent + index * float(render_params.grid_step), 6) for index in range(grid_count + 1)]
            if grid_values[-1] < grid_extent:
                grid_values.append(grid_extent)
            grid_values = [max(-grid_extent, min(grid_extent, float(value))) for value in grid_values]
            for value in grid_values:
                _draw_line(
                    draw,
                    _project_xy((-grid_extent, value, 0.0), camera, frame),
                    _project_xy((grid_extent, value, 0.0), camera, frame),
                    fill=grid_rgb,
                    width=render_params.line_width_px,
                )
                _draw_line(
                    draw,
                    _project_xy((value, -grid_extent, 0.0), camera, frame),
                    _project_xy((value, grid_extent, 0.0), camera, frame),
                    fill=grid_rgb,
                    width=render_params.line_width_px,
                )
    else:
        grid_extent = float(extent)
        grid_count = int(math.ceil((2.0 * grid_extent) / float(render_params.grid_step)))
        grid_values = [round(-grid_extent + index * float(render_params.grid_step), 6) for index in range(grid_count + 1)]
        if grid_values[-1] < grid_extent:
            grid_values.append(grid_extent)
        grid_values = [max(-grid_extent, min(grid_extent, float(value))) for value in grid_values]
        for value in grid_values:
            _draw_line(
                draw,
                _project_xy((-grid_extent, value, 0.0), camera, frame),
                _project_xy((grid_extent, value, 0.0), camera, frame),
                fill=grid_rgb,
                width=render_params.line_width_px,
            )
            _draw_line(
                draw,
                _project_xy((value, -grid_extent, 0.0), camera, frame),
                _project_xy((value, grid_extent, 0.0), camera, frame),
                fill=grid_rgb,
                width=render_params.line_width_px,
            )
    platform_points: List[Tuple[float, float]] = []
    if str(scene_variant) == "studio_platform" and not full_bleed:
        platform_points = [
            _project_xy((-2.4, -2.35, 0.03), camera, frame),
            _project_xy((2.4, -2.35, 0.03), camera, frame),
            _project_xy((2.4, 2.35, 0.03), camera, frame),
            _project_xy((-2.4, 2.35, 0.03), camera, frame),
        ]
        draw.line(platform_points + [platform_points[0]], fill=(78, 90, 106), width=max(2, int(render_params.line_width_px) + 1))

    if full_bleed:
        room_bbox = [0.0, 0.0, float(render_params.canvas_width), float(render_params.canvas_height)]
    else:
        all_points = list(floor) + list(platform_points)
        room_bbox = [
            round(float(min(point[0] for point in all_points)), 3),
            round(float(min(point[1] for point in all_points)), 3),
            round(float(max(point[0] for point in all_points)), 3),
            round(float(max(point[1] for point in all_points)), 3),
        ]
    return room_bbox, [
        {
            "entity_id": "open_floor_stage",
            "entity_type": "three_d_open_floor_stage",
            "bbox_px": list(room_bbox),
            "attrs": {
                "scene_variant": str(scene_variant),
                "room_extent": float(extent),
                "full_bleed_floor": bool(full_bleed),
                "grid_extent": float(grid_extent),
                "grid_mode": str(grid_mode),
                "grid_world_bbox": list(grid_world_bbox) if grid_world_bbox is not None else None,
                "has_walls": False,
            },
        }
    ]


def _shade(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(round(float(channel) * float(factor))))) for channel in rgb)


def _tint(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(round(float(channel) + (255.0 - float(channel)) * float(factor))))) for channel in rgb)


def _object_vertices(spec: Mapping[str, Any]) -> Dict[str, Tuple[float, float, float]]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    return {
        f"{sx}{sy}{top}": (x + sx * width * 0.5, y + sy * depth * 0.5, base_z + (height if top else 0.0))
        for sx in (-1, 1)
        for sy in (-1, 1)
        for top in (0, 1)
    }


def _draw_polyline(draw: ImageDraw.ImageDraw, points: Sequence[Sequence[float]], *, fill: Tuple[int, int, int], width: int = 2) -> None:
    for index in range(len(points)):
        start = points[index]
        end = points[(index + 1) % len(points)]
        _draw_line(draw, start, end, fill=fill, width=width)


def _bbox_from_screen_points(points: Sequence[Sequence[float]]) -> List[float]:
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in points])


def _project_face(face: Sequence[Sequence[float]], camera: _CameraSpec, frame: _ProjectionFrame) -> List[Tuple[float, float]]:
    return [_project_xy(point, camera, frame) for point in face]


def _face_distance(face: Sequence[Sequence[float]], camera: _CameraSpec) -> float:
    center = tuple(sum(float(point[index]) for point in face) / float(len(face)) for index in range(3))
    return _distance(center, camera.camera_position)


def _draw_box_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    vertices = _object_vertices(spec)
    sx = 1 if camera.camera_position[0] >= float(spec["world_xyz"][0]) else -1
    sy = 1 if camera.camera_position[1] >= float(spec["world_xyz"][1]) else -1
    faces = [
        (
            [vertices[f"{-sx}{-sy}1"], vertices[f"{sx}{-sy}1"], vertices[f"{sx}{sy}1"], vertices[f"{-sx}{sy}1"]],
            _tint(fill, 0.25),
        ),
        (
            [vertices[f"{sx}{-sy}0"], vertices[f"{sx}{sy}0"], vertices[f"{sx}{sy}1"], vertices[f"{sx}{-sy}1"]],
            _shade(fill, 0.86),
        ),
        (
            [vertices[f"{-sx}{sy}0"], vertices[f"{sx}{sy}0"], vertices[f"{sx}{sy}1"], vertices[f"{-sx}{sy}1"]],
            _shade(fill, 0.72),
        ),
    ]
    projected_points: List[Tuple[float, float]] = []
    for face, color in sorted(faces, key=lambda item: _face_distance(item[0], camera), reverse=True):
        projected = _project_face(face, camera, frame)
        draw.polygon(projected, fill=color)
        _draw_polyline(draw, projected, fill=(28, 35, 45), width=2)
        projected_points.extend(projected)
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected_points])


def _sub_box_spec(
    spec: Mapping[str, Any],
    *,
    offset_xyz: Tuple[float, float, float],
    dimensions_xyz: Tuple[float, float, float],
) -> Dict[str, Any]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    width, depth, height = (float(value) for value in dimensions_xyz)
    cx = float(x + float(offset_xyz[0]))
    cy = float(y + float(offset_xyz[1]))
    base_z = float(offset_xyz[2])
    return {
        **dict(spec),
        "world_xyz": [round(cx, 4), round(cy, 4), round(base_z + height * 0.5, 4)],
        "base_xyz": [round(cx, 4), round(cy, 4), round(base_z, 4)],
        "dimensions_xyz": [round(float(width), 4), round(float(depth), 4), round(float(height), 4)],
    }


def _draw_box_parts_object(
    draw: ImageDraw.ImageDraw,
    parts: Sequence[Mapping[str, Any]],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bboxes: List[List[float]] = []
    for index, part in enumerate(sorted(parts, key=lambda item: _distance(item["world_xyz"], camera.camera_position), reverse=True)):
        part_fill = _tint(fill, 0.06) if index % 2 == 0 else _shade(fill, 0.95)
        bboxes.append(_draw_box_object(draw, part, camera=camera, frame=frame, fill=part_fill))
    return _bbox_union(*bboxes)


def _draw_footprint_prism_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
    footprint_xy: Sequence[Tuple[float, float]],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    base = [(x + px * width * 0.5, y + py * depth * 0.5, base_z) for px, py in footprint_xy]
    top = [(point[0], point[1], base_z + height) for point in base]
    faces: List[Tuple[List[Tuple[float, float, float]], Tuple[int, int, int]]] = [
        (list(top), _tint(fill, 0.22)),
    ]
    for index in range(len(base)):
        next_index = (index + 1) % len(base)
        shade_factor = 0.70 + 0.18 * ((index % 3) / 2.0)
        faces.append(
            (
                [base[index], base[next_index], top[next_index], top[index]],
                _shade(fill, shade_factor),
            )
        )
    projected_points: List[Tuple[float, float]] = []
    for face, color in sorted(faces, key=lambda item: _face_distance(item[0], camera), reverse=True):
        projected = _project_face(face, camera, frame)
        draw.polygon(projected, fill=color)
        _draw_polyline(draw, projected, fill=(28, 35, 45), width=2)
        projected_points.extend(projected)
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected_points])


def _star_footprint_points() -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for index in range(10):
        angle = -math.pi * 0.5 + index * math.pi / 5.0
        radius = 1.0 if index % 2 == 0 else 0.46
        points.append((math.cos(angle) * radius, math.sin(angle) * radius))
    return points


def _hexagon_footprint_points() -> List[Tuple[float, float]]:
    return [
        (math.cos(-math.pi * 0.5 + index * math.pi / 3.0), math.sin(-math.pi * 0.5 + index * math.pi / 3.0))
        for index in range(6)
    ]


def _arrow_footprint_points() -> List[Tuple[float, float]]:
    return [
        (0.0, -1.0),
        (0.74, -0.08),
        (0.25, -0.08),
        (0.25, 1.0),
        (-0.25, 1.0),
        (-0.25, -0.08),
        (-0.74, -0.08),
    ]


def _gear_footprint_points() -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for index in range(24):
        angle = -math.pi * 0.5 + index * math.pi / 12.0
        radius = 1.0 if index % 2 == 0 else 0.76
        points.append((math.cos(angle) * radius, math.sin(angle) * radius))
    return points


def _draw_half_cylinder_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    radius_y = depth * 0.5
    profile = [
        (y - radius_y, base_z),
        *[
            (
                y + math.cos(math.pi - step * math.pi / 8.0) * radius_y,
                base_z + math.sin(math.pi - step * math.pi / 8.0) * height,
            )
            for step in range(1, 8)
        ],
        (y + radius_y, base_z),
    ]
    left_x = x - width * 0.5
    right_x = x + width * 0.5
    left_face = [(left_x, py, pz) for py, pz in profile]
    right_face = [(right_x, py, pz) for py, pz in profile]
    faces: List[Tuple[List[Tuple[float, float, float]], Tuple[int, int, int]]] = [
        (left_face, _shade(fill, 0.76)),
        (right_face, _tint(fill, 0.16)),
    ]
    for index in range(len(profile) - 1):
        faces.append(
            (
                [left_face[index], right_face[index], right_face[index + 1], left_face[index + 1]],
                _shade(fill, 0.74 + 0.16 * (index / max(1, len(profile) - 2))),
            )
        )
    projected_points: List[Tuple[float, float]] = []
    for face, color in sorted(faces, key=lambda item: _face_distance(item[0], camera), reverse=True):
        projected = _project_face(face, camera, frame)
        draw.polygon(projected, fill=color)
        _draw_polyline(draw, projected, fill=(28, 35, 45), width=2)
        projected_points.extend(projected)
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected_points])


def _draw_pyramid_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    base = [
        (x - width * 0.5, y - depth * 0.5, base_z),
        (x + width * 0.5, y - depth * 0.5, base_z),
        (x + width * 0.5, y + depth * 0.5, base_z),
        (x - width * 0.5, y + depth * 0.5, base_z),
    ]
    apex = (x, y, base_z + height)
    faces = [
        ([base[0], base[1], apex], _tint(fill, 0.16)),
        ([base[1], base[2], apex], _shade(fill, 0.88)),
        ([base[2], base[3], apex], _shade(fill, 0.76)),
        ([base[3], base[0], apex], _shade(fill, 0.68)),
    ]
    projected_points: List[Tuple[float, float]] = []
    for face, color in sorted(faces, key=lambda item: _face_distance(item[0], camera), reverse=True):
        projected = _project_face(face, camera, frame)
        draw.polygon(projected, fill=color)
        _draw_polyline(draw, projected, fill=(28, 35, 45), width=2)
        projected_points.extend(projected)
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected_points])


def _draw_wedge_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    left = x - width * 0.5
    right = x + width * 0.5
    front = y - depth * 0.5
    back = y + depth * 0.5
    vertices = [
        (left, front, base_z),
        (right, front, base_z),
        (right, back, base_z),
        (left, back, base_z),
        (left, front, base_z + height),
        (left, back, base_z + height),
    ]
    faces = [
        ([vertices[0], vertices[1], vertices[2], vertices[3]], _shade(fill, 0.70)),
        ([vertices[0], vertices[1], vertices[4]], _tint(fill, 0.16)),
        ([vertices[3], vertices[2], vertices[5]], _shade(fill, 0.76)),
        ([vertices[0], vertices[3], vertices[5], vertices[4]], _shade(fill, 0.86)),
        ([vertices[1], vertices[2], vertices[5], vertices[4]], _tint(fill, 0.24)),
    ]
    projected_points: List[Tuple[float, float]] = []
    for face, color in sorted(faces, key=lambda item: _face_distance(item[0], camera), reverse=True):
        projected = _project_face(face, camera, frame)
        draw.polygon(projected, fill=color)
        _draw_polyline(draw, projected, fill=(28, 35, 45), width=2)
        projected_points.extend(projected)
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected_points])


def _upright_profile_world_points(
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    profile_xz: Sequence[Tuple[float, float]],
) -> List[Tuple[float, float, float]]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
    return [
        (
            x + float(camera.right[0]) * float(px) * width * 0.5,
            y + float(camera.right[1]) * float(px) * width * 0.5,
            base_z + (float(pz) + 1.0) * height * 0.5,
        )
        for px, pz in profile_xz
    ]


def _draw_upright_profile_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
    profile_xz: Sequence[Tuple[float, float]],
    inset_scale: float = 0.70,
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    _width, depth, _height = (float(value) for value in spec["dimensions_xyz"])
    back_dx = -float(camera.forward[0]) * float(depth) * 0.55
    back_dy = -float(camera.forward[1]) * float(depth) * 0.55
    shadow_spec = {
        **dict(spec),
        "world_xyz": [x + back_dx, y + back_dy, spec["world_xyz"][2]],
        "base_xyz": [x + back_dx, y + back_dy, spec["base_xyz"][2]],
    }
    shadow_world = _upright_profile_world_points(shadow_spec, camera=camera, profile_xz=profile_xz)
    face_world = _upright_profile_world_points(spec, camera=camera, profile_xz=profile_xz)
    shadow = _project_face(shadow_world, camera, frame)
    face = _project_face(face_world, camera, frame)
    draw.polygon(shadow, fill=_shade(fill, 0.60))
    draw.polygon(face, fill=_tint(fill, 0.12))
    _draw_polyline(draw, face, fill=(28, 35, 45), width=2)
    if 0.0 < float(inset_scale) < 1.0:
        center_x = sum(point[0] for point in face) / float(len(face))
        center_y = sum(point[1] for point in face) / float(len(face))
        inset = [
            (
                center_x + (point[0] - center_x) * float(inset_scale),
                center_y + (point[1] - center_y) * float(inset_scale),
            )
            for point in face
        ]
        _draw_polyline(draw, inset, fill=_shade(fill, 0.78), width=2)
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in [*shadow, *face]])


def _heart_profile_points() -> List[Tuple[float, float]]:
    raw: List[Tuple[float, float]] = []
    for index in range(40):
        t = (2.0 * math.pi * index) / 40.0
        x = 16.0 * math.sin(t) ** 3
        y = 13.0 * math.cos(t) - 5.0 * math.cos(2.0 * t) - 2.0 * math.cos(3.0 * t) - math.cos(4.0 * t)
        raw.append((x, y))
    min_y = min(point[1] for point in raw)
    max_y = max(point[1] for point in raw)
    return [
        (float(x) / 17.0, ((float(y) - min_y) / max(1e-6, max_y - min_y)) * 2.0 - 1.0)
        for x, y in raw
    ]


def _draw_shield_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (-0.78, 1.0),
        (0.78, 1.0),
        (0.92, 0.36),
        (0.54, -0.66),
        (0.0, -1.0),
        (-0.54, -0.66),
        (-0.92, 0.36),
    ]
    return _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=fill,
        profile_xz=profile,
        inset_scale=0.68,
    )


def _draw_heart_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    return _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=fill,
        profile_xz=_heart_profile_points(),
        inset_scale=0.0,
    )


def _draw_diamond_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    waist_z = base_z + height * 0.52
    top = (x, y, base_z + height)
    bottom = (x, y, base_z)
    waist = [
        (x - width * 0.5, y, waist_z),
        (x, y - depth * 0.5, waist_z),
        (x + width * 0.5, y, waist_z),
        (x, y + depth * 0.5, waist_z),
    ]
    faces: List[Tuple[List[Tuple[float, float, float]], Tuple[int, int, int]]] = []
    for index in range(4):
        faces.append(([top, waist[index], waist[(index + 1) % 4]], _tint(fill, 0.10 + 0.08 * (index % 2))))
        faces.append(([bottom, waist[(index + 1) % 4], waist[index]], _shade(fill, 0.62 + 0.08 * (index % 2))))
    projected_points: List[Tuple[float, float]] = []
    for face, color in sorted(faces, key=lambda item: _face_distance(item[0], camera), reverse=True):
        projected = _project_face(face, camera, frame)
        draw.polygon(projected, fill=color)
        _draw_polyline(draw, projected, fill=(28, 35, 45), width=2)
        projected_points.extend(projected)
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected_points])


def _draw_sword_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    parts = [
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, depth * 0.42, 0.0),
                dimensions_xyz=(width * 0.22, depth * 1.16, height * 0.64),
            ),
            (198, 207, 214),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, -depth * 0.20, 0.0),
                dimensions_xyz=(width * 1.22, depth * 0.10, height * 0.70),
            ),
            _tint(fill, 0.08),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, -depth * 0.36, 0.0),
                dimensions_xyz=(width * 0.34, depth * 0.22, height * 0.58),
            ),
            (106, 75, 48),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, -depth * 0.45, 0.0),
                dimensions_xyz=(width * 0.58, depth * 0.10, height * 0.62),
            ),
            _shade(fill, 0.72),
        ),
    ]
    bboxes: List[List[float]] = []
    for part, color in sorted(parts, key=lambda item: _distance(item[0]["world_xyz"], camera.camera_position), reverse=True):
        bboxes.append(_draw_box_object(draw, part, camera=camera, frame=frame, fill=color))
    return _bbox_union(*bboxes)


def _draw_key_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    floor_rgb: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    key_fill = (196, 157, 54)
    bow = _sub_box_spec(
        spec,
        offset_xyz=(0.0, -depth * 0.36, 0.0),
        dimensions_xyz=(width * 0.76, width * 0.76, height * 0.36),
    )
    parts = [
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, depth * 0.12, 0.0),
                dimensions_xyz=(width * 0.16, depth * 0.88, height * 0.52),
            ),
            _tint(key_fill, 0.08),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(width * 0.16, depth * 0.46, 0.0),
                dimensions_xyz=(width * 0.36, depth * 0.12, height * 0.54),
            ),
            _shade(key_fill, 0.86),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(-width * 0.13, depth * 0.56, 0.0),
                dimensions_xyz=(width * 0.30, depth * 0.11, height * 0.54),
            ),
            _shade(key_fill, 0.78),
        ),
    ]
    bboxes: List[List[float]] = [
        _draw_torus_object(draw, bow, camera=camera, frame=frame, fill=key_fill, floor_rgb=floor_rgb)
    ]
    for part, color in sorted(parts, key=lambda item: _distance(item[0]["world_xyz"], camera.camera_position), reverse=True):
        bboxes.append(_draw_box_object(draw, part, camera=camera, frame=frame, fill=color))
    return _bbox_union(*bboxes)


def _draw_crown_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (-0.90, -1.0),
        (0.90, -1.0),
        (0.82, 0.18),
        (0.45, -0.05),
        (0.25, 0.96),
        (0.0, 0.20),
        (-0.25, 0.96),
        (-0.45, -0.05),
        (-0.82, 0.18),
    ]
    return _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=(204, 164, 56),
        profile_xz=profile,
        inset_scale=0.78,
    )


def _draw_hourglass_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    glass_profile = [
        (-0.64, 0.82),
        (0.64, 0.82),
        (0.32, 0.22),
        (0.08, 0.02),
        (0.32, -0.22),
        (0.64, -0.82),
        (-0.64, -0.82),
        (-0.32, -0.22),
        (-0.08, 0.02),
        (-0.32, 0.22),
    ]
    glass_world = _upright_profile_world_points(spec, camera=camera, profile_xz=glass_profile)
    glass = _project_face(glass_world, camera, frame)
    draw.polygon(glass, fill=(218, 230, 226))
    _draw_polyline(draw, glass, fill=(50, 60, 64), width=2)

    sand_fill = (210, 164, 82)
    sand_profiles = [
        [(-0.44, 0.62), (0.44, 0.62), (0.12, 0.10), (-0.12, 0.10)],
        [(-0.44, -0.70), (0.44, -0.70), (0.24, -0.36), (0.0, -0.18), (-0.24, -0.36)],
    ]
    bboxes: List[List[float]] = [_bbox_union(*[[point[0], point[1], point[0], point[1]] for point in glass])]
    for profile in sand_profiles:
        projected = _project_face(_upright_profile_world_points(spec, camera=camera, profile_xz=profile), camera, frame)
        draw.polygon(projected, fill=sand_fill)
        _draw_polyline(draw, projected, fill=(128, 92, 48), width=1)
        bboxes.append(_bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected]))

    frame_parts = [
        (
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.88), dimensions_xyz=(width * 0.96, depth * 0.30, height * 0.10)),
            (116, 80, 48),
        ),
        (
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.96, depth * 0.30, height * 0.10)),
            (116, 80, 48),
        ),
        (
            _sub_box_spec(spec, offset_xyz=(-width * 0.40, 0.0, height * 0.08), dimensions_xyz=(width * 0.10, depth * 0.24, height * 0.84)),
            (96, 66, 42),
        ),
        (
            _sub_box_spec(spec, offset_xyz=(width * 0.40, 0.0, height * 0.08), dimensions_xyz=(width * 0.10, depth * 0.24, height * 0.84)),
            (96, 66, 42),
        ),
    ]
    for part, color in sorted(frame_parts, key=lambda item: _distance(item[0]["world_xyz"], camera.camera_position), reverse=True):
        bboxes.append(_draw_box_object(draw, part, camera=camera, frame=frame, fill=color))
    waist_top = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.0, 0.10)])[0], camera, frame)
    waist_bottom = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.0, -0.18)])[0], camera, frame)
    _draw_line(draw, waist_top, waist_bottom, fill=sand_fill, width=2)
    bboxes.append(
        [
            min(waist_top[0], waist_bottom[0]),
            min(waist_top[1], waist_bottom[1]),
            max(waist_top[0], waist_bottom[0]),
            max(waist_top[1], waist_bottom[1]),
        ]
    )
    return _bbox_union(*bboxes)


def _draw_anchor_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (0.0, 1.0),
        (0.20, 0.86),
        (0.12, 0.70),
        (0.12, 0.24),
        (0.74, 0.24),
        (0.74, 0.04),
        (0.20, 0.04),
        (0.20, -0.36),
        (0.42, -0.20),
        (0.66, -0.18),
        (0.90, -0.34),
        (0.78, -0.56),
        (0.56, -0.76),
        (0.30, -0.90),
        (0.0, -0.98),
        (-0.30, -0.90),
        (-0.56, -0.76),
        (-0.78, -0.56),
        (-0.90, -0.34),
        (-0.66, -0.18),
        (-0.42, -0.20),
        (-0.20, -0.36),
        (-0.20, 0.04),
        (-0.74, 0.04),
        (-0.74, 0.24),
        (-0.12, 0.24),
        (-0.12, 0.70),
        (-0.20, 0.86),
    ]
    return _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=fill,
        profile_xz=profile,
        inset_scale=0.0,
    )


def _draw_horseshoe_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (-0.88, 0.88),
        (-0.50, 0.88),
        (-0.50, -0.20),
        (-0.34, -0.56),
        (0.0, -0.70),
        (0.34, -0.56),
        (0.50, -0.20),
        (0.50, 0.88),
        (0.88, 0.88),
        (0.88, -0.32),
        (0.64, -0.74),
        (0.32, -0.96),
        (0.0, -1.0),
        (-0.32, -0.96),
        (-0.64, -0.74),
        (-0.88, -0.32),
    ]
    return _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=(156, 162, 171),
        profile_xz=profile,
        inset_scale=0.0,
    )


def _draw_hammer_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    parts = [
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, -depth * 0.10, 0.0),
                dimensions_xyz=(width * 0.18, depth * 0.92, height * 0.60),
            ),
            (118, 82, 48),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, depth * 0.36, 0.0),
                dimensions_xyz=(width * 1.08, depth * 0.22, height * 0.76),
            ),
            (174, 181, 188),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(-width * 0.38, depth * 0.38, 0.0),
                dimensions_xyz=(width * 0.34, depth * 0.15, height * 0.68),
            ),
            (152, 160, 168),
        ),
    ]
    bboxes: List[List[float]] = []
    for part, color in sorted(parts, key=lambda item: _distance(item[0]["world_xyz"], camera.camera_position), reverse=True):
        bboxes.append(_draw_box_object(draw, part, camera=camera, frame=frame, fill=color))
    return _bbox_union(*bboxes)


def _draw_bell_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (-0.86, -1.0),
        (0.86, -1.0),
        (0.94, -0.76),
        (0.78, -0.52),
        (0.62, 0.16),
        (0.36, 0.72),
        (0.0, 0.96),
        (-0.36, 0.72),
        (-0.62, 0.16),
        (-0.78, -0.52),
        (-0.94, -0.76),
    ]
    body_bbox = _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=(196, 152, 48),
        profile_xz=profile,
        inset_scale=0.76,
    )
    rim = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.70, -0.80), (0.70, -0.80)])
    clapper_center = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.72)])[0]
    clapper_radius = max(3.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.035)
    draw.line(rim, fill=(116, 82, 28), width=3)
    draw.ellipse(
        (
            clapper_center[0] - clapper_radius,
            clapper_center[1] - clapper_radius,
            clapper_center[0] + clapper_radius,
            clapper_center[1] + clapper_radius,
        ),
        fill=(116, 82, 28),
        outline=(74, 52, 22),
        width=1,
    )
    return _bbox_union(
        body_bbox,
        _bbox_from_screen_points(rim),
        [
            clapper_center[0] - clapper_radius,
            clapper_center[1] - clapper_radius,
            clapper_center[0] + clapper_radius,
            clapper_center[1] + clapper_radius,
        ],
    )


def _draw_trophy_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (-0.90, 0.72),
        (-0.74, 0.96),
        (0.74, 0.96),
        (0.90, 0.72),
        (0.72, 0.30),
        (0.48, 0.06),
        (0.22, -0.08),
        (0.16, -0.52),
        (0.56, -0.52),
        (0.56, -0.74),
        (0.80, -0.74),
        (0.80, -1.0),
        (-0.80, -1.0),
        (-0.80, -0.74),
        (-0.56, -0.74),
        (-0.56, -0.52),
        (-0.16, -0.52),
        (-0.22, -0.08),
        (-0.48, 0.06),
        (-0.72, 0.30),
    ]
    return _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=(210, 168, 54),
        profile_xz=profile,
        inset_scale=0.76,
    )


def _draw_open_book_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
) -> List[float]:
    bboxes: List[List[float]] = []
    faces = [
        ([(-1.02, -0.88), (-0.08, -1.00), (0.00, 0.84), (-0.92, 1.00)], (112, 72, 56), (72, 48, 38)),
        ([(0.08, -1.00), (1.02, -0.88), (0.92, 1.00), (0.00, 0.84)], (112, 72, 56), (72, 48, 38)),
        ([(-0.88, -0.74), (-0.08, -0.88), (-0.02, 0.70), (-0.80, 0.84)], (237, 230, 204), (140, 116, 86)),
        ([(0.08, -0.88), (0.88, -0.74), (0.80, 0.84), (0.02, 0.70)], (246, 238, 213), (140, 116, 86)),
    ]
    for profile, face_fill, outline in faces:
        projected = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=profile)
        draw.polygon(projected, fill=face_fill)
        _draw_polyline(draw, projected, fill=outline, width=2)
        bboxes.append(_bbox_from_screen_points(projected))
    spine = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.90), (0.0, 0.78)])
    draw.line(spine, fill=(92, 62, 48), width=3)
    bboxes.append(_bbox_from_screen_points(spine))
    for pz in (-0.48, -0.20, 0.08, 0.36):
        left_line = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.16, pz - 0.04), (-0.68, pz + 0.04)])
        right_line = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.16, pz - 0.04), (0.68, pz + 0.04)])
        draw.line(left_line, fill=(176, 162, 132), width=1)
        draw.line(right_line, fill=(176, 162, 132), width=1)
        bboxes.extend([_bbox_from_screen_points(left_line), _bbox_from_screen_points(right_line)])
    return _bbox_union(*bboxes)


def _draw_dumbbell_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    shaft = _sub_box_spec(
        spec,
        offset_xyz=(0.0, 0.0, 0.0),
        dimensions_xyz=(width * 0.96, depth * 0.18, height * 0.34),
    )
    left = _sub_box_spec(
        spec,
        offset_xyz=(-width * 0.44, 0.0, 0.0),
        dimensions_xyz=(width * 0.22, depth * 0.66, height * 0.58),
    )
    right = _sub_box_spec(
        spec,
        offset_xyz=(width * 0.44, 0.0, 0.0),
        dimensions_xyz=(width * 0.22, depth * 0.66, height * 0.58),
    )
    parts = [
        (shaft, _shade(fill, 0.86), "box"),
        (left, _tint(fill, 0.08), "cylinder"),
        (right, _tint(fill, 0.08), "cylinder"),
    ]
    bboxes: List[List[float]] = []
    for part, color, kind in sorted(parts, key=lambda item: _distance(item[0]["world_xyz"], camera.camera_position), reverse=True):
        if str(kind) == "cylinder":
            bboxes.append(_draw_cylinder_object(draw, part, camera=camera, frame=frame, fill=color))
        else:
            bboxes.append(_draw_box_object(draw, part, camera=camera, frame=frame, fill=color))
    return _bbox_union(*bboxes)


def _draw_mushroom_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    stem_profile = [(-0.24, -1.0), (0.24, -1.0), (0.32, -0.08), (0.18, 0.12), (-0.18, 0.12), (-0.32, -0.08)]
    cap_profile = [
        (-0.98, -0.02),
        (-0.84, 0.34),
        (-0.54, 0.70),
        (-0.16, 0.88),
        (0.18, 0.88),
        (0.56, 0.70),
        (0.86, 0.34),
        (0.98, -0.02),
        (0.58, -0.20),
        (0.18, -0.26),
        (-0.18, -0.26),
        (-0.58, -0.20),
    ]
    stem = _project_face(_upright_profile_world_points(spec, camera=camera, profile_xz=stem_profile), camera, frame)
    cap = _project_face(_upright_profile_world_points(spec, camera=camera, profile_xz=cap_profile), camera, frame)
    draw.polygon(stem, fill=(232, 218, 181))
    _draw_polyline(draw, stem, fill=(105, 82, 58), width=2)
    draw.polygon(cap, fill=(174, 75, 58))
    _draw_polyline(draw, cap, fill=(80, 50, 42), width=2)
    gill_a = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(-0.56, -0.18)])[0], camera, frame)
    gill_b = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.56, -0.18)])[0], camera, frame)
    _draw_line(draw, gill_a, gill_b, fill=(118, 80, 58), width=2)
    bboxes = [
        _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in stem]),
        _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in cap]),
    ]
    for px, pz, radius_scale in [(-0.46, 0.34, 0.045), (0.0, 0.58, 0.055), (0.46, 0.30, 0.040)]:
        center = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(px, pz)])[0], camera, frame)
        radius = max(2.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * radius_scale)
        spot_bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
        draw.ellipse(tuple(spot_bbox), fill=(244, 232, 204), outline=(126, 86, 68), width=1)
        bboxes.append(spot_bbox)
    return _bbox_union(*bboxes)


def _draw_lantern_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    body_profile = [
        (-0.66, -0.90),
        (0.66, -0.90),
        (0.58, -0.60),
        (0.48, 0.46),
        (0.26, 0.66),
        (0.18, 0.82),
        (-0.18, 0.82),
        (-0.26, 0.66),
        (-0.48, 0.46),
        (-0.58, -0.60),
    ]
    bbox = _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=(94, 74, 50),
        profile_xz=body_profile,
        inset_scale=0.86,
    )
    width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
    glass_spec = _sub_box_spec(
        spec,
        offset_xyz=(0.0, 0.0, height * 0.16),
        dimensions_xyz=(
            width * 0.52,
            float(spec["dimensions_xyz"][1]) * 0.20,
            height * 0.52,
        ),
    )
    glass_world = _upright_profile_world_points(
        glass_spec,
        camera=camera,
        profile_xz=[(-0.62, -0.74), (0.62, -0.74), (0.62, 0.74), (-0.62, 0.74)],
    )
    glass = _project_face(glass_world, camera, frame)
    draw.polygon(glass, fill=(244, 205, 108))
    _draw_polyline(draw, glass, fill=(52, 43, 34), width=2)
    for px in (-0.30, 0.30):
        bottom = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(px, -0.72)])[0], camera, frame)
        top = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(px * 0.72, 0.62)])[0], camera, frame)
        _draw_line(draw, bottom, top, fill=(42, 35, 30), width=2)
    handle_points = []
    for index in range(13):
        t = math.pi * index / 12.0
        px = math.cos(t) * 0.42
        pz = 0.82 + math.sin(t) * 0.42
        handle_points.append(_project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(px, pz)])[0], camera, frame))
    _draw_polyline(draw, handle_points, fill=(42, 35, 30), width=3)
    flame = [
        (0.0, 0.26),
        (0.20, -0.12),
        (0.0, -0.36),
        (-0.20, -0.12),
    ]
    flame_projected = _project_face(_upright_profile_world_points(glass_spec, camera=camera, profile_xz=flame), camera, frame)
    draw.polygon(flame_projected, fill=(255, 238, 156))
    return _bbox_union(
        bbox,
        *[[point[0], point[1], point[0], point[1]] for point in [*glass, *handle_points, *flame_projected]],
    )


def _draw_wrench_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    metal = (171, 181, 188)
    parts = [
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, -depth * 0.14, 0.0),
                dimensions_xyz=(width * 0.20, depth * 0.96, height * 0.64),
            ),
            _shade(metal, 0.96),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(0.0, depth * 0.34, 0.0),
                dimensions_xyz=(width * 0.58, depth * 0.18, height * 0.70),
            ),
            _tint(metal, 0.08),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(-width * 0.26, depth * 0.52, 0.0),
                dimensions_xyz=(width * 0.20, depth * 0.36, height * 0.72),
            ),
            _tint(metal, 0.12),
        ),
        (
            _sub_box_spec(
                spec,
                offset_xyz=(width * 0.26, depth * 0.52, 0.0),
                dimensions_xyz=(width * 0.20, depth * 0.36, height * 0.72),
            ),
            _shade(metal, 0.88),
        ),
    ]
    bboxes: List[List[float]] = []
    for part, color in sorted(parts, key=lambda item: _distance(item[0]["world_xyz"], camera.camera_position), reverse=True):
        bboxes.append(_draw_box_object(draw, part, camera=camera, frame=frame, fill=color))
    return _bbox_union(*bboxes)


def _oval_profile_points(count: int = 32, *, x_scale: float = 1.0, z_scale: float = 1.0) -> List[Tuple[float, float]]:
    return [
        (
            math.cos(2.0 * math.pi * index / float(count)) * float(x_scale),
            math.sin(2.0 * math.pi * index / float(count)) * float(z_scale),
        )
        for index in range(int(count))
    ]


def _draw_padlock_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.92, depth, height * 0.62))
    body_bbox = _draw_box_object(draw, body, camera=camera, frame=frame, fill=(188, 142, 55))
    shackle_points = _project_face(
        _upright_profile_world_points(
            spec,
            camera=camera,
            profile_xz=[(-0.44, -0.10), (-0.44, 0.50), (-0.26, 0.82), (0.0, 0.94), (0.26, 0.82), (0.44, 0.50), (0.44, -0.10)],
        ),
        camera,
        frame,
    )
    draw.line(shackle_points, fill=(166, 174, 181), width=5, joint="curve")
    draw.line(shackle_points, fill=(64, 73, 82), width=2, joint="curve")
    center = _project_xy(_upright_profile_world_points(body, camera=camera, profile_xz=[(0.0, -0.12)])[0], camera, frame)
    bottom = _project_xy(_upright_profile_world_points(body, camera=camera, profile_xz=[(0.0, -0.38)])[0], camera, frame)
    radius = max(3.0, float(frame.scale) * width * 0.035)
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(48, 38, 28))
    _draw_line(draw, center, bottom, fill=(48, 38, 28), width=2)
    return _bbox_union(body_bbox, _bbox_from_screen_points(shackle_points), [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius], [bottom[0], bottom[1], bottom[0], bottom[1]])


def _draw_magnifying_glass_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
    floor_rgb: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    lens = _sub_box_spec(
        spec,
        offset_xyz=(-width * 0.18, -depth * 0.18, 0.0),
        dimensions_xyz=(width * 0.64, width * 0.64, height * 0.90),
    )
    handle = _sub_box_spec(
        spec,
        offset_xyz=(width * 0.18, depth * 0.24, 0.0),
        dimensions_xyz=(width * 0.15, depth * 0.68, height * 0.72),
    )
    lens_bbox = _draw_torus_object(draw, lens, camera=camera, frame=frame, fill=(110, 141, 164), floor_rgb=floor_rgb)
    cx, cy = _project_xy(lens["world_xyz"], camera, frame)
    radius = max(7.0, _radius_px_for_object(lens, camera, frame) * 0.40)
    draw.ellipse((cx - radius, cy - radius * 0.62, cx + radius, cy + radius * 0.62), fill=(202, 226, 235), outline=(80, 102, 120), width=1)
    handle_bbox = _draw_box_object(draw, handle, camera=camera, frame=frame, fill=(91, 69, 48))
    return _bbox_union(lens_bbox, handle_bbox)


def _draw_candle_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    wax = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, -height * 0.08), dimensions_xyz=(width * 0.32, depth * 0.32, height * 0.72))
    wax_bbox = _draw_cylinder_object(draw, wax, camera=camera, frame=frame, fill=(238, 225, 181))
    flame_profile = [(0.0, 1.0), (0.30, 0.24), (0.12, -0.42), (0.0, -0.76), (-0.12, -0.42), (-0.30, 0.24)]
    flame_spec = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.62), dimensions_xyz=(width * 0.34, depth * 0.14, height * 0.58))
    flame = _project_face(_upright_profile_world_points(flame_spec, camera=camera, profile_xz=flame_profile), camera, frame)
    draw.polygon(flame, fill=(244, 132, 46))
    _draw_polyline(draw, flame, fill=(135, 71, 32), width=1)
    inner_flame = _project_face(_upright_profile_world_points(flame_spec, camera=camera, profile_xz=[(0.0, 0.58), (0.12, 0.02), (0.0, -0.42), (-0.12, 0.02)]), camera, frame)
    draw.polygon(inner_flame, fill=(255, 213, 88))
    wick_top = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.0, 0.48)])[0], camera, frame)
    wick_bottom = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.0, 0.32)])[0], camera, frame)
    _draw_line(draw, wick_bottom, wick_top, fill=(42, 35, 28), width=2)
    return _bbox_union(wax_bbox, _bbox_from_screen_points(flame), _bbox_from_screen_points(inner_flame), _bbox_from_screen_points([wick_top, wick_bottom]))


def _draw_scroll_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    sheet = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.10), dimensions_xyz=(width * 0.78, depth * 0.48, height * 0.42))
    left_roll = _sub_box_spec(spec, offset_xyz=(-width * 0.42, 0.0, 0.0), dimensions_xyz=(width * 0.22, depth * 0.64, height * 0.86))
    right_roll = _sub_box_spec(spec, offset_xyz=(width * 0.42, 0.0, 0.0), dimensions_xyz=(width * 0.22, depth * 0.64, height * 0.86))
    bboxes = [
        _draw_box_object(draw, sheet, camera=camera, frame=frame, fill=(232, 216, 176)),
        _draw_cylinder_object(draw, left_roll, camera=camera, frame=frame, fill=(206, 184, 137)),
        _draw_cylinder_object(draw, right_roll, camera=camera, frame=frame, fill=(206, 184, 137)),
    ]
    for offset in (-0.18, 0.0, 0.18):
        p1 = _project_xy((float(spec["world_xyz"][0]) - width * 0.25, float(spec["world_xyz"][1]) + offset * depth, height * 0.55), camera, frame)
        p2 = _project_xy((float(spec["world_xyz"][0]) + width * 0.25, float(spec["world_xyz"][1]) + offset * depth, height * 0.55), camera, frame)
        _draw_line(draw, p1, p2, fill=(151, 120, 78), width=1)
        bboxes.append(_bbox_from_screen_points([p1, p2]))
    return _bbox_union(*bboxes)


def _draw_paint_brush_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    parts = [
        (_sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.16, 0.0), dimensions_xyz=(width * 0.16, depth * 0.86, height * 0.52)), (119, 77, 42)),
        (_sub_box_spec(spec, offset_xyz=(0.0, depth * 0.28, 0.0), dimensions_xyz=(width * 0.26, depth * 0.24, height * 0.58)), (166, 174, 180)),
        (_sub_box_spec(spec, offset_xyz=(0.0, depth * 0.48, 0.0), dimensions_xyz=(width * 0.42, depth * 0.20, height * 0.62)), _shade(fill, 0.72)),
    ]
    bboxes = []
    for part, color in sorted(parts, key=lambda item: _distance(item[0]["world_xyz"], camera.camera_position), reverse=True):
        bboxes.append(_draw_box_object(draw, part, camera=camera, frame=frame, fill=color))
    return _bbox_union(*bboxes)


def _draw_paint_palette_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.90, -0.28), (-0.76, 0.42), (-0.24, 0.90), (0.46, 0.78), (0.92, 0.24), (0.72, -0.42), (0.16, -0.82), (-0.50, -0.72)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(184, 132, 75), profile_xz=profile, inset_scale=0.0)
    points_for_bbox = []
    for px, pz, color in [(-0.38, 0.18, (214, 65, 58)), (0.04, 0.40, (64, 137, 205)), (0.32, 0.04, (77, 158, 91)), (-0.10, -0.30, (230, 190, 60))]:
        center = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(px, pz)])[0], camera, frame)
        radius = max(3.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.035)
        draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=color, outline=(44, 46, 50), width=1)
        points_for_bbox.extend([(center[0] - radius, center[1] - radius), (center[0] + radius, center[1] + radius)])
    hole = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.46, 0.46)])[0], camera, frame)
    radius = max(4.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.045)
    draw.ellipse((hole[0] - radius, hole[1] - radius, hole[0] + radius, hole[1] + radius), fill=(246, 248, 247), outline=(70, 54, 42), width=1)
    points_for_bbox.extend([(hole[0] - radius, hole[1] - radius), (hole[0] + radius, hole[1] + radius)])
    return _bbox_union(bbox, _bbox_from_screen_points(points_for_bbox))


def _draw_goblet_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.68, 0.92), (0.68, 0.92), (0.50, 0.18), (0.20, -0.08), (0.12, -0.58), (0.54, -0.72), (0.54, -0.96), (-0.54, -0.96), (-0.54, -0.72), (-0.12, -0.58), (-0.20, -0.08), (-0.50, 0.18)]
    return _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(204, 163, 65), profile_xz=profile, inset_scale=0.76)


def _draw_teapot_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.74, depth * 0.86, height * 0.78))
    lid = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.58), dimensions_xyz=(width * 0.38, depth * 0.42, height * 0.16))
    spout = _sub_box_spec(spec, offset_xyz=(width * 0.43, -depth * 0.04, height * 0.22), dimensions_xyz=(width * 0.38, depth * 0.14, height * 0.22))
    bboxes = [
        _draw_sphere_object(draw, body, camera=camera, frame=frame, fill=_tint(fill, 0.10)),
        _draw_cylinder_object(draw, lid, camera=camera, frame=frame, fill=_shade(fill, 0.82)),
        _draw_wedge_object(draw, spout, camera=camera, frame=frame, fill=_shade(fill, 0.90)),
    ]
    handle_points = _project_face(
        _upright_profile_world_points(
            spec,
            camera=camera,
            profile_xz=[(-0.48, 0.22), (-0.74, 0.12), (-0.82, -0.18), (-0.66, -0.46), (-0.42, -0.38)],
        ),
        camera,
        frame,
    )
    draw.line(handle_points, fill=_shade(fill, 0.68), width=5, joint="curve")
    draw.line(handle_points, fill=(42, 48, 54), width=2, joint="curve")
    bboxes.append(_bbox_from_screen_points(handle_points))
    return _bbox_union(*bboxes)


def _draw_watering_can_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(-width * 0.06, 0.0, 0.0), dimensions_xyz=(width * 0.66, depth * 0.76, height * 0.62))
    spout = _sub_box_spec(spec, offset_xyz=(width * 0.42, depth * 0.18, height * 0.20), dimensions_xyz=(width * 0.44, depth * 0.14, height * 0.18))
    top = _sub_box_spec(spec, offset_xyz=(-width * 0.10, 0.0, height * 0.52), dimensions_xyz=(width * 0.32, depth * 0.38, height * 0.16))
    bboxes = [
        _draw_cylinder_object(draw, body, camera=camera, frame=frame, fill=_tint(fill, 0.08)),
        _draw_wedge_object(draw, spout, camera=camera, frame=frame, fill=_shade(fill, 0.90)),
        _draw_cylinder_object(draw, top, camera=camera, frame=frame, fill=_shade(fill, 0.82)),
    ]
    handle = _project_face(
        _upright_profile_world_points(spec, camera=camera, profile_xz=[(-0.52, -0.22), (-0.80, 0.06), (-0.66, 0.54), (-0.20, 0.70), (0.22, 0.54)]),
        camera,
        frame,
    )
    draw.line(handle, fill=_shade(fill, 0.70), width=5, joint="curve")
    draw.line(handle, fill=(42, 50, 54), width=2, joint="curve")
    bboxes.append(_bbox_from_screen_points(handle))
    return _bbox_union(*bboxes)


def _draw_basket_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_open_box_object(draw, spec, camera=camera, frame=frame, fill=(170, 116, 58))
    handle = _project_face(
        _upright_profile_world_points(spec, camera=camera, profile_xz=[(-0.72, -0.05), (-0.46, 0.68), (0.0, 0.94), (0.46, 0.68), (0.72, -0.05)]),
        camera,
        frame,
    )
    draw.line(handle, fill=(120, 80, 46), width=4, joint="curve")
    draw.line(handle, fill=(54, 40, 30), width=1, joint="curve")
    for px in (-0.34, 0.0, 0.34):
        top = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(px, -0.12)])[0], camera, frame)
        bottom = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(px, -0.72)])[0], camera, frame)
        _draw_line(draw, top, bottom, fill=(124, 83, 48), width=1)
    return _bbox_union(bbox, _bbox_from_screen_points(handle))


def _draw_mail_envelope_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.94, -0.66), (0.94, -0.66), (0.94, 0.66), (-0.94, 0.66)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(232, 220, 185), profile_xz=profile, inset_scale=0.0)
    line_profiles = [
        [(-0.90, 0.58), (0.0, -0.08), (0.90, 0.58)],
        [(-0.90, -0.58), (0.0, -0.08), (0.90, -0.58)],
    ]
    line_points = []
    for profile_points in line_profiles:
        projected = _project_face(_upright_profile_world_points(spec, camera=camera, profile_xz=profile_points), camera, frame)
        draw.line(projected, fill=(140, 116, 78), width=2)
        line_points.extend(projected)
    return _bbox_union(bbox, _bbox_from_screen_points(line_points))


def _draw_camera_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth, height * 0.72))
    lens = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.20, height * 0.02), dimensions_xyz=(width * 0.48, depth * 0.40, height * 0.52))
    top = _sub_box_spec(spec, offset_xyz=(-width * 0.24, 0.0, height * 0.52), dimensions_xyz=(width * 0.28, depth * 0.38, height * 0.18))
    bboxes = [
        _draw_box_object(draw, body, camera=camera, frame=frame, fill=(53, 63, 76)),
        _draw_cylinder_object(draw, lens, camera=camera, frame=frame, fill=(42, 48, 58)),
        _draw_box_object(draw, top, camera=camera, frame=frame, fill=(78, 91, 108)),
    ]
    cx, cy = _project_xy(lens["world_xyz"], camera, frame)
    radius = max(6.0, _radius_px_for_object(lens, camera, frame) * 0.46)
    outer = (cx - radius, cy - radius * 0.76, cx + radius, cy + radius * 0.76)
    inner_radius = radius * 0.56
    inner = (cx - inner_radius, cy - inner_radius * 0.72, cx + inner_radius, cy + inner_radius * 0.72)
    draw.ellipse(outer, fill=(26, 32, 40), outline=(8, 12, 18), width=2)
    draw.ellipse(inner, fill=(94, 133, 163), outline=(155, 183, 202), width=1)
    flash = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.48, 0.42), (0.70, 0.42), (0.70, 0.64), (0.48, 0.64)])
    viewfinder = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.64, 0.32), (-0.38, 0.32), (-0.38, 0.54), (-0.64, 0.54)])
    draw.polygon(flash, fill=(226, 229, 213), outline=(23, 30, 38))
    draw.polygon(viewfinder, fill=(82, 105, 124), outline=(23, 30, 38))
    return _bbox_union(*bboxes, list(outer), _bbox_from_screen_points(flash), _bbox_from_screen_points(viewfinder))


def _draw_compass_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(225, 209, 154), profile_xz=_oval_profile_points(36), inset_scale=0.82)
    needle = _project_face(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.0, 0.70), (0.12, -0.06), (0.0, -0.72), (-0.12, -0.06)]), camera, frame)
    draw.polygon(needle[:2] + [needle[3]], fill=(202, 56, 52))
    draw.polygon([needle[1], needle[2], needle[3]], fill=(48, 68, 96))
    _draw_polyline(draw, needle, fill=(28, 35, 45), width=1)
    return _bbox_union(bbox, _bbox_from_screen_points(needle))


def _draw_flask_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.26, 0.92), (0.26, 0.92), (0.22, 0.10), (0.78, -0.74), (0.60, -0.98), (-0.60, -0.98), (-0.78, -0.74), (-0.22, 0.10)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(196, 221, 229), profile_xz=profile, inset_scale=0.0)
    liquid = _project_face(_upright_profile_world_points(spec, camera=camera, profile_xz=[(-0.56, -0.72), (0.56, -0.72), (0.44, -0.42), (-0.44, -0.42)]), camera, frame)
    draw.polygon(liquid, fill=_tint(fill, 0.18))
    _draw_polyline(draw, liquid, fill=_shade(fill, 0.66), width=1)
    return _bbox_union(bbox, _bbox_from_screen_points(liquid))


def _draw_test_tube_rack_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    rack = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth * 0.72, height * 0.34))
    bboxes = [_draw_box_object(draw, rack, camera=camera, frame=frame, fill=(127, 94, 63))]
    liquid_colors = [(90, 153, 205), (213, 103, 89), (92, 169, 113)]
    for index, px in enumerate((-0.30, 0.0, 0.30)):
        tube = _sub_box_spec(spec, offset_xyz=(width * px, 0.0, height * 0.18), dimensions_xyz=(width * 0.14, depth * 0.24, height * 0.74))
        bboxes.append(_draw_cylinder_object(draw, tube, camera=camera, frame=frame, fill=(207, 226, 232)))
        liquid = _sub_box_spec(spec, offset_xyz=(width * px, 0.0, height * 0.20), dimensions_xyz=(width * 0.12, depth * 0.20, height * 0.30))
        bboxes.append(_draw_cylinder_object(draw, liquid, camera=camera, frame=frame, fill=liquid_colors[index]))
    return _bbox_union(*bboxes)


def _draw_scroll_map_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    z = base_z + height
    sheet_world = [(x - width * 0.50, y - depth * 0.48, z), (x + width * 0.50, y - depth * 0.44, z), (x + width * 0.44, y + depth * 0.50, z), (x - width * 0.46, y + depth * 0.42, z)]
    sheet = _project_face(sheet_world, camera, frame)
    draw.polygon(sheet, fill=(229, 217, 178))
    _draw_polyline(draw, sheet, fill=(118, 90, 60), width=2)
    route_world = [(x - width * 0.30, y - depth * 0.24, z + height * 0.05), (x - width * 0.05, y + depth * 0.04, z + height * 0.05), (x + width * 0.18, y - depth * 0.02, z + height * 0.05), (x + width * 0.32, y + depth * 0.24, z + height * 0.05)]
    route = _project_face(route_world, camera, frame)
    draw.line(route, fill=(81, 118, 154), width=3)
    mark = _project_xy((x + width * 0.34, y + depth * 0.26, z + height * 0.05), camera, frame)
    radius = max(4.0, float(frame.scale) * width * 0.025)
    _draw_line(draw, (mark[0] - radius, mark[1] - radius), (mark[0] + radius, mark[1] + radius), fill=(180, 56, 52), width=2)
    _draw_line(draw, (mark[0] - radius, mark[1] + radius), (mark[0] + radius, mark[1] - radius), fill=(180, 56, 52), width=2)
    return _bbox_union(_bbox_from_screen_points(sheet), _bbox_from_screen_points(route), [mark[0] - radius, mark[1] - radius, mark[0] + radius, mark[1] + radius])


def _draw_microphone_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    head = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.48), dimensions_xyz=(width * 0.70, depth * 0.72, height * 0.42))
    handle = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.22, depth * 0.28, height * 0.58))
    base = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.72, depth * 0.48, height * 0.10))
    bboxes = [
        _draw_sphere_object(draw, head, camera=camera, frame=frame, fill=(74, 83, 94)),
        _draw_cylinder_object(draw, handle, camera=camera, frame=frame, fill=_shade(fill, 0.70)),
        _draw_cylinder_object(draw, base, camera=camera, frame=frame, fill=(50, 58, 68)),
    ]
    for pz in (0.58, 0.72, 0.86):
        p1 = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(-0.30, pz)])[0], camera, frame)
        p2 = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.30, pz)])[0], camera, frame)
        _draw_line(draw, p1, p2, fill=(150, 160, 170), width=1)
        bboxes.append(_bbox_from_screen_points([p1, p2]))
    return _bbox_union(*bboxes)


def _draw_stopwatch_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    body_bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(221, 206, 150), profile_xz=_oval_profile_points(36, z_scale=0.88), inset_scale=0.82)
    button = _project_face(_upright_profile_world_points(spec, camera=camera, profile_xz=[(-0.18, 0.86), (0.18, 0.86), (0.18, 1.08), (-0.18, 1.08)]), camera, frame)
    draw.polygon(button, fill=(120, 128, 136))
    _draw_polyline(draw, button, fill=(38, 43, 50), width=1)
    center = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.0, 0.0)])[0], camera, frame)
    hand1 = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.0, 0.46)])[0], camera, frame)
    hand2 = _project_xy(_upright_profile_world_points(spec, camera=camera, profile_xz=[(0.34, -0.18)])[0], camera, frame)
    _draw_line(draw, center, hand1, fill=(43, 50, 60), width=2)
    _draw_line(draw, center, hand2, fill=(43, 50, 60), width=2)
    return _bbox_union(body_bbox, _bbox_from_screen_points(button), _bbox_from_screen_points([center, hand1, hand2]))


def _upright_screen_points(
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    profile_xz: Sequence[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    return _project_face(_upright_profile_world_points(spec, camera=camera, profile_xz=profile_xz), camera, frame)


def _draw_apple_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (0.0, 0.72),
        (0.22, 0.88),
        (0.58, 0.70),
        (0.78, 0.28),
        (0.68, -0.42),
        (0.34, -0.88),
        (0.0, -0.96),
        (-0.34, -0.88),
        (-0.68, -0.42),
        (-0.78, 0.28),
        (-0.58, 0.70),
        (-0.22, 0.88),
    ]
    body_bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(204, 58, 50), profile_xz=profile, inset_scale=0.72)
    notch = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.18, 0.72), (0.0, 0.60), (0.18, 0.72)])
    stem = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.02, 0.68), (0.16, 1.02)])
    leaf = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.14, 0.86), (0.58, 0.96), (0.28, 0.66)])
    draw.line(notch, fill=(136, 38, 38), width=2)
    draw.line(stem, fill=(84, 57, 32), width=3)
    draw.polygon(leaf, fill=(73, 143, 70))
    _draw_polyline(draw, leaf, fill=(34, 88, 42), width=1)
    return _bbox_union(body_bbox, _bbox_from_screen_points(notch), _bbox_from_screen_points(stem), _bbox_from_screen_points(leaf))


def _draw_carrot_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.58, 0.54), (0.58, 0.54), (0.18, -0.96), (0.0, -1.10), (-0.18, -0.96)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(226, 118, 38), profile_xz=profile, inset_scale=0.0)
    leaves = [
        _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.00, 0.50), (-0.42, 1.02)]),
        _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.00, 0.54), (0.00, 1.12)]),
        _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.00, 0.50), (0.42, 1.02)]),
    ]
    bboxes = [bbox]
    for leaf in leaves:
        draw.line(leaf, fill=(66, 140, 70), width=4)
        bboxes.append(_bbox_from_screen_points(leaf))
    return _bbox_union(*bboxes)


def _draw_pear_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.40, 0.92), (0.40, 0.92), (0.64, 0.42), (0.82, -0.22), (0.48, -0.92), (0.0, -1.04), (-0.48, -0.92), (-0.82, -0.22), (-0.64, 0.42)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(168, 181, 75), profile_xz=profile, inset_scale=0.0)
    stem = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.00, 0.82), (0.12, 1.10)])
    draw.line(stem, fill=(87, 58, 34), width=3)
    return _bbox_union(bbox, _bbox_from_screen_points(stem))


def _draw_fish_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    body_profile = [(-0.52, 0.00), (-0.18, 0.58), (0.48, 0.52), (0.92, 0.00), (0.48, -0.52), (-0.18, -0.58)]
    body_bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(70, 154, 190), profile_xz=body_profile, inset_scale=0.0)
    tail = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.54, 0.00), (-1.02, 0.52), (-0.90, 0.00), (-1.02, -0.52)])
    draw.polygon(tail, fill=(50, 120, 162))
    _draw_polyline(draw, tail, fill=(25, 62, 82), width=2)
    eye = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.62, 0.18)])[0]
    radius = max(2.0, min(4.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.010))
    draw.ellipse((eye[0] - radius, eye[1] - radius, eye[0] + radius, eye[1] + radius), fill=(18, 24, 30))
    return _bbox_union(body_bbox, _bbox_from_screen_points(tail), [eye[0] - radius, eye[1] - radius, eye[0] + radius, eye[1] + radius])


def _draw_leaf_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.94, 0.00), (-0.54, 0.54), (0.00, 0.86), (0.54, 0.54), (0.94, 0.00), (0.54, -0.54), (0.00, -0.86), (-0.54, -0.54)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(82, 153, 75), profile_xz=profile, inset_scale=0.0)
    vein = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.82, 0.00), (0.82, 0.00)])
    draw.line(vein, fill=(44, 98, 52), width=2)
    bboxes = [bbox, _bbox_from_screen_points(vein)]
    for px in (-0.38, 0.05, 0.42):
        for pz in (-0.32, 0.32):
            detail = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px, 0.0), (px + 0.20, pz)])
            draw.line(detail, fill=(55, 114, 60), width=1)
            bboxes.append(_bbox_from_screen_points(detail))
    return _bbox_union(*bboxes)


def _draw_feather_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.10, -0.96), (-0.56, -0.36), (-0.64, 0.30), (-0.26, 0.88), (0.12, 1.00), (0.52, 0.44), (0.46, -0.24)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(173, 183, 155), profile_xz=profile, inset_scale=0.0)
    shaft = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.02, -0.98), (0.10, 0.90)])
    draw.line(shaft, fill=(78, 72, 56), width=2)
    bboxes = [bbox, _bbox_from_screen_points(shaft)]
    for pz in (-0.48, -0.18, 0.12, 0.42):
        left = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.02, pz), (-0.38, pz + 0.15)])
        right = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.04, pz + 0.08), (0.34, pz + 0.24)])
        draw.line(left, fill=(103, 108, 89), width=1)
        draw.line(right, fill=(103, 108, 89), width=1)
        bboxes.extend([_bbox_from_screen_points(left), _bbox_from_screen_points(right)])
    return _bbox_union(*bboxes)


def _draw_shoe_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (-0.94, -0.72),
        (-0.52, -0.82),
        (0.44, -0.82),
        (0.94, -0.60),
        (0.84, -0.34),
        (0.42, -0.14),
        (0.08, 0.10),
        (-0.36, 0.06),
        (-0.70, -0.22),
    ]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(72, 104, 151), profile_xz=profile, inset_scale=0.0)
    sole = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.74, -0.72), (0.58, -0.72), (0.88, -0.58)])
    tongue = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.18, -0.20), (0.18, -0.08), (0.02, 0.08)])
    laces = [
        _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.26, -0.24), (0.18, -0.34)]),
        _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.18, -0.08), (0.28, -0.20)]),
        _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.08, 0.04), (0.36, -0.08)]),
    ]
    heel = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.74, -0.22), (-0.62, -0.62)])
    draw.line(sole, fill=(37, 40, 44), width=3)
    draw.polygon(tongue, fill=(51, 77, 120))
    _draw_polyline(draw, tongue, fill=(30, 43, 66), width=1)
    for lace in laces:
        draw.line(lace, fill=(238, 240, 235), width=2)
    draw.line(heel, fill=(40, 49, 66), width=2)
    return _bbox_union(bbox, _bbox_from_screen_points(sole), _bbox_from_screen_points(tongue), _bbox_from_screen_points(heel), *[_bbox_from_screen_points(lace) for lace in laces])


def _draw_glove_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.76, -0.86), (0.42, -0.86), (0.58, -0.32), (0.92, -0.02), (0.70, 0.28), (0.40, 0.16), (0.36, 0.82), (0.10, 0.94), (-0.08, 0.28), (-0.26, 0.90), (-0.52, 0.80), (-0.48, 0.20), (-0.78, 0.50), (-0.96, 0.24), (-0.66, -0.18)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(135, 85, 159), profile_xz=profile, inset_scale=0.0)
    palm = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.44, -0.40), (0.36, -0.40)])
    draw.line(palm, fill=(76, 48, 92), width=2)
    return _bbox_union(bbox, _bbox_from_screen_points(palm))


def _draw_hat_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    brim = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth, height * 0.18))
    dome_spec = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.10), dimensions_xyz=(width * 0.66, depth * 0.76, height * 0.72))
    brim_bbox = _draw_box_object(draw, brim, camera=camera, frame=frame, fill=(93, 79, 64))
    dome = _draw_upright_profile_object(draw, dome_spec, camera=camera, frame=frame, fill=(139, 108, 72), profile_xz=[(-0.78, -0.82), (0.78, -0.82), (0.62, 0.22), (0.22, 0.80), (-0.22, 0.80), (-0.62, 0.22)], inset_scale=0.0)
    band = _upright_screen_points(dome_spec, camera=camera, frame=frame, profile_xz=[(-0.62, -0.38), (0.62, -0.38)])
    draw.line(band, fill=(55, 45, 39), width=3)
    return _bbox_union(brim_bbox, dome, _bbox_from_screen_points(band))


def _draw_helmet_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.88, -0.18), (-0.72, 0.44), (-0.34, 0.84), (0.28, 0.88), (0.74, 0.54), (0.92, -0.14), (0.64, -0.54), (-0.56, -0.54)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(82, 142, 170), profile_xz=profile, inset_scale=0.0)
    visor = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.56, 0.02), (0.62, 0.02), (0.50, -0.30), (-0.44, -0.30)])
    draw.polygon(visor, fill=(45, 59, 72))
    _draw_polyline(draw, visor, fill=(16, 24, 32), width=1)
    return _bbox_union(bbox, _bbox_from_screen_points(visor))


def _draw_cup_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(-width * 0.06, 0.0, 0.0), dimensions_xyz=(width * 0.76, depth * 0.82, height * 0.86))
    body_bbox = _draw_cylinder_object(draw, body, camera=camera, frame=frame, fill=_tint(fill, 0.10))
    rim_center = _project_xy((float(spec["world_xyz"][0]) - width * 0.06, float(spec["world_xyz"][1]), float(spec["world_xyz"][2]) + height * 0.34), camera, frame)
    rim_radius = max(5.0, _radius_px_for_object(body, camera, frame) * 0.58)
    rim_h = max(4.0, rim_radius * 0.28)
    draw.ellipse(
        (rim_center[0] - rim_radius, rim_center[1] - rim_h, rim_center[0] + rim_radius, rim_center[1] + rim_h),
        outline=(35, 42, 50),
        width=2,
    )
    x0, y0, x1, y1 = (float(value) for value in body_bbox)
    body_w = max(1.0, x1 - x0)
    body_h = max(1.0, y1 - y0)
    side_handle = [
        x1 - body_w * 0.03,
        y0 + body_h * 0.26,
        x1 + body_w * 0.38,
        y0 + body_h * 0.70,
    ]
    draw.arc(tuple(side_handle), start=-82, end=82, fill=(35, 42, 50), width=7)
    draw.arc(tuple(side_handle), start=-82, end=82, fill=_tint(fill, 0.10), width=4)
    top_attach = (float(side_handle[0]) + body_w * 0.04, float(side_handle[1]) + body_h * 0.07)
    bottom_attach = (float(side_handle[0]) + body_w * 0.04, float(side_handle[3]) - body_h * 0.07)
    _draw_line(draw, (x1 - body_w * 0.12, y0 + body_h * 0.34), top_attach, fill=(35, 42, 50), width=2)
    _draw_line(draw, (x1 - body_w * 0.12, y0 + body_h * 0.62), bottom_attach, fill=(35, 42, 50), width=2)
    return _bbox_union(body_bbox, side_handle)


def _draw_bottle_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (-0.34, 0.96),
        (0.34, 0.96),
        (0.34, 0.62),
        (0.56, 0.40),
        (0.62, -0.66),
        (0.42, -0.96),
        (-0.42, -0.96),
        (-0.62, -0.66),
        (-0.56, 0.40),
        (-0.34, 0.62),
    ]
    body_bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(82, 151, 134), profile_xz=profile, inset_scale=0.72)
    label = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.40, -0.38), (0.40, -0.38), (0.40, 0.04), (-0.40, 0.04)])
    cap = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.36, 0.86), (0.36, 0.86), (0.36, 1.02), (-0.36, 1.02)])
    shoulder = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.54, 0.38), (-0.30, 0.56), (0.30, 0.56), (0.54, 0.38)])
    draw.polygon(cap, fill=(58, 67, 74))
    _draw_polyline(draw, cap, fill=(32, 38, 44), width=1)
    draw.polygon(label, fill=(230, 235, 210))
    _draw_polyline(draw, label, fill=(83, 96, 92), width=1)
    draw.line(shoulder, fill=(48, 105, 96), width=1)
    return _bbox_union(body_bbox, _bbox_from_screen_points(label), _bbox_from_screen_points(cap), _bbox_from_screen_points(shoulder))


def _draw_vase_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.30, 0.92), (0.30, 0.92), (0.44, 0.38), (0.72, -0.22), (0.46, -0.92), (-0.46, -0.92), (-0.72, -0.22), (-0.44, 0.38)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(120, 157, 174), profile_xz=profile, inset_scale=0.72)
    return list(bbox)


def _draw_umbrella_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    canopy = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.96, 0.20), (-0.62, 0.68), (0.00, 0.86), (0.62, 0.68), (0.96, 0.20), (0.58, 0.06), (0.20, 0.18), (-0.20, 0.06), (-0.58, 0.18)])
    draw.polygon(canopy, fill=(201, 67, 86))
    _draw_polyline(draw, canopy, fill=(86, 38, 48), width=2)
    shaft = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, 0.14), (0.0, -0.88)])
    hook = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.88), (0.20, -0.98), (0.34, -0.78)])
    draw.line(shaft, fill=(54, 61, 68), width=3)
    draw.line(hook, fill=(54, 61, 68), width=3, joint="curve")
    return _bbox_union(_bbox_from_screen_points(canopy), _bbox_from_screen_points(shaft), _bbox_from_screen_points(hook))


def _draw_scissors_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    left = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.44, -0.60)])[0]
    right = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.44, -0.60)])[0]
    pivot = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.10)])[0]
    blade_a = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.10), (-0.62, 0.70)])
    blade_b = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.10), (0.62, 0.70)])
    radius = max(6.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.050)
    bboxes = []
    for center in (left, right):
        bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
        draw.ellipse(bbox, outline=(46, 55, 64), width=4)
        bboxes.append(bbox)
        _draw_line(draw, center, pivot, fill=(46, 55, 64), width=3)
        bboxes.append(_bbox_from_screen_points([center, pivot]))
    draw.line(blade_a, fill=(166, 174, 181), width=5)
    draw.line(blade_b, fill=(166, 174, 181), width=5)
    draw.ellipse((pivot[0] - radius * 0.32, pivot[1] - radius * 0.32, pivot[0] + radius * 0.32, pivot[1] + radius * 0.32), fill=(92, 100, 110))
    return _bbox_union(*bboxes, _bbox_from_screen_points(blade_a), _bbox_from_screen_points(blade_b))


def _draw_screwdriver_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.22, 0.0), dimensions_xyz=(width * 0.54, depth * 0.38, height * 0.76))
    shaft = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.18, 0.0), dimensions_xyz=(width * 0.18, depth * 0.48, height * 0.42))
    tip = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.46, 0.0), dimensions_xyz=(width * 0.24, depth * 0.16, height * 0.34))
    return _bbox_union(
        _draw_box_object(draw, handle, camera=camera, frame=frame, fill=(188, 77, 54)),
        _draw_box_object(draw, shaft, camera=camera, frame=frame, fill=(157, 166, 174)),
        _draw_wedge_object(draw, tip, camera=camera, frame=frame, fill=(122, 132, 142)),
    )


def _draw_pencil_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.08, 0.0), dimensions_xyz=(width * 0.34, depth * 0.66, height * 0.58))
    eraser = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.46, 0.0), dimensions_xyz=(width * 0.36, depth * 0.16, height * 0.58))
    tip = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.38, 0.0), dimensions_xyz=(width * 0.38, depth * 0.22, height * 0.54))
    return _bbox_union(
        _draw_box_object(draw, body, camera=camera, frame=frame, fill=(219, 176, 63)),
        _draw_box_object(draw, eraser, camera=camera, frame=frame, fill=(210, 105, 124)),
        _draw_cone_object(draw, tip, camera=camera, frame=frame, fill=(182, 139, 83)),
    )


def _draw_fork_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.16, 0.0), dimensions_xyz=(width * 0.18, depth * 0.58, height * 0.46))
    neck = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.20, 0.0), dimensions_xyz=(width * 0.34, depth * 0.14, height * 0.42))
    bboxes = [
        _draw_box_object(draw, handle, camera=camera, frame=frame, fill=(154, 162, 170)),
        _draw_box_object(draw, neck, camera=camera, frame=frame, fill=(176, 184, 190)),
    ]
    for px in (-0.24, 0.0, 0.24):
        tine = _sub_box_spec(spec, offset_xyz=(width * px, depth * 0.42, 0.0), dimensions_xyz=(width * 0.08, depth * 0.30, height * 0.36))
        bboxes.append(_draw_box_object(draw, tine, camera=camera, frame=frame, fill=(184, 192, 198)))
    return _bbox_union(*bboxes)


def _draw_spoon_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.18, 0.0), dimensions_xyz=(width * 0.16, depth * 0.60, height * 0.42))
    bowl = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.32, 0.0), dimensions_xyz=(width * 0.66, depth * 0.32, height * 0.58))
    return _bbox_union(
        _draw_box_object(draw, handle, camera=camera, frame=frame, fill=(156, 166, 176)),
        _draw_upright_profile_object(draw, bowl, camera=camera, frame=frame, fill=(188, 198, 206), profile_xz=_oval_profile_points(32, z_scale=0.72), inset_scale=0.72),
    )


def _draw_spatula_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.20, 0.0), dimensions_xyz=(width * 0.16, depth * 0.58, height * 0.42))
    blade = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.34, 0.0), dimensions_xyz=(width * 0.78, depth * 0.32, height * 0.38))
    slots = []
    blade_bbox = _draw_box_object(draw, blade, camera=camera, frame=frame, fill=(169, 178, 184))
    for px in (-0.22, 0.0, 0.22):
        slot = _upright_screen_points(blade, camera=camera, frame=frame, profile_xz=[(px, -0.36), (px, 0.36)])
        draw.line(slot, fill=(82, 91, 98), width=1)
        slots.append(_bbox_from_screen_points(slot))
    return _bbox_union(_draw_box_object(draw, handle, camera=camera, frame=frame, fill=(109, 84, 58)), blade_bbox, *slots)


def _draw_toothbrush_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.12, 0.0), dimensions_xyz=(width * 0.22, depth * 0.68, height * 0.42))
    head = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.36, height * 0.02), dimensions_xyz=(width * 0.40, depth * 0.20, height * 0.42))
    bboxes = [
        _draw_box_object(draw, handle, camera=camera, frame=frame, fill=(78, 154, 194)),
        _draw_box_object(draw, head, camera=camera, frame=frame, fill=(232, 236, 238)),
    ]
    for px in (-0.18, 0.0, 0.18):
        bristle = _upright_screen_points(head, camera=camera, frame=frame, profile_xz=[(px, 0.12), (px, 0.56)])
        draw.line(bristle, fill=(90, 168, 202), width=2)
        bboxes.append(_bbox_from_screen_points(bristle))
    return _bbox_union(*bboxes)


def _draw_comb_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    spine = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.16, 0.0), dimensions_xyz=(width * 0.34, depth * 0.78, height * 0.56))
    bbox = _draw_box_object(draw, spine, camera=camera, frame=frame, fill=(190, 139, 64))
    bboxes = [bbox]
    x0, y0, x1, y1 = (float(value) for value in bbox)
    comb_w = max(1.0, x1 - x0)
    comb_h = max(1.0, y1 - y0)
    rail_y = y0 + comb_h * 0.22
    _draw_line(draw, (x0 + comb_w * 0.08, rail_y), (x1 - comb_w * 0.08, rail_y), fill=(82, 50, 28), width=5)
    for index in range(6):
        x = x0 + comb_w * (0.18 + index * 0.128)
        tooth = [x, rail_y + comb_h * 0.08, x, y0 + comb_h * 0.86]
        _draw_line(draw, (tooth[0], tooth[1]), (tooth[2], tooth[3]), fill=(82, 50, 28), width=3)
        bboxes.append([x - 1.5, tooth[1], x + 1.5, tooth[3]])
    return _bbox_union(*bboxes)


def _draw_whistle_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(-width * 0.10, 0.0, 0.0), dimensions_xyz=(width * 0.70, depth * 0.72, height * 0.82))
    mouth = _sub_box_spec(spec, offset_xyz=(width * 0.34, 0.0, height * 0.08), dimensions_xyz=(width * 0.34, depth * 0.46, height * 0.36))
    bboxes = [
        _draw_cylinder_object(draw, body, camera=camera, frame=frame, fill=(214, 174, 64)),
        _draw_box_object(draw, mouth, camera=camera, frame=frame, fill=(184, 145, 46)),
    ]
    hole = _upright_screen_points(body, camera=camera, frame=frame, profile_xz=[(-0.06, 0.08)])[0]
    radius = max(4.0, float(frame.scale) * width * 0.035)
    draw.ellipse((hole[0] - radius, hole[1] - radius, hole[0] + radius, hole[1] + radius), fill=(66, 60, 45))
    return _bbox_union(*bboxes, [hole[0] - radius, hole[1] - radius, hole[0] + radius, hole[1] + radius])


def _draw_flashlight_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.12, 0.0), dimensions_xyz=(width * 0.50, depth * 0.62, height * 0.72))
    head = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.32, 0.0), dimensions_xyz=(width * 0.70, depth * 0.28, height * 0.84))
    bboxes = [
        _draw_box_object(draw, body, camera=camera, frame=frame, fill=(63, 73, 86)),
        _draw_cylinder_object(draw, head, camera=camera, frame=frame, fill=(88, 102, 118)),
    ]
    lens = _project_xy(head["world_xyz"], camera, frame)
    radius = max(5.0, _radius_px_for_object(head, camera, frame) * 0.30)
    draw.ellipse((lens[0] - radius, lens[1] - radius * 0.70, lens[0] + radius, lens[1] + radius * 0.70), fill=(232, 224, 148), outline=(52, 61, 72), width=1)
    return _bbox_union(*bboxes, [lens[0] - radius, lens[1] - radius, lens[0] + radius, lens[1] + radius])


def _draw_calculator_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(67, 78, 92), profile_xz=[(-0.72, -0.98), (0.72, -0.98), (0.72, 0.98), (-0.72, 0.98)], inset_scale=0.0)
    display = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.50, 0.54), (0.50, 0.54), (0.50, 0.82), (-0.50, 0.82)])
    draw.polygon(display, fill=(164, 188, 169))
    _draw_polyline(draw, display, fill=(26, 35, 38), width=1)
    bboxes = [bbox, _bbox_from_screen_points(display)]
    for px in (-0.45, -0.15, 0.15, 0.45):
        for pz in (-0.66, -0.40, -0.14, 0.12, 0.36):
            center = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px, pz)])[0]
            radius = max(2.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.017)
            button = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
            draw.rectangle(button, fill=(214, 218, 220), outline=(31, 36, 42), width=1)
            bboxes.append(button)
    return _bbox_union(*bboxes)


def _draw_phone_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(38, 45, 54), profile_xz=[(-0.58, -1.0), (0.58, -1.0), (0.58, 1.0), (-0.58, 1.0)], inset_scale=0.0)
    screen = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.46, -0.74), (0.46, -0.74), (0.46, 0.74), (-0.46, 0.74)])
    draw.polygon(screen, fill=(89, 143, 174))
    _draw_polyline(draw, screen, fill=(18, 24, 30), width=1)
    home = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.88)])[0]
    radius = max(2.6, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.022)
    draw.ellipse((home[0] - radius, home[1] - radius, home[0] + radius, home[1] + radius), fill=(220, 225, 230))
    return _bbox_union(bbox, _bbox_from_screen_points(screen), [home[0] - radius, home[1] - radius, home[0] + radius, home[1] + radius])


def _draw_light_bulb_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    bulb = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.22), dimensions_xyz=(width, depth, height * 0.64))
    base = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.46, depth * 0.46, height * 0.32))
    bboxes = [
        _draw_sphere_object(draw, bulb, camera=camera, frame=frame, fill=(238, 221, 118)),
        _draw_cylinder_object(draw, base, camera=camera, frame=frame, fill=(137, 145, 152)),
    ]
    filament = _upright_screen_points(bulb, camera=camera, frame=frame, profile_xz=[(-0.28, -0.08), (-0.08, 0.12), (0.08, -0.08), (0.28, 0.12)])
    draw.line(filament, fill=(145, 92, 44), width=2)
    return _bbox_union(*bboxes, _bbox_from_screen_points(filament))


def _draw_suitcase_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_box_object(draw, spec, camera=camera, frame=frame, fill=(145, 92, 59))
    handle = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.30, 0.86), (-0.22, 1.06), (0.22, 1.06), (0.30, 0.86)])
    seam = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.76), (0.0, 0.70)])
    draw.line(handle, fill=(63, 45, 34), width=4, joint="curve")
    draw.line(seam, fill=(82, 57, 42), width=2)
    return _bbox_union(bbox, _bbox_from_screen_points(handle), _bbox_from_screen_points(seam))


def _draw_dice_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_box_object(draw, spec, camera=camera, frame=frame, fill=(232, 235, 232))
    x0, y0, x1, y1 = (float(value) for value in bbox)
    dice_w = max(1.0, x1 - x0)
    dice_h = max(1.0, y1 - y0)
    radius = max(2.2, min(4.6, min(dice_w, dice_h) * 0.055))
    bboxes = [bbox]

    def add_pip(cx: float, cy: float) -> None:
        spot = [cx - radius, cy - radius, cx + radius, cy + radius]
        draw.ellipse(spot, fill=(38, 44, 52))
        bboxes.append(spot)

    # Approximate the three visible dice faces: one on top, two on left, three on right.
    add_pip(x0 + dice_w * 0.50, y0 + dice_h * 0.25)
    for cx, cy in ((x0 + dice_w * 0.25, y0 + dice_h * 0.54), (x0 + dice_w * 0.42, y0 + dice_h * 0.76)):
        add_pip(cx, cy)
    for cx, cy in (
        (x0 + dice_w * 0.63, y0 + dice_h * 0.52),
        (x0 + dice_w * 0.75, y0 + dice_h * 0.64),
        (x0 + dice_w * 0.87, y0 + dice_h * 0.76),
    ):
        add_pip(cx, cy)
    return _bbox_union(*bboxes)


def _draw_rocket_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    body = _draw_upright_profile_object(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=(200, 212, 218),
        profile_xz=[(-0.36, -0.70), (0.36, -0.70), (0.42, 0.42), (0.0, 1.04), (-0.42, 0.42)],
        inset_scale=0.0,
    )
    fins = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.34, -0.44), (-0.74, -0.92), (-0.34, -0.80), (0.34, -0.80), (0.74, -0.92), (0.34, -0.44)])
    draw.polygon(fins[:3], fill=(196, 62, 66))
    draw.polygon(fins[3:], fill=(196, 62, 66))
    window = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, 0.26)])[0]
    radius = max(4.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.035)
    draw.ellipse((window[0] - radius, window[1] - radius, window[0] + radius, window[1] + radius), fill=(91, 156, 192), outline=(42, 54, 68), width=1)
    flame = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.20, -0.72), (0.0, -1.14), (0.20, -0.72)])
    draw.polygon(flame, fill=(239, 143, 43))
    return _bbox_union(body, _bbox_from_screen_points(fins), _bbox_from_screen_points(flame), [window[0] - radius, window[1] - radius, window[0] + radius, window[1] + radius])


def _draw_kite_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    diamond = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, 0.98), (0.78, 0.12), (0.0, -0.98), (-0.78, 0.12)])
    draw.polygon(diamond, fill=(224, 91, 78))
    _draw_polyline(draw, diamond, fill=(74, 52, 58), width=2)
    cross_a = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, 0.98), (0.0, -0.98)])
    cross_b = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.78, 0.12), (0.78, 0.12)])
    tail = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.98), (0.16, -1.22), (-0.10, -1.46), (0.12, -1.70)])
    draw.line(cross_a, fill=(242, 220, 164), width=2)
    draw.line(cross_b, fill=(242, 220, 164), width=2)
    draw.line(tail, fill=(56, 65, 74), width=2)
    return _bbox_union(_bbox_from_screen_points(diamond), _bbox_from_screen_points(cross_a), _bbox_from_screen_points(cross_b), _bbox_from_screen_points(tail))


def _draw_paint_can_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.88, depth * 0.88, height * 0.86))
    lid = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.72), dimensions_xyz=(width * 0.90, depth * 0.90, height * 0.12))
    bboxes = [
        _draw_cylinder_object(draw, body, camera=camera, frame=frame, fill=(166, 176, 184)),
        _draw_cylinder_object(draw, lid, camera=camera, frame=frame, fill=(92, 102, 112)),
    ]
    label = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.42, -0.24), (0.42, -0.24), (0.42, 0.24), (-0.42, 0.24)])
    draw.polygon(label, fill=(235, 234, 204))
    _draw_polyline(draw, label, fill=(80, 88, 94), width=1)
    handle = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.52, 0.42), (-0.26, 0.80), (0.26, 0.80), (0.52, 0.42)])
    draw.line(handle, fill=(72, 82, 90), width=3, joint="curve")
    return _bbox_union(*bboxes, _bbox_from_screen_points(label), _bbox_from_screen_points(handle))


def _draw_cactus_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [
        (-0.18, -1.0),
        (0.18, -1.0),
        (0.18, 0.70),
        (0.30, 0.92),
        (0.12, 1.0),
        (-0.12, 1.0),
        (-0.30, 0.92),
        (-0.18, 0.70),
    ]
    trunk_bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(72, 151, 91), profile_xz=profile, inset_scale=0.72)
    bboxes = [trunk_bbox]
    arms = [
        [(-0.18, 0.12), (-0.48, 0.12), (-0.48, 0.52), (-0.68, 0.52), (-0.68, -0.08), (-0.18, -0.08)],
        [(0.18, 0.26), (0.50, 0.26), (0.50, 0.66), (0.70, 0.66), (0.70, 0.06), (0.18, 0.06)],
    ]
    for arm in arms:
        points = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=arm)
        draw.polygon(points, fill=(62, 135, 82))
        _draw_polyline(draw, points, fill=(34, 94, 56), width=2)
        bboxes.append(_bbox_from_screen_points(points))
    for px in (-0.08, 0.0, 0.08):
        stripe = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px, -0.74), (px * 0.6, 0.72)])
        draw.line(stripe, fill=(116, 188, 127), width=1)
        bboxes.append(_bbox_from_screen_points(stripe))
    return _bbox_union(*bboxes)


def _draw_pumpkin_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_sphere_object(draw, spec, camera=camera, frame=frame, fill=(215, 112, 48))
    bboxes = [bbox]
    for px in (-0.50, -0.24, 0.0, 0.24, 0.50):
        groove = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px, -0.62), (px * 0.42, 0.64)])
        draw.line(groove, fill=(143, 73, 38), width=1)
        bboxes.append(_bbox_from_screen_points(groove))
    stem = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.08, 0.58), (0.06, 0.98), (0.18, 0.88), (0.04, 0.56)])
    draw.polygon(stem, fill=(83, 72, 38))
    return _bbox_union(*bboxes, _bbox_from_screen_points(stem))


def _draw_acorn_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    nut_profile = [(-0.52, 0.20), (0.52, 0.20), (0.62, -0.32), (0.18, -0.98), (0.0, -1.08), (-0.18, -0.98), (-0.62, -0.32)]
    cap_profile = [(-0.70, 0.02), (0.70, 0.02), (0.58, 0.44), (0.22, 0.74), (-0.22, 0.74), (-0.58, 0.44)]
    nut = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(152, 94, 45), profile_xz=nut_profile, inset_scale=0.0)
    cap = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=cap_profile)
    draw.polygon(cap, fill=(91, 67, 42))
    _draw_polyline(draw, cap, fill=(48, 38, 26), width=2)
    bboxes = [nut, _bbox_from_screen_points(cap)]
    for px in (-0.46, -0.18, 0.10, 0.38):
        hatch = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px - 0.16, 0.12), (px + 0.18, 0.56)])
        draw.line(hatch, fill=(54, 42, 28), width=1)
        bboxes.append(_bbox_from_screen_points(hatch))
    for px in (-0.36, -0.08, 0.20, 0.48):
        hatch = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px + 0.14, 0.12), (px - 0.16, 0.54)])
        draw.line(hatch, fill=(112, 86, 54), width=1)
        bboxes.append(_bbox_from_screen_points(hatch))
    highlight = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.18, -0.70), (-0.06, -0.18)])
    draw.line(highlight, fill=(190, 126, 66), width=2)
    stem = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.06, 0.66), (0.10, 0.94)])
    draw.line(stem, fill=(68, 50, 30), width=3)
    bboxes.extend([_bbox_from_screen_points(highlight), _bbox_from_screen_points(stem)])
    return _bbox_union(*bboxes)


def _draw_pinecone_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.28, 0.98), (0.28, 0.98), (0.58, 0.38), (0.50, -0.46), (0.18, -0.98), (-0.18, -0.98), (-0.50, -0.46), (-0.58, 0.38)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(121, 83, 48), profile_xz=profile, inset_scale=0.0)
    bboxes = [bbox]
    for pz in (-0.56, -0.24, 0.08, 0.40):
        row = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.38, pz), (0.0, pz + 0.18), (0.38, pz)])
        draw.line(row, fill=(76, 52, 34), width=2)
        bboxes.append(_bbox_from_screen_points(row))
    return _bbox_union(*bboxes)


def _draw_seashell_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.92, -0.52), (-0.72, 0.10), (-0.38, 0.58), (0.0, 0.78), (0.38, 0.58), (0.72, 0.10), (0.92, -0.52), (0.42, -0.84), (-0.42, -0.84)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(222, 188, 145), profile_xz=profile, inset_scale=0.0)
    bboxes = [bbox]
    for px in (-0.52, -0.22, 0.0, 0.22, 0.52):
        rib = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.78), (px, 0.46)])
        draw.line(rib, fill=(154, 113, 86), width=1)
        bboxes.append(_bbox_from_screen_points(rib))
    return _bbox_union(*bboxes)


def _draw_magnet_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.72, 0.82), (-0.34, 0.82), (-0.34, -0.42), (0.34, -0.42), (0.34, 0.82), (0.72, 0.82), (0.72, -0.72), (-0.72, -0.72)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(82, 95, 113), profile_xz=profile, inset_scale=0.0)
    left_tip = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.72, 0.46), (-0.34, 0.46), (-0.34, 0.82), (-0.72, 0.82)])
    right_tip = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.34, 0.46), (0.72, 0.46), (0.72, 0.82), (0.34, 0.82)])
    draw.polygon(left_tip, fill=(202, 58, 58))
    draw.polygon(right_tip, fill=(57, 112, 188))
    return _bbox_union(bbox, _bbox_from_screen_points(left_tip), _bbox_from_screen_points(right_tip))


def _draw_guitar_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.26, 0.0), dimensions_xyz=(width * 0.64, depth * 0.34, height * 1.10))
    neck = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.18, 0.0), dimensions_xyz=(width * 0.14, depth * 0.68, height * 0.58))
    head = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.54, 0.0), dimensions_xyz=(width * 0.32, depth * 0.18, height * 0.62))
    bboxes = [
        _draw_sphere_object(draw, body, camera=camera, frame=frame, fill=(168, 101, 55)),
        _draw_box_object(draw, neck, camera=camera, frame=frame, fill=(92, 57, 38)),
        _draw_box_object(draw, head, camera=camera, frame=frame, fill=(76, 48, 34)),
    ]
    hole = _project_xy(body["world_xyz"], camera, frame)
    radius = max(4.0, _radius_px_for_object(body, camera, frame) * 0.18)
    draw.ellipse((hole[0] - radius, hole[1] - radius * 0.66, hole[0] + radius, hole[1] + radius * 0.66), fill=(42, 30, 24))
    return _bbox_union(*bboxes, [hole[0] - radius, hole[1] - radius, hole[0] + radius, hole[1] + radius])


def _draw_drum_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.92, depth * 0.92, height * 0.86))
    top = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.72), dimensions_xyz=(width * 0.98, depth * 0.98, height * 0.12))
    bboxes = [
        _draw_cylinder_object(draw, body, camera=camera, frame=frame, fill=(170, 76, 63)),
        _draw_cylinder_object(draw, top, camera=camera, frame=frame, fill=(230, 224, 202)),
    ]
    for px in (-0.32, 0.32):
        stripe = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px, -0.56), (px, 0.52)])
        draw.line(stripe, fill=(94, 48, 42), width=2)
        bboxes.append(_bbox_from_screen_points(stripe))
    return _bbox_union(*bboxes)


def _draw_shovel_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.18, 0.0), dimensions_xyz=(width * 0.12, depth * 0.62, height * 0.42))
    blade = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.34, 0.0), dimensions_xyz=(width * 0.70, depth * 0.34, height * 0.66))
    return _bbox_union(
        _draw_box_object(draw, handle, camera=camera, frame=frame, fill=(109, 74, 44)),
        _draw_upright_profile_object(draw, blade, camera=camera, frame=frame, fill=(132, 144, 154), profile_xz=[(-0.62, 0.42), (0.62, 0.42), (0.46, -0.58), (0.0, -0.94), (-0.46, -0.58)], inset_scale=0.0),
    )


def _draw_saw_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    blade = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.08, 0.0), dimensions_xyz=(width * 0.56, depth * 0.76, height * 0.50))
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.42, 0.0), dimensions_xyz=(width * 0.58, depth * 0.22, height * 0.72))
    blade_poly = _upright_screen_points(blade, camera=camera, frame=frame, profile_xz=[(-0.36, -0.78), (0.36, -0.78), (0.42, 0.70), (0.22, 0.52), (0.06, 0.70), (-0.10, 0.52), (-0.26, 0.70), (-0.42, 0.52)])
    draw.polygon(blade_poly, fill=(175, 184, 190))
    _draw_polyline(draw, blade_poly, fill=(70, 80, 88), width=2)
    handle_bbox = _draw_box_object(draw, handle, camera=camera, frame=frame, fill=(124, 72, 44))
    return _bbox_union(_bbox_from_screen_points(blade_poly), handle_bbox)


def _draw_pliers_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    pivot = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, 0.02)])[0]
    left_handle = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.10, -0.08), (-0.58, -0.88)])
    right_handle = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.10, -0.08), (0.58, -0.88)])
    left_jaw = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.04, 0.08), (-0.46, 0.78)])
    right_jaw = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.04, 0.08), (0.46, 0.78)])
    draw.line(left_handle, fill=(177, 70, 62), width=6)
    draw.line(right_handle, fill=(177, 70, 62), width=6)
    draw.line(left_jaw, fill=(148, 158, 166), width=5)
    draw.line(right_jaw, fill=(148, 158, 166), width=5)
    radius = max(3.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.025)
    draw.ellipse((pivot[0] - radius, pivot[1] - radius, pivot[0] + radius, pivot[1] + radius), fill=(76, 84, 92))
    return _bbox_union(_bbox_from_screen_points(left_handle), _bbox_from_screen_points(right_handle), _bbox_from_screen_points(left_jaw), _bbox_from_screen_points(right_jaw), [pivot[0] - radius, pivot[1] - radius, pivot[0] + radius, pivot[1] + radius])


def _draw_telescope_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    tube = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.46, depth * 0.82, height * 0.70))
    lens = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.38, 0.0), dimensions_xyz=(width * 0.60, depth * 0.18, height * 0.82))
    eyepiece = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.42, 0.0), dimensions_xyz=(width * 0.32, depth * 0.14, height * 0.58))
    return _bbox_union(
        _draw_cylinder_object(draw, tube, camera=camera, frame=frame, fill=(65, 87, 115)),
        _draw_cylinder_object(draw, lens, camera=camera, frame=frame, fill=(92, 123, 150)),
        _draw_cylinder_object(draw, eyepiece, camera=camera, frame=frame, fill=(44, 55, 70)),
    )


def _draw_ruler_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_box_object(draw, spec, camera=camera, frame=frame, fill=(218, 185, 88))
    bboxes = [bbox]
    for index, py in enumerate((-0.42, -0.28, -0.14, 0.0, 0.14, 0.28, 0.42)):
        length = 0.62 if index % 2 == 0 else 0.40
        tick = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.34, py), (-0.34 + length, py)])
        draw.line(tick, fill=(89, 72, 42), width=1)
        bboxes.append(_bbox_from_screen_points(tick))
    return _bbox_union(*bboxes)


def _draw_pickaxe_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.18, 0.0), dimensions_xyz=(width * 0.14, depth * 0.72, height * 0.42))
    head = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.38, height * 0.06), dimensions_xyz=(width * 0.96, depth * 0.18, height * 0.44))
    points = _upright_screen_points(head, camera=camera, frame=frame, profile_xz=[(-0.96, 0.14), (-0.26, 0.34), (0.0, 0.06), (0.26, 0.34), (0.96, 0.14), (0.18, -0.16), (0.0, -0.08), (-0.18, -0.16)])
    draw.polygon(points, fill=(137, 148, 158))
    _draw_polyline(draw, points, fill=(53, 62, 70), width=2)
    return _bbox_union(_draw_box_object(draw, handle, camera=camera, frame=frame, fill=(102, 69, 43)), _bbox_from_screen_points(points))


def _draw_paint_roller_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    handle = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.30, 0.0), dimensions_xyz=(width * 0.16, depth * 0.42, height * 0.44))
    roller = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.36, height * 0.04), dimensions_xyz=(width * 0.80, depth * 0.22, height * 0.72))
    wire = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.28), (0.34, 0.10), (0.34, 0.46)])
    draw.line(wire, fill=(88, 98, 106), width=3)
    return _bbox_union(
        _draw_box_object(draw, handle, camera=camera, frame=frame, fill=(87, 65, 47)),
        _draw_cylinder_object(draw, roller, camera=camera, frame=frame, fill=(92, 151, 190)),
        _bbox_from_screen_points(wire),
    )


def _draw_tape_measure_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    body = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(223, 177, 50), profile_xz=[(-0.78, -0.62), (0.54, -0.62), (0.76, -0.20), (0.54, 0.56), (-0.52, 0.66), (-0.78, 0.20)], inset_scale=0.0)
    tape = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.50, -0.06), (1.02, -0.06)])
    draw.line(tape, fill=(235, 229, 175), width=5)
    draw.line(tape, fill=(66, 58, 35), width=1)
    return _bbox_union(body, _bbox_from_screen_points(tape))


def _draw_remote_control_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(54, 62, 74), profile_xz=[(-0.52, -1.0), (0.52, -1.0), (0.52, 1.0), (-0.52, 1.0)], inset_scale=0.0)
    bboxes = [bbox]
    for px, pz, color in [(0.0, 0.66, (196, 55, 55)), (-0.22, 0.26, (216, 221, 224)), (0.22, 0.26, (216, 221, 224)), (-0.22, -0.12, (216, 221, 224)), (0.22, -0.12, (216, 221, 224)), (0.0, -0.52, (91, 148, 184))]:
        center = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px, pz)])[0]
        radius = max(2.4, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.020)
        button = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
        draw.ellipse(button, fill=color, outline=(22, 27, 33), width=1)
        bboxes.append(button)
    return _bbox_union(*bboxes)


def _draw_plug_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(-width * 0.10, 0.0, 0.0), dimensions_xyz=(width * 0.64, depth * 0.72, height * 0.74))
    prong1 = _sub_box_spec(spec, offset_xyz=(width * 0.34, -depth * 0.12, height * 0.08), dimensions_xyz=(width * 0.28, depth * 0.10, height * 0.22))
    prong2 = _sub_box_spec(spec, offset_xyz=(width * 0.34, depth * 0.12, height * 0.08), dimensions_xyz=(width * 0.28, depth * 0.10, height * 0.22))
    return _bbox_union(
        _draw_box_object(draw, body, camera=camera, frame=frame, fill=(52, 60, 70)),
        _draw_box_object(draw, prong1, camera=camera, frame=frame, fill=(168, 174, 178)),
        _draw_box_object(draw, prong2, camera=camera, frame=frame, fill=(168, 174, 178)),
    )


def _draw_wallet_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(112, 74, 48), profile_xz=[(-0.90, -0.58), (0.90, -0.58), (0.90, 0.58), (-0.90, 0.58)], inset_scale=0.0)
    flap = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.82, 0.18), (-0.18, -0.12), (0.82, 0.18)])
    draw.line(flap, fill=(66, 45, 34), width=2)
    return _bbox_union(bbox, _bbox_from_screen_points(flap))


def _draw_purse_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    profile = [(-0.72, -0.80), (0.72, -0.80), (0.58, 0.50), (0.24, 0.72), (-0.24, 0.72), (-0.58, 0.50)]
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(142, 78, 128), profile_xz=profile, inset_scale=0.0)
    handle = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.34, 0.50), (-0.18, 1.02), (0.18, 1.02), (0.34, 0.50)])
    draw.line(handle, fill=(74, 43, 68), width=4, joint="curve")
    return _bbox_union(bbox, _bbox_from_screen_points(handle))


def _draw_sunglasses_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    left = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.46, 0.0)])[0]
    right = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.46, 0.0)])[0]
    radius_x = max(8.0, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.050)
    radius_y = max(5.0, radius_x * 0.58)
    bboxes = []
    for center in (left, right):
        bbox = [center[0] - radius_x, center[1] - radius_y, center[0] + radius_x, center[1] + radius_y]
        draw.ellipse(bbox, fill=(40, 52, 66), outline=(17, 23, 30), width=3)
        bboxes.append(bbox)
    bridge = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.18, 0.02), (0.18, 0.02)])
    arm_l = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.76, 0.00), (-1.00, 0.34)])
    arm_r = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.76, 0.00), (1.00, 0.34)])
    draw.line(bridge, fill=(17, 23, 30), width=3)
    draw.line(arm_l, fill=(17, 23, 30), width=2)
    draw.line(arm_r, fill=(17, 23, 30), width=2)
    return _bbox_union(*bboxes, _bbox_from_screen_points(bridge), _bbox_from_screen_points(arm_l), _bbox_from_screen_points(arm_r))


def _draw_violin_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.20, 0.0), dimensions_xyz=(width * 0.66, depth * 0.42, height * 1.06))
    neck = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.28, 0.0), dimensions_xyz=(width * 0.12, depth * 0.54, height * 0.56))
    body_bbox = _draw_upright_profile_object(draw, body, camera=camera, frame=frame, fill=(157, 83, 43), profile_xz=[(-0.58, 0.64), (-0.30, 0.88), (0.0, 0.62), (0.30, 0.88), (0.58, 0.64), (0.34, 0.10), (0.58, -0.54), (0.18, -0.90), (0.0, -0.62), (-0.18, -0.90), (-0.58, -0.54), (-0.34, 0.10)], inset_scale=0.0)
    strings = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, -0.72), (0.0, 0.98)])
    draw.line(strings, fill=(236, 220, 174), width=2)
    return _bbox_union(body_bbox, _draw_box_object(draw, neck, camera=camera, frame=frame, fill=(75, 48, 34)), _bbox_from_screen_points(strings))


def _draw_trumpet_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    tube = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.08, 0.0), dimensions_xyz=(width * 0.20, depth * 0.70, height * 0.44))
    bell = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.38, 0.0), dimensions_xyz=(width * 0.72, depth * 0.26, height * 0.70))
    mouth = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.50, 0.0), dimensions_xyz=(width * 0.32, depth * 0.12, height * 0.38))
    bboxes = [
        _draw_cylinder_object(draw, tube, camera=camera, frame=frame, fill=(207, 162, 50)),
        _draw_cone_object(draw, bell, camera=camera, frame=frame, fill=(224, 180, 62)),
        _draw_cylinder_object(draw, mouth, camera=camera, frame=frame, fill=(183, 138, 42)),
    ]
    for px in (-0.22, 0.0, 0.22):
        valve = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px, 0.00), (px, 0.28)])
        draw.line(valve, fill=(138, 98, 30), width=2)
        bboxes.append(_bbox_from_screen_points(valve))
    return _bbox_union(*bboxes)


def _draw_donut_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
    floor_rgb: Tuple[int, int, int],
) -> List[float]:
    return _draw_torus_object(draw, spec, camera=camera, frame=frame, fill=(194, 125, 64), floor_rgb=floor_rgb)


def _draw_pretzel_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    left = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.72, 0.06), (-0.58, 0.48), (-0.16, 0.42), (-0.18, 0.02), (-0.54, -0.26), (-0.82, -0.06)])
    right = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.72, 0.06), (0.58, 0.48), (0.16, 0.42), (0.18, 0.02), (0.54, -0.26), (0.82, -0.06)])
    cross = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.54, -0.46), (0.0, 0.10), (0.54, -0.46)])
    for path in (left, right, cross):
        draw.line(path, fill=(154, 93, 45), width=6, joint="curve")
        draw.line(path, fill=(92, 58, 36), width=1, joint="curve")
    return _bbox_union(_bbox_from_screen_points(left), _bbox_from_screen_points(right), _bbox_from_screen_points(cross))


def _draw_lollipop_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    stick = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.12, depth * 0.12, height * 0.62))
    candy = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.44), dimensions_xyz=(width * 0.88, depth * 0.88, height * 0.46))
    swirl = _upright_screen_points(candy, camera=camera, frame=frame, profile_xz=[(-0.34, 0.04), (-0.10, 0.26), (0.20, 0.14), (0.34, -0.12), (0.02, -0.28), (-0.24, -0.10)])
    draw.line(swirl, fill=(242, 238, 244), width=3, joint="curve")
    return _bbox_union(
        _draw_cylinder_object(draw, stick, camera=camera, frame=frame, fill=(232, 226, 190)),
        _draw_sphere_object(draw, candy, camera=camera, frame=frame, fill=(205, 64, 126)),
        _bbox_from_screen_points(swirl),
    )


def _draw_ice_cream_cone_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    cone = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.66, depth * 0.66, height * 0.58))
    scoop = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.46), dimensions_xyz=(width * 0.86, depth * 0.86, height * 0.44))
    hatch1 = _upright_screen_points(cone, camera=camera, frame=frame, profile_xz=[(-0.34, -0.34), (0.34, 0.34)])
    hatch2 = _upright_screen_points(cone, camera=camera, frame=frame, profile_xz=[(0.34, -0.34), (-0.34, 0.34)])
    bboxes = [
        _draw_cone_object(draw, cone, camera=camera, frame=frame, fill=(198, 145, 72)),
        _draw_sphere_object(draw, scoop, camera=camera, frame=frame, fill=(232, 206, 146)),
    ]
    draw.line(hatch1, fill=(125, 82, 42), width=1)
    draw.line(hatch2, fill=(125, 82, 42), width=1)
    return _bbox_union(*bboxes, _bbox_from_screen_points(hatch1), _bbox_from_screen_points(hatch2))


def _draw_soap_bar_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(136, 190, 204), profile_xz=[(-0.84, -0.46), (0.84, -0.46), (0.96, -0.18), (0.74, 0.46), (-0.74, 0.46), (-0.96, -0.18)], inset_scale=0.76)
    shine = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.42, 0.10), (-0.10, 0.24)])
    draw.line(shine, fill=(213, 236, 240), width=2)
    return _bbox_union(bbox, _bbox_from_screen_points(shine))


def _draw_clock_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    body = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(224, 207, 149), profile_xz=_oval_profile_points(48, z_scale=0.92), inset_scale=0.74)
    outer_rim = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=_oval_profile_points(56, z_scale=0.92))
    inner_face = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(x * 0.74, z * 0.74) for x, z in _oval_profile_points(56, z_scale=0.92)])
    _draw_polyline(draw, outer_rim + [outer_rim[0]], fill=(42, 49, 56), width=2)
    _draw_polyline(draw, inner_face + [inner_face[0]], fill=(126, 112, 82), width=1)
    center = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, 0.0)])[0]
    hand1 = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, 0.0), (0.0, 0.46)])
    hand2 = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.0, 0.0), (0.36, -0.16)])
    _draw_line(draw, hand1[0], hand1[1], fill=(45, 52, 60), width=2)
    _draw_line(draw, hand2[0], hand2[1], fill=(45, 52, 60), width=2)
    tick_bboxes = [_bbox_from_screen_points(outer_rim), _bbox_from_screen_points(inner_face)]
    for index in range(12):
        angle = math.pi * 0.5 - index * math.tau / 12.0
        outer_x = math.cos(angle) * 0.66
        outer_z = math.sin(angle) * 0.61
        inner_scale = 0.82 if index % 3 == 0 else 0.90
        tick = _upright_screen_points(
            spec,
            camera=camera,
            frame=frame,
            profile_xz=[(outer_x * inner_scale, outer_z * inner_scale), (outer_x, outer_z)],
        )
        draw.line(tick, fill=(62, 70, 78), width=2 if index % 3 == 0 else 1)
        tick_bboxes.append(_bbox_from_screen_points(tick))
    center_radius = max(2.4, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.018)
    draw.ellipse(
        (
            center[0] - center_radius,
            center[1] - center_radius,
            center[0] + center_radius,
            center[1] + center_radius,
        ),
        fill=(45, 52, 60),
    )
    return _bbox_union(
        body,
        _bbox_from_screen_points([center, hand1[1], hand2[1]]),
        [center[0] - center_radius, center[1] - center_radius, center[0] + center_radius, center[1] + center_radius],
        *tick_bboxes,
    )


def _radius_px_for_object(spec: Mapping[str, Any], camera: _CameraSpec, frame: _ProjectionFrame) -> float:
    x, y, z = (float(value) for value in spec["world_xyz"])
    width, depth, _height = (float(value) for value in spec["dimensions_xyz"])
    center = _project_xy((x, y, z), camera, frame)
    offsets = [
        _project_xy((x + width * 0.5, y, z), camera, frame),
        _project_xy((x - width * 0.5, y, z), camera, frame),
        _project_xy((x, y + depth * 0.5, z), camera, frame),
        _project_xy((x, y - depth * 0.5, z), camera, frame),
    ]
    return max(18.0, max(math.hypot(point[0] - center[0], point[1] - center[1]) for point in offsets))


def _draw_sphere_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, z = (float(value) for value in spec["world_xyz"])
    cx, cy = _project_xy((x, y, z), camera, frame)
    radius = _radius_px_for_object(spec, camera, frame)
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    for step in range(8, 0, -1):
        factor = step / 8.0
        inset = radius * (1.0 - factor)
        color = _tint(fill, 0.10 + (1.0 - factor) * 0.32)
        draw.ellipse((bbox[0] + inset, bbox[1] + inset, bbox[2] - inset, bbox[3] - inset), fill=color)
    draw.ellipse(bbox, outline=(28, 35, 45), width=2)
    highlight = radius * 0.18
    draw.ellipse((cx - radius * 0.38 - highlight, cy - radius * 0.42 - highlight, cx - radius * 0.38 + highlight, cy - radius * 0.42 + highlight), fill=(255, 255, 255))
    return [round(float(value), 3) for value in bbox]


def _draw_cylinder_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    _width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
    base = _project_xy((x, y, base_z), camera, frame)
    top = _project_xy((x, y, base_z + height), camera, frame)
    radius = _radius_px_for_object({**dict(spec), "world_xyz": [x, y, base_z + height * 0.5]}, camera, frame)
    ellipse_h = max(9.0, radius * 0.42)
    side = [(top[0] - radius, top[1]), (top[0] + radius, top[1]), (base[0] + radius, base[1]), (base[0] - radius, base[1])]
    draw.polygon(side, fill=_shade(fill, 0.82))
    draw.ellipse((base[0] - radius, base[1] - ellipse_h, base[0] + radius, base[1] + ellipse_h), fill=_shade(fill, 0.70), outline=(28, 35, 45), width=2)
    draw.ellipse((top[0] - radius, top[1] - ellipse_h, top[0] + radius, top[1] + ellipse_h), fill=_tint(fill, 0.20), outline=(28, 35, 45), width=2)
    _draw_line(draw, (top[0] - radius, top[1]), (base[0] - radius, base[1]), fill=(28, 35, 45), width=2)
    _draw_line(draw, (top[0] + radius, top[1]), (base[0] + radius, base[1]), fill=(28, 35, 45), width=2)
    return _bbox_union(
        [top[0] - radius, top[1] - ellipse_h, top[0] + radius, top[1] + ellipse_h],
        [base[0] - radius, base[1] - ellipse_h, base[0] + radius, base[1] + ellipse_h],
    )


def _draw_cone_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    _width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
    base = _project_xy((x, y, base_z), camera, frame)
    apex = _project_xy((x, y, base_z + height), camera, frame)
    radius = _radius_px_for_object({**dict(spec), "world_xyz": [x, y, base_z + height * 0.25]}, camera, frame)
    ellipse_h = max(8.0, radius * 0.38)
    left = (base[0] - radius, base[1])
    right = (base[0] + radius, base[1])
    draw.polygon([left, right, apex], fill=_shade(fill, 0.84))
    draw.polygon([left, base, apex], fill=_tint(fill, 0.18))
    draw.ellipse((base[0] - radius, base[1] - ellipse_h, base[0] + radius, base[1] + ellipse_h), fill=_shade(fill, 0.72), outline=(28, 35, 45), width=2)
    _draw_line(draw, left, apex, fill=(28, 35, 45), width=2)
    _draw_line(draw, right, apex, fill=(28, 35, 45), width=2)
    return _bbox_union([base[0] - radius, base[1] - ellipse_h, base[0] + radius, base[1] + ellipse_h], [apex[0], apex[1], apex[0], apex[1]])


def _draw_torus_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
    floor_rgb: Tuple[int, int, int],
) -> List[float]:
    x, y, z = (float(value) for value in spec["world_xyz"])
    cx, cy = _project_xy((x, y, z), camera, frame)
    radius = _radius_px_for_object(spec, camera, frame)
    outer_h = max(18.0, radius * 0.64)
    inner_w = radius * 0.48
    inner_h = outer_h * 0.42
    outer = [cx - radius, cy - outer_h, cx + radius, cy + outer_h]
    inner = [cx - inner_w, cy - inner_h, cx + inner_w, cy + inner_h]
    draw.ellipse(outer, fill=_tint(fill, 0.10), outline=(28, 35, 45), width=2)
    draw.ellipse((outer[0] + radius * 0.10, outer[1] + outer_h * 0.18, outer[2] - radius * 0.10, outer[3] - outer_h * 0.20), outline=_shade(fill, 0.74), width=5)
    draw.ellipse(inner, fill=floor_rgb, outline=(28, 35, 45), width=2)
    draw.arc(outer, start=205, end=330, fill=_shade(fill, 0.72), width=5)
    return [round(float(value), 3) for value in outer]


def _draw_arch_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    post_w = width * 0.22
    lintel_h = height * 0.24
    parts = [
        _sub_box_spec(spec, offset_xyz=(-width * 0.34, 0.0, 0.0), dimensions_xyz=(post_w, depth, height)),
        _sub_box_spec(spec, offset_xyz=(width * 0.34, 0.0, 0.0), dimensions_xyz=(post_w, depth, height)),
        _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height - lintel_h), dimensions_xyz=(width, depth, lintel_h)),
    ]
    return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)


def _draw_table_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    top_h = height * 0.18
    leg_w = min(width, depth) * 0.16
    leg_h = height - top_h
    parts = [
        _sub_box_spec(spec, offset_xyz=(sx * width * 0.34, sy * depth * 0.34, 0.0), dimensions_xyz=(leg_w, leg_w, leg_h))
        for sx in (-1.0, 1.0)
        for sy in (-1.0, 1.0)
    ]
    parts.append(_sub_box_spec(spec, offset_xyz=(0.0, 0.0, leg_h), dimensions_xyz=(width, depth, top_h)))
    return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)


def _draw_shelf_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    post_w = width * 0.12
    shelf_h = height * 0.10
    parts = [
        _sub_box_spec(spec, offset_xyz=(-width * 0.42, 0.0, 0.0), dimensions_xyz=(post_w, depth, height)),
        _sub_box_spec(spec, offset_xyz=(width * 0.42, 0.0, 0.0), dimensions_xyz=(post_w, depth, height)),
    ]
    for base_z in (0.0, height * 0.43, height * 0.86):
        parts.append(_sub_box_spec(spec, offset_xyz=(0.0, 0.0, base_z), dimensions_xyz=(width, depth, shelf_h)))
    return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)


def _draw_open_box_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    wall = min(width, depth) * 0.12
    base_h = height * 0.18
    wall_h = (height - base_h) * 0.58
    front_h = (height - base_h) * 0.34
    parts = [
        _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth, base_h)),
        _sub_box_spec(spec, offset_xyz=(-width * 0.5 + wall * 0.5, 0.0, base_h), dimensions_xyz=(wall, depth, wall_h)),
        _sub_box_spec(spec, offset_xyz=(width * 0.5 - wall * 0.5, 0.0, base_h), dimensions_xyz=(wall, depth, wall_h)),
        _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.5 - wall * 0.5, base_h), dimensions_xyz=(width, wall, wall_h)),
        _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.5 + wall * 0.5, base_h), dimensions_xyz=(width, wall, front_h)),
    ]
    return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)


def _draw_pedestal_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    cap_h = height * 0.18
    column_h = height - cap_h * 2.0
    parts = [
        _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth, cap_h)),
        _sub_box_spec(spec, offset_xyz=(0.0, 0.0, cap_h), dimensions_xyz=(width * 0.58, depth * 0.58, column_h)),
        _sub_box_spec(spec, offset_xyz=(0.0, 0.0, cap_h + column_h), dimensions_xyz=(width, depth, cap_h)),
    ]
    return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)


def _draw_cabinet_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    wood = _shade(fill, 0.86)
    bboxes: List[List[float]] = [
        _draw_box_object(
            draw,
            _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth, height)),
            camera=camera,
            frame=frame,
            fill=wood,
        )
    ]
    face_y = y - depth * 0.515 if float(camera.camera_position[1]) <= y else y + depth * 0.515
    x_left = x - width * 0.39
    x_right = x + width * 0.39
    outline = (50, 42, 36)
    handle_rgb = (210, 176, 92)
    for index, lower_frac in enumerate((0.12, 0.31, 0.50, 0.69)):
        drawer_bottom = base_z + height * float(lower_frac)
        drawer_top = drawer_bottom + height * 0.145
        drawer_face = [
            (x_left, face_y, drawer_bottom),
            (x_right, face_y, drawer_bottom),
            (x_right, face_y, drawer_top),
            (x_left, face_y, drawer_top),
        ]
        projected = _project_face(drawer_face, camera, frame)
        draw.polygon(projected, fill=_tint(wood, 0.08 + 0.035 * (index % 2)))
        _draw_polyline(draw, projected, fill=outline, width=2)
        handle_z = (drawer_bottom + drawer_top) * 0.5
        handle = [
            _project_xy((x - width * 0.12, face_y, handle_z), camera, frame),
            _project_xy((x + width * 0.12, face_y, handle_z), camera, frame),
        ]
        _draw_line(draw, handle[0], handle[1], fill=handle_rgb, width=4)
        bboxes.append(_bbox_union(*[[point[0], point[1], point[0], point[1]] for point in [*projected, *handle]]))
    return _bbox_union(*bboxes)


def _draw_sofa_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    parts = [
        _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.08, 0.0), dimensions_xyz=(width * 0.82, depth * 0.66, height * 0.34)),
        _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.36, height * 0.28), dimensions_xyz=(width * 0.90, depth * 0.18, height * 0.66)),
        _sub_box_spec(spec, offset_xyz=(-width * 0.47, -depth * 0.04, 0.0), dimensions_xyz=(width * 0.13, depth * 0.74, height * 0.58)),
        _sub_box_spec(spec, offset_xyz=(width * 0.47, -depth * 0.04, 0.0), dimensions_xyz=(width * 0.13, depth * 0.74, height * 0.58)),
        _sub_box_spec(spec, offset_xyz=(-width * 0.20, -depth * 0.12, height * 0.18), dimensions_xyz=(width * 0.34, depth * 0.52, height * 0.20)),
        _sub_box_spec(spec, offset_xyz=(width * 0.20, -depth * 0.12, height * 0.18), dimensions_xyz=(width * 0.34, depth * 0.52, height * 0.20)),
    ]
    return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)


def _draw_barrel_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    _width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
    base = _project_xy((x, y, base_z), camera, frame)
    mid = _project_xy((x, y, base_z + height * 0.50), camera, frame)
    top = _project_xy((x, y, base_z + height), camera, frame)
    radius = _radius_px_for_object({**dict(spec), "world_xyz": [x, y, base_z + height * 0.5]}, camera, frame)
    top_radius = radius * 0.86
    bulge_radius = radius * 1.08
    ellipse_h = max(10.0, radius * 0.36)
    wood = (154, 99, 48)
    dark_wood = (104, 63, 34)
    hoop = (61, 70, 78)
    outline = (28, 35, 45)
    side = [
        (top[0] - top_radius, top[1]),
        (top[0] + top_radius, top[1]),
        (mid[0] + bulge_radius, mid[1]),
        (base[0] + top_radius, base[1]),
        (base[0] - top_radius, base[1]),
        (mid[0] - bulge_radius, mid[1]),
    ]
    draw.polygon(side, fill=wood)
    draw.polygon(
        [(top[0] - top_radius, top[1]), (mid[0] - bulge_radius, mid[1]), (base[0] - top_radius, base[1]), base, top],
        fill=_shade(wood, 0.78),
    )
    draw.ellipse(
        (base[0] - top_radius, base[1] - ellipse_h, base[0] + top_radius, base[1] + ellipse_h),
        fill=_shade(dark_wood, 0.82),
        outline=outline,
        width=2,
    )
    draw.ellipse(
        (top[0] - top_radius, top[1] - ellipse_h, top[0] + top_radius, top[1] + ellipse_h),
        fill=_tint(wood, 0.18),
        outline=outline,
        width=2,
    )
    for frac in (0.14, 0.30, 0.68, 0.86):
        center = _project_xy((x, y, base_z + height * frac), camera, frame)
        band_radius = radius * (1.05 if 0.28 < frac < 0.72 else 0.96)
        band_h = max(7.0, ellipse_h * 0.62)
        draw.ellipse(
            (center[0] - band_radius, center[1] - band_h, center[0] + band_radius, center[1] + band_h),
            outline=hoop,
            width=6,
        )
    for offset in (-0.52, -0.26, 0.0, 0.26, 0.52):
        top_point = (top[0] + offset * top_radius, top[1] + ellipse_h * 0.20)
        base_point = (base[0] + offset * top_radius, base[1] - ellipse_h * 0.20)
        _draw_line(draw, top_point, base_point, fill=_shade(dark_wood, 0.90), width=2)
    tap_y = float(mid[1] + ellipse_h * 0.08)
    tap_x = float(mid[0] - radius * 0.18)
    tap = [tap_x - radius * 0.10, tap_y - ellipse_h * 0.30, tap_x + radius * 0.24, tap_y + ellipse_h * 0.12]
    draw.rectangle(tap, fill=(201, 154, 75), outline=outline, width=2)
    plug_r = max(3.0, radius * 0.08)
    plug_cx = float(mid[0] + radius * 0.24)
    plug_cy = float(mid[1] - ellipse_h * 0.05)
    draw.ellipse((plug_cx - plug_r, plug_cy - plug_r, plug_cx + plug_r, plug_cy + plug_r), fill=(76, 43, 26), outline=outline, width=1)
    _draw_polyline(draw, side, fill=outline, width=2)
    return _bbox_union(
        [top[0] - top_radius, top[1] - ellipse_h, top[0] + top_radius, top[1] + ellipse_h],
        [mid[0] - bulge_radius, mid[1] - ellipse_h, mid[0] + bulge_radius, mid[1] + ellipse_h],
        [base[0] - top_radius, base[1] - ellipse_h, base[0] + top_radius, base[1] + ellipse_h],
        tap,
    )


def _draw_chair_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    seat_h = height * 0.14
    leg_h = height * 0.42
    leg_w = min(width, depth) * 0.11
    parts = [
        _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.08, leg_h), dimensions_xyz=(width * 0.82, depth * 0.70, seat_h)),
        _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.35, leg_h + seat_h * 0.15), dimensions_xyz=(width * 0.82, depth * 0.15, height * 0.58)),
    ]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            parts.append(
                _sub_box_spec(
                    spec,
                    offset_xyz=(sx * width * 0.32, sy * depth * 0.26, 0.0),
                    dimensions_xyz=(leg_w, leg_w, leg_h),
                )
            )
    return _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)


def _draw_option_label(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    center: Sequence[float],
    font,
) -> List[float]:
    x, y = float(center[0]), float(center[1])
    text_bbox = draw.textbbox((0, 0), str(label), font=font, stroke_width=3)
    width = float(text_bbox[2] - text_bbox[0])
    height = float(text_bbox[3] - text_bbox[1])
    label_bbox = [
        round(x - width * 0.5 - 4.0, 3),
        round(y - height * 0.5 - 5.0, 3),
        round(x + width * 0.5 + 4.0, 3),
        round(y + height * 0.5 + 3.0, 3),
    ]
    draw.text(
        (x - width * 0.5, y - height * 0.5 - 1.0),
        str(label),
        font=font,
        fill=(255, 255, 255),
        stroke_width=3,
        stroke_fill=(24, 29, 38),
    )
    return list(label_bbox)


def render_object_scene_3d(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: _RenderParams,
) -> _RenderedScene:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    camera = _camera_from_dataset(dataset)
    frame = _frame_from_dataset(dataset)
    scene_variant = str(dataset.get("scene_variant", "floor_grid_room"))
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    room_bbox, entities = _draw_room(draw, camera=camera, frame=frame, render_params=render_params, scene_variant=scene_variant)

    point_specs = [dict(spec) for spec in dataset["point_specs"]]
    context_object_specs = [dict(spec) for spec in dataset.get("context_object_specs", [])]
    all_specs = [*point_specs, *context_object_specs]

    def draw_order_key(item: Mapping[str, Any]) -> float:
        return float(item["camera_distance"]) + float(item.get("render_order_bias", 0.0))

    for spec in sorted(all_specs, key=lambda item: float(item["camera_distance"]), reverse=True):
        base = _project_screen(spec["base_xyz"], camera, frame)
        width, depth, _height = (float(value) for value in spec["dimensions_xyz"])
        shadow_radius = max(22.0, float(render_params.marker_radius_px) * 1.75 * (7.0 / max(2.2, float(spec["camera_distance"]))) ** 0.28)
        shadow_radius *= max(0.78, min(1.75, float(width + depth) * 0.55))
        draw.ellipse(
            (
                base[0] - shadow_radius,
                base[1] - shadow_radius * 0.36,
                base[0] + shadow_radius,
                base[1] + shadow_radius * 0.36,
            ),
            fill=(158, 166, 172),
            outline=None,
        )

    point_bboxes: Dict[str, List[float]] = {}
    point_centers: Dict[str, List[float]] = {}
    object_bboxes: Dict[str, List[float]] = {}
    object_centers: Dict[str, List[float]] = {}
    context_object_bboxes: Dict[str, List[float]] = {}
    context_object_centers: Dict[str, List[float]] = {}
    for spec in sorted(all_specs, key=draw_order_key, reverse=True):
        label = str(spec.get("point_label", ""))
        shape_type = str(spec["shape_type"])
        x, y = float(spec["screen_xy"][0]), float(spec["screen_xy"][1])
        if bool(spec.get("is_answer_candidate", False)):
            base_color = POINT_COLORS[POINT_LABELS.index(label) % len(POINT_COLORS)]
            color = resolve_three_d_object_fill_rgb(
                spec,
                base_rgb=base_color,
                salt=f"{scene_variant}.candidate",
                variation_strength=0.10,
            )
        else:
            color = resolve_three_d_object_fill_rgb(
                spec,
                palette=CONTEXT_OBJECT_COLORS,
                salt=f"{scene_variant}.context",
                variation_strength=0.26,
            )
        if shape_type == "sphere":
            shape_bbox = _draw_sphere_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "cylinder":
            shape_bbox = _draw_cylinder_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "cone":
            shape_bbox = _draw_cone_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "arrow":
            shape_bbox = _draw_footprint_prism_object(
                draw,
                spec,
                camera=camera,
                frame=frame,
                fill=color,
                footprint_xy=_arrow_footprint_points(),
            )
        elif shape_type == "sword":
            shape_bbox = _draw_sword_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "shield":
            shape_bbox = _draw_shield_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "diamond":
            shape_bbox = _draw_diamond_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "heart":
            shape_bbox = _draw_heart_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "key":
            shape_bbox = _draw_key_object(
                draw,
                spec,
                camera=camera,
                frame=frame,
                floor_rgb=render_params.floor_rgb,
            )
        elif shape_type == "crown":
            shape_bbox = _draw_crown_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "hourglass":
            shape_bbox = _draw_hourglass_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "anchor":
            shape_bbox = _draw_anchor_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "horseshoe":
            shape_bbox = _draw_horseshoe_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "hammer":
            shape_bbox = _draw_hammer_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "gear":
            shape_bbox = _draw_footprint_prism_object(
                draw,
                spec,
                camera=camera,
                frame=frame,
                fill=color,
                footprint_xy=_gear_footprint_points(),
            )
        elif shape_type == "bell":
            shape_bbox = _draw_bell_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "trophy":
            shape_bbox = _draw_trophy_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "open_book":
            shape_bbox = _draw_open_book_object(draw, spec, camera=camera, frame=frame)
        elif shape_type == "dumbbell":
            shape_bbox = _draw_dumbbell_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "mushroom":
            shape_bbox = _draw_mushroom_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "lantern":
            shape_bbox = _draw_lantern_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "wrench":
            shape_bbox = _draw_wrench_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "padlock":
            shape_bbox = _draw_padlock_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "magnifying_glass":
            shape_bbox = _draw_magnifying_glass_object(draw, spec, camera=camera, frame=frame, fill=color, floor_rgb=render_params.floor_rgb)
        elif shape_type == "candle":
            shape_bbox = _draw_candle_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "scroll":
            shape_bbox = _draw_scroll_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "paint_brush":
            shape_bbox = _draw_paint_brush_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "paint_palette":
            shape_bbox = _draw_paint_palette_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "goblet":
            shape_bbox = _draw_goblet_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "teapot":
            shape_bbox = _draw_teapot_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "watering_can":
            shape_bbox = _draw_watering_can_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "basket":
            shape_bbox = _draw_basket_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "mail_envelope":
            shape_bbox = _draw_mail_envelope_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "camera":
            shape_bbox = _draw_camera_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "compass":
            shape_bbox = _draw_compass_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "flask":
            shape_bbox = _draw_flask_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "test_tube_rack":
            shape_bbox = _draw_test_tube_rack_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "scroll_map":
            shape_bbox = _draw_scroll_map_object(draw, spec, camera=camera, frame=frame)
        elif shape_type == "microphone":
            shape_bbox = _draw_microphone_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "stopwatch":
            shape_bbox = _draw_stopwatch_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "clock":
            shape_bbox = _draw_clock_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "apple":
            shape_bbox = _draw_apple_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "carrot":
            shape_bbox = _draw_carrot_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "pear":
            shape_bbox = _draw_pear_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "fish":
            shape_bbox = _draw_fish_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "leaf":
            shape_bbox = _draw_leaf_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "feather":
            shape_bbox = _draw_feather_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "shoe":
            shape_bbox = _draw_shoe_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "glove":
            shape_bbox = _draw_glove_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "hat":
            shape_bbox = _draw_hat_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "helmet":
            shape_bbox = _draw_helmet_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "cup":
            shape_bbox = _draw_cup_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "bottle":
            shape_bbox = _draw_bottle_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "vase":
            shape_bbox = _draw_vase_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "umbrella":
            shape_bbox = _draw_umbrella_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "scissors":
            shape_bbox = _draw_scissors_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "screwdriver":
            shape_bbox = _draw_screwdriver_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "pencil":
            shape_bbox = _draw_pencil_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "fork":
            shape_bbox = _draw_fork_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "spoon":
            shape_bbox = _draw_spoon_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "spatula":
            shape_bbox = _draw_spatula_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "toothbrush":
            shape_bbox = _draw_toothbrush_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "comb":
            shape_bbox = _draw_comb_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "whistle":
            shape_bbox = _draw_whistle_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "flashlight":
            shape_bbox = _draw_flashlight_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "calculator":
            shape_bbox = _draw_calculator_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "phone":
            shape_bbox = _draw_phone_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "light_bulb":
            shape_bbox = _draw_light_bulb_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "suitcase":
            shape_bbox = _draw_suitcase_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "dice":
            shape_bbox = _draw_dice_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "rocket":
            shape_bbox = _draw_rocket_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "kite":
            shape_bbox = _draw_kite_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "paint_can":
            shape_bbox = _draw_paint_can_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "cactus":
            shape_bbox = _draw_cactus_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "pumpkin":
            shape_bbox = _draw_pumpkin_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "acorn":
            shape_bbox = _draw_acorn_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "pinecone":
            shape_bbox = _draw_pinecone_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "seashell":
            shape_bbox = _draw_seashell_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "magnet":
            shape_bbox = _draw_magnet_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "guitar":
            shape_bbox = _draw_guitar_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "drum":
            shape_bbox = _draw_drum_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "shovel":
            shape_bbox = _draw_shovel_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "saw":
            shape_bbox = _draw_saw_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "pliers":
            shape_bbox = _draw_pliers_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "telescope":
            shape_bbox = _draw_telescope_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "ruler":
            shape_bbox = _draw_ruler_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "pickaxe":
            shape_bbox = _draw_pickaxe_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "paint_roller":
            shape_bbox = _draw_paint_roller_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "tape_measure":
            shape_bbox = _draw_tape_measure_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "remote_control":
            shape_bbox = _draw_remote_control_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "plug":
            shape_bbox = _draw_plug_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "wallet":
            shape_bbox = _draw_wallet_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "purse":
            shape_bbox = _draw_purse_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "sunglasses":
            shape_bbox = _draw_sunglasses_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "violin":
            shape_bbox = _draw_violin_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "trumpet":
            shape_bbox = _draw_trumpet_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "donut":
            shape_bbox = _draw_donut_object(draw, spec, camera=camera, frame=frame, fill=color, floor_rgb=render_params.floor_rgb)
        elif shape_type == "pretzel":
            shape_bbox = _draw_pretzel_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "lollipop":
            shape_bbox = _draw_lollipop_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "ice_cream_cone":
            shape_bbox = _draw_ice_cream_cone_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "soap_bar":
            shape_bbox = _draw_soap_bar_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "torus":
            shape_bbox = _draw_torus_object(draw, spec, camera=camera, frame=frame, fill=color, floor_rgb=render_params.floor_rgb)
        elif shape_type == "pyramid":
            shape_bbox = _draw_pyramid_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "wedge":
            shape_bbox = _draw_wedge_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "star_prism":
            shape_bbox = _draw_footprint_prism_object(draw, spec, camera=camera, frame=frame, fill=color, footprint_xy=_star_footprint_points())
        elif shape_type == "hexagonal_prism":
            shape_bbox = _draw_footprint_prism_object(draw, spec, camera=camera, frame=frame, fill=color, footprint_xy=_hexagon_footprint_points())
        elif shape_type == "half_cylinder":
            shape_bbox = _draw_half_cylinder_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "arch":
            shape_bbox = _draw_arch_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "table":
            shape_bbox = _draw_table_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "shelf":
            shape_bbox = _draw_shelf_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "open_box":
            shape_bbox = _draw_open_box_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "pedestal":
            shape_bbox = _draw_pedestal_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "cabinet":
            shape_bbox = _draw_cabinet_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "sofa":
            shape_bbox = _draw_sofa_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "barrel":
            shape_bbox = _draw_barrel_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "chair":
            shape_bbox = _draw_chair_object(draw, spec, camera=camera, frame=frame, fill=color)
        else:
            shape_bbox = _draw_box_object(draw, spec, camera=camera, frame=frame, fill=color)
        bbox = list(shape_bbox)
        if bool(spec.get("is_answer_candidate", False)):
            label_center = (x, y)
            if shape_type == "torus":
                label_center = (x, float(shape_bbox[1]) + 0.34 * (float(shape_bbox[3]) - float(shape_bbox[1])))
            label_bbox = _draw_option_label(draw, label=label, center=label_center, font=label_font)
            bbox = _bbox_union(shape_bbox, label_bbox)
            point_bboxes[label] = list(bbox)
            point_centers[label] = [round(float(x), 3), round(float(y), 3)]
        else:
            context_object_bboxes[str(spec["object_id"])] = list(bbox)
            context_object_centers[str(spec["object_id"])] = [round(float(x), 3), round(float(y), 3)]
        object_bboxes[str(spec["object_id"])] = list(bbox)
        object_centers[str(spec["object_id"])] = [round(float(x), 3), round(float(y), 3)]
        entities.append(
            {
                "entity_id": str(spec["object_id"]),
                "entity_type": "three_d_candidate_object" if bool(spec.get("is_answer_candidate", False)) else "three_d_context_object",
                "bbox_px": list(bbox),
                "attrs": {
                    "point_label": str(label) if label else None,
                    "object_label": str(label) if label else None,
                    "shape_type": str(shape_type),
                    "object_name": str(spec.get("object_name", _object_name(shape_type))),
                    "prompt_name": str(spec.get("prompt_name", _object_name(shape_type))),
                    "nameable_for_prompt": bool(spec.get("nameable_for_prompt", False)),
                    "object_role": str(spec.get("object_role", "candidate")),
                    "is_answer_candidate": bool(spec.get("is_answer_candidate", False)),
                    "fill_rgb": [int(channel) for channel in color],
                    "world_xyz": list(spec["world_xyz"]),
                    "base_xyz": list(spec["base_xyz"]),
                    "dimensions_xyz": list(spec["dimensions_xyz"]),
                    "dimension_scale": float(spec.get("dimension_scale", 1.0)),
                    "screen_xy": [round(float(x), 3), round(float(y), 3)],
                    "camera_xyz": list(spec["camera_xyz"]),
                    "camera_distance": float(spec["camera_distance"]),
                    "scene_variant": str(scene_variant),
                },
            }
        )

    answer_label = str(dataset["answer_label"])
    evidence_bbox = list(point_bboxes[answer_label])
    all_bboxes = [list(room_bbox)] + [list(bbox) for bbox in object_bboxes.values()]
    scene_bbox = [
        round(float(min(bbox[0] for bbox in all_bboxes)), 3),
        round(float(min(bbox[1] for bbox in all_bboxes)), 3),
        round(float(max(bbox[2] for bbox in all_bboxes)), 3),
        round(float(max(bbox[3] for bbox in all_bboxes)), 3),
    ]
    return _RenderedScene(
        image=image,
        entities=list(entities),
        scene_bbox_px=list(scene_bbox),
        point_bboxes_px=dict(point_bboxes),
        point_centers_px=dict(point_centers),
        object_bboxes_px=dict(object_bboxes),
        object_centers_px=dict(object_centers),
        context_object_bboxes_px=dict(context_object_bboxes),
        context_object_centers_px=dict(context_object_centers),
        room_bbox_px=list(room_bbox),
        evidence_bboxes=[list(evidence_bbox)],
        evidence_entity_ids=[str(dataset["answer_point_id"])],
    )




def _build_complexity(
    *,
    query_variant: str,
    scene_variant: str,
    point_count: int,
    distance_margin: float,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.40)),
        "depth_reasoning": float(raw_weights.get("depth_reasoning", 0.38)),
        "ambiguity": float(raw_weights.get("ambiguity", 0.14)),
        "scene_variant_load": float(raw_weights.get("scene_variant_load", 0.08)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(int(point_count), 4, 8),
        "depth_reasoning": 0.52 if str(query_variant) == "closest_to_camera" else 0.58,
        "ambiguity": 1.0 - _normalize_unit(float(distance_margin), 0.42, 1.4),
        "scene_variant_load": {
            "floor_grid_room": 0.28,
            "tabletop_room": 0.32,
            "studio_platform": 0.36,
        }.get(str(scene_variant), 0.30),
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
class ThreeDSpatialCameraDistanceExtremumLabelTask:
    """Choose the lettered 3D object closest to or farthest from the camera."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "spatial"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return self._generate_once(int(attempt_seed), params=params, camera_yaw_band=camera_yaw_band)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        camera_yaw_band: Tuple[float, float] | None = None,
    ) -> TaskOutput:
        query_variant, query_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_QUERY_VARIANTS,
            explicit_key="query_variant",
            weights_key="query_variant_weights",
            balance_flag_key="balanced_query_variant_sampling",
            axis_namespace="query_variant",
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
        point_count, point_count_probabilities = _resolve_point_count(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        context_object_count, context_object_count_probabilities = _resolve_context_object_count(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_scene_dataset(
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            context_object_count=int(context_object_count),
            render_params=render_params,
            instance_seed=int(instance_seed),
            camera_yaw_band=camera_yaw_band,
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_object_scene_3d(background, dataset=dataset, render_params=render_params)
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
        solver_trace = dict(dataset["solver_trace"])
        complexity = _build_complexity(
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            point_count=int(point_count),
            distance_margin=float(solver_trace.get("unique_camera_distance_margin", 0.42)),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_scene",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "point_count": int(point_count),
                    "candidate_count": int(point_count),
                    "context_object_count": int(context_object_count),
                    "object_count": int(dataset["object_count"]),
                    "candidate_shape_types": [str(spec["shape_type"]) for spec in dataset["point_specs"]],
                    "context_shape_types": [str(spec["shape_type"]) for spec in dataset["context_object_specs"]],
                    "shape_types": [str(spec["shape_type"]) for spec in dataset["object_specs"]],
                    "candidate_object_names": [str(spec["object_name"]) for spec in dataset["point_specs"]],
                    "context_object_names": [str(spec["object_name"]) for spec in dataset["context_object_specs"]],
                    "nameable_candidate_object_names": [
                        str(spec["object_name"]) for spec in dataset["point_specs"] if bool(spec.get("nameable_for_prompt", False))
                    ],
                    "nameable_context_object_names": [
                        str(spec["object_name"]) for spec in dataset["context_object_specs"] if bool(spec.get("nameable_for_prompt", False))
                    ],
                    "view_family": "synthetic_perspective_3d_scene",
                    "answer_point_id": str(dataset["answer_point_id"]),
                    "answer_label": str(answer_label),
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
                    "point_count": int(point_count),
                    "candidate_count": int(point_count),
                    "object_count": int(dataset["object_count"]),
                    "point_count_probabilities": dict(point_count_probabilities),
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_object_count_probabilities),
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
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "room_bbox_px": list(rendered_scene.room_bbox_px),
                "point_bboxes_px": {str(key): list(value) for key, value in rendered_scene.point_bboxes_px.items()},
                "point_centers_px": {str(key): list(value) for key, value in rendered_scene.point_centers_px.items()},
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "context_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.context_object_bboxes_px.items()},
                "context_object_centers_px": {str(key): list(value) for key, value in rendered_scene.context_object_centers_px.items()},
            },
            "execution_trace": {
                "query_variant": "default",
                "query_id": str(query_variant),
                "scene_variant": str(scene_variant),
                "point_count": int(point_count),
                "candidate_count": int(point_count),
                "context_object_count": int(context_object_count),
                "object_count": int(dataset["object_count"]),
                "point_specs": [dict(spec) for spec in dataset["point_specs"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "answer_label": str(answer_label),
                "answer_point_id": str(dataset["answer_point_id"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_variant),
                "view_family": "synthetic_perspective_3d_scene",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(item) for item in rendered_scene.evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
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
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query_variant),
        )


__all__ = ["ThreeDSpatialCameraDistanceExtremumLabelTask"]
