"""Identity-free sampling primitives for Minecraft-like block-world scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support

from .defaults import (
    DEFAULTS,
    HEIGHT_CONDITION_AT_LEAST,
    HEIGHT_CONDITION_EXACT,
    ORE_KINDS,
    RESOURCE_KINDS,
    SAMPLE_KIND_HEIGHT_FILTER,
    SAMPLE_KIND_REACHABLE_RESOURCE,
    SAMPLE_KIND_ROUTE_COST,
    SAMPLE_KIND_TOP_RESOURCE,
    STYLE_VARIANTS,
)
from .rules import validate_minecraft_sample
from .state import (
    MinecraftBlock,
    MinecraftCell,
    MinecraftRouteOverlay,
    MinecraftSceneSample,
    route_obstacle_entity_id,
    stack_entity_id,
    terrain_cell_entity_id,
    water_cell_entity_id,
)


@dataclass(frozen=True)
class MinecraftAxes:
    """Resolved semantic and visual axes for one block-world instance."""

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


def resolve_top_resource_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
) -> MinecraftAxes:
    """Resolve axes for a top-resource stack count scene."""

    return _resolve_axes(
        int(instance_seed),
        gen_defaults=gen_defaults,
        namespace=str(namespace),
        params=params,
        answer_support_key="top_ore_stack_answer_support",
        answer_fallback=DEFAULTS.top_resource_answer_support,
    )


def resolve_reachable_resource_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
) -> MinecraftAxes:
    """Resolve axes for a one-line reachable-resource scene."""

    style_variant, style_variant_probabilities = _resolve_style_variant(
        int(instance_seed),
        gen_defaults=gen_defaults,
        namespace=str(namespace),
        params=params,
    )
    target_answer, answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="reachable_ore_stack_answer_support",
        explicit_key="target_answer",
        fallback_support=DEFAULTS.reachable_resource_answer_support,
        namespace=f"{namespace}.reachable_answer",
        balanced_flag_key="balanced_answer_sampling",
        namespace_support_permutation=True,
    )
    raw_line_length_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="reachable_line_length_support",
        fallback=DEFAULTS.reachable_line_length_support,
    )
    min_line_length = max(6, int(target_answer) + 2)
    line_length_support = tuple(length for length in raw_line_length_support if int(length) >= int(min_line_length))
    if not line_length_support:
        raise ValueError("reachable line length support cannot fit the requested answer")
    line_params = dict(params)
    line_params["reachable_line_length_support"] = tuple(int(length) for length in line_length_support)
    line_length, line_length_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=line_params,
        gen_defaults=gen_defaults,
        support_key="reachable_line_length_support",
        explicit_key="line_length",
        fallback_support=line_length_support,
        namespace=f"{namespace}.line_length",
        balanced_flag_key="balanced_reachable_line_length_sampling",
        namespace_support_permutation=True,
    )
    return MinecraftAxes(
        style_variant=str(style_variant),
        grid_width=int(line_length),
        grid_depth=4,
        target_answer=int(target_answer),
        target_stack_height=0,
        line_length=int(line_length),
        route_option_count=0,
        style_variant_probabilities=dict(style_variant_probabilities),
        grid_width_probabilities={str(int(line_length)): 1.0},
        grid_depth_probabilities={"4": 1.0},
        answer_probabilities=dict(answer_probabilities),
        target_stack_height_probabilities={"0": 1.0},
        line_length_probabilities=dict(line_length_probabilities),
        route_option_count_probabilities={"0": 1.0},
    )


def resolve_route_cost_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
) -> MinecraftAxes:
    """Resolve axes for a labeled route-cost scene."""

    axes = _resolve_axes(
        int(instance_seed),
        gen_defaults=gen_defaults,
        namespace=str(namespace),
        params=params,
        answer_support_key="route_answer_support",
        answer_fallback=DEFAULTS.route_answer_support,
        width_support_key="route_grid_width_support",
        depth_support_key="route_grid_depth_support",
        width_fallback=DEFAULTS.route_grid_width_support,
        depth_fallback=DEFAULTS.route_grid_depth_support,
    )
    route_option_count, route_option_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="route_option_count_support",
        explicit_key="route_option_count",
        fallback_support=DEFAULTS.route_option_count_support,
        namespace=f"{namespace}.route_option_count",
        balanced_flag_key="balanced_route_option_count_sampling",
        namespace_support_permutation=True,
    )
    return MinecraftAxes(
        **{
            **axes.__dict__,
            "route_option_count": int(route_option_count),
            "route_option_count_probabilities": dict(route_option_count_probabilities),
        }
    )


def resolve_height_filter_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    height_condition: str,
) -> MinecraftAxes:
    """Resolve axes for exact-height or at-least-height stack counting."""

    if str(height_condition) == HEIGHT_CONDITION_EXACT:
        height_support_key = "exact_target_height_support"
        height_fallback = DEFAULTS.exact_target_height_support
    elif str(height_condition) == HEIGHT_CONDITION_AT_LEAST:
        height_support_key = "at_least_target_height_support"
        height_fallback = DEFAULTS.at_least_target_height_support
    else:
        raise ValueError(f"unsupported stack height condition: {height_condition}")

    axes = _resolve_axes(
        int(instance_seed),
        gen_defaults=gen_defaults,
        namespace=str(namespace),
        params=params,
        answer_support_key="stack_height_answer_support",
        answer_fallback=DEFAULTS.height_filter_answer_support,
    )
    target_stack_height, target_stack_height_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=height_support_key,
        explicit_key="target_stack_height",
        fallback_support=height_fallback,
        namespace=f"{namespace}.target_stack_height",
        balanced_flag_key="balanced_target_stack_height_sampling",
        namespace_support_permutation=True,
    )
    return MinecraftAxes(
        **{
            **axes.__dict__,
            "target_stack_height": int(target_stack_height),
            "target_stack_height_probabilities": dict(target_stack_height_probabilities),
        }
    )


def sample_top_resource_scene(
    *,
    rng: Any,
    axes: MinecraftAxes,
    gen_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
) -> MinecraftSceneSample:
    """Construct a scene with an exact count of target-resource top cubes."""

    answer = int(axes.target_answer)
    target_kind = _resource_kind(rng=rng, params=params, allowed_kinds=ORE_KINDS)
    distractor_ore_kinds = tuple(kind for kind in ORE_KINDS if str(kind) != str(target_kind))
    height_support = tuple(sorted(set(_stack_height_support(params, gen_defaults=gen_defaults))))
    if not height_support:
        raise ValueError("top-resource stack count requires stack height support")
    distractor_count = int(rng.randrange(4, 8))
    total_stacks = int(answer) + int(distractor_count)
    stack_cells = _sample_distinct_cells(
        rng=rng,
        grid_width=int(axes.grid_width),
        grid_depth=int(axes.grid_depth),
        count=total_stacks,
        min_x=1,
        max_x_exclusive=int(axes.grid_width) - 1,
        min_y=1,
        max_y_exclusive=int(axes.grid_depth) - 1,
    )
    blocks: list[MinecraftBlock] = []
    annotation_ids: list[str] = []
    for stack_index, (x, y) in enumerate(stack_cells):
        qualifies = int(stack_index) < int(answer)
        height = int(rng.choice(height_support))
        top_kind = str(target_kind) if qualifies else str(rng.choice(("stone", "dirt", *distractor_ore_kinds)))
        if qualifies:
            annotation_ids.append(stack_entity_id(int(x), int(y)))
        for z in range(int(height)):
            kind = str(top_kind if int(z) == int(height) - 1 else rng.choice(("stone", "dirt")))
            blocks.append(
                MinecraftBlock(
                    block_id=f"top_resource_stack_{int(stack_index):02d}_z{int(z):02d}",
                    x=int(x),
                    y=int(y),
                    z=int(z),
                    kind=kind,
                )
            )
    rng.shuffle(blocks)
    sample = MinecraftSceneSample(
        grid_width=int(axes.grid_width),
        grid_depth=int(axes.grid_depth),
        sample_kind=SAMPLE_KIND_TOP_RESOURCE,
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=int(axes.grid_width), grid_depth=int(axes.grid_depth)),
        blocks=tuple(blocks),
        player_cell=None,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        annotation_entity_ids=tuple(sorted(annotation_ids)),
        construction_mode=f"top_resource_{answer}",
        target_resource_kind=target_kind,
        counted_resource_kind=target_kind,
    )
    validate_minecraft_sample(sample)
    return sample


def sample_reachable_resource_scene(
    *,
    rng: Any,
    axes: MinecraftAxes,
    gen_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
) -> MinecraftSceneSample:
    """Construct a one-line height-constrained reachable resource scene."""

    answer = int(axes.target_answer)
    if not (0 <= answer <= 6):
        raise ValueError("reachable-resource answer must be in 0..6")
    target_kind = _resource_kind(rng=rng, params=params, allowed_kinds=ORE_KINDS)
    height_support = tuple(sorted(set(_stack_height_support(params, gen_defaults=gen_defaults))))
    if len(height_support) < 3:
        raise ValueError("reachable-resource task requires at least three stack heights")
    max_height = int(max(height_support))
    if not tuple(int(height) for height in height_support if int(height) <= int(max_height) - 2):
        raise ValueError("reachable-resource task requires a stack height at least two below the maximum")

    line_length = int(axes.line_length)
    if not (6 <= line_length <= 10) or int(line_length) < int(answer) + 2:
        raise ValueError("reachable-resource line length must be 6..10 and at least answer + 2")
    min_prefix_length = max(1, int(answer))
    max_prefix_length = int(line_length) - 2
    prefix_length = int(rng.randrange(int(min_prefix_length), int(max_prefix_length) + 1))

    heights: list[int] = [1]
    for _index in range(1, int(prefix_length)):
        previous_height = int(heights[-1])
        candidates = tuple(
            int(height)
            for height in height_support
            if int(previous_height) <= int(height) <= int(previous_height) + 1
            and int(height) <= int(max_height) - 2
        )
        if not candidates:
            raise ValueError("reachable-resource prefix cannot maintain the movement rule")
        heights.append(int(rng.choice(candidates)))

    blocker_candidates = tuple(int(height) for height in height_support if int(height) >= int(heights[-1]) + 2)
    if not blocker_candidates:
        raise ValueError("reachable-resource task cannot create a blocking height jump")
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
    line_cells = tuple((int(index), row_y) for index in range(int(line_length)))
    cell_kinds = {cell: "route_path" for cell in line_cells}
    blocks: list[MinecraftBlock] = []
    annotation_ids: list[str] = []
    for stack_index, (x, y) in enumerate(line_cells):
        is_counted = int(stack_index) in prefix_target_indices
        is_suffix_target = int(stack_index) in suffix_target_indices
        top_kind = str(target_kind) if is_counted or is_suffix_target else str(rng.choice(("stone", "dirt")))
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
        grid_width=int(line_length),
        grid_depth=4,
        sample_kind=SAMPLE_KIND_REACHABLE_RESOURCE,
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=int(line_length), grid_depth=4, cell_kinds=cell_kinds),
        blocks=tuple(blocks),
        player_cell=None,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        annotation_entity_ids=tuple(sorted(annotation_ids)),
        construction_mode=f"reachable_resource_{answer}_of_{line_length}_prefix_{prefix_length}",
        target_resource_kind=target_kind,
        counted_resource_kind=target_kind,
        stack_line_cells=line_cells,
        reachable_prefix_length=int(prefix_length),
    )
    validate_minecraft_sample(sample)
    return sample


def sample_route_cost_scene(*, rng: Any, axes: MinecraftAxes) -> MinecraftSceneSample:
    """Construct labeled route options with a selected exact block cost."""

    answer = int(axes.target_answer)
    grid_width = int(axes.grid_width)
    grid_depth = int(axes.grid_depth)
    option_count = max(2, min(3, int(axes.route_option_count)))
    labels = tuple("ABCD"[:option_count])
    selected_label = str(rng.choice(labels))
    max_route_cost = max(3, min(9, grid_width - 3))
    route_cost_by_label: dict[str, int] = {}
    for label in labels:
        route_cost_by_label[str(label)] = answer if label == selected_label else int(rng.randrange(2, max_route_cost + 1))

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
            blocks.append(
                MinecraftBlock(
                    block_id=block_id,
                    x=int(x),
                    y=int(y),
                    z=0,
                    kind=str(rng.choice(("stone", "dirt"))),
                )
            )
            route_annotation_ids.append(block_id)
        for cell in path_cells:
            cell_kinds.setdefault((int(cell[0]), int(cell[1])), "route_path")

        if str(label) == selected_label:
            annotation_ids = route_annotation_ids
        route_costs.append((str(label), int(route_cost)))

    sample = MinecraftSceneSample(
        grid_width=grid_width,
        grid_depth=grid_depth,
        sample_kind=SAMPLE_KIND_ROUTE_COST,
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
        construction_mode=f"route_cost_{answer}_{selected_label}",
        route_overlays=tuple(route_overlays),
        route_costs=tuple(route_costs),
        selected_route_label=str(selected_label),
    )
    validate_minecraft_sample(sample)
    return sample


def sample_height_filter_scene(
    *,
    rng: Any,
    axes: MinecraftAxes,
    gen_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    height_condition: str,
) -> MinecraftSceneSample:
    """Construct a stack field with an exact count for one height predicate."""

    answer = int(axes.target_answer)
    target_height = int(axes.target_stack_height)
    height_support = tuple(sorted(set(_stack_height_support(params, gen_defaults=gen_defaults))))
    if target_height not in height_support:
        raise ValueError("target stack height must be in stack height support")
    if str(height_condition) == HEIGHT_CONDITION_EXACT:
        qualifying_heights = tuple(height for height in height_support if int(height) == target_height)
        distractor_heights = tuple(height for height in height_support if int(height) != target_height)
    elif str(height_condition) == HEIGHT_CONDITION_AT_LEAST:
        qualifying_heights = tuple(height for height in height_support if int(height) >= target_height)
        distractor_heights = tuple(height for height in height_support if int(height) < target_height)
    else:
        raise ValueError(f"unsupported stack height condition: {height_condition}")
    if not qualifying_heights or not distractor_heights:
        raise ValueError("height-filter query needs both qualifying and distractor heights")

    distractor_count = int(rng.randrange(4, 8))
    total_stacks = int(answer) + int(distractor_count)
    stack_cells = _sample_distinct_cells(
        rng=rng,
        grid_width=int(axes.grid_width),
        grid_depth=int(axes.grid_depth),
        count=total_stacks,
        min_x=1,
        max_x_exclusive=int(axes.grid_width) - 1,
        min_y=1,
        max_y_exclusive=int(axes.grid_depth) - 1,
    )
    blocks: list[MinecraftBlock] = []
    annotation_ids: list[str] = []
    for stack_index, (x, y) in enumerate(stack_cells):
        qualifies = int(stack_index) < int(answer)
        height = int(rng.choice(qualifying_heights if qualifies else distractor_heights))
        if qualifies:
            annotation_ids.append(stack_entity_id(int(x), int(y)))
        for z in range(int(height)):
            blocks.append(
                MinecraftBlock(
                    block_id=f"height_stack_{int(stack_index):02d}_z{int(z):02d}",
                    x=int(x),
                    y=int(y),
                    z=int(z),
                    kind=str(rng.choice(("stone", "dirt"))),
                )
            )
    rng.shuffle(blocks)
    sample = MinecraftSceneSample(
        grid_width=int(axes.grid_width),
        grid_depth=int(axes.grid_depth),
        sample_kind=SAMPLE_KIND_HEIGHT_FILTER,
        style_variant=str(axes.style_variant),
        answer=answer,
        terrain_cells=_terrain_cells_from_kinds(grid_width=int(axes.grid_width), grid_depth=int(axes.grid_depth)),
        blocks=tuple(blocks),
        player_cell=None,
        target_cell=None,
        river_width=0,
        scaffold_cost=0,
        ladder_present=False,
        annotation_entity_ids=tuple(sorted(annotation_ids)),
        construction_mode=f"height_filter_{height_condition}_{target_height}_{answer}",
        target_stack_height=int(target_height),
        stack_height_condition=str(height_condition),
    )
    validate_minecraft_sample(sample)
    return sample


def stack_height_support(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve allowed visible stack heights for block-world constructions."""

    return _stack_height_support(params, gen_defaults=gen_defaults)


