"""Minimum route-change count in a metro-route graph."""

from __future__ import annotations

from ...registry import register_task
from ..shared.metro_route_task import MetroRouteGraphTaskBase


@register_task
class GraphPathMetroTransferCountTask(MetroRouteGraphTaskBase):
    """Count route changes in a unique source-via-goal metro trip."""

    task_id = "task_graph__metro__transfer_count"
    task_group = "path"
    query_id = "metro_transfer_count"
    prompt_annotation_key = "annotation_hint"
    prompt_task_key_fallback = "metro_transfer_count_query"


__all__ = ["GraphPathMetroTransferCountTask"]
