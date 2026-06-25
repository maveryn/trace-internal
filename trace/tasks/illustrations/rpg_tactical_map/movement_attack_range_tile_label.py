"""Select a tile attackable after tactical RPG movement."""

from __future__ import annotations

import random
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.scene_config import get_scene_defaults
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    group_default,
    split_scene_generation_rendering_prompt_defaults,
)

from ._lifecycle import (
    RpgTacticalMapOptionAttempt,
    RpgTacticalMapOptionPlan,
    run_rpg_tactical_map_option_lifecycle,
)
from .shared.output import movement_attack_range_render_map
from .shared.prompts import rpg_tactical_map_terrain_rules_text
from .shared.relations import (
    TERRAIN_MOVEMENT_COSTS,
    TERRAIN_WATER,
    shortest_movement_costs,
)
from .shared.rendering import DEFAULT_CANDIDATE_LABELS, SCENE_ID
from .shared.sampling import select_int_from_support
from .shared.state import RpgTacticalMapScene, RpgTacticalTile


TASK_ID = "task_illustrations__rpg_tactical_map__movement_attack_range_tile_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "movement_attack_range_tile"
DEFAULT_MOVEMENT_BUDGET_SUPPORT: tuple[int, ...] = (3, 4, 5)
DEFAULT_ATTACK_RANGE_SUPPORT: tuple[int, ...] = (1, 2)
DEFAULT_CANDIDATE_COUNT = 4

_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _tiles_by_coord(scene: RpgTacticalMapScene) -> dict[tuple[int, int], RpgTacticalTile]:
    return {(int(tile.row), int(tile.col)): tile for tile in scene.tiles}


def _tile_by_id(scene: RpgTacticalMapScene) -> dict[str, RpgTacticalTile]:
    return {str(tile.tile_id): tile for tile in scene.tiles}


def _tile_manhattan(first: RpgTacticalTile, second: RpgTacticalTile) -> int:
    return abs(int(first.row) - int(second.row)) + abs(int(first.col) - int(second.col))


def _cardinal_distance(first: RpgTacticalTile, second: RpgTacticalTile) -> int | None:
    if int(first.row) == int(second.row) and int(first.col) != int(second.col):
        return abs(int(first.col) - int(second.col))
    if int(first.col) == int(second.col) and int(first.row) != int(second.row):
        return abs(int(first.row) - int(second.row))
    return None


def _direction_bucket(origin: RpgTacticalTile, tile: RpgTacticalTile) -> str:
    drow = int(tile.row) - int(origin.row)
    dcol = int(tile.col) - int(origin.col)
    row_part = "s" if drow > 0 else "n" if drow < 0 else ""
    col_part = "e" if dcol > 0 else "w" if dcol < 0 else ""
    return f"{row_part}{col_part}" or "same"


def _reachable_and_attackable_tiles(
    *,
    scene: RpgTacticalMapScene,
    movement_budget: int,
    attack_range: int,
) -> tuple[dict[str, int], str, list[str], list[str], dict[str, list[str]]]:
    """Return movement positions and target tiles attackable in cardinal range."""

    if not scene.units:
        raise ValueError("attack range task requires a blue unit")
    tiles_by_id = _tile_by_id(scene)
    tiles_by_coord = _tiles_by_coord(scene)
    start_tile_id = str(scene.units[0].tile_id)
    start_tile = tiles_by_id[start_tile_id]
    movement_costs = shortest_movement_costs(tiles_by_coord, start_coord=start_tile.coord)
    reachable_move_tile_ids = [
        str(tile.tile_id)
        for tile in scene.tiles
        if str(tile.tile_id) in movement_costs and int(movement_costs[str(tile.tile_id)]) <= int(movement_budget)
    ]
    attack_sources_by_tile_id: dict[str, set[str]] = {}
    for source_id in reachable_move_tile_ids:
        source = tiles_by_id[str(source_id)]
        for drow, dcol in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for distance in range(1, int(attack_range) + 1):
                target = tiles_by_coord.get((int(source.row) + int(drow) * distance, int(source.col) + int(dcol) * distance))
                if target is None or str(target.tile_id) == start_tile_id:
                    continue
                attack_sources_by_tile_id.setdefault(str(target.tile_id), set()).add(str(source_id))
    attackable_tile_ids = sorted(
        attack_sources_by_tile_id,
        key=lambda tile_id: (int(tiles_by_id[str(tile_id)].row), int(tiles_by_id[str(tile_id)].col), str(tile_id)),
    )
    sorted_sources = {
        str(tile_id): sorted(
            (str(source_id) for source_id in source_ids),
            key=lambda source_id: (int(tiles_by_id[str(source_id)].row), int(tiles_by_id[str(source_id)].col), str(source_id)),
        )
        for tile_id, source_ids in attack_sources_by_tile_id.items()
    }
    return movement_costs, start_tile_id, reachable_move_tile_ids, attackable_tile_ids, sorted_sources