def _resolve_style_variant(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
) -> tuple[str, Dict[str, float]]:
    """Resolve the scene style axis shared by all block-world tasks."""

    return resolve_games_named_axis(
        task_id=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=f"{namespace}.style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported_variants=STYLE_VARIANTS,
    )


def _resolve_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    answer_support_key: str,
    answer_fallback: Sequence[int],
    width_support_key: str = "grid_width_support",
    depth_support_key: str = "grid_depth_support",
    width_fallback: Sequence[int] = DEFAULTS.grid_width_support,
    depth_fallback: Sequence[int] = DEFAULTS.grid_depth_support,
) -> MinecraftAxes:
    """Resolve common style, board-size, and target-answer axes."""

    style_variant, style_variant_probabilities = _resolve_style_variant(
        int(instance_seed),
        gen_defaults=gen_defaults,
        namespace=str(namespace),
        params=params,
    )
    grid_width, grid_width_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(width_support_key),
        explicit_key="grid_width",
        fallback_support=tuple(int(value) for value in width_fallback),
        namespace=f"{namespace}.grid_width",
        balanced_flag_key="balanced_grid_width_sampling",
        namespace_support_permutation=True,
    )
    grid_depth, grid_depth_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(depth_support_key),
        explicit_key="grid_depth",
        fallback_support=tuple(int(value) for value in depth_fallback),
        namespace=f"{namespace}.grid_depth",
        balanced_flag_key="balanced_grid_depth_sampling",
        namespace_support_permutation=True,
    )
    target_answer, answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(answer_support_key),
        explicit_key="target_answer",
        fallback_support=tuple(int(value) for value in answer_fallback),
        namespace=f"{namespace}.answer",
        balanced_flag_key="balanced_answer_sampling",
        namespace_support_permutation=True,
    )
    return MinecraftAxes(
        style_variant=str(style_variant),
        grid_width=int(grid_width),
        grid_depth=int(grid_depth),
        target_answer=int(target_answer),
        target_stack_height=0,
        line_length=0,
        route_option_count=0,
        style_variant_probabilities=dict(style_variant_probabilities),
        grid_width_probabilities=dict(grid_width_probabilities),
        grid_depth_probabilities=dict(grid_depth_probabilities),
        answer_probabilities=dict(answer_probabilities),
        target_stack_height_probabilities={"0": 1.0},
        line_length_probabilities={"0": 1.0},
        route_option_count_probabilities={"0": 1.0},
    )


