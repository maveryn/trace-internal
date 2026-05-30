"""Shared street-intersection scene assembly for three_d tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import group_default
from ...shared.text_rendering import load_font
from ..shared.task_support import float_value as _float_value
from ..shared.task_support import int_value as _int_value
from ..shared.object_resources import (
    BUILDING_STYLE_DIMENSION_FACTORS,
    BUILDING_STYLE_POOLS,
    BUILDING_STYLES,
)
from ..shared.camera_projection import (
    project_screen as _project_screen,
    project_xy as _project_xy,
)
from ..shared.object_scene_rendering import (
    _bbox_union,
    _draw_option_label,
)
from ..shared.object_scene import (
    _bbox_intersection_area,
    _object_reference_points,
    _object_screen_bbox,
)
from .intersection_rendering import (
    PEDESTRIAN_OBJECT_TYPES,
    _street_object_name,
    _street_object_fill_rgb,
    _base_street_object_dimensions,
    _fixed_building_style_for_street_object,
    _apply_street_building_style,
    _dimensions_for_orientation,
    _orientation_axis_for_xy,
    _missing_arm_for_layout,
    _arm_is_present,
    _canvas_floor_polygon_available,
    _draw_street_shell,
    _draw_shadow,
    _draw_candidate_object,
    _draw_context_object,
    _stable_palette_index,
)


SCENE_ID = "street"
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
MIN_CANDIDATE_VISIBLE_PX = 20.0
MIN_CANDIDATE_CENTER_SEPARATION_PX = 42.0
MAX_CANDIDATE_BBOX_INTERSECTION_PX = 6500.0
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
    if str(object_type) in PEDESTRIAN_OBJECT_TYPES:
        if str(object_type) == "female_pedestrian":
            gender_id = "female"
        elif str(object_type) == "male_pedestrian":
            gender_id = "male"
        else:
            gender_id = "female" if _stable_palette_index(str(object_id), 2) == 1 else "male"
        spec.update(
            {
                "pedestrian_gender_id": str(gender_id),
                "pedestrian_appearance_id": f"pedestrian_{gender_id}",
            }
        )
    return spec


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
        context_specs.append(_apply_street_building_style(spec, style=str(building_style)))
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
        ("store", (-3.34, 1.56), "x", 0.12),
        ("store", (3.34, -1.56), "x", 0.12),
        ("office_building", (-3.58, -1.70), "x", 0.12),
        ("office_building", (3.58, 1.70), "x", 0.12),
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
        spec = _make_street_object_spec(
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
        context_specs.append(_apply_street_building_style(spec))
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

__all__ = [
    "DEFAULT_INTERSECTION_CENTER_JITTER_X",
    "DEFAULT_INTERSECTION_CENTER_JITTER_Y",
    "INTERSECTION_CENTER_XY",
    "MAX_CANDIDATE_BBOX_INTERSECTION_PX",
    "MIN_CANDIDATE_CENTER_SEPARATION_PX",
    "MIN_CANDIDATE_VISIBLE_PX",
    "SCENE_ID",
    "STREET_CAMERA_YAW_BANDS_DEGREES",
    "STREET_FULL_BLEED_FALLBACK_EXTENT_MULTIPLIER",
    "SUPPORTED_INTERSECTION_LAYOUTS",
    "SUPPORTED_SCENE_VARIANTS",
    "_RenderedStreetScene",
    "_StreetRenderParams",
    "_arm_is_present",
    "_bbox_area",
    "_bbox_intersection_area",
    "_candidate_context_visibility_ok",
    "_candidate_screen_separation_ok",
    "_canvas_floor_polygon_available",
    "_dimensions_for_orientation",
    "_draw_candidate_object",
    "_finalize_specs",
    "_frame_from_dataset",
    "_make_street_object_spec",
    "_min_pairwise",
    "_missing_arm_for_layout",
    "_object_reference_points",
    "_object_screen_bbox",
    "_orientation_axis_for_xy",
    "_resolve_render_params",
    "_sample_context_specs",
    "_sample_intersection_center",
    "_slot_allowed_for_layout",
    "_translate_scene_xy",
    "render_street_intersection_scene_3d",
]
