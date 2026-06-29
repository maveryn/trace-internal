"""Sampling primitives for voxel-ladder puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from trace.core.sampling import integer_range_choice, uniform_choice
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.named_colors import sample_named_color_palette

from .defaults import get_int_range, to_int
from .rules import (
    build_route_path,
    checkpoint_item_id,
    is_ladder_edge,
    make_graph_edges,
    orthogonal_neighbors,
    reachable_nodes,
    route_edges,
    sequence_distractors,
    sequence_rgb,
    sequence_text,
)
from .state import (
    Checkpoint,
    Ladder,
    OPTION_LABELS,
    OptionSpec,
    SCENE_VARIANTS,
    VoxelLadderDataset,
)


@dataclass(frozen=True)
class VoxelLadderPlan:
    """Task-owned semantic requirements for one generated ladder scene."""

    route_checkpoint_count: int
    route_option_count: int = 0
    answer_option_label: str | None = None
    target_reachable_count: int | None = None
    unreachable_checkpoint_count: int = 0
    add_reachable_branch: bool = False


def explicit_or_cursor_choice(
    params: Mapping[str, Any],
    *,
    key: str,
    support: Sequence[str],
    rng: Any,
) -> str:
    """Sample from support with explicit override and review-cursor cycling."""

    values = tuple(str(value) for value in support)
    explicit = params.get(str(key))
    if explicit is not None:
        text = str(explicit)
        if text not in values:
            raise ValueError(f"{key} must be one of {values}")
        return text
    cursor = params.get("_sample_cursor")
    if cursor is not None:
        return values[abs(int(cursor)) % len(values)]
    return str(uniform_choice(rng, values))


def explicit_or_cursor_int(
    params: Mapping[str, Any],
    *,
    key: str,
    lower: int,
    upper: int,
    rng: Any,
) -> int:
    """Sample an integer support with explicit override and review-cursor cycling."""

    explicit = params.get(str(key))
    if explicit is not None:
        value = to_int(explicit, int(lower))
        if not (int(lower) <= int(value) <= int(upper)):
            raise ValueError(f"{key} must be in [{lower}, {upper}]")
        return int(value)
    cursor = params.get("_sample_cursor")
    if cursor is not None:
        support = tuple(range(int(lower), int(upper) + 1))
        return int(support[abs(int(cursor)) % len(support)])
    selected, _probabilities = integer_range_choice(rng, int(lower), int(upper))
    return int(selected)


def select_scene_variant(
    params: Mapping[str, Any],
    rng: Any,
) -> tuple[str, dict[str, float]]:
    """Select a scene render variant without using task/query routing."""

    explicit = params.get("scene_variant")
    if explicit is not None:
        variant = str(explicit)
        if variant not in SCENE_VARIANTS:
            raise ValueError(f"unsupported scene_variant: {variant}")
        return variant, {
            item: (1.0 if item == variant else 0.0) for item in SCENE_VARIANTS
        }
    cursor = params.get("_sample_cursor")
    if cursor is not None:
        variant = SCENE_VARIANTS[abs(int(cursor)) % len(SCENE_VARIANTS)]
        return variant, {item: 1.0 / len(SCENE_VARIANTS) for item in SCENE_VARIANTS}
    variant = str(uniform_choice(rng, SCENE_VARIANTS))
    return variant, {item: 1.0 / len(SCENE_VARIANTS) for item in SCENE_VARIANTS}


def route_checkpoint_count(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng: Any,
) -> int:
    """Resolve the number of checkpoints on the start-to-goal route."""

    lower, upper = get_int_range(
        params,
        defaults,
        min_key="route_checkpoint_count_min",
        max_key="route_checkpoint_count_max",
        fallback_min=2,
        fallback_max=4,
    )
    return explicit_or_cursor_int(
        params,
        key="route_checkpoint_count",
        lower=lower,
        upper=upper,
        rng=rng,
    )


def route_option_count(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng: Any,
) -> int:
    """Resolve the number of route-sequence option cards."""

    lower, upper = get_int_range(
        params,
        defaults,
        min_key="route_option_count_min",
        max_key="route_option_count_max",
        fallback_min=6,
        fallback_max=6,
    )
    return explicit_or_cursor_int(
        params,
        key="route_option_count",
        lower=lower,
        upper=upper,
        rng=rng,
    )


def sample_voxel_ladder_scene(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rng: Any,
    plan: VoxelLadderPlan,
) -> VoxelLadderDataset:
    """Build a voxel-ladder scene satisfying the task-owned semantic plan."""

    scene_variant, scene_variant_probabilities = select_scene_variant(params, rng)
    ladder_min, ladder_max = get_int_range(
        params,
        generation_defaults,
        min_key="route_ladder_count_min",
        max_key="route_ladder_count_max",
        fallback_min=1,
        fallback_max=3,
    )
    ladder_count = int(rng.randint(ladder_min, ladder_max))
    path_nodes = build_route_path(rng, ladder_count=int(ladder_count))
    path_edges = route_edges(path_nodes)
    ladder_edges = [edge for edge in path_edges if is_ladder_edge(edge)]
    ladders = tuple(
        Ladder(
            ladder_id=f"ladder_{index}",
            lower=min(edge[0], edge[1], key=lambda node: node[2]),
            upper=max(edge[0], edge[1], key=lambda node: node[2]),
            on_goal_route=True,
        )
        for index, edge in enumerate(ladder_edges)
    )
    cubes: set[tuple[int, int, int]] = set(path_nodes)
    route_candidates = [
        node
        for node in path_nodes[1:-1]
        if not any(node == ladder.upper for ladder in ladders)
    ]
    if len(route_candidates) < 5:
        route_candidates = list(path_nodes[1:-1])
    route_count = min(int(plan.route_checkpoint_count), max(2, len(route_candidates)))
    main_nodes = _spaced_route_nodes(route_candidates, path_nodes, route_count, rng)
    reachable_branch_nodes: list[tuple[int, int, int]] = []
    target_reachable = plan.target_reachable_count
    branch_needed = 1 if bool(plan.add_reachable_branch) else 0
    if target_reachable is not None:
        branch_needed = max(0, int(target_reachable) - len(main_nodes))
    if branch_needed > 0:
        reachable_branch_nodes = _add_reachable_branch_nodes(
            cubes,
            path_nodes,
            needed=int(branch_needed),
            rng=rng,
        )
    unreachable_nodes = _add_unreachable_nodes(
        cubes,
        count=int(plan.unreachable_checkpoint_count),
        ladder_count=int(ladder_count),
        rng=rng,
    )
    checkpoints = _build_checkpoints(
        rng,
        main_nodes=main_nodes,
        reachable_branch_nodes=reachable_branch_nodes,
        unreachable_nodes=unreachable_nodes,
    )
    graph_edges = make_graph_edges(tuple(sorted(cubes)), ladders)
    reachable = reachable_nodes(path_nodes[0], graph_edges)
    for checkpoint in checkpoints:
        if bool(checkpoint.reachable) != bool(checkpoint.node in reachable):
            raise RuntimeError("voxel-ladder checkpoint reachability drift")
    reachable_count = sum(1 for checkpoint in checkpoints if checkpoint.reachable)
    if target_reachable is not None and int(reachable_count) != int(target_reachable):
        raise RuntimeError("voxel-ladder reachable target drift")
    route_labels = tuple(
        checkpoint.color_name
        for checkpoint in sorted(
            (checkpoint for checkpoint in checkpoints if checkpoint.on_goal_route),
            key=lambda checkpoint: path_nodes.index(checkpoint.node),
        )
    )
    option_specs = _build_route_options(
        rng,
        route_labels=route_labels,
        all_labels=[checkpoint.color_name for checkpoint in checkpoints],
        option_count=int(plan.route_option_count),
        answer_option_label=plan.answer_option_label,
    )
    return VoxelLadderDataset(
        scene_variant=str(scene_variant),
        cubes=tuple(sorted(cubes)),
        route_nodes=tuple(path_nodes),
        route_edges=tuple(path_edges),
        start_node=tuple(path_nodes[0]),
        goal_node=tuple(path_nodes[-1]),
        checkpoints=tuple(checkpoints),
        ladders=tuple(ladders),
        graph_edges=tuple(graph_edges),
        option_specs=tuple(option_specs),
        route_checkpoint_sequence=tuple(route_labels),
        reachable_checkpoint_count=int(reachable_count),
        semantic_params={
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "route_ladder_count": int(len(ladders)),
        },
    )


def _spaced_route_nodes(
    route_candidates: Sequence[tuple[int, int, int]],
    path_nodes: Sequence[tuple[int, int, int]],
    count: int,
    rng: Any,
) -> list[tuple[int, int, int]]:
    """Choose route checkpoints in path order with rough spacing."""

    step = max(1, len(route_candidates) // max(1, int(count)))
    main_nodes = list(route_candidates[::step][: int(count)])
    while len(main_nodes) < int(count):
        candidate = route_candidates[int(rng.randrange(len(route_candidates)))]
        if candidate not in main_nodes:
            main_nodes.append(candidate)
    return sorted(main_nodes, key=lambda node: path_nodes.index(node))


def _add_reachable_branch_nodes(
    cubes: set[tuple[int, int, int]],
    path_nodes: Sequence[tuple[int, int, int]],
    *,
    needed: int,
    rng: Any,
) -> list[tuple[int, int, int]]:
    """Attach extra reachable checkpoint cubes to the route."""

    branch_nodes: list[tuple[int, int, int]] = []
    sources = list(path_nodes[1:-1])
    rng.shuffle(sources)
    remaining = int(needed)
    for source in sources:
        for neighbor in orthogonal_neighbors(source):
            if neighbor not in cubes and neighbor[2] >= 0:
                cubes.add(neighbor)
                branch_nodes.append(neighbor)
                remaining -= 1
                break
        if remaining <= 0:
            break
    if remaining > 0:
        raise RuntimeError("could not place enough reachable branch checkpoints")
    return branch_nodes


def _add_unreachable_nodes(
    cubes: set[tuple[int, int, int]],
    *,
    count: int,
    ladder_count: int,
    rng: Any,
) -> list[tuple[int, int, int]]:
    """Place unreachable checkpoint cubes away from the route graph."""

    if int(count) <= 0:
        return []
    max_x = max(node[0] for node in cubes)
    max_y = max(node[1] for node in cubes)
    nodes: list[tuple[int, int, int]] = []
    for index in range(int(count)):
        node = (
            max_x + 3 + index,
            max_y + int(rng.randint(0, 2)),
            int(rng.randint(0, max(1, int(ladder_count)))),
        )
        cubes.add(node)
        nodes.append(node)
    return nodes


def _build_checkpoints(
    rng: Any,
    *,
    main_nodes: Sequence[tuple[int, int, int]],
    reachable_branch_nodes: Sequence[tuple[int, int, int]],
    unreachable_nodes: Sequence[tuple[int, int, int]],
) -> tuple[Checkpoint, ...]:
    """Assign unique canonical color names to checkpoint nodes."""

    label_count = len(main_nodes) + len(reachable_branch_nodes) + len(unreachable_nodes)
    palette = sample_named_color_palette(rng, palette_size=int(label_count))
    if len(palette) < int(label_count):
        raise RuntimeError("voxel-ladder checkpoint count exceeds named-color palette")
    checkpoints: list[Checkpoint] = []
    label_index = 0
    for node in main_nodes:
        color_name, color_rgb = palette[label_index]
        checkpoints.append(
            Checkpoint(
                color_name=str(color_name),
                color_rgb=tuple(int(v) for v in color_rgb),
                node=tuple(node),
                reachable=True,
                on_goal_route=True,
            )
        )
        label_index += 1
    for node in reachable_branch_nodes:
        color_name, color_rgb = palette[label_index]
        checkpoints.append(
            Checkpoint(
                color_name=str(color_name),
                color_rgb=tuple(int(v) for v in color_rgb),
                node=tuple(node),
                reachable=True,
                on_goal_route=False,
            )
        )
        label_index += 1
    for node in unreachable_nodes:
        color_name, color_rgb = palette[label_index]
        checkpoints.append(
            Checkpoint(
                color_name=str(color_name),
                color_rgb=tuple(int(v) for v in color_rgb),
                node=tuple(node),
                reachable=False,
                on_goal_route=False,
            )
        )
        label_index += 1
    return tuple(checkpoints)


def _build_route_options(
    rng: Any,
    *,
    route_labels: Sequence[str],
    all_labels: Sequence[str],
    option_count: int,
    answer_option_label: str | None,
) -> tuple[OptionSpec, ...]:
    """Build route-sequence option cards when requested."""

    if int(option_count) <= 0:
        return ()
    labels = OPTION_LABELS[: int(option_count)]
    correct_label = str(answer_option_label or labels[0])
    if correct_label not in labels:
        raise ValueError(f"answer option label must be in {labels}")
    correct_index = labels.index(correct_label)
    correct_sequence = tuple(str(label) for label in route_labels)
    distractors = sequence_distractors(
        rng,
        correct_sequence,
        [str(label) for label in all_labels],
        int(option_count),
    )
    option_sequences = list(distractors)
    option_sequences.insert(correct_index, correct_sequence)
    return tuple(
        OptionSpec(
            option_label=str(labels[index]),
            sequence_items=tuple(option_sequences[index]),
            sequence_text=sequence_text(option_sequences[index]),
            sequence_rgb=sequence_rgb(option_sequences[index]),
            is_correct=bool(index == correct_index),
        )
        for index in range(int(option_count))
    )


def checkpoint_bboxes_for_reachable(
    dataset: VoxelLadderDataset,
    item_bbox_map: Mapping[str, tuple[float, float, float, float]],
) -> tuple[tuple[float, float, float, float], ...]:
    """Return bboxes for all reachable checkpoint cubes."""

    return tuple(
        item_bbox_map[checkpoint_item_id(checkpoint.color_name)]
        for checkpoint in dataset.checkpoints
        if checkpoint.reachable
    )


def unreachable_checkpoint(dataset: VoxelLadderDataset) -> Checkpoint:
    """Return the single unreachable checkpoint."""

    unreachable = [
        checkpoint for checkpoint in dataset.checkpoints if not checkpoint.reachable
    ]
    if len(unreachable) != 1:
        raise ValueError("expected exactly one unreachable checkpoint")
    return unreachable[0]
