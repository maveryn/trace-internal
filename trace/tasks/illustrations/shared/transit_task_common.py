"""Shared sampling helpers for transit-terminal illustration tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ...shared.config_defaults import group_default
from .object_library import STYLE_IDS
from .task_support import (
    bounds,
    render_params as _shared_render_params,
    sample_count,
    spawned_task_rng,
    style_weights as _shared_style_weights,
    uniform_string_probability_map,
)
from .transit_terminal_scene import TRANSIT_BOARDING_AREA_IDS, TRANSIT_SETTING_IDS


def area_support(params: Mapping[str, Any], defaults: Mapping[str, Any], *, fallback: Sequence[str] = TRANSIT_BOARDING_AREA_IDS) -> Tuple[str, ...]:
    """Resolve supported transit boarding-area ids."""

    raw = params.get("boarding_area_support", group_default(defaults, "boarding_area_support", fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("boarding_area_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(TRANSIT_BOARDING_AREA_IDS))
    if len(support) < 2:
        raise ValueError("boarding_area_support must contain at least two boarding areas")
    return tuple(dict.fromkeys(support))


def render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    fallback_width: int,
    fallback_height: int,
    fallback_scale: int,
    instance_seed: int | None = None,
    namespace: str = "transit_terminal:canvas_profile",
) -> Dict[str, Any]:
    """Resolve transit canvas render parameters."""

    return _shared_render_params(
        params,
        render_defaults,
        prefix="transit",
        fallback_width=fallback_width,
        fallback_height=fallback_height,
        fallback_scale=fallback_scale,
        instance_seed=instance_seed,
        namespace=namespace,
    )


def style_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve illustration style weights."""

    return _shared_style_weights(params, render_defaults, style_ids=STYLE_IDS)


def setting_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve transit setting weights."""

    raw = params.get("transit_setting_weights", group_default(render_defaults, "transit_setting_weights", {setting: 1.0 for setting in TRANSIT_SETTING_IDS}))
    if not isinstance(raw, Mapping):
        raise ValueError("transit_setting_weights must be a mapping")
    return {str(key): max(0.0, float(value)) for key, value in raw.items()}


__all__ = [
    "area_support",
    "bounds",
    "render_params",
    "sample_count",
    "setting_weights",
    "spawned_task_rng",
    "style_weights",
    "uniform_string_probability_map",
]
