from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import (
    ContainerVolumeQueryProgram,
    ContainerVolumeTaskBinding,
    prepare_container_volume_transfer_task_parts,
    resolve_container_volume_problem,
)
from .shared.defaults import DOMAIN
from .shared.annotations import CONTAINER_BBOX_ANNOTATION_KEYS
from .shared.measurements import json_answer_value, resolve_transferred_volume
from .shared.sampling import TRANSFERRED_VOLUME_CASES, select_repeated_cone_volume_case, select_repeated_cylinder_volume_case

TASK_ID = "task_geometry__container_volume_transfer__transferred_volume_value"
TASK_ID_TRANSFERRED_VOLUME = TASK_ID
QUERY_ID_REPEATED_CONE_POURS_TOTAL_VOLUME = "repeated_cone_pours_total_volume"
QUERY_ID_REPEATED_CYLINDER_POURS_TOTAL_VOLUME = "repeated_cylinder_pours_total_volume"
SUPPORTED_QUERY_IDS = (QUERY_ID_REPEATED_CONE_POURS_TOTAL_VOLUME, QUERY_ID_REPEATED_CYLINDER_POURS_TOTAL_VOLUME)
TRANSFERRED_VOLUME_ANNOTATION_KEYS = CONTAINER_BBOX_ANNOTATION_KEYS
TASK_BINDING = ContainerVolumeTaskBinding("transferred_volume_value_query", TRANSFERRED_VOLUME_ANNOTATION_KEYS, "answer_hint_integer", "integer")
QUERY_PROGRAMS = {
    QUERY_ID_REPEATED_CONE_POURS_TOTAL_VOLUME: ContainerVolumeQueryProgram(
        select_repeated_cone_volume_case,
        resolve_transferred_volume,
        tuple(case for case in TRANSFERRED_VOLUME_CASES if int(case[0]) == 0),
        "answer",
        "repeated_cone_volume",
    ),
    QUERY_ID_REPEATED_CYLINDER_POURS_TOTAL_VOLUME: ContainerVolumeQueryProgram(
        select_repeated_cylinder_volume_case,
        resolve_transferred_volume,
        tuple(case for case in TRANSFERRED_VOLUME_CASES if int(case[0]) == 1),
        "answer",
        "repeated_cylinder_volume",
    ),
}


def _build_problem(*, selected_query, query_probabilities, instance_seed, params):
    program = QUERY_PROGRAMS.get(str(selected_query))
    if program is None:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_query}")
    return resolve_container_volume_problem(
        public_identifier=TASK_ID,
        program=program,
        query_probabilities=query_probabilities,
        instance_seed=int(instance_seed),
        params=params,
    )


@register_task
class GeometryContainerVolumeTransferTransferredVolumeValueTask:
    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID_REPEATED_CONE_POURS_TOTAL_VOLUME,
            task_id=TASK_ID,
        )
        problem = _build_problem(
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            instance_seed=int(instance_seed),
            params=task_params,
        )
        parts = prepare_container_volume_transfer_task_parts(
            public_identifier=TASK_ID,
            selected_query=str(selected_query),
            internal_prompt_key=str(selected_query),
            query_probabilities=query_probabilities,
            problem=problem,
            binding=TASK_BINDING,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        return TaskOutput(*parts.output_args(answer_type=TASK_BINDING.answer_type, answer_value=json_answer_value(problem.answer), query_id=str(selected_query)))
