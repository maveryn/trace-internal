"""Games tasks over Minecraft-like voxel block worlds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice
from ..shared.complexity import build_games_complexity, clamp_unit_interval, normalize_linear, resolve_games_complexity_weights
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.minecraft_common import (
    MinecraftBlock,
    MinecraftCell,
    MinecraftRouteOverlay,
    MinecraftSceneSample,
    SUPPORTED_MINECRAFT_RESOURCE_KINDS,
    SUPPORTED_MINECRAFT_STYLE_VARIANTS,
    ore_block_entity_id,
    resource_prompt_name,
    route_obstacle_entity_id,
    terrain_cell_entity_id,
    tunnel_block_entity_id,
    validate_minecraft_sample,
    water_cell_entity_id,
)
from ..shared.minecraft_scene import MinecraftRenderParams, render_minecraft_block_world_scene
from ..shared.sampling import resolve_games_named_axis
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_GROUP = "minecraft"
SCENE_ID = "minecraft"
BASE_TASK_ID = "games_minecraft_block_world_base"

ORE_BLOCK_QUERY_ID = "ore_block_count"
TUNNEL_CLEARANCE_QUERY_ID = "tunnel_clearance_count"
RESOURCE_ROUTE_QUERY_ID = "resource_route_cost"
MINECRAFT_ORE_KINDS: Tuple[str, ...] = ("diamond_ore", "gold_ore")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Minecraft-like block-world tasks."""

    grid_width_support: Tuple[int, ...] = (8, 9, 10)
    grid_depth_support: Tuple[int, ...] = (8, 9, 10)
    ore_answer_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    tunnel_answer_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    route_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    route_grid_width_support: Tuple[int, ...] = (11,)
    route_grid_depth_support: Tuple[int, ...] = (8, 9, 10)
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
    style_variant_probabilities: Dict[str, float]
    grid_width_probabilities: Dict[str, float]
    grid_depth_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=BASE_TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group=TASK_GROUP)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def _answer_support_key(query_id: str) -> tuple[str, str, Tuple[int, ...]]:
    if str(query_id) == ORE_BLOCK_QUERY_ID:
        return ("ore_answer_support", "target_answer", _DEFAULTS.ore_answer_support)
    if str(query_id) == TUNNEL_CLEARANCE_QUERY_ID:
        return ("tunnel_answer_support", "target_answer", _DEFAULTS.tunnel_answer_support)
    if str(query_id) == RESOURCE_ROUTE_QUERY_ID:
        return ("route_answer_support", "target_answer", _DEFAULTS.route_answer_support)
    raise ValueError(f"unsupported minecraft query_id: {query_id}")


