"""Shared rendering helpers for annotated analytical 2D geometry scenes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...shared.text_rendering import draw_text_centered, load_font
from .annotation_values import build_role_value_evidence, format_annotation_value
from .conic_geometry import draw_circle_outline
from .graph_rendering import scale_point
from .polygon_geometry import alphabetic_labels
from .shape_style import GeometryShapeStyle
from .single_object_scene import GraphSceneContext

Point = Tuple[float, float]
Segment = Tuple[Point, Point]


@dataclass(frozen=True)
class Analytical2DAnnotationSpec:
    """One numeric measurement annotation anchored to a segment."""

    role: str
    point_a_id: str
    point_b_id: str
    anchor_fraction: float = 0.5
    offset_scale: float = 1.0
    direction_override: Point | None = None


@dataclass(frozen=True)
class Analytical2DPolygonEntitySpec:
    """One polygon-like rendered entity."""

    entity_id: str
    entity_type: str
    point_ids: Tuple[str, ...]


@dataclass(frozen=True)
class Analytical2DCircleEntitySpec:
    """One circle rendered entity."""

    entity_id: str
    center_id: str
    radius_units: float


@dataclass(frozen=True)
class Analytical2DSegmentEntitySpec:
    """One standalone rendered segment, visible or helper."""

    entity_id: str
    entity_type: str
    point_a_id: str
    point_b_id: str
    helper: bool = False


@dataclass(frozen=True)
class Analytical2DSceneBlueprint:
    """Variant-specific analytical 2D scene definition before pixel rendering."""

    point_units: Dict[str, Point]
    fit_points: Tuple[Point, ...]
    polygon_entities: Tuple[Analytical2DPolygonEntitySpec, ...]
    circle_entities: Tuple[Analytical2DCircleEntitySpec, ...]
    segment_entities: Tuple[Analytical2DSegmentEntitySpec, ...]
    annotation_specs: Tuple[Analytical2DAnnotationSpec, ...]
    label_point_ids: Tuple[str, ...]
    label_directions: Dict[str, Point]
    evidence_roles: Tuple[str, ...]
    role_values: Dict[str, Any]


@dataclass(frozen=True)
class Analytical2DRenderedScene:
    """Rendered analytical 2D scene payload reused by sibling tasks."""

    point_labels: Dict[str, str]
    role_tokens: Dict[str, str]
    evidence_map: Dict[str, Any]
    annotation_centers: Dict[str, List[float]]
    entities: List[Dict[str, Any]]
    render_anchor: Dict[str, Any]


def analytical_unit_spacing_px(context: GraphSceneContext) -> int:
    """Return preferred unit spacing for analytical 2D scenes."""
    raw_value = context.render_params.get("analytical_unit_spacing_px", context.graph_spacing)
    spacing_px = int(raw_value)
    if int(spacing_px) < 2:
        raise ValueError("analytical_unit_spacing_px must be >= 2")
    return int(spacing_px)


def analytical_unit_padding_px(context: GraphSceneContext) -> int:
    """Return reserved border padding for analytical 2D scenes."""
    raw_value = context.render_params.get("analytical_unit_padding_px", 20)
    padding_px = int(raw_value)
    if int(padding_px) < 0:
        raise ValueError("analytical_unit_padding_px must be >= 0")
    return int(padding_px)


def normalize_direction(vector: Point) -> Point:
    """Return one normalized direction vector or a stable fallback."""
    norm = math.hypot(float(vector[0]), float(vector[1]))
    if norm <= 1e-9:
        return (1.0, -1.0)
    return (float(vector[0]) / float(norm), float(vector[1]) / float(norm))


def midpoint(point_a: Point, point_b: Point, *, fraction: float = 0.5) -> Point:
    """Return one interpolated point on a segment."""
    frac = max(0.0, min(1.0, float(fraction)))
    return (
        float(point_a[0]) + (float(point_b[0]) - float(point_a[0])) * float(frac),
        float(point_a[1]) + (float(point_b[1]) - float(point_a[1])) * float(frac),
    )


def polygon_centroid(points: Sequence[Point]) -> Point:
    """Return arithmetic centroid for a non-empty point sequence."""
    return (
        float(sum(float(point[0]) for point in points) / float(len(points))),
        float(sum(float(point[1]) for point in points) / float(len(points))),
    )


def segment_direction(point_a: Point, point_b: Point) -> Point:
    """Return one perpendicular annotation direction for a segment."""
    return normalize_direction((-(float(point_b[1]) - float(point_a[1])), float(point_b[0]) - float(point_a[0])))


def annotation_token(point_labels: Mapping[str, str], point_a_id: str, point_b_id: str) -> str:
    """Return one endpoint token such as `AB`."""
    return f"{point_labels[str(point_a_id)]}{point_labels[str(point_b_id)]}"


def fit_points_to_canvas(
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
    padding_px = float(analytical_unit_padding_px(context))
    preferred_spacing = float(analytical_unit_spacing_px(context))
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


def transform_point(point: Point, *, scale: float, offset_x: float, offset_y: float) -> Point:
    """Map one analytical-unit point into pixel coordinates."""
    return (
        float(offset_x) + (float(point[0]) * float(scale)),
        float(offset_y) - (float(point[1]) * float(scale)),
    )


def _assign_point_labels(rng, point_ids: Sequence[str]) -> Dict[str, str]:
    """Assign deterministic alphabetic point labels to named point ids."""
    ids = [str(point_id) for point_id in point_ids]
    labels = alphabetic_labels(len(ids), start_index=int(rng.randrange(26)))
    return {str(point_id): str(label) for point_id, label in zip(ids, labels)}


def _draw_polygon_outline(draw: ImageDraw.ImageDraw, points: Sequence[Point], *, width: int, fill: Tuple[int, int, int]) -> None:
    """Draw one closed polygon outline."""
    polyline = [tuple((float(point[0]), float(point[1]))) for point in points]
    if len(polyline) < 2:
        return
    draw.line([*polyline, polyline[0]], fill=tuple(int(value) for value in fill), width=max(1, int(width)), joint="curve")


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
    """Resolve one nearby text center while keeping analytical labels local."""
    text_bbox = draw.textbbox((0.0, 0.0), str(text), font=font, stroke_width=int(stroke_width))
    width = max(1.0, float(text_bbox[2]) - float(text_bbox[0]))
    height = max(1.0, float(text_bbox[3]) - float(text_bbox[1]))
    base = normalize_direction(base_direction)
    left = normalize_direction((-float(base[1]), float(base[0])))
    right = normalize_direction((float(base[1]), -float(base[0])))
    opposite = normalize_direction((-float(base[0]), -float(base[1])))
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


def _draw_measurement_annotations(
    draw: ImageDraw.ImageDraw,
    *,
    point_positions: Mapping[str, Point],
    point_labels: Mapping[str, str],
    annotations: Sequence[Analytical2DAnnotationSpec],
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
    centroid = polygon_centroid(list(point_positions.values()))
    for annotation in annotations:
        point_a = point_positions[str(annotation.point_a_id)]
        point_b = point_positions[str(annotation.point_b_id)]
        token = annotation_token(point_labels, str(annotation.point_a_id), str(annotation.point_b_id))
        role_tokens[str(annotation.role)] = str(token)
        mid = midpoint(point_a, point_b, fraction=float(annotation.anchor_fraction))
        direction = annotation.direction_override
        if direction is None:
            direction = segment_direction(point_a, point_b)
            outward = (float(mid[0]) - float(centroid[0]), float(mid[1]) - float(centroid[1]))
            if (float(direction[0]) * float(outward[0])) + (float(direction[1]) * float(outward[1])) < 0.0:
                direction = (-float(direction[0]), -float(direction[1]))
        direction = normalize_direction(direction)
        scaled_anchor = scale_point((float(mid[0]), float(mid[1])), int(scene_scale))
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
    centroid = polygon_centroid(list(point_positions.values()))
    occupied_padding = max(4.0, 2.0 * float(scene_scale))
    blocked_scaled = [
        (
            scale_point((float(seg_a[0]), float(seg_a[1])), int(scene_scale)),
            scale_point((float(seg_b[0]), float(seg_b[1])), int(scene_scale)),
        )
        for seg_a, seg_b in blocked_segments
    ]
    for point_id, label in point_labels.items():
        point = point_positions[str(point_id)]
        direction = label_directions.get(str(point_id), (float(point[0]) - float(centroid[0]), float(point[1]) - float(centroid[1])))
        direction = normalize_direction(direction)
        scaled_anchor = scale_point((float(point[0]), float(point[1])), int(scene_scale))
        center, bbox = _resolve_local_text_center(
            draw,
            text=str(label),
            anchor=(float(scaled_anchor[0]), float(scaled_anchor[1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(max(10.0, float(label_offset_px))),
            font=font,
            blocked_segments=blocked_scaled,
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


def render_analytical_2d_scene(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    blueprint: Analytical2DSceneBlueprint,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    fill_ratio: float,
) -> Analytical2DRenderedScene:
    """Render one analytical 2D scene and build shared evidence payloads."""
    scale, offset_x, offset_y = fit_points_to_canvas(
        rng,
        points=blueprint.fit_points,
        context=context,
        fill_ratio=float(fill_ratio),
    )
    point_positions = {
        str(point_id): transform_point(point, scale=float(scale), offset_x=float(offset_x), offset_y=float(offset_y))
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
        blocked_segments.extend((points[index], points[(index + 1) % len(points)]) for index in range(len(points)))
        entities.append(
            {
                "entity_id": str(polygon.entity_id),
                "entity_type": str(polygon.entity_type),
                "attrs": {"vertices": [[float(point[0]), float(point[1])] for point in points]},
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
                "attrs": {"center": [float(center[0]), float(center[1])], "radius_px": int(radius_px)},
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
    xs = [float(point[0]) for point in point_positions.values()]
    ys = [float(point[1]) for point in point_positions.values()]
    return Analytical2DRenderedScene(
        point_labels=dict(point_labels),
        role_tokens=dict(role_tokens),
        evidence_map=dict(evidence_map),
        annotation_centers=dict(annotation_centers),
        entities=entities,
        render_anchor={"bbox": [min(xs), min(ys), max(xs), max(ys)], "coord_space": "pixel"},
    )


__all__ = [
    "Analytical2DAnnotationSpec",
    "Analytical2DCircleEntitySpec",
    "Analytical2DPolygonEntitySpec",
    "Analytical2DRenderedScene",
    "Analytical2DSceneBlueprint",
    "Analytical2DSegmentEntitySpec",
    "Point",
    "Segment",
    "analytical_unit_padding_px",
    "analytical_unit_spacing_px",
    "annotation_token",
    "fit_points_to_canvas",
    "midpoint",
    "normalize_direction",
    "polygon_centroid",
    "render_analytical_2d_scene",
    "segment_direction",
    "transform_point",
]
