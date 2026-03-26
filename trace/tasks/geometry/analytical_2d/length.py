"""Derived analytical 2D length task with multi-shape annotated scenes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import (
    draw_text_centered,
    load_font,
    resolve_scene_label_font_size_px,
)
from ..shared.analytical_task import required_prompt_text, resolve_answer_bounds, resolve_task_variant
from ..shared.annotation_values import build_role_value_evidence, format_annotation_value
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.conic_geometry import draw_circle_outline
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.polygon_geometry import alphabetic_labels
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import (
    GeometryShapeStyle,
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import ANALYTICAL_SHARED_DEFAULTS

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

LENGTH_VARIANTS: Tuple[str, ...] = (
    "triangle_altitude_side",
    "rectangle_diagonal_side",
    "rhombus_diagonal_side",
    "isosceles_trapezoid_leg",
    "inscribed_square_side",
    "circle_chord_length",
)

ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="analytical_2d")
ANALYTICAL_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="analytical_2d")


@dataclass(frozen=True)
class _AnnotationSpec:
    """One numeric measurement annotation anchored to a segment."""

    role: str
    point_a_id: str
    point_b_id: str
    anchor_fraction: float = 0.5
    offset_scale: float = 1.0
    direction_override: Point | None = None


@dataclass(frozen=True)
class _PolygonEntitySpec:
    """One polygon-like rendered entity."""

    entity_id: str
    entity_type: str
    point_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _CircleEntitySpec:
    """One circle rendered entity."""

    entity_id: str
    center_id: str
    radius_units: float


@dataclass(frozen=True)
class _SegmentEntitySpec:
    """One standalone rendered segment, visible or helper."""

    entity_id: str
    entity_type: str
    point_a_id: str
    point_b_id: str
    helper: bool = False


@dataclass(frozen=True)
class _SceneBlueprint:
    """Variant-specific scene definition before pixel rendering."""

    point_units: Dict[str, Point]
    fit_points: Tuple[Point, ...]
    polygon_entities: Tuple[_PolygonEntitySpec, ...]
    circle_entities: Tuple[_CircleEntitySpec, ...]
    segment_entities: Tuple[_SegmentEntitySpec, ...]
    annotation_specs: Tuple[_AnnotationSpec, ...]
    label_point_ids: Tuple[str, ...]
    label_directions: Dict[str, Point]
    evidence_roles: Tuple[str, ...]
    role_values: Dict[str, Any]
    target_point_ids: Tuple[str, str]
    formula_expression: str
    raw_answer_value: float


@dataclass(frozen=True)
class _RenderedCase:
    """Fully rendered analytical length case payload."""

    task_variant: str
    answer_value: float
    raw_answer_value: float
    answer_scalar: int
    formula_expression: str
    target_annotation: str
    evidence_roles: Tuple[str, ...]
    role_values: Dict[str, Any]
    role_tokens: Dict[str, str]
    evidence_map: Dict[str, Any]
    annotation_centers: Dict[str, List[float]]
    entities: List[Dict[str, Any]]
    render_anchor: Dict[str, Any]


def _rounded_tenth(value: float) -> float:
    """Round one numeric answer to the nearest tenth deterministically."""
    return round(float(value) + 1e-9, 1)


def _analytical_unit_spacing_px(context: GraphSceneContext) -> int:
    """Return preferred unit spacing for analytical 2D scenes."""
    raw_value = context.render_params.get("analytical_unit_spacing_px", context.graph_spacing)
    spacing_px = int(raw_value)
    if int(spacing_px) < 2:
        raise ValueError("analytical_unit_spacing_px must be >= 2")
    return int(spacing_px)


def _analytical_unit_padding_px(context: GraphSceneContext) -> int:
    """Return padding reserved for analytical scenes."""
    raw_value = context.render_params.get("analytical_unit_padding_px", 20)
    padding_px = int(raw_value)
    if int(padding_px) < 0:
        raise ValueError("analytical_unit_padding_px must be >= 0")
    return int(padding_px)


def _normalize(vector: Point) -> Point:
    """Return normalized vector or a default direction when degenerate."""
    norm = math.hypot(float(vector[0]), float(vector[1]))
    if norm <= 1e-9:
        return (1.0, -1.0)
    return (float(vector[0]) / float(norm), float(vector[1]) / float(norm))


def _midpoint(point_a: Point, point_b: Point, *, fraction: float = 0.5) -> Point:
    """Return one interpolated point on a segment."""
    frac = max(0.0, min(1.0, float(fraction)))
    return (
        float(point_a[0]) + (float(point_b[0]) - float(point_a[0])) * float(frac),
        float(point_a[1]) + (float(point_b[1]) - float(point_a[1])) * float(frac),
    )


def _point_key(point: Point, *, scale: int = 1000) -> Tuple[int, int]:
    """Return one hashable key for approximately equal points."""
    return (
        int(round(float(point[0]) * float(scale))),
        int(round(float(point[1]) * float(scale))),
    )


def _polygon_centroid(points: Sequence[Point]) -> Point:
    """Return arithmetic centroid for a point sequence."""
    return (
        float(sum(float(point[0]) for point in points) / float(len(points))),
        float(sum(float(point[1]) for point in points) / float(len(points))),
    )


def _segment_direction(point_a: Point, point_b: Point) -> Point:
    """Return one perpendicular annotation direction for a segment."""
    return _normalize((-(float(point_b[1]) - float(point_a[1])), float(point_b[0]) - float(point_a[0])))


def _fit_points_to_canvas(
    rng,
    *,
    points: Sequence[Point],
    context: GraphSceneContext,
    fill_ratio: float,
) -> Tuple[float, float, float]:
    """Compute a unit-to-pixel transform that fits points inside the canvas."""
    if not points:
        raise ValueError("fit_points must be non-empty")
    min_x = min(float(point[0]) for point in points)
    max_x = max(float(point[0]) for point in points)
    min_y = min(float(point[1]) for point in points)
    max_y = max(float(point[1]) for point in points)
    span_x = max(1.0, float(max_x) - float(min_x))
    span_y = max(1.0, float(max_y) - float(min_y))
    padding_px = float(_analytical_unit_padding_px(context))
    preferred_spacing = float(_analytical_unit_spacing_px(context))
    usable_total = max(32.0, float(context.canvas_size) - (2.0 * float(padding_px)))
    occupancy = max(0.4, min(0.95, float(fill_ratio)))
    target_usable = float(usable_total) * float(occupancy)
    reserve = max(0.0, float(usable_total) - float(target_usable))
    scale = min(float(preferred_spacing), float(target_usable / span_x), float(target_usable / span_y))
    if float(scale) <= 0.0:
        raise ValueError("invalid analytical unit scale")
    extra_x = max(0.0, float(usable_total) - (float(span_x) * float(scale)))
    extra_y = max(0.0, float(usable_total) - (float(span_y) * float(scale)))
    min_origin_x = float(padding_px) + (0.5 * float(reserve))
    min_origin_y = float(padding_px) + (0.5 * float(reserve))
    jitter_x = max(0.0, float(extra_x) - float(reserve))
    jitter_y = max(0.0, float(extra_y) - float(reserve))
    origin_x = float(min_origin_x) + (float(rng.random()) * float(jitter_x))
    origin_y = float(min_origin_y) + (float(rng.random()) * float(jitter_y))
    offset_x = float(origin_x) - (float(min_x) * float(scale))
    offset_y = float(origin_y) + (float(max_y) * float(scale))
    return float(scale), float(offset_x), float(offset_y)


def _transform_point(point: Point, *, scale: float, offset_x: float, offset_y: float) -> Point:
    """Map one analytical unit point into pixel coordinates."""
    return (
        float(offset_x) + (float(point[0]) * float(scale)),
        float(offset_y) - (float(point[1]) * float(scale)),
    )


def _draw_polygon_outline(draw: ImageDraw.ImageDraw, points: Sequence[Point], *, width: int, fill: Tuple[int, int, int]) -> None:
    """Draw one closed polygon outline."""
    polyline = [tuple((float(point[0]), float(point[1]))) for point in points]
    if len(polyline) < 2:
        return
    draw.line([*polyline, polyline[0]], fill=tuple(int(value) for value in fill), width=max(1, int(width)), joint="curve")


def _assign_point_labels(rng, point_ids: Sequence[str]) -> Dict[str, str]:
    """Assign deterministic alphabetic point labels to named point ids."""
    ids = [str(point_id) for point_id in point_ids]
    labels = alphabetic_labels(len(ids), start_index=int(rng.randrange(26)))
    return {str(point_id): str(label) for point_id, label in zip(ids, labels)}


def _annotation_token(point_labels: Mapping[str, str], point_a_id: str, point_b_id: str) -> str:
    """Return one endpoint token such as `AB`."""
    return f"{point_labels[str(point_a_id)]}{point_labels[str(point_b_id)]}"


def _draw_point_labels(
    draw: ImageDraw.ImageDraw,
    *,
    point_labels: Mapping[str, str],
    point_positions: Mapping[str, Point],
    blocked_segments: Sequence[Segment],
    occupied_boxes: List[Tuple[float, float, float, float]],
    label_directions: Mapping[str, Point],
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
) -> None:
    """Draw point labels near their associated points."""
    scene_scale = max(1, int(context.scene_scale))
    font = load_font(int(label_font_size_px), bold=True)
    stroke_width = max(1, int(label_stroke_width))
    centroid = _polygon_centroid(list(point_positions.values()))
    occupied_padding = max(4.0, 2.0 * float(scene_scale))
    for point_id, label in point_labels.items():
        point = point_positions[str(point_id)]
        direction = label_directions.get(str(point_id), (float(point[0]) - float(centroid[0]), float(point[1]) - float(centroid[1])))
        direction = _normalize(direction)
        scaled_anchor = scale_point((float(point[0]), float(point[1])), int(scene_scale))
        center, bbox = _resolve_local_text_center(
            draw,
            text=str(label),
            anchor=(float(scaled_anchor[0]), float(scaled_anchor[1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(max(10.0, float(label_offset_px))),
            font=font,
            blocked_segments=[
                (
                    scale_point((float(seg_a[0]), float(seg_a[1])), int(scene_scale)),
                    scale_point((float(seg_b[0]), float(seg_b[1])), int(scene_scale)),
                )
                for seg_a, seg_b in blocked_segments
            ],
            occupied_boxes=occupied_boxes,
            stroke_width=int(stroke_width),
            line_clearance_px=max(3.0, 2.4 * float(scene_scale)),
            canvas_size=int(context.canvas_size) * int(scene_scale),
        )
        draw_text_centered(
            draw,
            text=str(label),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(stroke_width),
        )
        occupied_boxes.append(
            (
                float(bbox[0]) - float(occupied_padding),
                float(bbox[1]) - float(occupied_padding),
                float(bbox[2]) + float(occupied_padding),
                float(bbox[3]) + float(occupied_padding),
            )
        )


def _draw_measurement_annotations(
    draw: ImageDraw.ImageDraw,
    *,
    point_positions: Mapping[str, Point],
    point_labels: Mapping[str, str],
    annotations: Sequence[_AnnotationSpec],
    role_values: Mapping[str, Any],
    blocked_segments: Sequence[Segment],
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
) -> Tuple[Dict[str, List[float]], Dict[str, str], List[Tuple[float, float, float, float]]]:
    """Draw numeric measurement annotations and return centers/token mapping."""
    scene_scale = max(1, int(context.scene_scale))
    font = load_font(int(label_font_size_px), bold=True)
    stroke_width = max(1, int(label_stroke_width))
    blocked_scaled = [
        (
            scale_point((float(seg_a[0]), float(seg_a[1])), int(scene_scale)),
            scale_point((float(seg_b[0]), float(seg_b[1])), int(scene_scale)),
        )
        for seg_a, seg_b in blocked_segments
    ]
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    centers: Dict[str, List[float]] = {}
    role_tokens: Dict[str, str] = {}
    occupied_padding = max(4.0, 2.0 * float(scene_scale))
    all_points = [point_positions[point_id] for point_id in point_positions]
    centroid = _polygon_centroid(all_points)
    for annotation in annotations:
        point_a = point_positions[str(annotation.point_a_id)]
        point_b = point_positions[str(annotation.point_b_id)]
        token = _annotation_token(point_labels, str(annotation.point_a_id), str(annotation.point_b_id))
        role_tokens[str(annotation.role)] = str(token)
        midpoint = _midpoint(point_a, point_b, fraction=float(annotation.anchor_fraction))
        direction = annotation.direction_override
        if direction is None:
            direction = _segment_direction(point_a, point_b)
            outward = (float(midpoint[0]) - float(centroid[0]), float(midpoint[1]) - float(centroid[1]))
            if (float(direction[0]) * float(outward[0])) + (float(direction[1]) * float(outward[1])) < 0.0:
                direction = (-float(direction[0]), -float(direction[1]))
        direction = _normalize(direction)
        scaled_anchor = scale_point((float(midpoint[0]), float(midpoint[1])), int(scene_scale))
        center, bbox = _resolve_local_text_center(
            draw,
            text=format_annotation_value(role_values[str(annotation.role)]),
            anchor=(float(scaled_anchor[0]), float(scaled_anchor[1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(max(12.0, float(label_offset_px) * max(0.8, float(annotation.offset_scale)))),
            font=font,
            blocked_segments=blocked_scaled,
            occupied_boxes=occupied_boxes,
            stroke_width=int(stroke_width),
            line_clearance_px=max(4.0, 2.4 * float(scene_scale)),
            canvas_size=int(context.canvas_size) * int(scene_scale),
        )
        draw_text_centered(
            draw,
            text=format_annotation_value(role_values[str(annotation.role)]),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(stroke_width),
        )
        occupied_boxes.append(
            (
                float(bbox[0]) - float(occupied_padding),
                float(bbox[1]) - float(occupied_padding),
                float(bbox[2]) + float(occupied_padding),
                float(bbox[3]) + float(occupied_padding),
            )
        )
        centers[str(token)] = [float(center[0]) / float(scene_scale), float(center[1]) / float(scene_scale)]
    return dict(centers), dict(role_tokens), occupied_boxes


def _resolve_local_text_center(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    anchor: Point,
    base_direction: Point,
    offset_px: float,
    font,
    blocked_segments: Sequence[Segment],
    occupied_boxes: Sequence[Tuple[float, float, float, float]],
    stroke_width: int,
    line_clearance_px: float,
    canvas_size: int,
) -> Tuple[Point, Tuple[float, float, float, float]]:
    """Resolve one nearby text center while keeping analytical labels local.

    The placement keeps labels on one side of the associated segment/point by
    offsetting far enough to clear the text bbox in the chosen direction, then
    trying a small deterministic set of nearby directions.
    """
    text_bbox = draw.textbbox((0.0, 0.0), str(text), font=font, stroke_width=int(stroke_width))
    width = max(1.0, float(text_bbox[2]) - float(text_bbox[0]))
    height = max(1.0, float(text_bbox[3]) - float(text_bbox[1]))
    base = _normalize(base_direction)
    left = _normalize((-float(base[1]), float(base[0])))
    right = _normalize((float(base[1]), -float(base[0])))
    opposite = _normalize((-float(base[0]), -float(base[1])))
    candidates = (base, left, right, opposite)
    margin = max(4.0, 0.35 * float(offset_px))
    best_center: Point | None = None
    best_bbox: Tuple[float, float, float, float] | None = None
    best_score: float | None = None
    for direction in candidates:
        dir_x, dir_y = float(direction[0]), float(direction[1])
        half_extent = 0.5 * ((abs(float(dir_x)) * float(width)) + (abs(float(dir_y)) * float(height)))
        for scale in (1.0, 1.2, 1.45):
            distance = (float(half_extent) + float(line_clearance_px) + float(offset_px)) * float(scale)
            center = (
                float(anchor[0]) + (float(dir_x) * float(distance)),
                float(anchor[1]) + (float(dir_y) * float(distance)),
            )
            bbox = (
                float(center[0]) - (0.5 * float(width)),
                float(center[1]) - (0.5 * float(height)),
                float(center[0]) + (0.5 * float(width)),
                float(center[1]) + (0.5 * float(height)),
            )
            if (
                float(bbox[0]) < float(margin)
                or float(bbox[1]) < float(margin)
                or float(bbox[2]) > float(canvas_size) - float(margin)
                or float(bbox[3]) > float(canvas_size) - float(margin)
            ):
                continue
            if any(
                not (
                    float(bbox[2]) < float(other[0])
                    or float(bbox[0]) > float(other[2])
                    or float(bbox[3]) < float(other[1])
                    or float(bbox[1]) > float(other[3])
                )
                for other in occupied_boxes
            ):
                continue
            expanded = (
                float(bbox[0]) - float(line_clearance_px),
                float(bbox[1]) - float(line_clearance_px),
                float(bbox[2]) + float(line_clearance_px),
                float(bbox[3]) + float(line_clearance_px),
            )
            intersects = False
            for seg_a, seg_b in blocked_segments:
                min_x = min(float(seg_a[0]), float(seg_b[0]))
                max_x = max(float(seg_a[0]), float(seg_b[0]))
                min_y = min(float(seg_a[1]), float(seg_b[1]))
                max_y = max(float(seg_a[1]), float(seg_b[1]))
                if not (
                    float(max_x) < float(expanded[0])
                    or float(min_x) > float(expanded[2])
                    or float(max_y) < float(expanded[1])
                    or float(min_y) > float(expanded[3])
                ):
                    intersects = True
                    break
            if intersects:
                continue
            score = math.hypot(float(center[0]) - float(anchor[0]), float(center[1]) - float(anchor[1]))
            if best_score is None or float(score) < float(best_score):
                best_center = (float(center[0]), float(center[1]))
                best_bbox = bbox
                best_score = float(score)
        if best_center is not None and best_bbox is not None:
            return best_center, best_bbox

    half_w = 0.5 * float(width)
    half_h = 0.5 * float(height)
    fallback_distance = float(offset_px) + float(line_clearance_px) + max(float(half_w), float(half_h))
    fallback_center = (
        float(anchor[0]) + (float(base[0]) * float(fallback_distance)),
        float(anchor[1]) + (float(base[1]) * float(fallback_distance)),
    )
    fallback_bbox = (
        float(fallback_center[0]) - float(half_w),
        float(fallback_center[1]) - float(half_h),
        float(fallback_center[0]) + float(half_w),
        float(fallback_center[1]) + float(half_h),
    )
    return fallback_center, fallback_bbox


def _render_blueprint(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    task_variant: str,
    blueprint: _SceneBlueprint,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    fill_ratio: float,
) -> _RenderedCase:
    """Render one sampled blueprint into pixel space and build evidence payloads."""
    scale, offset_x, offset_y = _fit_points_to_canvas(
        rng,
        points=blueprint.fit_points,
        context=context,
        fill_ratio=float(fill_ratio),
    )
    point_positions = {
        str(point_id): _transform_point(point, scale=float(scale), offset_x=float(offset_x), offset_y=float(offset_y))
        for point_id, point in blueprint.point_units.items()
    }
    point_labels = _assign_point_labels(rng, blueprint.label_point_ids)

    blocked_segments: List[Segment] = []
    entities: List[Dict[str, Any]] = []

    for polygon in blueprint.polygon_entities:
        points = [point_positions[point_id] for point_id in polygon.point_ids]
        draw_points = [scale_point((float(point[0]), float(point[1])), int(context.scene_scale)) for point in points]
        _draw_polygon_outline(
            draw,
            draw_points,
            width=int(line_width),
            fill=tuple(int(value) for value in shape_style.line_color),
        )
        blocked_segments.extend(
            [
                (points[index], points[(index + 1) % len(points)])
                for index in range(len(points))
            ]
        )
        entities.append(
            {
                "entity_id": str(polygon.entity_id),
                "entity_type": str(polygon.entity_type),
                "attrs": {
                    "vertices": [[float(point[0]), float(point[1])] for point in points],
                },
            }
        )

    for circle in blueprint.circle_entities:
        center = point_positions[str(circle.center_id)]
        radius_px = max(1, int(round(float(circle.radius_units) * float(scale))))
        draw_circle_outline(
            draw,
            center=scale_point((float(center[0]), float(center[1])), int(context.scene_scale)),
            radius_px=int(radius_px) * int(context.scene_scale),
            line_width=int(line_width) * int(context.scene_scale),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        entities.append(
            {
                "entity_id": str(circle.entity_id),
                "entity_type": "circle",
                "attrs": {
                    "center": [float(center[0]), float(center[1])],
                    "radius_px": int(radius_px),
                },
            }
        )

    for segment in blueprint.segment_entities:
        point_a = point_positions[str(segment.point_a_id)]
        point_b = point_positions[str(segment.point_b_id)]
        width = int(helper_line_width if bool(segment.helper) else line_width)
        draw.line(
            [
                scale_point((float(point_a[0]), float(point_a[1])), int(context.scene_scale)),
                scale_point((float(point_b[0]), float(point_b[1])), int(context.scene_scale)),
            ],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(width) * int(context.scene_scale)),
        )
        blocked_segments.append((point_a, point_b))
        entities.append(
            {
                "entity_id": str(segment.entity_id),
                "entity_type": str(segment.entity_type),
                "attrs": {
                    "point_a": [float(point_a[0]), float(point_a[1])],
                    "point_b": [float(point_b[0]), float(point_b[1])],
                    "helper": bool(segment.helper),
                },
            }
        )

    annotation_centers, role_tokens, occupied_boxes = _draw_measurement_annotations(
        draw,
        point_positions=point_positions,
        point_labels=point_labels,
        annotations=blueprint.annotation_specs,
        role_values=blueprint.role_values,
        blocked_segments=blocked_segments,
        context=context,
        shape_style=shape_style,
        label_offset_px=float(label_offset_px),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
    )
    _draw_point_labels(
        draw,
        point_labels={point_id: point_labels[point_id] for point_id in blueprint.label_point_ids},
        point_positions={point_id: point_positions[point_id] for point_id in blueprint.label_point_ids},
        blocked_segments=blocked_segments,
        occupied_boxes=occupied_boxes,
        label_directions=blueprint.label_directions,
        context=context,
        shape_style=shape_style,
        label_offset_px=float(label_offset_px),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
    )

    evidence_map = build_role_value_evidence(
        roles=blueprint.evidence_roles,
        role_to_annotation=role_tokens,
        role_to_value=blueprint.role_values,
    )
    target_annotation = _annotation_token(point_labels, blueprint.target_point_ids[0], blueprint.target_point_ids[1])
    rounded_answer = _rounded_tenth(float(blueprint.raw_answer_value))

    xs = [float(point[0]) for point in point_positions.values()]
    ys = [float(point[1]) for point in point_positions.values()]
    render_anchor = {
        "bbox": [min(xs), min(ys), max(xs), max(ys)],
        "coord_space": "pixel",
    }
    return _RenderedCase(
        task_variant=str(task_variant),
        answer_value=float(rounded_answer),
        raw_answer_value=float(blueprint.raw_answer_value),
        answer_scalar=int(round(float(rounded_answer) * 10.0)),
        formula_expression=str(blueprint.formula_expression),
        target_annotation=str(target_annotation),
        evidence_roles=tuple(str(role) for role in blueprint.evidence_roles),
        role_values=dict(blueprint.role_values),
        role_tokens=dict(role_tokens),
        evidence_map=dict(evidence_map),
        annotation_centers=dict(annotation_centers),
        entities=entities,
        render_anchor=dict(render_anchor),
    )


def _dimension_bounds(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve inclusive integer dimension bounds for analytical length variants."""
    minimum = int(params.get("dimension_min", gen_defaults.get("dimension_min", 4)))
    maximum = int(params.get("dimension_max", gen_defaults.get("dimension_max", 40)))
    if int(minimum) < 1 or int(minimum) > int(maximum):
        raise ValueError("invalid dimension_min/dimension_max for analytical 2D length")
    return int(minimum), int(maximum)


