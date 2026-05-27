# `task_games__nine_mens_morris__pieces_in_mill_count`

## Contract
1. Domain: `games`
2. Scene id: `nine_mens_morris`
3. Source task group: `nine_mens_morris`
4. Query id: `all_pieces_in_mill_count`
5. Objective: Count all visible pieces that belong to at least one mill.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over all counted mill pieces.
3. Public `query_variant` is `default`; `all_pieces_in_mill_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_nine_mens_morris_v0`
## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as player color, board size, axis, direction, style, and target-answer support remain explicit params inside the task.
