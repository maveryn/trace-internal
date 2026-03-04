"""Deterministic post-image noise augmentation helpers for TRACE tasks.

This module applies simple post-render noise edits (blur/downsample/jpeg/noise)
with deterministic sampling. Task groups provide their own default config;
this module only merges defaults with per-task/per-instance override keys.
"""

from __future__ import annotations

import io
import random
from copy import deepcopy
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageFilter

from ..seed import spawn_rng


_ALLOWED_EDIT_TYPES = {"blur", "downsample", "jpeg", "noise"}

TRACE_DEFAULT_NOISE_VALUE_RANGES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "blur": {"radius": (0.2, 0.6)},
    "downsample": {"scale": (0.85, 0.95)},
    "jpeg": {"quality": (70.0, 90.0)},
    "noise": {"alpha": (0.03, 0.08)},
}

_DEFAULT_NOISE_CONFIG: Dict[str, Any] = {
    "apply_prob": 0.0,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 2],
    "value_ranges": deepcopy(TRACE_DEFAULT_NOISE_VALUE_RANGES),
}


def _clamp_prob(value: Any, default: float) -> float:
    try:
        prob = float(value)
    except Exception:
        prob = float(default)
    return max(0.0, min(1.0, prob))


def _normalize_edit_count_range(value: Any, default_pair: Sequence[int]) -> Tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        lo, hi = int(default_pair[0]), int(default_pair[1])
    else:
        lo, hi = int(value[0]), int(value[1])
    lo_n = max(0, min(lo, hi))
    hi_n = max(0, max(lo, hi))
    return lo_n, hi_n


def _normalize_value_ranges(raw: Any, fallback: Mapping[str, Mapping[str, Tuple[float, float]]]) -> Dict[str, Dict[str, Tuple[float, float]]]:
    out: Dict[str, Dict[str, Tuple[float, float]]] = {}
    if not isinstance(raw, Mapping):
        raw = fallback
    for edit_type, param_map in raw.items():
        edit_key = str(edit_type).strip().lower()
        if edit_key not in _ALLOWED_EDIT_TYPES or not isinstance(param_map, Mapping):
            continue
        clean_params: Dict[str, Tuple[float, float]] = {}
        for param_name, bounds in param_map.items():
            if not isinstance(bounds, (list, tuple)) or len(bounds) < 2:
                continue
            lo = float(bounds[0])
            hi = float(bounds[1])
            clean_params[str(param_name)] = (min(lo, hi), max(lo, hi))
        if clean_params:
            out[edit_key] = clean_params
    return out


def _sample_edit_params(
    edit_type: str,
    rng: random.Random,
    value_ranges: Mapping[str, Mapping[str, Tuple[float, float]]],
) -> Dict[str, float]:
    params: Dict[str, float] = {}
    for param_name, (lo, hi) in value_ranges.get(edit_type, {}).items():
        value = float(rng.uniform(float(lo), float(hi)))
        if str(param_name) == "quality":
            params[str(param_name)] = float(int(round(value)))
        else:
            params[str(param_name)] = float(value)
    return params


def _apply_noise_blend(image: Image.Image, rng: random.Random, alpha: float) -> Image.Image:
    base = image.convert("RGB")
    width, height = base.size
    noise = Image.new("RGB", (width, height))
    pixels = noise.load()
    for y in range(height):
        for x in range(width):
            value = int(rng.randint(0, 255))
            pixels[x, y] = (value, value, value)
    return Image.blend(base, noise, max(0.0, min(1.0, float(alpha))))


def _apply_single_edit(image: Image.Image, edit_type: str, params: Mapping[str, float], rng: random.Random) -> Image.Image:
    base = image.convert("RGB")
    if edit_type == "blur":
        radius = float(params.get("radius", 0.4))
        return base.filter(ImageFilter.GaussianBlur(radius=radius))
    if edit_type == "downsample":
        scale = max(0.05, min(1.0, float(params.get("scale", 0.9))))
        width, height = base.size
        down_w = max(1, int(round(width * scale)))
        down_h = max(1, int(round(height * scale)))
        low = base.resize((down_w, down_h), resample=Image.BILINEAR)
        return low.resize((width, height), resample=Image.NEAREST)
    if edit_type == "jpeg":
        quality = int(round(float(params.get("quality", 80.0))))
        quality = max(5, min(95, quality))
        buf = io.BytesIO()
        base.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        return Image.open(buf).convert("RGB")
    if edit_type == "noise":
        alpha = float(params.get("alpha", 0.05))
        return _apply_noise_blend(base, rng, alpha)
    return base


