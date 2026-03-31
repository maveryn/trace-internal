"""Helpers for consolidated icons tasks backed by legacy generators."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, Mapping, Sequence

from ...base import TaskOutput
from ...registry import TASK_REGISTRY


_CONSOLIDATED_KEYS = {
    "task_variant",
    "task_variant_weights",
    "balanced_variant_sampling",
}


def unregister_legacy_tasks(task_ids: Sequence[str]) -> None:
    """Remove legacy task registrations after importing their classes."""

    for task_id in task_ids:
        TASK_REGISTRY.pop(str(task_id), None)


def strip_consolidated_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Return params with consolidated wrapper keys removed."""

    return {
        str(key): value
        for key, value in dict(params).items()
        if str(key) not in _CONSOLIDATED_KEYS
    }


def normalize_legacy_icons_output(
    output: TaskOutput,
    *,
    scene_variant: str,
    task_variant: str,
    legacy_task_id: str,
    variant_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float] | None = None,
    legacy_scene_variant: str | None = None,
    legacy_task_variant: str | None = None,
    scene_kind: str | None = None,
    prompt_bundle_id: str | None = None,
    prompt_artifacts: Any | None = None,
    extra_query_params: Mapping[str, Any] | None = None,
    extra_execution_trace: Mapping[str, Any] | None = None,
) -> TaskOutput:
    """Rewrite legacy icon-task trace metadata to the consolidated task surface."""

    trace_payload = deepcopy(dict(output.trace_payload))

    execution_trace = dict(trace_payload.get("execution_trace") or {})
    prior_scene_variant = legacy_scene_variant if legacy_scene_variant is not None else execution_trace.get("scene_variant")
    prior_task_variant = legacy_task_variant if legacy_task_variant is not None else execution_trace.get("task_variant")
    execution_trace["legacy_task_id"] = str(legacy_task_id)
    if prior_scene_variant is not None:
        execution_trace["legacy_scene_variant"] = str(prior_scene_variant)
    if prior_task_variant is not None:
        execution_trace["legacy_task_variant"] = str(prior_task_variant)
    execution_trace["scene_variant"] = str(scene_variant)
    execution_trace["task_variant"] = str(task_variant)
    execution_trace["task_variant_probabilities"] = {
        str(key): float(value) for key, value in sorted(variant_probabilities.items())
    }
    if scene_variant_probabilities is not None:
        execution_trace["scene_variant_probabilities"] = {
            str(key): float(value) for key, value in sorted(scene_variant_probabilities.items())
        }
    if extra_execution_trace:
        execution_trace.update({str(key): value for key, value in dict(extra_execution_trace).items()})
    trace_payload["execution_trace"] = execution_trace

    render_spec = dict(trace_payload.get("render_spec") or {})
    render_spec["scene_variant"] = str(scene_variant)
    render_spec["task_variant"] = str(task_variant)
    if prior_scene_variant is not None:
        render_spec["legacy_scene_variant"] = str(prior_scene_variant)
    trace_payload["render_spec"] = render_spec

    query_spec = dict(trace_payload.get("query_spec") or {})
    query_params = dict(query_spec.get("params") or {})
    query_params["legacy_task_id"] = str(legacy_task_id)
    query_params["scene_variant"] = str(scene_variant)
    query_params["task_variant"] = str(task_variant)
    query_params["task_variant_probabilities"] = {
        str(key): float(value) for key, value in sorted(variant_probabilities.items())
    }
    if prior_scene_variant is not None:
        query_params["legacy_scene_variant"] = str(prior_scene_variant)
    if prior_task_variant is not None:
        query_params["legacy_task_variant"] = str(prior_task_variant)
    if scene_variant_probabilities is not None:
        query_params["scene_variant_probabilities"] = {
            str(key): float(value) for key, value in sorted(scene_variant_probabilities.items())
        }
    if extra_query_params:
        query_params.update({str(key): value for key, value in dict(extra_query_params).items()})
    query_spec["params"] = query_params
    query_spec["task_variant"] = str(task_variant)
    if prompt_bundle_id is not None:
        query_spec["template_id"] = str(prompt_bundle_id)
    if prompt_artifacts is not None:
        query_spec["prompt_variant"] = dict(prompt_artifacts.prompt_variant)
        query_spec["prompt_variant_active_key"] = str(prompt_artifacts.prompt_variant_active_key)
        query_spec["prompt_variants"] = dict(prompt_artifacts.prompt_variants_for_trace)
    trace_payload["query_spec"] = query_spec

    scene_ir = dict(trace_payload.get("scene_ir") or {})
    if scene_kind is not None:
        scene_ir["scene_kind"] = str(scene_kind)
    relations = dict(scene_ir.get("relations") or {})
    relations["legacy_task_id"] = str(legacy_task_id)
    relations["scene_variant"] = str(scene_variant)
    relations["task_variant"] = str(task_variant)
    if prior_scene_variant is not None:
        relations["legacy_scene_variant"] = str(prior_scene_variant)
    if prior_task_variant is not None:
        relations["legacy_task_variant"] = str(prior_task_variant)
    scene_ir["relations"] = relations
    trace_payload["scene_ir"] = scene_ir

    prompt = output.prompt
    prompt_variants = dict(output.prompt_variants)
    if prompt_artifacts is not None:
        prompt = str(prompt_artifacts.prompt)
        prompt_variants = dict(prompt_artifacts.prompt_variants)

    return replace(
        output,
        prompt=str(prompt),
        trace_payload=trace_payload,
        task_variant=str(task_variant),
        prompt_variants=prompt_variants,
    )


__all__ = [
    "normalize_legacy_icons_output",
    "strip_consolidated_params",
    "unregister_legacy_tasks",
]
