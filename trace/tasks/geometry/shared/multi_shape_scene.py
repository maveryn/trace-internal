"""Shared mixed-shape scene helpers for geometry tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from PIL import ImageDraw

from ...shared.geometry_primitives import Point
from ...shared.text_rendering import draw_text_centered, load_font, resolve_text_label_center
from .conic_geometry import draw_circle_outline, draw_ellipse_outline
from .graph_rendering import scale_point
from .shape_style import GeometryShapeStyle


@dataclass(frozen=True)
class MixedShapeSceneObject:
    """One labeled mixed-shape object rendered in a multi-object scene."""

    label: str
    shape_kind: str
    center: Point
    polygon_vertices: Tuple[Point, ...] = ()
    circle_radius_px: float | None = None
    ellipse_radius_x_px: float | None = None
    ellipse_radius_y_px: float | None = None


def _object_bounds(scaled: dict[str, object]) -> Tuple[float, float, float, float]:
    """Return one conservative bounding box for a scaled mixed-shape object."""

    polygon = list(scaled.get("polygon_vertices", []))
    if polygon:
        min_x = min(float(point[0]) for point in polygon)
        max_x = max(float(point[0]) for point in polygon)
        min_y = min(float(point[1]) for point in polygon)
        max_y = max(float(point[1]) for point in polygon)
        return (float(min_x), float(min_y), float(max_x), float(max_y))
    center = tuple(scaled["center"])  # type: ignore[assignment]
    if scaled.get("circle_radius_px") is not None:
        radius = float(scaled["circle_radius_px"])
        return (
            float(center[0]) - float(radius),
            float(center[1]) - float(radius),
            float(center[0]) + float(radius),
            float(center[1]) + float(radius),
        )
    radius_x = float(scaled.get("ellipse_radius_x_px") or 0.0)
    radius_y = float(scaled.get("ellipse_radius_y_px") or 0.0)
    return (
        float(center[0]) - float(radius_x),
        float(center[1]) - float(radius_y),
        float(center[0]) + float(radius_x),
        float(center[1]) + float(radius_y),
    )


def draw_mixed_shape_objects(
    draw: ImageDraw.ImageDraw,
    *,
    objects: Sequence[MixedShapeSceneObject],
    scene_scale: int,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    render_canvas_size: int,
    shape_style: GeometryShapeStyle,
    draw_object_labels: bool = True,
) -> Dict[str, List[float]]:
    """Draw mixed geometry objects plus object labels and return label centers."""

    scaled_objects = []
    for obj in objects:
        scaled_objects.append(
            {
                "label": str(obj.label),
                "shape_kind": str(obj.shape_kind),
                "center": scale_point(obj.center, int(scene_scale)),
                "polygon_vertices": [scale_point(point, int(scene_scale)) for point in obj.polygon_vertices],
                "circle_radius_px": (
                    None if obj.circle_radius_px is None else float(obj.circle_radius_px) * float(scene_scale)
                ),
                "ellipse_radius_x_px": (
                    None if obj.ellipse_radius_x_px is None else float(obj.ellipse_radius_x_px) * float(scene_scale)
                ),
                "ellipse_radius_y_px": (
                    None if obj.ellipse_radius_y_px is None else float(obj.ellipse_radius_y_px) * float(scene_scale)
                ),
            }
        )

    blocked_segments: List[Tuple[Point, Point]] = []
    line_color = tuple(int(value) for value in shape_style.line_color)
    for scaled in scaled_objects:
        polygon = list(scaled["polygon_vertices"])
        if polygon:
            draw.line([*polygon, polygon[0]], fill=line_color, width=max(1, int(line_width)), joint="curve")
            for index in range(len(polygon)):
                point_a = polygon[index]
                point_b = polygon[(index + 1) % len(polygon)]
                blocked_segments.append(
                    ((float(point_a[0]), float(point_a[1])), (float(point_b[0]), float(point_b[1])))
                )
            continue
        center = tuple(scaled["center"])  # type: ignore[assignment]
        if scaled.get("circle_radius_px") is not None:
            draw_circle_outline(
                draw,
                center=(float(center[0]), float(center[1])),
                radius_px=float(scaled["circle_radius_px"]),
                line_color=line_color,
                line_width=max(1, int(line_width)),
            )
            continue
        draw_ellipse_outline(
            draw,
            center=(float(center[0]), float(center[1])),
            semi_axis_x_px=int(round(float(scaled["ellipse_radius_x_px"] or 0.0))),
            semi_axis_y_px=int(round(float(scaled["ellipse_radius_y_px"] or 0.0))),
            line_color=line_color,
            line_width=max(1, int(line_width)),
        )

    if not bool(draw_object_labels):
        return {}

    font = load_font(int(label_font_size_px), bold=True)
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    label_centers: Dict[str, List[float]] = {}
    for scaled in scaled_objects:
        min_x, min_y, max_x, max_y = _object_bounds(scaled)
        center = tuple(scaled["center"])  # type: ignore[assignment]
        direction = (
            float(center[0]) - (0.5 * float(render_canvas_size)),
            float(center[1]) - (0.5 * float(render_canvas_size)),
        )
        outward_offset = max(
            float(object_label_offset_px) * float(scene_scale),
            0.58 * max(float(max_x - min_x), float(max_y - min_y)),
        )
        label_center, label_bbox = resolve_text_label_center(
            draw,
            text=str(scaled["label"]),
            anchor=(float(center[0]), float(center[1])),
            base_direction=direction,
            offset_px=float(outward_offset),
            font=font,
            blocked_segments=blocked_segments,
            occupied_boxes=occupied_boxes,
            stroke_width=int(label_stroke_width),
            line_clearance_px=max(6.0, 1.2 * float(max(1, int(line_width)))),
            canvas_size=int(render_canvas_size),
        )
        draw_text_centered(
            draw,
            text=str(scaled["label"]),
            center=(float(label_center[0]), float(label_center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(label_stroke_width),
        )
        occupied_boxes.append(label_bbox)
        label_centers[str(scaled["label"])] = [
            float(label_center[0]) / float(max(1, int(scene_scale))),
            float(label_center[1]) / float(max(1, int(scene_scale))),
        ]
    return label_centers


__all__ = [
    "MixedShapeSceneObject",
    "draw_mixed_shape_objects",
]
