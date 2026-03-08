"""Shared circle/ellipse sampling and evidence helpers for geometry tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...shared.geometry_primitives import Point
from .graph_paper import lattice_axis_coordinates_for_offsets, sample_lattice_point_with_offsets


@dataclass(frozen=True)
class EllipseInstance:
    """One axis-aligned ellipse sampled on graph-paper coordinates."""

    center: Point
    semi_axis_x_units: int
    semi_axis_y_units: int

    @property
    def area_pi_coefficient(self) -> int:
        """Return integer coefficient `k` in ellipse area `kπ`."""
        return int(self.semi_axis_x_units) * int(self.semi_axis_y_units)


@dataclass(frozen=True)
class CircleInstance:
    """One circle sampled on graph-paper coordinates."""

    center: Point
    radius_units: int

    @property
    def area_pi_coefficient(self) -> int:
        """Return integer coefficient `k` in circle area `kπ`."""
        return int(self.radius_units) * int(self.radius_units)

    @property
    def circumference_pi_coefficient(self) -> int:
        """Return integer coefficient `k` in circle circumference `kπ`."""
        return 2 * int(self.radius_units)


def ellipse_axis_pairs(
    *,
    axis_min: int,
    axis_max: int,
    coefficient_min: int | None = None,
    coefficient_max: int | None = None,
    allow_circle: bool = True,
) -> List[Tuple[int, int]]:
    """Return feasible integer semiaxis pairs for one ellipse area-coefficient range."""
    low = max(1, int(axis_min))
    high = max(int(low), int(axis_max))
    pairs: List[Tuple[int, int]] = []
    for semi_x in range(int(low), int(high) + 1):
        for semi_y in range(int(low), int(high) + 1):
            if (not bool(allow_circle)) and int(semi_x) == int(semi_y):
                continue
            coeff = int(semi_x) * int(semi_y)
            if coefficient_min is not None and int(coeff) < int(coefficient_min):
                continue
            if coefficient_max is not None and int(coeff) > int(coefficient_max):
                continue
            pairs.append((int(semi_x), int(semi_y)))
    return pairs


def circle_radii_for_pi_coefficient(
    *,
    radius_min: int,
    radius_max: int,
    coefficient_min: int | None = None,
    coefficient_max: int | None = None,
    coefficient_scale: int = 2,
) -> List[int]:
    """Return feasible integer radii for one `kπ` coefficient range."""
    low = max(1, int(radius_min))
    high = max(int(low), int(radius_max))
    scale = max(1, int(coefficient_scale))
    values: List[int] = []
    for radius in range(int(low), int(high) + 1):
        coeff = int(scale) * int(radius)
        if coefficient_min is not None and int(coeff) < int(coefficient_min):
            continue
        if coefficient_max is not None and int(coeff) > int(coefficient_max):
            continue
        values.append(int(radius))
    return values


def sample_ellipse_instance_on_graph_paper(
    rng,
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None,
    axis_pairs: Sequence[Tuple[int, int]],
    padding_units: int = 0,
    max_attempts: int = 220,
) -> EllipseInstance:
    """Sample one ellipse center and semiaxes on graph-paper lattice."""
    candidates = [(int(pair[0]), int(pair[1])) for pair in axis_pairs if len(pair) == 2]
    if not candidates:
        raise ValueError("axis_pairs must include at least one pair")
    for _ in range(max(1, int(max_attempts))):
        semi_x_units, semi_y_units = rng.choice(candidates)
        try:
            center = sample_lattice_point_with_offsets(
                rng,
                canvas_size=int(canvas_size),
                spacing=int(graph_spacing),
                x_offsets=[0, -int(semi_x_units), int(semi_x_units)],
                y_offsets=[0, -int(semi_y_units), int(semi_y_units)],
                lattice_origin=(
                    (float(graph_origin[0]), float(graph_origin[1]))
                    if graph_origin is not None
                    else None
                ),
                padding=int(max(0, int(padding_units)) * int(graph_spacing)),
            )
        except ValueError:
            continue
        return EllipseInstance(
            center=(float(center[0]), float(center[1])),
            semi_axis_x_units=int(semi_x_units),
            semi_axis_y_units=int(semi_y_units),
        )
    raise ValueError("failed to sample ellipse instance for current scene constraints")


def feasible_ellipse_axis_pairs_on_graph_paper(
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None,
    axis_pairs: Sequence[Tuple[int, int]],
    padding_units: int = 0,
) -> List[Tuple[int, int]]:
    """Filter ellipse semiaxis pairs that can place a center on the current lattice."""
    origin = (
        (float(graph_origin[0]), float(graph_origin[1]))
        if graph_origin is not None
        else (0.0, 0.0)
    )
    spacing_px = max(1, int(graph_spacing))
    padding_px = int(max(0, int(padding_units)) * int(spacing_px))
    feasible: List[Tuple[int, int]] = []
    for raw_pair in axis_pairs:
        if len(raw_pair) != 2:
            continue
        semi_x_units = int(raw_pair[0])
        semi_y_units = int(raw_pair[1])
        if semi_x_units < 1 or semi_y_units < 1:
            continue
        x_values = lattice_axis_coordinates_for_offsets(
            canvas_size=int(canvas_size),
            spacing=int(spacing_px),
            offsets=[0, -int(semi_x_units), int(semi_x_units)],
            lattice_origin=float(origin[0]),
            padding=int(padding_px),
        )
        if not x_values:
            continue
        y_values = lattice_axis_coordinates_for_offsets(
            canvas_size=int(canvas_size),
            spacing=int(spacing_px),
            offsets=[0, -int(semi_y_units), int(semi_y_units)],
            lattice_origin=float(origin[1]),
            padding=int(padding_px),
        )
        if not y_values:
            continue
        feasible.append((int(semi_x_units), int(semi_y_units)))
    return feasible


def sample_circle_instance_on_graph_paper(
    rng,
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None,
    radii: Sequence[int],
    padding_units: int = 0,
    max_attempts: int = 220,
) -> CircleInstance:
    """Sample one circle center and radius on graph-paper lattice."""
    candidates = [int(radius) for radius in radii if int(radius) >= 1]
    if not candidates:
        raise ValueError("radii must include at least one positive integer")
    for _ in range(max(1, int(max_attempts))):
        radius_units = int(rng.choice(candidates))
        try:
            center = sample_lattice_point_with_offsets(
                rng,
                canvas_size=int(canvas_size),
                spacing=int(graph_spacing),
                x_offsets=[0, -int(radius_units), int(radius_units)],
                y_offsets=[0, -int(radius_units), int(radius_units)],
                lattice_origin=(
                    (float(graph_origin[0]), float(graph_origin[1]))
                    if graph_origin is not None
                    else None
                ),
                padding=int(max(0, int(padding_units)) * int(graph_spacing)),
            )
        except ValueError:
            continue
        return CircleInstance(
            center=(float(center[0]), float(center[1])),
            radius_units=int(radius_units),
        )
    raise ValueError("failed to sample circle instance for current scene constraints")


def feasible_circle_radii_on_graph_paper(
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point | None,
    radii: Sequence[int],
    padding_units: int = 0,
) -> List[int]:
    """Filter circle radii that can place a center on the current lattice."""
    origin = (
        (float(graph_origin[0]), float(graph_origin[1]))
        if graph_origin is not None
        else (0.0, 0.0)
    )
    spacing_px = max(1, int(graph_spacing))
    padding_px = int(max(0, int(padding_units)) * int(spacing_px))
    feasible: List[int] = []
    for raw_radius in radii:
        radius_units = int(raw_radius)
        if radius_units < 1:
            continue
        x_values = lattice_axis_coordinates_for_offsets(
            canvas_size=int(canvas_size),
            spacing=int(spacing_px),
            offsets=[0, -int(radius_units), int(radius_units)],
            lattice_origin=float(origin[0]),
            padding=int(padding_px),
        )
        if not x_values:
            continue
        y_values = lattice_axis_coordinates_for_offsets(
            canvas_size=int(canvas_size),
            spacing=int(spacing_px),
            offsets=[0, -int(radius_units), int(radius_units)],
            lattice_origin=float(origin[1]),
            padding=int(padding_px),
        )
        if not y_values:
            continue
        feasible.append(int(radius_units))
    return feasible


def draw_ellipse_outline(
    draw: ImageDraw.ImageDraw,
    *,
    center: Point,
    semi_axis_x_px: int,
    semi_axis_y_px: int,
    line_width: int,
    line_color: Tuple[int, int, int] = (22, 22, 22),
) -> None:
    """Draw one axis-aligned ellipse boundary."""
    cx, cy = float(center[0]), float(center[1])
    rx = max(1, int(semi_axis_x_px))
    ry = max(1, int(semi_axis_y_px))
    draw.ellipse(
        [cx - float(rx), cy - float(ry), cx + float(rx), cy + float(ry)],
        outline=tuple(int(value) for value in line_color),
        width=max(1, int(line_width)),
    )


def draw_circle_outline(
    draw: ImageDraw.ImageDraw,
    *,
    center: Point,
    radius_px: int,
    line_width: int,
    line_color: Tuple[int, int, int] = (22, 22, 22),
) -> None:
    """Draw one circle boundary."""
    draw_ellipse_outline(
        draw,
        center=center,
        semi_axis_x_px=int(radius_px),
        semi_axis_y_px=int(radius_px),
        line_width=int(line_width),
        line_color=tuple(int(value) for value in line_color),
    )


def ellipse_scene_entity(instance: EllipseInstance, *, entity_id: str = "ellipse_1") -> Dict[str, Any]:
    """Build `scene_ir.entities` entry for one ellipse instance."""
    return {
        "entity_id": str(entity_id),
        "entity_type": "ellipse",
        "attrs": {
            "center": [float(instance.center[0]), float(instance.center[1])],
            "semi_axis_x_units": int(instance.semi_axis_x_units),
            "semi_axis_y_units": int(instance.semi_axis_y_units),
            "area_pi_coefficient": int(instance.area_pi_coefficient),
        },
    }


def circle_scene_entity(instance: CircleInstance, *, entity_id: str = "circle_1") -> Dict[str, Any]:
    """Build `scene_ir.entities` entry for one circle instance."""
    return {
        "entity_id": str(entity_id),
        "entity_type": "circle",
        "attrs": {
            "center": [float(instance.center[0]), float(instance.center[1])],
            "radius_units": int(instance.radius_units),
            "area_pi_coefficient": int(instance.area_pi_coefficient),
            "circumference_pi_coefficient": int(instance.circumference_pi_coefficient),
        },
    }


def conic_render_anchor(
    *,
    center: Point,
    semi_axis_x_px: int,
    semi_axis_y_px: int,
) -> Dict[str, Any]:
    """Build deterministic render-map anchor for one axis-aligned conic."""
    cx, cy = float(center[0]), float(center[1])
    rx = float(max(1, int(semi_axis_x_px)))
    ry = float(max(1, int(semi_axis_y_px)))
    return {
        "point": [float(cx), float(cy)],
        "bbox": [float(cx - rx), float(cy - ry), float(cx + rx), float(cy + ry)],
        "coord_space": "pixel",
    }
