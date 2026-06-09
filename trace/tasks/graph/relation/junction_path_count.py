"""Merged path-relation junction count task in a pipe-junction graph."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ...base import TaskOutput
from ...registry import register_task
from ..shared.fixed_query_task import (
    decoupled_merged_branch_params,
    select_merged_graph_query_id,
)
from ..shared.pipe_junction_task import PipeJunctionGraphTaskBase


PIPE_EXACT_DISTANCE_COUNT_TASK_ID = "task_graph__pipe_network__pipe_exact_distance_count"
PIPE_REACHABLE_JUNCTION_COUNT_TASK_ID = "task_graph__pipe_network__pipe_reachable_junction_count"

_MERGED_QUERY_IDS: Tuple[str, ...] = (
    "pipe_exact_distance_count",
    "pipe_reachable_junction_count",
)

_MERGED_QUERY_ALIASES: Dict[str, str] = {
    "exact_distance_count": "pipe_exact_distance_count",
    "reachable_count": "pipe_reachable_junction_count",
    "reachable_junction_count": "pipe_reachable_junction_count",
}

_QUERY_PROMPT_KEYS: Dict[str, Tuple[str, str]] = {
    "pipe_exact_distance_count": (
        "annotation_hint_exact_distance_count",
        "exact_distance_count_query",
    ),
    "pipe_reachable_junction_count": (
        "annotation_hint_reachable_count",
        "reachable_count_query",
    ),
}


def _selected_query_from_params(params: Mapping[str, Any], instance_seed: int) -> str:
    """Return the pipe-junction path query id for this merged task."""

    return select_merged_graph_query_id(
        params=params,
        instance_seed=int(instance_seed),
        task_id=PIPE_EXACT_DISTANCE_COUNT_TASK_ID,
        supported_query_ids=_MERGED_QUERY_IDS,
        aliases=_MERGED_QUERY_ALIASES,
    )


class _PipeJunctionPathCountBranch(PipeJunctionGraphTaskBase):
    """One selected internal query branch for the public pipe path-count task."""

    task_group = "relation"

    def __init__(self, query_id: str, *, task_id: str) -> None:
        annotation_key, task_key = _QUERY_PROMPT_KEYS[str(query_id)]
        self.task_id = str(task_id)
        self.query_id = str(query_id)
        self.prompt_annotation_key = str(annotation_key)
        self.prompt_task_key_fallback = str(task_key)


@register_task
class GraphRelationPipeExactDistanceCountTask:
    """Count pipe junctions at one exact shortest-path distance."""

    task_id = PIPE_EXACT_DISTANCE_COUNT_TASK_ID
    domain = "graph"
    task_group = "relation"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _PipeJunctionPathCountBranch(
            "pipe_exact_distance_count",
            task_id=self.task_id,
        ).generate(
            int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class GraphRelationPipeReachableJunctionCountTask:
    """Count pipe junctions reachable through open pipes from one start junction."""

    task_id = PIPE_REACHABLE_JUNCTION_COUNT_TASK_ID
    domain = "graph"
    task_group = "relation"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        branch_base_params = decoupled_merged_branch_params(
            params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_query_ids=("pipe_reachable_junction_count",),
            aliases=_MERGED_QUERY_ALIASES,
        )
        return _PipeJunctionPathCountBranch(
            "pipe_reachable_junction_count",
            task_id=self.task_id,
        ).generate(
            int(instance_seed),
            params=dict(branch_base_params),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "GraphRelationPipeExactDistanceCountTask",
    "GraphRelationPipeReachableJunctionCountTask",
]
