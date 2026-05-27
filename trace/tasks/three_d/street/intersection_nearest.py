"""Nearest-to-intersection task for a synthetic 3D street scene."""

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
from ...shared.deterministic_sampling import (
    resolve_selection_index,
    uniform_probability_map,
)
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
from ..shared.task_support import resolve_count as _shared_resolve_count
from ..shared.color_variation import resolve_three_d_object_fill_rgb
from ..shared.object_resources import (
    BUILDING_STYLE_BASE_COLORS,
    BUILDING_STYLE_DIMENSION_FACTORS,
    BUILDING_STYLE_DISPLAY_NAMES,
    BUILDING_STYLE_POOLS,
    BUILDING_STYLES,
    STREET_CONTEXT_OBJECT_TYPES,
    STREET_OBJECT_BASE_DIMENSIONS,
    STREET_OBJECT_COLORS,
    STREET_OBJECT_NAMES,
    STREET_OBJECT_TYPES,
    STREET_RADIAL_OBJECT_TYPES,
    STREET_VEHICLE_OBJECT_TYPES,
)
from ..spatial.camera_distance import (
    POINT_LABELS,
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
    _draw_sphere_object,
    _object_reference_points,
    _object_screen_bbox,
    _polygon_axis_line_segment,
    _project_screen,
    _project_xy,
    _sample_camera,
    _screen_to_floor_xy,
    _shade,
    _sub_box_spec,
    _tint,
)


TASK_ID = "task_three_d__street__intersection_nearest_label"
SCENE_ID = "street"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = ("closest_to_intersection",)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "downtown_intersection",
    "neighborhood_intersection",
    "transit_intersection",
)
SUPPORTED_INTERSECTION_LAYOUTS: Tuple[str, ...] = (
    "four_way",
    "t_missing_north",
    "t_missing_south",
    "t_missing_east",
    "t_missing_west",
)
STREET_CAMERA_YAW_BANDS_DEGREES: Tuple[Tuple[float, float], ...] = (
    (-54.0, -28.0),
    (28.0, 54.0),
    (-146.0, -116.0),
    (116.0, 146.0),
)
VEHICLE_OBJECT_TYPES = set(STREET_VEHICLE_OBJECT_TYPES)
ANSWER_SLOTS: Tuple[Tuple[float, float], ...] = (
    (-0.84, -0.22),
    (0.84, 0.22),
    (-0.22, 0.84),
    (0.22, -0.84),
)
DISTRACTOR_SLOTS: Tuple[Tuple[float, float], ...] = (
    (-2.12, 0.32),
    (2.14, -0.32),
    (0.35, 2.24),
    (-0.35, -2.24),
    (-2.28, -1.54),
    (2.30, 1.54),
    (-1.48, 2.70),
    (1.48, -2.70),
    (-3.04, 0.42),
    (3.02, -0.42),
)
MIN_CANDIDATE_VISIBLE_PX = 20.0
MIN_CANDIDATE_CENTER_SEPARATION_PX = 42.0
MAX_CANDIDATE_BBOX_INTERSECTION_PX = 6500.0
MIN_NEAREST_DISTANCE_MARGIN = 0.52
INTERSECTION_CENTER_XY: Tuple[float, float] = (0.0, 0.0)
DEFAULT_INTERSECTION_CENTER_JITTER_X = 0.62
DEFAULT_INTERSECTION_CENTER_JITTER_Y = 0.54
STREET_FULL_BLEED_FALLBACK_EXTENT_MULTIPLIER = 3.2


@dataclass(frozen=True)
class _StreetRenderParams:
    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    room_extent: float
    street_extent: float
    road_half_width: float
    marker_radius_px: int
    label_font_size_px: int
    line_width_px: int
    sidewalk_rgb: Tuple[int, int, int]
    asphalt_rgb: Tuple[int, int, int]
    road_mark_rgb: Tuple[int, int, int]
    crosswalk_rgb: Tuple[int, int, int]
    curb_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedStreetScene:
    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    street_bbox_px: List[float]
    object_bboxes_px: Dict[str, List[float]]
    object_centers_px: Dict[str, List[float]]
    candidate_bboxes_px: Dict[str, List[float]]
    candidate_centers_px: Dict[str, List[float]]
    context_object_bboxes_px: Dict[str, List[float]]
    context_object_centers_px: Dict[str, List[float]]
    evidence_bboxes: List[List[float]]
    evidence_entity_ids: List[str]








def _min_pairwise(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 999.0
    return min(
        abs(float(a) - float(b))
        for index, a in enumerate(values)
        for b in values[index + 1 :]
    )






def _resolve_camera_yaw_band(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
) -> Tuple[Tuple[float, float], Dict[str, float], int]:
    explicit = params.get("camera_yaw_band_index")
    support = tuple(range(len(STREET_CAMERA_YAW_BANDS_DEGREES)))
    if explicit is not None:
        selected_index = int(explicit)
        if selected_index not in set(support):
            raise ValueError(f"unsupported camera_yaw_band_index: {selected_index}")
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.camera_yaw_band_index",
        )
        selected_index = int(support[abs(int(selection_index)) % len(support)])
    probabilities = dict(uniform_probability_map(support, selected=int(selected_index) if explicit is not None else None))
    return (
        tuple(float(value) for value in STREET_CAMERA_YAW_BANDS_DEGREES[int(selected_index)]),
        {str(key): float(value) for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))},
        int(selected_index),
    )


def _sample_intersection_center(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_params: _StreetRenderParams,
) -> Tuple[float, float]:
    explicit = params.get("intersection_center_xy")
    if isinstance(explicit, Sequence) and not isinstance(explicit, (str, bytes)) and len(explicit) >= 2:
        return (
            round(max(-1.0, min(1.0, float(explicit[0]))), 4),
            round(max(-1.0, min(1.0, float(explicit[1]))), 4),
        )
    max_x = min(
        float(DEFAULT_INTERSECTION_CENTER_JITTER_X),
        float(group_default(gen_defaults, "intersection_center_jitter_x", DEFAULT_INTERSECTION_CENTER_JITTER_X)),
        max(0.0, float(render_params.street_extent) - float(render_params.road_half_width) - 2.75),
    )
    max_y = min(
        float(DEFAULT_INTERSECTION_CENTER_JITTER_Y),
        float(group_default(gen_defaults, "intersection_center_jitter_y", DEFAULT_INTERSECTION_CENTER_JITTER_Y)),
        max(0.0, float(render_params.street_extent) - float(render_params.road_half_width) - 2.85),
    )
    return (
        round(float(rng.uniform(-max_x, max_x)), 4),
        round(float(rng.uniform(-max_y, max_y)), 4),
    )


def _resolve_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> _StreetRenderParams:
    merged = dict(render_defaults)
    merged.update(dict(params))
    street_extent = _float_value(merged, "street_extent", 4.45)
    return _StreetRenderParams(
        canvas_width=_int_value(merged, "canvas_width", 1180),
        canvas_height=_int_value(merged, "canvas_height", 920),
        scene_margin_left_px=_int_value(merged, "scene_margin_left_px", 48),
        scene_margin_right_px=_int_value(merged, "scene_margin_right_px", 48),
        scene_margin_top_px=_int_value(merged, "scene_margin_top_px", 42),
        scene_margin_bottom_px=_int_value(merged, "scene_margin_bottom_px", 52),
        room_extent=float(street_extent),
        street_extent=float(street_extent),
        road_half_width=_float_value(merged, "road_half_width", 1.02),
        marker_radius_px=_int_value(merged, "marker_radius_px", 20),
        label_font_size_px=_int_value(merged, "label_font_size_px", 25),
        line_width_px=_int_value(merged, "line_width_px", 2),
        sidewalk_rgb=_rgb(merged.get("sidewalk_rgb", (214, 222, 218)), (214, 222, 218)),
        asphalt_rgb=_rgb(merged.get("asphalt_rgb", (86, 93, 101)), (86, 93, 101)),
        road_mark_rgb=_rgb(merged.get("road_mark_rgb", (236, 210, 86)), (236, 210, 86)),
        crosswalk_rgb=_rgb(merged.get("crosswalk_rgb", (240, 243, 238)), (240, 243, 238)),
        curb_rgb=_rgb(merged.get("curb_rgb", (157, 168, 171)), (157, 168, 171)),
        text_rgb=_rgb(merged.get("text_rgb", (24, 28, 36)), (24, 28, 36)),
        text_stroke_rgb=_rgb(merged.get("text_stroke_rgb", (255, 255, 255)), (255, 255, 255)),
    )


def _street_object_name(object_type: str) -> str:
    return str(STREET_OBJECT_NAMES.get(str(object_type), str(object_type).replace("_", " ")))


def _street_object_fill_rgb(spec: Mapping[str, Any]) -> Tuple[int, int, int]:
    object_type = str(spec.get("object_type", ""))
    if object_type == "building":
        base = BUILDING_STYLE_BASE_COLORS.get(
            str(spec.get("building_style", "")),
            STREET_OBJECT_COLORS.get(object_type, (116, 126, 139)),
        )
    else:
        base = STREET_OBJECT_COLORS.get(object_type, (116, 126, 139))
    if bool(spec.get("is_answer_candidate", False)):
        strength = 0.18
        salt = "street.candidate"
    elif object_type in {"building", "bench", "street_sign"}:
        strength = 0.28
        salt = "street.context.strong"
    else:
        strength = 0.16
        salt = "street.context"
    return resolve_three_d_object_fill_rgb(
        spec,
        base_rgb=base,
        salt=salt,
        variation_strength=float(strength),
    )


def _base_street_object_dimensions(object_type: str) -> Tuple[float, float, float]:
    return tuple(float(value) for value in STREET_OBJECT_BASE_DIMENSIONS.get(str(object_type), (0.6, 0.44, 0.42)))


def _dimensions_for_orientation(
    object_type: str,
    *,
    orientation_axis: str,
    scale: float,
) -> Tuple[float, float, float]:
    length, width, height = _base_street_object_dimensions(str(object_type))
    if str(object_type) in STREET_RADIAL_OBJECT_TYPES:
        return (round(float(width * scale), 4), round(float(width * scale), 4), round(float(height * scale), 4))
    if str(orientation_axis) == "y":
        return (round(float(width * scale), 4), round(float(length * scale), 4), round(float(height * scale), 4))
    return (round(float(length * scale), 4), round(float(width * scale), 4), round(float(height * scale), 4))


def _orientation_axis_for_xy(xy: Sequence[float]) -> str:
    return "x" if abs(float(xy[0])) >= abs(float(xy[1])) else "y"


def _missing_arm_for_layout(intersection_layout: str) -> str | None:
    layout = str(intersection_layout)
    if layout.startswith("t_missing_"):
        return layout.removeprefix("t_missing_")
    return None


def _arm_is_present(intersection_layout: str, arm: str) -> bool:
    return _missing_arm_for_layout(str(intersection_layout)) != str(arm)


def _slot_allowed_for_layout(
    relative_xy: Sequence[float],
    *,
    intersection_layout: str,
    road_half_width: float,
) -> bool:
    missing = _missing_arm_for_layout(str(intersection_layout))
    if missing is None:
        return True
    x, y = float(relative_xy[0]), float(relative_xy[1])
    corridor = float(road_half_width) * 1.04
    offset = float(road_half_width) * 1.20
    if missing == "north":
        return not (abs(x) < corridor and y > offset)
    if missing == "south":
        return not (abs(x) < corridor and y < -offset)
    if missing == "east":
        return not (x > offset and abs(y) < corridor)
    if missing == "west":
        return not (x < -offset and abs(y) < corridor)
    return True


def _translate_scene_xy(
    relative_xy: Sequence[float],
    *,
    center_xy: Sequence[float],
    extent: float,
    margin: float,
    rng=None,
    jitter: float = 0.0,
) -> Tuple[float, float]:
    x = float(center_xy[0]) + float(relative_xy[0])
    y = float(center_xy[1]) + float(relative_xy[1])
    if rng is not None and float(jitter) > 0.0:
        x += float(rng.uniform(-float(jitter), float(jitter)))
        y += float(rng.uniform(-float(jitter), float(jitter)))
    limit = max(0.1, float(extent) - float(margin))
    return (
        round(max(-limit, min(limit, x)), 4),
        round(max(-limit, min(limit, y)), 4),
    )


def _make_street_object_spec(
    *,
    object_id: str,
    object_type: str,
    object_role: str,
    xy: Tuple[float, float],
    intersection_center_xy: Tuple[float, float],
    orientation_axis: str,
    dimensions_xyz: Tuple[float, float, float],
    label: str | None,
    dimension_scale: float,
) -> Dict[str, Any]:
    width, depth, height = (float(value) for value in dimensions_xyz)
    x, y = float(xy[0]), float(xy[1])
    center_x, center_y = float(intersection_center_xy[0]), float(intersection_center_xy[1])
    ground_distance = math.hypot(x - center_x, y - center_y)
    footprint_radius = 0.5 * math.sqrt(float(width) * float(width) + float(depth) * float(depth))
    spec: Dict[str, Any] = {
        "object_id": str(object_id),
        "object_type": str(object_type),
        "object_name": _street_object_name(str(object_type)),
        "prompt_name": _street_object_name(str(object_type)),
        "object_role": str(object_role),
        "orientation_axis": str(orientation_axis),
        "is_answer_candidate": bool(label),
        "dimension_scale": round(float(dimension_scale), 4),
        "world_xyz": [round(x, 4), round(y, 4), round(float(height * 0.5), 4)],
        "base_xyz": [round(x, 4), round(y, 4), 0.0],
        "dimensions_xyz": [round(width, 4), round(depth, 4), round(height, 4)],
        "footprint_radius": round(float(footprint_radius), 4),
        "intersection_center_xy": [round(float(center_x), 4), round(float(center_y), 4)],
        "ground_distance_to_intersection": round(float(ground_distance), 4),
    }
    if label is not None:
        spec.update(
            {
                "point_id": f"street_object_{label}",
                "point_label": str(label),
                "object_label": str(label),
            }
        )
    if str(object_type) == "pedestrian":
        gender_id = "female" if _stable_palette_index(str(object_id), 2) == 1 else "male"
        spec.update(
            {
                "pedestrian_gender_id": str(gender_id),
                "pedestrian_appearance_id": f"pedestrian_{gender_id}",
            }
        )
    return spec


