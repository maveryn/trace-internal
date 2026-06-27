"""Identity-free sampling primitives for polygon equation diagrams."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.seed import spawn_rng

from .algebra import format_angle_expression, format_degrees, format_linear_expression, side_name
from .state import polygon_kind


def _side_count(instance_seed: int, params: Mapping[str, Any], namespace: str) -> int:
    if "side_count" in params:
        value = int(params["side_count"])
        if value not in {3, 4, 5, 6}:
            raise ValueError("side_count must be one of 3, 4, 5, 6")
        return value
    rng = spawn_rng(int(instance_seed), namespace)
    return int(rng.choice((3, 4, 5, 6)))


def _equation_pair_for_value(*, rng: Any, value: int, variable_value: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return two distinct linear expressions that evaluate to the same value."""

    coefficients = (1, 2, 3, 4)
    for _ in range(200):
        first = int(rng.choice(coefficients))
        second = int(rng.choice(coefficients))
        if first == second:
            continue
        return (
            (first, int(value) - (first * int(variable_value))),
            (second, int(value) - (second * int(variable_value))),
        )
    raise ValueError("failed to sample distinct linear expressions")


def _sample_values_for_sum(*, rng: Any, count: int, total: int, min_value: int, max_value: int) -> tuple[int, ...]:
    """Sample integer angle values whose sum is exactly total."""

    for _ in range(8000):
        values = [int(rng.randint(int(min_value), int(max_value))) for _ in range(int(count) - 1)]
        last = int(total) - sum(values)
        if int(min_value) <= last <= int(max_value):
            values.append(last)
            rng.shuffle(values)
            return tuple(int(value) for value in values)
    raise ValueError("failed to sample angle values for requested sum")


