"""Chart-domain adapter for shared structured-information styling."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from ...shared.visual_style.information_scene import (
    Color,
    InformationSceneStyle,
    make_information_scene_background,
    resolve_information_scene_style,
)
from .chart_scene import ChartRenderParams


ChartInformationStyle = InformationSceneStyle


def resolve_chart_information_style(
    *,
    instance_seed: int,
    params: Mapping[str, Any] | None,
    scene_id: str,
    task_group: str,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool = False,
) -> tuple[ChartInformationStyle, dict[str, Any]]:
    """Resolve one chart presentation style without changing semantic marks."""

    resolved_params = params or {}
    return resolve_information_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"charts.{str(task_group)}.{str(scene_id)}.information_scene_style",
        treatments=resolved_params.get("information_scene_treatments"),
        treatment_weights=resolved_params.get("information_scene_treatment_weights", {}),
        palettes=resolved_params.get("information_scene_palettes"),
        palette_weights=resolved_params.get("information_scene_palette_weights", {}),
        chrome_modes=resolved_params.get("information_scene_chrome_modes"),
        chrome_mode_weights=resolved_params.get("information_scene_chrome_mode_weights", {}),
        allow_dark=bool(allow_dark),
        protected_colors=protected_colors or (),
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
    task_group: str,
    render_params: ChartRenderParams,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool = False,
) -> tuple[ChartRenderParams, Any, dict[str, Any], dict[str, Any]]:
    """Resolve chart information style, apply it, and create the background."""

    style, style_meta = resolve_chart_information_style(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=str(scene_id),
        task_group=str(task_group),
        protected_colors=protected_colors or (),
        allow_dark=bool(allow_dark),
    )
    styled_render_params = apply_chart_information_style(render_params, style)
    background, background_meta = make_chart_information_background(
        canvas_width=int(styled_render_params.canvas_width),
        canvas_height=int(styled_render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=f"charts.{str(task_group)}.{str(scene_id)}.information_scene_background",
    )
    return styled_render_params, background, background_meta, style_meta


__all__ = [
    "ChartInformationStyle",
    "apply_chart_information_style",
    "make_chart_information_background",
    "prepare_chart_information_scene",
    "resolve_chart_information_style",
]