def _select_attack_candidates(
    *,
    scene: RpgTacticalMapScene,
    movement_budget: int,
    attack_range: int,
    candidate_count: int,
    instance_seed: int,
) -> RpgTacticalMapOptionAttempt:
    """Select exactly one attackable candidate tile and plausible distractors."""

    movement_costs, start_tile_id, reachable_move_tile_ids, attackable_tile_ids, attack_sources = _reachable_and_attackable_tiles(
        scene=scene,
        movement_budget=int(movement_budget),
        attack_range=int(attack_range),
    )
    tiles_by_id = _tile_by_id(scene)
    start_tile = tiles_by_id[start_tile_id]
    reachable_set = {str(tile_id) for tile_id in reachable_move_tile_ids}
    attackable_set = {str(tile_id) for tile_id in attackable_tile_ids}
    answer_pool = [
        tiles_by_id[str(tile_id)]
        for tile_id in attackable_tile_ids
        if str(tile_id) not in reachable_set and str(tile_id) != start_tile_id
    ] or [
        tiles_by_id[str(tile_id)]
        for tile_id in attackable_tile_ids
        if str(tile_id) != start_tile_id
    ]
    invalid_pool = [
        tile
        for tile in scene.tiles
        if str(tile.tile_id) not in attackable_set and str(tile.tile_id) != start_tile_id
    ]
    if not answer_pool:
        raise ValueError("no attackable answer tile available")
    if len(invalid_pool) < int(candidate_count) - 1:
        raise ValueError("not enough non-attackable distractor tiles")

    rng = random.Random(f"{int(instance_seed)}:movement_attack_candidates:{int(movement_budget)}:{int(attack_range)}")
    tile_jitter = {str(tile.tile_id): float(rng.random()) for tile in scene.tiles}
    reachable_sources = [tiles_by_id[str(tile_id)] for tile_id in reachable_move_tile_ids]

    def source_distance(tile: RpgTacticalTile) -> int:
        return min(
            _tile_manhattan(tile, tiles_by_id[str(source_id)])
            for source_id in attack_sources.get(str(tile.tile_id), ())
        )

    def answer_sort_key(tile: RpgTacticalTile) -> tuple[int, int, int, float]:
        return (
            0 if str(tile.tile_id) not in reachable_set else 1,
            -source_distance(tile),
            _tile_manhattan(start_tile, tile),
            tile_jitter[str(tile.tile_id)],
        )

    answer_tile = sorted(answer_pool, key=answer_sort_key)[0]

    def invalid_plausibility(tile: RpgTacticalTile) -> tuple[int, int, int, float]:
        line_distances = [
            distance
            for source in reachable_sources
            for distance in (_cardinal_distance(source, tile),)
            if distance is not None and distance > int(attack_range)
        ]
        if line_distances:
            nearest_gap = min(abs(int(distance) - (int(attack_range) + 1)) for distance in line_distances)
            nearest_line = min(int(distance) for distance in line_distances)
            return (0, nearest_gap, nearest_line, tile_jitter[str(tile.tile_id)])
        nearest_manhattan = min(_tile_manhattan(tile, source) for source in reachable_sources)
        diagonal_near = 0 if nearest_manhattan <= int(attack_range) + 2 else 1
        return (1 + diagonal_near, nearest_manhattan, _tile_manhattan(start_tile, tile), tile_jitter[str(tile.tile_id)])

    def spread_score(tile: RpgTacticalTile, selected: Sequence[RpgTacticalTile], used_buckets: set[str]) -> tuple[int, int, int, float]:
        min_distance = min(_tile_manhattan(tile, existing) for existing in selected)
        bucket = _direction_bucket(start_tile, tile)
        plausible = invalid_plausibility(tile)
        return (
            1 if bucket not in used_buckets else 0,
            min_distance,
            -int(plausible[0]),
            -tile_jitter[str(tile.tile_id)],
        )

    def choose_spread_distractors(*, minimum_distance: int) -> list[RpgTacticalTile]:
        selected = [answer_tile]
        distractors: list[RpgTacticalTile] = []
        selected_tile_ids = {str(answer_tile.tile_id), start_tile_id}
        used_buckets = {_direction_bucket(start_tile, answer_tile)}
        remaining = sorted(invalid_pool, key=invalid_plausibility)
        while len(distractors) < int(candidate_count) - 1:
            eligible = [
                tile
                for tile in remaining
                if str(tile.tile_id) not in selected_tile_ids
                and min(_tile_manhattan(tile, existing) for existing in selected) >= int(minimum_distance)
            ]
            if not eligible:
                break
            chosen = max(eligible, key=lambda tile: spread_score(tile, selected, used_buckets))
            distractors.append(chosen)
            selected.append(chosen)
            selected_tile_ids.add(str(chosen.tile_id))
            used_buckets.add(_direction_bucket(start_tile, chosen))
            remaining = [tile for tile in remaining if str(tile.tile_id) != str(chosen.tile_id)]
        return distractors

    distractors: list[RpgTacticalTile] = []
    for min_distance in (3, 2, 1):
        distractors = choose_spread_distractors(minimum_distance=min_distance)
        if len(distractors) >= int(candidate_count) - 1:
            break
    if len(distractors) < int(candidate_count) - 1:
        raise ValueError("could not build enough attack-range distractors")

    labels = list(DEFAULT_CANDIDATE_LABELS[: int(candidate_count)])
    selected_label = str(labels[int(instance_seed) % int(candidate_count)])
    candidates_by_label: dict[str, str] = {selected_label: str(answer_tile.tile_id)}
    for label, tile in zip((label for label in labels if str(label) != selected_label), distractors, strict=True):
        candidates_by_label[str(label)] = str(tile.tile_id)
    candidates_by_label = {str(label): str(candidates_by_label[str(label)]) for label in labels}
    selected_sources = [str(source_id) for source_id in attack_sources[str(answer_tile.tile_id)]]
    return RpgTacticalMapOptionAttempt(
        candidate_tile_ids_by_label=candidates_by_label,
        selected_label=selected_label,
        relation_fields={
            "operation": "select_tile_attackable_after_movement",
            "movement_budget": int(movement_budget),
            "attack_range": int(attack_range),
            "attack_directions": ["up", "down", "left", "right"],
            "attack_range_ignores_terrain_cost": True,
            "terrain_movement_costs": dict(TERRAIN_MOVEMENT_COSTS),
            "blocked_terrain": [TERRAIN_WATER],
            "start_tile_id": str(start_tile_id),
            "reachable_move_tile_ids": list(reachable_move_tile_ids),
            "attackable_tile_ids": list(attackable_tile_ids),
            "attack_sources_by_tile_id": {str(tile_id): list(source_ids) for tile_id, source_ids in attack_sources.items()},
            "selected_attack_source_tile_ids": list(selected_sources),
        },
        execution_fields={
            "movement_budget": int(movement_budget),
            "attack_range": int(attack_range),
            "movement_costs_by_tile_id": {str(tile_id): int(cost) for tile_id, cost in movement_costs.items()},
            "start_tile_id": str(start_tile_id),
            "reachable_move_tile_ids": list(reachable_move_tile_ids),
            "attackable_tile_ids": list(attackable_tile_ids),
            "attack_sources_by_tile_id": {str(tile_id): list(source_ids) for tile_id, source_ids in attack_sources.items()},
            "selected_attack_source_tile_ids": list(selected_sources),
        },
        witness_fields={
            "movement_budget": int(movement_budget),
            "attack_range": int(attack_range),
            "selected_attack_source_tile_ids": list(selected_sources),
        },
    )


