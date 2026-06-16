from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import prepare_concentric_chord_task_parts
from .shared.measurements import (
    fmt_measure,
    inner_radius_from_case,
    tangent_chord_diagram_spec,
)
from .shared.sampling import (
    group_concentric_chord_cases_by_answer,
    select_answer_balanced_concentric_chord_case,
)

TASK_ID = "task_geometry__concentric_chord__inner_radius_from_chord"
INTERNAL_QUERY_ID = "inner_radius_from_chord"
SUPPORTED_QUERY_IDS = ("single",)

_CASES_BY_ANSWER = group_concentric_chord_cases_by_answer(
    answer_fn=inner_radius_from_case,
)


def _inner_radius_request(*, instance_seed, params):
    case, case_index, answer_probabilities = select_answer_balanced_concentric_chord_case(
        answer_cases=_CASES_BY_ANSWER,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{INTERNAL_QUERY_ID}.case",
    )
    answer = inner_radius_from_case(case)
    diagram_spec = tangent_chord_diagram_spec(
        case,
        answer=answer,
        inner_radius_label="r=?",
        chord_label=f"c={fmt_measure(case.chord_length)}",
        formula_family="inner_radius_from_chord",
        unknown_measure="inner_radius",
    )
    return diagram_spec, case_index, answer_probabilities


@register_task
class GeometryConcentricInnerRadiusFromChordTask:
    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id="single",
            task_id=TASK_ID,
        )
        spec, case_index, answer_probabilities = _inner_radius_request(
            instance_seed=int(instance_seed),
            params=task_params,
        )
        parts = prepare_concentric_chord_task_parts(
            task_id=TASK_ID,
            internal_query_id=INTERNAL_QUERY_ID,
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            spec=spec,
            case_index=case_index,
            instance_seed=instance_seed,
            params=task_params,
            max_attempts=max_attempts,
            target_support_probabilities=answer_probabilities,
        )
        return TaskOutput(
            parts.prompt,
            TypedValue(type="integer", value=int(spec.answer)),
            TypedValue(type=parts.annotation_artifacts.annotation_type, value=parts.annotation_artifacts.value),
            parts.image,
            "img0",
            parts.trace_payload,
            parts.task_versions,
            parts.scene_id,
            selected_query,
            parts.prompt_variants,
        )
