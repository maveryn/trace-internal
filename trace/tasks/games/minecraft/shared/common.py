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
    "iron_ore",
    "diamond_ore",
    "gold_ore",
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
    mode: str
    style_variant: str
    answer: int
    terrain_cells: Tuple[MinecraftCell, ...]
    blocks: Tuple[MinecraftBlock, ...]
    player_cell: Tuple[int, int] | None
    target_cell: Tuple[int, int] | None
    river_width: int
    scaffold_cost: int
    ladder_present: bool
    annotation_entity_ids: Tuple[str, ...]
    construction_mode: str
    route_overlays: Tuple[MinecraftRouteOverlay, ...] = ()
    route_costs: Tuple[Tuple[str, int], ...] = ()
    selected_route_label: str = ""
    target_resource_kind: str = ""
    counted_resource_kind: str = ""
    ladder_columns: Tuple[Tuple[int, int, int], ...] = ()
    target_stack_height: int = 0
    stack_height_condition: str = ""
    stack_line_cells: Tuple[Tuple[int, int], ...] = ()
    reachable_prefix_length: int = 0


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


def stack_entity_id(x: int, y: int) -> str:
    """Return a stable visible cube-stack entity id."""

    return f"stack_{int(x):02d}_{int(y):02d}"


def ladder_entity_id() -> str:
    """Return the stable ladder entity id."""

    return "ladder"


def player_entity_id() -> str:
    """Return the stable player marker entity id."""

    return "player_marker"


def resource_prompt_name(kind: str) -> str:
    """Return the prompt-facing resource name for one block kind."""

    names = {
        "iron_ore": "iron ore",
        "diamond_ore": "diamond ore",
        "gold_ore": "gold ore",
    }
    return names.get(str(kind), str(kind).replace("_", " "))


