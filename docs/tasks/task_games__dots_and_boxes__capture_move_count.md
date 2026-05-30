# `task_games__dots_and_boxes__capture_move_count`

## Contract
1. Domain: `games`
2. Scene id: `dots_and_boxes`
3. Source task group: `dots_and_boxes`
4. Query ids: `capture_move_count`, `highlighted_candidate_capture_count`
5. Objective: Count missing-edge moves that would complete at least one box, either over all missing edges or over highlighted candidate edges.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set` over the counted capture edge gaps.
3. The concrete internal query is retained as `query_id` and `query_spec.params.query_id` for diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_dots_and_boxes_v0`
3. The highlighted-candidate branch is represented by the `highlighted_candidate_capture_count` query id.
4. Rendering uses shared games/puzzles panel backgrounds, sampled title fonts, unit-size jitter, dynamic canvas sizing, layout jitter, and six board themes.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as board size, candidate-edge count, style, and target-answer support remain explicit params inside the task.
