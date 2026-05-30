"""Tool, device, and toy glyphs for shared three_d object scenes."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from .camera_projection import (
    CameraSpec as _CameraSpec,
    ProjectionFrame as _ProjectionFrame,
    distance as _distance,
    project_xy as _project_xy,
)
from .object_scene_primitives import (
    _arrow_footprint_points,
    _bbox_from_screen_points,
    _bbox_union,
    _draw_box_object,
    _draw_box_parts_object,
    _draw_cone_object,
    _draw_cylinder_object,
    _draw_footprint_prism_object,
    _draw_half_cylinder_object,
    _draw_line,
    _draw_polyline,
    _draw_pyramid_object,
    _draw_sphere_object,
    _draw_torus_object,
    _draw_upright_profile_object,
    _draw_wedge_object,
    _face_distance,
    _gear_footprint_points,
    _heart_profile_points,
    _hexagon_footprint_points,
    _object_vertices,
    _oval_profile_points,
    _project_face,
    _radius_px_for_object,
    _shade,
    _star_footprint_points,
    _sub_box_spec,
    _tint,
    _upright_profile_world_points,
    _upright_screen_points,
)


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
    x, y, _z = (float(value) for value in spec["world_xyz"])
    raw_base = spec.get("base_xyz", (x, y, 0.0))
    base_z = float(raw_base[2]) if isinstance(raw_base, Sequence) and len(raw_base) >= 3 else 0.0
    beam = [
        _project_xy((x, y + depth * 0.54, base_z + height * 0.48), camera, frame),
        _project_xy((x - width * 0.80, y + depth * 1.62, base_z + height * 0.72), camera, frame),
        _project_xy((x + width * 0.80, y + depth * 1.62, base_z + height * 0.20), camera, frame),
    ]
    draw.polygon(beam, fill=(248, 237, 164))
    _draw_polyline(draw, beam, fill=(220, 202, 118), width=1)
    body = _sub_box_spec(spec, offset_xyz=(0.0, -depth * 0.18, height * 0.02), dimensions_xyz=(width * 0.42, depth * 0.60, height * 0.48))
    head = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.24, 0.0), dimensions_xyz=(width * 0.64, depth * 0.32, height * 0.70))
    bezel = _sub_box_spec(spec, offset_xyz=(0.0, depth * 0.44, height * 0.02), dimensions_xyz=(width * 0.76, depth * 0.14, height * 0.76))
    bboxes = [
        _bbox_from_screen_points(beam),
        _draw_box_object(draw, body, camera=camera, frame=frame, fill=(52, 62, 74)),
        _draw_cylinder_object(draw, head, camera=camera, frame=frame, fill=(88, 102, 118)),
        _draw_cylinder_object(draw, bezel, camera=camera, frame=frame, fill=(44, 52, 63)),
    ]
    lens = _project_xy((x, y + depth * 0.52, base_z + height * 0.40), camera, frame)
    radius = max(5.0, _radius_px_for_object(bezel, camera, frame) * 0.28)
    draw.ellipse((lens[0] - radius, lens[1] - radius * 0.70, lens[0] + radius, lens[1] + radius * 0.70), fill=(255, 240, 132), outline=(30, 38, 48), width=2)
    button = _upright_screen_points(body, camera=camera, frame=frame, profile_xz=[(0.0, 0.16)])[0]
    button_radius = max(2.2, radius * 0.24)
    draw.ellipse((button[0] - button_radius, button[1] - button_radius, button[0] + button_radius, button[1] + button_radius), fill=(206, 64, 54), outline=(28, 35, 45), width=1)
    bboxes.append([button[0] - button_radius, button[1] - button_radius, button[0] + button_radius, button[1] + button_radius])
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
    bbox = _draw_upright_profile_object(draw, spec, camera=camera, frame=frame, fill=(28, 34, 43), profile_xz=[(-0.56, -1.0), (0.56, -1.0), (0.56, 1.0), (-0.56, 1.0)], inset_scale=0.0)
    screen = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.44, -0.74), (0.44, -0.74), (0.44, 0.72), (-0.44, 0.72)])
    draw.polygon(screen, fill=(78, 138, 182))
    _draw_polyline(draw, screen, fill=(18, 24, 30), width=1)
    speaker = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.18, 0.84), (0.18, 0.84)])
    draw.line(speaker, fill=(212, 218, 224), width=2)
    camera_dot = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(0.30, 0.84)])[0]
    dot_radius = max(1.8, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.014)
    draw.ellipse((camera_dot[0] - dot_radius, camera_dot[1] - dot_radius, camera_dot[0] + dot_radius, camera_dot[1] + dot_radius), fill=(160, 176, 188))
    bboxes = [bbox, _bbox_from_screen_points(screen), _bbox_from_screen_points(speaker), [camera_dot[0] - dot_radius, camera_dot[1] - dot_radius, camera_dot[0] + dot_radius, camera_dot[1] + dot_radius]]
    icon_colors = [(236, 84, 72), (245, 186, 69), (81, 182, 121), (79, 144, 222), (154, 99, 210), (58, 194, 205)]
    icon_index = 0
    icon_size = max(2.6, float(frame.scale) * float(spec["dimensions_xyz"][0]) * 0.020)
    for pz in (0.34, 0.02, -0.30):
        for px in (-0.26, 0.0, 0.26):
            center = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(px, pz)])[0]
            icon_bbox = [center[0] - icon_size, center[1] - icon_size, center[0] + icon_size, center[1] + icon_size]
            draw.rectangle(icon_bbox, fill=icon_colors[icon_index % len(icon_colors)], outline=(20, 28, 38), width=1)
            bboxes.append(icon_bbox)
            icon_index += 1
    home_bar = _upright_screen_points(spec, camera=camera, frame=frame, profile_xz=[(-0.18, -0.88), (0.18, -0.88)])
    draw.line(home_bar, fill=(226, 230, 234), width=2)
    bboxes.append(_bbox_from_screen_points(home_bar))
    return _bbox_union(*bboxes)


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


__all__ = [
    "_draw_scissors_object",
    "_draw_screwdriver_object",
    "_draw_pencil_object",
    "_draw_spoon_object",
    "_draw_spatula_object",
    "_draw_toothbrush_object",
    "_draw_whistle_object",
    "_draw_flashlight_object",
    "_draw_calculator_object",
    "_draw_phone_object",
    "_draw_light_bulb_object",
    "_draw_suitcase_object",
    "_draw_dice_object",
    "_draw_rocket_object",
    "_draw_kite_object",
    "_draw_paint_can_object",
    "_draw_cactus_object",
]
