"""Sampling helpers for RPG dungeon public tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.seed import hash64
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map


def select_count_from_support(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    max_value: int | None = None,
) -> tuple[int, dict[str, float]]:
    """Select an integer count from task params, defaults, or fallback support."""

    raw_support = params.get(str(support_key), group_default(gen_defaults, str(support_key), tuple(fallback_support)))
    if isinstance(raw_support, int):
        support = (int(raw_support),)
    else:
        support = tuple(dict.fromkeys(int(value) for value in raw_support))
    if max_value is not None:
        support = tuple(value for value in support if int(value) <= int(max_value))
    if not support:
        raise ValueError(f"{support_key} must contain at least one value")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError(f"{explicit_key} must be one of {support}")
        return int(value), {str(value): 1.0}
    if params.get("_sample_cursor") is not None:
        value = support[abs(int(params["_sample_cursor"])) % len(support)]
    else:
        index = resolve_selection_index(
            params=params,
            instance_seed=hash64(int(instance_seed), str(namespace)),
            namespace=str(namespace),
        )
        value = support[int(index) % len(support)]
    return int(value), dict(uniform_probability_map(support))


__all__ = ["select_count_from_support"]
