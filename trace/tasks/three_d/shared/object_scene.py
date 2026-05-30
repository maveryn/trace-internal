"""Shared object-scene assembly for synthetic three_d spatial tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.text_rendering import load_font
from .task_support import float_value as _float_value
from .task_support import int_value as _int_value
from .color_variation import resolve_three_d_object_fill_rgb
from .camera_projection import (
    CameraSpec as _CameraSpec,
    ProjectionFrame as _ProjectionFrame,
    build_projection_frame as _build_projection_frame,
    canvas_floor_polygon_xy as _canvas_floor_polygon_xy,
    dedupe_line_points as _dedupe_line_points,
    distance as _distance,
    grid_values_for_range as _grid_values_for_range,
    min_pairwise as _min_pairwise,
    polygon_axis_line_segment as _polygon_axis_line_segment,
    project_normalized as _project_normalized,
    project_screen as _project_screen,
    project_xy as _project_xy,
    sample_camera as _sample_camera,
    screen_to_floor_xy as _screen_to_floor_xy,
    screen_to_normalized as _screen_to_normalized,
    stage_reference_points as _stage_reference_points,
    vec_cross as _vec_cross,
    vec_dot as _vec_dot,
    vec_norm as _vec_norm,
    vec_sub as _vec_sub,
)
from .object_scene_rendering import (
    _bbox_union,
    _draw_line,
    _draw_room,
    _shade,
    _tint,
    _object_vertices,
    _draw_polyline,
    _bbox_from_screen_points,
    _project_face,
    _face_distance,
    _draw_box_object,
    _sub_box_spec,
    _draw_box_parts_object,
    _draw_footprint_prism_object,
    _star_footprint_points,
    _hexagon_footprint_points,
    _arrow_footprint_points,
    _gear_footprint_points,
    _draw_half_cylinder_object,
    _draw_pyramid_object,
    _draw_wedge_object,
    _upright_profile_world_points,
    _draw_upright_profile_object,
    _heart_profile_points,
    _draw_shield_object,
    _draw_heart_object,
    _draw_diamond_object,
    _draw_sword_object,
    _draw_key_object,
    _draw_crown_object,
    _draw_hourglass_object,
    _draw_anchor_object,
    _draw_horseshoe_object,
    _draw_hammer_object,
    _draw_bell_object,
    _draw_trophy_object,
    _draw_open_book_object,
    _draw_dumbbell_object,
    _draw_mushroom_object,
    _draw_lantern_object,
    _draw_wrench_object,
    _oval_profile_points,
    _draw_padlock_object,
    _draw_magnifying_glass_object,
    _draw_candle_object,
    _draw_scroll_object,
    _draw_paint_brush_object,
    _draw_paint_palette_object,
    _draw_goblet_object,
    _draw_teapot_object,
    _draw_watering_can_object,
    _draw_basket_object,
    _draw_mail_envelope_object,
    _draw_camera_object,
    _draw_compass_object,
    _draw_flask_object,
    _draw_test_tube_rack_object,
    _draw_scroll_map_object,
    _draw_microphone_object,
    _draw_stopwatch_object,
    _upright_screen_points,
    _draw_apple_object,
    _draw_carrot_object,
    _draw_pear_object,
    _draw_fish_object,
    _draw_leaf_object,
    _draw_feather_object,
    _draw_shoe_object,
    _draw_glove_object,
    _draw_hat_object,
    _draw_helmet_object,
    _draw_cup_object,
    _draw_bottle_object,
    _draw_vase_object,
    _draw_umbrella_object,
    _draw_scissors_object,
    _draw_screwdriver_object,
    _draw_pencil_object,
    _draw_spoon_object,
    _draw_spatula_object,
    _draw_toothbrush_object,
    _draw_whistle_object,
    _draw_flashlight_object,
    _draw_calculator_object,
    _draw_phone_object,
    _draw_light_bulb_object,
    _draw_suitcase_object,
    _draw_dice_object,
    _draw_rocket_object,
    _draw_kite_object,
    _draw_paint_can_object,
    _draw_cactus_object,
    _draw_pumpkin_object,
    _draw_acorn_object,
    _draw_pinecone_object,
    _draw_seashell_object,
    _draw_magnet_object,
    _draw_guitar_object,
    _draw_drum_object,
    _draw_shovel_object,
    _draw_saw_object,
    _draw_pliers_object,
    _draw_telescope_object,
    _draw_ruler_object,
    _draw_pickaxe_object,
    _draw_paint_roller_object,
    _draw_tape_measure_object,
    _draw_remote_control_object,
    _draw_plug_object,
    _draw_wallet_object,
    _draw_purse_object,
    _draw_sunglasses_object,
    _draw_violin_object,
    _draw_trumpet_object,
    _draw_donut_object,
    _draw_pretzel_object,
    _draw_lollipop_object,
    _draw_ice_cream_cone_object,
    _draw_soap_bar_object,
    _draw_clock_object,
    _radius_px_for_object,
    _draw_sphere_object,
    _draw_cylinder_object,
    _draw_cone_object,
    _draw_torus_object,
    _draw_arch_object,
    _draw_table_object,
    _draw_shelf_object,
    _draw_open_box_object,
    _draw_refrigerator_object,
    _draw_washing_machine_object,
    _draw_vending_machine_object,
    _draw_trash_bin_object,
    _draw_bench_object,
    _draw_piano_object,
    _draw_locker_object,
    _draw_cabinet_object,
    _draw_sofa_object,
    _draw_barrel_object,
    _draw_chair_object,
    _draw_option_label,
)
from .object_resources import (
    OBJECT_SCENE_CONTEXT_DIMENSIONS,
    OBJECT_SCENE_CONTEXT_SHAPE_TYPES,
    OBJECT_SCENE_NAME_BY_SHAPE_TYPE,
    OBJECT_SCENE_SHAPE_TYPES,
    OBJECT_SCENE_SMALL_DIMENSIONS,
    OBJECT_SCENE_SMALL_SHAPE_TYPES,
)

SCENE_ID = "object_scene"
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


def render_object_scene_3d(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: _RenderParams,
    draw_candidate_labels: bool = True,
    highlight_object_ids: Sequence[str] = (),
    evidence_label: str | None = None,
    compute_single_evidence: bool = True,
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
        if spec.get("fill_rgb") is not None:
            fallback_color = POINT_COLORS[POINT_LABELS.index(label) % len(POINT_COLORS)] if label in POINT_LABELS else POINT_COLORS[0]
            color = _rgb(spec.get("fill_rgb"), fallback_color)
        elif bool(spec.get("is_answer_candidate", False)):
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
        elif shape_type == "mushroom":
            shape_bbox = _draw_mushroom_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "lantern":
            shape_bbox = _draw_lantern_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "candle":
            shape_bbox = _draw_candle_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "goblet":
            shape_bbox = _draw_goblet_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "mail_envelope":
            shape_bbox = _draw_mail_envelope_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "compass":
            shape_bbox = _draw_compass_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "flask":
            shape_bbox = _draw_flask_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "clock":
            shape_bbox = _draw_clock_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "apple":
            shape_bbox = _draw_apple_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "carrot":
            shape_bbox = _draw_carrot_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "fish":
            shape_bbox = _draw_fish_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "leaf":
            shape_bbox = _draw_leaf_object(draw, spec, camera=camera, frame=frame, fill=color)
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
        elif shape_type == "umbrella":
            shape_bbox = _draw_umbrella_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "calculator":
            shape_bbox = _draw_calculator_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "dice":
            shape_bbox = _draw_dice_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "kite":
            shape_bbox = _draw_kite_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "cactus":
            shape_bbox = _draw_cactus_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "drum":
            shape_bbox = _draw_drum_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "ruler":
            shape_bbox = _draw_ruler_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "remote_control":
            shape_bbox = _draw_remote_control_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "plug":
            shape_bbox = _draw_plug_object(draw, spec, camera=camera, frame=frame, fill=color)
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
        elif shape_type == "refrigerator":
            shape_bbox = _draw_refrigerator_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "washing_machine":
            shape_bbox = _draw_washing_machine_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "vending_machine":
            shape_bbox = _draw_vending_machine_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "trash_bin":
            shape_bbox = _draw_trash_bin_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "bench":
            shape_bbox = _draw_bench_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "piano":
            shape_bbox = _draw_piano_object(draw, spec, camera=camera, frame=frame, fill=color)
        elif shape_type == "locker":
            shape_bbox = _draw_locker_object(draw, spec, camera=camera, frame=frame, fill=color)
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
            if bool(draw_candidate_labels):
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
                "entity_type": (
                    "three_d_candidate_object"
                    if bool(spec.get("is_answer_candidate", False))
                    else "three_d_countable_object"
                    if bool(spec.get("is_countable_object", False))
                    else "three_d_context_object"
                ),
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
                    "is_countable_object": bool(spec.get("is_countable_object", False)),
                    "matches_query": bool(spec.get("matches_query", False)),
                    "count_role": str(spec.get("count_role", "")) or None,
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

    for object_id in tuple(str(item) for item in highlight_object_ids):
        if object_id not in object_bboxes:
            continue
        raw_bbox = object_bboxes[str(object_id)]
        highlight_bbox = [
            round(max(0.0, float(raw_bbox[0]) - 8.0), 3),
            round(max(0.0, float(raw_bbox[1]) - 8.0), 3),
            round(min(float(render_params.canvas_width), float(raw_bbox[2]) + 8.0), 3),
            round(min(float(render_params.canvas_height), float(raw_bbox[3]) + 8.0), 3),
        ]
        draw.rectangle(highlight_bbox, outline=(24, 25, 28), width=8)
        draw.rectangle(highlight_bbox, outline=(220, 42, 45), width=4)
        entities.append(
            {
                "entity_id": f"red_reference_box_{object_id}",
                "entity_type": "red_reference_box",
                "bbox_px": list(highlight_bbox),
                "attrs": {
                    "target_object_id": str(object_id),
                    "scene_variant": str(scene_variant),
                },
            }
        )

    evidence_bboxes: List[List[float]] = []
    evidence_entity_ids: List[str] = []
    if bool(compute_single_evidence):
        answer_label = str(evidence_label if evidence_label is not None else dataset["answer_label"])
        evidence_bboxes = [list(point_bboxes[answer_label])]
        evidence_entity_ids = [str(dataset["answer_point_id"])]
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
        evidence_bboxes=list(evidence_bboxes),
        evidence_entity_ids=list(evidence_entity_ids),
    )

__all__ = [
    "CAMERA_YAW_BANDS_DEGREES",
    "CONTEXT_OBJECT_COLORS",
    "LARGE_CONTEXT_SHAPE_TYPES",
    "NAMEABLE_CONTEXT_SHAPE_TYPES",
    "NAMEABLE_SMALL_OBJECT_SHAPE_TYPES",
    "OBJECT_NAME_BY_SHAPE_TYPE",
    "POINT_COLORS",
    "POINT_LABELS",
    "SCENE_ID",
    "SHAPE_TYPES",
    "SMALL_OBJECT_SHAPE_TYPES",
    "SUPPORTED_SCENE_VARIANTS",
    "_RenderedScene",
    "_RenderParams",
    "_base_shape_dimensions",
    "_bbox_intersection_area",
    "_bool_value",
    "_camera_from_dataset",
    "_camera_yaw_band_for_instance",
    "_frame_from_dataset",
    "_make_object_spec",
    "_nameable_for_prompt",
    "_object_name",
    "_object_reference_points",
    "_object_screen_bbox",
    "_resolve_render_params",
    "_sample_scene_object_specs",
    "_sample_shape_dimensions",
    "render_object_scene_3d",
]
