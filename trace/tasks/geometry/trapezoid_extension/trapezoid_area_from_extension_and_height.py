"""Compute trapezoid area from an extension construction and height."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from ._lifecycle import TrapezoidExtensionObjectivePlan, run_trapezoid_extension_public_entry
from .shared.measurements import area_case_pool, case_trace_values, fmt_measure, trapezoid_area
from .shared.rendering import render_trapezoid_extension_scene
from .shared.sampling import choose_case_by_answer
from .shared.state import DOMAIN, LabelSpec, TrapezoidExtensionProblem


TASK_ID = "task_geometry__trapezoid_extension__trapezoid_area_from_extension_and_height"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
TASK_PROMPT_KEY = "trapezoid_area_from_extension_and_height_query"

_CASE_POOL = area_case_pool()


def _prepare_area_from_extension_and_height(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_query: str,
    branch_probabilities: Mapping[str, float],
) -> TrapezoidExtensionObjectivePlan:
    """Bind the area formula where the lower base is derived from the extension."""

    if str(selected_query) != SINGLE_QUERY_ID:
        raise ValueError(f"unsupported query branch for {TASK_ID}: {selected_query}")
    case, answer_probabilities = choose_case_by_answer(
        cases=_CASE_POOL,
        answer_fn=trapezoid_area,
        params=params,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    answer = trapezoid_area(case)
    trace_values = {
        "formula_family": "trapezoid_area_from_extension_and_height",
        "formula": "trapezoid area = h * (AB + DC) / 2, with DC = AB + BE",
        "target_support_probabilities": dict(answer_probabilities),
        "query_id_probabilities": dict(branch_probabilities),
        **case_trace_values(case),
    }
    problem = TrapezoidExtensionProblem(
        target_text="trapezoid area=?",
        target_position_key="target_area",
        answer=float(answer),
        case=case,
        formula_family="trapezoid_area_from_extension_and_height",
        formula_text="trapezoid area = h * (AB + DC) / 2, with DC = AB + BE",
        reasoning_steps=2,
        support_labels=(
            LabelSpec("extension", f"BE={fmt_measure(case.extension)}", "extension"),
        ),
        target_support_probabilities=dict(answer_probabilities),
    )
    return TrapezoidExtensionObjectivePlan(
        prompt_key=TASK_PROMPT_KEY,
        problem=problem,
        render_scene=render_trapezoid_extension_scene,
        answer_value=float(answer),
        query_params=trace_values,
        trace_values=trace_values,
    )


@register_task
class GeometryTrapezoidAreaFromExtensionAndHeightTask:
    """Compute trapezoid area from the extension and height."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SINGLE_QUERY_ID
    prepare_objective = staticmethod(_prepare_area_from_extension_and_height)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_trapezoid_extension_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryTrapezoidAreaFromExtensionAndHeightTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
