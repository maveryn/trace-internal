"""Compute the center distance from an external common tangent."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import (
    PairTangentValueProblem,
    build_pair_tangent_value_problem,
    complete_pair_tangent_value,
)
from .shared.construction import TANGENT_CASES, select_tangent_layout
from .shared.state import ANNOTATION_KEYS, LARGER_CIRCLE_SIDES, SCENE_ID, TANGENT_SIDES

TASK_ID_CENTER_DISTANCE = "task_geometry__circle_pair_tangents__center_distance_value"
TASK_ID = TASK_ID_CENTER_DISTANCE
QUERY_ID_CENTER_DISTANCE = "external_common_tangent_center_distance"
QUERY_ID = QUERY_ID_CENTER_DISTANCE
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID_CENTER_DISTANCE,)
_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)
_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS,
    task_id=TASK_ID,
)


def _center_distance_sampling_namespace() -> str:
    """Return the deterministic sampling namespace for center-distance cases."""

    return f"{TASK_ID}.{QUERY_ID_CENTER_DISTANCE}"


def _build_center_distance_problem(*, instance_seed: int, params: Mapping[str, Any]) -> PairTangentValueProblem:
    """Bind the center segment CD as the requested integer answer."""

    layout = select_tangent_layout(
        instance_seed=int(instance_seed),
        params=params,
        sampling_namespace=_center_distance_sampling_namespace(),
    )
    return build_pair_tangent_value_problem(
        layout=layout,
        answer=int(layout.case.center_distance),
        center_segment_label="CD=?",
        tangent_segment_label=f"AB={int(layout.case.tangent_length)}",
        formula_family="external_common_tangent_center_distance",
        formula="d^2 = t^2 + (r2-r1)^2",
        unknown_role="center_distance",
        answer_metric="center_distance",
    )


@register_task
class GeometryCirclePairTangentsCenterDistanceValueTask:
    """Compute the center-to-center distance CD."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Select a center-distance case and construct answer plus annotation."""

        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID_CENTER_DISTANCE,
            task_id=TASK_ID,
        )
        problem = _build_center_distance_problem(instance_seed=int(instance_seed), params=task_params)
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
    "GeometryCirclePairTangentsCenterDistanceValueTask",
    "LARGER_CIRCLE_SIDES",
    "QUERY_ID",
    "QUERY_ID_CENTER_DISTANCE",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "TANGENT_SIDES",
    "TASK_ID",
    "TASK_ID_CENTER_DISTANCE",
    "_TANGENT_CASES",
]
