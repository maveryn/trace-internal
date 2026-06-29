"""Sampling primitives for pipe-flow repair puzzles."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.sampling import integer_range_choice
from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default, resolve_required_int_bounds

from .defaults import DEFAULTS
from .rules import (
    block_cells,
    cell_add,
    connected_to_destination,
    direction_between,
    local_cells,
    localize_block,
    normalize_openings,
    option_connecting_rotation_turns,
    option_connects,
    option_signature,
    parse_grid_size_variant,
    path_openings,
    rotate_local_option,
    rotation_canonical_option_signature,
)
from .state import LABEL_POOL, Cell, Openings, OptionSpec, PipeFlowDataset, TileSpec


def find_path(
    rng,
    *,
    rows: int,
    cols: int,
    min_length: int,
    max_length: int,
) -> tuple[Cell, ...]:
    """Sample a simple start-marker-to-finish-flag path across the grid."""

    for _ in range(260):
        start = (int(rng.randrange(int(rows))), 0)
        goal = (int(rng.randrange(int(rows))), int(cols - 1))
        stack: list[tuple[Cell, list[Cell], set[Cell]]] = [(start, [start], {start})]
        step_limit = max(1, int(rows * cols * 8))
        while stack and step_limit > 0:
            step_limit -= 1
            cell, path, visited = stack.pop()
            if cell == goal and int(min_length) <= len(path) <= int(max_length):
                return tuple(path)
            if len(path) >= int(max_length):
                continue
            directions = ["N", "E", "S", "W"]
            rng.shuffle(directions)
            directions.sort(
                key=lambda direction: (
                    0
                    if direction == "E" and cell[1] < goal[1]
                    else (1 if direction in {"N", "S"} else 2)
                )
            )
            for direction in directions:
                nxt = cell_add(cell, direction)
                if not (0 <= nxt[0] < int(rows) and 0 <= nxt[1] < int(cols)):
                    continue
                if nxt in visited:
                    continue
                if nxt[1] < cell[1] - 1:
                    continue
                new_path = [*path, nxt]
                remaining_min = abs(int(goal[0] - nxt[0])) + abs(int(goal[1] - nxt[1]))
                if len(new_path) + remaining_min > int(max_length):
                    continue
                stack.append((nxt, new_path, {*visited, nxt}))
    raise RuntimeError("failed to sample pipe-flow path")


def select_missing_origin(
    path: tuple[Cell, ...],
    *,
    rows: int,
    cols: int,
    rng,
) -> Cell:
    """Choose an interior 2x2 block that a contiguous path segment crosses."""

    candidates: list[tuple[int, Cell]] = []
    indexed_path = {tuple(cell): index for index, cell in enumerate(path)}
    for row in range(1, max(1, int(rows) - 2)):
        for col in range(1, max(1, int(cols) - 2)):
            origin = (int(row), int(col))
            block = set(block_cells(origin))
            inside_indices = sorted(
                indexed_path[cell]
                for cell in block
                if cell in indexed_path
            )
            if len(inside_indices) < 2:
                continue
            if inside_indices[-1] - inside_indices[0] + 1 != len(inside_indices):
                continue
            if inside_indices[0] <= 0 or inside_indices[-1] >= len(path) - 1:
                continue
            if tuple(path[inside_indices[0] - 1]) in block:
                continue
            if tuple(path[inside_indices[-1] + 1]) in block:
                continue
            candidates.append((len(inside_indices), origin))
    if not candidates:
        raise RuntimeError("failed to choose a 2x2 pipe-flow missing block")
    max_inside = max(score for score, _origin in candidates)
    preferred = [origin for score, origin in candidates if int(score) == int(max_inside)]
    return tuple(preferred[int(rng.randrange(len(preferred)))])


def add_opening(openings_by_cell: dict[Cell, set[str]], left: Cell, right: Cell) -> None:
    """Add a bidirectional pipe connection between adjacent cells."""

    direction = direction_between(tuple(left), tuple(right))
    opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}
    openings_by_cell.setdefault(tuple(left), set()).add(direction)
    openings_by_cell.setdefault(tuple(right), set()).add(opposite[direction])


def is_boundary_cell(cell: Cell, *, rows: int, cols: int) -> bool:
    """Return whether a cell touches any grid side."""

    row, col = int(cell[0]), int(cell[1])
    return row == 0 or row == int(rows) - 1 or col == 0 or col == int(cols) - 1


def boundary_distance(cell: Cell, *, rows: int, cols: int) -> int:
    """Return Manhattan distance from a cell to the nearest grid side."""

    row, col = int(cell[0]), int(cell[1])
    return min(row, int(rows) - 1 - row, col, int(cols) - 1 - col)


def find_branch_path_to_side(
    *,
    anchor: Cell,
    occupied: set[Cell],
    rows: int,
    cols: int,
    min_length: int,
    max_length: int,
    rng,
) -> tuple[Cell, ...] | None:
    """Find an offshoot path from a main-path anchor to any grid side."""

    anchor = tuple(anchor)
    stack: list[tuple[Cell, list[Cell], set[Cell]]] = [(anchor, [], {anchor})]
    step_limit = max(1, int(rows * cols * 10))
    while stack and step_limit > 0:
        step_limit -= 1
        cell, branch_path, visited = stack.pop()
        if (
            branch_path
            and len(branch_path) >= int(min_length)
            and is_boundary_cell(branch_path[-1], rows=int(rows), cols=int(cols))
        ):
            return tuple(branch_path)
        if len(branch_path) >= int(max_length):
            continue
        directions = ["N", "E", "S", "W"]
        rng.shuffle(directions)
        directions.sort(
            key=lambda direction: boundary_distance(
                cell_add(cell, direction),
                rows=int(rows),
                cols=int(cols),
            )
        )
        for direction in directions:
            nxt = cell_add(cell, direction)
            if not (0 <= nxt[0] < int(rows) and 0 <= nxt[1] < int(cols)):
                continue
            if nxt in occupied or nxt in visited:
                continue
            stack.append((nxt, [*branch_path, nxt], {*visited, nxt}))
    return None


def add_branch_paths(
    openings_by_cell: dict[Cell, set[str]],
    *,
    path: tuple[Cell, ...],
    missing_cells: set[Cell],
    rows: int,
    cols: int,
    branch_count: int,
    branch_length_min: int,
    branch_length_max: int,
    rng,
) -> tuple[tuple[Cell, ...], tuple[Cell, ...]]:
    """Attach visible offshoots to the main path, ending each on a grid side."""

    occupied = {tuple(cell) for cell in path} | set(missing_cells)
    branch_cells: set[Cell] = set()
    branch_terminals: list[Cell] = []
    anchors = [tuple(cell) for cell in path[1:-1] if tuple(cell) not in missing_cells]
    for _ in range(max(0, int(branch_count))):
        rng.shuffle(anchors)
        started = False
        for anchor in anchors:
            max_length = max(int(branch_length_max), int(min(rows, cols) - 1))
            branch_path = find_branch_path_to_side(
                anchor=anchor,
                occupied=set(occupied),
                rows=int(rows),
                cols=int(cols),
                min_length=max(1, int(branch_length_min)),
                max_length=max(1, int(max_length)),
                rng=rng,
            )
            if not branch_path:
                continue
            prev = anchor
            for current in branch_path:
                current = tuple(current)
                if current in occupied:
                    break
                add_opening(openings_by_cell, tuple(prev), current)
                occupied.add(current)
                branch_cells.add(current)
                prev = current
            else:
                branch_terminals.append(tuple(branch_path[-1]))
                started = True
            break
        if not started:
            break
    return tuple(sorted(branch_cells)), tuple(branch_terminals)


def random_local_option(rng) -> dict[Cell, Openings]:
    """Build one internally consistent random 2x2 pipe option."""

    openings: dict[Cell, set[str]] = {cell: set() for cell in local_cells()}
    internal_edges = (
        ((0, 0), "E", (0, 1), "W"),
        ((1, 0), "E", (1, 1), "W"),
        ((0, 0), "S", (1, 0), "N"),
        ((0, 1), "S", (1, 1), "N"),
    )
    for left, left_dir, right, right_dir in internal_edges:
        if rng.random() < 0.46:
            openings[left].add(left_dir)
            openings[right].add(right_dir)
    boundary_stubs = (
        ((0, 0), "N"),
        ((0, 1), "N"),
        ((1, 0), "S"),
        ((1, 1), "S"),
        ((0, 0), "W"),
        ((1, 0), "W"),
        ((0, 1), "E"),
        ((1, 1), "E"),
    )
    stubs = list(boundary_stubs)
    rng.shuffle(stubs)
    for cell, direction in stubs[: int(rng.randint(2, 5))]:
        openings[cell].add(direction)
    if sum(1 for value in openings.values() if value) < 2:
        cell, direction = stubs[-1]
        openings[cell].add(direction)
    return {cell: normalize_openings(value) for cell, value in openings.items()}


def build_option_specs(
    *,
    correct_local_openings: Mapping[Cell, Openings],
    visible_map: Mapping[Cell, Openings],
    origin: Cell,
    rows: int,
    cols: int,
    start_cell: Cell,
    destination_cell: Cell,
    candidate_labels: tuple[str, ...],
    answer_label: str,
    rng,
) -> tuple[OptionSpec, ...]:
    """Create one rotatable correct option and distinct unsolvable distractors."""

    labels = tuple(str(label) for label in candidate_labels)
    if str(answer_label) not in set(labels):
        raise ValueError(f"answer_label {answer_label!r} outside candidate labels")
    answer_label_index = int(labels.index(str(answer_label)))
    correct_display_turns = int(rng.randrange(4))
    correct_display_openings = rotate_local_option(
        correct_local_openings,
        turns=correct_display_turns,
    )
    correct_signature = rotation_canonical_option_signature(correct_display_openings)
    correct_connecting_turns = option_connecting_rotation_turns(
        visible_map=visible_map,
        local_openings=correct_display_openings,
        origin=origin,
        rows=int(rows),
        cols=int(cols),
        start_cell=start_cell,
        destination_cell=destination_cell,
    )
    if not correct_connecting_turns:
        raise RuntimeError("displayed correct pipe-flow option is not solvable under rotation")

    distractors: list[dict[Cell, Openings]] = []
    seen = {correct_signature}

    def maybe_add(candidate: Mapping[Cell, Openings]) -> None:
        normalized = {
            cell: normalize_openings(candidate.get(cell, ()))
            for cell in local_cells()
        }
        signature = rotation_canonical_option_signature(normalized)
        if signature in seen:
            return
        if option_connecting_rotation_turns(
            visible_map=visible_map,
            local_openings=normalized,
            origin=origin,
            rows=int(rows),
            cols=int(cols),
            start_cell=start_cell,
            destination_cell=destination_cell,
        ):
            return
        seen.add(signature)
        distractors.append(normalized)

    for _ in range(1200):
        if len(distractors) >= len(labels) - 1:
            break
        maybe_add(random_local_option(rng))
    if len(distractors) < len(labels) - 1:
        raise RuntimeError("failed to build enough pipe-flow option distractors")

    options: list[OptionSpec] = []
    distractor_iter = iter(distractors)
    for option_index, label in enumerate(labels):
        is_correct = bool(option_index == int(answer_label_index))
        local_openings = (
            {
                cell: normalize_openings(correct_display_openings.get(cell, ()))
                for cell in local_cells()
            }
            if is_correct
            else next(distractor_iter)
        )
        connecting_turns = (
            correct_connecting_turns
            if is_correct
            else option_connecting_rotation_turns(
                visible_map=visible_map,
                local_openings=local_openings,
                origin=origin,
                rows=int(rows),
                cols=int(cols),
                start_cell=start_cell,
                destination_cell=destination_cell,
            )
        )
        if bool(is_correct) != bool(connecting_turns):
            raise RuntimeError("pipe-flow option uniqueness check failed")
        options.append(
            OptionSpec(
                option_id=f"option_panel_{int(option_index + 1)}",
                label=str(label),
                local_openings=option_signature(local_openings),
                is_correct=is_correct,
                connects_after_rotation_turns=tuple(int(value) for value in connecting_turns),
                display_rotation_turns=int(correct_display_turns if is_correct else 0),
            )
        )
    return tuple(options)


def sample_pipe_flow_dataset(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    grid_size_variant: str,
    scene_variant: str,
    candidate_count: int,
    answer_label: str,
) -> PipeFlowDataset:
    """Sample a complete pipe-flow scene with one unique rotatable repair option."""

    rows, cols = parse_grid_size_variant(str(grid_size_variant))
    path_min, path_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="path_length_min",
        max_key="path_length_max",
        fallback_min=DEFAULTS.path_length_min,
        fallback_max=DEFAULTS.path_length_max,
        context="pipe_flow path length",
    )
    branch_min, branch_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="branch_count_min",
        max_key="branch_count_max",
        fallback_min=DEFAULTS.branch_count_min,
        fallback_max=DEFAULTS.branch_count_max,
        context="pipe_flow branch count",
    )
    branch_length_min, branch_length_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="branch_length_min",
        max_key="branch_length_max",
        fallback_min=DEFAULTS.branch_length_min,
        fallback_max=DEFAULTS.branch_length_max,
        context="pipe_flow branch length",
    )
    labels = tuple(LABEL_POOL[index] for index in range(int(candidate_count)))
    if str(answer_label) not in set(labels):
        raise ValueError(f"answer_label {answer_label!r} outside candidate labels")
    rng = spawn_rng(int(instance_seed), "puzzles.pipe_flow.dataset")

    for _ in range(180):
        path = find_path(
            rng,
            rows=int(rows),
            cols=int(cols),
            min_length=max(8, int(path_min)),
            max_length=min(int(rows * cols), int(path_max)),
        )
        if len(path) < 8:
            continue
        try:
            missing_origin = select_missing_origin(path, rows=int(rows), cols=int(cols), rng=rng)
        except RuntimeError:
            continue
        missing_cells = set(block_cells(missing_origin))
        path_opening_map = path_openings(tuple(path))
        full_openings: dict[Cell, set[str]] = {
            tuple(cell): set(openings)
            for cell, openings in path_opening_map.items()
        }
        branch_count, _branch_count_probabilities = integer_range_choice(
            rng,
            int(branch_min),
            int(branch_max),
            weights=group_default(gen_defaults, "branch_count_weights", None),
        )
        branch_cells, branch_terminal_cells = add_branch_paths(
            full_openings,
            path=tuple(path),
            missing_cells=set(missing_cells),
            rows=int(rows),
            cols=int(cols),
            branch_count=int(branch_count),
            branch_length_min=int(branch_length_min),
            branch_length_max=int(branch_length_max),
            rng=rng,
        )
        if len(branch_terminal_cells) < max(1, min(int(branch_count), int(branch_min))):
            continue
        full_map: dict[Cell, Openings] = {
            tuple(cell): normalize_openings(openings)
            for cell, openings in full_openings.items()
            if openings
        }
        visible_map = {
            tuple(cell): tuple(openings)
            for cell, openings in full_map.items()
            if tuple(cell) not in missing_cells
        }
        if connected_to_destination(
            visible_map,
            rows=rows,
            cols=cols,
            start_cell=path[0],
            destination_cell=path[-1],
        ):
            continue
        correct_local_openings = localize_block(full_map, origin=missing_origin)
        if not option_connects(
            visible_map=visible_map,
            local_openings=correct_local_openings,
            origin=missing_origin,
            rows=int(rows),
            cols=int(cols),
            start_cell=path[0],
            destination_cell=path[-1],
        ):
            continue
        try:
            options = build_option_specs(
                correct_local_openings=correct_local_openings,
                visible_map=visible_map,
                origin=missing_origin,
                rows=int(rows),
                cols=int(cols),
                start_cell=path[0],
                destination_cell=path[-1],
                candidate_labels=labels,
                answer_label=str(answer_label),
                rng=rng,
            )
        except RuntimeError:
            continue

        path_set = set(path)
        branch_set = set(branch_cells)
        tiles = tuple(
            TileSpec(
                tile_id=f"tile_r{cell[0]}c{cell[1]}",
                row=int(cell[0]),
                col=int(cell[1]),
                required_openings=tuple(path_opening_map.get(cell, tuple())),
                current_openings=tuple(visible_map[cell]),
                is_path=bool(cell in path_set),
                is_branch=bool(cell in branch_set),
                label="",
            )
            for cell in sorted(visible_map)
        )
        correct_option = next(option for option in options if option.is_correct)
        return PipeFlowDataset(
            rows=int(rows),
            cols=int(cols),
            grid_size_variant=str(grid_size_variant),
            scene_variant=str(scene_variant),
            path_cells=tuple(path),
            branch_cells=tuple(branch_cells),
            branch_terminal_cells=tuple(branch_terminal_cells),
            start_cell=tuple(path[0]),
            destination_cell=tuple(path[-1]),
            missing_origin=tuple(missing_origin),
            missing_cells=tuple(sorted(missing_cells)),
            missing_region_id="missing_region",
            correct_option_panel_id=str(correct_option.option_id),
            answer_label=str(answer_label),
            candidate_count=int(candidate_count),
            tiles=tiles,
            options=tuple(options),
        )
    raise RuntimeError("failed to construct unique pipe-flow option puzzle")
