"""Infer a missing angle from special-quadrilateral diagonal relations."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import prepare_special_quadrilateral_task_parts
from .shared.rendering import (
    RENDER_KITE_SYMMETRY_BISECTOR,
    RENDER_RHOMBUS_PERPENDICULAR_DIAGONALS,
    RENDER_RHOMBUS_VERTEX_BISECTOR,
)
from .shared.sampling import select_case_from_answer_support
from .shared.state import DEGREE_SYMBOL, DOMAIN, QuadrilateralCase, SCENE_ID, SpecialQuadrilateralProblem

TASK_ID = "task_geometry__special_quadrilateral__diagonal_angle_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "rhombus_vertex_angle_bisected_by_diagonal",
    "kite_vertex_angle_bisected_by_symmetry_diagonal",
    "rhombus_diagonal_perpendicular_complement",
)
TASK_PROMPT_KEY = "diagonal_angle_value_query"


def _degree(value: int) -> str:
    return f"{int(value)}{DEGREE_SYMBOL}"


def _case(*, render_kind: str, shape_kind: str, answer: int, target_name: str, support_angle: int, theorem: str) -> QuadrilateralCase:
    return QuadrilateralCase(
        render_kind=str(render_kind),
        shape_kind=str(shape_kind),
        answer=int(answer),
        target_name=str(target_name),
        target_label=_degree(answer),
        support_label=_degree(support_angle),
        theorem=str(theorem),
    )


_CASES_BY_BRANCH: dict[str, tuple[QuadrilateralCase, ...]] = {
    "rhombus_vertex_angle_bisected_by_diagonal": tuple(
        _case(
            render_kind=RENDER_RHOMBUS_VERTEX_BISECTOR,
            shape_kind="rhombus",
            answer=value,
            target_name="angle BDO",
            support_angle=value,
            theorem="rhombus_diagonal_bisects_vertex_angle",
        )
        for value in (35, 45, 55, 25, 65)
    ),
    "kite_vertex_angle_bisected_by_symmetry_diagonal": tuple(
        _case(
            render_kind=RENDER_KITE_SYMMETRY_BISECTOR,
            shape_kind="kite",
            answer=value,
            target_name="angle BAC",
            support_angle=value,
            theorem="kite_symmetry_diagonal_bisects_vertex_angle",
        )
        for value in (30, 40, 50, 25, 55)
    ),
    "rhombus_diagonal_perpendicular_complement": tuple(
        _case(
            render_kind=RENDER_RHOMBUS_PERPENDICULAR_DIAGONALS,
            shape_kind="rhombus",
            answer=value,
            target_name="angle ABO",
            support_angle=90 - value,
            theorem="rhombus_diagonals_are_perpendicular",
        )
        for value in (30, 40, 55, 20, 65)
    ),
}


def _prepare_problem(*, selected_query: str, params: Mapping[str, Any], instance_seed: int) -> tuple[SpecialQuadrilateralProblem, dict[str, float]]:
    """Bind the selected diagonal theorem branch to one case."""

    cases = _CASES_BY_BRANCH.get(str(selected_query))
    if not cases:
        raise ValueError(f"unsupported special quadrilateral diagonal-angle query: {selected_query}")
    case, case_index, answer_probabilities = select_case_from_answer_support(
        cases=cases,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_query}.case",
    )
    return SpecialQuadrilateralProblem(case=case, case_index=int(case_index), layout_seed=int(instance_seed)), dict(answer_probabilities)


def generate_diagonal_angle_value(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
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
class GeometrySpecialQuadrilateralDiagonalAngleValueTask:
    """Infer a missing angle from special-quadrilateral diagonal relations."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Delegate to this public file's diagonal-angle implementation."""

        task_seed = int(instance_seed)
        task_params = dict(params)
        attempt_limit = max(1, int(max_attempts))
        result = generate_diagonal_angle_value(
            self,
            task_seed,
            params=task_params,
            max_attempts=attempt_limit,
        )
        return result


__all__ = ["GeometrySpecialQuadrilateralDiagonalAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
