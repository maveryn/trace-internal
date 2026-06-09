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


def layout_surface_element_grid(count: int) -> Tuple[int, int]:
    cols = max(2, int(math.ceil(math.sqrt(float(count) * 1.35))))
    rows = int(math.ceil(float(count) / float(cols)))
    return int(rows), int(cols)


def fixture_quad(render_params: Any, scene_variant: str) -> List[Tuple[float, float]]:
    width = float(render_params.canvas_width)
    height = float(render_params.canvas_height)
    if str(scene_variant) == "wall_tile_panel":
        return [
            (width * 0.20, height * 0.18),
            (width * 0.83, height * 0.12),
            (width * 0.78, height * 0.74),
            (width * 0.16, height * 0.80),
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


def _draw_fixture_context(draw: ImageDraw.ImageDraw, render_params: Any, quad: Sequence[Sequence[float]], scene_variant: str) -> List[float]:
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    floor_y = int(height * 0.83)
    draw.polygon([(0, floor_y), (width, int(height * 0.70)), (width, height), (0, height)], fill=(221, 226, 224))
    draw.line([(0, floor_y), (width, int(height * 0.70))], fill=(160, 166, 168), width=2)
    shadow = [(float(x) + 12.0, float(y) + 16.0) for x, y in quad]
    draw.polygon(shadow, fill=(171, 178, 181))
    panel_fill = {
        "wall_tile_panel": (226, 229, 224),
        "perforated_panel": (184, 193, 198),
        "slot_board": (200, 181, 142),
        "compartment_tray": (197, 207, 205),
        "vent_panel": (198, 205, 207),
        "window_grid": (184, 205, 219),
        "door_bank": (183, 162, 125),
        "drawer_pull_panel": (202, 188, 162),
    }.get(str(scene_variant), (218, 224, 226))
    draw.polygon([(float(x), float(y)) for x, y in quad], fill=panel_fill)
    draw.line([(float(x), float(y)) for x, y in [*quad, quad[0]]], fill=(65, 75, 84), width=3)
    if str(scene_variant) == "compartment_tray":
        inner_lip = shrink_polygon(quad, 0.92)
        draw.line(inner_lip + [inner_lip[0]], fill=(236, 241, 239), width=3)
        draw.line(inner_lip + [inner_lip[0]], fill=(88, 103, 104), width=1)
    elif str(scene_variant) == "window_grid":
        inner_frame = shrink_polygon(quad, 0.94)
        draw.line(inner_frame + [inner_frame[0]], fill=(238, 245, 248), width=4)
        draw.line(inner_frame + [inner_frame[0]], fill=(62, 86, 101), width=1)
    elif str(scene_variant) == "door_bank":
        sill = [quad_point(quad, 0.03, 0.98), quad_point(quad, 0.97, 0.98)]
        draw.line(sill, fill=(91, 74, 54), width=4)
    elif str(scene_variant) == "drawer_pull_panel":
        rail_a = [quad_point(quad, 0.06, 0.08), quad_point(quad, 0.94, 0.08)]
        rail_b = [quad_point(quad, 0.06, 0.92), quad_point(quad, 0.94, 0.92)]
        draw.line(rail_a, fill=(235, 221, 188), width=3)
        draw.line(rail_b, fill=(118, 93, 62), width=2)
    for u, v in ((0.04, 0.05), (0.96, 0.05), (0.96, 0.95), (0.04, 0.95)):
        cx, cy = quad_point(quad, u, v)
        radius = 4.0
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(98, 109, 118), outline=(45, 54, 63), width=1)
    return bbox_from_points(quad)


