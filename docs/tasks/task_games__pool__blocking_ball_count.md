# `task_games__pool__blocking_ball_count`

## Contract
1. Domain: `games`
2. Scene id: `pool`
3. Source task group: `pool`
4. Query id: `blocking_ball_count`
5. Objective: Count balls that block the marked shot lane.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `point_set` over the center of every ball blocking the marked shot lane.
3. `blocking_ball_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games Pool-table renderer for its scene id.
2. Prompt bundle: `games_pool_v0`
3. Generation marks one object ball and one pocket, draws the two-segment shot lane, and places a controlled number of blockers on that lane.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Visual style, line-clearance radius, marked lane construction, and answer support remain explicit params inside the task.
