"""Problem/query sampling for polygon angle-chase tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ......core.seed import spawn_rng
from .....shared.config_defaults import group_default
from .....shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import (
    geometry_selected_probability_map as _probability_map,
    select_indexed_geometry_query_id,
)

from .polygon_angle_chase_common import (
    POLYGON_INTERIOR_NAMESPACE,
    PARALLEL_LINE_NAMESPACE,
    SYMMETRY_ANGLE_NAMESPACE,
    _ISOSCELES_TARGET_ROLES,
    _LABEL_STYLES,
    _PARALLEL_QUERY_IDS,
    _QUERY_SIDE_COUNTS,
    _SINGLE_TRANSVERSAL_RELATIONS,
    _SYMMETRY_QUERY_IDS,
    _VERTEX_LABELS,
    _ResolvedParallelLineProblem,
    _ResolvedPolygonProblem,
    _ResolvedSymmetryAngleProblem,
    _angle_name,
    _format_angle_expression,
    _format_degrees,
    _format_linear_expression,
    _query_angle_sum,
)

def _sample_values_for_sum(
    rng: Any,
    *,
    count: int,
    total: int,
    min_value: int,
    max_value: int,
    step: int,
) -> Tuple[int, ...]:
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

def _sample_candidate_values_for_sum(
    rng: Any,
    *,
    count: int,
    total: int,
    candidates: Sequence[int],
) -> Tuple[int, ...]:
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

def _select_label_style(
    *,
    sampling_namespace: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("label_style")
    if explicit is not None:
        style = str(explicit)
        if style not in set(_LABEL_STYLES):
            raise ValueError(f"unsupported label_style for {sampling_namespace}: {style}")
        return style, _probability_map(_LABEL_STYLES, selected=style)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{sampling_namespace}.label_style",
    )
    style = str(_LABEL_STYLES[int(index) % len(_LABEL_STYLES)])
    return style, _probability_map(_LABEL_STYLES)

def _resolve_parallel_query_param(
    *,
    sampling_namespace: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in _PARALLEL_QUERY_IDS:
            raise ValueError(f"unsupported query_id for {sampling_namespace}: {query_id}")
        return query_id, _probability_map(_PARALLEL_QUERY_IDS, selected=query_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{sampling_namespace}.query_id",
    )
    query_id = str(_PARALLEL_QUERY_IDS[int(index) % len(_PARALLEL_QUERY_IDS)])
    return query_id, _probability_map(_PARALLEL_QUERY_IDS)

def _select_single_transversal_relation(
    *,
    sampling_namespace: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("relation_id")
    if explicit is not None:
        relation_id = str(explicit)
        if relation_id not in _SINGLE_TRANSVERSAL_RELATIONS:
            raise ValueError(f"unsupported relation_id for {sampling_namespace}: {relation_id}")
        return relation_id, _probability_map(_SINGLE_TRANSVERSAL_RELATIONS, selected=relation_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{sampling_namespace}.single_transversal_relation",
    )
    relation_id = str(_SINGLE_TRANSVERSAL_RELATIONS[int(index) % len(_SINGLE_TRANSVERSAL_RELATIONS)])
    return relation_id, _probability_map(_SINGLE_TRANSVERSAL_RELATIONS)

def _resolve_symmetry_query_param(
    *,
    sampling_namespace: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in _SYMMETRY_QUERY_IDS:
            raise ValueError(f"unsupported query_id for {sampling_namespace}: {query_id}")
        return query_id, _probability_map(_SYMMETRY_QUERY_IDS, selected=query_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{sampling_namespace}.query_id",
    )
    query_id = str(_SYMMETRY_QUERY_IDS[int(index) % len(_SYMMETRY_QUERY_IDS)])
    return query_id, _probability_map(_SYMMETRY_QUERY_IDS)

def _select_isosceles_target_role(
    *,
    sampling_namespace: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("target_role")
    if explicit is not None:
        role = str(explicit)
        if role not in _ISOSCELES_TARGET_ROLES:
            raise ValueError(f"unsupported target_role for {sampling_namespace}: {role}")
        return role, _probability_map(_ISOSCELES_TARGET_ROLES, selected=role)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{sampling_namespace}.isosceles_target_role",
    )
    role = str(_ISOSCELES_TARGET_ROLES[int(index) % len(_ISOSCELES_TARGET_ROLES)])
    return role, _probability_map(_ISOSCELES_TARGET_ROLES)

def _resolve_symmetry_angle_problem(
    *,
    sampling_namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> _ResolvedSymmetryAngleProblem:
    query_id, query_probabilities = _resolve_symmetry_query_param(
        sampling_namespace=sampling_namespace,
        params=params,
        instance_seed=int(instance_seed),
    )
    rng = spawn_rng(int(instance_seed), f"{sampling_namespace}.symmetry_problem")
    step = int(group_default(generation_defaults, "angle_step", 5))
    target_label = str(params.get("target_angle_label", "x"))

    if str(query_id) == "rectangle_diagonal_angle":
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
        return _ResolvedSymmetryAngleProblem(
            query_id=str(query_id),
            relation_id="rectangle_diagonal_complement",
            support_angle=int(known_angle),
            answer=int(answer),
            target_angle_label=str(target_label),
            target_role="corner_complement",
            query_probabilities=dict(query_probabilities),
            target_role_probabilities={"corner_complement": 1.0},
            witness=dict(witness),
        )

    if str(query_id) == "reflection_axis_angle":
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
        return _ResolvedSymmetryAngleProblem(
            query_id=str(query_id),
            relation_id="reflection_axis_angle_double",
            support_angle=int(support_angle),
            answer=int(answer),
            target_angle_label=str(target_label),
            target_role="reflected_ray_angle",
            query_probabilities=dict(query_probabilities),
            target_role_probabilities={"reflected_ray_angle": 1.0},
            witness=dict(witness),
        )

    if str(query_id) == "isosceles_base_angle_chain":
        target_role, target_role_probabilities = _select_isosceles_target_role(
            sampling_namespace=sampling_namespace,
            params=params,
            instance_seed=int(instance_seed),
        )
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
        return _ResolvedSymmetryAngleProblem(
            query_id=str(query_id),
            relation_id=str(relation_id),
            support_angle=int(support_angle),
            answer=int(answer),
            target_angle_label=str(target_label),
            target_role=str(target_role),
            query_probabilities=dict(query_probabilities),
            target_role_probabilities=dict(target_role_probabilities),
            witness=dict(witness),
        )

    raise ValueError(f"unsupported symmetry query_id: {query_id}")

def _resolve_parallel_line_problem(
    *,
    sampling_namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> _ResolvedParallelLineProblem:
    query_id, query_probabilities = _resolve_parallel_query_param(
        sampling_namespace=sampling_namespace,
        params=params,
        instance_seed=int(instance_seed),
    )
    rng = spawn_rng(int(instance_seed), f"{sampling_namespace}.parallel_problem")
    step = int(group_default(generation_defaults, "angle_step", 5))
    support_min = int(group_default(generation_defaults, "support_angle_min", 40))
    support_max = int(group_default(generation_defaults, "support_angle_max", 75))
    candidates = tuple(range(int(support_min), int(support_max) + 1, int(step)))
    target_label = str(params.get("target_angle_label", "x"))

    if str(query_id) == "single_transversal_chain":
        relation_id, relation_probabilities = _select_single_transversal_relation(
            sampling_namespace=sampling_namespace,
            params=params,
            instance_seed=int(instance_seed),
        )
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
        return _ResolvedParallelLineProblem(
            query_id=str(query_id),
            relation_id=str(relation_id),
            support_angles=(int(support_angle),),
            answer=int(answer),
            target_angle_label=str(target_label),
            query_probabilities=dict(query_probabilities),
            relation_probabilities=dict(relation_probabilities),
            witness=dict(witness),
        )

    if str(query_id) == "two_transversal_angle_sum":
        answer_min = int(group_default(generation_defaults, "answer_angle_min", 45))
        answer_max = int(group_default(generation_defaults, "answer_angle_max", 110))
        for _ in range(1000):
            left_angle = int(params.get("support_angle_1", rng.choice(candidates)))
            right_angle = int(params.get("support_angle_2", rng.choice(candidates)))
            answer = 180 - left_angle - right_angle
            if int(answer_min) <= int(answer) <= int(answer_max) and answer % step == 0:
                break
        else:
            raise ValueError("failed to sample two-transversal angle-sum problem")
        relation_probabilities = {"angle_sum": 1.0}
        witness = {
            "parallel_line_count": 2,
            "transversal_count": 2,
            "relation_id": "angle_sum",
            "support_angles": [int(left_angle), int(right_angle)],
            "answer_angle": int(answer),
            "equation": "target_angle = 180 - support_angle_1 - support_angle_2",
        }
        return _ResolvedParallelLineProblem(
            query_id=str(query_id),
            relation_id="angle_sum",
            support_angles=(int(left_angle), int(right_angle)),
            answer=int(answer),
            target_angle_label=str(target_label),
            query_probabilities=dict(query_probabilities),
            relation_probabilities=dict(relation_probabilities),
            witness=dict(witness),
        )

    raise ValueError(f"unsupported parallel-line query_id: {query_id}")

def _resolve_problem(
    *,
    sampling_namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> _ResolvedPolygonProblem:
    query_id, query_probabilities = select_indexed_geometry_query_id(
        params=params,
        query_ids=tuple(_QUERY_SIDE_COUNTS),
        task_id=str(sampling_namespace),
        instance_seed=int(instance_seed),
    )
    side_count = int(_QUERY_SIDE_COUNTS[str(query_id)])
    labels = _VERTEX_LABELS[:side_count]
    polygon_sum = _query_angle_sum(side_count)
    label_style, label_style_probabilities = _select_label_style(
        sampling_namespace=sampling_namespace,
        params=params,
        instance_seed=int(instance_seed),
    )
    target_index = int(
        params.get(
            "target_index",
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{sampling_namespace}.target_index",
            )
            % side_count,
        )
    )
    if target_index < 0 or target_index >= side_count:
        raise ValueError("target_index is outside polygon vertex support")

    min_angle = int(group_default(generation_defaults, "angle_min", 40))
    max_angle = int(group_default(generation_defaults, "angle_max", 150))
    step = int(group_default(generation_defaults, "angle_step", 5))
    rng = spawn_rng(int(instance_seed), f"{sampling_namespace}.problem")
    candidates = tuple(range(int(min_angle), int(max_angle) + 1, int(step)))

    display_labels: list[str] = [""] * side_count
    numeric_angles: list[int] = [0] * side_count
    expression_vertex_index: int | None = None
    witness: Dict[str, Any] = {
        "polygon_side_count": int(side_count),
        "interior_angle_sum": int(polygon_sum),
        "label_style": str(label_style),
    }

    support_indices = [index for index in range(side_count) if index != target_index]
    support_start = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{sampling_namespace}.expression_support_start",
        )
    ) % len(support_indices)
    ordered_support_indices = support_indices[support_start:] + support_indices[:support_start]
    constant_candidates = tuple(range(-35, 36))
    x_floor = max(35, int(round(float(polygon_sum) / float(side_count))) - 35)
    x_ceiling = min(135, int(round(float(polygon_sum) / float(side_count))) + 35)
    x_candidates = tuple(range(x_floor, x_ceiling + 1))
    candidate_set = set(candidates)

    if label_style == "target_expression_mixed":
        expression_count = 2 if side_count <= 4 else 3
        expression_indices = tuple([target_index, *ordered_support_indices[: expression_count - 1]])
        numeric_indices = tuple(index for index in range(side_count) if index not in expression_indices)
        expression_vertex_index = expression_indices[1] if len(expression_indices) > 1 else target_index
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
                numeric_values = _sample_values_for_sum(
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
                    display_labels[index] = _format_angle_expression(1, int(constants_by_index[index]))
                else:
                    value = int(numeric_by_index[index])
                    numeric_angles[index] = value
                    display_labels[index] = _format_degrees(value)
            witness.update(
                {
                    "equation": f"sum(visible_linear_expressions) + sum(visible_numeric_angles) = {polygon_sum}",
                    "x": int(x_value),
                    "expression_vertices": [str(labels[int(index)]) for index in expression_indices],
                    "expressions": {
                        str(labels[int(index)]): _format_linear_expression(1, int(constants_by_index[int(index)]))
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
        expression_vertex_index = ordered_support_indices[0] if ordered_support_indices else target_index
        for _ in range(8000):
            x_value = int(rng.choice(x_candidates))
            required_constant_sum = int(polygon_sum) - (int(side_count) * int(x_value))
            try:
                constants = _sample_candidate_values_for_sum(
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
                display_labels[index] = _format_angle_expression(1, int(constants_by_index[index]))
            witness.update(
                {
                    "equation": f"sum(visible_linear_expressions) = {polygon_sum}",
                    "x": int(x_value),
                    "expression_vertices": [str(labels[int(index)]) for index in expression_indices],
                    "expressions": {
                        str(labels[int(index)]): _format_linear_expression(1, int(constants_by_index[int(index)]))
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

    target_angle_name = _angle_name(labels, target_index)
    angle_names = [_angle_name(labels, index) for index in range(side_count)]
    witness.update(
        {
            "target_vertex": str(labels[int(target_index)]),
            "target_angle_name": str(target_angle_name),
            "angle_names": list(angle_names),
            "numeric_angles": [int(value) for value in numeric_angles],
            "display_angle_labels": list(display_labels),
        }
    )
    return _ResolvedPolygonProblem(
        query_id=str(query_id),
        side_count=int(side_count),
        target_index=int(target_index),
        target_angle_name=str(target_angle_name),
        labels=tuple(labels),
        numeric_angles=tuple(int(value) for value in numeric_angles),
        display_angle_labels=tuple(str(value) for value in display_labels),
        answer=int(numeric_angles[int(target_index)]),
        label_style=str(label_style),
        expression_vertex_index=expression_vertex_index,
        query_probabilities=dict(query_probabilities),
        label_style_probabilities=dict(label_style_probabilities),
        witness=dict(witness),
    )


__all__ = [
    '_sample_values_for_sum',
    '_sample_candidate_values_for_sum',
    '_select_label_style',
    '_resolve_parallel_query_param',
    '_select_single_transversal_relation',
    '_resolve_symmetry_query_param',
    '_select_isosceles_target_role',
    '_resolve_symmetry_angle_problem',
    '_resolve_parallel_line_problem',
    '_resolve_problem',
]
