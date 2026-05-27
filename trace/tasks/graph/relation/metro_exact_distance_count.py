"""Exact-distance station count in a metro-route graph."""

from __future__ import annotations

from ...registry import register_task
from ..shared.metro_route_task import MetroRouteGraphTaskBase


@register_task
class GraphRelationMetroExactDistanceCountTask(MetroRouteGraphTaskBase):
    """Count stations exactly k route segments away from a queried station."""

    task_id = "task_graph__metro__exact_distance_station_count"
    task_group = "relation"
    query_id = "metro_exact_distance_count"
    prompt_evidence_key = "evidence_hint_exact_distance_count"
    prompt_task_key_fallback = "exact_distance_count_query"


__all__ = ["GraphRelationMetroExactDistanceCountTask"]
