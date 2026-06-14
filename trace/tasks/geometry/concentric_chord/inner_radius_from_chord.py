"""Compute an inner radius from an outer tangent chord."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import prepare_concentric_chord_task_parts
from .shared.measurements import (
    fmt_measure,
    inner_radius_from_case,
    inner_radius_support_values,
    tangent_chord_diagram_spec,
)
from .shared.sampling import PYTHAGOREAN_CASES, select_concentric_chord_case

TASK_ID = "task_geometry__concentric_chord__inner_radius_from_chord"
INTERNAL_QUERY_ID = "inner_radius_from_chord"
SUPPORTED_QUERY_IDS = ("single",)


def _inner_radius_request(*, instance_seed, params):
    """Select one case and hide the inner radius value."""

    case, case_index = select_concentric_chord_case(
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
    return diagram_spec, int(case_index)


@register_task
class GeometryConcentricInnerRadiusFromChordTask:
    """Compute the inner radius from the visible outer radius and chord."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    reasoning_kind = "concentric_circle_chord"

    def generate(self, instance_seed, *, params, max_attempts) -> TaskOutput:
        """Bind the radius objective and return answer plus keyed annotation."""

        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id="single",
            task_id=TASK_ID,
        )
        spec, case_index = _inner_radius_request(
            instance_seed=int(instance_seed),
            params=task_params,
        )
        parts = prepare_concentric_chord_task_parts(
            task_id=TASK_ID,
            internal_query_id=INTERNAL_QUERY_ID,
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            spec=spec,
            case_index=int(case_index),
            support_values=inner_radius_support_values(PYTHAGOREAN_CASES),
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        return TaskOutput(
            parts.prompt,
            TypedValue(type="number", value=float(spec.answer)),
            TypedValue(type=parts.annotation_artifacts.annotation_type, value=parts.annotation_artifacts.value),
            parts.image,
            "img0",
            parts.trace_payload,
            parts.task_versions,
            parts.scene_id,
            str(selected_query),
            dict(parts.prompt_variants),
        )


__all__ = ["GeometryConcentricInnerRadiusFromChordTask"]
