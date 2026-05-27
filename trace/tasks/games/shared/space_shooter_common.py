"""Shared Space-shooter helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SUPPORTED_SPACE_SHOOTER_QUERY_IDS: Tuple[str, ...] = (
    "clear_shot_count",
    "projectile_intercept_count",
    "highest_threat_label",
    "safe_lane_count",
)
SUPPORTED_SPACE_SHOOTER_SCENE_VARIANTS: Tuple[str, ...] = ("defense_wave",)
SUPPORTED_SPACE_SHOOTER_STYLE_VARIANTS: Tuple[str, ...] = (
    "neon",
    "deep_space",
    "vector",
    "amber",
    "terminal",
)


@dataclass(frozen=True)
class SpaceEnemy:
    """One visible enemy ship."""

    enemy_id: str
    label: str
    lane: int
    y_slot: int
    dx_frac: float
    dy_px: float


@dataclass(frozen=True)
class SpaceProjectile:
    """One visible enemy projectile."""

    projectile_id: str
    lane: int
    y_slot: int
    dx_frac: float
    dy_px: float


@dataclass(frozen=True)
class SpaceBlocker:
    """One visible shield/asteroid blocker."""

    blocker_id: str
    lane: int
    y_slot: int
    blocker_type: str
    dx_frac: float
    dy_px: float


@dataclass(frozen=True)
class SpaceShooterSample:
    """Generated Space-shooter scene state."""

    lane_count: int
    query_id: str
    scene_variant: str
    answer: int | str
    player_lane: int
    enemies: Tuple[SpaceEnemy, ...]
    projectiles: Tuple[SpaceProjectile, ...]
    blockers: Tuple[SpaceBlocker, ...]
    clear_enemy_ids: Tuple[str, ...]
    intercept_projectile_ids: Tuple[str, ...]
    highest_threat_enemy_id: str
    highest_threat_label: str
    safe_lane_indices: Tuple[int, ...]
    evidence_entity_ids: Tuple[str, ...]
    target_answer: int | None
    construction_mode: str


def lane_entity_id(lane: int) -> str:
    """Return the stable render/entity id for one bottom lane pad."""

    return f"lane_{int(lane)}"


def sorted_entity_ids(values: Tuple[str, ...] | list[str]) -> Tuple[str, ...]:
    """Return stable sorted entity ids."""

    return tuple(sorted(str(value) for value in values))


def validate_space_shooter_sample(sample: SpaceShooterSample) -> None:
    """Validate that the generated answer and evidence match the active query."""

    lane_count = int(sample.lane_count)
    if lane_count <= 0:
        raise ValueError("space shooter lane_count must be positive")
    if not (0 <= int(sample.player_lane) < lane_count):
        raise ValueError("space shooter player_lane out of range")
    enemy_ids = [enemy.enemy_id for enemy in sample.enemies]
    projectile_ids = [projectile.projectile_id for projectile in sample.projectiles]
    blocker_ids = [blocker.blocker_id for blocker in sample.blockers]
    if len(enemy_ids) != len(set(enemy_ids)):
        raise ValueError("space shooter enemy ids must be unique")
    if len(projectile_ids) != len(set(projectile_ids)):
        raise ValueError("space shooter projectile ids must be unique")
    if len(blocker_ids) != len(set(blocker_ids)):
        raise ValueError("space shooter blocker ids must be unique")
    if len(set(enemy.label for enemy in sample.enemies)) != len(sample.enemies):
        raise ValueError("space shooter enemy labels must be unique")
    known_entities = set(enemy_ids) | set(projectile_ids) | set(blocker_ids) | {
        lane_entity_id(lane) for lane in range(lane_count)
    }
    if not set(sample.evidence_entity_ids) <= known_entities:
        raise ValueError("space shooter evidence references unknown entities")
    if not set(sample.clear_enemy_ids) <= set(enemy_ids):
        raise ValueError("space shooter clear shot ids must reference enemies")
    if not set(sample.intercept_projectile_ids) <= set(projectile_ids):
        raise ValueError("space shooter intercept ids must reference projectiles")
    if sample.highest_threat_enemy_id not in set(enemy_ids):
        raise ValueError("space shooter highest threat id must reference an enemy")
    if sample.highest_threat_label not in {enemy.label for enemy in sample.enemies}:
        raise ValueError("space shooter highest threat label must reference an enemy")
    if not set(sample.safe_lane_indices) <= set(range(lane_count)):
        raise ValueError("space shooter safe lanes out of range")

    query = str(sample.query_id)
    if query == "clear_shot_count":
        expected_answer: int | str = len(sample.clear_enemy_ids)
        expected_evidence = set(sample.clear_enemy_ids)
    elif query == "projectile_intercept_count":
        expected_answer = len(sample.intercept_projectile_ids)
        expected_evidence = set(sample.intercept_projectile_ids)
    elif query == "highest_threat_label":
        expected_answer = str(sample.highest_threat_label)
        expected_evidence = {str(sample.highest_threat_enemy_id)}
    elif query == "safe_lane_count":
        expected_answer = len(sample.safe_lane_indices)
        expected_evidence = {lane_entity_id(lane) for lane in sample.safe_lane_indices}
    else:
        raise ValueError(f"unsupported space shooter query_id: {sample.query_id}")
    if sample.answer != expected_answer:
        raise ValueError("space shooter answer does not match active query")
    if set(sample.evidence_entity_ids) != expected_evidence:
        raise ValueError("space shooter evidence ids do not match active query")


__all__ = [
    "SUPPORTED_SPACE_SHOOTER_QUERY_IDS",
    "SUPPORTED_SPACE_SHOOTER_SCENE_VARIANTS",
    "SUPPORTED_SPACE_SHOOTER_STYLE_VARIANTS",
    "SpaceBlocker",
    "SpaceEnemy",
    "SpaceProjectile",
    "SpaceShooterSample",
    "lane_entity_id",
    "sorted_entity_ids",
    "validate_space_shooter_sample",
]