def _sample_candidate_specs(
    *,
    rng,
    candidate_count: int,
    intersection_center_xy: Tuple[float, float],
    intersection_layout: str,
    road_half_width: float,
    street_extent: float,
) -> List[Dict[str, Any]]:
    object_types = list(STREET_OBJECT_TYPES)
    rng.shuffle(object_types)
    selected_types = object_types[: int(candidate_count)]
    answer_slots = [
        slot for slot in ANSWER_SLOTS
        if _slot_allowed_for_layout(slot, intersection_layout=str(intersection_layout), road_half_width=float(road_half_width))
    ] or list(ANSWER_SLOTS)
    distractor_slots = [
        slot for slot in DISTRACTOR_SLOTS
        if _slot_allowed_for_layout(slot, intersection_layout=str(intersection_layout), road_half_width=float(road_half_width))
    ] or list(DISTRACTOR_SLOTS)
    rng.shuffle(answer_slots)
    rng.shuffle(distractor_slots)
    if int(candidate_count) - 1 > len(distractor_slots):
        raise ValueError("not enough street-object distractor slots")
    raw_slots: List[Tuple[Tuple[float, float], bool]] = [(answer_slots[0], True)]
    raw_slots.extend((slot, False) for slot in distractor_slots[: int(candidate_count) - 1])
    rng.shuffle(raw_slots)
    specs: List[Dict[str, Any]] = []
    for index, (slot_xy, is_answer_slot) in enumerate(raw_slots):
        object_type = str(selected_types[index])
        jitter = 0.055 if bool(is_answer_slot) else 0.115
        xy = (
            float(slot_xy[0] + rng.uniform(-jitter, jitter)),
            float(slot_xy[1] + rng.uniform(-jitter, jitter)),
        )
        xy = _translate_scene_xy(
            xy,
            center_xy=intersection_center_xy,
            extent=float(street_extent),
            margin=0.44,
        )
        orientation_axis = _orientation_axis_for_xy(xy)
        scale = float(rng.uniform(0.92, 1.12))
        dimensions = _dimensions_for_orientation(
            object_type,
            orientation_axis=orientation_axis,
            scale=float(scale),
        )
        specs.append(
            _make_street_object_spec(
                object_id=f"candidate_{index}_{object_type}",
                object_type=str(object_type),
                object_role="street_candidate",
                xy=xy,
                intersection_center_xy=tuple(float(value) for value in intersection_center_xy),
                orientation_axis=str(orientation_axis),
                dimensions_xyz=dimensions,
                label="?",
                dimension_scale=float(scale),
            )
        )
    return list(specs)


def _sample_context_specs(
    *,
    rng,
    scene_variant: str,
    context_object_count: int,
    intersection_center_xy: Tuple[float, float],
    intersection_layout: str,
    road_half_width: float,
    street_extent: float,
) -> List[Dict[str, Any]]:
    building_height_ranges = {
        "downtown_intersection": (1.12, 1.78),
        "neighborhood_intersection": (0.76, 1.22),
        "transit_intersection": (0.94, 1.52),
    }
    building_slots = [
        (-3.36, -3.20),
        (3.28, -3.26),
        (-3.30, 3.24),
        (3.36, 3.18),
        (-3.66, -1.55),
        (-3.66, 1.55),
        (3.66, -1.55),
        (3.66, 1.55),
        (-3.72, -2.58),
        (3.72, -2.58),
        (-3.72, 2.58),
        (3.72, 2.58),
        (-1.55, -3.66),
        (1.55, -3.66),
        (-1.55, 3.66),
        (1.55, 3.66),
        (-2.58, -3.72),
        (2.58, -3.72),
        (-2.58, 3.72),
        (2.58, 3.72),
    ]
    missing_arm = _missing_arm_for_layout(str(intersection_layout))
    if missing_arm == "north":
        building_slots.extend([(-0.58, 3.24), (0.64, 3.34)])
    elif missing_arm == "south":
        building_slots.extend([(-0.58, -3.24), (0.64, -3.34)])
    elif missing_arm == "east":
        building_slots.extend([(3.28, -0.62), (3.38, 0.62)])
    elif missing_arm == "west":
        building_slots.extend([(-3.28, -0.62), (-3.38, 0.62)])
    rng.shuffle(building_slots)
    context_specs: List[Dict[str, Any]] = []
    min_h, max_h = building_height_ranges.get(str(scene_variant), (0.92, 1.42))
    building_count = min(max(5, int(round(rng.uniform(5.2, 6.8)))), int(context_object_count), len(building_slots))
    building_styles = list(BUILDING_STYLE_POOLS.get(str(scene_variant), BUILDING_STYLES))
    rng.shuffle(building_styles)
    for index, relative_xy in enumerate(building_slots[:building_count]):
        xy = _translate_scene_xy(
            relative_xy,
            center_xy=intersection_center_xy,
            extent=float(street_extent),
            margin=0.62,
            rng=rng,
            jitter=0.18,
        )
        building_style = str(building_styles[index % len(building_styles)])
        width_factor, depth_factor, height_factor = (
            float(value)
            for value in BUILDING_STYLE_DIMENSION_FACTORS.get(str(building_style), (1.0, 1.0, 1.0))
        )
        scale = float(rng.uniform(0.92, 1.16))
        base_w, base_d, _base_h = _base_street_object_dimensions("building")
        height = float(rng.uniform(float(min_h), float(max_h))) * float(height_factor)
        dimensions = (
            round(float(base_w * scale * width_factor), 4),
            round(float(base_d * scale * depth_factor), 4),
            round(float(height), 4),
        )
        spec = _make_street_object_spec(
            object_id=f"context_building_{index}",
            object_type="building",
            object_role="street_context",
            xy=(float(xy[0]), float(xy[1])),
            intersection_center_xy=tuple(float(value) for value in intersection_center_xy),
            orientation_axis="x",
            dimensions_xyz=dimensions,
            label=None,
            dimension_scale=float(scale),
        )
        spec.update(
            {
                "building_style": str(building_style),
                "building_style_name": str(BUILDING_STYLE_DISPLAY_NAMES.get(str(building_style), "building")),
            }
        )
        context_specs.append(spec)
    corner = float(road_half_width) + 0.34
    optional_context = [
        ("tree", (-2.34, -2.74), "x", 0.20),
        ("tree", (2.36, 2.74), "x", 0.20),
        ("tree", (-2.58, 2.42), "x", 0.20),
        ("tree", (2.72, -2.38), "x", 0.20),
        ("tree", (-3.28, 0.92), "x", 0.18),
        ("tree", (3.24, -0.92), "x", 0.18),
        ("shrub", (-2.92, -2.12), "x", 0.18),
        ("shrub", (2.92, 2.12), "x", 0.18),
        ("shrub", (-2.96, 2.02), "x", 0.18),
        ("shrub", (2.96, -2.02), "x", 0.18),
        ("shrub", (-3.40, -0.82), "x", 0.16),
        ("shrub", (3.40, 0.82), "x", 0.16),
        ("traffic_light", (-corner, -corner), "x", 0.08),
        ("traffic_light", (corner, corner), "x", 0.08),
        ("traffic_light", (-corner, corner), "x", 0.08),
        ("street_sign", (corner + 0.20, -corner), "y", 0.11),
        ("street_sign", (-corner - 0.20, corner), "y", 0.11),
        ("street_sign", (corner + 0.18, corner + 0.10), "y", 0.11),
        ("bench", (-2.78, 1.44), "x", 0.18),
        ("bench", (2.78, -1.44), "x", 0.18),
        ("bench", (2.58, 1.70), "x", 0.18),
    ]
    if str(scene_variant) == "transit_intersection":
        optional_context.append(("street_sign", (-2.65, -1.36), "x", 0.12))
    optional_context = [
        item for item in optional_context
        if _slot_allowed_for_layout(item[1], intersection_layout=str(intersection_layout), road_half_width=float(road_half_width))
        or str(item[0]) not in {"traffic_light", "street_sign"}
    ]
    rng.shuffle(optional_context)
    target_optional = max(0, int(context_object_count) - len(context_specs))
    for index, (object_type, relative_xy, orientation_axis, jitter) in enumerate(optional_context[:target_optional]):
        xy = _translate_scene_xy(
            relative_xy,
            center_xy=intersection_center_xy,
            extent=float(street_extent),
            margin=0.48,
            rng=rng,
            jitter=float(jitter),
        )
        scale = float(rng.uniform(0.92, 1.14))
        dimensions = _dimensions_for_orientation(
            str(object_type),
            orientation_axis=str(orientation_axis),
            scale=float(scale),
        )
        context_specs.append(
            _make_street_object_spec(
                object_id=f"context_{index}_{object_type}",
                object_type=str(object_type),
                object_role="street_context",
                xy=(float(xy[0]), float(xy[1])),
                intersection_center_xy=tuple(float(value) for value in intersection_center_xy),
                orientation_axis=str(orientation_axis),
                dimensions_xyz=dimensions,
                label=None,
                dimension_scale=float(scale),
            )
        )
    return list(context_specs)


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


def _candidate_screen_separation_ok(
    specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
    render_params: _StreetRenderParams,
) -> bool:
    bboxes = [_object_screen_bbox(spec, camera, frame, pad_px=16.0) for spec in specs]
    centers = [(float(spec["screen_xy"][0]), float(spec["screen_xy"][1])) for spec in specs]
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
    return True


def _bbox_area(bbox: Sequence[float]) -> float:
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _candidate_context_visibility_ok(
    candidate_specs: Sequence[Mapping[str, Any]],
    context_specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
) -> bool:
    candidate_bboxes = {
        str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=22.0)
        for spec in candidate_specs
    }
    context_bboxes = {
        str(spec["object_id"]): _object_screen_bbox(spec, camera, frame, pad_px=10.0)
        for spec in context_specs
    }
    for candidate in candidate_specs:
        candidate_bbox = candidate_bboxes[str(candidate["object_id"])]
        candidate_area = max(1.0, _bbox_area(candidate_bbox))
        for context in context_specs:
            if float(context["camera_distance"]) >= float(candidate["camera_distance"]) - 0.05:
                continue
            context_bbox = context_bboxes[str(context["object_id"])]
            overlap = _bbox_intersection_area(candidate_bbox, context_bbox)
            if overlap > 900.0 and overlap / candidate_area > 0.10:
                return False
    return True


def _build_street_dataset(
    *,
    params: Mapping[str, Any],
    query_variant: str,
    scene_variant: str,
    intersection_layout: str,
    candidate_count: int,
    context_object_count: int,
    camera_yaw_band: Tuple[float, float],
    camera_yaw_band_index: int,
    render_params: _StreetRenderParams,
    instance_seed: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    for _attempt in range(360):
        intersection_center_xy = _sample_intersection_center(
            rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            render_params=render_params,
        )
        camera = _sample_camera(rng, yaw_band_degrees=tuple(float(value) for value in camera_yaw_band))
        candidate_specs = _sample_candidate_specs(
            rng=rng,
            candidate_count=int(candidate_count),
            intersection_center_xy=tuple(intersection_center_xy),
            intersection_layout=str(intersection_layout),
            road_half_width=float(render_params.road_half_width),
            street_extent=float(render_params.street_extent),
        )
        context_specs = _sample_context_specs(
            rng=rng,
            scene_variant=str(scene_variant),
            context_object_count=int(context_object_count),
            intersection_center_xy=tuple(intersection_center_xy),
            intersection_layout=str(intersection_layout),
            road_half_width=float(render_params.road_half_width),
            street_extent=float(render_params.street_extent),
        )
        all_specs = [*candidate_specs, *context_specs]
        reference_points: List[Tuple[float, float, float]] = [
            (-render_params.street_extent, -render_params.street_extent, 0.0),
            (render_params.street_extent, -render_params.street_extent, 0.0),
            (render_params.street_extent, render_params.street_extent, 0.0),
            (-render_params.street_extent, render_params.street_extent, 0.0),
            (-render_params.street_extent, -render_params.street_extent, 1.7),
            (render_params.street_extent, render_params.street_extent, 1.7),
        ]
        for spec in all_specs:
            reference_points.extend(_object_reference_points(spec))
        frame = _build_projection_frame(
            camera=camera,
            render_params=render_params,
            point_worlds=reference_points,
        )
        if not _canvas_floor_polygon_available(camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_candidates = _finalize_specs(candidate_specs, camera=camera, frame=frame)
        finalized_context = _finalize_specs(context_specs, camera=camera, frame=frame)
        if not _candidate_screen_separation_ok(
            finalized_candidates,
            camera=camera,
            frame=frame,
            render_params=render_params,
        ):
            continue
        if not _candidate_context_visibility_ok(
            finalized_candidates,
            finalized_context,
            camera=camera,
            frame=frame,
        ):
            continue
        sorted_by_distance = sorted(
            finalized_candidates,
            key=lambda spec: (float(spec["ground_distance_to_intersection"]), str(spec["object_id"])),
        )
        distance_values = [float(spec["ground_distance_to_intersection"]) for spec in finalized_candidates]
        if len(sorted_by_distance) < 2:
            continue
        nearest_margin = float(sorted_by_distance[1]["ground_distance_to_intersection"]) - float(sorted_by_distance[0]["ground_distance_to_intersection"])
        if nearest_margin < MIN_NEAREST_DISTANCE_MARGIN:
            continue

        answer_object_id = str(sorted_by_distance[0]["object_id"])
        answer_label_index = abs(
            int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}.answer_label",
                )
            )
        ) % int(candidate_count)
        answer_label = str(POINT_LABELS[int(answer_label_index)])
        remaining_labels = [
            str(label)
            for label in POINT_LABELS[: int(candidate_count)]
            if str(label) != str(answer_label)
        ]
        rng.shuffle(remaining_labels)
        relabeled_candidates: List[Dict[str, Any]] = []
        for spec in finalized_candidates:
            updated = dict(spec)
            label = str(answer_label) if str(updated["object_id"]) == answer_object_id else str(remaining_labels.pop())
            updated.update(
                {
                    "object_id": f"street_object_{label}",
                    "point_id": f"street_object_{label}",
                    "point_label": str(label),
                    "object_label": str(label),
                    "is_answer_candidate": True,
                }
            )
            relabeled_candidates.append(updated)
        sorted_by_distance = sorted(
            relabeled_candidates,
            key=lambda spec: (float(spec["ground_distance_to_intersection"]), str(spec["point_label"])),
        )
        answer_spec = next(spec for spec in relabeled_candidates if str(spec["point_label"]) == str(answer_label))
        all_finalized = [*relabeled_candidates, *finalized_context]
        candidate_ground_distances = {
            str(spec["point_label"]): round(float(spec["ground_distance_to_intersection"]), 4)
            for spec in relabeled_candidates
        }
        candidate_ground_xy = {
            str(spec["point_label"]): [round(float(spec["base_xyz"][0]), 4), round(float(spec["base_xyz"][1]), 4)]
            for spec in relabeled_candidates
        }
        candidate_object_types = {
            str(spec["point_label"]): str(spec["object_type"]) for spec in relabeled_candidates
        }
        candidate_projected_bboxes = {
            str(spec["point_label"]): [
                round(float(value), 3)
                for value in _object_screen_bbox(spec, camera, frame, pad_px=0.0)
            ]
            for spec in relabeled_candidates
        }
        return {
            "query_variant": str(query_variant),
            "scene_variant": str(scene_variant),
            "intersection_layout": str(intersection_layout),
            "missing_road_arm": _missing_arm_for_layout(str(intersection_layout)),
            "candidate_count": int(candidate_count),
            "context_object_count": int(context_object_count),
            "intersection_center_xy": [round(float(intersection_center_xy[0]), 4), round(float(intersection_center_xy[1]), 4)],
            "candidate_object_specs": sorted(relabeled_candidates, key=lambda spec: str(spec["point_label"])),
            "context_object_specs": sorted(finalized_context, key=lambda spec: str(spec["object_id"])),
            "object_specs": sorted(all_finalized, key=lambda spec: str(spec["object_id"])),
            "target_object_ids": [str(answer_spec["object_id"])],
            "answer_label": str(answer_label),
            "answer_object_id": str(answer_spec["object_id"]),
            "answer_object_type": str(answer_spec["object_type"]),
            "candidate_ground_xy_by_label": dict(sorted(candidate_ground_xy.items())),
            "ground_distance_to_intersection_by_label": dict(sorted(candidate_ground_distances.items())),
            "candidate_object_types_by_label": dict(sorted(candidate_object_types.items())),
            "candidate_projected_bboxes_by_label": dict(sorted(candidate_projected_bboxes.items())),
            "distance_order_near_to_far": [str(spec["point_label"]) for spec in sorted_by_distance],
            "nearest_distance_margin": round(float(nearest_margin), 4),
            "min_pairwise_ground_distance_gap": round(float(_min_pairwise(distance_values)), 4),
            "object_count": int(len(all_finalized)),
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
                "sort_key": "ground_distance_to_intersection",
                "candidate_only": True,
                "intersection_center_xy": [round(float(intersection_center_xy[0]), 4), round(float(intersection_center_xy[1]), 4)],
                "intersection_layout": str(intersection_layout),
                "missing_road_arm": _missing_arm_for_layout(str(intersection_layout)),
                "ground_distance_to_intersection_by_label": dict(sorted(candidate_ground_distances.items())),
                "distance_order_near_to_far": [str(spec["point_label"]) for spec in sorted_by_distance],
                "candidate_object_types_by_label": dict(sorted(candidate_object_types.items())),
                "context_building_styles_by_id": {
                    str(spec["object_id"]): str(spec.get("building_style", ""))
                    for spec in sorted(finalized_context, key=lambda item: str(item["object_id"]))
                    if str(spec.get("object_type")) == "building"
                },
                "nearest_distance_margin": round(float(nearest_margin), 4),
                "answer_label": str(answer_label),
                "answer_object_id": str(answer_spec["object_id"]),
                "unique_answer": True,
            },
        }
    raise ValueError("could not construct a visible street-intersection nearest-object scene")


