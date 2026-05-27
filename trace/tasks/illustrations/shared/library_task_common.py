"""Shared sampling helpers for library illustration tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ...shared.color_format import format_named_color_with_hex
from ...shared.config_defaults import group_default
from ...shared.named_colors import available_named_colors, named_color
from .library_scene import (
    BOOK_ORIENTATIONS,
    LIBRARY_SECTION_TYPES,
    LIBRARY_SETTING_IDS,
    LibraryBookSpec,
    LibrarySectionSpec,
)
from .object_library import STYLE_IDS
from .task_support import (
    bounds,
    render_params as _shared_render_params,
    sample_count,
    spawned_task_rng,
    style_weights as _shared_style_weights,
    uniform_string_probability_map,
)


DEFAULT_BOOK_COLOR_SUPPORT: Tuple[str, ...] = ("red", "blue", "green", "orange", "purple", "cyan", "magenta")


def section_support(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    """Resolve supported library section keys."""

    raw = params.get("section_key_support", group_default(defaults, "section_key_support", LIBRARY_SECTION_TYPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("section_key_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(LIBRARY_SECTION_TYPES))
    if len(support) < 3:
        raise ValueError("section_key_support must contain at least three library sections")
    return tuple(dict.fromkeys(support))


def color_support(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    """Resolve supported canonical book colors."""

    known = {str(name) for name, _rgb in available_named_colors()}
    raw = params.get("color_name_support", group_default(defaults, "color_name_support", DEFAULT_BOOK_COLOR_SUPPORT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("color_name_support must be a sequence")
    support = tuple(str(value).strip().lower() for value in raw if str(value).strip().lower() in known)
    if len(support) < 3:
        raise ValueError("color_name_support must contain at least three canonical colors")
    return tuple(dict.fromkeys(support))


def orientation_support(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    """Resolve supported book orientations."""

    raw = params.get("orientation_support", group_default(defaults, "orientation_support", BOOK_ORIENTATIONS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("orientation_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(BOOK_ORIENTATIONS))
    if not support:
        raise ValueError("orientation_support resolved no supported orientations")
    return tuple(dict.fromkeys(support))


def section_keys_for_scene(
    *,
    rng,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    target_section_key: str,
    section_count: int,
) -> Tuple[str, ...]:
    """Return a shuffled unique section-key set containing the target section."""

    support = section_support(params, defaults)
    others = [str(value) for value in support if str(value) != str(target_section_key)]
    if len(others) + 1 < int(section_count):
        raise ValueError("section_count exceeds available unique section support")
    selected = [str(target_section_key), *rng.sample(others, k=int(section_count) - 1)]
    rng.shuffle(selected)
    return tuple(str(value) for value in selected)


def render_params(params: Mapping[str, Any], render_defaults: Mapping[str, Any], *, fallback_width: int, fallback_height: int, fallback_scale: int) -> Dict[str, int]:
    """Resolve library canvas render parameters."""

    return _shared_render_params(
        params,
        render_defaults,
        prefix="library",
        fallback_width=fallback_width,
        fallback_height=fallback_height,
        fallback_scale=fallback_scale,
    )


def style_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve illustration style weights."""

    return _shared_style_weights(params, render_defaults, style_ids=STYLE_IDS)


def setting_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve library setting weights."""

    raw = params.get("library_setting_weights", group_default(render_defaults, "library_setting_weights", {setting: 1.0 for setting in LIBRARY_SETTING_IDS}))
    if not isinstance(raw, Mapping):
        raise ValueError("library_setting_weights must be a mapping")
    return {str(key): max(0.0, float(value)) for key, value in raw.items()}


def random_book_specs(
    *,
    rng,
    section_key: str,
    count: int,
    colors: Sequence[str],
    orientations: Sequence[str] = BOOK_ORIENTATIONS,
    role: str = "distractor",
) -> Tuple[LibraryBookSpec, ...]:
    """Create random book specs for one section."""

    color_values = tuple(str(value) for value in colors)
    orientation_values = tuple(str(value) for value in orientations)
    if not color_values:
        raise ValueError("random_book_specs needs at least one color")
    if not orientation_values:
        raise ValueError("random_book_specs needs at least one orientation")
    return tuple(
        LibraryBookSpec(
            section_key=str(section_key),
            color_name=str(rng.choice(color_values)),
            orientation=str(rng.choice(orientation_values)),
            role=str(role),
        )
        for _ in range(int(count))
    )


def make_library_section_specs(
    *,
    section_keys: Sequence[str],
    specs_by_section: Mapping[str, Sequence[LibraryBookSpec]],
) -> Tuple[LibrarySectionSpec, ...]:
    """Build ordered section specs from per-section book specs."""

    return tuple(
        LibrarySectionSpec(
            section_key=str(section_key),
            book_specs=tuple(specs_by_section[str(section_key)]),
            role="target" if any(str(spec.role) == "target" for spec in specs_by_section[str(section_key)]) else "distractor",
        )
        for section_key in section_keys
    )


def color_label(color_name: str) -> str:
    """Return prompt-facing canonical color label."""

    return format_named_color_with_hex(str(color_name), named_color(str(color_name)))


__all__ = [
    "DEFAULT_BOOK_COLOR_SUPPORT",
    "bounds",
    "color_label",
    "color_support",
    "make_library_section_specs",
    "orientation_support",
    "random_book_specs",
    "render_params",
    "sample_count",
    "section_keys_for_scene",
    "section_support",
    "setting_weights",
    "spawned_task_rng",
    "style_weights",
    "uniform_string_probability_map",
]
