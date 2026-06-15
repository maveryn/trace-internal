"""Scene-rule helpers for Minecraft-like block-world tasks."""

from __future__ import annotations

from typing import Sequence, Tuple

from .defaults import (
    HEIGHT_CONDITION_AT_LEAST,
    HEIGHT_CONDITION_EXACT,
    SAMPLE_KIND_HEIGHT_FILTER,
    SAMPLE_KIND_REACHABLE_RESOURCE,
    SAMPLE_KIND_ROUTE_COST,
    SAMPLE_KIND_TOP_RESOURCE,
    STYLE_VARIANTS,
)
from .state import (
    MinecraftBlock,
    MinecraftSceneSample,
    ladder_entity_id,
    player_entity_id,
    stack_entity_id,
)


def stack_heights_by_coord(blocks: Sequence[MinecraftBlock]) -> dict[Tuple[int, int], set[int]]:
    """Group visible z levels by horizontal stack coordinate."""

    heights: dict[Tuple[int, int], set[int]] = {}
    for block in blocks:
        heights.setdefault((int(block.x), int(block.y)), set()).add(int(block.z))
    return heights


def top_block_by_coord(blocks: Sequence[MinecraftBlock]) -> dict[Tuple[int, int], Tuple[int, str]]:
    """Return the top z level and block kind for every visible stack."""

    top_by_coord: dict[Tuple[int, int], Tuple[int, str]] = {}
    for block in blocks:
        coord = (int(block.x), int(block.y))
        z = int(block.z)
        if coord not in top_by_coord or z > int(top_by_coord[coord][0]):
            top_by_coord[coord] = (z, str(block.kind))
    return top_by_coord


def require_contiguous_stack_levels(blocks: Sequence[MinecraftBlock]) -> None:
    """Validate that every stack contains all z levels from ground to top."""

    for coord, z_values in stack_heights_by_coord(blocks).items():
        expected = set(range(max(z_values) + 1))
        if z_values != expected:
            raise ValueError(f"block stack at {coord} must use contiguous z levels")


def reachable_prefix_length_for_heights(heights: Sequence[int]) -> int:
    """Return how far a left-to-right path can move under the one-cube climb rule."""

    prefix_length = 1
    for previous_height, next_height in zip(heights, heights[1:]):
        if int(next_height) <= int(previous_height) + 1:
            prefix_length += 1
        else:
            break
    return int(prefix_length)


def stack_ids_with_top_kind(blocks: Sequence[MinecraftBlock], target_kind: str) -> set[str]:
    """Return stack ids whose visible top cube has the requested resource kind."""

    return {
        stack_entity_id(int(x), int(y))
        for (x, y), (_z, kind) in top_block_by_coord(blocks).items()
        if str(kind) == str(target_kind)
    }


def stack_ids_matching_height(
    blocks: Sequence[MinecraftBlock],
    *,
    target_height: int,
    condition: str,
) -> set[str]:
    """Return stack ids satisfying one exact/at-least height predicate."""

    if str(condition) == HEIGHT_CONDITION_EXACT:
        return {
            stack_entity_id(int(x), int(y))
            for (x, y), z_values in stack_heights_by_coord(blocks).items()
            if len(z_values) == int(target_height)
        }
    if str(condition) == HEIGHT_CONDITION_AT_LEAST:
        return {
            stack_entity_id(int(x), int(y))
            for (x, y), z_values in stack_heights_by_coord(blocks).items()
            if len(z_values) >= int(target_height)
        }
    raise ValueError(f"unsupported stack height condition: {condition}")


def validate_minecraft_sample(sample: MinecraftSceneSample) -> None:
    """Validate generated answer and annotation against block-world semantics."""

    if int(sample.grid_width) < 4 or int(sample.grid_depth) < 4:
        raise ValueError("minecraft grid must be at least 4 x 4")
    if str(sample.style_variant) not in STYLE_VARIANTS:
        raise ValueError(f"unsupported minecraft style: {sample.style_variant}")

    known_ids = {str(cell.cell_id) for cell in sample.terrain_cells}
    known_ids |= {str(block.block_id) for block in sample.blocks}
    known_ids |= {stack_entity_id(int(block.x), int(block.y)) for block in sample.blocks}
    if bool(sample.ladder_present):
        known_ids.add(ladder_entity_id())
        for ladder_index, _column in enumerate(sample.ladder_columns):
            known_ids.add(
                ladder_entity_id()
                if int(ladder_index) == 0
                else f"{ladder_entity_id()}_{int(ladder_index):02d}"
            )
    if sample.player_cell is not None:
        known_ids.add(player_entity_id())
    if not set(sample.annotation_entity_ids) <= known_ids:
        raise ValueError("minecraft annotation references unknown entities")

    if str(sample.sample_kind) == SAMPLE_KIND_TOP_RESOURCE:
        _validate_top_resource_sample(sample)
    elif str(sample.sample_kind) == SAMPLE_KIND_REACHABLE_RESOURCE:
        _validate_reachable_resource_sample(sample)
    elif str(sample.sample_kind) == SAMPLE_KIND_ROUTE_COST:
        _validate_route_cost_sample(sample)
    elif str(sample.sample_kind) == SAMPLE_KIND_HEIGHT_FILTER:
        _validate_height_filter_sample(sample)
    else:
        raise ValueError(f"unsupported minecraft sample kind: {sample.sample_kind}")


