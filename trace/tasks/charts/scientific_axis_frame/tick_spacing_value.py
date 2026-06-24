"""Compute spacing between adjacent numeric tick labels in a scientific plot frame."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trace.tasks.charts.scientific_axis_frame._lifecycle import (
    AxisFrameTaskPlan,
    run_axis_frame_lifecycle,
)
from trace.tasks.charts.scientific_axis_frame.shared.prompts import dynamic_slots
from trace.tasks.charts.scientific_axis_frame.shared.sampling import build_tick_spacing_dataset
from trace.tasks.charts.scientific_axis_frame.shared.state import DOMAIN
from trace.tasks.registry import register_task


TASK_ID = "task_charts__scientific_axis_frame__tick_spacing_value"
PROGRAM_CODE = (
    "difference(next_adjacent_tick(axis), first_adjacent_tick(axis)); "
    "output=integer_value; annotation=bbox_map(first_tick,next_tick); "
    "scene=scientific_axis_frame; scope=tick_spacing_value"
)
TICK_SPACING_QUERY_IDS = (
    "x_tick_spacing_value",
    "y_tick_spacing_value",
)
REASONING_LOAD = 0.38
DEFAULT_QUERY_ID = TICK_SPACING_QUERY_IDS[0]


def _build_tick_spacing_plan(
    params: Mapping[str, Any],
    instance_seed: int,
    selected_query_id: str,
    query_probabilities: Mapping[str, float],
) -> AxisFrameTaskPlan:
    """Bind one public query id to an adjacent-tick spacing objective."""

    if str(selected_query_id) not in set(TICK_SPACING_QUERY_IDS):
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_query_id}")
    axis = str(selected_query_id)[0]
    dataset = build_tick_spacing_dataset(
        params=params,
        instance_seed=int(instance_seed),
        axis=str(axis),
    )
    return AxisFrameTaskPlan(
        dataset=dataset,
        params=dict(params),
        prompt_key=str(selected_query_id),
        dynamic_slots=dynamic_slots(axis_name=str(dataset.binding.trace["axis_name"])),
        question_format="scientific_axis_frame",
        program_code=PROGRAM_CODE,
        query_params={
            "axis": str(axis),
            "query_id_probabilities": dict(query_probabilities),
        },
        reasoning_load=REASONING_LOAD,
        highlight_tick_keys=tuple(str(value) for value in dataset.binding.annotation_roles.values()),
    )


@register_task
class ChartsScientificAxisFrameTickSpacingValueTask:
    """Compute spacing between highlighted adjacent numeric tick labels."""

    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = "tick_spacing_value"
    supported_query_ids = TICK_SPACING_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        return run_axis_frame_lifecycle(
            task=self,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
            default_query_id=DEFAULT_QUERY_ID,
            build_plan=_build_tick_spacing_plan,
        )


__all__ = [
    "ChartsScientificAxisFrameTickSpacingValueTask",
    "TICK_SPACING_QUERY_IDS",
]
