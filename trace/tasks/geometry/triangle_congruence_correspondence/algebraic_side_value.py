"""Solve an algebraic corresponding-side value from congruent triangles."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import run_triangle_congruence_public_entry
from .shared.construction import (
    build_algebraic_side_case,
    side_endpoint_labels,
    support_side_endpoint_labels,
)
from .shared.rendering import render_triangle_congruence_scene
from .shared.sampling import choose_case_by_answer
from .shared.state import DOMAIN, TriangleCongruenceCase, TriangleCongruenceProblem


TASK_ID = "task_geometry__triangle_congruence_correspondence__algebraic_side_value"
TASK_PROMPT_KEY = "algebraic_side_value_query"
ANSWER_HINT_KEY = "answer_hint_integer_length"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "single_expression_equal_sides",
    "two_expression_equal_sides",
    "shared_side_congruence_expression",
)

_BRANCH_CONFIGS = {
    "single_expression_equal_sides": {
        "layout_kind": "separated",
        "source_side": (0, 1),
        "target_side": (0, 1),
        "support_side": (1, 2),
        "cue_family": "one_expression_one_numeric_support_side",
        "answers": tuple(range(11, 56)),
    },
    "two_expression_equal_sides": {
        "layout_kind": "statement",
        "source_side": (0, 1),
        "target_side": (0, 1),
        "support_side": (1, 2),
        "cue_family": "two_expression_support_sides",
        "answers": tuple(range(12, 58)),
    },
    "shared_side_congruence_expression": {
        "layout_kind": "overlap",
        "source_side": (0, 1),
        "target_side": (0, 1),
        "support_side": (1, 2),
        "cue_family": "overlapping_triangle_expression_support",
        "answers": tuple(range(11, 56)),
    },
}


def _linear_expression(coefficient: int, constant: int) -> str:
    if int(coefficient) == 1:
        prefix = "x"
    else:
        prefix = f"{int(coefficient)}x"
    if int(constant) == 0:
        return prefix
    sign = "+" if int(constant) > 0 else "-"
    return f"{prefix}{sign}{abs(int(constant))}"


def _single_expression_cases(config: Mapping[str, object]) -> tuple[TriangleCongruenceCase, ...]:
    cases: list[TriangleCongruenceCase] = []
    for answer in config["answers"]:  # type: ignore[index]
        for x_value in range(3, min(15, int(answer) - 2)):
            side_offset = int(answer) - int(x_value)
            support_offset = 2 + ((int(answer) + int(x_value)) % 7)
            cases.append(
                build_algebraic_side_case(
                    layout_kind=str(config["layout_kind"]),
                    answer=int(answer),
                    x_value=int(x_value),
                    source_target_expression=_linear_expression(1, side_offset),
                    source_support_expression=_linear_expression(1, support_offset),
                    target_support_expression=str(int(x_value) + support_offset),
                    source_side=config["source_side"],  # type: ignore[arg-type]
                    target_side=config["target_side"],  # type: ignore[arg-type]
                    support_side=config["support_side"],  # type: ignore[arg-type]
                )
            )
    return tuple(cases)


def _two_expression_cases(config: Mapping[str, object]) -> tuple[TriangleCongruenceCase, ...]:
    cases: list[TriangleCongruenceCase] = []
    for answer in config["answers"]:  # type: ignore[index]
        for x_value in range(4, min(16, int(answer) - 3)):
            target_offset = int(answer) - int(x_value)
            left_offset = 1 + ((int(answer) + int(x_value)) % 9)
            right_offset = int(x_value) + left_offset
            cases.append(
                build_algebraic_side_case(
                    layout_kind=str(config["layout_kind"]),
                    answer=int(answer),
                    x_value=int(x_value),
                    source_target_expression=_linear_expression(1, target_offset),
                    source_support_expression=_linear_expression(2, left_offset),
                    target_support_expression=_linear_expression(1, right_offset),
                    source_side=config["source_side"],  # type: ignore[arg-type]
                    target_side=config["target_side"],  # type: ignore[arg-type]
                    support_side=config["support_side"],  # type: ignore[arg-type]
                )
            )
    return tuple(cases)


def _shared_side_cases(config: Mapping[str, object]) -> tuple[TriangleCongruenceCase, ...]:
    cases: list[TriangleCongruenceCase] = []
    for answer in config["answers"]:  # type: ignore[index]
        for x_value in range(3, min(14, int(answer) - 2)):
            target_offset = int(answer) - int(x_value)
            support_offset = 2 + ((int(answer) + int(x_value)) % 8)
            cases.append(
                build_algebraic_side_case(
                    layout_kind=str(config["layout_kind"]),
                    answer=int(answer),
                    x_value=int(x_value),
                    source_target_expression=_linear_expression(1, target_offset),
                    source_support_expression=_linear_expression(2, support_offset),
                    target_support_expression=str((2 * int(x_value)) + support_offset),
                    source_side=config["source_side"],  # type: ignore[arg-type]
                    target_side=config["target_side"],  # type: ignore[arg-type]
                    support_side=config["support_side"],  # type: ignore[arg-type]
                )
            )
    return tuple(cases)


def _algebraic_cases(selected_branch: str) -> tuple[TriangleCongruenceCase, ...]:
    """Build algebraic CPCTC side cases for one semantic branch."""

    if str(selected_branch) not in _BRANCH_CONFIGS:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
    config = _BRANCH_CONFIGS[str(selected_branch)]
    if str(selected_branch) == "single_expression_equal_sides":
        return _single_expression_cases(config)
    if str(selected_branch) == "two_expression_equal_sides":
        return _two_expression_cases(config)
    return _shared_side_cases(config)


def _prepare_algebraic_side_value(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
) -> tuple[TriangleCongruenceProblem, int, tuple[str, ...], dict[str, Any]]:
    """Bind an algebraic side-transfer construction from task-owned semantics."""

    config = _BRANCH_CONFIGS[str(selected_branch)]
    case, answer_probabilities = choose_case_by_answer(
        cases=_algebraic_cases(str(selected_branch)),
        answer_fn=lambda item: int(item.answer),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_branch}",
    )
    side_labels = side_endpoint_labels(
        case.layout_kind,
        source_side=case.source_side,
        target_side=case.target_side,
    )
    support_labels = support_side_endpoint_labels(case.layout_kind, support_side=case.support_side)
    annotation_labels = tuple(dict.fromkeys((*side_labels, *support_labels)))
    trace_values = {
        "formula_family": "cpctc_algebraic_side_equality",
        "formula": "solve equal support-side expressions for x, then evaluate the corresponding source side",
        "cue_family": str(config["cue_family"]),
        "layout_kind": str(case.layout_kind),
        "target_side_labels": list(side_labels[:2]),
        "source_side_labels": list(side_labels[2:]),
        "support_side_labels": list(support_labels),
        "source_target_side_value": int(case.source_target_side_value or 0),
        "target_target_side_value": int(case.target_target_side_value or 0),
        "x_value": int(case.x_value or 0),
        "source_target_expression": str(case.source_target_expression or ""),
        "source_support_expression": str(case.source_support_expression or ""),
        "target_support_expression": str(case.target_support_expression or ""),
        "target_support_probabilities": dict(answer_probabilities),
    }
    problem = TriangleCongruenceProblem(
        case=case,
        reasoning_steps=2,
        layout_seed=int(instance_seed),
        answer_support_probabilities=dict(answer_probabilities),
    )
    return problem, int(case.answer), annotation_labels, trace_values


@register_task
class GeometryTriangleCongruenceCorrespondenceAlgebraicSideValueTask:
    """Solve an algebraic corresponding-side value from congruent triangles."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    task_prompt_key = TASK_PROMPT_KEY
    answer_hint_key = ANSWER_HINT_KEY
    render_scene = staticmethod(render_triangle_congruence_scene)
    prepare_objective = staticmethod(_prepare_algebraic_side_value)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_triangle_congruence_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryTriangleCongruenceCorrespondenceAlgebraicSideValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
