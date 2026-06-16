"""Compute the folded cone base radius from a sector net."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import prepare_cone_net_task_parts
from .shared.defaults import DOMAIN, SCENE_ID
from .shared.measurements import (
    base_radius_from_sector,
    base_radius_support_values,
    cone_net_diagram_spec,
)
from .shared.sampling import CONE_NET_CASES, resolve_cone_net_case

TASK_ID = "task_geometry__cone_net__base_radius_from_sector_angle"
INTERNAL_QUERY_ID = "base_radius_from_sector_angle"
SUPPORTED_QUERY_IDS = ("single",)
BASE_RADIUS_ANNOTATION_ROLES = ("S", "P", "Q", "C", "R")
BASE_RADIUS_TARGET_LABEL = "r=?"
BASE_RADIUS_LABEL_ANCHOR = "radius_segment"


@dataclass(frozen=True)
class _BaseRadiusRequest:
    """Task-owned radius answer binding before shared rendering."""

    selected_query: str
    query_probabilities: Mapping[str, float]
    params: Mapping[str, Any]
    case_index: int
    answer_value: float
    answer_support: tuple[float, ...]
    diagram_spec: Any


def _radius_public_branch(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Mapping[str, float], Mapping[str, Any]]:
    """Resolve the public no-branch query while preserving review overrides."""

    selected_query, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id="single",
        task_id=TASK_ID,
    )
    return str(selected_query), dict(query_probabilities), dict(task_params)


def _base_radius_request(*, instance_seed: int, params: Mapping[str, Any]) -> _BaseRadiusRequest:
    """Select a radius answer first, then bind one compatible cone net."""

    selected_query, query_probabilities, task_params = _radius_public_branch(
        instance_seed=int(instance_seed),
        params=params,
    )
    case, case_index = resolve_cone_net_case(
        target_measure="base_radius",
        instance_seed=int(instance_seed),
        params=task_params,
        namespace=f"{TASK_ID}.{INTERNAL_QUERY_ID}.case",
    )
    radius_value = float(base_radius_from_sector(case))
    diagram_spec = cone_net_diagram_spec(
        case,
        answer=radius_value,
        target_measure="base_radius",
        target_label=BASE_RADIUS_TARGET_LABEL,
        target_label_anchor=BASE_RADIUS_LABEL_ANCHOR,
        annotation_roles=BASE_RADIUS_ANNOTATION_ROLES,
        formula_family=INTERNAL_QUERY_ID,
        reasoning_steps=1,
    )
    return _BaseRadiusRequest(
        selected_query=selected_query,
        query_probabilities=query_probabilities,
        params=task_params,
        case_index=int(case_index),
        answer_value=radius_value,
        answer_support=base_radius_support_values(CONE_NET_CASES),
        diagram_spec=diagram_spec,
    )


@register_task
class GeometryConeNetBaseRadiusFromSectorAngleTask:
    """Return the cone base radius implied by the arc length of the sector net."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Build the radius-specific answer and annotation from one rendered trace."""

        request = _base_radius_request(
            instance_seed=int(instance_seed),
            params=params,
        )
        parts = prepare_cone_net_task_parts(
            public_identifier=TASK_ID,
            internal_prompt_key=INTERNAL_QUERY_ID,
            selected_query=request.selected_query,
            query_probabilities=request.query_probabilities,
            spec=request.diagram_spec,
            case_index=request.case_index,
            support_values=request.answer_support,
            instance_seed=int(instance_seed),
            params=request.params,
            max_attempts=int(max_attempts),
        )
        radius_answer = TypedValue(type="number", value=request.answer_value)
        radius_annotation = TypedValue(
            type=parts.annotation_artifacts.annotation_type,
            value=parts.annotation_artifacts.value,
        )
        prompt_variant_map = dict(parts.prompt_variants)
        return TaskOutput(
            prompt=parts.prompt,
            answer_gt=radius_answer,
            annotation_gt=radius_annotation,
            image=parts.image,
            image_id="img0",
            trace_payload=parts.trace_payload,
            task_versions=parts.task_versions,
            scene_id=parts.scene_id,
            query_id=request.selected_query,
            prompt_variants=prompt_variant_map,
        )
