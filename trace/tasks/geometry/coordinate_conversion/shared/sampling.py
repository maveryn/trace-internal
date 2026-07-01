"""Answer-first coordinate-conversion sampling primitives."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence, TypeVar

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default

from .state import CartesianPointCase, PolarPointCase

_CaseT = TypeVar("_CaseT")


def rounded_decimal(value: float, *, digits: int = 1) -> float:
    """Return a stable one-decimal numeric answer without negative zero."""

    rounded = round(float(value), int(digits))
    if abs(float(rounded)) < 0.5 * (10 ** -int(digits)):
        return 0.0
    return float(rounded)


def format_number(value: float | int) -> str:
    """Format a displayed numeric value without unnecessary trailing zeros."""

    numeric = float(value)
    if abs(numeric - round(numeric)) <= 1e-9:
        return str(int(round(numeric)))
    return f"{numeric:.1f}".rstrip("0").rstrip(".")


def canonical_number_key(value: float | int) -> str:
    """Return a compact JSON-stable key for one numeric answer value."""

    return format_number(float(value))


def cartesian_abs_max(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> int:
    """Resolve the Cartesian support bound."""

    return max(4, int(params.get("cartesian_abs_max", group_default(defaults, "cartesian_abs_max", 12))))


def polar_radius_bounds(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> tuple[int, int]:
    """Resolve inclusive polar radius support bounds."""

    radius_min = int(params.get("polar_radius_min", group_default(defaults, "polar_radius_min", 12)))
    radius_max = int(params.get("polar_radius_max", group_default(defaults, "polar_radius_max", 80)))
    radius_min = max(2, int(radius_min))
    radius_max = max(int(radius_min), int(radius_max))
    return int(radius_min), int(radius_max)


def polar_angle_step(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> int:
    """Resolve polar angle step size in degrees."""

    step = int(params.get("polar_angle_step_degrees", group_default(defaults, "polar_angle_step_degrees", 30)))
    if step <= 0 or 360 % step != 0:
        raise ValueError("polar_angle_step_degrees must be a positive divisor of 360")
    return int(step)


def _with_answer_probabilities(
    *,
    cases: Sequence[_CaseT],
    answer_of: Callable[[_CaseT], float],
    selected_answer: float,
) -> tuple[int, dict[str, float]]:
    answers = sorted({canonical_number_key(answer_of(case)) for case in cases}, key=lambda item: float(item))
    probability = 1.0 / float(len(answers)) if answers else 0.0
    return len(answers), {key: (1.0 if key == canonical_number_key(selected_answer) else 0.0) for key in answers} or {}


def _select_answer_first(
    *,
    cases: Sequence[_CaseT],
    answer_of: Callable[[_CaseT], float],
    instance_seed: int,
    namespace: str,
    params: Mapping[str, Any],
) -> tuple[_CaseT, float, int, dict[str, float]]:
    grouped: dict[str, list[_CaseT]] = defaultdict(list)
    for case in cases:
        grouped[canonical_number_key(answer_of(case))].append(case)
    answers = sorted(grouped, key=lambda item: float(item))
    if not answers:
        raise ValueError("coordinate-conversion support is empty")

    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        cursor = abs(int(sample_cursor))
        answer_key = answers[cursor % len(answers)]
        case_group = grouped[answer_key]
        selected_case = case_group[(cursor // len(answers)) % len(case_group)]
    else:
        rng = spawn_rng(int(instance_seed), str(namespace))
        answer_key = str(rng.choice(tuple(answers)))
        selected_case = rng.choice(tuple(grouped[answer_key]))

    selected_answer = float(answer_of(selected_case))
    support_count, probabilities = _with_answer_probabilities(
        cases=cases,
        answer_of=answer_of,
        selected_answer=selected_answer,
    )
    return selected_case, selected_answer, int(support_count), dict(probabilities)


def _cartesian_support(abs_max: int) -> tuple[tuple[int, int, float, float], ...]:
    cases: list[tuple[int, int, float, float]] = []
    for x_value in range(-int(abs_max), int(abs_max) + 1):
        for y_value in range(-int(abs_max), int(abs_max) + 1):
            if x_value == 0 and y_value == 0:
                continue
            radius = rounded_decimal(math.hypot(float(x_value), float(y_value)))
            angle = rounded_decimal(math.degrees(math.atan2(float(y_value), float(x_value))) % 360.0)
            if abs(angle - 360.0) <= 1e-9:
                angle = 0.0
            cases.append((int(x_value), int(y_value), float(radius), float(angle)))
    return tuple(cases)


def select_cartesian_point_case(
    *,
    component: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> CartesianPointCase:
    """Select a Cartesian point after first choosing the requested answer value."""

    resolved_component = str(component)
    if resolved_component not in {"radius", "angle"}:
        raise ValueError(f"unsupported Cartesian polar component: {component!r}")
    candidates = _cartesian_support(cartesian_abs_max(params, generation_defaults))

    def answer_of(raw_case: tuple[int, int, float, float]) -> float:
        return float(raw_case[2] if resolved_component == "radius" else raw_case[3])

    raw, answer, support_count, probabilities = _select_answer_first(
        cases=candidates,
        answer_of=answer_of,
        instance_seed=int(instance_seed),
        namespace=f"geometry.coordinate_conversion.cartesian.{resolved_component}",
        params=params,
    )
    return CartesianPointCase(
        x=int(raw[0]),
        y=int(raw[1]),
        radius=float(raw[2]),
        angle_degrees=float(raw[3]),
        selected_answer=float(answer),
        answer_support_count=int(support_count),
        answer_candidate_probabilities=dict(probabilities),
    )


def _polar_support(radius_min: int, radius_max: int, angle_step_degrees: int) -> tuple[tuple[int, int, float, float], ...]:
    cases: list[tuple[int, int, float, float]] = []
    for radius in range(int(radius_min), int(radius_max) + 1):
        for theta in range(0, 360, int(angle_step_degrees)):
            theta_rad = math.radians(float(theta))
            x_component = rounded_decimal(float(radius) * math.cos(theta_rad))
            y_component = rounded_decimal(float(radius) * math.sin(theta_rad))
            cases.append((int(radius), int(theta), float(x_component), float(y_component)))
    return tuple(cases)


def select_polar_point_case(
    *,
    component: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> PolarPointCase:
    """Select a polar point after first choosing the requested Cartesian component."""

    resolved_component = str(component)
    if resolved_component not in {"x", "y"}:
        raise ValueError(f"unsupported polar Cartesian component: {component!r}")
    radius_min, radius_max = polar_radius_bounds(params, generation_defaults)
    candidates = _polar_support(radius_min, radius_max, polar_angle_step(params, generation_defaults))

    def answer_of(raw_case: tuple[int, int, float, float]) -> float:
        return float(raw_case[2] if resolved_component == "x" else raw_case[3])

    raw, answer, support_count, probabilities = _select_answer_first(
        cases=candidates,
        answer_of=answer_of,
        instance_seed=int(instance_seed),
        namespace=f"geometry.coordinate_conversion.polar.{resolved_component}",
        params=params,
    )
    return PolarPointCase(
        radius=int(raw[0]),
        theta_degrees=int(raw[1]),
        x_component=float(raw[2]),
        y_component=float(raw[3]),
        selected_answer=float(answer),
        answer_support_count=int(support_count),
        answer_candidate_probabilities=dict(probabilities),
    )


__all__ = [
    "canonical_number_key",
    "format_number",
    "rounded_decimal",
    "select_cartesian_point_case",
    "select_polar_point_case",
]
