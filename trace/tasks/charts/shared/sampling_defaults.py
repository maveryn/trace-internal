"""Shared sampling/default plumbing for chart task families."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ...shared.deterministic_sampling import resolve_selection_index
from .labeled_chart_core import resolve_chart_axis_variant


def public_task_param_overrides(
    defaults: Mapping[str, Any],
    task_id: str,
    *,
    sections: Sequence[str] = ("generation", "rendering"),
) -> Dict[str, Any]:
    """Return shallow task-id-specific params from scene defaults."""

    overrides: Dict[str, Any] = {}
    if not isinstance(defaults, Mapping):
        return overrides
    for section in sections:
        section_cfg = defaults.get(str(section))
        if not isinstance(section_cfg, Mapping):
            continue
        task_overrides = section_cfg.get("task_overrides")
        if not isinstance(task_overrides, Mapping):
            continue
        task_values = task_overrides.get(str(task_id))
        if isinstance(task_values, Mapping):
            overrides.update({str(key): value for key, value in task_values.items()})
    return overrides


def uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str],
    explicit_key: str = "query_id",
    weights_key: str = "query_id_weights",
    balance_flag_key: str = "balanced_query_id_sampling",
) -> bool:
    """Return whether support sampling should decouple from query-id cycling."""

    if params.get(str(explicit_key)) is not None or params.get(str(weights_key)) is not None:
        return False
    enabled = bool(params.get(str(balance_flag_key), gen_defaults.get(str(balance_flag_key), True)))
    if not enabled:
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(tuple(supported_query_ids)):
        return False
    return max(positives) - min(positives) <= 1e-9


def support_sampling_params_for_uniform_query_cycle(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Decouple `_sample_cursor` from uniform public query-id cycling."""

    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not uses_uniform_query_id_cycle(
        params,
        gen_defaults=gen_defaults,
        query_id_probabilities=query_id_probabilities,
        supported_query_ids=supported_query_ids,
    ):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(tuple(supported_query_ids)))
    return support_params


def decouple_sample_cursor_for_axis_lengths(
    params: Mapping[str, Any],
    *,
    axes: Sequence[Tuple[int, Sequence[str]]],
    explicit_policy: str = "present",
    use_abs: bool = False,
) -> Dict[str, Any]:
    """Decouple `_sample_cursor` by fixed axis lengths when axes are implicit.

    `explicit_policy="present"` preserves helpers that treated key presence as
    explicit. `explicit_policy="non_null"` treats only non-null values as
    explicit.
    """

    support_params = dict(params)
    if "_sample_cursor" not in support_params:
        return support_params
    divisor = 1
    for axis_length, explicit_keys in axes:
        keys = tuple(str(key) for key in explicit_keys)
        if str(explicit_policy) == "present":
            axis_explicit = any(key in support_params for key in keys)
        elif str(explicit_policy) == "non_null":
            axis_explicit = any(support_params.get(key) is not None for key in keys)
        else:
            raise ValueError(f"unsupported explicit_policy: {explicit_policy}")
        if not axis_explicit:
            divisor *= max(1, int(axis_length))
    cursor = abs(int(support_params["_sample_cursor"])) if bool(use_abs) else int(support_params["_sample_cursor"])
    support_params["_sample_cursor"] = int(cursor) // max(1, int(divisor))
    return support_params


def balanced_int_from_support(
    support: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Select one integer from an ordered support using the shared seed cursor."""

    ordered = [int(value) for value in support]
    if not ordered:
        raise ValueError(f"empty support for {namespace}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(ordered[int(index) % len(ordered)])


__all__ = [
    "balanced_int_from_support",
    "decouple_sample_cursor_for_axis_lengths",
    "public_task_param_overrides",
    "resolve_chart_axis_variant",
    "support_sampling_params_for_uniform_query_cycle",
    "uses_uniform_query_id_cycle",
]
