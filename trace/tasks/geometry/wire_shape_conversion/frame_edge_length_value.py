"""Compute a frame edge length after reshaping a wire into a 3D frame."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id as choose_frame_query

from ._lifecycle import WireShapeTaskBinding, prepare_wire_shape_task_parts as assemble_frame_parts
from .shared.annotations import FRAME_EDGE_ANNOTATION_KEYS
from .shared.construction import (
    Case,
    PARALLELOGRAM_WIRE_TO_CUBOID_FRAME_CASES,
    TRAPEZOID_WIRE_TO_CUBE_FRAME_CASES,
    bind_case_metadata,
    resolve_parallelogram_wire_to_cuboid_frame,
    resolve_trapezoid_wire_to_cube_frame,
)
from .shared.defaults import DOMAIN
from .shared.rendering import render_conversion_scene
from .shared.sampling import select_case_by_answer_support
from .shared.state import ResolvedProblem


TASK_ID = "task_geometry__wire_shape_conversion__frame_edge_length_value"
TASK_ID_FRAME_EDGE_LENGTH = TASK_ID
QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME = "trapezoid_wire_to_cube_frame"
QUERY_ID_PARALLELOGRAM_WIRE_TO_CUBOID_FRAME = "parallelogram_wire_to_cuboid_frame"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME,
    QUERY_ID_PARALLELOGRAM_WIRE_TO_CUBOID_FRAME,
)
FRAME_EDGE_LENGTH_QUERY_IDS = SUPPORTED_QUERY_IDS
PROMPT_TASK_KEY = "frame_edge_length_value_query"
FRAME_TASK_BINDING = WireShapeTaskBinding(
    prompt_task_key=PROMPT_TASK_KEY,
    annotation_keys=FRAME_EDGE_ANNOTATION_KEYS,
    answer_type="integer",
    render_scene=render_conversion_scene,
)


@dataclass(frozen=True)
class _FrameBranchProgram:
    cases: Sequence[Case]
    resolver: Callable[[Case], ResolvedProblem]
    case_label: str


def _frame_branch_program(selected_branch: str) -> _FrameBranchProgram:
    if str(selected_branch) == QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME:
        return _FrameBranchProgram(
            cases=TRAPEZOID_WIRE_TO_CUBE_FRAME_CASES,
            resolver=resolve_trapezoid_wire_to_cube_frame,
            case_label="trapezoid_wire_to_cube_frame",
        )
    if str(selected_branch) == QUERY_ID_PARALLELOGRAM_WIRE_TO_CUBOID_FRAME:
        return _FrameBranchProgram(
            cases=PARALLELOGRAM_WIRE_TO_CUBOID_FRAME_CASES,
            resolver=resolve_parallelogram_wire_to_cuboid_frame,
            case_label="parallelogram_wire_to_cuboid_frame",
        )
    raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")


def _resolve_problem(
    *,
    selected_branch: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> ResolvedProblem:
    program = _frame_branch_program(str(selected_branch))
    case, case_probabilities, support = select_case_by_answer_support(
        case_label=program.case_label,
        cases=program.cases,
        resolver=program.resolver,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{selected_branch}.case",
    )
    return bind_case_metadata(
        program.resolver(case),
        case_probabilities=case_probabilities,
        support=support,
    )


@register_task
class GeometryWireShapeConversionFrameEdgeLengthValueTask:
    """Compute a frame edge length after reshaping a wire into a 3D frame."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query, query_distribution, effective_params = choose_frame_query(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        frame_problem = _resolve_problem(
            selected_branch=str(selected_query),
            instance_seed=int(instance_seed),
            params=effective_params,
        )
        frame_parts = assemble_frame_parts(
            public_identifier=TASK_ID,
            branch_key=str(selected_query),
            branch_probabilities=query_distribution,
            problem=frame_problem,
            binding=FRAME_TASK_BINDING,
            instance_seed=int(instance_seed),
            params=effective_params,
            max_attempts=int(max_attempts),
        )
        answer_value = TypedValue(type="integer", value=int(frame_problem.answer))
        annotation_value = TypedValue(type="bbox_map", value=dict(frame_parts.annotation_value))
        return TaskOutput(
            frame_parts.prompt,
            answer_value,
            annotation_value,
            frame_parts.image,
            "img0",
            frame_parts.trace_payload,
            frame_parts.task_versions,
            frame_parts.scene_id,
            str(selected_query),
            dict(frame_parts.prompt_variants),
        )
