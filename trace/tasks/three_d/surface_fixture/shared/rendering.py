"""Rendering helpers for synthetic 3D surface-fixture scenes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw


@dataclass(frozen=True)
class RenderedSurfaceFixture:
    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    fixture_bbox_px: List[float]
    element_bboxes_px: Dict[str, List[float]]
    element_centers_px: Dict[str, List[float]]


def bbox_union(*bboxes: Sequence[float]) -> List[float]:
    return [
        round(float(min(float(bbox[0]) for bbox in bboxes)), 3),
        round(float(min(float(bbox[1]) for bbox in bboxes)), 3),
        round(float(max(float(bbox[2]) for bbox in bboxes)), 3),
        round(float(max(float(bbox[3]) for bbox in bboxes)), 3),
    ]


def bbox_from_points(points: Sequence[Sequence[float]]) -> List[float]:
    return bbox_union(*[[point[0], point[1], point[0], point[1]] for point in points])


def quad_point(quad: Sequence[Sequence[float]], u: float, v: float) -> Tuple[float, float]:
    top_x = float(quad[0][0]) + (float(quad[1][0]) - float(quad[0][0])) * float(u)
    top_y = float(quad[0][1]) + (float(quad[1][1]) - float(quad[0][1])) * float(u)
    bottom_x = float(quad[3][0]) + (float(quad[2][0]) - float(quad[3][0])) * float(u)
    bottom_y = float(quad[3][1]) + (float(quad[2][1]) - float(quad[3][1])) * float(u)
    return (
        float(top_x + (bottom_x - top_x) * float(v)),
        float(top_y + (bottom_y - top_y) * float(v)),
    )


def quad_cell(quad: Sequence[Sequence[float]], u0: float, v0: float, u1: float, v1: float) -> List[Tuple[float, float]]:
    return [
        quad_point(quad, u0, v0),
        quad_point(quad, u1, v0),
        quad_point(quad, u1, v1),
        quad_point(quad, u0, v1),
    ]


def shrink_polygon(points: Sequence[Sequence[float]], scale: float) -> List[Tuple[float, float]]:
    cx = sum(float(point[0]) for point in points) / float(len(points))
    cy = sum(float(point[1]) for point in points) / float(len(points))
    return [
        (
            float(cx + (float(point[0]) - cx) * float(scale)),
            float(cy + (float(point[1]) - cy) * float(scale)),
        )
        for point in points
    ]


def _mix(rgb: Sequence[int], other: Sequence[int], alpha: float) -> Tuple[int, int, int]:
    return tuple(
        int(round(float(rgb[index]) * (1.0 - float(alpha)) + float(other[index]) * float(alpha)))
        for index in range(3)
    )


def _as_rgb(value: Any, default: Sequence[int]) -> Tuple[int, int, int]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) >= 3:
        return (int(value[0]), int(value[1]), int(value[2]))
    return (int(default[0]), int(default[1]), int(default[2]))


def layout_surface_element_grid(count: int) -> Tuple[int, int]:
    cols = max(2, int(math.ceil(math.sqrt(float(count) * 1.35))))
    rows = int(math.ceil(float(count) / float(cols)))
    return int(rows), int(cols)


def fixture_quad(render_params: Any, scene_variant: str) -> List[Tuple[float, float]]:
    """Return the projected panel quadrilateral for one fixture family.

    The panel shape is the scene grammar anchor: wall-like fixtures use a
    mostly upright projection, floor pavers use a lower perspective slab, and
    specialty panels use mild offsets while preserving a single convex support
    surface for all element bboxes.
    """

    width = float(render_params.canvas_width)
    height = float(render_params.canvas_height)
    wall_like = {
        "wall_tile_panel",
        "brick_wall",
        "locker_bank",
        "mailbox_bank",
        "server_rack",
        "control_panel",
        "solar_panel_array",
    }
    if str(scene_variant) in wall_like:
        return [
            (width * 0.18, height * 0.15),
            (width * 0.83, height * 0.12),
            (width * 0.80, height * 0.77),
            (width * 0.14, height * 0.80),
        ]
    if str(scene_variant) == "paver_floor":
        return [
            (width * 0.12, height * 0.44),
            (width * 0.82, height * 0.33),
            (width * 0.91, height * 0.78),
            (width * 0.20, height * 0.88),
        ]
    if str(scene_variant) == "slot_board":
        return [
            (width * 0.19, height * 0.20),
            (width * 0.80, height * 0.18),
            (width * 0.85, height * 0.76),
            (width * 0.14, height * 0.74),
        ]
    if str(scene_variant) == "compartment_tray":
        return [
            (width * 0.17, height * 0.24),
            (width * 0.84, height * 0.18),
            (width * 0.80, height * 0.78),
            (width * 0.12, height * 0.74),
        ]
    if str(scene_variant) == "vent_panel":
        return [
            (width * 0.18, height * 0.19),
            (width * 0.83, height * 0.17),
            (width * 0.84, height * 0.73),
            (width * 0.15, height * 0.77),
        ]
    if str(scene_variant) == "window_grid":
        return [
            (width * 0.18, height * 0.15),
            (width * 0.82, height * 0.12),
            (width * 0.80, height * 0.76),
            (width * 0.15, height * 0.80),
        ]
    if str(scene_variant) == "door_bank":
        return [
            (width * 0.16, height * 0.18),
            (width * 0.84, height * 0.17),
            (width * 0.82, height * 0.82),
            (width * 0.13, height * 0.79),
        ]
    if str(scene_variant) == "drawer_pull_panel":
        return [
            (width * 0.17, height * 0.19),
            (width * 0.83, height * 0.15),
            (width * 0.85, height * 0.76),
            (width * 0.13, height * 0.77),
        ]
    return [
        (width * 0.18, height * 0.18),
        (width * 0.82, height * 0.16),
        (width * 0.86, height * 0.78),
        (width * 0.13, height * 0.76),
    ]


def _panel_fill(scene_variant: str) -> Tuple[int, int, int]:
    return {
        "wall_tile_panel": (226, 229, 224),
        "perforated_panel": (184, 193, 198),
        "slot_board": (200, 181, 142),
        "compartment_tray": (197, 207, 205),
        "vent_panel": (198, 205, 207),
        "window_grid": (184, 205, 219),
        "door_bank": (183, 162, 125),
        "drawer_pull_panel": (202, 188, 162),
        "brick_wall": (176, 96, 75),
        "paver_floor": (170, 158, 136),
        "locker_bank": (174, 184, 194),
        "mailbox_bank": (189, 179, 151),
        "server_rack": (62, 70, 81),
        "control_panel": (86, 96, 105),
        "solar_panel_array": (37, 64, 92),
    }.get(str(scene_variant), (218, 224, 226))


def _draw_fixture_context(draw: ImageDraw.ImageDraw, render_params: Any, quad: Sequence[Sequence[float]], scene_variant: str) -> List[float]:
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    floor_y = int(height * 0.83)
    draw.polygon([(0, floor_y), (width, int(height * 0.70)), (width, height), (0, height)], fill=(221, 226, 224))
    draw.line([(0, floor_y), (width, int(height * 0.70))], fill=(160, 166, 168), width=2)
    if str(scene_variant) == "paver_floor":
        shadow = [(float(x) + 8.0, float(y) + 10.0) for x, y in quad]
    else:
        shadow = [(float(x) + 12.0, float(y) + 16.0) for x, y in quad]
    draw.polygon(shadow, fill=(171, 178, 181))
    panel_fill = _panel_fill(str(scene_variant))
    draw.polygon([(float(x), float(y)) for x, y in quad], fill=panel_fill)
    outline = (43, 50, 58) if str(scene_variant) in {"server_rack", "control_panel", "solar_panel_array"} else (65, 75, 84)
    draw.line([(float(x), float(y)) for x, y in [*quad, quad[0]]], fill=outline, width=3)

    if str(scene_variant) in {"compartment_tray", "mailbox_bank"}:
        inner_lip = shrink_polygon(quad, 0.92)
        draw.line(inner_lip + [inner_lip[0]], fill=(236, 241, 239), width=3)
        draw.line(inner_lip + [inner_lip[0]], fill=(88, 103, 104), width=1)
    elif str(scene_variant) in {"window_grid", "solar_panel_array"}:
        inner_frame = shrink_polygon(quad, 0.94)
        draw.line(inner_frame + [inner_frame[0]], fill=(238, 245, 248), width=3)
        draw.line(inner_frame + [inner_frame[0]], fill=(38, 60, 76), width=1)
    elif str(scene_variant) in {"door_bank", "locker_bank"}:
        sill = [quad_point(quad, 0.03, 0.98), quad_point(quad, 0.97, 0.98)]
        draw.line(sill, fill=(91, 74, 54), width=4)
    elif str(scene_variant) == "drawer_pull_panel":
        for v in (0.08, 0.92):
            rail = [quad_point(quad, 0.06, v), quad_point(quad, 0.94, v)]
            draw.line(rail, fill=(235, 221, 188) if v < 0.5 else (118, 93, 62), width=3)
    elif str(scene_variant) == "server_rack":
        for u in (0.035, 0.965):
            rail = [quad_point(quad, u, 0.04), quad_point(quad, u, 0.96)]
            draw.line(rail, fill=(27, 32, 39), width=4)

    for u, v in ((0.04, 0.05), (0.96, 0.05), (0.96, 0.95), (0.04, 0.95)):
        cx, cy = quad_point(quad, u, v)
        radius = 4.0
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(98, 109, 118), outline=(45, 54, 63), width=1)
    return bbox_from_points(quad)


def _fallback_cells(dataset: Mapping[str, Any]) -> List[Dict[str, Any]]:
    count = int(dataset["target_count"])
    element_type = str(dataset["target_element_type"])
    rows, cols = layout_surface_element_grid(count)
    cells: List[Dict[str, Any]] = []
    u_pad = 0.065
    v_pad = 0.075
    cell_gap = 0.016
    for index in range(count):
        row = int(index // cols)
        col = int(index % cols)
        u0 = u_pad + (float(col) / float(cols)) * (1.0 - 2.0 * u_pad)
        u1 = u_pad + (float(col + 1) / float(cols)) * (1.0 - 2.0 * u_pad)
        v0 = v_pad + (float(row) / float(rows)) * (1.0 - 2.0 * v_pad)
        v1 = v_pad + (float(row + 1) / float(rows)) * (1.0 - 2.0 * v_pad)
        cells.append(
            {
                "element_id": f"{element_type}_{index:02d}",
                "cell_id": f"cell_{index:02d}",
                "element_type": element_type,
                "row": row,
                "column": col,
                "u0": u0 + cell_gap,
                "u1": u1 - cell_gap,
                "v0": v0 + cell_gap,
                "v1": v1 - cell_gap,
                "present": True,
                "count_role": "target",
            }
        )
    return cells


def _draw_missing_cell(draw: ImageDraw.ImageDraw, cell_polygon: Sequence[Sequence[float]], scene_variant: str) -> None:
    gap = shrink_polygon(cell_polygon, 0.88)
    draw.polygon(gap, fill=_mix(_panel_fill(str(scene_variant)), (28, 30, 32), 0.58), outline=(35, 38, 42))
    draw.line([(float(x), float(y)) for x, y in [*gap, gap[0]]], fill=(225, 227, 221), width=1)
    a = gap[0]
    c = gap[2]
    b = gap[1]
    d = gap[3]
    draw.line([(a[0], a[1]), (c[0], c[1])], fill=(72, 76, 82), width=2)
    draw.line([(b[0], b[1]), (d[0], d[1])], fill=(72, 76, 82), width=2)


def _draw_element(
    draw: ImageDraw.ImageDraw,
    *,
    quad: Sequence[Sequence[float]],
    scene_variant: str,
    cell_record: Mapping[str, Any],
) -> Tuple[List[float], List[float]]:
    """Draw one element from a normalized cell record and return its witness box.

    Each branch draws only the element visible inside the already projected
    fixture cell. The returned bbox is the verifier witness for the element,
    so state/color decoration may change the drawing but must remain inside the
    element-level visual support.
    """

    element_type = str(cell_record["element_type"])
    u0 = float(cell_record["u0"])
    u1 = float(cell_record["u1"])
    v0 = float(cell_record["v0"])
    v1 = float(cell_record["v1"])
    cell = quad_cell(quad, u0, v0, u1, v1)
    bbox = bbox_from_points(cell)
    center = quad_point(quad, (u0 + u1) * 0.5, (v0 + v1) * 0.5)
    fill = _as_rgb(cell_record.get("fill_rgb"), _mix(_panel_fill(str(scene_variant)), (255, 255, 255), 0.16))
    state = str(cell_record.get("state", "normal"))
    index = int(cell_record.get("flat_index", 0))

    if not bool(cell_record.get("present", True)):
        _draw_missing_cell(draw, cell, str(scene_variant))
        return [round(float(value), 3) for value in bbox], [round(float(center[0]), 3), round(float(center[1]), 3)]

    if element_type in {"tile", "brick", "paver"}:
        shade = fill if cell_record.get("fill_rgb") is not None else _mix(fill, (245, 245, 238), 0.12 + (index % 3) * 0.05)
        grout = (235, 238, 232) if element_type != "brick" else (218, 197, 184)
        outline = (108, 116, 119) if element_type != "brick" else (107, 70, 59)
        draw.polygon(cell, fill=shade, outline=outline)
        draw.line([(float(x), float(y)) for x, y in [*cell, cell[0]]], fill=grout, width=3 if element_type != "paver" else 2)
        if element_type == "brick":
            top = quad_point(cell, 0.18, 0.18)
            bot = quad_point(cell, 0.82, 0.78)
            draw.line([top, bot], fill=_mix(shade, (92, 49, 43), 0.18), width=1)
        if element_type == "paver":
            mid = [quad_point(cell, 0.14, 0.54), quad_point(cell, 0.86, 0.46)]
            draw.line(mid, fill=_mix(shade, (92, 90, 82), 0.18), width=1)
    elif element_type == "hole":
        w = max(6.0, (float(bbox[2]) - float(bbox[0])) * 0.42)
        h = max(5.0, (float(bbox[3]) - float(bbox[1])) * 0.38)
        bbox = [center[0] - w * 0.5, center[1] - h * 0.5, center[0] + w * 0.5, center[1] + h * 0.5]
        draw.ellipse(bbox, fill=(43, 51, 58), outline=(223, 229, 231), width=2)
        draw.ellipse([bbox[0] + w * 0.22, bbox[1] + h * 0.18, bbox[2] - w * 0.18, bbox[3] - h * 0.28], fill=(23, 28, 33))
    elif element_type == "slot":
        w = max(12.0, (float(bbox[2]) - float(bbox[0])) * 0.78)
        h = max(6.0, (float(bbox[3]) - float(bbox[1])) * 0.28)
        bbox = [center[0] - w * 0.5, center[1] - h * 0.5, center[0] + w * 0.5, center[1] + h * 0.5]
        draw.rounded_rectangle(bbox, radius=max(3, int(h * 0.45)), fill=(63, 55, 43), outline=(236, 226, 198), width=2)
        draw.line([(bbox[0] + w * 0.16, center[1]), (bbox[2] - w * 0.16, center[1])], fill=(31, 27, 22), width=2)
    elif element_type == "compartment":
        rim = shrink_polygon(cell, 0.94)
        opening = shrink_polygon(cell, 0.70)
        draw.polygon(rim, fill=fill, outline=(87, 101, 103))
        draw.polygon(opening, fill=_mix(fill, (38, 48, 50), 0.42), outline=(47, 59, 62))
        shadow = shrink_polygon(opening, 0.78)
        draw.polygon(shadow, fill=_mix(fill, (20, 28, 30), 0.58))
        lip = shrink_polygon(cell, 0.80)
        draw.line(lip + [lip[0]], fill=(242, 246, 244), width=2)
        bbox = bbox_from_points(opening)
    elif element_type == "vent":
        w = max(14.0, (float(bbox[2]) - float(bbox[0])) * 0.82)
        h = max(9.0, (float(bbox[3]) - float(bbox[1])) * 0.58)
        bbox = [center[0] - w * 0.5, center[1] - h * 0.5, center[0] + w * 0.5, center[1] + h * 0.5]
        draw.rounded_rectangle(bbox, radius=max(2, int(h * 0.16)), fill=fill, outline=(74, 86, 94), width=2)
        for offset in (0.26, 0.42, 0.58, 0.74):
            y = bbox[1] + h * offset
            draw.line([(bbox[0] + w * 0.12, y), (bbox[2] - w * 0.12, y - h * 0.05)], fill=(57, 69, 78), width=2)
    elif element_type == "window":
        frame = shrink_polygon(cell, 0.86)
        pane_fill = (249, 221, 114) if state == "lit" else fill
        if state == "unlit":
            pane_fill = _mix(fill, (30, 45, 57), 0.52)
        pane = shrink_polygon(cell, 0.70)
        draw.polygon(frame, fill=(236, 242, 244), outline=(58, 82, 98))
        draw.polygon(pane, fill=pane_fill, outline=(62, 100, 124))
        mullion_v = [quad_point(frame, 0.50, 0.08), quad_point(frame, 0.50, 0.92)]
        mullion_h = [quad_point(frame, 0.08, 0.50), quad_point(frame, 0.92, 0.50)]
        draw.line(mullion_v, fill=(238, 244, 246), width=2)
        draw.line(mullion_h, fill=(238, 244, 246), width=2)
        bbox = bbox_from_points(frame)
    elif element_type in {"door", "locker", "mailbox"}:
        face = shrink_polygon(cell, 0.88 if element_type == "door" else 0.92)
        body_fill = fill
        if state == "open":
            draw.polygon(face, fill=_mix(fill, (18, 22, 27), 0.64), outline=(52, 57, 63))
            inner = shrink_polygon(face, 0.70)
            draw.polygon(inner, fill=(34, 39, 45), outline=(102, 110, 118))
        else:
            draw.polygon(face, fill=body_fill, outline=(72, 54, 38) if element_type == "door" else (70, 78, 84))
            inner = shrink_polygon(face, 0.66)
            draw.polygon(inner, outline=_mix(body_fill, (35, 40, 44), 0.30))
        if element_type == "door":
            knob = quad_point(face, 0.78, 0.52)
            knob_radius = max(2.0, min(float(bbox[2]) - float(bbox[0]), float(bbox[3]) - float(bbox[1])) * 0.055)
            knob_bbox = [knob[0] - knob_radius, knob[1] - knob_radius, knob[0] + knob_radius, knob[1] + knob_radius]
            draw.ellipse(knob_bbox, fill=(226, 186, 72), outline=(81, 61, 28), width=1)
            bbox = bbox_union(bbox_from_points(face), knob_bbox)
        elif element_type == "locker":
            for vv in (0.26, 0.34, 0.42):
                a = quad_point(face, 0.18, vv)
                b = quad_point(face, 0.70, vv)
                draw.line([a, b], fill=(62, 72, 80), width=1)
            handle = quad_point(face, 0.82, 0.58)
            draw.rectangle([handle[0] - 2.2, handle[1] - 6.0, handle[0] + 2.2, handle[1] + 6.0], fill=(35, 39, 42))
            bbox = bbox_from_points(face)
        else:
            slot_a = quad_point(face, 0.20, 0.40)
            slot_b = quad_point(face, 0.78, 0.38)
            draw.line([slot_a, slot_b], fill=(63, 62, 53), width=2)
            flag = quad_point(face, 0.84, 0.22)
            draw.rectangle([flag[0] - 3.0, flag[1] - 7.0, flag[0] + 3.0, flag[1] + 7.0], fill=(185, 54, 48))
            bbox = bbox_from_points(face)
    elif element_type == "drawer_pull":
        face = shrink_polygon(cell, 0.92)
        draw.polygon(face, fill=fill, outline=(115, 91, 62))
        pull_w = max(13.0, (float(bbox[2]) - float(bbox[0])) * 0.58)
        pull_h = max(6.0, (float(bbox[3]) - float(bbox[1])) * 0.22)
        pull_bbox = [center[0] - pull_w * 0.5, center[1] - pull_h * 0.5, center[0] + pull_w * 0.5, center[1] + pull_h * 0.5]
        draw.rounded_rectangle(pull_bbox, radius=max(3, int(pull_h * 0.45)), fill=(86, 68, 48), outline=(39, 31, 24), width=2)
        draw.line([(pull_bbox[0] + pull_w * 0.18, center[1] - pull_h * 0.08), (pull_bbox[2] - pull_w * 0.18, center[1] - pull_h * 0.12)], fill=(174, 147, 96), width=1)
        bbox = list(pull_bbox)
    elif element_type == "drive_bay":
        bay = shrink_polygon(cell, 0.88)
        bay_fill = (38, 45, 52)
        if state == "lit":
            bay_fill = _mix(bay_fill, fill, 0.30)
        draw.polygon(bay, fill=bay_fill, outline=(16, 20, 24))
        for vv in (0.28, 0.50, 0.72):
            a = quad_point(bay, 0.14, vv)
            b = quad_point(bay, 0.86, vv)
            draw.line([a, b], fill=(102, 116, 125), width=1)
        led = quad_point(bay, 0.86, 0.28)
        led_rgb = fill if state == "lit" else (72, 80, 82)
        draw.ellipse([led[0] - 3, led[1] - 3, led[0] + 3, led[1] + 3], fill=led_rgb, outline=(18, 22, 24))
        bbox = bbox_from_points(bay)
    elif element_type == "button":
        button = shrink_polygon(cell, 0.76)
        button_bbox = bbox_from_points(button)
        button_fill = _mix(fill, (45, 50, 55), 0.24) if state == "pressed" else fill
        if state == "lit":
            glow = bbox_from_points(shrink_polygon(cell, 0.92))
            draw.ellipse(glow, fill=_mix(fill, (250, 240, 120), 0.35))
        draw.ellipse(button_bbox, fill=button_fill, outline=(28, 32, 37), width=2)
        highlight = [button_bbox[0] + 4, button_bbox[1] + 3, button_bbox[0] + (button_bbox[2] - button_bbox[0]) * 0.52, button_bbox[1] + (button_bbox[3] - button_bbox[1]) * 0.34]
        draw.ellipse(highlight, fill=_mix(button_fill, (255, 255, 255), 0.34))
        bbox = list(button_bbox)
    elif element_type == "solar_panel":
        panel = shrink_polygon(cell, 0.88)
        panel_fill = fill if cell_record.get("fill_rgb") is not None else (35, 76, 126)
        draw.polygon(panel, fill=panel_fill, outline=(18, 30, 42))
        for uu in (0.33, 0.66):
            a = quad_point(panel, uu, 0.10)
            b = quad_point(panel, uu, 0.90)
            draw.line([a, b], fill=(96, 140, 178), width=1)
        for vv in (0.36, 0.68):
            a = quad_point(panel, 0.10, vv)
            b = quad_point(panel, 0.90, vv)
            draw.line([a, b], fill=(96, 140, 178), width=1)
        if state == "cracked":
            crack = [quad_point(panel, 0.20, 0.22), quad_point(panel, 0.44, 0.48), quad_point(panel, 0.36, 0.78), quad_point(panel, 0.72, 0.88)]
            draw.line(crack, fill=(230, 236, 239), width=2)
        bbox = bbox_from_points(panel)
    else:
        raise ValueError(f"unsupported surface element type: {element_type}")

    return [round(float(value), 3) for value in bbox], [round(float(center[0]), 3), round(float(center[1]), 3)]


def _draw_surface_elements(
    draw: ImageDraw.ImageDraw,
    *,
    quad: Sequence[Sequence[float]],
    scene_variant: str,
    cells: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]], Dict[str, List[float]]]:
    entities: List[Dict[str, Any]] = []
    bboxes: Dict[str, List[float]] = {}
    centers: Dict[str, List[float]] = {}
    for cell_record in cells:
        element_id = str(cell_record["element_id"])
        bbox, center = _draw_element(draw, quad=quad, scene_variant=str(scene_variant), cell_record=cell_record)
        bboxes[element_id] = list(bbox)
        centers[element_id] = list(center)
        entities.append(
            {
                "entity_id": str(element_id),
                "entity_type": "three_d_surface_repeated_element",
                "bbox_px": list(bbox),
                "attrs": {
                    "cell_id": str(cell_record.get("cell_id", element_id)),
                    "element_type": str(cell_record.get("element_type")),
                    "scene_variant": str(scene_variant),
                    "row": int(cell_record.get("row", 0)),
                    "column": int(cell_record.get("column", 0)),
                    "present": bool(cell_record.get("present", True)),
                    "color_name": str(cell_record.get("color_name", "")),
                    "state": str(cell_record.get("state", "normal")),
                    "count_role": str(cell_record.get("count_role", "distractor")),
                },
            }
        )
    return entities, bboxes, centers


def render_surface_fixture(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: Any,
) -> RenderedSurfaceFixture:
    """Render a complete fixture panel from scene metadata.

    The renderer consumes finalized cell records from task-owned construction,
    projects them onto one panel, and records entity bboxes/centers from the
    same draw pass used to make the image.
    """

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    scene_variant = str(dataset["scene_variant"])
    quad = fixture_quad(render_params, scene_variant)
    fixture_bbox = _draw_fixture_context(draw, render_params, quad, scene_variant)
    cells = [dict(cell) for cell in dataset.get("surface_cells", _fallback_cells(dataset))]
    element_entities, element_bboxes, element_centers = _draw_surface_elements(
        draw,
        quad=quad,
        scene_variant=scene_variant,
        cells=cells,
    )
    scene_bbox = bbox_union(fixture_bbox, *element_bboxes.values()) if element_bboxes else list(fixture_bbox)
    fixture_entity = {
        "entity_id": "surface_fixture_panel",
        "entity_type": "three_d_surface_fixture",
        "bbox_px": list(fixture_bbox),
        "attrs": {
            "scene_variant": str(scene_variant),
            "surface_world_corners": [list(point) for point in dataset["surface_world_corners"]],
            "surface_screen_corners_px": [list(point) for point in quad],
            "projection_model": "synthetic_perspective_panel_v0",
            "layout_rows": int(dataset.get("layout_rows", 0)),
            "layout_columns": int(dataset.get("layout_columns", 0)),
            "layout_style": str(dataset.get("layout_style", "uniform_grid")),
        },
    }
    return RenderedSurfaceFixture(
        image=image,
        entities=[fixture_entity, *element_entities],
        scene_bbox_px=list(scene_bbox),
        fixture_bbox_px=list(fixture_bbox),
        element_bboxes_px=dict(element_bboxes),
        element_centers_px=dict(element_centers),
    )


__all__ = [
    "RenderedSurfaceFixture",
    "bbox_from_points",
    "bbox_union",
    "fixture_quad",
    "layout_surface_element_grid",
    "quad_cell",
    "quad_point",
    "render_surface_fixture",
    "shrink_polygon",
]
