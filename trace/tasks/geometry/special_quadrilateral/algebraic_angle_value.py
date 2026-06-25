"""Solve algebraic angle expressions in a special quadrilateral."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from ._lifecycle import expression_payload, render_special_quadrilateral_problem
from .shared.output import common_trace_sections, prompt_artifacts_for_bound_case
from .shared.rendering import (
    RENDER_KITE_OPPOSITE_ANGLES,
    RENDER_PARALLELOGRAM_CONSECUTIVE_ANGLES,
    RENDER_PARALLELOGRAM_OPPOSITE_ANGLES,
    RENDER_RHOMBUS_HALF_ANGLE_EXPRESSION,
)
from .shared.sampling import select_case_from_answer_support
from .shared.state import DOMAIN, LinearExpression, QuadrilateralCase, SCENE_ID, SpecialQuadrilateralProblem

TASK_ID = "task_geometry__special_quadrilateral__algebraic_angle_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "parallelogram_opposite_angle_expression",
    "parallelogram_consecutive_angle_expression",
    "rhombus_diagonal_half_angle_expression",
    "kite_opposite_angle_expression",
)
TASK_PROMPT_KEY = "algebraic_angle_value_query"


def _expr(coefficient: int, constant: int) -> LinearExpression:
    return LinearExpression(int(coefficient), int(constant))


def _case(
    *,
    render_kind: str,
    shape_kind: str,
    answer: int,
    target_name: str,
    target_expression: LinearExpression,
    support_expression: LinearExpression,
    theorem: str,
    x_value: int,
) -> QuadrilateralCase:
    return QuadrilateralCase(
        render_kind=str(render_kind),
        shape_kind=str(shape_kind),
        answer=int(answer),
        target_name=str(target_name),
        target_label=target_expression.display(degree=True),
        support_label=support_expression.display(degree=True),
        theorem=str(theorem),
        x_value=int(x_value),
        target_expression=target_expression,
        support_expression=support_expression,
    )


_CASES_BY_BRANCH: dict[str, tuple[QuadrilateralCase, ...]] = {
    "parallelogram_opposite_angle_expression": (
        _case(render_kind=RENDER_PARALLELOGRAM_OPPOSITE_ANGLES, shape_kind="parallelogram", answer=45, target_name="angle BCD", target_expression=_expr(2, 25), support_expression=_expr(3, 15), theorem="opposite_angles_of_a_parallelogram_are_equal", x_value=10),
        _case(render_kind=RENDER_PARALLELOGRAM_OPPOSITE_ANGLES, shape_kind="parallelogram", answer=60, target_name="angle BCD", target_expression=_expr(1, 42), support_expression=_expr(2, 24), theorem="opposite_angles_of_a_parallelogram_are_equal", x_value=18),
        _case(render_kind=RENDER_PARALLELOGRAM_OPPOSITE_ANGLES, shape_kind="parallelogram", answer=70, target_name="angle BCD", target_expression=_expr(4, 30), support_expression=_expr(3, 40), theorem="opposite_angles_of_a_parallelogram_are_equal", x_value=10),
        _case(render_kind=RENDER_PARALLELOGRAM_OPPOSITE_ANGLES, shape_kind="parallelogram", answer=80, target_name="angle BCD", target_expression=_expr(5, 20), support_expression=_expr(2, 56), theorem="opposite_angles_of_a_parallelogram_are_equal", x_value=12),
        _case(render_kind=RENDER_PARALLELOGRAM_OPPOSITE_ANGLES, shape_kind="parallelogram", answer=95, target_name="angle BCD", target_expression=_expr(3, 50), support_expression=_expr(4, 35), theorem="opposite_angles_of_a_parallelogram_are_equal", x_value=15),
    ),
    "parallelogram_consecutive_angle_expression": (
        _case(render_kind=RENDER_PARALLELOGRAM_CONSECUTIVE_ANGLES, shape_kind="parallelogram", answer=120, target_name="angle ABC", target_expression=_expr(3, 60), support_expression=_expr(2, 20), theorem="consecutive_angles_of_a_parallelogram_are_supplementary", x_value=20),
        _case(render_kind=RENDER_PARALLELOGRAM_CONSECUTIVE_ANGLES, shape_kind="parallelogram", answer=110, target_name="angle ABC", target_expression=_expr(2, 74), support_expression=_expr(3, 16), theorem="consecutive_angles_of_a_parallelogram_are_supplementary", x_value=18),
        _case(render_kind=RENDER_PARALLELOGRAM_CONSECUTIVE_ANGLES, shape_kind="parallelogram", answer=100, target_name="angle ABC", target_expression=_expr(3, 40), support_expression=_expr(2, 40), theorem="consecutive_angles_of_a_parallelogram_are_supplementary", x_value=20),
        _case(render_kind=RENDER_PARALLELOGRAM_CONSECUTIVE_ANGLES, shape_kind="parallelogram", answer=130, target_name="angle ABC", target_expression=_expr(4, 70), support_expression=_expr(2, 20), theorem="consecutive_angles_of_a_parallelogram_are_supplementary", x_value=15),
        _case(render_kind=RENDER_PARALLELOGRAM_CONSECUTIVE_ANGLES, shape_kind="parallelogram", answer=105, target_name="angle ABC", target_expression=_expr(5, 55), support_expression=_expr(4, 35), theorem="consecutive_angles_of_a_parallelogram_are_supplementary", x_value=10),
    ),
    "rhombus_diagonal_half_angle_expression": (
        _case(render_kind=RENDER_RHOMBUS_HALF_ANGLE_EXPRESSION, shape_kind="rhombus", answer=42, target_name="angle ABO", target_expression=_expr(4, 2), support_expression=_expr(3, 12), theorem="rhombus_diagonal_bisects_vertex_angle", x_value=10),
        _case(render_kind=RENDER_RHOMBUS_HALF_ANGLE_EXPRESSION, shape_kind="rhombus", answer=50, target_name="angle ABO", target_expression=_expr(2, 28), support_expression=_expr(3, 17), theorem="rhombus_diagonal_bisects_vertex_angle", x_value=11),
        _case(render_kind=RENDER_RHOMBUS_HALF_ANGLE_EXPRESSION, shape_kind="rhombus", answer=35, target_name="angle ABO", target_expression=_expr(3, 20), support_expression=_expr(2, 25), theorem="rhombus_diagonal_bisects_vertex_angle", x_value=5),
        _case(render_kind=RENDER_RHOMBUS_HALF_ANGLE_EXPRESSION, shape_kind="rhombus", answer=45, target_name="angle ABO", target_expression=_expr(4, 13), support_expression=_expr(5, 5), theorem="rhombus_diagonal_bisects_vertex_angle", x_value=8),
        _case(render_kind=RENDER_RHOMBUS_HALF_ANGLE_EXPRESSION, shape_kind="rhombus", answer=60, target_name="angle ABO", target_expression=_expr(2, 40), support_expression=_expr(3, 30), theorem="rhombus_diagonal_bisects_vertex_angle", x_value=10),
    ),
    "kite_opposite_angle_expression": (
        _case(render_kind=RENDER_KITE_OPPOSITE_ANGLES, shape_kind="kite", answer=75, target_name="angle ABC", target_expression=_expr(2, 51), support_expression=_expr(3, 39), theorem="opposite_non_vertex_angles_of_this_kite_are_equal", x_value=12),
        _case(render_kind=RENDER_KITE_OPPOSITE_ANGLES, shape_kind="kite", answer=90, target_name="angle ABC", target_expression=_expr(1, 68), support_expression=_expr(2, 46), theorem="opposite_non_vertex_angles_of_this_kite_are_equal", x_value=22),
        _case(render_kind=RENDER_KITE_OPPOSITE_ANGLES, shape_kind="kite", answer=60, target_name="angle ABC", target_expression=_expr(2, 36), support_expression=_expr(1, 48), theorem="opposite_non_vertex_angles_of_this_kite_are_equal", x_value=12),
        _case(render_kind=RENDER_KITE_OPPOSITE_ANGLES, shape_kind="kite", answer=80, target_name="angle ABC", target_expression=_expr(3, 38), support_expression=_expr(2, 52), theorem="opposite_non_vertex_angles_of_this_kite_are_equal", x_value=14),
        _case(render_kind=RENDER_KITE_OPPOSITE_ANGLES, shape_kind="kite", answer=100, target_name="angle ABC", target_expression=_expr(2, 60), support_expression=_expr(3, 40), theorem="opposite_non_vertex_angles_of_this_kite_are_equal", x_value=20),
    ),
}


def _prepare_problem(*, selected_query: str, params: Mapping[str, Any], instance_seed: int) -> tuple[SpecialQuadrilateralProblem, dict[str, float]]:
    """Bind the selected algebraic-angle branch to one theorem case."""

    cases = _CASES_BY_BRANCH.get(str(selected_query))
    if not cases:
        raise ValueError(f"unsupported special quadrilateral algebraic-angle query: {selected_query}")
    case, case_index, answer_probabilities = select_case_from_answer_support(
        cases=cases,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_query}.case",
    )
    return SpecialQuadrilateralProblem(case=case, case_index=int(case_index), layout_seed=int(instance_seed)), dict(answer_probabilities)


def _select_bound_problem(
    *,
    instance_seed: int,
    params: dict[str, Any],
) -> tuple[str, dict[str, float], dict[str, Any], SpecialQuadrilateralProblem, dict[str, float]]:
    """Resolve this task's query branch and algebraic-angle case."""

    selected_query, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SUPPORTED_QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )
    problem, answer_probabilities = _prepare_problem(
        selected_query=str(selected_query),
        params=task_params,
        instance_seed=int(instance_seed),
    )
    return str(selected_query), dict(branch_probabilities), dict(task_params), problem, dict(answer_probabilities)


