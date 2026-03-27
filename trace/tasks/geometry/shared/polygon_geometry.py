"""Shared procedural polygon sampling, rendering, and metric helpers."""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Sequence, Tuple

from PIL import ImageDraw

from ...shared.geometry_primitives import Point, point_inside_square_canvas
from ...shared.sequence import rotate_sequence
from ...shared.text_rendering import draw_text_centered, load_font, resolve_text_label_center
from .graph_paper import sample_lattice_point_with_offsets
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


def _has_adjacent_collinear_vertices(vertices: Sequence[UnitPoint]) -> bool:
    """Return true when any adjacent polygon triple is collinear.

    Geometry measurement tasks treat `n`-gons as visually distinct polygons, so
    adjacent collinear vertices are rejected instead of silently accepting a
    degenerate `n`-gon whose boundary collapses to fewer effective sides.
    """

    n = int(len(vertices))
    if n < 3:
        return True
    for index in range(n):
        prev_point = vertices[index - 1]
        point = vertices[index]
        next_point = vertices[(index + 1) % n]
        if int(_segment_orientation(prev_point, point, next_point)) == 0:
            return True
    return False


def _polygon_signature(vertices: Sequence[UnitPoint]) -> str:
    """Return deterministic short signature for one polygon unit-vertex sequence."""
    payload = ";".join(f"{int(point[0])},{int(point[1])}" for point in vertices)
    digest = hashlib.blake2s(payload.encode("utf-8"), digest_size=6).hexdigest()
    return str(digest)


def _polygon_probe_seed(*parts: Any) -> int:
    """Return a stable integer seed for deterministic polygon-support probes."""
    payload = "|".join(str(part) for part in parts)
    return int.from_bytes(hashlib.blake2s(payload.encode("utf-8"), digest_size=8).digest(), "big")


