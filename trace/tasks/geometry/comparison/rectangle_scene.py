"""Shared rectangle-comparison scene helpers for geometry/comparison tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ...shared.comparison_sampling import (
    ComparisonGapMetrics,
    comparison_gap_is_valid,
    compute_comparison_gap_metrics,
)
from ...shared.geometry_primitives import Point, point_inside_square_canvas
from ...shared.text_rendering import (
    draw_text_centered,
    load_font,
    resolve_text_label_center,
)
from ..shared.graph_rendering import scale_point
from ..shared.shape_style import GeometryShapeStyle
from .shared import (
    COMPARISON_ANSWER_LABEL_POOL,
    bulky_slot_centers_graph_units,
    graph_units_to_pixel,
)

RectangleMetricKind = Literal["area_square_units", "perimeter_units"]


@dataclass(frozen=True)
class RectangleComparisonObject:
    """One labeled rectangle object rendered in a comparison scene."""

    label: str
    vertices: Tuple[Point, Point, Point, Point]
    width_units: int
    height_units: int
    area_square_units: int
    perimeter_units: int
    center: Point


@dataclass(frozen=True)
class RectangleComparisonScenePayload:
    """Trace-ready scene payload for one multi-rectangle comparison instance."""

    query_type: str
    object_count: int
    objects: Tuple[RectangleComparisonObject, ...]
    winner_metrics: ComparisonGapMetrics
    winner_label: str
    evidence_points_by_label: Dict[str, Point]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]


def rectangle_dimensions_by_metric(
    *,
    metric_kind: RectangleMetricKind,
    min_width: int,
    max_width: int,
    min_height: int,
    max_height: int,
) -> Dict[int, List[Tuple[int, int]]]:
    """Group feasible integer rectangle dimensions by one scalar metric."""

    grouped: Dict[int, List[Tuple[int, int]]] = {}
    for width in range(int(min_width), int(max_width) + 1):
        for height in range(int(min_height), int(max_height) + 1):
            area = int(width) * int(height)
            perimeter = int(2 * (int(width) + int(height)))
            value = int(area if str(metric_kind) == "area_square_units" else perimeter)
            grouped.setdefault(int(value), []).append((int(width), int(height)))
    return grouped


def sample_target_metric_values(
    rng,
    *,
    candidate_values: Sequence[int],
    object_count: int,
    query_type: str,
    min_normalized_gap: float,
    min_absolute_gap: float,
) -> List[int]:
    """Sample distinct target values whose winner gap is visually meaningful."""

    candidates = [int(value) for value in candidate_values]
    if len(candidates) < int(object_count):
        raise ValueError("not enough feasible rectangle metric candidates for requested object_count")
    for _ in range(800):
        selected = [int(value) for value in rng.sample(candidates, int(object_count))]
        if comparison_gap_is_valid(
            [float(value) for value in selected],
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap),
        ):
            return selected
    raise ValueError("failed to sample rectangle comparison targets with configured gap rule")


def rectangle_vertices_from_slot(
    slot_units: Tuple[int, int],
    *,
    width_units: int,
    height_units: int,
    graph_origin: Point,
    graph_spacing: int,
) -> Tuple[Point, Point, Point, Point, Point]:
    """Return pixel-space rectangle vertices plus center from one slot."""

    left = int(slot_units[0]) - int(width_units // 2)
    bottom = int(slot_units[1]) - int(height_units // 2)
    unit_vertices = (
        (int(left), int(bottom)),
        (int(left + width_units), int(bottom)),
        (int(left + width_units), int(bottom + height_units)),
        (int(left), int(bottom + height_units)),
    )
    pixel_vertices = tuple(
        graph_units_to_pixel(
            unit_point,
            graph_origin=(float(graph_origin[0]), float(graph_origin[1])),
            spacing=int(graph_spacing),
        )
        for unit_point in unit_vertices
    )
    center_units = (float(left) + (0.5 * float(width_units)), float(bottom) + (0.5 * float(height_units)))
    center = (
        float(graph_origin[0]) + (float(center_units[0]) * float(graph_spacing)),
        float(graph_origin[1]) - (float(center_units[1]) * float(graph_spacing)),
    )
    return (
        pixel_vertices[0],
        pixel_vertices[1],
        pixel_vertices[2],
        pixel_vertices[3],
        center,
    )


def draw_rectangle_comparison_scene(
    draw: ImageDraw.ImageDraw,
    *,
    objects: Sequence[RectangleComparisonObject],
    scene_scale: int,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    render_canvas_size: int,
    shape_style: GeometryShapeStyle,
) -> Dict[str, List[float]]:
    """Draw all compared rectangles plus object labels and return label centers."""

    scaled_objects = [
        {
            "label": str(obj.label),
            "vertices": [scale_point(point, int(scene_scale)) for point in obj.vertices],
            "center": scale_point(obj.center, int(scene_scale)),
        }
        for obj in objects
    ]
    blocked_segments: List[Tuple[Point, Point]] = []
    line_color = tuple(int(value) for value in shape_style.line_color)
    for scaled in scaled_objects:
        polygon = scaled["vertices"]
        draw.line([*polygon, polygon[0]], fill=line_color, width=max(1, int(line_width)))
        blocked_segments.extend(
            [
                ((float(polygon[0][0]), float(polygon[0][1])), (float(polygon[1][0]), float(polygon[1][1]))),
                ((float(polygon[1][0]), float(polygon[1][1])), (float(polygon[2][0]), float(polygon[2][1]))),
                ((float(polygon[2][0]), float(polygon[2][1])), (float(polygon[3][0]), float(polygon[3][1]))),
                ((float(polygon[3][0]), float(polygon[3][1])), (float(polygon[0][0]), float(polygon[0][1]))),
            ]
        )

    font = load_font(int(label_font_size_px), bold=True)
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    label_centers: Dict[str, List[float]] = {}
    for scaled in scaled_objects:
        polygon = scaled["vertices"]
        min_x = min(float(point[0]) for point in polygon)
        max_x = max(float(point[0]) for point in polygon)
        min_y = min(float(point[1]) for point in polygon)
        max_y = max(float(point[1]) for point in polygon)
        center = (float(scaled["center"][0]), float(scaled["center"][1]))
        direction = (
            float(center[0]) - (0.5 * float(render_canvas_size)),
            float(center[1]) - (0.5 * float(render_canvas_size)),
        )
        width_px = float(max_x - min_x)
        height_px = float(max_y - min_y)
        center_outward_offset = max(
            float(object_label_offset_px) * float(scene_scale),
            0.55 * max(float(width_px), float(height_px)),
        )
        center_text, center_bbox = resolve_text_label_center(
            draw,
            text=str(scaled["label"]),
            anchor=center,
            base_direction=direction,
            offset_px=float(center_outward_offset),
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
            center=(float(center_text[0]), float(center_text[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(label_stroke_width),
        )
        occupied_boxes.append(center_bbox)
        label_centers[str(scaled["label"])] = [
            float(center_text[0]) / float(max(1, int(scene_scale))),
            float(center_text[1]) / float(max(1, int(scene_scale))),
        ]
    return label_centers


def sample_rectangle_comparison_scene(
    rng,
    *,
    winner_label: str,
    context,
    query_type: str,
    object_count: int,
    metric_kind: RectangleMetricKind,
    min_rectangle_width: int,
    max_rectangle_width: int,
    min_rectangle_height: int,
    max_rectangle_height: int,
    min_normalized_gap: float,
    min_absolute_gap: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    draw: ImageDraw.ImageDraw,
    shape_style: GeometryShapeStyle,
) -> RectangleComparisonScenePayload:
    """Sample and draw one multi-rectangle comparison scene."""

    dimensions_by_metric = rectangle_dimensions_by_metric(
        metric_kind=str(metric_kind),  # type: ignore[arg-type]
        min_width=int(min_rectangle_width),
        max_width=int(max_rectangle_width),
        min_height=int(min_rectangle_height),
        max_height=int(max_rectangle_height),
    )
    candidate_values = [int(value) for value in sorted(dimensions_by_metric.keys())]
    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    endpoint_padding_px = max(3.0, 0.75 * float(context.graph_spacing) * float(context.scene_scale))

    last_error: Exception | None = None
    for _ in range(700):
        labels = [
            str(label)
            for label in COMPARISON_ANSWER_LABEL_POOL
            if str(label) != str(winner_label)
        ]
        rng.shuffle(labels)
        selected_labels = [str(winner_label), *labels[: max(0, int(object_count) - 1)]]
        rng.shuffle(selected_labels)
        slots = bulky_slot_centers_graph_units(
            object_count=int(object_count),
            graph_cells=int(context.graph_cells),
            rng=rng,
        )
        sampled_target_values = sample_target_metric_values(
            rng,
            candidate_values=candidate_values,
            object_count=int(object_count),
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap),
        )
        winner_target_value = (
            int(max(sampled_target_values))
            if str(query_type) == "largest"
            else int(min(sampled_target_values))
        )
        other_target_values = [
            int(value) for value in sampled_target_values if int(value) != int(winner_target_value)
        ]
        rng.shuffle(other_target_values)

        objects: List[RectangleComparisonObject] = []
        try:
            for label, slot_units in zip(selected_labels, slots):
                target_value = (
                    int(winner_target_value)
                    if str(label) == str(winner_label)
                    else int(other_target_values.pop())
                )
                candidates = list(dimensions_by_metric[int(target_value)])
                rng.shuffle(candidates)
                selected_object: RectangleComparisonObject | None = None
                for width_units, height_units in candidates:
                    v0, v1, v2, v3, center = rectangle_vertices_from_slot(
                        slot_units,
                        width_units=int(width_units),
                        height_units=int(height_units),
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                    )
                    scaled_vertices = [scale_point(point, int(context.scene_scale)) for point in (v0, v1, v2, v3)]
                    if not all(
                        point_inside_square_canvas(
                            point,
                            canvas_size=int(render_canvas_size),
                            padding=float(endpoint_padding_px),
                        )
                        for point in scaled_vertices
                    ):
                        continue
                    area = int(width_units) * int(height_units)
                    perimeter = int(2 * (int(width_units) + int(height_units)))
                    selected_object = RectangleComparisonObject(
                        label=str(label),
                        vertices=(v0, v1, v2, v3),
                        width_units=int(width_units),
                        height_units=int(height_units),
                        area_square_units=int(area),
                        perimeter_units=int(perimeter),
                        center=(float(center[0]), float(center[1])),
                    )
                    break
                if selected_object is None:
                    raise ValueError(f"no feasible rectangle geometry for target {target_value}")
                objects.append(selected_object)
        except Exception as exc:
            last_error = exc
            continue

        values = [
            float(
                obj.area_square_units if str(metric_kind) == "area_square_units" else obj.perimeter_units
            )
            for obj in objects
        ]
        metrics = compute_comparison_gap_metrics(values, query_type=str(query_type))
        if str(objects[int(metrics.winner_index)].label) != str(winner_label):
            continue
        if not comparison_gap_is_valid(
            values,
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap),
        ):
            continue

        label_centers = draw_rectangle_comparison_scene(
            draw,
            objects=tuple(objects),
            scene_scale=int(context.scene_scale),
            line_width=int(line_width) * int(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            object_label_offset_px=float(object_label_offset_px),
            render_canvas_size=int(render_canvas_size),
            shape_style=shape_style,
        )
        winner = objects[int(metrics.winner_index)]
        return RectangleComparisonScenePayload(
            query_type=str(query_type),
            object_count=int(object_count),
            objects=tuple(objects),
            winner_metrics=metrics,
            winner_label=str(winner.label),
            evidence_points_by_label={
                "vertex_1": winner.vertices[0],
                "vertex_2": winner.vertices[1],
                "vertex_3": winner.vertices[2],
                "vertex_4": winner.vertices[3],
            },
            object_label_centers=label_centers,
            render_anchor={
                "winner_label": str(winner.label),
                "winner_center": [float(winner.center[0]), float(winner.center[1])],
                "winner_polygon": [[float(point[0]), float(point[1])] for point in winner.vertices],
            },
        )
    raise RuntimeError("failed to sample rectangle-comparison scene") from last_error


__all__ = [
    "RectangleComparisonObject",
    "RectangleComparisonScenePayload",
    "RectangleMetricKind",
    "draw_rectangle_comparison_scene",
    "rectangle_dimensions_by_metric",
    "rectangle_vertices_from_slot",
    "sample_rectangle_comparison_scene",
    "sample_target_metric_values",
]
