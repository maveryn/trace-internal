"""Numeric construction helpers for polygon angle-chase tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .measurements import (
    VERTEX_LABELS,
    angle_name,
    format_angle_expression,
    format_degrees,
    format_linear_expression,
    polygon_angle_sum,
    probability_map,
)
from .state import ParallelAnglePlan, PolygonAnglePlan, SymmetryAnglePlan


def sample_values_for_sum(
    rng: Any,
    *,
    count: int,
    total: int,
    min_value: int,
    max_value: int,
    step: int,
) -> tuple[int, ...]:
    """Sample integer values from an arithmetic support with a fixed sum."""

    candidates = tuple(range(int(min_value), int(max_value) + 1, int(step)))
    if int(count) <= 0:
        if int(total) != 0:
            raise ValueError("empty angle value set cannot match nonzero total")
        return ()
    for _ in range(3000):
        values = [int(rng.choice(candidates)) for _ in range(max(0, int(count) - 1))]
        last = int(total) - sum(values)
        if last in candidates:
            values.append(int(last))
            rng.shuffle(values)
            return tuple(int(value) for value in values)
    raise ValueError("failed to sample polygon angle values with requested sum")


def sample_candidate_values_for_sum(
    rng: Any,
    *,
    count: int,
    total: int,
    candidates: Sequence[int],
) -> tuple[int, ...]:
    """Sample integer values from explicit candidates with a fixed sum."""

    resolved = tuple(int(value) for value in candidates)
    if int(count) <= 0:
        if int(total) != 0:
            raise ValueError("empty value set cannot match nonzero total")
        return ()
    candidate_set = set(resolved)
    for _ in range(6000):
        values = [int(rng.choice(resolved)) for _ in range(max(0, int(count) - 1))]
        last = int(total) - sum(values)
        if last in candidate_set:
            values.append(int(last))
            rng.shuffle(values)
            return tuple(int(value) for value in values)
    raise ValueError("failed to sample candidate values with requested sum")


def select_internal_option(
    *,
    options: Sequence[str],
    params: Mapping[str, Any],
    param_name: str,
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select one non-public internal construction option."""

    resolved = tuple(str(option) for option in options)
    explicit = params.get(str(param_name))
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(resolved):
            raise ValueError(f"unsupported {param_name}: {selected}")
        return selected, probability_map(resolved, selected=selected)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    selected = str(resolved[int(index) % len(resolved)])
    return selected, probability_map(resolved)


