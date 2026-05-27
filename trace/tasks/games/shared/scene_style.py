"""Games-domain adapter for globally shared panel-style renderers."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ...shared.visual_style.panel import (
    DEFAULT_PANEL_SCENE_STYLE,
    PANEL_SCENE_TREATMENTS,
    PanelSceneStyle,
    draw_panel_grid_cell,
    draw_panel_option_card,
    draw_panel_scene_chrome,
    make_panel_scene_background,
    panel_scene_style_metadata,
    resolve_panel_scene_style,
)

GamePanelSceneStyle = PanelSceneStyle
DEFAULT_GAME_PANEL_SCENE_STYLE = DEFAULT_PANEL_SCENE_STYLE
GAME_PANEL_SCENE_TREATMENTS = PANEL_SCENE_TREATMENTS


def resolve_game_panel_scene_style(
    *,
    instance_seed: int,
    namespace: str,
    treatments: Sequence[str] | None = None,
    treatment_weights: Mapping[str, float] | None = None,
    palette_weights: Mapping[str, float] | None = None,
) -> tuple[GamePanelSceneStyle, dict[str, Any]]:
    """Resolve one game scene style via the shared panel-style layer."""

    return resolve_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=str(namespace),
        treatments=treatments,
        treatment_weights=treatment_weights,
        palette_weights=palette_weights,
    )


def game_panel_scene_style_metadata(style: GamePanelSceneStyle) -> dict[str, Any]:
    """Serialize one game scene style using the shared metadata schema."""

    return panel_scene_style_metadata(style)


__all__ = [
    "DEFAULT_GAME_PANEL_SCENE_STYLE",
    "GAME_PANEL_SCENE_TREATMENTS",
    "GamePanelSceneStyle",
    "draw_panel_grid_cell",
    "draw_panel_option_card",
    "draw_panel_scene_chrome",
    "game_panel_scene_style_metadata",
    "make_panel_scene_background",
    "resolve_game_panel_scene_style",
]
