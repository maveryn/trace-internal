"""Space-shooter lane and threat rules."""

from __future__ import annotations

from .state import SpaceEnemy, SpaceProjectile


def lower_enemy_exists(enemy: SpaceEnemy, enemies: tuple[SpaceEnemy, ...]) -> bool:
    """Return whether another enemy is below this enemy in the same lane."""

    return any(
        int(other.lane) == int(enemy.lane) and int(other.y_slot) > int(enemy.y_slot)
        for other in enemies
        if str(other.enemy_id) != str(enemy.enemy_id)
    )


def lower_player_projectile_exists(enemy: SpaceEnemy, projectiles: tuple[SpaceProjectile, ...]) -> bool:
    """Return whether an upward player shot blocks this enemy from below."""

    return any(
        str(projectile.owner) == "player"
        and int(projectile.lane) == int(enemy.lane)
        and int(projectile.y_slot) > int(enemy.y_slot)
        for projectile in projectiles
    )


def clear_shot_enemy_ids(enemies: tuple[SpaceEnemy, ...], projectiles: tuple[SpaceProjectile, ...]) -> tuple[str, ...]:
    """Return enemy ids with no lower enemy or player shot in their lane."""

    return tuple(
        str(enemy.enemy_id)
        for enemy in enemies
        if not lower_enemy_exists(enemy, enemies) and not lower_player_projectile_exists(enemy, projectiles)
    )


def enemy_projectile_ids_in_lane(projectiles: tuple[SpaceProjectile, ...], lane: int) -> tuple[str, ...]:
    """Return enemy projectile ids in one lane."""

    return tuple(
        str(projectile.projectile_id)
        for projectile in projectiles
        if str(projectile.owner) == "enemy" and int(projectile.lane) == int(lane)
    )


def enemy_projectile_lanes(projectiles: tuple[SpaceProjectile, ...]) -> set[int]:
    """Return lanes threatened by falling enemy shots."""

    return {int(projectile.lane) for projectile in projectiles if str(projectile.owner) == "enemy"}