def _serialize_edits(edits: Sequence[Tuple[str, Mapping[str, float]]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for edit_type, params in edits:
        rows.append(
            {
                "type": str(edit_type),
                "params": {
                    str(key): round(float(value), 6)
                    for key, value in dict(params).items()
                },
            }
        )
    return rows


def _normalize_default_config(default_config: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Normalize caller-provided task-group defaults against global fallback."""
    base = deepcopy(_DEFAULT_NOISE_CONFIG)
    if not isinstance(default_config, Mapping):
        return base

    base_apply_prob = float(base["apply_prob"])
    base["apply_prob"] = _clamp_prob(default_config.get("apply_prob", base_apply_prob), base_apply_prob)

    value_ranges = _normalize_value_ranges(default_config.get("value_ranges", base["value_ranges"]), fallback=base["value_ranges"])
    base["value_ranges"] = value_ranges

    raw_types = default_config.get("edit_types", base["edit_types"])
    if isinstance(raw_types, (list, tuple)):
        edit_types = [
            str(item).strip().lower()
            for item in raw_types
            if str(item).strip().lower() in _ALLOWED_EDIT_TYPES
        ]
    else:
        edit_types = []
    base["edit_types"] = [edit_type for edit_type in edit_types if edit_type in value_ranges]

    edit_count_range = _normalize_edit_count_range(
        default_config.get("edit_count_range", base["edit_count_range"]),
        default_pair=base["edit_count_range"],
    )
    base["edit_count_range"] = [int(edit_count_range[0]), int(edit_count_range[1])]
    return base


def _resolve_noise_overrides(params: Mapping[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    visual = params.get("visual")
    if isinstance(visual, Mapping):
        noise_cfg = visual.get("noise")
        if isinstance(noise_cfg, Mapping):
            merged.update(dict(noise_cfg))

    # Flat-key compatibility for easier one-off overrides.
    flat_map = {
        "noise_apply_prob": "apply_prob",
        "noise_edit_types": "edit_types",
        "noise_edit_count_range": "edit_count_range",
        "noise_edit_value_ranges": "value_ranges",
    }
    for flat_key, target_key in flat_map.items():
        if flat_key in params and target_key not in merged:
            merged[target_key] = params.get(flat_key)
    return merged


def _resolve_post_noise_config(params: Mapping[str, Any], *, default_config: Mapping[str, Any] | None) -> Dict[str, Any]:
    base = _normalize_default_config(default_config)
    overrides = _resolve_noise_overrides(params)

    apply_prob = _clamp_prob(overrides.get("apply_prob", base.get("apply_prob", 0.0)), float(base.get("apply_prob", 0.0)))
    value_ranges = _normalize_value_ranges(
        overrides.get("value_ranges", base.get("value_ranges", {})),
        fallback=base.get("value_ranges", {}),
    )

    raw_types = overrides.get("edit_types", base.get("edit_types", []))
    if isinstance(raw_types, (list, tuple)):
        edit_types = [
            str(item).strip().lower()
            for item in raw_types
            if str(item).strip().lower() in _ALLOWED_EDIT_TYPES
        ]
    else:
        edit_types = []
    # Keep only types with declared parameter ranges.
    edit_types = [edit_type for edit_type in edit_types if edit_type in value_ranges]

    edit_count_range = _normalize_edit_count_range(
        overrides.get("edit_count_range", base.get("edit_count_range", [1, 1])),
        default_pair=base.get("edit_count_range", [1, 1]),
    )

    return {
        "apply_prob": float(apply_prob),
        "edit_types": list(edit_types),
        "edit_count_range": [int(edit_count_range[0]), int(edit_count_range[1])],
        "value_ranges": value_ranges,
    }


def _sample_noise_edits(
    rng: random.Random,
    *,
    edit_types: Sequence[str],
    value_ranges: Mapping[str, Mapping[str, Tuple[float, float]]],
    edit_count_range: Sequence[int],
) -> List[Tuple[str, Dict[str, float]]]:
    if not edit_types:
        return []
    lo = max(0, int(edit_count_range[0]))
    hi = max(lo, int(edit_count_range[1]))
    if hi <= 0:
        return []
    count = int(rng.randint(lo, hi))
    if count <= 0:
        return []
    chosen = rng.sample(list(edit_types), k=min(int(count), len(edit_types)))
    return [(edit_type, _sample_edit_params(edit_type, rng, value_ranges)) for edit_type in chosen]


def apply_post_image_noise(
    image: Image.Image,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    default_config: Mapping[str, Any] | None = None,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """Apply deterministic post-composite noise edits and return trace metadata."""
    cfg = _resolve_post_noise_config(params, default_config=default_config)
    enabled = bool(float(cfg["apply_prob"]) > 0.0 and cfg["edit_types"] and int(cfg["edit_count_range"][1]) > 0)

    meta: Dict[str, Any] = {
        "enabled": bool(enabled),
        "applied": False,
        "apply_prob": float(cfg["apply_prob"]),
        "edit_types": list(cfg["edit_types"]),
        "edit_count_range": [int(cfg["edit_count_range"][0]), int(cfg["edit_count_range"][1])],
        "edits": [],
    }

    if not enabled:
        return image, meta

    gate_rng = spawn_rng(instance_seed, "visual.noise_gate")
    if gate_rng.random() > float(cfg["apply_prob"]):
        return image, meta

    select_rng = spawn_rng(instance_seed, "visual.noise_select")
    edits = _sample_noise_edits(
        select_rng,
        edit_types=cfg["edit_types"],
        value_ranges=cfg["value_ranges"],
        edit_count_range=cfg["edit_count_range"],
    )
    if not edits:
        return image, meta

    apply_rng = spawn_rng(instance_seed, "visual.noise_apply")
    output = image.convert("RGB")
    for edit_type, edit_params in edits:
        output = _apply_single_edit(output, edit_type, edit_params, apply_rng)

    meta["applied"] = True
    meta["edits"] = _serialize_edits(edits)
    return output, meta
