# `task_games__chess__check_attacker_count`

## Contract
1. Domain: `games`
2. Scene id: `chess`
3. Source task group: `chess`
4. Query id: `check_attacker_count`
5. Objective: Count opponent pieces attacking the blue-outlined king.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set containing the attacking opponent-piece boxes.
3. `check_attacker_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games Chess-board renderer for its scene id.
2. Prompt bundle: `games_chess_v0`
3. Generation constructs a unique marked-king attack count under standard attack patterns, excluding castling, en passant, and promotion cases.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene density, visual style, marked king color, and target-answer support remain explicit params inside the task.
