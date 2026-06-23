"""Count triangles of a requested type on graph paper."""

from __future__ import annotations

from typing import Any

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import (
    GraphPaperTaskPlan,
    _build_triangle_type_count,
    run_graph_paper_entry,
)

TASK_ID = "task_geometry__graph_paper__triangle_type_count"
QUERY_ID = "single"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


def _build_triangle_type_count_plan() -> GraphPaperTaskPlan:
    """Bind the triangle-type count objective."""

    return GraphPaperTaskPlan(
        builder=_build_triangle_type_count,
        prompt_key="triangle_type_count",
        salt="triangle_type_count_seed",
        target_field="triangle_type",
    )


@register_task
class GeometryGraphPaperTriangleTypeCountTask:
    """Count how many rendered triangles have the requested type."""

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
            plan=_build_triangle_type_count_plan(),
        )


__all__ = ["GeometryGraphPaperTriangleTypeCountTask"]