def sample_procedural_polygon_template(
    rng,
    *,
    sides: int,
    max_span_units: int,
    max_abs_component: int = 8,
    min_edge_length: int = 2,
    max_edge_length: int = 10,
    min_area_square_units: int = 4,
    required_edge_length: int | None = None,
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
    vector_lengths = {(int(dx), int(dy)): int(length) for dx, dy, length in vector_pool}
    vectors_by_length: Dict[int, Tuple[Tuple[int, int, int], ...]] = {}
    for dx, dy, length in vector_pool:
        vectors_by_length.setdefault(int(length), []).append((int(dx), int(dy), int(length)))
    required_length = None if required_edge_length is None else int(required_edge_length)
    required_pool = tuple(vectors_by_length.get(int(required_length), ())) if required_length is not None else ()
    if required_length is not None and not required_pool:
        raise ValueError("required_edge_length has no feasible lattice vectors under current polygon constraints")

    for _ in range(max(1, int(max_attempts))):
        edges: List[Tuple[int, int, int]] = []
        sum_x = 0
        sum_y = 0
        valid_prefix = True
        required_edge_index = int(rng.randrange(n_sides)) if required_length is not None else -1
        for _edge_idx in range(n_sides - 1):
            candidate_pool = required_pool if int(_edge_idx) == int(required_edge_index) else vector_pool
            chosen: Tuple[int, int, int] | None = None
            for _ in range(48):
                dx, dy, length = rng.choice(candidate_pool)
                if edges:
                    prev_x, prev_y, _prev_length = edges[-1]
                    if int(prev_x * dy - prev_y * dx) == 0:
                        continue
                trial_sum_x = int(sum_x + dx)
                trial_sum_y = int(sum_y + dy)
                if abs(int(trial_sum_x)) > int(span_limit) or abs(int(trial_sum_y)) > int(span_limit):
                    continue
                chosen = (int(dx), int(dy), int(length))
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
        if closing == (0, 0) or closing not in vector_lengths:
            continue
        closing_length = int(vector_lengths[closing])
        if required_length is not None and int(required_edge_index) == int(n_sides - 1) and int(closing_length) != int(required_length):
            continue
        if edges:
            prev_x, prev_y, _prev_length = edges[-1]
            if int(prev_x * closing[1] - prev_y * closing[0]) == 0:
                continue
        edges.append((int(closing[0]), int(closing[1]), int(closing_length)))
        if len(edges) != n_sides:
            continue
        if required_length is not None and not any(int(length) == int(required_length) for _dx, _dy, length in edges):
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
        for dx, dy, _length in edges[:-1]:
            cursor_x = int(cursor_x + dx)
            cursor_y = int(cursor_y + dy)
            vertices.append((int(cursor_x), int(cursor_y)))
        if len(vertices) != n_sides or len(set(vertices)) != n_sides:
            continue
        if _has_adjacent_collinear_vertices(vertices):
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


@lru_cache(maxsize=64)
def feasible_polygon_side_lengths(
    *,
    sides: int,
    max_span_units: int,
    min_edge_length: int = 2,
    max_edge_length: int = 10,
    max_abs_component: int = 8,
    min_area_square_units: int = 4,
    probe_attempts_per_length: int = 6,
    template_attempts_per_probe: int = 96,
) -> Tuple[int, ...]:
    """Return targeted polygon side lengths that are feasible under current bounds.

    The probe is deterministic and is used when tasks need to sample a target
    polygon-side answer before scene placement, so smaller/easier layouts do
    not dominate the realized answer distribution.
    """

    span_limit = max(3, int(max_span_units))
    lo = max(1, int(min_edge_length))
    hi = min(int(max_edge_length), int(span_limit))
    if int(lo) > int(hi):
        return tuple()

    feasible: List[int] = []
    for target_length in range(int(lo), int(hi) + 1):
        found = False
        for probe_index in range(max(1, int(probe_attempts_per_length))):
            probe_rng = random.Random(
                _polygon_probe_seed(
                    "polygon_side_support",
                    int(sides),
                    int(span_limit),
                    int(lo),
                    int(hi),
                    int(max_abs_component),
                    int(min_area_square_units),
                    int(target_length),
                    int(probe_index),
                )
            )
            try:
                sample_procedural_polygon_template(
                    probe_rng,
                    sides=int(sides),
                    max_span_units=int(span_limit),
                    max_abs_component=int(max_abs_component),
                    min_edge_length=int(lo),
                    max_edge_length=int(hi),
                    min_area_square_units=int(min_area_square_units),
                    required_edge_length=int(target_length),
                    max_attempts=int(template_attempts_per_probe),
                )
                found = True
                break
            except ValueError:
                continue
        if found:
            feasible.append(int(target_length))
    return tuple(int(value) for value in feasible)


@lru_cache(maxsize=64)
def required_graph_cells_for_polygon_side_length(
    *,
    sides: int,
    target_length: int,
    max_span_units: int,
    min_edge_length: int = 2,
    max_edge_length: int = 10,
    max_abs_component: int = 8,
    min_area_square_units: int = 4,
    probe_attempts_per_span: int = 6,
    template_attempts_per_probe: int = 96,
) -> int:
    """Return the minimum graph-cell count that supports one targeted side length."""

    span_limit = max(3, int(max_span_units))
    side_count = int(sides)
    edge_length = int(target_length)
    lo = max(1, int(min_edge_length))
    hi = min(int(max_edge_length), int(span_limit))
    if int(edge_length) < int(lo) or int(edge_length) > int(hi):
        raise ValueError("target_length is outside configured polygon edge bounds")

    min_span_guess = max(2, int(edge_length))
    for span_units in range(int(min_span_guess), int(span_limit) + 1):
        for probe_index in range(max(1, int(probe_attempts_per_span))):
            probe_rng = random.Random(
                _polygon_probe_seed(
                    "polygon_side_min_span",
                    int(side_count),
                    int(span_units),
                    int(lo),
                    int(hi),
                    int(max_abs_component),
                    int(min_area_square_units),
                    int(edge_length),
                    int(probe_index),
                )
            )
            try:
                sample_procedural_polygon_template(
                    probe_rng,
                    sides=int(side_count),
                    max_span_units=int(span_units),
                    max_abs_component=int(max_abs_component),
                    min_edge_length=int(lo),
                    max_edge_length=int(hi),
                    min_area_square_units=int(min_area_square_units),
                    required_edge_length=int(edge_length),
                    max_attempts=int(template_attempts_per_probe),
                )
                return int(span_units) + 2
            except ValueError:
                continue
    raise ValueError("failed to resolve minimum graph-cell support for polygon side length")


@lru_cache(maxsize=32)
def _triangle_integer_edge_specs(max_span_units: int) -> Tuple[Tuple[int, int, int], ...]:
    """Return `(base_units, apex_x_units, height_units)` specs with integer side lengths."""
    span_limit = max(2, int(max_span_units))
    vectors = integer_length_vectors(
        max_abs_component=int(span_limit),
        min_edge_length=1,
        max_edge_length=max(2, int(2 * span_limit)),
    )
    by_height: Dict[int, set[int]] = {}
    for dx, dy, _length in vectors:
        if int(dy) <= 0:
            continue
        by_height.setdefault(int(dy), set()).add(int(dx))

    specs = set()
    for height_units, x_values in by_height.items():
        if int(height_units) > int(span_limit):
            continue
        sorted_x = sorted(int(value) for value in x_values)
        for apex_x_units in sorted_x:
            if int(apex_x_units) <= 0 or int(apex_x_units) > int(span_limit):
                continue
            for other_x_units in sorted_x:
                if int(other_x_units) >= int(apex_x_units):
                    continue
                base_units = int(apex_x_units - int(other_x_units))
                if int(base_units) < 2 or int(base_units) > int(span_limit):
                    continue
                specs.add((int(base_units), int(apex_x_units), int(height_units)))
    return tuple(sorted(specs))


def triangle_integer_edge_specs_for_area(
    *,
    area_square_units: int,
    max_span_units: int,
) -> Tuple[Tuple[int, int, int], ...]:
    """Return integer-edge triangle specs for one target area under span bounds."""
    area_value = int(area_square_units)
    if int(area_value) <= 0:
        return tuple()
    matches = []
    for base_units, apex_x_units, height_units in _triangle_integer_edge_specs(int(max_span_units)):
        if int(base_units * height_units) != int(2 * area_value):
            continue
        matches.append((int(base_units), int(apex_x_units), int(height_units)))
    return tuple(matches)


def _template_span_units(vertices: Sequence[UnitPoint]) -> int:
    """Return the maximum axis span covered by one unit-vertex template."""
    if not vertices:
        raise ValueError("vertices must be non-empty")
    x_values = [int(point[0]) for point in vertices]
    y_values = [int(point[1]) for point in vertices]
    width_units = int(max(x_values) - min(x_values))
    height_units = int(max(y_values) - min(y_values))
    return max(int(width_units), int(height_units))


@lru_cache(maxsize=32)
def _quadrilateral_area_templates(max_span_units: int) -> Tuple[PolygonTemplate, ...]:
    """Return constructive integer-edge quadrilateral templates for exact areas.

    The catalog is used by measurement tasks that need target-first answer
    sampling for 4-gon area. We restrict the family to rectangles and
    integer-edge parallelograms so the resulting `PolygonInstance` remains
    compatible with the shared perimeter contract while still offering broad
    answer coverage.
    """

    span_limit = max(4, int(max_span_units))
    templates_by_signature: Dict[str, PolygonTemplate] = {}
    parallelogram_offsets = {
        (abs(int(dx)), abs(int(dy)))
        for dx, dy, _length in integer_length_vectors(
            max_abs_component=int(span_limit),
            min_edge_length=2,
            max_edge_length=max(2, int(2 * span_limit)),
        )
        if int(dx) > 0 and int(dy) > 0
    }

    def _register(vertices: Sequence[UnitPoint], *, family: str) -> None:
        ordered_vertices = tuple((int(x_value), int(y_value)) for x_value, y_value in vertices)
        if len(set(ordered_vertices)) != 4:
            return
        if _has_adjacent_collinear_vertices(ordered_vertices):
            return
        if not _is_simple_polygon(ordered_vertices):
            return
        if int(_template_span_units(ordered_vertices)) > int(span_limit):
            return
        area_value = int(polygon_area_square_units(ordered_vertices))
        if int(area_value) < 4:
            return
        signature = _polygon_signature(ordered_vertices)
        templates_by_signature.setdefault(
            signature,
            PolygonTemplate(
                template_id=f"{family}_{signature}",
                vertices=ordered_vertices,
            ),
        )

    for width_units in range(2, int(span_limit) + 1):
        for height_units in range(2, int(span_limit) + 1):
            _register(
                (
                    (0, 0),
                    (int(width_units), 0),
                    (int(width_units), int(height_units)),
                    (0, int(height_units)),
                ),
                family="quadrilateral_rectangle",
            )
            for shift_units, slant_height_units in sorted(parallelogram_offsets):
                if int(slant_height_units) != int(height_units):
                    continue
                if int(width_units + shift_units) > int(span_limit):
                    continue
                _register(
                    (
                        (0, 0),
                        (int(width_units), 0),
                        (int(width_units + shift_units), int(slant_height_units)),
                        (int(shift_units), int(slant_height_units)),
                    ),
                    family="quadrilateral_parallelogram",
                )

    return tuple(sorted(templates_by_signature.values(), key=lambda template: str(template.template_id)))


def quadrilateral_area_templates_for_area(
    *,
    area_square_units: int,
    max_span_units: int,
) -> Tuple[PolygonTemplate, ...]:
    """Return constructive quadrilateral templates for one exact target area."""
    area_value = int(area_square_units)
    if int(area_value) <= 0:
        return tuple()
    matches = [
        template
        for template in _quadrilateral_area_templates(int(max_span_units))
        if int(polygon_area_square_units(template.vertices)) == int(area_value)
    ]
    return tuple(matches)


def feasible_quadrilateral_area_values(
    *,
    max_span_units: int,
    area_min: int | None = None,
    area_max: int | None = None,
) -> Tuple[int, ...]:
    """Return exact quadrilateral areas supported by the constructive catalog."""
    values = set()
    for template in _quadrilateral_area_templates(int(max_span_units)):
        area_value = int(polygon_area_square_units(template.vertices))
        if area_min is not None and int(area_value) < int(area_min):
            continue
        if area_max is not None and int(area_value) > int(area_max):
            continue
        values.add(int(area_value))
    return tuple(sorted(values))


def required_graph_cells_for_quadrilateral_area(
    *,
    area_square_units: int,
    max_span_units: int,
) -> int:
    """Return the minimum graph-cell count that supports one quadrilateral area."""
    templates = quadrilateral_area_templates_for_area(
        area_square_units=int(area_square_units),
        max_span_units=int(max_span_units),
    )
    if not templates:
        raise ValueError("no feasible quadrilateral templates for requested area")
    return min(int(_template_span_units(template.vertices)) for template in templates) + 4


def feasible_triangle_area_values(
    *,
    max_span_units: int,
    area_min: int | None = None,
    area_max: int | None = None,
) -> Tuple[int, ...]:
    """Return exact integer triangle-area values with integer-edge lattice triangles."""
    values = set()
    for base_units, _apex_x_units, height_units in _triangle_integer_edge_specs(int(max_span_units)):
        product = int(base_units * height_units)
        if int(product) % 2 != 0:
            continue
        area_value = int(product // 2)
        if area_min is not None and int(area_value) < int(area_min):
            continue
        if area_max is not None and int(area_value) > int(area_max):
            continue
        values.add(int(area_value))
    return tuple(sorted(values))


def _triangle_perimeter_units_for_spec(
    *,
    base_units: int,
    apex_x_units: int,
    height_units: int,
) -> int:
    """Return integer perimeter for one cached integer-edge triangle spec."""
    side_a = int(round(math.hypot(float(apex_x_units), float(height_units))))
    side_b = int(round(math.hypot(float(base_units - apex_x_units), float(height_units))))
    return int(base_units) + int(side_a) + int(side_b)


def triangle_integer_edge_specs_for_perimeter(
    *,
    perimeter_units: int,
    max_span_units: int,
) -> Tuple[Tuple[int, int, int], ...]:
    """Return integer-edge triangle specs for one target perimeter under span bounds."""
    perimeter_value = int(perimeter_units)
    if int(perimeter_value) <= 0:
        return tuple()
    matches = []
    for base_units, apex_x_units, height_units in _triangle_integer_edge_specs(int(max_span_units)):
        if int(
            _triangle_perimeter_units_for_spec(
                base_units=int(base_units),
                apex_x_units=int(apex_x_units),
                height_units=int(height_units),
            )
        ) != int(perimeter_value):
            continue
        matches.append((int(base_units), int(apex_x_units), int(height_units)))
    return tuple(matches)


def feasible_triangle_perimeter_values(
    *,
    max_span_units: int,
    perimeter_min: int | None = None,
    perimeter_max: int | None = None,
) -> Tuple[int, ...]:
    """Return exact integer triangle perimeters with integer-edge lattice triangles."""
    values = set()
    for base_units, apex_x_units, height_units in _triangle_integer_edge_specs(int(max_span_units)):
        perimeter_value = int(
            _triangle_perimeter_units_for_spec(
                base_units=int(base_units),
                apex_x_units=int(apex_x_units),
                height_units=int(height_units),
            )
        )
        if perimeter_min is not None and int(perimeter_value) < int(perimeter_min):
            continue
        if perimeter_max is not None and int(perimeter_value) > int(perimeter_max):
            continue
        values.add(int(perimeter_value))
    return tuple(sorted(values))


def _span_limit_for_graph_scene(*, canvas_size: int, graph_spacing: int, padding_units: int) -> int:
    """Return a conservative unit-span limit for one graph-paper scene.

    The renderer can leave partial cells at the canvas edges, so we keep an
    extra two-cell safety band beyond the requested interior padding.
    """

    spacing_px = max(1, int(graph_spacing))
    estimated_cells_per_side = max(2, int(round(float(int(canvas_size)) / float(spacing_px))))
    safety_cells = 2 + (2 * max(0, int(padding_units)))
    return max(3, int(estimated_cells_per_side) - int(safety_cells))


def sample_triangle_instance_with_area_on_graph_paper(
    rng,
    *,
    area_square_units: int,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None = None,
    padding_units: int = 1,
    max_attempts: int = 220,
) -> PolygonInstance:
    """Sample one graph-paper triangle with the requested integer area."""
    span_limit = _span_limit_for_graph_scene(
        canvas_size=int(canvas_size),
        graph_spacing=int(graph_spacing),
        padding_units=int(padding_units),
    )
    area_value = int(area_square_units)
    triangle_specs = triangle_integer_edge_specs_for_area(
        area_square_units=int(area_value),
        max_span_units=int(span_limit),
    )
    if not triangle_specs:
        raise ValueError("no feasible integer-edge triangle specs for requested area and graph span")

    for _ in range(max(1, int(max_attempts))):
        base_units, apex_x_units, height_units = rng.choice(triangle_specs)
        unit_vertices: Tuple[UnitPoint, ...] = (
            (0, 0),
            (int(base_units), 0),
            (int(apex_x_units), int(height_units)),
        )
        template = PolygonTemplate(
            template_id=f"triangle_area_{int(area_value)}_{_polygon_signature(unit_vertices)}",
            vertices=tuple(unit_vertices),
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
    raise ValueError("failed to sample triangle instance for requested area and graph-paper constraints")


def sample_triangle_instance_with_perimeter_on_graph_paper(
    rng,
    *,
    perimeter_units: int,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None = None,
    padding_units: int = 1,
    max_attempts: int = 220,
) -> PolygonInstance:
    """Sample one graph-paper triangle with the requested integer perimeter."""
    span_limit = _span_limit_for_graph_scene(
        canvas_size=int(canvas_size),
        graph_spacing=int(graph_spacing),
        padding_units=int(padding_units),
    )
    perimeter_value = int(perimeter_units)
    triangle_specs = triangle_integer_edge_specs_for_perimeter(
        perimeter_units=int(perimeter_value),
        max_span_units=int(span_limit),
    )
    if not triangle_specs:
        raise ValueError("no feasible integer-edge triangle specs for requested perimeter and graph span")

    for _ in range(max(1, int(max_attempts))):
        base_units, apex_x_units, height_units = rng.choice(triangle_specs)
        unit_vertices: Tuple[UnitPoint, ...] = (
            (0, 0),
            (int(base_units), 0),
            (int(apex_x_units), int(height_units)),
        )
        template = PolygonTemplate(
            template_id=f"triangle_perimeter_{int(perimeter_value)}_{_polygon_signature(unit_vertices)}",
            vertices=tuple(unit_vertices),
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
    raise ValueError("failed to sample triangle instance for requested perimeter and graph-paper constraints")


def sample_quadrilateral_instance_with_area_on_graph_paper(
    rng,
    *,
    area_square_units: int,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None = None,
    padding_units: int = 1,
    max_attempts: int = 220,
) -> PolygonInstance:
    """Sample one graph-paper quadrilateral with the requested integer area.

    The template catalog is constructive and exact, so target-first area
    sampling stays balanced instead of drifting toward low-area procedural
    quadrilaterals.
    """

    span_limit = _span_limit_for_graph_scene(
        canvas_size=int(canvas_size),
        graph_spacing=int(graph_spacing),
        padding_units=int(padding_units),
    )
    area_value = int(area_square_units)
    templates = quadrilateral_area_templates_for_area(
        area_square_units=int(area_value),
        max_span_units=int(span_limit),
    )
    if not templates:
        raise ValueError("no feasible quadrilateral templates for requested area and graph span")

    for _ in range(max(1, int(max_attempts))):
        template = rng.choice(templates)
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
    raise ValueError("failed to sample quadrilateral instance for requested area and graph-paper constraints")


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


def classify_polygon_convexity(vertices: Sequence[UnitPoint]) -> str:
    """Return `convex`, `concave`, or `degenerate` for one simple polygon.

    The classification is strict: any adjacent collinear triple or
    self-intersection is treated as `degenerate` so task modules can reject
    borderline cases instead of relying on visual interpretation.
    """

    ordered_vertices = tuple((int(point[0]), int(point[1])) for point in vertices)
    if len(ordered_vertices) < 3:
        raise ValueError("polygon convexity classification requires at least 3 vertices")
    if _has_adjacent_collinear_vertices(ordered_vertices):
        return "degenerate"
    if not _is_simple_polygon(ordered_vertices):
        return "degenerate"

    turn_sign: int | None = None
    for index in range(len(ordered_vertices)):
        orientation = int(
            _segment_orientation(
                ordered_vertices[index - 1],
                ordered_vertices[index],
                ordered_vertices[(index + 1) % len(ordered_vertices)],
            )
        )
        if int(orientation) == 0:
            return "degenerate"
        current_sign = 1 if int(orientation) > 0 else -1
        if turn_sign is None:
            turn_sign = int(current_sign)
            continue
        if int(current_sign) != int(turn_sign):
            return "concave"
    return "convex"


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
    min_edge_length_units: int = 2,
    max_edge_length_units: int = 10,
    max_abs_edge_component: int = 8,
    required_side_length_units: int | None = None,
) -> PolygonInstance:
    """Sample one valid procedurally generated polygon instance for a scene."""
    side_options = sorted({int(side) for side in allowed_sides if int(side) >= 3})
    if not side_options:
        raise ValueError("allowed_sides must include at least one value >= 3")
    span_limit = _span_limit_for_graph_scene(
        canvas_size=int(canvas_size),
        graph_spacing=int(graph_spacing),
        padding_units=int(padding_units),
    )
    for _ in range(max(1, int(max_attempts))):
        template = sample_procedural_polygon_template(
            rng,
            sides=int(rng.choice(side_options)),
            max_span_units=int(span_limit),
            max_abs_component=int(max_abs_edge_component),
            min_edge_length=int(min_edge_length_units),
            max_edge_length=int(max_edge_length_units),
            min_area_square_units=int(min_area_square_units),
            required_edge_length=(
                None if required_side_length_units is None else int(required_side_length_units)
            ),
            max_attempts=192,
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
