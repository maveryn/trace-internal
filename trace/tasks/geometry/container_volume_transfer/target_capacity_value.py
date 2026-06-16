from trace.core.query_ids import SINGLE_QUERY_ID
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
from .shared.measurements import json_answer_value, resolve_target_capacity
from .shared.sampling import TARGET_CAPACITY_CASES, select_target_capacity_case

TASK_ID = "task_geometry__container_volume_transfer__target_capacity_value"
TASK_ID_TARGET_CAPACITY = TASK_ID
QUERY_ID_TARGET_CAPACITY_FROM_SOURCE_AND_COUNT = "target_capacity_from_source_and_count"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
TARGET_CAPACITY_ANNOTATION_KEYS = CONTAINER_BBOX_ANNOTATION_KEYS
TASK_BINDING = ContainerVolumeTaskBinding("target_capacity_value_query", TARGET_CAPACITY_ANNOTATION_KEYS, "answer_hint_integer", "integer")
QUERY_PROGRAM = ContainerVolumeQueryProgram(
    select_target_capacity_case,
    resolve_target_capacity,
    TARGET_CAPACITY_CASES,
    "target_volume",
    "target_capacity",
)


def _build_problem(*, query_probabilities, instance_seed, params):
    return resolve_container_volume_problem(
        public_identifier=TASK_ID,
        program=QUERY_PROGRAM,
        query_probabilities=query_probabilities,
        instance_seed=int(instance_seed),
        params=params,
    )


@register_task
class GeometryContainerVolumeTransferTargetCapacityValueTask:
    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
        )
        problem = _build_problem(
            query_probabilities=query_probabilities,
            instance_seed=int(instance_seed),
            params=task_params,
        )
        parts = prepare_container_volume_transfer_task_parts(
            public_identifier=TASK_ID,
            selected_query=str(selected_query),
            internal_prompt_key=QUERY_ID_TARGET_CAPACITY_FROM_SOURCE_AND_COUNT,
            query_probabilities=query_probabilities,
            problem=problem,
            binding=TASK_BINDING,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        return TaskOutput(*parts.output_args(answer_type=TASK_BINDING.answer_type, answer_value=json_answer_value(problem.answer), query_id=str(selected_query)))
