"""Render parameter helpers for two-anchor icon scenes."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....shared.config_defaults import group_default
from ...shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, resolve_icon_rgb_param

from .defaults import TwoAnchorDefaults


def resolve_two_anchor_render_params(
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    fallback_defaults: TwoAnchorDefaults,
    instance_seed: int,
) -> Dict[str, Any]:
    """Resolve common icon render params plus two-anchor scene chrome."""

    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=render_defaults,
        fallback_defaults=fallback_defaults,
        instance_seed=int(instance_seed),
    )
    for extra_key, fallback_value in (
        ("anchor_highlight_padding_px", fallback_defaults.anchor_highlight_padding_px),
        ("anchor_highlight_radius_px", fallback_defaults.anchor_highlight_radius_px),
        ("anchor_label_font_size_px", fallback_defaults.anchor_label_font_size_px),
        ("strip_boundary_margin_px", fallback_defaults.strip_boundary_margin_px),
        ("strip_span_ratio_min", fallback_defaults.strip_span_ratio_min),
        ("strip_span_ratio_max", fallback_defaults.strip_span_ratio_max),
        ("strip_outside_ratio_min", fallback_defaults.strip_outside_ratio_min),
        ("anchor_edge_padding_px", fallback_defaults.anchor_edge_padding_px),
    ):
        render_params[str(extra_key)] = params.get(
            str(extra_key),
            group_default(render_defaults, str(extra_key), fallback_value),
        )
    render_params["anchor_outline_rgb"] = resolve_icon_rgb_param(
        params=params,
        render_defaults=render_defaults,
        key="anchor_outline_rgb",
        fallback=fallback_defaults.anchor_outline_rgb,
        instance_seed=int(instance_seed),
    )
    render_params["anchor_label_color_rgb"] = resolve_icon_rgb_param(
        params=params,
        render_defaults=render_defaults,
        key="anchor_label_color_rgb",
        fallback=fallback_defaults.anchor_label_color_rgb,
        instance_seed=int(instance_seed),
    )
    return render_params


def two_anchor_style_trace(
    *,
    render_params: Mapping[str, Any],
    sampled_palette_rgb,
) -> Dict[str, Any]:
    """Serialize two-anchor style metadata."""

    return {
        **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=sampled_palette_rgb),
        "strip_boundary_margin_px": int(render_params["strip_boundary_margin_px"]),
        "strip_span_ratio_min": float(render_params["strip_span_ratio_min"]),
        "strip_span_ratio_max": float(render_params["strip_span_ratio_max"]),
        "strip_outside_ratio_min": float(render_params["strip_outside_ratio_min"]),
        "anchor_highlight_padding_px": int(render_params["anchor_highlight_padding_px"]),
        "anchor_highlight_radius_px": int(render_params["anchor_highlight_radius_px"]),
        "anchor_outline_rgb": [int(v) for v in render_params["anchor_outline_rgb"]],
        "anchor_label_color_rgb": [int(v) for v in render_params["anchor_label_color_rgb"]],
        "anchor_label_font_size_px": int(render_params["anchor_label_font_size_px"]),
    }


__all__ = ["resolve_two_anchor_render_params", "two_anchor_style_trace"]

