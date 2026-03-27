"""Thin tile-domain wrapper over the shared named-color palette."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from ...shared.named_colors import (
    available_named_colors,
    named_color,
    sample_named_color_palette,
)

Color = Tuple[int, int, int]
NamedColor = Tuple[str, Color]


def available_named_tile_colors() -> Sequence[NamedColor]:
    """Return the canonical named tile color palette."""

    return tuple((str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2]))) for name, rgb in available_named_colors())


def named_tile_color(name: str) -> Color:
    """Return one canonical named tile color by name."""

    rgb = named_color(str(name))
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def sample_named_tile_palette(rng, *, palette_size: int, exclude_names: Iterable[str] = ()) -> List[NamedColor]:
    """Sample one deterministic named color palette."""

    sampled = sample_named_color_palette(rng, palette_size=int(palette_size), exclude_names=exclude_names)
    return [(str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2]))) for name, rgb in sampled]


__all__ = [
    "Color",
    "NamedColor",
    "available_named_tile_colors",
    "named_tile_color",
    "sample_named_tile_palette",
]