def _draw_surface_elements(
    draw: ImageDraw.ImageDraw,
    *,
    quad: Sequence[Sequence[float]],
    scene_variant: str,
    element_type: str,
    count: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]], Dict[str, List[float]]]:
    rows, cols = layout_surface_element_grid(int(count))
    u_pad = 0.065
    v_pad = 0.075
    cell_gap = 0.016
    entities: List[Dict[str, Any]] = []
    bboxes: Dict[str, List[float]] = {}
    centers: Dict[str, List[float]] = {}
    for index in range(int(count)):
        row = int(index // cols)
        col = int(index % cols)
        u0 = u_pad + (float(col) / float(cols)) * (1.0 - 2.0 * u_pad)
        u1 = u_pad + (float(col + 1) / float(cols)) * (1.0 - 2.0 * u_pad)
        v0 = v_pad + (float(row) / float(rows)) * (1.0 - 2.0 * v_pad)
        v1 = v_pad + (float(row + 1) / float(rows)) * (1.0 - 2.0 * v_pad)
        u0 += cell_gap
        u1 -= cell_gap
        v0 += cell_gap
        v1 -= cell_gap
        cell = quad_cell(quad, u0, v0, u1, v1)
        bbox = bbox_from_points(cell)
        center = quad_point(quad, (u0 + u1) * 0.5, (v0 + v1) * 0.5)
        element_id = f"{str(element_type)}_{index:02d}"
        if str(element_type) == "tile":
            shade = 238 - (index % 4) * 5
            draw.polygon(cell, fill=(shade, shade + 1, max(210, shade - 8)), outline=(111, 125, 132))
            grout = [(float(x), float(y)) for x, y in [*cell, cell[0]]]
            draw.line(grout, fill=(236, 240, 238), width=3)
            draw.line(grout, fill=(118, 132, 140), width=1)
        elif str(element_type) == "hole":
            w = max(6.0, (float(bbox[2]) - float(bbox[0])) * 0.42)
            h = max(5.0, (float(bbox[3]) - float(bbox[1])) * 0.38)
            bbox = [center[0] - w * 0.5, center[1] - h * 0.5, center[0] + w * 0.5, center[1] + h * 0.5]
            draw.ellipse(bbox, fill=(43, 51, 58), outline=(223, 229, 231), width=2)
            draw.ellipse([bbox[0] + w * 0.22, bbox[1] + h * 0.18, bbox[2] - w * 0.18, bbox[3] - h * 0.28], fill=(23, 28, 33))
        elif str(element_type) == "slot":
            w = max(12.0, (float(bbox[2]) - float(bbox[0])) * 0.78)
            h = max(6.0, (float(bbox[3]) - float(bbox[1])) * 0.28)
            bbox = [center[0] - w * 0.5, center[1] - h * 0.5, center[0] + w * 0.5, center[1] + h * 0.5]
            draw.rounded_rectangle(bbox, radius=max(3, int(h * 0.45)), fill=(63, 55, 43), outline=(236, 226, 198), width=2)
            draw.line([(bbox[0] + w * 0.16, center[1]), (bbox[2] - w * 0.16, center[1])], fill=(31, 27, 22), width=2)
        elif str(element_type) == "compartment":
            rim = shrink_polygon(cell, 0.94)
            opening = shrink_polygon(cell, 0.70)
            draw.polygon(rim, fill=(221, 228, 225), outline=(87, 101, 103))
            draw.polygon(opening, fill=(123, 139, 139), outline=(47, 59, 62))
            shadow = shrink_polygon(opening, 0.78)
            draw.polygon(shadow, fill=(82, 96, 99))
            lip = shrink_polygon(cell, 0.80)
            draw.line(lip + [lip[0]], fill=(242, 246, 244), width=2)
            bbox = bbox_from_points(opening)
        elif str(element_type) == "vent":
            w = max(14.0, (float(bbox[2]) - float(bbox[0])) * 0.82)
            h = max(9.0, (float(bbox[3]) - float(bbox[1])) * 0.58)
            bbox = [center[0] - w * 0.5, center[1] - h * 0.5, center[0] + w * 0.5, center[1] + h * 0.5]
            draw.rounded_rectangle(bbox, radius=max(2, int(h * 0.16)), fill=(225, 230, 231), outline=(74, 86, 94), width=2)
            for offset in (0.26, 0.42, 0.58, 0.74):
                y = bbox[1] + h * offset
                draw.line([(bbox[0] + w * 0.12, y), (bbox[2] - w * 0.12, y - h * 0.05)], fill=(57, 69, 78), width=2)
        elif str(element_type) == "window":
            frame = shrink_polygon(cell, 0.86)
            pane = shrink_polygon(cell, 0.70)
            draw.polygon(frame, fill=(236, 242, 244), outline=(58, 82, 98))
            draw.polygon(pane, fill=(130, 178, 205), outline=(62, 100, 124))
            mullion_v = [quad_point(frame, 0.50, 0.08), quad_point(frame, 0.50, 0.92)]
            mullion_h = [quad_point(frame, 0.08, 0.50), quad_point(frame, 0.92, 0.50)]
            draw.line(mullion_v, fill=(238, 244, 246), width=2)
            draw.line(mullion_h, fill=(238, 244, 246), width=2)
            shine = [quad_point(frame, 0.20, 0.22), quad_point(frame, 0.42, 0.12)]
            draw.line(shine, fill=(229, 247, 253), width=2)
            bbox = bbox_from_points(frame)
        elif str(element_type) == "door":
            door = shrink_polygon(cell, 0.88)
            inner = shrink_polygon(cell, 0.62)
            draw.polygon(door, fill=(163, 115, 67), outline=(72, 54, 38))
            draw.polygon(inner, outline=(104, 75, 47))
            knob = quad_point(door, 0.78, 0.52)
            knob_radius = max(2.0, min(float(bbox[2]) - float(bbox[0]), float(bbox[3]) - float(bbox[1])) * 0.055)
            knob_bbox = [
                knob[0] - knob_radius,
                knob[1] - knob_radius,
                knob[0] + knob_radius,
                knob[1] + knob_radius,
            ]
            draw.ellipse(knob_bbox, fill=(226, 186, 72), outline=(81, 61, 28), width=1)
            bbox = bbox_union(bbox_from_points(door), knob_bbox)
        elif str(element_type) == "drawer_pull":
            face = shrink_polygon(cell, 0.92)
            draw.polygon(face, fill=(214, 196, 156), outline=(115, 91, 62))
            pull_w = max(13.0, (float(bbox[2]) - float(bbox[0])) * 0.58)
            pull_h = max(6.0, (float(bbox[3]) - float(bbox[1])) * 0.22)
            pull_bbox = [
                center[0] - pull_w * 0.5,
                center[1] - pull_h * 0.5,
                center[0] + pull_w * 0.5,
                center[1] + pull_h * 0.5,
            ]
            draw.rounded_rectangle(pull_bbox, radius=max(3, int(pull_h * 0.45)), fill=(86, 68, 48), outline=(39, 31, 24), width=2)
            highlight = [(pull_bbox[0] + pull_w * 0.18, center[1] - pull_h * 0.08), (pull_bbox[2] - pull_w * 0.18, center[1] - pull_h * 0.12)]
            draw.line(highlight, fill=(174, 147, 96), width=1)
            bbox = list(pull_bbox)
        else:
            raise ValueError(f"unsupported surface element type: {element_type}")
        bbox = [round(float(value), 3) for value in bbox]
        bboxes[element_id] = list(bbox)
        centers[element_id] = [round(float(center[0]), 3), round(float(center[1]), 3)]
        entities.append(
            {
                "entity_id": str(element_id),
                "entity_type": "three_d_surface_repeated_element",
                "bbox_px": list(bbox),
                "attrs": {
                    "element_type": str(element_type),
                    "scene_variant": str(scene_variant),
                    "row": int(row),
                    "column": int(col),
                    "count_role": "target",
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
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    scene_variant = str(dataset["scene_variant"])
    element_type = str(dataset["target_element_type"])
    quad = fixture_quad(render_params, scene_variant)
    fixture_bbox = _draw_fixture_context(draw, render_params, quad, scene_variant)
    element_entities, element_bboxes, element_centers = _draw_surface_elements(
        draw,
        quad=quad,
        scene_variant=scene_variant,
        element_type=element_type,
        count=int(dataset["target_count"]),
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


__all__ = ["RenderedSurfaceFixture", "layout_surface_element_grid", "render_surface_fixture"]
