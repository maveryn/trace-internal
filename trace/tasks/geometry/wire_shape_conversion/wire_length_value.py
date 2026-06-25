"""Compute the total length of wire around a shown shape."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import WIRE_LENGTH_ANNOTATION_KEYS, projected_annotation
from .shared.construction import (
    CIRCLE_WIRE_LENGTH_FROM_AREA_CASES,
    PARALLELOGRAM_WIRE_LENGTH_CASES,
    SOURCE_CIRCLE,
    SOURCE_PARALLELOGRAM,
    SOURCE_TRAPEZOID,
    TRAPEZOID_WIRE_LENGTH_CASES,
    bind_case_metadata,
    resolve_circle_wire_length_from_area,
    resolve_parallelogram_wire_length,
    resolve_trapezoid_wire_length,
)
from .shared.defaults import DOMAIN, SCENE_ID, load_wire_shape_defaults
from .shared.output import prepare_wire_shape_artifacts, trace_with_prompt_sections
from .shared.rendering import render_wire_length_scene
from .shared.sampling import select_case_by_answer_support
from .shared.state import RenderedScene, ResolvedProblem


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


def _wire_measurement_terms(problem: ResolvedProblem) -> dict[str, Any]:
    if problem.source_shape == SOURCE_TRAPEZOID:
        return {
            "shape_family": "isosceles_trapezoid",
            "operation": "sum_all_sides",
            "terms": [
                {"role": "top_base", "value": int(problem.source_values["top"])},
                {"role": "bottom_base", "value": int(problem.source_values["bottom"])},
                {"role": "equal_side", "value": int(problem.source_values["side"])},
                {"role": "equal_side", "value": int(problem.source_values["side"])},
            ],
        }
    if problem.source_shape == SOURCE_PARALLELOGRAM:
        return {
            "shape_family": "parallelogram",
            "operation": "twice_adjacent_side_sum",
            "terms": [
                {"role": "base", "value": int(problem.source_values["base"]), "multiplicity": 2},
                {"role": "side", "value": int(problem.source_values["side"]), "multiplicity": 2},
            ],
        }
    if problem.source_shape == SOURCE_CIRCLE:
        return {
            "shape_family": "circle",
            "operation": "circumference_from_area",
            "terms": [
                {"role": "area", "value": int(problem.source_values["area"])},
                {"role": "pi", "value": int(problem.source_values["pi"])},
                {"role": "radius", "value": int(problem.source_values["radius"])},
            ],
        }
    raise ValueError(f"unsupported source shape for {TASK_ID}: {problem.source_shape}")


def _query_params(
    *,
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "scene_id": SCENE_ID,
        "query_id": str(selected_branch),
        "query_id_probabilities": dict(branch_probabilities),
        "case_probabilities": dict(problem.case_probabilities),
        "answer_support_probabilities": dict(problem.answer_support_probabilities),
        "source_shape": str(problem.source_shape),
        "source_values": dict(problem.source_values),
        "requested_measurement": "total_wire_length",
        "source_wire_length": int(problem.source_values["wire_length"]),
        "wire_measurement_terms": _wire_measurement_terms(problem),
    }


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
    """Build the task-specific trace for the visible wire-length objective."""

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
        annotation_keys=WIRE_LENGTH_ANNOTATION_KEYS,
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
            "target_shape": "",
            "answer": int(problem.answer),
            "requested_measurement": "total_wire_length",
            "wire_measurement_terms": _wire_measurement_terms(problem),
        }
    )
    trace_payload["witness_symbolic"] = dict(params)
    trace_payload["projected_annotation"] = projected_annotation(dict(annotation_value))
    return trace_payload


@register_task
class GeometryWireShapeConversionWireLengthValueTask:
    """Compute the total length of wire around a shown shape."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    @staticmethod
    def _problem_for_branch(
        selected_branch: str,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
    ) -> ResolvedProblem:
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
        """Generate one visible-shape perimeter or circumference task."""

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
        _generation_defaults, render_defaults, prompt_defaults = load_wire_shape_defaults(TASK_ID)
        artifacts = prepare_wire_shape_artifacts(
            problem=problem,
            render_scene=render_wire_length_scene,
            annotation_keys=WIRE_LENGTH_ANNOTATION_KEYS,
            prompt_task_key=PROMPT_TASK_KEY,
            prompt_branch_key=str(selected_branch),
            answer=int(problem.answer),
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            render_defaults=render_defaults,
            prompt_defaults=prompt_defaults,
            random_namespace=TASK_ID,
        )
        return TaskOutput(
            prompt=str(artifacts.prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="bbox_map", value=dict(artifacts.annotation_value)),
            image=artifacts.image,
            image_id="img0",
            trace_payload=_trace_payload(
                selected_branch=str(selected_branch),
                branch_probabilities=branch_probabilities,
                problem=problem,
                rendered=artifacts.rendered,
                prompt_artifacts=artifacts.prompt_artifacts,
                annotation_value=artifacts.annotation_value,
                noise_meta=artifacts.noise_meta,
                image_size=artifacts.image.size,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_branch),
            prompt_variants=dict(artifacts.prompt_artifacts.prompt_variants),
        )
