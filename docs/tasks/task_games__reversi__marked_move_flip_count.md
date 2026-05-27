# `task_games__reversi__marked_move_flip_count`

## Contract
1. Domain: `games`
2. Scene id: `reversi`
3. Source task group: `reversi`
4. Query id: `flip_count_for_marked_move`
5. Objective: Count discs flipped by the marked Reversi move.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over flipped discs.
3. Public `query_variant` is `default`; `flip_count_for_marked_move` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_reversi_v0`
## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as player color, board size, axis, direction, style, and target-answer support remain explicit params inside the task.
