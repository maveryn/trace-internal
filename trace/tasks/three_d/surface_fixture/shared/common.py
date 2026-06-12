"""Shared constants for synthetic 3D surface-fixture scenes."""

from __future__ import annotations

from typing import Mapping, Tuple


SCENE_ID = "surface_fixture"

REPEATED_TASK_ID = "task_three_d__surface_fixture__repeated_element_count"
COLORED_TASK_ID = "task_three_d__surface_fixture__colored_element_count"
STATE_TASK_ID = "task_three_d__surface_fixture__state_element_count"
SCOPED_COLORED_TASK_ID = "task_three_d__surface_fixture__scoped_colored_element_count"
EMPTY_MISSING_TASK_ID = "task_three_d__surface_fixture__empty_or_missing_cell_count"
ADJACENT_TASK_ID = "task_three_d__surface_fixture__adjacent_to_reference_count"

SURFACE_FIXTURE_TASK_IDS: Tuple[str, ...] = (
    REPEATED_TASK_ID,
    COLORED_TASK_ID,
    STATE_TASK_ID,
    SCOPED_COLORED_TASK_ID,
    EMPTY_MISSING_TASK_ID,
    ADJACENT_TASK_ID,
)

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "wall_tile_panel",
    "perforated_panel",
    "slot_board",
    "compartment_tray",
    "vent_panel",
    "window_grid",
    "door_bank",
    "drawer_pull_panel",
    "brick_wall",
    "paver_floor",
    "locker_bank",
    "mailbox_bank",
    "server_rack",
    "control_panel",
    "solar_panel_array",
)

ELEMENT_TYPE_BY_SCENE_VARIANT: Mapping[str, str] = {
    "wall_tile_panel": "tile",
    "perforated_panel": "hole",
    "slot_board": "slot",
    "compartment_tray": "compartment",
    "vent_panel": "vent",
    "window_grid": "window",
    "door_bank": "door",
    "drawer_pull_panel": "drawer_pull",
    "brick_wall": "brick",
    "paver_floor": "paver",
    "locker_bank": "locker",
    "mailbox_bank": "mailbox",
    "server_rack": "drive_bay",
    "control_panel": "button",
    "solar_panel_array": "solar_panel",
}

SCENE_VARIANT_BY_ELEMENT_TYPE: Mapping[str, str] = {
    str(element_type): str(scene_variant)
    for scene_variant, element_type in ELEMENT_TYPE_BY_SCENE_VARIANT.items()
}

SURFACE_FIXTURE_DISPLAY_NAME: Mapping[str, str] = {
    "wall_tile_panel": "tiled wall panel",
    "perforated_panel": "perforated metal panel",
    "slot_board": "slotted board",
    "compartment_tray": "compartment tray",
    "vent_panel": "vent panel",
    "window_grid": "window grid",
    "door_bank": "bank of small doors",
    "drawer_pull_panel": "drawer front panel",
    "brick_wall": "brick wall",
    "paver_floor": "paver floor",
    "locker_bank": "locker bank",
    "mailbox_bank": "mailbox bank",
    "server_rack": "server rack",
    "control_panel": "control panel",
    "solar_panel_array": "solar panel array",
}

ELEMENT_DISPLAY_NAME: Mapping[str, str] = {
    "tile": "tile",
    "hole": "hole",
    "slot": "slot",
    "compartment": "compartment",
    "vent": "vent",
    "window": "window",
    "door": "door",
    "drawer_pull": "drawer pull",
    "brick": "brick",
    "paver": "paver",
    "locker": "locker",
    "mailbox": "mailbox",
    "drive_bay": "drive bay",
    "button": "button",
    "solar_panel": "solar panel",
}

ELEMENT_PLURAL: Mapping[str, str] = {
    "tile": "tiles",
    "hole": "holes",
    "slot": "slots",
    "compartment": "compartments",
    "vent": "vents",
    "window": "windows",
    "door": "doors",
    "drawer_pull": "drawer pulls",
    "brick": "bricks",
    "paver": "pavers",
    "locker": "lockers",
    "mailbox": "mailboxes",
    "drive_bay": "drive bays",
    "button": "buttons",
    "solar_panel": "solar panels",
}

SEMANTIC_COLOR_RGB: Mapping[str, Tuple[int, int, int]] = {
    "red": (196, 74, 62),
    "blue": (65, 121, 185),
    "green": (74, 144, 93),
    "yellow": (221, 177, 73),
    "purple": (129, 94, 169),
    "orange": (210, 126, 58),
    "gray": (142, 151, 156),
}

SEMANTIC_COLOR_SUPPORT: Tuple[str, ...] = tuple(SEMANTIC_COLOR_RGB.keys())

STATE_SUPPORT_BY_SCENE_VARIANT: Mapping[str, Tuple[str, ...]] = {
    "locker_bank": ("open", "closed"),
    "mailbox_bank": ("open", "closed"),
    "server_rack": ("lit", "unlit"),
    "control_panel": ("lit", "unlit", "pressed"),
    "solar_panel_array": ("intact", "cracked"),
    "door_bank": ("open", "closed"),
    "window_grid": ("lit", "unlit"),
}

STATE_DISPLAY_NAME: Mapping[str, str] = {
    "open": "open",
    "closed": "closed",
    "lit": "lit",
    "unlit": "unlit",
    "pressed": "pressed",
    "intact": "intact",
    "cracked": "cracked",
}

COLORABLE_SCENE_VARIANTS: Tuple[str, ...] = (
    "wall_tile_panel",
    "compartment_tray",
    "vent_panel",
    "window_grid",
    "door_bank",
    "drawer_pull_panel",
    "brick_wall",
    "paver_floor",
    "locker_bank",
    "mailbox_bank",
    "server_rack",
    "control_panel",
    "solar_panel_array",
)

MISSING_SCENE_VARIANTS: Tuple[str, ...] = (
    "wall_tile_panel",
    "compartment_tray",
    "window_grid",
    "door_bank",
    "brick_wall",
    "paver_floor",
    "locker_bank",
    "mailbox_bank",
    "server_rack",
    "control_panel",
    "solar_panel_array",
)

ADJACENCY_SCENE_VARIANTS: Tuple[str, ...] = (
    "wall_tile_panel",
    "compartment_tray",
    "vent_panel",
    "window_grid",
    "door_bank",
    "brick_wall",
    "paver_floor",
    "locker_bank",
    "mailbox_bank",
    "server_rack",
    "control_panel",
    "solar_panel_array",
)

SURFACE_FIXTURE_OBJECT_TYPES: Tuple[str, ...] = SUPPORTED_SCENE_VARIANTS

