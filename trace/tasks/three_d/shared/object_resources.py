"""Canonical named object resources for TRACE 3D scenes.

This module is the ownership point for object pools, display names, base
dimensions, and scene-role profiles used by the three_d domain. Scene modules
should select objects from these definitions instead of maintaining independent
object inventories.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Mapping, Sequence, Tuple


OBJECT_SCENE_ID = "object_scene"
ROOM_SCENE_ID = "room"
STREET_SCENE_ID = "street"
WAREHOUSE_SCENE_ID = "warehouse"


@dataclass(frozen=True)
class ThreeDObjectProfile:
    """One domain-owned rendering profile for a canonical named object."""

    profile_id: str
    canonical_id: str
    source_scene: str
    role: str
    object_type: str
    display_name: str
    size_class: str
    renderer: str
    resource_kind: str = "standalone"
    support_required: bool = False
    base_object_type: str | None = None
    support_profile_id: str | None = None
    mounting: str | None = None
    dimensions_xyz: Tuple[float, ...] | None = None


def _canonical_id(display_name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(display_name).strip().lower())
    return cleaned.strip("_") or "object"


OBJECT_SCENE_SMALL_SHAPE_TYPES: Tuple[str, ...] = (
    "sphere",
    "cube",
    "cylinder",
    "cone",
    "arrow",
    "sword",
    "shield",
    "diamond",
    "heart",
    "key",
    "crown",
    "hourglass",
    "anchor",
    "horseshoe",
    "hammer",
    "gear",
    "bell",
    "trophy",
    "open_book",
    "dumbbell",
    "mushroom",
    "lantern",
    "wrench",
    "padlock",
    "magnifying_glass",
    "candle",
    "scroll",
    "paint_brush",
    "paint_palette",
    "goblet",
    "teapot",
    "watering_can",
    "basket",
    "mail_envelope",
    "camera",
    "compass",
    "flask",
    "test_tube_rack",
    "scroll_map",
    "microphone",
    "stopwatch",
    "clock",
    "apple",
    "carrot",
    "pear",
    "fish",
    "leaf",
    "feather",
    "shoe",
    "glove",
    "hat",
    "helmet",
    "cup",
    "bottle",
    "vase",
    "umbrella",
    "scissors",
    "screwdriver",
    "pencil",
    "fork",
    "spoon",
    "spatula",
    "toothbrush",
    "comb",
    "whistle",
    "flashlight",
    "calculator",
    "phone",
    "light_bulb",
    "suitcase",
    "dice",
    "rocket",
    "kite",
    "paint_can",
    "cactus",
    "pumpkin",
    "acorn",
    "pinecone",
    "seashell",
    "magnet",
    "guitar",
    "drum",
    "shovel",
    "saw",
    "pliers",
    "telescope",
    "ruler",
    "pickaxe",
    "paint_roller",
    "tape_measure",
    "remote_control",
    "plug",
    "wallet",
    "purse",
    "sunglasses",
    "violin",
    "trumpet",
    "donut",
    "pretzel",
    "lollipop",
    "ice_cream_cone",
    "soap_bar",
    "torus",
    "pyramid",
    "wedge",
    "star_prism",
    "hexagonal_prism",
    "half_cylinder",
)
OBJECT_SCENE_CONTEXT_SHAPE_TYPES: Tuple[str, ...] = (
    "arch",
    "table",
    "shelf",
    "open_box",
    "pedestal",
    "cabinet",
    "sofa",
    "barrel",
    "chair",
)
OBJECT_SCENE_SHAPE_TYPES: Tuple[str, ...] = OBJECT_SCENE_SMALL_SHAPE_TYPES + OBJECT_SCENE_CONTEXT_SHAPE_TYPES
OBJECT_SCENE_NAME_BY_SHAPE_TYPE: Dict[str, str] = {
    "sphere": "ball",
    "cube": "cube",
    "cylinder": "cylinder",
    "cone": "cone",
    "arrow": "arrow",
    "sword": "sword",
    "shield": "shield",
    "diamond": "diamond",
    "heart": "heart",
    "key": "key",
    "crown": "crown",
    "hourglass": "hourglass",
    "anchor": "anchor",
    "horseshoe": "horseshoe",
    "hammer": "hammer",
    "gear": "gear",
    "bell": "bell",
    "trophy": "trophy",
    "open_book": "book",
    "dumbbell": "dumbbell",
    "mushroom": "mushroom",
    "lantern": "lantern",
    "wrench": "wrench",
    "padlock": "padlock",
    "magnifying_glass": "magnifying glass",
    "candle": "candle",
    "scroll": "scroll",
    "paint_brush": "paint brush",
    "paint_palette": "paint palette",
    "goblet": "goblet",
    "teapot": "teapot",
    "watering_can": "watering can",
    "basket": "basket",
    "mail_envelope": "envelope",
    "camera": "camera",
    "compass": "compass",
    "flask": "flask",
    "test_tube_rack": "test tube rack",
    "scroll_map": "map",
    "microphone": "microphone",
    "stopwatch": "stopwatch",
    "clock": "clock",
    "apple": "apple",
    "carrot": "carrot",
    "pear": "pear",
    "fish": "fish",
    "leaf": "leaf",
    "feather": "feather",
    "shoe": "shoe",
    "glove": "glove",
    "hat": "hat",
    "helmet": "helmet",
    "cup": "cup",
    "bottle": "bottle",
    "vase": "vase",
    "umbrella": "umbrella",
    "scissors": "scissors",
    "screwdriver": "screwdriver",
    "pencil": "pencil",
    "fork": "fork",
    "spoon": "spoon",
    "spatula": "spatula",
    "toothbrush": "toothbrush",
    "comb": "comb",
    "whistle": "whistle",
    "flashlight": "flashlight",
    "calculator": "calculator",
    "phone": "phone",
    "light_bulb": "light bulb",
    "suitcase": "suitcase",
    "dice": "dice",
    "rocket": "rocket",
    "kite": "kite",
    "paint_can": "paint can",
    "cactus": "cactus",
    "pumpkin": "pumpkin",
    "acorn": "acorn",
    "pinecone": "pinecone",
    "seashell": "seashell",
    "magnet": "magnet",
    "guitar": "guitar",
    "drum": "drum",
    "shovel": "shovel",
    "saw": "saw",
    "pliers": "pliers",
    "telescope": "telescope",
    "ruler": "ruler",
    "pickaxe": "pickaxe",
    "paint_roller": "paint roller",
    "tape_measure": "tape measure",
    "remote_control": "remote control",
    "plug": "plug",
    "wallet": "wallet",
    "purse": "purse",
    "sunglasses": "sunglasses",
    "violin": "violin",
    "trumpet": "trumpet",
    "donut": "donut",
    "pretzel": "pretzel",
    "lollipop": "lollipop",
    "ice_cream_cone": "ice cream cone",
    "soap_bar": "soap bar",
    "torus": "ring",
    "pyramid": "pyramid",
    "wedge": "ramp",
    "star_prism": "star",
    "hexagonal_prism": "hexagon",
    "half_cylinder": "half cylinder",
    "arch": "arch",
    "table": "table",
    "shelf": "shelf",
    "open_box": "open box",
    "pedestal": "stand",
    "cabinet": "cabinet",
    "sofa": "sofa",
    "barrel": "barrel",
    "chair": "chair",
}
OBJECT_SCENE_SMALL_DIMENSIONS: Dict[str, Tuple[float, float, float]] = {
    "sphere": (0.48, 0.48, 0.48),
    "cube": (0.52, 0.52, 0.52),
    "cylinder": (0.50, 0.50, 0.64),
    "cone": (0.54, 0.54, 0.68),
    "arrow": (0.52, 0.73, 0.24),
    "sword": (0.50, 0.73, 0.24),
    "shield": (0.64, 0.20, 0.74),
    "diamond": (0.64, 0.64, 0.72),
    "heart": (0.66, 0.20, 0.64),
    "key": (0.46, 0.72, 0.22),
    "crown": (0.68, 0.20, 0.66),
    "hourglass": (0.56, 0.20, 0.92),
    "anchor": (0.64, 0.20, 0.92),
    "horseshoe": (0.64, 0.20, 0.78),
    "hammer": (0.56, 0.72, 0.24),
    "gear": (0.70, 0.70, 0.30),
    "bell": (0.66, 0.20, 0.74),
    "trophy": (0.70, 0.20, 0.82),
    "open_book": (0.72, 0.20, 0.58),
    "dumbbell": (0.72, 0.32, 0.24),
    "mushroom": (0.62, 0.20, 0.70),
    "lantern": (0.62, 0.20, 0.82),
    "wrench": (0.54, 0.72, 0.22),
    "padlock": (0.56, 0.20, 0.78),
    "magnifying_glass": (0.62, 0.72, 0.20),
    "candle": (0.36, 0.36, 0.88),
    "scroll": (0.72, 0.28, 0.38),
    "paint_brush": (0.48, 0.72, 0.22),
    "paint_palette": (0.70, 0.20, 0.62),
    "goblet": (0.58, 0.20, 0.78),
    "teapot": (0.72, 0.54, 0.58),
    "watering_can": (0.72, 0.54, 0.62),
    "basket": (0.72, 0.54, 0.42),
    "mail_envelope": (0.72, 0.18, 0.52),
    "camera": (0.72, 0.38, 0.50),
    "compass": (0.62, 0.20, 0.62),
    "flask": (0.58, 0.20, 0.78),
    "test_tube_rack": (0.72, 0.36, 0.62),
    "scroll_map": (0.72, 0.58, 0.12),
    "microphone": (0.46, 0.26, 0.86),
    "stopwatch": (0.58, 0.20, 0.72),
    "clock": (0.58, 0.20, 0.68),
    "apple": (0.58, 0.58, 0.58),
    "carrot": (0.44, 0.22, 0.76),
    "pear": (0.56, 0.56, 0.70),
    "fish": (0.72, 0.22, 0.44),
    "leaf": (0.68, 0.18, 0.42),
    "feather": (0.52, 0.18, 0.78),
    "shoe": (0.72, 0.38, 0.32),
    "glove": (0.66, 0.18, 0.70),
    "hat": (0.72, 0.52, 0.42),
    "helmet": (0.66, 0.52, 0.50),
    "cup": (0.50, 0.50, 0.62),
    "bottle": (0.42, 0.42, 0.82),
    "vase": (0.54, 0.54, 0.78),
    "umbrella": (0.72, 0.20, 0.82),
    "scissors": (0.64, 0.58, 0.18),
    "screwdriver": (0.38, 0.72, 0.20),
    "pencil": (0.34, 0.72, 0.18),
    "fork": (0.38, 0.72, 0.16),
    "spoon": (0.38, 0.72, 0.16),
    "spatula": (0.46, 0.72, 0.18),
    "toothbrush": (0.36, 0.72, 0.16),
    "comb": (0.72, 0.72, 0.22),
    "whistle": (0.62, 0.38, 0.34),
    "flashlight": (0.42, 0.72, 0.28),
    "calculator": (0.60, 0.20, 0.78),
    "phone": (0.48, 0.18, 0.78),
    "light_bulb": (0.48, 0.48, 0.72),
    "suitcase": (0.70, 0.32, 0.62),
    "dice": (0.54, 0.54, 0.54),
    "rocket": (0.50, 0.24, 0.82),
    "kite": (0.64, 0.18, 0.74),
    "paint_can": (0.54, 0.54, 0.58),
    "cactus": (0.58, 0.22, 0.84),
    "pumpkin": (0.64, 0.64, 0.54),
    "acorn": (0.52, 0.52, 0.62),
    "pinecone": (0.52, 0.42, 0.76),
    "seashell": (0.66, 0.18, 0.54),
    "magnet": (0.60, 0.20, 0.72),
    "guitar": (0.54, 0.72, 0.20),
    "drum": (0.56, 0.56, 0.76),
    "shovel": (0.44, 0.72, 0.22),
    "saw": (0.46, 0.72, 0.18),
    "pliers": (0.58, 0.60, 0.18),
    "telescope": (0.46, 0.72, 0.28),
    "ruler": (0.34, 0.72, 0.14),
    "pickaxe": (0.58, 0.72, 0.20),
    "paint_roller": (0.48, 0.72, 0.24),
    "tape_measure": (0.60, 0.44, 0.38),
    "remote_control": (0.46, 0.18, 0.78),
    "plug": (0.58, 0.42, 0.42),
    "wallet": (0.70, 0.20, 0.48),
    "purse": (0.64, 0.24, 0.62),
    "sunglasses": (0.72, 0.24, 0.26),
    "violin": (0.56, 0.72, 0.20),
    "trumpet": (0.50, 0.72, 0.28),
    "donut": (0.62, 0.62, 0.24),
    "pretzel": (0.70, 0.22, 0.44),
    "lollipop": (0.46, 0.22, 0.78),
    "ice_cream_cone": (0.54, 0.54, 0.74),
    "soap_bar": (0.62, 0.42, 0.24),
    "torus": (0.62, 0.62, 0.30),
    "pyramid": (0.58, 0.58, 0.58),
    "wedge": (0.70, 0.52, 0.54),
    "star_prism": (0.72, 0.72, 0.42),
    "hexagonal_prism": (0.66, 0.66, 0.52),
    "half_cylinder": (0.72, 0.52, 0.50),
}
OBJECT_SCENE_CONTEXT_DIMENSIONS: Dict[str, Tuple[float, float, float]] = {
    "arch": (1.92, 0.66, 1.84),
    "table": (2.06, 1.42, 1.10),
    "shelf": (1.78, 0.68, 1.96),
    "open_box": (1.62, 1.22, 0.80),
    "pedestal": (1.06, 1.06, 1.34),
    "cabinet": (1.42, 0.72, 1.92),
    "sofa": (2.12, 1.12, 0.92),
    "barrel": (1.00, 1.00, 1.90),
    "chair": (1.10, 1.02, 1.54),
}
SPATIAL_REFERENCE_NEAREST_REFERENCE_SHAPE_TYPES: Tuple[str, ...] = (
    "sphere",
    "cube",
    "cylinder",
    "cone",
    "torus",
    "pyramid",
    "wedge",
    "arch",
    "table",
    "shelf",
    "open_box",
    "pedestal",
    "cabinet",
    "sofa",
    "barrel",
    "chair",
)
SPATIAL_OBJECT_RELATION_ON_TOP_PROP_TYPES: Tuple[str, ...] = ("table", "shelf", "pedestal")
SPATIAL_OBJECT_RELATION_UNDER_PROP_TYPES: Tuple[str, ...] = ("arch", "table")
SPATIAL_OBJECT_RELATION_INSIDE_PROP_TYPES: Tuple[str, ...] = ("open_box",)
SPATIAL_OBJECT_RELATION_ELEVATED_COMPATIBLE_SHAPES: Tuple[str, ...] = ("sphere", "cube", "torus")
SPATIAL_OCCLUSION_REFERENCE_SHAPE_TYPES: Tuple[str, ...] = (
    "arch",
    "table",
    "shelf",
    "pedestal",
    "cabinet",
    "sofa",
    "barrel",
    "chair",
)
SPATIAL_BETWEEN_REFERENCE_SHAPE_TYPES: Tuple[str, ...] = (
    "arch",
    "table",
    "shelf",
    "open_box",
    "pedestal",
    "cabinet",
    "sofa",
    "barrel",
    "chair",
)
SPATIAL_HEIGHT_SUPPORT_PLACEMENTS: Tuple[Tuple[str, str | None, Tuple[float, float]], ...] = (
    ("floor_spot", None, (-2.58, -2.42)),
    ("open_box_low", "open_box", (2.46, -2.28)),
    ("table_top", "table", (-2.32, 0.12)),
    ("chair_seat", "chair", (2.32, 0.18)),
    ("pedestal_top", "pedestal", (-1.22, 2.34)),
    ("shelf_top", "shelf", (1.46, 2.24)),
)
SPATIAL_HEIGHT_FLOOR_CANDIDATE_SHAPE_TYPES: Tuple[str, ...] = ("sphere", "cube", "cylinder", "cone", "pyramid")
SPATIAL_HEIGHT_ELEVATED_CANDIDATE_SHAPE_TYPES: Tuple[str, ...] = ("cube", "cylinder")


ROOM_QUERY_OBJECT_TYPE_BY_VARIANT: Dict[str, str] = {
    "tv_wall_mounted_count": "tv",
    "clock_wall_mounted_count": "clock",
    "picture_frame_wall_mounted_count": "picture_frame",
    "mirror_wall_mounted_count": "mirror",
    "wall_shelf_wall_mounted_count": "wall_shelf",
    "wall_fan_wall_mounted_count": "wall_fan",
    "air_conditioner_wall_mounted_count": "air_conditioner",
    "hanging_plant_wall_mounted_count": "hanging_plant",
    "hanging_coat_wall_mounted_count": "hanging_coat",
}
ROOM_OBJECT_PROMPT_NAMES: Dict[str, Tuple[str, str]] = {
    "tv": ("TV", "TVs"),
    "clock": ("clock", "clocks"),
    "picture_frame": ("picture frame", "picture frames"),
    "mirror": ("mirror", "mirrors"),
    "wall_shelf": ("shelf", "shelves"),
    "wall_fan": ("fan", "fans"),
    "air_conditioner": ("air conditioner", "air conditioners"),
    "hanging_plant": ("hanging plant", "hanging plants"),
    "hanging_coat": ("coat", "coats"),
    "poster": ("poster", "posters"),
    "wall_lamp": ("wall lamp", "wall lamps"),
    "speaker": ("speaker", "speakers"),
    "wall_cabinet": ("wall cabinet", "wall cabinets"),
}
ROOM_QUERY_TARGET_TYPES: Tuple[str, ...] = tuple(ROOM_QUERY_OBJECT_TYPE_BY_VARIANT.values())
ROOM_EXTRA_WALL_TYPES: Tuple[str, ...] = ("poster", "wall_lamp", "speaker", "wall_cabinet")
ROOM_FLOOR_DISTRACTOR_TYPES: Tuple[str, ...] = (
    "tv",
    "clock",
    "picture_frame",
    "mirror",
    "wall_shelf",
    "wall_fan",
    "air_conditioner",
    "hanging_plant",
    "hanging_coat",
)
ROOM_SURFACE_DISTRACTOR_TYPES: Tuple[str, ...] = ("tv", "clock", "picture_frame")
ROOM_SURFACE_PROP_SHAPES_BY_SCENE: Dict[str, Tuple[str, ...]] = {
    "living_room": ("coffee_table", "media_console", "side_table"),
    "office_room": ("desk", "side_table", "media_console"),
    "studio_room": ("bed", "desk", "coffee_table"),
}
ROOM_SURFACE_PROP_TYPES: Tuple[str, ...] = ("coffee_table", "media_console", "side_table", "desk", "bed")
ROOM_FLOOR_PROP_SHAPES: Tuple[str, ...] = (
    "sofa",
    "armchair",
    "coffee_table",
    "media_console",
    "side_table",
    "desk",
    "bed",
    "plant",
    "floor_lamp",
    "box",
    "ball",
    "open_box",
)
ROOM_FRONT_FLOOR_PROP_SHAPES: Tuple[str, ...] = ("armchair", "coffee_table", "plant", "floor_lamp", "box", "open_box")
ROOM_CAMERA_DISTANCE_CANDIDATE_WALL_OBJECT_TYPES: Tuple[str, ...] = (
    "tv",
    "clock",
    "picture_frame",
    "mirror",
    "wall_fan",
    "air_conditioner",
    "hanging_plant",
    "hanging_coat",
)
ROOM_CAMERA_DISTANCE_CONTEXT_WALL_OBJECT_TYPES: Tuple[str, ...] = ("poster", "wall_lamp", "speaker", "wall_cabinet")
ROOM_SAME_WALL_REFERENCE_WALL_OBJECT_TYPES: Tuple[str, ...] = (
    "tv",
    "clock",
    "mirror",
    "wall_fan",
    "air_conditioner",
    "hanging_plant",
    "hanging_coat",
)
ROOM_SIDE_RELATION_REFERENCE_OBJECT_TYPE = "tv"
ROOM_WALL_BASE_DIMENSIONS: Dict[str, Tuple[float, float]] = {
    "tv": (1.02, 0.60),
    "clock": (0.66, 0.66),
    "picture_frame": (0.58, 0.48),
    "mirror": (0.62, 0.82),
    "wall_shelf": (0.96, 0.16),
    "wall_fan": (0.78, 0.78),
    "air_conditioner": (0.92, 0.38),
    "hanging_plant": (0.48, 0.64),
    "hanging_coat": (0.78, 1.02),
    "poster": (0.52, 0.70),
    "wall_lamp": (0.30, 0.42),
    "speaker": (0.46, 0.66),
    "wall_cabinet": (0.66, 0.58),
}
ROOM_SURFACE_DISTRACTOR_SPECS: Dict[str, Dict[str, object]] = {
    "tv": {"prompt_name": "tabletop TV", "dimensions_xyz": (0.66, 0.10, 0.38), "color_role": "tv_floor"},
    "clock": {"prompt_name": "tabletop clock", "dimensions_xyz": (0.42, 0.16, 0.42), "color_role": "clock_floor"},
    "picture_frame": {
        "prompt_name": "tabletop picture frame",
        "dimensions_xyz": (0.34, 0.06, 0.34),
        "color_role": "picture_frame_floor",
    },
}
ROOM_FLOOR_DISTRACTOR_SPECS: Dict[str, Dict[str, object]] = {
    "tv": {"prompt_name": "floor-standing TV", "dimensions_xyz": (0.95, 0.16, 0.58), "color_role": "tv_floor"},
    "clock": {"prompt_name": "floor clock", "dimensions_xyz": (0.54, 0.22, 0.54), "color_role": "clock_floor"},
    "picture_frame": {
        "prompt_name": "leaning picture frame",
        "dimensions_xyz": (0.55, 0.08, 0.58),
        "color_role": "picture_frame_floor",
    },
    "mirror": {"prompt_name": "standing mirror", "dimensions_xyz": (0.58, 0.10, 0.96), "color_role": "mirror_floor"},
    "wall_fan": {"prompt_name": "floor fan", "dimensions_xyz": (0.66, 0.20, 0.82), "color_role": "fan_floor"},
    "air_conditioner": {
        "prompt_name": "portable air conditioner",
        "dimensions_xyz": (0.46, 0.26, 0.76),
        "color_role": "ac_floor",
    },
    "hanging_plant": {"prompt_name": "potted plant", "dimensions_xyz": (0.42, 0.42, 0.58), "color_role": "plant"},
    "hanging_coat": {"prompt_name": "coat on stand", "dimensions_xyz": (0.62, 0.18, 1.02), "color_role": "coat_floor"},
    "wall_shelf": {"prompt_name": "standing shelf", "dimensions_xyz": (0.70, 0.34, 1.05), "color_role": "shelf_floor"},
}
ROOM_FLOOR_PROP_SPECS: Dict[str, Dict[str, object]] = {
    "sofa": {"object_type": "sofa", "prompt_name": "sofa", "dimensions_xyz": (1.58, 0.74, 0.62), "color_role": "sofa"},
    "armchair": {
        "object_type": "armchair",
        "prompt_name": "armchair",
        "dimensions_xyz": (0.82, 0.72, 0.70),
        "color_role": "armchair",
    },
    "coffee_table": {
        "object_type": "coffee_table",
        "prompt_name": "coffee table",
        "dimensions_xyz": (1.18, 0.66, 0.46),
        "color_role": "wood",
        "shape_type": "table",
    },
    "side_table": {
        "object_type": "side_table",
        "prompt_name": "side table",
        "dimensions_xyz": (0.58, 0.48, 0.52),
        "color_role": "wood",
        "shape_type": "table",
    },
    "desk": {
        "object_type": "desk",
        "prompt_name": "desk",
        "dimensions_xyz": (1.36, 0.70, 0.74),
        "color_role": "wood",
        "shape_type": "table",
    },
    "media_console": {
        "object_type": "media_console",
        "prompt_name": "media console",
        "dimensions_xyz": (1.34, 0.38, 0.46),
        "color_role": "wood",
    },
    "bed": {"object_type": "bed", "prompt_name": "bed", "dimensions_xyz": (1.62, 1.04, 0.48), "color_role": "bed"},
    "plant": {
        "object_type": "plant",
        "prompt_name": "plant",
        "dimensions_xyz": (0.45, 0.45, 0.72),
        "color_role": "plant",
        "shape_type": "cylinder",
    },
    "floor_lamp": {
        "object_type": "floor_lamp",
        "prompt_name": "floor lamp",
        "dimensions_xyz": (0.36, 0.36, 1.42),
        "color_role": "lamp",
        "shape_type": "cylinder",
    },
    "ball": {
        "object_type": "ball",
        "prompt_name": "ball",
        "dimensions_xyz": (0.42, 0.42, 0.42),
        "color_role": "toy",
        "shape_type": "sphere",
    },
    "open_box": {
        "object_type": "open_box",
        "prompt_name": "open box",
        "dimensions_xyz": (0.72, 0.56, 0.34),
        "color_role": "box",
        "shape_type": "open_box",
    },
    "box": {"object_type": "box", "prompt_name": "box", "dimensions_xyz": (0.52, 0.48, 0.46), "color_role": "box"},
}


STREET_OBJECT_TYPES: Tuple[str, ...] = (
    "car",
    "taxi",
    "van",
    "bus",
    "delivery_truck",
    "pickup_truck",
    "scooter",
    "motorcycle",
    "pedestrian",
    "bicycle",
    "traffic_cone",
    "fire_hydrant",
    "trash_bin",
    "mailbox",
    "construction_barrier",
    "road_barrel",
)
STREET_VEHICLE_OBJECT_TYPES = {"car", "taxi", "van", "bus", "delivery_truck", "pickup_truck"}
STREET_CONTEXT_OBJECT_TYPES: Tuple[str, ...] = ("building", "tree", "shrub", "traffic_light", "street_sign", "bench")
STREET_SAME_ROAD_REFERENCE_OBJECT_TYPES: Tuple[str, ...] = (
    "car",
    "taxi",
    "van",
    "bus",
    "pickup_truck",
    "scooter",
    "motorcycle",
    "bicycle",
    "fire_hydrant",
    "mailbox",
    "trash_bin",
)
STREET_LANE_AHEAD_REFERENCE_OBJECT_TYPE = "car"
STREET_OBJECT_NAMES: Dict[str, str] = {
    "car": "car",
    "taxi": "taxi",
    "van": "van",
    "bus": "bus",
    "delivery_truck": "delivery truck",
    "pickup_truck": "pickup truck",
    "scooter": "scooter",
    "motorcycle": "motorcycle",
    "pedestrian": "pedestrian",
    "bicycle": "bicycle",
    "traffic_cone": "traffic cone",
    "fire_hydrant": "fire hydrant",
    "trash_bin": "trash bin",
    "mailbox": "mailbox",
    "construction_barrier": "construction barrier",
    "road_barrel": "road barrel",
    "building": "building",
    "tree": "tree",
    "shrub": "shrub",
    "traffic_light": "traffic light",
    "street_sign": "street sign",
    "bench": "bench",
}
STREET_OBJECT_COLORS: Dict[str, Tuple[int, int, int]] = {
    "car": (65, 121, 205),
    "taxi": (231, 181, 55),
    "van": (112, 131, 151),
    "bus": (218, 111, 59),
    "delivery_truck": (204, 83, 77),
    "pickup_truck": (74, 151, 111),
    "scooter": (150, 86, 177),
    "motorcycle": (45, 65, 86),
    "pedestrian": (52, 135, 160),
    "bicycle": (70, 83, 107),
    "traffic_cone": (225, 121, 45),
    "fire_hydrant": (218, 58, 49),
    "trash_bin": (79, 121, 93),
    "mailbox": (42, 104, 164),
    "construction_barrier": (229, 131, 48),
    "road_barrel": (223, 102, 45),
    "building": (150, 142, 131),
    "tree": (77, 132, 76),
    "shrub": (70, 145, 84),
    "traffic_light": (63, 70, 78),
    "street_sign": (75, 132, 94),
    "bench": (142, 106, 78),
}
STREET_OBJECT_BASE_DIMENSIONS: Dict[str, Tuple[float, float, float]] = {
    "car": (0.92, 0.46, 0.44),
    "taxi": (0.92, 0.46, 0.46),
    "van": (1.06, 0.54, 0.58),
    "bus": (1.34, 0.56, 0.68),
    "delivery_truck": (1.22, 0.58, 0.66),
    "pickup_truck": (1.06, 0.50, 0.50),
    "scooter": (0.62, 0.24, 0.40),
    "motorcycle": (0.86, 0.32, 0.56),
    "pedestrian": (0.54, 0.42, 1.16),
    "bicycle": (0.78, 0.22, 0.48),
    "traffic_cone": (0.30, 0.30, 0.50),
    "fire_hydrant": (0.36, 0.36, 0.58),
    "trash_bin": (0.46, 0.46, 0.62),
    "mailbox": (0.64, 0.40, 0.74),
    "construction_barrier": (0.84, 0.22, 0.58),
    "road_barrel": (0.38, 0.38, 0.66),
    "building": (1.06, 1.02, 1.28),
    "tree": (0.46, 0.46, 1.02),
    "shrub": (0.58, 0.58, 0.34),
    "traffic_light": (0.18, 0.18, 1.32),
    "street_sign": (0.18, 0.18, 1.04),
    "bench": (0.86, 0.30, 0.42),
}
STREET_RADIAL_OBJECT_TYPES = {"pedestrian", "traffic_cone", "fire_hydrant", "trash_bin", "road_barrel", "shrub"}
BUILDING_STYLES: Tuple[str, ...] = (
    "office_glass",
    "apartment_brick",
    "glass_tower",
    "retail_corner",
    "cafe_shop",
    "market_shop",
    "bookstore_shop",
    "concrete_midrise",
    "stucco_walkup",
)
BUILDING_STYLE_POOLS: Dict[str, Tuple[str, ...]] = {
    "downtown_intersection": (
        "office_glass",
        "glass_tower",
        "apartment_brick",
        "concrete_midrise",
        "retail_corner",
        "cafe_shop",
        "market_shop",
    ),
    "neighborhood_intersection": (
        "apartment_brick",
        "cafe_shop",
        "market_shop",
        "bookstore_shop",
        "stucco_walkup",
        "retail_corner",
        "concrete_midrise",
        "office_glass",
    ),
    "transit_intersection": (
        "office_glass",
        "concrete_midrise",
        "retail_corner",
        "cafe_shop",
        "market_shop",
        "apartment_brick",
        "glass_tower",
    ),
}
BUILDING_STYLE_DISPLAY_NAMES: Dict[str, str] = {
    "office_glass": "glass office building",
    "apartment_brick": "brick apartment building",
    "glass_tower": "glass tower",
    "retail_corner": "corner shop building",
    "cafe_shop": "cafe storefront",
    "market_shop": "market storefront",
    "bookstore_shop": "bookstore storefront",
    "concrete_midrise": "concrete midrise building",
    "stucco_walkup": "stucco walkup building",
}
BUILDING_STYLE_BASE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "office_glass": (108, 145, 166),
    "apartment_brick": (158, 94, 76),
    "glass_tower": (92, 139, 184),
    "retail_corner": (184, 150, 106),
    "cafe_shop": (185, 130, 103),
    "market_shop": (158, 166, 107),
    "bookstore_shop": (128, 120, 158),
    "concrete_midrise": (142, 149, 154),
    "stucco_walkup": (190, 168, 137),
}
BUILDING_STYLE_DIMENSION_FACTORS: Dict[str, Tuple[float, float, float]] = {
    "office_glass": (1.10, 0.96, 1.06),
    "apartment_brick": (1.02, 1.06, 1.02),
    "glass_tower": (0.84, 0.88, 1.24),
    "retail_corner": (1.28, 1.08, 0.72),
    "cafe_shop": (1.52, 1.10, 0.66),
    "market_shop": (1.64, 1.14, 0.72),
    "bookstore_shop": (1.42, 1.08, 0.70),
    "concrete_midrise": (1.08, 0.98, 0.94),
    "stucco_walkup": (1.04, 1.02, 0.86),
}


WAREHOUSE_OBJECT_TYPES: Tuple[str, ...] = (
    "crate_stack",
    "pallet_load",
    "barrel",
    "traffic_cone",
    "floor_sign",
    "tool_cart",
    "pallet_jack",
    "forklift",
    "box_stack",
    "tire_stack",
    "safety_barrier",
    "storage_bin",
    "ladder",
    "workbench",
    "rolling_bin",
    "trash_can",
    "warning_bollard",
    "wrapped_bundle",
    "fire_extinguisher",
    "hand_truck",
    "stacked_pipes",
)
WAREHOUSE_CONTEXT_OBJECT_TYPES: Tuple[str, ...] = (
    "shelf_rack",
    "charging_dock",
    "conveyor",
    "pallet",
    "crate_stack",
    "barrel",
    "storage_bin",
    "safety_barrier",
    "tool_cart",
    "traffic_cone",
    "workbench",
    "rolling_bin",
    "trash_can",
    "warning_bollard",
    "wrapped_bundle",
    "fire_extinguisher",
    "hand_truck",
    "stacked_pipes",
)
WAREHOUSE_OBJECT_NAMES: Dict[str, str] = {
    "warehouse_robot": "robot",
    "shelf_rack": "shelf rack",
    "crate_stack": "crate stack",
    "pallet_load": "loaded pallet",
    "barrel": "barrel",
    "traffic_cone": "traffic cone",
    "floor_sign": "floor sign",
    "tool_cart": "tool cart",
    "pallet_jack": "pallet jack",
    "forklift": "forklift",
    "box_stack": "box stack",
    "tire_stack": "tire stack",
    "safety_barrier": "safety barrier",
    "storage_bin": "storage bin",
    "ladder": "ladder",
    "charging_dock": "charging dock",
    "conveyor": "conveyor",
    "pallet": "pallet",
    "workbench": "workbench",
    "rolling_bin": "rolling bin",
    "trash_can": "trash can",
    "warning_bollard": "warning bollard",
    "wrapped_bundle": "wrapped bundle",
    "fire_extinguisher": "fire extinguisher",
    "hand_truck": "hand truck",
    "stacked_pipes": "stacked pipes",
}
WAREHOUSE_OBJECT_COLORS: Dict[str, Tuple[int, int, int]] = {
    "warehouse_robot": (72, 111, 182),
    "shelf_rack": (124, 130, 140),
    "crate_stack": (178, 111, 62),
    "pallet_load": (191, 137, 74),
    "barrel": (63, 126, 171),
    "traffic_cone": (224, 113, 40),
    "floor_sign": (230, 188, 62),
    "tool_cart": (77, 148, 129),
    "pallet_jack": (196, 76, 64),
    "forklift": (225, 169, 52),
    "box_stack": (192, 154, 93),
    "tire_stack": (55, 61, 68),
    "safety_barrier": (222, 124, 48),
    "storage_bin": (83, 142, 91),
    "ladder": (115, 128, 142),
    "charging_dock": (80, 92, 105),
    "conveyor": (99, 112, 128),
    "pallet": (151, 109, 70),
    "workbench": (96, 112, 118),
    "rolling_bin": (68, 137, 152),
    "trash_can": (83, 101, 96),
    "warning_bollard": (222, 184, 54),
    "wrapped_bundle": (187, 174, 149),
    "fire_extinguisher": (204, 48, 43),
    "hand_truck": (64, 92, 132),
    "stacked_pipes": (119, 131, 142),
}
WAREHOUSE_OBJECT_BASE_DIMENSIONS: Dict[str, Tuple[float, float, float]] = {
    "warehouse_robot": (0.74, 0.60, 0.62),
    "shelf_rack": (2.78, 0.42, 1.56),
    "crate_stack": (0.72, 0.62, 0.74),
    "pallet_load": (0.90, 0.68, 0.72),
    "barrel": (0.40, 0.40, 1.30),
    "traffic_cone": (0.34, 0.34, 0.54),
    "floor_sign": (0.54, 0.28, 0.50),
    "tool_cart": (0.76, 0.46, 0.64),
    "pallet_jack": (0.98, 0.42, 0.34),
    "forklift": (1.08, 0.62, 0.86),
    "box_stack": (0.82, 0.62, 0.70),
    "tire_stack": (0.56, 0.56, 0.56),
    "safety_barrier": (0.96, 0.22, 0.58),
    "storage_bin": (0.62, 0.58, 0.64),
    "ladder": (0.34, 0.88, 0.52),
    "charging_dock": (0.82, 0.32, 0.46),
    "conveyor": (1.46, 0.52, 0.48),
    "pallet": (0.88, 0.64, 0.20),
    "workbench": (1.06, 0.58, 0.68),
    "rolling_bin": (0.66, 0.58, 0.66),
    "trash_can": (0.42, 0.42, 0.62),
    "warning_bollard": (0.28, 0.28, 0.72),
    "wrapped_bundle": (0.88, 0.62, 0.58),
    "fire_extinguisher": (0.24, 0.24, 0.62),
    "hand_truck": (0.50, 0.76, 0.82),
    "stacked_pipes": (0.94, 0.42, 0.42),
}
WAREHOUSE_RADIAL_OBJECT_TYPES = {
    "barrel",
    "traffic_cone",
    "tire_stack",
    "storage_bin",
    "trash_can",
    "warning_bollard",
    "fire_extinguisher",
}
WAREHOUSE_NEAREST_REFERENCE_OBJECT_TYPE = "red_sphere"
WAREHOUSE_NEAREST_REFERENCE_OBJECT_NAME = "red sphere"
WAREHOUSE_NEAREST_REFERENCE_OBJECT_RGB: Tuple[int, int, int] = (214, 50, 50)
WAREHOUSE_NEAREST_REFERENCE_OBJECT_DIMENSIONS: Tuple[float, float, float] = (0.52, 0.52, 0.52)
WAREHOUSE_NEAREST_OBJECT_CANDIDATE_TYPES: Tuple[str, ...] = tuple(
    object_type
    for object_type in WAREHOUSE_OBJECT_TYPES
    if object_type not in {"floor_sign", "ladder", "warning_bollard", "fire_extinguisher"}
)
WAREHOUSE_ROBOT_HEADINGS: Tuple[str, ...] = ("east", "north", "west", "south")
WAREHOUSE_ROBOT_DESIGNS: Tuple[str, ...] = ("low_cart", "sensor_tower", "stacker_bot")
WAREHOUSE_SHELF_RACK_STYLES: Tuple[str, ...] = ("open_frame", "loaded_bins", "mixed_crates", "tall_sparse", "heavy_low")
WAREHOUSE_ROBOT_BASE_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (55, 112, 190),
    (62, 145, 132),
    (205, 128, 48),
    (101, 98, 171),
    (74, 91, 112),
    (182, 74, 66),
)
WAREHOUSE_ROBOT_ACCENT_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (235, 190, 55),
    (236, 236, 228),
    (52, 58, 70),
    (232, 104, 59),
    (79, 184, 219),
)
WAREHOUSE_SHELF_FRAME_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (86, 96, 110),
    (45, 101, 148),
    (72, 118, 100),
    (168, 105, 55),
    (126, 87, 148),
    (92, 99, 88),
    (182, 146, 57),
)
WAREHOUSE_SHELF_LOAD_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (82, 133, 146),
    (172, 107, 58),
    (93, 140, 91),
    (188, 154, 86),
    (83, 92, 111),
    (178, 73, 60),
)


def _make_profile(
    *,
    source_scene: str,
    role: str,
    object_type: str,
    display_name: str,
    size_class: str,
    renderer: str,
    resource_kind: str = "standalone",
    support_required: bool = False,
    base_object_type: str | None = None,
    support_profile_id: str | None = None,
    mounting: str | None = None,
    dimensions_xyz: Sequence[float] | None = None,
) -> ThreeDObjectProfile:
    return ThreeDObjectProfile(
        profile_id=f"{source_scene}:{role}:{object_type}",
        canonical_id=_canonical_id(display_name),
        source_scene=str(source_scene),
        role=str(role),
        object_type=str(object_type),
        display_name=str(display_name),
        size_class=str(size_class),
        renderer=str(renderer),
        resource_kind=str(resource_kind),
        support_required=bool(support_required),
        base_object_type=str(base_object_type) if base_object_type is not None else None,
        support_profile_id=str(support_profile_id) if support_profile_id is not None else None,
        mounting=str(mounting) if mounting is not None else None,
        dimensions_xyz=tuple(float(value) for value in dimensions_xyz) if dimensions_xyz is not None else None,
    )


def _build_profiles() -> Tuple[ThreeDObjectProfile, ...]:
    profiles = []
    for object_type in OBJECT_SCENE_SMALL_SHAPE_TYPES:
        profiles.append(
            _make_profile(
                source_scene=OBJECT_SCENE_ID,
                role="spatial_small_shape",
                object_type=object_type,
                display_name=OBJECT_SCENE_NAME_BY_SHAPE_TYPE[object_type],
                size_class="small",
                renderer="object_scene_shape",
                resource_kind="standalone",
                dimensions_xyz=OBJECT_SCENE_SMALL_DIMENSIONS[object_type],
            )
        )
    for object_type in OBJECT_SCENE_CONTEXT_SHAPE_TYPES:
        profiles.append(
            _make_profile(
                source_scene=OBJECT_SCENE_ID,
                role="spatial_context_shape",
                object_type=object_type,
                display_name=OBJECT_SCENE_NAME_BY_SHAPE_TYPE[object_type],
                size_class="large",
                renderer="object_scene_shape",
                resource_kind="standalone",
                dimensions_xyz=OBJECT_SCENE_CONTEXT_DIMENSIONS[object_type],
            )
        )
    for object_type in (*ROOM_QUERY_TARGET_TYPES, *ROOM_EXTRA_WALL_TYPES):
        profiles.append(
            _make_profile(
                source_scene=ROOM_SCENE_ID,
                role="room_wall_object",
                object_type=object_type,
                display_name=ROOM_OBJECT_PROMPT_NAMES[object_type][0],
                size_class="small",
                renderer="room_wall_object",
                resource_kind="mounted",
                support_required=True,
                base_object_type=object_type,
                mounting="wall_mounted",
                dimensions_xyz=ROOM_WALL_BASE_DIMENSIONS[object_type],
            )
        )
    for object_type, spec in ROOM_SURFACE_DISTRACTOR_SPECS.items():
        profiles.append(
            _make_profile(
                source_scene=ROOM_SCENE_ID,
                role="room_surface_variant",
                object_type=object_type,
                display_name=str(spec["prompt_name"]),
                size_class="small",
                renderer="room_floor_object",
                resource_kind="composite",
                support_required=True,
                base_object_type=object_type,
                mounting="on_furniture",
                dimensions_xyz=spec["dimensions_xyz"],
            )
        )
    for prop_shape in ROOM_FLOOR_PROP_SHAPES:
        spec = ROOM_FLOOR_PROP_SPECS[prop_shape]
        profiles.append(
            _make_profile(
                source_scene=ROOM_SCENE_ID,
                role="room_floor_prop",
                object_type=prop_shape,
                display_name=str(spec["prompt_name"]),
                size_class="large",
                renderer="room_floor_object",
                resource_kind="standalone",
                mounting="floor",
                dimensions_xyz=spec["dimensions_xyz"],
            )
        )
    for object_type in ROOM_FLOOR_DISTRACTOR_TYPES:
        spec = ROOM_FLOOR_DISTRACTOR_SPECS[object_type]
        profiles.append(
            _make_profile(
                source_scene=ROOM_SCENE_ID,
                role="room_floor_variant",
                object_type=object_type,
                display_name=str(spec["prompt_name"]),
                size_class="large",
                renderer="room_floor_object",
                resource_kind="variant",
                base_object_type=object_type,
                mounting="floor",
                dimensions_xyz=spec["dimensions_xyz"],
            )
        )
    for object_type in STREET_OBJECT_TYPES:
        profiles.append(
            _make_profile(
                source_scene=STREET_SCENE_ID,
                role="street_candidate",
                object_type=object_type,
                display_name=STREET_OBJECT_NAMES[object_type],
                size_class="large" if object_type in STREET_VEHICLE_OBJECT_TYPES else "small",
                renderer="street_object",
                resource_kind="standalone",
                mounting="ground",
                dimensions_xyz=STREET_OBJECT_BASE_DIMENSIONS[object_type],
            )
        )
    for object_type in STREET_CONTEXT_OBJECT_TYPES:
        profiles.append(
            _make_profile(
                source_scene=STREET_SCENE_ID,
                role="street_context",
                object_type=object_type,
                display_name=STREET_OBJECT_NAMES[object_type],
                size_class="large",
                renderer="street_object",
                resource_kind="standalone",
                mounting="ground",
                dimensions_xyz=STREET_OBJECT_BASE_DIMENSIONS[object_type],
            )
        )
    warehouse_seen = []
    for object_type in ("warehouse_robot", *WAREHOUSE_OBJECT_TYPES, *WAREHOUSE_CONTEXT_OBJECT_TYPES):
        if object_type not in warehouse_seen:
            warehouse_seen.append(object_type)
    warehouse_large = {
        "warehouse_robot",
        "shelf_rack",
        "crate_stack",
        "pallet_load",
        "forklift",
        "box_stack",
        "charging_dock",
        "conveyor",
        "pallet",
        "workbench",
        "wrapped_bundle",
    }
    for object_type in warehouse_seen:
        profiles.append(
            _make_profile(
                source_scene=WAREHOUSE_SCENE_ID,
                role="warehouse_object" if object_type in WAREHOUSE_OBJECT_TYPES or object_type == "warehouse_robot" else "warehouse_context",
                object_type=object_type,
                display_name=WAREHOUSE_OBJECT_NAMES[object_type],
                size_class="large" if object_type in warehouse_large else "small",
                renderer="warehouse_object",
                resource_kind="standalone",
                mounting="floor",
                dimensions_xyz=WAREHOUSE_OBJECT_BASE_DIMENSIONS[object_type],
            )
        )
    profiles.append(
        _make_profile(
            source_scene=WAREHOUSE_SCENE_ID,
            role="warehouse_reference",
            object_type=WAREHOUSE_NEAREST_REFERENCE_OBJECT_TYPE,
            display_name=WAREHOUSE_NEAREST_REFERENCE_OBJECT_NAME,
            size_class="small",
            renderer="warehouse_object",
            resource_kind="reference",
            mounting="floor",
            dimensions_xyz=WAREHOUSE_NEAREST_REFERENCE_OBJECT_DIMENSIONS,
        )
    )
    return tuple(profiles)


THREE_D_OBJECT_PROFILES: Tuple[ThreeDObjectProfile, ...] = _build_profiles()


def object_profiles(
    *,
    source_scene: str | None = None,
    role: str | None = None,
    size_class: str | None = None,
    resource_kind: str | None = None,
) -> Tuple[ThreeDObjectProfile, ...]:
    """Return canonical object profiles filtered by scene role."""

    profiles = THREE_D_OBJECT_PROFILES
    if source_scene is not None:
        profiles = tuple(profile for profile in profiles if profile.source_scene == str(source_scene))
    if role is not None:
        profiles = tuple(profile for profile in profiles if profile.role == str(role))
    if size_class is not None:
        profiles = tuple(profile for profile in profiles if profile.size_class == str(size_class))
    if resource_kind is not None:
        profiles = tuple(profile for profile in profiles if profile.resource_kind == str(resource_kind))
    return tuple(profiles)


def profiles_by_canonical_id() -> Mapping[str, Tuple[ThreeDObjectProfile, ...]]:
    grouped: Dict[str, Tuple[ThreeDObjectProfile, ...]] = {}
    for profile in THREE_D_OBJECT_PROFILES:
        grouped[profile.canonical_id] = (*grouped.get(profile.canonical_id, ()), profile)
    return grouped