def build_polygon_angle_plan(
    *,
    side_count: int,
    label_style: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> PolygonAnglePlan:
    """Construct one algebraic polygon interior-angle problem."""

    side_count = int(side_count)
    labels = VERTEX_LABELS[:side_count]
    polygon_sum = polygon_angle_sum(side_count)
    target_index = int(
        params.get(
            "target_index",
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace="polygon_angle_chase.polygon.target_index",
            )
            % side_count,
        )
    )
    if target_index < 0 or target_index >= side_count:
        raise ValueError("target_index is outside polygon vertex support")

    min_angle = int(group_default(generation_defaults, "angle_min", 40))
    max_angle = int(group_default(generation_defaults, "angle_max", 150))
    step = int(group_default(generation_defaults, "angle_step", 5))
    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.polygon.problem")
    candidates = tuple(range(int(min_angle), int(max_angle) + 1, int(step)))
    candidate_set = set(candidates)

    display_labels: list[str] = [""] * side_count
    numeric_angles: list[int] = [0] * side_count
    witness: dict[str, Any] = {
        "polygon_side_count": int(side_count),
        "interior_angle_sum": int(polygon_sum),
        "label_style": str(label_style),
    }

    support_indices = [index for index in range(side_count) if index != target_index]
    support_start = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace="polygon_angle_chase.polygon.expression_support_start",
        )
    ) % len(support_indices)
    ordered_support_indices = support_indices[support_start:] + support_indices[:support_start]
    constant_candidates = tuple(range(-35, 36))
    x_floor = max(35, int(round(float(polygon_sum) / float(side_count))) - 35)
    x_ceiling = min(135, int(round(float(polygon_sum) / float(side_count))) + 35)
    x_candidates = tuple(range(x_floor, x_ceiling + 1))

    if label_style == "target_expression_mixed":
        expression_count = 2 if side_count <= 4 else 3
        expression_indices = tuple([target_index, *ordered_support_indices[: expression_count - 1]])
        numeric_indices = tuple(index for index in range(side_count) if index not in expression_indices)
        for _ in range(8000):
            x_value = int(rng.choice(x_candidates))
            constants_by_index = {
                int(index): int(rng.choice(constant_candidates))
                for index in expression_indices
            }
            if constants_by_index[int(target_index)] == 0:
                continue
            if sum(1 for value in constants_by_index.values() if int(value) != 0) < 2:
                continue
            expression_values = {
                int(index): int(x_value) + int(constant)
                for index, constant in constants_by_index.items()
            }
            if any(value not in candidate_set for value in expression_values.values()):
                continue
            remaining_total = int(polygon_sum) - sum(int(value) for value in expression_values.values())
            try:
                numeric_values = sample_values_for_sum(
                    rng,
                    count=len(numeric_indices),
                    total=remaining_total,
                    min_value=min_angle,
                    max_value=max_angle,
                    step=step,
                )
            except ValueError:
                continue
            numeric_by_index = {int(index): int(value) for index, value in zip(numeric_indices, numeric_values)}
            for index in range(side_count):
                if index in expression_values:
                    numeric_angles[index] = int(expression_values[index])
                    display_labels[index] = format_angle_expression(1, int(constants_by_index[index]))
                else:
                    value = int(numeric_by_index[index])
                    numeric_angles[index] = value
                    display_labels[index] = format_degrees(value)
            witness.update(
                {
                    "equation": f"sum(visible_linear_expressions) + sum(visible_numeric_angles) = {polygon_sum}",
                    "x": int(x_value),
                    "expression_vertices": [str(labels[int(index)]) for index in expression_indices],
                    "expressions": {
                        str(labels[int(index)]): format_linear_expression(1, int(constants_by_index[int(index)]))
                        for index in expression_indices
                    },
                    "expression_values": {
                        str(labels[int(index)]): int(expression_values[int(index)])
                        for index in expression_indices
                    },
                    "answer_angle": int(expression_values[int(target_index)]),
                    "known_numeric_angle_values": [
                        int(numeric_by_index[int(index)])
                        for index in numeric_indices
                    ],
                }
            )
            break
        else:
            raise ValueError("failed to construct mixed algebraic polygon angle problem")
    elif label_style == "all_expression":
        expression_indices = tuple(range(side_count))
        for _ in range(8000):
            x_value = int(rng.choice(x_candidates))
            required_constant_sum = int(polygon_sum) - (int(side_count) * int(x_value))
            try:
                constants = sample_candidate_values_for_sum(
                    rng,
                    count=side_count,
                    total=required_constant_sum,
                    candidates=constant_candidates,
                )
            except ValueError:
                continue
            constants_by_index = {
                int(index): int(constant)
                for index, constant in zip(expression_indices, constants)
            }
            if constants_by_index[int(target_index)] == 0:
                continue
            if sum(1 for value in constants_by_index.values() if int(value) != 0) < max(2, side_count - 1):
                continue
            expression_values = {
                int(index): int(x_value) + int(constant)
                for index, constant in constants_by_index.items()
            }
            if any(value not in candidate_set for value in expression_values.values()):
                continue
            for index in range(side_count):
                numeric_angles[index] = int(expression_values[index])
                display_labels[index] = format_angle_expression(1, int(constants_by_index[index]))
            witness.update(
                {
                    "equation": f"sum(visible_linear_expressions) = {polygon_sum}",
                    "x": int(x_value),
                    "expression_vertices": [str(labels[int(index)]) for index in expression_indices],
                    "expressions": {
                        str(labels[int(index)]): format_linear_expression(1, int(constants_by_index[int(index)]))
                        for index in expression_indices
                    },
                    "expression_values": {
                        str(labels[int(index)]): int(expression_values[int(index)])
                        for index in expression_indices
                    },
                    "answer_angle": int(expression_values[int(target_index)]),
                    "known_numeric_angle_values": [],
                }
            )
            break
        else:
            raise ValueError("failed to construct all-expression polygon angle problem")
    else:
        raise ValueError(f"unsupported polygon angle label_style: {label_style}")

    target_angle_name = angle_name(labels, target_index)
    angle_names = [angle_name(labels, index) for index in range(side_count)]
    witness.update(
        {
            "target_vertex": str(labels[int(target_index)]),
            "target_angle_name": str(target_angle_name),
            "angle_names": list(angle_names),
            "numeric_angles": [int(value) for value in numeric_angles],
            "display_angle_labels": list(display_labels),
        }
    )
    return PolygonAnglePlan(
        side_count=int(side_count),
        target_index=int(target_index),
        target_angle_name=str(target_angle_name),
        labels=tuple(labels),
        numeric_angles=tuple(int(value) for value in numeric_angles),
        display_angle_labels=tuple(str(value) for value in display_labels),
        answer=int(numeric_angles[int(target_index)]),
        label_style=str(label_style),
        label_style_probabilities=probability_map(("target_expression_mixed", "all_expression"), selected=str(label_style)),
        witness=dict(witness),
    )


