"""Sampling helpers for isometric harbor tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from trace.tasks.illustrations.shared.canvas_profiles import resolve_canvas_profile
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map


@dataclass(frozen=True)
class CountTaskSampleSpec:
    """Resolved sampling state for one harbor count task instance."""

    selected_key: str
    prompt_query_key: str
    query_probabilities: dict[str, float]
    target_count: int
    target_count_probabilities: dict[str, float]
    answer_count_support: tuple[int, ...]
    answer_count_probabilities: dict[str, float]
    canvas_width: int
    canvas_height: int
    canvas_profile: str
    canvas_profile_probabilities: dict[str, float]


def support_ints(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    support_key: str,
    fallback: Sequence[int],
) -> tuple[int, ...]:
    """Resolve a numeric support list from params/defaults."""

    raw = params.get(str(support_key), group_default(defaults, str(support_key), tuple(fallback)))
    values = (raw,) if isinstance(raw, int) else tuple(raw if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) else ())
    support = tuple(dict.fromkeys(int(value) for value in values))
    if not support:
        raise ValueError(f"{support_key} must include at least one value")
    return support


def select_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback: Sequence[int],
    namespace: str,
) -> tuple[int, dict[str, float], tuple[int, ...]]:
    """Select a count from finite support, using review cursors when present."""

    support = support_ints(params, defaults, support_key=str(support_key), fallback=fallback)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError(f"{explicit_key} must be one of {support}")
        return value, {str(value): 1.0}, support
    if params.get("_sample_cursor") is not None:
        index = abs(int(params["_sample_cursor"]))
    else:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = int(support[int(index) % len(support)])
    return value, dict(uniform_probability_map(support)), support


__all__ = ["CountTaskSampleSpec", "select_count", "support_ints"]
