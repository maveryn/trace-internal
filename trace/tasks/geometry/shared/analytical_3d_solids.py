"""Reusable 3D analytical-solid sampling and wireframe rendering helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...shared.isometric_projection import iso_project_point_3d as shared_iso_project_point_3d
from ...shared.config_defaults import group_default
from ...shared.text_rendering import (
    draw_text_centered,
    load_font,
    resolve_text_label_center,
)
from .annotation_values import build_role_value_evidence, format_annotation_value
from .polygon_geometry import alphabetic_labels
from .shape_style import GeometryShapeStyle

Point = Tuple[float, float]
Point3 = Tuple[float, float, float]
Segment = Tuple[Point, Point]

VOLUME_VARIANTS: Tuple[str, ...] = (
    "rectangular_prism_given_lwh",
    "triangular_prism_given_b_h_l",
    "square_pyramid_given_base_height",
    "cylinder_given_r_h",
    "cone_given_r_h",
    "sphere_given_r",
)

INTEGER_VOLUME_VARIANTS = {
    "rectangular_prism_given_lwh",
    "triangular_prism_given_b_h_l",
    "square_pyramid_given_base_height",
}

PI_VOLUME_VARIANTS = {
    "cylinder_given_r_h",
    "cone_given_r_h",
    "sphere_given_r",
}

SURFACE_AREA_VARIANTS: Tuple[str, ...] = (
    "rectangular_prism_given_lwh",
    "triangular_prism_given_a_b_c_l",
    "square_pyramid_given_base_side_slant_height",
    "cylinder_given_r_h",
    "cone_given_r_slant_height",
    "sphere_given_r",
)

INTEGER_SURFACE_AREA_VARIANTS = {
    "rectangular_prism_given_lwh",
    "triangular_prism_given_a_b_c_l",
    "square_pyramid_given_base_side_slant_height",
}

PI_SURFACE_AREA_VARIANTS = {
    "cylinder_given_r_h",
    "cone_given_r_slant_height",
    "sphere_given_r",
}


@dataclass(frozen=True)
class _AnnotationSegment:
    """One measurement annotation segment for value/evidence extraction."""

    role: str
    value: int
    point_a: Point
    point_b: Point
    direction: Point | None = None
    offset_scale: float = 1.0


@dataclass(frozen=True)
class Analytical3DSolidCase:
    """Fully rendered 3D analytical solid case payload."""

    task_variant: str
    answer_type: str
    answer_scalar: int
    answer_value: int | str
    formula_expression: str
    evidence_roles: Tuple[str, ...]
    role_values: Dict[str, Any]
    role_tokens: Dict[str, str]
    evidence_map: Dict[str, Any]
    annotation_centers: Dict[str, List[float]]
    entity: Dict[str, Any]
    render_anchor: Dict[str, Any]


def _pi_expression(value: int) -> str:
    """Format one integer coefficient as canonical `kπ` text."""
    coefficient = int(value)
    if int(coefficient) == 1:
        return "π"
    return f"{int(coefficient)}π"


def iso_project_point_3d(point_3d: Point3) -> Point:
    """Project one 3D point to an isometric 2D plane."""
    return tuple(float(value) for value in shared_iso_project_point_3d(point_3d))


def _iso_project(point_3d: Point3) -> Point:
    """Backward-compatible private alias for the shared 3D isometric projection."""

    return iso_project_point_3d(point_3d)


def _fit_projected_points(
    points_3d: Mapping[str, Point3],
    *,
    canvas_size: int,
    margin_px: float,
) -> Dict[str, Point]:
    """Project and fit one 3D point map into a square canvas."""
    raw_points = {str(key): iso_project_point_3d(point) for key, point in points_3d.items()}
    x_values = [float(point[0]) for point in raw_points.values()]
    y_values = [float(point[1]) for point in raw_points.values()]
    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)
    raw_width = max(1e-6, float(max_x - min_x))
    raw_height = max(1e-6, float(max_y - min_y))
    side = float(max(1, int(canvas_size)))
    margin = float(max(8.0, min(float(margin_px), 0.45 * side)))
    usable_side = max(16.0, side - (2.0 * margin))
    scale = min(float(usable_side / raw_width), float(usable_side / raw_height))
    center_x_raw = 0.5 * (float(min_x) + float(max_x))
    center_y_raw = 0.5 * (float(min_y) + float(max_y))
    center_canvas = 0.5 * side
    return {
        str(key): (
            float((float(point[0]) - float(center_x_raw)) * float(scale) + float(center_canvas)),
            float((float(point[1]) - float(center_y_raw)) * float(scale) + float(center_canvas)),
        )
        for key, point in raw_points.items()
    }


def _point_key(point: Point, *, scale: int = 1000) -> Tuple[int, int]:
    """Return one hashable key for point-equivalence under small float noise."""
    return (
        int(round(float(point[0]) * float(scale))),
        int(round(float(point[1]) * float(scale))),
    )


def _scale_point(point: Point, scene_scale: int) -> Point:
    """Scale one point by scene supersample factor."""
    return (float(point[0]) * float(scene_scale), float(point[1]) * float(scene_scale))


def _segment_midpoint(segment: Segment) -> Point:
    """Return midpoint of one segment."""
    point_a, point_b = segment
    return (
        0.5 * (float(point_a[0]) + float(point_b[0])),
        0.5 * (float(point_a[1]) + float(point_b[1])),
    )


def _segment_perpendicular(segment: Segment) -> Point:
    """Return one perpendicular direction for a segment."""
    point_a, point_b = segment
    dx = float(point_b[0]) - float(point_a[0])
    dy = float(point_b[1]) - float(point_a[1])
    if abs(float(dx)) + abs(float(dy)) <= 1e-9:
        return (1.0, -1.0)
    return (-float(dy), float(dx))


def _draw_segments(
    draw: ImageDraw.ImageDraw,
    *,
    segments: Sequence[Segment],
    scene_scale: int,
    color: Tuple[int, int, int],
    line_width: int,
) -> None:
    """Draw a sequence of segments in scaled render space."""
    for point_a, point_b in segments:
        draw.line(
            [_scale_point(point_a, int(scene_scale)), _scale_point(point_b, int(scene_scale))],
            fill=tuple(int(value) for value in color),
            width=max(1, int(line_width) * int(scene_scale)),
        )


def _draw_ellipse_outline(
    draw: ImageDraw.ImageDraw,
    *,
    center: Point,
    radius_x: float,
    radius_y: float,
    scene_scale: int,
    color: Tuple[int, int, int],
    line_width: int,
) -> None:
    """Draw one ellipse outline in scaled render space."""
    center_scaled = _scale_point((float(center[0]), float(center[1])), int(scene_scale))
    radius_x_scaled = float(radius_x) * float(scene_scale)
    radius_y_scaled = float(radius_y) * float(scene_scale)
    draw.ellipse(
        [
            float(center_scaled[0] - radius_x_scaled),
            float(center_scaled[1] - radius_y_scaled),
            float(center_scaled[0] + radius_x_scaled),
            float(center_scaled[1] + radius_y_scaled),
        ],
        outline=tuple(int(value) for value in color),
        width=max(1, int(line_width) * int(scene_scale)),
    )


def _assign_annotation_tokens(
    rng,
    *,
    annotations: Sequence[_AnnotationSegment],
) -> Tuple[Dict[str, str], Dict[str, Point]]:
    """Assign deterministic endpoint labels and derive annotation tokens."""
    point_by_key: Dict[Tuple[int, int], Point] = {}
    ordered_keys: List[Tuple[int, int]] = []
    for annotation in annotations:
        for point in (annotation.point_a, annotation.point_b):
            key = _point_key((float(point[0]), float(point[1])))
            if key not in point_by_key:
                point_by_key[key] = (float(point[0]), float(point[1]))
                ordered_keys.append(key)
    labels = alphabetic_labels(len(ordered_keys), start_index=int(rng.randrange(26)))
    point_label = {key: str(label) for key, label in zip(ordered_keys, labels)}
    role_to_token: Dict[str, str] = {}
    for annotation in annotations:
        key_a = _point_key((float(annotation.point_a[0]), float(annotation.point_a[1])))
        key_b = _point_key((float(annotation.point_b[0]), float(annotation.point_b[1])))
        role_to_token[str(annotation.role)] = f"{point_label[key_a]}{point_label[key_b]}"
    label_positions = {str(point_label[key]): (float(point_by_key[key][0]), float(point_by_key[key][1])) for key in ordered_keys}
    return dict(role_to_token), dict(label_positions)


def _draw_annotation_text(
    draw: ImageDraw.ImageDraw,
    *,
    annotations: Sequence[_AnnotationSegment],
    role_to_token: Mapping[str, str],
    blocked_segments: Sequence[Segment],
    occupied_boxes: Sequence[Tuple[float, float, float, float]],
    scene_scale: int,
    canvas_size: int,
    shape_style: GeometryShapeStyle,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
) -> Dict[str, List[float]]:
    """Draw numeric annotation text and return annotation centers by token."""
    stroke_width = max(1, int(label_stroke_width))
    font = load_font(int(label_font_size_px), bold=True)
    blocked_scaled = [
        (_scale_point((float(seg_a[0]), float(seg_a[1])), int(scene_scale)), _scale_point((float(seg_b[0]), float(seg_b[1])), int(scene_scale)))
        for seg_a, seg_b in blocked_segments
    ]
    occupied: List[Tuple[float, float, float, float]] = list(occupied_boxes)
    centers_by_token: Dict[str, List[float]] = {}
    for annotation in annotations:
        token = str(role_to_token[str(annotation.role)])
        text = format_annotation_value(annotation.value)
        segment = (
            (float(annotation.point_a[0]), float(annotation.point_a[1])),
            (float(annotation.point_b[0]), float(annotation.point_b[1])),
        )
        midpoint = _segment_midpoint(segment)
        direction = annotation.direction if annotation.direction is not None else _segment_perpendicular(segment)
        scaled_anchor = _scale_point(midpoint, int(scene_scale))
        center, bbox = resolve_text_label_center(
            draw,
            text=str(text),
            anchor=(float(scaled_anchor[0]), float(scaled_anchor[1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(max(10.0, float(label_offset_px) * float(annotation.offset_scale))),
            font=font,
            blocked_segments=blocked_scaled,
            occupied_boxes=occupied,
            stroke_width=int(stroke_width),
            line_clearance_px=max(3.0, 2.0 * float(scene_scale)),
            canvas_size=int(canvas_size) * int(scene_scale),
        )
        draw_text_centered(
            draw,
            text=str(text),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(stroke_width),
        )
        centers_by_token[str(token)] = [
            float(center[0]) / float(scene_scale),
            float(center[1]) / float(scene_scale),
        ]
        padding = max(3.0, 1.6 * float(scene_scale))
        occupied.append(
            (
                float(bbox[0]) - float(padding),
                float(bbox[1]) - float(padding),
                float(bbox[2]) + float(padding),
                float(bbox[3]) + float(padding),
            )
        )
    return dict(centers_by_token)


def _draw_endpoint_labels(
    draw: ImageDraw.ImageDraw,
    *,
    label_positions: Mapping[str, Point],
    blocked_segments: Sequence[Segment],
    scene_scale: int,
    canvas_size: int,
    shape_style: GeometryShapeStyle,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
) -> List[Tuple[float, float, float, float]]:
    """Draw endpoint labels for annotation-token grounding and return occupied boxes."""
    stroke_width = max(1, int(label_stroke_width))
    font = load_font(int(label_font_size_px), bold=True)
    blocked_scaled = [
        (_scale_point((float(seg_a[0]), float(seg_a[1])), int(scene_scale)), _scale_point((float(seg_b[0]), float(seg_b[1])), int(scene_scale)))
        for seg_a, seg_b in blocked_segments
    ]
    occupied: List[Tuple[float, float, float, float]] = []
    canvas_center = (
        0.5 * float(int(canvas_size) * int(scene_scale)),
        0.5 * float(int(canvas_size) * int(scene_scale)),
    )
    for label, point in sorted(label_positions.items()):
        scaled_anchor = _scale_point((float(point[0]), float(point[1])), int(scene_scale))
        direction = (
            float(scaled_anchor[0]) - float(canvas_center[0]),
            float(scaled_anchor[1]) - float(canvas_center[1]),
        )
        if abs(float(direction[0])) + abs(float(direction[1])) <= 1e-6:
            direction = (1.0, -1.0)
        center, bbox = resolve_text_label_center(
            draw,
            text=str(label),
            anchor=(float(scaled_anchor[0]), float(scaled_anchor[1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(max(10.0, float(label_offset_px))),
            font=font,
            blocked_segments=blocked_scaled,
            occupied_boxes=occupied,
            stroke_width=int(stroke_width),
            line_clearance_px=max(3.0, 2.0 * float(scene_scale)),
            canvas_size=int(canvas_size) * int(scene_scale),
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
        padding = max(3.0, 1.6 * float(scene_scale))
        occupied.append(
            (
                float(bbox[0]) - float(padding),
                float(bbox[1]) - float(padding),
                float(bbox[2]) + float(padding),
                float(bbox[3]) + float(padding),
            )
        )
    return occupied


def _render_annotations_and_evidence(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    annotations: Sequence[_AnnotationSegment],
    blocked_segments: Sequence[Segment],
    scene_scale: int,
    canvas_size: int,
    shape_style: GeometryShapeStyle,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, List[float]]]:
    """Render annotation text and build evidence map/token metadata."""
    role_to_token, label_positions = _assign_annotation_tokens(rng, annotations=annotations)
    role_values = {str(annotation.role): int(annotation.value) for annotation in annotations}
    evidence_roles = [str(annotation.role) for annotation in annotations]
    evidence_map = build_role_value_evidence(
        roles=evidence_roles,
        role_to_annotation=role_to_token,
        role_to_value=role_values,
    )
    occupied_boxes = _draw_endpoint_labels(
        draw,
        label_positions=label_positions,
        blocked_segments=blocked_segments,
        scene_scale=int(scene_scale),
        canvas_size=int(canvas_size),
        shape_style=shape_style,
        label_offset_px=float(label_offset_px),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
    )
    annotation_centers = _draw_annotation_text(
        draw,
        annotations=annotations,
        role_to_token=role_to_token,
        blocked_segments=blocked_segments,
        occupied_boxes=occupied_boxes,
        scene_scale=int(scene_scale),
        canvas_size=int(canvas_size),
        shape_style=shape_style,
        label_offset_px=float(label_offset_px),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
    )
    return dict(evidence_map), dict(role_to_token), dict(annotation_centers)


def _render_anchor_from_points(points: Mapping[str, Point]) -> Dict[str, Any]:
    """Build a deterministic render anchor from projected points."""
    values = [list((float(point[0]), float(point[1]))) for key, point in sorted(points.items())]
    center_x = float(sum(point[0] for point in values) / float(len(values)))
    center_y = float(sum(point[1] for point in values) / float(len(values)))
    return {
        "point": [float(center_x), float(center_y)],
        "polyline": values,
        "coord_space": "pixel",
    }


def _dimension_bounds(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> Tuple[int, int, int, int, int, int]:
    """Resolve integer dimension/radius bounds from params/defaults."""
    dimension_min = int(params.get("dimension_min", group_default(generation_defaults, "dimension_min", 2)))
    dimension_max = int(params.get("dimension_max", group_default(generation_defaults, "dimension_max", 10)))
    radius_min = int(params.get("radius_min", group_default(generation_defaults, "radius_min", 2)))
    radius_max = int(params.get("radius_max", group_default(generation_defaults, "radius_max", 8)))
    sphere_radius_min = int(
        params.get("sphere_radius_min", group_default(generation_defaults, "sphere_radius_min", 3))
    )
    sphere_radius_max = int(
        params.get("sphere_radius_max", group_default(generation_defaults, "sphere_radius_max", 9))
    )
    if int(dimension_min) > int(dimension_max):
        raise ValueError("dimension_min must be <= dimension_max")
    if int(radius_min) > int(radius_max):
        raise ValueError("radius_min must be <= radius_max")
    if int(sphere_radius_min) > int(sphere_radius_max):
        raise ValueError("sphere_radius_min must be <= sphere_radius_max")
    return (
        int(dimension_min),
        int(dimension_max),
        int(radius_min),
        int(radius_max),
        int(sphere_radius_min),
        int(sphere_radius_max),
    )


def _right_triangle_leg_triples(
    *,
    min_leg: int,
    max_leg: int,
) -> List[Tuple[int, int, int]]:
    """Return right-triangle leg triples constrained to the configured dimension range."""
    triples: List[Tuple[int, int, int]] = []
    for leg_a in range(int(min_leg), int(max_leg) + 1):
        for leg_b in range(int(leg_a), int(max_leg) + 1):
            hyp_sq = (int(leg_a) * int(leg_a)) + (int(leg_b) * int(leg_b))
            hyp = int(math.isqrt(int(hyp_sq)))
            if int(hyp) * int(hyp) != int(hyp_sq):
                continue
            if int(hyp) > int(max_leg):
                continue
            triples.append((int(leg_a), int(leg_b), int(hyp)))
    return triples


def _sample_rectangular_prism_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render rectangular-prism volume case."""
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(260):
        length_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        width_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        height_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        volume = int(length_units * width_units * height_units)
        if int(volume) < int(answer_min) or int(volume) > int(answer_max):
            continue
        points_3d = {
            "A": (0.0, 0.0, 0.0),
            "B": (float(length_units), 0.0, 0.0),
            "C": (float(length_units), float(width_units), 0.0),
            "D": (0.0, float(width_units), 0.0),
            "E": (0.0, 0.0, float(height_units)),
            "F": (float(length_units), 0.0, float(height_units)),
            "G": (float(length_units), float(width_units), float(height_units)),
            "H": (0.0, float(width_units), float(height_units)),
        }
        points_2d = _fit_projected_points(points_3d, canvas_size=int(canvas_size), margin_px=36.0)
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "A"),
            ("E", "F"),
            ("F", "G"),
            ("G", "H"),
            ("H", "E"),
            ("A", "E"),
            ("B", "F"),
            ("C", "G"),
            ("D", "H"),
        ]
        segments = [((float(points_2d[a][0]), float(points_2d[a][1])), (float(points_2d[b][0]), float(points_2d[b][1]))) for a, b in edges]
        _draw_segments(
            draw,
            segments=segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        annotations = [
            _AnnotationSegment(
                role="l",
                value=int(length_units),
                point_a=points_2d["A"],
                point_b=points_2d["B"],
            ),
            _AnnotationSegment(
                role="w",
                value=int(width_units),
                point_a=points_2d["B"],
                point_b=points_2d["C"],
            ),
            _AnnotationSegment(
                role="h",
                value=int(height_units),
                point_a=points_2d["A"],
                point_b=points_2d["E"],
            ),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        return Analytical3DSolidCase(
            task_variant="rectangular_prism_given_lwh",
            answer_type="integer",
            answer_scalar=int(volume),
            answer_value=int(volume),
            formula_expression="V = l * w * h",
            evidence_roles=("l", "w", "h"),
            role_values={"l": int(length_units), "w": int(width_units), "h": int(height_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "rectangular_prism",
                "attrs": {
                    "task_variant": "rectangular_prism_given_lwh",
                    "length_units": int(length_units),
                    "width_units": int(width_units),
                    "height_units": int(height_units),
                    "volume_cubic_units": int(volume),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points_2d.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points_2d),
        )
    raise ValueError("failed to sample rectangular-prism volume case")


def _sample_triangular_prism_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render triangular-prism volume case."""
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(280):
        base_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        tri_height_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        prism_length_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        if int(base_units * tri_height_units) % 2 != 0:
            continue
        triangle_area = int((int(base_units) * int(tri_height_units)) // 2)
        volume = int(triangle_area * int(prism_length_units))
        if int(volume) < int(answer_min) or int(volume) > int(answer_max):
            continue
        points_3d = {
            "A": (0.0, 0.0, 0.0),
            "B": (float(base_units), 0.0, 0.0),
            "C": (0.0, 0.0, float(tri_height_units)),
            "D": (0.0, float(prism_length_units), 0.0),
            "E": (float(base_units), float(prism_length_units), 0.0),
            "F": (0.0, float(prism_length_units), float(tri_height_units)),
        }
        points_2d = _fit_projected_points(points_3d, canvas_size=int(canvas_size), margin_px=36.0)
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),
            ("D", "E"),
            ("E", "F"),
            ("F", "D"),
            ("A", "D"),
            ("B", "E"),
            ("C", "F"),
        ]
        segments = [((float(points_2d[a][0]), float(points_2d[a][1])), (float(points_2d[b][0]), float(points_2d[b][1]))) for a, b in edges]
        _draw_segments(
            draw,
            segments=segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        annotations = [
            _AnnotationSegment(
                role="b",
                value=int(base_units),
                point_a=points_2d["A"],
                point_b=points_2d["B"],
            ),
            _AnnotationSegment(
                role="h",
                value=int(tri_height_units),
                point_a=points_2d["A"],
                point_b=points_2d["C"],
            ),
            _AnnotationSegment(
                role="L",
                value=int(prism_length_units),
                point_a=points_2d["A"],
                point_b=points_2d["D"],
            ),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        return Analytical3DSolidCase(
            task_variant="triangular_prism_given_b_h_l",
            answer_type="integer",
            answer_scalar=int(volume),
            answer_value=int(volume),
            formula_expression="V = (b * h / 2) * L",
            evidence_roles=("b", "h", "L"),
            role_values={
                "b": int(base_units),
                "h": int(tri_height_units),
                "L": int(prism_length_units),
            },
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "triangular_prism",
                "attrs": {
                    "task_variant": "triangular_prism_given_b_h_l",
                    "base_units": int(base_units),
                    "triangle_height_units": int(tri_height_units),
                    "prism_length_units": int(prism_length_units),
                    "volume_cubic_units": int(volume),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points_2d.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points_2d),
        )
    raise ValueError("failed to sample triangular-prism volume case")


def _sample_square_pyramid_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render square-pyramid volume case."""
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(280):
        side_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        height_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        numerator = int(side_units * side_units * height_units)
        if int(numerator) % 3 != 0:
            continue
        volume = int(numerator // 3)
        if int(volume) < int(answer_min) or int(volume) > int(answer_max):
            continue
        points_3d = {
            "A": (0.0, 0.0, 0.0),
            "B": (float(side_units), 0.0, 0.0),
            "C": (float(side_units), float(side_units), 0.0),
            "D": (0.0, float(side_units), 0.0),
            "E": (0.5 * float(side_units), 0.5 * float(side_units), float(height_units)),
            "O": (0.5 * float(side_units), 0.5 * float(side_units), 0.0),
        }
        points_2d = _fit_projected_points(points_3d, canvas_size=int(canvas_size), margin_px=36.0)
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "A"),
            ("A", "E"),
            ("B", "E"),
            ("C", "E"),
            ("D", "E"),
        ]
        segments = [((float(points_2d[a][0]), float(points_2d[a][1])), (float(points_2d[b][0]), float(points_2d[b][1]))) for a, b in edges]
        _draw_segments(
            draw,
            segments=segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        helper_segment = (
            (float(points_2d["O"][0]), float(points_2d["O"][1])),
            (float(points_2d["E"][0]), float(points_2d["E"][1])),
        )
        _draw_segments(
            draw,
            segments=[helper_segment],
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        blocked_segments = [*segments, helper_segment]
        annotations = [
            _AnnotationSegment(
                role="s",
                value=int(side_units),
                point_a=points_2d["A"],
                point_b=points_2d["B"],
            ),
            _AnnotationSegment(
                role="h",
                value=int(height_units),
                point_a=points_2d["O"],
                point_b=points_2d["E"],
                direction=(1.0, 0.0),
            ),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=blocked_segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        return Analytical3DSolidCase(
            task_variant="square_pyramid_given_base_height",
            answer_type="integer",
            answer_scalar=int(volume),
            answer_value=int(volume),
            formula_expression="V = (s^2 * h) / 3",
            evidence_roles=("s", "h"),
            role_values={"s": int(side_units), "h": int(height_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "square_pyramid",
                "attrs": {
                    "task_variant": "square_pyramid_given_base_height",
                    "base_side_units": int(side_units),
                    "height_units": int(height_units),
                    "volume_cubic_units": int(volume),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points_2d.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points_2d),
        )
    raise ValueError("failed to sample square-pyramid volume case")


def _cylindrical_scale(radius_units: float, height_units: float, *, canvas_size: int) -> float:
    """Resolve stable visual scale for cylinder/cone-like wireframes."""
    side = float(max(1, int(canvas_size)))
    usable = max(24.0, side - 88.0)
    width_units = max(2.0, 2.2 * float(radius_units))
    height_units_visual = max(2.0, float(height_units) + (0.8 * float(radius_units)))
    return float(usable / max(width_units, height_units_visual))


def _cylinder_cap_radius_y(*, radius_px: float, height_px: float, line_width: int) -> float | None:
    """Resolve non-overlapping cylinder-cap semi-axis height.

    Returns `None` when current sampled dimensions cannot support two visible,
    non-overlapping caps with the active stroke width.
    """
    base = max(4.0, 0.34 * float(radius_px))
    clearance_limit = float(0.5 * float(height_px) - (0.6 * float(max(1, int(line_width))) + 1.5))
    if float(clearance_limit) <= 2.0:
        return None
    return float(min(float(base), float(clearance_limit)))


def _sample_cylinder_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render cylinder volume case."""
    _, _, radius_min, radius_max, _, _ = _dimension_bounds(params, generation_defaults)
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(260):
        radius_units = int(rng.randint(int(radius_min), int(radius_max)))
        height_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        coefficient = int(radius_units * radius_units * height_units)
        if int(coefficient) < int(answer_min) or int(coefficient) > int(answer_max):
            continue
        scale = _cylindrical_scale(int(radius_units), int(height_units), canvas_size=int(canvas_size))
        radius_px = float(radius_units) * float(scale)
        height_px = float(height_units) * float(scale)
        ellipse_radius_y = _cylinder_cap_radius_y(
            radius_px=float(radius_px),
            height_px=float(height_px),
            line_width=int(line_width),
        )
        if ellipse_radius_y is None:
            continue
        center_x = 0.5 * float(canvas_size)
        top_center = (float(center_x), 0.5 * float(canvas_size) - (0.5 * float(height_px)))
        bottom_center = (float(center_x), float(top_center[1] + float(height_px)))
        left_top = (float(top_center[0] - float(radius_px)), float(top_center[1]))
        right_top = (float(top_center[0] + float(radius_px)), float(top_center[1]))
        left_bottom = (float(bottom_center[0] - float(radius_px)), float(bottom_center[1]))
        right_bottom = (float(bottom_center[0] + float(radius_px)), float(bottom_center[1]))
        _draw_ellipse_outline(
            draw,
            center=top_center,
            radius_x=float(radius_px),
            radius_y=float(ellipse_radius_y),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        _draw_ellipse_outline(
            draw,
            center=bottom_center,
            radius_x=float(radius_px),
            radius_y=float(ellipse_radius_y),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        side_segments = [
            (left_top, left_bottom),
            (right_top, right_bottom),
        ]
        _draw_segments(
            draw,
            segments=side_segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        height_offset = float(max(10.0, 0.28 * float(radius_px)))
        h_a = (float(right_top[0] + float(height_offset)), float(top_center[1]))
        h_b = (float(right_bottom[0] + float(height_offset)), float(bottom_center[1]))
        helper_segments = [
            (h_a, h_b),
            (right_top, h_a),
            (right_bottom, h_b),
            (top_center, right_top),
        ]
        _draw_segments(
            draw,
            segments=helper_segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        blocked_segments = [
            *side_segments,
            *helper_segments,
            (left_top, right_top),
            (left_bottom, right_bottom),
        ]
        annotations = [
            _AnnotationSegment(
                role="r",
                value=int(radius_units),
                point_a=top_center,
                point_b=right_top,
                direction=(0.0, -1.0),
            ),
            _AnnotationSegment(
                role="h",
                value=int(height_units),
                point_a=h_a,
                point_b=h_b,
                direction=(1.0, 0.0),
            ),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=blocked_segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        points = {
            "top_center": top_center,
            "bottom_center": bottom_center,
            "left_top": left_top,
            "right_top": right_top,
            "left_bottom": left_bottom,
            "right_bottom": right_bottom,
            "h_a": h_a,
            "h_b": h_b,
        }
        return Analytical3DSolidCase(
            task_variant="cylinder_given_r_h",
            answer_type="pi_expression",
            answer_scalar=int(coefficient),
            answer_value=_pi_expression(int(coefficient)),
            formula_expression="V = π * r^2 * h",
            evidence_roles=("r", "h"),
            role_values={"r": int(radius_units), "h": int(height_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "cylinder",
                "attrs": {
                    "task_variant": "cylinder_given_r_h",
                    "radius_units": int(radius_units),
                    "height_units": int(height_units),
                    "volume_pi_coefficient": int(coefficient),
                    "render_radius_px": float(radius_px),
                    "render_height_px": float(height_px),
                    "render_cap_radius_y_px": float(ellipse_radius_y),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points),
        )
    raise ValueError("failed to sample cylinder volume case")


def _sample_cone_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render cone volume case."""
    _, _, radius_min, radius_max, _, _ = _dimension_bounds(params, generation_defaults)
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(280):
        radius_units = int(rng.randint(int(radius_min), int(radius_max)))
        height_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        numerator = int(radius_units * radius_units * height_units)
        if int(numerator) % 3 != 0:
            continue
        coefficient = int(numerator // 3)
        if int(coefficient) < int(answer_min) or int(coefficient) > int(answer_max):
            continue
        scale = _cylindrical_scale(int(radius_units), int(height_units), canvas_size=int(canvas_size))
        radius_px = float(radius_units) * float(scale)
        height_px = float(height_units) * float(scale)
        ellipse_radius_y = max(6.0, 0.34 * float(radius_px))
        center_x = 0.5 * float(canvas_size)
        base_center = (float(center_x), 0.56 * float(canvas_size))
        apex = (float(center_x), float(base_center[1] - float(height_px)))
        left_base = (float(base_center[0] - float(radius_px)), float(base_center[1]))
        right_base = (float(base_center[0] + float(radius_px)), float(base_center[1]))
        _draw_ellipse_outline(
            draw,
            center=base_center,
            radius_x=float(radius_px),
            radius_y=float(ellipse_radius_y),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        _draw_segments(
            draw,
            segments=[(apex, left_base), (apex, right_base)],
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        _draw_segments(
            draw,
            segments=[(apex, base_center), (base_center, right_base)],
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        blocked_segments = [
            (apex, left_base),
            (apex, right_base),
            (apex, base_center),
            (base_center, right_base),
            (left_base, right_base),
        ]
        annotations = [
            _AnnotationSegment(
                role="r",
                value=int(radius_units),
                point_a=base_center,
                point_b=right_base,
                direction=(0.0, 1.0),
            ),
            _AnnotationSegment(
                role="h",
                value=int(height_units),
                point_a=apex,
                point_b=base_center,
                direction=(1.0, 0.0),
            ),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=blocked_segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        points = {
            "apex": apex,
            "base_center": base_center,
            "left_base": left_base,
            "right_base": right_base,
        }
        return Analytical3DSolidCase(
            task_variant="cone_given_r_h",
            answer_type="pi_expression",
            answer_scalar=int(coefficient),
            answer_value=_pi_expression(int(coefficient)),
            formula_expression="V = (π * r^2 * h) / 3",
            evidence_roles=("r", "h"),
            role_values={"r": int(radius_units), "h": int(height_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "cone",
                "attrs": {
                    "task_variant": "cone_given_r_h",
                    "radius_units": int(radius_units),
                    "height_units": int(height_units),
                    "volume_pi_coefficient": int(coefficient),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points),
        )
    raise ValueError("failed to sample cone volume case")


def _sample_sphere_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render sphere volume case."""
    _, _, _, _, sphere_radius_min, sphere_radius_max = _dimension_bounds(params, generation_defaults)
    valid_radii = [
        int(radius)
        for radius in range(int(sphere_radius_min), int(sphere_radius_max) + 1)
        if int((4 * int(radius) * int(radius) * int(radius))) % 3 == 0
    ]
    if not valid_radii:
        raise ValueError("no feasible sphere radii satisfy integer π coefficient")
    for _ in range(220):
        radius_units = int(valid_radii[int(rng.randrange(len(valid_radii)))])
        coefficient = int((4 * int(radius_units) * int(radius_units) * int(radius_units)) // 3)
        if int(coefficient) < int(answer_min) or int(coefficient) > int(answer_max):
            continue
        scale = float((float(canvas_size) - 84.0) / max(2.0, 2.0 * float(radius_units)))
        radius_px = float(radius_units) * float(scale)
        center = (0.5 * float(canvas_size), 0.52 * float(canvas_size))
        _draw_ellipse_outline(
            draw,
            center=center,
            radius_x=float(radius_px),
            radius_y=float(radius_px),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        _draw_ellipse_outline(
            draw,
            center=center,
            radius_x=float(radius_px),
            radius_y=max(5.0, 0.35 * float(radius_px)),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        right_point = (float(center[0] + float(radius_px)), float(center[1]))
        _draw_segments(
            draw,
            segments=[(center, right_point)],
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        blocked_segments = [
            ((float(center[0] - float(radius_px)), float(center[1])), right_point),
            (center, right_point),
        ]
        annotations = [
            _AnnotationSegment(
                role="r",
                value=int(radius_units),
                point_a=center,
                point_b=right_point,
                direction=(0.0, -1.0),
            )
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=blocked_segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        points = {"center": center, "right_point": right_point}
        return Analytical3DSolidCase(
            task_variant="sphere_given_r",
            answer_type="pi_expression",
            answer_scalar=int(coefficient),
            answer_value=_pi_expression(int(coefficient)),
            formula_expression="V = (4/3) * π * r^3",
            evidence_roles=("r",),
            role_values={"r": int(radius_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "sphere",
                "attrs": {
                    "task_variant": "sphere_given_r",
                    "radius_units": int(radius_units),
                    "volume_pi_coefficient": int(coefficient),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points),
        )
    raise ValueError("failed to sample sphere volume case")


def _sample_rectangular_prism_surface_area_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render rectangular-prism total surface area case."""
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(260):
        length_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        width_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        height_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        surface_area = int(
            2
            * (
                (int(length_units) * int(width_units))
                + (int(length_units) * int(height_units))
                + (int(width_units) * int(height_units))
            )
        )
        if int(surface_area) < int(answer_min) or int(surface_area) > int(answer_max):
            continue
        points_3d = {
            "A": (0.0, 0.0, 0.0),
            "B": (float(length_units), 0.0, 0.0),
            "C": (float(length_units), float(width_units), 0.0),
            "D": (0.0, float(width_units), 0.0),
            "E": (0.0, 0.0, float(height_units)),
            "F": (float(length_units), 0.0, float(height_units)),
            "G": (float(length_units), float(width_units), float(height_units)),
            "H": (0.0, float(width_units), float(height_units)),
        }
        points_2d = _fit_projected_points(points_3d, canvas_size=int(canvas_size), margin_px=36.0)
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "A"),
            ("E", "F"),
            ("F", "G"),
            ("G", "H"),
            ("H", "E"),
            ("A", "E"),
            ("B", "F"),
            ("C", "G"),
            ("D", "H"),
        ]
        segments = [((float(points_2d[a][0]), float(points_2d[a][1])), (float(points_2d[b][0]), float(points_2d[b][1]))) for a, b in edges]
        _draw_segments(
            draw,
            segments=segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        annotations = [
            _AnnotationSegment(role="l", value=int(length_units), point_a=points_2d["A"], point_b=points_2d["B"]),
            _AnnotationSegment(role="w", value=int(width_units), point_a=points_2d["B"], point_b=points_2d["C"]),
            _AnnotationSegment(role="h", value=int(height_units), point_a=points_2d["A"], point_b=points_2d["E"]),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        return Analytical3DSolidCase(
            task_variant="rectangular_prism_given_lwh",
            answer_type="integer",
            answer_scalar=int(surface_area),
            answer_value=int(surface_area),
            formula_expression="SA = 2 * (l*w + l*h + w*h)",
            evidence_roles=("l", "w", "h"),
            role_values={"l": int(length_units), "w": int(width_units), "h": int(height_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "rectangular_prism",
                "attrs": {
                    "task_variant": "rectangular_prism_given_lwh",
                    "length_units": int(length_units),
                    "width_units": int(width_units),
                    "height_units": int(height_units),
                    "surface_area_square_units": int(surface_area),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points_2d.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points_2d),
        )
    raise ValueError("failed to sample rectangular-prism surface area case")


def _sample_triangular_prism_surface_area_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render triangular-prism total surface area case."""
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    triples = _right_triangle_leg_triples(min_leg=int(dimension_min), max_leg=int(dimension_max))
    if not triples:
        raise ValueError("no feasible right-triangle triples for triangular-prism surface area case")
    for _ in range(320):
        leg_a_units, leg_b_units, hyp_units = triples[int(rng.randrange(len(triples)))]
        prism_length_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        surface_area = int((int(leg_a_units) * int(leg_b_units)) + (int(prism_length_units) * int(leg_a_units + leg_b_units + hyp_units)))
        if int(surface_area) < int(answer_min) or int(surface_area) > int(answer_max):
            continue
        points_3d = {
            "A": (0.0, 0.0, 0.0),
            "B": (float(leg_a_units), 0.0, 0.0),
            "C": (0.0, 0.0, float(leg_b_units)),
            "D": (0.0, float(prism_length_units), 0.0),
            "E": (float(leg_a_units), float(prism_length_units), 0.0),
            "F": (0.0, float(prism_length_units), float(leg_b_units)),
        }
        points_2d = _fit_projected_points(points_3d, canvas_size=int(canvas_size), margin_px=36.0)
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),
            ("D", "E"),
            ("E", "F"),
            ("F", "D"),
            ("A", "D"),
            ("B", "E"),
            ("C", "F"),
        ]
        segments = [((float(points_2d[a][0]), float(points_2d[a][1])), (float(points_2d[b][0]), float(points_2d[b][1]))) for a, b in edges]
        _draw_segments(
            draw,
            segments=segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        annotations = [
            _AnnotationSegment(role="a", value=int(leg_a_units), point_a=points_2d["A"], point_b=points_2d["B"]),
            _AnnotationSegment(role="b", value=int(leg_b_units), point_a=points_2d["A"], point_b=points_2d["C"]),
            _AnnotationSegment(role="c", value=int(hyp_units), point_a=points_2d["B"], point_b=points_2d["C"]),
            _AnnotationSegment(role="L", value=int(prism_length_units), point_a=points_2d["A"], point_b=points_2d["D"]),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        return Analytical3DSolidCase(
            task_variant="triangular_prism_given_a_b_c_l",
            answer_type="integer",
            answer_scalar=int(surface_area),
            answer_value=int(surface_area),
            formula_expression="SA = a*b + L*(a + b + c)",
            evidence_roles=("a", "b", "c", "L"),
            role_values={
                "a": int(leg_a_units),
                "b": int(leg_b_units),
                "c": int(hyp_units),
                "L": int(prism_length_units),
            },
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "triangular_prism",
                "attrs": {
                    "task_variant": "triangular_prism_given_a_b_c_l",
                    "leg_a_units": int(leg_a_units),
                    "leg_b_units": int(leg_b_units),
                    "hypotenuse_units": int(hyp_units),
                    "prism_length_units": int(prism_length_units),
                    "surface_area_square_units": int(surface_area),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points_2d.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points_2d),
        )
    raise ValueError("failed to sample triangular-prism surface area case")


def _sample_square_pyramid_surface_area_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render square-pyramid total surface area case."""
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(320):
        side_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        min_slant = max(int(dimension_min), int(math.floor(float(side_units) / 2.0)) + 1)
        if int(min_slant) > int(dimension_max):
            continue
        slant_height_units = int(rng.randint(int(min_slant), int(dimension_max)))
        half_side = 0.5 * float(side_units)
        height_sq = (float(slant_height_units) * float(slant_height_units)) - (float(half_side) * float(half_side))
        if float(height_sq) <= 4.0:
            continue
        pyramid_height_units = math.sqrt(float(height_sq))
        surface_area = int((int(side_units) * int(side_units)) + (2 * int(side_units) * int(slant_height_units)))
        if int(surface_area) < int(answer_min) or int(surface_area) > int(answer_max):
            continue
        points_3d = {
            "A": (0.0, 0.0, 0.0),
            "B": (float(side_units), 0.0, 0.0),
            "C": (float(side_units), float(side_units), 0.0),
            "D": (0.0, float(side_units), 0.0),
            "E": (0.5 * float(side_units), 0.5 * float(side_units), float(pyramid_height_units)),
            "M": (0.5 * float(side_units), 0.0, 0.0),
        }
        points_2d = _fit_projected_points(points_3d, canvas_size=int(canvas_size), margin_px=36.0)
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "A"),
            ("A", "E"),
            ("B", "E"),
            ("C", "E"),
            ("D", "E"),
        ]
        segments = [((float(points_2d[a][0]), float(points_2d[a][1])), (float(points_2d[b][0]), float(points_2d[b][1]))) for a, b in edges]
        _draw_segments(
            draw,
            segments=segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        slant_helper = (
            (float(points_2d["M"][0]), float(points_2d["M"][1])),
            (float(points_2d["E"][0]), float(points_2d["E"][1])),
        )
        _draw_segments(
            draw,
            segments=[slant_helper],
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        blocked_segments = [*segments, slant_helper]
        annotations = [
            _AnnotationSegment(role="s", value=int(side_units), point_a=points_2d["A"], point_b=points_2d["B"]),
            _AnnotationSegment(
                role="l",
                value=int(slant_height_units),
                point_a=points_2d["M"],
                point_b=points_2d["E"],
                direction=(1.0, 0.0),
            ),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=blocked_segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        return Analytical3DSolidCase(
            task_variant="square_pyramid_given_base_side_slant_height",
            answer_type="integer",
            answer_scalar=int(surface_area),
            answer_value=int(surface_area),
            formula_expression="SA = s^2 + 2*s*l",
            evidence_roles=("s", "l"),
            role_values={"s": int(side_units), "l": int(slant_height_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "square_pyramid",
                "attrs": {
                    "task_variant": "square_pyramid_given_base_side_slant_height",
                    "base_side_units": int(side_units),
                    "slant_height_units": int(slant_height_units),
                    "height_units": float(pyramid_height_units),
                    "surface_area_square_units": int(surface_area),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points_2d.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points_2d),
        )
    raise ValueError("failed to sample square-pyramid surface area case")


def _sample_cylinder_surface_area_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render cylinder total surface area case."""
    _, _, radius_min, radius_max, _, _ = _dimension_bounds(params, generation_defaults)
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(260):
        radius_units = int(rng.randint(int(radius_min), int(radius_max)))
        height_units = int(rng.randint(int(dimension_min), int(dimension_max)))
        coefficient = int(2 * int(radius_units) * int(radius_units + height_units))
        if int(coefficient) < int(answer_min) or int(coefficient) > int(answer_max):
            continue
        scale = _cylindrical_scale(float(radius_units), float(height_units), canvas_size=int(canvas_size))
        radius_px = float(radius_units) * float(scale)
        height_px = float(height_units) * float(scale)
        ellipse_radius_y = _cylinder_cap_radius_y(
            radius_px=float(radius_px),
            height_px=float(height_px),
            line_width=int(line_width),
        )
        if ellipse_radius_y is None:
            continue
        center_x = 0.5 * float(canvas_size)
        top_center = (float(center_x), 0.5 * float(canvas_size) - (0.5 * float(height_px)))
        bottom_center = (float(center_x), float(top_center[1] + float(height_px)))
        left_top = (float(top_center[0] - float(radius_px)), float(top_center[1]))
        right_top = (float(top_center[0] + float(radius_px)), float(top_center[1]))
        left_bottom = (float(bottom_center[0] - float(radius_px)), float(bottom_center[1]))
        right_bottom = (float(bottom_center[0] + float(radius_px)), float(bottom_center[1]))
        _draw_ellipse_outline(
            draw,
            center=top_center,
            radius_x=float(radius_px),
            radius_y=float(ellipse_radius_y),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        _draw_ellipse_outline(
            draw,
            center=bottom_center,
            radius_x=float(radius_px),
            radius_y=float(ellipse_radius_y),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        side_segments = [(left_top, left_bottom), (right_top, right_bottom)]
        _draw_segments(
            draw,
            segments=side_segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        height_offset = float(max(10.0, 0.28 * float(radius_px)))
        h_a = (float(right_top[0] + float(height_offset)), float(top_center[1]))
        h_b = (float(right_bottom[0] + float(height_offset)), float(bottom_center[1]))
        helper_segments = [(h_a, h_b), (right_top, h_a), (right_bottom, h_b), (top_center, right_top)]
        _draw_segments(
            draw,
            segments=helper_segments,
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        blocked_segments = [*side_segments, *helper_segments, (left_top, right_top), (left_bottom, right_bottom)]
        annotations = [
            _AnnotationSegment(role="r", value=int(radius_units), point_a=top_center, point_b=right_top, direction=(0.0, -1.0)),
            _AnnotationSegment(role="h", value=int(height_units), point_a=h_a, point_b=h_b, direction=(1.0, 0.0)),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=blocked_segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        points = {
            "top_center": top_center,
            "bottom_center": bottom_center,
            "left_top": left_top,
            "right_top": right_top,
            "left_bottom": left_bottom,
            "right_bottom": right_bottom,
            "h_a": h_a,
            "h_b": h_b,
        }
        return Analytical3DSolidCase(
            task_variant="cylinder_given_r_h",
            answer_type="pi_expression",
            answer_scalar=int(coefficient),
            answer_value=_pi_expression(int(coefficient)),
            formula_expression="SA = 2 * π * r * (r + h)",
            evidence_roles=("r", "h"),
            role_values={"r": int(radius_units), "h": int(height_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "cylinder",
                "attrs": {
                    "task_variant": "cylinder_given_r_h",
                    "radius_units": int(radius_units),
                    "height_units": int(height_units),
                    "surface_area_pi_coefficient": int(coefficient),
                    "render_radius_px": float(radius_px),
                    "render_height_px": float(height_px),
                    "render_cap_radius_y_px": float(ellipse_radius_y),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points),
        )
    raise ValueError("failed to sample cylinder surface area case")


def _sample_cone_surface_area_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render cone total surface area case."""
    _, _, radius_min, radius_max, _, _ = _dimension_bounds(params, generation_defaults)
    dimension_min, dimension_max, _, _, _, _ = _dimension_bounds(params, generation_defaults)
    for _ in range(320):
        radius_units = int(rng.randint(int(radius_min), int(radius_max)))
        min_slant = max(int(dimension_min), int(radius_units) + 1)
        if int(min_slant) > int(dimension_max):
            continue
        slant_height_units = int(rng.randint(int(min_slant), int(dimension_max)))
        height_sq = (int(slant_height_units) * int(slant_height_units)) - (int(radius_units) * int(radius_units))
        if int(height_sq) <= 4:
            continue
        height_units = math.sqrt(float(height_sq))
        coefficient = int(int(radius_units) * int(radius_units + slant_height_units))
        if int(coefficient) < int(answer_min) or int(coefficient) > int(answer_max):
            continue
        scale = _cylindrical_scale(float(radius_units), float(height_units), canvas_size=int(canvas_size))
        radius_px = float(radius_units) * float(scale)
        height_px = float(height_units) * float(scale)
        ellipse_radius_y = max(6.0, 0.34 * float(radius_px))
        center_x = 0.5 * float(canvas_size)
        base_center = (float(center_x), 0.58 * float(canvas_size))
        apex = (float(center_x), float(base_center[1] - float(height_px)))
        left_base = (float(base_center[0] - float(radius_px)), float(base_center[1]))
        right_base = (float(base_center[0] + float(radius_px)), float(base_center[1]))
        _draw_ellipse_outline(
            draw,
            center=base_center,
            radius_x=float(radius_px),
            radius_y=float(ellipse_radius_y),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        _draw_segments(
            draw,
            segments=[(apex, left_base), (apex, right_base)],
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        _draw_segments(
            draw,
            segments=[(base_center, right_base)],
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        blocked_segments = [
            (apex, left_base),
            (apex, right_base),
            (base_center, right_base),
            (left_base, right_base),
        ]
        annotations = [
            _AnnotationSegment(role="r", value=int(radius_units), point_a=base_center, point_b=right_base, direction=(0.0, 1.0)),
            _AnnotationSegment(role="l", value=int(slant_height_units), point_a=apex, point_b=right_base, direction=(1.0, 0.0)),
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=blocked_segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        points = {
            "apex": apex,
            "base_center": base_center,
            "left_base": left_base,
            "right_base": right_base,
        }
        return Analytical3DSolidCase(
            task_variant="cone_given_r_slant_height",
            answer_type="pi_expression",
            answer_scalar=int(coefficient),
            answer_value=_pi_expression(int(coefficient)),
            formula_expression="SA = π * r * (r + l)",
            evidence_roles=("r", "l"),
            role_values={"r": int(radius_units), "l": int(slant_height_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "cone",
                "attrs": {
                    "task_variant": "cone_given_r_slant_height",
                    "radius_units": int(radius_units),
                    "slant_height_units": int(slant_height_units),
                    "height_units": float(height_units),
                    "surface_area_pi_coefficient": int(coefficient),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points),
        )
    raise ValueError("failed to sample cone surface area case")


def _sample_sphere_surface_area_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render sphere total surface area case."""
    _, _, _, _, sphere_radius_min, sphere_radius_max = _dimension_bounds(params, generation_defaults)
    valid_radii = list(range(int(sphere_radius_min), int(sphere_radius_max) + 1))
    if not valid_radii:
        raise ValueError("no feasible sphere radii for surface area case")
    for _ in range(220):
        radius_units = int(valid_radii[int(rng.randrange(len(valid_radii)))])
        coefficient = int(4 * int(radius_units) * int(radius_units))
        if int(coefficient) < int(answer_min) or int(coefficient) > int(answer_max):
            continue
        scale = float((float(canvas_size) - 84.0) / max(2.0, 2.0 * float(radius_units)))
        radius_px = float(radius_units) * float(scale)
        center = (0.5 * float(canvas_size), 0.52 * float(canvas_size))
        _draw_ellipse_outline(
            draw,
            center=center,
            radius_x=float(radius_px),
            radius_y=float(radius_px),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(line_width),
        )
        _draw_ellipse_outline(
            draw,
            center=center,
            radius_x=float(radius_px),
            radius_y=max(5.0, 0.35 * float(radius_px)),
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        right_point = (float(center[0] + float(radius_px)), float(center[1]))
        _draw_segments(
            draw,
            segments=[(center, right_point)],
            scene_scale=int(scene_scale),
            color=tuple(int(value) for value in shape_style.line_color),
            line_width=int(helper_line_width),
        )
        blocked_segments = [
            ((float(center[0] - float(radius_px)), float(center[1])), right_point),
            (center, right_point),
        ]
        annotations = [
            _AnnotationSegment(role="r", value=int(radius_units), point_a=center, point_b=right_point, direction=(0.0, -1.0))
        ]
        evidence_map, role_tokens, annotation_centers = _render_annotations_and_evidence(
            rng,
            draw,
            annotations=annotations,
            blocked_segments=blocked_segments,
            scene_scale=int(scene_scale),
            canvas_size=int(canvas_size),
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(scene_scale)),
        )
        points = {"center": center, "right_point": right_point}
        return Analytical3DSolidCase(
            task_variant="sphere_given_r",
            answer_type="pi_expression",
            answer_scalar=int(coefficient),
            answer_value=_pi_expression(int(coefficient)),
            formula_expression="SA = 4 * π * r^2",
            evidence_roles=("r",),
            role_values={"r": int(radius_units)},
            role_tokens=dict(role_tokens),
            evidence_map=dict(evidence_map),
            annotation_centers=dict(annotation_centers),
            entity={
                "entity_id": "solid_1",
                "entity_type": "sphere",
                "attrs": {
                    "task_variant": "sphere_given_r",
                    "radius_units": int(radius_units),
                    "surface_area_pi_coefficient": int(coefficient),
                    "points": {key: [float(point[0]), float(point[1])] for key, point in points.items()},
                },
            },
            render_anchor=_render_anchor_from_points(points),
        )
    raise ValueError("failed to sample sphere surface area case")


def sample_analytical_3d_volume_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    task_variant: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render one configured analytical 3D volume case."""
    variant_key = str(task_variant)
    if str(variant_key) == "rectangular_prism_given_lwh":
        return _sample_rectangular_prism_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "triangular_prism_given_b_h_l":
        return _sample_triangular_prism_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "square_pyramid_given_base_height":
        return _sample_square_pyramid_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "cylinder_given_r_h":
        return _sample_cylinder_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "cone_given_r_h":
        return _sample_cone_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "sphere_given_r":
        return _sample_sphere_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    raise ValueError(f"unsupported analytical 3d volume variant: {variant_key}")


def sample_analytical_3d_surface_area_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    task_variant: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    canvas_size: int,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> Analytical3DSolidCase:
    """Sample and render one configured analytical 3D surface-area case."""
    variant_key = str(task_variant)
    if str(variant_key) == "rectangular_prism_given_lwh":
        return _sample_rectangular_prism_surface_area_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "triangular_prism_given_a_b_c_l":
        return _sample_triangular_prism_surface_area_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "square_pyramid_given_base_side_slant_height":
        return _sample_square_pyramid_surface_area_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "cylinder_given_r_h":
        return _sample_cylinder_surface_area_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "cone_given_r_slant_height":
        return _sample_cone_surface_area_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if str(variant_key) == "sphere_given_r":
        return _sample_sphere_surface_area_case(
            rng,
            draw,
            params=params,
            generation_defaults=generation_defaults,
            canvas_size=int(canvas_size),
            scene_scale=int(scene_scale),
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    raise ValueError(f"unsupported analytical 3d surface-area variant: {variant_key}")
