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


def _information_scene_shadows_enabled(params: Mapping[str, Any]) -> bool:
    """Return whether pages adapters should draw shadow offsets for this scene."""

    if "information_scene_shadows_enabled" in params:
        return bool(params.get("information_scene_shadows_enabled"))
    policy = str(params.get("information_scene_shadow_policy", "auto")).strip().lower()
    return policy not in {"none", "off", "disabled", "disable"}


def _suppress_information_scene_shadows(
    style: PagesInformationStyle,
    metadata: Mapping[str, Any],
) -> tuple[PagesInformationStyle, dict[str, Any]]:
    """Zero non-semantic shadow offsets and keep trace metadata in sync."""

    original_shadow_offset = int(style.shadow_offset_px)
    adjusted = replace(style, shadow_offset_px=0)
    adjusted_meta = dict(metadata)
    layout_style = dict(adjusted_meta.get("layout_style", {}))
    layout_style["shadow_offset_px"] = 0
    adjusted_meta["layout_style"] = layout_style
    adapter_meta = dict(adjusted_meta.get("pages_adapter", {}))
    adapter_meta.update(
        {
            "information_scene_shadow_policy": "none",
            "original_shadow_offset_px": int(original_shadow_offset),
        }
    )
    adjusted_meta["pages_adapter"] = adapter_meta
    return adjusted, adjusted_meta


def resolve_pages_information_style(
    *,
    instance_seed: int,
    params: Mapping[str, Any] | None,
    scene_id: str,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool = False,
) -> tuple[PagesInformationStyle, dict[str, Any]]:
    """Resolve one pages presentation style without changing visible values."""

    resolved_params = params or {}
    route_id = str(scene_id) if scene_id is not None else str(scene_id)
    style, metadata = resolve_information_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"pages.{route_id}.{str(scene_id)}.information_scene_style",
        treatments=resolved_params.get("information_scene_treatments"),
        treatment_weights=resolved_params.get("information_scene_treatment_weights", {}),
        palettes=resolved_params.get("information_scene_palettes"),
        palette_weights=resolved_params.get("information_scene_palette_weights", {}),
        chrome_modes=resolved_params.get("information_scene_chrome_modes"),
        chrome_mode_weights=resolved_params.get("information_scene_chrome_mode_weights", {}),
        allow_dark=bool(allow_dark),
        protected_colors=protected_colors or (),
    )
    if not _information_scene_shadows_enabled(resolved_params):
        return _suppress_information_scene_shadows(style, metadata)

    adapter_meta = dict(metadata.get("pages_adapter", {}))
    adapter_meta.setdefault("information_scene_shadow_policy", "auto")
    metadata["pages_adapter"] = adapter_meta
    return style, metadata


def apply_document_information_style(
    render_params: DocumentRenderParams,
    style: PagesInformationStyle,
    *,
    suppress_shadows: bool = False,
) -> DocumentRenderParams:
    """Map shared style roles into structured-document chrome."""

    return replace(
        render_params,
        page_shadow_offset_px=0 if bool(suppress_shadows) else int(render_params.page_shadow_offset_px),
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
    render_params: DocumentRenderParams,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool = False,
) -> tuple[DocumentRenderParams, Any, dict[str, Any], dict[str, Any]]:
    """Resolve pages information style, apply it, and create the background."""

    style, style_meta = resolve_pages_information_style(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=str(scene_id),
        protected_colors=protected_colors or (),
        allow_dark=bool(allow_dark),
    )
    suppress_shadows = not _information_scene_shadows_enabled(params)
    styled_render_params = apply_document_information_style(
        render_params,
        style,
        suppress_shadows=bool(suppress_shadows),
    )
    background, background_meta = make_information_scene_background(
        canvas_width=int(styled_render_params.canvas_width),
        canvas_height=int(styled_render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=f"pages.{str(scene_id)}.{str(scene_id)}.information_scene_background",
    )
    return styled_render_params, background, background_meta, style_meta


__all__ = [
    "PagesInformationStyle",
    "apply_document_information_style",
    "prepare_document_information_scene",
    "resolve_pages_information_style",
]
