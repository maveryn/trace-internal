"""Compute a missing dimension after reshaping the same wire into another shape."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id as choose_missing_query

from ._lifecycle import WireShapeTaskBinding, prepare_wire_shape_task_parts as compose_missing_parts
from .shared.annotations import MISSING_DIMENSION_ANNOTATION_KEYS
from .shared.construction import (
    SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE_CASES,
    SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE_CASES,
    bind_case_metadata,
    resolve_same_wire_circle_to_trapezoid_side,
    resolve_same_wire_polygon_to_rectangle_side,
)
from .shared.defaults import DOMAIN
from .shared.rendering import render_conversion_scene
from .shared.sampling import select_case_by_answer_support
from .shared.state import ResolvedProblem


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
MISSING_TASK_BINDING = WireShapeTaskBinding(
    prompt_task_key=PROMPT_TASK_KEY,
    annotation_keys=MISSING_DIMENSION_ANNOTATION_KEYS,
    answer_type="integer",
    render_scene=render_conversion_scene,
)


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


@register_task
class GeometryWireShapeConversionMissingDimensionValueTask:
    """Compute a missing dimension after reshaping the same wire into another shape."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
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
        packet = compose_missing_parts(
            public_identifier=TASK_ID,
            branch_key=str(branch_id),
            branch_probabilities=probability_by_branch,
            problem=solved,
            binding=MISSING_TASK_BINDING,
            instance_seed=int(instance_seed),
            params=prepared_params,
            max_attempts=int(max_attempts),
        )
        output_fields = {
            "prompt": packet.prompt,
            "answer_gt": TypedValue(type="integer", value=int(solved.answer)),
            "annotation_gt": TypedValue(type="bbox_map", value=dict(packet.annotation_value)),
            "image": packet.image,
            "image_id": "img0",
            "trace_payload": packet.trace_payload,
            "task_versions": packet.task_versions,
            "scene_id": packet.scene_id,
            "query_id": str(branch_id),
            "prompt_variants": dict(packet.prompt_variants),
        }
        return TaskOutput(**output_fields)
