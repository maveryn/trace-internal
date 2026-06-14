"""Sampling helpers for indoor-room illustration tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ....shared.config_defaults import group_default
from ....shared.deterministic_sampling import resolve_selection_index
from ...shared.object_library import display_name_for_object_type
from .state import INDOOR_THEME_IDS


def display_name(object_type: str) -> str:
    return display_name_for_object_type(str(object_type))


def uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def theme_support(params: Mapping[str, Any], generation_defaults: Mapping[str, Any]) -> tuple[str, ...]:
    raw = params.get("theme_support", group_default(generation_defaults, "indoor_theme_support", INDOOR_THEME_IDS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("theme_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(INDOOR_THEME_IDS))
    if not supported:
        raise ValueError("theme_support resolved no supported indoor themes")
    return tuple(dict.fromkeys(supported))


def typed_support(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    param_key: str,
    default_key: str,
    fallback: Sequence[str],
    error_name: str,
) -> tuple[str, ...]:
    raw = params.get(param_key, group_default(generation_defaults, default_key, tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError(f"{param_key} must be a sequence")
    allowed = set(str(value) for value in fallback)
    supported = tuple(str(value) for value in raw if str(value) in allowed)
    if not supported:
        raise ValueError(f"{error_name} resolved no supported values")
    return tuple(dict.fromkeys(supported))


def support_choice(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    support: Sequence[str],
    explicit_key: str,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get(explicit_key)
    values = tuple(str(value) for value in support)
    if explicit is not None:
        choice = str(explicit)
        if choice not in set(values):
            raise ValueError(f"{explicit_key} must be one of {values}")
        return choice, uniform_string_probability_map(values, selected=choice)
    selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    choice = str(values[int(selection_index) % len(values)])
    return choice, uniform_string_probability_map(values)


__all__ = [
    "display_name",
    "support_choice",
    "theme_support",
    "typed_support",
    "uniform_string_probability_map",
]
