"""Task-level config fallback helpers shared across task modules."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ...core.task_group_config import resolve_task_group_section_defaults


def group_default(mapping: Mapping[str, Any], key: str, fallback: Any) -> Any:
    """Return `mapping[key]` when present; otherwise return `fallback`."""
    if key in mapping:
        return mapping.get(key)
    return fallback


def required_group_default(mapping: Mapping[str, Any], key: str, *, context: str) -> Any:
    """Return a required config value and fail fast when missing/empty."""
    if key not in mapping:
        raise ValueError(f"missing required config key '{key}' in {context}")
    value = mapping.get(key)
    if value is None:
        raise ValueError(f"config key '{key}' in {context} cannot be null")
    if isinstance(value, str) and not str(value).strip():
        raise ValueError(f"config key '{key}' in {context} cannot be empty")
    return value


def required_group_defaults(
    mapping: Mapping[str, Any],
    keys: Sequence[str],
    *,
    context: str,
) -> Dict[str, Any]:
    """Return required config values for `keys` with one fail-fast validation pass."""
    return {
        str(key): required_group_default(mapping, str(key), context=context)
        for key in [str(item) for item in keys]
    }


def resolve_optional_int_bounds(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    context: str,
) -> Tuple[int | None, int | None]:
    """Resolve optional inclusive integer bounds from params/defaults."""
    raw_min = params.get(str(min_key), group_default(defaults, str(min_key), None))
    raw_max = params.get(str(max_key), group_default(defaults, str(max_key), None))
    min_value = int(raw_min) if raw_min is not None else None
    max_value = int(raw_max) if raw_max is not None else None
    if min_value is not None and max_value is not None and int(min_value) > int(max_value):
        raise ValueError(f"{min_key} must be <= {max_key} in {context}")
    return min_value, max_value


def resolve_required_int_bounds(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    context: str,
) -> Tuple[int, int]:
    """Resolve required inclusive integer bounds from params/defaults/fallbacks."""
    min_value = int(params.get(str(min_key), group_default(defaults, str(min_key), int(fallback_min))))
    max_value = int(params.get(str(max_key), group_default(defaults, str(max_key), int(fallback_max))))
    if int(min_value) > int(max_value):
        raise ValueError(f"{min_key} must be <= {max_key} in {context}")
    return int(min_value), int(max_value)


def resolve_required_float_bounds(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: float,
    fallback_max: float,
    context: str,
) -> Tuple[float, float]:
    """Resolve required inclusive float bounds from params/defaults/fallbacks."""
    min_value = float(params.get(str(min_key), group_default(defaults, str(min_key), float(fallback_min))))
    max_value = float(params.get(str(max_key), group_default(defaults, str(max_key), float(fallback_max))))
    if float(min_value) > float(max_value):
        raise ValueError(f"{min_key} must be <= {max_key} in {context}")
    return float(min_value), float(max_value)


def split_generation_rendering_prompt_defaults(
    mapping: Mapping[str, Any],
    *,
    task_id: str | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Return `generation`, `rendering`, and `prompt` defaults sections."""
    generation = resolve_task_group_section_defaults(mapping, "generation", task_id=task_id)
    rendering = resolve_task_group_section_defaults(mapping, "rendering", task_id=task_id)
    prompt = resolve_task_group_section_defaults(mapping, "prompt", task_id=task_id)
    return generation, rendering, prompt
