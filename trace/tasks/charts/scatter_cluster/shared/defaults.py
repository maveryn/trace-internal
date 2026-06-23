"""Configuration and render defaults for scatter-cluster charts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.scene_config import get_scene_defaults
from trace.tasks.charts.shared.visual_defaults import (
    load_chart_scene_background_defaults,
    load_chart_scene_noise_defaults,
)
from trace.tasks.shared.config_defaults import (
    group_default,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.font_assets import font_asset_version, sample_font_family
from trace.tasks.shared.render_variation import (
    apply_layout_jitter_to_margins,
    resolve_render_int,
    resolve_render_rgb,
)

from .state import PROMPT_BUNDLE_ID, SCENE_ID, SCENE_NAMESPACE, RGB, ScatterClusterRenderParams


SCENE_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
GEN_DEFAULTS, RENDER_DEFAULTS, PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    SCENE_DEFAULTS if isinstance(SCENE_DEFAULTS, Mapping) else {},
    task_id=SCENE_NAMESPACE,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(
        resolve_render_int(
            params,
            RENDER_DEFAULTS,
            str(key),
            int(fallback),
            instance_seed=render_style_seed(params),
            namespace=SCENE_NAMESPACE,
        )
    )


def resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=render_style_seed(params),
        namespace=SCENE_NAMESPACE,
    )


def gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(GEN_DEFAULTS, str(key), int(fallback))))


def gen_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(GEN_DEFAULTS, str(key), float(fallback))))


def sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def font_assets_payload(*, chart_font_family: str) -> dict[str, str]:
    return {
        "font_asset_version": font_asset_version(),
        "chart_font_family": str(chart_font_family),
    }


def palette(params: Mapping[str, Any]) -> tuple[RGB, ...]:
    raw = params.get("cluster_palette_rgb", RENDER_DEFAULTS.get("cluster_palette_rgb", ()))
    colors: list[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            colors.append(as_rgb(item, (60, 110, 180)))
    if len(colors) >= 8:
        return tuple(colors[:8])
    return (
        (38, 101, 176),
        (218, 91, 75),
        (56, 150, 96),
        (142, 92, 188),
        (218, 145, 46),
        (78, 159, 191),
        (188, 87, 132),
        (109, 125, 55),
    )


def resolve_render_params(params: Mapping[str, Any]) -> ScatterClusterRenderParams:
    margin_left = resolve_int(params, "plot_margin_left_px", 110)
    margin_right = resolve_int(params, "plot_margin_right_px", 260)
    margin_top = resolve_int(params, "plot_margin_top_px", 72)
    margin_bottom = resolve_int(params, "plot_margin_bottom_px", 112)
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=RENDER_DEFAULTS,
        instance_seed=render_style_seed(params),
        namespace=f"{SCENE_NAMESPACE}.layout",
    )
    return ScatterClusterRenderParams(
        canvas_width=resolve_int(params, "canvas_width", 1280),
        canvas_height=resolve_int(params, "canvas_height", 820),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=resolve_int(params, "axis_line_width_px", 2),
        grid_line_width_px=resolve_int(params, "grid_line_width_px", 1),
        tick_length_px=resolve_int(params, "tick_length_px", 8),
        point_radius_px=resolve_int(params, "point_radius_px", 7),
        tick_font_size_px=resolve_int(params, "tick_font_size_px", 17),
        legend_font_size_px=resolve_int(params, "legend_font_size_px", 22),
        title_font_size_px=resolve_int(params, "title_font_size_px", 26),
        cluster_hull_padding_px=resolve_int(params, "cluster_hull_padding_px", 14),
        axis_color_rgb=resolve_rgb(params, "axis_color_rgb", (74, 78, 86)),
        grid_color_rgb=resolve_rgb(params, "grid_color_rgb", (225, 228, 234)),
        text_color_rgb=resolve_rgb(params, "text_color_rgb", (38, 41, 48)),
        text_stroke_rgb=resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        plot_fill_rgb=resolve_rgb(params, "plot_fill_rgb", (255, 255, 255)),
        panel_fill_rgb=resolve_rgb(params, "panel_fill_rgb", (252, 253, 255)),
        panel_border_rgb=resolve_rgb(params, "panel_border_rgb", (204, 210, 220)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def resolved_prompt_bundle_id() -> str:
    return str(PROMPT_DEFAULTS.get("bundle_id", PROMPT_BUNDLE_ID))
