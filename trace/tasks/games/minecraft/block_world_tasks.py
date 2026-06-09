"""Games tasks over Minecraft-like voxel block worlds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_complexity, clamp_unit_interval, normalize_linear, resolve_games_complexity_weights
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.minecraft_common import (
    MinecraftBlock,
    MinecraftCell,
    MinecraftRouteOverlay,
    MinecraftSceneSample,
    SUPPORTED_MINECRAFT_RESOURCE_KINDS,
    SUPPORTED_MINECRAFT_STYLE_VARIANTS,
    resource_prompt_name,
    route_obstacle_entity_id,
    terrain_cell_entity_id,
    stack_entity_id,
    validate_minecraft_sample,
    water_cell_entity_id,
)
from ..shared.minecraft_scene import MinecraftRenderParams, render_minecraft_block_world_scene
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_GROUP = "minecraft"
SCENE_ID = "minecraft"
BASE_TASK_ID = "games_minecraft_block_world_base"

TOP_ORE_STACK_QUERY_ID = "top_ore_stack_count"
REACHABLE_ORE_STACK_QUERY_ID = "reachable_ore_stack_count"
RESOURCE_ROUTE_QUERY_ID = "resource_route_cost"
EXACT_HEIGHT_QUERY_ID = "exact_height_count"
AT_LEAST_HEIGHT_QUERY_ID = "at_least_height_count"
STACK_HEIGHT_QUERY_IDS: Tuple[str, ...] = (EXACT_HEIGHT_QUERY_ID, AT_LEAST_HEIGHT_QUERY_ID)
MINECRAFT_ORE_KINDS: Tuple[str, ...] = ("iron_ore", "gold_ore", "diamond_ore")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Minecraft-like block-world tasks."""

    grid_width_support: Tuple[int, ...] = (8, 9, 10)
    grid_depth_support: Tuple[int, ...] = (8, 9, 10)
    top_ore_stack_answer_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    reachable_ore_stack_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    reachable_line_length_support: Tuple[int, ...] = (6, 7, 8, 9, 10)
    reachable_grid_width_support: Tuple[int, ...] = (8, 9, 10, 11, 12)
    reachable_grid_depth_support: Tuple[int, ...] = (5,)
    route_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    stack_height_answer_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    exact_target_height_support: Tuple[int, ...] = (2, 3, 4, 5)
    at_least_target_height_support: Tuple[int, ...] = (2, 3, 4)
    stack_height_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    route_grid_width_support: Tuple[int, ...] = (11,)
    route_grid_depth_support: Tuple[int, ...] = (8, 9, 10)
    route_option_count_support: Tuple[int, ...] = (2, 3)
    canvas_width: int = 840
    canvas_height: int = 680
    tile_width_px: int = 58
    tile_height_px: int = 30
    cube_height_px: int = 30
    outline_width_px: int = 2
    player_marker_size_px: int = 28


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one block-world instance."""

    query_id: str
    style_variant: str
    grid_width: int
    grid_depth: int
    target_answer: int
    target_stack_height: int
    line_length: int
    route_option_count: int
    style_variant_probabilities: Dict[str, float]
    grid_width_probabilities: Dict[str, float]
    grid_depth_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    target_stack_height_probabilities: Dict[str, float]
    line_length_probabilities: Dict[str, float]
    route_option_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=BASE_TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def _answer_support_key(query_id: str) -> tuple[str, str, Tuple[int, ...]]:
    if str(query_id) == TOP_ORE_STACK_QUERY_ID:
        return ("top_ore_stack_answer_support", "target_answer", _DEFAULTS.top_ore_stack_answer_support)
    if str(query_id) == REACHABLE_ORE_STACK_QUERY_ID:
        return (
            "reachable_ore_stack_answer_support",
            "target_answer",
            _DEFAULTS.reachable_ore_stack_answer_support,
        )
    if str(query_id) == RESOURCE_ROUTE_QUERY_ID:
        return ("route_answer_support", "target_answer", _DEFAULTS.route_answer_support)
    if str(query_id) in STACK_HEIGHT_QUERY_IDS:
        return ("stack_height_answer_support", "target_answer", _DEFAULTS.stack_height_answer_support)
    raise ValueError(f"unsupported minecraft query_id: {query_id}")


def _grid_support_keys(query_id: str) -> tuple[str, str, Tuple[int, ...], Tuple[int, ...]]:
    if str(query_id) == REACHABLE_ORE_STACK_QUERY_ID:
        return (
            "reachable_grid_width_support",
            "reachable_grid_depth_support",
            _DEFAULTS.reachable_grid_width_support,
            _DEFAULTS.reachable_grid_depth_support,
        )
    if str(query_id) == RESOURCE_ROUTE_QUERY_ID:
        return (
            "route_grid_width_support",
            "route_grid_depth_support",
            _DEFAULTS.route_grid_width_support,
            _DEFAULTS.route_grid_depth_support,
        )
    return ("grid_width_support", "grid_depth_support", _DEFAULTS.grid_width_support, _DEFAULTS.grid_depth_support)


def _target_height_support_key(query_id: str) -> tuple[str, Tuple[int, ...]]:
    if str(query_id) == EXACT_HEIGHT_QUERY_ID:
        return ("exact_target_height_support", _DEFAULTS.exact_target_height_support)
    if str(query_id) == AT_LEAST_HEIGHT_QUERY_ID:
        return ("at_least_target_height_support", _DEFAULTS.at_least_target_height_support)
    return ("", (0,))


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any], query_id: str) -> _ResolvedAxes:
    """Resolve all axes for one Minecraft-like block-world instance."""

    style_variant, style_variant_probabilities = resolve_games_named_axis(
        task_id=BASE_TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported_variants=SUPPORTED_MINECRAFT_STYLE_VARIANTS,
    )
    if str(query_id) == REACHABLE_ORE_STACK_QUERY_ID:
        grid_width = 0
        grid_depth = 0
        grid_width_probabilities: Dict[str, float] = {}
        grid_depth_probabilities: Dict[str, float] = {}
    else:
        width_support_key, depth_support_key, width_fallback, depth_fallback = _grid_support_keys(str(query_id))
        grid_width, grid_width_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=width_support_key,
            explicit_key="grid_width",
            fallback_support=width_fallback,
            namespace=f"{BASE_TASK_ID}.grid_width",
            balanced_flag_key="balanced_grid_width_sampling",
            namespace_support_permutation=True,
        )
        grid_depth, grid_depth_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=depth_support_key,
            explicit_key="grid_depth",
            fallback_support=depth_fallback,
            namespace=f"{BASE_TASK_ID}.grid_depth",
            balanced_flag_key="balanced_grid_depth_sampling",
            namespace_support_permutation=True,
        )
    support_key, explicit_key, fallback = _answer_support_key(str(query_id))
    target_answer, answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        explicit_key=explicit_key,
        fallback_support=fallback,
        namespace=f"{BASE_TASK_ID}.{str(query_id)}.answer",
        balanced_flag_key="balanced_answer_sampling",
        namespace_support_permutation=True,
    )
    if str(query_id) == RESOURCE_ROUTE_QUERY_ID:
        route_option_count, route_option_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="route_option_count_support",
            explicit_key="route_option_count",
            fallback_support=_DEFAULTS.route_option_count_support,
            namespace=f"{BASE_TASK_ID}.{str(query_id)}.route_option_count",
            balanced_flag_key="balanced_route_option_count_sampling",
            namespace_support_permutation=True,
        )
    else:
        route_option_count = 0
        route_option_count_probabilities = {"0": 1.0}
    if str(query_id) in STACK_HEIGHT_QUERY_IDS:
        height_support_key, height_fallback = _target_height_support_key(str(query_id))
        target_stack_height, target_stack_height_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=height_support_key,
            explicit_key="target_stack_height",
            fallback_support=height_fallback,
            namespace=f"{BASE_TASK_ID}.{str(query_id)}.target_stack_height",
            balanced_flag_key="balanced_target_stack_height_sampling",
            namespace_support_permutation=True,
        )
    else:
        target_stack_height = 0
        target_stack_height_probabilities = {"0": 1.0}
    if str(query_id) == REACHABLE_ORE_STACK_QUERY_ID:
        raw_line_length_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="reachable_line_length_support",
            fallback=_DEFAULTS.reachable_line_length_support,
        )
        min_line_length = max(6, int(target_answer) + 2)
        line_length_support = tuple(length for length in raw_line_length_support if int(length) >= int(min_line_length))
        if not line_length_support:
            raise ValueError("reachable_line_length_support cannot support the sampled target answer")
        line_params = dict(params)
        line_params["reachable_line_length_support"] = tuple(int(length) for length in line_length_support)
        line_length, line_length_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=line_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="reachable_line_length_support",
            explicit_key="line_length",
            fallback_support=line_length_support,
            namespace=f"{BASE_TASK_ID}.{str(query_id)}.line_length",
            balanced_flag_key="balanced_reachable_line_length_sampling",
            namespace_support_permutation=True,
        )
        grid_width = int(line_length)
        grid_depth = 4
        grid_width_probabilities = {str(int(grid_width)): 1.0}
        grid_depth_probabilities = {str(int(grid_depth)): 1.0}
    else:
        line_length = 0
        line_length_probabilities = {"0": 1.0}
    return _ResolvedAxes(
        query_id=str(query_id),
        style_variant=str(style_variant),
        grid_width=int(grid_width),
        grid_depth=int(grid_depth),
        target_answer=int(target_answer),
        target_stack_height=int(target_stack_height),
        line_length=int(line_length),
        route_option_count=int(route_option_count),
        style_variant_probabilities=dict(style_variant_probabilities),
        grid_width_probabilities=dict(grid_width_probabilities),
        grid_depth_probabilities=dict(grid_depth_probabilities),
        answer_probabilities=dict(answer_probabilities),
        target_stack_height_probabilities=dict(target_stack_height_probabilities),
        line_length_probabilities=dict(line_length_probabilities),
        route_option_count_probabilities=dict(route_option_count_probabilities),
    )


def _resolve_task_query_id(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> tuple[str, Dict[str, float]]:
    """Resolve the internal Minecraft query branch for a public task."""

    supported = tuple(str(query_id) for query_id in supported_query_ids)
    if not supported:
        raise ValueError(f"{task_id} must define at least one supported query_id")

    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in supported:
            raise ValueError(f"{task_id} does not support query_id={query_id!r}")
        return query_id, {query_id: 1.0}

    if len(supported) == 1:
        return supported[0], {supported[0]: 1.0}

    raw_cursor = params.get("_sample_cursor")
    if raw_cursor is not None:
        query_id = supported[abs(int(raw_cursor)) % len(supported)]
    else:
        rng = spawn_rng(int(instance_seed), f"{task_id}.query_id")
        query_id = str(rng.choice(supported))

    probability = 1.0 / float(len(supported))
    return str(query_id), {query_id: probability for query_id in supported}


def _render_params(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    grid_width: int,
    grid_depth: int,
    max_stack_height: int = 1,
    player_marker_label: str = "P",
) -> MinecraftRenderParams:
    """Resolve Minecraft-like rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.minecraft.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.minecraft.layout",
        ),
        unit_scale_meta,
    )
    tile_width = scale_games_px(params.get("tile_width_px", group_default(_RENDER_DEFAULTS, "tile_width_px", _DEFAULTS.tile_width_px)), unit_scale, min_px=29)
    tile_height = scale_games_px(params.get("tile_height_px", group_default(_RENDER_DEFAULTS, "tile_height_px", _DEFAULTS.tile_height_px)), unit_scale, min_px=15)
    cube_height = scale_games_px(params.get("cube_height_px", group_default(_RENDER_DEFAULTS, "cube_height_px", _DEFAULTS.cube_height_px)), unit_scale, min_px=15)
    default_canvas_width = int(group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))
    default_canvas_height = int(group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))
    world_width = float((int(grid_width) + int(grid_depth)) * int(tile_width) / 2.0)
    stack_height = max(1, int(max_stack_height))
    world_height = float((int(grid_width) + int(grid_depth)) * int(tile_height) / 2.0) + float(cube_height * stack_height)
    canvas_width = int(params.get("canvas_width", min(default_canvas_width, max(520, int(round(world_width + 190.0))))))
    canvas_height = int(params.get("canvas_height", min(default_canvas_height, max(430, int(round(world_height + 165.0))))))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.minecraft.font_family",
        params=params,
    )
    return MinecraftRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        tile_width_px=int(tile_width),
        tile_height_px=int(tile_height),
        cube_height_px=int(cube_height),
        outline_width_px=scale_games_px(params.get("outline_width_px", group_default(_RENDER_DEFAULTS, "outline_width_px", _DEFAULTS.outline_width_px)), unit_scale, min_px=1),
        player_marker_size_px=scale_games_px(params.get("player_marker_size_px", group_default(_RENDER_DEFAULTS, "player_marker_size_px", _DEFAULTS.player_marker_size_px)), unit_scale, min_px=14),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
        max_stack_height=int(stack_height),
        player_marker_label=str(player_marker_label or "P"),
    )


