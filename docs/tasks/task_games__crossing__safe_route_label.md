# `task_games__crossing__safe_route_label`

## Contract
1. Domain: `games`
2. Scene id: `crossing`
3. Source task group: `crossing`
4. Query id: `safe_start_label` or `goal_reachable_label`
5. Objective: Identify the unique labeled route choice that reaches the goal without colliding with moving objects.

## Answer and Evidence
1. Answer type: `string`
2. Evidence type: `bbox_set` over the selected start pad or route option.
3. The sampled label-query mode is retained as `query_id` and `query_spec.params.query_id` for diagnostics.

## Implementation
1. This task uses the shared games lane-crossing renderer.
2. Prompt bundle: `games_crossing_v0`
3. Motion is discrete by tick: the runner advances one traffic row upward per tick, and each moving object shifts one lane cell per tick in its arrow direction.
4. The task samples between straight start-pad and labeled route-option constructions; each construction guarantees a unique safe answer.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, row count, route-option count, target label, internal query mode, and visual style remain explicit params inside the task.
