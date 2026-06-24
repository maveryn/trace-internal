"""Sampling primitives for right-triangle altitude theorem cases."""

from __future__ import annotations

from trace.core.seed import spawn_rng

from .state import RightTriangleAltitudeProblem, TheoremValues


def _values(
    left_projection: int,
    right_projection: int,
    altitude: int,
    left_leg: int | None = None,
    right_leg: int | None = None,
) -> TheoremValues:
    return TheoremValues(
        left_projection=int(left_projection),
        right_projection=int(right_projection),
        altitude=int(altitude),
        left_leg=None if left_leg is None else int(left_leg),
        right_leg=None if right_leg is None else int(right_leg),
    )


_ALTITUDE_VALUE_ROWS: tuple[TheoremValues, ...] = (
    _values(4, 9, 6),
    _values(9, 16, 12, 15, 20),
    _values(16, 25, 20),
    _values(25, 36, 30),
    _values(18, 32, 24, 30, 40),
    _values(12, 27, 18),
    _values(36, 64, 48, 60, 80),
    _values(8, 18, 12),
)

_LEG_VALUE_ROWS: tuple[TheoremValues, ...] = (
    _values(9, 16, 12, 15, 20),
    _values(16, 9, 12, 20, 15),
    _values(18, 32, 24, 30, 40),
    _values(32, 18, 24, 40, 30),
    _values(27, 48, 36, 45, 60),
    _values(48, 27, 36, 60, 45),
    _values(36, 64, 48, 60, 80),
)


def _select_case(
    instance_seed: int,
    cases: tuple[RightTriangleAltitudeProblem, ...],
    *,
    seed_namespace: str,
) -> RightTriangleAltitudeProblem:
    if not cases:
        raise ValueError("right-triangle altitude theorem case pool is empty")
    rng = spawn_rng(int(instance_seed), str(seed_namespace))
    index = int(rng.randrange(len(cases)))
    case = cases[index]
    return RightTriangleAltitudeProblem(
        answer=int(case.answer),
        target_name=str(case.target_name),
        target_role=str(case.target_role),
        relation=str(case.relation),
        values=case.values,
        visible_labels=dict(case.visible_labels),
        case_index=int(index),
        layout_seed=int(instance_seed),
    )


def sample_altitude_from_split_hypotenuse(
    instance_seed: int,
    *,
    seed_namespace: str,
) -> RightTriangleAltitudeProblem:
    """Sample a case where the altitude is the unknown geometric mean."""

    cases = tuple(
        RightTriangleAltitudeProblem(
            answer=int(values.altitude),
            target_name="segment AD",
            target_role="altitude",
            relation="altitude_geometric_mean_from_split_hypotenuse",
            values=values,
            visible_labels={
                "left_projection": str(values.left_projection),
                "right_projection": str(values.right_projection),
                "altitude": "?",
            },
            case_index=index,
            layout_seed=int(instance_seed),
        )
        for index, values in enumerate(_ALTITUDE_VALUE_ROWS)
    )
    return _select_case(int(instance_seed), cases, seed_namespace=str(seed_namespace))


def sample_projection_from_altitude(
    instance_seed: int,
    *,
    seed_namespace: str,
) -> RightTriangleAltitudeProblem:
    """Sample a case where one hypotenuse projection is unknown."""

    cases: list[RightTriangleAltitudeProblem] = []
    for values in _ALTITUDE_VALUE_ROWS:
        cases.append(
            RightTriangleAltitudeProblem(
                answer=int(values.right_projection),
                target_name="segment DC",
                target_role="right_projection",
                relation="projection_from_altitude_and_other_projection",
                values=values,
                visible_labels={
                    "left_projection": str(values.left_projection),
                    "right_projection": "?",
                    "altitude": str(values.altitude),
                },
                case_index=len(cases),
                layout_seed=int(instance_seed),
            )
        )
        cases.append(
            RightTriangleAltitudeProblem(
                answer=int(values.left_projection),
                target_name="segment BD",
                target_role="left_projection",
                relation="projection_from_altitude_and_other_projection",
                values=values,
                visible_labels={
                    "left_projection": "?",
                    "right_projection": str(values.right_projection),
                    "altitude": str(values.altitude),
                },
                case_index=len(cases),
                layout_seed=int(instance_seed),
            )
        )
    return _select_case(int(instance_seed), tuple(cases), seed_namespace=str(seed_namespace))


def sample_leg_from_hypotenuse_projection(
    instance_seed: int,
    *,
    seed_namespace: str,
) -> RightTriangleAltitudeProblem:
    """Sample a case where one leg is unknown from hypotenuse and projection."""

    cases: list[RightTriangleAltitudeProblem] = []
    for values in _LEG_VALUE_ROWS:
        if values.left_leg is None or values.right_leg is None:
            continue
        cases.append(
            RightTriangleAltitudeProblem(
                answer=int(values.left_leg),
                target_name="segment AB",
                target_role="left_leg",
                relation="leg_geometric_mean_from_hypotenuse_projection",
                values=values,
                visible_labels={
                    "hypotenuse": str(values.hypotenuse),
                    "left_projection": str(values.left_projection),
                    "left_leg": "?",
                },
                case_index=len(cases),
                layout_seed=int(instance_seed),
            )
        )
        cases.append(
            RightTriangleAltitudeProblem(
                answer=int(values.right_leg),
                target_name="segment AC",
                target_role="right_leg",
                relation="leg_geometric_mean_from_hypotenuse_projection",
                values=values,
                visible_labels={
                    "hypotenuse": str(values.hypotenuse),
                    "right_projection": str(values.right_projection),
                    "right_leg": "?",
                },
                case_index=len(cases),
                layout_seed=int(instance_seed),
            )
        )
    return _select_case(int(instance_seed), tuple(cases), seed_namespace=str(seed_namespace))


def sample_projection_from_leg_and_hypotenuse(
    instance_seed: int,
    *,
    seed_namespace: str,
) -> RightTriangleAltitudeProblem:
    """Sample a case where one projection is unknown from a leg and hypotenuse."""

    cases: list[RightTriangleAltitudeProblem] = []
    for values in _LEG_VALUE_ROWS:
        if values.left_leg is None or values.right_leg is None:
            continue
        cases.append(
            RightTriangleAltitudeProblem(
                answer=int(values.left_projection),
                target_name="segment BD",
                target_role="left_projection",
                relation="projection_length_from_leg_hypotenuse",
                values=values,
                visible_labels={
                    "hypotenuse": str(values.hypotenuse),
                    "left_leg": str(values.left_leg),
                    "left_projection": "?",
                },
                case_index=len(cases),
                layout_seed=int(instance_seed),
            )
        )
        cases.append(
            RightTriangleAltitudeProblem(
                answer=int(values.right_projection),
                target_name="segment DC",
                target_role="right_projection",
                relation="projection_length_from_leg_hypotenuse",
                values=values,
                visible_labels={
                    "hypotenuse": str(values.hypotenuse),
                    "right_leg": str(values.right_leg),
                    "right_projection": "?",
                },
                case_index=len(cases),
                layout_seed=int(instance_seed),
            )
        )
    return _select_case(int(instance_seed), tuple(cases), seed_namespace=str(seed_namespace))


__all__ = [
    "sample_altitude_from_split_hypotenuse",
    "sample_leg_from_hypotenuse_projection",
    "sample_projection_from_altitude",
    "sample_projection_from_leg_and_hypotenuse",
]
