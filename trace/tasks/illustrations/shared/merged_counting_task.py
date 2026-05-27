"""Helpers for merged illustration counting tasks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, Sequence, Tuple

from ...base import TaskOutput
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index


def query_support(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    fallback: Sequence[str],
) -> Tuple[str, ...]:
    """Resolve supported query ids for a merged public counting task."""

    raw = params.get("query_id_support", group_default(defaults, "query_id_support", fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("query_id_support must be a sequence")
    valid = set(str(value) for value in fallback)
    support = tuple(str(value) for value in raw if str(value) in valid)
    if not support:
        raise ValueError("query_id_support resolved no supported queries")
    return tuple(dict.fromkeys(support))


def select_query_id(
    *,
    task_id: str,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    instance_seed: int,
    fallback: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Select a query id and report the merged-task query distribution."""

    support = query_support(params, defaults, fallback=fallback)
    explicit = params.get("query_id")
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(support):
            raise ValueError(f"query_id must be one of {support}")
        return selected, {selected: 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}:query_id")
    selected = str(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return selected, {str(value): probability for value in support}


def rewrite_branch_output(
    output: TaskOutput,
    *,
    public_task_id: str,
    branch_id: str,
    query_probabilities: Mapping[str, float],
) -> TaskOutput:
    """Rewrite a private branch output to the merged public task identity."""

    trace_payload = deepcopy(output.trace_payload)
    query_id = str(output.query_id)
    query_spec = trace_payload.setdefault("query_spec", {})
    if isinstance(query_spec, dict):
        query_spec["task_id"] = str(public_task_id)
        query_spec["query_variant"] = query_id
        query_spec["query_id"] = query_id
        query_spec["branch_id"] = str(branch_id)
        params = query_spec.setdefault("params", {})
        if isinstance(params, dict):
            params["merged_query_probabilities"] = {str(key): float(value) for key, value in query_probabilities.items()}

    scene_ir = trace_payload.setdefault("scene_ir", {})
    if isinstance(scene_ir, dict):
        relations = scene_ir.setdefault("relations", {})
        if isinstance(relations, dict):
            relations["query_variant"] = query_id
            relations["query_id"] = query_id
            relations["branch_id"] = str(branch_id)

    execution_trace = trace_payload.setdefault("execution_trace", {})
    if isinstance(execution_trace, dict):
        execution_trace["query_variant"] = query_id
        execution_trace["query_id"] = query_id
        execution_trace["public_task_id"] = str(public_task_id)
        execution_trace["branch_id"] = str(branch_id)

    output.trace_payload = trace_payload
    output.query_variant = query_id
    output.query_id = query_id
    return output


__all__ = ["query_support", "rewrite_branch_output", "select_query_id"]
