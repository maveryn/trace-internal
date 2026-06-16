"""Scene-rule helpers for Minecraft-like block-world tasks."""

from __future__ import annotations

from typing import Sequence, Tuple

from .defaults import (
    HEIGHT_CONDITION_AT_LEAST,
    HEIGHT_CONDITION_EXACT,
    SAMPLE_KIND_HEIGHT_FILTER,
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


def _validate_route_cost_sample(sample: MinecraftSceneSample) -> None:
    """Validate a route-cost construction using one visible track."""

    track_cells = {(int(x), int(y)) for x, y in sample.track_cells}
    if len(track_cells) < 4:
        raise ValueError("route sample requires one visible track")
    block_by_id = {str(block.block_id): block for block in sample.blocks}
    annotation_ids = {str(entity_id) for entity_id in sample.annotation_entity_ids}
    if len(sample.annotation_entity_ids) != int(sample.answer):
        raise ValueError("route annotation count must match raised track-block cost")
    if annotation_ids != set(block_by_id):
        raise ValueError("route annotation must include every raised track block and no other blocks")
    for block in block_by_id.values():
        if (int(block.x), int(block.y)) not in track_cells:
            raise ValueError("raised route block must sit on the visible track")
        if str(block.kind) not in {"stone", "dirt"}:
            raise ValueError("raised route blocks must be stone or dirt")


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
    "stack_heights_by_coord",
    "stack_ids_matching_height",
    "stack_ids_with_top_kind",
    "top_block_by_coord",
    "validate_minecraft_sample",
]
