"""Shared multi-angle scene helpers for geometry tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...shared.geometry_primitives import Point, point_inside_square_canvas
from ...shared.text_rendering import (
    draw_text_centered,
    load_font,
    resolve_text_label_center,
)
from .graph_paper import offset_point_by_grid_vector
from .graph_rendering import graph_units_to_pixel, scale_point
from .shape_style import GeometryShapeStyle
from .single_object_scene import GraphSceneContext

Vector = Tuple[int, int]


@dataclass(frozen=True)
class AngleSceneObject:
    """One labeled angle object in a multi-object scene."""

    label: str
    vertex: Point
    point_a: Point
    point_b: Point
    target_angle_degrees: int
    raw_angle_degrees: float


def screen_bisector_direction(obj: AngleSceneObject) -> Point:
    """Return one stable screen-space bisector direction for object-label placement."""

    vec_a = (float(obj.point_a[0]) - float(obj.vertex[0]), float(obj.point_a[1]) - float(obj.vertex[1]))
    vec_b = (float(obj.point_b[0]) - float(obj.vertex[0]), float(obj.point_b[1]) - float(obj.vertex[1]))
    mag_a = math.hypot(float(vec_a[0]), float(vec_a[1]))
    mag_b = math.hypot(float(vec_b[0]), float(vec_b[1]))
    if mag_a <= 1e-9 or mag_b <= 1e-9:
        return (1.0, -1.0)
    bisector = (
        (float(vec_a[0]) / float(mag_a)) + (float(vec_b[0]) / float(mag_b)),
        (float(vec_a[1]) / float(mag_a)) + (float(vec_b[1]) / float(mag_b)),
    )
    if math.hypot(float(bisector[0]), float(bisector[1])) <= 1e-9:
        return (float(-(vec_a[1]) / float(mag_a)), float(vec_a[0] / float(mag_a)))
    return bisector


def sample_angle_objects_for_targets(
    rng,
    *,
    labels: Sequence[str],
    target_angles: Sequence[int],
    slot_units: Sequence[Tuple[int, int]],
    context: GraphSceneContext,
    angle_catalog: Mapping[int, Sequence[Tuple[Vector, Vector, float]]],
) -> Tuple[AngleSceneObject, ...]:
    """Construct one angle object per label/target-angle pair on provided slots."""

    if not (len(labels) == len(target_angles) == len(slot_units)):
        raise ValueError("labels, target_angles, and slot_units must have the same length")

    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    endpoint_padding_px = max(3.0, 0.75 * float(context.graph_spacing) * float(context.scene_scale))
    objects: List[AngleSceneObject] = []
    for label, target_angle, slot in zip(labels, target_angles, slot_units):
        pairs = list(angle_catalog[int(target_angle)])
        rng.shuffle(pairs)
        selected_object: AngleSceneObject | None = None
        vertex = graph_units_to_pixel(
            (int(slot[0]), int(slot[1])),
            origin=context.graph_origin,
            spacing=int(context.graph_spacing),
        )
        for vector_a, vector_b, raw_angle in pairs:
            if bool(rng.randint(0, 1)):
                vector_a, vector_b = vector_b, vector_a
            point_a = offset_point_by_grid_vector(
                vertex,
                (int(vector_a[0]), int(vector_a[1])),
                spacing=int(context.graph_spacing),
            )
            point_b = offset_point_by_grid_vector(
                vertex,
                (int(vector_b[0]), int(vector_b[1])),
                spacing=int(context.graph_spacing),
            )
            scaled_point_a = scale_point(point_a, int(context.scene_scale))
            scaled_vertex = scale_point(vertex, int(context.scene_scale))
            scaled_point_b = scale_point(point_b, int(context.scene_scale))
            if not (
                point_inside_square_canvas(
                    scaled_point_a,
                    canvas_size=int(render_canvas_size),
                    padding=float(endpoint_padding_px),
                )
                and point_inside_square_canvas(
                    scaled_vertex,
                    canvas_size=int(render_canvas_size),
                    padding=float(endpoint_padding_px),
                )
                and point_inside_square_canvas(
                    scaled_point_b,
                    canvas_size=int(render_canvas_size),
                    padding=float(endpoint_padding_px),
                )
            ):
                continue
            selected_object = AngleSceneObject(
                label=str(label),
                vertex=(float(vertex[0]), float(vertex[1])),
                point_a=(float(point_a[0]), float(point_a[1])),
                point_b=(float(point_b[0]), float(point_b[1])),
                target_angle_degrees=int(target_angle),
                raw_angle_degrees=float(raw_angle),
            )
            break
        if selected_object is None:
            raise ValueError(f"no feasible angle geometry for target {target_angle}")
        objects.append(selected_object)
    return tuple(objects)


def draw_angle_objects(
    draw: ImageDraw.ImageDraw,
    *,
    objects: Sequence[AngleSceneObject],
    scene_scale: int,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    render_canvas_size: int,
    shape_style: GeometryShapeStyle,
) -> Dict[str, List[float]]:
    """Draw one multi-angle scene and return unscaled label centers."""

    scaled_objects = [
        {
            "label": str(obj.label),
            "vertex": scale_point(obj.vertex, int(scene_scale)),
            "point_a": scale_point(obj.point_a, int(scene_scale)),
            "point_b": scale_point(obj.point_b, int(scene_scale)),
            "raw": obj,
        }
        for obj in objects
    ]
    blocked_segments: List[Tuple[Point, Point]] = []
    line_color = tuple(int(value) for value in shape_style.line_color)
    for scaled in scaled_objects:
        point_a = scaled["point_a"]
        vertex = scaled["vertex"]
        point_b = scaled["point_b"]
        draw.line([point_a[0], point_a[1], vertex[0], vertex[1]], fill=line_color, width=max(1, int(line_width)))
        draw.line([vertex[0], vertex[1], point_b[0], point_b[1]], fill=line_color, width=max(1, int(line_width)))
        blocked_segments.extend(
            [
                ((float(point_a[0]), float(point_a[1])), (float(vertex[0]), float(vertex[1]))),
                ((float(vertex[0]), float(vertex[1])), (float(point_b[0]), float(point_b[1]))),
            ]
        )

    font = load_font(int(label_font_size_px), bold=True)
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    label_centers: Dict[str, List[float]] = {}
    for scaled in scaled_objects:
        obj = scaled["raw"]
        direction = screen_bisector_direction(obj)
        center, bbox = resolve_text_label_center(
            draw,
            text=str(obj.label),
            anchor=(float(scaled["vertex"][0]), float(scaled["vertex"][1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(object_label_offset_px) * float(scene_scale),
            font=font,
            blocked_segments=blocked_segments,
            occupied_boxes=occupied_boxes,
            stroke_width=int(label_stroke_width),
            line_clearance_px=max(4.0, 0.9 * float(max(1, int(line_width)))),
            canvas_size=int(render_canvas_size),
        )
        draw_text_centered(
            draw,
            text=str(obj.label),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(label_stroke_width),
        )
        occupied_boxes.append(bbox)
        label_centers[str(obj.label)] = [
            float(center[0]) / float(max(1, int(scene_scale))),
            float(center[1]) / float(max(1, int(scene_scale))),
        ]
    return label_centers


__all__ = [
    "AngleSceneObject",
    "draw_angle_objects",
    "sample_angle_objects_for_targets",
    "screen_bisector_direction",
]
