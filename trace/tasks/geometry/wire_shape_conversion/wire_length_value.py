"""Compute the total length of wire around a shown shape."""

from __future__ import annotations

from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import WireShapeTaskBinding, prepare_wire_shape_task_parts
from .shared.annotations import WIRE_LENGTH_ANNOTATION_KEYS
from .shared.construction import (
    CIRCLE_WIRE_LENGTH_FROM_AREA_CASES,
    PARALLELOGRAM_WIRE_LENGTH_CASES,
    TRAPEZOID_WIRE_LENGTH_CASES,
    bind_case_metadata,
    resolve_circle_wire_length_from_area,
    resolve_parallelogram_wire_length,
    resolve_trapezoid_wire_length,
)
from .shared.defaults import DOMAIN
from .shared.rendering import render_wire_length_scene
from .shared.sampling import select_case_by_answer_support


TASK_ID = "task_geometry__wire_shape_conversion__wire_length_value"
TASK_ID_WIRE_LENGTH = TASK_ID
QUERY_ID_TRAPEZOID_WIRE_LENGTH = "trapezoid_wire_length"
QUERY_ID_PARALLELOGRAM_WIRE_LENGTH = "parallelogram_wire_length"
QUERY_ID_CIRCLE_WIRE_LENGTH_FROM_AREA = "circle_wire_length_from_area"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    QUERY_ID_TRAPEZOID_WIRE_LENGTH,
    QUERY_ID_PARALLELOGRAM_WIRE_LENGTH,
    QUERY_ID_CIRCLE_WIRE_LENGTH_FROM_AREA,
)
WIRE_LENGTH_QUERY_IDS = SUPPORTED_QUERY_IDS
PROMPT_TASK_KEY = "wire_length_value_query"
WIRE_TASK_BINDING = WireShapeTaskBinding(
    prompt_task_key=PROMPT_TASK_KEY,
    annotation_keys=WIRE_LENGTH_ANNOTATION_KEYS,
    answer_type="integer",
    render_scene=render_wire_length_scene,
)

@register_task
class GeometryWireShapeConversionWireLengthValueTask:
    """Compute the total length of wire around a shown shape."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    @staticmethod
    def _problem_for_branch(selected_branch: str, *, instance_seed: int, params: dict[str, Any]):
        match str(selected_branch):
            case "trapezoid_wire_length":
                resolver = resolve_trapezoid_wire_length
                cases = TRAPEZOID_WIRE_LENGTH_CASES
                case_label = "trapezoid_wire_length"
            case "parallelogram_wire_length":
                resolver = resolve_parallelogram_wire_length
                cases = PARALLELOGRAM_WIRE_LENGTH_CASES
                case_label = "parallelogram_wire_length"
            case "circle_wire_length_from_area":
                resolver = resolve_circle_wire_length_from_area
                cases = CIRCLE_WIRE_LENGTH_FROM_AREA_CASES
                case_label = "circle_wire_length_from_area"
            case _:
                raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
        case_value, case_probabilities, support = select_case_by_answer_support(
            case_label=case_label,
            cases=cases,
            resolver=resolver,
            instance_seed=int(instance_seed),
            params=params,
            namespace=f"{TASK_ID}.{selected_branch}.case",
        )
        return bind_case_metadata(
            resolver(case_value),
            case_probabilities=case_probabilities,
            support=support,
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_branch, branch_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        problem = self._problem_for_branch(
            str(selected_branch),
            instance_seed=int(instance_seed),
            params=task_params,
        )
        parts = prepare_wire_shape_task_parts(
            public_identifier=TASK_ID,
            branch_key=str(selected_branch),
            branch_probabilities=branch_probabilities,
            problem=problem,
            binding=WIRE_TASK_BINDING,
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
