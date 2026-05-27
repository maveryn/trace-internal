# `task_games__crossing__moving_object_count`

## Contract
1. Domain: `games`
2. Scene id: `crossing`
3. Source task group: `crossing`
4. Query id: `moving_object_count`
5. Objective: Count moving objects that intersect the marked route at their row-crossing ticks.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the moving objects that intersect the marked route.
3. `moving_object_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games lane-crossing renderer.
2. Prompt bundle: `games_crossing_v0`
3. The count includes only moving objects occupying the same lane cell as the marked route at the tick when the route crosses that row.
4. The marked route is visually emphasized with larger numbered route cells, and
   the task uses lower non-intersecting traffic clutter than the shared scene
   default.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, row count, target count, and visual style remain explicit params inside the task; the default answer support is `1..5`.
