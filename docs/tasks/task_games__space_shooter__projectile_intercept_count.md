# `task_games__space_shooter__projectile_intercept_count`

## Contract
1. Domain: `games`
2. Scene id: `space_shooter`
3. Source task group: `space_shooter`
4. Query id: `projectile_intercept_count`
5. Objective: Count falling enemy shots in the same lane as the player ship.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the counted enemy shots.
3. Public `query_variant` is `default`; `projectile_intercept_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Space-shooter playfield renderer.
2. Prompt bundle: `games_space_shooter_v0`
3. Projectiles are lane-aligned; the query asks for enemy-shot alignment with the player ship. The player lane pad is visually emphasized in the shared renderer.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, enemy count, target answer, player lane, and visual style remain explicit params inside the task.
