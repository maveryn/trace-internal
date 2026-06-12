"""Chart-domain adapter for shared structured-information styling."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Any, Mapping, Sequence

from ....core.scene_config import get_scene_defaults
from ...shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ...shared.visual_style.information_scene import (
    Color,
    InformationSceneStyle,
    make_information_scene_background,
    resolve_information_scene_style_from_request,
)
from ...shared.visual_style.request import (
    build_visual_style_request,
    resolve_style_bool,
)
from .chart_scene import ChartRenderParams


ChartInformationStyle = InformationSceneStyle


@lru_cache(maxsize=64)
def _chart_scene_render_defaults(scene_id: str) -> dict[str, Any]:
    """Return shared chart rendering defaults for scene-style resolution."""

    try:
        defaults = get_scene_defaults("charts", str(scene_id))
    except Exception:
        return {}
    if not isinstance(defaults, Mapping):
        return {}
    _gen, rendering, _prompt = split_scene_generation_rendering_prompt_defaults(
        defaults,
        task_id=f"charts_{str(scene_id)}_style_defaults",
    )
    return dict(rendering)


def resolve_chart_information_style(
    *,
    instance_seed: int,
    params: Mapping[str, Any] | None,
    scene_id: str,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool | None = None,
    allow_colored_surface: bool | None = None,
) -> tuple[ChartInformationStyle, dict[str, Any]]:
    """Resolve one chart presentation style without changing semantic marks."""

    routing_key = str(scene_id)
    default_params = _chart_scene_render_defaults(str(scene_id))
    resolved_params = {**default_params, **dict(params or {})}
    resolved_allow_dark = (
        resolve_style_bool(resolved_params, "information_scene_allow_dark", False)
        if allow_dark is None
        else bool(allow_dark)
    )
    resolved_allow_colored_surface = (
        resolve_style_bool(resolved_params, "information_scene_allow_colored_surface", True)
        if allow_colored_surface is None
        else bool(allow_colored_surface)
    )
    request = build_visual_style_request(
        domain="charts",
        scene_id=str(scene_id),
        routing_key=str(routing_key),
        instance_seed=int(instance_seed),
        params=resolved_params,
        style_family="information_scene",
        allow_dark=bool(resolved_allow_dark),
        allow_colored_surface=bool(resolved_allow_colored_surface),
        protected_colors=protected_colors or (),
        required_text_roles=("chart_label", "axis_tick", "legend_label"),
    )
    return resolve_information_scene_style_from_request(
        request,
        treatments=resolved_params.get("information_scene_treatments"),
        treatment_weights=resolved_params.get("information_scene_treatment_weights", {}),
        palettes=resolved_params.get("information_scene_palettes"),
        palette_weights=resolved_params.get("information_scene_palette_weights", {}),
        chrome_modes=resolved_params.get("information_scene_chrome_modes"),
        chrome_mode_weights=resolved_params.get("information_scene_chrome_mode_weights", {}),
    )


def make_chart_information_background(
    *,
    canvas_width: int,
    canvas_height: int,
    style: ChartInformationStyle,
    instance_seed: int,
    namespace: str,
) -> tuple[Any, dict[str, Any]]:
    """Create a chart background from the shared information style."""

    return make_information_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def apply_chart_information_style(
    render_params: ChartRenderParams,
    style: ChartInformationStyle,
) -> ChartRenderParams:
    """Map non-semantic shared style roles into chart render parameters."""

    return replace(
        render_params,
        axis_color_rgb=tuple(int(value) for value in style.axis_rgb),
        grid_color_rgb=tuple(int(value) for value in style.grid_rgb),
        text_color_rgb=tuple(int(value) for value in style.text_rgb),
        text_stroke_rgb=tuple(int(value) for value in style.text_stroke_rgb),
        plot_fill_rgb=tuple(int(value) for value in style.surface_rgb),
        guide_line_color_rgb=tuple(int(value) for value in style.guide_rgb),
    )


def prepare_chart_information_scene(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_id: str,
    render_params: ChartRenderParams,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool | None = None,
    allow_colored_surface: bool | None = None,
) -> tuple[ChartRenderParams, Any, dict[str, Any], dict[str, Any]]:
    """Resolve chart information style, apply it, and create the background."""

    style, style_meta = resolve_chart_information_style(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=str(scene_id),
        protected_colors=protected_colors or (),
        allow_dark=allow_dark,
        allow_colored_surface=allow_colored_surface,
    )
    styled_render_params = apply_chart_information_style(render_params, style)
    background, background_meta = make_chart_information_background(
        canvas_width=int(styled_render_params.canvas_width),
        canvas_height=int(styled_render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=f"charts.{str(scene_id)}.information_scene_background",
    )
    return styled_render_params, background, background_meta, style_meta


__all__ = [
    "ChartInformationStyle",
    "apply_chart_information_style",
    "make_chart_information_background",
    "prepare_chart_information_scene",
    "resolve_chart_information_style",
]
