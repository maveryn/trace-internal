"""Helpers for exposing one chart scene/query contract as a narrow task id."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ...base import TaskOutput
from ...shared.fixed_query import (
    explicit_query_id_param,
    force_query_id_params,
    normalize_query_id_params,
    rewrite_public_query_output,
)


def forced_query_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Return params that force one source chart query id."""

    return force_query_id_params(params, query_id=str(query_id))


def merged_query_params(
    params: Mapping[str, Any],
    *,
    allowed_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Return params that restrict a shared chart task to one public query set."""

    merged = normalize_query_id_params(params)
    allowed = tuple(str(value) for value in allowed_query_ids if str(value).strip())
    allowed_set = set(allowed)

    explicit_query = explicit_query_id_param(params)
    if allowed and explicit_query is not None:
        variant_text = str(explicit_query)
        if variant_text not in allowed_set:
            raise ValueError(f"unsupported query id for merged chart task: {variant_text}")
        return merged

    raw_weights = merged.get("query_id_weights", merged.get("query_variant_weights"))
    if allowed and raw_weights is None:
        merged["query_id_weights"] = {str(value): 1.0 for value in allowed}
    elif allowed and isinstance(raw_weights, Mapping):
        positive_variants = {
            str(key)
            for key, value in raw_weights.items()
            if float(value) > 0.0
        }
        invalid = sorted(positive_variants.difference(allowed_set))
        if invalid:
            raise ValueError(f"unsupported positive query weights for merged chart task: {invalid}")
    elif allowed and raw_weights is not None:
        raise ValueError("query_id_weights must be a mapping when provided")

    return merged


def infer_query_id_from_output(output: TaskOutput) -> str:
    """Infer the concrete generated query before rewriting public task metadata."""

    if str(output.query_id).strip():
        return str(output.query_id)
    if str(output.query_id).strip() and str(output.query_id) != "default":
        return str(output.query_id)

    payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
    sources = [
        payload.get("query_spec") if isinstance(payload, Mapping) else None,
        payload.get("execution_trace") if isinstance(payload, Mapping) else None,
    ]
    scene_ir = payload.get("scene_ir") if isinstance(payload, Mapping) else None
    if isinstance(scene_ir, Mapping):
        sources.append(scene_ir.get("relations"))
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        params = source.get("params")
        for candidate_source in (source, params if isinstance(params, Mapping) else None):
            if not isinstance(candidate_source, Mapping):
                continue
            for key in ("query_id", "query_variant"):
                value = candidate_source.get(str(key))
                if value is not None and str(value).strip() and str(value) != "default":
                    return str(value)
    return ""


def rewrite_fixed_query_output(output: TaskOutput, *, query_id: str) -> TaskOutput:
    """Rewrite generated output so the public task has no semantic query id."""

    return rewrite_public_query_output(
        output,
        query_id=str(query_id),
        query_id_probabilities={"default": 1.0},
    )


class FixedChartQueryVariantTaskMixin:
    """Mixin for wrapper tasks that force one source chart query id."""

    default_dataset_enabled = True
    fixed_query_id: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=forced_query_params(params, query_id=str(self.fixed_query_id)),
            max_attempts=int(max_attempts),
        )
        return rewrite_fixed_query_output(output, query_id=str(self.fixed_query_id))


class MergedChartQueryVariantTaskMixin:
    """Mixin for public tasks that sample a small set of internal chart queries."""

    default_dataset_enabled = True
    allowed_query_ids: Sequence[str] = ()
    fixed_query_ids: Sequence[str] = ()

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        raw_allowed = self.allowed_query_ids or self.fixed_query_ids
        allowed = tuple(str(value) for value in raw_allowed if str(value).strip())
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=merged_query_params(params, allowed_query_ids=allowed),
            max_attempts=int(max_attempts),
        )
        query_id = infer_query_id_from_output(output)
        if allowed and str(query_id) not in set(allowed):
            raise ValueError(f"generated unsupported query id for merged chart task: {query_id}")
        return rewrite_fixed_query_output(output, query_id=str(query_id))


__all__ = [
    "FixedChartQueryVariantTaskMixin",
    "MergedChartQueryVariantTaskMixin",
    "forced_query_params",
    "infer_query_id_from_output",
    "merged_query_params",
    "rewrite_fixed_query_output",
]
