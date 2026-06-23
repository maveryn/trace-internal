"""Neutral sampling helpers for Venn-field icon scenes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....shared.color_format import format_named_color_with_hex
from ....shared.config_defaults import group_default
from ....shared.named_colors import available_named_colors, named_color
from ....shared.weighted_sampling import weighted_probability_map
from ...shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_probability_map,
    validate_procedural_named_icon_fill_style_support,
)

from .defaults import VennFieldDefaults
from .state import NamedColorEntry


def int_bounds(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    low_key: str,
    high_key: str,
    fallback_low: int,
    fallback_high: int,
) -> Tuple[int, int]:
    """Resolve inclusive integer bounds from params/defaults."""

    low = int(params.get(low_key, group_default(defaults, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(defaults, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} bounds")
    return int(low), int(high)


def shape_support(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    """Resolve procedural named-icon shape support."""

    raw = params.get("shape_id_support", group_default(defaults, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(str(value) for value in raw)
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    support = tuple(dict.fromkeys(values))
    if len(support) < 5:
        raise ValueError("shape_id_support must include at least five shapes")
    return support


def color_support(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Tuple[NamedColorEntry, ...]:
    """Resolve semantic named-color support."""

    color_by_name = {str(name): tuple(int(channel) for channel in rgb) for name, rgb in available_named_colors()}
    raw = params.get("named_color_support", group_default(defaults, "named_color_support", tuple(color_by_name)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("named_color_support must be a sequence")
    names = tuple(dict.fromkeys(str(value).strip().lower() for value in raw if str(value).strip()))
    unsupported = sorted(set(names) - set(color_by_name))
    if unsupported:
        raise ValueError(f"unsupported named colors: {unsupported}")
    if len(names) < 2:
        raise ValueError("named_color_support must include at least two colors")
    return tuple(
        NamedColorEntry(
            name=str(name),
            rgb=tuple(int(channel) for channel in named_color(str(name))),
            label=format_named_color_with_hex(str(name), named_color(str(name))),
        )
        for name in names
    )


def fill_style_support(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    fallback: Sequence[str] = PROCEDURAL_NAMED_ICON_FILL_STYLES,
) -> Tuple[str, ...]:
    """Resolve named-icon fill-style support used as render variation."""

    key = "named_icon_fill_style_support"
    raw = params.get(key, group_default(defaults, key, tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = tuple(fallback)
    return validate_procedural_named_icon_fill_style_support(tuple(str(value) for value in raw))


def fill_style_probabilities(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    support: Sequence[str],
) -> Dict[str, float]:
    """Resolve fill-style sampling probabilities."""

    raw = params.get("named_icon_fill_style_weights", group_default(defaults, "named_icon_fill_style_weights", None))
    if not isinstance(raw, Mapping):
        raw = None
    return procedural_named_icon_fill_style_probability_map(tuple(str(value) for value in support), dict(raw) if raw is not None else None)


def uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    """Return a uniform probability map, or a point mass for explicit values."""

    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): probability for value in support}


def target_mode_probabilities(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve target-predicate mode probabilities for task-owned selection."""

    raw = params.get("target_attribute_mode_weights", group_default(defaults, "target_attribute_mode_weights", None))
    if not isinstance(raw, Mapping):
        raw = {"shape_only": 0.5, "color_shape": 0.5}
    return weighted_probability_map(("shape_only", "color_shape"), raw)


def target_description(*, mode: str, shape_id: str, target_color: NamedColorEntry | None) -> str:
    """Return prompt-facing target phrase for one sampled predicate."""

    shape_name = procedural_named_icon_display_name(str(shape_id))
    quoted_shape = f'"{shape_name}"'
    if str(mode) == "shape_only":
        return f"{quoted_shape} icons"
    if str(mode) == "color_shape":
        if target_color is None:
            raise ValueError("color_shape target is missing target_color")
        return f"{target_color.label} {quoted_shape} icons"
    raise ValueError(f"unsupported target mode: {mode}")


def default_target_mode_support() -> Tuple[str, ...]:
    """Return supported semantic target predicate modes."""

    return ("shape_only", "color_shape")


__all__ = [
    "color_support",
    "default_target_mode_support",
    "fill_style_probabilities",
    "fill_style_support",
    "int_bounds",
    "shape_support",
    "target_description",
    "target_mode_probabilities",
    "uniform_string_probability_map",
]
