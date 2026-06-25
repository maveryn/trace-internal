"""Compute a missing dimension after reshaping the same wire into another shape."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id as choose_missing_query
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import MISSING_DIMENSION_ANNOTATION_KEYS, projected_annotation
from .shared.construction import (
    SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE_CASES,
    SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE_CASES,
    bind_case_metadata,
    resolve_same_wire_circle_to_trapezoid_side,
    resolve_same_wire_polygon_to_rectangle_side,
)
from .shared.defaults import DOMAIN, SCENE_ID, load_wire_shape_defaults
from .shared.output import conversion_problem_metadata, prepare_wire_shape_artifacts, trace_with_prompt_sections
from .shared.rendering import render_conversion_scene
from .shared.sampling import select_case_by_answer_support
from .shared.state import RenderedScene, ResolvedProblem


TASK_ID = "task_geometry__wire_shape_conversion__missing_dimension_value"
TASK_ID_MISSING_DIMENSION = TASK_ID
QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE = "same_wire_circle_to_trapezoid_side"
QUERY_ID_SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE = "same_wire_polygon_to_rectangle_side"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE,
    QUERY_ID_SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE,
)
MISSING_DIMENSION_QUERY_IDS = SUPPORTED_QUERY_IDS
PROMPT_TASK_KEY = "missing_dimension_value_query"


def _target_unknown_side_name(problem: ResolvedProblem) -> str:
    if "side" in problem.target_values:
        return "side"
    if "unknown_side" in problem.target_values:
        return "unknown_side"
    return "missing_side"


def _target_known_dimensions(problem: ResolvedProblem) -> dict[str, int]:
    unknown_side = _target_unknown_side_name(problem)
    return {
        str(role): int(value)
        for role, value in sorted(problem.target_values.items())
        if str(role) not in {unknown_side, "wire_length"}
    }


def _missing_dimension_equation(problem: ResolvedProblem) -> dict[str, Any]:
    unknown_side = _target_unknown_side_name(problem)
    return {
        "same_wire_constraint": "target_perimeter_equals_source_wire_length",
        "source_wire_length": int(problem.source_values["wire_length"]),
        "target_unknown_dimension": unknown_side,
        "target_known_dimensions": _target_known_dimensions(problem),
        "target_unknown_value": int(problem.answer),
    }


def _circle_to_trapezoid_problem(*, instance_seed: int, params: Mapping[str, Any]) -> ResolvedProblem:
    circle_case, circle_case_distribution, circle_answer_support = select_case_by_answer_support(
        case_label="same_wire_circle_to_trapezoid_side",
        cases=SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE_CASES,
        resolver=resolve_same_wire_circle_to_trapezoid_side,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.circle_to_trapezoid.case",
    )
    return bind_case_metadata(
        resolve_same_wire_circle_to_trapezoid_side(circle_case),
        case_probabilities=circle_case_distribution,
        support=circle_answer_support,
    )


def _polygon_to_rectangle_problem(*, instance_seed: int, params: Mapping[str, Any]) -> ResolvedProblem:
    polygon_case, polygon_case_distribution, rectangle_answer_support = select_case_by_answer_support(
        case_label="same_wire_polygon_to_rectangle_side",
        cases=SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE_CASES,
        resolver=resolve_same_wire_polygon_to_rectangle_side,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.polygon_to_rectangle.case",
    )
    return bind_case_metadata(
        resolve_same_wire_polygon_to_rectangle_side(polygon_case),
        case_probabilities=polygon_case_distribution,
        support=rectangle_answer_support,
    )


def _resolve_problem(
    *,
    selected_branch: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> ResolvedProblem:
    if str(selected_branch) == QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE:
        return _circle_to_trapezoid_problem(instance_seed=int(instance_seed), params=params)
    if str(selected_branch) == QUERY_ID_SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE:
        return _polygon_to_rectangle_problem(instance_seed=int(instance_seed), params=params)
    raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")


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
        "requested_target_dimension": _target_unknown_side_name(problem),
        "known_target_dimensions": _target_known_dimensions(problem),
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
    """Build the task-specific trace for the same-wire missing-side objective."""

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
        annotation_keys=MISSING_DIMENSION_ANNOTATION_KEYS,
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
            "requested_target_dimension": _target_unknown_side_name(problem),
            "missing_dimension_equation": _missing_dimension_equation(problem),
        }
    )
    trace_payload["witness_symbolic"] = dict(params)
    trace_payload["projected_annotation"] = projected_annotation(dict(annotation_value))
    return trace_payload


@register_task
class GeometryWireShapeConversionMissingDimensionValueTask:
    """Compute a missing dimension after reshaping the same wire into another shape."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one same-wire conversion task that asks for a missing target side."""

        branch_id, probability_by_branch, prepared_params = choose_missing_query(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        solved = _resolve_problem(
            selected_branch=str(branch_id),
            instance_seed=int(instance_seed),
            params=prepared_params,
        )
        _generation_defaults, render_defaults, prompt_defaults = load_wire_shape_defaults(TASK_ID)
        artifacts = prepare_wire_shape_artifacts(
            problem=solved,
            render_scene=render_conversion_scene,
            annotation_keys=MISSING_DIMENSION_ANNOTATION_KEYS,
            prompt_task_key=PROMPT_TASK_KEY,
            prompt_branch_key=str(branch_id),
            answer=int(solved.answer),
            instance_seed=int(instance_seed),
            params=prepared_params,
            max_attempts=int(max_attempts),
            render_defaults=render_defaults,
            prompt_defaults=prompt_defaults,
            random_namespace=TASK_ID,
        )
        return TaskOutput(
            prompt=str(artifacts.prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(solved.answer)),
            annotation_gt=TypedValue(type="bbox_map", value=dict(artifacts.annotation_value)),
            image=artifacts.image,
            image_id="img0",
            trace_payload=_trace_payload(
                selected_branch=str(branch_id),
                branch_probabilities=probability_by_branch,
                problem=solved,
                rendered=artifacts.rendered,
                prompt_artifacts=artifacts.prompt_artifacts,
                annotation_value=artifacts.annotation_value,
                noise_meta=artifacts.noise_meta,
                image_size=artifacts.image.size,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(branch_id),
            prompt_variants=dict(artifacts.prompt_artifacts.prompt_variants),
        )
