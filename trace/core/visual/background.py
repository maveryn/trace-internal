"""Deterministic task-group background-style helpers for TRACE tasks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from ..sampling import normalize_positive_weights, weighted_choice
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
_DEFAULT_GRID_STYLE: Dict[str, Any] = {
    "kind": "grid",
    "base_color": list(_DEFAULT_BASE_COLOR),
    "line_color": [220, 220, 220],
    "spacing": 24,
    "line_width": 1,
    "major_every": 0,
    "major_line_color": [220, 220, 220],
    "major_line_width": 1,
    "axis_enabled": False,
    "axis_color": [220, 220, 220],
    "axis_line_width": 2,
    "center_point_enabled": False,
    "center_point_color": [220, 220, 220],
    "center_point_radius": 2,
    "supersample_scale": 1,
}


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


def _to_bool(value: Any, fallback: bool) -> bool:
    """Parse a boolean-like value with fallback for invalid values."""
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
    return bool(fallback)


def _normalize_rgb(value: Any, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Normalize RGB-like input into a clamped 3-channel integer tuple."""
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (
            max(0, min(255, _to_int(value[0], fallback[0]))),
            max(0, min(255, _to_int(value[1], fallback[1]))),
            max(0, min(255, _to_int(value[2], fallback[2]))),
        )
    return tuple(fallback)