def _camera_from_dataset(dataset: Mapping[str, Any]):
    camera = type("CameraTuple", (), {})()
    raw = dataset["camera"]
    camera.camera_position = tuple(float(value) for value in raw["camera_position"])
    camera.target = tuple(float(value) for value in raw["target"])
    camera.right = tuple(float(value) for value in raw["right"])
    camera.up = tuple(float(value) for value in raw["up"])
    camera.forward = tuple(float(value) for value in raw["forward"])
    camera.yaw_degrees = float(raw["yaw_degrees"])
    camera.pitch_degrees = float(raw["pitch_degrees"])
    camera.distance = float(raw["distance"])
    return camera


def _frame_from_dataset(dataset: Mapping[str, Any]):
    frame = type("FrameTuple", (), {})()
    raw = dataset["projection_frame"]
    frame.scale = float(raw["scale"])
    frame.center_x = float(raw["center_x"])
    frame.center_y = float(raw["center_y"])
    frame.normalized_center_u = float(raw["normalized_center_u"])
    frame.normalized_center_v = float(raw["normalized_center_v"])
    return frame


def _world_polygon(
    points: Sequence[Sequence[float]],
    *,
    camera,
    frame,
) -> List[Tuple[float, float]]:
    return [_project_xy(point, camera, frame) for point in points]


def _draw_world_rect(
    draw: ImageDraw.ImageDraw,
    *,
    camera,
    frame,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    z: float,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int] | None = None,
    width: int = 1,
) -> List[float]:
    points = _world_polygon(
        [
            (float(x0), float(y0), float(z)),
            (float(x1), float(y0), float(z)),
            (float(x1), float(y1), float(z)),
            (float(x0), float(y1), float(z)),
        ],
        camera=camera,
        frame=frame,
    )
    draw.polygon(points, fill=fill)
    if outline is not None:
        draw.line(points + [points[0]], fill=outline, width=max(1, int(width)))
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in points])


def _floor_polygon_area_xy(polygon_xy: Sequence[Tuple[float, float]]) -> float:
    area = 0.0
    if len(polygon_xy) < 3:
        return 0.0
    for index, point_a in enumerate(polygon_xy):
        point_b = polygon_xy[(index + 1) % len(polygon_xy)]
        area += float(point_a[0]) * float(point_b[1]) - float(point_b[0]) * float(point_a[1])
    return float(area * 0.5)


def _line_intersection_xy(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    q1: Tuple[float, float],
    q2: Tuple[float, float],
) -> Tuple[float, float]:
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    x3, y3 = float(q1[0]), float(q1[1])
    x4, y4 = float(q2[0]), float(q2[1])
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return (float(x2), float(y2))
    det_p = x1 * y2 - y1 * x2
    det_q = x3 * y4 - y3 * x4
    return (
        float((det_p * (x3 - x4) - (x1 - x2) * det_q) / denom),
        float((det_p * (y3 - y4) - (y1 - y2) * det_q) / denom),
    )


