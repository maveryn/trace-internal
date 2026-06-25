"""Compute a forward survey bearing from a visible back bearing."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import build_survey_trace_payload, render_survey_attempts, survey_output_metadata
from .shared.annotations import point_scene_annotation
from .shared.defaults import load_survey_traverse_defaults
from .shared.measurements import normalize_bearing
from .shared.prompts import build_survey_traverse_prompt_artifacts
from .shared.rendering import render_back_bearing_scene
from .shared.sampling import BEARING_SUPPORT, choose_from_support, choose_station_labels3
from .shared.state import DOMAIN, BearingBackCase

TASK_ID = "task_geometry__survey_traverse__forward_bearing_from_back_bearing_value"
SINGLE_QUERY_ID = "single"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (SINGLE_QUERY_ID,)
TASK_PROMPT_KEY = "forward_bearing_from_back_bearing_value_query"
FORMULA_FAMILY = "survey_forward_bearing_from_back_bearing"

_GENERATION_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_survey_traverse_defaults()


@register_task
class GeometrySurveyTraverseForwardBearingFromBackBearingValueTask:
    """Compute a forward bearing from the shown reverse bearing."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Bind the reverse-bearing diagram directly to the forward answer."""

        query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )

        station_labels = choose_station_labels3(
            params=task_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.labels",
        )
        forward_bearing, bearing_probabilities = choose_from_support(
            values=BEARING_SUPPORT,
            params=task_params,
            explicit_key="target_bearing",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_bearing",
        )
        reverse_bearing = normalize_bearing(int(forward_bearing) + 180)
        bearing_case = BearingBackCase(
            answer=int(forward_bearing),
            given_bearing=int(reverse_bearing),
            station_labels=station_labels,
            bearing_probabilities=dict(bearing_probabilities),
        )

        def render_forward_scene(context, attempt_seed: int):
            return render_back_bearing_scene(context, bearing_case, instance_seed=int(attempt_seed))

        rendered_attempt = render_survey_attempts(
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            render_defaults=_RENDER_DEFAULTS,
            render_scene=render_forward_scene,
            build_annotation=point_scene_annotation,
        )
        prompt_artifacts = build_survey_traverse_prompt_artifacts(
            prompt_defaults=_PROMPT_DEFAULTS,
            task_prompt_key=TASK_PROMPT_KEY,
            prompt_branch_key=str(query_id),
            annotation_roles=rendered_attempt.rendered.annotation_roles,
            annotation_kind=str(rendered_attempt.annotation_artifacts.annotation_type),
            answer_value=int(forward_bearing),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_survey_trace_payload(
            task_identity=TASK_ID,
            query_id=str(query_id),
            formula_family=FORMULA_FAMILY,
            rendered_attempt=rendered_attempt,
            prompt_artifacts=prompt_artifacts,
            answer_value=int(forward_bearing),
            query_probabilities=query_probabilities,
            query_params_extra={
                "bearing_probabilities": dict(bearing_probabilities),
                **dict(rendered_attempt.rendered.witness),
            },
            execution_extra={
                "known_back_bearing": int(reverse_bearing),
                "target_forward_bearing": int(forward_bearing),
                **dict(rendered_attempt.rendered.witness),
            },
            witness_extra=dict(rendered_attempt.rendered.witness),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(forward_bearing)),
            annotation_gt=TypedValue(
                type=str(rendered_attempt.annotation_artifacts.annotation_type),
                value=rendered_attempt.annotation_artifacts.value,
            ),
            image=rendered_attempt.image,
            image_id="img0",
            trace_payload=dict(trace_payload),
            **survey_output_metadata(prompt_artifacts=prompt_artifacts, query_name=str(query_id)),
        )


__all__ = [
    "GeometrySurveyTraverseForwardBearingFromBackBearingValueTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
