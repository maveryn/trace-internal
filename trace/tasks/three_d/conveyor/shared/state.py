"""Scene state and object catalogs for straight 3D conveyor scenes."""

from __future__ import annotations

from typing import Mapping, Tuple

from trace.tasks.shared.named_colors import available_named_colors, sample_named_color_palette
from trace.tasks.three_d.shared.object_resources import (
    OBJECT_CLUSTER_DIMENSIONS,
    OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE,
    OBJECT_CLUSTER_SHAPE_TYPES,
)


SCENE_ID = "conveyor"

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "warehouse_line",
    "factory_line",
    "parcel_line",
)

SEMANTIC_COLOR_RGB: Mapping[str, Tuple[int, int, int]] = {
    str(name): (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    for name, rgb in available_named_colors()
}

HORIZONTAL_LANE_KEYS: Tuple[str, ...] = ("top", "middle", "bottom")
VERTICAL_LANE_KEYS: Tuple[str, ...] = ("left", "middle", "right")

LANE_LABELS: Mapping[str, str] = {
    "top": "TOP",
    "bottom": "BOTTOM",
    "left": "LEFT",
    "right": "RIGHT",
    "middle": "MIDDLE",
}

CONVEYOR_OBJECT_SHAPE_TYPES: Tuple[str, ...] = tuple(
    shape
    for shape in (
        "apple",
        "sphere",
        "bell",
        "open_book",
        "bottle",
        "bowl",
        "button",
        "cactus",
        "calculator",
        "candle",
        "card",
        "carrot",
        "chess_piece",
        "clock",
        "cone",
        "cube",
        "cup",
        "cylinder",
        "dice",
        "drum",
        "mail_envelope",
        "flower",
        "glove",
        "hat",
        "heart",
        "jar",
        "key",
        "lantern",
        "leaf",
        "mushroom",
        "pencil",
        "plate",
        "plug",
        "puzzle_piece",
        "pyramid",
        "remote_control",
        "torus",
        "ruler",
        "shield",
        "star_prism",
        "tray",
        "trophy",
        "umbrella",
    )
    if shape in set(OBJECT_CLUSTER_SHAPE_TYPES)
)


def public_object_name(shape_type: str) -> str:
    """Return the prompt-facing object name for one conveyor object."""

    return str(OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE.get(str(shape_type), str(shape_type).replace("_", " ")))


def public_object_plural(shape_type: str) -> str:
    """Return the prompt-facing plural object name for one conveyor object."""

    raw = public_object_name(str(shape_type)).strip()
    if raw in {"fish", "dice"}:
        return raw
    if raw.endswith("y") and (len(raw) < 2 or raw[-2].lower() not in {"a", "e", "i", "o", "u"}):
        return f"{raw[:-1]}ies"
    if raw.endswith(("s", "x", "z", "ch", "sh")):
        return f"{raw}es"
    return f"{raw}s"


def object_dimensions(shape_type: str, *, scale: float) -> tuple[float, float, float]:
    """Return scaled base dimensions for one scene object."""

    base = OBJECT_CLUSTER_DIMENSIONS.get(str(shape_type), (0.52, 0.52, 0.52))
    return tuple(round(float(value) * float(scale), 4) for value in base)


def sample_visual_color_names(rng: object, *, palette_size: int = 4) -> tuple[str, ...]:
    """Sample canonical named colors for non-semantic visual variety."""

    palette = sample_named_color_palette(rng, palette_size=int(palette_size))
    return tuple(str(name) for name, _rgb in palette)


__all__ = [
    "CONVEYOR_OBJECT_SHAPE_TYPES",
    "HORIZONTAL_LANE_KEYS",
    "LANE_LABELS",
    "SCENE_ID",
    "SEMANTIC_COLOR_RGB",
    "SUPPORTED_SCENE_VARIANTS",
    "VERTICAL_LANE_KEYS",
    "object_dimensions",
    "public_object_name",
    "public_object_plural",
    "sample_visual_color_names",
]
