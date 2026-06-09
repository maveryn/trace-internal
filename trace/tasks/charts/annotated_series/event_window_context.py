"""Non-answer context layer helpers for annotated-series chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.context_text_assets import sample_context_text
from ...shared.font_assets import sample_font_family
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font
from ...shared.visual_style.context_layer import (
    ContextTextElement,
    draw_dashboard_reserved_margin_context,
    resolve_dashboard_context_layout,
)
from .event_window_common import (
    RGB,
    TASK_ID,
    _CONTEXT_PARAM_KEYS,
    _DEFAULTS,
    _RENDER_DEFAULTS,
    _render_default_value,
)

def _context_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    resolved: Dict[str, Any] = {}
    for key in _CONTEXT_PARAM_KEYS:
        value = params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), None))
        if value is not None:
            resolved[str(key)] = value
    return resolved


def _choose_context_mode(*, params: Mapping[str, Any], instance_seed: int) -> str:
    if not bool(_render_default_value(params, "context_text_enabled", False)):
        return "clean"
    supported = ("clean", "light_context", "right_sidebar", "bottom_band")
    raw_weights = _render_default_value(
        params,
        "context_text_mode_weights",
        {"clean": 0.5, "light_context": 0.3, "right_sidebar": 0.1, "bottom_band": 0.1},
    )
    if not isinstance(raw_weights, Mapping):
        raw_weights = {"clean": 1.0}
    weights = []
    for mode in supported:
        weight = max(0.0, float(raw_weights.get(str(mode), 0.0)))
        if weight > 0.0:
            weights.append((str(mode), float(weight)))
    if not weights:
        return "clean"
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.context_text_mode")
    cursor = rng.random() * sum(weight for _, weight in weights)
    running = 0.0
    for mode, weight in weights:
        running += float(weight)
        if cursor <= running:
            return str(mode)
    return str(weights[-1][0])


def _resolve_context_layout(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
) -> Dict[str, Any]:
    mode = _choose_context_mode(params=params, instance_seed=int(instance_seed))
    context_params = _context_params(params)
    top_reserved = int(context_params.get("context_text_top_reserved_px", 64))
    bottom_reserved = int(context_params.get("context_text_bottom_reserved_px", 28))
    if str(mode) == "clean":
        return {
            "enabled": False,
            "mode": "clean",
            "layout_mode": "clean",
            "placement": "none",
            "context_params": context_params,
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
            "context_params": context_params,
            "top_reserved_px": int(top_reserved),
            "bottom_reserved_px": int(bottom_reserved),
        }
    placement = "right_sidebar" if str(mode) == "right_sidebar" else "bottom_band"
    layout = resolve_dashboard_context_layout(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.context",
        params={**context_params, "context_text_enabled": True, "context_text_placement": str(placement)},
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        top_reserved_px=int(top_reserved),
        bottom_reserved_px=int(bottom_reserved),
        left_margin_px=int(context_params.get("context_text_left_margin_px", 24)),
        right_margin_px=int(context_params.get("context_text_right_margin_px", 24)),
    )
    return {
        **dict(layout),
        "enabled": True,
        "mode": str(mode),
        "context_params": context_params,
    }


def _apply_context_margin_overrides(
    params: Mapping[str, Any],
    *,
    context_layout: Mapping[str, Any],
) -> Dict[str, Any]:
    resolved = dict(params)
    if not bool(context_layout.get("enabled", False)):
        return resolved

    base_left = int(_render_default_value(params, "plot_margin_left_px", _DEFAULTS.plot_margin_left_px))
    base_right = int(_render_default_value(params, "plot_margin_right_px", _DEFAULTS.plot_margin_right_px))
    base_bottom = int(_render_default_value(params, "plot_margin_bottom_px", _DEFAULTS.plot_margin_bottom_px))
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


def _fit_context_text(draw: ImageDraw.ImageDraw, text: str, *, font: Any, max_width_px: int) -> str:
    raw = " ".join(str(text).split())
    if not raw:
        return ""
    max_width = max(20, int(max_width_px))
    if draw.textbbox((0, 0), raw, font=font)[2] <= int(max_width):
        return raw
    suffix = "..."
    words = raw.split()
    fitted = ""
    for word in words:
        candidate = f"{fitted} {word}".strip()
        if draw.textbbox((0, 0), f"{candidate}{suffix}", font=font)[2] > int(max_width):
            break
        fitted = candidate
    if fitted:
        return f"{fitted}{suffix}"
    chars: List[str] = []
    for char in raw:
        candidate = "".join(chars) + str(char)
        if draw.textbbox((0, 0), f"{candidate}{suffix}", font=font)[2] > int(max_width):
            break
        chars.append(str(char))
    return f"{''.join(chars).strip()}{suffix}" if chars else suffix


def _draw_light_context_text(
    draw: ImageDraw.ImageDraw,
    *,
    elements: List[ContextTextElement],
    rng: Any,
    role: str,
    manifest_path: str,
    xy: Tuple[float, float],
    anchor: str,
    font: Any,
    font_family: str,
    fill_rgb: RGB,
    max_width_px: int,
    canvas_width: int,
    canvas_height: int,
) -> None:
    selection = sample_context_text(str(manifest_path), rng=rng)
    fitted = _fit_context_text(draw, str(selection.text), font=font, max_width_px=int(max_width_px))
    try:
        bbox_raw = draw.textbbox(tuple(xy), str(fitted), font=font, anchor=str(anchor))
    except TypeError:
        bbox_raw = draw.textbbox(tuple(xy), str(fitted), font=font)
    draw_text_traced(draw,tuple(xy), str(fitted), font=font, fill=tuple(fill_rgb), anchor=str(anchor), role="readout", required=False)
    bbox = (
        max(0, min(int(canvas_width) - 1, int(round(float(bbox_raw[0]))))),
        max(0, min(int(canvas_height) - 1, int(round(float(bbox_raw[1]))))),
        max(1, min(int(canvas_width), int(round(float(bbox_raw[2]))))),
        max(1, min(int(canvas_height), int(round(float(bbox_raw[3]))))),
    )
    elements.append(
        ContextTextElement(
            context_id=f"context_{len(elements):02d}",
            role=str(role),
            text=str(fitted),
            bbox_xyxy=tuple(int(value) for value in bbox),
            manifest_path=str(selection.manifest_path),
            source_ids=tuple(str(source_id) for source_id in selection.source_ids),
            row_index=int(selection.row_index),
            layout_mode="light_context:top_bottom_notes",
            font_family=str(font_family),
        )
    )


def _rgb_role(information_style_meta: Mapping[str, Any], role: str, fallback: RGB) -> RGB:
    roles = information_style_meta.get("roles_rgb", {})
    if isinstance(roles, Mapping):
        value = roles.get(str(role))
        if isinstance(value, Sequence) and len(value) >= 3:
            return (int(value[0]), int(value[1]), int(value[2]))
    return tuple(int(value) for value in fallback)


def _draw_context_layer(
    image: Image.Image,
    *,
    context_layout: Mapping[str, Any],
    information_style_meta: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[ContextTextElement, ...]:
    if not bool(context_layout.get("enabled", False)):
        return tuple()

    context_params = dict(context_layout.get("context_params", {})) if isinstance(context_layout.get("context_params", {}), Mapping) else {}
    text_rgb = _rgb_role(information_style_meta, "text", (35, 40, 48))
    muted_rgb = _rgb_role(information_style_meta, "muted_text", (90, 96, 108))
    panel_fill_rgb = _rgb_role(information_style_meta, "panel_fill", (255, 255, 255))
    panel_border_rgb = _rgb_role(information_style_meta, "panel_border", (200, 207, 216))
    accent_rgb = _rgb_role(information_style_meta, "accent", (35, 99, 180))

    mode = str(context_layout.get("mode", context_layout.get("layout_mode", "clean")))
    if mode in {"right_sidebar", "bottom_band"}:
        return draw_dashboard_reserved_margin_context(
            image,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.context",
            params=context_params,
            text_rgb=text_rgb,
            muted_text_rgb=muted_rgb,
            panel_fill_rgb=panel_fill_rgb,
            panel_border_rgb=panel_border_rgb,
            accent_rgb=accent_rgb,
            top_reserved_px=int(context_layout.get("top_reserved_px", 64)),
            bottom_reserved_px=int(context_layout.get("bottom_reserved_px", 28)),
            left_margin_px=int(context_layout.get("left_margin_px", 24)),
            right_margin_px=int(context_layout.get("right_margin_px", 24)),
            layout_spec=context_layout,
        )

    draw = ImageDraw.Draw(image)
    font_family = sample_font_family(
        role="context",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.context_light_font",
        params=context_params,
        exclude_tags=("mono", "display", "script", "handwriting"),
        explicit_key="context_text_light_font_family",
        weights_key="context_text_font_family_weights",
    )
    header_font = load_font(14, bold=True, font_family=font_family)
    small_font = load_font(12, bold=False, font_family=font_family)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.context_light")
    width, height = image.size
    elements: List[ContextTextElement] = []
    left_margin = 24
    right_margin = 24
    _draw_light_context_text(
        draw,
        elements=elements,
        rng=rng,
        role="header",
        manifest_path="phrases/headlines.txt",
        xy=(float(left_margin), 12.0),
        anchor="la",
        font=header_font,
        font_family=str(font_family),
        fill_rgb=text_rgb,
        max_width_px=max(180, int(width * 0.34)),
        canvas_width=int(width),
        canvas_height=int(height),
    )
    _draw_light_context_text(
        draw,
        elements=elements,
        rng=rng,
        role="source_note",
        manifest_path="phrases/source_notes.txt",
        xy=(float(width - right_margin), 12.0),
        anchor="ra",
        font=small_font,
        font_family=str(font_family),
        fill_rgb=muted_rgb,
        max_width_px=max(180, int(width * 0.34)),
        canvas_width=int(width),
        canvas_height=int(height),
    )
    _draw_light_context_text(
        draw,
        elements=elements,
        rng=rng,
        role="footer",
        manifest_path="phrases/footers.txt",
        xy=(float(left_margin), float(height - 18)),
        anchor="lm",
        font=small_font,
        font_family=str(font_family),
        fill_rgb=muted_rgb,
        max_width_px=max(220, int(width * 0.45)),
        canvas_width=int(width),
        canvas_height=int(height),
    )
    draw.line((left_margin, 40, width - right_margin, 40), fill=panel_border_rgb, width=1)
    draw.line((left_margin, height - 38, width - right_margin, height - 38), fill=panel_border_rgb, width=1)
    return tuple(elements)
