"""Shared angle-geometry helpers for single-object measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...shared.geometry_primitives import Point, point_inside_square_canvas
from ...shared.text_rendering import draw_text_centered, load_font, resolve_text_label_center
from .graph_paper import offset_point_by_grid_vector, sample_lattice_point_with_offsets
from .graph_rendering import pixel_point_to_graph_units

Vector = Tuple[int, int]


@dataclass(frozen=True)
class PrimitiveAngleSample:
    """One sampled primitive-angle specification on graph-paper coordinates."""

    angle_degrees: int
    raw_angle_degrees: float
    vertex: Point
    point_a: Point
    point_b: Point
    labels: Tuple[str, str, str]


def _vector_angle_degrees(vec_a: Vector, vec_b: Vector) -> float:
    """Return interior angle in degrees between two integer vectors."""
    ax, ay = float(vec_a[0]), float(vec_a[1])
    bx, by = float(vec_b[0]), float(vec_b[1])
    mag_a = math.hypot(ax, ay)
    mag_b = math.hypot(bx, by)
    if mag_a <= 1e-9 or mag_b <= 1e-9:
        raise ValueError("angle vectors must be non-zero")
    dot = (ax * bx) + (ay * by)
    cos_value = max(-1.0, min(1.0, dot / (mag_a * mag_b)))
    return float(math.degrees(math.acos(cos_value)))


@lru_cache(maxsize=16)
def primitive_angle_pair_catalog(
    *,
    angle_step: int,
    min_angle: int,
    max_angle: int,
    max_abs_vector_component: int = 6,
    max_quantization_error: float = 2.0,
    min_vector_length_units: float = 1.0,
) -> Dict[int, Tuple[Tuple[Vector, Vector, float], ...]]:
    """Build a cached map from snapped angle value to feasible integer-vector pairs.

    Catalog policy:
    - one arm is axis-aligned (horizontal/vertical),
    - the other arm is any non-zero integer vector in the search window,
    - both vectors must have length >= `min_vector_length_units`,
    - raw angle must snap to `angle_step` within `max_quantization_error`.
    """
    step = int(angle_step)
    if step <= 0:
        raise ValueError("angle_step must be > 0")
    min_value = int(min_angle)
    max_value = int(max_angle)
    if min_value < step or min_value > max_value:
        raise ValueError("invalid angle range")
    min_vector_length = float(min_vector_length_units)
    if min_vector_length < 0.0:
        raise ValueError("min_vector_length_units must be >= 0")

    vectors: List[Vector] = [
        (dx, dy)
        for dx in range(-int(max_abs_vector_component), int(max_abs_vector_component) + 1)
        for dy in range(-int(max_abs_vector_component), int(max_abs_vector_component) + 1)
        if not (dx == 0 and dy == 0)
    ]
    axis_vectors = [vector for vector in vectors if (vector[0] == 0 or vector[1] == 0)]

    by_angle: Dict[int, List[Tuple[Vector, Vector, float]]] = {}
    for axis_vector in axis_vectors:
        if math.hypot(float(axis_vector[0]), float(axis_vector[1])) < float(min_vector_length):
            continue
        for other_vector in vectors:
            if (other_vector[0] == 0 and other_vector[1] == 0) or other_vector == axis_vector:
                continue
            if math.hypot(float(other_vector[0]), float(other_vector[1])) < float(min_vector_length):
                continue
            raw = _vector_angle_degrees(axis_vector, other_vector)
            snapped = int(round(raw / float(step))) * int(step)
            if snapped < min_value or snapped > max_value:
                continue
            if abs(raw - float(snapped)) > float(max_quantization_error):
                continue
            if snapped in {0, 180}:
                continue
            by_angle.setdefault(int(snapped), []).append((axis_vector, other_vector, float(raw)))

    out: Dict[int, Tuple[Tuple[Vector, Vector, float], ...]] = {}
    for angle_value, pairs in sorted(by_angle.items()):
        # deterministic ordering for reproducible RNG choices downstream
        ordered = sorted(
            {
                (
                    int(pair[0][0]),
                    int(pair[0][1]),
                    int(pair[1][0]),
                    int(pair[1][1]),
                    round(float(pair[2]), 6),
                )
                for pair in pairs
            }
        )
        out[int(angle_value)] = tuple(
            ((int(item[0]), int(item[1])), (int(item[2]), int(item[3])), float(item[4]))
            for item in ordered
        )
    if not out:
        raise ValueError("primitive angle catalog resolved empty")
    return out


def _sample_letters(rng) -> Tuple[str, str, str]:
    """Sample deterministic triplet labels from `A..Z` without replacement."""
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    rng.shuffle(letters)
    selected = sorted(letters[:3])
    # keep middle letter as vertex label for stable `A,B,C` ordering in prompts
    return (str(selected[0]), str(selected[1]), str(selected[2]))


def sample_primitive_angle(
    rng,
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None = None,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    max_abs_vector_component: int = 6,
    max_quantization_error: float = 2.0,
    min_vector_length_units: float = 1.0,
    margin_padding_units: int = 2,
    target_angle: int | None = None,
) -> PrimitiveAngleSample:
    """Sample one primitive angle whose answer snaps to `angle_step` multiples."""
    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_abs_vector_component=int(max_abs_vector_component),
        max_quantization_error=float(max_quantization_error),
        min_vector_length_units=float(min_vector_length_units),
    )
    feasible_angles = sorted(catalog.keys())
    if not feasible_angles:
        raise ValueError("no feasible primitive angles for requested range")
    if target_angle is not None and int(target_angle) not in set(feasible_angles):
        raise ValueError("target_angle is not feasible for primitive-angle catalog")

    for _ in range(220):
        angle_target = int(target_angle) if target_angle is not None else int(rng.choice(feasible_angles))
        pairs = list(catalog[angle_target])
        rng.shuffle(pairs)
        if not pairs:
            continue

        for vector_a, vector_b, raw_angle in pairs:
            try:
                vertex = sample_lattice_point_with_offsets(
                    rng,
                    canvas_size=int(canvas_size),
                    spacing=int(graph_spacing),
                    x_offsets=(0, int(vector_a[0]), int(vector_b[0])),
                    y_offsets=(0, int(vector_a[1]), int(vector_b[1])),
                    lattice_origin=(
                        (float(graph_origin[0]), float(graph_origin[1]))
                        if graph_origin is not None
                        else None
                    ),
                    padding=int(max(0, int(margin_padding_units)) * int(graph_spacing)),
                )
            except ValueError:
                continue
            point_a = offset_point_by_grid_vector(vertex, vector_a, spacing=int(graph_spacing))
            point_b = offset_point_by_grid_vector(vertex, vector_b, spacing=int(graph_spacing))
            if not (
                point_inside_square_canvas(point_a, canvas_size=int(canvas_size))
                and point_inside_square_canvas(point_b, canvas_size=int(canvas_size))
            ):
                continue
            labels = _sample_letters(rng)
            return PrimitiveAngleSample(
                angle_degrees=int(angle_target),
                raw_angle_degrees=float(raw_angle),
                vertex=vertex,
                point_a=point_a,
                point_b=point_b,
                labels=labels,
            )
    raise ValueError("failed to sample primitive angle on graph paper")


def draw_labeled_angle(
    draw: ImageDraw.ImageDraw,
    *,
    vertex: Point,
    point_a: Point,
    point_b: Point,
    labels: Sequence[str],
    line_width: int,
    label_offset_px: float,
    font_size_px: int,
    text_stroke_width: int | None = None,
    line_color: Tuple[int, int, int] = (24, 24, 24),
    label_color: Tuple[int, int, int] = (24, 24, 24),
    label_stroke_color: Tuple[int, int, int] = (252, 252, 252),
    blocked_segments: Sequence[Tuple[Point, Point]] | None = None,
    canvas_size: int | None = None,
) -> None:
    """Draw one angle with overlap-aware endpoint/vertex labels."""
    vx, vy = float(vertex[0]), float(vertex[1])
    ax, ay = float(point_a[0]), float(point_a[1])
    bx, by = float(point_b[0]), float(point_b[1])
    draw.line([ax, ay, vx, vy], fill=tuple(int(value) for value in line_color), width=max(1, int(line_width)))
    draw.line([bx, by, vx, vy], fill=tuple(int(value) for value in line_color), width=max(1, int(line_width)))

    points = [point_a, vertex, point_b]
    segments: List[Tuple[Point, Point]] = [
        ((float(point_a[0]), float(point_a[1])), (float(vertex[0]), float(vertex[1]))),
        ((float(vertex[0]), float(vertex[1])), (float(point_b[0]), float(point_b[1]))),
    ]
    if blocked_segments:
        segments.extend(
            (
                (float(seg_a[0]), float(seg_a[1])),
                (float(seg_b[0]), float(seg_b[1])),
            )
            for seg_a, seg_b in blocked_segments
        )
    centroid_x = float(sum(point[0] for point in points) / 3.0)
    centroid_y = float(sum(point[1] for point in points) / 3.0)
    offset = float(max(8.0, float(label_offset_px)))
    font = load_font(int(font_size_px), bold=True)
    stroke_width = (
        int(text_stroke_width)
        if text_stroke_width is not None
        else max(1, int(round(0.08 * float(max(8, int(font_size_px))))))
    )
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    for label, point in zip(labels, points):
        px, py = float(point[0]), float(point[1])
        dx, dy = px - centroid_x, py - centroid_y
        center, label_bbox = resolve_text_label_center(
            draw,
            text=str(label),
            anchor=(float(px), float(py)),
            base_direction=(float(dx), float(dy)),
            offset_px=float(offset),
            font=font,
            blocked_segments=segments,
            occupied_boxes=occupied_boxes,
            stroke_width=int(stroke_width),
            line_clearance_px=max(2.0, 0.8 * float(max(1, int(line_width)))),
            canvas_size=int(canvas_size) if canvas_size is not None else None,
        )
        draw_text_centered(
            draw,
            text=str(label),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in label_color),
            stroke_fill=tuple(int(value) for value in label_stroke_color),
            stroke_width=int(stroke_width),
        )
        occupied_boxes.append(label_bbox)


def angle_triplet_evidence_artifacts(
    *,
    point_a: Point,
    vertex: Point,
    point_b: Point,
    graph_origin: Point,
    graph_spacing: int,
) -> Dict[str, Any]:
    """Build evidence/witness/projection payloads for one ordered angle-point triplet."""
    pixel_points = [
        [float(point_a[0]), float(point_a[1])],
        [float(vertex[0]), float(vertex[1])],
        [float(point_b[0]), float(point_b[1])],
    ]
    grid_points = [
        pixel_point_to_graph_units(
            (float(point[0]), float(point[1])),
            origin=(float(graph_origin[0]), float(graph_origin[1])),
            spacing=int(graph_spacing),
        )
        for point in pixel_points
    ]
    return {
        "evidence_type": "grid_point_set",
        "evidence_value": [list(point) for point in grid_points],
        "witness_symbolic": {
            "type": "angle_triplet",
            "roles": ["ray_endpoint_a", "vertex", "ray_endpoint_b"],
        },
        "projected_evidence": {
            "point_set": [list(point) for point in pixel_points],
            "point_path": [list(point) for point in pixel_points],
            "grid_point_set": [list(point) for point in grid_points],
            "grid_point_path": [list(point) for point in grid_points],
        },
    }
