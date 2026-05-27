# `task_games__space_shooter__clear_shot_count`

## Contract
1. Domain: `games`
2. Scene id: `space_shooter`
3. Source task group: `space_shooter`
4. Query id: `clear_shot_count`
5. Objective: Count enemy ships with no enemy ship, shield, or asteroid below them in the same lane.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the counted enemy ships.
3. Public `query_variant` is `default`; `clear_shot_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Space-shooter playfield renderer.
2. Prompt bundle: `games_space_shooter_v0`
3. Enemy shots do not block the clear-shot count; only lower enemy ships, shields, and asteroids block the lane. The current sampler keeps the clear-shot scene sparse enough that the visible obstruction is normally a shield or asteroid below the candidate enemy.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, target answer, and visual style remain explicit params inside the task; the clear-shot scene derives the visible enemy count from the lane construction.
