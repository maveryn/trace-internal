"""Count quadrilaterals of a requested type on graph paper."""

from __future__ import annotations

from typing import Any

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import (
    GraphPaperTaskPlan,
    _build_quadrilateral_type_count,
    run_graph_paper_entry,
)

TASK_ID = "task_geometry__graph_paper__quadrilateral_type_count"
QUERY_ID = "single"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


def _build_quadrilateral_type_count_plan() -> GraphPaperTaskPlan:
    """Bind the quadrilateral-type count objective."""

    return GraphPaperTaskPlan(
        builder=_build_quadrilateral_type_count,
        prompt_key="quadrilateral_type_count",
        salt="quadrilateral_type_count_seed",
        target_field="quadrilateral_type",
    )


@register_task
class GeometryGraphPaperQuadrilateralTypeCountTask:
    """Count how many rendered quadrilaterals have the requested type."""

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
            plan=_build_quadrilateral_type_count_plan(),
        )


__all__ = ["GeometryGraphPaperQuadrilateralTypeCountTask"]
