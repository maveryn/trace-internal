"""Misc-domain adapter for globally shared panel-style renderers."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ...shared.visual_style.panel import (
    DEFAULT_PANEL_SCENE_STYLE,
    PANEL_SCENE_TREATMENTS,
    PanelSceneStyle,
    draw_panel_chrome_by_mode,
    draw_panel_grid_cell,
    draw_panel_option_card,
    draw_panel_plain_chrome,
    draw_panel_scene_chrome,
    make_panel_scene_background,
    panel_scene_style_metadata,
    resolve_panel_chrome_mode,
    resolve_panel_scene_style,
)

MiscSceneStyle = PanelSceneStyle
DEFAULT_MISC_SCENE_STYLE = DEFAULT_PANEL_SCENE_STYLE
MISC_SCENE_TREATMENTS = PANEL_SCENE_TREATMENTS


def resolve_misc_scene_style(
    *,
    instance_seed: int,
    namespace: str,
    treatments: Sequence[str] | None = None,
    treatment_weights: Mapping[str, float] | None = None,
    style_pack_weights: Mapping[str, float] | None = None,
    palette_weights: Mapping[str, float] | None = None,
) -> tuple[MiscSceneStyle, dict[str, Any]]:
    """Resolve one misc scene style via the shared panel-style layer."""

    return resolve_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=str(namespace),
        treatments=treatments,
        treatment_weights=treatment_weights,
        palette_weights=palette_weights or style_pack_weights,
    )


def misc_scene_style_metadata(style: MiscSceneStyle) -> dict[str, Any]:
    """Serialize one misc scene style using the shared metadata schema."""

    return panel_scene_style_metadata(style)


draw_misc_grid_cell = draw_panel_grid_cell
draw_misc_option_card = draw_panel_option_card
draw_misc_chrome_by_mode = draw_panel_chrome_by_mode
draw_misc_plain_chrome = draw_panel_plain_chrome
draw_misc_panel_chrome = draw_panel_scene_chrome
make_misc_scene_background = make_panel_scene_background


__all__ = [
    "DEFAULT_MISC_SCENE_STYLE",
    "MISC_SCENE_TREATMENTS",
    "MiscSceneStyle",
    "draw_misc_chrome_by_mode",
    "draw_misc_grid_cell",
    "draw_misc_option_card",
    "draw_misc_panel_chrome",
    "draw_misc_plain_chrome",
    "make_misc_scene_background",
    "misc_scene_style_metadata",
    "resolve_panel_chrome_mode",
    "resolve_misc_scene_style",
]
