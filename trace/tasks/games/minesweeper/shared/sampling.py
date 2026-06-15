"""Identity-free Minesweeper board construction primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.style import SUPPORTED_MINESWEEPER_STYLE_VARIANTS

from .defaults import DEFAULTS, REVEAL_OUTCOME_BY_CODE, REVEAL_OUTCOME_LABELS, REVEAL_OUTCOME_VOCAB, SCENE_VARIANTS
from .rules import (
    adjacent_flag_count,
    clue_context_flags,
    clue_number,
    forced_mine_supports,
    forced_safe_supports,
    neighbor_coords,
    satisfied_clue_coords,
    unsatisfied_clue_coords,
    validate_board_contract,
)
from .state import Coord, MinesweeperSample, all_coords, sorted_coords


@dataclass(frozen=True)
class MinesweeperAxes:
    """Resolved semantic and visual axes for one Minesweeper sample."""

    scene_variant: str
    style_variant: str
    board_size: int
    target_answer: int | None
    target_answer_support: Tuple[int, ...]
    branch_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    board_size_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    option_count: int = 0
    option_count_support: Tuple[int, ...] = tuple()
    option_count_probabilities: Dict[str, float] | None = None


def _resolve_named_axis(
    *,
    gen_defaults: Mapping[str, Any],
    namespace_root: str,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named Minesweeper generation/render axis."""

    return resolve_games_named_axis(
        task_id=str(namespace_root),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=f"{namespace_root}.{namespace}",
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=supported,
    )


