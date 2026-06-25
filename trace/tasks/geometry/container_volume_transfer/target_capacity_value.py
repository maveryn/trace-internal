from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import build_container_volume_result
from .shared.defaults import DOMAIN, load_container_volume_transfer_task_defaults
from .shared.annotations import CONTAINER_BBOX_ANNOTATION_KEYS
from .shared.measurements import json_answer_value, resolve_target_capacity
from .shared.relations import (
    ContainerVolumeQueryProgram,
    ContainerVolumeTaskBinding,
    resolve_container_volume_problem,
)
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
        program=QUERY_PROGRAM,
        query_probabilities=query_probabilities,
        instance_seed=int(instance_seed),
        params=params,
        random_namespace=f"{TASK_ID}.{QUERY_PROGRAM.namespace_suffix}.case",
    )

@register_task
class GeometryContainerVolumeTransferTargetCapacityValueTask:
    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Bind the capacity objective and return the final task output."""

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
        render_defaults, prompt_defaults = load_container_volume_transfer_task_defaults(TASK_ID)
        return build_container_volume_result(
            str(selected_query),
            QUERY_ID_TARGET_CAPACITY_FROM_SOURCE_AND_COUNT,
            query_probabilities,
            problem,
            TASK_BINDING,
            json_answer_value(problem.answer),
            render_defaults,
            prompt_defaults,
            int(instance_seed),
            task_params,
            int(max_attempts),
            f"{TASK_ID}.render",
        )
