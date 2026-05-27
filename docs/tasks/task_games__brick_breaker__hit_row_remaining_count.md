# `task_games__brick_breaker__hit_row_remaining_count`

## Contract
1. Domain: `games`
2. Scene id: `brick_breaker`
3. Source task group: `brick_breaker`
4. Query id: `hit_row_remaining_count`
5. Objective: Extrapolate the shown ball trajectory to the hit brick, remove that brick, and count how many visible bricks remain in the same row.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the bricks left in the hit brick's row after removal.
3. Public `query_variant` is `default`; `hit_row_remaining_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Brick-breaker playfield renderer.
2. Prompt bundle: `games_brick_breaker_v0`
3. The sampler constructs a unique hit brick in the lower brick row and records the row-survivor brick ids as the evidence set.
4. Visible brick labels are capped to single uppercase letters `A..Z`.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Brick grid size, catch-lane count, row-survivor count, and visual style remain explicit params inside the task.
