"""Compute the folded cone base radius from a sector net."""

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import prepare_cone_net_task_parts
from .shared.defaults import DOMAIN, SCENE_ID
from .shared.measurements import (
    base_radius_from_sector,
    base_radius_support_values,
    cone_net_diagram_spec,
)
from .shared.sampling import CONE_NET_CASES, resolve_cone_net_case

TASK_ID = "task_geometry__cone_net__base_radius_from_sector_angle"
INTERNAL_QUERY_ID = "base_radius_from_sector_angle"
SUPPORTED_QUERY_IDS = ("single",)


def _build_base_radius_request(*, instance_seed, params):
    case, case_index = resolve_cone_net_case(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{INTERNAL_QUERY_ID}.case",
    )
    answer = base_radius_from_sector(case)
    return (
        cone_net_diagram_spec(
            case,
            answer=answer,
            target_measure="base_radius",
            target_label="r=?",
            target_label_anchor="radius_segment",
            annotation_roles=("S", "P", "Q", "C", "R"),
            formula_family=INTERNAL_QUERY_ID,
            reasoning_steps=1,
        ),
        int(case_index),
    )


@register_task
class GeometryConeNetBaseRadiusFromSectorAngleTask:
    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id="single",
            task_id=TASK_ID,
        )
        spec, case_index = _build_base_radius_request(
            instance_seed=int(instance_seed),
            params=task_params,
        )
        parts = prepare_cone_net_task_parts(
            public_identifier=TASK_ID,
            internal_prompt_key=INTERNAL_QUERY_ID,
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            spec=spec,
            case_index=int(case_index),
            support_values=base_radius_support_values(CONE_NET_CASES),
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
