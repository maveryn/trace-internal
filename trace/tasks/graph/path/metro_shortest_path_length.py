"""Shortest route length in a metro-route graph."""

from __future__ import annotations

from ...registry import register_task
from ..shared.metro_route_task import MetroRouteGraphTaskBase


@register_task
class GraphPathMetroShortestPathLengthTask(MetroRouteGraphTaskBase):
    """Count route segments in a unique shortest station path."""

    task_id = "task_graph__metro__shortest_path_length"
    task_group = "path"
    query_id = "metro_shortest_path_length"
    prompt_evidence_key = "evidence_hint"
    prompt_task_key_fallback = "shortest_path_length_query"


__all__ = ["GraphPathMetroShortestPathLengthTask"]
