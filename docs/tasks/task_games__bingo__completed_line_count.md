# `task_games__bingo__completed_line_count`

## Contract
1. Domain: `games`
2. Scene id: `bingo`
3. Source task group: `bingo`
4. Query id: `completed_axis_line_count`
5. Objective: Count completed bingo lines along a sampled axis (`row|column`).

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over marked cells in the counted completed lines.
3. Public `query_variant` is `default`; `completed_axis_line_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_bingo_v0`
## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as player color, board size, axis, direction, style, and target-answer support remain explicit params inside the task.
