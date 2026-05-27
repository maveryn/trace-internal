"""Shared Minecraft-like block-world helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SUPPORTED_MINECRAFT_STYLE_VARIANTS: Tuple[str, ...] = (
    "grass",
    "desert",
    "snow",
    "cave",
    "mesa",
)
SUPPORTED_MINECRAFT_RESOURCE_KINDS: Tuple[str, ...] = (
    "diamond_ore",
    "gold_ore",
    "pumpkin",
)


@dataclass(frozen=True)
class MinecraftCell:
    """One visible terrain cell in the Minecraft-like block scene."""

    cell_id: str
    x: int
    y: int
    kind: str


@dataclass(frozen=True)
class MinecraftBlock:
    """One visible cube block in the Minecraft-like block scene."""

    block_id: str
    x: int
    y: int
    z: int
    kind: str


@dataclass(frozen=True)
class MinecraftRouteOverlay:
    """One visible route cue drawn over the block-world floor."""

    label: str
    cells: Tuple[Tuple[int, int], ...]
    rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class MinecraftSceneSample:
    """Generated Minecraft-like scene state."""

    grid_width: int
    grid_depth: int
    query_id: str
    style_variant: str
    answer: int
    terrain_cells: Tuple[MinecraftCell, ...]
    blocks: Tuple[MinecraftBlock, ...]
    player_cell: Tuple[int, int] | None
    target_cell: Tuple[int, int] | None
    river_width: int
    scaffold_cost: int
    ladder_present: bool
    evidence_entity_ids: Tuple[str, ...]
    construction_mode: str
    route_overlays: Tuple[MinecraftRouteOverlay, ...] = ()
    route_costs: Tuple[Tuple[str, int], ...] = ()
    selected_route_label: str = ""
    target_resource_kind: str = ""
    counted_resource_kind: str = ""
    ladder_columns: Tuple[Tuple[int, int, int], ...] = ()


def terrain_cell_entity_id(x: int, y: int) -> str:
    """Return a stable terrain-cell entity id."""

    return f"cell_{int(x):02d}_{int(y):02d}"


def water_cell_entity_id(x: int, y: int) -> str:
    """Return a stable water-cell entity id."""

    return f"water_{int(x):02d}_{int(y):02d}"


def ore_block_entity_id(index: int) -> str:
    """Return a stable visible ore/resource block id."""

    return f"ore_{int(index):02d}"


def tunnel_block_entity_id(index: int) -> str:
    """Return a stable tunnel-clearance block id."""

    return f"tunnel_block_{int(index):02d}"


def route_obstacle_entity_id(route_label: str, index: int) -> str:
    """Return a stable route-obstacle block id."""

    return f"route_{str(route_label).lower()}_obstacle_{int(index):02d}"


def route_resource_entity_id(route_label: str) -> str:
    """Return a stable route target-resource block id."""

    return f"route_{str(route_label).lower()}_resource"


def ladder_entity_id() -> str:
    """Return the stable ladder entity id."""

    return "ladder"


def player_entity_id() -> str:
    """Return the stable player marker entity id."""

    return "player_marker"


def resource_prompt_name(kind: str) -> str:
    """Return the prompt-facing resource name for one block kind."""

    names = {
        "diamond_ore": "diamond ore",
        "gold_ore": "gold ore",
        "pumpkin": "pumpkin",
    }
    return names.get(str(kind), str(kind).replace("_", " "))


def validate_minecraft_sample(sample: MinecraftSceneSample) -> None:
    """Validate generated answer and evidence for a Minecraft-like scene."""

    if int(sample.grid_width) < 4 or int(sample.grid_depth) < 4:
        raise ValueError("minecraft grid must be at least 4 x 4")
    if str(sample.style_variant) not in SUPPORTED_MINECRAFT_STYLE_VARIANTS:
        raise ValueError(f"unsupported minecraft style: {sample.style_variant}")
    known_ids = {str(cell.cell_id) for cell in sample.terrain_cells}
    known_ids |= {str(block.block_id) for block in sample.blocks}
    if bool(sample.ladder_present):
        known_ids.add(ladder_entity_id())
        for ladder_index, _column in enumerate(sample.ladder_columns):
            known_ids.add(ladder_entity_id() if int(ladder_index) == 0 else f"{ladder_entity_id()}_{int(ladder_index):02d}")
    if sample.player_cell is not None:
        known_ids.add(player_entity_id())
    if not set(sample.evidence_entity_ids) <= known_ids:
        raise ValueError("minecraft evidence references unknown entities")

    query_id = str(sample.query_id)
    if query_id == "ore_block_count":
        target_kind = str(sample.counted_resource_kind)
        counted_ids = {str(block.block_id) for block in sample.blocks if str(block.kind) == target_kind}
        if int(sample.answer) != len(counted_ids):
            raise ValueError("ore-count answer must equal counted resource blocks")
        if set(sample.evidence_entity_ids) != counted_ids:
            raise ValueError("ore-count evidence must be exactly the counted resource blocks")
    elif query_id == "tunnel_clearance_count":
        if int(sample.answer) != len(sample.evidence_entity_ids):
            raise ValueError("tunnel-clearance evidence count must equal answer")
        if not all(str(entity_id).startswith("tunnel_block_") for entity_id in sample.evidence_entity_ids):
            raise ValueError("tunnel-clearance evidence must include only tunnel-block witnesses")
    elif query_id == "resource_route_cost":
        route_costs = [(str(label), int(cost)) for label, cost in sample.route_costs]
        if not route_costs:
            raise ValueError("resource-route sample requires route costs")
        queried_label = str(sample.selected_route_label)
        route_cost_by_label = {label: int(cost) for label, cost in route_costs}
        if queried_label not in route_cost_by_label:
            raise ValueError("resource-route selected route label must be present in route costs")
        if int(sample.answer) != int(route_cost_by_label[queried_label]):
            raise ValueError("resource-route answer must equal selected route cost")
        if len(sample.evidence_entity_ids) != int(sample.answer):
            raise ValueError("resource-route evidence count must match selected route cost")
        route_prefix = f"route_{queried_label.lower()}_obstacle_"
        if not all(str(entity_id).startswith(route_prefix) for entity_id in sample.evidence_entity_ids):
            raise ValueError("resource-route evidence must include only selected-route obstacle witnesses")
    else:
        raise ValueError(f"unsupported minecraft query_id: {query_id}")


__all__ = [
    "SUPPORTED_MINECRAFT_RESOURCE_KINDS",
    "SUPPORTED_MINECRAFT_STYLE_VARIANTS",
    "MinecraftBlock",
    "MinecraftCell",
    "MinecraftRouteOverlay",
    "MinecraftSceneSample",
    "ladder_entity_id",
    "ore_block_entity_id",
    "player_entity_id",
    "resource_prompt_name",
    "route_obstacle_entity_id",
    "route_resource_entity_id",
    "terrain_cell_entity_id",
    "tunnel_block_entity_id",
    "validate_minecraft_sample",
    "water_cell_entity_id",
]
