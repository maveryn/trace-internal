"""Shared deterministic task-variant sampling helpers across domains."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ...core.sampling import normalize_positive_weights, weighted_choice
from .config_defaults import group_default


def is_uniform_probability_map(probabilities: Mapping[str, float], *, tol: float = 1e-9) -> bool:
    """Return true when all positive probabilities are approximately equal."""

    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if not positives:
        return False
    return max(positives) - min(positives) <= float(tol)


def has_non_null_param(params: Mapping[str, Any], key: str) -> bool:
    """Return true when a non-null override key is present."""

    return key in params and params.get(key) is not None


def resolve_variant(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    supported_variants: Sequence[str],
    explicit_key: str = "shape_variant",
    weights_key: str = "variant_weights",
) -> Tuple[str, Dict[str, float]]:
    """Resolve one variant with optional explicit override + weighted sampling."""

    supported = [str(item) for item in supported_variants]
    supported_set = set(supported)
    explicit_variant = params.get(str(explicit_key))
    if explicit_variant is not None:
        selected = str(explicit_variant).strip()
        if selected not in supported_set:
            raise ValueError(f"unsupported {explicit_key}: {selected}")
        return selected, {key: (1.0 if key == selected else 0.0) for key in sorted(supported_set)}

    raw_weights = params.get(
        str(weights_key),
        group_default(gen_defaults, str(weights_key), {key: 1.0 for key in supported}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError(f"{weights_key} must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in supported_set
    }
    probabilities = normalize_positive_weights(weights, default_keys=supported)
    selected_variant = weighted_choice(rng, probabilities, sort_keys=True)
    return str(selected_variant), {str(key): float(value) for key, value in sorted(probabilities.items())}


def apply_balanced_variant_sampling(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    selected_variant: str,
    variant_probabilities: Mapping[str, float],
    supported_variants: Sequence[str],
    balance_flag_key: str = "balanced_variant_sampling",
    explicit_key: str = "shape_variant",
    weights_key: str = "variant_weights",
) -> str:
    """Apply deterministic cycling over variants when configuration is uniform."""

    enabled = bool(params.get(str(balance_flag_key), group_default(gen_defaults, str(balance_flag_key), True)))
    if not bool(enabled):
        return str(selected_variant)
    overridden = any(has_non_null_param(params, key) for key in (str(explicit_key), str(weights_key)))
    if overridden or (not is_uniform_probability_map(variant_probabilities)):
        return str(selected_variant)
    values = [str(item) for item in supported_variants]
    if not values:
        return str(selected_variant)
    sampling_index = params.get("_sampling_index", instance_seed)
    return str(values[abs(int(sampling_index)) % len(values)])


__all__ = [
    "apply_balanced_variant_sampling",
    "has_non_null_param",
    "is_uniform_probability_map",
    "resolve_variant",
]