def _dedupe_polygon_points_xy(points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    deduped: List[Tuple[float, float]] = []
    for point in points:
        candidate = (float(point[0]), float(point[1]))
        if not deduped or math.hypot(candidate[0] - deduped[-1][0], candidate[1] - deduped[-1][1]) > 1e-7:
            deduped.append(candidate)
    if len(deduped) > 1 and math.hypot(deduped[0][0] - deduped[-1][0], deduped[0][1] - deduped[-1][1]) <= 1e-7:
        deduped.pop()
    return deduped


def _clip_polygon_to_convex_floor(
    subject_polygon_xy: Sequence[Tuple[float, float]],
    clip_polygon_xy: Sequence[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    if len(subject_polygon_xy) < 3 or len(clip_polygon_xy) < 3:
        return []
    orientation = 1.0 if _floor_polygon_area_xy(clip_polygon_xy) >= 0.0 else -1.0

    def inside(point: Tuple[float, float], edge_a: Tuple[float, float], edge_b: Tuple[float, float]) -> bool:
        cross = (
            (float(edge_b[0]) - float(edge_a[0])) * (float(point[1]) - float(edge_a[1]))
            - (float(edge_b[1]) - float(edge_a[1])) * (float(point[0]) - float(edge_a[0]))
        )
        return cross >= -1e-8 if orientation > 0.0 else cross <= 1e-8

    output = _dedupe_polygon_points_xy(subject_polygon_xy)
    for index, edge_start in enumerate(clip_polygon_xy):
        edge_end = clip_polygon_xy[(index + 1) % len(clip_polygon_xy)]
        if not output:
            break
        input_points = list(output)
        output = []
        previous = input_points[-1]
        previous_inside = inside(previous, edge_start, edge_end)
        for current in input_points:
            current_inside = inside(current, edge_start, edge_end)
            if current_inside:
                if not previous_inside:
                    output.append(_line_intersection_xy(previous, current, edge_start, edge_end))
                output.append((float(current[0]), float(current[1])))
            elif previous_inside:
                output.append(_line_intersection_xy(previous, current, edge_start, edge_end))
            previous = current
            previous_inside = current_inside
        output = _dedupe_polygon_points_xy(output)
    return _dedupe_polygon_points_xy(output)


def _fallback_floor_polygon_xy(render_params: _StreetRenderParams) -> List[Tuple[float, float]]:
    extent = float(render_params.street_extent) * float(STREET_FULL_BLEED_FALLBACK_EXTENT_MULTIPLIER)
    return [
        (-extent, -extent),
        (extent, -extent),
        (extent, extent),
        (-extent, extent),
    ]


def _visible_floor_polygon_xy(
    *,
    camera,
    frame,
    render_params: _StreetRenderParams,
) -> Tuple[List[Tuple[float, float]], str]:
    floor_polygon = _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params)
    if len(floor_polygon) >= 3:
        return ([(float(x), float(y)) for x, y in floor_polygon], "canvas_ray_polygon")

    width = float(render_params.canvas_width)
    height = float(render_params.canvas_height)
    sample_hits: List[Tuple[float, float]] = []
    for screen_x in (0.0, width * 0.5, width):
        for screen_y in (0.0, height * 0.5, height):
            floor_xy = _screen_to_floor_xy(screen_x, screen_y, camera=camera, frame=frame)
            if floor_xy is not None:
                sample_hits.append((float(floor_xy[0]), float(floor_xy[1])))
    if len(sample_hits) >= 3:
        return (_fallback_floor_polygon_xy(render_params), "expanded_fallback_square")
    return (_fallback_floor_polygon_xy(render_params), "expanded_fallback_square")


def _canvas_floor_polygon_available(
    *,
    camera,
    frame,
    render_params: _StreetRenderParams,
) -> bool:
    return len(_canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params)) >= 3


def _floor_bounds_xy(floor_polygon_xy: Sequence[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    return (
        min(float(point[0]) for point in floor_polygon_xy),
        max(float(point[0]) for point in floor_polygon_xy),
        min(float(point[1]) for point in floor_polygon_xy),
        max(float(point[1]) for point in floor_polygon_xy),
    )


def _draw_clipped_floor_rect(
    draw: ImageDraw.ImageDraw,
    *,
    camera,
    frame,
    floor_polygon_xy: Sequence[Tuple[float, float]],
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    z: float,
    fill: Tuple[int, int, int],
) -> List[float] | None:
    low_x, high_x = sorted((float(x0), float(x1)))
    low_y, high_y = sorted((float(y0), float(y1)))
    subject = [
        (low_x, low_y),
        (high_x, low_y),
        (high_x, high_y),
        (low_x, high_y),
    ]
    clipped = _clip_polygon_to_convex_floor(subject, floor_polygon_xy)
    if len(clipped) < 3:
        return None
    points = [_project_xy((float(x), float(y), float(z)), camera, frame) for x, y in clipped]
    draw.polygon(points, fill=fill)
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in points])


def _draw_crosswalks(
    draw: ImageDraw.ImageDraw,
    *,
    camera,
    frame,
    render_params: _StreetRenderParams,
    intersection_center_xy: Sequence[float],
    intersection_layout: str,
) -> None:
    road = float(render_params.road_half_width)
    cx, cy = float(intersection_center_xy[0]), float(intersection_center_xy[1])
    z = 0.018
    stripe = 0.075
    gap = 0.12
    span = road * 1.82
    crosswalk_offset = road + 0.34
    horizontal_crosswalks = []
    if _arm_is_present(str(intersection_layout), "west"):
        horizontal_crosswalks.append(cx - crosswalk_offset)
    if _arm_is_present(str(intersection_layout), "east"):
        horizontal_crosswalks.append(cx + crosswalk_offset)
    for center_x in horizontal_crosswalks:
        start_x = float(center_x - 0.33)
        for index in range(6):
            x0 = start_x + index * gap
            _draw_world_rect(
                draw,
                camera=camera,
                frame=frame,
                x0=x0,
                y0=cy - span * 0.5,
                x1=x0 + stripe,
                y1=cy + span * 0.5,
                z=z,
                fill=render_params.crosswalk_rgb,
            )
    vertical_crosswalks = []
    if _arm_is_present(str(intersection_layout), "south"):
        vertical_crosswalks.append(cy - crosswalk_offset)
    if _arm_is_present(str(intersection_layout), "north"):
        vertical_crosswalks.append(cy + crosswalk_offset)
    for center_y in vertical_crosswalks:
        start_y = float(center_y - 0.33)
        for index in range(6):
            y0 = start_y + index * gap
            _draw_world_rect(
                draw,
                camera=camera,
                frame=frame,
                x0=cx - span * 0.5,
                y0=y0,
                x1=cx + span * 0.5,
                y1=y0 + stripe,
                z=z,
                fill=render_params.crosswalk_rgb,
            )


def _draw_lane_markings(
    draw: ImageDraw.ImageDraw,
    *,
    camera,
    frame,
    render_params: _StreetRenderParams,
    floor_polygon_xy: Sequence[Tuple[float, float]],
    intersection_center_xy: Sequence[float],
    intersection_layout: str,
) -> None:
    road = float(render_params.road_half_width)
    cx, cy = float(intersection_center_xy[0]), float(intersection_center_xy[1])
    z = 0.022
    dash_len = 0.42
    gap = 0.28
    mark_w = 0.035
    intersection_gap = road * 1.32

    def draw_horizontal_segment(x0: float, x1: float) -> None:
        if float(x1) <= float(x0):
            return
        x = float(x0)
        while x < float(x1):
            dash_x1 = min(float(x1), x + dash_len)
            if dash_x1 - x > 0.08:
                _draw_clipped_floor_rect(
                    draw,
                    camera=camera,
                    frame=frame,
                    floor_polygon_xy=floor_polygon_xy,
                    x0=x,
                    y0=cy - mark_w,
                    x1=dash_x1,
                    y1=cy + mark_w,
                    z=z,
                    fill=render_params.road_mark_rgb,
                )
            x += dash_len + gap

    def draw_vertical_segment(y0: float, y1: float) -> None:
        if float(y1) <= float(y0):
            return
        y = float(y0)
        while y < float(y1):
            dash_y1 = min(float(y1), y + dash_len)
            if dash_y1 - y > 0.08:
                _draw_clipped_floor_rect(
                    draw,
                    camera=camera,
                    frame=frame,
                    floor_polygon_xy=floor_polygon_xy,
                    x0=cx - mark_w,
                    y0=y,
                    x1=cx + mark_w,
                    y1=dash_y1,
                    z=z,
                    fill=render_params.road_mark_rgb,
                )
            y += dash_len + gap

    horizontal_segment = _polygon_axis_line_segment(floor_polygon_xy, axis="y", value=cy)
    if horizontal_segment is None:
        x_min, x_max, _y_min, _y_max = _floor_bounds_xy(floor_polygon_xy)
    else:
        x_min = min(float(horizontal_segment[0][0]), float(horizontal_segment[1][0]))
        x_max = max(float(horizontal_segment[0][0]), float(horizontal_segment[1][0]))
    vertical_segment = _polygon_axis_line_segment(floor_polygon_xy, axis="x", value=cx)
    if vertical_segment is None:
        _x_min, _x_max, y_min, y_max = _floor_bounds_xy(floor_polygon_xy)
    else:
        y_min = min(float(vertical_segment[0][1]), float(vertical_segment[1][1]))
        y_max = max(float(vertical_segment[0][1]), float(vertical_segment[1][1]))

    if _arm_is_present(str(intersection_layout), "west"):
        draw_horizontal_segment(float(x_min), cx - intersection_gap)
    if _arm_is_present(str(intersection_layout), "east"):
        draw_horizontal_segment(cx + intersection_gap, float(x_max))
    if _arm_is_present(str(intersection_layout), "south"):
        draw_vertical_segment(float(y_min), cy - intersection_gap)
    if _arm_is_present(str(intersection_layout), "north"):
        draw_vertical_segment(cy + intersection_gap, float(y_max))


def _road_rects_for_layout(
    *,
    intersection_center_xy: Sequence[float],
    intersection_layout: str,
    floor_bounds_xy: Tuple[float, float, float, float],
    road_half_width: float,
) -> Dict[str, Tuple[float, float, float, float]]:
    cx, cy = float(intersection_center_xy[0]), float(intersection_center_xy[1])
    road = float(road_half_width)
    x_min, x_max, y_min, y_max = (float(value) for value in floor_bounds_xy)
    horizontal_x0 = x_min if _arm_is_present(str(intersection_layout), "west") else cx - road
    horizontal_x1 = x_max if _arm_is_present(str(intersection_layout), "east") else cx + road
    vertical_y0 = y_min if _arm_is_present(str(intersection_layout), "south") else cy - road
    vertical_y1 = y_max if _arm_is_present(str(intersection_layout), "north") else cy + road
    return {
        "horizontal": (horizontal_x0, cy - road, horizontal_x1, cy + road),
        "vertical": (cx - road, vertical_y0, cx + road, vertical_y1),
        "center": (cx - road, cy - road, cx + road, cy + road),
    }


def _draw_street_shell(
    draw: ImageDraw.ImageDraw,
    *,
    camera,
    frame,
    render_params: _StreetRenderParams,
    scene_variant: str,
    intersection_center_xy: Sequence[float],
    intersection_layout: str,
) -> Tuple[List[float], List[Dict[str, Any]]]:
    extent = float(render_params.street_extent)
    road = float(render_params.road_half_width)
    cx, cy = float(intersection_center_xy[0]), float(intersection_center_xy[1])
    sidewalk_fill = render_params.sidewalk_rgb
    if str(scene_variant) == "neighborhood_intersection":
        sidewalk_fill = (206, 224, 206)
    elif str(scene_variant) == "transit_intersection":
        sidewalk_fill = (218, 220, 224)
    floor_polygon_xy, floor_polygon_mode = _visible_floor_polygon_xy(
        camera=camera,
        frame=frame,
        render_params=render_params,
    )
    floor_bounds = _floor_bounds_xy(floor_polygon_xy)
    draw.rectangle(
        (0, 0, int(render_params.canvas_width), int(render_params.canvas_height)),
        fill=sidewalk_fill,
    )
    road_rects = _road_rects_for_layout(
        intersection_center_xy=intersection_center_xy,
        intersection_layout=str(intersection_layout),
        floor_bounds_xy=floor_bounds,
        road_half_width=float(road),
    )
    h_x0, h_y0, h_x1, h_y1 = road_rects["horizontal"]
    _draw_clipped_floor_rect(
        draw,
        camera=camera,
        frame=frame,
        floor_polygon_xy=floor_polygon_xy,
        x0=h_x0,
        y0=h_y0,
        x1=h_x1,
        y1=h_y1,
        z=0.006,
        fill=render_params.asphalt_rgb,
    )
    v_x0, v_y0, v_x1, v_y1 = road_rects["vertical"]
    _draw_clipped_floor_rect(
        draw,
        camera=camera,
        frame=frame,
        floor_polygon_xy=floor_polygon_xy,
        x0=v_x0,
        y0=v_y0,
        x1=v_x1,
        y1=v_y1,
        z=0.008,
        fill=_tint(render_params.asphalt_rgb, 0.03),
    )
    c_x0, c_y0, c_x1, c_y1 = road_rects["center"]
    _draw_clipped_floor_rect(
        draw,
        camera=camera,
        frame=frame,
        floor_polygon_xy=floor_polygon_xy,
        x0=c_x0,
        y0=c_y0,
        x1=c_x1,
        y1=c_y1,
        z=0.012,
        fill=_shade(render_params.asphalt_rgb, 0.92),
    )
    _draw_lane_markings(
        draw,
        camera=camera,
        frame=frame,
        render_params=render_params,
        floor_polygon_xy=floor_polygon_xy,
        intersection_center_xy=intersection_center_xy,
        intersection_layout=str(intersection_layout),
    )
    _draw_crosswalks(
        draw,
        camera=camera,
        frame=frame,
        render_params=render_params,
        intersection_center_xy=intersection_center_xy,
        intersection_layout=str(intersection_layout),
    )
    street_bbox = [
        0.0,
        0.0,
        float(render_params.canvas_width),
        float(render_params.canvas_height),
    ]
    return list(street_bbox), [
        {
            "entity_id": "street_intersection_surface",
            "entity_type": "three_d_street_intersection_surface",
            "bbox_px": list(street_bbox),
            "attrs": {
                "scene_variant": str(scene_variant),
                "street_extent": round(float(extent), 4),
                "semantic_street_extent": round(float(extent), 4),
                "render_full_bleed_surface": True,
                "floor_polygon_mode": str(floor_polygon_mode),
                "floor_bounds_xy": [round(float(value), 4) for value in floor_bounds],
                "road_half_width": round(float(road), 4),
                "intersection_center_xy": [round(float(cx), 4), round(float(cy), 4)],
                "intersection_layout": str(intersection_layout),
                "missing_road_arm": _missing_arm_for_layout(str(intersection_layout)),
            },
        }
    ]


def _draw_shadow(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> None:
    base = _project_screen(spec["base_xyz"], camera, frame)
    width, depth, _height = (float(value) for value in spec["dimensions_xyz"])
    radius = max(12.0, 18.0 * (7.0 / max(2.2, float(spec["camera_distance"]))) ** 0.35)
    radius *= max(0.72, min(2.2, float(width + depth) * 0.65))
    draw.ellipse(
        (
            base[0] - radius,
            base[1] - radius * 0.30,
            base[0] + radius,
            base[1] + radius * 0.30,
        ),
        fill=(136, 145, 148),
    )


def _draw_vehicle_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    axis = str(spec.get("orientation_axis", "x"))
    body_h = height * 0.58
    roof_h = height * 0.34
    wheel_h = max(0.055, height * 0.12)
    if axis == "x":
        roof_dims = (width * 0.44, depth * 0.74, roof_h)
        roof_offset = (width * 0.02, 0.0, wheel_h + body_h)
    else:
        roof_dims = (width * 0.74, depth * 0.44, roof_h)
        roof_offset = (0.0, depth * 0.02, wheel_h + body_h)
    parts = [
        _sub_box_spec(spec, offset_xyz=(0.0, 0.0, wheel_h), dimensions_xyz=(width, depth, body_h)),
        _sub_box_spec(spec, offset_xyz=roof_offset, dimensions_xyz=roof_dims),
    ]
    if str(spec.get("object_type")) in {"delivery_truck", "pickup_truck"}:
        if axis == "x":
            cab_offset = (-width * 0.28, 0.0, wheel_h + body_h * 0.06)
            cargo_offset = (width * 0.18, 0.0, wheel_h + body_h * 0.04)
            parts = [
                _sub_box_spec(spec, offset_xyz=cab_offset, dimensions_xyz=(width * 0.34, depth * 0.92, body_h * 1.12)),
                _sub_box_spec(spec, offset_xyz=cargo_offset, dimensions_xyz=(width * 0.58, depth, body_h * 1.20)),
            ]
        else:
            cab_offset = (0.0, -depth * 0.28, wheel_h + body_h * 0.06)
            cargo_offset = (0.0, depth * 0.18, wheel_h + body_h * 0.04)
            parts = [
                _sub_box_spec(spec, offset_xyz=cab_offset, dimensions_xyz=(width * 0.92, depth * 0.34, body_h * 1.12)),
                _sub_box_spec(spec, offset_xyz=cargo_offset, dimensions_xyz=(width, depth * 0.58, body_h * 1.20)),
            ]
    bbox = _draw_box_parts_object(draw, parts, camera=camera, frame=frame, fill=fill)
    x, y, _z = (float(value) for value in spec["base_xyz"])
    wheel_points = []
    if axis == "x":
        for dx in (-width * 0.34, width * 0.34):
            for dy in (-depth * 0.53, depth * 0.53):
                wheel_points.append((x + dx, y + dy, wheel_h * 0.62))
    else:
        for dx in (-width * 0.53, width * 0.53):
            for dy in (-depth * 0.34, depth * 0.34):
                wheel_points.append((x + dx, y + dy, wheel_h * 0.62))
    wheel_bboxes: List[List[float]] = []
    for point in wheel_points:
        px, py = _project_xy(point, camera, frame)
        radius = max(4.0, min(11.0, 6.0 * (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.4))
        wheel_bbox = [px - radius, py - radius * 0.66, px + radius, py + radius * 0.66]
        draw.ellipse(wheel_bbox, fill=(28, 31, 36), outline=(10, 12, 16), width=1)
        wheel_bboxes.append([round(float(value), 3) for value in wheel_bbox])
    if str(spec.get("object_type")) == "taxi":
        top = _project_xy((float(spec["base_xyz"][0]), float(spec["base_xyz"][1]), height + 0.07), camera, frame)
        draw.rectangle((top[0] - 9, top[1] - 5, top[0] + 9, top[1] + 5), fill=(248, 241, 153), outline=(34, 35, 38), width=1)
        wheel_bboxes.append([top[0] - 9, top[1] - 5, top[0] + 9, top[1] + 5])
    return _bbox_union(bbox, *wheel_bboxes) if wheel_bboxes else list(bbox)


def _draw_scooter_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    axis = str(spec.get("orientation_axis", "x"))
    deck_dims = (width, depth * 0.45, height * 0.22) if axis == "x" else (width * 0.45, depth, height * 0.22)
    deck = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.12), dimensions_xyz=deck_dims)
    bbox = _draw_box_object(draw, deck, camera=camera, frame=frame, fill=fill)
    x, y, _z = (float(value) for value in spec["base_xyz"])
    endpoints = (
        [(x - width * 0.42, y, height * 0.12), (x + width * 0.42, y, height * 0.12)]
        if axis == "x"
        else [(x, y - depth * 0.42, height * 0.12), (x, y + depth * 0.42, height * 0.12)]
    )
    wheel_bboxes = []
    for point in endpoints:
        px, py = _project_xy(point, camera, frame)
        radius = max(5.0, min(11.0, 7.0 * (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.45))
        wheel_bbox = [px - radius, py - radius, px + radius, py + radius]
        draw.ellipse(wheel_bbox, fill=(24, 27, 33), outline=(8, 9, 12), width=1)
        wheel_bboxes.append(wheel_bbox)
    handle_base = endpoints[-1]
    handle_top = (handle_base[0], handle_base[1], height)
    _draw_line(
        draw,
        _project_xy(handle_base, camera, frame),
        _project_xy(handle_top, camera, frame),
        fill=(30, 34, 42),
        width=2,
    )
    handle_bbox = _bbox_union(
        [_project_xy(handle_base, camera, frame)[0], _project_xy(handle_base, camera, frame)[1], _project_xy(handle_base, camera, frame)[0], _project_xy(handle_base, camera, frame)[1]],
        [_project_xy(handle_top, camera, frame)[0], _project_xy(handle_top, camera, frame)[1], _project_xy(handle_top, camera, frame)[0], _project_xy(handle_top, camera, frame)[1]],
    )
    return _bbox_union(bbox, handle_bbox, *wheel_bboxes)


def _draw_bicycle_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    axis = str(spec.get("orientation_axis", "x"))
    x, y, _z = (float(value) for value in spec["base_xyz"])
    if axis == "x":
        wheel_world = [(x - width * 0.40, y, height * 0.18), (x + width * 0.40, y, height * 0.18)]
        frame_world = [(x - width * 0.40, y, height * 0.18), (x, y, height * 0.50), (x + width * 0.40, y, height * 0.18), (x, y, height * 0.18)]
    else:
        wheel_world = [(x, y - depth * 0.40, height * 0.18), (x, y + depth * 0.40, height * 0.18)]
        frame_world = [(x, y - depth * 0.40, height * 0.18), (x, y, height * 0.50), (x, y + depth * 0.40, height * 0.18), (x, y, height * 0.18)]
    bboxes: List[List[float]] = []
    for point in wheel_world:
        px, py = _project_xy(point, camera, frame)
        radius = max(7.0, min(13.0, 8.5 * (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.45))
        bbox = [px - radius, py - radius, px + radius, py + radius]
        draw.ellipse(bbox, outline=(238, 238, 226), width=4)
        draw.ellipse(bbox, outline=(18, 22, 27), width=2)
        hub_r = max(2.0, radius * 0.14)
        draw.ellipse((px - hub_r, py - hub_r, px + hub_r, py + hub_r), fill=(238, 238, 226), outline=(18, 22, 27), width=1)
        bboxes.append(bbox)
    projected = [_project_xy(point, camera, frame) for point in frame_world]
    for wheel_center in [_project_xy(point, camera, frame) for point in wheel_world]:
        for frame_point in projected:
            if math.hypot(frame_point[0] - wheel_center[0], frame_point[1] - wheel_center[1]) < 32.0:
                _draw_line(draw, wheel_center, frame_point, fill=(238, 238, 226), width=1)
    frame_path = [projected[0], projected[1], projected[2], projected[3], projected[0]]
    draw.line(frame_path, fill=(238, 238, 226), width=5, joint="curve")
    draw.line(frame_path, fill=(36, 112, 190), width=3, joint="curve")
    seat = _project_xy((x, y, height * 0.60), camera, frame)
    handle = _project_xy((x + width * 0.48, y, height * 0.52) if axis == "x" else (x, y + depth * 0.48, height * 0.52), camera, frame)
    _draw_line(draw, (seat[0] - 5.0, seat[1]), (seat[0] + 6.0, seat[1]), fill=(18, 22, 27), width=3)
    _draw_line(draw, handle, (handle[0] + 7.0, handle[1] - 2.0), fill=(18, 22, 27), width=3)
    frame_bbox = _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected])
    return _bbox_union(frame_bbox, *bboxes)


def _draw_motorcycle_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    axis = str(spec.get("orientation_axis", "x"))
    x, y, _z = (float(value) for value in spec["base_xyz"])
    if axis == "x":
        wheel_world = [(x - width * 0.38, y, height * 0.20), (x + width * 0.38, y, height * 0.20)]
        body_dims = (width * 0.50, depth * 0.72, height * 0.24)
        seat_dims = (width * 0.34, depth * 0.50, height * 0.12)
        handle_base = (x + width * 0.34, y, height * 0.42)
        handle_top = (x + width * 0.47, y, height * 0.66)
        fork_base = (x + width * 0.38, y, height * 0.20)
    else:
        wheel_world = [(x, y - depth * 0.38, height * 0.20), (x, y + depth * 0.38, height * 0.20)]
        body_dims = (width * 0.72, depth * 0.50, height * 0.24)
        seat_dims = (width * 0.50, depth * 0.34, height * 0.12)
        handle_base = (x, y + depth * 0.34, height * 0.42)
        handle_top = (x, y + depth * 0.47, height * 0.66)
        fork_base = (x, y + depth * 0.38, height * 0.20)
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.28), dimensions_xyz=body_dims)
    seat = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.53), dimensions_xyz=seat_dims)
    bboxes: List[List[float]] = [
        _draw_box_object(draw, body, camera=camera, frame=frame, fill=fill),
        _draw_box_object(draw, seat, camera=camera, frame=frame, fill=(34, 38, 43)),
    ]
    for point in wheel_world:
        px, py = _project_xy(point, camera, frame)
        radius = max(8.0, min(16.0, 10.5 * (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.45))
        wheel_bbox = [px - radius, py - radius, px + radius, py + radius]
        draw.ellipse(wheel_bbox, fill=(25, 28, 32), outline=(8, 9, 12), width=2)
        inner = [px - radius * 0.42, py - radius * 0.42, px + radius * 0.42, py + radius * 0.42]
        draw.ellipse(inner, fill=(101, 111, 120), outline=(35, 39, 44), width=1)
        bboxes.append(wheel_bbox)
    handle_base_px = _project_xy(handle_base, camera, frame)
    handle_top_px = _project_xy(handle_top, camera, frame)
    fork_base_px = _project_xy(fork_base, camera, frame)
    _draw_line(draw, fork_base_px, handle_base_px, fill=(31, 35, 40), width=3)
    _draw_line(draw, handle_base_px, handle_top_px, fill=(31, 35, 40), width=3)
    handle_w = max(12.0, min(22.0, 15.0 * (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.35))
    draw.line(
        (handle_top_px[0] - handle_w * 0.5, handle_top_px[1], handle_top_px[0] + handle_w * 0.5, handle_top_px[1]),
        fill=(31, 35, 40),
        width=3,
    )
    bboxes.extend(
        [
            _screen_line_bbox(fork_base_px, handle_base_px, pad_px=4.0),
            _screen_line_bbox(handle_base_px, handle_top_px, pad_px=4.0),
            [handle_top_px[0] - handle_w * 0.5, handle_top_px[1] - 3.0, handle_top_px[0] + handle_w * 0.5, handle_top_px[1] + 3.0],
        ]
    )
    return _bbox_union(*bboxes)


def _draw_fire_hydrant_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    x, y, _z = (float(value) for value in spec["base_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.06), dimensions_xyz=(width * 0.56, depth * 0.56, height * 0.72))
    cap = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.68), dimensions_xyz=(width * 0.46, depth * 0.46, height * 0.20))
    base = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.78, depth * 0.78, height * 0.14))
    bboxes: List[List[float]] = [
        _draw_cylinder_object(draw, base, camera=camera, frame=frame, fill=_shade(fill, 0.74)),
        _draw_cylinder_object(draw, body, camera=camera, frame=frame, fill=fill),
        _draw_cylinder_object(draw, cap, camera=camera, frame=frame, fill=_tint(fill, 0.12)),
    ]
    side_points = [
        (x - width * 0.46, y, height * 0.43),
        (x + width * 0.46, y, height * 0.43),
    ]
    center = _project_xy((x, y, height * 0.43), camera, frame)
    for point in side_points:
        projected = _project_xy(point, camera, frame)
        _draw_line(draw, center, projected, fill=_shade(fill, 0.82), width=4)
        radius = max(3.0, min(7.0, 4.5 * (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.40))
        nozzle_bbox = [projected[0] - radius, projected[1] - radius, projected[0] + radius, projected[1] + radius]
        draw.ellipse(nozzle_bbox, fill=_tint(fill, 0.18), outline=(72, 38, 34), width=1)
        bboxes.append(nozzle_bbox)
    return _bbox_union(*bboxes)


def _draw_trash_bin_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.05), dimensions_xyz=(width * 0.88, depth * 0.88, height * 0.76))
    lid = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.80), dimensions_xyz=(width, depth, height * 0.12))
    bbox = _bbox_union(
        _draw_cylinder_object(draw, body, camera=camera, frame=frame, fill=fill),
        _draw_cylinder_object(draw, lid, camera=camera, frame=frame, fill=_shade(fill, 0.70)),
    )
    center = _project_xy(spec["world_xyz"], camera, frame)
    handle_w = max(14.0, min(24.0, 17.0 * (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.35))
    handle_bbox = [center[0] - handle_w * 0.5, center[1] - handle_w * 0.18, center[0] + handle_w * 0.5, center[1] + handle_w * 0.18]
    draw.rectangle(handle_bbox, fill=_shade(fill, 0.48), outline=(31, 39, 35), width=1)
    return _bbox_union(bbox, handle_bbox)


def _draw_mailbox_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    axis = str(spec.get("orientation_axis", "x"))
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.18), dimensions_xyz=(width, depth, height * 0.50))
    roof_dims = (width, depth * 0.90, height * 0.22) if axis == "x" else (width * 0.90, depth, height * 0.22)
    roof = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.62), dimensions_xyz=roof_dims)
    post = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.16, depth * 0.16, height * 0.38))
    bbox = _bbox_union(
        _draw_box_object(draw, post, camera=camera, frame=frame, fill=(76, 70, 62)),
        _draw_box_object(draw, body, camera=camera, frame=frame, fill=fill),
        _draw_box_object(draw, roof, camera=camera, frame=frame, fill=_tint(fill, 0.08)),
    )
    x, y, _z = (float(value) for value in spec["base_xyz"])
    flag_world = (x + width * 0.56, y, height * 0.62) if axis == "x" else (x, y + depth * 0.56, height * 0.62)
    flag_center = _project_xy(flag_world, camera, frame)
    scale = max(0.75, min(1.25, (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.35))
    flag_bbox = _screen_rect_bbox(flag_center, width_px=18.0 * scale, height_px=11.0 * scale)
    draw.rectangle(flag_bbox, fill=(202, 55, 55), outline=(80, 29, 29), width=1)
    return _bbox_union(bbox, flag_bbox)


def _draw_construction_barrier_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    axis = str(spec.get("orientation_axis", "x"))
    if axis == "x":
        rail_dims = (width, depth * 0.34, height * 0.14)
        leg_dims = (width * 0.10, depth * 0.44, height * 0.58)
        leg_offsets = [(-width * 0.36, 0.0, height * 0.08), (width * 0.36, 0.0, height * 0.08)]
    else:
        rail_dims = (width * 0.34, depth, height * 0.14)
        leg_dims = (width * 0.44, depth * 0.10, height * 0.58)
        leg_offsets = [(0.0, -depth * 0.36, height * 0.08), (0.0, depth * 0.36, height * 0.08)]
    rail_parts = [
        _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.28), dimensions_xyz=rail_dims),
        _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.56), dimensions_xyz=rail_dims),
    ]
    leg_parts = [_sub_box_spec(spec, offset_xyz=offset, dimensions_xyz=leg_dims) for offset in leg_offsets]
    bboxes: List[List[float]] = []
    for part in leg_parts:
        leg_bbox = _draw_box_object(draw, part, camera=camera, frame=frame, fill=_shade(fill, 0.60))
        draw.rectangle(tuple(leg_bbox), outline=(88, 44, 24), width=1)
        bboxes.append(leg_bbox)
    rail_bboxes: List[List[float]] = []
    for part in rail_parts:
        rail_bbox = _draw_box_object(draw, part, camera=camera, frame=frame, fill=(226, 105, 42))
        draw.rectangle(tuple(rail_bbox), outline=(94, 47, 25), width=2)
        rail_bboxes.append(rail_bbox)
        bboxes.append(rail_bbox)
    stripe_color = (246, 242, 216)
    stripe_outline = (156, 84, 42)
    for rail_bbox in rail_bboxes:
        x0, y0, x1, y1 = (float(value) for value in rail_bbox)
        rail_w = max(1.0, x1 - x0)
        rail_h = max(1.0, y1 - y0)
        if rail_w >= rail_h:
            for start_frac in (0.10, 0.36, 0.62):
                rect = [
                    x0 + rail_w * start_frac,
                    y0 + rail_h * 0.20,
                    x0 + rail_w * (start_frac + 0.16),
                    y1 - rail_h * 0.20,
                ]
                draw.rectangle(rect, fill=stripe_color, outline=stripe_outline, width=1)
                _draw_line(draw, (rect[0], rect[3]), (rect[2], rect[1]), fill=(156, 84, 42), width=1)
                bboxes.append(rect)
        else:
            for start_frac in (0.10, 0.36, 0.62):
                rect = [
                    x0 + rail_w * 0.20,
                    y0 + rail_h * start_frac,
                    x1 - rail_w * 0.20,
                    y0 + rail_h * (start_frac + 0.16),
                ]
                draw.rectangle(rect, fill=stripe_color, outline=stripe_outline, width=1)
                _draw_line(draw, (rect[0], rect[3]), (rect[2], rect[1]), fill=(156, 84, 42), width=1)
                bboxes.append(rect)
    return _bbox_union(*bboxes)


