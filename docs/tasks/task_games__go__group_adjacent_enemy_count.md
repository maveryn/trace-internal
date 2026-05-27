# `task_games__go__group_adjacent_enemy_count`

## Contract
1. Domain: `games`
2. Scene id: `go`
3. Source task group: `go`
4. Query id: `marked_group_adjacent_enemy_count`
5. Objective: Count enemy stones adjacent to the marked Go group.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over adjacent enemy stones.
3. Public `query_variant` is `default`; `marked_group_adjacent_enemy_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_go_v0`
3. Default adjacent-enemy answer support is `1..6`.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as player color, board size, axis, direction, style, and target-answer support remain explicit params inside the task.
