"""Solve algebraic side or diagonal segment lengths in a special quadrilateral."""

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


@register_task
class GeometrySpecialQuadrilateralSegmentLengthValueTask:
    """Solve algebraic side or diagonal segment lengths in a special quadrilateral."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _bind_segment_case(
        self,
        *,
        seed: int,
        params: dict[str, Any],
    ) -> tuple[str, dict[str, float], dict[str, Any], SpecialQuadrilateralProblem, dict[str, float]]:
        """Choose one segment relation query and one valid equation case."""

        branch, branch_probs, task_params = select_task_query_id(
            instance_seed=int(seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=self.supported_query_ids[0],
            task_id=self.task_id,
            namespace=f"{self.task_id}.query",
        )
        problem, answer_probs = _prepare_problem(
            selected_query=str(branch),
            params=task_params,
            instance_seed=int(seed),
        )
        return str(branch), dict(branch_probs), dict(task_params), problem, dict(answer_probs)

    def _draw_segment_problem(
        self,
        *,
        seed: int,
        max_attempts: int,
        params: Mapping[str, Any],
        branch: str,
        problem: SpecialQuadrilateralProblem,
    ):
        """Render a resolved segment relation and task prompt artifacts."""

        parts = render_special_quadrilateral_problem(
            problem=problem,
            instance_seed=int(seed),
            params=params,
            max_attempts=int(max_attempts),
        )
        prompt_artifacts = prompt_artifacts_for_bound_case(
            prompt_defaults=parts.prompt_defaults,
            task_prompt_key=TASK_PROMPT_KEY,
            branch_prompt_key=str(branch),
            target_name=str(problem.case.target_name),
            annotation_roles=tuple(parts.annotation_artifacts.value.keys()),
            answer_value=int(problem.case.answer),
            instance_seed=int(seed),
        )
        return parts, prompt_artifacts

    def _segment_query_params(
        self,
        *,
        branch_probs: Mapping[str, float],
        answer_probs: Mapping[str, float],
        problem: SpecialQuadrilateralProblem,
    ) -> dict[str, Any]:
        """Return query metadata specific to the segment-length objective."""

        return {
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(branch_probs),
            "answer_support_probabilities": dict(answer_probs),
            "case_index": int(problem.case_index),
            "shape_kind": str(problem.case.shape_kind),
            "theorem": str(problem.case.theorem),
            **expression_payload(problem.case),
        }

    def _segment_trace(
        self,
        *,
        branch: str,
        branch_probs: Mapping[str, float],
        answer_probs: Mapping[str, float],
        problem: SpecialQuadrilateralProblem,
        parts: Any,
        prompt_artifacts: Any,
    ) -> dict[str, Any]:
        """Attach this public task's ids and equation metadata to the trace."""

        trace_payload = common_trace_sections(
            branch_probabilities=dict(branch_probs),
            answer_probabilities=answer_probs,
            prompt_artifacts=prompt_artifacts,
            problem=problem,
            parts=parts,
            extra_case_values=expression_payload(problem.case),
        )
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(branch),
            params=self._segment_query_params(
                branch_probs=branch_probs,
                answer_probs=answer_probs,
                problem=problem,
            ),
        )
        query_spec["scene_id"] = SCENE_ID
        trace_payload["query_spec"] = query_spec
        trace_payload["scene_ir"].update({"task_id": self.task_id, "query_id": str(branch)})
        trace_payload["scene_ir"]["relations"]["query_id"] = str(branch)
        trace_payload["render_spec"].update({"task_id": self.task_id, "query_id": str(branch)})
        trace_payload["execution_trace"]["query_id"] = str(branch)
        trace_payload["witness_symbolic"] = {
            "type": "special_quadrilateral_segment_length_relation",
            "task_id": self.task_id,
            **dict(trace_payload["execution_trace"]),
        }
        return trace_payload

    def _segment_output(
        self,
        *,
        branch: str,
        problem: SpecialQuadrilateralProblem,
        parts: Any,
        prompt_artifacts: Any,
        trace_payload: dict[str, Any],
    ) -> TaskOutput:
        """Construct final output after segment answer and annotation binding."""

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.case.answer)),
            annotation_gt=TypedValue(type=parts.annotation_artifacts.annotation_type, value=parts.annotation_artifacts.value),
            image=parts.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=parts.task_versions,
            scene_id=SCENE_ID,
            query_id=str(branch),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one segment-length instance with task-owned binding."""

        task_seed = int(instance_seed)
        branch, branch_probs, task_params, problem, answer_probs = self._bind_segment_case(
            seed=task_seed,
            params=dict(params),
        )
        parts, prompt_artifacts = self._draw_segment_problem(
            seed=task_seed,
            max_attempts=max(1, int(max_attempts)),
            params=task_params,
            branch=branch,
            problem=problem,
        )
        trace_payload = self._segment_trace(
            branch=branch,
            branch_probs=branch_probs,
            answer_probs=answer_probs,
            problem=problem,
            parts=parts,
            prompt_artifacts=prompt_artifacts,
        )
        return self._segment_output(
            branch=branch,
            problem=problem,
            parts=parts,
            prompt_artifacts=prompt_artifacts,
            trace_payload=trace_payload,
        )


__all__ = ["GeometrySpecialQuadrilateralSegmentLengthValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