def _render_bound_artifacts(
    *,
    instance_seed: int,
    max_attempts: int,
    task_params: Mapping[str, Any],
    selected_query: str,
    problem: SpecialQuadrilateralProblem,
):
    """Render image and prompt artifacts for the algebraic-angle objective."""

    parts = render_special_quadrilateral_problem(
        problem=problem,
        instance_seed=int(instance_seed),
        params=task_params,
        max_attempts=int(max_attempts),
    )
    prompt_artifacts = prompt_artifacts_for_bound_case(
        prompt_defaults=parts.prompt_defaults,
        task_prompt_key=TASK_PROMPT_KEY,
        branch_prompt_key=str(selected_query),
        target_name=str(problem.case.target_name),
        annotation_roles=tuple(parts.annotation_artifacts.value.keys()),
        answer_value=int(problem.case.answer),
        instance_seed=int(instance_seed),
    )
    return parts, prompt_artifacts


def _query_params(
    *,
    selected_query: str,
    branch_probabilities: Mapping[str, float],
    answer_probabilities: Mapping[str, float],
    problem: SpecialQuadrilateralProblem,
) -> dict[str, Any]:
    """Build task-owned prompt query metadata for the algebraic branch."""

    expression_values = expression_payload(problem.case)
    return {
        "scene_id": SCENE_ID,
        "query_id_probabilities": dict(branch_probabilities),
        "answer_support_probabilities": dict(answer_probabilities),
        "case_index": int(problem.case_index),
        "shape_kind": str(problem.case.shape_kind),
        "theorem": str(problem.case.theorem),
        **dict(expression_values),
    }