def _grid_support_keys(query_id: str) -> tuple[str, str, Tuple[int, ...], Tuple[int, ...]]:
    if str(query_id) == RESOURCE_ROUTE_QUERY_ID:
        return (
            "route_grid_width_support",
            "route_grid_depth_support",
            _DEFAULTS.route_grid_width_support,
            _DEFAULTS.route_grid_depth_support,
        )
    return ("grid_width_support", "grid_depth_support", _DEFAULTS.grid_width_support, _DEFAULTS.grid_depth_support)


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
    return _ResolvedAxes(
        query_id=str(query_id),
        style_variant=str(style_variant),
        grid_width=int(grid_width),
        grid_depth=int(grid_depth),
        target_answer=int(target_answer),
        style_variant_probabilities=dict(style_variant_probabilities),
        grid_width_probabilities=dict(grid_width_probabilities),
        grid_depth_probabilities=dict(grid_depth_probabilities),
        answer_probabilities=dict(answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> MinecraftRenderParams:
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
    return MinecraftRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        tile_width_px=scale_games_px(params.get("tile_width_px", group_default(_RENDER_DEFAULTS, "tile_width_px", _DEFAULTS.tile_width_px)), unit_scale, min_px=29),
        tile_height_px=scale_games_px(params.get("tile_height_px", group_default(_RENDER_DEFAULTS, "tile_height_px", _DEFAULTS.tile_height_px)), unit_scale, min_px=15),
        cube_height_px=scale_games_px(params.get("cube_height_px", group_default(_RENDER_DEFAULTS, "cube_height_px", _DEFAULTS.cube_height_px)), unit_scale, min_px=15),
        outline_width_px=scale_games_px(params.get("outline_width_px", group_default(_RENDER_DEFAULTS, "outline_width_px", _DEFAULTS.outline_width_px)), unit_scale, min_px=1),
        player_marker_size_px=scale_games_px(params.get("player_marker_size_px", group_default(_RENDER_DEFAULTS, "player_marker_size_px", _DEFAULTS.player_marker_size_px)), unit_scale, min_px=14),
        layout_jitter_meta=layout_jitter,
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


def _sample_ore_block_count(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> MinecraftSceneSample:
    answer = int(axes.target_answer)
    grid_width = int(axes.grid_width)
    grid_depth = int(axes.grid_depth)
    target_kind = _resource_kind(rng=rng, params=params, allowed_kinds=MINECRAFT_ORE_KINDS)
    distractor_kind = "gold_ore" if target_kind == "diamond_ore" else "diamond_ore"
    target_cells = _sample_distinct_cells(
        rng=rng,
        grid_width=grid_width,
        grid_depth=grid_depth,
        count=answer,
        min_x=1,
        max_x_exclusive=grid_width - 1,
        min_y=1,
        max_y_exclusive=grid_depth - 1,
    )
    distractor_count = int(rng.randrange(3, 6))
    distractor_cells = _sample_distinct_cells(
        rng=rng,
        grid_width=grid_width,
        grid_depth=grid_depth,
        count=distractor_count,
        avoid=target_cells,
        min_x=1,
        max_x_exclusive=grid_width - 1,
        min_y=1,
        max_y_exclusive=grid_depth - 1,
    )
    blocks: list[MinecraftBlock] = []
    evidence_ids: list[str] = []
    for index, (x, y) in enumerate(target_cells):
        block_id = ore_block_entity_id(int(index))
        blocks.append(MinecraftBlock(block_id=block_id, x=int(x), y=int(y), z=0, kind=target_kind))
        evidence_ids.append(block_id)
    for index, (x, y) in enumerate(distractor_cells):
        kind = str(rng.choice((distractor_kind, "stone", "dirt", "pumpkin")))
        blocks.append(MinecraftBlock(block_id=f"ore_distractor_{int(index):02d}", x=int(x), y=int(y), z=0, kind=kind))
    sample = MinecraftSceneSample(
        grid_width=grid_width,
        grid_depth=grid_depth,
        query_id=ORE_BLOCK_QUERY_ID,
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=grid_width, grid_depth=grid_depth),
        blocks=tuple(blocks),
        player_cell=None,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        evidence_entity_ids=tuple(evidence_ids),
        construction_mode=f"count_{target_kind}_{answer}",
        target_resource_kind=target_kind,
        counted_resource_kind=target_kind,
    )
    validate_minecraft_sample(sample)
    return sample


def _bent_path(*, start: Tuple[int, int], end: Tuple[int, int], bend_x: int) -> Tuple[Tuple[int, int], ...]:
    sx, sy = int(start[0]), int(start[1])
    ex, ey = int(end[0]), int(end[1])
    cells: list[Tuple[int, int]] = []
    step_x = 1 if int(bend_x) >= sx else -1
    for x in range(sx, int(bend_x) + step_x, step_x):
        cells.append((int(x), sy))
    step_y = 1 if ey >= sy else -1
    for y in range(sy + step_y, ey + step_y, step_y):
        cells.append((int(bend_x), int(y)))
    step_x2 = 1 if ex >= int(bend_x) else -1
    for x in range(int(bend_x) + step_x2, ex + step_x2, step_x2):
        cells.append((int(x), ey))
    deduped: list[Tuple[int, int]] = []
    for cell in cells:
        if not deduped or deduped[-1] != cell:
            deduped.append(cell)
    return tuple(deduped)


def _sample_tunnel_clearance_count(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> MinecraftSceneSample:
    answer = int(axes.target_answer)
    grid_width = int(axes.grid_width)
    grid_depth = int(axes.grid_depth)
    start = (1, int(rng.randrange(1, 3)))
    end = (grid_width - 2, int(rng.randrange(grid_depth - 3, grid_depth - 1)))
    bend_x = int(rng.randrange(3, grid_width - 3))
    path_cells = _bent_path(start=start, end=end, bend_x=bend_x)
    interior_cells = tuple(cell for cell in path_cells[1:-1])
    if len(interior_cells) < answer:
        raise ValueError("tunnel path too short for answer")
    blocked_cells = tuple(rng.sample(interior_cells, answer))
    blocked_set = set(blocked_cells)
    blocks: list[MinecraftBlock] = []
    evidence_ids: list[str] = []
    for index, (x, y) in enumerate(blocked_cells):
        block_id = tunnel_block_entity_id(int(index))
        blocks.append(MinecraftBlock(block_id=block_id, x=int(x), y=int(y), z=0, kind=str(rng.choice(("stone", "dirt", "stone")))))
        evidence_ids.append(block_id)
    distractor_count = int(rng.randrange(3, 6))
    distractor_cells = _sample_distinct_cells(
        rng=rng,
        grid_width=grid_width,
        grid_depth=grid_depth,
        count=distractor_count,
        avoid=tuple(path_cells),
    )
    for index, (x, y) in enumerate(distractor_cells):
        blocks.append(MinecraftBlock(block_id=f"tunnel_distractor_{int(index):02d}", x=int(x), y=int(y), z=0, kind=str(rng.choice(("stone", "dirt")))))
    cell_kinds = {cell: "tunnel_path" for cell in path_cells}
    route = MinecraftRouteOverlay(label="", cells=path_cells, rgb=(237, 159, 47))
    sample = MinecraftSceneSample(
        grid_width=grid_width,
        grid_depth=grid_depth,
        query_id=TUNNEL_CLEARANCE_QUERY_ID,
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=grid_width, grid_depth=grid_depth, cell_kinds=cell_kinds),
        blocks=tuple(blocks),
        player_cell=start,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        evidence_entity_ids=tuple(evidence_ids),
        construction_mode=f"marked_tunnel_blocked_{answer}_path_{len(path_cells)}",
        route_overlays=(route,),
    )
    if not blocked_set <= set(interior_cells):
        raise ValueError("invalid tunnel blocked cells")
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
    option_count = 2
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
    evidence_ids: list[str] = []
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
        route_evidence_ids: list[str] = []
        for obstacle_index, (x, y) in enumerate(obstacle_cells):
            block_id = route_obstacle_entity_id(str(label), int(obstacle_index))
            blocks.append(MinecraftBlock(block_id=block_id, x=int(x), y=int(y), z=0, kind=str(rng.choice(("stone", "dirt")))))
            route_evidence_ids.append(block_id)
        for cell in path_cells:
            cell_kinds.setdefault((int(cell[0]), int(cell[1])), "route_path")

        if str(label) == queried_label:
            evidence_ids = route_evidence_ids
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
        evidence_entity_ids=tuple(evidence_ids),
        construction_mode=f"route_cost_{answer}_{queried_label}",
        route_overlays=tuple(route_overlays),
        route_costs=tuple(route_costs),
        selected_route_label=str(queried_label),
        target_resource_kind="",
        counted_resource_kind="",
    )
    validate_minecraft_sample(sample)
    return sample


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> MinecraftSceneSample:
    if str(axes.query_id) == ORE_BLOCK_QUERY_ID:
        return _sample_ore_block_count(rng=rng, axes=axes, params=params)
    if str(axes.query_id) == TUNNEL_CLEARANCE_QUERY_ID:
        return _sample_tunnel_clearance_count(rng=rng, axes=axes, params=params)
    if str(axes.query_id) == RESOURCE_ROUTE_QUERY_ID:
        return _sample_resource_route_cost(rng=rng, axes=axes, params=params)
    raise ValueError(f"unsupported minecraft query_id: {axes.query_id}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) == TUNNEL_CLEARANCE_QUERY_ID:
        answer_value = 4
        evidence_value = [[352, 245, 410, 304], [381, 274, 439, 333], [410, 303, 468, 362], [439, 332, 497, 391]]
    elif str(query_id) == RESOURCE_ROUTE_QUERY_ID:
        answer_value = 6
        evidence_value = [
            [286, 302, 344, 332],
            [315, 273, 373, 303],
            [492, 182, 554, 242],
            [492, 122, 554, 182],
            [492, 62, 554, 122],
            [521, 210, 579, 270],
        ]
    else:
        answer_value = 5
        evidence_value = [[310, 310, 367, 371], [368, 281, 425, 342], [426, 252, 483, 313], [455, 223, 512, 284], [339, 194, 396, 255]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _build_complexity(*, task_id: str, sample: MinecraftSceneSample) -> TaskComplexity:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=task_id)
    query_id = str(sample.query_id)
    if query_id == ORE_BLOCK_QUERY_ID:
        block_reasoning = 0.30
        arithmetic_load = 0.12
    elif query_id == TUNNEL_CLEARANCE_QUERY_ID:
        block_reasoning = 0.48
        arithmetic_load = 0.18
    else:
        block_reasoning = 0.76
        arithmetic_load = 0.56
    visual_scan = clamp_unit_interval(
        (0.45 * normalize_linear(float(sample.grid_width * sample.grid_depth), min_value=64.0, max_value=120.0))
        + (0.35 * normalize_linear(float(len(sample.blocks)), min_value=0.0, max_value=6.0))
        + (0.20 * normalize_linear(float(sample.river_width), min_value=0.0, max_value=6.0))
    )
    output_burden = normalize_linear(float(len(sample.evidence_entity_ids)), min_value=1.0, max_value=11.0)
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
    query_id = ORE_BLOCK_QUERY_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params, query_id=str(self.query_id))
        render_params = _render_params(params, instance_seed=int(instance_seed))
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

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
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
        evidence_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_entity_ids
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
                "minecraft_tunnel_rule_text",
                "minecraft_route_cost_rule_text",
                f"answer_hint_{str(sampled_scene.query_id)}",
                f"evidence_hint_{str(sampled_scene.query_id)}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        target_kind = str(sampled_scene.target_resource_kind or sampled_scene.counted_resource_kind or "")
        json_example, json_example_answer_only = _build_prompt_json_examples(str(sampled_scene.query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(sampled_scene.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_block_world"]),
                "minecraft_tunnel_rule_text": str(prompt_defaults["minecraft_tunnel_rule_text"]),
                "minecraft_route_cost_rule_text": str(prompt_defaults["minecraft_route_cost_rule_text"]),
                "queried_route_label": str(sampled_scene.selected_route_label),
                "target_resource_name": resource_prompt_name(target_kind),
                "counted_resource_name": resource_prompt_name(sampled_scene.counted_resource_kind or target_kind),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(sampled_scene.query_id)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(sampled_scene.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
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
                    "selected_route_label": str(sampled_scene.selected_route_label),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
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
                    "selected_route_label": str(sampled_scene.selected_route_label),
                    "target_resource_kind": str(sampled_scene.target_resource_kind),
                    "counted_resource_kind": str(sampled_scene.counted_resource_kind),
                    "player_cell": list(sampled_scene.player_cell) if sampled_scene.player_cell is not None else None,
                    "target_cell": list(sampled_scene.target_cell) if sampled_scene.target_cell is not None else None,
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "grid_width_probabilities": dict(axes.grid_width_probabilities),
                    "grid_depth_probabilities": dict(axes.grid_depth_probabilities),
                    "answer_probabilities": dict(axes.answer_probabilities),
                    "query_id_probabilities": {str(sampled_scene.query_id): 1.0},
                },
            },
            "render_spec": {
                "style_variant": str(sampled_scene.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
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
                "selected_route_label": str(sampled_scene.selected_route_label),
                "target_resource_kind": str(sampled_scene.target_resource_kind),
                "counted_resource_kind": str(sampled_scene.counted_resource_kind),
                "player_cell": list(sampled_scene.player_cell) if sampled_scene.player_cell is not None else None,
                "target_cell": list(sampled_scene.target_cell) if sampled_scene.target_cell is not None else None,
                "terrain_cells": terrain_trace,
                "blocks": block_trace,
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(task_id=str(self.task_id), sample=sampled_scene),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sampled_scene.query_id),
        )


@register_task
class GamesMinecraftOreBlockCountTask(GamesMinecraftBlockWorldTask):
    """Count visible blocks of a requested Minecraft-like ore type."""

    task_id = "task_games__minecraft__ore_block_count"
    query_id = ORE_BLOCK_QUERY_ID


@register_task
class GamesMinecraftTunnelClearanceCountTask(GamesMinecraftBlockWorldTask):
    """Count solid blocks that must be cleared from a marked tunnel path."""

    task_id = "task_games__minecraft__tunnel_clearance_count"
    query_id = TUNNEL_CLEARANCE_QUERY_ID


@register_task
class GamesMinecraftResourceRouteCostTask(GamesMinecraftBlockWorldTask):
    """Count block cost along one named Minecraft-like mining route."""

    task_id = "task_games__minecraft__resource_route_cost_value"
    query_id = RESOURCE_ROUTE_QUERY_ID


__all__ = [
    "GamesMinecraftBlockWorldTask",
    "GamesMinecraftOreBlockCountTask",
    "GamesMinecraftResourceRouteCostTask",
    "GamesMinecraftTunnelClearanceCountTask",
    "ORE_BLOCK_QUERY_ID",
    "RESOURCE_ROUTE_QUERY_ID",
    "TUNNEL_CLEARANCE_QUERY_ID",
]