def coerce_grid_style_spec(
    spec: Mapping[str, Any],
    *,
    fallback_style: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Normalize one grid-style spec into deterministic, valid values."""
    fallback = dict(_DEFAULT_GRID_STYLE)
    if isinstance(fallback_style, Mapping):
        fallback.update(dict(fallback_style))

    merged = dict(fallback)
    if isinstance(spec, Mapping):
        merged.update(dict(spec))

    line_width = max(1, _to_int(merged.get("line_width"), fallback.get("line_width", 1)))
    major_line_color = _normalize_rgb(
        merged.get("major_line_color"),
        _normalize_rgb(merged.get("line_color"), (220, 220, 220)),
    )
    axis_color = _normalize_rgb(merged.get("axis_color"), major_line_color)
    axis_line_width = max(line_width, _to_int(merged.get("axis_line_width"), max(2, line_width + 1)))

    return {
        "kind": "grid",
        "base_color": list(_normalize_rgb(merged.get("base_color"), _DEFAULT_BASE_COLOR)),
        "line_color": list(_normalize_rgb(merged.get("line_color"), (220, 220, 220))),
        "spacing": max(4, _to_int(merged.get("spacing"), 24)),
        "line_width": int(line_width),
        "major_every": max(0, _to_int(merged.get("major_every"), 0)),
        "major_line_color": list(major_line_color),
        "major_line_width": max(line_width, _to_int(merged.get("major_line_width"), line_width)),
        "axis_enabled": _to_bool(merged.get("axis_enabled"), False),
        "axis_color": list(axis_color),
        "axis_line_width": int(axis_line_width),
        "center_point_enabled": _to_bool(merged.get("center_point_enabled"), False),
        "center_point_color": list(_normalize_rgb(merged.get("center_point_color"), axis_color)),
        "center_point_radius": max(1, _to_int(merged.get("center_point_radius"), max(2, axis_line_width))),
        "supersample_scale": max(1, min(4, _to_int(merged.get("supersample_scale"), 1))),
    }


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
            out[style_name] = coerce_grid_style_spec(spec)
    return out


def _normalize_weights(raw: Any, styles: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
    """Normalize style weights and return a probability map over style names."""
    if not isinstance(raw, Mapping):
        raw = {}
    weights = {name: _to_float(raw.get(name, 0.0), 0.0) for name in styles.keys()}
    try:
        return normalize_positive_weights(weights, default_keys=styles.keys())
    except ValueError:
        return {}


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
    """Collect background overrides from nested task params."""
    merged: Dict[str, Any] = {}
    visual = params.get("visual")
    if isinstance(visual, Mapping):
        background_cfg = visual.get("background")
        if isinstance(background_cfg, Mapping):
            merged.update(dict(background_cfg))
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


def _draw_grid_lines(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    height: int,
    spacing: int,
    line_color: Tuple[int, int, int],
    line_width: int,
    major_every: int,
    major_line_color: Tuple[int, int, int],
    major_line_width: int,
) -> None:
    """Draw minor/major graph-paper lines with deterministic boundary clamping."""
    max_x_start_minor = max(0, width - int(line_width))
    max_x_start_major = max(0, width - int(major_line_width))
    for idx, x in enumerate(range(0, width + 1, spacing)):
        use_major = bool(major_every) and int(idx) % int(major_every) == 0
        color = major_line_color if use_major else line_color
        width_px = int(major_line_width if use_major else line_width)
        max_x_start = max_x_start_major if use_major else max_x_start_minor
        x_start = max(0, min(int(x), max_x_start))
        draw.rectangle([x_start, 0, x_start + width_px - 1, height - 1], fill=color)

    max_y_start_minor = max(0, height - int(line_width))
    max_y_start_major = max(0, height - int(major_line_width))
    for idx, y in enumerate(range(0, height + 1, spacing)):
        use_major = bool(major_every) and int(idx) % int(major_every) == 0
        color = major_line_color if use_major else line_color
        width_px = int(major_line_width if use_major else line_width)
        max_y_start = max_y_start_major if use_major else max_y_start_minor
        y_start = max(0, min(int(y), max_y_start))
        draw.rectangle([0, y_start, width - 1, y_start + width_px - 1], fill=color)


def _axis_origin_for_extent(*, extent: int, spacing: int) -> int:
    """Return center axis coordinate snapped to the graph-paper lattice."""
    size = max(1, int(extent))
    spacing_px = max(1, int(spacing))
    max_idx = max(0, size - 1)
    center = int(round((float(max_idx) / 2.0) / float(spacing_px)) * float(spacing_px))
    return max(0, min(int(center), max_idx))


def compute_grid_axis_origin(*, canvas_size: int, spacing: int) -> Tuple[int, int]:
    """Compute graph-paper center-origin pixel coordinates for square canvases."""
    size = max(1, int(canvas_size))
    x = _axis_origin_for_extent(extent=size, spacing=int(spacing))
    y = _axis_origin_for_extent(extent=size, spacing=int(spacing))
    return (x, y)


def _draw_center_axes(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    height: int,
    spacing: int,
    axis_color: Tuple[int, int, int],
    axis_line_width: int,
) -> Tuple[int, int]:
    """Draw center x/y axes aligned to nearest graph-paper intersections."""
    axis_width = max(1, int(axis_line_width))
    max_x_start = max(0, width - axis_width)
    max_y_start = max(0, height - axis_width)

    center_x = _axis_origin_for_extent(extent=width, spacing=spacing)
    center_y = _axis_origin_for_extent(extent=height, spacing=spacing)
    x_start = max(0, min(center_x, max_x_start))
    y_start = max(0, min(center_y, max_y_start))

    draw.rectangle([x_start, 0, x_start + axis_width - 1, height - 1], fill=axis_color)
    draw.rectangle([0, y_start, width - 1, y_start + axis_width - 1], fill=axis_color)
    return (x_start, y_start)


def _draw_center_origin_marker(
    draw: ImageDraw.ImageDraw,
    *,
    origin_x: int,
    origin_y: int,
    color: Tuple[int, int, int],
    radius: int,
) -> None:
    """Draw one filled origin marker where center axes intersect."""
    radius_px = max(1, int(radius))
    x = int(origin_x)
    y = int(origin_y)
    draw.ellipse(
        [x - radius_px, y - radius_px, x + radius_px, y + radius_px],
        fill=color,
        outline=(20, 20, 20),
        width=max(1, int(round(radius_px / 2))),
    )


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
        major_every = max(0, _to_int(style_spec.get("major_every"), 0))
        major_line_color = _normalize_rgb(style_spec.get("major_line_color"), line_color)
        major_line_width = max(line_width, _to_int(style_spec.get("major_line_width"), line_width))
        axis_enabled = _to_bool(style_spec.get("axis_enabled"), False)
        axis_color = _normalize_rgb(style_spec.get("axis_color"), major_line_color)
        axis_line_width = max(line_width, _to_int(style_spec.get("axis_line_width"), max(2, line_width + 1)))
        center_point_enabled = _to_bool(style_spec.get("center_point_enabled"), False)
        center_point_color = _normalize_rgb(style_spec.get("center_point_color"), axis_color)
        center_point_radius = max(1, _to_int(style_spec.get("center_point_radius"), max(2, axis_line_width)))
        supersample_scale = max(1, min(4, _to_int(style_spec.get("supersample_scale"), 1)))

        render_size = int(canvas_size) * int(supersample_scale)
        scaled_spacing = int(spacing) * int(supersample_scale)
        scaled_line_width = int(line_width) * int(supersample_scale)
        scaled_major_line_width = int(major_line_width) * int(supersample_scale)
        scaled_axis_line_width = int(axis_line_width) * int(supersample_scale)
        scaled_center_point_radius = int(center_point_radius) * int(supersample_scale)

        image = Image.new("RGB", (render_size, render_size), base_color)
        draw = ImageDraw.Draw(image)
        _draw_grid_lines(
            draw,
            width=render_size,
            height=render_size,
            spacing=scaled_spacing,
            line_color=line_color,
            line_width=scaled_line_width,
            major_every=major_every,
            major_line_color=major_line_color,
            major_line_width=scaled_major_line_width,
        )
        if axis_enabled:
            center_origin = _draw_center_axes(
                draw,
                width=render_size,
                height=render_size,
                spacing=scaled_spacing,
                axis_color=axis_color,
                axis_line_width=scaled_axis_line_width,
            )
            if center_point_enabled:
                _draw_center_origin_marker(
                    draw,
                    origin_x=int(center_origin[0]),
                    origin_y=int(center_origin[1]),
                    color=center_point_color,
                    radius=scaled_center_point_radius,
                )
        if supersample_scale > 1:
            image = image.resize((int(canvas_size), int(canvas_size)), resample=Image.Resampling.LANCZOS)
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
        selected_style = weighted_choice(rng, cfg.get("weights", {}), sort_keys=True)
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
