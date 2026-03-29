"""Reusable lattice-polygon sampling and rigid-transform helpers.

These helpers are intentionally narrow: they support the first geometry
transformation/similarity families, which need asymmetric lattice polygons whose
vertices stay on the graph-paper lattice under translation, reflection, and
quarter-turn rotation.
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from ...shared.geometry_primitives import Point


Polygon = Tuple[Point, ...]

_TRIANGLE_TEMPLATES: Tuple[Polygon, ...] = (
    ((-3.0, -1.0), (2.0, -2.0), (1.0, 3.0)),
    ((-2.0, -3.0), (3.0, -1.0), (-1.0, 2.0)),
    ((-3.0, 1.0), (1.0, -2.0), (2.0, 3.0)),
)
_QUADRILATERAL_TEMPLATES: Tuple[Polygon, ...] = (
    ((-3.0, -1.0), (-1.0, 2.0), (3.0, 1.0), (1.0, -3.0)),
    ((-2.0, -3.0), (-3.0, 1.0), (1.0, 3.0), (3.0, -1.0)),
    ((-3.0, 0.0), (-1.0, 3.0), (2.0, 2.0), (3.0, -2.0)),
)

_TEMPLATES_BY_SCENE: Dict[str, Tuple[Polygon, ...]] = {
    "triangle": _TRIANGLE_TEMPLATES,
    "quadrilateral": _QUADRILATERAL_TEMPLATES,
}


def sample_asymmetric_polygon_template(scene_variant: str, rng) -> Polygon:
    """Sample one asymmetric lattice polygon template for the requested family."""

    family = str(scene_variant).strip().lower()
    templates = _TEMPLATES_BY_SCENE.get(family)
    if not templates:
        raise ValueError(f"unsupported transformation scene_variant: {scene_variant}")
    return tuple(rng.choice(list(templates)))


def translate_polygon(vertices: Sequence[Point], *, dx: int, dy: int) -> Polygon:
    """Translate one lattice polygon by an integer graph-unit vector."""

    return tuple((float(x_value) + float(dx), float(y_value) + float(dy)) for x_value, y_value in vertices)


def rotate_polygon_quarter_turns(vertices: Sequence[Point], *, quarter_turns: int) -> Polygon:
    """Rotate one lattice polygon about the origin by 90° steps."""

    steps = int(quarter_turns) % 4
    out = [(float(x_value), float(y_value)) for x_value, y_value in vertices]
    for _ in range(steps):
        out = [(float(y_value), -float(x_value)) for x_value, y_value in out]
    return tuple(out)


def reflect_polygon(vertices: Sequence[Point], *, axis_kind: str) -> Polygon:
    """Reflect one lattice polygon across the requested canonical axis."""

    normalized_axis = str(axis_kind).strip().lower()
    if normalized_axis == "vertical":
        return tuple((-float(x_value), float(y_value)) for x_value, y_value in vertices)
    if normalized_axis == "horizontal":
        return tuple((float(x_value), -float(y_value)) for x_value, y_value in vertices)
    raise ValueError(f"unsupported reflection axis_kind: {axis_kind}")


def polygon_center(vertices: Sequence[Point]) -> Point:
    """Return the arithmetic center of one polygon vertex list."""

    if not vertices:
        raise ValueError("polygon_center requires at least one vertex")
    count = float(len(vertices))
    return (
        sum(float(x_value) for x_value, _ in vertices) / count,
        sum(float(y_value) for _, y_value in vertices) / count,
    )


def ordered_vertex_label_map(vertices: Sequence[Point]) -> Dict[str, Point]:
    """Build the canonical `vertex_i -> point` map used for prompt-facing evidence."""

    return {
        f"vertex_{int(index) + 1}": (float(point[0]), float(point[1]))
        for index, point in enumerate(vertices)
    }


__all__ = [
    "Polygon",
    "ordered_vertex_label_map",
    "polygon_center",
    "reflect_polygon",
    "rotate_polygon_quarter_turns",
    "sample_asymmetric_polygon_template",
    "translate_polygon",
]
