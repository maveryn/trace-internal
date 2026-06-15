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
from .shared.measurements import json_answer_value, resolve_cone_resulting_height, resolve_cylinder_resulting_height
from .shared.sampling import CONE_HEIGHT_CASES, CYLINDER_HEIGHT_CASES, select_cone_height_case, select_cylinder_height_case

TASK_ID = "task_geometry__container_volume_transfer__resulting_height_value"
TASK_ID_RESULTING_HEIGHT = TASK_ID
QUERY_ID_CONE_POURS_TO_CYLINDER_HEIGHT = "cone_pours_to_cylinder_height"
QUERY_ID_CYLINDER_POURS_TO_CUBOID_HEIGHT = "cylinder_pours_to_cuboid_height"
SUPPORTED_QUERY_IDS = (QUERY_ID_CONE_POURS_TO_CYLINDER_HEIGHT, QUERY_ID_CYLINDER_POURS_TO_CUBOID_HEIGHT)
RESULTING_HEIGHT_ANNOTATION_KEYS = (
    "source_container_bbox",
    "target_container_bbox",
    "source_dimension_region_bbox",
    "target_base_dimension_region_bbox",
    "transfer_count_bbox",
    "fill_mark_bbox",
)
TASK_BINDING = ContainerVolumeTaskBinding("resulting_height_value_query", RESULTING_HEIGHT_ANNOTATION_KEYS, "answer_hint_decimal", "number")
QUERY_PROGRAMS = {
    QUERY_ID_CONE_POURS_TO_CYLINDER_HEIGHT: ContainerVolumeQueryProgram(
        select_cone_height_case,
        resolve_cone_resulting_height,
        CONE_HEIGHT_CASES,
        "answer",
        "cone_resulting_height",
    ),
    QUERY_ID_CYLINDER_POURS_TO_CUBOID_HEIGHT: ContainerVolumeQueryProgram(
        select_cylinder_height_case,
        resolve_cylinder_resulting_height,
        CYLINDER_HEIGHT_CASES,
        "answer",
        "cylinder_resulting_height",
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
class GeometryContainerVolumeTransferResultingHeightValueTask:
    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID_CONE_POURS_TO_CYLINDER_HEIGHT,
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
