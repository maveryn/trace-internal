"""Scene-specific wire conversion formulas and case pools."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any

from .defaults import PI_APPROX
from .state import ResolvedProblem

Case = int | tuple[int, ...]
Resolver = Callable[[Case], ResolvedProblem]

SOURCE_TRAPEZOID = "isosceles_trapezoid_wire"
SOURCE_PARALLELOGRAM = "parallelogram_wire"
SOURCE_CIRCLE = "circle_wire"
TARGET_CUBE_FRAME = "cube_frame"
TARGET_CUBOID_FRAME = "cuboid_frame"
TARGET_RECTANGLE = "rectangle_wire"


def trapezoid_perimeter(top: int, bottom: int, side: int) -> int:
    return int(top) + int(bottom) + 2 * int(side)


def parallelogram_perimeter(base: int, side: int) -> int:
    return 2 * (int(base) + int(side))


def circle_circumference_from_radius(radius: int) -> int:
    return 2 * PI_APPROX * int(radius)


def _tuple_case(case: Case, *, arity: int, name: str) -> tuple[int, ...]:
    if isinstance(case, int):
        raise ValueError(f"{name} case must contain {arity} integers")
    values = tuple(int(value) for value in case)
    if len(values) != int(arity):
        raise ValueError(f"{name} case must contain {arity} integers")
    return values


def _base_problem(
    *,
    source_shape: str,
    target_shape: str = "",
    source_values: dict[str, int],
    target_values: dict[str, int] | None = None,
    answer: int,
    formula: str,
) -> ResolvedProblem:
    return ResolvedProblem(
        source_shape=str(source_shape),
        target_shape=str(target_shape),
        source_values=dict(source_values),
        target_values=dict(target_values or {}),
        answer=int(answer),
        formula_family="wire_shape_conversion",
        formula=str(formula),
        case_probabilities={},
        answer_support_probabilities={},
    )


def resolve_trapezoid_wire_length(case: Case) -> ResolvedProblem:
    top, bottom, side = _tuple_case(case, arity=3, name="trapezoid perimeter")
    answer = trapezoid_perimeter(top, bottom, side)
    return _base_problem(
        source_shape=SOURCE_TRAPEZOID,
        source_values={"top": top, "bottom": bottom, "side": side, "wire_length": answer},
        answer=answer,
        formula="wire_length = top_base + bottom_base + 2 * equal_side",
    )


def resolve_parallelogram_wire_length(case: Case) -> ResolvedProblem:
    base, side = _tuple_case(case, arity=2, name="parallelogram perimeter")
    answer = parallelogram_perimeter(base, side)
    return _base_problem(
        source_shape=SOURCE_PARALLELOGRAM,
        source_values={"base": base, "side": side, "wire_length": answer},
        answer=answer,
        formula="wire_length = 2 * (base + side)",
    )


def resolve_circle_wire_length_from_area(case: Case) -> ResolvedProblem:
    radius = int(case)
    if radius <= 0:
        raise ValueError("circle radius must be positive")
    area = PI_APPROX * radius * radius
    answer = circle_circumference_from_radius(radius)
    return _base_problem(
        source_shape=SOURCE_CIRCLE,
        source_values={"radius": radius, "area": area, "pi": PI_APPROX, "wire_length": answer},
        answer=answer,
        formula="wire_length = 2 * pi * radius, with radius from area = pi * r^2",
    )


def resolve_trapezoid_wire_to_cube_frame(case: Case) -> ResolvedProblem:
    top, bottom, side = _tuple_case(case, arity=3, name="trapezoid to cube frame")
    wire_length = trapezoid_perimeter(top, bottom, side)
    if wire_length % 12 != 0:
        raise ValueError("trapezoid-to-cube frame cases must have perimeter divisible by 12")
    answer = wire_length // 12
    if answer <= 0:
        raise ValueError("cube edge must be positive")
    return _base_problem(
        source_shape=SOURCE_TRAPEZOID,
        target_shape=TARGET_CUBE_FRAME,
        source_values={"top": top, "bottom": bottom, "side": side, "wire_length": wire_length},
        target_values={"edge": answer, "frame_edge_count": 12, "wire_length": wire_length},
        answer=answer,
        formula="cube_edge = source_wire_length / 12",
    )


def resolve_parallelogram_wire_to_cuboid_frame(case: Case) -> ResolvedProblem:
    base, side, length, width = _tuple_case(case, arity=4, name="parallelogram to cuboid frame")
    wire_length = parallelogram_perimeter(base, side)
    answer = wire_length // 4 - int(length) - int(width)
    if 4 * (int(length) + int(width) + int(answer)) != wire_length or answer <= 0:
        raise ValueError("parallelogram-to-cuboid frame case must yield a positive missing edge")
    return _base_problem(
        source_shape=SOURCE_PARALLELOGRAM,
        target_shape=TARGET_CUBOID_FRAME,
        source_values={"base": base, "side": side, "wire_length": wire_length},
        target_values={"length": length, "width": width, "height": answer, "wire_length": wire_length},
        answer=answer,
        formula="cuboid_height = source_wire_length / 4 - length - width",
    )


def resolve_same_wire_circle_to_trapezoid_side(case: Case) -> ResolvedProblem:
    radius, top, bottom = _tuple_case(case, arity=3, name="circle to trapezoid")
    wire_length = circle_circumference_from_radius(radius)
    answer = (wire_length - int(top) - int(bottom)) // 2
    if int(top) + int(bottom) + 2 * int(answer) != wire_length or answer <= 0:
        raise ValueError("circle-to-trapezoid cases must yield a positive equal side")
    return _base_problem(
        source_shape=SOURCE_CIRCLE,
        target_shape=SOURCE_TRAPEZOID,
        source_values={"radius": radius, "wire_length": wire_length, "pi": PI_APPROX},
        target_values={"top": top, "bottom": bottom, "side": answer},
        answer=answer,
        formula="trapezoid_side = (source_circle_wire_length - top_base - bottom_base) / 2",
    )


def resolve_same_wire_polygon_to_rectangle_side(case: Case) -> ResolvedProblem:
    top, bottom, known_side = _tuple_case(case, arity=3, name="polygon to rectangle")
    wire_length = trapezoid_perimeter(top, bottom, known_side)
    answer = wire_length // 2 - int(known_side)
    if 2 * (int(known_side) + int(answer)) != wire_length or answer <= 0:
        raise ValueError("polygon-to-rectangle cases must yield a positive missing side")
    return _base_problem(
        source_shape=SOURCE_TRAPEZOID,
        target_shape=TARGET_RECTANGLE,
        source_values={"top": top, "bottom": bottom, "side": known_side, "wire_length": wire_length},
        target_values={"known_side": known_side, "unknown_side": answer, "wire_length": wire_length},
        answer=answer,
        formula="rectangle_unknown_side = source_wire_length / 2 - known_side",
    )


def _first_case_per_answer(candidates: Iterable[Case], resolver: Resolver, *, limit: int) -> tuple[Case, ...]:
    selected: dict[int, Case] = {}
    for candidate in candidates:
        answer = int(resolver(candidate).answer)
        if answer not in selected:
            selected[answer] = candidate
        if len(selected) >= int(limit):
            break
    return tuple(selected[answer] for answer in sorted(selected))


TRAPEZOID_WIRE_LENGTH_CASES: tuple[Case, ...] = _first_case_per_answer(
    (
        (top, top + extra, side)
        for side in range(3, 26)
        for top in range(4, 36)
        for extra in range(2, min(2 * side, 18), 2)
    ),
    resolve_trapezoid_wire_length,
    limit=80,
)
PARALLELOGRAM_WIRE_LENGTH_CASES: tuple[Case, ...] = _first_case_per_answer(
    ((base, side) for base in range(4, 48) for side in range(3, 28)),
    resolve_parallelogram_wire_length,
    limit=80,
)
CIRCLE_WIRE_LENGTH_FROM_AREA_CASES: tuple[Case, ...] = tuple(range(3, 73))
TRAPEZOID_WIRE_TO_CUBE_FRAME_CASES: tuple[Case, ...] = tuple(
    (3 * edge, 5 * edge, 2 * edge) for edge in range(2, 72)
)
PARALLELOGRAM_WIRE_TO_CUBOID_FRAME_CASES: tuple[Case, ...] = tuple(
    (
        edge + 4 + edge % 7 + 3 + edge % 5,
        edge + 4 + edge % 7 + 3 + edge % 5,
        4 + edge % 7,
        3 + edge % 5,
    )
    for edge in range(2, 72)
)
SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE_CASES: tuple[Case, ...] = tuple(
    (side + 3, 2 * (side + 3), 2 * side + 12) for side in range(4, 74)
)
SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE_CASES: tuple[Case, ...] = tuple(
    (side - 2, side + 2, 5 + side % 7) for side in range(4, 74)
)


def answer_support(cases: Sequence[Case], resolver: Resolver) -> tuple[int, ...]:
    return tuple(sorted({int(resolver(case).answer) for case in cases}))


def bind_case_metadata(
    problem: ResolvedProblem,
    *,
    case_probabilities: dict[str, float],
    support: Sequence[int],
) -> ResolvedProblem:
    probability = 1.0 / float(len(support)) if support else 1.0
    return ResolvedProblem(
        source_shape=problem.source_shape,
        target_shape=problem.target_shape,
        source_values=dict(problem.source_values),
        target_values=dict(problem.target_values),
        answer=int(problem.answer),
        formula_family=str(problem.formula_family),
        formula=str(problem.formula),
        case_probabilities=dict(case_probabilities),
        answer_support_probabilities={str(int(value)): probability for value in support},
    )


def case_key(case_label: str, case: Case) -> str:
    if isinstance(case, int):
        return f"{case_label}:{case}"
    return f"{case_label}:" + "_".join(str(int(value)) for value in case)


__all__ = [
    "CIRCLE_WIRE_LENGTH_FROM_AREA_CASES",
    "Case",
    "PARALLELOGRAM_WIRE_LENGTH_CASES",
    "PARALLELOGRAM_WIRE_TO_CUBOID_FRAME_CASES",
    "Resolver",
    "SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE_CASES",
    "SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE_CASES",
    "SOURCE_CIRCLE",
    "SOURCE_PARALLELOGRAM",
    "SOURCE_TRAPEZOID",
    "TARGET_CUBE_FRAME",
    "TARGET_CUBOID_FRAME",
    "TARGET_RECTANGLE",
    "TRAPEZOID_WIRE_LENGTH_CASES",
    "TRAPEZOID_WIRE_TO_CUBE_FRAME_CASES",
    "answer_support",
    "bind_case_metadata",
    "case_key",
    "circle_circumference_from_radius",
    "parallelogram_perimeter",
    "resolve_circle_wire_length_from_area",
    "resolve_parallelogram_wire_length",
    "resolve_parallelogram_wire_to_cuboid_frame",
    "resolve_same_wire_circle_to_trapezoid_side",
    "resolve_same_wire_polygon_to_rectangle_side",
    "resolve_trapezoid_wire_length",
    "resolve_trapezoid_wire_to_cube_frame",
    "trapezoid_perimeter",
]
