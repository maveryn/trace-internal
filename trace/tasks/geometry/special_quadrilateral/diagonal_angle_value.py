"""Infer a missing angle from special-quadrilateral diagonal relations."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from ._lifecycle import render_special_quadrilateral_problem
from .shared.output import common_trace_sections, prompt_artifacts_for_bound_case
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


def _select_bound_problem(
    *,
    instance_seed: int,
    params: dict[str, Any],
) -> tuple[str, dict[str, float], dict[str, Any], SpecialQuadrilateralProblem, dict[str, float]]:
    """Resolve this task's diagonal theorem query and numeric case."""

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
    """Render image and prompt artifacts for the diagonal-angle objective."""

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
    branch_probabilities: Mapping[str, float],
    answer_probabilities: Mapping[str, float],
    problem: SpecialQuadrilateralProblem,
) -> dict[str, Any]:
    """Build task-owned prompt query metadata for the diagonal branch."""

    return {
        "scene_id": SCENE_ID,
        "query_id_probabilities": dict(branch_probabilities),
        "answer_support_probabilities": dict(answer_probabilities),
        "case_index": int(problem.case_index),
        "shape_kind": str(problem.case.shape_kind),
        "theorem": str(problem.case.theorem),
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

    trace_payload = common_trace_sections(
        branch_probabilities=dict(branch_probabilities),
        answer_probabilities=answer_probabilities,
        prompt_artifacts=prompt_artifacts,
        problem=problem,
        parts=parts,
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params=_query_params(
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
        "type": "special_quadrilateral_diagonal_angle_relation",
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
    """Bind final public output fields for the diagonal-angle task."""

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
class GeometrySpecialQuadrilateralDiagonalAngleValueTask:
    """Infer a missing angle from special-quadrilateral diagonal relations."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one diagonal-angle instance with task-owned binding."""

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


__all__ = ["GeometrySpecialQuadrilateralDiagonalAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
