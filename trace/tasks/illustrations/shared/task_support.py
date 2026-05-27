"""Shared sampling and config helpers for illustration tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map


def bounds(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    low_key: str,
    high_key: str,
    fallback_low: int,
    fallback_high: int,
    *,
    min_low: int = 1,
) -> Tuple[int, int]:
    """Resolve integer low/high bounds from params, group defaults, or fallback."""

    low = int(params.get(low_key, group_default(defaults, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(defaults, high_key, fallback_high)))
    if low < int(min_low) or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} bounds")
    return int(low), int(high)


def uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    """Return a uniform probability map over string support."""

    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def sample_count(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    low: int,
    high: int,
    explicit_key: str,
    cycle_index: int | None = None,
) -> Tuple[int, Dict[str, float]]:
    """Sample an integer count with deterministic seeded cycling."""

    support = tuple(range(int(low), int(high) + 1))
    if not support:
        raise ValueError(f"{explicit_key} has no feasible support")
    explicit = params.get(explicit_key)
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError(f"{explicit_key} is outside configured support")
        return int(value), dict(uniform_probability_map(support, selected=int(value)))
    if cycle_index is None:
        cycle_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = int(support[int(cycle_index) % len(support)])
    return int(value), dict(uniform_probability_map(support))


def string_support(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[str],
    *,
    valid_values: Sequence[str],
    min_count: int = 1,
) -> Tuple[str, ...]:
    """Resolve and validate a configured string support list."""

    raw = params.get(str(key), group_default(defaults, str(key), fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError(f"{key} must be a sequence")
    valid = set(str(value) for value in valid_values)
    support = tuple(str(value) for value in raw if str(value) in valid)
    support = tuple(dict.fromkeys(support))
    if len(support) < int(min_count):
        raise ValueError(f"{key} must contain at least {min_count} supported values")
    return support


def query_support(params: Mapping[str, Any], defaults: Mapping[str, Any], fallback: Sequence[str]) -> Tuple[str, ...]:
    """Resolve query-id support."""

    return string_support(params, defaults, "query_id_support", fallback, valid_values=fallback, min_count=1)


def style_weights(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    style_ids: Sequence[str],
) -> Dict[str, float]:
    """Resolve non-semantic illustration style weights."""

    raw = params.get("style_weights", group_default(render_defaults, "style_weights", {style: 1.0 for style in style_ids}))
    if not isinstance(raw, Mapping):
        raise ValueError("style_weights must be a mapping")
    return {str(key): max(0.0, float(value)) for key, value in raw.items()}


def setting_weights(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    key: str,
    setting_ids: Sequence[str],
) -> Dict[str, float]:
    """Resolve non-semantic illustration scene-setting weights."""

    raw = params.get(str(key), group_default(render_defaults, str(key), {setting: 1.0 for setting in setting_ids}))
    if not isinstance(raw, Mapping):
        raise ValueError(f"{key} must be a mapping")
    return {str(name): max(0.0, float(value)) for name, value in raw.items()}


def render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    prefix: str,
    fallback_width: int,
    fallback_height: int,
    fallback_scale: int,
) -> Dict[str, int]:
    """Resolve prefix-scoped illustration canvas render parameters."""

    return {
        "canvas_width": int(params.get("canvas_width", group_default(render_defaults, f"{prefix}_canvas_width", fallback_width))),
        "canvas_height": int(params.get("canvas_height", group_default(render_defaults, f"{prefix}_canvas_height", fallback_height))),
        "render_scale": int(params.get("render_scale", group_default(render_defaults, f"{prefix}_render_scale", fallback_scale))),
    }


def spawned_task_rng(instance_seed: int, task_id: str, attempt_index: int):
    """Return the standard illustration-task sampling RNG."""

    return spawn_rng(int(instance_seed), f"{task_id}:sample", int(attempt_index))


__all__ = [
    "bounds",
    "query_support",
    "render_params",
    "sample_count",
    "setting_weights",
    "spawned_task_rng",
    "string_support",
    "style_weights",
    "uniform_string_probability_map",
]
