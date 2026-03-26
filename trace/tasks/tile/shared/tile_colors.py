"""Named color helpers shared by single-board tile tasks."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple


Color = Tuple[int, int, int]
NamedColor = Tuple[str, Color]


_TILE_COLOR_PALETTE: Sequence[NamedColor] = (
    ("red", (230, 50, 50)),
    ("blue", (45, 117, 230)),
    ("green", (55, 185, 75)),
    ("yellow", (212, 194, 30)),
    ("orange", (238, 136, 26)),
    ("purple", (150, 58, 202)),
    ("brown", (136, 112, 68)),
    ("cyan", (52, 196, 224)),
    ("magenta", (208, 44, 145)),
    ("maroon", (150, 54, 68)),
)


def available_named_tile_colors() -> Sequence[NamedColor]:
    """Return the canonical named tile color palette."""
    return tuple(_TILE_COLOR_PALETTE)


def named_tile_color(name: str) -> Color:
    """Return one canonical named tile color by name."""
    needle = str(name).strip().lower()
    for entry_name, rgb in _TILE_COLOR_PALETTE:
        if str(entry_name).strip().lower() == needle:
            return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    raise KeyError(f"unknown named tile color: {name}")


def sample_named_tile_palette(rng, *, palette_size: int, exclude_names: Iterable[str] = ()) -> List[NamedColor]:
    """Sample one deterministic named color palette."""
    excluded = {str(name).strip().lower() for name in exclude_names if str(name).strip()}
    candidates = [entry for entry in _TILE_COLOR_PALETTE if str(entry[0]).lower() not in excluded]
    size = max(0, min(int(palette_size), len(candidates)))
    if size <= 0:
        return []
    sampled = list(rng.sample(candidates, k=int(size)))
    return [(str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2]))) for name, rgb in sampled]


__all__ = [
    "Color",
    "NamedColor",
    "available_named_tile_colors",
    "named_tile_color",
    "sample_named_tile_palette",
]
