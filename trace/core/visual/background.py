"""Deterministic task-group background-style helpers for TRACE tasks."""

from __future__ import annotations

import random
from copy import deepcopy
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from ..seed import spawn_rng


_DEFAULT_BASE_COLOR = (245, 245, 245)

_DEFAULT_BACKGROUND_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "solid_default": {
            "kind": "solid",
            "color": list(_DEFAULT_BASE_COLOR),
        }
    },
    "weights": {"solid_default": 1.0},
}

_ALLOWED_STYLE_KINDS = {"solid", "grid"}


def _to_int(value: Any, fallback: int) -> int:
    """Parse an integer with fallback for invalid values."""
    try:
        return int(value)
    except Exception:
        return int(fallback)


def _to_float(value: Any, fallback: float) -> float:
    """Parse a float with fallback for invalid values."""
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _normalize_rgb(value: Any, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Normalize RGB-like input into a clamped 3-channel integer tuple."""
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (
            max(0, min(255, _to_int(value[0], fallback[0]))),
            max(0, min(255, _to_int(value[1], fallback[1]))),
            max(0, min(255, _to_int(value[2], fallback[2]))),
        )
    return tuple(fallback)


def _normalize_styles(raw: Any, fallback: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Normalize style definitions to a validated internal representation."""
    if not isinstance(raw, Mapping):
        raw = fallback
    out: Dict[str, Dict[str, Any]] = {}
    for name, spec in raw.items():
        if not isinstance(spec, Mapping):
            continue
        style_name = str(name).strip()
        if not style_name:
            continue
        kind = str(spec.get("kind", "solid")).strip().lower()
        if kind not in _ALLOWED_STYLE_KINDS:
            continue
        if kind == "solid":
            out[style_name] = {
                "kind": "solid",
                "color": list(_normalize_rgb(spec.get("color"), _DEFAULT_BASE_COLOR)),
            }
        else:
            out[style_name] = {
                "kind": "grid",
                "base_color": list(_normalize_rgb(spec.get("base_color"), _DEFAULT_BASE_COLOR)),
                "line_color": list(_normalize_rgb(spec.get("line_color"), (220, 220, 220))),
                "spacing": max(4, _to_int(spec.get("spacing"), 24)),
                "line_width": max(1, _to_int(spec.get("line_width"), 1)),
            }
    return out


def _normalize_weights(raw: Any, styles: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
    """Normalize style weights and return a probability map over style names."""
    if not isinstance(raw, Mapping):
        raw = {}
    weights = {name: _to_float(raw.get(name, 0.0), 0.0) for name in styles.keys()}
    positive = {name: value for name, value in weights.items() if value > 0.0}
    if not positive:
        if not styles:
            return {}
        p = 1.0 / float(len(styles))
        return {name: p for name in styles.keys()}
    total = sum(positive.values())
    return {name: (value / total) for name, value in sorted(positive.items())}


def _normalize_default_config(default_config: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Normalize task-group background defaults against global fallbacks."""
    base = deepcopy(_DEFAULT_BACKGROUND_CONFIG)
    if not isinstance(default_config, Mapping):
        return base

    enabled = bool(default_config.get("enabled", base["enabled"]))
    styles = _normalize_styles(default_config.get("styles"), fallback=base["styles"])
    weights = _normalize_weights(default_config.get("weights"), styles)
    if not styles:
        styles = deepcopy(base["styles"])
        weights = deepcopy(base["weights"])
    return {
        "enabled": enabled,
        "styles": styles,
        "weights": weights,
    }


def _resolve_background_overrides(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Collect background overrides from nested and flat task params."""
    merged: Dict[str, Any] = {}
    visual = params.get("visual")
    if isinstance(visual, Mapping):
        background_cfg = visual.get("background")
        if isinstance(background_cfg, Mapping):
            merged.update(dict(background_cfg))

    flat_map = {
        "background_enabled": "enabled",
        "background_style": "style_name",
    }
    for flat_key, target_key in flat_map.items():
        if flat_key in params and target_key not in merged:
            merged[target_key] = params.get(flat_key)
    return merged


def _resolve_background_config(params: Mapping[str, Any], *, default_config: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Merge defaults and overrides into one background rendering config."""
    base = _normalize_default_config(default_config)
    overrides = _resolve_background_overrides(params)

    styles = _normalize_styles(overrides.get("styles", base.get("styles", {})), fallback=base.get("styles", {}))
    weights = _normalize_weights(overrides.get("weights", base.get("weights", {})), styles)
    if not styles:
        styles = deepcopy(base["styles"])
        weights = deepcopy(base["weights"])

    return {
        "enabled": bool(overrides.get("enabled", base.get("enabled", True))),
        "styles": styles,
        "weights": weights,
        "style_name": str(overrides.get("style_name", "")).strip(),
    }


def _weighted_choice(rng: random.Random, probabilities: Mapping[str, float]) -> str:
    """Sample one key from a normalized probability map."""
    roll = float(rng.random())
    cumulative = 0.0
    last_key = ""
    for key, probability in sorted(probabilities.items()):
        cumulative += float(probability)
        last_key = str(key)
        if roll <= cumulative:
            return str(key)
    return last_key


def _render_style(canvas_size: int, style_spec: Mapping[str, Any]) -> Image.Image:
    """Render a background image for one normalized style specification."""
    kind = str(style_spec.get("kind", "solid"))
    if kind == "solid":
        color = _normalize_rgb(style_spec.get("color"), _DEFAULT_BASE_COLOR)
        return Image.new("RGB", (canvas_size, canvas_size), color)

    if kind == "grid":
        base_color = _normalize_rgb(style_spec.get("base_color"), _DEFAULT_BASE_COLOR)
        line_color = _normalize_rgb(style_spec.get("line_color"), (220, 220, 220))
        spacing = max(4, _to_int(style_spec.get("spacing"), 24))
        line_width = max(1, _to_int(style_spec.get("line_width"), 1))
        image = Image.new("RGB", (canvas_size, canvas_size), base_color)
        draw = ImageDraw.Draw(image)
        for x in range(0, canvas_size + 1, spacing):
            draw.line([(x, 0), (x, canvas_size)], fill=line_color, width=line_width)
        for y in range(0, canvas_size + 1, spacing):
            draw.line([(0, y), (canvas_size, y)], fill=line_color, width=line_width)
        return image

    return Image.new("RGB", (canvas_size, canvas_size), _DEFAULT_BASE_COLOR)


def make_background_canvas(
    *,
    canvas_size: int,
    instance_seed: int,
    params: Mapping[str, Any],
    default_config: Mapping[str, Any] | None = None,
    fallback_color: Tuple[int, int, int] = _DEFAULT_BASE_COLOR,
) -> tuple[Image.Image, Dict[str, Any]]:
    """Create deterministic background canvas plus trace metadata."""
    cfg = _resolve_background_config(params, default_config=default_config)
    enabled = bool(cfg["enabled"])
    styles = cfg.get("styles", {})

    if not enabled or not styles:
        return (
            Image.new("RGB", (canvas_size, canvas_size), _normalize_rgb(fallback_color, _DEFAULT_BASE_COLOR)),
            {
                "enabled": False,
                "selected_style": None,
                "available_styles": sorted(styles.keys()),
            },
        )

    style_name = str(cfg.get("style_name", "")).strip()
    if style_name and style_name in styles:
        selected_style = style_name
    else:
        rng = spawn_rng(instance_seed, "visual.background_style")
        selected_style = _weighted_choice(rng, cfg.get("weights", {}))
        if not selected_style:
            selected_style = sorted(styles.keys())[0]

    selected_spec = dict(styles[selected_style])
    image = _render_style(canvas_size, selected_spec)
    metadata = {
        "enabled": True,
        "selected_style": selected_style,
        "available_styles": sorted(styles.keys()),
        "style_spec": selected_spec,
    }
    return image, metadata
