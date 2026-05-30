# `task_games__go__group_adjacent_enemy_count`

## Contract
1. Domain: `games`
2. Scene id: `go`
3. Source task group: `go`
4. Query id: `marked_group_adjacent_enemy_count`
5. Objective: Count enemy stones adjacent to the marked Go group.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `point_set` at adjacent enemy-stone centers.
3. `marked_group_adjacent_enemy_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_go_v0`
3. Default adjacent-enemy answer support is `1..6`.
4. Rendering uses shared games/puzzles panel backgrounds, six board/stone themes, unit-size jitter, dynamic canvas sizing, and layout jitter.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as player color, board size, style, and target-answer support remain explicit params inside the task.
