"""Shared semantic/visual axis sampling helpers for games-domain tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant


def resolve_games_query_variant(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    supported_variants: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query axis, honoring `query_variant` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_variant") is None and alias_params.get("query_variant") is not None:
        alias_params["query_variant"] = alias_params["query_variant"]
    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.query_variant")
    selected, probabilities = resolve_variant(
        rng,
        params=alias_params,
        gen_defaults=gen_defaults,
        supported_variants=[str(item) for item in supported_variants],
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported_variants],
        balance_flag_key="balanced_query_variant_sampling",
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        sampling_namespace=f"{str(task_id)}.query_variant",
    )
    return str(selected), dict(probabilities)


def resolve_games_named_axis(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported_variants: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named visual or semantic axis for a games task."""

    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.{str(namespace)}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(item) for item in supported_variants],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported_variants],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{str(task_id)}.{str(namespace)}",
    )
    return str(selected), dict(probabilities)


__all__ = [
    "resolve_games_named_axis",
    "resolve_games_query_variant",
]