def _draw_road_barrel_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    body = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width, depth, height))
    bbox = _draw_cylinder_object(draw, body, camera=camera, frame=frame, fill=fill)
    center = _project_xy(spec["world_xyz"], camera, frame)
    scale = max(0.72, min(1.22, (8.0 / max(2.2, float(spec["camera_distance"]))) ** 0.38))
    band_w = max(18.0, min(34.0, 24.0 * scale))
    band_h = max(5.0, min(9.0, 6.5 * scale))
    bands: List[List[float]] = []
    for offset in (-0.22, 0.18):
        band_center = (float(center[0]), float(center[1]) + offset * 42.0 * scale)
        band_bbox = _screen_rect_bbox(band_center, width_px=band_w, height_px=band_h)
        draw.rectangle(band_bbox, fill=(246, 238, 211), outline=(145, 83, 45), width=1)
        bands.append(band_bbox)
    return _bbox_union(bbox, *bands)


def _draw_projected_limb(
    draw: ImageDraw.ImageDraw,
    start_world: Sequence[float],
    end_world: Sequence[float],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
    width_px: int,
) -> List[float]:
    start = _project_xy(start_world, camera, frame)
    end = _project_xy(end_world, camera, frame)
    width = max(2, int(width_px))
    radius = float(width) * 0.55
    draw.line([start, end], fill=fill, width=width)
    draw.ellipse(
        (start[0] - radius, start[1] - radius, start[0] + radius, start[1] + radius),
        fill=fill,
    )
    draw.ellipse(
        (end[0] - radius, end[1] - radius, end[0] + radius, end[1] + radius),
        fill=fill,
    )
    return [
        round(float(min(start[0], end[0]) - radius), 3),
        round(float(min(start[1], end[1]) - radius), 3),
        round(float(max(start[0], end[0]) + radius), 3),
        round(float(max(start[1], end[1]) + radius), 3),
    ]


def _screen_line_bbox(p1: Sequence[float], p2: Sequence[float], *, pad_px: float) -> List[float]:
    return [
        round(float(min(float(p1[0]), float(p2[0])) - pad_px), 3),
        round(float(min(float(p1[1]), float(p2[1])) - pad_px), 3),
        round(float(max(float(p1[0]), float(p2[0])) + pad_px), 3),
        round(float(max(float(p1[1]), float(p2[1])) + pad_px), 3),
    ]


def _screen_rect_bbox(center: Sequence[float], *, width_px: float, height_px: float) -> List[float]:
    half_w = float(width_px) * 0.5
    half_h = float(height_px) * 0.5
    return [
        round(float(center[0]) - half_w, 3),
        round(float(center[1]) - half_h, 3),
        round(float(center[0]) + half_w, 3),
        round(float(center[1]) + half_h, 3),
    ]


def _draw_screen_pole(
    draw: ImageDraw.ImageDraw,
    base: Sequence[float],
    top: Sequence[float],
    *,
    fill: Tuple[int, int, int],
    width_px: int,
) -> List[float]:
    _draw_line(draw, base, top, fill=(23, 27, 31), width=max(1, int(width_px) + 2))
    _draw_line(draw, base, top, fill=fill, width=max(1, int(width_px)))
    radius = max(2.0, float(width_px) * 0.78)
    foot_bbox = [
        float(base[0]) - radius * 1.55,
        float(base[1]) - radius * 0.45,
        float(base[0]) + radius * 1.55,
        float(base[1]) + radius * 0.45,
    ]
    draw.ellipse(foot_bbox, fill=(52, 56, 60), outline=(23, 27, 31), width=1)
    return _bbox_union(_screen_line_bbox(base, top, pad_px=float(width_px) + 1.0), foot_bbox)


def _draw_traffic_light_context_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _base_z = (float(value) for value in spec["base_xyz"])
    _width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
    distance = max(2.2, float(spec["camera_distance"]))
    scale = max(0.78, min(1.22, (8.0 / distance) ** 0.36))
    base = _project_xy((x, y, 0.0), camera, frame)
    top = _project_xy((x, y, height * 0.94), camera, frame)
    head_center = _project_xy((x, y, height * 0.69), camera, frame)
    pole_bbox = _draw_screen_pole(
        draw,
        base,
        top,
        fill=(78, 82, 86),
        width_px=max(3, int(round(4.5 * scale))),
    )
    box_w = max(15.0, min(24.0, 18.5 * scale))
    box_h = max(34.0, min(48.0, 39.0 * scale))
    signal_bbox = _screen_rect_bbox(head_center, width_px=box_w, height_px=box_h)
    draw.rectangle(signal_bbox, fill=_shade(fill, 0.72), outline=(18, 21, 25), width=2)
    lens_radius = max(3.3, min(5.8, box_w * 0.26))
    lens_x = float(head_center[0])
    lens_gap = box_h * 0.25
    for offset, color in ((-lens_gap, (199, 45, 42)), (0.0, (235, 185, 48)), (lens_gap, (62, 159, 87))):
        cy = float(head_center[1]) + float(offset)
        draw.ellipse(
            (
                lens_x - lens_radius,
                cy - lens_radius,
                lens_x + lens_radius,
                cy + lens_radius,
            ),
            fill=color,
            outline=(18, 21, 25),
            width=1,
        )
    cap_y = float(signal_bbox[1]) - max(1.5, 2.0 * scale)
    cap_bbox = [
        float(signal_bbox[0]) - 1.0,
        cap_y,
        float(signal_bbox[2]) + 1.0,
        cap_y + max(3.0, 4.0 * scale),
    ]
    draw.rectangle(cap_bbox, fill=_shade(fill, 0.54), outline=(18, 21, 25), width=1)
    return _bbox_union(pole_bbox, signal_bbox, cap_bbox)


def _draw_street_sign_context_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    x, y, _base_z = (float(value) for value in spec["base_xyz"])
    _width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
    distance = max(2.2, float(spec["camera_distance"]))
    scale = max(0.78, min(1.20, (8.0 / distance) ** 0.36))
    base = _project_xy((x, y, 0.0), camera, frame)
    top = _project_xy((x, y, height * 0.96), camera, frame)
    sign_center = _project_xy((x, y, height * 0.79), camera, frame)
    pole_bbox = _draw_screen_pole(
        draw,
        base,
        top,
        fill=(79, 83, 87),
        width_px=max(3, int(round(4.0 * scale))),
    )
    panel_w = max(34.0, min(54.0, 43.0 * scale))
    panel_h = max(16.0, min(23.0, 18.5 * scale))
    panel_bbox = _screen_rect_bbox(sign_center, width_px=panel_w, height_px=panel_h)
    draw.rectangle(panel_bbox, fill=fill, outline=(241, 246, 241), width=2)
    line_y = float(sign_center[1])
    draw.line(
        (
            float(panel_bbox[0]) + panel_w * 0.20,
            line_y,
            float(panel_bbox[2]) - panel_w * 0.20,
            line_y,
        ),
        fill=(237, 244, 237),
        width=max(1, int(round(1.6 * scale))),
    )
    return _bbox_union(pole_bbox, panel_bbox)