def _terrain_cells_from_kinds(
    *,
    grid_width: int,
    grid_depth: int,
    cell_kinds: Mapping[Tuple[int, int], str] | None = None,
) -> Tuple[MinecraftCell, ...]:
    kind_by_cell = {(int(x), int(y)): str(kind) for (x, y), kind in dict(cell_kinds or {}).items()}
    cells: list[MinecraftCell] = []
    for y in range(int(grid_depth)):
        for x in range(int(grid_width)):
            kind = str(kind_by_cell.get((int(x), int(y)), "ground"))
            if kind == "water":
                cells.append(MinecraftCell(cell_id=water_cell_entity_id(int(x), int(y)), x=int(x), y=int(y), kind="water"))
            else:
                cells.append(MinecraftCell(cell_id=terrain_cell_entity_id(int(x), int(y)), x=int(x), y=int(y), kind=kind))
    return tuple(cells)


def _resource_kind(*, rng, params: Mapping[str, Any], allowed_kinds: Sequence[str] | None = None) -> str:
    explicit = params.get("resource_kind", params.get("target_resource_kind"))
    supported = tuple(str(kind) for kind in (allowed_kinds or SUPPORTED_MINECRAFT_RESOURCE_KINDS))
    if explicit is not None:
        kind = str(explicit)
        if kind not in supported:
            raise ValueError(f"unsupported resource_kind: {kind}")
        return str(kind)
    return str(rng.choice(supported))


