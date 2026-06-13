"""Shared sampling and scoring helpers for three_d tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant


def normalize_unit(value: float, lower: float, upper: float) -> float:
    """Normalize a scalar to [0, 1] with a degenerate-range fallback."""

    if float(upper) <= float(lower):
        return 0.0
    return max(0.0, min(1.0, (float(value) - float(lower)) / (float(upper) - float(lower))))


def int_value(mapping: Mapping[str, Any], key: str, default: int) -> int:
    """Resolve an integer render/default value."""

    return int(mapping.get(str(key), int(default)))


def float_value(mapping: Mapping[str, Any], key: str, default: float) -> float:
    """Resolve a float render/default value."""

    return float(mapping.get(str(key), float(default)))


def _namespace_value(namespace: str) -> str:
    resolved = str(namespace).strip()
    if not resolved:
        raise ValueError("three_d sampling namespace must be non-empty")
    return resolved


def _support_key_value(*, key: str | None, prefix: str | None) -> str:
    support_key = str(key if key is not None else prefix)
    if support_key == "None":
        raise ValueError("resolve_count requires key or prefix")
    return support_key


def resolve_axis_variant_for_namespace(
    params: Mapping[str, Any],
    *,
    namespace: str,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    supported_variants: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    allow_locked: bool = False,
) -> Tuple[str, Dict[str, float]]:
    """Resolve a balanced scene/query axis variant with an identity-free namespace."""

    sampling_namespace = _namespace_value(namespace)
    local_params = dict(params)
    locked_variant = local_params.get(f"_locked_{explicit_key}") if bool(allow_locked) else None
    if str(explicit_key) == "query_id" and "query_id" not in local_params and "query_variant" in local_params:
        local_params["query_id"] = local_params["query_variant"]
    rng = spawn_rng(int(instance_seed), sampling_namespace)
    selected, probabilities = resolve_variant(
        rng,
        params=local_params,
        gen_defaults=gen_defaults,
        supported_variants=[str(item) for item in supported_variants],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=local_params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported_variants],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=sampling_namespace,
    )
    if locked_variant is not None:
        locked = str(locked_variant)
        if locked not in {str(item) for item in supported_variants}:
            raise ValueError(f"unsupported locked {explicit_key}: {locked}")
        return locked, {str(key): float(value) for key, value in sorted(probabilities.items())}
    return str(balanced), {str(key): float(value) for key, value in sorted(probabilities.items())}


def resolve_axis_variant(
    params: Mapping[str, Any],
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    supported_variants: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
    allow_locked: bool = False,
) -> Tuple[str, Dict[str, float]]:
    """Legacy wrapper using a public task id for namespace construction."""

    return resolve_axis_variant_for_namespace(
        params,
        namespace=f"{task_id}.{axis_namespace}",
        gen_defaults=gen_defaults,
        instance_seed=instance_seed,
        supported_variants=supported_variants,
        explicit_key=explicit_key,
        weights_key=weights_key,
        balance_flag_key=balance_flag_key,
        allow_locked=allow_locked,
    )


def resolve_count_for_namespace(
    params: Mapping[str, Any],
    *,
    namespace: str,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    key: str | None = None,
    prefix: str | None = None,
    default_min: int | None = None,
    default_max: int | None = None,
    minimum_default: int | None = None,
    maximum_default: int | None = None,
    lower: int,
    upper: int,
    allow_locked: bool = False,
) -> Tuple[int, Dict[str, float]]:
    """Resolve an integer support with an identity-free sampling namespace."""

    sampling_namespace = _namespace_value(namespace)
    support_key = _support_key_value(key=key, prefix=prefix)
    min_default = int(default_min if default_min is not None else minimum_default)
    max_default = int(default_max if default_max is not None else maximum_default)
    min_count = int(params.get(f"{support_key}_min", group_default(gen_defaults, f"{support_key}_min", min_default)))
    max_count = int(params.get(f"{support_key}_max", group_default(gen_defaults, f"{support_key}_max", max_default)))
    min_count = max(int(lower), min(int(upper), int(min_count)))
    max_count = max(min_count, min(int(upper), int(max_count)))
    support = tuple(range(int(min_count), int(max_count) + 1))
    locked = params.get(f"_locked_{support_key}") if bool(allow_locked) else None
    explicit = params.get(str(support_key))
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported {support_key}: {selected}")
        return int(selected), dict(uniform_probability_map(support, selected=int(selected)))
    if locked is not None:
        selected = int(locked)
        if selected not in set(support):
            raise ValueError(f"unsupported locked {support_key}: {selected}")
        return int(selected), dict(uniform_probability_map(support))
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=sampling_namespace,
    )
    selected = int(support[abs(int(selection_index)) % len(support)])
    return int(selected), dict(uniform_probability_map(support))


def resolve_count(
    params: Mapping[str, Any],
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    key: str | None = None,
    prefix: str | None = None,
    default_min: int | None = None,
    default_max: int | None = None,
    minimum_default: int | None = None,
    maximum_default: int | None = None,
    lower: int,
    upper: int,
    allow_locked: bool = False,
) -> Tuple[int, Dict[str, float]]:
    """Legacy wrapper using a public task id for namespace construction."""

    support_key = _support_key_value(key=key, prefix=prefix)
    return resolve_count_for_namespace(
        params,
        namespace=f"{task_id}.{support_key}",
        gen_defaults=gen_defaults,
        instance_seed=instance_seed,
        key=support_key,
        default_min=default_min,
        default_max=default_max,
        minimum_default=minimum_default,
        maximum_default=maximum_default,
        lower=lower,
        upper=upper,
        allow_locked=allow_locked,
    )


__all__ = [
    "float_value",
    "int_value",
    "normalize_unit",
    "resolve_axis_variant",
    "resolve_axis_variant_for_namespace",
    "resolve_count",
    "resolve_count_for_namespace",
]