def _draw_pedestrian_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    _width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
    x, y, _base_z = (float(value) for value in spec["base_xyz"])
    base = _project_xy((x, y, 0.0), camera, frame)
    top = _project_xy((x, y, height), camera, frame)
    up = (float(top[0]) - float(base[0]), float(top[1]) - float(base[1]))
    height_px = math.hypot(up[0], up[1])
    if height_px < 1.0:
        up_unit = (0.0, -1.0)
    else:
        up_unit = (up[0] / height_px, up[1] / height_px)
    side_unit = (-up_unit[1], up_unit[0])
    person_h = max(52.0, min(92.0, float(height_px) * 1.08))
    base_center = (float(base[0]), float(base[1]))

    def p(lateral: float, upward: float) -> Tuple[float, float]:
        return (
            base_center[0] + side_unit[0] * float(lateral) + up_unit[0] * float(upward),
            base_center[1] + side_unit[1] * float(lateral) + up_unit[1] * float(upward),
        )

    def line_bbox(points: Sequence[Sequence[float]], *, fill_rgb: Tuple[int, int, int], width_px: int, outline_rgb: Tuple[int, int, int] = (28, 35, 45)) -> List[float]:
        screen_points = [(float(px), float(py)) for px, py in points]
        draw.line(screen_points, fill=outline_rgb, width=max(3, int(width_px) + 3), joint="curve")
        draw.line(screen_points, fill=fill_rgb, width=max(2, int(width_px)), joint="curve")
        radius = max(2.0, float(width_px) * 0.52)
        for px, py in points:
            draw.ellipse(
                (float(px) - radius - 1.0, float(py) - radius - 1.0, float(px) + radius + 1.0, float(py) + radius + 1.0),
                fill=outline_rgb,
            )
            draw.ellipse((float(px) - radius, float(py) - radius, float(px) + radius, float(py) + radius), fill=fill_rgb)
        return [
            round(float(min(px for px, _py in points) - radius), 3),
            round(float(min(py for _px, py in points) - radius), 3),
            round(float(max(px for px, _py in points) + radius), 3),
            round(float(max(py for _px, py in points) + radius), 3),
        ]

    def poly_bbox(points: Sequence[Sequence[float]], *, fill_rgb: Tuple[int, int, int], outline_rgb: Tuple[int, int, int], width_px: int = 2) -> List[float]:
        screen_points = [(float(px), float(py)) for px, py in points]
        draw.polygon(screen_points, fill=fill_rgb)
        for index in range(len(screen_points)):
            _draw_line(draw, screen_points[index], screen_points[(index + 1) % len(screen_points)], fill=outline_rgb, width=max(1, int(width_px)))
        return [
            round(float(min(px for px, _py in screen_points)), 3),
            round(float(min(py for _px, py in screen_points)), 3),
            round(float(max(px for px, _py in screen_points)), 3),
            round(float(max(py for _px, py in screen_points)), 3),
        ]

    def ellipse_bbox(center: Sequence[float], radius_x: float, radius_y: float, *, fill_rgb: Tuple[int, int, int], outline_rgb: Tuple[int, int, int], width_px: int = 2) -> List[float]:
        bbox = [
            float(center[0]) - float(radius_x),
            float(center[1]) - float(radius_y),
            float(center[0]) + float(radius_x),
            float(center[1]) + float(radius_y),
        ]
        draw.ellipse(tuple(bbox), fill=fill_rgb, outline=outline_rgb, width=max(1, int(width_px)))
        return [round(float(value), 3) for value in bbox]

    limb_width = max(4, min(9, int(round(person_h * 0.085))))
    arm_width = max(3, int(round(limb_width * 0.82)))
    shoe_width = max(4, int(round(limb_width * 1.10)))
    skin = (224, 178, 137)
    pants = (47, 62, 96)
    hair = (55, 45, 37)
    outline = (28, 35, 45)
    gender_id = str(spec.get("pedestrian_gender_id", "male")).lower()
    if gender_id not in {"male", "female"}:
        gender_id = "male"
    shirt = _tint(fill, 0.08)
    skirt_rgb = (145, 82, 138)
    if gender_id == "female":
        shirt = (91, 141, 166)
    bboxes: List[List[float]] = []

    left_foot = p(-person_h * 0.15, person_h * 0.02)
    right_foot = p(person_h * 0.15, person_h * 0.02)
    left_knee = p(-person_h * 0.08, person_h * 0.18)
    right_knee = p(person_h * 0.08, person_h * 0.18)
    if gender_id == "female":
        left_leg_top = p(-person_h * 0.08, person_h * 0.30)
        right_leg_top = p(person_h * 0.08, person_h * 0.30)
    else:
        left_leg_top = p(-person_h * 0.07, person_h * 0.38)
        right_leg_top = p(person_h * 0.07, person_h * 0.38)
    bboxes.append(line_bbox([left_leg_top, left_knee, left_foot], fill_rgb=pants, width_px=limb_width, outline_rgb=outline))
    bboxes.append(line_bbox([right_leg_top, right_knee, right_foot], fill_rgb=pants, width_px=limb_width, outline_rgb=outline))
    bboxes.append(line_bbox([left_foot, p(-person_h * 0.24, person_h * 0.02)], fill_rgb=(31, 35, 40), width_px=shoe_width, outline_rgb=outline))
    bboxes.append(line_bbox([right_foot, p(person_h * 0.24, person_h * 0.02)], fill_rgb=(31, 35, 40), width_px=shoe_width, outline_rgb=outline))

    left_shoulder = p(-person_h * 0.17, person_h * 0.62)
    right_shoulder = p(person_h * 0.17, person_h * 0.62)
    left_hand = p(-person_h * 0.33, person_h * 0.42)
    right_hand = p(person_h * 0.33, person_h * 0.42)
    bboxes.append(line_bbox([left_shoulder, p(-person_h * 0.26, person_h * 0.50), left_hand], fill_rgb=_shade(shirt, 0.88), width_px=arm_width, outline_rgb=outline))
    bboxes.append(line_bbox([right_shoulder, p(person_h * 0.26, person_h * 0.50), right_hand], fill_rgb=_shade(shirt, 0.88), width_px=arm_width, outline_rgb=outline))
    hand_radius = max(2.2, float(arm_width) * 0.72)
    for hand in (left_hand, right_hand):
        bboxes.append(ellipse_bbox(hand, hand_radius, hand_radius, fill_rgb=skin, outline_rgb=outline, width_px=1))

    if gender_id == "female":
        torso_points = [
            left_shoulder,
            right_shoulder,
            p(person_h * 0.12, person_h * 0.46),
            p(-person_h * 0.12, person_h * 0.46),
        ]
        bboxes.append(poly_bbox(torso_points, fill_rgb=shirt, outline_rgb=outline, width_px=2))
        skirt_points = [
            p(-person_h * 0.12, person_h * 0.46),
            p(person_h * 0.12, person_h * 0.46),
            p(person_h * 0.23, person_h * 0.30),
            p(-person_h * 0.23, person_h * 0.30),
        ]
        bboxes.append(poly_bbox(skirt_points, fill_rgb=skirt_rgb, outline_rgb=outline, width_px=2))
    else:
        torso_points = [
            left_shoulder,
            right_shoulder,
            p(person_h * 0.14, person_h * 0.38),
            p(-person_h * 0.14, person_h * 0.38),
        ]
        bboxes.append(poly_bbox(torso_points, fill_rgb=shirt, outline_rgb=outline, width_px=2))
        belt = [p(-person_h * 0.12, person_h * 0.39), p(person_h * 0.12, person_h * 0.39)]
        bboxes.append(line_bbox(belt, fill_rgb=(39, 43, 51), width_px=max(2, arm_width - 1), outline_rgb=outline))

    neck_bottom = p(0.0, person_h * 0.62)
    neck_top = p(0.0, person_h * 0.68)
    bboxes.append(line_bbox([neck_bottom, neck_top], fill_rgb=skin, width_px=max(3, arm_width), outline_rgb=outline))

    head_center = p(0.0, person_h * 0.80)
    head_radius = max(8.0, min(14.0, person_h * 0.13))
    head_bbox = [
        head_center[0] - head_radius,
        head_center[1] - head_radius,
        head_center[0] + head_radius,
        head_center[1] + head_radius,
    ]
    hx0, hy0, hx1, hy1 = (float(value) for value in head_bbox)
    head_w = hx1 - hx0
    head_h = hy1 - hy0
    if gender_id == "female":
        hair_back = [
            hx0 - head_w * 0.18,
            hy0 - head_h * 0.20,
            hx1 + head_w * 0.18,
            hy1 + head_h * 0.56,
        ]
        draw.ellipse(tuple(hair_back), fill=hair, outline=outline, width=2)
        bboxes.append([round(float(value), 3) for value in hair_back])
        left_lock = [
            (hx0 + head_w * 0.10, hy0 + head_h * 0.18),
            (hx0 - head_w * 0.26, hy0 + head_h * 0.38),
            (hx0 - head_w * 0.10, hy1 + head_h * 0.70),
            (hx0 + head_w * 0.24, hy1 + head_h * 0.28),
        ]
        right_lock = [
            (hx1 - head_w * 0.10, hy0 + head_h * 0.18),
            (hx1 + head_w * 0.26, hy0 + head_h * 0.38),
            (hx1 + head_w * 0.10, hy1 + head_h * 0.70),
            (hx1 - head_w * 0.24, hy1 + head_h * 0.28),
        ]
        bboxes.append(poly_bbox(left_lock, fill_rgb=hair, outline_rgb=outline, width_px=1))
        bboxes.append(poly_bbox(right_lock, fill_rgb=hair, outline_rgb=outline, width_px=1))
    bboxes.append(ellipse_bbox(head_center, head_radius, head_radius, fill_rgb=skin, outline_rgb=outline, width_px=2))
    if gender_id == "female":
        cap = [
            hx0 - head_w * 0.10,
            hy0 - head_h * 0.24,
            hx1 + head_w * 0.10,
            hy0 + head_h * 0.44,
        ]
        draw.ellipse(tuple(cap), fill=hair, outline=outline, width=1)
        fringe = [
            (hx0 + head_w * 0.05, hy0 + head_h * 0.20),
            (hx0 + head_w * 0.42, hy0 - head_h * 0.08),
            (hx1 - head_w * 0.08, hy0 + head_h * 0.22),
            (hx0 + head_w * 0.36, hy0 + head_h * 0.42),
        ]
        bboxes.append(poly_bbox(fringe, fill_rgb=hair, outline_rgb=outline, width_px=1))
    else:
        cap = [
            hx0 + head_w * 0.04,
            hy0 - head_h * 0.10,
            hx1 - head_w * 0.04,
            hy0 + head_h * 0.30,
        ]
        draw.rounded_rectangle(tuple(cap), radius=max(2, int(round(head_radius * 0.20))), fill=hair, outline=outline, width=1)
        bboxes.append([round(float(value), 3) for value in cap])
        for sideburn in (
            (hx0 + head_w * 0.02, hy0 + head_h * 0.20, hx0 + head_w * 0.18, hy0 + head_h * 0.50),
            (hx1 - head_w * 0.18, hy0 + head_h * 0.20, hx1 - head_w * 0.02, hy0 + head_h * 0.50),
        ):
            draw.rounded_rectangle(tuple(sideburn), radius=2, fill=hair)
            bboxes.append([round(float(value), 3) for value in sideburn])
    eye_r = max(1.2, head_radius * 0.09)
    for eye in (p(-head_radius * 0.36, person_h * 0.805), p(head_radius * 0.36, person_h * 0.805)):
        bboxes.append(ellipse_bbox(eye, eye_r, eye_r, fill_rgb=(35, 40, 44), outline_rgb=(35, 40, 44), width_px=1))
    mouth = [p(-head_radius * 0.20, person_h * 0.772), p(head_radius * 0.22, person_h * 0.772)]
    bboxes.append(line_bbox(mouth, fill_rgb=(125, 67, 63), width_px=1, outline_rgb=(125, 67, 63)))
    return _bbox_union(*bboxes)


def _stable_palette_index(value: str, modulo: int) -> int:
    if int(modulo) <= 0:
        return 0
    return sum(ord(char) for char in str(value)) % int(modulo)


def _draw_building_face_rect(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    face_axis: str,
    face_side: int,
    span0: float,
    span1: float,
    z0: float,
    z1: float,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int] | None = None,
    width: int = 1,
) -> List[float]:
    x, y, base_z = (float(value) for value in spec["base_xyz"])
    building_w, building_d, building_h = (float(value) for value in spec["dimensions_xyz"])
    span0 = max(0.0, min(1.0, float(span0)))
    span1 = max(0.0, min(1.0, float(span1)))
    if span1 <= span0:
        span1 = min(1.0, span0 + 0.02)
    z0 = max(0.0, min(1.04, float(z0)))
    z1 = max(0.0, min(1.04, float(z1)))
    if z1 <= z0:
        z1 = min(1.04, z0 + 0.02)
    if str(face_axis) == "x":
        fixed_x = x + int(face_side) * building_w * 0.501
        y0 = y - building_d * 0.5 + building_d * span0
        y1 = y - building_d * 0.5 + building_d * span1
        points = [
            (fixed_x, y0, base_z + building_h * z0),
            (fixed_x, y1, base_z + building_h * z0),
            (fixed_x, y1, base_z + building_h * z1),
            (fixed_x, y0, base_z + building_h * z1),
        ]
    else:
        fixed_y = y + int(face_side) * building_d * 0.501
        x0 = x - building_w * 0.5 + building_w * span0
        x1 = x - building_w * 0.5 + building_w * span1
        points = [
            (x0, fixed_y, base_z + building_h * z0),
            (x1, fixed_y, base_z + building_h * z0),
            (x1, fixed_y, base_z + building_h * z1),
            (x0, fixed_y, base_z + building_h * z1),
        ]
    projected = [_project_xy(point, camera, frame) for point in points]
    draw.polygon(projected, fill=fill)
    if outline is not None:
        draw.line(projected + [projected[0]], fill=outline, width=max(1, int(width)))
    return _bbox_union(*[[point[0], point[1], point[0], point[1]] for point in projected])


def _draw_building_window_grid(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    face_axis: str,
    face_side: int,
    cols: int,
    rows: int,
    z_min: float,
    z_max: float,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    span_margin: float = 0.12,
) -> List[List[float]]:
    cols = max(1, int(cols))
    rows = max(1, int(rows))
    span_width = max(0.12, 1.0 - 2.0 * float(span_margin))
    cell_w = span_width / float(cols)
    cell_h = max(0.05, (float(z_max) - float(z_min)) / float(rows))
    bboxes: List[List[float]] = []
    for col in range(cols):
        span0 = float(span_margin) + col * cell_w + cell_w * 0.17
        span1 = float(span_margin) + (col + 1) * cell_w - cell_w * 0.17
        for row in range(rows):
            row_z0 = float(z_min) + row * cell_h + cell_h * 0.20
            row_z1 = float(z_min) + (row + 1) * cell_h - cell_h * 0.18
            if span1 - span0 < 0.025 or row_z1 - row_z0 < 0.022:
                continue
            bboxes.append(
                _draw_building_face_rect(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=str(face_axis),
                    face_side=int(face_side),
                    span0=span0,
                    span1=span1,
                    z0=row_z0,
                    z1=row_z1,
                    fill=fill,
                    outline=outline,
                    width=1,
                )
            )
    return list(bboxes)