def _validate_top_resource_sample(sample: MinecraftSceneSample) -> None:
    """Validate a top-resource stack count construction."""

    require_contiguous_stack_levels(sample.blocks)
    counted_ids = stack_ids_with_top_kind(sample.blocks, sample.counted_resource_kind)
    if int(sample.answer) != len(counted_ids):
        raise ValueError("top-resource answer must equal stacks with matching top resource")
    if set(sample.annotation_entity_ids) != counted_ids:
        raise ValueError("top-resource annotation must be exactly the counted stack witnesses")


def _validate_reachable_resource_sample(sample: MinecraftSceneSample) -> None:
    """Validate a left-to-right reachable resource stack construction."""

    target_kind = str(sample.counted_resource_kind)
    line_cells = tuple((int(x), int(y)) for x, y in sample.stack_line_cells)
    if not (6 <= len(line_cells) <= 10):
        raise ValueError("reachable-resource line length must be 6..10")
    row_y = int(line_cells[0][1])
    for index, (x, y) in enumerate(line_cells):
        if int(y) != row_y:
            raise ValueError("reachable-resource line must stay in one row")
        if index and int(x) != int(line_cells[index - 1][0]) + 1:
            raise ValueError("reachable-resource line cells must be consecutive left-to-right cells")

    require_contiguous_stack_levels(sample.blocks)
    heights_by_coord = stack_heights_by_coord(sample.blocks)
    top_by_coord = top_block_by_coord(sample.blocks)
    for coord in line_cells:
        if coord not in heights_by_coord:
            raise ValueError(f"reachable-resource line cell {coord} has no stack")

    heights = [len(heights_by_coord[coord]) for coord in line_cells]
    for previous_height, next_height in zip(heights, heights[1:]):
        if int(next_height) < int(previous_height):
            raise ValueError("reachable-resource stack heights must be nondecreasing left to right")
    reachable_prefix_length = reachable_prefix_length_for_heights(heights)
    if reachable_prefix_length >= len(line_cells):
        raise ValueError("reachable-resource sample must include an unreachable suffix")
    if int(sample.reachable_prefix_length) != int(reachable_prefix_length):
        raise ValueError("reachable-resource prefix length does not match stack heights")

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
        raise ValueError("reachable-resource sample must include a target stack after the blocker")
    if int(sample.answer) != len(counted_ids):
        raise ValueError("reachable-resource answer must equal reachable target stack count")
    if set(sample.annotation_entity_ids) != counted_ids:
        raise ValueError("reachable-resource annotation must be exactly the reachable target witnesses")


def _validate_route_cost_sample(sample: MinecraftSceneSample) -> None:
    """Validate a route-cost construction using selected raised blocks."""

    route_costs = [(str(label), int(cost)) for label, cost in sample.route_costs]
    if not route_costs:
        raise ValueError("route sample requires route costs")
    selected_label = str(sample.selected_route_label)
    route_cost_by_label = {label: int(cost) for label, cost in route_costs}
    if selected_label not in route_cost_by_label:
        raise ValueError("selected route label must be present in route costs")
    if int(sample.answer) != int(route_cost_by_label[selected_label]):
        raise ValueError("answer must equal selected route cost")
    if len(sample.annotation_entity_ids) != int(sample.answer):
        raise ValueError("route annotation count must match selected route cost")
    route_prefix = f"route_{selected_label.lower()}_obstacle_"
    if not all(str(entity_id).startswith(route_prefix) for entity_id in sample.annotation_entity_ids):
        raise ValueError("route annotation must include only selected-route obstacle witnesses")


def _validate_height_filter_sample(sample: MinecraftSceneSample) -> None:
    """Validate a stack-height filter construction."""

    target_height = int(sample.target_stack_height)
    if target_height <= 0:
        raise ValueError("height-filter sample requires target_stack_height")
    require_contiguous_stack_levels(sample.blocks)
    counted_ids = stack_ids_matching_height(
        sample.blocks,
        target_height=int(target_height),
        condition=str(sample.stack_height_condition),
    )
    if int(sample.answer) != len(counted_ids):
        raise ValueError("height-filter answer must equal qualifying stack count")
    if set(sample.annotation_entity_ids) != counted_ids:
        raise ValueError("height-filter annotation must be exactly the qualifying stack witnesses")


__all__ = [
    "reachable_prefix_length_for_heights",
    "stack_heights_by_coord",
    "stack_ids_matching_height",
    "stack_ids_with_top_kind",
    "top_block_by_coord",
    "validate_minecraft_sample",
]
