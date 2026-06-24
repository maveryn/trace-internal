"""Solve algebraic angle expressions in a special quadrilateral."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import prepare_special_quadrilateral_task_parts
from .shared.rendering import (
    RENDER_KITE_OPPOSITE_ANGLES,
    RENDER_PARALLELOGRAM_CONSECUTIVE_ANGLES,
    RENDER_PARALLELOGRAM_OPPOSITE_ANGLES,
    RENDER_RHOMBUS_HALF_ANGLE_EXPRESSION,
)
from .shared.sampling import select_case_from_answer_support
from .shared.state import DEGREE_SYMBOL, DOMAIN, LinearExpression, QuadrilateralCase, SCENE_ID, SpecialQuadrilateralProblem

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


def generate_algebraic_angle_value(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
    """Select the theorem branch, bind the answer, then render final output."""

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
    parts = prepare_special_quadrilateral_task_parts(
        public_task_id=TASK_ID,
        selected_query=str(selected_query),
        branch_probabilities=branch_probabilities,
        answer_probabilities=answer_probabilities,
        problem=problem,
        prompt_task_key=TASK_PROMPT_KEY,
        instance_seed=int(instance_seed),
        params=task_params,
        max_attempts=int(max_attempts),
    )
    return TaskOutput(
        prompt=parts.prompt,
        answer_gt=TypedValue(type="integer", value=int(problem.case.answer)),
        annotation_gt=TypedValue(type=parts.annotation_artifacts.annotation_type, value=parts.annotation_artifacts.value),
        image=parts.image,
        image_id="img0",
        trace_payload=parts.trace_payload,
        task_versions=parts.task_versions,
        scene_id=SCENE_ID,
        query_id=str(selected_query),
        prompt_variants=dict(parts.prompt_variants),
    )


@register_task
class GeometrySpecialQuadrilateralAlgebraicAngleValueTask:
    """Solve algebraic angle expressions in a special quadrilateral."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Delegate to this public file's algebraic-angle implementation."""

        task_seed = int(instance_seed)
        task_params = dict(params)
        attempt_limit = max(1, int(max_attempts))
        result = generate_algebraic_angle_value(
            self,
            task_seed,
            params=task_params,
            max_attempts=attempt_limit,
        )
        return result


__all__ = ["GeometrySpecialQuadrilateralAlgebraicAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