def _draw_building_vertical_glass(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    face_axis: str,
    face_side: int,
    cols: int,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
) -> List[List[float]]:
    bboxes: List[List[float]] = []
    cols = max(2, int(cols))
    for col in range(cols):
        cell_w = 0.80 / float(cols)
        span0 = 0.10 + col * cell_w + cell_w * 0.08
        span1 = 0.10 + (col + 1) * cell_w - cell_w * 0.08
        panel_fill = _tint(fill, 0.08) if col % 2 == 0 else _shade(fill, 0.92)
        bboxes.append(
            _draw_building_face_rect(
                draw,
                spec,
                camera=camera,
                frame=frame,
                face_axis=str(face_axis),
                face_side=int(face_side),
                span0=span0,
                span1=span1,
                z0=0.15,
                z1=0.91,
                fill=panel_fill,
                outline=outline,
                width=1,
            )
        )
    for row in range(1, 5):
        z = 0.15 + row * 0.152
        bboxes.append(
            _draw_building_face_rect(
                draw,
                spec,
                camera=camera,
                frame=frame,
                face_axis=str(face_axis),
                face_side=int(face_side),
                span0=0.11,
                span1=0.89,
                z0=z,
                z1=z + 0.010,
                fill=outline,
            )
        )
    return list(bboxes)


def _draw_building_horizontal_bands(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    face_axis: str,
    face_side: int,
    rows: int,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
) -> List[List[float]]:
    bboxes: List[List[float]] = []
    rows = max(2, int(rows))
    for row in range(rows):
        cell_h = 0.70 / float(rows)
        z0 = 0.18 + row * cell_h + cell_h * 0.22
        z1 = 0.18 + (row + 1) * cell_h - cell_h * 0.22
        band_fill = _tint(fill, 0.10) if row % 2 == 0 else _shade(fill, 0.94)
        bboxes.append(
            _draw_building_face_rect(
                draw,
                spec,
                camera=camera,
                frame=frame,
                face_axis=str(face_axis),
                face_side=int(face_side),
                span0=0.11,
                span1=0.89,
                z0=z0,
                z1=z1,
                fill=band_fill,
                outline=outline,
                width=1,
            )
        )
    return list(bboxes)


def _draw_retail_front(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    face_axis: str,
    face_side: int,
    fill: Tuple[int, int, int],
) -> List[List[float]]:
    awning_palette = [(176, 59, 62), (63, 127, 112), (201, 159, 68), (70, 95, 145)]
    accent = awning_palette[_stable_palette_index(str(spec.get("object_id", "")), len(awning_palette))]
    outline = (82, 64, 48)
    bboxes = [
        _draw_building_face_rect(
            draw,
            spec,
            camera=camera,
            frame=frame,
            face_axis=str(face_axis),
            face_side=int(face_side),
            span0=0.12,
            span1=0.88,
            z0=0.48,
            z1=0.60,
            fill=accent,
            outline=outline,
            width=1,
        ),
        _draw_building_face_rect(
            draw,
            spec,
            camera=camera,
            frame=frame,
            face_axis=str(face_axis),
            face_side=int(face_side),
            span0=0.16,
            span1=0.46,
            z0=0.16,
            z1=0.43,
            fill=(156, 190, 205),
            outline=outline,
            width=1,
        ),
        _draw_building_face_rect(
            draw,
            spec,
            camera=camera,
            frame=frame,
            face_axis=str(face_axis),
            face_side=int(face_side),
            span0=0.54,
            span1=0.82,
            z0=0.15,
            z1=0.45,
            fill=_tint(fill, 0.20),
            outline=outline,
            width=1,
        ),
    ]
    return bboxes


def _draw_shopfront(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    face_axis: str,
    face_side: int,
    style: str,
    fill: Tuple[int, int, int],
) -> List[List[float]]:
    accents = {
        "cafe_shop": (176, 75, 66),
        "market_shop": (72, 135, 86),
        "bookstore_shop": (82, 95, 151),
    }
    accent = accents.get(str(style), (176, 75, 66))
    trim = _shade(accent, 0.64)
    glass = (168, 204, 210)
    cream = (239, 225, 188)
    outline = (72, 62, 52)
    bboxes: List[List[float]] = [
        _draw_building_face_rect(
            draw,
            spec,
            camera=camera,
            frame=frame,
            face_axis=str(face_axis),
            face_side=int(face_side),
            span0=0.08,
            span1=0.92,
            z0=0.52,
            z1=0.66,
            fill=accent,
            outline=outline,
            width=1,
        ),
        _draw_building_face_rect(
            draw,
            spec,
            camera=camera,
            frame=frame,
            face_axis=str(face_axis),
            face_side=int(face_side),
            span0=0.12,
            span1=0.46,
            z0=0.14,
            z1=0.46,
            fill=glass,
            outline=outline,
            width=1,
        ),
        _draw_building_face_rect(
            draw,
            spec,
            camera=camera,
            frame=frame,
            face_axis=str(face_axis),
            face_side=int(face_side),
            span0=0.56,
            span1=0.78,
            z0=0.12,
            z1=0.46,
            fill=_shade(fill, 0.74),
            outline=outline,
            width=1,
        ),
        _draw_building_face_rect(
            draw,
            spec,
            camera=camera,
            frame=frame,
            face_axis=str(face_axis),
            face_side=int(face_side),
            span0=0.10,
            span1=0.90,
            z0=0.46,
            z1=0.53,
            fill=trim,
            outline=outline,
            width=1,
        ),
    ]
    for stripe_index in range(5):
        span0 = 0.11 + float(stripe_index) * 0.156
        span1 = min(0.89, span0 + 0.116)
        bboxes.append(
            _draw_building_face_rect(
                draw,
                spec,
                camera=camera,
                frame=frame,
                face_axis=str(face_axis),
                face_side=int(face_side),
                span0=span0,
                span1=span1,
                z0=0.47,
                z1=0.52,
                fill=accent if stripe_index % 2 == 0 else cream,
            )
        )
    for span0, span1 in ((0.14, 0.34), (0.38, 0.50), (0.80, 0.90)):
        bboxes.append(
            _draw_building_face_rect(
                draw,
                spec,
                camera=camera,
                frame=frame,
                face_axis=str(face_axis),
                face_side=int(face_side),
                span0=span0,
                span1=span1,
                z0=0.69,
                z1=0.83,
                fill=_tint(glass, 0.12),
                outline=outline,
                width=1,
            )
        )
    return list(bboxes)


def _draw_styled_building_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
    fill: Tuple[int, int, int],
) -> List[float]:
    style = str(spec.get("building_style", "concrete_midrise"))
    bbox = _draw_box_object(draw, spec, camera=camera, frame=frame, fill=fill)
    width, depth, height = (float(value) for value in spec["dimensions_xyz"])
    x, y, _z = (float(value) for value in spec["world_xyz"])
    sx = 1 if float(camera.camera_position[0]) >= x else -1
    sy = 1 if float(camera.camera_position[1]) >= y else -1
    feature_bboxes: List[List[float]] = [list(bbox)]

    if style in {"office_glass", "glass_tower", "concrete_midrise", "stucco_walkup"}:
        cap_h = max(0.035, min(0.075, height * 0.055))
        cap_fill = _shade(fill, 0.72) if style != "stucco_walkup" else (116, 80, 66)
        cap = _sub_box_spec(
            spec,
            offset_xyz=(0.0, 0.0, max(0.0, height - cap_h * 0.72)),
            dimensions_xyz=(width * 1.04, depth * 1.04, cap_h),
        )
        feature_bboxes.append(_draw_box_object(draw, cap, camera=camera, frame=frame, fill=cap_fill))

    visible_faces = (("x", sx), ("y", sy))
    for face_axis, face_side in visible_faces:
        face_span = depth if face_axis == "x" else width
        rows = max(2, min(6, int(round(height / 0.27))))
        cols = max(2, min(5, int(round(face_span / 0.24))))
        if style == "office_glass":
            feature_bboxes.extend(
                _draw_building_window_grid(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    cols=max(3, cols),
                    rows=max(3, rows),
                    z_min=0.18,
                    z_max=0.88,
                    fill=(166, 204, 221),
                    outline=(65, 91, 105),
                    span_margin=0.10,
                )
            )
        elif style == "glass_tower":
            feature_bboxes.extend(
                _draw_building_vertical_glass(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    cols=max(4, cols),
                    fill=(126, 180, 214),
                    outline=(58, 87, 111),
                )
            )
        elif style == "apartment_brick":
            feature_bboxes.extend(
                _draw_building_window_grid(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    cols=max(2, cols - 1),
                    rows=max(3, rows),
                    z_min=0.18,
                    z_max=0.86,
                    fill=(235, 218, 169),
                    outline=(94, 64, 52),
                    span_margin=0.15,
                )
            )
            feature_bboxes.extend(
                _draw_building_face_rect(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    span0=0.12,
                    span1=0.88,
                    z0=z,
                    z1=z + 0.014,
                    fill=(105, 58, 49),
                )
                for z in (0.37, 0.59, 0.81)
            )
        elif style == "retail_corner":
            feature_bboxes.extend(
                _draw_retail_front(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    fill=fill,
                )
            )
            feature_bboxes.extend(
                _draw_building_window_grid(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    cols=max(2, cols - 1),
                    rows=2,
                    z_min=0.66,
                    z_max=0.90,
                    fill=(208, 229, 220),
                    outline=(92, 78, 61),
                    span_margin=0.18,
                )
            )
        elif style in {"cafe_shop", "market_shop", "bookstore_shop"}:
            feature_bboxes.extend(
                _draw_shopfront(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    style=str(style),
                    fill=fill,
                )
            )
        elif style == "stucco_walkup":
            feature_bboxes.extend(
                _draw_building_window_grid(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    cols=max(2, cols - 1),
                    rows=max(2, rows - 1),
                    z_min=0.20,
                    z_max=0.80,
                    fill=(96, 132, 146),
                    outline=(119, 83, 63),
                    span_margin=0.17,
                )
            )
        else:
            feature_bboxes.extend(
                _draw_building_horizontal_bands(
                    draw,
                    spec,
                    camera=camera,
                    frame=frame,
                    face_axis=face_axis,
                    face_side=face_side,
                    rows=max(4, rows),
                    fill=(174, 191, 199),
                    outline=(92, 102, 108),
                )
            )
    return _bbox_union(*feature_bboxes)


def _draw_context_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    object_type = str(spec["object_type"])
    fill = _street_object_fill_rgb(spec)
    if object_type == "building":
        return _draw_styled_building_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "tree":
        width, depth, height = (float(value) for value in spec["dimensions_xyz"])
        trunk = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, 0.0), dimensions_xyz=(width * 0.26, depth * 0.26, height * 0.48))
        canopy = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.42), dimensions_xyz=(width, depth, height * 0.56))
        trunk_bbox = _draw_cylinder_object(draw, trunk, camera=camera, frame=frame, fill=(115, 84, 60))
        canopy_bbox = _draw_sphere_object(draw, canopy, camera=camera, frame=frame, fill=fill)
        return _bbox_union(trunk_bbox, canopy_bbox)
    if object_type == "shrub":
        width, depth, height = (float(value) for value in spec["dimensions_xyz"])
        lobes = [
            _sub_box_spec(spec, offset_xyz=(-width * 0.18, 0.0, height * 0.12), dimensions_xyz=(width * 0.62, depth * 0.62, height * 0.78)),
            _sub_box_spec(spec, offset_xyz=(width * 0.18, 0.0, height * 0.10), dimensions_xyz=(width * 0.62, depth * 0.62, height * 0.74)),
            _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.16, height * 0.16), dimensions_xyz=(width * 0.58, depth * 0.58, height * 0.82)),
        ]
        lobe_bboxes = [
            _draw_sphere_object(draw, lobe, camera=camera, frame=frame, fill=_tint(fill, 0.06 * index))
            for index, lobe in enumerate(lobes)
        ]
        return _bbox_union(*lobe_bboxes)
    if object_type == "traffic_light":
        return _draw_traffic_light_context_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "street_sign":
        return _draw_street_sign_context_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "bench":
        width, depth, height = (float(value) for value in spec["dimensions_xyz"])
        seat = _sub_box_spec(spec, offset_xyz=(0.0, 0.0, height * 0.22), dimensions_xyz=(width, depth, height * 0.18))
        back = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.32, height * 0.42), dimensions_xyz=(width, depth * 0.18, height * 0.36))
        return _draw_box_parts_object(draw, [seat, back], camera=camera, frame=frame, fill=fill)
    return _draw_box_object(draw, spec, camera=camera, frame=frame, fill=fill)


def _draw_candidate_object(
    draw: ImageDraw.ImageDraw,
    spec: Mapping[str, Any],
    *,
    camera,
    frame,
) -> List[float]:
    object_type = str(spec["object_type"])
    fill = _street_object_fill_rgb(spec)
    if object_type in VEHICLE_OBJECT_TYPES:
        return _draw_vehicle_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "scooter":
        return _draw_scooter_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "motorcycle":
        return _draw_motorcycle_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "bicycle":
        return _draw_bicycle_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "pedestrian":
        return _draw_pedestrian_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "traffic_cone":
        return _draw_cone_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "fire_hydrant":
        return _draw_fire_hydrant_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "trash_bin":
        return _draw_trash_bin_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "mailbox":
        return _draw_mailbox_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "construction_barrier":
        return _draw_construction_barrier_object(draw, spec, camera=camera, frame=frame, fill=fill)
    if object_type == "road_barrel":
        return _draw_road_barrel_object(draw, spec, camera=camera, frame=frame, fill=fill)
    return _draw_box_object(draw, spec, camera=camera, frame=frame, fill=fill)


