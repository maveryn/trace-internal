"""Helpers for exposing pages query branches as public task ids."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Sequence

from ...base import TaskOutput
from ...shared.fixed_query import (
    explicit_query_id_param,
    force_query_id_params,
    normalize_query_id_params,
    probability_map,
    rewrite_public_query_output,
)


def forced_pages_query_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Return params that force one source pages query id."""

    return force_query_id_params(params, query_id=str(query_id))


def merged_pages_query_params(
    params: Mapping[str, Any],
    *,
    allowed_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Return params restricted to one public pages query set."""

    allowed = tuple(str(value) for value in allowed_query_ids if str(value).strip())
    if not allowed:
        raise ValueError("allowed_query_ids must contain at least one query id")
    allowed_set = set(allowed)
    merged = normalize_query_id_params(params)
    explicit_query = explicit_query_id_param(merged)
    if explicit_query is not None:
        if str(explicit_query) not in allowed_set:
            raise ValueError(f"unsupported query id for pages task: {explicit_query}")
        return merged

    raw_weights = merged.get("query_id_weights")
    if raw_weights is None:
        merged["query_id_weights"] = {str(query_id): 1.0 for query_id in allowed}
        return merged
    if not isinstance(raw_weights, Mapping):
        raise ValueError("query_id_weights must be a mapping when provided")
    positive = {str(key) for key, value in raw_weights.items() if float(value) > 0.0}
    invalid = sorted(positive.difference(allowed_set))
    if invalid:
        raise ValueError(f"unsupported positive query weights for pages task: {invalid}")
    return merged


def infer_pages_query_id(output: TaskOutput) -> str:
    """Infer the generated source query id from output metadata."""

    if str(output.query_id).strip() and str(output.query_id) != "default":
        return str(output.query_id)
    payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
    for source in (
        payload.get("query_spec") if isinstance(payload, Mapping) else None,
        payload.get("execution_trace") if isinstance(payload, Mapping) else None,
        payload.get("scene_ir", {}).get("relations") if isinstance(payload.get("scene_ir"), Mapping) else None,
    ):
        if not isinstance(source, Mapping):
            continue
        params = source.get("params")
        for candidate in (source, params if isinstance(params, Mapping) else None):
            if not isinstance(candidate, Mapping):
                continue
            value = candidate.get("query_id")
            if value is not None and str(value).strip() and str(value) != "default":
                return str(value)
    return ""


def query_probabilities_from_pages_output(
    output: TaskOutput,
    *,
    fallback_query_ids: Sequence[str],
) -> Dict[str, float]:
    """Return query probability metadata from a generated pages output."""

    payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
    for source in (
        payload.get("execution_trace") if isinstance(payload, Mapping) else None,
        payload.get("query_spec", {}).get("params") if isinstance(payload.get("query_spec"), Mapping) else None,
    ):
        if isinstance(source, Mapping) and isinstance(source.get("query_id_probabilities"), Mapping):
            return {str(key): float(value) for key, value in source["query_id_probabilities"].items()}
    return probability_map(tuple(str(query_id) for query_id in fallback_query_ids))


def rewrite_pages_public_task_output(
    output: TaskOutput,
    *,
    task_id: str,
    scene_id: str,
    query_id: str,
    query_probabilities: Mapping[str, float] | None = None,
) -> TaskOutput:
    """Rewrite generated pages output under the public task id."""

    rewritten = rewrite_public_query_output(
        output,
        task_id=str(task_id),
        scene_id=str(scene_id),
        query_id=str(query_id),
        include_render_spec=True,
        include_scene_ir_root=True,
        query_id_probabilities=dict(query_probabilities or {str(query_id): 1.0}),
        preserve_prior_task_id_as="source_task_id",
        preserve_internal_query_id_as=("source_query_id", "internal_query_id"),
        update_existing_taxonomy=True,
    )
    return replace(rewritten, image_id=f"{str(task_id)}_image")


class FixedPagesQueryTaskMixin:
    """Mixin for public pages tasks backed by one source query branch."""

    default_dataset_enabled = True
    fixed_query_id: str
    public_scene_id: str
    source_task_cls: type

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        source_task = self.source_task_cls()
        output = source_task.generate(
            int(instance_seed),
            params=forced_pages_query_params(params, query_id=str(self.fixed_query_id)),
            max_attempts=int(max_attempts),
        )
        return rewrite_pages_public_task_output(
            output,
            task_id=str(self.task_id),
            scene_id=str(self.public_scene_id),
            query_id=str(self.fixed_query_id),
            query_probabilities={str(self.fixed_query_id): 1.0},
        )


class MergedPagesQueryTaskMixin:
    """Mixin for public pages tasks that sample equivalent source query branches."""

    default_dataset_enabled = True
    allowed_query_ids: Sequence[str] = ()
    public_scene_id: str
    source_task_cls: type

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        allowed = tuple(str(value) for value in self.allowed_query_ids if str(value).strip())
        source_task = self.source_task_cls()
        output = source_task.generate(
            int(instance_seed),
            params=merged_pages_query_params(params, allowed_query_ids=allowed),
            max_attempts=int(max_attempts),
        )
        query_id = infer_pages_query_id(output)
        if str(query_id) not in set(allowed):
            raise ValueError(f"generated unsupported query id for public pages task: {query_id}")
        return rewrite_pages_public_task_output(
            output,
            task_id=str(self.task_id),
            scene_id=str(self.public_scene_id),
            query_id=str(query_id),
            query_probabilities=query_probabilities_from_pages_output(
                output,
                fallback_query_ids=allowed,
            ),
        )


__all__ = [
    "FixedPagesQueryTaskMixin",
    "MergedPagesQueryTaskMixin",
    "forced_pages_query_params",
    "infer_pages_query_id",
    "merged_pages_query_params",
    "query_probabilities_from_pages_output",
    "rewrite_pages_public_task_output",
]
