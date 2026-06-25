"""Compute a station elevation from survey leveling or profile notes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import SurveyRenderedAttempt, build_survey_trace_payload, render_survey_attempts, survey_output_metadata
from .shared.annotations import point_scene_annotation
from .shared.defaults import load_survey_traverse_defaults
from .shared.prompts import build_survey_traverse_prompt_artifacts
from .shared.rendering import render_leveling_station_scene, render_slope_elevation_scene
from .shared.sampling import LEVELING_CASES, SLOPE_ELEVATION_CASES, choose_from_support, choose_station_labels3
from .shared.state import (
    DOMAIN,
    SCENE_ID,
    ElevationLevelingCase,
    ElevationSlopeCase,
)

TASK_ID = "task_geometry__survey_traverse__station_elevation_value"
LEVELING_BRANCH = "leveling_station_elevation"
SLOPE_BRANCH = "slope_distance_elevation_change"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (LEVELING_BRANCH, SLOPE_BRANCH)
TASK_PROMPT_KEY = "station_elevation_value_query"

_GENERATION_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_survey_traverse_defaults()


@dataclass(frozen=True)
class ResolvedElevationProblem:
    """Task-owned elevation problem with formula inputs bound."""

    branch_name: str
    answer: int
    reference_elevation: int
    target_elevation: int
    station_labels: tuple[str, str, str]
    backsight: int | None
    foresight: int | None
    height_of_instrument: int | None
    slope_distance: int | None
    rise_per_20: int | None
    total_rise: int | None
    formula_family: str
    branch_probabilities: dict[str, float]
    case_probabilities: dict[str, float]


def _resolve_elevation_problem(*, branch_name: str, branch_probabilities: Mapping[str, float], instance_seed: int, params: Mapping[str, Any]) -> ResolvedElevationProblem:
    """Resolve one public elevation branch into concrete field-note arithmetic."""

    labels = choose_station_labels3(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.labels")
    if str(branch_name) == LEVELING_BRANCH:
        case, case_probabilities = choose_from_support(
            values=LEVELING_CASES,
            params=params,
            explicit_key="elevation_case",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.leveling_case",
        )
        reference_elevation, backsight, foresight = [int(value) for value in case]
        height_of_instrument = int(reference_elevation + backsight)
        target_elevation = int(height_of_instrument - foresight)
        return ResolvedElevationProblem(
            branch_name=str(branch_name),
            answer=int(target_elevation),
            reference_elevation=int(reference_elevation),
            target_elevation=int(target_elevation),
            station_labels=labels,
            backsight=int(backsight),
            foresight=int(foresight),
            height_of_instrument=int(height_of_instrument),
            slope_distance=None,
            rise_per_20=None,
            total_rise=None,
            formula_family="survey_leveling_station_elevation",
            branch_probabilities=dict(branch_probabilities),
            case_probabilities=dict(case_probabilities),
        )

    case, case_probabilities = choose_from_support(
        values=SLOPE_ELEVATION_CASES,
        params=params,
        explicit_key="elevation_case",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.slope_case",
    )
    reference_elevation, slope_distance, rise_per_20 = [int(value) for value in case]
    total_rise = int((int(slope_distance) // 20) * int(rise_per_20))
    target_elevation = int(reference_elevation + total_rise)
    return ResolvedElevationProblem(
        branch_name=str(branch_name),
        answer=int(target_elevation),
        reference_elevation=int(reference_elevation),
        target_elevation=int(target_elevation),
        station_labels=labels,
        backsight=None,
        foresight=None,
        height_of_instrument=None,
        slope_distance=int(slope_distance),
        rise_per_20=int(rise_per_20),
        total_rise=int(total_rise),
        formula_family="survey_slope_distance_elevation_change",
        branch_probabilities=dict(branch_probabilities),
        case_probabilities=dict(case_probabilities),
    )


def _render_elevation_attempt(
    *,
    problem: ResolvedElevationProblem,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> SurveyRenderedAttempt:
    """Render the elevation field-note case selected by this public task."""

    def render_scene(context, attempt_seed: int):
        if problem.branch_name == LEVELING_BRANCH:
            return render_leveling_station_scene(
                context,
                ElevationLevelingCase(
                    answer=int(problem.answer),
                    reference_elevation=int(problem.reference_elevation),
                    backsight=int(problem.backsight or 0),
                    foresight=int(problem.foresight or 0),
                    height_of_instrument=int(problem.height_of_instrument or 0),
                    station_labels=problem.station_labels,
                    case_probabilities=dict(problem.case_probabilities),
                ),
                instance_seed=int(attempt_seed),
            )
        return render_slope_elevation_scene(
            context,
            ElevationSlopeCase(
                answer=int(problem.answer),
                reference_elevation=int(problem.reference_elevation),
                slope_distance=int(problem.slope_distance or 0),
                rise_per_20=int(problem.rise_per_20 or 0),
                total_rise=int(problem.total_rise or 0),
                station_labels=problem.station_labels,
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
        build_annotation=point_scene_annotation,
    )


def _answer_value(problem: ResolvedElevationProblem) -> int:
    """Bind the integer answer from the selected elevation formula."""

    return int(problem.answer)


def _formula_fields(problem: ResolvedElevationProblem, rendered_attempt: SurveyRenderedAttempt) -> dict[str, Any]:
    """Return task-owned elevation formula fields for trace output."""

    return {
        "reference_elevation": int(problem.reference_elevation),
        "target_elevation": int(problem.target_elevation),
        "backsight": problem.backsight,
        "foresight": problem.foresight,
        "height_of_instrument": problem.height_of_instrument,
        "slope_distance": problem.slope_distance,
        "rise_per_20": problem.rise_per_20,
        "total_rise": problem.total_rise,
        **dict(rendered_attempt.rendered.witness),
    }


@register_task
class GeometrySurveyTraverseStationElevationValueTask:
    """Compute a missing station elevation from a survey diagram and field note."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Bind the selected elevation formula, prompt, annotation, and output."""

        branch_name, branch_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=LEVELING_BRANCH,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        problem = _resolve_elevation_problem(
            branch_name=str(branch_name),
            branch_probabilities=branch_probabilities,
            instance_seed=int(instance_seed),
            params=task_params,
        )
        rendered_attempt = _render_elevation_attempt(
            problem=problem,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        answer = _answer_value(problem)
        prompt_artifacts = build_survey_traverse_prompt_artifacts(
            task_prompt_key=TASK_PROMPT_KEY,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            prompt_branch_key=str(problem.branch_name),
            annotation_roles=rendered_attempt.rendered.annotation_roles,
            annotation_kind=str(rendered_attempt.annotation_artifacts.annotation_type),
            answer_value=int(answer),
        )
        formula_fields = _formula_fields(problem, rendered_attempt)
        trace_payload = build_survey_trace_payload(
            task_identity=TASK_ID,
            query_id=str(problem.branch_name),
            formula_family=str(problem.formula_family),
            rendered_attempt=rendered_attempt,
            prompt_artifacts=prompt_artifacts,
            answer_value=int(answer),
            query_probabilities=problem.branch_probabilities,
            query_params_extra={
                "case_probabilities": dict(problem.case_probabilities),
                **dict(rendered_attempt.rendered.witness),
            },
            execution_extra=formula_fields,
            witness_extra=dict(rendered_attempt.rendered.witness),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer)),
            annotation_gt=TypedValue(
                type=str(rendered_attempt.annotation_artifacts.annotation_type),
                value=rendered_attempt.annotation_artifacts.value,
            ),
            image=rendered_attempt.image,
            image_id="img0",
            trace_payload=dict(trace_payload),
            **survey_output_metadata(prompt_artifacts=prompt_artifacts, query_name=str(problem.branch_name)),
        )


__all__ = ["GeometrySurveyTraverseStationElevationValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
