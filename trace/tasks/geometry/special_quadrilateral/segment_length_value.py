"""Solve algebraic side or diagonal segment lengths in a special quadrilateral."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import prepare_special_quadrilateral_task_parts
from .shared.rendering import (
    RENDER_KITE_ADJACENT_SIDES,
    RENDER_PARALLELOGRAM_BISECTED_DIAGONAL,
    RENDER_PARALLELOGRAM_OPPOSITE_SIDES,
    RENDER_RHOMBUS_ALL_SIDES,
)
from .shared.sampling import select_case_from_answer_support
from .shared.state import DOMAIN, LinearExpression, QuadrilateralCase, SCENE_ID, SpecialQuadrilateralProblem

TASK_ID = "task_geometry__special_quadrilateral__segment_length_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "parallelogram_opposite_side_expression",
    "rhombus_all_sides_expression",
    "kite_adjacent_equal_side_expression",
    "parallelogram_diagonal_bisection_expression",
)
TASK_PROMPT_KEY = "segment_length_value_query"
SegmentCaseRecord = tuple[str, str, int, str, tuple[int, int], tuple[int, int], str, int]


def _segment_expression(raw: tuple[int, int]) -> LinearExpression:
    coefficient, constant = raw
    return LinearExpression(int(coefficient), int(constant))


def _segment_case_from_record(record: SegmentCaseRecord) -> QuadrilateralCase:
    render_kind, shape_kind, answer, target_name, target_raw, support_raw, theorem, x_value = record
    target_expression = _segment_expression(target_raw)
    support_expression = _segment_expression(support_raw)
    return QuadrilateralCase(
        render_kind=str(render_kind),
        shape_kind=str(shape_kind),
        answer=int(answer),
        target_name=str(target_name),
        target_label=target_expression.display(),
        support_label=support_expression.display(),
        theorem=str(theorem),
        x_value=int(x_value),
        target_expression=target_expression,
        support_expression=support_expression,
    )


def _segment_cases(*records: SegmentCaseRecord) -> tuple[QuadrilateralCase, ...]:
    return tuple(_segment_case_from_record(record) for record in records)


_CASES_BY_BRANCH: dict[str, tuple[QuadrilateralCase, ...]] = {
    "parallelogram_opposite_side_expression": _segment_cases(
        (RENDER_PARALLELOGRAM_OPPOSITE_SIDES, "parallelogram", 17, "segment BC", (3, -1), (2, 5), "opposite_sides_of_a_parallelogram_are_equal", 6),
        (RENDER_PARALLELOGRAM_OPPOSITE_SIDES, "parallelogram", 24, "segment BC", (2, 10), (3, 3), "opposite_sides_of_a_parallelogram_are_equal", 7),
        (RENDER_PARALLELOGRAM_OPPOSITE_SIDES, "parallelogram", 20, "segment BC", (2, 4), (1, 12), "opposite_sides_of_a_parallelogram_are_equal", 8),
        (RENDER_PARALLELOGRAM_OPPOSITE_SIDES, "parallelogram", 28, "segment BC", (3, 1), (2, 10), "opposite_sides_of_a_parallelogram_are_equal", 9),
        (RENDER_PARALLELOGRAM_OPPOSITE_SIDES, "parallelogram", 32, "segment BC", (2, 12), (3, 2), "opposite_sides_of_a_parallelogram_are_equal", 10),
    ),
    "rhombus_all_sides_expression": _segment_cases(
        (RENDER_RHOMBUS_ALL_SIDES, "rhombus", 20, "segment CD", (2, 4), (1, 12), "all_sides_of_a_rhombus_are_equal", 8),
        (RENDER_RHOMBUS_ALL_SIDES, "rhombus", 27, "segment CD", (3, 6), (2, 13), "all_sides_of_a_rhombus_are_equal", 7),
        (RENDER_RHOMBUS_ALL_SIDES, "rhombus", 18, "segment CD", (2, 8), (1, 13), "all_sides_of_a_rhombus_are_equal", 5),
        (RENDER_RHOMBUS_ALL_SIDES, "rhombus", 24, "segment CD", (3, 3), (2, 10), "all_sides_of_a_rhombus_are_equal", 7),
        (RENDER_RHOMBUS_ALL_SIDES, "rhombus", 30, "segment CD", (2, 12), (3, 3), "all_sides_of_a_rhombus_are_equal", 9),
    ),
    "kite_adjacent_equal_side_expression": _segment_cases(
        (RENDER_KITE_ADJACENT_SIDES, "kite", 18, "segment AD", (2, 6), (1, 12), "adjacent_marked_sides_of_a_kite_are_equal", 6),
        (RENDER_KITE_ADJACENT_SIDES, "kite", 25, "segment AD", (3, 1), (2, 9), "adjacent_marked_sides_of_a_kite_are_equal", 8),
        (RENDER_KITE_ADJACENT_SIDES, "kite", 20, "segment AD", (2, 8), (3, 2), "adjacent_marked_sides_of_a_kite_are_equal", 6),
        (RENDER_KITE_ADJACENT_SIDES, "kite", 22, "segment AD", (3, 1), (2, 8), "adjacent_marked_sides_of_a_kite_are_equal", 7),
        (RENDER_KITE_ADJACENT_SIDES, "kite", 28, "segment AD", (2, 12), (3, 4), "adjacent_marked_sides_of_a_kite_are_equal", 8),
    ),
    "parallelogram_diagonal_bisection_expression": _segment_cases(
        (RENDER_PARALLELOGRAM_BISECTED_DIAGONAL, "parallelogram", 23, "segment OC", (2, 9), (3, 2), "diagonals_of_a_parallelogram_bisect_each_other", 7),
        (RENDER_PARALLELOGRAM_BISECTED_DIAGONAL, "parallelogram", 32, "segment OC", (3, 5), (2, 14), "diagonals_of_a_parallelogram_bisect_each_other", 9),
        (RENDER_PARALLELOGRAM_BISECTED_DIAGONAL, "parallelogram", 18, "segment OC", (2, 6), (3, 0), "diagonals_of_a_parallelogram_bisect_each_other", 6),
        (RENDER_PARALLELOGRAM_BISECTED_DIAGONAL, "parallelogram", 26, "segment OC", (3, 5), (2, 12), "diagonals_of_a_parallelogram_bisect_each_other", 7),
        (RENDER_PARALLELOGRAM_BISECTED_DIAGONAL, "parallelogram", 30, "segment OC", (2, 12), (3, 3), "diagonals_of_a_parallelogram_bisect_each_other", 9),
    ),
}


def _validate_segment_case_table(case_table: Mapping[str, tuple[QuadrilateralCase, ...]]) -> None:
    """Fail fast if a segment-length equation case does not bind to its answer."""

    for branch_name, branch_cases in case_table.items():
        if not branch_cases:
            raise ValueError(f"special quadrilateral segment branch has no cases: {branch_name}")
        for case in branch_cases:
            if case.target_expression is None or case.support_expression is None or case.x_value is None:
                raise ValueError(f"segment case is missing algebraic length expressions: {branch_name}")
            x_value = int(case.x_value)
            target_value = int(case.target_expression.evaluate(x_value))
            support_value = int(case.support_expression.evaluate(x_value))
            if target_value != int(case.answer) or support_value != int(case.answer):
                raise ValueError(f"segment case does not evaluate to the bound answer: {branch_name}")
            if int(case.answer) <= 0:
                raise ValueError(f"segment length answer must be positive: {branch_name}")


_validate_segment_case_table(_CASES_BY_BRANCH)


def _prepare_problem(*, selected_query: str, params: Mapping[str, Any], instance_seed: int) -> tuple[SpecialQuadrilateralProblem, dict[str, float]]:
    """Bind the selected segment theorem branch to one case."""

    cases = _CASES_BY_BRANCH.get(str(selected_query))
    if not cases:
        raise ValueError(f"unsupported special quadrilateral segment-length query: {selected_query}")
    case, case_index, answer_probabilities = select_case_from_answer_support(
        cases=cases,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_query}.case",
    )
    return SpecialQuadrilateralProblem(case=case, case_index=int(case_index), layout_seed=int(instance_seed)), dict(answer_probabilities)


def generate_segment_length_value(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
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
class GeometrySpecialQuadrilateralSegmentLengthValueTask:
    """Solve algebraic side or diagonal segment lengths in a special quadrilateral."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Delegate to this public file's segment-length implementation."""

        task_seed = int(instance_seed)
        task_params = dict(params)
        attempt_limit = max(1, int(max_attempts))
        result = generate_segment_length_value(
            self,
            task_seed,
            params=task_params,
            max_attempts=attempt_limit,
        )
        return result


__all__ = ["GeometrySpecialQuadrilateralSegmentLengthValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
