"""Helpers for exposing one graph query contract as a narrow public task id."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Sequence

from ...base import TaskOutput
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.fixed_query import force_query_id_params, rewrite_public_query_output
from .information_style import infer_graph_scene_id


def forced_query_id_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Return params that force one internal graph query id."""

    return force_query_id_params(params, query_id=str(query_id))


def rewrite_graph_query_output(output: TaskOutput, *, query_id: str) -> TaskOutput:
    """Rewrite generated graph output so public task metadata has one default variant."""

    rewritten = rewrite_public_query_output(
        output,
        query_id=str(query_id),
        params_query_id_probabilities={"default": 1.0},
        preserve_internal_query_id_as="internal_query_id",
    )
    if rewritten.scene_id:
        return rewritten
    return replace(rewritten, scene_id=infer_graph_scene_id(str(query_id)))


def rewrite_graph_public_task_output(
    output: TaskOutput,
    *,
    task_id: str,
    query_id: str | None = None,
) -> TaskOutput:
    """Rewrite graph output produced by an absorbed branch under one public task id."""

    task_id_text = str(task_id)
    query_id_text = str(query_id if query_id is not None else output.query_id)
    scene_id_text = infer_graph_scene_id(task_id_text)
    return rewrite_public_query_output(
        output,
        query_id=query_id_text,
        scene_id=scene_id_text,
        task_id=task_id_text,
        include_scene_ir_root=True,
        clear_keys=("internal_task_id",),
    )


def select_merged_graph_query_id(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_query_ids: Sequence[str],
    aliases: Mapping[str, str] | None = None,
    namespace: str = "merged_query",
) -> str:
    """Resolve a public merged graph query id with balanced sequential sampling."""

    supported = tuple(str(query_id) for query_id in supported_query_ids)
    if not supported:
        raise ValueError("merged graph task has no supported query ids")
    alias_map = {str(key): str(value) for key, value in (aliases or {}).items()}
    forced = forced_merged_graph_query_id(
        params=params,
        supported_query_ids=supported,
        aliases=alias_map,
    )
    if forced is not None:
        return str(forced)

    raw_weights = params.get("query_id_weights", params.get("query_id_weights"))
    if isinstance(raw_weights, Mapping):
        weighted: list[str] = []
        canonical_weights = {str(query_id): 0.0 for query_id in supported}
        for raw_key, raw_weight in raw_weights.items():
            canonical = alias_map.get(str(raw_key), str(raw_key))
            if canonical in canonical_weights:
                canonical_weights[str(canonical)] += float(raw_weight)
        for query_id in supported:
            weight = float(canonical_weights.get(str(query_id), 0.0))
            if weight <= 0.0:
                continue
            repeats = max(1, int(round(float(weight) * 100.0)))
            weighted.extend([str(query_id)] * int(repeats))
        if weighted:
            index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}:{namespace}"))
            return str(weighted[int(index % len(weighted))])

    index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}:{namespace}"))
    return str(supported[int(index % len(supported))])


def forced_merged_graph_query_id(
    *,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
    aliases: Mapping[str, str] | None = None,
) -> str | None:
    """Return an explicitly requested merged query id, if present."""

    supported = tuple(str(query_id) for query_id in supported_query_ids)
    alias_map = {str(key): str(value) for key, value in (aliases or {}).items()}
    supported_set = set(supported)
    for key in ("query_id", "query_id"):
        value = params.get(str(key))
        if value is None:
            continue
        text = str(value)
        resolved = alias_map.get(text, text)
        if str(resolved) in supported_set:
            return str(resolved)
    return None


def decoupled_merged_branch_params(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str,
    supported_query_ids: Sequence[str],
    aliases: Mapping[str, str] | None = None,
    namespace: str = "merged_query",
) -> Dict[str, Any]:
    """Return params whose sampling index is independent of the merged query axis."""

    branch_params = dict(params)
    if forced_merged_graph_query_id(
        params=params,
        supported_query_ids=supported_query_ids,
        aliases=aliases,
    ) is not None:
        return branch_params
    divisor = max(1, len(tuple(supported_query_ids)))
    selection_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}:{namespace}"))
    branch_params["_sampling_index"] = int(selection_index // int(divisor))
    return branch_params


__all__ = [
    "forced_query_id_params",
    "rewrite_graph_query_output",
    "rewrite_graph_public_task_output",
    "decoupled_merged_branch_params",
    "forced_merged_graph_query_id",
    "select_merged_graph_query_id",
]
