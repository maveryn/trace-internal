"""Measure one angle drawn on graph paper."""

from __future__ import annotations

from typing import Any

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import GraphPaperTaskPlan, _build_angle_value, run_graph_paper_entry

TASK_ID = "task_geometry__graph_paper__angle_value"
QUERY_ID = "single"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


def _build_angle_value_plan() -> GraphPaperTaskPlan:
    """Bind the angle-measurement objective."""

    return GraphPaperTaskPlan(
        builder=_build_angle_value,
        prompt_key="angle_value",
        salt="angle_value_seed",
        value_param="angle_value",
    )


@register_task
class GeometryGraphPaperAngleValueTask:
    """Measure one rendered angle in degrees."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(
        self, instance_seed: int, *, params: dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        return run_graph_paper_entry(
            self,
            instance_seed,
            params=params,
            max_attempts=max_attempts,
            plan=_build_angle_value_plan(),
        )


__all__ = ["GeometryGraphPaperAngleValueTask"]