def build_parallel_single_plan(
    *,
    relation_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> ParallelAnglePlan:
    """Construct one parallel-line one-transversal problem."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.parallel.single")
    step = int(group_default(generation_defaults, "angle_step", 5))
    support_min = int(group_default(generation_defaults, "support_angle_min", 40))
    support_max = int(group_default(generation_defaults, "support_angle_max", 75))
    candidates = tuple(range(int(support_min), int(support_max) + 1, int(step)))
    support_angle = int(params.get("support_angle", rng.choice(candidates)))
    if support_angle not in candidates:
        raise ValueError("support_angle is outside configured support")
    answer = int(support_angle if relation_id == "corresponding_same" else 180 - support_angle)
    witness = {
        "parallel_line_count": 3,
        "transversal_count": 1,
        "relation_id": str(relation_id),
        "support_angle": int(support_angle),
        "answer_angle": int(answer),
        "equation": (
            "target_angle = support_angle"
            if relation_id == "corresponding_same"
            else "target_angle = 180 - support_angle"
        ),
    }
    return ParallelAnglePlan(
        construction_kind="one_transversal_three_parallel_lines",
        relation_id=str(relation_id),
        support_angles=(int(support_angle),),
        answer=int(answer),
        target_angle_label=str(params.get("target_angle_label", "x")),
        relation_probabilities=probability_map(("corresponding_same", "supplementary"), selected=str(relation_id)),
        witness=dict(witness),
    )


def build_parallel_two_plan(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> ParallelAnglePlan:
    """Construct one parallel-line two-transversal angle-sum problem."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.parallel.two")
    step = int(group_default(generation_defaults, "angle_step", 5))
    support_min = int(group_default(generation_defaults, "support_angle_min", 40))
    support_max = int(group_default(generation_defaults, "support_angle_max", 75))
    answer_min = int(group_default(generation_defaults, "answer_angle_min", 45))
    answer_max = int(group_default(generation_defaults, "answer_angle_max", 110))
    candidates = tuple(range(int(support_min), int(support_max) + 1, int(step)))
    for _ in range(1000):
        left_angle = int(params.get("support_angle_1", rng.choice(candidates)))
        right_angle = int(params.get("support_angle_2", rng.choice(candidates)))
        answer = 180 - left_angle - right_angle
        if int(answer_min) <= int(answer) <= int(answer_max) and answer % step == 0:
            break
    else:
        raise ValueError("failed to sample two-transversal angle-sum problem")
    witness = {
        "parallel_line_count": 2,
        "transversal_count": 2,
        "relation_id": "angle_sum",
        "support_angles": [int(left_angle), int(right_angle)],
        "answer_angle": int(answer),
        "equation": "target_angle = 180 - support_angle_1 - support_angle_2",
    }
    return ParallelAnglePlan(
        construction_kind="two_transversals_two_parallel_lines",
        relation_id="angle_sum",
        support_angles=(int(left_angle), int(right_angle)),
        answer=int(answer),
        target_angle_label=str(params.get("target_angle_label", "x")),
        relation_probabilities={"angle_sum": 1.0},
        witness=dict(witness),
    )


