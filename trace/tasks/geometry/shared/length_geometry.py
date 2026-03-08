"""Shared segment/length geometry helpers for measurement-style tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Sequence, Tuple

from PIL import ImageDraw

from ...shared.geometry_primitives import Point
from ...shared.text_rendering import draw_text_centered, load_font, resolve_text_label_center
from .graph_paper import offset_point_by_grid_vector, sample_lattice_point_with_offsets
from .graph_rendering import pixel_point_to_graph_units

UnitVector = Tuple[int, int]


@dataclass(frozen=True)
class SegmentInstance:
    """One concrete labeled segment instance in pixel coordinates."""

    endpoint_a: Point
    endpoint_b: Point
    labels: Tuple[str, str]
    length_units: int


def _is_perfect_square(value: int) -> bool:
    """Return true when `value` is a perfect square."""
    if int(value) < 0:
        return False
    root = int(math.isqrt(int(value)))
    return int(root * root) == int(value)


@lru_cache(maxsize=16)
def integer_length_vectors(
    *,
    max_abs_component: int = 8,
    min_edge_length: int = 2,
    max_edge_length: int = 10,
) -> Tuple[Tuple[int, int, int], ...]:
    """Return lattice vectors whose Euclidean lengths are integers."""
    vectors: List[Tuple[int, int, int]] = []
    for dx in range(-int(max_abs_component), int(max_abs_component) + 1):
        for dy in range(-int(max_abs_component), int(max_abs_component) + 1):
            if dx == 0 and dy == 0:
                continue
            length_sq = int(dx * dx) + int(dy * dy)
            if not _is_perfect_square(length_sq):
                continue
            length = int(math.isqrt(length_sq))
            if int(length) < int(min_edge_length) or int(length) > int(max_edge_length):
                continue
            vectors.append((int(dx), int(dy), int(length)))
    if not vectors:
        raise ValueError("integer_length_vectors resolved empty")
    return tuple(vectors)


def segment_length_units(point_a: Point, point_b: Point, *, tol: float = 1e-6) -> int:
    """Return integer Euclidean segment length in graph units."""
    length = math.hypot(float(point_b[0]) - float(point_a[0]), float(point_b[1]) - float(point_a[1]))
    rounded = int(round(length))
    if abs(float(length) - float(rounded)) > float(tol):
        raise ValueError("segment length is not integer in graph units")
    return int(rounded)


def sample_segment_instance_on_graph_paper(
    rng,
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None,
    min_length_units: int,
    max_length_units: int,
    max_abs_vector_component: int = 10,
    labels: Sequence[str] = ("A", "B"),
    padding_units: int = 0,
    max_attempts: int = 220,
) -> SegmentInstance:
    """Sample one integer-length segment whose endpoints lie on graph-paper lattice."""
    lo = max(1, int(min_length_units))
    hi = max(int(lo), int(max_length_units))
    vectors = [
        (int(dx), int(dy), int(length))
        for dx, dy, length in integer_length_vectors(
            max_abs_component=int(max_abs_vector_component),
            min_edge_length=int(lo),
            max_edge_length=int(hi),
        )
        if int(lo) <= int(length) <= int(hi)
    ]
    if not vectors:
        raise ValueError("no feasible integer-length segment vectors")
    label_values = tuple(str(label) for label in labels[:2])
    if len(label_values) != 2:
        raise ValueError("labels must include exactly two entries")

    for _ in range(max(1, int(max_attempts))):
        dx, dy, length_units = rng.choice(vectors)
        try:
            endpoint_a = sample_lattice_point_with_offsets(
                rng,
                canvas_size=int(canvas_size),
                spacing=int(graph_spacing),
                x_offsets=[0, int(dx)],
                y_offsets=[0, int(dy)],
                lattice_origin=(
                    (float(graph_origin[0]), float(graph_origin[1]))
                    if graph_origin is not None
                    else None
                ),
                padding=int(max(0, int(padding_units)) * int(graph_spacing)),
            )
        except ValueError:
            continue
        endpoint_b = offset_point_by_grid_vector(
            (float(endpoint_a[0]), float(endpoint_a[1])),
            (int(dx), int(dy)),
            spacing=int(graph_spacing),
        )
        return SegmentInstance(
            endpoint_a=(float(endpoint_a[0]), float(endpoint_a[1])),
            endpoint_b=(float(endpoint_b[0]), float(endpoint_b[1])),
            labels=tuple(label_values),
            length_units=int(length_units),
        )
    raise ValueError("failed to sample segment instance for current scene constraints")


def draw_labeled_segment(
    draw: ImageDraw.ImageDraw,
    *,
    endpoint_a: Point,
    endpoint_b: Point,
    labels: Sequence[str],
    line_width: int,
    label_offset_px: float,
    font_size_px: int,
    text_stroke_width: int | None = None,
    line_color: Tuple[int, int, int] = (22, 22, 22),
    label_color: Tuple[int, int, int] = (24, 24, 24),
    label_stroke_color: Tuple[int, int, int] = (252, 252, 252),
    canvas_size: int | None = None,
) -> None:
    """Draw one segment and two endpoint labels with overlap-aware placement."""
    point_a = (float(endpoint_a[0]), float(endpoint_a[1]))
    point_b = (float(endpoint_b[0]), float(endpoint_b[1]))
    draw.line(
        [point_a, point_b],
        fill=tuple(int(value) for value in line_color),
        width=max(1, int(line_width)),
    )
    label_values = [str(item) for item in labels]
    if len(label_values) != 2:
        return
    font = load_font(int(font_size_px), bold=True)
    stroke_width = (
        int(text_stroke_width)
        if text_stroke_width is not None
        else max(1, int(round(0.08 * float(max(8, int(font_size_px))))))
    )
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    segment = ((float(point_a[0]), float(point_a[1])), (float(point_b[0]), float(point_b[1])))
    placements = [
        (label_values[0], point_a, (float(point_a[0] - point_b[0]), float(point_a[1] - point_b[1]))),
        (label_values[1], point_b, (float(point_b[0] - point_a[0]), float(point_b[1] - point_a[1]))),
    ]
    for label, anchor, direction in placements:
        center, bbox = resolve_text_label_center(
            draw,
            text=str(label),
            anchor=(float(anchor[0]), float(anchor[1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(max(8.0, float(label_offset_px))),
            font=font,
            blocked_segments=[segment],
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
        occupied_boxes.append(bbox)


def segment_scene_entity(
    instance: SegmentInstance,
    *,
    entity_id: str = "segment_1",
    segment_kind: str = "segment",
) -> Dict[str, Any]:
    """Build `scene_ir.entities` entry for one segment instance."""
    return {
        "entity_id": str(entity_id),
        "entity_type": "segment",
        "attrs": {
            "segment_kind": str(segment_kind),
            "length_units": int(instance.length_units),
            "labels": [str(instance.labels[0]), str(instance.labels[1])],
            "points": {
                "endpoint_a": [float(instance.endpoint_a[0]), float(instance.endpoint_a[1])],
                "endpoint_b": [float(instance.endpoint_b[0]), float(instance.endpoint_b[1])],
            },
        },
    }


def segment_render_anchor(instance: SegmentInstance) -> Dict[str, Any]:
    """Build deterministic render-map anchor for one segment instance."""
    point_a = [float(instance.endpoint_a[0]), float(instance.endpoint_a[1])]
    point_b = [float(instance.endpoint_b[0]), float(instance.endpoint_b[1])]
    return {
        "point": list(point_a),
        "polyline": [list(point_a), list(point_b)],
        "coord_space": "pixel",
    }


def two_point_evidence_artifacts(
    *,
    point_a: Point,
    point_b: Point,
    graph_origin: Point,
    graph_spacing: int,
    witness_type: str,
    roles: Sequence[str] = ("point_a", "point_b"),
) -> Dict[str, Any]:
    """Build evidence/witness/projection payloads for one ordered 2-point segment."""
    pixel_points = [
        [float(point_a[0]), float(point_a[1])],
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
            "type": str(witness_type),
            "roles": [str(role) for role in roles],
        },
        "projected_evidence": {
            "point_set": [list(point) for point in pixel_points],
            "point_path": [list(point) for point in pixel_points],
            "grid_point_set": [list(point) for point in grid_points],
            "grid_point_path": [list(point) for point in grid_points],
        },
    }