def _circle_radius_bounds(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve inclusive integer circle radius bounds."""
    minimum = int(params.get("circle_radius_min", gen_defaults.get("circle_radius_min", 6)))
    maximum = int(params.get("circle_radius_max", gen_defaults.get("circle_radius_max", 36)))
    if int(minimum) < 1 or int(minimum) > int(maximum):
        raise ValueError("invalid circle_radius_min/circle_radius_max for analytical 2D length")
    return int(minimum), int(maximum)


def _answer_in_bounds(raw_answer: float, *, answer_min: int, answer_max: int) -> bool:
    """Return true when the rounded answer stays within inclusive bounds."""
    rounded = _rounded_tenth(float(raw_answer))
    return float(answer_min) <= float(rounded) <= float(answer_max)


def _sample_triangle_altitude_side(rng, *, answer_min: int, answer_max: int, dimension_min: int, dimension_max: int) -> _SceneBlueprint:
    """Triangle with altitude to base; infer one slanted side from height and base segment."""
    for _ in range(400):
        height = int(rng.randint(max(2, int(dimension_min)), int(dimension_max)))
        left_base = int(rng.randint(max(2, int(dimension_min // 2)), int(dimension_max)))
        right_base = int(rng.randint(max(2, int(dimension_min // 2)), int(dimension_max)))
        answer = math.hypot(float(height), float(left_base))
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        if abs(float(answer) - float(round(answer))) <= 1e-6:
            continue
        point_units = {
            "A": (-float(left_base), 0.0),
            "D": (0.0, 0.0),
            "B": (float(right_base), 0.0),
            "C": (0.0, float(height)),
        }
        return _SceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(_PolygonEntitySpec("triangle_1", "triangle", ("A", "B", "C")),),
            circle_entities=(),
            segment_entities=(_SegmentEntitySpec("altitude_1", "altitude", "C", "D", True),),
            annotation_specs=(
                _AnnotationSpec("height", "C", "D", offset_scale=1.0),
                _AnnotationSpec("base_part", "A", "D", offset_scale=0.9),
            ),
            label_point_ids=("A", "B", "C", "D"),
            label_directions={"D": (-1.0, -1.0)},
            evidence_roles=("height", "base_part"),
            role_values={"height": int(height), "base_part": int(left_base)},
            target_point_ids=("A", "C"),
            formula_expression="sqrt(height^2 + base_part^2)",
            raw_answer_value=float(answer),
        )
    raise ValueError("failed to sample triangle_altitude_side")


def _sample_rectangle_diagonal_side(rng, *, answer_min: int, answer_max: int, dimension_min: int, dimension_max: int) -> _SceneBlueprint:
    """Rectangle with one side and diagonal annotated; infer the missing side."""
    for _ in range(600):
        height = int(rng.randint(max(2, int(dimension_min)), int(dimension_max)))
        diagonal = int(rng.randint(max(int(height) + 1, int(dimension_min) + 1), max(int(height) + 2, int(dimension_max) + 20)))
        residual = float(diagonal * diagonal) - float(height * height)
        if residual <= 0.0:
            continue
        width = math.sqrt(float(residual))
        if width < 2.0:
            continue
        if not _answer_in_bounds(width, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        if abs(float(width) - float(round(width))) <= 1e-6:
            continue
        point_units = {
            "A": (0.0, 0.0),
            "B": (float(width), 0.0),
            "C": (float(width), float(height)),
            "D": (0.0, float(height)),
        }
        return _SceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(_PolygonEntitySpec("rectangle_1", "rectangle", ("A", "B", "C", "D")),),
            circle_entities=(),
            segment_entities=(_SegmentEntitySpec("diagonal_1", "diagonal", "A", "C", True),),
            annotation_specs=(
                _AnnotationSpec("known_side", "B", "C", offset_scale=0.9),
                _AnnotationSpec("diagonal", "A", "C", offset_scale=1.1),
            ),
            label_point_ids=("A", "B", "C", "D"),
            label_directions={},
            evidence_roles=("known_side", "diagonal"),
            role_values={"known_side": int(height), "diagonal": int(diagonal)},
            target_point_ids=("A", "B"),
            formula_expression="sqrt(diagonal^2 - known_side^2)",
            raw_answer_value=float(width),
        )
    raise ValueError("failed to sample rectangle_diagonal_side")


def _sample_rhombus_diagonal_side(rng, *, answer_min: int, answer_max: int, dimension_min: int, dimension_max: int) -> _SceneBlueprint:
    """Rhombus with diagonals annotated; infer one side."""
    for _ in range(500):
        diag_x = int(rng.randint(max(4, int(dimension_min)), int(dimension_max) * 2))
        diag_y = int(rng.randint(max(4, int(dimension_min)), int(dimension_max) * 2))
        answer = math.hypot(float(diag_x) / 2.0, float(diag_y) / 2.0)
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (-float(diag_x) / 2.0, 0.0),
            "B": (0.0, float(diag_y) / 2.0),
            "C": (float(diag_x) / 2.0, 0.0),
            "D": (0.0, -float(diag_y) / 2.0),
        }
        return _SceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(_PolygonEntitySpec("rhombus_1", "rhombus", ("A", "B", "C", "D")),),
            circle_entities=(),
            segment_entities=(
                _SegmentEntitySpec("diag_x_1", "diagonal", "A", "C", True),
                _SegmentEntitySpec("diag_y_1", "diagonal", "B", "D", True),
            ),
            annotation_specs=(
                _AnnotationSpec("diag_x", "A", "C", anchor_fraction=0.35, offset_scale=1.6, direction_override=(0.0, -1.0)),
                _AnnotationSpec("diag_y", "B", "D", anchor_fraction=0.35, offset_scale=1.6, direction_override=(1.0, 0.0)),
            ),
            label_point_ids=("A", "B", "C", "D"),
            label_directions={},
            evidence_roles=("diag_x", "diag_y"),
            role_values={"diag_x": int(diag_x), "diag_y": int(diag_y)},
            target_point_ids=("A", "B"),
            formula_expression="sqrt((diag_x/2)^2 + (diag_y/2)^2)",
            raw_answer_value=float(answer),
        )
    raise ValueError("failed to sample rhombus_diagonal_side")


def _sample_isosceles_trapezoid_leg(rng, *, answer_min: int, answer_max: int, dimension_min: int, dimension_max: int) -> _SceneBlueprint:
    """Isosceles trapezoid with height; infer one leg."""
    for _ in range(500):
        base_top = int(rng.randint(max(3, int(dimension_min)), int(dimension_max)))
        half_diff = int(rng.randint(1, max(2, int(dimension_max // 2))))
        base_bottom = int(base_top + (2 * half_diff))
        height = int(rng.randint(max(2, int(dimension_min // 2)), int(dimension_max)))
        answer = math.hypot(float(height), float(half_diff))
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (-float(base_bottom) / 2.0, 0.0),
            "B": (float(base_bottom) / 2.0, 0.0),
            "C": (float(base_top) / 2.0, float(height)),
            "D": (-float(base_top) / 2.0, float(height)),
            "E": (-float(base_top) / 2.0, 0.0),
        }
        return _SceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(_PolygonEntitySpec("trapezoid_1", "isosceles_trapezoid", ("A", "B", "C", "D")),),
            circle_entities=(),
            segment_entities=(_SegmentEntitySpec("height_1", "altitude", "D", "E", True),),
            annotation_specs=(
                _AnnotationSpec("base_bottom", "A", "B", offset_scale=0.9),
                _AnnotationSpec("base_top", "D", "C", offset_scale=1.15, direction_override=(0.0, -1.0)),
                _AnnotationSpec("height", "D", "E", offset_scale=1.2, direction_override=(-1.0, 0.0)),
            ),
            label_point_ids=("A", "B", "C", "D", "E"),
            label_directions={"E": (-1.0, -1.0)},
            evidence_roles=("base_bottom", "base_top", "height"),
            role_values={"base_bottom": int(base_bottom), "base_top": int(base_top), "height": int(height)},
            target_point_ids=("A", "D"),
            formula_expression="sqrt(height^2 + ((base_bottom - base_top)/2)^2)",
            raw_answer_value=float(answer),
        )
    raise ValueError("failed to sample isosceles_trapezoid_leg")


def _sample_inscribed_square_side(rng, *, answer_min: int, answer_max: int, radius_min: int, radius_max: int) -> _SceneBlueprint:
    """Square inscribed in a circle; infer the square side from a diameter."""
    for _ in range(320):
        radius = int(rng.randint(int(radius_min), int(radius_max)))
        answer = float(radius) * math.sqrt(2.0)
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (0.0, float(radius)),
            "B": (float(radius), 0.0),
            "C": (0.0, -float(radius)),
            "D": (-float(radius), 0.0),
            "O": (0.0, 0.0),
        }
        fit_points = (
            (-float(radius), -float(radius)),
            (-float(radius), float(radius)),
            (float(radius), -float(radius)),
            (float(radius), float(radius)),
        )
        return _SceneBlueprint(
            point_units=point_units,
            fit_points=fit_points,
            polygon_entities=(_PolygonEntitySpec("square_1", "square", ("A", "B", "C", "D")),),
            circle_entities=(_CircleEntitySpec("circle_1", "O", float(radius)),),
            segment_entities=(
                _SegmentEntitySpec("diameter_1", "diameter", "D", "B", True),
            ),
            annotation_specs=(
                _AnnotationSpec("diameter", "D", "B", offset_scale=1.05, direction_override=(0.0, -1.0)),
            ),
            label_point_ids=("A", "B", "C", "D"),
            label_directions={},
            evidence_roles=("diameter",),
            role_values={"diameter": int(2 * radius)},
            target_point_ids=("A", "B"),
            formula_expression="diameter / sqrt(2)",
            raw_answer_value=float(answer),
        )
    raise ValueError("failed to sample inscribed_square_side")


def _sample_circle_chord_length(rng, *, answer_min: int, answer_max: int, radius_min: int, radius_max: int) -> _SceneBlueprint:
    """Circle with center-to-chord distance; infer chord length."""
    for _ in range(500):
        radius = int(rng.randint(max(3, int(radius_min)), int(radius_max)))
        distance = int(rng.randint(1, max(1, int(radius) - 1)))
        half_chord = math.sqrt(max(1e-9, float(radius * radius) - float(distance * distance)))
        answer = 2.0 * float(half_chord)
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "O": (0.0, 0.0),
            "R": (float(radius), 0.0),
            "M": (0.0, float(distance)),
            "A": (-float(half_chord), float(distance)),
            "B": (float(half_chord), float(distance)),
        }
        fit_points = (
            (-float(radius), -float(radius)),
            (-float(radius), float(radius)),
            (float(radius), -float(radius)),
            (float(radius), float(radius)),
        )
        return _SceneBlueprint(
            point_units=point_units,
            fit_points=fit_points,
            polygon_entities=(),
            circle_entities=(_CircleEntitySpec("circle_1", "O", float(radius)),),
            segment_entities=(
                _SegmentEntitySpec("radius_1", "radius", "O", "R", True),
                _SegmentEntitySpec("distance_1", "distance_to_chord", "O", "M", True),
                _SegmentEntitySpec("chord_1", "chord", "A", "B", False),
            ),
            annotation_specs=(
                _AnnotationSpec("radius", "O", "R", anchor_fraction=0.7, offset_scale=1.15, direction_override=(0.0, 1.0)),
                _AnnotationSpec("offset", "O", "M", anchor_fraction=0.55, offset_scale=1.15, direction_override=(-1.0, 0.0)),
            ),
            label_point_ids=("O", "R", "M", "A", "B"),
            label_directions={
                "O": (-1.0, 1.0),
                "M": (1.0, 1.0),
                "R": (1.0, -1.0),
                "A": (-1.0, -1.0),
                "B": (1.0, -1.0),
            },
            evidence_roles=("radius", "offset"),
            role_values={"radius": int(radius), "offset": int(distance)},
            target_point_ids=("A", "B"),
            formula_expression="2 * sqrt(radius^2 - offset^2)",
            raw_answer_value=float(answer),
        )
    raise ValueError("failed to sample circle_chord_length")


def sample_analytical_2d_length_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    task_variant: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    fill_ratio: float,
    answer_min: int,
    answer_max: int,
) -> _RenderedCase:
    """Sample and render one analytical 2D length case for the selected variant."""
    dimension_min, dimension_max = _dimension_bounds(params, generation_defaults)
    radius_min, radius_max = _circle_radius_bounds(params, generation_defaults)
    samplers = {
        "triangle_altitude_side": lambda: _sample_triangle_altitude_side(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "rectangle_diagonal_side": lambda: _sample_rectangle_diagonal_side(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "rhombus_diagonal_side": lambda: _sample_rhombus_diagonal_side(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "isosceles_trapezoid_leg": lambda: _sample_isosceles_trapezoid_leg(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "inscribed_square_side": lambda: _sample_inscribed_square_side(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            radius_min=int(radius_min),
            radius_max=int(radius_max),
        ),
        "circle_chord_length": lambda: _sample_circle_chord_length(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            radius_min=int(radius_min),
            radius_max=int(radius_max),
        ),
    }
    if str(task_variant) not in samplers:
        raise ValueError(f"unsupported analytical 2D length task_variant: {task_variant}")
    blueprint = samplers[str(task_variant)]()
    return _render_blueprint(
        rng,
        draw,
        task_variant=str(task_variant),
        blueprint=blueprint,
        context=context,
        shape_style=shape_style,
        line_width=int(line_width),
        helper_line_width=int(helper_line_width),
        label_offset_px=float(label_offset_px),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
        fill_ratio=float(fill_ratio),
    )


@register_task
class GeometryAnalyticalLength2DTask:
    """Compute derived length values from annotated analytical 2D scenes."""

    task_id = "task_geometry_analytical_2d_length"
    domain = "geometry"
    task_group = "analytical_2d"

    def _complexity(self, *, task_variant: str, answer_scalar: int, answer_max: int) -> TaskComplexity:
        """Compute complexity from variant family and answer magnitude."""
        variant_weight = {
            "triangle_altitude_side": 0.42,
            "rectangle_diagonal_side": 0.38,
            "rhombus_diagonal_side": 0.48,
            "isosceles_trapezoid_leg": 0.52,
            "inscribed_square_side": 0.56,
            "circle_chord_length": 0.60,
        }.get(str(task_variant), 0.5)
        magnitude = 0.0
        if int(answer_max) > 0:
            magnitude = min(1.0, float(answer_scalar) / float(max(1, int(answer_max) * 10)))
        score = max(0.0, min(1.0, 0.32 + (0.52 * float(variant_weight)) + (0.16 * float(magnitude))))
        return TaskComplexity(
            complexity_score=float(score),
            complexity_components={
                "task_variant": str(task_variant),
                "answer_scalar": int(answer_scalar),
                "variant_component": float(variant_weight),
                "magnitude_component": float(magnitude),
            },
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic analytical 2D length instance."""
        task_group_defaults = get_task_group_defaults(self.domain, self.task_group)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
        )
        answer_min, answer_max = resolve_answer_bounds(
            params,
            gen_defaults=gen_defaults,
            task_id=str(self.task_id),
            fallback_min=3,
            fallback_max=100,
        )
        scene_rng = spawn_rng(int(instance_seed), "scene")
        task_variant, variant_probabilities = resolve_task_variant(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            supported_variants=LENGTH_VARIANTS,
        )
        context_params = dict(params)
        line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="line_width",
            fallback=int(ANALYTICAL_SHARED_DEFAULTS.line_width),
            min_key="line_width_min",
            max_key="line_width_max",
            minimum_value=1,
        )
        helper_line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="helper_line_width",
            fallback=int(ANALYTICAL_SHARED_DEFAULTS.helper_line_width),
            min_key="helper_line_width_min",
            max_key="helper_line_width_max",
            minimum_value=1,
        )
        label_stroke_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="label_stroke_width",
            fallback=int(ANALYTICAL_SHARED_DEFAULTS.label_stroke_width),
            min_key="label_stroke_width_min",
            max_key="label_stroke_width_max",
            minimum_value=1,
        )
        fill_ratio = float(group_default(render_defaults, "analytical_scene_fill_ratio", 0.74))

        attempt_budget = max(1, int(max_attempts))
        context: GraphSceneContext | None = None
        image = None
        background_meta: Dict[str, Any] = {}
        shape_style = None
        case = None
        last_error: Exception | None = None

        for _ in range(int(attempt_budget)):
            try:
                context = resolve_graph_scene_context(
                    scene_rng,
                    params=context_params,
                    render_defaults=render_defaults,
                    background_defaults=ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS,
                    fallback_canvas_min=ANALYTICAL_SHARED_DEFAULTS.canvas_size_min,
                    fallback_canvas_max=ANALYTICAL_SHARED_DEFAULTS.canvas_size_max,
                    fallback_cells_min=ANALYTICAL_SHARED_DEFAULTS.graph_cells_min,
                    fallback_cells_max=ANALYTICAL_SHARED_DEFAULTS.graph_cells_max,
                    require_graph_paper_background=False,
                )
                label_offset_px = float(group_default(render_defaults, "label_offset_px", ANALYTICAL_SHARED_DEFAULTS.label_offset_px))
                label_font_size_px = resolve_scene_label_font_size_px(
                    canvas_size=int(context.canvas_size),
                    graph_spacing=int(_analytical_unit_spacing_px(context)),
                    scene_scale=int(context.scene_scale),
                    min_px=int(group_default(render_defaults, "label_font_size_min", ANALYTICAL_SHARED_DEFAULTS.label_font_size_min)),
                    max_px=int(group_default(render_defaults, "label_font_size_max", ANALYTICAL_SHARED_DEFAULTS.label_font_size_max)),
                )
                image, draw, background_meta = make_graph_scene_canvas(
                    instance_seed=int(instance_seed),
                    context=context,
                    background_defaults=ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS,
                    require_graph_paper=False,
                )
                shape_style = sample_geometry_shape_style(
                    scene_rng,
                    params=context_params,
                    render_defaults=render_defaults,
                    anchor_colors=extract_background_anchor_colors(background_meta),
                )
                case = sample_analytical_2d_length_case(
                    scene_rng,
                    draw,
                    task_variant=str(task_variant),
                    params=params,
                    generation_defaults=gen_defaults,
                    context=context,
                    shape_style=shape_style,
                    line_width=int(line_width),
                    helper_line_width=int(helper_line_width),
                    label_offset_px=float(label_offset_px),
                    label_font_size_px=int(label_font_size_px),
                    label_stroke_width=int(label_stroke_width),
                    fill_ratio=float(fill_ratio),
                    answer_min=int(answer_min),
                    answer_max=int(answer_max),
                )
                break
            except Exception as exc:
                last_error = exc
                context = None
                image = None
                shape_style = None
                case = None
                continue

        if case is None or context is None or image is None or shape_style is None:
            raise RuntimeError("failed to generate task_geometry_analytical_2d_length instance") from last_error

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=ANALYTICAL_POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_required = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "evidence_hint_measurement_map",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        required_annotations = [
            str(case.role_tokens[role])
            for role in case.evidence_roles
            if str(role) in case.role_tokens
        ]
        evidence_hint_base = str(prompt_required["evidence_hint_measurement_map"]).strip()
        if evidence_hint_base and evidence_hint_base[-1] not in {".", "!", "?", ":", ";"}:
            evidence_hint_base = f"{evidence_hint_base}."
        evidence_hint = (
            f"{evidence_hint_base} Required annotations: {', '.join(required_annotations)}"
            if evidence_hint_base
            else f"Required annotations: {', '.join(required_annotations)}"
        )
        question_template = required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"question_text_{case.task_variant}", "question_text"),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = str(question_template).format(target_annotation=str(case.target_annotation))
        answer_hint = required_prompt_text(
            prompt_defaults,
            preferred_keys=("answer_hint_number", "answer_hint"),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=case.evidence_map,
            answer_type="number",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_required["bundle_id"]),
            task_family_key=str(prompt_required["task_family_key"]),
            task_key=str(prompt_required["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_required["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_required["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_required["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="number", value=float(case.answer_value))
        evidence_gt = TypedValue(type="measurement_ref_map", value=dict(case.evidence_map))
        complexity = self._complexity(
            task_variant=str(case.task_variant),
            answer_scalar=int(case.answer_scalar),
            answer_max=int(answer_max),
        )
        projected_point_set = [
            [float(case.annotation_centers[label][0]), float(case.annotation_centers[label][1])]
            for label in required_annotations
            if label in case.annotation_centers
        ]
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_2d_analytical_length",
                "entities": [dict(entity) for entity in case.entities],
                "relations": {},
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "graph_unit": {
                        "origin_pixel": list(context.graph_frame["origin_pixel"]),
                        "spacing_px": int(context.graph_frame["spacing_px"]),
                        "x_positive": str(context.graph_frame["x_positive"]),
                        "y_positive": str(context.graph_frame["y_positive"]),
                    },
                },
            },
            "query_spec": {
                "task_variant": str(case.task_variant),
                "template_id": str(prompt_required["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(case.task_variant),
                    "variant_probabilities": dict(variant_probabilities),
                    "answer_min": int(answer_min),
                    "answer_max": int(answer_max),
                },
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
            },
            "render_map": {
                "instance_anchor": dict(case.render_anchor),
                "annotation_labels": dict(case.role_tokens),
                "annotation_centers": dict(case.annotation_centers),
                "coord_space": "pixel",
            },
            "execution_trace": {
                "task_variant": str(case.task_variant),
                "formula_expression": str(case.formula_expression),
                "answer_type": "number",
                "raw_answer_value": float(case.raw_answer_value),
                "answer_scalar": int(case.answer_scalar),
                "answer_value": float(case.answer_value),
                "target_annotation": str(case.target_annotation),
                "evidence_roles": list(case.evidence_roles),
                "required_annotations": list(required_annotations),
                "evidence_role_values": dict(case.role_values),
                "evidence_role_tokens": dict(case.role_tokens),
                "evidence_map": dict(case.evidence_map),
                "variant_probabilities": dict(variant_probabilities),
                "answer_min": int(answer_min),
                "answer_max": int(answer_max),
            },
            "witness_symbolic": {
                "type": "annotation_measurement_map",
                "task_variant": str(case.task_variant),
                "formula_expression": str(case.formula_expression),
                "annotation_ids": list(required_annotations),
                "annotation_values": dict(case.evidence_map),
                "annotation_labels": dict(case.role_tokens),
                "measurement_ref_map": dict(case.evidence_map),
            },
            "projected_evidence": {
                "measurement_ref_map": dict(case.evidence_map),
                "id_set": list(required_annotations),
                "pixel_point_set": list(projected_point_set),
                "annotation_labels": dict(case.role_tokens),
                "pixel_annotation_centers": dict(case.annotation_centers),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img_0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(case.task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