def _polygon_angles(side_count: int, *, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[int, ...]:
    rng = spawn_rng(int(instance_seed), namespace)
    min_angle = int(params.get("angle_min", 38))
    max_angle = int(params.get("angle_max", 152))
    return _sample_values_for_sum(
        rng=rng,
        count=int(side_count),
        total=(int(side_count) - 2) * 180,
        min_value=int(min_angle),
        max_value=int(max_angle),
    )


def _target_indices(side_count: int, *, instance_seed: int, namespace: str) -> tuple[int, int]:
    rng = spawn_rng(int(instance_seed), namespace)
    first = int(rng.randrange(int(side_count)))
    gap = int(rng.randrange(1, int(side_count)))
    return first, (first + gap) % int(side_count)


def sample_equal_side_relation(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> dict[str, Any]:
    """Sample a marked equal-side algebraic relation without binding an objective answer."""

    side_count = _side_count(int(instance_seed), params, f"{namespace}.side_count")
    labels = tuple(chr(ord("A") + index) for index in range(side_count))
    rng = spawn_rng(int(instance_seed), namespace)
    variable_name = str(params.get("variable_name", "x"))
    variable_value = int(rng.randint(3, 31))
    side_value = int(rng.randint(12, 96))
    side_a, side_b = _target_indices(side_count, instance_seed=int(instance_seed), namespace=f"{namespace}.sides")
    first_expr, second_expr = _equation_pair_for_value(
        rng=rng,
        value=side_value,
        variable_value=variable_value,
    )
    first_side = side_name(labels, side_a)
    second_side = side_name(labels, side_b)
    side_labels = {
        first_side: format_linear_expression(first_expr[0], variable_name, first_expr[1]),
        second_side: format_linear_expression(second_expr[0], variable_name, second_expr[1]),
    }
    return {
        "side_count": int(side_count),
        "variable_name": str(variable_name),
        "variable_value": int(variable_value),
        "side_value": int(side_value),
        "target_side": str(first_side),
        "side_labels": dict(side_labels),
        "equal_sides": (str(first_side), str(second_side)),
        "witness": {
            "polygon_kind": polygon_kind(side_count),
            "variable_value": int(variable_value),
            "equal_side_length": int(side_value),
            "equation": f"{side_labels[first_side]} = {side_labels[second_side]}",
        },
    }


def sample_equal_angle_relation(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> dict[str, Any]:
    """Sample a marked equal-angle algebraic relation without binding an objective answer."""

    side_count = _side_count(int(instance_seed), params, f"{namespace}.side_count")
    labels = tuple(chr(ord("A") + index) for index in range(side_count))
    rng = spawn_rng(int(instance_seed), namespace)
    variable_name = str(params.get("variable_name", "x"))
    variable_value = int(rng.randint(4, 41))
    angle_value = int(rng.randint(42, 132))
    first_index, second_index = _target_indices(
        side_count,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.angles",
    )
    first_expr, second_expr = _equation_pair_for_value(
        rng=rng,
        value=angle_value,
        variable_value=variable_value,
    )
    first_angle = labels[first_index]
    second_angle = labels[second_index]
    angle_labels = {
        first_angle: format_angle_expression(first_expr[0], variable_name, first_expr[1]),
        second_angle: format_angle_expression(second_expr[0], variable_name, second_expr[1]),
    }
    return {
        "side_count": int(side_count),
        "variable_name": str(variable_name),
        "variable_value": int(variable_value),
        "angle_value": int(angle_value),
        "target_angle": str(first_angle),
        "angle_labels": dict(angle_labels),
        "equal_angles": (str(first_angle), str(second_angle)),
        "witness": {
            "polygon_kind": polygon_kind(side_count),
            "variable_value": int(variable_value),
            "equal_angle_measure": int(angle_value),
            "equation": f"{angle_labels[first_angle]} = {angle_labels[second_angle]}",
        },
    }


def sample_interior_angle_sum_relation(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    namespace: str,
) -> dict[str, Any]:
    """Sample polygon interior-angle labels without binding an objective answer."""

    side_count = _side_count(int(instance_seed), params, f"{namespace}.side_count")
    labels = tuple(chr(ord("A") + index) for index in range(side_count))
    rng = spawn_rng(int(instance_seed), namespace)
    variable_name = str(params.get("variable_name", "x"))
    angles = _polygon_angles(
        side_count,
        instance_seed=int(instance_seed),
        params={**dict(generation_defaults), **dict(params)},
        namespace=f"{namespace}.angles",
    )
    target_index = int(rng.randrange(side_count))
    variable_value = int(rng.randint(12, 96))
    expression_count = 2 if side_count <= 4 else 3
    expression_indices = [target_index]
    for offset in range(1, side_count):
        if len(expression_indices) >= expression_count:
            break
        expression_indices.append((target_index + offset) % side_count)

    angle_labels: dict[str, str] = {}
    expression_values: dict[str, int] = {}
    for index, value in enumerate(angles):
        label = labels[index]
        if index in expression_indices:
            coefficient = 1 if index == target_index else int(rng.choice((1, 2, 3)))
            offset = int(value) - (int(coefficient) * int(variable_value))
            angle_labels[label] = format_angle_expression(coefficient, variable_name, offset)
            expression_values[label] = int(value)
        else:
            angle_labels[label] = format_degrees(int(value))

    target_angle = labels[target_index]
    return {
        "side_count": int(side_count),
        "variable_name": str(variable_name),
        "variable_value": int(variable_value),
        "target_angle": str(target_angle),
        "target_angle_value": int(angles[target_index]),
        "angle_labels": dict(angle_labels),
        "witness": {
            "polygon_kind": polygon_kind(side_count),
            "variable_value": int(variable_value),
            "numeric_angle_values": [int(value) for value in angles],
            "expression_values": dict(expression_values),
            "equation": f"sum(interior_angles) = {(side_count - 2) * 180}",
        },
    }


__all__ = [
    "sample_equal_angle_relation",
    "sample_equal_side_relation",
    "sample_interior_angle_sum_relation",
]
