"""Compute the folded cone height from a sector net."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import prepare_cone_net_task_parts
from .shared.defaults import DOMAIN
from .shared.measurements import (
    cone_net_diagram_spec,
    height_from_sector,
    height_support_values,
)
from .shared.sampling import CONE_NET_CASES, resolve_cone_net_case

TASK_ID = "task_geometry__cone_net__height_from_sector_angle"
INTERNAL_QUERY_ID = "height_from_sector_angle"
SUPPORTED_QUERY_IDS = ("single",)
HEIGHT_TARGET_MEASURE = "height"
HEIGHT_ANNOTATION_ROLES = ("S", "P", "Q", "C", "A")
HEIGHT_PROMPT_LABEL = "h=?"
HEIGHT_PROMPT_ANCHOR = "height_segment"


def _public_query_state(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[str, dict[str, float], dict[str, Any]]:
    """Resolve the public single-query branch for the height objective."""

    selected_query, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id="single",
        task_id=TASK_ID,
    )
    return str(selected_query), dict(query_probabilities), dict(task_params)


def _height_diagram_spec(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[Any, int, float]:
    """Select a height answer first and encode the matching sector-net diagram."""

    case, case_index = resolve_cone_net_case(
        target_measure=HEIGHT_TARGET_MEASURE,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{INTERNAL_QUERY_ID}.case",
    )
    height_value = float(height_from_sector(case))
    if height_value <= 0:
        raise ValueError("cone-net height objective requires a positive folded height")
    diagram_spec = cone_net_diagram_spec(
        case,
        answer=height_value,
        target_measure=HEIGHT_TARGET_MEASURE,
        target_label=HEIGHT_PROMPT_LABEL,
        target_label_anchor=HEIGHT_PROMPT_ANCHOR,
        annotation_roles=HEIGHT_ANNOTATION_ROLES,
        formula_family=INTERNAL_QUERY_ID,
        reasoning_steps=2,
    )
    return diagram_spec, int(case_index), height_value


@register_task
class GeometryConeNetHeightFromSectorAngleTask:
    """Return the cone height after deriving radius from the sector arc."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Bind the two-step height computation and its rendered annotation."""

        selected_query, query_probabilities, task_params = _public_query_state(
            instance_seed=int(instance_seed),
            params=params,
        )
        diagram_spec, case_index, height_value = _height_diagram_spec(
            instance_seed=int(instance_seed),
            params=task_params,
        )
        support_values = height_support_values(CONE_NET_CASES)
        parts = prepare_cone_net_task_parts(
            public_identifier=TASK_ID,
            internal_prompt_key=INTERNAL_QUERY_ID,
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            spec=diagram_spec,
            case_index=int(case_index),
            support_values=support_values,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        annotation_value = parts.annotation_artifacts.value
        return TaskOutput(
            parts.prompt,
            TypedValue(type="number", value=height_value),
            TypedValue(type=parts.annotation_artifacts.annotation_type, value=annotation_value),
            parts.image,
            "img0",
            parts.trace_payload,
            parts.task_versions,
            parts.scene_id,
            str(selected_query),
            dict(parts.prompt_variants),
        )
