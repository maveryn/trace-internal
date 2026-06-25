"""Compute a survey traverse area from coordinate or offset field notes."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import build_survey_trace_payload, render_survey_attempts, survey_output_metadata
from .shared.annotations import area_scene_annotation
from .shared.defaults import load_survey_traverse_defaults
from .shared.measurements import offset_area_from_chainages, polygon_area
from .shared.prompts import build_survey_traverse_prompt_artifacts
from .shared.rendering import render_coordinate_area_scene, render_offset_area_scene
from .shared.sampling import COORDINATE_TRAVERSE_CASES, OFFSET_TRAPEZOID_CASES, choose_from_support, choose_station_labels4
from .shared.state import (
    DOMAIN,
    AreaCoordinateCase,
    AreaOffsetCase,
)

TASK_ID = "task_geometry__survey_traverse__traverse_area_value"
COORDINATE_AREA_BRANCH = "coordinate_traverse_area"
OFFSET_AREA_BRANCH = "offset_trapezoid_area"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (COORDINATE_AREA_BRANCH, OFFSET_AREA_BRANCH)
TASK_PROMPT_KEY = "traverse_area_value_query"

_GENERATION_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_survey_traverse_defaults()


def _coordinate_area_scene_inputs(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[AreaCoordinateCase, dict[str, float]]:
    """Choose a coordinate traverse and bind its area answer."""

    labels = choose_station_labels4(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.labels")
    case, case_probabilities = choose_from_support(
        values=COORDINATE_TRAVERSE_CASES,
        params=params,
        explicit_key="area_case",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.coordinate_case",
    )
    points = tuple((int(case[idx]), int(case[idx + 1])) for idx in range(0, len(case), 2))
    return (
        AreaCoordinateCase(
            answer=int(polygon_area(points)),
            station_labels=labels,
            coordinate_points=points,
            case_probabilities=dict(case_probabilities),
        ),
        dict(case_probabilities),
    )


def _offset_area_scene_inputs(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[AreaOffsetCase, dict[str, float]]:
    """Choose offset survey notes and bind their trapezoid-rule area."""

    labels = choose_station_labels4(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.labels")
    case, case_probabilities = choose_from_support(
        values=OFFSET_TRAPEZOID_CASES,
        params=params,
        explicit_key="area_case",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.offset_case",
    )
    chainages = (0, int(case[0]), int(case[1]), int(case[2]))
    offsets = (int(case[3]), int(case[4]), int(case[5]), int(case[6]))
    return (
        AreaOffsetCase(
            answer=int(offset_area_from_chainages(chainages, offsets)),
            station_labels=labels,
            chainages=chainages,
            offsets=offsets,
            case_probabilities=dict(case_probabilities),
        ),
        dict(case_probabilities),
    )


@register_task
class GeometrySurveyTraverseTraverseAreaValueTask:
    """Compute a survey traverse area from coordinate or offset field notes."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Bind coordinate or offset field notes to an integer traverse area."""

        branch_name, branch_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=COORDINATE_AREA_BRANCH,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )

        if str(branch_name) == COORDINATE_AREA_BRANCH:
            area_case, case_probabilities = _coordinate_area_scene_inputs(instance_seed=int(instance_seed), params=task_params)
            formula_family = "survey_coordinate_traverse_area"

            def render_area_scene(context, attempt_seed: int):
                return render_coordinate_area_scene(context, area_case, instance_seed=int(attempt_seed))

            area_fields = {
                "coordinate_points": [[int(x), int(y)] for x, y in area_case.coordinate_points],
                "chainages": [],
                "offsets": [],
            }
        else:
            area_case, case_probabilities = _offset_area_scene_inputs(instance_seed=int(instance_seed), params=task_params)
            formula_family = "survey_offset_trapezoid_area"

            def render_area_scene(context, attempt_seed: int):
                return render_offset_area_scene(context, area_case, instance_seed=int(attempt_seed))

            area_fields = {
                "coordinate_points": [],
                "chainages": [int(value) for value in area_case.chainages],
                "offsets": [int(value) for value in area_case.offsets],
            }

        rendered_attempt = render_survey_attempts(
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            render_defaults=_RENDER_DEFAULTS,
            render_scene=render_area_scene,
            build_annotation=area_scene_annotation,
        )
        answer = int(area_case.answer)
        prompt_artifacts = build_survey_traverse_prompt_artifacts(
            task_prompt_key=TASK_PROMPT_KEY,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            prompt_branch_key=str(branch_name),
            annotation_roles=rendered_attempt.rendered.annotation_roles,
            annotation_kind=str(rendered_attempt.annotation_artifacts.annotation_type),
            answer_value=int(answer),
        )
        trace_payload = build_survey_trace_payload(
            task_identity=TASK_ID,
            query_id=str(branch_name),
            formula_family=str(formula_family),
            rendered_attempt=rendered_attempt,
            prompt_artifacts=prompt_artifacts,
            answer_value=int(answer),
            query_probabilities=branch_probabilities,
            query_params_extra={
                "case_probabilities": dict(case_probabilities),
                **dict(rendered_attempt.rendered.witness),
            },
            execution_extra={
                **area_fields,
                **dict(rendered_attempt.rendered.witness),
            },
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
            **survey_output_metadata(prompt_artifacts=prompt_artifacts, query_name=str(branch_name)),
        )


__all__ = ["GeometrySurveyTraverseTraverseAreaValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
