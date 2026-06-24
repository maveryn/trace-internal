"""Compute a survey-traverse bearing angle from visible station information."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import SurveyRenderedAttempt, SurveyTraceFields, render_survey_attempts, run_survey_public_task
from .shared.annotations import point_scene_annotation
from .shared.defaults import load_survey_traverse_defaults
from .shared.measurements import normalize_bearing
from .shared.rendering import render_back_bearing_scene, render_closed_traverse_scene
from .shared.sampling import BEARING_SUPPORT, choose_from_support, choose_station_labels3, choose_turn
from .shared.state import (
    DOMAIN,
    SCENE_ID,
    BearingBackCase,
    BearingTurnCase,
)

TASK_ID = "task_geometry__survey_traverse__bearing_angle_value"
BEARING_FROM_BACK_BRANCH = "bearing_from_back_bearing"
CLOSED_TRAVERSE_BRANCH = "closed_traverse_missing_bearing"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (BEARING_FROM_BACK_BRANCH, CLOSED_TRAVERSE_BRANCH)
TASK_PROMPT_KEY = "bearing_angle_value_query"

_GENERATION_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_survey_traverse_defaults(TASK_ID)


@dataclass(frozen=True)
class ResolvedBearingProblem:
    """Task-owned bearing problem with query branch and formula inputs bound."""

    branch_name: str
    answer: int
    known_bearing: int
    given_bearing: int
    station_labels: tuple[str, str, str]
    turn_angle: int | None
    turn_direction: str | None
    branch_probabilities: dict[str, float]
    bearing_probabilities: dict[str, float]
    turn_probabilities: dict[str, float]


def _resolve_bearing_problem(*, branch_name: str, branch_probabilities: Mapping[str, float], instance_seed: int, params: Mapping[str, Any]) -> ResolvedBearingProblem:
    """Resolve one public bearing branch into concrete formula inputs."""

    labels = choose_station_labels3(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.labels")
    if str(branch_name) == BEARING_FROM_BACK_BRANCH:
        answer, bearing_probabilities = choose_from_support(
            values=BEARING_SUPPORT,
            params=params,
            explicit_key="target_bearing",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_bearing",
        )
        given_bearing = normalize_bearing(int(answer) + 180)
        return ResolvedBearingProblem(
            branch_name=str(branch_name),
            answer=int(answer),
            known_bearing=int(answer),
            given_bearing=int(given_bearing),
            station_labels=labels,
            turn_angle=None,
            turn_direction=None,
            branch_probabilities=dict(branch_probabilities),
            bearing_probabilities=dict(bearing_probabilities),
            turn_probabilities={},
        )

    base_bearing, bearing_probabilities = choose_from_support(
        values=BEARING_SUPPORT,
        params=params,
        explicit_key="base_bearing",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.base_bearing",
    )
    turn_angle, turn_direction, turn_probabilities = choose_turn(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.turn",
    )
    answer = (
        normalize_bearing(int(base_bearing) - int(turn_angle))
        if str(turn_direction) == "left"
        else normalize_bearing(int(base_bearing) + int(turn_angle))
    )
    if int(answer) == 0:
        answer = 360
    if int(answer) >= 360:
        raise ValueError("closed traverse generated unsupported 360-degree answer")
    return ResolvedBearingProblem(
        branch_name=str(branch_name),
        answer=int(answer),
        known_bearing=int(base_bearing),
        given_bearing=int(base_bearing),
        station_labels=labels,
        turn_angle=int(turn_angle),
        turn_direction=str(turn_direction),
        branch_probabilities=dict(branch_probabilities),
        bearing_probabilities=dict(bearing_probabilities),
        turn_probabilities=dict(turn_probabilities),
    )


def _render_bearing_attempt(
    *,
    problem: ResolvedBearingProblem,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> SurveyRenderedAttempt:
    """Render the bearing-specific scene case selected by this public task."""

    def render_scene(context, attempt_seed: int):
        if problem.branch_name == BEARING_FROM_BACK_BRANCH:
            return render_back_bearing_scene(
                context,
                BearingBackCase(
                    answer=int(problem.answer),
                    given_bearing=int(problem.given_bearing),
                    station_labels=problem.station_labels,
                    bearing_probabilities=dict(problem.bearing_probabilities),
                ),
                instance_seed=int(attempt_seed),
            )
        return render_closed_traverse_scene(
            context,
            BearingTurnCase(
                answer=int(problem.answer),
                base_bearing=int(problem.known_bearing),
                turn_angle=int(problem.turn_angle or 0),
                turn_direction=str(problem.turn_direction or "right"),
                station_labels=problem.station_labels,
                bearing_probabilities=dict(problem.bearing_probabilities),
                turn_probabilities=dict(problem.turn_probabilities),
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


def _answer_value(problem: ResolvedBearingProblem) -> int:
    """Bind the integer answer from the selected bearing formula."""

    return int(problem.answer)


def _build_bearing_trace_fields(problem: ResolvedBearingProblem, rendered_attempt: SurveyRenderedAttempt, answer_value: int) -> SurveyTraceFields:
    """Expose bearing-specific formula fields to the common trace envelope."""

    return SurveyTraceFields(
        formula_family="survey_bearing_angle",
        query_params_extra={
            "bearing_probabilities": dict(problem.bearing_probabilities),
            "turn_probabilities": dict(problem.turn_probabilities),
            **dict(rendered_attempt.rendered.witness),
        },
        execution_extra={
            "known_bearing": int(problem.known_bearing),
            "given_bearing": int(problem.given_bearing),
            "turn_angle": problem.turn_angle,
            "turn_direction": problem.turn_direction,
            **dict(rendered_attempt.rendered.witness),
        },
        witness_extra=dict(rendered_attempt.rendered.witness),
        relation_extra={},
    )


@register_task
class GeometrySurveyTraverseBearingAngleValueTask:
    """Compute a survey-style bearing angle from station diagram relationships."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_survey_public_task(
            task_identity=TASK_ID,
            supported_branches=SUPPORTED_QUERY_IDS,
            default_branch=BEARING_FROM_BACK_BRANCH,
            task_prompt_key=TASK_PROMPT_KEY,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            resolve_problem=_resolve_bearing_problem,
            render_attempt=_render_bearing_attempt,
            answer_value=_answer_value,
            trace_fields=_build_bearing_trace_fields,
        )


__all__ = ["GeometrySurveyTraverseBearingAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
