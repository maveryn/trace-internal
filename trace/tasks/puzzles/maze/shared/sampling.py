"""Sampling helpers for maze-exit puzzle instances."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from trace.core.seed import spawn_rng

from trace.tasks.shared.config_defaults import group_default

from .defaults import to_int
from .state import EXIT_LABEL_POOL, SCENE_NAMESPACE, TARGET_REACHABILITY_VALUES, Cell
from .topology import (
    boundary_sides,
    exit_clockwise_sort_key,
    generate_spanning_tree,
    reachable_cells_from_start,
)

def resolve_int_bounds(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    lower = to_int(params.get(str(min_key), group_default(defaults, str(min_key), int(fallback_min))), int(fallback_min))
    upper = to_int(params.get(str(max_key), group_default(defaults, str(max_key), int(fallback_max))), int(fallback_max))
    if int(lower) > int(upper):
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(lower), int(upper)
def sample_int(
    *,
    rng,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    sampling_offset: int,
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = resolve_int_bounds(
        params,
        defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
    )
    explicit = params.get(str(key))
    if explicit is not None:
        value = to_int(explicit, int(lower))
        if not (int(lower) <= int(value) <= int(upper)):
            raise ValueError(f"{key} must be within [{lower}, {upper}]")
        return int(value), (int(lower), int(upper))
    support = list(range(int(lower), int(upper) + 1))
    _ = sampling_offset
    return int(rng.randint(int(lower), int(upper))), (int(lower), int(upper))
def sample_exit_target_index(*, params: Mapping[str, Any], rng, exit_count: int, offset: int) -> int:
    support = list(range(int(exit_count)))
    if "target_exit_index" in params:
        value = to_int(params["target_exit_index"], 0)
        if int(value) not in support:
            raise ValueError("target_exit_index must be within the active exit support")
        return int(value)
    _ = offset
    return int(rng.choice(support))
def sample_reachable_count(*, params: Mapping[str, Any], defaults: Mapping[str, Any], rng, exit_count: int) -> Tuple[int, Tuple[int, int]]:
    lower, upper = resolve_int_bounds(
        params,
        defaults,
        min_key="reachable_exit_count_min",
        max_key="reachable_exit_count_max",
        fallback_min=1,
        fallback_max=5,
    )
    active_lower = max(1, min(int(lower), int(exit_count) - 1))
    active_upper = max(int(active_lower), min(int(upper), int(exit_count) - 1))
    support = list(range(int(active_lower), int(active_upper) + 1))
    if "reachable_exit_total" in params:
        value = to_int(params["reachable_exit_total"], int(active_lower))
        if int(value) not in support:
            raise ValueError("reachable_exit_total must be within the active exit-count support")
        return int(value), (int(lower), int(upper))
    return int(rng.choice(support)), (int(lower), int(upper))
def sample_reachable_count_for_exit_range(
    *,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
    exit_count_range: Tuple[int, int],
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = resolve_int_bounds(
        params,
        defaults,
        min_key="reachable_exit_count_min",
        max_key="reachable_exit_count_max",
        fallback_min=1,
        fallback_max=5,
    )
    active_lower = max(1, min(int(lower), int(exit_count_range[1]) - 1))
    active_upper = max(int(active_lower), min(int(upper), int(exit_count_range[1]) - 1))
    support = list(range(int(active_lower), int(active_upper) + 1))
    if "reachable_exit_total" in params:
        value = to_int(params["reachable_exit_total"], int(active_lower))
        if int(value) not in support:
            raise ValueError("reachable_exit_total must be within the active exit-count support")
        return int(value), (int(lower), int(upper))
    return int(rng.choice(support)), (int(lower), int(upper))
def sample_exit_count_for_reachable_count(
    *,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
    reachable_count: int,
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = resolve_int_bounds(
        params,
        defaults,
        min_key="exit_count_min",
        max_key="exit_count_max",
        fallback_min=5,
        fallback_max=8,
    )
    if int(upper) > len(EXIT_LABEL_POOL):
        raise ValueError("exit_count cannot exceed the available exit-label pool")
    active_lower = max(int(lower), int(reachable_count) + 1)
    if int(active_lower) > int(upper):
        raise ValueError("reachable_exit_total requires more exits than exit_count_max allows")
    support = list(range(int(active_lower), int(upper) + 1))
    if "exit_count" in params:
        value = to_int(params["exit_count"], int(active_lower))
        if not (int(lower) <= int(value) <= int(upper)):
            raise ValueError(f"exit_count must be within [{lower}, {upper}]")
        if int(value) <= int(reachable_count):
            raise ValueError("exit_count must be greater than reachable_exit_total")
        return int(value), (int(lower), int(upper))
    return int(rng.choice(support)), (int(lower), int(upper))

def build_maze_exit_dataset(
    *,
    request_kind: str,
    target_reachability: str | None,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    generation_defaults: Mapping[str, Any],
    max_attempts: int,
) -> Dict[str, Any]:
    """Build a maze instance without any public task identity branching.

    ``request_kind`` selects the neutral construction shape: either a single
    target exit with a requested reachability, or a reachable-exit count with a
    sampled count support. Public task files bind those constructions to task
    ids, prompts, answers, and annotations.
    """

    is_label_request = str(request_kind) == "exit_label"
    if bool(is_label_request):
        if str(target_reachability) not in set(TARGET_REACHABILITY_VALUES):
            raise ValueError("target_reachability must be reachable or unreachable for exit_reachability_label")
        resolved_target_reachability = str(target_reachability)
    else:
        resolved_target_reachability = None
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.dataset")
    rows, row_range = sample_int(
        rng=rng,
        params=params,
        defaults=generation_defaults,
        key="maze_rows",
        min_key="maze_rows_min",
        max_key="maze_rows_max",
        fallback_min=7,
        fallback_max=10,
        sampling_offset=0,
    )
    cols, col_range = sample_int(
        rng=rng,
        params=params,
        defaults=generation_defaults,
        key="maze_cols",
        min_key="maze_cols_min",
        max_key="maze_cols_max",
        fallback_min=9,
        fallback_max=13,
        sampling_offset=3,
    )
    sampled_reachable_count: int | None = None
    reachable_count_range: Tuple[int, int] | None = None

    if str(request_kind) == "reachable_count" and "exit_count" not in params:
        exit_count_bounds = resolve_int_bounds(
            params,
            generation_defaults,
            min_key="exit_count_min",
            max_key="exit_count_max",
            fallback_min=5,
            fallback_max=8,
        )
        sampled_reachable_count, reachable_count_range = sample_reachable_count_for_exit_range(
            params=params,
            defaults=generation_defaults,
            rng=rng,
            exit_count_range=exit_count_bounds,
        )
        exit_count, exit_count_range = sample_exit_count_for_reachable_count(
            params=params,
            defaults=generation_defaults,
            rng=rng,
            reachable_count=int(sampled_reachable_count),
        )
    else:
        exit_count, exit_count_range = sample_int(
            rng=rng,
            params=params,
            defaults=generation_defaults,
            key="exit_count",
            min_key="exit_count_min",
            max_key="exit_count_max",
            fallback_min=5,
            fallback_max=8,
            sampling_offset=11,
        )
    if int(exit_count) > len(EXIT_LABEL_POOL):
        raise ValueError("exit_count cannot exceed the available exit-label pool")

    start_col_options = [max(1, int(cols) // 2 - 1), int(cols) // 2, min(int(cols) - 2, int(cols) // 2 + 1)]
    start_row_options = [max(1, int(rows) // 2 - 1), int(rows) // 2, min(int(rows) - 2, int(rows) // 2 + 1)]
    start = (int(rng.choice(start_col_options)), int(rng.choice(start_row_options)))
    if not (0 < start[0] < int(cols) - 1 and 0 < start[1] < int(rows) - 1):
        start = (max(1, min(int(cols) - 2, int(cols) // 2)), max(1, min(int(rows) - 2, int(rows) // 2)))

    all_boundary_cells = [
        (int(col), int(row))
        for row in range(int(rows))
        for col in range(int(cols))
        if bool(boundary_sides((int(col), int(row)), rows=int(rows), cols=int(cols)))
    ]
    attempt_count = max(120, int(max_attempts) * 16)
    for attempt in range(int(attempt_count)):
        tree_rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.maze_tree", index=int(attempt))
        candidate_cells = list(all_boundary_cells)
        tree_rng.shuffle(candidate_cells)
        if len(candidate_cells) < int(exit_count):
            continue
        exit_cells = [tuple(cell) for cell in candidate_cells[: int(exit_count)]]
        labels = list(EXIT_LABEL_POOL)
        tree_rng.shuffle(labels)
        exits: List[Dict[str, Any]] = []
        for index, cell in enumerate(exit_cells):
            sides = list(boundary_sides(cell, rows=int(rows), cols=int(cols)))
            side = str(tree_rng.choice(sides))
            exits.append(
                {
                    "item_id": f"exit_{index + 1}",
                    "label": str(labels[index]),
                    "cell": [int(cell[0]), int(cell[1])],
                    "side": str(side),
                }
            )
        exits = sorted(exits, key=lambda item: exit_clockwise_sort_key(item, rows=int(rows), cols=int(cols)))

        target_index = sample_exit_target_index(params=params, rng=tree_rng, exit_count=int(exit_count), offset=17)
        if bool(is_label_request) and str(resolved_target_reachability) == "reachable":
            reachable_indices = {int(target_index)}
        elif bool(is_label_request) and str(resolved_target_reachability) == "unreachable":
            reachable_indices = {index for index in range(int(exit_count)) if index != int(target_index)}
        else:
            if sampled_reachable_count is None:
                sampled_reachable_count, reachable_count_range = sample_reachable_count(
                    params=params,
                    defaults=generation_defaults,
                    rng=tree_rng,
                    exit_count=int(exit_count),
                )
            shuffled_indices = list(range(int(exit_count)))
            tree_rng.shuffle(shuffled_indices)
            reachable_indices = set(shuffled_indices[: int(sampled_reachable_count)])

        blocked_exit_cells = {
            tuple(int(value) for value in exit_spec["cell"])
            for index, exit_spec in enumerate(exits)
            if int(index) not in reachable_indices
        }
        allowed_cells = {
            (int(col), int(row))
            for row in range(int(rows))
            for col in range(int(cols))
            if (int(col), int(row)) not in blocked_exit_cells
        }
        try:
            open_edges = set(
                generate_spanning_tree(
                    rows=int(rows),
                    cols=int(cols),
                    start=tuple(start),
                    rng=tree_rng,
                    allowed_cells=allowed_cells,
                )
            )
        except ValueError:
            continue
        for index, exit_spec in enumerate(exits):
            cell = tuple(int(value) for value in exit_spec["cell"])
            if int(index) in reachable_indices and cell not in allowed_cells:
                raise ValueError("reachable exit cell was excluded from the maze")

        reachable_cells = set(reachable_cells_from_start(start=tuple(start), rows=int(rows), cols=int(cols), edges=tuple(open_edges)))
        for index, exit_spec in enumerate(exits):
            cell = tuple(int(value) for value in exit_spec["cell"])
            exit_spec["reachable"] = bool(cell in reachable_cells)
        if {index for index, exit_spec in enumerate(exits) if bool(exit_spec["reachable"])} != set(reachable_indices):
            continue

        reachable_exits = [exit_spec for exit_spec in exits if bool(exit_spec["reachable"])]
        unreachable_exits = [exit_spec for exit_spec in exits if not bool(exit_spec["reachable"])]
        reachable_labels = [str(exit_spec["label"]) for exit_spec in reachable_exits]
        unreachable_labels = [str(exit_spec["label"]) for exit_spec in unreachable_exits]
        if bool(is_label_request) and str(resolved_target_reachability) == "reachable":
            answer_exit = reachable_exits[0]
            answer_value: str | int = str(answer_exit["label"])
            supporting_item_ids = [str(answer_exit["item_id"])]
            annotation_policy = "single_reachable_exit_bbox"
            query_details: Dict[str, Any] = {"target_reachability": str(resolved_target_reachability)}
        elif bool(is_label_request) and str(resolved_target_reachability) == "unreachable":
            answer_exit = unreachable_exits[0]
            answer_value = str(answer_exit["label"])
            supporting_item_ids = [str(answer_exit["item_id"])]
            annotation_policy = "single_unreachable_exit_bbox"
            query_details = {"target_reachability": str(resolved_target_reachability)}
        else:
            answer_value = int(len(reachable_exits))
            supporting_item_ids = [str(exit_spec["item_id"]) for exit_spec in sorted(reachable_exits, key=lambda item: str(item["label"]))]
            annotation_policy = "reachable_exit_bboxes_by_label"
            query_details = {"reachable_exit_total": int(answer_value)}
            reachable_count_range = locals().get("reachable_count_range", [1, 5])

        return {
            "target_reachability": str(resolved_target_reachability) if resolved_target_reachability is not None else None,
            "scene_variant": str(scene_variant),
            "request_kind": str(request_kind),
            "view_family": "topology_orthogonal_maze_exit_label",
            "topology_rule": "move_through_open_corridors_from_start_walls_block_motion",
            "maze_rows": int(rows),
            "maze_cols": int(cols),
            "maze_rows_range": [int(row_range[0]), int(row_range[1])],
            "maze_cols_range": [int(col_range[0]), int(col_range[1])],
            "start_cell": [int(start[0]), int(start[1])],
            "open_edges": [
                [[int(edge[0][0]), int(edge[0][1])], [int(edge[1][0]), int(edge[1][1])]]
                for edge in sorted(open_edges, key=lambda item: (item[0][1], item[0][0], item[1][1], item[1][0]))
            ],
            "exits": [dict(exit_spec) for exit_spec in exits],
            "exit_count": int(exit_count),
            "exit_count_range": [int(exit_count_range[0]), int(exit_count_range[1])],
            "reachable_exit_total": int(len(reachable_exits)),
            "reachable_exit_total_range": list(reachable_count_range) if str(request_kind) == "reachable_count" else [1, max(1, int(exit_count) - 1)],
            "reachable_exit_labels": list(reachable_labels),
            "unreachable_exit_labels": list(unreachable_labels),
            "answer_value": answer_value,
            "supporting_item_ids": list(supporting_item_ids),
            "annotation_policy": str(annotation_policy),
            "query_details": dict(query_details),
            "solver_trace": {
                "start_cell": [int(start[0]), int(start[1])],
                "reachable_exit_labels": list(reachable_labels),
                "unreachable_exit_labels": list(unreachable_labels),
                "target_reachability": str(resolved_target_reachability) if resolved_target_reachability is not None else None,
                "answer_value": answer_value,
                "supporting_item_ids": list(supporting_item_ids),
                "annotation_policy": str(annotation_policy),
                **dict(query_details),
            },
        }

    raise ValueError("failed to build a maze with enough boundary leaf exits")


def sample_exit_label_maze(
    *,
    target_reachability: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    generation_defaults: Mapping[str, Any],
    max_attempts: int,
) -> Dict[str, Any]:
    """Build a maze with exactly one target reachable/unreachable exit."""

    return build_maze_exit_dataset(
        request_kind="exit_label",
        target_reachability=str(target_reachability),
        scene_variant=str(scene_variant),
        params=params,
        instance_seed=int(instance_seed),
        generation_defaults=generation_defaults,
        max_attempts=int(max_attempts),
    )


def sample_reachable_exit_count_maze(
    *,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    generation_defaults: Mapping[str, Any],
    max_attempts: int,
) -> Dict[str, Any]:
    """Build a maze with a sampled number of reachable boundary exits."""

    return build_maze_exit_dataset(
        request_kind="reachable_count",
        target_reachability=None,
        scene_variant=str(scene_variant),
        params=params,
        instance_seed=int(instance_seed),
        generation_defaults=generation_defaults,
        max_attempts=int(max_attempts),
    )


__all__ = [
    "sample_exit_label_maze",
    "sample_reachable_exit_count_maze",
]
