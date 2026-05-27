"""Merged station-membership count task for metro-route graphs."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ...base import TaskOutput
from ...registry import register_task
from ..shared.fixed_query_task import (
    decoupled_merged_branch_params,
    rewrite_graph_public_task_output,
    select_merged_graph_query_id,
)


TASK_ID = "task_graph__metro__station_membership_count"

_MERGED_QUERY_IDS: Tuple[str, ...] = (
    "metro_transfer_station_count",
    "metro_single_route_station_count",
)

_MERGED_QUERY_ALIASES: Dict[str, str] = {
    "transfer_station_count": "metro_transfer_station_count",
    "single_route_station_count": "metro_single_route_station_count",
    "non_transfer_station_count": "metro_single_route_station_count",
}


def _selected_query_from_params(params: Mapping[str, Any], instance_seed: int) -> str:
    """Return the metro station-membership query id for this merged task."""

    if params.get("target_transfer_count") is not None:
        return "metro_transfer_station_count"
    return select_merged_graph_query_id(
        params=params,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        supported_query_ids=_MERGED_QUERY_IDS,
        aliases=_MERGED_QUERY_ALIASES,
    )


@register_task
class GraphCountingMetroStationMembershipCountTask:
    """Count stations by route-membership predicate in a metro-route graph."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        branch_base_params = decoupled_merged_branch_params(
            params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            supported_query_ids=_MERGED_QUERY_IDS,
            aliases=_MERGED_QUERY_ALIASES,
        )
        query_id = _selected_query_from_params(params, int(instance_seed))
        if str(query_id) == "metro_transfer_station_count":
            from .metro_transfer_station_count import GraphCountingTransferStationCountTask

            output = GraphCountingTransferStationCountTask().generate(
                int(instance_seed),
                params=dict(branch_base_params),
                max_attempts=int(max_attempts),
            )
        else:
            from .metro_single_route_station_count import GraphCountingSingleRouteStationCountTask

            output = GraphCountingSingleRouteStationCountTask().generate(
                int(instance_seed),
                params=dict(branch_base_params),
                max_attempts=int(max_attempts),
            )
        return rewrite_graph_public_task_output(output, task_id=TASK_ID, query_id=output.query_id)


__all__ = ["GraphCountingMetroStationMembershipCountTask"]
