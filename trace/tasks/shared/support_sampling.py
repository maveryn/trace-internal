"""Shared deterministic integer-support sampling helpers for task domains."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence, Tuple

from ...core.seed import hash64, spawn_rng
from .config_defaults import group_default
from .deterministic_sampling import resolve_selection_index, uniform_probability_map


def resolve_integer_support(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
) -> Tuple[int, ...]:
    """Resolve one explicit integer support list from params/defaults."""

    raw_support = params.get(str(key), group_default(gen_defaults, str(key), tuple(int(value) for value in fallback)))
    support: list[int] = []
    for raw_value in raw_support:
        value = int(raw_value)
        if value not in support:
            support.append(int(value))
    if not support:
        raise ValueError(f"{key} must contain at least one integer")
    return tuple(sorted(support))


def resolve_integer_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str,
    use_instance_seed_cycle: bool = False,
    namespace_explicit_sampling_index: bool = False,
) -> Tuple[int, Dict[str, float]]:
    """Resolve one integer choice from explicit support with optional balanced cycling.

    When `namespace_explicit_sampling_index` is enabled, review-time `_sampling_index`
    is mixed with `namespace` before cycling the support so multiple balanced axes do
    not alias the same raw review index.
    """

    support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key=str(support_key),
        fallback=fallback_support,
    )
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported {explicit_key}: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    balanced_enabled = bool(params.get(str(balanced_flag_key), group_default(gen_defaults, str(balanced_flag_key), True)))
    if bool(balanced_enabled):
        explicit_sampling_index = params.get("_sampling_index")
        if bool(namespace_explicit_sampling_index) and explicit_sampling_index is not None:
            raw_index = abs(int(explicit_sampling_index))
            support_size = int(len(support))
            if int(support_size) <= 1:
                selection_index = int(raw_index)
            else:
                offset = abs(int(hash64(0, str(namespace), 1))) % int(support_size)
                multiplier_candidates = [
                    candidate
                    for candidate in range(1, int(support_size))
                    if math.gcd(int(candidate), int(support_size)) == 1
                ]
                if not multiplier_candidates:
                    multiplier = 1
                else:
                    multiplier = int(
                        multiplier_candidates[
                            abs(int(hash64(0, str(namespace), 2)))
                            % len(multiplier_candidates)
                        ]
                    )
                selection_index = int((int(raw_index) * int(multiplier)) + int(offset))
        elif bool(use_instance_seed_cycle) and explicit_sampling_index is None:
            selection_index = abs(int(instance_seed))
        else:
            selection_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=str(namespace),
            )
        selected = int(support[int(selection_index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), str(namespace))
        selected = int(support[int(rng.randrange(len(support)))])
    return int(selected), uniform_probability_map(support)


__all__ = [
    "resolve_integer_choice",
    "resolve_integer_support",
]
