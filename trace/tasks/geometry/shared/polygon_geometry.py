"""Shared procedural polygon sampling, rendering, and metric helpers."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import ImageDraw

from ...shared.geometry_primitives import Point, point_inside_square_canvas
from ...shared.sequence import rotate_sequence
from ...shared.text_rendering import draw_text_centered, load_font, resolve_text_label_center
from .graph_paper import sample_lattice_point_with_offsets
from .graph_rendering import pixel_point_to_graph_units
from .length_geometry import integer_length_vectors

UnitPoint = Tuple[int, int]


@dataclass(frozen=True)
class PolygonTemplate:
    """Canonical integer-grid polygon template in graph-unit coordinates."""

    template_id: str
    vertices: Tuple[UnitPoint, ...]

    @property
    def sides(self) -> int:
        return int(len(self.vertices))


@dataclass(frozen=True)
class PolygonInstance:
    """One concrete polygon instance in pixel coordinates."""

    template_id: str
    sides: int
    area_square_units: int
    perimeter_units: int
    vertices: Tuple[Point, ...]
    labels: Tuple[str, ...]


def _segment_orientation(a: UnitPoint, b: UnitPoint, c: UnitPoint) -> int:
    """Return signed orientation determinant for ordered triplet `(a, b, c)`."""
    return int((int(b[0]) - int(a[0])) * (int(c[1]) - int(a[1])) - (int(b[1]) - int(a[1])) * (int(c[0]) - int(a[0])))


def _point_on_segment(a: UnitPoint, b: UnitPoint, c: UnitPoint) -> bool:
    """Return true when point `b` lies on segment `[a, c]`."""
    return (
        min(int(a[0]), int(c[0])) <= int(b[0]) <= max(int(a[0]), int(c[0]))
        and min(int(a[1]), int(c[1])) <= int(b[1]) <= max(int(a[1]), int(c[1]))
    )


def _segments_intersect(a1: UnitPoint, a2: UnitPoint, b1: UnitPoint, b2: UnitPoint) -> bool:
    """Return true when two closed segments intersect (including touching)."""
    o1 = _segment_orientation(a1, a2, b1)
    o2 = _segment_orientation(a1, a2, b2)
    o3 = _segment_orientation(b1, b2, a1)
    o4 = _segment_orientation(b1, b2, a2)

    if o1 == 0 and _point_on_segment(a1, b1, a2):
        return True
    if o2 == 0 and _point_on_segment(a1, b2, a2):
        return True
    if o3 == 0 and _point_on_segment(b1, a1, b2):
        return True
    if o4 == 0 and _point_on_segment(b1, a2, b2):
        return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def _is_simple_polygon(vertices: Sequence[UnitPoint]) -> bool:
    """Return true when polygon boundary has no self-intersections."""
    n = int(len(vertices))
    if n < 3:
        return False
    for i in range(n):
        a1 = (int(vertices[i][0]), int(vertices[i][1]))
        a2 = (int(vertices[(i + 1) % n][0]), int(vertices[(i + 1) % n][1]))
        for j in range(i + 1, n):
            if j == i or j == (i + 1) % n or (i == 0 and j == n - 1):
                continue
            b1 = (int(vertices[j][0]), int(vertices[j][1]))
            b2 = (int(vertices[(j + 1) % n][0]), int(vertices[(j + 1) % n][1]))
            if _segments_intersect(a1, a2, b1, b2):
                return False
    return True


def _polygon_signature(vertices: Sequence[UnitPoint]) -> str:
    """Return deterministic short signature for one polygon unit-vertex sequence."""
    payload = ";".join(f"{int(point[0])},{int(point[1])}" for point in vertices)
    digest = hashlib.blake2s(payload.encode("utf-8"), digest_size=6).hexdigest()
    return str(digest)


def sample_procedural_polygon_template(
    rng,
    *,
    sides: int,
    max_span_units: int,
    max_abs_component: int = 8,
    min_edge_length: int = 2,
    max_edge_length: int = 10,
    min_area_square_units: int = 4,
    max_attempts: int = 2200,
) -> PolygonTemplate:
    """Sample a random simple lattice polygon with integer edge lengths.

    Policy:
    - edge vectors are sampled from integer-length lattice vectors,
    - closing edge is solved exactly to enforce loop closure,
    - polygon must be simple (no self-intersections),
    - polygon area must be integer and at least `min_area_square_units`,
    - final span in both axes is bounded by `max_span_units`.
    """
    n_sides = int(sides)
    if n_sides < 3:
        raise ValueError("sides must be >= 3")
    span_limit = max(2, int(max_span_units))
    vector_pool = integer_length_vectors(
        max_abs_component=int(max_abs_component),
        min_edge_length=int(min_edge_length),
        max_edge_length=int(max_edge_length),
    )
    vector_set = {(int(dx), int(dy)) for dx, dy, _length in vector_pool}

    for _ in range(max(1, int(max_attempts))):
        edges: List[UnitPoint] = []
        sum_x = 0
        sum_y = 0
        valid_prefix = True
        for _edge_idx in range(n_sides - 1):
            chosen: UnitPoint | None = None
            for _ in range(48):
                dx, dy, _length = rng.choice(vector_pool)
                if edges:
                    prev_x, prev_y = edges[-1]
                    if int(prev_x * dy - prev_y * dx) == 0:
                        continue
                trial_sum_x = int(sum_x + dx)
                trial_sum_y = int(sum_y + dy)
                if abs(int(trial_sum_x)) > int(span_limit) or abs(int(trial_sum_y)) > int(span_limit):
                    continue
                chosen = (int(dx), int(dy))
                break
            if chosen is None:
                valid_prefix = False
                break
            edges.append(chosen)
            sum_x = int(sum_x + chosen[0])
            sum_y = int(sum_y + chosen[1])
        if not valid_prefix:
            continue

        closing = (int(-sum_x), int(-sum_y))
        if closing == (0, 0) or closing not in vector_set:
            continue
        if edges:
            prev_x, prev_y = edges[-1]
            if int(prev_x * closing[1] - prev_y * closing[0]) == 0:
                continue
        edges.append(closing)
        if len(edges) != n_sides:
            continue

        if any(
            int(edges[idx][0]) == int(-edges[(idx + 1) % n_sides][0])
            and int(edges[idx][1]) == int(-edges[(idx + 1) % n_sides][1])
            for idx in range(n_sides)
        ):
            continue

        vertices: List[UnitPoint] = [(0, 0)]
        cursor_x = 0
        cursor_y = 0
        for dx, dy in edges[:-1]:
            cursor_x = int(cursor_x + dx)
            cursor_y = int(cursor_y + dy)
            vertices.append((int(cursor_x), int(cursor_y)))
        if len(vertices) != n_sides or len(set(vertices)) != n_sides:
            continue
        if not _is_simple_polygon(vertices):
            continue

        min_x = min(int(point[0]) for point in vertices)
        max_x = max(int(point[0]) for point in vertices)
        min_y = min(int(point[1]) for point in vertices)
        max_y = max(int(point[1]) for point in vertices)
        if int(max_x - min_x) > int(span_limit) or int(max_y - min_y) > int(span_limit):
            continue

        double_area = 0
        for idx, (x_value, y_value) in enumerate(vertices):
            next_x, next_y = vertices[(idx + 1) % n_sides]
            double_area += (int(x_value) * int(next_y)) - (int(y_value) * int(next_x))
        if abs(int(double_area)) < int(2 * int(min_area_square_units)):
            continue
        if abs(int(double_area)) % 2 != 0:
            continue

        ordered_vertices = tuple((int(point[0]), int(point[1])) for point in (reversed(vertices) if double_area < 0 else vertices))
        template_id = f"procedural_{int(n_sides)}_{_polygon_signature(ordered_vertices)}"
        return PolygonTemplate(template_id=str(template_id), vertices=ordered_vertices)

    raise ValueError("failed to sample procedural polygon template")


def polygon_area_square_units(vertices: Sequence[UnitPoint]) -> int:
    """Return integer polygon area in graph square units."""
    if len(vertices) < 3:
        raise ValueError("polygon must contain at least 3 vertices")
    double_area = 0
    for index, (x_value, y_value) in enumerate(vertices):
        next_x, next_y = vertices[(index + 1) % len(vertices)]
        double_area += (int(x_value) * int(next_y)) - (int(y_value) * int(next_x))
    if abs(double_area) % 2 != 0:
        raise ValueError("polygon area must resolve to integer square units")
    return int(abs(double_area) // 2)


def polygon_perimeter_units(vertices: Sequence[UnitPoint], *, tol: float = 1e-6) -> int:
    """Return integer Euclidean perimeter in graph units."""
    if len(vertices) < 3:
        raise ValueError("polygon must contain at least 3 vertices")
    perimeter = 0.0
    for index, (x_value, y_value) in enumerate(vertices):
        next_x, next_y = vertices[(index + 1) % len(vertices)]
        perimeter += math.hypot(float(next_x) - float(x_value), float(next_y) - float(y_value))
    rounded = int(round(perimeter))
    if abs(perimeter - float(rounded)) > float(tol):
        raise ValueError("polygon perimeter is not integer in graph units")
    return int(rounded)


def transform_unit_vertices(vertices: Sequence[UnitPoint], *, transform_index: int) -> Tuple[UnitPoint, ...]:
    """Apply one lattice-preserving dihedral transform to integer vertices."""
    out: List[UnitPoint] = []
    for x_value, y_value in vertices:
        x_val, y_val = int(x_value), int(y_value)
        transforms: Tuple[UnitPoint, ...] = (
            (x_val, y_val),
            (-y_val, x_val),
            (-x_val, -y_val),
            (y_val, -x_val),
            (-x_val, y_val),
            (y_val, x_val),
            (x_val, -y_val),
            (-y_val, -x_val),
        )
        out.append(transforms[int(transform_index) % len(transforms)])
    return tuple(out)


def unit_vertices_to_pixel(vertices: Sequence[UnitPoint], *, center: Point, spacing: int) -> Tuple[Point, ...]:
    """Map integer unit vertices to pixel coordinates under one graph frame."""
    cx, cy = float(center[0]), float(center[1])
    scale = int(spacing)
    return tuple(
        (
            cx + float(int(x_value) * scale),
            cy + float(int(y_value) * scale),
        )
        for x_value, y_value in vertices
    )


def sample_polygon_center(
    rng,
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None = None,
    unit_vertices: Sequence[UnitPoint],
    padding_units: int = 1,
) -> Point:
    """Sample one center so all polygon vertices remain inside a padded canvas."""
    vertices = tuple((int(point[0]), int(point[1])) for point in unit_vertices)
    if not vertices:
        raise ValueError("unit_vertices must be non-empty")
    x_offsets = [0, *[int(x_value) for x_value, _ in vertices]]
    y_offsets = [0, *[int(y_value) for _, y_value in vertices]]
    return sample_lattice_point_with_offsets(
        rng,
        canvas_size=int(canvas_size),
        spacing=int(graph_spacing),
        x_offsets=x_offsets,
        y_offsets=y_offsets,
        lattice_origin=(
            (float(graph_origin[0]), float(graph_origin[1]))
            if graph_origin is not None
            else None
        ),
        padding=int(max(0, int(padding_units)) * int(graph_spacing)),
    )


def build_polygon_instance(
    *,
    template: PolygonTemplate,
    center: Point,
    spacing: int,
    transform_index: int,
    labels: Sequence[str],
    canvas_size: int,
) -> PolygonInstance:
    """Build one transformed polygon instance and validate in-canvas constraints."""
    unit_vertices = transform_unit_vertices(template.vertices, transform_index=int(transform_index))
    pixel_vertices = unit_vertices_to_pixel(unit_vertices, center=center, spacing=int(spacing))
    if not all(point_inside_square_canvas(point, canvas_size=int(canvas_size)) for point in pixel_vertices):
        raise ValueError("polygon instance exceeds canvas bounds")
    area = polygon_area_square_units(unit_vertices)
    perimeter = polygon_perimeter_units(unit_vertices)
    return PolygonInstance(
        template_id=str(template.template_id),
        sides=int(template.sides),
        area_square_units=int(area),
        perimeter_units=int(perimeter),
        vertices=tuple((float(point[0]), float(point[1])) for point in pixel_vertices),
        labels=tuple(str(label) for label in labels),
    )


def sample_polygon_instance_on_graph_paper(
    rng,
    *,
    allowed_sides: Sequence[int],
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None = None,
    padding_units: int = 1,
    max_attempts: int = 220,
    min_area_square_units: int = 4,
) -> PolygonInstance:
    """Sample one valid procedurally generated polygon instance for a scene."""
    side_options = sorted({int(side) for side in allowed_sides if int(side) >= 3})
    if not side_options:
        raise ValueError("allowed_sides must include at least one value >= 3")
    spacing_px = max(1, int(graph_spacing))
    estimated_cells_per_side = max(2, int(round(float(int(canvas_size)) / float(spacing_px))))
    span_limit = max(3, int(estimated_cells_per_side) - 2)
    for _ in range(max(1, int(max_attempts))):
        template = sample_procedural_polygon_template(
            rng,
            sides=int(rng.choice(side_options)),
            max_span_units=int(span_limit),
            min_area_square_units=int(min_area_square_units),
            max_attempts=64,
        )
        labels = rotate_labels(
            alphabetic_labels(template.sides, start_index=int(rng.randrange(26))),
            shift=int(rng.randrange(template.sides)),
        )
        transform_index = int(rng.randrange(8))
        transformed_vertices = transform_unit_vertices(template.vertices, transform_index=transform_index)
        try:
            center = sample_polygon_center(
                rng,
                canvas_size=int(canvas_size),
                graph_spacing=int(graph_spacing),
                graph_origin=(
                    (float(graph_origin[0]), float(graph_origin[1]))
                    if graph_origin is not None
                    else None
                ),
                unit_vertices=transformed_vertices,
                padding_units=int(padding_units),
            )
        except ValueError:
            continue
        try:
            return build_polygon_instance(
                template=template,
                center=center,
                spacing=int(graph_spacing),
                transform_index=transform_index,
                labels=labels,
                canvas_size=int(canvas_size),
            )
        except ValueError:
            continue
    raise ValueError("failed to sample polygon instance for current scene constraints")


def draw_polygon_outline(
    draw: ImageDraw.ImageDraw,
    *,
    vertices: Sequence[Point],
    line_width: int,
    line_color: Tuple[int, int, int] = (22, 22, 22),
) -> None:
    """Draw polygon boundary only (no center marker)."""
    points = [tuple(vertex) for vertex in vertices]
    if not points:
        return
    closed = [*points, points[0]]
    draw.line(closed, fill=tuple(int(value) for value in line_color), width=max(1, int(line_width)))


def draw_polygon_labels(
    draw: ImageDraw.ImageDraw,
    *,
    vertices: Sequence[Point],
    labels: Sequence[str],
    label_offset_px: float,
    font_size_px: int,
    text_stroke_width: int | None = None,
    label_color: Tuple[int, int, int] = (24, 24, 24),
    label_stroke_color: Tuple[int, int, int] = (252, 252, 252),
    canvas_size: int | None = None,
) -> None:
    """Draw polygon vertex labels with overlap-aware placement."""
    if not vertices or len(vertices) != len(labels):
        return
    centroid_x = float(sum(float(point[0]) for point in vertices) / float(len(vertices)))
    centroid_y = float(sum(float(point[1]) for point in vertices) / float(len(vertices)))
    offset = float(max(8.0, float(label_offset_px)))
    font = load_font(int(font_size_px), bold=True)
    stroke_width = (
        int(text_stroke_width)
        if text_stroke_width is not None
        else max(1, int(round(0.08 * float(max(8, int(font_size_px))))))
    )
    segments: List[Tuple[Point, Point]] = []
    for index in range(len(vertices)):
        seg_a = vertices[index]
        seg_b = vertices[(index + 1) % len(vertices)]
        segments.append(
            (
                (float(seg_a[0]), float(seg_a[1])),
                (float(seg_b[0]), float(seg_b[1])),
            )
        )
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    for label, point in zip(labels, vertices):
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
            line_clearance_px=2.0,
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


def polygon_scene_entity(instance: PolygonInstance) -> Dict[str, Any]:
    """Build `scene_ir.entities` entry for one polygon instance."""
    return {
        "entity_id": "polygon_1",
        "entity_type": "polygon",
        "attrs": {
            "polygon_sides": int(instance.sides),
            "template_id": str(instance.template_id),
            "area_square_units": int(instance.area_square_units),
            "perimeter_units": int(instance.perimeter_units),
            "vertices": [[float(point[0]), float(point[1])] for point in instance.vertices],
            "labels": [str(label) for label in instance.labels],
        },
    }


def polygon_render_anchor(instance: PolygonInstance) -> Dict[str, Any]:
    """Build deterministic render-map anchor for one polygon instance."""
    vertices = [[float(point[0]), float(point[1])] for point in instance.vertices]
    return {
        "point": list(vertices[0]),
        "polyline": [*vertices, list(vertices[0])],
        "coord_space": "pixel",
    }


def polygon_vertices_evidence_artifacts(
    *,
    instance: PolygonInstance,
    graph_origin: Point,
    graph_spacing: int,
) -> Dict[str, Any]:
    """Build evidence/witness/projection payload for polygon-vertex-set evidence."""
    pixel_vertices = [[float(point[0]), float(point[1])] for point in instance.vertices]
    grid_vertices = [
        pixel_point_to_graph_units(
            (float(point[0]), float(point[1])),
            origin=(float(graph_origin[0]), float(graph_origin[1])),
            spacing=int(graph_spacing),
        )
        for point in pixel_vertices
    ]
    return {
        "evidence_type": "grid_point_set",
        "evidence_value": [list(point) for point in grid_vertices],
        "witness_symbolic": {"type": "polygon_vertex_set", "entity_id": "polygon_1"},
        "projected_evidence": {
            "point_set": [list(point) for point in pixel_vertices],
            "point_path": [list(point) for point in pixel_vertices],
            "grid_point_set": [list(point) for point in grid_vertices],
            "grid_point_path": [list(point) for point in grid_vertices],
        },
    }


def alphabetic_labels(count: int, *, start_index: int = 0) -> Tuple[str, ...]:
    """Return deterministic alphabetic labels for a requested vertex count."""
    total = int(count)
    if total <= 0:
        raise ValueError("count must be positive")
    labels: List[str] = []
    for idx in range(total):
        absolute = int(start_index) + idx
        labels.append(chr(ord("A") + (absolute % 26)))
    return tuple(labels)


def rotate_labels(labels: Sequence[str], *, shift: int) -> Tuple[str, ...]:
    """Rotate label ordering by one deterministic shift."""
    return tuple(rotate_sequence([str(label) for label in labels], shift=int(shift)))