def _sample_distinct_cells(
    *,
    rng,
    grid_width: int,
    grid_depth: int,
    count: int,
    avoid: Sequence[Tuple[int, int]] = (),
    min_x: int = 1,
    max_x_exclusive: int | None = None,
    min_y: int = 1,
    max_y_exclusive: int | None = None,
) -> Tuple[Tuple[int, int], ...]:
    """Sample distinct interior grid cells."""

    avoid_set = {(int(x), int(y)) for x, y in avoid}
    max_x = int(max_x_exclusive) if max_x_exclusive is not None else int(grid_width) - 1
    max_y = int(max_y_exclusive) if max_y_exclusive is not None else int(grid_depth) - 1
    candidates = [
        (int(x), int(y))
        for y in range(int(min_y), int(max_y))
        for x in range(int(min_x), int(max_x))
        if (int(x), int(y)) not in avoid_set
    ]
    if len(candidates) < int(count):
        raise ValueError("not enough minecraft cells to sample")
    return tuple(rng.sample(candidates, int(count)))


def _sample_top_ore_stack_count(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> MinecraftSceneSample:
    answer = int(axes.target_answer)
    grid_width = int(axes.grid_width)
    grid_depth = int(axes.grid_depth)
    target_kind = _resource_kind(rng=rng, params=params, allowed_kinds=MINECRAFT_ORE_KINDS)
    distractor_ore_kinds = tuple(kind for kind in MINECRAFT_ORE_KINDS if str(kind) != str(target_kind))
    height_support = tuple(sorted(set(_stack_height_support(params))))
    if not height_support:
        raise ValueError("top-ore stack count requires stack_height_support")
    distractor_count = int(rng.randrange(4, 8))
    total_stacks = int(answer) + int(distractor_count)
    stack_cells = _sample_distinct_cells(
        rng=rng,
        grid_width=grid_width,
        grid_depth=grid_depth,
        count=total_stacks,
        min_x=1,
        max_x_exclusive=grid_width - 1,
        min_y=1,
        max_y_exclusive=grid_depth - 1,
    )
    blocks: list[MinecraftBlock] = []
    annotation_ids: list[str] = []
    for stack_index, (x, y) in enumerate(stack_cells):
        qualifies = int(stack_index) < int(answer)
        height = int(rng.choice(height_support))
        top_kind = (
            str(target_kind)
            if qualifies
            else str(rng.choice(("stone", "dirt", *distractor_ore_kinds)))
        )
        if qualifies:
            annotation_ids.append(stack_entity_id(int(x), int(y)))
        for z in range(int(height)):
            kind = str(top_kind if int(z) == int(height) - 1 else rng.choice(("stone", "dirt")))
            blocks.append(
                MinecraftBlock(
                    block_id=f"top_ore_stack_{int(stack_index):02d}_z{int(z):02d}",
                    x=int(x),
                    y=int(y),
                    z=int(z),
                    kind=kind,
                )
            )
    rng.shuffle(blocks)
    sample = MinecraftSceneSample(
        grid_width=grid_width,
        grid_depth=grid_depth,
        query_id=TOP_ORE_STACK_QUERY_ID,
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=grid_width, grid_depth=grid_depth),
        blocks=tuple(blocks),
        player_cell=None,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        annotation_entity_ids=tuple(sorted(annotation_ids)),
        construction_mode=f"top_{target_kind}_stack_count_{answer}",
        target_resource_kind=target_kind,
        counted_resource_kind=target_kind,
    )
    validate_minecraft_sample(sample)
    return sample


