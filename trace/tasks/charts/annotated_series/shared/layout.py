"""Layout helpers for the annotated-series chart scene."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.seed import spawn_rng
from trace.tasks.charts.annotated_series.shared.defaults import (
    CONTEXT_PARAM_KEYS,
    FALLBACK_CHART_DEFAULTS,
    SCENE_NAMESPACE,
    rendering_value,
)
from trace.tasks.shared.visual_style.context_layer import resolve_dashboard_context_layout


def context_params(params: Mapping[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key in CONTEXT_PARAM_KEYS:
        value = rendering_value(params, str(key), None)
        if value is not None:
            resolved[str(key)] = value
    return resolved


def choose_context_mode(*, params: Mapping[str, Any], instance_seed: int) -> str:
    if not bool(rendering_value(params, "context_text_enabled", False)):
        return "clean"
    supported = ("clean", "light_context", "right_sidebar", "bottom_band")
    raw_weights = rendering_value(
        params,
        "context_text_mode_weights",
        {"clean": 0.5, "light_context": 0.3, "right_sidebar": 0.1, "bottom_band": 0.1},
    )
    if not isinstance(raw_weights, Mapping):
        raw_weights = {"clean": 1.0}
    weights: list[tuple[str, float]] = []
    for mode in supported:
        weight = max(0.0, float(raw_weights.get(str(mode), 0.0)))
        if weight > 0.0:
            weights.append((str(mode), float(weight)))
    if not weights:
        return "clean"
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.context_text_mode")
    cursor = rng.random() * sum(weight for _, weight in weights)
    running = 0.0
    for mode, weight in weights:
        running += float(weight)
        if cursor <= running:
            return str(mode)
    return str(weights[-1][0])


def resolve_context_layout(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
) -> dict[str, Any]:
    """Resolve non-answer context placement for the annotated-series scene.

    This helper chooses scene-level context geometry only. It does not know the
    public task objective, answer labels, or annotation target.
    """
    mode = choose_context_mode(params=params, instance_seed=int(instance_seed))
    resolved_context_params = context_params(params)
    top_reserved = int(resolved_context_params.get("context_text_top_reserved_px", 64))
    bottom_reserved = int(resolved_context_params.get("context_text_bottom_reserved_px", 28))
    if str(mode) == "clean":
        return {
            "enabled": False,
            "mode": "clean",
            "layout_mode": "clean",
            "placement": "none",
            "context_params": resolved_context_params,
            "top_reserved_px": int(top_reserved),
            "bottom_reserved_px": int(bottom_reserved),
        }
    if str(mode) == "light_context":
        return {
            "enabled": True,
            "mode": "light_context",
            "layout_mode": "light_context",
            "placement": "top_bottom_notes",
            "box_count": 0,
            "context_params": resolved_context_params,
            "top_reserved_px": int(top_reserved),
            "bottom_reserved_px": int(bottom_reserved),
        }
    placement = "right_sidebar" if str(mode) == "right_sidebar" else "bottom_band"
    layout = resolve_dashboard_context_layout(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.context",
        params={
            **resolved_context_params,
            "context_text_enabled": True,
            "context_text_placement": str(placement),
        },
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        top_reserved_px=int(top_reserved),
        bottom_reserved_px=int(bottom_reserved),
        left_margin_px=int(resolved_context_params.get("context_text_left_margin_px", 24)),
        right_margin_px=int(resolved_context_params.get("context_text_right_margin_px", 24)),
    )
    return {
        **dict(layout),
        "enabled": True,
        "mode": str(mode),
        "context_params": resolved_context_params,
    }


def apply_context_margin_overrides(
    params: Mapping[str, Any],
    *,
    context_layout: Mapping[str, Any],
) -> dict[str, Any]:
    resolved = dict(params)
    if not bool(context_layout.get("enabled", False)):
        return resolved

    base_left = int(rendering_value(params, "plot_margin_left_px", FALLBACK_CHART_DEFAULTS.plot_margin_left_px))
    base_right = int(rendering_value(params, "plot_margin_right_px", FALLBACK_CHART_DEFAULTS.plot_margin_right_px))
    base_bottom = int(
        rendering_value(params, "plot_margin_bottom_px", FALLBACK_CHART_DEFAULTS.plot_margin_bottom_px)
    )
    placement = str(context_layout.get("placement", "none"))
    if placement == "right_sidebar":
        sidebar_width = int(context_layout.get("sidebar_width_px", 0))
        sidebar_gap = int(context_layout.get("sidebar_gap_px", 14))
        resolved["plot_margin_right_px"] = int(base_right + max(0, sidebar_width) + max(0, sidebar_gap))
        resolved["plot_margin_left_px"] = int(base_left)
        resolved["layout_jitter_x_px"] = 0
    elif placement == "bottom_band":
        bottom_height = int(context_layout.get("bottom_band_height_px", 0))
        bottom_gap = int(context_layout.get("bottom_band_gap_px", 14))
        resolved["plot_margin_bottom_px"] = int(base_bottom + max(0, bottom_height) + max(0, bottom_gap))
        resolved["layout_jitter_y_px"] = 0
    return resolved


__all__ = [
    "apply_context_margin_overrides",
    "choose_context_mode",
    "context_params",
    "resolve_context_layout",
]