def render_street_intersection_scene_3d(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: _StreetRenderParams,
) -> _RenderedStreetScene:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    camera = _camera_from_dataset(dataset)
    frame = _frame_from_dataset(dataset)
    scene_variant = str(dataset["scene_variant"])
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    street_bbox, entities = _draw_street_shell(
        draw,
        camera=camera,
        frame=frame,
        render_params=render_params,
        scene_variant=str(scene_variant),
        intersection_center_xy=dataset["intersection_center_xy"],
        intersection_layout=str(dataset["intersection_layout"]),
    )
    candidate_specs = [dict(spec) for spec in dataset["candidate_object_specs"]]
    reference_specs = [
        dict(spec)
        for spec in dataset.get("reference_object_specs", [])
        if isinstance(spec, Mapping)
    ]
    context_specs = [dict(spec) for spec in dataset["context_object_specs"]]
    all_specs = [*candidate_specs, *reference_specs, *context_specs]

    for spec in sorted(all_specs, key=lambda item: float(item["camera_distance"]), reverse=True):
        _draw_shadow(draw, spec, camera=camera, frame=frame)
    shape_bboxes: Dict[str, List[float]] = {}
    for spec in sorted(all_specs, key=lambda item: float(item["camera_distance"]), reverse=True):
        if bool(spec.get("is_answer_candidate", False)):
            shape_bboxes[str(spec["object_id"])] = _draw_candidate_object(draw, spec, camera=camera, frame=frame)
        elif str(spec.get("object_role", "")) == "street_reference":
            shape_bboxes[str(spec["object_id"])] = _draw_candidate_object(draw, spec, camera=camera, frame=frame)
        else:
            shape_bboxes[str(spec["object_id"])] = _draw_context_object(draw, spec, camera=camera, frame=frame)

    reference_marker_bboxes: Dict[str, List[float]] = {}
    reference_direction_marker_bboxes: Dict[str, List[float]] = {}
    for spec in reference_specs:
        object_id = str(spec["object_id"])
        if object_id not in shape_bboxes:
            continue
        x0, y0, x1, y1 = (float(value) for value in shape_bboxes[object_id])
        pad = 8.0
        marker_bbox = [
            round(x0 - pad, 3),
            round(y0 - pad, 3),
            round(x1 + pad, 3),
            round(y1 + pad, 3),
        ]
        for offset, color in ((2.0, (255, 255, 255)), (0.0, (216, 44, 44))):
            draw.rectangle(
                (
                    marker_bbox[0] - offset,
                    marker_bbox[1] - offset,
                    marker_bbox[2] + offset,
                    marker_bbox[3] + offset,
                ),
                outline=color,
                width=4,
            )
        reference_marker_bboxes[object_id] = list(marker_bbox)
        shape_bboxes[object_id] = _bbox_union(shape_bboxes[object_id], marker_bbox)
        direction = spec.get("travel_direction_vector_xy")
        if isinstance(direction, Sequence) and not isinstance(direction, (str, bytes)) and len(direction) >= 2:
            dx, dy = float(direction[0]), float(direction[1])
            norm = math.hypot(dx, dy)
            if norm > 0.001:
                dx /= norm
                dy /= norm
                x, y, _base_z = (float(value) for value in spec["base_xyz"])
                _width, _depth, height = (float(value) for value in spec["dimensions_xyz"])
                start = _project_xy((x, y, height + 0.18), camera, frame)
                end = _project_xy((x + dx * 0.62, y + dy * 0.62, height + 0.18), camera, frame)
                draw.line([start, end], fill=(255, 255, 255), width=8)
                draw.line([start, end], fill=(216, 44, 44), width=5)
                vx = float(end[0]) - float(start[0])
                vy = float(end[1]) - float(start[1])
                vnorm = math.hypot(vx, vy)
                if vnorm > 0.001:
                    ux, uy = vx / vnorm, vy / vnorm
                    px, py = -uy, ux
                    head_len = 18.0
                    head_w = 12.0
                    head_points = [
                        (float(end[0]), float(end[1])),
                        (
                            float(end[0]) - ux * head_len + px * head_w * 0.5,
                            float(end[1]) - uy * head_len + py * head_w * 0.5,
                        ),
                        (
                            float(end[0]) - ux * head_len - px * head_w * 0.5,
                            float(end[1]) - uy * head_len - py * head_w * 0.5,
                        ),
                    ]
                    outline_points = [
                        (head_points[0][0] + ux * 1.5, head_points[0][1] + uy * 1.5),
                        (
                            head_points[1][0] - ux * 2.0 + px * 1.8,
                            head_points[1][1] - uy * 2.0 + py * 1.8,
                        ),
                        (
                            head_points[2][0] - ux * 2.0 - px * 1.8,
                            head_points[2][1] - uy * 2.0 - py * 1.8,
                        ),
                    ]
                    draw.polygon(outline_points, fill=(255, 255, 255))
                    draw.polygon(head_points, fill=(216, 44, 44))
                    arrow_bbox = [
                        round(min(start[0], end[0], *(point[0] for point in outline_points)) - 5.0, 3),
                        round(min(start[1], end[1], *(point[1] for point in outline_points)) - 5.0, 3),
                        round(max(start[0], end[0], *(point[0] for point in outline_points)) + 5.0, 3),
                        round(max(start[1], end[1], *(point[1] for point in outline_points)) + 5.0, 3),
                    ]
                    reference_direction_marker_bboxes[object_id] = list(arrow_bbox)
                    shape_bboxes[object_id] = _bbox_union(shape_bboxes[object_id], arrow_bbox)

    label_bboxes: Dict[str, List[float]] = {}
    for spec in sorted(candidate_specs, key=lambda item: str(item["point_label"])):
        label = str(spec["point_label"])
        x, y = float(spec["screen_xy"][0]), float(spec["screen_xy"][1])
        label_bboxes[str(spec["object_id"])] = _draw_option_label(
            draw,
            label=str(label),
            center=(x, y),
            font=label_font,
        )

    object_bboxes: Dict[str, List[float]] = {}
    object_centers: Dict[str, List[float]] = {}
    candidate_bboxes: Dict[str, List[float]] = {}
    candidate_centers: Dict[str, List[float]] = {}
    context_bboxes: Dict[str, List[float]] = {}
    context_centers: Dict[str, List[float]] = {}
    for spec in all_specs:
        object_id = str(spec["object_id"])
        bbox = list(shape_bboxes[object_id])
        if object_id in label_bboxes:
            bbox = _bbox_union(bbox, label_bboxes[object_id])
        center = [round(float(spec["screen_xy"][0]), 3), round(float(spec["screen_xy"][1]), 3)]
        object_bboxes[object_id] = list(bbox)
        object_centers[object_id] = list(center)
        if bool(spec.get("is_answer_candidate", False)):
            label = str(spec["point_label"])
            candidate_bboxes[label] = list(bbox)
            candidate_centers[label] = list(center)
        else:
            context_bboxes[object_id] = list(bbox)
            context_centers[object_id] = list(center)
        fill_rgb = _street_object_fill_rgb(spec)
        entities.append(
            {
                "entity_id": object_id,
                "entity_type": "three_d_street_candidate_object" if bool(spec.get("is_answer_candidate", False)) else "three_d_street_context_object",
                "bbox_px": list(bbox),
                "attrs": {
                    "point_label": spec.get("point_label"),
                    "object_label": spec.get("object_label"),
                    "object_type": str(spec["object_type"]),
                    "object_name": str(spec["object_name"]),
                    "prompt_name": str(spec["prompt_name"]),
                    "building_style": spec.get("building_style"),
                    "building_style_name": spec.get("building_style_name"),
                    "object_role": str(spec["object_role"]),
                    "orientation_axis": str(spec.get("orientation_axis", "")),
                    "is_answer_candidate": bool(spec.get("is_answer_candidate", False)),
                    "fill_rgb": [int(channel) for channel in fill_rgb],
                    "world_xyz": list(spec["world_xyz"]),
                    "base_xyz": list(spec["base_xyz"]),
                    "dimensions_xyz": list(spec["dimensions_xyz"]),
                    "dimension_scale": float(spec.get("dimension_scale", 1.0)),
                    "screen_xy": list(center),
                    "camera_xyz": list(spec["camera_xyz"]),
                    "camera_distance": float(spec["camera_distance"]),
                    "ground_distance_to_intersection": float(spec["ground_distance_to_intersection"]),
                    "intersection_center_xy": list(spec["intersection_center_xy"]),
                    "road_arm": spec.get("road_arm"),
                    "reference_marker": "red_bbox" if object_id in reference_marker_bboxes else None,
                    "reference_marker_bbox_px": reference_marker_bboxes.get(object_id),
                    "reference_direction_marker_bbox_px": reference_direction_marker_bboxes.get(object_id),
                    "travel_direction_vector_xy": spec.get("travel_direction_vector_xy"),
                    "scene_variant": str(scene_variant),
                },
            }
        )
    evidence_ids = [str(value) for value in dataset["target_object_ids"]]
    evidence_bboxes = [list(object_bboxes[object_id]) for object_id in evidence_ids]
    all_bboxes = [list(street_bbox), *[list(value) for value in object_bboxes.values()]]
    scene_bbox = [
        round(float(min(bbox[0] for bbox in all_bboxes)), 3),
        round(float(min(bbox[1] for bbox in all_bboxes)), 3),
        round(float(max(bbox[2] for bbox in all_bboxes)), 3),
        round(float(max(bbox[3] for bbox in all_bboxes)), 3),
    ]
    return _RenderedStreetScene(
        image=image,
        entities=list(entities),
        scene_bbox_px=list(scene_bbox),
        street_bbox_px=list(street_bbox),
        object_bboxes_px=dict(object_bboxes),
        object_centers_px=dict(object_centers),
        candidate_bboxes_px=dict(candidate_bboxes),
        candidate_centers_px=dict(candidate_centers),
        context_object_bboxes_px=dict(context_bboxes),
        context_object_centers_px=dict(context_centers),
        evidence_bboxes=[list(bbox) for bbox in evidence_bboxes],
        evidence_entity_ids=list(evidence_ids),
    )


def _build_complexity(
    *,
    candidate_count: int,
    context_object_count: int,
    nearest_distance_margin: float,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.34)),
        "ground_plane_distance": float(raw_weights.get("ground_plane_distance", 0.36)),
        "perspective_depth": float(raw_weights.get("perspective_depth", 0.18)),
        "ambiguity": float(raw_weights.get("ambiguity", 0.12)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    ambiguity = 1.0 - _normalize_unit(float(nearest_distance_margin), 0.48, 1.30)
    components = {
        "visual_scan": _normalize_unit(float(candidate_count + context_object_count), 9.0, 15.0),
        "ground_plane_distance": 0.74,
        "perspective_depth": 0.62,
        "ambiguity": max(0.0, min(1.0, float(ambiguity))),
    }
    score = sum(float(components[key]) * max(0.0, float(weights[key])) for key in weights) / float(total)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={key: round(float(value), 6) for key, value in components.items()},
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "street")
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
class ThreeDStreetIntersectionNearestLabelTask:
    """Choose the lettered street object nearest to an intersection center."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "street"
    default_dataset_enabled = True

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(
                    spawn_rng(
                        int(instance_seed),
                        f"{TASK_ID}.attempt_seed.{attempt_index}",
                    ).randrange(1, 2**62)
                )
            )
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(
            f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}"
        )

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
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
        intersection_layout, intersection_layout_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_INTERSECTION_LAYOUTS,
            explicit_key="intersection_layout",
            weights_key="intersection_layout_weights",
            balance_flag_key="balanced_intersection_layout_sampling",
            axis_namespace="intersection_layout",
        )
        candidate_count, candidate_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="candidate_count",
            default_min=6,
            default_max=6,
            lower=5,
            upper=6,
        )
        context_object_count, context_object_count_probabilities = _shared_resolve_count(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            key="context_object_count",
            default_min=10,
            default_max=10,
            lower=6,
            upper=12,
        )
        camera_yaw_band, camera_yaw_probabilities, camera_yaw_band_index = _resolve_camera_yaw_band(
            params,
            instance_seed=int(instance_seed),
        )
        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_street_dataset(
            params=params,
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            intersection_layout=str(intersection_layout),
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
        rendered_scene = render_street_intersection_scene_3d(
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
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in rendered_scene.evidence_bboxes
        ]
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        complexity = _build_complexity(
            candidate_count=int(dataset["candidate_count"]),
            context_object_count=int(dataset["context_object_count"]),
            nearest_distance_margin=float(dataset["nearest_distance_margin"]),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )
        solver_trace = dict(dataset["solver_trace"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_street_intersection",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "candidate_count": int(dataset["candidate_count"]),
                    "context_object_count": int(dataset["context_object_count"]),
                    "object_count": int(dataset["object_count"]),
                    "intersection_center_xy": list(dataset["intersection_center_xy"]),
                    "intersection_layout": str(dataset["intersection_layout"]),
                    "missing_road_arm": dataset["missing_road_arm"],
                    "ground_distance_to_intersection_by_label": dict(dataset["ground_distance_to_intersection_by_label"]),
                    "candidate_ground_xy_by_label": dict(dataset["candidate_ground_xy_by_label"]),
                    "candidate_object_types_by_label": dict(dataset["candidate_object_types_by_label"]),
                    "distance_order_near_to_far": list(dataset["distance_order_near_to_far"]),
                    "answer_label": str(answer_label),
                    "answer_object_id": str(dataset["answer_object_id"]),
                    "view_family": "synthetic_perspective_3d_street",
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
                    "intersection_layout": str(intersection_layout),
                    "intersection_layout_probabilities": dict(intersection_layout_probabilities),
                    "candidate_count": int(candidate_count),
                    "candidate_count_probabilities": dict(candidate_count_probabilities),
                    "context_object_count": int(context_object_count),
                    "context_object_count_probabilities": dict(context_object_count_probabilities),
                    "camera_yaw_band": str(camera_yaw_band_index),
                    "camera_yaw_band_index": int(camera_yaw_band_index),
                    "camera_yaw_band_probabilities": dict(camera_yaw_probabilities),
                    "intersection_center_xy": list(dataset["intersection_center_xy"]),
                    "object_count": int(dataset["object_count"]),
                    "answer_label_probabilities": {
                        str(label): round(1.0 / float(candidate_count), 8)
                        for label in POINT_LABELS[: int(candidate_count)]
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "intersection_layout": str(dataset["intersection_layout"]),
                "missing_road_arm": dataset["missing_road_arm"],
                "intersection_center_xy": list(dataset["intersection_center_xy"]),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "label_font_size_px": int(render_params.label_font_size_px),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "street_bbox_px": list(rendered_scene.street_bbox_px),
                "object_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.object_bboxes_px.items()
                },
                "object_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.object_centers_px.items()
                },
                "candidate_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.candidate_bboxes_px.items()
                },
                "candidate_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.candidate_centers_px.items()
                },
                "context_object_bboxes_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.context_object_bboxes_px.items()
                },
                "context_object_centers_px": {
                    str(key): list(value)
                    for key, value in rendered_scene.context_object_centers_px.items()
                },
                "target_object_bboxes_px": {
                    str(key): list(rendered_scene.object_bboxes_px[str(key)])
                    for key in dataset["target_object_ids"]
                },
            },
            "execution_trace": {
                "query_variant": "default",
                "query_id": str(query_variant),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "candidate_count": int(dataset["candidate_count"]),
                "context_object_count": int(dataset["context_object_count"]),
                "object_count": int(dataset["object_count"]),
                "intersection_layout": str(dataset["intersection_layout"]),
                "missing_road_arm": dataset["missing_road_arm"],
                "answer_label": str(answer_label),
                "answer_object_id": str(dataset["answer_object_id"]),
                "answer_object_type": str(dataset["answer_object_type"]),
                "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                "candidate_object_specs": [dict(spec) for spec in dataset["candidate_object_specs"]],
                "context_object_specs": [dict(spec) for spec in dataset["context_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "intersection_center_xy": list(dataset["intersection_center_xy"]),
                "candidate_ground_xy_by_label": dict(dataset["candidate_ground_xy_by_label"]),
                "ground_distance_to_intersection_by_label": dict(dataset["ground_distance_to_intersection_by_label"]),
                "candidate_object_types_by_label": dict(dataset["candidate_object_types_by_label"]),
                "candidate_projected_bboxes_by_label": dict(dataset["candidate_projected_bboxes_by_label"]),
                "distance_order_near_to_far": list(dataset["distance_order_near_to_far"]),
                "nearest_distance_margin": float(dataset["nearest_distance_margin"]),
                "min_pairwise_ground_distance_gap": float(dataset["min_pairwise_ground_distance_gap"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_variant),
                "view_family": "synthetic_perspective_3d_street",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "object",
                "id": str(dataset["answer_object_id"]),
                "answer": str(answer_label),
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


__all__ = ["ThreeDStreetIntersectionNearestLabelTask"]
