"""Count wall-mounted objects in a synthetic 3D indoor room scene."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
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
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from ..shared.object_resources import (
    ROOM_EXTRA_WALL_TYPES,
    ROOM_FLOOR_DISTRACTOR_SPECS,
    ROOM_FLOOR_DISTRACTOR_TYPES,
    ROOM_FLOOR_PROP_SHAPES,
    ROOM_FLOOR_PROP_SPECS,
    ROOM_FRONT_FLOOR_PROP_SHAPES,
    ROOM_OBJECT_PROMPT_NAMES,
    ROOM_QUERY_OBJECT_TYPE_BY_VARIANT,
    ROOM_QUERY_TARGET_TYPES,
    ROOM_SURFACE_DISTRACTOR_SPECS,
    ROOM_SURFACE_DISTRACTOR_TYPES,
    ROOM_SURFACE_PROP_SHAPES_BY_SCENE,
    ROOM_SURFACE_PROP_TYPES,
    ROOM_WALL_BASE_DIMENSIONS,
)
from ..spatial.camera_distance import (
    _CameraSpec,
    CONTEXT_OBJECT_COLORS,
    POINT_COLORS,
    SCENE_ID as OBJECT_SCENE_ID,
    _RenderParams,
    _bbox_union,
    _build_projection_frame,
    _draw_box_object,
    _draw_cone_object,
    _draw_cylinder_object,
    _draw_line,
    _draw_open_box_object,
    _draw_pyramid_object,
    _draw_sphere_object,
    _draw_table_object,
    _make_object_spec,
    _object_reference_points,
    _object_screen_bbox,
    _project_screen,
    _resolve_render_params,
    _screen_to_floor_xy,
    _shade,
    _tint,
    _vec_cross,
    _vec_norm,
    _vec_sub,
)


TASK_ID = "task_three_d__room__wall_mounted_object_count"
SCENE_ID = "room"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "tv_wall_mounted_count",
    "clock_wall_mounted_count",
    "picture_frame_wall_mounted_count",
    "mirror_wall_mounted_count",
    "wall_shelf_wall_mounted_count",
    "wall_fan_wall_mounted_count",
    "air_conditioner_wall_mounted_count",
    "hanging_plant_wall_mounted_count",
    "hanging_coat_wall_mounted_count",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("living_room", "office_room", "studio_room")
QUERY_OBJECT_TYPE_BY_VARIANT: Dict[str, str] = dict(ROOM_QUERY_OBJECT_TYPE_BY_VARIANT)
OBJECT_PROMPT_NAMES: Dict[str, Tuple[str, str]] = dict(ROOM_OBJECT_PROMPT_NAMES)
QUERY_TARGET_TYPES: Tuple[str, ...] = ROOM_QUERY_TARGET_TYPES
EXTRA_WALL_TYPES: Tuple[str, ...] = ROOM_EXTRA_WALL_TYPES
FLOOR_DISTRACTOR_TYPES: Tuple[str, ...] = ROOM_FLOOR_DISTRACTOR_TYPES
SURFACE_DISTRACTOR_TYPES: Tuple[str, ...] = ROOM_SURFACE_DISTRACTOR_TYPES
SURFACE_PROP_SHAPES_BY_SCENE: Dict[str, Tuple[str, ...]] = dict(ROOM_SURFACE_PROP_SHAPES_BY_SCENE)
SURFACE_PROP_TYPES: Tuple[str, ...] = ROOM_SURFACE_PROP_TYPES
FLOOR_PROP_SHAPES: Tuple[str, ...] = ROOM_FLOOR_PROP_SHAPES
PICTURE_SCENERY_VARIANTS: Tuple[str, ...] = ("mountains", "lake", "forest", "sunset", "city")
WALL_X = 3.35
WALL_BACK_Y = 2.85
ROOM_FRONT_Y = -2.95
ROOM_HEIGHT = 3.05
ROOM_RENDER_FRONT_MIN_EXTENSION = 1.8
ROOM_RENDER_FRONT_MAX_EXTENSION = 5.2
ROOM_RENDER_SIDE_WALL_MAX_EXTENSION = 2.15
ROOM_CAMERA_PITCH_DEGREES: Tuple[float, float] = (9.0, 18.0)
ROOM_CAMERA_DISTANCE_RANGE: Tuple[float, float] = (6.8, 8.2)
ROOM_CAMERA_TARGET_Z = 1.05
FRONT_FLOOR_PROP_SLOTS: Tuple[Tuple[float, float], ...] = (
    (-2.36, -2.56),
    (-0.86, -2.66),
    (0.82, -2.64),
    (2.28, -2.46),
)
FRONT_FLOOR_PROP_SHAPES: Tuple[str, ...] = ROOM_FRONT_FLOOR_PROP_SHAPES
ROOM_VIEW_YAW_BANDS: Dict[str, Tuple[float, float]] = {
    "living_room": (-24.0, -10.0),
    "office_room": (10.0, 24.0),
    "studio_room": (-8.0, 8.0),
}


@dataclass(frozen=True)
class _RenderedRoomScene:
    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    object_bboxes_px: Dict[str, List[float]]
    object_centers_px: Dict[str, List[float]]
    wall_object_bboxes_px: Dict[str, List[float]]
    wall_object_centers_px: Dict[str, List[float]]
    floor_object_bboxes_px: Dict[str, List[float]]
    floor_object_centers_px: Dict[str, List[float]]
    room_bbox_px: List[float]
    evidence_bboxes: List[List[float]]
    evidence_entity_ids: List[str]


def _object_name(object_type: str) -> str:
    return str(OBJECT_PROMPT_NAMES.get(str(object_type), (str(object_type).replace("_", " "), ""))[0])


def _object_plural(object_type: str) -> str:
    singular, plural = OBJECT_PROMPT_NAMES.get(str(object_type), (str(object_type).replace("_", " "), ""))
    return str(plural or f"{singular}s")




def _resolve_target_count(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[int, Dict[str, float]]:
    lower = int(params.get("target_count_min", group_default(gen_defaults, "target_count_min", 0)))
    upper = int(params.get("target_count_max", group_default(gen_defaults, "target_count_max", 4)))
    lower = max(0, min(6, int(lower)))
    upper = max(lower, min(6, int(upper)))
    support = tuple(range(int(lower), int(upper) + 1))
    explicit = params.get("target_count")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported target_count: {selected}")
        return int(selected), dict(uniform_probability_map(support, selected=int(selected)))
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_count",
    )
    selected = int(support[abs(int(selection_index)) % len(support)])
    return int(selected), dict(uniform_probability_map(support))


def _sample_room_camera(
    rng,
    *,
    scene_variant: str,
    yaw_band_degrees: Tuple[float, float] | None = None,
) -> _CameraSpec:
    yaw_lower, yaw_upper = (
        tuple(float(value) for value in yaw_band_degrees)
        if yaw_band_degrees is not None
        else ROOM_VIEW_YAW_BANDS.get(str(scene_variant), ROOM_VIEW_YAW_BANDS["studio_room"])
    )
    yaw_degrees = float(rng.uniform(float(yaw_lower), float(yaw_upper)))
    pitch_degrees = float(rng.uniform(float(ROOM_CAMERA_PITCH_DEGREES[0]), float(ROOM_CAMERA_PITCH_DEGREES[1])))
    distance = float(rng.uniform(float(ROOM_CAMERA_DISTANCE_RANGE[0]), float(ROOM_CAMERA_DISTANCE_RANGE[1])))
    yaw = math.radians(float(yaw_degrees))
    pitch = math.radians(float(pitch_degrees))
    target = (0.0, 0.0, float(ROOM_CAMERA_TARGET_Z))
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


def _wall_center(wall: str, hpos: float, z: float) -> Tuple[float, float, float]:
    if str(wall) == "back":
        return (float(hpos), float(WALL_BACK_Y), float(z))
    if str(wall) == "left":
        return (-float(WALL_X), float(hpos), float(z))
    return (float(WALL_X), float(hpos), float(z))


def _wall_axes(wall: str) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]:
    if str(wall) == "back":
        return (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    if str(wall) == "left":
        return (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)
    return (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (-1.0, 0.0, 0.0)


def _add_vec(
    center: Sequence[float],
    horizontal_axis: Sequence[float],
    vertical_axis: Sequence[float],
    normal_axis: Sequence[float],
    *,
    hw: float,
    hh: float,
    normal_offset: float = 0.0,
) -> Tuple[float, float, float]:
    return (
        float(center[0]) + float(horizontal_axis[0]) * float(hw) + float(vertical_axis[0]) * float(hh) + float(normal_axis[0]) * float(normal_offset),
        float(center[1]) + float(horizontal_axis[1]) * float(hw) + float(vertical_axis[1]) * float(hh) + float(normal_axis[1]) * float(normal_offset),
        float(center[2]) + float(horizontal_axis[2]) * float(hw) + float(vertical_axis[2]) * float(hh) + float(normal_axis[2]) * float(normal_offset),
    )


def _wall_rect_points(spec: Mapping[str, Any], *, inset: float = 0.0, normal_offset: float = 0.018) -> List[Tuple[float, float, float]]:
    wall = str(spec["wall"])
    width = max(0.05, float(spec["wall_width"]) - float(inset) * 2.0)
    height = max(0.05, float(spec["wall_height"]) - float(inset) * 2.0)
    horizontal_axis, vertical_axis, normal_axis = _wall_axes(wall)
    center = tuple(float(value) for value in spec["world_xyz"])
    return [
        _add_vec(center, horizontal_axis, vertical_axis, normal_axis, hw=-width * 0.5, hh=-height * 0.5, normal_offset=normal_offset),
        _add_vec(center, horizontal_axis, vertical_axis, normal_axis, hw=width * 0.5, hh=-height * 0.5, normal_offset=normal_offset),
        _add_vec(center, horizontal_axis, vertical_axis, normal_axis, hw=width * 0.5, hh=height * 0.5, normal_offset=normal_offset),
        _add_vec(center, horizontal_axis, vertical_axis, normal_axis, hw=-width * 0.5, hh=height * 0.5, normal_offset=normal_offset),
    ]


def _project_points(points: Sequence[Sequence[float]], camera, frame) -> List[Tuple[float, float]]:
    return [(float(_project_screen(point, camera, frame)[0]), float(_project_screen(point, camera, frame)[1])) for point in points]


def _points_bbox(points: Sequence[Sequence[float]], *, pad_px: float = 0.0) -> List[float]:
    return [
        round(float(min(point[0] for point in points) - pad_px), 3),
        round(float(min(point[1] for point in points) - pad_px), 3),
        round(float(max(point[0] for point in points) + pad_px), 3),
        round(float(max(point[1] for point in points) + pad_px), 3),
    ]


def _projected_polygon_bbox(points: Sequence[Sequence[float]], camera, frame, *, pad_px: float = 0.0) -> List[float]:
    return _points_bbox(_project_points(points, camera, frame), pad_px=float(pad_px))


def _wall_reference_points(spec: Mapping[str, Any]) -> List[Tuple[float, float, float]]:
    points = list(_wall_rect_points(spec, normal_offset=0.04)) + [tuple(float(value) for value in spec["world_xyz"])]
    object_type = str(spec.get("object_type", ""))
    if object_type not in {"tv", "wall_shelf"}:
        return points

    horizontal_axis, vertical_axis, normal_axis = _wall_axes(str(spec["wall"]))
    center = tuple(float(value) for value in spec["world_xyz"])

    def physical_point(h: float, v: float, normal_offset: float) -> Tuple[float, float, float]:
        return _add_vec(
            center,
            horizontal_axis,
            vertical_axis,
            normal_axis,
            hw=float(h),
            hh=float(v),
            normal_offset=float(normal_offset),
        )

    half_w = float(spec["wall_width"]) * 0.5
    half_h = float(spec["wall_height"]) * 0.5
    normal_offsets = (0.04, 0.18) if object_type == "tv" else (0.04, 0.43)
    points.extend(
        physical_point(h, v, normal_offset)
        for h in (-half_w, half_w)
        for v in (-half_h, half_h)
        for normal_offset in normal_offsets
    )
    if object_type == "wall_shelf":
        for hpos in (-half_w * 0.36, half_w * 0.36):
            points.extend(
                [
                    physical_point(hpos, -half_h, 0.35),
                    physical_point(hpos, -half_h - 0.30, 0.055),
                ]
            )
    return points


def _floor_spec(
    *,
    object_id: str,
    object_type: str,
    prompt_name: str,
    xy: Tuple[float, float],
    dimensions_xyz: Tuple[float, float, float],
    color_role: str = "furniture",
    base_z: float = 0.0,
    mounting: str = "floor",
    support_object_id: str | None = None,
    support_surface_type: str | None = None,
    draw_order: int = 10,
) -> Dict[str, Any]:
    spec = _make_object_spec(
        object_id=str(object_id),
        shape_type="rectangular_prism",
        object_role="context",
        xy=(float(xy[0]), float(xy[1])),
        dimensions_xyz=tuple(float(value) for value in dimensions_xyz),
        dimension_scale=1.0,
    )
    height = float(dimensions_xyz[2])
    spec.update(
        {
            "world_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(base_z) + height * 0.5, 4)],
            "base_xyz": [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(base_z), 4)],
            "object_type": str(object_type),
            "object_name": str(prompt_name),
            "prompt_name": str(prompt_name),
            "object_role": "floor_object",
            "is_wall_mounted": False,
            "mounting": str(mounting),
            "counts_for_query": False,
            "color_role": str(color_role),
            "draw_order": int(draw_order),
        }
    )
    if support_object_id is not None:
        spec["support_object_id"] = str(support_object_id)
    if support_surface_type is not None:
        spec["support_surface_type"] = str(support_surface_type)
    return spec


def _wall_spec(
    *,
    object_id: str,
    object_type: str,
    wall: str,
    hpos: float,
    z: float,
    width: float,
    height: float,
    counts_for_query: bool,
) -> Dict[str, Any]:
    center = _wall_center(str(wall), float(hpos), float(z))
    return {
        "object_id": str(object_id),
        "object_type": str(object_type),
        "shape_type": str(object_type),
        "object_name": _object_name(str(object_type)),
        "prompt_name": _object_name(str(object_type)),
        "object_role": "wall_object",
        "world_xyz": [round(float(center[0]), 4), round(float(center[1]), 4), round(float(center[2]), 4)],
        "base_xyz": [round(float(center[0]), 4), round(float(center[1]), 4), round(max(0.0, float(center[2]) - float(height) * 0.5), 4)],
        "dimensions_xyz": [round(float(width), 4), 0.06, round(float(height), 4)],
        "wall": str(wall),
        "wall_width": round(float(width), 4),
        "wall_height": round(float(height), 4),
        "is_wall_mounted": True,
        "mounting": "wall_mounted",
        "counts_for_query": bool(counts_for_query),
        "nameable_for_prompt": True,
    }


def _with_picture_scenery(spec: Mapping[str, Any], rng) -> Dict[str, Any]:
    updated = dict(spec)
    if str(updated.get("object_type")) == "picture_frame":
        scenery_variant = str(rng.choice(PICTURE_SCENERY_VARIANTS))
        updated["scenery_variant"] = scenery_variant
        updated["picture_content"] = f"simple {scenery_variant} painting"
    return updated


def _top_z(spec: Mapping[str, Any]) -> float:
    base = spec.get("base_xyz", (0.0, 0.0, 0.0))
    base_z = float(base[2]) if isinstance(base, Sequence) and len(base) >= 3 else 0.0
    return round(float(base_z) + float(spec["dimensions_xyz"][2]), 4)


def _support_can_hold(object_type: str, support_spec: Mapping[str, Any]) -> bool:
    support_type = str(support_spec.get("object_type", ""))
    support_width = float(support_spec["dimensions_xyz"][0])
    if str(object_type) == "tv":
        return support_type in {"coffee_table", "media_console", "desk", "bed"} and support_width >= 0.90
    if str(object_type) in {"clock", "picture_frame"}:
        return support_type in set(SURFACE_PROP_TYPES)
    return False


def _surface_xy(
    rng,
    support_spec: Mapping[str, Any],
    dimensions_xyz: Tuple[float, float, float],
) -> Tuple[float, float]:
    support_width, support_depth, _support_height = (float(value) for value in support_spec["dimensions_xyz"])
    object_width, object_depth, _object_height = (float(value) for value in dimensions_xyz)
    max_dx = max(0.0, support_width * 0.5 - object_width * 0.5 - 0.06)
    max_dy = max(0.0, support_depth * 0.5 - object_depth * 0.5 - 0.06)
    support_x = float(support_spec["world_xyz"][0])
    support_y = float(support_spec["world_xyz"][1])
    return (
        float(support_x + rng.uniform(-max_dx, max_dx)),
        float(support_y + rng.uniform(-max_dy, max_dy)),
    )


def _surface_distractor_for_type(
    *,
    rng,
    object_id: str,
    object_type: str,
    support_spec: Mapping[str, Any],
) -> Dict[str, Any]:
    spec_data = ROOM_SURFACE_DISTRACTOR_SPECS.get(str(object_type), ROOM_SURFACE_DISTRACTOR_SPECS["picture_frame"])
    dimensions = tuple(float(value) for value in spec_data["dimensions_xyz"])
    spec = _floor_spec(
        object_id=str(object_id),
        object_type=str(object_type),
        prompt_name=str(spec_data["prompt_name"]),
        xy=_surface_xy(rng, support_spec, dimensions),
        dimensions_xyz=tuple(float(value) for value in dimensions),
        color_role=str(spec_data["color_role"]),
        base_z=_top_z(support_spec),
        mounting="on_furniture",
        support_object_id=str(support_spec["object_id"]),
        support_surface_type=str(support_spec.get("object_type", "")),
        draw_order=24,
    )
    return _with_picture_scenery(spec, rng)


def _floor_distractor_for_type(
    *,
    rng,
    object_id: str,
    object_type: str,
    xy: Tuple[float, float],
) -> Dict[str, Any]:
    spec_data = ROOM_FLOOR_DISTRACTOR_SPECS.get(str(object_type), ROOM_FLOOR_DISTRACTOR_SPECS["wall_shelf"])
    spec = _floor_spec(
        object_id=object_id,
        object_type=str(object_type) if str(object_type) in ROOM_FLOOR_DISTRACTOR_SPECS else "wall_shelf",
        prompt_name=str(spec_data["prompt_name"]),
        xy=xy,
        dimensions_xyz=tuple(float(value) for value in spec_data["dimensions_xyz"]),
        color_role=str(spec_data["color_role"]),
        base_z=0.0,
    )
    return _with_picture_scenery(spec, rng)


def _make_floor_prop(
    *,
    rng,
    object_id: str,
    prop_shape: str,
    xy: Tuple[float, float],
) -> Dict[str, Any]:
    spec_data = ROOM_FLOOR_PROP_SPECS.get(str(prop_shape), ROOM_FLOOR_PROP_SPECS["box"])
    spec = _floor_spec(
        object_id=object_id,
        object_type=str(spec_data["object_type"]),
        prompt_name=str(spec_data["prompt_name"]),
        xy=xy,
        dimensions_xyz=tuple(float(value) for value in spec_data["dimensions_xyz"]),
        color_role=str(spec_data["color_role"]),
    )
    if "shape_type" in spec_data:
        spec["shape_type"] = str(spec_data["shape_type"])
    return spec


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


def _slot_is_compatible(slot: Tuple[str, float, float], *, object_type: str, target_object: bool = False) -> bool:
    wall, _hpos, z = slot
    if bool(target_object) and str(object_type) in set(QUERY_TARGET_TYPES) and str(wall) != "back":
        return False
    if str(object_type) == "wall_shelf" and str(wall) != "back":
        return False
    if str(object_type) in {"tv", "mirror"} and float(z) < 1.15:
        return False
    return True


def _wall_dimensions_for_type(object_type: str, rng) -> Tuple[float, float]:
    scale = float(rng.uniform(0.88, 1.12))
    base = ROOM_WALL_BASE_DIMENSIONS.get(str(object_type), (0.50, 0.50))
    return round(float(base[0]) * scale, 4), round(float(base[1]) * scale, 4)


def _build_room_dataset(
    *,
    query_id: str,
    scene_variant: str,
    target_count: int,
    render_params: _RenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    target_type = str(QUERY_OBJECT_TYPE_BY_VARIANT[str(query_id)])
    camera = _sample_room_camera(rng, scene_variant=str(scene_variant))
    wall_slots = [
        ("back", -2.35, 1.25),
        ("back", -1.22, 2.05),
        ("back", 0.0, 1.38),
        ("back", 1.18, 2.12),
        ("back", 2.32, 1.30),
        ("left", -2.05, 1.65),
        ("left", -0.82, 2.20),
        ("left", 0.62, 1.36),
        ("left", 1.82, 2.04),
        ("right", -1.92, 1.46),
        ("right", -0.52, 2.18),
        ("right", 0.88, 1.34),
        ("right", 2.02, 2.00),
    ]
    rng.shuffle(wall_slots)
    selected_wall_specs: List[Dict[str, Any]] = []

    def take_slot(object_type: str, *, target_object: bool = False) -> Tuple[str, float, float]:
        for index, slot in enumerate(wall_slots):
            if _slot_is_compatible(slot, object_type=str(object_type), target_object=bool(target_object)):
                return wall_slots.pop(index)
        raise ValueError(f"no compatible wall slot for {object_type}")

    for index in range(int(target_count)):
        wall, hpos, z = take_slot(str(target_type), target_object=True)
        width, height = _wall_dimensions_for_type(str(target_type), rng)
        selected_wall_specs.append(
            _with_picture_scenery(_wall_spec(
                object_id=f"wall_target_{index}_{target_type}",
                object_type=str(target_type),
                wall=str(wall),
                hpos=float(hpos + rng.uniform(-0.06, 0.06)),
                z=float(z + rng.uniform(-0.05, 0.05)),
                width=float(width),
                height=float(height),
                counts_for_query=True,
            ), rng)
        )

    other_types = list(EXTRA_WALL_TYPES)
    rng.shuffle(other_types)
    other_wall_count = int(rng.randint(5, 8))
    for index in range(int(other_wall_count)):
        object_type = str(other_types[index % len(other_types)])
        wall, hpos, z = take_slot(str(object_type))
        width, height = _wall_dimensions_for_type(str(object_type), rng)
        selected_wall_specs.append(
            _with_picture_scenery(_wall_spec(
                object_id=f"wall_context_{index}_{object_type}",
                object_type=str(object_type),
                wall=str(wall),
                hpos=float(hpos + rng.uniform(-0.06, 0.06)),
                z=float(z + rng.uniform(-0.05, 0.05)),
                width=float(width),
                height=float(height),
                counts_for_query=False,
            ), rng)
        )

    floor_slots = [
        *FRONT_FLOOR_PROP_SLOTS,
        (-2.38, -1.95),
        (-1.15, -2.12),
        (0.18, -2.18),
        (1.48, -1.94),
        (2.48, -1.18),
        (-2.52, -0.35),
        (-1.08, -0.68),
        (0.62, -0.56),
        (1.98, -0.34),
        (-2.18, 1.08),
        (-0.62, 0.84),
        (1.02, 0.86),
        (2.34, 0.98),
    ]
    floor_specs: List[Dict[str, Any]] = []

    foreground_xy = tuple(float(value) for value in rng.choice(FRONT_FLOOR_PROP_SLOTS))
    floor_slots.remove(foreground_xy)
    foreground_shape = str(rng.choice(FRONT_FLOOR_PROP_SHAPES))
    floor_specs.append(
        _make_floor_prop(
            rng=rng,
            object_id=f"foreground_context_0_{foreground_shape}",
            prop_shape=str(foreground_shape),
            xy=(
                float(foreground_xy[0] + rng.uniform(-0.07, 0.07)),
                float(foreground_xy[1] + rng.uniform(-0.05, 0.05)),
            ),
        )
    )

    rng.shuffle(floor_slots)

    surface_shapes = list(SURFACE_PROP_SHAPES_BY_SCENE.get(str(scene_variant), SURFACE_PROP_SHAPES_BY_SCENE["studio_room"]))
    rng.shuffle(surface_shapes)
    surface_prop_count = min(len(surface_shapes), 3)
    for index in range(int(surface_prop_count)):
        xy = floor_slots.pop()
        prop_shape = str(surface_shapes[index])
        floor_specs.append(
            _make_floor_prop(
                rng=rng,
                object_id=f"surface_context_{index}_{prop_shape}",
                prop_shape=str(prop_shape),
                xy=(float(xy[0] + rng.uniform(-0.08, 0.08)), float(xy[1] + rng.uniform(-0.08, 0.08))),
            )
        )

    support_specs = [spec for spec in floor_specs if str(spec.get("object_type")) in set(SURFACE_PROP_TYPES)]
    same_type_distractors = int(rng.randint(1, 3))
    for index in range(int(same_type_distractors)):
        compatible_supports = [spec for spec in support_specs if _support_can_hold(str(target_type), spec)]
        if str(target_type) in set(SURFACE_DISTRACTOR_TYPES) and compatible_supports:
            rng.shuffle(compatible_supports)
            support = compatible_supports[index % len(compatible_supports)]
            floor_specs.append(
                _surface_distractor_for_type(
                    rng=rng,
                    object_id=f"surface_same_type_{index}_{target_type}",
                    object_type=str(target_type),
                    support_spec=support,
                )
            )
        else:
            xy = floor_slots.pop()
            floor_specs.append(
                _floor_distractor_for_type(
                    rng=rng,
                    object_id=f"floor_same_type_{index}_{target_type}",
                    object_type=str(target_type),
                    xy=(float(xy[0] + rng.uniform(-0.08, 0.08)), float(xy[1] + rng.uniform(-0.08, 0.08))),
                )
            )

    prop_shapes = [shape for shape in FLOOR_PROP_SHAPES if str(shape) not in set(SURFACE_PROP_TYPES)]
    rng.shuffle(prop_shapes)
    floor_prop_count = int(rng.randint(4, 6))
    for index in range(int(floor_prop_count)):
        xy = floor_slots.pop()
        prop_shape = str(prop_shapes[index % len(prop_shapes)])
        floor_specs.append(
            _make_floor_prop(
                rng=rng,
                object_id=f"floor_context_{index}_{prop_shape}",
                prop_shape=str(prop_shape),
                xy=(float(xy[0] + rng.uniform(-0.08, 0.08)), float(xy[1] + rng.uniform(-0.08, 0.08))),
            )
        )

    all_reference_points: List[Tuple[float, float, float]] = [
        (-WALL_X, ROOM_FRONT_Y, 0.0),
        (WALL_X, ROOM_FRONT_Y, 0.0),
        (-WALL_X, WALL_BACK_Y, 0.0),
        (WALL_X, WALL_BACK_Y, 0.0),
        (-WALL_X, WALL_BACK_Y, ROOM_HEIGHT),
        (WALL_X, WALL_BACK_Y, ROOM_HEIGHT),
        (-WALL_X, ROOM_FRONT_Y, ROOM_HEIGHT),
        (WALL_X, ROOM_FRONT_Y, ROOM_HEIGHT),
    ]
    for spec in selected_wall_specs:
        all_reference_points.extend(_wall_reference_points(spec))
    for spec in floor_specs:
        all_reference_points.extend(_object_reference_points(spec))

    frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=all_reference_points)
    finalized_wall = _finalize_specs(selected_wall_specs, camera=camera, frame=frame)
    finalized_floor = _finalize_specs(floor_specs, camera=camera, frame=frame)
    all_finalized = [*finalized_wall, *finalized_floor]
    target_specs = [
        spec
        for spec in finalized_wall
        if bool(spec.get("counts_for_query")) and str(spec.get("object_type")) == str(target_type)
    ]
    if len(target_specs) != int(target_count):
        raise ValueError("target count mismatch")

    object_type_counts = Counter(str(spec["object_type"]) for spec in all_finalized)
    wall_object_type_counts = Counter(str(spec["object_type"]) for spec in finalized_wall)
    floor_object_type_counts = Counter(str(spec["object_type"]) for spec in finalized_floor)
    same_type_floor_distractor_count = int(sum(1 for spec in finalized_floor if str(spec["object_type"]) == str(target_type)))
    same_type_surface_distractor_count = int(
        sum(1 for spec in finalized_floor if str(spec["object_type"]) == str(target_type) and str(spec.get("mounting")) == "on_furniture")
    )
    support_surface_count = int(sum(1 for spec in finalized_floor if str(spec.get("object_type")) in set(SURFACE_PROP_TYPES)))
    sorted_targets = sorted(
        target_specs,
        key=lambda spec: (str(spec.get("wall", "")), float(spec["base_xyz"][2]), float(spec["world_xyz"][0]), float(spec["world_xyz"][1])),
    )
    return {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "target_object_type": str(target_type),
        "target_object_name": _object_name(str(target_type)),
        "target_object_plural": _object_plural(str(target_type)),
        "target_count": int(target_count),
        "wall_object_specs": list(sorted(finalized_wall, key=lambda spec: str(spec["object_id"]))),
        "floor_object_specs": list(sorted(finalized_floor, key=lambda spec: str(spec["object_id"]))),
        "object_specs": list(sorted(all_finalized, key=lambda spec: str(spec["object_id"]))),
        "target_object_ids": [str(spec["object_id"]) for spec in sorted_targets],
        "object_count": int(len(all_finalized)),
        "wall_object_count": int(len(finalized_wall)),
        "floor_object_count": int(len(finalized_floor)),
        "same_type_floor_distractor_count": int(same_type_floor_distractor_count),
        "same_type_surface_distractor_count": int(same_type_surface_distractor_count),
        "support_surface_count": int(support_surface_count),
        "object_type_counts": dict(sorted(object_type_counts.items())),
        "wall_object_type_counts": dict(sorted(wall_object_type_counts.items())),
        "floor_object_type_counts": dict(sorted(floor_object_type_counts.items())),
        "camera": {
            "camera_position": [round(float(value), 4) for value in camera.camera_position],
            "target": [round(float(value), 4) for value in camera.target],
            "yaw_degrees": round(float(camera.yaw_degrees), 4),
            "yaw_band_degrees": [round(float(value), 4) for value in ROOM_VIEW_YAW_BANDS[str(scene_variant)]],
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
            "predicate": "object_type == target_object_type and is_wall_mounted",
            "target_object_type": str(target_type),
            "target_object_ids": [str(spec["object_id"]) for spec in sorted_targets],
            "target_count": int(target_count),
            "same_type_floor_distractor_count": int(same_type_floor_distractor_count),
            "same_type_surface_distractor_count": int(same_type_surface_distractor_count),
            "support_surface_count": int(support_surface_count),
            "wall_object_type_counts": dict(sorted(wall_object_type_counts.items())),
            "floor_object_type_counts": dict(sorted(floor_object_type_counts.items())),
            "unique_count_answer": True,
        },
    }


def _draw_poly(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Sequence[float]],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int] = (58, 68, 78),
    width: int = 2,
) -> List[float]:
    projected = _project_points(points, camera, frame)
    draw.polygon(projected, fill=fill)
    for index in range(len(projected)):
        _draw_line(draw, projected[index], projected[(index + 1) % len(projected)], fill=outline, width=int(width))
    return _points_bbox(projected)


def _draw_poly_fill_only(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Sequence[float]],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    projected = _project_points(points, camera, frame)
    draw.polygon(projected, fill=fill)
    return _points_bbox(projected)


def _inset_bbox(bbox: Sequence[float], x_frac: float, y_frac: float) -> List[float]:
    x1, y1, x2, y2 = (float(value) for value in bbox)
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    return [
        round(float(x1 + width * float(x_frac)), 3),
        round(float(y1 + height * float(y_frac)), 3),
        round(float(x2 - width * float(x_frac)), 3),
        round(float(y2 - height * float(y_frac)), 3),
    ]


def _draw_screen_scenery(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    variant: str,
    outline: Tuple[int, int, int] = (74, 48, 37),
) -> None:
    x1, y1, x2, y2 = (float(value) for value in bbox)
    if x2 - x1 < 10.0 or y2 - y1 < 10.0:
        draw.rectangle((x1, y1, x2, y2), fill=(204, 217, 210), outline=outline, width=1)
        return
    width = x2 - x1
    height = y2 - y1
    horizon = y1 + height * 0.56
    if str(variant) == "sunset":
        sky = (238, 170, 118)
        ground = (110, 132, 104)
        accent = (250, 218, 116)
    elif str(variant) == "lake":
        sky = (177, 215, 231)
        ground = (93, 151, 180)
        accent = (236, 244, 248)
    elif str(variant) == "forest":
        sky = (188, 218, 198)
        ground = (75, 131, 91)
        accent = (42, 96, 63)
    elif str(variant) == "city":
        sky = (181, 202, 224)
        ground = (126, 136, 150)
        accent = (78, 87, 102)
    else:
        sky = (175, 210, 230)
        ground = (115, 154, 105)
        accent = (93, 118, 142)
    draw.rectangle((x1, y1, x2, horizon), fill=sky)
    draw.rectangle((x1, horizon, x2, y2), fill=ground)
    if str(variant) == "city":
        for index in range(4):
            bx1 = x1 + width * (0.12 + index * 0.18)
            bx2 = bx1 + width * 0.11
            by1 = horizon - height * (0.18 + 0.07 * (index % 2))
            draw.rectangle((bx1, by1, bx2, horizon), fill=accent)
    elif str(variant) == "forest":
        for index in range(4):
            cx = x1 + width * (0.18 + index * 0.18)
            draw.polygon(
                [(cx, horizon - height * 0.28), (cx - width * 0.08, horizon), (cx + width * 0.08, horizon)],
                fill=accent,
            )
    else:
        draw.polygon(
            [(x1 + width * 0.05, horizon), (x1 + width * 0.30, y1 + height * 0.22), (x1 + width * 0.56, horizon)],
            fill=accent,
        )
        draw.polygon(
            [(x1 + width * 0.40, horizon), (x1 + width * 0.68, y1 + height * 0.26), (x1 + width * 0.96, horizon)],
            fill=_shade(accent, 0.86),
        )
        if str(variant) in {"lake", "sunset"}:
            cx = x1 + width * 0.76
            cy = y1 + height * 0.22
            radius = min(width, height) * 0.09
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(247, 221, 111))
    draw.rectangle((x1, y1, x2, y2), outline=outline, width=1)


def _wall_plane_point(spec: Mapping[str, Any], u: float, v: float, *, normal_offset: float = 0.03) -> Tuple[float, float, float]:
    horizontal_axis, vertical_axis, normal_axis = _wall_axes(str(spec["wall"]))
    center = tuple(float(value) for value in spec["world_xyz"])
    return _add_vec(
        center,
        horizontal_axis,
        vertical_axis,
        normal_axis,
        hw=float(spec["wall_width"]) * float(u),
        hh=float(spec["wall_height"]) * float(v),
        normal_offset=float(normal_offset),
    )


def _wall_physical_point(spec: Mapping[str, Any], h: float, v: float, *, normal_offset: float = 0.03) -> Tuple[float, float, float]:
    horizontal_axis, vertical_axis, normal_axis = _wall_axes(str(spec["wall"]))
    center = tuple(float(value) for value in spec["world_xyz"])
    return _add_vec(
        center,
        horizontal_axis,
        vertical_axis,
        normal_axis,
        hw=float(h),
        hh=float(v),
        normal_offset=float(normal_offset),
    )


def _wall_quad_points(
    spec: Mapping[str, Any],
    u_start: float,
    v_start: float,
    u_end: float,
    v_end: float,
    *,
    normal_offset: float = 0.03,
) -> List[Tuple[float, float, float]]:
    return [
        _wall_plane_point(spec, u_start, v_start, normal_offset=normal_offset),
        _wall_plane_point(spec, u_end, v_start, normal_offset=normal_offset),
        _wall_plane_point(spec, u_end, v_end, normal_offset=normal_offset),
        _wall_plane_point(spec, u_start, v_end, normal_offset=normal_offset),
    ]


def _face_camera_distance_sq(face: Sequence[Sequence[float]], camera) -> float:
    center = tuple(sum(float(point[index]) for point in face) / float(len(face)) for index in range(3))
    return sum((float(center[index]) - float(camera.camera_position[index])) ** 2 for index in range(3))


def _draw_wall_cuboid(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    normal_near: float,
    normal_far: float,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
) -> List[float]:
    half_w = float(spec["wall_width"]) * 0.5
    half_h = float(spec["wall_height"]) * 0.5
    back = {
        "lb": _wall_physical_point(spec, -half_w, -half_h, normal_offset=float(normal_near)),
        "rb": _wall_physical_point(spec, half_w, -half_h, normal_offset=float(normal_near)),
        "rt": _wall_physical_point(spec, half_w, half_h, normal_offset=float(normal_near)),
        "lt": _wall_physical_point(spec, -half_w, half_h, normal_offset=float(normal_near)),
    }
    front = {
        "lb": _wall_physical_point(spec, -half_w, -half_h, normal_offset=float(normal_far)),
        "rb": _wall_physical_point(spec, half_w, -half_h, normal_offset=float(normal_far)),
        "rt": _wall_physical_point(spec, half_w, half_h, normal_offset=float(normal_far)),
        "lt": _wall_physical_point(spec, -half_w, half_h, normal_offset=float(normal_far)),
    }
    faces = [
        ([front["lb"], front["rb"], front["rt"], front["lt"]], _tint(fill, 0.10)),
        ([back["lt"], front["lt"], front["rt"], back["rt"]], _tint(fill, 0.22)),
        ([back["lb"], back["rb"], front["rb"], front["lb"]], _shade(fill, 0.76)),
        ([back["rb"], back["rt"], front["rt"], front["rb"]], _shade(fill, 0.84)),
        ([back["lb"], front["lb"], front["lt"], back["lt"]], _shade(fill, 0.68)),
    ]
    bboxes: List[List[float]] = []
    for points, face_fill in sorted(faces, key=lambda item: _face_camera_distance_sq(item[0], camera), reverse=True):
        bboxes.append(_draw_poly(draw, points, camera=camera, frame=frame, fill=face_fill, outline=outline, width=2))
    return _bbox_union(*bboxes)


def _draw_wall_tv_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    bbox = _draw_wall_cuboid(
        draw,
        spec,
        camera=camera,
        frame=frame,
        normal_near=0.018,
        normal_far=0.18,
        fill=(35, 41, 50),
        outline=(17, 22, 28),
    )
    inner_points = _wall_rect_points(
        {
            **dict(spec),
            "wall_width": float(spec["wall_width"]) * 0.78,
            "wall_height": float(spec["wall_height"]) * 0.66,
        },
        normal_offset=0.186,
    )
    _draw_poly(draw, inner_points, camera=camera, frame=frame, fill=(16, 25, 36), outline=(80, 96, 112), width=1)
    return list(bbox)


def _draw_wall_shelf_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    board_bbox = _draw_wall_cuboid(
        draw,
        spec,
        camera=camera,
        frame=frame,
        normal_near=0.035,
        normal_far=0.42,
        fill=(132, 101, 73),
        outline=(67, 51, 39),
    )
    half_w = float(spec["wall_width"]) * 0.5
    half_h = float(spec["wall_height"]) * 0.5
    bracket_bboxes: List[List[float]] = []
    for hpos in (-half_w * 0.36, half_w * 0.36):
        triangle = [
            _wall_physical_point(spec, hpos, -half_h, normal_offset=0.055),
            _wall_physical_point(spec, hpos, -half_h, normal_offset=0.35),
            _wall_physical_point(spec, hpos, -half_h - 0.30, normal_offset=0.055),
        ]
        bracket_bboxes.append(
            _draw_poly(draw, triangle, camera=camera, frame=frame, fill=(103, 77, 55), outline=(67, 51, 39), width=2)
        )
    lip_spec = {
        **dict(spec),
        "wall_width": float(spec["wall_width"]) * 0.96,
        "wall_height": max(0.045, float(spec["wall_height"]) * 0.35),
        "world_xyz": list(_wall_physical_point(spec, 0.0, -half_h - 0.02, normal_offset=0.43)),
    }
    bracket_bboxes.append(
        _draw_wall_cuboid(
            draw,
            lip_spec,
            camera=camera,
            frame=frame,
            normal_near=0.0,
            normal_far=0.035,
            fill=(110, 83, 58),
            outline=(67, 51, 39),
        )
    )
    return _bbox_union(board_bbox, *bracket_bboxes)


def _fill_wall_shape(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Sequence[float]],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> None:
    draw.polygon(_project_points(points, camera, frame), fill=fill)


def _outline_wall_shape(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Sequence[float]],
    *,
    camera,
    frame,
    outline: Tuple[int, int, int],
    width: int = 1,
) -> None:
    projected = _project_points(points, camera, frame)
    for index in range(len(projected)):
        _draw_line(draw, projected[index], projected[(index + 1) % len(projected)], fill=outline, width=int(width))


def _draw_wall_disc(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    radius_u: float = 0.46,
    radius_v: float = 0.46,
    normal_offset: float = 0.034,
) -> List[float]:
    points = [
        _wall_plane_point(
            spec,
            math.cos(2.0 * math.pi * index / 28.0) * float(radius_u),
            math.sin(2.0 * math.pi * index / 28.0) * float(radius_v),
            normal_offset=float(normal_offset),
        )
        for index in range(28)
    ]
    projected = _project_points(points, camera, frame)
    draw.polygon(projected, fill=fill)
    for index in range(len(projected)):
        _draw_line(draw, projected[index], projected[(index + 1) % len(projected)], fill=outline, width=2)
    return _points_bbox(projected)


def _draw_wall_fan_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    bbox = _draw_wall_disc(
        draw,
        spec,
        camera=camera,
        frame=frame,
        fill=(214, 222, 224),
        outline=(45, 56, 66),
        radius_u=0.50,
        radius_v=0.50,
    )
    for angle in (math.pi * 0.5, math.pi * 1.17, math.pi * 1.83):
        blade = [
            _wall_plane_point(spec, 0.06 * math.cos(angle - 0.30), 0.06 * math.sin(angle - 0.30), normal_offset=0.042),
            _wall_plane_point(spec, 0.40 * math.cos(angle), 0.40 * math.sin(angle), normal_offset=0.042),
            _wall_plane_point(spec, 0.06 * math.cos(angle + 0.30), 0.06 * math.sin(angle + 0.30), normal_offset=0.042),
        ]
        _fill_wall_shape(draw, blade, camera=camera, frame=frame, fill=(112, 130, 140))
        _outline_wall_shape(draw, blade, camera=camera, frame=frame, outline=(55, 67, 76), width=1)
    hub_spec = {**dict(spec), "wall_width": float(spec["wall_width"]) * 0.22, "wall_height": float(spec["wall_height"]) * 0.22}
    hub_spec["world_xyz"] = list(_wall_plane_point(spec, 0.0, 0.0, normal_offset=0.045))
    _draw_wall_disc(
        draw,
        hub_spec,
        camera=camera,
        frame=frame,
        fill=(68, 82, 92),
        outline=(34, 42, 48),
        radius_u=0.50,
        radius_v=0.50,
        normal_offset=0.047,
    )
    center = _project_points([_wall_plane_point(spec, 0.0, 0.0, normal_offset=0.048)], camera, frame)[0]
    for angle in (0.0, math.pi * 0.25, math.pi * 0.50, math.pi * 0.75, math.pi, math.pi * 1.25, math.pi * 1.50, math.pi * 1.75):
        edge = _project_points([_wall_plane_point(spec, 0.44 * math.cos(angle), 0.44 * math.sin(angle), normal_offset=0.048)], camera, frame)[0]
        _draw_line(draw, center, edge, fill=(108, 121, 130), width=1)
    # A few grill chords make this read as a fan rather than a second clock.
    for u in (-0.24, 0.0, 0.24):
        top = _project_points([_wall_plane_point(spec, u, 0.34, normal_offset=0.046)], camera, frame)[0]
        bottom = _project_points([_wall_plane_point(spec, u, -0.34, normal_offset=0.046)], camera, frame)[0]
        _draw_line(draw, top, bottom, fill=(115, 128, 136), width=1)
    return list(bbox)


def _draw_wall_air_conditioner_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    bbox = _draw_wall_flat_object(draw, spec, camera=camera, frame=frame, fill=(220, 226, 226), trim=(77, 89, 94))
    left_cap = _wall_quad_points(spec, -0.48, -0.36, -0.39, 0.36, normal_offset=0.041)
    right_cap = _wall_quad_points(spec, 0.39, -0.36, 0.48, 0.36, normal_offset=0.041)
    _fill_wall_shape(draw, left_cap, camera=camera, frame=frame, fill=(197, 209, 212))
    _fill_wall_shape(draw, right_cap, camera=camera, frame=frame, fill=(197, 209, 212))
    _outline_wall_shape(draw, left_cap, camera=camera, frame=frame, outline=(77, 89, 94), width=1)
    _outline_wall_shape(draw, right_cap, camera=camera, frame=frame, outline=(77, 89, 94), width=1)
    grille = _wall_quad_points(spec, -0.42, 0.08, 0.42, 0.30, normal_offset=0.038)
    _fill_wall_shape(draw, grille, camera=camera, frame=frame, fill=(192, 203, 207))
    _outline_wall_shape(draw, grille, camera=camera, frame=frame, outline=(87, 102, 108), width=1)
    for v in (0.12, 0.17, 0.22, 0.27):
        left = _project_points([_wall_plane_point(spec, -0.37, v, normal_offset=0.043)], camera, frame)[0]
        right = _project_points([_wall_plane_point(spec, 0.37, v, normal_offset=0.043)], camera, frame)[0]
        _draw_line(draw, left, right, fill=(92, 108, 115), width=1)
    outlet = _wall_quad_points(spec, -0.38, -0.28, 0.38, -0.11, normal_offset=0.04)
    _fill_wall_shape(draw, outlet, camera=camera, frame=frame, fill=(236, 240, 239))
    _outline_wall_shape(draw, outlet, camera=camera, frame=frame, outline=(88, 103, 108), width=1)
    for u in (-0.24, 0.0, 0.24):
        top = _project_points([_wall_plane_point(spec, u, -0.11, normal_offset=0.044)], camera, frame)[0]
        bottom = _project_points([_wall_plane_point(spec, u - 0.08, -0.28, normal_offset=0.044)], camera, frame)[0]
        _draw_line(draw, top, bottom, fill=(113, 126, 130), width=1)
    indicator = _wall_quad_points(spec, 0.28, -0.02, 0.39, 0.05, normal_offset=0.045)
    _fill_wall_shape(draw, indicator, camera=camera, frame=frame, fill=(88, 151, 174))
    _outline_wall_shape(draw, indicator, camera=camera, frame=frame, outline=(47, 83, 96), width=1)
    return list(bbox)


def _draw_wall_hanging_plant_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    bboxes: List[List[float]] = []
    hook = [
        _wall_plane_point(spec, 0.0, 0.46, normal_offset=0.038),
        _wall_plane_point(spec, -0.20, 0.15, normal_offset=0.038),
        _wall_plane_point(spec, 0.20, 0.15, normal_offset=0.038),
    ]
    projected_hook = _project_points(hook, camera, frame)
    _draw_line(draw, projected_hook[0], projected_hook[1], fill=(69, 74, 70), width=2)
    _draw_line(draw, projected_hook[0], projected_hook[2], fill=(69, 74, 70), width=2)
    bboxes.append(_points_bbox(projected_hook))

    pot = [
        _wall_plane_point(spec, -0.28, 0.12, normal_offset=0.052),
        _wall_plane_point(spec, 0.28, 0.12, normal_offset=0.052),
        _wall_plane_point(spec, 0.20, -0.30, normal_offset=0.052),
        _wall_plane_point(spec, -0.20, -0.30, normal_offset=0.052),
    ]
    bboxes.append(_draw_poly(draw, pot, camera=camera, frame=frame, fill=(137, 86, 55), outline=(68, 48, 34), width=2))
    for u, v, width_scale, height_scale, fill in (
        (-0.20, 0.24, 0.24, 0.18, (65, 132, 80)),
        (0.00, 0.30, 0.26, 0.20, (78, 150, 87)),
        (0.22, 0.22, 0.22, 0.18, (58, 122, 74)),
        (-0.02, 0.08, 0.22, 0.16, (46, 112, 66)),
    ):
        leaf_spec = {
            **dict(spec),
            "wall_width": float(spec["wall_width"]) * float(width_scale),
            "wall_height": float(spec["wall_height"]) * float(height_scale),
            "world_xyz": list(_wall_plane_point(spec, float(u), float(v), normal_offset=0.062)),
        }
        bboxes.append(
            _draw_wall_disc(
                draw,
                leaf_spec,
                camera=camera,
                frame=frame,
                fill=fill,
                outline=(35, 82, 48),
                radius_u=0.50,
                radius_v=0.42,
                normal_offset=0.064,
            )
        )
    return _bbox_union(*bboxes)


def _draw_wall_hanging_coat_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    hook = [
        _wall_plane_point(spec, 0.0, 0.48, normal_offset=0.04),
        _wall_plane_point(spec, 0.0, 0.34, normal_offset=0.04),
    ]
    projected_hook = _project_points(hook, camera, frame)
    _draw_line(draw, projected_hook[0], projected_hook[1], fill=(53, 55, 58), width=2)
    body = [
        _wall_plane_point(spec, -0.30, 0.30, normal_offset=0.055),
        _wall_plane_point(spec, 0.30, 0.30, normal_offset=0.055),
        _wall_plane_point(spec, 0.39, -0.44, normal_offset=0.055),
        _wall_plane_point(spec, -0.39, -0.44, normal_offset=0.055),
    ]
    left_sleeve = [
        _wall_plane_point(spec, -0.30, 0.22, normal_offset=0.053),
        _wall_plane_point(spec, -0.56, -0.12, normal_offset=0.053),
        _wall_plane_point(spec, -0.42, -0.28, normal_offset=0.053),
        _wall_plane_point(spec, -0.14, 0.10, normal_offset=0.053),
    ]
    right_sleeve = [
        _wall_plane_point(spec, 0.30, 0.22, normal_offset=0.053),
        _wall_plane_point(spec, 0.56, -0.12, normal_offset=0.053),
        _wall_plane_point(spec, 0.42, -0.28, normal_offset=0.053),
        _wall_plane_point(spec, 0.14, 0.10, normal_offset=0.053),
    ]
    color = (116, 80, 145)
    bboxes = [
        _points_bbox(projected_hook),
        _draw_poly(draw, left_sleeve, camera=camera, frame=frame, fill=_shade(color, 0.86), outline=(53, 42, 68), width=2),
        _draw_poly(draw, right_sleeve, camera=camera, frame=frame, fill=_shade(color, 0.92), outline=(53, 42, 68), width=2),
        _draw_poly(draw, body, camera=camera, frame=frame, fill=color, outline=(53, 42, 68), width=2),
    ]
    collar = [
        _wall_plane_point(spec, -0.10, 0.25, normal_offset=0.062),
        _wall_plane_point(spec, 0.0, 0.12, normal_offset=0.062),
        _wall_plane_point(spec, 0.10, 0.25, normal_offset=0.062),
    ]
    bboxes.append(_draw_poly(draw, collar, camera=camera, frame=frame, fill=(232, 225, 210), outline=(53, 42, 68), width=1))
    seam = _project_points(
        [
            _wall_plane_point(spec, 0.0, 0.08, normal_offset=0.064),
            _wall_plane_point(spec, 0.0, -0.38, normal_offset=0.064),
        ],
        camera,
        frame,
    )
    _draw_line(draw, seam[0], seam[1], fill=(63, 47, 82), width=2)
    bboxes.append(_points_bbox(seam))
    for v in (-0.04, -0.18, -0.32):
        center = _project_points([_wall_plane_point(spec, 0.05, v, normal_offset=0.066)], camera, frame)[0]
        draw.ellipse((center[0] - 2.2, center[1] - 2.2, center[0] + 2.2, center[1] + 2.2), fill=(226, 218, 202), outline=(53, 42, 68), width=1)
        bboxes.append([center[0] - 2.2, center[1] - 2.2, center[0] + 2.2, center[1] + 2.2])
    return _bbox_union(*bboxes)


def _draw_wall_scenery(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    variant: str,
    outline: Tuple[int, int, int],
) -> None:
    if str(variant) == "sunset":
        sky = (238, 170, 118)
        ground = (110, 132, 104)
        accent = (250, 218, 116)
    elif str(variant) == "lake":
        sky = (177, 215, 231)
        ground = (93, 151, 180)
        accent = (236, 244, 248)
    elif str(variant) == "forest":
        sky = (188, 218, 198)
        ground = (75, 131, 91)
        accent = (42, 96, 63)
    elif str(variant) == "city":
        sky = (181, 202, 224)
        ground = (126, 136, 150)
        accent = (78, 87, 102)
    else:
        sky = (175, 210, 230)
        ground = (115, 154, 105)
        accent = (93, 118, 142)

    horizon = -0.06
    _fill_wall_shape(draw, _wall_quad_points(spec, -0.5, horizon, 0.5, 0.5), camera=camera, frame=frame, fill=sky)
    _fill_wall_shape(draw, _wall_quad_points(spec, -0.5, -0.5, 0.5, horizon), camera=camera, frame=frame, fill=ground)

    if str(variant) == "city":
        for index in range(4):
            u_start = -0.38 + index * 0.20
            u_end = u_start + 0.11
            top = horizon + 0.05 + 0.10 * (index % 2)
            _fill_wall_shape(
                draw,
                _wall_quad_points(spec, u_start, horizon, u_end, top),
                camera=camera,
                frame=frame,
                fill=accent,
            )
    elif str(variant) == "forest":
        for index in range(4):
            u = -0.30 + index * 0.20
            tree = [
                _wall_plane_point(spec, u, 0.22),
                _wall_plane_point(spec, u - 0.08, horizon),
                _wall_plane_point(spec, u + 0.08, horizon),
            ]
            _fill_wall_shape(draw, tree, camera=camera, frame=frame, fill=accent)
    else:
        mountains = [
            (
                [
                    _wall_plane_point(spec, -0.45, horizon),
                    _wall_plane_point(spec, -0.22, 0.24),
                    _wall_plane_point(spec, 0.02, horizon),
                ],
                accent,
            ),
            (
                [
                    _wall_plane_point(spec, -0.08, horizon),
                    _wall_plane_point(spec, 0.20, 0.20),
                    _wall_plane_point(spec, 0.48, horizon),
                ],
                _shade(accent, 0.86),
            ),
        ]
        for points, color in mountains:
            _fill_wall_shape(draw, points, camera=camera, frame=frame, fill=color)
        if str(variant) in {"lake", "sunset"}:
            sun_spec = {**dict(spec), "wall_width": float(spec["wall_width"]) * 0.18, "wall_height": float(spec["wall_height"]) * 0.18}
            sun_spec["world_xyz"] = list(_wall_plane_point(spec, 0.30, 0.27, normal_offset=0.033))
            _draw_wall_disc(draw, sun_spec, camera=camera, frame=frame, fill=(247, 221, 111), outline=(196, 154, 75), radius_u=0.5, radius_v=0.5, normal_offset=0.034)

    _outline_wall_shape(
        draw,
        _wall_quad_points(spec, -0.5, -0.5, 0.5, 0.5),
        camera=camera,
        frame=frame,
        outline=outline,
        width=1,
    )


def _draw_room_shell(draw: ImageDraw.ImageDraw, *, camera, frame, render_params: _RenderParams, scene_variant: str) -> Tuple[List[float], List[Dict[str, Any]]]:
    floor_rgb = tuple(int(value) for value in render_params.floor_rgb)
    back_rgb = _tint((202, 210, 216), 0.30)
    side_rgb = _shade(back_rgb, 0.94)
    if str(scene_variant) == "living_room":
        back_rgb = (223, 216, 206)
        side_rgb = (214, 221, 216)
    elif str(scene_variant) == "office_room":
        back_rgb = (216, 222, 228)
        side_rgb = (224, 221, 214)

    render_front_y = _room_render_front_y(camera=camera, frame=frame, render_params=render_params)
    side_wall_front_y = max(
        float(render_front_y),
        float(ROOM_FRONT_Y) - float(ROOM_RENDER_SIDE_WALL_MAX_EXTENSION),
    )
    back_wall = [(-WALL_X, WALL_BACK_Y, 0.0), (WALL_X, WALL_BACK_Y, 0.0), (WALL_X, WALL_BACK_Y, ROOM_HEIGHT), (-WALL_X, WALL_BACK_Y, ROOM_HEIGHT)]
    left_wall = [(-WALL_X, side_wall_front_y, 0.0), (-WALL_X, WALL_BACK_Y, 0.0), (-WALL_X, WALL_BACK_Y, ROOM_HEIGHT), (-WALL_X, side_wall_front_y, ROOM_HEIGHT)]
    right_wall = [(WALL_X, WALL_BACK_Y, 0.0), (WALL_X, side_wall_front_y, 0.0), (WALL_X, side_wall_front_y, ROOM_HEIGHT), (WALL_X, WALL_BACK_Y, ROOM_HEIGHT)]
    floor = [(-WALL_X, render_front_y, 0.0), (WALL_X, render_front_y, 0.0), (WALL_X, WALL_BACK_Y, 0.0), (-WALL_X, WALL_BACK_Y, 0.0)]

    wall_bboxes = [
        _draw_poly_fill_only(draw, left_wall, camera=camera, frame=frame, fill=side_rgb),
        _draw_poly_fill_only(draw, right_wall, camera=camera, frame=frame, fill=_shade(side_rgb, 0.97)),
        _draw_poly(draw, back_wall, camera=camera, frame=frame, fill=back_rgb, outline=(94, 103, 114), width=2),
    ]

    floor_bbox = _draw_poly_fill_only(draw, floor, camera=camera, frame=frame, fill=floor_rgb)

    grid_rgb = tuple(int(value) for value in render_params.grid_rgb)
    step = float(render_params.grid_step)
    x = -WALL_X
    while x <= WALL_X + 1e-6:
        a = _project_screen((x, render_front_y, 0.0), camera, frame)
        b = _project_screen((x, WALL_BACK_Y, 0.0), camera, frame)
        _draw_line(draw, (a[0], a[1]), (b[0], b[1]), fill=grid_rgb, width=1)
        x += step
    y = render_front_y
    while y <= WALL_BACK_Y + 1e-6:
        a = _project_screen((-WALL_X, y, 0.0), camera, frame)
        b = _project_screen((WALL_X, y, 0.0), camera, frame)
        _draw_line(draw, (a[0], a[1]), (b[0], b[1]), fill=grid_rgb, width=1)
        y += step

    bboxes = [floor_bbox, *wall_bboxes]

    window = _wall_spec(object_id="room_window", object_type="window", wall="right", hpos=1.18, z=1.95, width=0.82, height=0.70, counts_for_query=False)
    door = _wall_spec(object_id="room_door", object_type="door", wall="left", hpos=1.78, z=0.92, width=0.82, height=1.84, counts_for_query=False)
    bboxes.append(_draw_wall_flat_object(draw, window, camera=camera, frame=frame, fill=(174, 210, 224), trim=(76, 103, 118)))
    bboxes.append(_draw_wall_flat_object(draw, door, camera=camera, frame=frame, fill=(150, 116, 84), trim=(74, 60, 48)))

    room_bbox = _bbox_union(*bboxes)
    entities = [
        {
            "entity_id": "room_shell",
            "entity_type": "three_d_room_shell",
            "bbox_px": list(room_bbox),
            "attrs": {
                "scene_variant": str(scene_variant),
                "room_extent_xyz": [float(WALL_X), float(WALL_BACK_Y - ROOM_FRONT_Y), float(ROOM_HEIGHT)],
                "render_front_y": round(float(render_front_y), 4),
                "render_side_wall_front_y": round(float(side_wall_front_y), 4),
                "semantic_front_y": float(ROOM_FRONT_Y),
                "has_floor": True,
                "has_walls": True,
            },
        }
    ]
    return list(room_bbox), entities


def _room_render_front_y(*, camera, frame, render_params: _RenderParams) -> float:
    floor_hits = [
        _screen_to_floor_xy(screen_x, float(render_params.canvas_height), camera=camera, frame=frame)
        for screen_x in (0.0, float(render_params.canvas_width) * 0.5, float(render_params.canvas_width))
    ]
    valid_y = [float(point[1]) for point in floor_hits if point is not None]
    if valid_y:
        desired_front_y = min(valid_y) - 0.35
    else:
        desired_front_y = float(ROOM_FRONT_Y) - float(ROOM_RENDER_FRONT_MAX_EXTENSION)
    min_front_y = float(ROOM_FRONT_Y) - float(ROOM_RENDER_FRONT_MAX_EXTENSION)
    max_front_y = float(ROOM_FRONT_Y) - float(ROOM_RENDER_FRONT_MIN_EXTENSION)
    return max(float(min_front_y), min(float(max_front_y), float(desired_front_y)))


def _draw_wall_flat_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
    trim: Tuple[int, int, int],
) -> List[float]:
    outer = _wall_rect_points(spec, normal_offset=0.024)
    bbox = _draw_poly(draw, outer, camera=camera, frame=frame, fill=fill, outline=trim, width=2)
    inner = _wall_rect_points({**dict(spec), "wall_width": float(spec["wall_width"]) * 0.78, "wall_height": float(spec["wall_height"]) * 0.74}, normal_offset=0.026)
    if str(spec.get("object_type")) in {"picture_frame", "poster"}:
        _draw_poly(draw, inner, camera=camera, frame=frame, fill=_tint(fill, 0.34), outline=_shade(trim, 0.8), width=1)
    elif str(spec.get("object_type")) == "mirror":
        _draw_poly(draw, inner, camera=camera, frame=frame, fill=(199, 226, 232), outline=_shade(trim, 0.9), width=1)
    return list(bbox)


def _draw_wall_speaker_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    bbox = _draw_wall_flat_object(draw, spec, camera=camera, frame=frame, fill=(43, 49, 56), trim=(17, 20, 24))
    bboxes = [bbox]
    for v, scale, cone_fill in ((-0.18, 0.52, (74, 84, 96)), (0.28, 0.26, (92, 103, 116))):
        driver_spec = {
            **dict(spec),
            "world_xyz": list(_wall_plane_point(spec, 0.0, v, normal_offset=0.040)),
            "wall_width": float(spec["wall_width"]) * float(scale),
            "wall_height": float(spec["wall_height"]) * float(scale),
        }
        bboxes.append(
            _draw_wall_disc(
                draw,
                driver_spec,
                camera=camera,
                frame=frame,
                fill=cone_fill,
                outline=(12, 15, 18),
                radius_u=0.50,
                radius_v=0.50,
                normal_offset=0.043,
            )
        )
        cap_spec = {
            **driver_spec,
            "wall_width": float(driver_spec["wall_width"]) * 0.38,
            "wall_height": float(driver_spec["wall_height"]) * 0.38,
        }
        bboxes.append(
            _draw_wall_disc(
                draw,
                cap_spec,
                camera=camera,
                frame=frame,
                fill=(25, 29, 34),
                outline=(120, 132, 142),
                radius_u=0.50,
                radius_v=0.50,
                normal_offset=0.047,
            )
        )
    for v in (-0.44, 0.04, 0.48):
        p1, p2 = _project_points(
            [
                _wall_plane_point(spec, -0.36, v, normal_offset=0.048),
                _wall_plane_point(spec, 0.36, v, normal_offset=0.048),
            ],
            camera,
            frame,
        )
        _draw_line(draw, p1, p2, fill=(122, 133, 143), width=1)
        bboxes.append([min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])])
    highlight = _wall_quad_points(spec, -0.42, 0.58, 0.42, 0.68, normal_offset=0.049)
    projected = _project_points(highlight, camera, frame)
    draw.polygon(projected, fill=(72, 82, 92))
    bboxes.append(_points_bbox(projected))
    return _bbox_union(*bboxes)


def _draw_wall_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    object_type = str(spec["object_type"])
    if object_type == "tv":
        return _draw_wall_tv_object(draw, spec, camera=camera, frame=frame)
    if object_type == "clock":
        bbox = _draw_wall_disc(draw, spec, camera=camera, frame=frame, fill=(244, 239, 218), outline=(46, 56, 66))
        center = _project_points([_wall_plane_point(spec, 0.0, 0.0, normal_offset=0.038)], camera, frame)[0]
        hand_up = _project_points([_wall_plane_point(spec, 0.0, 0.24, normal_offset=0.039)], camera, frame)[0]
        hand_right = _project_points([_wall_plane_point(spec, 0.18, -0.10, normal_offset=0.039)], camera, frame)[0]
        for index in range(12):
            angle = math.pi * 0.5 - index * math.tau / 12.0
            outer_u = math.cos(angle) * 0.37
            outer_v = math.sin(angle) * 0.37
            inner_scale = 0.76 if index % 3 == 0 else 0.86
            p1, p2 = _project_points(
                [
                    _wall_plane_point(spec, outer_u * inner_scale, outer_v * inner_scale, normal_offset=0.040),
                    _wall_plane_point(spec, outer_u, outer_v, normal_offset=0.040),
                ],
                camera,
                frame,
            )
            _draw_line(draw, p1, p2, fill=(70, 77, 84), width=2 if index % 3 == 0 else 1)
        _draw_line(draw, center, hand_up, fill=(38, 45, 54), width=2)
        _draw_line(draw, center, hand_right, fill=(38, 45, 54), width=2)
        dot_r = 2.4
        draw.ellipse((center[0] - dot_r, center[1] - dot_r, center[0] + dot_r, center[1] + dot_r), fill=(38, 45, 54))
        return list(bbox)
    if object_type == "picture_frame":
        outer = _draw_wall_flat_object(draw, spec, camera=camera, frame=frame, fill=(172, 112, 82), trim=(74, 48, 37))
        inner_spec = {
            **dict(spec),
            "wall_width": float(spec["wall_width"]) * 0.66,
            "wall_height": float(spec["wall_height"]) * 0.58,
        }
        _draw_wall_scenery(
            draw,
            inner_spec,
            camera=camera,
            frame=frame,
            variant=str(spec.get("scenery_variant", "mountains")),
            outline=(74, 48, 37),
        )
        return list(outer)
    if object_type == "mirror":
        return _draw_wall_flat_object(draw, spec, camera=camera, frame=frame, fill=(106, 139, 154), trim=(56, 75, 85))
    if object_type == "wall_shelf":
        return _draw_wall_shelf_object(draw, spec, camera=camera, frame=frame)
    if object_type == "wall_fan":
        return _draw_wall_fan_object(draw, spec, camera=camera, frame=frame)
    if object_type == "air_conditioner":
        return _draw_wall_air_conditioner_object(draw, spec, camera=camera, frame=frame)
    if object_type == "hanging_plant":
        return _draw_wall_hanging_plant_object(draw, spec, camera=camera, frame=frame)
    if object_type == "hanging_coat":
        return _draw_wall_hanging_coat_object(draw, spec, camera=camera, frame=frame)
    if object_type == "wall_lamp":
        return _draw_wall_disc(
            draw,
            spec,
            camera=camera,
            frame=frame,
            fill=(240, 206, 112),
            outline=(82, 67, 42),
            radius_u=0.42,
            radius_v=0.46,
        )
    if object_type == "speaker":
        return _draw_wall_speaker_object(draw, spec, camera=camera, frame=frame)
    if object_type == "wall_cabinet":
        return _draw_wall_flat_object(draw, spec, camera=camera, frame=frame, fill=(126, 113, 96), trim=(64, 57, 48))
    if object_type == "poster":
        return _draw_wall_flat_object(draw, spec, camera=camera, frame=frame, fill=(189, 114, 108), trim=(96, 54, 52))
    return _draw_wall_flat_object(draw, spec, camera=camera, frame=frame, fill=(160, 160, 150), trim=(70, 70, 68))


def _draw_floor_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    color_role = str(spec.get("color_role", "furniture"))
    color = {
        "sofa": (107, 126, 153),
        "armchair": (130, 102, 145),
        "wood": (137, 111, 82),
        "bed": (139, 126, 166),
        "tv_floor": (38, 43, 52),
        "clock_floor": (232, 217, 160),
        "picture_frame_floor": (166, 110, 78),
        "mirror_floor": (128, 158, 170),
        "shelf_floor": (126, 105, 88),
        "fan_floor": (174, 187, 193),
        "ac_floor": (205, 216, 218),
        "coat_floor": (116, 80, 145),
        "plant": (76, 142, 92),
        "lamp": (218, 184, 93),
        "box": (185, 128, 60),
        "toy": (91, 154, 200),
    }.get(color_role, CONTEXT_OBJECT_COLORS[sum(ord(char) for char in str(spec["object_id"])) % len(CONTEXT_OBJECT_COLORS)])
    shape_type = str(spec["shape_type"])
    if shape_type == "table":
        return _draw_table_object(draw, spec, camera=camera, frame=frame, fill=color)
    if shape_type == "sphere":
        return _draw_sphere_object(draw, spec, camera=camera, frame=frame, fill=color)
    if shape_type == "cylinder":
        return _draw_cylinder_object(draw, spec, camera=camera, frame=frame, fill=color)
    if shape_type == "cone":
        return _draw_cone_object(draw, spec, camera=camera, frame=frame, fill=color)
    if shape_type == "pyramid":
        return _draw_pyramid_object(draw, spec, camera=camera, frame=frame, fill=color)
    if shape_type == "open_box":
        return _draw_open_box_object(draw, spec, camera=camera, frame=frame, fill=color)
    bbox = _draw_box_object(draw, spec, camera=camera, frame=frame, fill=color)
    if str(spec.get("object_type")) == "tv":
        inner = [
            float(bbox[0]) + (float(bbox[2]) - float(bbox[0])) * 0.14,
            float(bbox[1]) + (float(bbox[3]) - float(bbox[1])) * 0.14,
            float(bbox[2]) - (float(bbox[2]) - float(bbox[0])) * 0.14,
            float(bbox[3]) - (float(bbox[3]) - float(bbox[1])) * 0.14,
        ]
        draw.rectangle(tuple(inner), fill=(18, 25, 35), outline=(74, 88, 103), width=2)
    elif str(spec.get("object_type")) == "clock":
        inner = _inset_bbox(bbox, 0.22, 0.18)
        draw.ellipse(tuple(inner), fill=(245, 239, 205), outline=(45, 54, 62), width=2)
        cx = (float(inner[0]) + float(inner[2])) * 0.5
        cy = (float(inner[1]) + float(inner[3])) * 0.5
        radius = min(float(inner[2]) - float(inner[0]), float(inner[3]) - float(inner[1])) * 0.28
        for angle_index in range(12):
            angle = math.pi * 0.5 - angle_index * math.tau / 12.0
            tick_outer = (cx + math.cos(angle) * radius * 1.42, cy - math.sin(angle) * radius * 1.42)
            tick_inner = (cx + math.cos(angle) * radius * (1.12 if angle_index % 3 == 0 else 1.25), cy - math.sin(angle) * radius * (1.12 if angle_index % 3 == 0 else 1.25))
            _draw_line(draw, tick_inner, tick_outer, fill=(70, 77, 84), width=2 if angle_index % 3 == 0 else 1)
        _draw_line(draw, (cx, cy), (cx, cy - radius), fill=(38, 45, 54), width=2)
        _draw_line(draw, (cx, cy), (cx + radius * 0.78, cy + radius * 0.30), fill=(38, 45, 54), width=2)
        draw.ellipse((cx - 2.2, cy - 2.2, cx + 2.2, cy + 2.2), fill=(38, 45, 54))
    elif str(spec.get("object_type")) == "picture_frame":
        inner = _inset_bbox(bbox, 0.17, 0.16)
        draw.rectangle(tuple(_inset_bbox(bbox, 0.10, 0.10)), fill=(133, 86, 61), outline=(72, 46, 34), width=2)
        _draw_screen_scenery(draw, inner, variant=str(spec.get("scenery_variant", "mountains")), outline=(72, 46, 34))
    elif str(spec.get("object_type")) == "mirror":
        inner = _inset_bbox(bbox, 0.16, 0.12)
        draw.rectangle(tuple(inner), fill=(197, 226, 232), outline=(70, 91, 100), width=2)
        _draw_line(draw, (inner[0], inner[1]), (inner[2], inner[3]), fill=(229, 244, 247), width=2)
    elif str(spec.get("object_type")) == "bed":
        pillow = _inset_bbox(bbox, 0.24, 0.18)
        pillow[3] = pillow[1] + max(8.0, (float(bbox[3]) - float(bbox[1])) * 0.20)
        draw.rounded_rectangle(tuple(pillow), radius=4, fill=(233, 229, 218), outline=(116, 107, 136), width=1)
    elif str(spec.get("object_type")) == "wall_fan":
        face = _inset_bbox(bbox, 0.12, 0.10)
        face[3] = face[1] + max(16.0, (float(bbox[3]) - float(bbox[1])) * 0.56)
        draw.ellipse(tuple(face), fill=(214, 222, 224), outline=(45, 56, 66), width=2)
        cx = (float(face[0]) + float(face[2])) * 0.5
        cy = (float(face[1]) + float(face[3])) * 0.5
        radius = min(float(face[2]) - float(face[0]), float(face[3]) - float(face[1])) * 0.34
        for angle in (math.pi * 0.5, math.pi * 1.17, math.pi * 1.83):
            tip = (cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
            _draw_line(draw, (cx, cy), tip, fill=(96, 113, 124), width=2)
        for angle in (0.0, math.pi * 0.25, math.pi * 0.50, math.pi * 0.75, math.pi, math.pi * 1.25, math.pi * 1.50, math.pi * 1.75):
            tip = (cx + math.cos(angle) * radius * 1.22, cy + math.sin(angle) * radius * 1.22)
            _draw_line(draw, (cx, cy), tip, fill=(123, 137, 146), width=1)
        draw.ellipse((cx - 3.0, cy - 3.0, cx + 3.0, cy + 3.0), fill=(48, 58, 68))
        _draw_line(draw, (cx, float(face[3])), (cx, float(bbox[3])), fill=(45, 56, 66), width=2)
    elif str(spec.get("object_type")) == "air_conditioner":
        grille = _inset_bbox(bbox, 0.18, 0.18)
        grille[3] = grille[1] + max(10.0, (float(bbox[3]) - float(bbox[1])) * 0.24)
        draw.rectangle(tuple(grille), fill=(182, 197, 202), outline=(76, 91, 98), width=1)
        for index in range(4):
            y = float(grille[1]) + (index + 1) * (float(grille[3]) - float(grille[1])) / 4.0
            _draw_line(draw, (float(grille[0]) + 2.0, y), (float(grille[2]) - 2.0, y), fill=(86, 101, 108), width=1)
        side_vent = [
            float(bbox[2]) - (float(bbox[2]) - float(bbox[0])) * 0.20,
            float(bbox[1]) + (float(bbox[3]) - float(bbox[1])) * 0.22,
            float(bbox[2]) - (float(bbox[2]) - float(bbox[0])) * 0.08,
            float(bbox[1]) + (float(bbox[3]) - float(bbox[1])) * 0.70,
        ]
        draw.rectangle(tuple(side_vent), fill=(119, 137, 145), outline=(60, 72, 78), width=1)
        outlet = _inset_bbox(bbox, 0.20, 0.22)
        outlet[1] = float(bbox[1]) + (float(bbox[3]) - float(bbox[1])) * 0.58
        outlet[3] = float(bbox[1]) + (float(bbox[3]) - float(bbox[1])) * 0.78
        draw.rectangle(tuple(outlet), fill=(233, 238, 238), outline=(76, 91, 98), width=1)
        wheel_y = float(bbox[3]) - 3.0
        _draw_line(draw, (float(bbox[0]) + 5.0, wheel_y), (float(bbox[0]) + 14.0, wheel_y), fill=(58, 65, 70), width=2)
        _draw_line(draw, (float(bbox[2]) - 14.0, wheel_y), (float(bbox[2]) - 5.0, wheel_y), fill=(58, 65, 70), width=2)
    elif str(spec.get("object_type")) == "hanging_plant":
        x1, y1, x2, y2 = (float(value) for value in bbox)
        width = max(1.0, x2 - x1)
        height = max(1.0, y2 - y1)
        pot = [
            round(x1 + width * 0.24, 3),
            round(y1 + height * 0.58, 3),
            round(x2 - width * 0.24, 3),
            round(y2 - height * 0.08, 3),
        ]
        draw.rectangle(tuple(pot), fill=(137, 86, 55), outline=(68, 48, 34), width=2)
        leaves = _inset_bbox(bbox, 0.16, 0.14)
        leaves[3] = leaves[1] + max(12.0, (float(bbox[3]) - float(bbox[1])) * 0.38)
        draw.ellipse(tuple(leaves), fill=(63, 132, 80), outline=(35, 82, 48), width=2)
    elif str(spec.get("object_type")) == "hanging_coat":
        body = _inset_bbox(bbox, 0.14, 0.08)
        sleeve_y = body[1] + (body[3] - body[1]) * 0.30
        draw.polygon(
            [
                (body[0] + (body[2] - body[0]) * 0.15, body[1] + (body[3] - body[1]) * 0.12),
                (body[0] - (body[2] - body[0]) * 0.26, sleeve_y),
                (body[0] - (body[2] - body[0]) * 0.10, sleeve_y + (body[3] - body[1]) * 0.28),
                (body[0] + (body[2] - body[0]) * 0.28, body[1] + (body[3] - body[1]) * 0.40),
            ],
            fill=(98, 67, 124),
            outline=(53, 42, 68),
        )
        draw.polygon(
            [
                (body[2] - (body[2] - body[0]) * 0.15, body[1] + (body[3] - body[1]) * 0.12),
                (body[2] + (body[2] - body[0]) * 0.26, sleeve_y),
                (body[2] + (body[2] - body[0]) * 0.10, sleeve_y + (body[3] - body[1]) * 0.28),
                (body[2] - (body[2] - body[0]) * 0.28, body[1] + (body[3] - body[1]) * 0.40),
            ],
            fill=(107, 74, 135),
            outline=(53, 42, 68),
        )
        draw.polygon(
            [
                ((body[0] + body[2]) * 0.5, body[1]),
                (body[2], body[1] + (body[3] - body[1]) * 0.34),
                (body[2] - (body[2] - body[0]) * 0.12, body[3]),
                (body[0] + (body[2] - body[0]) * 0.12, body[3]),
                (body[0], body[1] + (body[3] - body[1]) * 0.34),
            ],
            fill=(116, 80, 145),
            outline=(53, 42, 68),
        )
        collar = [
            ((body[0] + body[2]) * 0.5, body[1] + (body[3] - body[1]) * 0.20),
            (body[0] + (body[2] - body[0]) * 0.36, body[1] + (body[3] - body[1]) * 0.08),
            (body[0] + (body[2] - body[0]) * 0.46, body[1] + (body[3] - body[1]) * 0.24),
            (body[2] - (body[2] - body[0]) * 0.46, body[1] + (body[3] - body[1]) * 0.24),
            (body[2] - (body[2] - body[0]) * 0.36, body[1] + (body[3] - body[1]) * 0.08),
        ]
        draw.polygon(collar, fill=(226, 218, 202), outline=(53, 42, 68))
        button_x = (float(body[0]) + float(body[2])) * 0.5
        for button_y in (body[1] + (body[3] - body[1]) * 0.44, body[1] + (body[3] - body[1]) * 0.64):
            draw.ellipse((button_x - 2.0, button_y - 2.0, button_x + 2.0, button_y + 2.0), fill=(226, 218, 202))
    return list(bbox)


def _draw_room_option_label(
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


def _room_object_bbox(spec: Mapping[str, Any], camera, frame) -> List[float]:
    if str(spec.get("object_role")) == "wall_object":
        return _projected_polygon_bbox(_wall_reference_points(spec), camera, frame, pad_px=8.0)
    return _object_screen_bbox(spec, camera, frame, pad_px=8.0)


def _wall_object_visible_bbox(spec: Mapping[str, Any], camera, frame) -> List[float]:
    return _projected_polygon_bbox(_wall_reference_points(spec), camera, frame, pad_px=0.0)


def _bbox_pixel_width_height(bbox: Sequence[float]) -> Tuple[float, float]:
    return float(bbox[2]) - float(bbox[0]), float(bbox[3]) - float(bbox[1])


def _wall_object_visible_size_ok(
    specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
    min_width_px: float,
    min_height_px: float,
) -> bool:
    for spec in specs:
        bbox = _wall_object_visible_bbox(spec, camera, frame)
        width, height = _bbox_pixel_width_height(bbox)
        if width < float(min_width_px) or height < float(min_height_px):
            return False
    return True


def render_room_scene_3d(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: _RenderParams,
) -> _RenderedRoomScene:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    camera_spec = dataset["camera"]
    frame_spec = dataset["projection_frame"]
    camera = type("CameraTuple", (), {})()
    camera.camera_position = tuple(float(value) for value in camera_spec["camera_position"])
    camera.target = tuple(float(value) for value in camera_spec["target"])
    camera.right = tuple(float(value) for value in camera_spec["right"])
    camera.up = tuple(float(value) for value in camera_spec["up"])
    camera.forward = tuple(float(value) for value in camera_spec["forward"])
    camera.yaw_degrees = float(camera_spec["yaw_degrees"])
    camera.pitch_degrees = float(camera_spec["pitch_degrees"])
    camera.distance = float(camera_spec["distance"])
    frame = type("FrameTuple", (), {})()
    frame.scale = float(frame_spec["scale"])
    frame.center_x = float(frame_spec["center_x"])
    frame.center_y = float(frame_spec["center_y"])
    frame.normalized_center_u = float(frame_spec["normalized_center_u"])
    frame.normalized_center_v = float(frame_spec["normalized_center_v"])

    scene_variant = str(dataset["scene_variant"])
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    room_bbox, entities = _draw_room_shell(draw, camera=camera, frame=frame, render_params=render_params, scene_variant=scene_variant)
    wall_specs = [dict(spec) for spec in dataset["wall_object_specs"]]
    floor_specs = [dict(spec) for spec in dataset["floor_object_specs"]]

    label_bboxes: Dict[str, List[float]] = {}
    for spec in sorted(wall_specs, key=lambda item: float(item["camera_distance"]), reverse=True):
        _draw_wall_object(draw, spec, camera=camera, frame=frame)
    for spec in sorted(floor_specs, key=lambda item: (float(item["camera_distance"]), -int(item.get("draw_order", 10))), reverse=True):
        _draw_floor_object(draw, spec, camera=camera, frame=frame)
    for spec in wall_specs:
        label = str(spec.get("point_label", ""))
        if label:
            center = (float(spec["screen_xy"][0]), float(spec["screen_xy"][1]))
            label_bboxes[str(spec["object_id"])] = _draw_room_option_label(draw, label=label, center=center, font=label_font)

    object_bboxes: Dict[str, List[float]] = {}
    object_centers: Dict[str, List[float]] = {}
    wall_object_bboxes: Dict[str, List[float]] = {}
    wall_object_centers: Dict[str, List[float]] = {}
    floor_object_bboxes: Dict[str, List[float]] = {}
    floor_object_centers: Dict[str, List[float]] = {}
    all_specs = [*wall_specs, *floor_specs]
    for spec in all_specs:
        object_id = str(spec["object_id"])
        bbox = _room_object_bbox(spec, camera, frame)
        if object_id in label_bboxes:
            bbox = _bbox_union(bbox, label_bboxes[object_id])
        center = [round(float(spec["screen_xy"][0]), 3), round(float(spec["screen_xy"][1]), 3)]
        object_bboxes[object_id] = list(bbox)
        object_centers[object_id] = list(center)
        if str(spec.get("object_role")) == "wall_object":
            wall_object_bboxes[object_id] = list(bbox)
            wall_object_centers[object_id] = list(center)
        else:
            floor_object_bboxes[object_id] = list(bbox)
            floor_object_centers[object_id] = list(center)
        entities.append(
            {
                "entity_id": object_id,
                "entity_type": "three_d_room_wall_object" if str(spec.get("object_role")) == "wall_object" else "three_d_room_floor_object",
                "bbox_px": list(bbox),
                "attrs": {
                    "object_type": str(spec["object_type"]),
                    "object_name": str(spec["object_name"]),
                    "prompt_name": str(spec["prompt_name"]),
                    "object_role": str(spec.get("object_role", "")),
                    "is_wall_mounted": bool(spec.get("is_wall_mounted", False)),
                    "mounting": str(spec.get("mounting", "")),
                    "wall": spec.get("wall"),
                    "world_xyz": list(spec["world_xyz"]),
                    "base_xyz": list(spec["base_xyz"]),
                    "dimensions_xyz": list(spec["dimensions_xyz"]),
                    "screen_xy": list(spec["screen_xy"]),
                    "camera_xyz": list(spec["camera_xyz"]),
                    "camera_distance": float(spec["camera_distance"]),
                    "scene_variant": str(scene_variant),
                    "support_object_id": spec.get("support_object_id"),
                    "support_surface_type": spec.get("support_surface_type"),
                    "is_reference_furniture": bool(spec.get("is_reference_furniture", False)),
                    "adjacent_wall": spec.get("adjacent_wall"),
                    "wall_axis_interval": spec.get("wall_axis_interval"),
                    "wall_gap": spec.get("wall_gap"),
                    "scenery_variant": spec.get("scenery_variant"),
                    "picture_content": spec.get("picture_content"),
                    "point_label": spec.get("point_label"),
                    "is_answer_candidate": bool(spec.get("is_answer_candidate", False)),
                },
            }
        )

    evidence_ids = [str(value) for value in dataset["target_object_ids"]]
    evidence_bboxes = [list(object_bboxes[object_id]) for object_id in evidence_ids]
    all_bboxes = [list(room_bbox), *[list(value) for value in object_bboxes.values()]]
    scene_bbox = [
        round(float(min(bbox[0] for bbox in all_bboxes)), 3),
        round(float(min(bbox[1] for bbox in all_bboxes)), 3),
        round(float(max(bbox[2] for bbox in all_bboxes)), 3),
        round(float(max(bbox[3] for bbox in all_bboxes)), 3),
    ]
    return _RenderedRoomScene(
        image=image,
        entities=list(entities),
        scene_bbox_px=list(scene_bbox),
        object_bboxes_px=dict(object_bboxes),
        object_centers_px=dict(object_centers),
        wall_object_bboxes_px=dict(wall_object_bboxes),
        wall_object_centers_px=dict(wall_object_centers),
        floor_object_bboxes_px=dict(floor_object_bboxes),
        floor_object_centers_px=dict(floor_object_centers),
        room_bbox_px=list(room_bbox),
        evidence_bboxes=list(evidence_bboxes),
        evidence_entity_ids=list(evidence_ids),
    )




def _build_complexity(
    *,
    target_count: int,
    wall_object_count: int,
    floor_object_count: int,
    same_type_floor_distractor_count: int,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.38)),
        "wall_relation": float(raw_weights.get("wall_relation", 0.34)),
        "distractor_binding": float(raw_weights.get("distractor_binding", 0.18)),
        "answer_load": float(raw_weights.get("answer_load", 0.10)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(float(wall_object_count + floor_object_count), 10.0, 19.0),
        "wall_relation": 0.72,
        "distractor_binding": _normalize_unit(float(same_type_floor_distractor_count), 1.0, 3.0),
        "answer_load": _normalize_unit(float(target_count), 0.0, 4.0),
    }
    score = sum(float(components[key]) * max(0.0, float(weights[key])) for key in weights) / float(total)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={key: round(float(value), 6) for key, value in components.items()},
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "room")
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
class ThreeDRoomWallMountedObjectCountTask:
    """Count target objects mounted on walls in a perspective 3D room."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "room"
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
        target_count, target_count_probabilities = _resolve_target_count(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_room_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            target_count=int(target_count),
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
        rendered_scene = render_room_scene_3d(background, dataset=dataset, render_params=render_params)
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
        target_plural = str(dataset["target_object_plural"])
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
                "target_plural": target_plural,
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]).format(target_plural=target_plural),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(target_plural=target_plural),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(dataset["target_count"])
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in rendered_scene.evidence_bboxes]
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        solver_trace = dict(dataset["solver_trace"])
        complexity = _build_complexity(
            target_count=int(answer_value),
            wall_object_count=int(dataset["wall_object_count"]),
            floor_object_count=int(dataset["floor_object_count"]),
            same_type_floor_distractor_count=int(dataset["same_type_floor_distractor_count"]),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_room_scene",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "target_object_type": str(dataset["target_object_type"]),
                    "target_object_plural": str(dataset["target_object_plural"]),
                    "target_count": int(answer_value),
                    "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                    "wall_object_count": int(dataset["wall_object_count"]),
                    "floor_object_count": int(dataset["floor_object_count"]),
                    "same_type_surface_distractor_count": int(dataset["same_type_surface_distractor_count"]),
                    "support_surface_count": int(dataset["support_surface_count"]),
                    "object_count": int(dataset["object_count"]),
                    "wall_object_type_counts": dict(dataset["wall_object_type_counts"]),
                    "floor_object_type_counts": dict(dataset["floor_object_type_counts"]),
                    "view_family": "synthetic_perspective_3d_room",
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
                    "target_object_type": str(dataset["target_object_type"]),
                    "target_object_name": str(dataset["target_object_name"]),
                    "target_object_plural": str(dataset["target_object_plural"]),
                    "target_count": int(answer_value),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "object_count": int(dataset["object_count"]),
                    "wall_object_count": int(dataset["wall_object_count"]),
                    "floor_object_count": int(dataset["floor_object_count"]),
                    "same_type_surface_distractor_count": int(dataset["same_type_surface_distractor_count"]),
                    "support_surface_count": int(dataset["support_surface_count"]),
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
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "wall_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.wall_object_bboxes_px.items()},
                "wall_object_centers_px": {str(key): list(value) for key, value in rendered_scene.wall_object_centers_px.items()},
                "floor_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.floor_object_bboxes_px.items()},
                "floor_object_centers_px": {str(key): list(value) for key, value in rendered_scene.floor_object_centers_px.items()},
                "target_object_bboxes_px": {str(key): list(rendered_scene.object_bboxes_px[str(key)]) for key in dataset["target_object_ids"]},
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "target_object_type": str(dataset["target_object_type"]),
                "target_object_name": str(dataset["target_object_name"]),
                "target_object_plural": str(dataset["target_object_plural"]),
                "target_count": int(answer_value),
                "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                "wall_object_specs": [dict(spec) for spec in dataset["wall_object_specs"]],
                "floor_object_specs": [dict(spec) for spec in dataset["floor_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "object_count": int(dataset["object_count"]),
                "wall_object_count": int(dataset["wall_object_count"]),
                "floor_object_count": int(dataset["floor_object_count"]),
                "same_type_floor_distractor_count": int(dataset["same_type_floor_distractor_count"]),
                "same_type_surface_distractor_count": int(dataset["same_type_surface_distractor_count"]),
                "support_surface_count": int(dataset["support_surface_count"]),
                "object_type_counts": dict(dataset["object_type_counts"]),
                "wall_object_type_counts": dict(dataset["wall_object_type_counts"]),
                "floor_object_type_counts": dict(dataset["floor_object_type_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "view_family": "synthetic_perspective_3d_room",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(value) for value in dataset["target_object_ids"]],
                "answer": int(answer_value),
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
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["ThreeDRoomWallMountedObjectCountTask"]
