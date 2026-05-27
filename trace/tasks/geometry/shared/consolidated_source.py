"""Helpers for consolidated geometry tasks backed by source generators."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, Mapping, Sequence

from ...base import TaskOutput
from ...registry import TASK_REGISTRY


def unregister_source_tasks(task_ids: Sequence[str]) -> None:
    """Remove source task registrations after importing their classes.

    Consolidated geometry tasks reuse source task implementations internally, but
    those source task ids should not remain active in the global registry once the
    new consolidated task modules are imported.
    """

    for task_id in task_ids:
        TASK_REGISTRY.pop(str(task_id), None)


_CONSOLIDATED_KEYS = {
    "query_id",
    "scene_variant",
    "scene_variant_weights",
    "balanced_scene_variant_sampling",
    "query_id",
    "query_id_weights",
    "balanced_query_id_sampling",
    "extremum_direction",
    "extremum_direction_weights",
    "balanced_extremum_direction_sampling",
}


def strip_consolidated_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Return params with consolidated-scaffold keys removed for source tasks."""

    return {
        str(key): value
        for key, value in dict(params).items()
        if str(key) not in _CONSOLIDATED_KEYS
    }


def normalize_source_geometry_output(
    output: TaskOutput,
    *,
    scene_variant: str,
    query_id: str,
    source_task_id: str,
    scene_variant_probabilities: Mapping[str, float],
    query_id_probabilities: Mapping[str, float],
    source_scene_variant: str | None = None,
    source_query_id: str | None = None,
    extra_query_params: Mapping[str, Any] | None = None,
) -> TaskOutput:
    """Rewrite source task trace metadata to the consolidated scene/query schema."""

    trace_payload = deepcopy(dict(output.trace_payload))

    execution_trace = dict(trace_payload.get("execution_trace") or {})
    prior_scene_variant = source_scene_variant if source_scene_variant is not None else execution_trace.get("scene_variant")
    prior_query_id = source_query_id if source_query_id is not None else execution_trace.get("query_id")
    execution_trace["source_task_id"] = str(source_task_id)
    if prior_scene_variant is not None:
        execution_trace["source_scene_variant"] = str(prior_scene_variant)
    if prior_query_id is not None:
        execution_trace["source_query_id"] = str(prior_query_id)
    execution_trace["scene_variant"] = str(scene_variant)
    execution_trace["query_id"] = str(query_id)
    execution_trace["query_id"] = str(query_id)
    execution_trace["scene_variant_probabilities"] = {
        str(key): float(value) for key, value in sorted(scene_variant_probabilities.items())
    }
    execution_trace["query_id_probabilities"] = {
        str(key): float(value) for key, value in sorted(query_id_probabilities.items())
    }
    execution_trace["query_id_probabilities"] = {
        str(key): float(value) for key, value in sorted(query_id_probabilities.items())
    }
    if extra_query_params:
        execution_trace.update({str(key): value for key, value in dict(extra_query_params).items()})
    trace_payload["execution_trace"] = execution_trace

    render_spec = dict(trace_payload.get("render_spec") or {})
    if prior_scene_variant is not None:
        render_spec["source_scene_variant"] = str(prior_scene_variant)
    render_spec["scene_variant"] = str(scene_variant)
    render_spec["query_id"] = str(query_id)
    trace_payload["render_spec"] = render_spec

    query_spec = dict(trace_payload.get("query_spec") or {})
    query_params = dict(query_spec.get("params") or {})
    if prior_scene_variant is not None:
        query_params.setdefault("source_scene_variant", str(prior_scene_variant))
    if prior_query_id is not None:
        query_params.setdefault("source_query_id", str(prior_query_id))
    query_params["source_task_id"] = str(source_task_id)
    query_params["scene_variant"] = str(scene_variant)
    query_params["query_id"] = str(query_id)
    query_params["scene_variant_probabilities"] = {
        str(key): float(value) for key, value in sorted(scene_variant_probabilities.items())
    }
    query_params["query_id_probabilities"] = {
        str(key): float(value) for key, value in sorted(query_id_probabilities.items())
    }
    query_params["query_id_probabilities"] = {
        str(key): float(value) for key, value in sorted(query_id_probabilities.items())
    }
    if extra_query_params:
        query_params.update({str(key): value for key, value in dict(extra_query_params).items()})
    query_spec["params"] = query_params
    query_spec["query_id"] = str(query_id)
    trace_payload["query_spec"] = query_spec

    scene_ir = dict(trace_payload.get("scene_ir") or {})
    relations = dict(scene_ir.get("relations") or {})
    if prior_scene_variant is not None:
        relations.setdefault("source_scene_variant", str(prior_scene_variant))
    if prior_query_id is not None:
        relations.setdefault("source_query_id", str(prior_query_id))
    relations["scene_variant"] = str(scene_variant)
    relations["query_id"] = str(query_id)
    relations["source_task_id"] = str(source_task_id)
    if extra_query_params:
        relations.update({str(key): value for key, value in dict(extra_query_params).items()})
    scene_ir["relations"] = relations
    trace_payload["scene_ir"] = scene_ir

    return replace(output, trace_payload=trace_payload, query_id=str(query_id))
