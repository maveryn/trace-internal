"""Compute an external common tangent segment length."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import PairTangentValueProblem, complete_pair_tangent_value
from .shared.construction import (
    TANGENT_CASES,
    radii_for_center_order,
    select_larger_circle_side,
    select_tangent_case,
    select_tangent_side,
    tangent_answer_support,
)
from .shared.state import (
    ANNOTATION_KEYS,
    LARGER_CIRCLE_SIDES,
    SCENE_ID,
    TANGENT_SIDES,
    PairTangentDiagramSpec,
)

TASK_ID_COMMON_TANGENT_LENGTH = "task_geometry__circle_pair_tangents__common_tangent_length_value"
TASK_ID = TASK_ID_COMMON_TANGENT_LENGTH
QUERY_ID_COMMON_TANGENT_LENGTH = "external_common_tangent_length"
QUERY_ID = QUERY_ID_COMMON_TANGENT_LENGTH
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID_COMMON_TANGENT_LENGTH,)
_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)
_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS,
    task_id=TASK_ID,
)


def _build_common_tangent_length_problem(*, instance_seed: int, params: Mapping[str, Any]) -> PairTangentValueProblem:
    """Bind the tangent segment AB as the requested integer answer."""

    case, case_probabilities = select_tangent_case(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{QUERY_ID_COMMON_TANGENT_LENGTH}.tangent_case",
    )
    larger_side, larger_side_probabilities = select_larger_circle_side(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{QUERY_ID_COMMON_TANGENT_LENGTH}.larger_circle_side",
    )
    tangent_side, tangent_side_probabilities = select_tangent_side(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{QUERY_ID_COMMON_TANGENT_LENGTH}.tangent_side",
    )
    radius_o1, radius_o2 = radii_for_center_order(case, larger_side)
    answer = int(case.tangent_length)
    return PairTangentValueProblem(
        diagram_spec=PairTangentDiagramSpec(
            radius_o1=int(radius_o1),
            radius_o2=int(radius_o2),
            center_distance=int(case.center_distance),
            tangent_length=int(case.tangent_length),
            larger_circle_side=str(larger_side),
            tangent_side=str(tangent_side),
            center_segment_label=f"CD={int(case.center_distance)}",
            tangent_segment_label="AB=?",
            annotation_roles=ANNOTATION_KEYS,
        ),
        answer=int(answer),
        radius_o1=int(radius_o1),
        radius_o2=int(radius_o2),
        center_distance=int(case.center_distance),
        tangent_length=int(case.tangent_length),
        radius_difference=abs(int(radius_o2) - int(radius_o1)),
        larger_circle_side=str(larger_side),
        tangent_side=str(tangent_side),
        formula_family="external_common_tangent_length",
        formula="t^2 = d^2 - (r2-r1)^2",
        unknown_role="tangent_length",
        tangent_case_key=str(case.key),
        tangent_case_probabilities=dict(case_probabilities),
        larger_side_probabilities=dict(larger_side_probabilities),
        tangent_side_probabilities=dict(tangent_side_probabilities),
        answer_support_probabilities=tangent_answer_support(selected=answer, metric="tangent_length"),
    )


@register_task
class GeometryCirclePairTangentsCommonTangentLengthValueTask:
    """Compute the external common tangent segment length AB."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Select a tangent-length case and construct answer plus annotation."""

        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID_COMMON_TANGENT_LENGTH,
            task_id=TASK_ID,
        )
        problem = _build_common_tangent_length_problem(instance_seed=int(instance_seed), params=task_params)
        branch_name = str(selected_query)
        return complete_pair_tangent_value(
            task_id=TASK_ID,
            branch_name=branch_name,
            branch_probabilities=query_probabilities,
            problem=problem,
            prompt_defaults=_PROMPT_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            scene_defaults=_SCENE_DEFAULTS,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            style_namespace=f"{TASK_ID}.{branch_name}.render.scene",
        )


_TANGENT_CASES = TANGENT_CASES

__all__ = [
    "ANNOTATION_KEYS",
    "GeometryCirclePairTangentsCommonTangentLengthValueTask",
    "LARGER_CIRCLE_SIDES",
    "QUERY_ID",
    "QUERY_ID_COMMON_TANGENT_LENGTH",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "TANGENT_SIDES",
    "TASK_ID",
    "TASK_ID_COMMON_TANGENT_LENGTH",
    "_TANGENT_CASES",
]