def _sample_reachable_ore_stack_count(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> MinecraftSceneSample:
    answer = int(axes.target_answer)
    if not (0 <= answer <= 6):
        raise ValueError("reachable-ore answer must be in 0..6")
    target_kind = _resource_kind(rng=rng, params=params, allowed_kinds=MINECRAFT_ORE_KINDS)
    height_support = tuple(sorted(set(_stack_height_support(params))))
    if len(height_support) < 3:
        raise ValueError("reachable-ore task requires at least three stack heights")
    max_height = int(max(height_support))
    low_prefix_heights = tuple(int(height) for height in height_support if int(height) <= int(max_height) - 2)
    if not low_prefix_heights:
        raise ValueError("reachable-ore task requires a stack height at least two below the maximum")

    line_length = int(axes.line_length)
    if not (6 <= line_length <= 10) or int(line_length) < int(answer) + 2:
        raise ValueError("reachable-ore line length must be 6..10 and at least answer + 2")

    min_prefix_length = max(1, int(answer))
    max_prefix_length = int(line_length) - 2
    prefix_length = int(rng.randrange(int(min_prefix_length), int(max_prefix_length) + 1))

    # The platformer-style line starts on the ground-level stack; later stacks
    # rise from that baseline so the first visual support is always height 0.
    heights: list[int] = [1]
    for _index in range(1, int(prefix_length)):
        previous_height = int(heights[-1])
        candidates = tuple(
            int(height)
            for height in height_support
            if int(previous_height) <= int(height) <= int(previous_height) + 1 and int(height) <= int(max_height) - 2
        )
        if not candidates:
            raise ValueError("reachable-ore prefix cannot maintain the movement rule")
        heights.append(int(rng.choice(candidates)))

    blocker_candidates = tuple(int(height) for height in height_support if int(height) >= int(heights[-1]) + 2)
    if not blocker_candidates:
        raise ValueError("reachable-ore task cannot create a blocking height jump")
    heights.append(int(rng.choice(blocker_candidates)))
    while len(heights) < int(line_length):
        previous_height = int(heights[-1])
        suffix_candidates = tuple(int(height) for height in height_support if int(height) >= int(previous_height))
        heights.append(int(rng.choice(suffix_candidates or (previous_height,))))

    prefix_target_indices = set(rng.sample(tuple(range(int(prefix_length))), int(answer))) if answer else set()
    suffix_target_indices = {int(rng.randrange(int(prefix_length), int(line_length)))}
    for index in range(int(prefix_length), int(line_length)):
        if int(index) not in suffix_target_indices and float(rng.random()) < 0.25:
            suffix_target_indices.add(int(index))

    row_y = 1
    grid_width = int(line_length)
    grid_depth = 4
    line_cells = tuple((int(index), row_y) for index in range(int(line_length)))
    cell_kinds = {cell: "route_path" for cell in line_cells}

    blocks: list[MinecraftBlock] = []
    annotation_ids: list[str] = []
    for stack_index, (x, y) in enumerate(line_cells):
        is_counted = int(stack_index) in prefix_target_indices
        is_suffix_target = int(stack_index) in suffix_target_indices
        top_kind = (
            str(target_kind)
            if is_counted or is_suffix_target
            else str(rng.choice(("stone", "dirt")))
        )
        if is_counted:
            annotation_ids.append(stack_entity_id(int(x), int(y)))
        for z in range(int(heights[int(stack_index)])):
            kind = str(top_kind if int(z) == int(heights[int(stack_index)]) - 1 else rng.choice(("stone", "dirt")))
            blocks.append(
                MinecraftBlock(
                    block_id=f"reachable_stack_{int(stack_index):02d}_z{int(z):02d}",
                    x=int(x),
                    y=int(y),
                    z=int(z),
                    kind=kind,
                )
            )
    rng.shuffle(blocks)

    sample = MinecraftSceneSample(
        grid_width=int(grid_width),
        grid_depth=int(grid_depth),
        query_id=REACHABLE_ORE_STACK_QUERY_ID,
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=grid_width, grid_depth=grid_depth, cell_kinds=cell_kinds),
        blocks=tuple(blocks),
        player_cell=None,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        annotation_entity_ids=tuple(sorted(annotation_ids)),
        construction_mode=f"reachable_{target_kind}_{answer}_of_{line_length}_prefix_{prefix_length}",
        route_overlays=(),
        target_resource_kind=target_kind,
        counted_resource_kind=target_kind,
        stack_line_cells=line_cells,
        reachable_prefix_length=int(prefix_length),
    )
    validate_minecraft_sample(sample)
    return sample


