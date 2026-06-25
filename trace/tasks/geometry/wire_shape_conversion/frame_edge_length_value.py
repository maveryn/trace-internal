"""Compute a frame edge length after reshaping a wire into a 3D frame."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id as choose_frame_query
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import FRAME_EDGE_ANNOTATION_KEYS, projected_annotation
from .shared.construction import (
    Case,
    PARALLELOGRAM_WIRE_TO_CUBOID_FRAME_CASES,
    TRAPEZOID_WIRE_TO_CUBE_FRAME_CASES,
    bind_case_metadata,
    resolve_parallelogram_wire_to_cuboid_frame,
    resolve_trapezoid_wire_to_cube_frame,
)
from .shared.defaults import DOMAIN, SCENE_ID, load_wire_shape_defaults
from .shared.output import (
    PreparedWireShapeArtifacts,
    conversion_problem_metadata,
    prepare_wire_shape_artifacts,
    trace_with_prompt_sections,
)
from .shared.rendering import render_conversion_scene
from .shared.sampling import select_case_by_answer_support
from .shared.state import RenderedScene, ResolvedProblem


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


@dataclass(frozen=True)
class _FrameBranchProgram:
    cases: Sequence[Case]
    resolver: Callable[[Case], ResolvedProblem]
    case_label: str


@dataclass(frozen=True)
class _FrameTaskRun:
    selected_query: str
    query_distribution: dict[str, float]
    effective_params: dict[str, Any]
    problem: ResolvedProblem
    artifacts: PreparedWireShapeArtifacts


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


def _requested_frame_edge(problem: ResolvedProblem) -> str:
    if "edge" in problem.target_values:
        return "edge"
    if "height" in problem.target_values:
        return "height"
    return "missing_edge"


def _known_frame_dimensions(problem: ResolvedProblem) -> dict[str, int]:
    requested_edge = _requested_frame_edge(problem)
    return {
        str(role): int(value)
        for role, value in sorted(problem.target_values.items())
        if str(role) not in {requested_edge, "wire_length", "frame_edge_count"}
    }


def _frame_edge_equation(problem: ResolvedProblem) -> dict[str, Any]:
    requested_edge = _requested_frame_edge(problem)
    return {
        "same_wire_constraint": "frame_total_edge_length_equals_source_wire_length",
        "source_wire_length": int(problem.source_values["wire_length"]),
        "target_frame_shape": str(problem.target_shape),
        "target_requested_edge": requested_edge,
        "target_known_dimensions": _known_frame_dimensions(problem),
        "target_edge_count": int(problem.target_values.get("frame_edge_count", 12)),
        "target_requested_value": int(problem.answer),
    }


def _query_params(
    *,
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
) -> dict[str, Any]:
    params = {
        "task_id": TASK_ID,
        "scene_id": SCENE_ID,
        "query_id": str(selected_branch),
        "query_id_probabilities": dict(branch_probabilities),
        "requested_frame_edge": _requested_frame_edge(problem),
        "target_frame_edge_count": int(problem.target_values.get("frame_edge_count", 12)),
        "known_frame_dimensions": _known_frame_dimensions(problem),
    }
    params.update(conversion_problem_metadata(problem))
    return params


def _trace_payload(
    *,
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
    rendered: RenderedScene,
    prompt_artifacts: Any,
    annotation_value: Mapping[str, list[float]],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
) -> dict[str, Any]:
    """Build the task-specific trace for the wire-to-frame edge objective."""

    params = _query_params(
        selected_branch=str(selected_branch),
        branch_probabilities=branch_probabilities,
        problem=problem,
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_branch),
        params=params,
    )
    query_spec["task_id"] = TASK_ID
    query_spec["scene_id"] = SCENE_ID
    trace_payload = trace_with_prompt_sections(
        problem=problem,
        rendered=rendered,
        annotation_keys=FRAME_EDGE_ANNOTATION_KEYS,
        noise_meta=noise_meta,
        image_size=image_size,
        prompt_artifacts=prompt_artifacts,
    )
    trace_payload["query_spec"] = query_spec
    trace_payload["scene_ir"].update({"task_id": TASK_ID, "query_id": str(selected_branch)})
    trace_payload["render_spec"].update({"task_id": TASK_ID, "query_id": str(selected_branch)})
    trace_payload["render_map"] = {"query_id": str(selected_branch), **dict(trace_payload["render_map"])}
    trace_payload["execution_trace"].update(
        {
            "task_id": TASK_ID,
            "query_id": str(selected_branch),
            "answer": int(problem.answer),
            "requested_frame_edge": _requested_frame_edge(problem),
            "target_frame_edge_count": int(problem.target_values.get("frame_edge_count", 12)),
            "frame_edge_equation": _frame_edge_equation(problem),
        }
    )
    trace_payload["witness_symbolic"] = dict(params)
    trace_payload["projected_annotation"] = projected_annotation(dict(annotation_value))
    return trace_payload


def _prepare_frame_run(
    *,
    instance_seed: int,
    params: dict[str, Any],
    max_attempts: int,
) -> _FrameTaskRun:
    """Resolve the frame objective before binding answer and annotation."""

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
    _generation_defaults, render_defaults, prompt_defaults = load_wire_shape_defaults(TASK_ID)
    artifacts = prepare_wire_shape_artifacts(
        problem=frame_problem,
        render_scene=render_conversion_scene,
        annotation_keys=FRAME_EDGE_ANNOTATION_KEYS,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_branch_key=str(selected_query),
        answer=int(frame_problem.answer),
        instance_seed=int(instance_seed),
        params=effective_params,
        max_attempts=int(max_attempts),
        render_defaults=render_defaults,
        prompt_defaults=prompt_defaults,
        random_namespace=TASK_ID,
    )
    return _FrameTaskRun(
        selected_query=str(selected_query),
        query_distribution=dict(query_distribution),
        effective_params=dict(effective_params),
        problem=frame_problem,
        artifacts=artifacts,
    )


def _frame_result(run: _FrameTaskRun) -> TaskOutput:
    """Bind the frame answer, annotation, and trace into the final task output."""

    return TaskOutput(
        prompt=str(run.artifacts.prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(run.problem.answer)),
        annotation_gt=TypedValue(type="bbox_map", value=dict(run.artifacts.annotation_value)),
        image=run.artifacts.image,
        image_id="img0",
        trace_payload=_trace_payload(
            selected_branch=str(run.selected_query),
            branch_probabilities=run.query_distribution,
            problem=run.problem,
            rendered=run.artifacts.rendered,
            prompt_artifacts=run.artifacts.prompt_artifacts,
            annotation_value=run.artifacts.annotation_value,
            noise_meta=run.artifacts.noise_meta,
            image_size=run.artifacts.image.size,
        ),
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(run.selected_query),
        prompt_variants=dict(run.artifacts.prompt_artifacts.prompt_variants),
    )


@register_task
class GeometryWireShapeConversionFrameEdgeLengthValueTask:
    """Compute a frame edge length after reshaping a wire into a 3D frame."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one same-wire conversion task that asks for a target frame edge."""

        run = _prepare_frame_run(
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
        return _frame_result(run)
