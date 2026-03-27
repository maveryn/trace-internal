"""Shared color-style helpers for curated icon tasks."""

from __future__ import annotations

from typing import Iterable, Sequence, Tuple

from ...shared.color_distance import (
    DEFAULT_COLOR_DISTANCE_SPACE,
    DEFAULT_MIN_COLOR_DISTANCE,
    color_distance,
    sample_color_palette_with_distance_constraints,
)

Color = Tuple[int, int, int]


def sample_icon_palette(
    rng,
    *,
    palette_size: int,
    channel_min: int,
    channel_max: int,
    anchor_colors: Iterable[Color],
    min_color_distance: float = DEFAULT_MIN_COLOR_DISTANCE,
    distance_space: str = DEFAULT_COLOR_DISTANCE_SPACE,
) -> Tuple[Color, ...]:
    """Sample one icon palette with anchor + pairwise color separation.

    TRACE icon scenes keep the panel/background chrome mostly fixed, so the icon
    palette should stay well separated from those anchors for readability.
    """

    return sample_color_palette_with_distance_constraints(
        rng,
        palette_size=max(1, int(palette_size)),
        channel_min=int(channel_min),
        channel_max=int(channel_max),
        anchor_colors=tuple(anchor_colors),
        min_distance=float(min_color_distance),
        distance_space=str(distance_space),
    )


def sample_icon_tints(
    rng,
    *,
    palette: Sequence[Color],
    count: int,
) -> Tuple[Color, ...]:
    """Sample one deterministic multiset of icon tints from a precomputed palette."""

    colors = [tuple(int(channel) for channel in color) for color in palette]
    if not colors:
        raise ValueError("palette must contain at least one color")
    return tuple(tuple(int(channel) for channel in rng.choice(colors)) for _ in range(max(0, int(count))))


def icon_palette_meets_distance_constraints(
    *,
    palette: Sequence[Color],
    anchor_colors: Iterable[Color],
    min_color_distance: float = DEFAULT_MIN_COLOR_DISTANCE,
    distance_space: str = DEFAULT_COLOR_DISTANCE_SPACE,
) -> bool:
    """Return whether a palette satisfies anchor + pairwise distance constraints."""

    threshold = float(min_color_distance)
    normalized_palette = [tuple(int(channel) for channel in color) for color in palette]
    normalized_anchors = [tuple(int(channel) for channel in color) for color in anchor_colors]
    for color in normalized_palette:
        for anchor in normalized_anchors:
            if float(color_distance(color, anchor, distance_space=str(distance_space))) < threshold:
                return False
    for index, left in enumerate(normalized_palette):
        for right in normalized_palette[index + 1 :]:
            if float(color_distance(left, right, distance_space=str(distance_space))) < threshold:
                return False
    return True


__all__ = ["icon_palette_meets_distance_constraints", "sample_icon_palette", "sample_icon_tints"]
