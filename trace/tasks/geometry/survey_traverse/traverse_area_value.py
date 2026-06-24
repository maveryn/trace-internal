"""Compute a survey traverse area from coordinate or offset field notes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import SurveyRenderedAttempt, SurveyTraceFields, render_survey_attempts, run_survey_public_task
from .shared.annotations import area_scene_annotation
from .shared.defaults import load_survey_traverse_defaults
from .shared.measurements import offset_area_from_chainages, polygon_area
from .shared.rendering import render_coordinate_area_scene, render_offset_area_scene
from .shared.sampling import COORDINATE_TRAVERSE_CASES, OFFSET_TRAPEZOID_CASES, choose_from_support, choose_station_labels4
from .shared.state import (
    DOMAIN,
    SCENE_ID,
    AreaCoordinateCase,
    AreaOffsetCase,
)

TASK_ID = "task_geometry__survey_traverse__traverse_area_value"
COORDINATE_AREA_BRANCH = "coordinate_traverse_area"
OFFSET_AREA_BRANCH = "offset_trapezoid_area"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (COORDINATE_AREA_BRANCH, OFFSET_AREA_BRANCH)
TASK_PROMPT_KEY = "traverse_area_value_query"

_GENERATION_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_survey_traverse_defaults(TASK_ID)


@dataclass(frozen=True)
class ResolvedAreaProblem:
    """Task-owned area problem with coordinates or offsets bound."""

    branch_name: str
    answer: int
    station_labels: tuple[str, str, str, str]
    coordinate_points: tuple[tuple[int, int], ...]
    chainages: tuple[int, ...]
    offsets: tuple[int, ...]
    formula_family: str
    branch_probabilities: dict[str, float]
    case_probabilities: dict[str, float]


def _resolve_area_problem(*, branch_name: str, branch_probabilities: Mapping[str, float], instance_seed: int, params: Mapping[str, Any]) -> ResolvedAreaProblem:
    """Resolve one public area branch into concrete coordinate or offset inputs."""

    labels = choose_station_labels4(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.labels")
    if str(branch_name) == COORDINATE_AREA_BRANCH:
        case, case_probabilities = choose_from_support(
            values=COORDINATE_TRAVERSE_CASES,
            params=params,
            explicit_key="area_case",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.coordinate_case",
        )
        points = tuple((int(case[idx]), int(case[idx + 1])) for idx in range(0, len(case), 2))
        return ResolvedAreaProblem(
            branch_name=str(branch_name),
            answer=int(polygon_area(points)),
            station_labels=labels,
            coordinate_points=points,
            chainages=(),
            offsets=(),
            formula_family="survey_coordinate_traverse_area",
            branch_probabilities=dict(branch_probabilities),
            case_probabilities=dict(case_probabilities),
        )

    case, case_probabilities = choose_from_support(
        values=OFFSET_TRAPEZOID_CASES,
        params=params,
        explicit_key="area_case",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.offset_case",
    )
    chainages = (0, int(case[0]), int(case[1]), int(case[2]))
    offsets = (int(case[3]), int(case[4]), int(case[5]), int(case[6]))
    return ResolvedAreaProblem(
        branch_name=str(branch_name),
        answer=int(offset_area_from_chainages(chainages, offsets)),
        station_labels=labels,
        coordinate_points=(),
        chainages=chainages,
        offsets=offsets,
        formula_family="survey_offset_trapezoid_area",
        branch_probabilities=dict(branch_probabilities),
        case_probabilities=dict(case_probabilities),
    )


def _render_area_attempt(
    *,
    problem: ResolvedAreaProblem,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> SurveyRenderedAttempt:
    """Render the coordinate or offset-area case selected by this public task."""

    def render_scene(context, attempt_seed: int):
        if problem.branch_name == COORDINATE_AREA_BRANCH:
            return render_coordinate_area_scene(
                context,
                AreaCoordinateCase(
                    answer=int(problem.answer),
                    station_labels=problem.station_labels,
                    coordinate_points=problem.coordinate_points,
                    case_probabilities=dict(problem.case_probabilities),
                ),
                instance_seed=int(attempt_seed),
            )
        return render_offset_area_scene(
            context,
            AreaOffsetCase(
                answer=int(problem.answer),
                station_labels=problem.station_labels,
                chainages=problem.chainages,
                offsets=problem.offsets,
                case_probabilities=dict(problem.case_probabilities),
            ),
            instance_seed=int(attempt_seed),
        )

    return render_survey_attempts(
        instance_seed=int(instance_seed),
        params=params,
        max_attempts=int(max_attempts),
        render_defaults=_RENDER_DEFAULTS,
        render_scene=render_scene,
        build_annotation=area_scene_annotation,
    )


def _answer_value(problem: ResolvedAreaProblem) -> int:
    """Bind the integer answer from the selected area formula."""

    return int(problem.answer)


def _build_area_trace_fields(problem: ResolvedAreaProblem, rendered_attempt: SurveyRenderedAttempt, answer_value: int) -> SurveyTraceFields:
    """Expose area-specific formula fields to the common trace envelope."""

    area_fields = {
        "coordinate_points": [[int(x), int(y)] for x, y in problem.coordinate_points],
        "chainages": [int(value) for value in problem.chainages],
        "offsets": [int(value) for value in problem.offsets],
        **dict(rendered_attempt.rendered.witness),
    }
    return SurveyTraceFields(
        formula_family=str(problem.formula_family),
        query_params_extra={
            "case_probabilities": dict(problem.case_probabilities),
            **dict(rendered_attempt.rendered.witness),
        },
        execution_extra=area_fields,
        witness_extra=dict(rendered_attempt.rendered.witness),
        relation_extra={},
    )


@register_task
class GeometrySurveyTraverseTraverseAreaValueTask:
    """Compute a survey traverse area from coordinate or offset field notes."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_survey_public_task(
            task_identity=TASK_ID,
            supported_branches=SUPPORTED_QUERY_IDS,
            default_branch=COORDINATE_AREA_BRANCH,
            task_prompt_key=TASK_PROMPT_KEY,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            resolve_problem=_resolve_area_problem,
            render_attempt=_render_area_attempt,
            answer_value=_answer_value,
            trace_fields=_build_area_trace_fields,
        )


__all__ = ["GeometrySurveyTraverseTraverseAreaValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
