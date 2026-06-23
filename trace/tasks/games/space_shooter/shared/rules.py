"""Space-shooter lane and threat rules."""

from __future__ import annotations

from .state import SpaceBlocker, SpaceEnemy, SpaceProjectile


def lower_enemy_exists(enemy: SpaceEnemy, enemies: tuple[SpaceEnemy, ...]) -> bool:
    """Return whether another enemy is below this enemy in the same lane."""

    return any(
        int(other.lane) == int(enemy.lane) and int(other.y_slot) > int(enemy.y_slot)
        for other in enemies
        if str(other.enemy_id) != str(enemy.enemy_id)
    )


def lower_blocker_exists(enemy: SpaceEnemy, blockers: tuple[SpaceBlocker, ...]) -> bool:
    """Return whether a shield or asteroid blocks this enemy from below."""

    return any(
        int(blocker.lane) == int(enemy.lane) and int(blocker.y_slot) > int(enemy.y_slot)
        for blocker in blockers
    )


def clear_shot_enemy_ids(enemies: tuple[SpaceEnemy, ...], blockers: tuple[SpaceBlocker, ...]) -> tuple[str, ...]:
    """Return enemy ids with no lower enemy or blocker in their lane."""

    return tuple(
        str(enemy.enemy_id)
        for enemy in enemies
        if not lower_enemy_exists(enemy, enemies) and not lower_blocker_exists(enemy, blockers)
    )


def projectile_ids_in_lane(projectiles: tuple[SpaceProjectile, ...], lane: int) -> tuple[str, ...]:
    """Return projectile ids in one lane."""

    return tuple(str(projectile.projectile_id) for projectile in projectiles if int(projectile.lane) == int(lane))


def blocked_pad_lanes(projectiles: tuple[SpaceProjectile, ...], blockers: tuple[SpaceBlocker, ...]) -> set[int]:
    """Return lanes made unsafe by a projectile or bottom-pad asteroid."""

    lanes = {int(projectile.lane) for projectile in projectiles}
    lanes.update(int(blocker.lane) for blocker in blockers if int(blocker.y_slot) >= 6)
    return lanes