def _route_rows(*, grid_depth: int, option_count: int) -> Tuple[int, ...]:
    if int(option_count) == 2:
        return (2, int(grid_depth) - 3)
    if int(option_count) == 4:
        return (1, max(3, int(grid_depth) // 3), max(5, (2 * int(grid_depth)) // 3), int(grid_depth) - 2)
    return (1, int(grid_depth) // 2, int(grid_depth) - 2)


def _sample_resource_route_cost(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> MinecraftSceneSample:
    answer = int(axes.target_answer)
    grid_width = int(axes.grid_width)
    grid_depth = int(axes.grid_depth)
    option_count = max(2, min(3, int(axes.route_option_count)))
    labels = tuple("ABCD"[:option_count])
    queried_label = str(rng.choice(labels))
    max_route_cost = max(3, min(9, grid_width - 3))
    route_cost_by_label: dict[str, int] = {}
    for label in labels:
        if label == queried_label:
            route_cost_by_label[label] = answer
        else:
            route_cost_by_label[label] = int(rng.randrange(2, max_route_cost + 1))

    route_colors = {
        "A": (220, 75, 73),
        "B": (68, 145, 219),
        "C": (72, 169, 94),
        "D": (157, 92, 209),
    }
    cell_kinds: dict[Tuple[int, int], str] = {}
    blocks: list[MinecraftBlock] = []
    route_overlays: list[MinecraftRouteOverlay] = []
    annotation_ids: list[str] = []
    route_costs: list[Tuple[str, int]] = []
    rows = _route_rows(grid_depth=grid_depth, option_count=option_count)
    for label, row_y in zip(labels, rows):
        path_cells = tuple((int(x), int(row_y)) for x in range(1, grid_width - 2))
        route_overlays.append(
            MinecraftRouteOverlay(
                label=str(label),
                cells=path_cells + ((grid_width - 2, int(row_y)),),
                rgb=route_colors[str(label)],
            )
        )
        route_cost = int(route_cost_by_label[str(label)])
        if int(route_cost) > len(path_cells):
            raise ValueError("route path too short for requested route cost")
        obstacle_cells = tuple(rng.sample(path_cells, int(route_cost)))
        route_annotation_ids: list[str] = []
        for obstacle_index, (x, y) in enumerate(obstacle_cells):
            block_id = route_obstacle_entity_id(str(label), int(obstacle_index))
            blocks.append(MinecraftBlock(block_id=block_id, x=int(x), y=int(y), z=0, kind=str(rng.choice(("stone", "dirt")))))
            route_annotation_ids.append(block_id)
        for cell in path_cells:
            cell_kinds.setdefault((int(cell[0]), int(cell[1])), "route_path")

        if str(label) == queried_label:
            annotation_ids = route_annotation_ids
        route_costs.append((str(label), int(route_cost)))

    sample = MinecraftSceneSample(
        grid_width=grid_width,
        grid_depth=grid_depth,
        query_id=RESOURCE_ROUTE_QUERY_ID,
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=grid_width, grid_depth=grid_depth, cell_kinds=cell_kinds),
        blocks=tuple(blocks),
        player_cell=None,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        annotation_entity_ids=tuple(annotation_ids),
        construction_mode=f"route_cost_{answer}_{queried_label}",
        route_overlays=tuple(route_overlays),
        route_costs=tuple(route_costs),
        selected_route_label=str(queried_label),
        target_resource_kind="",
        counted_resource_kind="",
    )
    validate_minecraft_sample(sample)
    return sample


def _stack_height_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return tuple(
        int(value)
        for value in resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="stack_height_support",
            fallback=_DEFAULTS.stack_height_support,
        )
    )


def _sample_stack_height_condition(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> MinecraftSceneSample:
    answer = int(axes.target_answer)
    grid_width = int(axes.grid_width)
    grid_depth = int(axes.grid_depth)
    target_height = int(axes.target_stack_height)
    height_support = tuple(sorted(set(_stack_height_support(params))))
    if target_height not in height_support:
        raise ValueError("target stack height must be in stack_height_support")
    if str(axes.query_id) == EXACT_HEIGHT_QUERY_ID:
        qualifying_heights = tuple(height for height in height_support if int(height) == target_height)
        distractor_heights = tuple(height for height in height_support if int(height) != target_height)
    elif str(axes.query_id) == AT_LEAST_HEIGHT_QUERY_ID:
        qualifying_heights = tuple(height for height in height_support if int(height) >= target_height)
        distractor_heights = tuple(height for height in height_support if int(height) < target_height)
    else:
        raise ValueError(f"unsupported stack-height query_id: {axes.query_id}")
    if not qualifying_heights or not distractor_heights:
        raise ValueError("stack-height query needs both qualifying and distractor heights")

    distractor_count = int(rng.randrange(4, 8))
    total_stacks = int(answer) + int(distractor_count)
    stack_cells = _sample_distinct_cells(
        rng=rng,
        grid_width=grid_width,
        grid_depth=grid_depth,
        count=total_stacks,
        min_x=1,
        max_x_exclusive=grid_width - 1,
        min_y=1,
        max_y_exclusive=grid_depth - 1,
    )
    block_kinds = ("stone", "dirt")
    blocks: list[MinecraftBlock] = []
    annotation_ids: list[str] = []
    for stack_index, (x, y) in enumerate(stack_cells):
        qualifies = int(stack_index) < int(answer)
        height = int(rng.choice(qualifying_heights if qualifies else distractor_heights))
        if qualifies:
            annotation_ids.append(stack_entity_id(int(x), int(y)))
        for z in range(int(height)):
            kind = str(rng.choice(block_kinds))
            blocks.append(
                MinecraftBlock(
                    block_id=f"stack_{int(stack_index):02d}_z{int(z):02d}",
                    x=int(x),
                    y=int(y),
                    z=int(z),
                    kind=kind,
                )
            )
    rng.shuffle(blocks)
    sample = MinecraftSceneSample(
        grid_width=grid_width,
        grid_depth=grid_depth,
        query_id=str(axes.query_id),
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=grid_width, grid_depth=grid_depth),
        blocks=tuple(blocks),
        player_cell=None,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        annotation_entity_ids=tuple(sorted(annotation_ids)),
        construction_mode=f"{str(axes.query_id)}_{target_height}_{answer}",
        target_resource_kind="",
        counted_resource_kind="",
        target_stack_height=int(target_height),
        stack_height_condition="exact" if str(axes.query_id) == EXACT_HEIGHT_QUERY_ID else "at_least",
    )
    validate_minecraft_sample(sample)
    return sample


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> MinecraftSceneSample:
    if str(axes.query_id) == TOP_ORE_STACK_QUERY_ID:
        return _sample_top_ore_stack_count(rng=rng, axes=axes, params=params)
    if str(axes.query_id) == REACHABLE_ORE_STACK_QUERY_ID:
        return _sample_reachable_ore_stack_count(rng=rng, axes=axes, params=params)
    if str(axes.query_id) == RESOURCE_ROUTE_QUERY_ID:
        return _sample_resource_route_cost(rng=rng, axes=axes, params=params)
    if str(axes.query_id) in STACK_HEIGHT_QUERY_IDS:
        return _sample_stack_height_condition(rng=rng, axes=axes, params=params)
    raise ValueError(f"unsupported minecraft query_id: {axes.query_id}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) == RESOURCE_ROUTE_QUERY_ID:
        answer_value = 4
        annotation_value = [
            [315, 316],
            [344, 287],
            [523, 212],
            [552, 240],
        ]
    elif str(query_id) in STACK_HEIGHT_QUERY_IDS:
        answer_value = 3
        annotation_value = [[290, 250], [423, 206], [542, 282]]
    elif str(query_id) == REACHABLE_ORE_STACK_QUERY_ID:
        answer_value = 2
        annotation_value = [[304, 252], [422, 222]]
    else:
        answer_value = 5
        annotation_value = [[339, 310], [397, 281], [455, 252], [484, 223], [368, 194]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _stack_heights_for_cells(blocks: Sequence[MinecraftBlock], cells: Sequence[Tuple[int, int]]) -> list[int]:
    """Return visible stack heights for an ordered stack line."""

    z_values_by_coord: dict[Tuple[int, int], set[int]] = {}
    for block in blocks:
        z_values_by_coord.setdefault((int(block.x), int(block.y)), set()).add(int(block.z))
    return [int(len(z_values_by_coord.get((int(x), int(y)), set()))) for x, y in cells]


def _build_complexity(*, task_id: str, sample: MinecraftSceneSample) -> TaskComplexity:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=task_id)
    query_id = str(sample.query_id)
    if query_id == TOP_ORE_STACK_QUERY_ID:
        block_reasoning = 0.44
        arithmetic_load = 0.12
    elif query_id == REACHABLE_ORE_STACK_QUERY_ID:
        block_reasoning = 0.78
        arithmetic_load = 0.16
    elif query_id == RESOURCE_ROUTE_QUERY_ID:
        block_reasoning = 0.76
        arithmetic_load = 0.56
    else:
        block_reasoning = 0.54
        arithmetic_load = 0.20
    visual_scan = clamp_unit_interval(
        (0.45 * normalize_linear(float(sample.grid_width * sample.grid_depth), min_value=64.0, max_value=120.0))
        + (0.35 * normalize_linear(float(len(sample.blocks)), min_value=0.0, max_value=6.0))
        + (0.20 * normalize_linear(float(sample.river_width), min_value=0.0, max_value=6.0))
    )
    output_burden = normalize_linear(float(len(sample.annotation_entity_ids)), min_value=1.0, max_value=11.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "block_reasoning": float(block_reasoning),
            "arithmetic_load": float(arithmetic_load),
            "output_burden": float(output_burden),
        },
    )


class GamesMinecraftBlockWorldTask:
    """Base generator for Minecraft-like block-world tasks."""

    task_id = BASE_TASK_ID
    domain = "games"
    task_group = TASK_GROUP
    query_id = TOP_ORE_STACK_QUERY_ID
    supported_query_ids: Tuple[str, ...] = (TOP_ORE_STACK_QUERY_ID,)

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_task_query_id(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=getattr(self, "supported_query_ids", (str(self.query_id),)),
        )
        axes = _resolve_axes(int(instance_seed), params=params, query_id=str(query_id))
        sampled_scene: MinecraftSceneSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{self.task_id}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        max_stack_height = (
            max(_stack_height_support(params))
            if str(query_id) in STACK_HEIGHT_QUERY_IDS
            or str(query_id) in {TOP_ORE_STACK_QUERY_ID, REACHABLE_ORE_STACK_QUERY_ID}
            else 1
        )
        render_params = _render_params(
            params,
            instance_seed=int(instance_seed),
            grid_width=int(sampled_scene.grid_width),
            grid_depth=int(sampled_scene.grid_depth),
            max_stack_height=int(max_stack_height),
            player_marker_label="START" if str(query_id) == REACHABLE_ORE_STACK_QUERY_ID else "P",
        )
        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.minecraft.panel_scene",
            treatment_weights=group_default(_GEN_DEFAULTS, "panel_treatment_weights", {}),
            palette_weights=group_default(_GEN_DEFAULTS, "panel_palette_weights", {}),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        ladder_columns = tuple(sampled_scene.ladder_columns)
        rendered_scene = render_minecraft_block_world_scene(
            grid_width=int(sampled_scene.grid_width),
            grid_depth=int(sampled_scene.grid_depth),
            terrain_cells=sampled_scene.terrain_cells,
            blocks=sampled_scene.blocks,
            player_cell=sampled_scene.player_cell,
            target_cell=sampled_scene.target_cell,
            style_variant=str(sampled_scene.style_variant),
            background=background,
            params=render_params,
            ladder_columns=ladder_columns,
            route_overlays=sampled_scene.route_overlays,
        )
        annotation_points = [
            list(rendered_scene.render_map["entity_points_px"][str(entity_id)])
            for entity_id in sampled_scene.annotation_entity_ids
        ]
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_block_world",
                "minecraft_route_cost_rule_text",
                f"answer_hint_{str(sampled_scene.query_id)}",
                f"annotation_hint_{str(sampled_scene.query_id)}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        target_kind = str(sampled_scene.target_resource_kind or sampled_scene.counted_resource_kind or "")
        json_example, json_example_answer_only = _build_prompt_json_examples(str(sampled_scene.query_id))
        object_description = str(prompt_defaults["object_description_block_world"])
        if str(sampled_scene.query_id) == REACHABLE_ORE_STACK_QUERY_ID:
            object_description = str(_PROMPT_DEFAULTS.get("object_description_reachable_stack_line", object_description))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(sampled_scene.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "minecraft_route_cost_rule_text": str(prompt_defaults["minecraft_route_cost_rule_text"]),
                "queried_route_label": str(sampled_scene.selected_route_label),
                "target_resource_name": resource_prompt_name(target_kind),
                "counted_resource_name": resource_prompt_name(sampled_scene.counted_resource_kind or target_kind),
                "target_stack_height": str(int(sampled_scene.target_stack_height)),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(sampled_scene.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(sampled_scene.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
        block_trace = [
            {
                "block_id": str(block.block_id),
                "x": int(block.x),
                "y": int(block.y),
                "z": int(block.z),
                "kind": str(block.kind),
            }
            for block in sampled_scene.blocks
        ]
        terrain_trace = [
            {
                "cell_id": str(cell.cell_id),
                "x": int(cell.x),
                "y": int(cell.y),
                "kind": str(cell.kind),
            }
            for cell in sampled_scene.terrain_cells
        ]
        stack_heights = _stack_heights_for_cells(sampled_scene.blocks, sampled_scene.stack_line_cells)
        first_blocker_index = (
            int(sampled_scene.reachable_prefix_length)
            if int(sampled_scene.reachable_prefix_length) < int(len(sampled_scene.stack_line_cells))
            else -1
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_minecraft_block_world",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "query_id": str(sampled_scene.query_id),
                    "style_variant": str(sampled_scene.style_variant),
                    "grid_width": int(sampled_scene.grid_width),
                    "grid_depth": int(sampled_scene.grid_depth),
                    "river_width": int(sampled_scene.river_width),
                    "scaffold_cost": int(sampled_scene.scaffold_cost),
                    "route_costs": [[str(label), int(cost)] for label, cost in sampled_scene.route_costs],
                    "route_option_count": int(len(sampled_scene.route_costs)),
                    "selected_route_label": str(sampled_scene.selected_route_label),
                    "target_stack_height": int(sampled_scene.target_stack_height),
                    "stack_height_condition": str(sampled_scene.stack_height_condition),
                    "stack_line_cells": [list(cell) for cell in sampled_scene.stack_line_cells],
                    "reachable_prefix_length": int(sampled_scene.reachable_prefix_length),
                    "stack_heights": list(stack_heights),
                    "first_blocker_index": int(first_blocker_index),
                    "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(sampled_scene.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(sampled_scene.query_id),
                    "style_variant": str(sampled_scene.style_variant),
                    "grid_width": int(sampled_scene.grid_width),
                    "grid_depth": int(sampled_scene.grid_depth),
                    "river_width": int(sampled_scene.river_width),
                    "scaffold_cost": int(sampled_scene.scaffold_cost),
                    "ladder_present": bool(sampled_scene.ladder_present),
                    "ladder_columns": [list(column) for column in sampled_scene.ladder_columns],
                    "route_costs": [[str(label), int(cost)] for label, cost in sampled_scene.route_costs],
                    "route_option_count": int(len(sampled_scene.route_costs)),
                    "selected_route_label": str(sampled_scene.selected_route_label),
                    "target_stack_height": int(sampled_scene.target_stack_height),
                    "target_stack_height_probabilities": dict(axes.target_stack_height_probabilities),
                    "stack_height_condition": str(sampled_scene.stack_height_condition),
                    "line_length": int(len(sampled_scene.stack_line_cells)),
                    "line_length_probabilities": dict(axes.line_length_probabilities),
                    "stack_line_cells": [list(cell) for cell in sampled_scene.stack_line_cells],
                    "reachable_prefix_length": int(sampled_scene.reachable_prefix_length),
                    "stack_heights": list(stack_heights),
                    "first_blocker_index": int(first_blocker_index),
                    "target_resource_kind": str(sampled_scene.target_resource_kind),
                    "counted_resource_kind": str(sampled_scene.counted_resource_kind),
                    "player_cell": list(sampled_scene.player_cell) if sampled_scene.player_cell is not None else None,
                    "target_cell": list(sampled_scene.target_cell) if sampled_scene.target_cell is not None else None,
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "grid_width_probabilities": dict(axes.grid_width_probabilities),
                    "grid_depth_probabilities": dict(axes.grid_depth_probabilities),
                    "answer_probabilities": dict(axes.answer_probabilities),
                    "route_option_count_probabilities": dict(axes.route_option_count_probabilities),
                    "query_id_probabilities": dict(query_id_probabilities),
                },
            },
            "render_spec": {
                "style_variant": str(sampled_scene.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(rendered_scene.render_map.get("text_style", {})),
                "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "query_id": str(sampled_scene.query_id),
                "style_variant": str(sampled_scene.style_variant),
                "answer": int(sampled_scene.answer),
                "grid_width": int(sampled_scene.grid_width),
                "grid_depth": int(sampled_scene.grid_depth),
                "river_width": int(sampled_scene.river_width),
                "scaffold_cost": int(sampled_scene.scaffold_cost),
                "ladder_present": bool(sampled_scene.ladder_present),
                "ladder_columns": [list(column) for column in sampled_scene.ladder_columns],
                "route_costs": [[str(label), int(cost)] for label, cost in sampled_scene.route_costs],
                "route_option_count": int(len(sampled_scene.route_costs)),
                "selected_route_label": str(sampled_scene.selected_route_label),
                "target_stack_height": int(sampled_scene.target_stack_height),
                "stack_height_condition": str(sampled_scene.stack_height_condition),
                "line_length": int(len(sampled_scene.stack_line_cells)),
                "stack_line_cells": [list(cell) for cell in sampled_scene.stack_line_cells],
                "reachable_prefix_length": int(sampled_scene.reachable_prefix_length),
                "stack_heights": list(stack_heights),
                "first_blocker_index": int(first_blocker_index),
                "target_resource_kind": str(sampled_scene.target_resource_kind),
                "counted_resource_kind": str(sampled_scene.counted_resource_kind),
                "player_cell": list(sampled_scene.player_cell) if sampled_scene.player_cell is not None else None,
                "target_cell": list(sampled_scene.target_cell) if sampled_scene.target_cell is not None else None,
                "terrain_cells": terrain_trace,
                "blocks": block_trace,
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": [list(point) for point in annotation_points],
                "pixel_point_set": [list(point) for point in annotation_points],
            },
            "background": background_meta,
            "panel_scene_style": dict(panel_style_meta),
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(task_id=str(self.task_id), sample=sampled_scene),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sampled_scene.query_id),
        )


@register_task
class GamesMinecraftTopOreStackCountTask(GamesMinecraftBlockWorldTask):
    """Count visible stacks whose top cube is a requested Minecraft-like ore type."""

    task_id = "task_games__minecraft__top_ore_stack_count"
    query_id = TOP_ORE_STACK_QUERY_ID
    supported_query_ids = (TOP_ORE_STACK_QUERY_ID,)


@register_task
class GamesMinecraftReachableOreStackCountTask(GamesMinecraftBlockWorldTask):
    """Count target-ore stack tops reachable along a height-constrained Minecraft-like line."""

    task_id = "task_games__minecraft__reachable_ore_stack_count"
    query_id = REACHABLE_ORE_STACK_QUERY_ID
    supported_query_ids = (REACHABLE_ORE_STACK_QUERY_ID,)


@register_task
class GamesMinecraftResourceRouteCostTask(GamesMinecraftBlockWorldTask):
    """Compute the block cost along a named Minecraft-like mining route."""

    task_id = "task_games__minecraft__resource_route_cost"
    query_id = RESOURCE_ROUTE_QUERY_ID
    supported_query_ids = (RESOURCE_ROUTE_QUERY_ID,)


@register_task
class GamesMinecraftStackHeightConditionCountTask(GamesMinecraftBlockWorldTask):
    """Count visible cube stacks satisfying a sampled height condition."""

    task_id = "task_games__minecraft__stack_height_condition_count"
    query_id = EXACT_HEIGHT_QUERY_ID
    supported_query_ids = STACK_HEIGHT_QUERY_IDS


__all__ = [
    "AT_LEAST_HEIGHT_QUERY_ID",
    "EXACT_HEIGHT_QUERY_ID",
    "GamesMinecraftBlockWorldTask",
    "GamesMinecraftReachableOreStackCountTask",
    "GamesMinecraftResourceRouteCostTask",
    "GamesMinecraftStackHeightConditionCountTask",
    "GamesMinecraftTopOreStackCountTask",
    "REACHABLE_ORE_STACK_QUERY_ID",
    "RESOURCE_ROUTE_QUERY_ID",
    "STACK_HEIGHT_QUERY_IDS",
    "TOP_ORE_STACK_QUERY_ID",
]
