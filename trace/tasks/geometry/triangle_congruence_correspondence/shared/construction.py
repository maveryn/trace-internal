"""Construction primitives for congruent-triangle correspondence diagrams."""

from __future__ import annotations

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.vector2d import point_to_list

from .state import (
    MEASUREMENT_ALGEBRAIC_SIDE,
    MEASUREMENT_ANGLE,
    MEASUREMENT_SIDE,
    Point,
    Side,
    TriangleCongruenceCase,
    TriangleGeometry,
)


def labels_for_layout(layout_kind: str) -> tuple[tuple[str, str, str], tuple[str, str, str]]:
    """Return source and target point labels for a layout kind."""

    if str(layout_kind) == "overlap":
        return ("A", "B", "C"), ("D", "C", "B")
    return ("A", "B", "C"), ("D", "E", "F")


def side_name(layout_kind: str, side: Side) -> str:
    """Name a target side from the visible target triangle labels."""

    _source, target = labels_for_layout(str(layout_kind))
    return f"segment {target[int(side[0])]}{target[int(side[1])]}"


def angle_name(layout_kind: str, index: int) -> str:
    """Name a target angle from the visible target triangle labels."""

    _source, target = labels_for_layout(str(layout_kind))
    return f"angle {target[int(index)]}"


def side_endpoint_labels(layout_kind: str, *, source_side: Side, target_side: Side) -> tuple[str, ...]:
    """Return visible point labels needed for one side correspondence."""

    source, target = labels_for_layout(str(layout_kind))
    labels = (
        target[int(target_side[0])],
        target[int(target_side[1])],
        source[int(source_side[0])],
        source[int(source_side[1])],
    )
    return tuple(dict.fromkeys(labels))


def support_side_endpoint_labels(layout_kind: str, *, support_side: Side) -> tuple[str, ...]:
    """Return visible point labels needed for one support side pair."""

    source, target = labels_for_layout(str(layout_kind))
    labels = (
        source[int(support_side[0])],
        source[int(support_side[1])],
        target[int(support_side[0])],
        target[int(support_side[1])],
    )
    return tuple(dict.fromkeys(labels))


def angle_witness_labels(
    layout_kind: str,
    *,
    source_angle_index: int,
    target_angle_index: int,
) -> tuple[str, ...]:
    """Return visible point labels needed for two corresponding angles."""

    source, target = labels_for_layout(str(layout_kind))
    labels = (
        target[int(target_angle_index)],
        target[(int(target_angle_index) - 1) % 3],
        target[(int(target_angle_index) + 1) % 3],
        source[int(source_angle_index)],
        source[(int(source_angle_index) - 1) % 3],
        source[(int(source_angle_index) + 1) % 3],
    )
    return tuple(dict.fromkeys(labels))


def build_side_case(
    *,
    layout_kind: str,
    value: int,
    source_side: Side,
    target_side: Side,
    show_statement: bool,
) -> TriangleCongruenceCase:
    """Build a direct CPCTC side-transfer case."""

    return TriangleCongruenceCase(
        measurement_family=MEASUREMENT_SIDE,
        layout_kind=str(layout_kind),
        answer=int(value),
        target_name=side_name(str(layout_kind), target_side),
        relation="cpctc_corresponding_side_equal",
        source_target_side_value=int(value),
        target_target_side_value=int(value),
        source_side=source_side,
        target_side=target_side,
        support_side=(1, 2),
        show_statement=bool(show_statement),
    )


def build_angle_case(
    *,
    layout_kind: str,
    value: int,
    source_index: int,
    target_index: int,
    show_statement: bool,
) -> TriangleCongruenceCase:
    """Build a direct CPCTC angle-transfer case."""

    return TriangleCongruenceCase(
        measurement_family=MEASUREMENT_ANGLE,
        layout_kind=str(layout_kind),
        answer=int(value),
        target_name=angle_name(str(layout_kind), int(target_index)),
        relation="cpctc_corresponding_angle_equal",
        source_angle_value=int(value),
        target_angle_value=int(value),
        source_angle_index=int(source_index),
        target_angle_index=int(target_index),
        show_statement=bool(show_statement),
    )


def build_algebraic_side_case(
    *,
    layout_kind: str,
    answer: int,
    x_value: int,
    source_target_expression: str,
    source_support_expression: str,
    target_support_expression: str,
    source_side: Side,
    target_side: Side,
    support_side: Side,
) -> TriangleCongruenceCase:
    """Build a CPCTC side-transfer case with a visible algebra step."""

    return TriangleCongruenceCase(
        measurement_family=MEASUREMENT_ALGEBRAIC_SIDE,
        layout_kind=str(layout_kind),
        answer=int(answer),
        target_name=side_name(str(layout_kind), target_side),
        relation="cpctc_algebraic_corresponding_side_equal",
        source_target_side_value=int(answer),
        target_target_side_value=int(answer),
        x_value=int(x_value),
        source_target_expression=str(source_target_expression),
        source_support_expression=str(source_support_expression),
        target_support_expression=str(target_support_expression),
        source_side=source_side,
        target_side=target_side,
        support_side=support_side,
        show_statement=True,
    )


def triangle_geometry(case: TriangleCongruenceCase, *, width: int, height: int, instance_seed: int) -> TriangleGeometry:
    """Place the visible source and target triangles for one construction."""

    rng = spawn_rng(int(instance_seed), f"{case.layout_kind}.triangle_layout")
    if case.layout_kind == "overlap":
        cx = float(width) / 2.0 + rng.uniform(-10.0, 10.0)
        cy = float(height) / 2.0 + rng.uniform(-8.0, 8.0)
        half_base = rng.uniform(115.0, 132.0)
        height_span = rng.uniform(145.0, 165.0)
        b = (cx - half_base, cy)
        c = (cx + half_base, cy)
        a = (cx, cy - height_span)
        d = (cx, cy + height_span)
        return TriangleGeometry(
            source_vertices=(a, b, c),
            target_vertices=(d, c, b),
            source_labels=("A", "B", "C"),
            target_labels=("D", "C", "B"),
            statement="ABC congruent DCB",
        )
    source_center = (float(width) * 0.32 + rng.uniform(-14.0, 12.0), float(height) * 0.54 + rng.uniform(-12.0, 16.0))
    target_center = (float(width) * 0.69 + rng.uniform(-12.0, 14.0), float(height) * 0.54 + rng.uniform(-12.0, 16.0))
    template = ((0.0, -105.0), (-105.0, 80.0), (116.0, 72.0))
    tilt = rng.uniform(-0.05, 0.05)
    source = tuple((source_center[0] + x + (tilt * y), source_center[1] + y) for x, y in template)
    target = tuple((target_center[0] + x - (tilt * y), target_center[1] + y) for x, y in template)
    return TriangleGeometry(
        source_vertices=source,  # type: ignore[arg-type]
        target_vertices=target,  # type: ignore[arg-type]
        source_labels=("A", "B", "C"),
        target_labels=("D", "E", "F"),
        statement="ABC congruent DEF",
    )


def vertices_payload(labels: tuple[str, ...], points: tuple[Point, ...]) -> dict[str, list[float]]:
    """Serialize visible labeled points for trace payloads."""

    return {label: point_to_list(point) for label, point in zip(labels, points, strict=True)}


__all__ = [
    "angle_name",
    "angle_witness_labels",
    "build_algebraic_side_case",
    "build_angle_case",
    "build_side_case",
    "labels_for_layout",
    "side_endpoint_labels",
    "side_name",
    "support_side_endpoint_labels",
    "triangle_geometry",
    "vertices_payload",
]
