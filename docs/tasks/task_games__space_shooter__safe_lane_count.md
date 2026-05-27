# `task_games__space_shooter__safe_lane_count`

## Contract
1. Domain: `games`
2. Scene id: `space_shooter`
3. Source task group: `space_shooter`
4. Query id: `safe_lane_count`
5. Objective: Count bottom lane pads with no enemy shot in that lane and no asteroid on the pad.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the safe bottom lane pads.
3. Public `query_variant` is `default`; `safe_lane_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Space-shooter playfield renderer.
2. Prompt bundle: `games_space_shooter_v0`
3. The evidence is the visible bottom lane pads counted as safe. Lane guides in the shared renderer connect the pads to falling shots and blockers.
4. The sampler keeps unrelated enemy ships in a sparse upper backdrop for this task; only falling enemy shots and asteroids on bottom pads determine pad safety.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, target answer, safe lane set, and visual style remain explicit params inside the task.