def build_rectangle_diagonal_plan(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> SymmetryAnglePlan:
    """Construct one rectangle diagonal complementary-angle problem."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.symmetry.rectangle")
    step = int(group_default(generation_defaults, "angle_step", 5))
    known_min = int(group_default(generation_defaults, "rectangle_known_angle_min", 25))
    known_max = int(group_default(generation_defaults, "rectangle_known_angle_max", 65))
    candidates = tuple(range(int(known_min), int(known_max) + 1, int(step)))
    known_angle = int(params.get("support_angle", rng.choice(candidates)))
    if known_angle not in candidates:
        raise ValueError("support_angle is outside rectangle diagonal support")
    answer = 90 - int(known_angle)
    witness = {
        "relation_id": "rectangle_diagonal_complement",
        "support_angle": int(known_angle),
        "answer_angle": int(answer),
        "target_role": "corner_complement",
        "equation": "target_angle = 90 - support_angle",
    }
    return SymmetryAnglePlan(
        construction_kind="rectangle_diagonal",
        relation_id="rectangle_diagonal_complement",
        support_angle=int(known_angle),
        answer=int(answer),
        target_angle_label=str(params.get("target_angle_label", "x")),
        target_role="corner_complement",
        target_role_probabilities={"corner_complement": 1.0},
        witness=dict(witness),
    )


def build_reflection_axis_plan(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> SymmetryAnglePlan:
    """Construct one reflected-rays angle problem."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.symmetry.reflection")
    step = int(group_default(generation_defaults, "angle_step", 5))
    support_min = int(group_default(generation_defaults, "reflection_support_angle_min", 25))
    support_max = int(group_default(generation_defaults, "reflection_support_angle_max", 50))
    candidates = tuple(range(int(support_min), int(support_max) + 1, int(step)))
    support_angle = int(params.get("support_angle", rng.choice(candidates)))
    if support_angle not in candidates:
        raise ValueError("support_angle is outside reflection support")
    answer = 2 * int(support_angle)
    witness = {
        "relation_id": "reflection_axis_angle_double",
        "support_angle": int(support_angle),
        "answer_angle": int(answer),
        "target_role": "reflected_ray_angle",
        "equation": "target_angle = 2 * support_angle",
    }
    return SymmetryAnglePlan(
        construction_kind="reflection_axis",
        relation_id="reflection_axis_angle_double",
        support_angle=int(support_angle),
        answer=int(answer),
        target_angle_label=str(params.get("target_angle_label", "x")),
        target_role="reflected_ray_angle",
        target_role_probabilities={"reflected_ray_angle": 1.0},
        witness=dict(witness),
    )


def build_isosceles_plan(
    *,
    target_role: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> SymmetryAnglePlan:
    """Construct one isosceles equal-side angle problem."""

    rng = spawn_rng(int(instance_seed), "polygon_angle_chase.symmetry.isosceles")
    step = int(group_default(generation_defaults, "angle_step", 5))
    if target_role == "base_angle":
        support_min = int(group_default(generation_defaults, "isosceles_apex_angle_min", 40))
        support_max = int(group_default(generation_defaults, "isosceles_apex_angle_max", 90))
        candidates = tuple(range(int(support_min), int(support_max) + 1, int(step * 2)))
        support_angle = int(params.get("support_angle", rng.choice(candidates)))
        if support_angle not in candidates:
            raise ValueError("support_angle is outside isosceles apex support")
        answer = (180 - int(support_angle)) // 2
        equation = "target_angle = (180 - apex_angle) / 2"
        relation_id = "isosceles_base_from_apex"
    else:
        support_min = int(group_default(generation_defaults, "isosceles_base_angle_min", 45))
        support_max = int(group_default(generation_defaults, "isosceles_base_angle_max", 70))
        candidates = tuple(range(int(support_min), int(support_max) + 1, int(step)))
        support_angle = int(params.get("support_angle", rng.choice(candidates)))
        if support_angle not in candidates:
            raise ValueError("support_angle is outside isosceles base support")
        answer = 180 - (2 * int(support_angle))
        equation = "target_angle = 180 - 2 * base_angle"
        relation_id = "isosceles_apex_from_base"
    witness = {
        "relation_id": str(relation_id),
        "support_angle": int(support_angle),
        "answer_angle": int(answer),
        "target_role": str(target_role),
        "equation": str(equation),
    }
    return SymmetryAnglePlan(
        construction_kind="isosceles_triangle",
        relation_id=str(relation_id),
        support_angle=int(support_angle),
        answer=int(answer),
        target_angle_label=str(params.get("target_angle_label", "x")),
        target_role=str(target_role),
        target_role_probabilities=probability_map(("base_angle", "apex_angle"), selected=str(target_role)),
        witness=dict(witness),
    )


__all__ = [
    "build_isosceles_plan",
    "build_parallel_single_plan",
    "build_parallel_two_plan",
    "build_polygon_angle_plan",
    "build_rectangle_diagonal_plan",
    "build_reflection_axis_plan",
    "sample_candidate_values_for_sum",
    "sample_values_for_sum",
    "select_internal_option",
]
