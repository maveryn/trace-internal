# `task_games__crossing__collision_time_value`

## Contract
1. Domain: `games`
2. Scene id: `crossing`
3. Source task group: `crossing`
4. Query id: `collision_time_value`
5. Objective: Return the first tick at which the marked route collides with a moving object.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the first colliding moving object and the marked route cell at that tick.
3. `collision_time_value` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games lane-crossing renderer.
2. Prompt bundle: `games_crossing_v0`
3. The marked route shows tick numbers on its row cells; the answer is unique by construction.
4. Collision-time instances cap nonessential extra traffic per row so the target moving-object event remains visually resolvable while preserving distractors.
5. Public calibration support uses contiguous first-collision ticks `1..5`; the harder high-tail tick `6` was removed after Qwen2.5 calibration stayed below the mean solve-rate gate.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, row count, target tick, and visual style remain explicit params inside the task.