def _trace_payload(
    *,
    selected_query: str,
    branch_probabilities: Mapping[str, float],
    answer_probabilities: Mapping[str, float],
    problem: SpecialQuadrilateralProblem,
    parts: Any,
    prompt_artifacts: Any,
) -> dict[str, Any]:
    """Bind task identity and query metadata onto neutral trace sections."""

    expression_values = expression_payload(problem.case)
    trace_payload = common_trace_sections(
        branch_probabilities=dict(branch_probabilities),
        answer_probabilities=answer_probabilities,
        prompt_artifacts=prompt_artifacts,
        problem=problem,
        parts=parts,
        extra_case_values=expression_values,
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params=_query_params(
            selected_query=str(selected_query),
            branch_probabilities=branch_probabilities,
            answer_probabilities=answer_probabilities,
            problem=problem,
        ),
    )
    query_spec["scene_id"] = SCENE_ID
    trace_payload["query_spec"] = query_spec
    trace_payload["scene_ir"]["task_id"] = TASK_ID
    trace_payload["scene_ir"]["query_id"] = str(selected_query)
    trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query)
    trace_payload["render_spec"]["task_id"] = TASK_ID
    trace_payload["render_spec"]["query_id"] = str(selected_query)
    trace_payload["execution_trace"]["query_id"] = str(selected_query)
    trace_payload["witness_symbolic"] = {
        "type": "special_quadrilateral_algebraic_angle_relation",
        "task_id": TASK_ID,
        **dict(trace_payload["execution_trace"]),
    }
    return trace_payload


def _task_output(
    *,
    selected_query: str,
    problem: SpecialQuadrilateralProblem,
    parts: Any,
    prompt_artifacts: Any,
    trace_payload: dict[str, Any],
) -> TaskOutput:
    """Bind final public output fields for the algebraic-angle task."""

    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(problem.case.answer)),
        annotation_gt=TypedValue(type=parts.annotation_artifacts.annotation_type, value=parts.annotation_artifacts.value),
        image=parts.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=parts.task_versions,
        scene_id=SCENE_ID,
        query_id=str(selected_query),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


@register_task
class GeometrySpecialQuadrilateralAlgebraicAngleValueTask:
    """Solve algebraic angle expressions in a special quadrilateral."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one algebraic-angle instance with task-owned binding."""

        task_seed = int(instance_seed)
        selected_query, branch_probs, task_params, problem, answer_probs = _select_bound_problem(
            instance_seed=task_seed,
            params=dict(params),
        )
        parts, prompt_artifacts = _render_bound_artifacts(
            instance_seed=task_seed,
            max_attempts=max(1, int(max_attempts)),
            task_params=task_params,
            selected_query=selected_query,
            problem=problem,
        )
        trace_payload = _trace_payload(
            selected_query=selected_query,
            branch_probabilities=branch_probs,
            answer_probabilities=answer_probs,
            problem=problem,
            parts=parts,
            prompt_artifacts=prompt_artifacts,
        )
        return _task_output(
            selected_query=selected_query,
            problem=problem,
            parts=parts,
            prompt_artifacts=prompt_artifacts,
            trace_payload=trace_payload,
        )


__all__ = ["GeometrySpecialQuadrilateralAlgebraicAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