def resolve_minesweeper_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    branch_probabilities: Mapping[str, float],
    board_size_support_key: str,
    board_size_fallback_support: Sequence[int],
    target_support_key: str,
    target_fallback_support: Sequence[int],
    option_count_support_key: str = "option_count_support",
    option_count_fallback_support: Sequence[int] = (),
) -> MinesweeperAxes:
    """Resolve common scene/style/board/target axes without public task routing."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_MINESWEEPER_STYLE_VARIANTS,
    )
    board_size, board_size_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(board_size_support_key),
        explicit_key="board_size",
        fallback_support=tuple(int(value) for value in board_size_fallback_support),
        namespace=f"{namespace}.board_size.{str(board_size_support_key)}",
        balanced_flag_key="balanced_board_size_sampling",
        namespace_support_permutation=True,
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=tuple(int(value) for value in target_fallback_support),
        namespace=f"{namespace}.target_answer.{str(target_support_key)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key=str(target_support_key),
        fallback=tuple(int(value) for value in target_fallback_support),
    )
    option_count = 0
    option_count_support: Tuple[int, ...] = tuple()
    option_count_probabilities: Dict[str, float] = {}
    if option_count_fallback_support:
        option_count, option_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            support_key=str(option_count_support_key),
            explicit_key="option_count",
            fallback_support=tuple(int(value) for value in option_count_fallback_support),
            namespace=f"{namespace}.option_count",
            balanced_flag_key="balanced_option_count_sampling",
            namespace_support_permutation=True,
        )
        option_count_support = resolve_integer_support(
            params,
            gen_defaults=gen_defaults,
            key=str(option_count_support_key),
            fallback=tuple(int(value) for value in option_count_fallback_support),
        )
    return MinesweeperAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        board_size=int(board_size),
        target_answer=None if target_answer is None else int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        branch_probabilities=dict(branch_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        board_size_probabilities=dict(board_size_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        option_count=int(option_count),
        option_count_support=tuple(int(value) for value in option_count_support),
        option_count_probabilities=dict(option_count_probabilities),
    )


def _distractor_bounds(scene_variant: str) -> Tuple[int, int]:
    """Return hidden-distractor count bounds for one scene variant."""

    if str(scene_variant) == "mixed_grid":
        return int(DEFAULTS.mixed_min_distractor_hidden_count), int(DEFAULTS.mixed_max_distractor_hidden_count)
    return int(DEFAULTS.open_min_distractor_hidden_count), int(DEFAULTS.open_max_distractor_hidden_count)


def _choose_distractors(
    *,
    rng,
    size: int,
    clue_cell: Coord,
    occupied: set[Coord],
    scene_variant: str,
) -> Tuple[Coord, ...]:
    """Choose non-local hidden distractor cells away from the forcing clue."""

    local = set(neighbor_coords(clue_cell, size=int(size)))
    local.add(clue_cell)
    candidates = [coord for coord in all_coords(size=int(size)) if coord not in occupied and coord not in local]
    rng.shuffle(candidates)
    low, high = _distractor_bounds(str(scene_variant))
    count = int(rng.randint(min(int(low), len(candidates)), min(int(high), len(candidates)))) if candidates else 0
    return tuple(sorted(candidates[:count]))


def _chebyshev_distance(a: Coord, b: Coord) -> int:
    """Return grid Chebyshev distance between two coordinates."""

    return max(abs(int(a[0]) - int(b[0])), abs(int(a[1]) - int(b[1])))


def _build_state(
    *,
    size: int,
    mine_coords: set[Coord],
    flagged_coords: set[Coord],
    hidden_coords: set[Coord],
) -> Tuple[Tuple[Coord, ...], Tuple[Coord, ...], Tuple[Coord, ...], Tuple[Coord, ...]]:
    """Return canonical mine/revealed/flagged/hidden partitions."""

    revealed_coords = set(all_coords(size=int(size))) - set(hidden_coords) - set(flagged_coords)
    validate_board_contract(
        size=int(size),
        mine_coords=tuple(mine_coords),
        revealed_coords=tuple(revealed_coords),
        flagged_coords=tuple(flagged_coords),
        hidden_coords=tuple(hidden_coords),
    )
    return (
        sorted_coords(mine_coords),
        sorted_coords(revealed_coords),
        sorted_coords(flagged_coords),
        sorted_coords(hidden_coords),
    )


def _supporting_clues(
    *,
    forced_cells: Tuple[Coord, ...],
    support_map: Mapping[Coord, Tuple[Coord, ...]],
) -> Tuple[Coord, ...]:
    """Return clue witnesses for a homogeneous forced-cell set."""

    clue_coords: set[Coord] = set()
    for coord in forced_cells:
        clue_coords.update(support_map.get(coord, ()))
    return sorted_coords(clue_coords)


def sample_forced_cell_scene(
    *,
    rng,
    axes: MinesweeperAxes,
    force_kind: str,
    target_count: int,
) -> MinesweeperSample:
    """Construct one board around a local forced mine-or-safe clue."""

    size = int(axes.board_size)
    interior = [(row, col) for row in range(1, size - 1) for col in range(1, size - 1)]
    clue_cell = tuple(rng.choice(interior))
    neighbors = list(neighbor_coords(clue_cell, size=int(size)))
    rng.shuffle(neighbors)
    hidden_targets = set(tuple(coord) for coord in neighbors[: int(target_count)])
    remaining_neighbors = [coord for coord in neighbors if coord not in hidden_targets]
    if str(force_kind) == "safe":
        flag_count = int(rng.randint(1, max(1, min(3, len(remaining_neighbors)))))
    else:
        max_flags = min(2, len(remaining_neighbors))
        flag_count = int(rng.randint(0, max_flags)) if max_flags > 0 else 0
    flagged_coords = set(tuple(coord) for coord in remaining_neighbors[: int(flag_count)])
    occupied = set(hidden_targets) | set(flagged_coords) | {clue_cell}
    distractors = set(
        _choose_distractors(
            rng=rng,
            size=int(size),
            clue_cell=clue_cell,
            occupied=occupied,
            scene_variant=str(axes.scene_variant),
        )
    )
    hidden_coords = set(hidden_targets) | set(distractors)
    if str(force_kind) == "mine":
        mine_coords = set(hidden_targets) | set(flagged_coords)
    elif str(force_kind) == "safe":
        mine_coords = set(distractors) | set(flagged_coords)
    else:
        raise ValueError(f"unsupported Minesweeper force kind: {force_kind}")
    mine_coords_tuple, revealed_coords, flagged_coords_tuple, hidden_coords_tuple = _build_state(
        size=int(size),
        mine_coords=mine_coords,
        flagged_coords=set(flagged_coords),
        hidden_coords=hidden_coords,
    )
    mine_support = forced_mine_supports(
        size=int(size),
        mine_coords=mine_coords_tuple,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords_tuple,
        hidden_coords=hidden_coords_tuple,
    )
    safe_support = forced_safe_supports(
        size=int(size),
        mine_coords=mine_coords_tuple,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords_tuple,
        hidden_coords=hidden_coords_tuple,
    )
    if str(force_kind) == "mine":
        forced = sorted_coords(mine_support.keys())
        support_map = mine_support
    else:
        forced = sorted_coords(safe_support.keys())
        support_map = safe_support
    if set(forced) != set(hidden_targets):
        raise ValueError("constructed Minesweeper forced-cell count does not match target")
    satisfied = satisfied_clue_coords(
        size=int(size),
        mine_coords=mine_coords_tuple,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords_tuple,
    )
    unsatisfied = unsatisfied_clue_coords(
        size=int(size),
        mine_coords=mine_coords_tuple,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords_tuple,
    )
    return MinesweeperSample(
        size=int(size),
        answer=int(len(forced)),
        mine_coords=tuple(mine_coords_tuple),
        revealed_coords=tuple(revealed_coords),
        flagged_coords=tuple(flagged_coords_tuple),
        hidden_coords=tuple(hidden_coords_tuple),
        forced_mine_coords=sorted_coords(mine_support.keys()),
        forced_safe_coords=sorted_coords(safe_support.keys()),
        satisfied_clue_coords=tuple(satisfied),
        unsatisfied_clue_coords=tuple(unsatisfied),
        forcing_clue_coords=_supporting_clues(forced_cells=tuple(forced), support_map=support_map),
        annotation_coords=tuple(forced),
        target_answer=int(target_count),
        distractor_hidden_count=len(distractors),
        construction_mode=f"local_forced_{str(force_kind)}_cells",
    )


def sample_remaining_adjacent_mine_scene(*, rng, axes: MinesweeperAxes, target_count: int) -> MinesweeperSample:
    """Construct one board asking for remaining adjacent mines around one clue."""

    size = int(axes.board_size)
    target = int(target_count)
    if target < 0 or target > 5:
        raise ValueError(f"unsupported remaining adjacent mine target count: {target}")
    interior = [(row, col) for row in range(1, size - 1) for col in range(1, size - 1)]
    if not interior:
        raise ValueError("remaining adjacent mine count requires an interior clue cell")
    for _attempt in range(256):
        clue_cell = tuple(rng.choice(interior))
        neighbors = list(neighbor_coords(clue_cell, size=int(size)))
        rng.shuffle(neighbors)
        if int(target) == 0:
            max_flags = min(4, len(neighbors) - 1)
            if max_flags < 1:
                continue
            flag_count = int(rng.randint(1, max_flags))
            max_hidden_safe = min(4, len(neighbors) - int(flag_count))
            if max_hidden_safe < 1:
                continue
            hidden_safe_count = int(rng.randint(1, max_hidden_safe))
        else:
            max_flags = min(3, len(neighbors) - int(target) - 1)
            if max_flags < 0:
                continue
            flag_count = int(rng.randint(0, max_flags))
            max_extra_safe = min(3, len(neighbors) - int(flag_count) - int(target))
            if max_extra_safe < 1:
                continue
            hidden_safe_count = int(rng.randint(1, max_extra_safe))
        flagged_coords = set(tuple(coord) for coord in neighbors[:flag_count])
        hidden_mines = set(tuple(coord) for coord in neighbors[flag_count : flag_count + int(target)])
        hidden_safe_start = int(flag_count) + int(target)
        hidden_safe = set(tuple(coord) for coord in neighbors[hidden_safe_start : hidden_safe_start + int(hidden_safe_count)])
        occupied = set(flagged_coords) | set(hidden_mines) | set(hidden_safe) | {clue_cell}
        distractors = set(
            _choose_distractors(
                rng=rng,
                size=int(size),
                clue_cell=clue_cell,
                occupied=occupied,
                scene_variant=str(axes.scene_variant),
            )
        )
        mine_coords, revealed_coords, flagged_coords_tuple, hidden_coords_tuple = _build_state(
            size=int(size),
            mine_coords=set(flagged_coords) | set(hidden_mines),
            flagged_coords=set(flagged_coords),
            hidden_coords=set(hidden_mines) | set(hidden_safe) | set(distractors),
        )
        clue = clue_number(clue_cell, mine_coords=mine_coords, size=int(size))
        flags = adjacent_flag_count(clue_cell, flagged_coords=flagged_coords_tuple, size=int(size))
        if int(clue) <= 0 or int(clue) - int(flags) != int(target):
            continue
        mine_support = forced_mine_supports(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
            hidden_coords=hidden_coords_tuple,
        )
        safe_support = forced_safe_supports(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
            hidden_coords=hidden_coords_tuple,
        )
        satisfied = satisfied_clue_coords(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
        )
        unsatisfied = unsatisfied_clue_coords(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
        )
        return MinesweeperSample(
            size=int(size),
            answer=int(target),
            mine_coords=tuple(mine_coords),
            revealed_coords=tuple(revealed_coords),
            flagged_coords=tuple(flagged_coords_tuple),
            hidden_coords=tuple(hidden_coords_tuple),
            forced_mine_coords=sorted_coords(mine_support.keys()),
            forced_safe_coords=sorted_coords(safe_support.keys()),
            satisfied_clue_coords=tuple(satisfied),
            unsatisfied_clue_coords=tuple(unsatisfied),
            forcing_clue_coords=(clue_cell,),
            annotation_coords=(clue_cell,),
            target_answer=int(target),
            distractor_hidden_count=len(distractors),
            construction_mode="marked_number_remaining_adjacent_mines",
        )
    raise ValueError("failed to construct Minesweeper remaining-adjacent-mine board")


def sample_satisfied_number_scene(*, rng, axes: MinesweeperAxes, target_count: int) -> MinesweeperSample:
    """Construct a board with exact-count satisfied and unsatisfied opened numbers."""

    size = int(axes.board_size)
    target = int(target_count)
    if target < 1 or target > 8:
        raise ValueError(f"unsupported satisfied number target count: {target}")
    for _attempt in range(512):
        all_cells = list(all_coords(size=int(size)))
        if target >= 3 and rng.random() < 0.65:
            first = tuple(rng.choice(all_cells))
            pair_candidates = [
                coord
                for coord in neighbor_coords(first, size=int(size))
                if abs(int(coord[0]) - int(first[0])) + abs(int(coord[1]) - int(first[1])) == 1
            ]
            if not pair_candidates:
                continue
            flagged_seed = {first, tuple(rng.choice(pair_candidates))}
        else:
            flagged_seed = {tuple(rng.choice(all_cells))}
        target_pool: set[Coord] = set()
        for flag_cell in flagged_seed:
            target_pool.update(neighbor_coords(flag_cell, size=int(size)))
        target_pool -= set(flagged_seed)
        if len(target_pool) < target:
            continue
        shuffled_target_pool = list(sorted_coords(target_pool))
        rng.shuffle(shuffled_target_pool)
        visible_satisfied = set(shuffled_target_pool[:target])
        hidden_local_safe = set(shuffled_target_pool[target:])
        blocked = set(flagged_seed) | set(target_pool)
        unflagged_region_candidates = [
            coord
            for coord in all_cells
            if coord not in blocked and all(_chebyshev_distance(coord, flag_cell) >= 3 for flag_cell in flagged_seed)
        ]
        unflagged_pair_candidates = [
            (a, b)
            for index, a in enumerate(unflagged_region_candidates)
            for b in unflagged_region_candidates[index + 1 :]
            if _chebyshev_distance(a, b) == 1
        ]
        if not unflagged_pair_candidates:
            continue
        unflagged_mines = set(rng.choice(unflagged_pair_candidates))
        occupied = set(blocked) | set(unflagged_mines)
        distractor_candidates = [
            coord
            for coord in all_cells
            if coord not in occupied and all(_chebyshev_distance(coord, mine_cell) >= 2 for mine_cell in unflagged_mines)
        ]
        rng.shuffle(distractor_candidates)
        low, high = _distractor_bounds(str(axes.scene_variant))
        remote_count = (
            int(rng.randint(min(int(low), len(distractor_candidates)), min(int(high), len(distractor_candidates))))
            if distractor_candidates
            else 0
        )
        remote_hidden_safe = set(distractor_candidates[:remote_count])
        mine_coords, revealed_coords, flagged_coords_tuple, hidden_coords_tuple = _build_state(
            size=int(size),
            mine_coords=set(flagged_seed) | set(unflagged_mines),
            flagged_coords=set(flagged_seed),
            hidden_coords=set(hidden_local_safe) | set(remote_hidden_safe) | set(unflagged_mines),
        )
        mine_support = forced_mine_supports(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
            hidden_coords=hidden_coords_tuple,
        )
        safe_support = forced_safe_supports(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
            hidden_coords=hidden_coords_tuple,
        )
        satisfied = satisfied_clue_coords(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
        )
        unsatisfied = unsatisfied_clue_coords(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
        )
        if set(satisfied) != set(visible_satisfied):
            continue
        if len(unsatisfied) < max(2, min(4, int(target))):
            continue
        if not any(
            clue_number(coord, mine_coords=mine_coords, size=int(size)) >= 2
            and adjacent_flag_count(coord, flagged_coords=flagged_coords_tuple, size=int(size)) == 0
            for coord in unsatisfied
        ):
            continue
        return MinesweeperSample(
            size=int(size),
            answer=int(len(satisfied)),
            mine_coords=tuple(mine_coords),
            revealed_coords=tuple(revealed_coords),
            flagged_coords=tuple(flagged_coords_tuple),
            hidden_coords=tuple(hidden_coords_tuple),
            forced_mine_coords=sorted_coords(mine_support.keys()),
            forced_safe_coords=sorted_coords(safe_support.keys()),
            satisfied_clue_coords=tuple(satisfied),
            unsatisfied_clue_coords=tuple(unsatisfied),
            forcing_clue_coords=tuple(satisfied),
            annotation_coords=tuple(satisfied),
            target_answer=int(target),
            distractor_hidden_count=len(remote_hidden_safe),
            construction_mode="exact_satisfied_numbers_with_unsatisfied_distractors",
        )
    raise ValueError("failed to construct Minesweeper satisfied-number board")


def reveal_outcome_for_code(code: int) -> str:
    """Return the visible reveal-outcome label for one balanced outcome code."""

    try:
        return str(REVEAL_OUTCOME_BY_CODE[int(code)])
    except KeyError as exc:
        raise ValueError(f"unsupported reveal outcome code: {code}") from exc


def sample_reveal_outcome_options(*, rng, outcome: str, option_count: int) -> Tuple[Tuple[str, str], ...]:
    """Return labeled image options containing the correct reveal outcome."""

    labels = tuple(str(label) for label in REVEAL_OUTCOME_LABELS[: int(option_count)])
    if len(labels) < 2:
        raise ValueError("Minesweeper reveal-outcome option count must be at least 2")
    distractors = [str(value) for value in REVEAL_OUTCOME_VOCAB if str(value) != str(outcome)]
    rng.shuffle(distractors)
    option_values = [str(outcome), *distractors[: max(0, len(labels) - 1)]]
    rng.shuffle(option_values)
    return tuple((str(label), str(value)) for label, value in zip(labels, option_values))


def _remote_hidden_distractors(
    *,
    rng,
    size: int,
    target_cell: Coord,
    support_clue: Coord,
    occupied: set[Coord],
    scene_variant: str,
) -> set[Coord]:
    """Choose hidden distractors away from the target and its supporting clue."""

    support_neighbors = set(neighbor_coords(support_clue, size=int(size)))
    target_neighbors = set(neighbor_coords(target_cell, size=int(size)))
    candidates = [
        coord
        for coord in all_coords(size=int(size))
        if coord not in occupied
        and coord != support_clue
        and coord not in support_neighbors
        and coord not in target_neighbors
        and _chebyshev_distance(coord, target_cell) >= 2
    ]
    rng.shuffle(candidates)
    low, high = _distractor_bounds(str(scene_variant))
    if not candidates:
        return set()
    count = int(rng.randint(min(int(low), len(candidates)), min(int(high), len(candidates))))
    return set(tuple(coord) for coord in candidates[:count])


def sample_reveal_cell_scene(
    *,
    rng,
    axes: MinesweeperAxes,
    target_code: int,
    option_count: int,
) -> MinesweeperSample:
    """Construct one board asking what a marked hidden cell would reveal."""

    size = int(axes.board_size)
    outcome = reveal_outcome_for_code(int(target_code))
    target_cells = list(all_coords(size=int(size)))
    rng.shuffle(target_cells)
    for target_cell in target_cells:
        target_neighbors = list(neighbor_coords(target_cell, size=int(size)))
        if str(outcome).isdigit() and len(target_neighbors) < int(outcome) + 1:
            continue
        for _attempt in range(96):
            rng.shuffle(target_neighbors)
            flagged_coords: set[Coord] = set()
            mine_coords: set[Coord] = set()
            if str(outcome) == "mine":
                support_clue = tuple(rng.choice(target_neighbors))
                support_candidates = [coord for coord in neighbor_coords(support_clue, size=int(size)) if coord != target_cell]
                rng.shuffle(support_candidates)
                support_flag_count = int(rng.randint(0, min(2, len(support_candidates)))) if support_candidates else 0
                flagged_coords = set(tuple(coord) for coord in support_candidates[:support_flag_count])
                mine_coords = {target_cell} | set(flagged_coords)
            else:
                reveal_count = 0 if str(outcome) == "empty" else int(outcome)
                if reveal_count == 0:
                    possible_supports = list(target_neighbors)
                    rng.shuffle(possible_supports)
                    support_clue = None
                    support_only_flag = None
                    for candidate in possible_supports:
                        support_only_flags = [
                            coord
                            for coord in neighbor_coords(candidate, size=int(size))
                            if coord != target_cell and coord not in set(target_neighbors)
                        ]
                        rng.shuffle(support_only_flags)
                        if support_only_flags:
                            support_clue = tuple(candidate)
                            support_only_flag = tuple(support_only_flags[0])
                            break
                    if support_clue is None or support_only_flag is None:
                        continue
                    flagged_coords = {support_only_flag}
                else:
                    if len(target_neighbors) < reveal_count + 1:
                        continue
                    support_clue = tuple(rng.choice(target_neighbors))
                    flag_candidates = [coord for coord in target_neighbors if coord != support_clue]
                    rng.shuffle(flag_candidates)
                    flagged_coords = set(tuple(coord) for coord in flag_candidates[:reveal_count])
                    if len(flagged_coords) != reveal_count:
                        continue
                    support_adjacent_flags = set(neighbor_coords(support_clue, size=int(size))) & set(flagged_coords)
                    if not support_adjacent_flags:
                        continue
                mine_coords = set(flagged_coords)
            occupied = {target_cell, support_clue} | set(flagged_coords) | set(mine_coords)
            distractors = _remote_hidden_distractors(
                rng=rng,
                size=int(size),
                target_cell=target_cell,
                support_clue=support_clue,
                occupied=occupied,
                scene_variant=str(axes.scene_variant),
            )
            hidden_coords = {target_cell} | set(distractors)
            mine_coords_tuple, revealed_coords, flagged_coords_tuple, hidden_coords_tuple = _build_state(
                size=int(size),
                mine_coords=set(mine_coords),
                flagged_coords=set(flagged_coords),
                hidden_coords=set(hidden_coords),
            )
            mine_support = forced_mine_supports(
                size=int(size),
                mine_coords=mine_coords_tuple,
                revealed_coords=revealed_coords,
                flagged_coords=flagged_coords_tuple,
                hidden_coords=hidden_coords_tuple,
            )
            safe_support = forced_safe_supports(
                size=int(size),
                mine_coords=mine_coords_tuple,
                revealed_coords=revealed_coords,
                flagged_coords=flagged_coords_tuple,
                hidden_coords=hidden_coords_tuple,
            )
            if str(outcome) == "mine":
                if target_cell not in mine_support:
                    continue
                supporting_clues = tuple(mine_support[target_cell])
            else:
                if target_cell not in safe_support:
                    continue
                actual_count = clue_number(target_cell, mine_coords=mine_coords_tuple, size=int(size))
                expected_count = 0 if str(outcome) == "empty" else int(outcome)
                if int(actual_count) != int(expected_count):
                    continue
                supporting_clues = tuple(safe_support[target_cell])
            target_neighbor_flags = set(neighbor_coords(target_cell, size=int(size))) & set(flagged_coords_tuple)
            context_flags = set(clue_context_flags(clue_coords=supporting_clues, flagged_coords=flagged_coords_tuple, size=int(size)))
            supporting_flags = sorted_coords(set(context_flags) | set(target_neighbor_flags))
            satisfied = satisfied_clue_coords(
                size=int(size),
                mine_coords=mine_coords_tuple,
                revealed_coords=revealed_coords,
                flagged_coords=flagged_coords_tuple,
            )
            unsatisfied = unsatisfied_clue_coords(
                size=int(size),
                mine_coords=mine_coords_tuple,
                revealed_coords=revealed_coords,
                flagged_coords=flagged_coords_tuple,
            )
            options = sample_reveal_outcome_options(rng=rng, outcome=str(outcome), option_count=int(option_count))
            answer_label = next(label for label, value in options if str(value) == str(outcome))
            annotation_coords = sorted_coords((target_cell, *supporting_clues, *supporting_flags))
            return MinesweeperSample(
                size=int(size),
                answer=str(answer_label),
                mine_coords=tuple(mine_coords_tuple),
                revealed_coords=tuple(revealed_coords),
                flagged_coords=tuple(flagged_coords_tuple),
                hidden_coords=tuple(hidden_coords_tuple),
                forced_mine_coords=sorted_coords(mine_support.keys()),
                forced_safe_coords=sorted_coords(safe_support.keys()),
                satisfied_clue_coords=tuple(satisfied),
                unsatisfied_clue_coords=tuple(unsatisfied),
                forcing_clue_coords=tuple(supporting_clues),
                annotation_coords=tuple(annotation_coords),
                target_answer=int(target_code),
                distractor_hidden_count=len(distractors),
                construction_mode=f"marked_hidden_cell_reveals_{str(outcome)}",
                target_cell_coord=target_cell,
                supporting_clue_coords=tuple(supporting_clues),
                supporting_flag_coords=tuple(supporting_flags),
                reveal_outcome=str(outcome),
                answer_options=tuple(options),
            )
    raise ValueError("failed to construct Minesweeper reveal-outcome board")


__all__ = [
    "MinesweeperAxes",
    "resolve_minesweeper_axes",
    "reveal_outcome_for_code",
    "sample_forced_cell_scene",
    "sample_remaining_adjacent_mine_scene",
    "sample_reveal_cell_scene",
    "sample_reveal_outcome_options",
    "sample_satisfied_number_scene",
]
