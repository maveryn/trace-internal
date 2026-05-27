"""Single-route station count in a metro-route graph."""

from __future__ import annotations

from ..shared.metro_route_task import MetroRouteGraphTaskBase


class GraphCountingSingleRouteStationCountTask(MetroRouteGraphTaskBase):
    """Count stations served by exactly one colored route."""

    task_id = "graph_metro_single_route_station_count_internal"
    task_group = "counting"
    query_id = "metro_single_route_station_count"
    prompt_evidence_key = "evidence_hint"
    prompt_task_key_fallback = "metro_single_route_station_count_query"


__all__ = ["GraphCountingSingleRouteStationCountTask"]
