# `task_games__brick_breaker__trajectory_target_label`

## Contract
1. Domain: `games`
2. Scene id: `brick_breaker`
3. Source task group: `brick_breaker`
4. Query ids: `next_hit_label`, `paddle_catch_label`
5. Objective: Identify the labeled brick or catch lane reached by the visible straight ball trajectory.

## Answer and Evidence
1. Answer type: `string`
2. Evidence type: bbox_set over the selected brick or bottom catch lane pad.
3. Public `query_variant` is `default`; the concrete trajectory target branch is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Brick-breaker playfield renderer.
2. Prompt bundle: `games_brick_breaker_v0`
3. The short dashed arrow shows the ball's current straight direction; solvers extrapolate it either to the first brick or to the bottom catch lane.
4. Visible brick labels are capped to single uppercase letters `A..Z`.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Brick grid size, catch-lane count, query id, and visual style remain explicit params inside the task.
