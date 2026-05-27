"""Transfer-station count in a metro-route graph."""

from __future__ import annotations

from ..shared.metro_route_task import MetroRouteGraphTaskBase


class GraphCountingTransferStationCountTask(MetroRouteGraphTaskBase):
    """Count stations served by two or more metro routes."""

    task_id = "graph_metro_transfer_station_count_internal"
    task_group = "counting"
    query_id = "metro_transfer_station_count"
    prompt_evidence_key = "evidence_hint"
    prompt_task_key_fallback = "metro_transfer_station_count_query"


__all__ = ["GraphCountingTransferStationCountTask"]
