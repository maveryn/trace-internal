"""Render-parameter helpers for the pattern-grid icons scene."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....shared.config_defaults import group_default
from ...shared.icon_task_rendering import resolve_icon_cell_render_params

from .defaults import PatternGridDefaults


_DEFAULTS = PatternGridDefaults()


def resolve_pattern_grid_render_params(
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Resolve scene-level render params and pattern-grid-specific knobs."""

    render_params = resolve_icon_cell_render_params(
        params=params,
        render_defaults=render_defaults,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    for key in (
        "color_icon_size_min_px",
        "color_icon_size_max_px",
        "size_icon_size_min_px",
        "size_icon_size_max_px",
        "size_level_gap_px",
    ):
        render_params[str(key)] = int(
            params.get(str(key), group_default(render_defaults, str(key), getattr(_DEFAULTS, str(key))))
        )
    return render_params


__all__ = ["resolve_pattern_grid_render_params"]
