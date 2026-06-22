"""Scene constants and object naming helpers for dense 3D clusters."""

from __future__ import annotations

from typing import Dict, Mapping, Sequence, Tuple

from trace.tasks.shared.named_colors import available_named_colors
from trace.tasks.three_d.shared.object_resources import (
    OBJECT_CLUSTER_DIMENSIONS,
    OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE,
    OBJECT_CLUSTER_SHAPE_TYPES,
)


SCENE_ID = "object_cluster"
CLUSTER_SCENE_VARIANTS: Tuple[str, ...] = ("tabletop_pile", "shallow_tray", "cluster_mat")
CLUSTER_COMPOSITION_MODES: Tuple[str, ...] = (
    "single_type_cluster",
    "near_homogeneous_cluster",
    "mixed_type_cluster",
)
OBJECT_CLUSTER_EXCLUDED_SHAPE_TYPES: Tuple[str, ...] = ("stick",)
COUNTABLE_SHAPE_TYPES: Tuple[str, ...] = tuple(
    str(shape)
    for shape in OBJECT_CLUSTER_SHAPE_TYPES
    if str(shape) not in set(OBJECT_CLUSTER_EXCLUDED_SHAPE_TYPES)
)
OBJECT_CLUSTER_ORIENTATION_DEGREES = 15.0
CLUSTER_DIMENSION_SCALE = 1.04
MIN_PROJECTED_OBJECT_AREA_PX = 320.0
MAX_PAIRWISE_OVERLAP_FRACTION = 0.55
MAX_PAIRWISE_OVERLAP_PX = 4600.0
MAX_RENDERED_PAIRWISE_OVERLAP_FRACTION = 0.50
MAX_RENDERED_PAIRWISE_OVERLAP_PX = 5000.0
MIN_RENDERED_VISIBLE_BBOX_FRACTION = 0.50
MIN_RENDERED_BBOX_SIDE_PX = 24.0
PLACEMENT_FOOTPRINT_SEPARATION_FACTOR = 0.58
CLUSTER_COUNT_WEIGHTS: Mapping[int, float] = {
    1: 0.65,
    2: 0.28,
    3: 0.07,
}
ANSWER_COUNT_BINS: Mapping[str, Tuple[int, int]] = {
    "4_8": (4, 8),
    "6_10": (6, 10),
    "11_17": (11, 17),
    "18_25": (18, 25),
}
DEFAULT_ANSWER_COUNT_BIN_WEIGHTS: Mapping[str, float] = {
    "6_10": 0.35,
    "11_17": 0.40,
    "18_25": 0.25,
}

PROMPT_COLOR_RGB: Dict[str, Tuple[int, int, int]] = {
    str(name): (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    for name, rgb in available_named_colors()
}
COLOR_SAFE_CLUSTER_SHAPE_TYPES: Tuple[str, ...] = tuple(
    shape
    for shape in (
        "sphere",
        "cube",
        "cylinder",
        "cone",
        "torus",
        "pyramid",
        "wedge",
        "star_prism",
        "diamond",
        "heart",
        "button",
        "candy_disc",
        "berry",
        "card",
        "bookmark",
        "small_box",
        "puzzle_piece",
        "cup",
        "bowl",
        "plate",
        "mini_chair",
        "mini_table",
        "stool",
        "flower",
        "cushion",
        "jar",
        "can",
        "lid",
        "bucket",
        "tray",
        "coaster",
        "clip",
        "socket",
        "hook",
        "tape_roll",
        "bag",
        "chess_piece",
        "straw",
        "ticket",
        "marble",
        "bead",
    )
    if shape in set(COUNTABLE_SHAPE_TYPES)
)
# Semantic-color tasks only use shapes whose projected renderer makes ``fill_rgb``
# a visible body color. Canonical-color glyphs such as books, apples, dice, and
# clocks stay available for non-color object-cluster tasks.
COLOR_READOUT_CLUSTER_SHAPE_TYPES: Tuple[str, ...] = tuple(
    shape
    for shape in (
        "sphere",
        "cube",
        "cylinder",
        "cone",
        "torus",
        "pyramid",
        "wedge",
        "star_prism",
        "diamond",
        "heart",
        "small_box",
        "puzzle_piece",
        "cup",
        "bowl",
        "stool",
        "flower",
        "can",
        "bucket",
        "tray",
        "bag",
        "chess_piece",
        "arrow",
        "shield",
        "gear",
        "flask",
        "half_cylinder",
    )
    if shape in set(COUNTABLE_SHAPE_TYPES)
)

COLOR_CONFUSION_EXCLUSIONS: Mapping[str, Tuple[str, ...]] = {
    "blue": ("cyan", "purple"),
    "red": ("maroon", "magenta"),
    "yellow": ("orange", "brown"),
    "orange": ("yellow", "brown"),
    "cyan": ("blue",),
    "maroon": ("red", "magenta"),
    "magenta": ("red", "maroon"),
    "brown": ("yellow", "orange"),
}

VISUAL_CONFUSION_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("pen", "pencil", "ruler", "tube", "stick", "straw"),
    ("card", "bookmark", "small_box", "ticket", "mail_envelope", "open_book"),
    ("candy_disc", "cd", "berry", "button", "sphere", "marble", "bead", "coaster", "lid"),
    ("screw", "hex_nut", "clip", "socket", "bolt", "hook", "tape_roll", "torus"),
    ("fork", "spoon"),
    ("plate", "bowl", "cup", "jar", "can", "lid", "bottle", "bucket", "tray", "coaster", "basket"),
    ("hammer", "paint_brush"),
    ("flower", "rose", "cactus", "leaf", "egg", "apple", "carrot", "tomato"),
    ("light_bulb", "lantern", "candle"),
    ("horseshoe", "umbrella"),
    ("mini_chair", "mini_table", "chair", "table", "stool"),
    ("small_box", "cabinet"),
    ("chess_piece", "trophy", "crown"),
)


