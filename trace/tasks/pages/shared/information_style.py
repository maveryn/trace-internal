"""Pages-domain adapter for shared structured-information styling."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from ...shared.visual_style.information_scene import (
    Color,
    InformationSceneStyle,
    make_information_scene_background,
    resolve_information_scene_style,
)
from .document_common import DocumentRenderParams


PagesInformationStyle = InformationSceneStyle


def resolve_pages_information_style(
    *,
    instance_seed: int,
    params: Mapping[str, Any] | None,
    scene_id: str,
    task_group: str,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool = False,
) -> tuple[PagesInformationStyle, dict[str, Any]]:
    """Resolve one pages presentation style without changing visible values."""

    resolved_params = params or {}
    return resolve_information_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"pages.{str(task_group)}.{str(scene_id)}.information_scene_style",
        treatments=resolved_params.get("information_scene_treatments"),
        treatment_weights=resolved_params.get("information_scene_treatment_weights", {}),
        palettes=resolved_params.get("information_scene_palettes"),
        palette_weights=resolved_params.get("information_scene_palette_weights", {}),
        chrome_modes=resolved_params.get("information_scene_chrome_modes"),
        chrome_mode_weights=resolved_params.get("information_scene_chrome_mode_weights", {}),
        allow_dark=bool(allow_dark),
        protected_colors=protected_colors or (),
    )


def apply_document_information_style(
    render_params: DocumentRenderParams,
    style: PagesInformationStyle,
) -> DocumentRenderParams:
    """Map shared style roles into structured-document chrome."""

    return replace(
        render_params,
        page_fill_rgb=tuple(int(value) for value in style.surface_rgb),
        page_outline_rgb=tuple(int(value) for value in style.panel_border_rgb),
        page_shadow_rgb=tuple(int(value) for value in style.shadow_rgb),
        field_fill_rgb=tuple(int(value) for value in style.panel_fill_rgb),
        field_outline_rgb=tuple(int(value) for value in style.panel_border_rgb),
        label_fill_rgb=tuple(int(value) for value in style.muted_text_rgb),
        label_stroke_rgb=tuple(int(value) for value in style.text_stroke_rgb),
        value_fill_rgb=tuple(int(value) for value in style.text_rgb),
        divider_rgb=tuple(int(value) for value in style.guide_rgb),
    )


def prepare_document_information_scene(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_id: str,
    task_group: str,
    render_params: DocumentRenderParams,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool = False,
) -> tuple[DocumentRenderParams, Any, dict[str, Any], dict[str, Any]]:
    """Resolve pages information style, apply it, and create the background."""

    style, style_meta = resolve_pages_information_style(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=str(scene_id),
        task_group=str(task_group),
        protected_colors=protected_colors or (),
        allow_dark=bool(allow_dark),
    )
    styled_render_params = apply_document_information_style(render_params, style)
    background, background_meta = make_information_scene_background(
        canvas_width=int(styled_render_params.canvas_width),
        canvas_height=int(styled_render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=f"pages.{str(task_group)}.{str(scene_id)}.information_scene_background",
    )
    return styled_render_params, background, background_meta, style_meta


__all__ = [
    "PagesInformationStyle",
    "apply_document_information_style",
    "prepare_document_information_scene",
    "resolve_pages_information_style",
]
