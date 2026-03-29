"""Shared temporal-task support for balanced named variant axes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant


def resolve_temporal_named_variant(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    instance_seed: int,
    task_id: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named temporal-task variant axis."""

    selected_variant, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=supported,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_variant),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{str(task_id)}:{str(namespace)}",
    )
    return str(variant), {str(key): float(value) for key, value in sorted(probabilities.items())}


__all__ = ["resolve_temporal_named_variant"]