def _terrain_cells_from_kinds(
    *,
    grid_width: int,
    grid_depth: int,
    cell_kinds: Mapping[Tuple[int, int], str] | None = None,
) -> Tuple[MinecraftCell, ...]:
    """Build terrain cells for every visible ground coordinate."""

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


def _resource_kind(*, rng: Any, params: Mapping[str, Any], allowed_kinds: Sequence[str] | None = None) -> str:
    """Resolve or sample one prompt-facing resource block kind."""

    explicit = params.get("resource_kind", params.get("target_resource_kind"))
    supported = tuple(str(kind) for kind in (allowed_kinds or RESOURCE_KINDS))
    if explicit is not None:
        kind = str(explicit)
        if kind not in supported:
            raise ValueError(f"unsupported resource kind: {kind}")
        return str(kind)
    return str(rng.choice(supported))


def _sample_distinct_cells(
    *,
    rng: Any,
    grid_width: int,
    grid_depth: int,
    count: int,
    avoid: Sequence[Tuple[int, int]] = (),
    min_x: int = 1,
    max_x_exclusive: int | None = None,
    min_y: int = 1,
    max_y_exclusive: int | None = None,
) -> Tuple[Tuple[int, int], ...]:
    """Sample distinct cells from an interior rectangular range."""

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


def _stack_height_support(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve configured stack-height support."""

    return tuple(
        int(value)
        for value in resolve_integer_support(
            params,
            gen_defaults=gen_defaults,
            key="stack_height_support",
            fallback=DEFAULTS.stack_height_support,
        )
    )


def _route_rows(*, grid_depth: int, option_count: int) -> Tuple[int, ...]:
    """Choose visually separated horizontal route rows."""

    if int(option_count) == 2:
        return (2, int(grid_depth) - 3)
    if int(option_count) == 4:
        return (1, max(3, int(grid_depth) // 3), max(5, (2 * int(grid_depth)) // 3), int(grid_depth) - 2)
    return (1, int(grid_depth) // 2, int(grid_depth) - 2)


__all__ = [
    "MinecraftAxes",
    "resolve_height_filter_axes",
    "resolve_reachable_resource_axes",
    "resolve_route_cost_axes",
    "resolve_top_resource_axes",
    "sample_height_filter_scene",
    "sample_reachable_resource_scene",
    "sample_route_cost_scene",
    "sample_top_resource_scene",
    "stack_height_support",
]