def object_name_for_shape(shape_type: str) -> str:
    """Return the public object name for one cluster shape."""

    return str(OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE.get(str(shape_type), str(shape_type).replace("_", " ")))


def object_plural(name: str) -> str:
    """Pluralize the short object labels used in prompts and trace metadata."""

    raw = str(name).strip()
    if raw in {"fish", "dice"}:
        return raw
    if raw.endswith("y") and (len(raw) < 2 or raw[-2].lower() not in {"a", "e", "i", "o", "u"}):
        return f"{raw[:-1]}ies"
    if raw.endswith(("s", "x", "z", "ch", "sh")):
        return f"{raw}es"
    return f"{raw}s"


def shape_plural(shape_type: str) -> str:
    """Return the prompt plural for one object shape type."""

    return object_plural(object_name_for_shape(str(shape_type)))


def cluster_dimensions(shape_type: str) -> tuple[float, float, float]:
    """Resolve dimensions for count-cluster resources with a stable fallback."""

    return tuple(float(value) for value in OBJECT_CLUSTER_DIMENSIONS.get(str(shape_type), (0.52, 0.52, 0.52)))


def compatible_distractor_pool(target_shape_type: str, *, support: Sequence[str] = COUNTABLE_SHAPE_TYPES) -> Tuple[str, ...]:
    """Choose shape distractors while avoiding visually near-identical groups."""

    blocked = {str(target_shape_type)}
    for group in VISUAL_CONFUSION_GROUPS:
        if str(target_shape_type) in {str(item) for item in group}:
            blocked.update(str(item) for item in group)
    pool = tuple(str(shape) for shape in support if str(shape) not in blocked)
    if not pool:
        raise ValueError("object cluster needs at least one compatible distractor shape")
    return pool


__all__ = [
    "ANSWER_COUNT_BINS",
    "CLUSTER_COMPOSITION_MODES",
    "CLUSTER_COUNT_WEIGHTS",
    "CLUSTER_DIMENSION_SCALE",
    "CLUSTER_SCENE_VARIANTS",
    "COLOR_CONFUSION_EXCLUSIONS",
    "COLOR_READOUT_CLUSTER_SHAPE_TYPES",
    "COLOR_SAFE_CLUSTER_SHAPE_TYPES",
    "COUNTABLE_SHAPE_TYPES",
    "DEFAULT_ANSWER_COUNT_BIN_WEIGHTS",
    "MAX_PAIRWISE_OVERLAP_FRACTION",
    "MAX_PAIRWISE_OVERLAP_PX",
    "MAX_RENDERED_PAIRWISE_OVERLAP_FRACTION",
    "MAX_RENDERED_PAIRWISE_OVERLAP_PX",
    "MIN_RENDERED_VISIBLE_BBOX_FRACTION",
    "MIN_RENDERED_BBOX_SIDE_PX",
    "MIN_PROJECTED_OBJECT_AREA_PX",
    "OBJECT_CLUSTER_EXCLUDED_SHAPE_TYPES",
    "OBJECT_CLUSTER_ORIENTATION_DEGREES",
    "PLACEMENT_FOOTPRINT_SEPARATION_FACTOR",
    "PROMPT_COLOR_RGB",
    "SCENE_ID",
    "cluster_dimensions",
    "compatible_distractor_pool",
    "object_name_for_shape",
    "object_plural",
    "shape_plural",
]
