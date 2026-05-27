# `task_games__cards__exact_triple_count`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Source task group: `cards`
4. Query id: `exact_triple_count`
5. Objective: Count ranks that appear exactly three times in the hand.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over cards belonging to exact triples.
3. `exact_triple_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_cards_v0`
## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as player color, board size, axis, direction, style, and target-answer support remain explicit params inside the task.