def _attack_range_text(attack_range: int) -> str:
    return "1 tile" if int(attack_range) == 1 else f"{int(attack_range)} tiles"


def _build_attack_range_plan(
    instance_seed: int,
    task_params: Mapping[str, Any],
    _query_probabilities: Mapping[str, float],
    _query_id: str,
) -> RpgTacticalMapOptionPlan:
    """Bind movement and attack range axes for the attackable-tile selection task."""

    movement_budget, movement_budget_probabilities = select_int_from_support(
        instance_seed=int(instance_seed),
        params=task_params,
        defaults=_GEN_DEFAULTS,
        support_key="movement_budget_support",
        explicit_key="movement_budget",
        fallback_support=DEFAULT_MOVEMENT_BUDGET_SUPPORT,
        namespace=f"{TASK_ID}:movement_budget",
    )
    attack_range, attack_range_probabilities = select_int_from_support(
        instance_seed=int(instance_seed),
        params=task_params,
        defaults=_GEN_DEFAULTS,
        support_key="attack_range_support",
        explicit_key="attack_range",
        fallback_support=DEFAULT_ATTACK_RANGE_SUPPORT,
        namespace=f"{TASK_ID}:attack_range",
    )
    candidate_count = int(task_params.get("candidate_count", group_default(_GEN_DEFAULTS, "candidate_count", DEFAULT_CANDIDATE_COUNT)))
    if candidate_count != DEFAULT_CANDIDATE_COUNT:
        raise ValueError("rpg tactical map attack task currently supports exactly four candidate tiles")

    def build_attempt(scene: RpgTacticalMapScene, attempt_seed: int) -> RpgTacticalMapOptionAttempt:
        return _select_attack_candidates(
            scene=scene,
            movement_budget=int(movement_budget),
            attack_range=int(attack_range),
            candidate_count=int(candidate_count),
            instance_seed=int(attempt_seed),
        )

    def build_render_map(scene: RpgTacticalMapScene, attempt: RpgTacticalMapOptionAttempt) -> Mapping[str, Any]:
        execution = attempt.execution_fields
        return movement_attack_range_render_map(
            scene=scene,
            candidate_tile_ids_by_label=attempt.candidate_tile_ids_by_label,
            selected_label=str(attempt.selected_label),
            movement_costs_by_tile_id=execution["movement_costs_by_tile_id"],
            movement_budget=int(execution["movement_budget"]),
            attack_range=int(execution["attack_range"]),
            reachable_move_tile_ids=execution["reachable_move_tile_ids"],
            attackable_tile_ids=execution["attackable_tile_ids"],
            attack_sources_by_tile_id=execution["attack_sources_by_tile_id"],
        )

    return RpgTacticalMapOptionPlan(
        prompt_query_key=PROMPT_QUERY_KEY,
        prompt_slots={
            "movement_points": str(int(movement_budget)),
            "attack_range_text": _attack_range_text(int(attack_range)),
            "terrain_rules": rpg_tactical_map_terrain_rules_text(),
        },
        answer_hint_key="answer_hint_movement_attack_range_tile_label",
        annotation_hint_key="annotation_hint_movement_attack_range_tile_label",
        json_example_key="json_example_movement_attack_range_tile_label",
        json_example_answer_only_key="json_example_answer_only_movement_attack_range_tile_label",
        query_params={
            "movement_budget": int(movement_budget),
            "movement_budget_probabilities": dict(movement_budget_probabilities),
            "attack_range": int(attack_range),
            "attack_range_probabilities": dict(attack_range_probabilities),
            "candidate_count": int(candidate_count),
            "candidate_labels": list(DEFAULT_CANDIDATE_LABELS[: int(candidate_count)]),
        },
        build_attempt=build_attempt,
        build_render_map=build_render_map,
        failure_label="movement attack range candidates",
    )


@register_task
class IllustrationsRpgTacticalMapMovementAttackRangeTileLabelTask:
    """Choose the lettered tile attackable after movement."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_rpg_tactical_map_option_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            prompt_defaults_source=_PROMPT_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_plan=_build_attack_range_plan,
        )


__all__ = [
    "IllustrationsRpgTacticalMapMovementAttackRangeTileLabelTask",
    "PROMPT_QUERY_KEY",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
