"""Cyclic quadrilateral angle circle-theorem task."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import run_integer_circle_theorem_task
from .shared.construction import (
    _build_cyclic_exterior_angle_scene,
    _build_cyclic_opposite_angle_scene,
)
from .shared.state import CYCLIC_QUADRILATERAL_ANGLE_SUPPORT, CircleTheoremProblem

TASK_ID = "task_geometry__circle_theorem__cyclic_quadrilateral_angle_value"
SUPPORTED_QUERY_IDS = (
    "opposite_angle_supplement",
    "exterior_angle_from_opposite_interior",
)
ANSWER_SUPPORT = CYCLIC_QUADRILATERAL_ANGLE_SUPPORT


def _bind_problem(
    _instance_seed: int,
    _params: Mapping[str, Any],
    selected_query: str,
    target_answer: int,
    target_probabilities: Mapping[str, float],
):
    """Bind the chosen cyclic-angle theorem branch to its construction."""

    problem = CircleTheoremProblem(
        target_answer=int(target_answer),
        target_answer_probabilities=dict(target_probabilities),
    )
    if str(selected_query) == "opposite_angle_supplement":
        return problem, {}, lambda rng, bound: _build_cyclic_opposite_angle_scene(rng, problem=bound)
    if str(selected_query) == "exterior_angle_from_opposite_interior":
        return problem, {}, lambda rng, bound: _build_cyclic_exterior_angle_scene(rng, problem=bound)
    raise ValueError(f"unsupported circle theorem query for this task: {selected_query}")


@register_task
class GeometryCircleCyclicQuadrilateralAngleValueTask:
    """Solve a cyclic quadrilateral angle."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        return run_integer_circle_theorem_task(
            task_id=TASK_ID,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            supported_query_ids=SUPPORTED_QUERY_IDS,
            answer_support=ANSWER_SUPPORT,
            bind_problem=_bind_problem,
        )


__all__ = ["GeometryCircleCyclicQuadrilateralAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
