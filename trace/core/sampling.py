"""Shared weighted-sampling helpers."""

from __future__ import annotations

from typing import Iterable, Mapping


def normalize_positive_weights(
    weights: Mapping[str, float],
    *,
    default_keys: Iterable[str] | None = None,
) -> dict[str, float]:
    """Normalize positive weights to probabilities.

    If no positive weights are present:
    - use uniform probabilities over `default_keys` when provided;
    - otherwise raise `ValueError`.
    """
    positive = {str(key): float(value) for key, value in weights.items() if float(value) > 0.0}
    if positive:
        total = sum(positive.values())
        if total <= 0.0:
            raise ValueError("at least one positive weight is required")
        return {key: value / total for key, value in sorted(positive.items())}

    if default_keys is None:
        raise ValueError("at least one positive weight is required")

    keys = [str(key) for key in default_keys]
    if not keys:
        raise ValueError("cannot normalize empty weights without default keys")
    probability = 1.0 / float(len(keys))
    return {key: probability for key in keys}


def weighted_choice(rng, probabilities: Mapping[str, float], *, sort_keys: bool = False) -> str:
    """Sample one key from a probability map using cumulative weights."""
    items = sorted(probabilities.items()) if bool(sort_keys) else list(probabilities.items())
    if not items:
        raise ValueError("cannot sample from an empty probability map")

    roll = float(rng.random())
    cumulative = 0.0
    last_key = str(items[-1][0])
    for key, probability in items:
        cumulative += float(probability)
        if roll <= cumulative:
            return str(key)
    return last_key
