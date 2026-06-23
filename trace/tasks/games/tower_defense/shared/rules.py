"""Tower-defense geometry and coverage rules."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from .state import Point, TowerDefenseSample, TowerDefenseTower


MODE_MARKED_ENEMY = "enemy_tower_coverage"
MODE_PATH_NODES = "path_node_coverage"


def tower_entity_id(index: int) -> str:
    """Return stable entity id for one tower."""

    return f"tower_{int(index):02d}"


def path_segment_entity_id(index: int) -> str:
    """Return stable entity id for one discrete path witness."""

    return f"path_segment_{int(index):02d}"


def enemy_entity_id() -> str:
    """Return stable entity id for the marked enemy."""

    return "marked_enemy"


def local_distance(point_a: Sequence[float], point_b: Sequence[float]) -> float:
    """Return local render-space distance between two points."""

    return math.hypot(float(point_a[0]) - float(point_b[0]), float(point_a[1]) - float(point_b[1]))


def tower_covers_point(tower: TowerDefenseTower, point: Sequence[float], *, epsilon_px: float = 1e-6) -> bool:
    """Return whether one tower covers a point under the visible circle rule."""

    return float(local_distance(tower.center_px, point)) <= float(tower.range_radius_px) + float(epsilon_px)


def covered_tower_ids(towers: Iterable[TowerDefenseTower], point: Sequence[float]) -> tuple[str, ...]:
    """Return ids of towers whose range covers the point."""

    return tuple(str(tower.tower_id) for tower in towers if tower_covers_point(tower, point))


def covered_path_segment_ids(towers: Iterable[TowerDefenseTower], path_points: Sequence[Point]) -> tuple[str, ...]:
    """Return ids of path nodes covered by at least one tower."""

    tower_tuple = tuple(towers)
    return tuple(
        path_segment_entity_id(index)
        for index, point in enumerate(path_points)
        if any(tower_covers_point(tower, point) for tower in tower_tuple)
    )


def validate_tower_defense_sample(sample: TowerDefenseSample) -> None:
    """Validate one generated tower-defense sample contract."""

    if str(sample.mode) not in {MODE_MARKED_ENEMY, MODE_PATH_NODES}:
        raise ValueError(f"unsupported tower-defense mode: {sample.mode}")
    if int(sample.map_width_px) <= 0 or int(sample.map_height_px) <= 0:
        raise ValueError("tower-defense map dimensions must be positive")
    if len(sample.path_points_px) < 6:
        raise ValueError("tower-defense path needs at least six visible points")
    tower_ids = [str(tower.tower_id) for tower in sample.towers]
    if len(tower_ids) != len(set(tower_ids)):
        raise ValueError("tower ids must be unique")
    if not sample.towers:
        raise ValueError("tower-defense sample must include at least one tower")
    for tower in sample.towers:
        x, y = float(tower.center_px[0]), float(tower.center_px[1])
        if not (0.0 <= x <= float(sample.map_width_px) and 0.0 <= y <= float(sample.map_height_px)):
            raise ValueError(f"tower center outside map: {tower.tower_id}")
        if float(tower.range_radius_px) <= 0.0:
            raise ValueError(f"tower range must be positive: {tower.tower_id}")
    if str(sample.mode) == MODE_MARKED_ENEMY:
        if sample.enemy is None:
            raise ValueError("marked enemy scene requires an enemy")
        if not (0 <= int(sample.enemy.path_index) < len(sample.path_points_px)):
            raise ValueError("marked enemy path_index must reference a visible path point")
        expected_enemy_point = sample.path_points_px[int(sample.enemy.path_index)]
        if local_distance(sample.enemy.center_px, expected_enemy_point) > 1e-6:
            raise ValueError("marked enemy center must lie on its path point")
        expected_annotation = covered_tower_ids(sample.towers, sample.enemy.center_px)
    else:
        expected_annotation = covered_path_segment_ids(sample.towers, sample.path_points_px)
    if tuple(str(value) for value in sample.annotation_entity_ids) != tuple(expected_annotation):
        raise ValueError("tower-defense annotation ids must match the task contract")
    if int(sample.answer) != len(expected_annotation):
        raise ValueError("tower-defense answer must equal annotation count")
    if int(sample.answer) != int(sample.target_answer):
        raise ValueError("tower-defense answer must equal target_answer")


def visible_tower_trace(towers: Sequence[TowerDefenseTower]) -> tuple[dict, ...]:
    """Return trace-friendly tower records."""

    return tuple(
        {
            "tower_id": str(tower.tower_id),
            "center_px_local": [round(float(tower.center_px[0]), 3), round(float(tower.center_px[1]), 3)],
            "range_radius_px": round(float(tower.range_radius_px), 3),
            "covers_target": bool(tower.covers_target),
        }
        for tower in towers
    )


__all__ = [
    "MODE_MARKED_ENEMY",
    "MODE_PATH_NODES",
    "covered_path_segment_ids",
    "covered_tower_ids",
    "enemy_entity_id",
    "local_distance",
    "path_segment_entity_id",
    "tower_covers_point",
    "tower_entity_id",
    "validate_tower_defense_sample",
    "visible_tower_trace",
]
