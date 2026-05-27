# `task_games__cards__longest_run_length`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Source task group: `cards`
4. Query id: `longest_run_length`
5. Objective: Return the longest consecutive rank run in the visible row-major hand order.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the cards in one longest run.
3. Public `query_variant` is `default`; `longest_run_length` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_cards_v0`
## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as player color, board size, axis, direction, style, and target-answer support remain explicit params inside the task.
