"""Shared semantic/visual axis sampling helpers for games-domain tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.fixed_query import normalize_query_id_params
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant


def get_games_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer parameter using game task/group precedence."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def get_games_int_range(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    """Resolve and validate an inclusive integer range for games-domain samplers."""

    lower = get_games_int_param(params, defaults, str(min_key), int(fallback_min))
    upper = get_games_int_param(params, defaults, str(max_key), int(fallback_max))
    if int(lower) > int(upper):
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(lower), int(upper)


def resolve_games_query_id(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    supported_variants: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query axis, honoring legacy aliases."""

    alias_params = normalize_query_id_params(params)
    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.query_id")
    selected, probabilities = resolve_variant(
        rng,
        params=alias_params,
        gen_defaults=gen_defaults,
        supported_variants=[str(item) for item in supported_variants],
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported_variants],
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{str(task_id)}.query_id",
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
    "get_games_int_param",
    "get_games_int_range",
    "resolve_games_named_axis",
    "resolve_games_query_id",
]