def validate_minecraft_sample(sample: MinecraftSceneSample) -> None:
    """Validate generated answer and annotation for a Minecraft-like scene."""

    if int(sample.grid_width) < 4 or int(sample.grid_depth) < 4:
        raise ValueError("minecraft grid must be at least 4 x 4")
    if str(sample.style_variant) not in SUPPORTED_MINECRAFT_STYLE_VARIANTS:
        raise ValueError(f"unsupported minecraft style: {sample.style_variant}")
    known_ids = {str(cell.cell_id) for cell in sample.terrain_cells}
    known_ids |= {str(block.block_id) for block in sample.blocks}
    known_ids |= {stack_entity_id(int(block.x), int(block.y)) for block in sample.blocks}
    if bool(sample.ladder_present):
        known_ids.add(ladder_entity_id())
        for ladder_index, _column in enumerate(sample.ladder_columns):
            known_ids.add(ladder_entity_id() if int(ladder_index) == 0 else f"{ladder_entity_id()}_{int(ladder_index):02d}")
    if sample.player_cell is not None:
        known_ids.add(player_entity_id())
    if not set(sample.annotation_entity_ids) <= known_ids:
        raise ValueError("minecraft annotation references unknown entities")

    mode = str(sample.mode)
    if mode == "top_ore_stack_count":
        target_kind = str(sample.counted_resource_kind)
        z_values_by_coord: dict[Tuple[int, int], set[int]] = {}
        top_by_coord: dict[Tuple[int, int], Tuple[int, str]] = {}
        for block in sample.blocks:
            coord = (int(block.x), int(block.y))
            z = int(block.z)
            z_values_by_coord.setdefault(coord, set()).add(z)
            if coord not in top_by_coord or z > int(top_by_coord[coord][0]):
                top_by_coord[coord] = (z, str(block.kind))
        for coord, z_values in z_values_by_coord.items():
            expected = set(range(max(z_values) + 1))
            if z_values != expected:
                raise ValueError(f"top-ore stack at {coord} must use contiguous z levels")
        counted_ids = {
            stack_entity_id(int(x), int(y))
            for (x, y), (_z, kind) in top_by_coord.items()
            if str(kind) == target_kind
        }
        if int(sample.answer) != len(counted_ids):
            raise ValueError("top-ore answer must equal stacks with matching top ore")
        if set(sample.annotation_entity_ids) != counted_ids:
            raise ValueError("top-ore annotation must be exactly the counted stack witnesses")
    elif mode == "reachable_ore_stack_count":
        target_kind = str(sample.counted_resource_kind)
        line_cells = tuple((int(x), int(y)) for x, y in sample.stack_line_cells)
        if not (6 <= len(line_cells) <= 10):
            raise ValueError("reachable-ore line length must be 6..10")
        row_y = int(line_cells[0][1])
        for index, (x, y) in enumerate(line_cells):
            if int(y) != row_y:
                raise ValueError("reachable-ore line must stay in one row")
            if index and int(x) != int(line_cells[index - 1][0]) + 1:
                raise ValueError("reachable-ore line cells must be consecutive left-to-right cells")

        z_values_by_coord: dict[Tuple[int, int], set[int]] = {}
        top_by_coord: dict[Tuple[int, int], Tuple[int, str]] = {}
        for block in sample.blocks:
            coord = (int(block.x), int(block.y))
            z = int(block.z)
            z_values_by_coord.setdefault(coord, set()).add(z)
            if coord not in top_by_coord or z > int(top_by_coord[coord][0]):
                top_by_coord[coord] = (z, str(block.kind))
        for coord in line_cells:
            if coord not in z_values_by_coord:
                raise ValueError(f"reachable-ore line cell {coord} has no stack")
        for coord, z_values in z_values_by_coord.items():
            expected = set(range(max(z_values) + 1))
            if z_values != expected:
                raise ValueError(f"reachable-ore stack at {coord} must use contiguous z levels")

        heights = [len(z_values_by_coord[coord]) for coord in line_cells]
        for previous_height, next_height in zip(heights, heights[1:]):
            if int(next_height) < int(previous_height):
                raise ValueError("reachable-ore stack heights must be nondecreasing left to right")
        reachable_prefix_length = 1
        for previous_height, next_height in zip(heights, heights[1:]):
            if int(next_height) <= int(previous_height) + 1:
                reachable_prefix_length += 1
            else:
                break
        if reachable_prefix_length >= len(line_cells):
            raise ValueError("reachable-ore sample must include an unreachable suffix")
        if int(sample.reachable_prefix_length) != int(reachable_prefix_length):
            raise ValueError("reachable-ore prefix length does not match stack heights")

        reachable_coords = set(line_cells[:reachable_prefix_length])
        counted_ids = {
            stack_entity_id(int(x), int(y))
            for x, y in reachable_coords
            if str(top_by_coord[(int(x), int(y))][1]) == target_kind
        }
        unreachable_target_ids = {
            stack_entity_id(int(x), int(y))
            for x, y in line_cells[reachable_prefix_length:]
            if str(top_by_coord[(int(x), int(y))][1]) == target_kind
        }
        if not unreachable_target_ids:
            raise ValueError("reachable-ore sample must include a target ore stack after the blocker")
        if int(sample.answer) != len(counted_ids):
            raise ValueError("reachable-ore answer must equal reachable target-ore stack count")
        if set(sample.annotation_entity_ids) != counted_ids:
            raise ValueError("reachable-ore annotation must be exactly the reachable target-ore stack witnesses")
    elif mode == "resource_route_cost":
        route_costs = [(str(label), int(cost)) for label, cost in sample.route_costs]
        if not route_costs:
            raise ValueError("resource-route sample requires route costs")
        queried_label = str(sample.selected_route_label)
        route_cost_by_label = {label: int(cost) for label, cost in route_costs}
        if queried_label not in route_cost_by_label:
            raise ValueError("resource-route selected route label must be present in route costs")
        if int(sample.answer) != int(route_cost_by_label[queried_label]):
            raise ValueError("resource-route answer must equal selected route cost")
        if len(sample.annotation_entity_ids) != int(sample.answer):
            raise ValueError("resource-route annotation count must match selected route cost")
        route_prefix = f"route_{queried_label.lower()}_obstacle_"
        if not all(str(entity_id).startswith(route_prefix) for entity_id in sample.annotation_entity_ids):
            raise ValueError("resource-route annotation must include only selected-route obstacle witnesses")
    elif mode in {"exact_height_count", "at_least_height_count"}:
        target_height = int(sample.target_stack_height)
        if target_height <= 0:
            raise ValueError("stack-height sample requires target_stack_height")
        heights: dict[Tuple[int, int], set[int]] = {}
        for block in sample.blocks:
            heights.setdefault((int(block.x), int(block.y)), set()).add(int(block.z))
        for coord, z_values in heights.items():
            expected = set(range(max(z_values) + 1))
            if z_values != expected:
                raise ValueError(f"stack at {coord} must use contiguous z levels")
        if mode == "exact_height_count":
            counted_coords = {coord for coord, z_values in heights.items() if len(z_values) == target_height}
        else:
            counted_coords = {coord for coord, z_values in heights.items() if len(z_values) >= target_height}
        counted_ids = {stack_entity_id(int(x), int(y)) for x, y in counted_coords}
        if int(sample.answer) != len(counted_ids):
            raise ValueError("stack-height answer must equal qualifying stack count")
        if set(sample.annotation_entity_ids) != counted_ids:
            raise ValueError("stack-height annotation must be exactly the qualifying stack witnesses")
    else:
        raise ValueError(f"unsupported minecraft mode: {mode}")


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
    "stack_entity_id",
    "terrain_cell_entity_id",
    "tunnel_block_entity_id",
    "validate_minecraft_sample",
    "water_cell_entity_id",
]
