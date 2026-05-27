"""Shared sampling helpers for park/playground illustration tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ...shared.config_defaults import group_default
from .object_library import STYLE_IDS
from .park_playground_scene import PARK_EQUIPMENT_TYPES, PARK_PERSON_ACTIVITIES, PARK_SETTING_IDS, PARK_ZONE_TYPES
from .task_support import (
    bounds,
    render_params as _shared_render_params,
    sample_count,
    spawned_task_rng,
    style_weights as _shared_style_weights,
    uniform_string_probability_map,
)


def activity_support(params: Mapping[str, Any], defaults: Mapping[str, Any], *, fallback: Sequence[str]) -> Tuple[str, ...]:
    """Resolve supported park person activity ids."""

    raw = params.get("activity_support", group_default(defaults, "activity_support", fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("activity_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(PARK_PERSON_ACTIVITIES))
    if len(support) < 2:
        raise ValueError("activity_support must contain at least two activities")
    return tuple(dict.fromkeys(support))


def equipment_support(params: Mapping[str, Any], defaults: Mapping[str, Any], *, fallback: Sequence[str] = PARK_EQUIPMENT_TYPES) -> Tuple[str, ...]:
    """Resolve supported park playground equipment ids."""

    raw = params.get("equipment_type_support", group_default(defaults, "equipment_type_support", fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("equipment_type_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(PARK_EQUIPMENT_TYPES))
    if len(support) < 2:
        raise ValueError("equipment_type_support must contain at least two equipment types")
    return tuple(dict.fromkeys(support))


def zone_support(params: Mapping[str, Any], defaults: Mapping[str, Any], *, fallback: Sequence[str] = PARK_ZONE_TYPES) -> Tuple[str, ...]:
    """Resolve supported semantic park zone ids."""

    raw = params.get("zone_support", group_default(defaults, "zone_support", fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("zone_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(PARK_ZONE_TYPES))
    if len(support) < 2:
        raise ValueError("zone_support must contain at least two park zones")
    return tuple(dict.fromkeys(support))


def render_params(params: Mapping[str, Any], render_defaults: Mapping[str, Any], *, fallback_width: int, fallback_height: int, fallback_scale: int) -> Dict[str, int]:
    """Resolve park canvas render parameters."""

    return _shared_render_params(
        params,
        render_defaults,
        prefix="park",
        fallback_width=fallback_width,
        fallback_height=fallback_height,
        fallback_scale=fallback_scale,
    )


def style_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve illustration style weights."""

    return _shared_style_weights(params, render_defaults, style_ids=STYLE_IDS)


def setting_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve park setting weights."""

    raw = params.get("park_setting_weights", group_default(render_defaults, "park_setting_weights", {setting: 1.0 for setting in PARK_SETTING_IDS}))
    if not isinstance(raw, Mapping):
        raise ValueError("park_setting_weights must be a mapping")
    return {str(key): max(0.0, float(value)) for key, value in raw.items()}


__all__ = [
    "activity_support",
    "bounds",
    "equipment_support",
    "render_params",
    "sample_count",
    "setting_weights",
    "spawned_task_rng",
    "style_weights",
    "uniform_string_probability_map",
    "zone_support",
]
