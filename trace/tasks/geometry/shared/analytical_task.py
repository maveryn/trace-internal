"""Shared task-module helpers for geometry analytical objectives."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ...shared.config_defaults import required_group_default, resolve_optional_int_bounds
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant


def required_prompt_text(
    prompt_defaults: Mapping[str, Any],
    *,
    preferred_keys: Sequence[str],
    context: str,
) -> str:
    """Return the first available non-empty prompt slot among ordered candidates."""
    for key in preferred_keys:
        if str(key) in prompt_defaults:
            return str(required_group_default(prompt_defaults, str(key), context=context))
    raise ValueError(f"missing required prompt key in {context}: one of {list(preferred_keys)}")


def resolve_answer_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    task_id: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    """Resolve inclusive integer answer bounds for one analytical task."""
    answer_min, answer_max = resolve_optional_int_bounds(
        params,
        gen_defaults,
        min_key="answer_min",
        max_key="answer_max",
        context=f"generation defaults for {task_id}",
    )
    resolved_min = int(fallback_min if answer_min is None else answer_min)
    resolved_max = int(fallback_max if answer_max is None else answer_max)
    if int(resolved_min) > int(resolved_max):
        raise ValueError("answer_min must be <= answer_max")
    return int(resolved_min), int(resolved_max)


def resolve_task_variant(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    supported_variants: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one analytical task variant with deterministic balancing."""
    selected_variant, variant_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=supported_variants,
        explicit_key="task_variant",
        weights_key="variant_weights",
    )
    task_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_variant),
        variant_probabilities=variant_probabilities,
        supported_variants=supported_variants,
        balance_flag_key="balanced_variant_sampling",
        explicit_key="task_variant",
        weights_key="variant_weights",
    )
    return str(task_variant), {str(key): float(value) for key, value in sorted(variant_probabilities.items())}
