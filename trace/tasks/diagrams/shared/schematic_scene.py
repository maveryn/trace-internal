"""Annotated schematic renderer shared by diagrams-domain schematic tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_rounded_rect
from .common import draw_diagram_text_in_box, resolve_diagram_panel_geometry, round_diagram_bbox
from .schematic_common import SchematicRenderParams, resolve_schematic_slot_spec


BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class RenderedSchematicScene:
    """Rendered annotated schematic plus traced part and callout geometry."""

    image: Image.Image
    entities: List[Dict[str, object]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    chassis_bbox_px: List[float]
    part_bbox_map: Dict[str, List[float]]
    part_label_bbox_map: Dict[str, List[float]]
    callout_bbox_map: Dict[str, List[float]]
    callout_label_bbox_map: Dict[str, List[float]]
    leader_bbox_map: Dict[str, List[float]]


def _normalize_bbox(container_bbox: BBox, norm_bbox: Sequence[float]) -> BBox:
    """Project one normalized bbox into image coordinates."""

    left, top, right, bottom = [float(value) for value in container_bbox]
    width = float(right - left)
    height = float(bottom - top)
    nx0, ny0, nx1, ny1 = [float(value) for value in norm_bbox]
    return (
        float(left + (nx0 * width)),
        float(top + (ny0 * height)),
        float(left + (nx1 * width)),
        float(top + (ny1 * height)),
    )


def _normalize_point(container_bbox: BBox, norm_point: Sequence[float]) -> tuple[float, float]:
    """Project one normalized point into image coordinates."""

    left, top, right, bottom = [float(value) for value in container_bbox]
    width = float(right - left)
    height = float(bottom - top)
    nx, ny = [float(value) for value in norm_point]
    return (float(left + (nx * width)), float(top + (ny * height)))


def _circle_bbox(center: tuple[float, float], *, diameter_px: float) -> BBox:
    """Return one circle bbox from its center and diameter."""

    cx, cy = float(center[0]), float(center[1])
    radius = 0.5 * float(diameter_px)
    return (float(cx - radius), float(cy - radius), float(cx + radius), float(cy + radius))


def _bbox_center(bbox: Sequence[float]) -> tuple[float, float]:
    """Return the center point of one bbox."""

    left, top, right, bottom = [float(value) for value in bbox]
    return (float(0.5 * (left + right)), float(0.5 * (top + bottom)))


def _edge_point_toward(bbox: Sequence[float], target: tuple[float, float]) -> tuple[float, float]:
    """Return the point where the ray toward `target` exits the bbox."""

    left, top, right, bottom = [float(value) for value in bbox]
    cx, cy = _bbox_center(bbox)
    tx, ty = float(target[0]), float(target[1])
    dx = float(tx - cx)
    dy = float(ty - cy)
    if math.isclose(dx, 0.0, abs_tol=1e-6) and math.isclose(dy, 0.0, abs_tol=1e-6):
        return (float(cx), float(cy))
    candidates: list[tuple[float, float]] = []
    if not math.isclose(dx, 0.0, abs_tol=1e-6):
        for x_edge in (float(left), float(right)):
            t = float((x_edge - cx) / dx)
            if float(t) <= 0.0:
                continue
            y_edge = float(cy + (t * dy))
            if float(top) - 1e-6 <= float(y_edge) <= float(bottom) + 1e-6:
                candidates.append((t, x_edge, y_edge))
    if not math.isclose(dy, 0.0, abs_tol=1e-6):
        for y_edge in (float(top), float(bottom)):
            t = float((y_edge - cy) / dy)
            if float(t) <= 0.0:
                continue
            x_edge = float(cx + (t * dx))
            if float(left) - 1e-6 <= float(x_edge) <= float(right) + 1e-6:
                candidates.append((t, x_edge, y_edge))
    if not candidates:
        return (float(cx), float(cy))
    _, edge_x, edge_y = min(candidates, key=lambda item: float(item[0]))
    return (float(edge_x), float(edge_y))


def _circle_edge_toward(circle_bbox: Sequence[float], target: tuple[float, float]) -> tuple[float, float]:
    """Return the circle-edge point toward `target`."""

    cx, cy = _bbox_center(circle_bbox)
    tx, ty = float(target[0]), float(target[1])
    dx = float(tx - cx)
    dy = float(ty - cy)
    length = math.hypot(dx, dy)
    if float(length) <= 1e-6:
        return (float(cx), float(cy))
    radius = 0.5 * float(circle_bbox[2] - circle_bbox[0])
    return (float(cx + (radius * dx / length)), float(cy + (radius * dy / length)))


def _leader_bbox(start: tuple[float, float], end: tuple[float, float], *, pad_px: float) -> List[float]:
    """Return one conservative bbox covering a leader line."""

    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    return round_diagram_bbox(
        (
            float(min(sx, ex) - pad_px),
            float(min(sy, ey) - pad_px),
            float(max(sx, ex) + pad_px),
            float(max(sy, ey) + pad_px),
        )
    )


def _hexagon_points(bbox: Sequence[float]) -> list[tuple[float, float]]:
    """Return one horizontally oriented hexagon inside the bbox."""

    left, top, right, bottom = [float(value) for value in bbox]
    width = float(right - left)
    inset = 0.18 * float(width)
    cy = float(0.5 * (top + bottom))
    return [
        (float(left + inset), float(top)),
        (float(right - inset), float(top)),
        (float(right), float(cy)),
        (float(right - inset), float(bottom)),
        (float(left + inset), float(bottom)),
        (float(left), float(cy)),
    ]


def _draw_part_shape(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    shape_kind: str,
    fill_rgb: Sequence[int],
    border_rgb: Sequence[int],
    border_width_px: int,
    corner_radius_px: int,
) -> None:
    """Draw one schematic part with the requested primitive shape."""

    fill = tuple(int(value) for value in fill_rgb)
    outline = tuple(int(value) for value in border_rgb)
    width = max(1, int(border_width_px))
    if str(shape_kind) == "ellipse":
        draw.ellipse(bbox, fill=fill, outline=outline, width=width)
        return
    if str(shape_kind) == "hexagon":
        points = _hexagon_points(bbox)
        draw.polygon(points, fill=fill, outline=outline)
        if width > 1:
            for offset in range(1, width):
                inset_bbox = (
                    float(bbox[0] + offset),
                    float(bbox[1] + offset),
                    float(bbox[2] - offset),
                    float(bbox[3] - offset),
                )
                draw.polygon(_hexagon_points(inset_bbox), outline=outline)
        return
    radius = int(corner_radius_px)
    if str(shape_kind) == "capsule":
        radius = int(0.5 * (float(bbox[3]) - float(bbox[1])))
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in bbox),
        radius=max(8, int(radius)),
        fill=fill,
        outline=outline,
        width=width,
    )


def render_schematic_scene(
    background: Image.Image,
    *,
    scene_title: str,
    scene_variant: str,
    part_specs: Sequence[Mapping[str, object]],
    render_params: SchematicRenderParams,
) -> RenderedSchematicScene:
    """Render one annotated schematic with external callouts and local part labels."""

    del scene_variant
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    entities: List[Dict[str, object]] = []
    part_bbox_map: Dict[str, List[float]] = {}
    part_label_bbox_map: Dict[str, List[float]] = {}
    callout_bbox_map: Dict[str, List[float]] = {}
    callout_label_bbox_map: Dict[str, List[float]] = {}
    leader_bbox_map: Dict[str, List[float]] = {}

    panel_bbox, title_bbox, content_bbox = resolve_diagram_panel_geometry(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        outer_margin_px=int(render_params.outer_margin_px),
        title_band_height_px=int(render_params.title_band_height_px),
        panel_padding_px=int(render_params.panel_padding_px),
    )
    draw_rounded_rect(
        draw,
        panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=2,
    )
    title_text_bbox = draw_diagram_text_in_box(
        draw,
        bbox=title_bbox,
        text=str(scene_title),
        font_size_px=int(render_params.title_font_size_px),
        bold=True,
        fill=render_params.title_color_rgb,
        stroke_fill=render_params.panel_fill_rgb,
        padding_px=12,
    )
    entities.append(
        {
            "entity_id": "diagram_panel",
            "entity_type": "diagram_panel",
            "bbox_xyxy": round_diagram_bbox(panel_bbox),
        }
    )
    entities.append(
        {
            "entity_id": "diagram_title",
            "entity_type": "diagram_title",
            "bbox_xyxy": list(title_text_bbox),
            "text": str(scene_title),
        }
    )

    content_left, content_top, content_right, content_bottom = [float(value) for value in content_bbox]
    content_width = float(content_right - content_left)
    content_height = float(content_bottom - content_top)
    chassis_bbox = (
        float(content_left + (0.12 * content_width)),
        float(content_top + (0.12 * content_height)),
        float(content_right - (0.12 * content_width)),
        float(content_top + (0.80 * content_height)),
    )
    draw_rounded_rect(
        draw,
        chassis_bbox,
        radius=int(render_params.chassis_corner_radius_px),
        fill=render_params.chassis_fill_rgb,
        outline=render_params.chassis_border_rgb,
        width=int(render_params.chassis_border_width_px),
    )
    entities.append(
        {
            "entity_id": "schematic_chassis",
            "entity_type": "diagram_schematic_chassis",
            "bbox_xyxy": round_diagram_bbox(chassis_bbox),
        }
    )

    chassis_left, chassis_top, chassis_right, chassis_bottom = [float(value) for value in chassis_bbox]
    bus_x = float(0.5 * (chassis_left + chassis_right))
    bus_y = float(chassis_top + (0.48 * (chassis_bottom - chassis_top)))
    bus_top = float(chassis_top + 46.0)
    bus_bottom = float(chassis_bottom - 38.0)
    draw.line(
        [(bus_x, bus_top), (bus_x, bus_bottom)],
        fill=tuple(int(value) for value in render_params.bus_color_rgb),
        width=max(1, int(render_params.bus_width_px)),
    )
    draw.line(
        [(chassis_left + 98.0, bus_y), (chassis_right - 98.0, bus_y)],
        fill=tuple(int(value) for value in render_params.bus_color_rgb),
        width=max(1, int(render_params.bus_width_px)),
    )
    entities.extend(
        [
            {
                "entity_id": "schematic_bus_vertical",
                "entity_type": "diagram_schematic_bus",
                "bbox_xyxy": _leader_bbox((bus_x, bus_top), (bus_x, bus_bottom), pad_px=3.0),
            },
            {
                "entity_id": "schematic_bus_horizontal",
                "entity_type": "diagram_schematic_bus",
                "bbox_xyxy": _leader_bbox((chassis_left + 98.0, bus_y), (chassis_right - 98.0, bus_y), pad_px=3.0),
            },
        ]
    )

    layout_records: list[dict[str, object]] = []
    for part_spec in part_specs:
        slot_spec = resolve_schematic_slot_spec(str(part_spec["slot_id"]))
        part_box = _normalize_bbox(chassis_bbox, slot_spec["part_bbox_norm"])
        callout_center = _normalize_point(content_bbox, slot_spec["callout_center_norm"])
        callout_box = _circle_bbox(callout_center, diameter_px=float(render_params.callout_diameter_px))
        layout_records.append(
            {
                "part_spec": dict(part_spec),
                "part_box": part_box,
                "callout_box": callout_box,
                "callout_center": callout_center,
            }
        )

    for record in layout_records:
        part_box = record["part_box"]
        callout_box = record["callout_box"]
        callout_center = record["callout_center"]
        part_center = _bbox_center(part_box)
        line_start = _edge_point_toward(part_box, callout_center)
        line_end = _circle_edge_toward(callout_box, part_center)
        draw.line(
            [line_start, line_end],
            fill=tuple(int(value) for value in render_params.leader_color_rgb),
            width=max(1, int(render_params.leader_width_px)),
        )
        endpoint_radius = 4.5
        draw.ellipse(
            (
                float(line_start[0] - endpoint_radius),
                float(line_start[1] - endpoint_radius),
                float(line_start[0] + endpoint_radius),
                float(line_start[1] + endpoint_radius),
            ),
            fill=tuple(int(value) for value in render_params.leader_color_rgb),
        )
        part_spec = record["part_spec"]
        leader_bbox_id = str(part_spec["leader_bbox_id"])
        leader_bbox_map[leader_bbox_id] = _leader_bbox(line_start, line_end, pad_px=float(render_params.leader_width_px))
        entities.append(
            {
                "entity_id": leader_bbox_id,
                "entity_type": "diagram_callout_leader",
                "bbox_xyxy": list(leader_bbox_map[leader_bbox_id]),
                "part_id": str(part_spec["part_id"]),
                "callout_id": str(part_spec["callout_id"]),
            }
        )

    for record in layout_records:
        part_spec = record["part_spec"]
        part_box = record["part_box"]
        highlighted = bool(part_spec["highlighted"])
        fill_rgb = (
            render_params.highlight_fill_rgb
            if highlighted
            else tuple(int(value) for value in part_spec["fill_rgb"])
        )
        border_rgb = render_params.highlight_border_rgb if highlighted else render_params.part_border_rgb
        border_width = int(render_params.part_border_width_px) + (2 if highlighted else 0)
        _draw_part_shape(
            draw,
            bbox=part_box,
            shape_kind=str(part_spec["shape_kind"]),
            fill_rgb=fill_rgb,
            border_rgb=border_rgb,
            border_width_px=int(border_width),
            corner_radius_px=int(render_params.part_corner_radius_px),
        )
        part_bbox_id = str(part_spec["part_bbox_id"])
        part_bbox_map[part_bbox_id] = round_diagram_bbox(part_box)
        label_bbox = draw_diagram_text_in_box(
            draw,
            bbox=part_box,
            text=str(part_spec["part_label"]),
            font_size_px=int(render_params.part_label_font_size_px),
            bold=True,
            fill=render_params.part_label_color_rgb,
            stroke_fill=render_params.part_label_stroke_rgb,
            padding_px=8,
        )
        part_label_bbox_id = str(part_spec["part_label_bbox_id"])
        part_label_bbox_map[part_label_bbox_id] = list(label_bbox)
        entities.append(
            {
                "entity_id": str(part_spec["part_id"]),
                "entity_type": "diagram_schematic_part",
                "bbox_xyxy": list(part_bbox_map[part_bbox_id]),
                "text": str(part_spec["part_label"]),
                "shape_kind": str(part_spec["shape_kind"]),
                "callout_label": str(part_spec["callout_label"]),
                "highlighted": bool(highlighted),
            }
        )
        entities.append(
            {
                "entity_id": part_label_bbox_id,
                "entity_type": "diagram_schematic_part_label",
                "bbox_xyxy": list(label_bbox),
                "text": str(part_spec["part_label"]),
                "part_id": str(part_spec["part_id"]),
            }
        )

    for record in layout_records:
        part_spec = record["part_spec"]
        callout_box = record["callout_box"]
        draw.ellipse(
            callout_box,
            fill=tuple(int(value) for value in render_params.callout_fill_rgb),
            outline=tuple(int(value) for value in render_params.callout_border_rgb),
            width=max(1, int(render_params.callout_border_width_px)),
        )
        callout_bbox_id = str(part_spec["callout_bbox_id"])
        callout_bbox_map[callout_bbox_id] = round_diagram_bbox(callout_box)
        label_bbox = draw_diagram_text_in_box(
            draw,
            bbox=callout_box,
            text=str(part_spec["callout_label"]),
            font_size_px=int(render_params.callout_font_size_px),
            bold=True,
            fill=render_params.callout_text_rgb,
            stroke_fill=render_params.callout_fill_rgb,
            padding_px=4,
        )
        callout_label_bbox_id = str(part_spec["callout_label_bbox_id"])
        callout_label_bbox_map[callout_label_bbox_id] = list(label_bbox)
        entities.append(
            {
                "entity_id": str(part_spec["callout_id"]),
                "entity_type": "diagram_schematic_callout",
                "bbox_xyxy": list(callout_bbox_map[callout_bbox_id]),
                "text": str(part_spec["callout_label"]),
                "part_id": str(part_spec["part_id"]),
            }
        )
        entities.append(
            {
                "entity_id": callout_label_bbox_id,
                "entity_type": "diagram_schematic_callout_label",
                "bbox_xyxy": list(label_bbox),
                "text": str(part_spec["callout_label"]),
                "callout_id": str(part_spec["callout_id"]),
            }
        )

    return RenderedSchematicScene(
        image=image.convert("RGB"),
        entities=entities,
        panel_bbox_px=round_diagram_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        chassis_bbox_px=round_diagram_bbox(chassis_bbox),
        part_bbox_map=part_bbox_map,
        part_label_bbox_map=part_label_bbox_map,
        callout_bbox_map=callout_bbox_map,
        callout_label_bbox_map=callout_label_bbox_map,
        leader_bbox_map=leader_bbox_map,
    )


__all__ = ["RenderedSchematicScene", "render_schematic_scene"]
