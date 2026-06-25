"""Solve a missing dimension after converting between equal-volume solids."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import VolumeEquivalenceTaskBinding, prepare_volume_equivalence_task_parts
from .shared.annotations import MISSING_DIMENSION_ANNOTATION_KEYS, OPTION_ANNOTATION_KEYS
from .shared.construction import (
    CONE_TO_CUBOID_HEIGHT_CASES,
    CUBOID_TO_CYLINDER_LENGTH_CASES,
    CYLINDER_TO_CONE_HEIGHT_CASES,
    bind_case_metadata,
    resolve_cone_to_cuboid_height,
    resolve_cuboid_to_cylinder_length,
    resolve_cylinder_to_cone_height,
)
from .shared.defaults import DOMAIN, SCENE_ID
from .shared.rendering import render_missing_dimension_scene
from .shared.sampling import select_conversion_case
from .shared.state import ResolvedProblem


TASK_ID = "task_geometry__volume_equivalence_conversion__missing_dimension_value"
TASK_ID_MISSING_DIMENSION = TASK_ID
TASK_ID_EQUAL_VOLUME_OPTION = "task_geometry__volume_equivalence_conversion__equal_volume_option_label"
QUERY_ID_CUBOID_TO_CYLINDER_LENGTH = "cuboid_to_cylinder_length"
QUERY_ID_CYLINDER_TO_CONE_HEIGHT = "cylinder_to_cone_height"
QUERY_ID_CONE_TO_CUBOID_HEIGHT = "cone_to_cuboid_height"
QUERY_ID_CONE_MATCHES_CYLINDER_OPTION = "cone_matches_cylinder_option"
QUERY_ID_CYLINDER_MATCHES_CONE_OPTION = "cylinder_matches_cone_option"
QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION = "cuboid_matches_cylinder_option"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    QUERY_ID_CUBOID_TO_CYLINDER_LENGTH,
    QUERY_ID_CYLINDER_TO_CONE_HEIGHT,
    QUERY_ID_CONE_TO_CUBOID_HEIGHT,
)
MISSING_DIMENSION_QUERY_IDS = SUPPORTED_QUERY_IDS
PROMPT_TASK_KEY = "missing_dimension_value_query"
TASK_BINDING = VolumeEquivalenceTaskBinding(
    prompt_task_key=PROMPT_TASK_KEY,
    annotation_keys=MISSING_DIMENSION_ANNOTATION_KEYS,
    answer_hint_key="answer_hint_integer",
    answer_type="integer",
    render_scene=render_missing_dimension_scene,
)

def _resolve_problem(
    *,
    selected_branch: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> ResolvedProblem:
    if str(selected_branch) == QUERY_ID_CUBOID_TO_CYLINDER_LENGTH:
        cases = CUBOID_TO_CYLINDER_LENGTH_CASES
        resolver = resolve_cuboid_to_cylinder_length
        branch_name = "cuboid_to_cylinder_length"
    elif str(selected_branch) == QUERY_ID_CYLINDER_TO_CONE_HEIGHT:
        cases = CYLINDER_TO_CONE_HEIGHT_CASES
        resolver = resolve_cylinder_to_cone_height
        branch_name = "cylinder_to_cone_height"
    elif str(selected_branch) == QUERY_ID_CONE_TO_CUBOID_HEIGHT:
        cases = CONE_TO_CUBOID_HEIGHT_CASES
        resolver = resolve_cone_to_cuboid_height
        branch_name = "cone_to_cuboid_height"
    else:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
    case, case_probabilities = select_conversion_case(
        branch_name=str(branch_name),
        cases=cases,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{selected_branch}.case",
    )
    problem = resolver(case)
    answer_support = [resolver(candidate).answer for candidate in cases]
    return bind_case_metadata(
        problem,
        case_probabilities=case_probabilities,
        answer_support=answer_support,
    )


@register_task
class GeometryVolumeEquivalenceConversionMissingDimensionValueTask:
    """Solve a missing dimension after converting one solid to an equal-volume target solid."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_branch, branch_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        problem = _resolve_problem(
            selected_branch=str(selected_branch),
            instance_seed=int(instance_seed),
            params=task_params,
        )
        parts = prepare_volume_equivalence_task_parts(
            public_identifier=TASK_ID,
            branch_key=str(selected_branch),
            branch_probabilities=branch_probabilities,
            problem=problem,
            binding=TASK_BINDING,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        return TaskOutput(
            prompt=parts.prompt,
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="bbox_map", value=dict(parts.annotation_value)),
            image=parts.image,
            image_id="img0",
            trace_payload=parts.trace_payload,
            task_versions=parts.task_versions,
            scene_id=parts.scene_id,
            query_id=str(selected_branch),
            prompt_variants=dict(parts.prompt_variants),
        )


__all__ = [
    "GeometryVolumeEquivalenceConversionMissingDimensionValueTask",
    "MISSING_DIMENSION_ANNOTATION_KEYS",
    "MISSING_DIMENSION_QUERY_IDS",
    "OPTION_ANNOTATION_KEYS",
    "QUERY_ID_CONE_MATCHES_CYLINDER_OPTION",
    "QUERY_ID_CONE_TO_CUBOID_HEIGHT",
    "QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION",
    "QUERY_ID_CUBOID_TO_CYLINDER_LENGTH",
    "QUERY_ID_CYLINDER_MATCHES_CONE_OPTION",
    "QUERY_ID_CYLINDER_TO_CONE_HEIGHT",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "TASK_ID_EQUAL_VOLUME_OPTION",
    "TASK_ID_MISSING_DIMENSION",
]
